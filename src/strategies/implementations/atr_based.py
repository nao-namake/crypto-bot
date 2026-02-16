"""
ATRレンジ消尽戦略実装

Phase 54.12: 完全リファクタリング

核心思想:
「今日の価格変動がATRの大部分を消費した → これ以上動かない → 反転を狙う」

BBReversalとの違い:
- BBReversal: 価格位置（バンド端）で判断 → 「価格が極端な位置にいる」
- ATRレンジ: 変動量（ATR消尽率）で判断 → 「今日の動きは十分だった」

戦略ロジック:
1. ATR消尽率計算（当日値幅 / ATR14）
2. レンジ相場確認（ADX < 25）
3. 消尽率閾値判定（70%以上で反転狙い）
4. RSIで反転方向決定
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from ...core.exceptions import StrategyError
from ..base.strategy_base import StrategyBase, StrategySignal
from ..strategy_registry import StrategyRegistry
from ..utils import EntryAction, SignalBuilder, StrategyType


@StrategyRegistry.register(name="ATRBased", strategy_type=StrategyType.ATR_BASED)
class ATRBasedStrategy(StrategyBase):
    """
    ATRレンジ消尽戦略

    ATRの消尽率に基づく逆張り戦略。
    価格がATRの大部分を消費した時点で反転を狙う。
    レンジ相場に特化。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """戦略初期化."""
        from ...core.config.threshold_manager import get_threshold

        default_config = {
            # ATR消尽率パラメータ（Phase 55.4: PF1以上の設定）
            "exhaustion_threshold": get_threshold(
                "strategies.atr_based.exhaustion_threshold", 0.70
            ),
            "high_exhaustion_threshold": get_threshold(
                "strategies.atr_based.high_exhaustion_threshold", 0.85
            ),
            # レンジ相場フィルタ
            "adx_range_threshold": get_threshold("strategies.atr_based.adx_range_threshold", 25),
            # RSI反転判定（メイン条件）
            "rsi_upper": get_threshold("strategies.atr_based.rsi_upper", 60),
            "rsi_lower": get_threshold("strategies.atr_based.rsi_lower", 40),
            "rsi_confirmation_bonus": get_threshold(
                "strategies.atr_based.rsi_confirmation_bonus", 0.05
            ),
            # 信頼度設定
            "min_confidence": get_threshold("strategies.atr_based.min_confidence", 0.35),
            "hold_confidence": get_threshold("strategies.atr_based.hold_confidence", 0.20),
            "base_confidence": get_threshold("strategies.atr_based.base_confidence", 0.40),
            "high_confidence": get_threshold("strategies.atr_based.high_confidence", 0.60),
            # スコア閾値（Phase 55.4: BB確認込みで0.65）
            "min_score_threshold": get_threshold("strategies.atr_based.min_score_threshold", 0.65),
            # BB位置確認（ボーナスとして使用、メイン条件ではない）
            "bb_position_enabled": get_threshold("strategies.atr_based.bb_position_enabled", True),
            "bb_position_threshold": get_threshold(
                "strategies.atr_based.bb_position_threshold", 0.20
            ),
            "bb_as_main_condition": get_threshold(
                "strategies.atr_based.bb_as_main_condition", False
            ),
            # ストップロス設定
            "sl_atr_multiplier": get_threshold("strategies.atr_based.sl_atr_multiplier", 1.5),
            # リスク管理（共通設定から取得）
            "stop_loss_atr_multiplier": get_threshold("sl_atr_normal_vol", 2.0),
            "take_profit_ratio": get_threshold(
                "position_management.take_profit.default_ratio", 1.29
            ),
        }
        merged_config = {**default_config, **(config or {})}
        super().__init__(name="ATRBased", config=merged_config)
        self.logger.info(
            f"ATRレンジ消尽戦略初期化: 消尽閾値={self.config['exhaustion_threshold']}, "
            f"ADX閾値={self.config['adx_range_threshold']}, "
            f"BB条件メイン={self.config['bb_as_main_condition']}"
        )

    def analyze(
        self, df: pd.DataFrame, multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> StrategySignal:
        """
        市場分析とシグナル生成

        ATRレンジ消尽に基づく反転シグナルを生成。

        Phase 56.10: BB位置メイン条件化
        - 消尽率 → レンジ相場 → BB位置 の順にチェック
        - BB位置でシグナル方向を決定
        - RSI確認は信頼度ボーナスとして使用
        """
        try:
            self.logger.debug("[ATRレンジ] 分析開始")
            current_price = float(df["close"].iloc[-1])

            # Step 1: 消尽率チェック（必須条件）
            exhaustion_analysis = self._calculate_exhaustion_ratio(df)
            if not exhaustion_analysis["is_exhausted"]:
                return SignalBuilder.create_hold_signal(
                    strategy_name=self.name,
                    current_price=current_price,
                    reason=exhaustion_analysis["reason"],
                    strategy_type=StrategyType.ATR_BASED,
                )

            # Step 2: レンジ相場チェック（必須条件）
            range_check = self._check_range_market(df)
            if not range_check["is_range"]:
                return SignalBuilder.create_hold_signal(
                    strategy_name=self.name,
                    current_price=current_price,
                    reason=range_check["reason"],
                    strategy_type=StrategyType.ATR_BASED,
                )

            # Phase 56.10: BB位置メイン条件モード
            if self.config.get("bb_as_main_condition", True):
                return self._analyze_bb_main_mode(
                    df, current_price, exhaustion_analysis, range_check, multi_timeframe_data
                )

            # 従来モード: RSI方向決定（必須条件）
            direction_analysis = self._determine_reversal_direction(df)
            if direction_analysis["action"] == EntryAction.HOLD:
                return SignalBuilder.create_hold_signal(
                    strategy_name=self.name,
                    current_price=current_price,
                    reason=direction_analysis["reason"],
                    strategy_type=StrategyType.ATR_BASED,
                )

            # BB位置確認（オプション：信頼度ボーナス）
            bb_check = self._check_bb_position(df)

            # 統合判定とシグナル生成
            decision = self._create_decision(exhaustion_analysis, direction_analysis, range_check)

            # BB帯端にいる場合は信頼度を上げる
            if self.config.get("bb_position_enabled", True) and bb_check["at_band_edge"]:
                rsi_direction = direction_analysis["action"]
                bb_direction = bb_check["direction"]
                if (rsi_direction == EntryAction.BUY and bb_direction == "BUY") or (
                    rsi_direction == EntryAction.SELL and bb_direction == "SELL"
                ):
                    decision["confidence"] = min(decision["confidence"] + 0.10, 0.80)
                    decision["analysis"] += f" | BB帯端一致+0.10"
                else:
                    decision["confidence"] = min(decision["confidence"] + 0.05, 0.75)
                    decision["analysis"] += f" | BB帯端+0.05"

            signal = self._create_signal(decision, current_price, df, multi_timeframe_data)

            self.logger.info(
                f"[ATRレンジ] シグナル生成: {signal.action} "
                f"(信頼度: {signal.confidence:.3f}, 消尽率: {exhaustion_analysis['ratio']:.1%})"
            )
            return signal

        except Exception as e:
            self.logger.error(f"[ATRレンジ] 分析エラー: {e}")
            raise StrategyError(f"ATRレンジ分析失敗: {e}", strategy_name=self.name)

    def _analyze_bb_main_mode(
        self,
        df: pd.DataFrame,
        current_price: float,
        exhaustion_analysis: Dict[str, Any],
        range_check: Dict[str, Any],
        multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> StrategySignal:
        """
        Phase 56.10: BB位置メイン条件モード

        BB位置で反転方向を決定し、RSI確認はボーナスとして使用。
        """
        # Step 3: BB位置で方向決定（必須条件）
        bb_check = self._check_bb_position(df)
        if not bb_check["at_band_edge"]:
            return SignalBuilder.create_hold_signal(
                strategy_name=self.name,
                current_price=current_price,
                reason=bb_check["reason"],
                strategy_type=StrategyType.ATR_BASED,
            )

        # BB方向からEntryActionに変換
        if bb_check["direction"] == "BUY":
            action = EntryAction.BUY
        elif bb_check["direction"] == "SELL":
            action = EntryAction.SELL
        else:
            return SignalBuilder.create_hold_signal(
                strategy_name=self.name,
                current_price=current_price,
                reason="BB方向不明",
                strategy_type=StrategyType.ATR_BASED,
            )

        # Step 4: 信頼度計算
        if exhaustion_analysis["is_high_exhaustion"]:
            base_conf = self.config["high_confidence"]
        else:
            base_conf = self.config["base_confidence"]

        confidence = base_conf

        # Step 5: RSI確認（ボーナス）
        rsi_bonus = self._check_rsi_confirmation(df, bb_check["direction"])
        if rsi_bonus["confirms"]:
            confidence += self.config.get("rsi_confirmation_bonus", 0.05)

        # 最小・最大制限
        confidence = max(self.config["min_confidence"], min(confidence, 0.75))

        # 分析テキスト生成
        action_str = action.value if hasattr(action, "value") else str(action)
        analysis = (
            f"ATRレンジ消尽（BB主導）: {action_str} "
            f"(消尽率={exhaustion_analysis['ratio']:.1%}, "
            f"BB位置={bb_check['position']:.1%}, ADX={range_check['adx']:.1f}"
        )
        if rsi_bonus["confirms"]:
            analysis += f", RSI確認+{self.config.get('rsi_confirmation_bonus', 0.05):.2f}"
        analysis += ")"

        decision = {
            "action": action,
            "confidence": confidence,
            "strength": (
                1.0 - bb_check["position"] if action == EntryAction.BUY else bb_check["position"]
            ),
            "analysis": analysis,
        }

        signal = self._create_signal(decision, current_price, df, multi_timeframe_data)

        self.logger.info(
            f"[ATRレンジ] シグナル生成（BB主導）: {signal.action} "
            f"(信頼度: {signal.confidence:.3f}, 消尽率: {exhaustion_analysis['ratio']:.1%}, "
            f"BB位置: {bb_check['position']:.1%})"
        )
        return signal

    def _check_rsi_confirmation(self, df: pd.DataFrame, expected_direction: str) -> Dict[str, Any]:
        """
        Phase 56.10: RSI確認（ボーナス用）

        BB方向とRSI方向が一致するか確認。
        """
        try:
            current_rsi = float(df["rsi_14"].iloc[-1])
            rsi_upper = self.config["rsi_upper"]
            rsi_lower = self.config["rsi_lower"]

            if expected_direction == "BUY" and current_rsi < rsi_lower:
                return {
                    "confirms": True,
                    "rsi": current_rsi,
                    "reason": f"RSI={current_rsi:.1f} < {rsi_lower}",
                }
            elif expected_direction == "SELL" and current_rsi > rsi_upper:
                return {
                    "confirms": True,
                    "rsi": current_rsi,
                    "reason": f"RSI={current_rsi:.1f} > {rsi_upper}",
                }
            else:
                return {
                    "confirms": False,
                    "rsi": current_rsi,
                    "reason": f"RSI={current_rsi:.1f}（中間）",
                }

        except Exception as e:
            self.logger.error(f"RSI確認エラー: {e}")
            return {"confirms": False, "rsi": 50.0, "reason": "確認エラー"}

    def _calculate_exhaustion_ratio(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        ATR消尽率を計算

        消尽率 = 当日の値幅 / ATR14
        """
        try:
            # 当日の値幅（High - Low）
            current_high = float(df["high"].iloc[-1])
            current_low = float(df["low"].iloc[-1])
            daily_range = current_high - current_low

            # ATR14
            atr_14 = float(df["atr_14"].iloc[-1])

            # 消尽率計算
            if atr_14 > 0:
                exhaustion_ratio = daily_range / atr_14
            else:
                exhaustion_ratio = 0.0

            # 閾値判定
            is_exhausted = exhaustion_ratio >= self.config["exhaustion_threshold"]
            is_high_exhaustion = exhaustion_ratio >= self.config["high_exhaustion_threshold"]

            # 理由生成
            if is_high_exhaustion:
                reason = f"高消尽（{exhaustion_ratio:.1%} >= {self.config['high_exhaustion_threshold']:.0%}）"
            elif is_exhausted:
                reason = (
                    f"消尽（{exhaustion_ratio:.1%} >= {self.config['exhaustion_threshold']:.0%}）"
                )
            else:
                reason = (
                    f"未消尽（{exhaustion_ratio:.1%} < {self.config['exhaustion_threshold']:.0%}）"
                )

            return {
                "ratio": exhaustion_ratio,
                "daily_range": daily_range,
                "atr_14": atr_14,
                "is_exhausted": is_exhausted,
                "is_high_exhaustion": is_high_exhaustion,
                "reason": reason,
            }

        except Exception as e:
            self.logger.error(f"消尽率計算エラー: {e}")
            return {
                "ratio": 0.0,
                "is_exhausted": False,
                "is_high_exhaustion": False,
                "reason": "計算エラー",
            }

    def _check_range_market(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        レンジ相場かどうかを確認（ADXフィルタ）

        ADX < 閾値 → レンジ相場と判定
        """
        try:
            if "adx_14" not in df.columns:
                return {"is_range": True, "adx": 0.0, "reason": "ADXデータなし（レンジと仮定）"}

            current_adx = float(df["adx_14"].iloc[-1])
            adx_threshold = self.config["adx_range_threshold"]

            if current_adx < adx_threshold:
                return {
                    "is_range": True,
                    "adx": current_adx,
                    "reason": f"レンジ相場（ADX={current_adx:.1f} < {adx_threshold}）",
                }
            else:
                return {
                    "is_range": False,
                    "adx": current_adx,
                    "reason": f"トレンド相場（ADX={current_adx:.1f} >= {adx_threshold}）→ 逆張り回避",
                }

        except Exception as e:
            self.logger.error(f"レンジ判定エラー: {e}")
            return {"is_range": True, "adx": 0.0, "reason": "判定エラー（レンジと仮定）"}

    def _check_bb_position(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        ボリンジャーバンド位置確認（Phase 55.4 Approach B）

        15分足レンジ相場向けの追加フィルタ。
        価格がBB帯端にいる場合、反転の信頼性が高い。

        Returns:
            at_band_edge: True if price is near band edge
            direction: Expected reversal direction ("BUY", "SELL", or "HOLD")
            position: Price position within BB (0=lower, 1=upper)
        """
        try:
            # BB関連データを取得
            if "bb_upper" not in df.columns or "bb_lower" not in df.columns:
                return {
                    "at_band_edge": False,
                    "direction": "HOLD",
                    "position": 0.5,
                    "reason": "BBデータなし",
                }

            close = float(df["close"].iloc[-1])
            bb_upper = float(df["bb_upper"].iloc[-1])
            bb_lower = float(df["bb_lower"].iloc[-1])
            bb_width = bb_upper - bb_lower

            if bb_width <= 0:
                return {
                    "at_band_edge": False,
                    "direction": "HOLD",
                    "position": 0.5,
                    "reason": "BB幅ゼロ",
                }

            # 価格のBB内位置（0=下端、1=上端）
            bb_position = (close - bb_lower) / bb_width
            threshold = self.config.get("bb_position_threshold", 0.20)

            # 帯端判定
            at_lower = bb_position < threshold  # 下端付近 → BUY期待
            at_upper = bb_position > (1 - threshold)  # 上端付近 → SELL期待

            if at_lower:
                return {
                    "at_band_edge": True,
                    "direction": "BUY",
                    "position": bb_position,
                    "reason": f"BB下端({bb_position:.1%} < {threshold:.0%}) → 上昇反転期待",
                }
            elif at_upper:
                return {
                    "at_band_edge": True,
                    "direction": "SELL",
                    "position": bb_position,
                    "reason": f"BB上端({bb_position:.1%} > {1 - threshold:.0%}) → 下落反転期待",
                }
            else:
                return {
                    "at_band_edge": False,
                    "direction": "HOLD",
                    "position": bb_position,
                    "reason": f"BB中間({bb_position:.1%}) → 帯端フィルタ未達",
                }

        except Exception as e:
            self.logger.error(f"BB位置確認エラー: {e}")
            return {
                "at_band_edge": False,
                "direction": "HOLD",
                "position": 0.5,
                "reason": "判定エラー",
            }

    def _determine_reversal_direction(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        反転方向を決定（RSI使用）

        RSI > 上限 → 上に動いた後 → SELL（下への反転期待）
        RSI < 下限 → 下に動いた後 → BUY（上への反転期待）
        中間 → HOLD（方向不明）
        """
        try:
            current_rsi = float(df["rsi_14"].iloc[-1])
            rsi_upper = self.config["rsi_upper"]
            rsi_lower = self.config["rsi_lower"]

            if current_rsi > rsi_upper:
                return {
                    "action": EntryAction.SELL,
                    "rsi": current_rsi,
                    "strength": min((current_rsi - rsi_upper) / 20.0, 1.0),
                    "reason": f"RSI={current_rsi:.1f} > {rsi_upper} → 下への反転期待",
                }
            elif current_rsi < rsi_lower:
                return {
                    "action": EntryAction.BUY,
                    "rsi": current_rsi,
                    "strength": min((rsi_lower - current_rsi) / 20.0, 1.0),
                    "reason": f"RSI={current_rsi:.1f} < {rsi_lower} → 上への反転期待",
                }
            else:
                return {
                    "action": EntryAction.HOLD,
                    "rsi": current_rsi,
                    "strength": 0.0,
                    "reason": f"RSI={current_rsi:.1f}（{rsi_lower}〜{rsi_upper}の中間）→ 方向不明",
                }

        except Exception as e:
            self.logger.error(f"反転方向判定エラー: {e}")
            return {
                "action": EntryAction.HOLD,
                "rsi": 50.0,
                "strength": 0.0,
                "reason": "判定エラー",
            }

    def _create_decision(
        self,
        exhaustion: Dict[str, Any],
        direction: Dict[str, Any],
        range_check: Dict[str, Any],
    ) -> Dict[str, Any]:
        """統合判定を作成（後方互換性のため維持）"""
        # 信頼度計算
        if exhaustion["is_high_exhaustion"]:
            base_conf = self.config["high_confidence"]
        else:
            base_conf = self.config["base_confidence"]

        # RSI強度で調整
        confidence = base_conf + direction["strength"] * 0.15

        # 最小信頼度チェック
        if confidence < self.config["min_confidence"]:
            confidence = self.config["min_confidence"]

        # 最大0.75に制限
        confidence = min(confidence, 0.75)

        # action値を取得（Enumまたは文字列に対応）
        action = direction["action"]
        action_str = action.value if hasattr(action, "value") else str(action)

        analysis = (
            f"ATRレンジ消尽: {action_str} "
            f"(消尽率={exhaustion['ratio']:.1%}, RSI={direction['rsi']:.1f}, "
            f"ADX={range_check['adx']:.1f}, 信頼度={confidence:.3f})"
        )

        return {
            "action": direction["action"],
            "confidence": confidence,
            "strength": direction["strength"],
            "analysis": analysis,
        }

    def _create_signal(
        self,
        decision: Dict[str, Any],
        current_price: float,
        df: pd.DataFrame,
        multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> StrategySignal:
        """シグナル作成"""
        return SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.name,
            decision=decision,
            current_price=current_price,
            df=df,
            config=self.config,
            strategy_type=StrategyType.ATR_BASED,
            multi_timeframe_data=multi_timeframe_data,
        )

    def get_required_features(self) -> List[str]:
        """必要特徴量リスト取得"""
        return [
            "close",
            "high",
            "low",
            "atr_14",
            "adx_14",
            "rsi_14",
            "bb_upper",  # Phase 55.4 Approach B: BB位置確認用
            "bb_lower",  # Phase 55.4 Approach B: BB位置確認用
        ]

    def get_signal_proximity(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        シグナルまでの距離を計算（HOLD診断機能）

        ATR消尽率・BB位置・ADXの現在値と閾値の差を計算し、
        「あとどれくらいでシグナルが出るか」を診断する。

        Returns:
            Dict[str, Any]: 診断情報
                - exhaustion_rate: 現在のATR消尽率
                - exhaustion_threshold: 消尽率閾値
                - exhaustion_gap: 閾値までの差（正=未達、負=到達）
                - bb_position: 現在のBB位置（0=下端、1=上端）
                - bb_threshold: BB位置閾値
                - bb_gap_to_buy: BUYシグナルまでの距離
                - bb_gap_to_sell: SELLシグナルまでの距離
                - adx: 現在のADX値
                - adx_threshold: ADX閾値
                - adx_ok: ADXがレンジ相場を示しているか
                - nearest_action: 最も近いシグナル方向
                - diagnosis: 診断テキスト
        """
        try:
            # ATR消尽率計算
            exhaustion_analysis = self._calculate_exhaustion_ratio(df)
            exhaustion_rate = exhaustion_analysis.get("ratio", 0.0)
            exhaustion_threshold = self.config["exhaustion_threshold"]
            exhaustion_gap = exhaustion_threshold - exhaustion_rate

            # BB位置計算
            bb_check = self._check_bb_position(df)
            bb_position = bb_check.get("position", 0.5)
            bb_threshold = self.config.get("bb_position_threshold", 0.20)
            bb_gap_to_buy = max(0, bb_position - bb_threshold)  # 下端(0)に近いほど0
            bb_gap_to_sell = max(0, (1 - bb_threshold) - bb_position)  # 上端(1)に近いほど0

            # ADX確認
            range_check = self._check_range_market(df)
            adx = range_check.get("adx", 0.0)
            adx_threshold = self.config["adx_range_threshold"]
            adx_ok = adx < adx_threshold

            # 最も近いシグナル方向を判定
            if bb_gap_to_buy <= bb_gap_to_sell:
                nearest_action = "buy"
                nearest_bb_gap = bb_gap_to_buy
            else:
                nearest_action = "sell"
                nearest_bb_gap = bb_gap_to_sell

            # 診断テキスト生成
            diagnosis_parts = []

            # 消尽率診断
            if exhaustion_gap > 0:
                diagnosis_parts.append(
                    f"消尽率={exhaustion_rate:.0%}(閾値{exhaustion_threshold:.0%}まで{exhaustion_gap:.0%})"
                )
            else:
                diagnosis_parts.append(f"消尽率={exhaustion_rate:.0%}✓")

            # BB位置診断
            if bb_check.get("at_band_edge"):
                diagnosis_parts.append(f"BB={bb_position:.0%}({bb_check.get('direction', '?')})✓")
            else:
                diagnosis_parts.append(
                    f"BB={bb_position:.0%}({nearest_action.upper()}端まで{nearest_bb_gap:.0%})"
                )

            # ADX診断
            if adx_ok:
                diagnosis_parts.append(f"ADX={adx:.1f}✓")
            else:
                diagnosis_parts.append(f"ADX={adx:.1f}(閾値{adx_threshold}超過)")

            return {
                "exhaustion_rate": exhaustion_rate,
                "exhaustion_threshold": exhaustion_threshold,
                "exhaustion_gap": exhaustion_gap,
                "bb_position": bb_position,
                "bb_threshold": bb_threshold,
                "bb_gap_to_buy": bb_gap_to_buy,
                "bb_gap_to_sell": bb_gap_to_sell,
                "adx": adx,
                "adx_threshold": adx_threshold,
                "adx_ok": adx_ok,
                "nearest_action": nearest_action,
                "diagnosis": " | ".join(diagnosis_parts),
            }

        except Exception as e:
            self.logger.error(f"[ATRBased] 診断エラー: {e}")
            return {
                "exhaustion_rate": 0.0,
                "exhaustion_gap": 1.0,
                "bb_position": 0.5,
                "bb_gap_to_buy": 0.5,
                "bb_gap_to_sell": 0.5,
                "adx": 0.0,
                "adx_ok": True,
                "nearest_action": "unknown",
                "diagnosis": f"診断エラー: {e}",
            }

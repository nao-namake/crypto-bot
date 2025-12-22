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

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from ...core.exceptions import StrategyError
from ...core.logger import get_logger
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
            # ATR消尽率パラメータ
            "exhaustion_threshold": get_threshold(
                "strategies.atr_based.exhaustion_threshold", 0.70
            ),
            "high_exhaustion_threshold": get_threshold(
                "strategies.atr_based.high_exhaustion_threshold", 0.85
            ),
            # レンジ相場フィルタ
            "adx_range_threshold": get_threshold("strategies.atr_based.adx_range_threshold", 25),
            # RSI反転判定
            "rsi_upper": get_threshold("strategies.atr_based.rsi_upper", 60),
            "rsi_lower": get_threshold("strategies.atr_based.rsi_lower", 40),
            # 信頼度設定
            "min_confidence": get_threshold("strategies.atr_based.min_confidence", 0.35),
            "hold_confidence": get_threshold("strategies.atr_based.hold_confidence", 0.20),
            "base_confidence": get_threshold("strategies.atr_based.base_confidence", 0.40),
            "high_confidence": get_threshold("strategies.atr_based.high_confidence", 0.60),
            # スコア閾値（Phase 55.4 Approach B: BB確認込みで0.65）
            "min_score_threshold": get_threshold("strategies.atr_based.min_score_threshold", 0.65),
            # BB位置確認（Phase 55.4 Approach B: 新規追加）
            "bb_position_enabled": get_threshold("strategies.atr_based.bb_position_enabled", True),
            "bb_position_threshold": get_threshold(
                "strategies.atr_based.bb_position_threshold", 0.20
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
            f"ADX閾値={self.config['adx_range_threshold']}"
        )

    def analyze(
        self, df: pd.DataFrame, multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> StrategySignal:
        """
        市場分析とシグナル生成

        ATRレンジ消尽に基づく反転シグナルを生成。

        Phase 55.4: 直列評価方式に戻す（高PF設定ベース）
        - 消尽率 → レンジ相場 → RSI方向 の順にチェック
        - すべて満たした場合のみシグナル生成
        - BB位置確認は信頼度ボーナスとして使用
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

            # Step 3: 反転方向決定（必須条件）
            direction_analysis = self._determine_reversal_direction(df)
            if direction_analysis["action"] == EntryAction.HOLD:
                return SignalBuilder.create_hold_signal(
                    strategy_name=self.name,
                    current_price=current_price,
                    reason=direction_analysis["reason"],
                    strategy_type=StrategyType.ATR_BASED,
                )

            # Step 4: BB位置確認（オプション：信頼度ボーナス）
            bb_check = self._check_bb_position(df)

            # Step 5: 統合判定とシグナル生成
            decision = self._create_decision(exhaustion_analysis, direction_analysis, range_check)

            # BB帯端にいる場合は信頼度を上げる
            if self.config.get("bb_position_enabled", True) and bb_check["at_band_edge"]:
                # RSI方向とBB方向が一致していれば更にボーナス
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

    def _infer_direction_from_price(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        価格変動から方向を推定（RSIが中間の場合のフォールバック）

        Phase 55.3: RSIが中間でもシグナル生成可能に
        - 直近の価格変動から方向を推定
        - 上昇後なら下落反転、下落後なら上昇反転を期待
        """
        try:
            # 直近5本の価格変動を確認
            closes = df["close"].iloc[-5:].values
            price_change = (closes[-1] - closes[0]) / closes[0]

            # 閾値（0.3%以上の変動で方向判定）
            change_threshold = 0.003

            if price_change > change_threshold:
                # 上昇後 → 下落反転期待
                return {
                    "action": EntryAction.SELL,
                    "rsi": 50.0,
                    "strength": min(abs(price_change) * 100, 0.5),
                    "reason": f"価格上昇後({price_change:.2%})→下落反転期待",
                }
            elif price_change < -change_threshold:
                # 下落後 → 上昇反転期待
                return {
                    "action": EntryAction.BUY,
                    "rsi": 50.0,
                    "strength": min(abs(price_change) * 100, 0.5),
                    "reason": f"価格下落後({price_change:.2%})→上昇反転期待",
                }
            else:
                return {
                    "action": EntryAction.HOLD,
                    "rsi": 50.0,
                    "strength": 0.0,
                    "reason": "価格変動不足で方向不明",
                }
        except Exception as e:
            self.logger.error(f"方向推定エラー: {e}")
            return {
                "action": EntryAction.HOLD,
                "rsi": 50.0,
                "strength": 0.0,
                "reason": "推定エラー",
            }

    def _create_decision_with_score(
        self,
        exhaustion: Dict[str, Any],
        direction: Dict[str, Any],
        range_check: Dict[str, Any],
        score: float,
    ) -> Dict[str, Any]:
        """
        スコアベースの統合判定を作成（Phase 55.3）

        スコアを信頼度に反映し、より柔軟なシグナル生成を実現
        """
        # スコアから信頼度を計算（スコア0.5→信頼度0.35、スコア1.0→信頼度0.65）
        confidence = 0.35 + (score - 0.5) * 0.6

        # 高消尽時はボーナス
        if exhaustion.get("is_high_exhaustion"):
            confidence += 0.05

        # RSI強度で追加調整
        confidence += direction.get("strength", 0) * 0.10

        # 最小・最大制限
        confidence = max(self.config["min_confidence"], min(confidence, 0.75))

        # action値を取得
        action = direction["action"]
        action_str = action.value if hasattr(action, "value") else str(action)

        analysis = (
            f"ATRレンジ消尽: {action_str} "
            f"(スコア={score:.2f}, 消尽率={exhaustion['ratio']:.1%}, "
            f"RSI={direction.get('rsi', 50):.1f}, ADX={range_check.get('adx', 0):.1f}, "
            f"信頼度={confidence:.3f})"
        )

        return {
            "action": direction["action"],
            "confidence": confidence,
            "strength": direction.get("strength", 0),
            "analysis": analysis,
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

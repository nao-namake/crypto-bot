"""
Stochastic Divergence戦略 - Phase 62.2 品質フィルタ強化

レンジ・トレンド両相場で機能するモメンタム乖離戦略。
価格とStochasticの乖離（ダイバージェンス）から反転を捉える。

核心思想:
「価格は高値更新しているがStochasticは低下している = モメンタム弱化 = 反転間近」

Phase 62.2変更:
- 最小価格変化チェック追加（0.5%以上）
- 弱いダイバージェンス（0.3%未満）をフィルタリング
- 期待: 44件→50-55件（品質向上）

差別化:
- BBReversal: 価格の現在位置（静的）
- ATRBased: 今日の変動量（1期間）
- StochasticDivergence: 価格とモメンタムの乖離（複数期間）
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from ...core.config.threshold_manager import get_threshold
from ..base.strategy_base import StrategyBase, StrategySignal
from ..strategy_registry import StrategyRegistry
from ..utils import EntryAction, SignalBuilder, StrategyType


@StrategyRegistry.register(
    name="StochasticReversal", strategy_type=StrategyType.STOCHASTIC_REVERSAL
)
class StochasticReversalStrategy(StrategyBase):
    """
    Stochastic Divergence戦略 - モメンタム乖離検出

    シグナル生成ロジック:
    1. ダイバージェンス検出（核心機能）
       - Bearish: 価格上昇 + Stochastic低下 → SELL
       - Bullish: 価格下落 + Stochastic上昇 → BUY
    2. 極端領域確認（信頼度ボーナス）
       - 過買い領域（stoch > 70）でBearish → +10%
       - 過売り領域（stoch < 30）でBullish → +10%
    3. ADXフィルタ（強トレンド除外のみ）
       - ADX < 50 で機能（大幅緩和）
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初期化

        Args:
            config: 戦略設定（thresholds.yamlから読み込み）
        """
        default_config = {
            # Divergence設定（核心機能）
            "divergence_lookback": get_threshold(
                "strategies.stochastic_reversal.divergence_lookback", 5
            ),
            "divergence_price_threshold": get_threshold(
                "strategies.stochastic_reversal.divergence_price_threshold", 0.002
            ),
            "divergence_stoch_threshold": get_threshold(
                "strategies.stochastic_reversal.divergence_stoch_threshold", 5
            ),
            # Phase 62.2: 最小価格変化チェック
            "min_price_change_ratio": get_threshold(
                "strategies.stochastic_reversal.min_price_change_ratio", 0.005
            ),
            "enable_min_price_filter": get_threshold(
                "strategies.stochastic_reversal.enable_min_price_filter", True
            ),
            # 極端領域設定
            "stoch_overbought": get_threshold(
                "strategies.stochastic_reversal.stoch_overbought", 70
            ),
            "stoch_oversold": get_threshold("strategies.stochastic_reversal.stoch_oversold", 30),
            # ADX設定
            "adx_max_threshold": get_threshold(
                "strategies.stochastic_reversal.adx_max_threshold", 50
            ),
            # 信頼度設定
            "min_confidence": get_threshold("strategies.stochastic_reversal.min_confidence", 0.30),
            "hold_confidence": get_threshold(
                "strategies.stochastic_reversal.hold_confidence", 0.22
            ),
            "base_confidence": get_threshold(
                "strategies.stochastic_reversal.base_confidence", 0.35
            ),
            "max_confidence": get_threshold("strategies.stochastic_reversal.max_confidence", 0.60),
            "zone_bonus": get_threshold("strategies.stochastic_reversal.zone_bonus", 0.10),
            # SL設定
            "sl_multiplier": get_threshold("strategies.stochastic_reversal.sl_multiplier", 1.5),
        }
        merged_config = {**default_config, **(config or {})}
        super().__init__(name="StochasticReversal", config=merged_config)

    def analyze(
        self,
        df: pd.DataFrame,
        multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> StrategySignal:
        """
        戦略分析実行

        Args:
            df: 市場データ（4時間足）
            multi_timeframe_data: マルチタイムフレームデータ（15m足含む）

        Returns:
            StrategySignal: 戦略シグナル
        """
        # 1. データ検証
        required_features = self.get_required_features()
        if df is None or df.empty or not all(f in df.columns for f in required_features):
            return self._create_hold_signal("insufficient_data", df)

        # 2. 最新データ取得
        latest = df.iloc[-1]
        current_price = float(latest["close"])

        # 3. ADXフィルタ（強トレンド除外）
        if not self._check_market_condition(df):
            return self._create_hold_signal("strong_trend_excluded", df)

        # 4. Stochastic Divergence分析
        decision = self._analyze_stochastic_divergence_signal(df)

        # 5. SignalBuilder使用
        return SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.name,
            decision=decision,
            current_price=current_price,
            df=df,
            config=self.config,
            strategy_type=StrategyType.STOCHASTIC_REVERSAL,
            multi_timeframe_data=multi_timeframe_data,
        )

    def get_required_features(self) -> List[str]:
        """
        必要な特徴量リスト

        Returns:
            List[str]: 必要な特徴量名のリスト
        """
        return [
            "close",
            "stoch_k",  # Stochastic %K（14期間）
            "stoch_d",  # Stochastic %D（3期間SMA）
            "adx_14",  # ADX（強トレンド除外用）
            "atr_14",  # ATR（リスク管理用）
        ]

    def _check_market_condition(self, df: pd.DataFrame) -> bool:
        """
        市場条件確認（強トレンド除外）

        ダイバージェンス戦略はトレンド・レンジ両方で機能するため、
        極端に強いトレンド（ADX > 50）のみ除外。

        Args:
            df: 市場データ

        Returns:
            bool: 取引可能な場合True
        """
        try:
            latest = df.iloc[-1]
            adx = float(latest["adx_14"])
            return adx < self.config["adx_max_threshold"]
        except (KeyError, TypeError, ValueError):
            return True  # ADX取得失敗時はデフォルトでTrue

    def _detect_divergence(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        ダイバージェンス検出（核心機能）

        Phase 55.3: 同時性要件緩和
        - 従来: 5期間前と現在を直接比較（同時性要求・厳しすぎ）
        - 改善: 期間内の最大/最小を使用（時間軸分離・柔軟に）

        Bearish Divergence（SELL信号）:
          - 価格: 期間内で上昇トレンド（現在が高値付近）
          - Stochastic: 期間内で下降トレンド（現在が安値付近）
          - 意味: 価格は上がっているがモメンタム弱化 → 反転下落期待

        Bullish Divergence（BUY信号）:
          - 価格: 期間内で下降トレンド（現在が安値付近）
          - Stochastic: 期間内で上昇トレンド（現在が高値付近）
          - 意味: 価格は下がっているがモメンタム回復 → 反転上昇期待

        Args:
            df: 市場データ

        Returns:
            Dict[str, Any]: ダイバージェンス検出結果
        """
        try:
            lookback = self.config["divergence_lookback"]
            price_threshold = self.config["divergence_price_threshold"]
            stoch_threshold = self.config["divergence_stoch_threshold"]

            if len(df) < lookback + 1:
                return {"type": "none", "action": EntryAction.HOLD, "strength": 0.0}

            # Phase 55.3: 期間内のデータを取得（同時性緩和）
            period_closes = df["close"].iloc[-lookback - 1 :].values
            period_stochs = df["stoch_k"].iloc[-lookback - 1 :].values

            current_close = float(period_closes[-1])
            current_stoch = float(period_stochs[-1])

            # 期間内の最大・最小値
            min_close = float(min(period_closes))
            max_close = float(max(period_closes))
            min_stoch = float(min(period_stochs))
            max_stoch = float(max(period_stochs))

            # 価格の位置（0=最安値、1=最高値）
            price_range = max_close - min_close
            if price_range > 0:
                price_position = (current_close - min_close) / price_range
            else:
                price_position = 0.5

            # Stochasticの位置（0=最安値、1=最高値）
            stoch_range = max_stoch - min_stoch
            if stoch_range > 0:
                stoch_position = (current_stoch - min_stoch) / stoch_range
            else:
                stoch_position = 0.5

            # 価格変化率（期間全体）
            period_start_close = float(period_closes[0])
            price_change_ratio = (current_close - period_start_close) / period_start_close

            # Stochastic変化量（期間全体）
            period_start_stoch = float(period_stochs[0])
            stoch_change = current_stoch - period_start_stoch

            # Phase 62.2: 最小価格変化チェック
            min_price_change = self.config.get("min_price_change_ratio", 0.005)
            enable_min_filter = self.config.get("enable_min_price_filter", True)

            # 価格変動の絶対値チェック
            price_range_ratio = price_range / min_close if min_close > 0 else 0
            has_sufficient_price_move = price_range_ratio >= min_price_change

            # Bearish Divergence検出（Phase 55.3: 緩和条件 + Phase 62.2: 価格変化フィルタ）
            # 条件1: 価格が高値付近（位置 > 0.6）AND Stochasticが安値付近（位置 < 0.4）
            # 条件2: または従来条件（価格上昇 + Stochastic下降）
            bearish_new = price_position > 0.6 and stoch_position < 0.4
            bearish_old = price_change_ratio > price_threshold and stoch_change < -stoch_threshold

            if bearish_new or bearish_old:
                # Phase 62.2: 弱いダイバージェンスをフィルタリング
                if enable_min_filter and not has_sufficient_price_move:
                    return {
                        "type": "weak_bearish",
                        "action": EntryAction.HOLD,
                        "strength": 0.0,
                        "price_change": price_change_ratio * 100,
                        "stoch_change": stoch_change,
                        "reason": f"弱Bearish除外 (価格変動{price_range_ratio:.2%}<{min_price_change:.2%})",
                    }

                strength = 0.3 + abs(price_position - stoch_position) * 0.4
                # 価格変動が大きいほど信頼度ボーナス
                if price_range_ratio > min_price_change * 2:
                    strength += 0.1
                return {
                    "type": "bearish",
                    "action": EntryAction.SELL,
                    "strength": min(strength, 1.0),
                    "price_change": price_change_ratio * 100,
                    "stoch_change": stoch_change,
                    "price_position": price_position,
                    "stoch_position": stoch_position,
                    "reason": f"Bearish Div (価格位置:{price_position:.1%} vs Stoch位置:{stoch_position:.1%})",
                }

            # Bullish Divergence検出（Phase 55.3: 緩和条件 + Phase 62.2: 価格変化フィルタ）
            # 条件1: 価格が安値付近（位置 < 0.4）AND Stochasticが高値付近（位置 > 0.6）
            # 条件2: または従来条件（価格下落 + Stochastic上昇）
            bullish_new = price_position < 0.4 and stoch_position > 0.6
            bullish_old = price_change_ratio < -price_threshold and stoch_change > stoch_threshold

            if bullish_new or bullish_old:
                # Phase 62.2: 弱いダイバージェンスをフィルタリング
                if enable_min_filter and not has_sufficient_price_move:
                    return {
                        "type": "weak_bullish",
                        "action": EntryAction.HOLD,
                        "strength": 0.0,
                        "price_change": price_change_ratio * 100,
                        "stoch_change": stoch_change,
                        "reason": f"弱Bullish除外 (価格変動{price_range_ratio:.2%}<{min_price_change:.2%})",
                    }

                strength = 0.3 + abs(stoch_position - price_position) * 0.4
                # 価格変動が大きいほど信頼度ボーナス
                if price_range_ratio > min_price_change * 2:
                    strength += 0.1
                return {
                    "type": "bullish",
                    "action": EntryAction.BUY,
                    "strength": min(strength, 1.0),
                    "price_change": price_change_ratio * 100,
                    "stoch_change": stoch_change,
                    "price_position": price_position,
                    "stoch_position": stoch_position,
                    "reason": f"Bullish Div (価格位置:{price_position:.1%} vs Stoch位置:{stoch_position:.1%})",
                }

            return {
                "type": "none",
                "action": EntryAction.HOLD,
                "strength": 0.0,
                "reason": f"ダイバージェンス未検出 (価格:{price_position:.1%}, Stoch:{stoch_position:.1%})",
            }

        except (KeyError, TypeError, ValueError, IndexError) as e:
            return {
                "type": "error",
                "action": EntryAction.HOLD,
                "strength": 0.0,
                "reason": f"検出エラー: {str(e)}",
            }

    def _check_extreme_zone(self, stoch_k: float, stoch_d: float) -> Dict[str, Any]:
        """
        極端領域確認（信頼度ボーナス用）

        過買い領域（stoch > 70）でBearish Divergence → 信頼度ボーナス
        過売り領域（stoch < 30）でBullish Divergence → 信頼度ボーナス

        Args:
            stoch_k: Stochastic %K値
            stoch_d: Stochastic %D値

        Returns:
            Dict[str, Any]: 領域判定結果
        """
        overbought = self.config["stoch_overbought"]
        oversold = self.config["stoch_oversold"]
        bonus = self.config["zone_bonus"]

        if stoch_k > overbought:
            return {"zone": "overbought", "bonus": bonus, "stoch_k": stoch_k}
        elif stoch_k < oversold:
            return {"zone": "oversold", "bonus": bonus, "stoch_k": stoch_k}
        else:
            return {"zone": "neutral", "bonus": 0.0, "stoch_k": stoch_k}

    def _analyze_stochastic_divergence_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Stochastic Divergence戦略分析

        シグナル生成ロジック:
        1. ダイバージェンス検出（核心）
        2. 極端領域確認（信頼度補正）
        3. 信頼度計算

        Args:
            df: 市場データ

        Returns:
            Dict[str, Any]: シグナル判断結果
        """
        latest = df.iloc[-1]
        stoch_k = float(latest["stoch_k"])
        stoch_d = float(latest["stoch_d"])

        # Step 1: ダイバージェンス検出
        divergence = self._detect_divergence(df)

        if divergence["type"] == "none" or divergence["type"] == "error":
            return {
                "action": EntryAction.HOLD,
                "confidence": self.config["hold_confidence"],
                "strength": 0.0,
                "reason": divergence.get("reason", "ダイバージェンス未検出"),
            }

        # Step 2: 極端領域確認（信頼度ボーナス）
        zone_check = self._check_extreme_zone(stoch_k, stoch_d)

        # Bearish Divergence + 過買い領域 = 強いSELL信号
        # Bullish Divergence + 過売り領域 = 強いBUY信号
        zone_match = (divergence["type"] == "bearish" and zone_check["zone"] == "overbought") or (
            divergence["type"] == "bullish" and zone_check["zone"] == "oversold"
        )

        # Step 3: 信頼度計算
        base_confidence = self.config["base_confidence"]
        max_confidence = self.config["max_confidence"]

        confidence = base_confidence + divergence["strength"] * 0.20

        if zone_match:
            confidence += zone_check["bonus"]

        # 最大値制限
        confidence = min(confidence, max_confidence)

        # 理由生成
        reason = divergence["reason"]
        if zone_match:
            reason += f" [{zone_check['zone']}]"

        return {
            "action": divergence["action"],
            "confidence": confidence,
            "strength": divergence["strength"],
            "reason": reason,
        }

    def get_signal_proximity(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        シグナルまでの距離を計算（HOLD診断機能）

        ダイバージェンス検出状態・Stochastic値・ADXの現在値を計算し、
        「あとどれくらいでシグナルが出るか」を診断する。

        Returns:
            Dict[str, Any]: 診断情報
                - divergence_detected: ダイバージェンスが検出されたか
                - divergence_type: ダイバージェンスタイプ（bullish/bearish/none）
                - price_position: 価格の相対位置（0=最安値、1=最高値）
                - stoch_position: Stochasticの相対位置
                - stoch_k: 現在のStochastic %K
                - adx: 現在のADX値
                - adx_ok: ADXが閾値以下か
                - price_range_ratio: 価格変動率
                - min_price_change: 最小価格変化閾値
                - nearest_action: 最も近いシグナル方向
                - diagnosis: 診断テキスト
        """
        try:
            if df is None or df.empty:
                return {
                    "divergence_detected": False,
                    "divergence_type": "none",
                    "stoch_k": 50.0,
                    "adx": 0.0,
                    "adx_ok": True,
                    "nearest_action": "unknown",
                    "diagnosis": "データ不足",
                }

            latest = df.iloc[-1]
            stoch_k = float(latest["stoch_k"])
            stoch_d = float(latest["stoch_d"])
            adx = float(latest["adx_14"]) if pd.notna(latest["adx_14"]) else 0

            # ADX確認
            adx_threshold = self.config["adx_max_threshold"]
            adx_ok = adx < adx_threshold

            # ダイバージェンス検出
            divergence = self._detect_divergence(df)
            divergence_detected = divergence["type"] in ("bullish", "bearish")
            divergence_type = divergence["type"]

            # 価格位置とStochastic位置
            price_position = divergence.get("price_position", 0.5)
            stoch_position = divergence.get("stoch_position", 0.5)

            # 価格変動率計算
            lookback = self.config["divergence_lookback"]
            if len(df) >= lookback + 1:
                period_closes = df["close"].iloc[-lookback - 1 :].values
                min_close = float(min(period_closes))
                max_close = float(max(period_closes))
                price_range = max_close - min_close
                price_range_ratio = price_range / min_close if min_close > 0 else 0
            else:
                price_range_ratio = 0

            min_price_change = self.config.get("min_price_change_ratio", 0.005)

            # 極端領域確認
            zone_check = self._check_extreme_zone(stoch_k, stoch_d)

            # 最も近いシグナル方向を推定
            if stoch_k < 30:
                nearest_action = "buy"
            elif stoch_k > 70:
                nearest_action = "sell"
            else:
                # 位置差から推定
                if price_position < stoch_position:
                    nearest_action = "buy"  # Bullish Divergence候補
                else:
                    nearest_action = "sell"  # Bearish Divergence候補

            # 診断テキスト生成
            diagnosis_parts = []

            # ダイバージェンス診断
            if divergence_detected:
                diagnosis_parts.append(f"Div={divergence_type}✓")
            else:
                position_diff = abs(price_position - stoch_position)
                if position_diff < 0.2:
                    diagnosis_parts.append(f"Div=未検出(位置差{position_diff:.0%}<20%)")
                else:
                    diagnosis_parts.append(
                        f"Div=未検出(価格{price_position:.0%}/Stoch{stoch_position:.0%})"
                    )

            # 価格変動診断
            if price_range_ratio >= min_price_change:
                diagnosis_parts.append(f"変動={price_range_ratio:.2%}✓")
            else:
                gap = min_price_change - price_range_ratio
                diagnosis_parts.append(
                    f"変動={price_range_ratio:.2%}(閾値{min_price_change:.2%}まで{gap:.2%})"
                )

            # Stochastic診断
            if zone_check["zone"] == "overbought":
                diagnosis_parts.append(f"Stoch={stoch_k:.1f}(過買い)✓")
            elif zone_check["zone"] == "oversold":
                diagnosis_parts.append(f"Stoch={stoch_k:.1f}(過売り)✓")
            else:
                diagnosis_parts.append(f"Stoch={stoch_k:.1f}(中立)")

            # ADX診断
            if adx_ok:
                diagnosis_parts.append(f"ADX={adx:.1f}✓")
            else:
                diagnosis_parts.append(f"ADX={adx:.1f}(閾値{adx_threshold}超過)")

            return {
                "divergence_detected": divergence_detected,
                "divergence_type": divergence_type,
                "price_position": price_position,
                "stoch_position": stoch_position,
                "stoch_k": stoch_k,
                "adx": adx,
                "adx_threshold": adx_threshold,
                "adx_ok": adx_ok,
                "price_range_ratio": price_range_ratio,
                "min_price_change": min_price_change,
                "nearest_action": nearest_action,
                "diagnosis": " | ".join(diagnosis_parts),
            }

        except Exception as e:
            self.logger.error(f"[StochasticReversal] 診断エラー: {e}")
            return {
                "divergence_detected": False,
                "divergence_type": "none",
                "stoch_k": 50.0,
                "adx": 0.0,
                "adx_ok": True,
                "nearest_action": "unknown",
                "diagnosis": f"診断エラー: {e}",
            }

    def _create_hold_signal(self, reason: str, df: pd.DataFrame) -> StrategySignal:
        """
        HOLDシグナル生成

        Args:
            reason: HOLD理由
            df: 市場データ

        Returns:
            StrategySignal: HOLDシグナル
        """
        latest = df.iloc[-1] if df is not None and not df.empty else None
        current_price = float(latest["close"]) if latest is not None else 0.0

        return StrategySignal(
            action=EntryAction.HOLD,
            confidence=self.config["hold_confidence"],
            strength=0.0,
            current_price=current_price,
            entry_price=current_price,
            take_profit=None,
            stop_loss=None,
            reason=f"StochasticReversal: {reason}",
            strategy_name=self.name,
            timestamp=str(pd.Timestamp.now()),
        )

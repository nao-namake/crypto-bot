"""
Stochastic Divergence戦略 - Phase 55.2

レンジ・トレンド両相場で機能するモメンタム乖離戦略。
価格とStochasticの乖離（ダイバージェンス）から反転を捉える。

核心思想:
「価格は高値更新しているがStochasticは低下している = モメンタム弱化 = 反転間近」

差別化:
- BBReversal: 価格の現在位置（静的）
- ATRBased: 今日の変動量（1期間）
- StochasticDivergence: 価格とモメンタムの乖離（複数期間）

Phase 55.2 完全リファクタリング
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
            # 極端領域設定
            "stoch_overbought": get_threshold(
                "strategies.stochastic_reversal.stoch_overbought", 70
            ),
            "stoch_oversold": get_threshold(
                "strategies.stochastic_reversal.stoch_oversold", 30
            ),
            # ADX設定
            "adx_max_threshold": get_threshold(
                "strategies.stochastic_reversal.adx_max_threshold", 50
            ),
            # 信頼度設定
            "min_confidence": get_threshold(
                "strategies.stochastic_reversal.min_confidence", 0.30
            ),
            "hold_confidence": get_threshold(
                "strategies.stochastic_reversal.hold_confidence", 0.22
            ),
            "base_confidence": get_threshold(
                "strategies.stochastic_reversal.base_confidence", 0.35
            ),
            "max_confidence": get_threshold(
                "strategies.stochastic_reversal.max_confidence", 0.60
            ),
            "zone_bonus": get_threshold(
                "strategies.stochastic_reversal.zone_bonus", 0.10
            ),
            # SL設定
            "sl_multiplier": get_threshold(
                "strategies.stochastic_reversal.sl_multiplier", 1.5
            ),
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
            "adx_14",   # ADX（強トレンド除外用）
            "atr_14",   # ATR（リスク管理用）
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

        Bearish Divergence（SELL信号）:
          - 価格: 高値切り上げ（close[i] > close[i-n]）
          - Stochastic: 高値切り下げ（stoch_k[i] < stoch_k[i-n]）
          - 意味: 価格は上がっているがモメンタム弱化 → 反転下落期待

        Bullish Divergence（BUY信号）:
          - 価格: 安値切り下げ（close[i] < close[i-n]）
          - Stochastic: 安値切り上げ（stoch_k[i] > stoch_k[i-n]）
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

            # 現在と過去のデータ取得
            current_close = float(df["close"].iloc[-1])
            previous_close = float(df["close"].iloc[-lookback])
            current_stoch = float(df["stoch_k"].iloc[-1])
            previous_stoch = float(df["stoch_k"].iloc[-lookback])

            # 価格変化率とStochastic変化量
            price_change_ratio = (current_close - previous_close) / previous_close
            stoch_change = current_stoch - previous_stoch

            # Bearish Divergence検出
            # 価格上昇（+0.2%以上）+ Stochastic低下（-5pt以上）
            if price_change_ratio > price_threshold and stoch_change < -stoch_threshold:
                strength = min(abs(stoch_change) / 50.0, 1.0)
                return {
                    "type": "bearish",
                    "action": EntryAction.SELL,
                    "strength": strength,
                    "price_change": price_change_ratio * 100,
                    "stoch_change": stoch_change,
                    "reason": f"Bearish Divergence (価格+{price_change_ratio*100:.1f}% vs Stoch{stoch_change:.0f})",
                }

            # Bullish Divergence検出
            # 価格下落（-0.2%以上）+ Stochastic上昇（+5pt以上）
            if price_change_ratio < -price_threshold and stoch_change > stoch_threshold:
                strength = min(abs(stoch_change) / 50.0, 1.0)
                return {
                    "type": "bullish",
                    "action": EntryAction.BUY,
                    "strength": strength,
                    "price_change": price_change_ratio * 100,
                    "stoch_change": stoch_change,
                    "reason": f"Bullish Divergence (価格{price_change_ratio*100:.1f}% vs Stoch+{stoch_change:.0f})",
                }

            return {
                "type": "none",
                "action": EntryAction.HOLD,
                "strength": 0.0,
                "reason": "ダイバージェンス未検出",
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
        zone_match = (
            (divergence["type"] == "bearish" and zone_check["zone"] == "overbought")
            or (divergence["type"] == "bullish" and zone_check["zone"] == "oversold")
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

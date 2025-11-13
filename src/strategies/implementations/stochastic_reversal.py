"""
Stochastic Reversal戦略 - Phase 51.7 Day 4

レンジ相場におけるモメンタム逆張り戦略。
Stochastic指標の過買い・過売り領域からの反転を捉える。

戦略ロジック:
- レンジ相場判定: ADX < 20
- SELL信号: Stochastic過買い（K>80, D>80）+ ベアクロス + RSI > 65
- BUY信号: Stochastic過売り（K<20, D<20）+ ゴールデンクロス + RSI < 35
- Dynamic confidence: 0.30-0.50（Stochastic値に基づく）

Phase 51.7 Day 4実装
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from ...core.config.threshold_manager import get_threshold
from ..base.strategy_base import StrategyBase, StrategySignal
from ..strategy_registry import StrategyRegistry
from ..utils import EntryAction, SignalBuilder, StrategyType


@StrategyRegistry.register(name="StochasticReversal", strategy_type=StrategyType.STOCHASTIC_REVERSAL)
class StochasticReversalStrategy(StrategyBase):
    """
    Stochastic Reversal戦略 - レンジ相場でのモメンタム逆張り

    シグナル生成ロジック:
    1. レンジ相場判定（ADX < 20）
    2. SELL信号:
       - stoch_k > 80 AND stoch_d > 80（過買い領域）
       - %Kが%Dを下抜け（ベアクロス）
       - RSI > 65（追加確認）
    3. BUY信号:
       - stoch_k < 20 AND stoch_d < 20（過売り領域）
       - %Kが%Dを上抜け（ゴールデンクロス）
       - RSI < 35（追加確認）
    4. それ以外 → HOLD
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初期化

        Args:
            config: 戦略設定（thresholds.yamlから読み込み）
        """
        default_config = {
            "min_confidence": get_threshold("strategies.stochastic_reversal.min_confidence", 0.30),
            "hold_confidence": get_threshold("strategies.stochastic_reversal.hold_confidence", 0.25),
            "stoch_overbought": get_threshold("strategies.stochastic_reversal.stoch_overbought", 80),
            "stoch_oversold": get_threshold("strategies.stochastic_reversal.stoch_oversold", 20),
            "rsi_overbought": get_threshold("strategies.stochastic_reversal.rsi_overbought", 65),
            "rsi_oversold": get_threshold("strategies.stochastic_reversal.rsi_oversold", 35),
            "adx_range_threshold": get_threshold("strategies.stochastic_reversal.adx_range_threshold", 20),
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

        # 3. レンジ相場判定
        if not self._is_range_market(df):
            return self._create_hold_signal("not_range_market", df)

        # 4. Stochastic反転シグナル分析
        decision = self._analyze_stochastic_reversal_signal(df)

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
            "rsi_14",  # RSI
            "adx_14",  # ADX（レンジ判定用）
            "atr_14",  # ATR（リスク管理用）
        ]

    def _is_range_market(self, df: pd.DataFrame) -> bool:
        """
        レンジ相場判定

        Args:
            df: 市場データ

        Returns:
            bool: レンジ相場の場合True
        """
        latest = df.iloc[-1]
        adx = float(latest["adx_14"])

        # ADX < 20 = レンジ相場
        return adx < self.config["adx_range_threshold"]

    def _detect_stochastic_crossover(self, df: pd.DataFrame) -> str:
        """
        Stochasticクロスオーバー検出

        Args:
            df: 市場データ

        Returns:
            str: "golden" (ゴールデンクロス), "bear" (ベアクロス), "none"
        """
        if len(df) < 2:
            return "none"

        # 最新と1つ前のデータ
        current = df.iloc[-1]
        previous = df.iloc[-2]

        current_k = float(current["stoch_k"])
        current_d = float(current["stoch_d"])
        previous_k = float(previous["stoch_k"])
        previous_d = float(previous["stoch_d"])

        # ゴールデンクロス: %Kが%Dを下から上に抜ける
        if previous_k <= previous_d and current_k > current_d:
            return "golden"

        # ベアクロス: %Kが%Dを上から下に抜ける
        if previous_k >= previous_d and current_k < current_d:
            return "bear"

        return "none"

    def _analyze_stochastic_reversal_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Stochastic反転シグナル分析

        Args:
            df: 市場データ

        Returns:
            Dict[str, Any]: シグナル判断結果
        """
        latest = df.iloc[-1]
        stoch_k = float(latest["stoch_k"])
        stoch_d = float(latest["stoch_d"])
        rsi = float(latest["rsi_14"])

        # クロスオーバー検出
        crossover = self._detect_stochastic_crossover(df)

        # SELL信号（過買い領域 + ベアクロス + RSI買われすぎ）
        if (
            stoch_k > self.config["stoch_overbought"]
            and stoch_d > self.config["stoch_overbought"]
            and crossover == "bear"
            and rsi > self.config["rsi_overbought"]
        ):
            # 信頼度：Stochastic値が極端なほど高い
            confidence = min(self.config["min_confidence"] + (stoch_k - 80) / 100.0, 0.50)
            strength = (stoch_k - 50) / 50.0  # 0.6-1.0の範囲

            return {
                "action": EntryAction.SELL,
                "confidence": confidence,
                "strength": strength,
                "reason": f"Stochastic反転SELL (K={stoch_k:.1f}, D={stoch_d:.1f}, RSI={rsi:.1f}, ベアクロス)",
            }

        # BUY信号（過売り領域 + ゴールデンクロス + RSI売られすぎ）
        elif (
            stoch_k < self.config["stoch_oversold"]
            and stoch_d < self.config["stoch_oversold"]
            and crossover == "golden"
            and rsi < self.config["rsi_oversold"]
        ):
            # 信頼度：Stochastic値が極端なほど高い
            confidence = min(self.config["min_confidence"] + (20 - stoch_k) / 100.0, 0.50)
            strength = (50 - stoch_k) / 50.0  # 0.6-1.0の範囲

            return {
                "action": EntryAction.BUY,
                "confidence": confidence,
                "strength": strength,
                "reason": f"Stochastic反転BUY (K={stoch_k:.1f}, D={stoch_d:.1f}, RSI={rsi:.1f}, ゴールデンクロス)",
            }

        # HOLD信号
        else:
            return {
                "action": EntryAction.HOLD,
                "confidence": self.config["hold_confidence"],
                "strength": 0.0,
                "reason": "Stochastic反転条件未達成",
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
        latest = df.iloc[-1] if not df.empty else None
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

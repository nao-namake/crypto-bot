"""
MACD + EMA Crossover戦略 - Phase 51.7 Day 5

トレンド転換期の押し目買い・戻り売り戦略。
MACDクロスオーバー + EMAトレンド確認による高精度エントリー。

戦略ロジック:
- トレンド相場判定: ADX > 25
- BUY信号: MACDゴールデンクロス + EMA 20 > EMA 50 + 出来高増加
- SELL信号: MACDデッドクロス + EMA 20 < EMA 50 + 出来高増加
- Dynamic confidence: 0.35-0.65（MACD強度 + EMA乖離に基づく）

Phase 51.7 Day 5実装
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from ...core.config.threshold_manager import get_threshold
from ..base.strategy_base import StrategyBase, StrategySignal
from ..strategy_registry import StrategyRegistry
from ..utils import EntryAction, SignalBuilder, StrategyType


@StrategyRegistry.register(name="MACDEMACrossover", strategy_type=StrategyType.MACD_EMA_CROSSOVER)
class MACDEMACrossoverStrategy(StrategyBase):
    """
    MACD + EMA Crossover戦略 - トレンド転換期の押し目買い・戻り売り

    シグナル生成ロジック:
    1. トレンド相場判定（ADX > 25）
    2. BUY信号:
       - MACDがシグナル線を上抜け（ゴールデンクロス）
       - EMA 20 > EMA 50（上昇トレンド確認）
       - volume_ratio > 1.1（出来高増加確認）
    3. SELL信号:
       - MACDがシグナル線を下抜け（デッドクロス）
       - EMA 20 < EMA 50（下降トレンド確認）
       - volume_ratio > 1.1（出来高増加確認）
    4. それ以外 → HOLD
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初期化

        Args:
            config: 戦略設定（thresholds.yamlから読み込み）
        """
        default_config = {
            "min_confidence": get_threshold("strategies.macd_ema_crossover.min_confidence", 0.35),
            "hold_confidence": get_threshold("strategies.macd_ema_crossover.hold_confidence", 0.25),
            "adx_trend_threshold": get_threshold("strategies.macd_ema_crossover.adx_trend_threshold", 25),
            "volume_ratio_threshold": get_threshold("strategies.macd_ema_crossover.volume_ratio_threshold", 1.1),
            "macd_strong_threshold": get_threshold("strategies.macd_ema_crossover.macd_strong_threshold", 50000),
            "ema_divergence_threshold": get_threshold("strategies.macd_ema_crossover.ema_divergence_threshold", 0.01),
            "sl_multiplier": get_threshold("strategies.macd_ema_crossover.sl_multiplier", 1.5),
        }
        merged_config = {**default_config, **(config or {})}
        super().__init__(name="MACDEMACrossover", config=merged_config)

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

        # 3. トレンド相場判定
        if not self._is_trend_market(df):
            return self._create_hold_signal("not_trend_market", df)

        # 4. MACD+EMAクロスシグナル分析
        decision = self._analyze_macd_ema_signal(df)

        # 5. SignalBuilder使用
        return SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.name,
            decision=decision,
            current_price=current_price,
            df=df,
            config=self.config,
            strategy_type=StrategyType.MACD_EMA_CROSSOVER,
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
            "macd",  # MACD線（12,26）
            "macd_signal",  # MACDシグナル線（9期間EMA）
            "ema_20",  # EMA 20期間
            "ema_50",  # EMA 50期間
            "adx_14",  # ADX（トレンド強度判定用）
            "volume_ratio",  # 出来高比率
            "atr_14",  # ATR（リスク管理用）
        ]

    def _is_trend_market(self, df: pd.DataFrame) -> bool:
        """
        トレンド相場判定

        Args:
            df: 市場データ

        Returns:
            bool: トレンド相場の場合True
        """
        latest = df.iloc[-1]
        adx = float(latest["adx_14"])

        # ADX > 25 = トレンド相場
        return adx >= self.config["adx_trend_threshold"]

    def _detect_macd_crossover(self, df: pd.DataFrame) -> str:
        """
        MACDクロスオーバー検出

        Args:
            df: 市場データ

        Returns:
            str: "golden" (ゴールデンクロス), "dead" (デッドクロス), "none"
        """
        if len(df) < 2:
            return "none"

        # 最新と1つ前のデータ
        current = df.iloc[-1]
        previous = df.iloc[-2]

        current_macd = float(current["macd"])
        current_signal = float(current["macd_signal"])
        previous_macd = float(previous["macd"])
        previous_signal = float(previous["macd_signal"])

        # ゴールデンクロス: MACDがシグナルを下から上に抜ける
        if previous_macd <= previous_signal and current_macd > current_signal:
            return "golden"

        # デッドクロス: MACDがシグナルを上から下に抜ける
        if previous_macd >= previous_signal and current_macd < current_signal:
            return "dead"

        return "none"

    def _check_ema_trend(self, df: pd.DataFrame) -> str:
        """
        EMAトレンド判定

        Args:
            df: 市場データ

        Returns:
            str: "uptrend" (上昇トレンド), "downtrend" (下降トレンド), "neutral"
        """
        latest = df.iloc[-1]
        ema_20 = float(latest["ema_20"])
        ema_50 = float(latest["ema_50"])

        # EMA 20 > EMA 50 = 上昇トレンド
        if ema_20 > ema_50:
            return "uptrend"
        # EMA 20 < EMA 50 = 下降トレンド
        elif ema_20 < ema_50:
            return "downtrend"
        else:
            return "neutral"

    def _calculate_macd_strength(self, df: pd.DataFrame) -> float:
        """
        MACD強度計算（ヒストグラム絶対値）

        Args:
            df: 市場データ

        Returns:
            float: MACD強度（0.0-1.0）
        """
        latest = df.iloc[-1]
        macd = float(latest["macd"])
        macd_signal = float(latest["macd_signal"])

        # MACDヒストグラム = MACD - Signal
        histogram = abs(macd - macd_signal)

        # 強度を正規化（0.0-1.0の範囲）
        # 強い: histogram > 50000 → 1.0
        # 弱い: histogram = 0 → 0.0
        strength = min(histogram / self.config["macd_strong_threshold"], 1.0)

        return strength

    def _calculate_ema_divergence(self, df: pd.DataFrame) -> float:
        """
        EMA乖離度計算

        Args:
            df: 市場データ

        Returns:
            float: EMA乖離度（0.0-1.0）
        """
        latest = df.iloc[-1]
        ema_20 = float(latest["ema_20"])
        ema_50 = float(latest["ema_50"])

        # 乖離度 = |EMA20 - EMA50| / EMA50
        divergence = abs(ema_20 - ema_50) / ema_50 if ema_50 > 0 else 0.0

        # 正規化（0.0-1.0の範囲）
        # 強い乖離: > 1% → 1.0
        normalized = min(divergence / self.config["ema_divergence_threshold"], 1.0)

        return normalized

    def _analyze_macd_ema_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        MACD+EMAシグナル分析

        Args:
            df: 市場データ

        Returns:
            Dict[str, Any]: シグナル判断結果
        """
        latest = df.iloc[-1]
        volume_ratio = float(latest["volume_ratio"])

        # クロスオーバー検出
        crossover = self._detect_macd_crossover(df)

        # EMAトレンド判定
        ema_trend = self._check_ema_trend(df)

        # MACD強度・EMA乖離度計算
        macd_strength = self._calculate_macd_strength(df)
        ema_divergence = self._calculate_ema_divergence(df)

        # BUY信号（ゴールデンクロス + 上昇トレンド + 出来高増加）
        if crossover == "golden" and ema_trend == "uptrend" and volume_ratio >= self.config["volume_ratio_threshold"]:
            # 信頼度：MACD強度 + EMA乖離度に基づく（0.35-0.65）
            confidence = min(
                self.config["min_confidence"] + (macd_strength * 0.15) + (ema_divergence * 0.15),
                0.65,
            )

            # シグナル強度：MACD強度を採用
            strength = macd_strength

            return {
                "action": EntryAction.BUY,
                "confidence": confidence,
                "strength": strength,
                "reason": f"MACD+EMAクロスBUY (MACD強度={macd_strength:.2f}, EMA乖離={ema_divergence:.2%}, 出来高比={volume_ratio:.2f})",
            }

        # SELL信号（デッドクロス + 下降トレンド + 出来高増加）
        elif crossover == "dead" and ema_trend == "downtrend" and volume_ratio >= self.config["volume_ratio_threshold"]:
            # 信頼度：MACD強度 + EMA乖離度に基づく（0.35-0.65）
            confidence = min(
                self.config["min_confidence"] + (macd_strength * 0.15) + (ema_divergence * 0.15),
                0.65,
            )

            # シグナル強度：MACD強度を採用
            strength = macd_strength

            return {
                "action": EntryAction.SELL,
                "confidence": confidence,
                "strength": strength,
                "reason": f"MACD+EMAクロスSELL (MACD強度={macd_strength:.2f}, EMA乖離={ema_divergence:.2%}, 出来高比={volume_ratio:.2f})",
            }

        # HOLD信号
        else:
            return {
                "action": EntryAction.HOLD,
                "confidence": self.config["hold_confidence"],
                "strength": 0.0,
                "reason": "MACD+EMAクロス条件未達成",
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
            reason=f"MACDEMACrossover: {reason}",
            strategy_name=self.name,
            timestamp=str(pd.Timestamp.now()),
        )

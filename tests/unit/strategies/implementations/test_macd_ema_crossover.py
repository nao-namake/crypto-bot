"""
MACD + EMA Crossover戦略のテストモジュール - Phase 51.7 Day 5

MACDEMACrossoverStrategyクラスの単体テスト。
トレンド転換期のシグナル検出、クロスオーバー判定、エラーハンドリングを検証。

テスト項目:
- 初期化・設定テスト
- トレンド相場判定テスト
- MACDクロスオーバー検出テスト（ゴールデン/デッド）
- EMAトレンド判定テスト
- BUY信号生成テスト（ゴールデンクロス + 上昇トレンド + 出来高増加）
- SELL信号生成テスト（デッドクロス + 下降トレンド + 出来高増加）
- HOLD信号生成テスト
- レンジ相場フィルタリングテスト
- データ検証テスト
- エラーハンドリングテスト

Phase 51.7 Day 5実装: 2025年11月
"""

import unittest
from datetime import datetime
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

from src.strategies.implementations.macd_ema_crossover import MACDEMACrossoverStrategy
from src.strategies.utils.strategy_utils import EntryAction


class TestMACDEMACrossoverStrategy(unittest.TestCase):
    """MACDEMACrossoverStrategyクラスのテスト"""

    def setUp(self):
        """テスト前処理"""
        self.config = {
            "min_confidence": 0.35,
            "hold_confidence": 0.25,
            "adx_trend_threshold": 25,
            "volume_ratio_threshold": 1.1,
            "macd_strong_threshold": 50000,
            "ema_divergence_threshold": 0.01,
            "sl_multiplier": 1.5,
        }
        self.strategy = MACDEMACrossoverStrategy(config=self.config)

    def _create_test_data(
        self,
        length: int = 50,
        macd: float = 0,
        macd_signal: float = 0,
        ema_20: float = 15000000,
        ema_50: float = 15000000,
        adx: float = 30,
        volume_ratio: float = 1.2,
        crossover_type: str = "none",
    ) -> pd.DataFrame:
        """
        テスト用データ生成

        Args:
            length: データ長
            macd: MACD値
            macd_signal: MACDシグナル値
            ema_20: EMA 20値
            ema_50: EMA 50値
            adx: ADX値
            volume_ratio: 出来高比率
            crossover_type: クロスオーバータイプ（"golden", "dead", "none"）

        Returns:
            テストデータ
        """
        np.random.seed(42)
        dates = pd.date_range(start="2025-01-01", periods=length, freq="4h")

        # 基本価格データ
        base_price = 15000000
        prices = base_price + np.cumsum(np.random.randn(length) * 10000)

        # MACD特徴量
        macd_values = np.full(length, macd)
        macd_signal_values = np.full(length, macd_signal)

        # クロスオーバー設定（最新2行のみ調整）
        if crossover_type == "golden" and length >= 2:
            # ゴールデンクロス: MACDがシグナルを下から上に抜ける
            macd_values[-2] = macd_signal - 1000  # 前: MACD < Signal
            macd_values[-1] = macd_signal + 1000  # 現: MACD > Signal
        elif crossover_type == "dead" and length >= 2:
            # デッドクロス: MACDがシグナルを上から下に抜ける
            macd_values[-2] = macd_signal + 1000  # 前: MACD > Signal
            macd_values[-1] = macd_signal - 1000  # 現: MACD < Signal

        # EMA特徴量
        ema_20_values = np.full(length, ema_20)
        ema_50_values = np.full(length, ema_50)

        # その他特徴量
        adx_14 = np.full(length, adx)
        volume_ratio_values = np.full(length, volume_ratio)
        atr_14 = np.full(length, base_price * 0.01)

        return pd.DataFrame(
            {
                "timestamp": dates,
                "close": prices,
                "macd": macd_values,
                "macd_signal": macd_signal_values,
                "ema_20": ema_20_values,
                "ema_50": ema_50_values,
                "adx_14": adx_14,
                "volume_ratio": volume_ratio_values,
                "atr_14": atr_14,
            }
        )

    def test_strategy_initialization(self):
        """戦略初期化テスト"""
        # デフォルト設定
        default_strategy = MACDEMACrossoverStrategy()
        self.assertEqual(default_strategy.name, "MACDEMACrossover")
        self.assertIsNotNone(default_strategy.config)

        # カスタム設定
        self.assertEqual(self.strategy.config["adx_trend_threshold"], 25)
        self.assertEqual(self.strategy.config["volume_ratio_threshold"], 1.1)
        self.assertEqual(self.strategy.config["macd_strong_threshold"], 50000)
        self.assertEqual(self.strategy.config["ema_divergence_threshold"], 0.01)

    def test_required_features(self):
        """必須特徴量テスト"""
        required = self.strategy.get_required_features()
        expected = [
            "close",
            "macd",
            "macd_signal",
            "ema_20",
            "ema_50",
            "adx_14",
            "volume_ratio",
            "atr_14",
        ]
        self.assertEqual(set(required), set(expected))

    def test_is_trend_market_true(self):
        """トレンド相場判定テスト - トレンド相場"""
        # トレンド相場条件: ADX >= 25
        df = self._create_test_data(adx=30)
        is_trend = self.strategy._is_trend_market(df)
        self.assertTrue(is_trend)

    def test_is_trend_market_false_low_adx(self):
        """トレンド相場判定テスト - レンジ相場（ADX低）"""
        # レンジ相場条件: ADX < 25
        df = self._create_test_data(adx=20)
        is_trend = self.strategy._is_trend_market(df)
        self.assertFalse(is_trend)

    def test_detect_macd_crossover_golden(self):
        """MACDクロスオーバー検出テスト - ゴールデンクロス"""
        df = self._create_test_data(
            length=50, macd=10000, macd_signal=9000, crossover_type="golden"
        )
        crossover = self.strategy._detect_macd_crossover(df)
        self.assertEqual(crossover, "golden")

    def test_detect_macd_crossover_dead(self):
        """MACDクロスオーバー検出テスト - デッドクロス"""
        df = self._create_test_data(length=50, macd=10000, macd_signal=11000, crossover_type="dead")
        crossover = self.strategy._detect_macd_crossover(df)
        self.assertEqual(crossover, "dead")

    def test_detect_macd_crossover_none(self):
        """MACDクロスオーバー検出テスト - クロスなし"""
        df = self._create_test_data(length=50, macd=10000, macd_signal=9000, crossover_type="none")
        crossover = self.strategy._detect_macd_crossover(df)
        self.assertEqual(crossover, "none")

    def test_detect_macd_crossover_insufficient_data(self):
        """MACDクロスオーバー検出テスト - データ不足"""
        df = self._create_test_data(length=1)
        crossover = self.strategy._detect_macd_crossover(df)
        self.assertEqual(crossover, "none")

    def test_check_ema_trend_uptrend(self):
        """EMAトレンド判定テスト - 上昇トレンド"""
        # EMA 20 > EMA 50
        df = self._create_test_data(ema_20=15200000, ema_50=15000000)
        ema_trend = self.strategy._check_ema_trend(df)
        self.assertEqual(ema_trend, "uptrend")

    def test_check_ema_trend_downtrend(self):
        """EMAトレンド判定テスト - 下降トレンド"""
        # EMA 20 < EMA 50
        df = self._create_test_data(ema_20=14800000, ema_50=15000000)
        ema_trend = self.strategy._check_ema_trend(df)
        self.assertEqual(ema_trend, "downtrend")

    def test_check_ema_trend_neutral(self):
        """EMAトレンド判定テスト - ニュートラル"""
        # EMA 20 = EMA 50
        df = self._create_test_data(ema_20=15000000, ema_50=15000000)
        ema_trend = self.strategy._check_ema_trend(df)
        self.assertEqual(ema_trend, "neutral")

    @patch(
        "src.strategies.implementations.macd_ema_crossover.SignalBuilder.create_signal_with_risk_management"
    )
    def test_analyze_buy_signal(self, mock_signal_builder):
        """BUY信号生成テスト - ゴールデンクロス + 上昇トレンド + 出来高増加"""
        # BUY条件: ゴールデンクロス + EMA 20 > EMA 50 + ADX >= 25 + volume_ratio >= 1.1
        df = self._create_test_data(
            macd=10000,
            macd_signal=9000,
            ema_20=15200000,
            ema_50=15000000,
            adx=30,
            volume_ratio=1.2,
            crossover_type="golden",
        )

        mock_signal = Mock()
        mock_signal.action = EntryAction.BUY
        mock_signal_builder.return_value = mock_signal

        signal = self.strategy.analyze(df)

        # SignalBuilderが呼ばれたことを確認
        mock_signal_builder.assert_called_once()
        call_args = mock_signal_builder.call_args

        # decision引数を確認
        decision = call_args[1]["decision"]
        self.assertEqual(decision["action"], EntryAction.BUY)
        self.assertGreater(decision["confidence"], 0.30)
        self.assertGreater(decision["strength"], 0)

    @patch(
        "src.strategies.implementations.macd_ema_crossover.SignalBuilder.create_signal_with_risk_management"
    )
    def test_analyze_sell_signal(self, mock_signal_builder):
        """SELL信号生成テスト - デッドクロス + 下降トレンド + 出来高増加"""
        # SELL条件: デッドクロス + EMA 20 < EMA 50 + ADX >= 25 + volume_ratio >= 1.1
        df = self._create_test_data(
            macd=10000,
            macd_signal=11000,
            ema_20=14800000,
            ema_50=15000000,
            adx=30,
            volume_ratio=1.2,
            crossover_type="dead",
        )

        mock_signal = Mock()
        mock_signal.action = EntryAction.SELL
        mock_signal_builder.return_value = mock_signal

        signal = self.strategy.analyze(df)

        # SignalBuilderが呼ばれたことを確認
        mock_signal_builder.assert_called_once()
        call_args = mock_signal_builder.call_args

        # decision引数を確認
        decision = call_args[1]["decision"]
        self.assertEqual(decision["action"], EntryAction.SELL)
        self.assertGreater(decision["confidence"], 0.30)
        self.assertGreater(decision["strength"], 0)

    @patch("src.strategies.implementations.macd_ema_crossover.SignalBuilder.create_hold_signal")
    def test_analyze_hold_signal_no_crossover(self, mock_hold_signal):
        """HOLD信号生成テスト - クロスオーバーなし"""
        # HOLD条件: クロスオーバーなし
        df = self._create_test_data(
            macd=10000,
            macd_signal=9000,
            ema_20=15200000,
            ema_50=15000000,
            adx=30,
            volume_ratio=1.2,
            crossover_type="none",
        )

        mock_signal = Mock()
        mock_signal.action = EntryAction.HOLD
        mock_hold_signal.return_value = mock_signal

        # クロスオーバーなしのでHOLD
        signal = self.strategy.analyze(df)

        # SignalBuilderが呼ばれる（HOLDシグナル生成）
        self.assertEqual(signal.action, EntryAction.HOLD)

    def test_analyze_hold_signal_range_market(self):
        """HOLD信号生成テスト - レンジ相場"""
        # レンジ相場条件: ADX < 25
        df = self._create_test_data(
            macd=10000,
            macd_signal=9000,
            ema_20=15200000,
            ema_50=15000000,
            adx=20,
            volume_ratio=1.2,
            crossover_type="golden",
        )

        # レンジ相場なので即HOLD
        signal = self.strategy.analyze(df)
        self.assertEqual(signal.action, EntryAction.HOLD)
        self.assertIn("not_trend_market", signal.reason)

    def test_analyze_macd_ema_signal_buy(self):
        """MACD+EMAシグナル分析テスト - BUY"""
        df = self._create_test_data(
            macd=10000,
            macd_signal=9000,
            ema_20=15200000,
            ema_50=15000000,
            volume_ratio=1.2,
            crossover_type="golden",
        )
        decision = self.strategy._analyze_macd_ema_signal(df)

        self.assertEqual(decision["action"], EntryAction.BUY)
        self.assertGreater(decision["confidence"], 0.30)
        self.assertGreater(decision["strength"], 0)
        self.assertIn("MACD+EMAクロスBUY", decision["reason"])

    def test_analyze_macd_ema_signal_sell(self):
        """MACD+EMAシグナル分析テスト - SELL"""
        df = self._create_test_data(
            macd=10000,
            macd_signal=11000,
            ema_20=14800000,
            ema_50=15000000,
            volume_ratio=1.2,
            crossover_type="dead",
        )
        decision = self.strategy._analyze_macd_ema_signal(df)

        self.assertEqual(decision["action"], EntryAction.SELL)
        self.assertGreater(decision["confidence"], 0.30)
        self.assertGreater(decision["strength"], 0)
        self.assertIn("MACD+EMAクロスSELL", decision["reason"])

    def test_analyze_macd_ema_signal_hold(self):
        """MACD+EMAシグナル分析テスト - HOLD"""
        df = self._create_test_data(
            macd=10000,
            macd_signal=9000,
            volume_ratio=1.0,  # 出来高不足
            crossover_type="none",
        )
        decision = self.strategy._analyze_macd_ema_signal(df)

        self.assertEqual(decision["action"], EntryAction.HOLD)
        self.assertEqual(decision["confidence"], self.config["hold_confidence"])
        self.assertEqual(decision["strength"], 0.0)

    def test_analyze_empty_dataframe(self):
        """空データフレームテスト"""
        df = pd.DataFrame()
        signal = self.strategy.analyze(df)

        self.assertEqual(signal.action, EntryAction.HOLD)
        self.assertIn("insufficient_data", signal.reason)

    def test_analyze_missing_features(self):
        """必須特徴量欠落テスト"""
        df = pd.DataFrame(
            {
                "close": [15000000],
                "macd": [10000],
                # 他の特徴量が欠落
            }
        )
        signal = self.strategy.analyze(df)

        self.assertEqual(signal.action, EntryAction.HOLD)
        self.assertIn("insufficient_data", signal.reason)

    def test_calculate_macd_strength(self):
        """MACD強度計算テスト"""
        # MACD強度 = |MACD - Signal| / macd_strong_threshold
        df = self._create_test_data(macd=60000, macd_signal=10000)  # ヒストグラム = 50000
        strength = self.strategy._calculate_macd_strength(df)

        # strength = 50000 / 50000 = 1.0
        self.assertAlmostEqual(strength, 1.0, places=2)

    def test_calculate_ema_divergence(self):
        """EMA乖離度計算テスト"""
        # EMA乖離度 = |EMA20 - EMA50| / EMA50
        df = self._create_test_data(ema_20=15150000, ema_50=15000000)  # 乖離 = 1%
        divergence = self.strategy._calculate_ema_divergence(df)

        # divergence = 0.01 / 0.01 = 1.0
        self.assertAlmostEqual(divergence, 1.0, places=2)


# pytest実行用
if __name__ == "__main__":
    unittest.main()

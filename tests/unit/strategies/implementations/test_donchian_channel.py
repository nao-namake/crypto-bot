"""
Donchian Channel戦略のテストモジュール

DonchianChannelStrategyクラスの単体テスト。
ブレイクアウト検出、リバーサル判定、エラーハンドリングを検証。

テスト項目:
- 初期化・設定テスト
- ブレイクアウトシグナルテスト
- リバーサルシグナルテスト
- データ検証テスト
- エラーハンドリングテスト

実装日: 2025年9月9日
"""

import unittest
from datetime import datetime
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

from src.strategies.implementations.donchian_channel import DonchianChannelStrategy


class TestDonchianChannelStrategy(unittest.TestCase):
    """DonchianChannelStrategyクラスのテスト"""

    def setUp(self):
        """テスト前処理"""
        self.config = {
            "channel_period": 20,
            "breakout_threshold": 0.002,
            "reversal_threshold": 0.05,
            "min_confidence": 0.4,
        }
        self.strategy = DonchianChannelStrategy(config=self.config)

    def _create_test_data(self, length: int = 50) -> pd.DataFrame:
        """テスト用データ生成"""
        np.random.seed(42)
        dates = pd.date_range(start="2025-01-01", periods=length, freq="1h")

        # 基本価格データ
        prices = 4500000 + np.cumsum(np.random.randn(length) * 1000)
        highs = prices + np.random.rand(length) * 2000
        lows = prices - np.random.rand(length) * 2000
        volumes = 1000 + np.random.rand(length) * 500

        # Donchian Channel特徴量
        donchian_high_20 = pd.Series(highs).rolling(20).max()
        donchian_low_20 = pd.Series(lows).rolling(20).min()
        channel_position = (prices - donchian_low_20) / (donchian_high_20 - donchian_low_20)

        # 追加特徴量
        atr_14 = pd.Series(highs - lows).rolling(14).mean()
        volume_ratio = volumes / pd.Series(volumes).rolling(20).mean()

        return pd.DataFrame(
            {
                "timestamp": dates,
                "close": prices,
                "high": highs,
                "low": lows,
                "volume": volumes,
                "donchian_high_20": donchian_high_20,
                "donchian_low_20": donchian_low_20,
                "channel_position": channel_position,
                "atr_14": atr_14,
                "volume_ratio": volume_ratio,
            }
        )

    def test_strategy_initialization(self):
        """戦略初期化テスト"""
        # デフォルト設定
        default_strategy = DonchianChannelStrategy()
        self.assertEqual(default_strategy.name, "DonchianChannel")
        self.assertEqual(default_strategy.channel_period, 20)

        # カスタム設定
        self.assertEqual(self.strategy.channel_period, 20)
        self.assertEqual(self.strategy.breakout_threshold, 0.002)

    def test_required_features(self):
        """必要特徴量テスト"""
        required = self.strategy.get_required_features()
        expected = [
            "close",
            "high",
            "low",
            "volume",
            "donchian_high_20",
            "donchian_low_20",
            "channel_position",
            "atr_14",
            "volume_ratio",
        ]

        for feature in expected:
            self.assertIn(feature, required)

    def test_data_validation_success(self):
        """データ検証成功テスト"""
        df = self._create_test_data(50)
        self.assertTrue(self.strategy._validate_data(df))

    def test_data_validation_insufficient_length(self):
        """データ不足テスト"""
        df = self._create_test_data(10)  # 20期間未満
        self.assertFalse(self.strategy._validate_data(df))

    def test_data_validation_missing_columns(self):
        """必要列不足テスト"""
        df = self._create_test_data(50)
        df = df.drop(columns=["donchian_high_20"])
        self.assertFalse(self.strategy._validate_data(df))

    def test_data_validation_nan_values(self):
        """NaN値テスト"""
        df = self._create_test_data(50)
        df.loc[df.index[-1], "channel_position"] = np.nan
        self.assertFalse(self.strategy._validate_data(df))

    def test_channel_analysis_success(self):
        """チャネル分析成功テスト"""
        df = self._create_test_data(50)
        analysis = self.strategy._analyze_donchian_channel(df)

        self.assertIsNotNone(analysis)
        self.assertIn("current_price", analysis)
        self.assertIn("channel_position", analysis)
        self.assertIn("is_upper_breakout", analysis)
        self.assertIn("is_lower_breakout", analysis)

    def test_upper_breakout_signal(self):
        """上方ブレイクアウトシグナルテスト"""
        df = self._create_test_data(50)

        # 上方ブレイクアウト条件設定
        latest_idx = df.index[-1]
        donchian_high = df.loc[latest_idx, "donchian_high_20"]
        df.loc[latest_idx, "close"] = donchian_high * 1.005  # +0.5%ブレイクアウト
        df.loc[latest_idx, "volume_ratio"] = 1.5  # 出来高増加

        signal = self.strategy.generate_signal(df)

        self.assertEqual(signal.action, "buy")
        self.assertGreater(signal.confidence, 0.6)
        self.assertIn("ブレイクアウト", signal.reason)

    def test_lower_breakout_signal(self):
        """下方ブレイクアウトシグナルテスト"""
        df = self._create_test_data(50)

        # 下方ブレイクアウト条件設定
        latest_idx = df.index[-1]
        donchian_low = df.loc[latest_idx, "donchian_low_20"]
        df.loc[latest_idx, "close"] = donchian_low * 0.995  # -0.5%ブレイクアウト
        df.loc[latest_idx, "volume_ratio"] = 1.5

        signal = self.strategy.generate_signal(df)

        self.assertEqual(signal.action, "sell")
        self.assertGreater(signal.confidence, 0.6)
        self.assertIn("ブレイクアウト", signal.reason)

    def test_upper_reversal_signal(self):
        """上限リバーサルシグナルテスト"""
        df = self._create_test_data(50)

        # 上限付近リバーサル条件設定
        latest_idx = df.index[-1]
        df.loc[latest_idx, "channel_position"] = 0.96  # 上部4%
        df.loc[latest_idx, "volume_ratio"] = 1.2

        signal = self.strategy.generate_signal(df)

        self.assertEqual(signal.action, "sell")
        self.assertGreaterEqual(signal.confidence, self.config["min_confidence"])
        self.assertIn("リバーサル", signal.reason)

    def test_lower_reversal_signal(self):
        """下限リバーサルシグナルテスト"""
        df = self._create_test_data(50)

        # 下限付近リバーサル条件設定
        latest_idx = df.index[-1]
        df.loc[latest_idx, "channel_position"] = 0.04  # 下部4%
        df.loc[latest_idx, "volume_ratio"] = 1.2

        signal = self.strategy.generate_signal(df)

        self.assertEqual(signal.action, "buy")
        self.assertGreaterEqual(signal.confidence, self.config["min_confidence"])
        self.assertIn("リバーサル", signal.reason)

    def test_middle_zone_hold(self):
        """中央域HOLDテスト"""
        df = self._create_test_data(50)

        # 中央域条件設定
        latest_idx = df.index[-1]
        df.loc[latest_idx, "channel_position"] = 0.5  # 中央
        df.loc[latest_idx, "volume_ratio"] = 1.0

        signal = self.strategy.generate_signal(df)

        self.assertEqual(signal.action, "hold")
        self.assertIn("中央域", signal.reason)

    def test_reversal_confidence_calculation(self):
        """リバーサル信頼度計算テスト"""
        analysis = {
            "channel_position": 0.02,  # 下限付近
            "volatility_ratio": 0.02,  # 適度なボラティリティ
            "volume_ratio": 1.3,  # 出来高増加
        }

        confidence = self.strategy._calculate_reversal_confidence(analysis, "buy")

        self.assertGreaterEqual(confidence, 0.2)
        self.assertLessEqual(confidence, 0.9)
        self.assertGreater(confidence, self.config["min_confidence"])

    def test_buy_signal_creation(self):
        """BUYシグナル生成テスト"""
        df = self._create_test_data(50)
        analysis = {
            "current_price": 4500000,
            "channel_position": 0.03,
            "channel_width": 50000,
            "volume_ratio": 1.5,
            "volatility_ratio": 0.02,
        }

        signal = self.strategy._create_buy_signal(df, analysis, confidence=0.7, reason="テストBUY")

        self.assertEqual(signal.action, "buy")
        self.assertEqual(signal.confidence, 0.7)
        self.assertIsNotNone(signal.stop_loss)
        self.assertIsNotNone(signal.take_profit)
        self.assertLess(signal.stop_loss, signal.current_price)
        self.assertGreater(signal.take_profit, signal.current_price)

    def test_sell_signal_creation(self):
        """SELLシグナル生成テスト"""
        df = self._create_test_data(50)
        analysis = {
            "current_price": 4500000,
            "channel_position": 0.97,
            "channel_width": 50000,
            "volume_ratio": 1.5,
            "volatility_ratio": 0.02,
        }

        signal = self.strategy._create_sell_signal(
            df, analysis, confidence=0.7, reason="テストSELL"
        )

        self.assertEqual(signal.action, "sell")
        self.assertEqual(signal.confidence, 0.7)
        self.assertIsNotNone(signal.stop_loss)
        self.assertIsNotNone(signal.take_profit)
        self.assertGreater(signal.stop_loss, signal.current_price)
        self.assertLess(signal.take_profit, signal.current_price)

    def test_hold_signal_creation(self):
        """HOLDシグナル生成テスト"""
        df = self._create_test_data(50)

        signal = self.strategy._create_hold_signal(df, "テスト理由")

        self.assertEqual(signal.action, "hold")
        self.assertGreater(signal.confidence, 0.0)
        self.assertIn("テスト理由", signal.reason)

    @patch("src.strategies.implementations.donchian_channel.get_threshold")
    def test_configuration_override(self, mock_get_threshold):
        """設定オーバーライドテスト"""
        mock_get_threshold.return_value = 0.5

        custom_config = {"min_confidence": 0.6}
        strategy = DonchianChannelStrategy(config=custom_config)

        self.assertEqual(strategy.min_confidence, 0.5)  # get_thresholdからの値

    def test_signal_generation_error_handling(self):
        """シグナル生成エラーハンドリングテスト"""
        df = pd.DataFrame()  # 空DataFrame

        from src.core.exceptions import StrategyError

        with self.assertRaises(StrategyError):  # StrategyErrorが発生することを期待
            self.strategy.generate_signal(df)

    def test_channel_analysis_error_handling(self):
        """チャネル分析エラーハンドリングテスト"""
        df = self._create_test_data(50)
        df["close"] = "invalid_data"  # 不正データ

        analysis = self.strategy._analyze_donchian_channel(df)

        self.assertIsNone(analysis)

    def test_signal_metadata_content(self):
        """シグナルメタデータ内容テスト"""
        df = self._create_test_data(50)

        # ブレイクアウトシグナル生成
        latest_idx = df.index[-1]
        donchian_high = df.loc[latest_idx, "donchian_high_20"]
        df.loc[latest_idx, "close"] = donchian_high * 1.005
        df.loc[latest_idx, "volume_ratio"] = 1.5

        signal = self.strategy.generate_signal(df)

        self.assertIn("channel_position", signal.metadata)
        self.assertIn("signal_type", signal.metadata)
        self.assertEqual(signal.metadata["signal_type"], "donchian_breakout")

    def test_multiple_signal_scenarios(self):
        """複数シナリオシグナルテスト"""
        df = self._create_test_data(50)

        scenarios = [
            # 上方ブレイクアウト
            {
                "channel_position": 0.95,
                "price_multiplier": 1.005,
                "volume_ratio": 1.5,
                "expected": "buy",
            },
            # 下方ブレイクアウト
            {
                "channel_position": 0.05,
                "price_multiplier": 0.995,
                "volume_ratio": 1.5,
                "expected": "sell",
            },
            # 中央域
            {
                "channel_position": 0.5,
                "price_multiplier": 1.0,
                "volume_ratio": 1.0,
                "expected": "hold",
            },
        ]

        for scenario in scenarios:
            with self.subTest(scenario=scenario):
                test_df = df.copy()
                latest_idx = test_df.index[-1]

                test_df.loc[latest_idx, "channel_position"] = scenario["channel_position"]
                test_df.loc[latest_idx, "volume_ratio"] = scenario["volume_ratio"]

                if scenario["price_multiplier"] > 1.0:
                    donchian_high = test_df.loc[latest_idx, "donchian_high_20"]
                    test_df.loc[latest_idx, "close"] = donchian_high * scenario["price_multiplier"]
                elif scenario["price_multiplier"] < 1.0:
                    donchian_low = test_df.loc[latest_idx, "donchian_low_20"]
                    test_df.loc[latest_idx, "close"] = donchian_low * scenario["price_multiplier"]

                signal = self.strategy.generate_signal(test_df)
                self.assertEqual(signal.action, scenario["expected"])


if __name__ == "__main__":
    unittest.main()

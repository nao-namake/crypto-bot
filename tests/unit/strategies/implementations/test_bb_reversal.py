"""
BB Reversal戦略のテストモジュール - Phase 51.7 Day 3

BBReversalStrategyクラスの単体テスト。
レンジ相場での平均回帰シグナル検出、市場条件判定、エラーハンドリングを検証。

テスト項目:
- 初期化・設定テスト
- BB幅計算テスト
- レンジ相場判定テスト
- SELL信号生成テスト（BB上限タッチ + RSI買われすぎ）
- BUY信号生成テスト（BB下限タッチ + RSI売られすぎ）
- HOLD信号生成テスト
- トレンド相場フィルタリングテスト
- データ検証テスト
- エラーハンドリングテスト

Phase 51.7 Day 3実装: 2025年11月
"""

import unittest
from datetime import datetime
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

from src.strategies.implementations.bb_reversal import BBReversalStrategy
from src.strategies.utils.strategy_utils import EntryAction


class TestBBReversalStrategy(unittest.TestCase):
    """BBReversalStrategyクラスのテスト"""

    def setUp(self):
        """テスト前処理"""
        self.config = {
            "min_confidence": 0.30,
            "hold_confidence": 0.25,
            "bb_width_threshold": 0.02,
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "bb_upper_threshold": 0.95,
            "bb_lower_threshold": 0.05,
            "adx_range_threshold": 20,
            "sl_multiplier": 1.5,
        }
        self.strategy = BBReversalStrategy(config=self.config)

    def _create_test_data(
        self, length: int = 50, bb_position: float = 0.5, rsi: float = 50, adx: float = 15
    ) -> pd.DataFrame:
        """
        テスト用データ生成

        Args:
            length: データ長
            bb_position: BB位置（0.0-1.0）
            rsi: RSI値（0-100）
            adx: ADX値（0-100）

        Returns:
            テストデータ
        """
        np.random.seed(42)
        dates = pd.date_range(start="2025-01-01", periods=length, freq="4h")

        # 基本価格データ
        base_price = 15000000
        prices = base_price + np.cumsum(np.random.randn(length) * 10000)

        # BB特徴量（bb_positionに基づいて計算）
        bb_middle = prices
        bb_width = base_price * 0.015  # 1.5%幅（レンジ相場）
        bb_upper = bb_middle + bb_width / 2
        bb_lower = bb_middle - bb_width / 2

        # bb_positionを反映した価格調整
        actual_prices = bb_lower + bb_position * (bb_upper - bb_lower)

        # その他特徴量
        atr_14 = np.full(length, base_price * 0.01)
        rsi_14 = np.full(length, rsi)
        adx_14 = np.full(length, adx)

        return pd.DataFrame(
            {
                "timestamp": dates,
                "close": actual_prices,
                "bb_position": np.full(length, bb_position),
                "bb_upper": bb_upper,
                "bb_lower": bb_lower,
                "rsi_14": rsi_14,
                "adx_14": adx_14,
                "atr_14": atr_14,
            }
        )

    def test_strategy_initialization(self):
        """戦略初期化テスト"""
        # デフォルト設定
        default_strategy = BBReversalStrategy()
        self.assertEqual(default_strategy.name, "BBReversal")
        self.assertIsNotNone(default_strategy.config)

        # カスタム設定
        self.assertEqual(self.strategy.config["bb_width_threshold"], 0.02)
        self.assertEqual(self.strategy.config["rsi_overbought"], 70)
        self.assertEqual(self.strategy.config["rsi_oversold"], 30)
        self.assertEqual(self.strategy.config["adx_range_threshold"], 20)

    def test_required_features(self):
        """必須特徴量テスト"""
        required = self.strategy.get_required_features()
        expected = [
            "close",
            "bb_position",
            "bb_upper",
            "bb_lower",
            "rsi_14",
            "adx_14",
            "atr_14",
        ]
        self.assertEqual(set(required), set(expected))

    def test_calculate_bb_width(self):
        """BB幅計算テスト"""
        df = self._create_test_data()
        bb_width = self.strategy._calculate_bb_width(df)

        # BB幅は正の値
        self.assertGreater(bb_width, 0)

        # 正規化されたBB幅（概ね0.01-0.02の範囲）
        self.assertLess(bb_width, 0.1)
        self.assertGreater(bb_width, 0.001)

    def test_is_range_market_true(self):
        """レンジ相場判定テスト - レンジ相場"""
        # レンジ相場条件: BB幅 < 2%, ADX < 20
        df = self._create_test_data(adx=15)
        is_range = self.strategy._is_range_market(df)
        self.assertTrue(is_range)

    def test_is_range_market_false_high_adx(self):
        """レンジ相場判定テスト - トレンド相場（ADX高）"""
        # トレンド相場条件: ADX >= 20
        df = self._create_test_data(adx=25)
        is_range = self.strategy._is_range_market(df)
        self.assertFalse(is_range)

    def test_is_range_market_false_wide_bb(self):
        """レンジ相場判定テスト - トレンド相場（BB幅広）"""
        # トレンド相場条件: BB幅 >= 2%
        df = self._create_test_data()
        # BB幅を強制的に広げる
        df["bb_upper"] = df["close"] * 1.03
        df["bb_lower"] = df["close"] * 0.97
        is_range = self.strategy._is_range_market(df)
        self.assertFalse(is_range)

    @patch(
        "src.strategies.implementations.bb_reversal.SignalBuilder.create_signal_with_risk_management"
    )
    def test_analyze_sell_signal(self, mock_signal_builder):
        """SELL信号生成テスト - BB上限タッチ + RSI買われすぎ"""
        # SELL条件: bb_position > 0.95, rsi > 70, ADX < 20
        df = self._create_test_data(bb_position=0.97, rsi=75, adx=15)

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
        self.assertGreater(decision["confidence"], 0.25)
        self.assertGreater(decision["strength"], 0)

    @patch(
        "src.strategies.implementations.bb_reversal.SignalBuilder.create_signal_with_risk_management"
    )
    def test_analyze_buy_signal(self, mock_signal_builder):
        """BUY信号生成テスト - BB下限タッチ + RSI売られすぎ"""
        # BUY条件: bb_position < 0.05, rsi < 30, ADX < 20
        df = self._create_test_data(bb_position=0.03, rsi=25, adx=15)

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
        self.assertGreater(decision["confidence"], 0.25)
        self.assertGreater(decision["strength"], 0)

    @patch("src.strategies.implementations.bb_reversal.SignalBuilder.create_hold_signal")
    def test_analyze_hold_signal_middle_range(self, mock_hold_signal):
        """HOLD信号生成テスト - BB中央付近"""
        # HOLD条件: bb_position = 0.5（中央）
        df = self._create_test_data(bb_position=0.5, rsi=50, adx=15)

        mock_signal = Mock()
        mock_signal.action = EntryAction.HOLD
        mock_hold_signal.return_value = mock_signal

        # レンジ相場だがBB中央なのでHOLD
        signal = self.strategy.analyze(df)

        # SignalBuilderが呼ばれる（HOLDシグナル生成）
        self.assertEqual(signal.action, EntryAction.HOLD)

    def test_analyze_hold_signal_trend_market(self):
        """HOLD信号生成テスト - トレンド相場"""
        # トレンド相場条件: ADX >= 20
        df = self._create_test_data(bb_position=0.97, rsi=75, adx=30)

        # トレンド相場なので即HOLD
        signal = self.strategy.analyze(df)
        self.assertEqual(signal.action, EntryAction.HOLD)
        self.assertIn("トレンド相場", signal.reason)

    def test_analyze_bb_reversal_signal_sell(self):
        """BB反転シグナル分析テスト - SELL"""
        df = self._create_test_data(bb_position=0.97, rsi=75)
        decision = self.strategy._analyze_bb_reversal_signal(df)

        self.assertEqual(decision["action"], EntryAction.SELL)
        self.assertGreater(decision["confidence"], 0.25)
        self.assertGreater(decision["strength"], 0)
        self.assertIn("BB反転SELL", decision["reason"])

    def test_analyze_bb_reversal_signal_buy(self):
        """BB反転シグナル分析テスト - BUY"""
        df = self._create_test_data(bb_position=0.03, rsi=25)
        decision = self.strategy._analyze_bb_reversal_signal(df)

        self.assertEqual(decision["action"], EntryAction.BUY)
        self.assertGreater(decision["confidence"], 0.25)
        self.assertGreater(decision["strength"], 0)
        self.assertIn("BB反転BUY", decision["reason"])

    def test_analyze_bb_reversal_signal_hold(self):
        """BB反転シグナル分析テスト - HOLD"""
        df = self._create_test_data(bb_position=0.5, rsi=50)
        decision = self.strategy._analyze_bb_reversal_signal(df)

        self.assertEqual(decision["action"], EntryAction.HOLD)
        self.assertEqual(decision["confidence"], self.config["hold_confidence"])
        self.assertEqual(decision["strength"], 0.0)

    def test_analyze_empty_dataframe(self):
        """空データフレームテスト"""
        df = pd.DataFrame()
        signal = self.strategy.analyze(df)

        self.assertEqual(signal.action, EntryAction.HOLD)
        self.assertIn("no_data", signal.reason)

    def test_analyze_missing_features(self):
        """必須特徴量欠落テスト"""
        df = pd.DataFrame(
            {
                "close": [15000000],
                "bb_position": [0.5],
                # 他の特徴量が欠落
            }
        )
        signal = self.strategy.analyze(df)

        self.assertEqual(signal.action, EntryAction.HOLD)
        self.assertIn("missing_features", signal.reason)

    def test_confidence_increases_with_extreme_bb_position(self):
        """信頼度テスト - 極端なBB位置で信頼度上昇"""
        # BB位置が極端なほど信頼度が高い

        # SELL: bb_position = 0.97 vs 0.98
        df_97 = self._create_test_data(bb_position=0.97, rsi=75)
        decision_97 = self.strategy._analyze_bb_reversal_signal(df_97)

        df_98 = self._create_test_data(bb_position=0.98, rsi=75)
        decision_98 = self.strategy._analyze_bb_reversal_signal(df_98)

        self.assertGreater(decision_98["confidence"], decision_97["confidence"])

    def test_strength_calculation_sell(self):
        """強度計算テスト - SELL"""
        df = self._create_test_data(bb_position=0.97, rsi=75)
        decision = self.strategy._analyze_bb_reversal_signal(df)

        # strength = (bb_position - 0.5) * 2.0
        expected_strength = (0.97 - 0.5) * 2.0
        self.assertAlmostEqual(decision["strength"], expected_strength, places=2)

    def test_strength_calculation_buy(self):
        """強度計算テスト - BUY"""
        df = self._create_test_data(bb_position=0.03, rsi=25)
        decision = self.strategy._analyze_bb_reversal_signal(df)

        # strength = (0.5 - bb_position) * 2.0
        expected_strength = (0.5 - 0.03) * 2.0
        self.assertAlmostEqual(decision["strength"], expected_strength, places=2)


# pytest実行用
if __name__ == "__main__":
    unittest.main()

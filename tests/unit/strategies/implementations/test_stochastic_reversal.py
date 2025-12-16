"""
Stochastic Reversal戦略のテストモジュール - Phase 51.7 Day 4

StochasticReversalStrategyクラスの単体テスト。
レンジ相場でのモメンタム逆張りシグナル検出、クロスオーバー判定、エラーハンドリングを検証。

テスト項目:
- 初期化・設定テスト
- レンジ相場判定テスト
- Stochasticクロスオーバー検出テスト（ゴールデン/ベア）
- SELL信号生成テスト（過買い + ベアクロス + RSI買われすぎ）
- BUY信号生成テスト（過売り + ゴールデンクロス + RSI売られすぎ）
- HOLD信号生成テスト
- トレンド相場フィルタリングテスト
- データ検証テスト
- エラーハンドリングテスト

Phase 51.7 Day 4実装: 2025年11月
"""

import unittest
from datetime import datetime
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

from src.strategies.implementations.stochastic_reversal import StochasticReversalStrategy
from src.strategies.utils.strategy_utils import EntryAction


class TestStochasticReversalStrategy(unittest.TestCase):
    """StochasticReversalStrategyクラスのテスト"""

    def setUp(self):
        """テスト前処理"""
        # Phase 54.5: 新閾値対応（stoch 90/10, RSI 70/30, require_crossover=False）
        self.config = {
            "min_confidence": 0.30,
            "hold_confidence": 0.25,
            "stoch_overbought": 90,  # Phase 54.5: 80→90
            "stoch_oversold": 10,  # Phase 54.5: 20→10
            "rsi_overbought": 70,  # Phase 54.5: 65→70
            "rsi_oversold": 30,  # Phase 54.5: 35→30
            "adx_range_threshold": 20,
            "bb_width_threshold": 0.02,  # Phase 54.5: BB幅フィルタ
            "require_crossover": False,  # Phase 54.5: クロスオーバー不要
            "sl_multiplier": 1.5,
        }
        self.strategy = StochasticReversalStrategy(config=self.config)

    def _create_test_data(
        self,
        length: int = 50,
        stoch_k: float = 50,
        stoch_d: float = 50,
        rsi: float = 50,
        adx: float = 15,
        crossover_type: str = "none",
        bb_width_ratio: float = 0.015,  # Phase 54.5: BB幅（デフォルト1.5% = レンジ相場）
    ) -> pd.DataFrame:
        """
        テスト用データ生成

        Args:
            length: データ長
            stoch_k: Stochastic %K値（0-100）
            stoch_d: Stochastic %D値（0-100）
            rsi: RSI値（0-100）
            adx: ADX値（0-100）
            crossover_type: クロスオーバータイプ（"golden", "bear", "none"）
            bb_width_ratio: BB幅（価格に対する比率）- Phase 54.5

        Returns:
            テストデータ
        """
        np.random.seed(42)
        dates = pd.date_range(start="2025-01-01", periods=length, freq="4h")

        # 基本価格データ
        base_price = 15000000
        prices = base_price + np.cumsum(np.random.randn(length) * 10000)

        # Stochastic特徴量
        stoch_k_values = np.full(length, stoch_k)
        stoch_d_values = np.full(length, stoch_d)

        # クロスオーバー設定（最新2行のみ調整）
        if crossover_type == "golden" and length >= 2:
            # ゴールデンクロス: %Kが%Dを下から上に抜ける
            stoch_k_values[-2] = stoch_d - 1  # 前: K < D
            stoch_k_values[-1] = stoch_d + 1  # 現: K > D
        elif crossover_type == "bear" and length >= 2:
            # ベアクロス: %Kが%Dを上から下に抜ける
            stoch_k_values[-2] = stoch_d + 1  # 前: K > D
            stoch_k_values[-1] = stoch_d - 1  # 現: K < D

        # その他特徴量
        atr_14 = np.full(length, base_price * 0.01)
        rsi_14 = np.full(length, rsi)
        adx_14 = np.full(length, adx)

        # Phase 54.5: BB幅フィルタ用
        bb_middle = prices
        bb_upper = prices * (1 + bb_width_ratio / 2)
        bb_lower = prices * (1 - bb_width_ratio / 2)

        return pd.DataFrame(
            {
                "timestamp": dates,
                "close": prices,
                "stoch_k": stoch_k_values,
                "stoch_d": stoch_d_values,
                "rsi_14": rsi_14,
                "adx_14": adx_14,
                "atr_14": atr_14,
                "bb_upper": bb_upper,  # Phase 54.5
                "bb_lower": bb_lower,  # Phase 54.5
            }
        )

    def test_strategy_initialization(self):
        """戦略初期化テスト"""
        # デフォルト設定
        default_strategy = StochasticReversalStrategy()
        self.assertEqual(default_strategy.name, "StochasticReversal")
        self.assertIsNotNone(default_strategy.config)

        # カスタム設定（Phase 54.5: 新閾値）
        self.assertEqual(self.strategy.config["stoch_overbought"], 90)  # 80→90
        self.assertEqual(self.strategy.config["stoch_oversold"], 10)  # 20→10
        self.assertEqual(self.strategy.config["rsi_overbought"], 70)  # 65→70
        self.assertEqual(self.strategy.config["rsi_oversold"], 30)  # 35→30
        self.assertEqual(self.strategy.config["adx_range_threshold"], 20)
        # Phase 54.5: 新設定
        self.assertEqual(self.strategy.config["bb_width_threshold"], 0.02)
        self.assertEqual(self.strategy.config["require_crossover"], False)

    def test_required_features(self):
        """必須特徴量テスト"""
        required = self.strategy.get_required_features()
        # Phase 54.5: bb_upper, bb_lower追加
        expected = [
            "close",
            "stoch_k",
            "stoch_d",
            "rsi_14",
            "adx_14",
            "atr_14",
            "bb_upper",  # Phase 54.5
            "bb_lower",  # Phase 54.5
        ]
        self.assertEqual(set(required), set(expected))

    def test_is_range_market_true(self):
        """レンジ相場判定テスト - レンジ相場"""
        # レンジ相場条件: ADX < 20
        df = self._create_test_data(adx=15)
        is_range = self.strategy._is_range_market(df)
        self.assertTrue(is_range)

    def test_is_range_market_false_high_adx(self):
        """レンジ相場判定テスト - トレンド相場（ADX高）"""
        # トレンド相場条件: ADX >= 20
        df = self._create_test_data(adx=25)
        is_range = self.strategy._is_range_market(df)
        self.assertFalse(is_range)

    def test_detect_stochastic_crossover_golden(self):
        """Stochasticクロスオーバー検出テスト - ゴールデンクロス"""
        df = self._create_test_data(length=50, stoch_k=25, stoch_d=24, crossover_type="golden")
        crossover = self.strategy._detect_stochastic_crossover(df)
        self.assertEqual(crossover, "golden")

    def test_detect_stochastic_crossover_bear(self):
        """Stochasticクロスオーバー検出テスト - ベアクロス"""
        df = self._create_test_data(length=50, stoch_k=75, stoch_d=76, crossover_type="bear")
        crossover = self.strategy._detect_stochastic_crossover(df)
        self.assertEqual(crossover, "bear")

    def test_detect_stochastic_crossover_none(self):
        """Stochasticクロスオーバー検出テスト - クロスなし"""
        df = self._create_test_data(length=50, stoch_k=50, stoch_d=50, crossover_type="none")
        crossover = self.strategy._detect_stochastic_crossover(df)
        self.assertEqual(crossover, "none")

    def test_detect_stochastic_crossover_insufficient_data(self):
        """Stochasticクロスオーバー検出テスト - データ不足"""
        df = self._create_test_data(length=1)
        crossover = self.strategy._detect_stochastic_crossover(df)
        self.assertEqual(crossover, "none")

    @patch(
        "src.strategies.implementations.stochastic_reversal.SignalBuilder.create_signal_with_risk_management"
    )
    def test_analyze_sell_signal(self, mock_signal_builder):
        """SELL信号生成テスト - Phase 54.5: stoch > 90, RSI > 70（クロスオーバー不要）"""
        # SELL条件: stoch_k > 90, stoch_d > 90, rsi > 70, ADX < 20, BB幅 < 2%
        df = self._create_test_data(stoch_k=92, stoch_d=91, rsi=75, adx=15, bb_width_ratio=0.015)

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
        "src.strategies.implementations.stochastic_reversal.SignalBuilder.create_signal_with_risk_management"
    )
    def test_analyze_buy_signal(self, mock_signal_builder):
        """BUY信号生成テスト - Phase 54.5: stoch < 10, RSI < 30（クロスオーバー不要）"""
        # BUY条件: stoch_k < 10, stoch_d < 10, rsi < 30, ADX < 20, BB幅 < 2%
        df = self._create_test_data(stoch_k=8, stoch_d=9, rsi=25, adx=15, bb_width_ratio=0.015)

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

    @patch("src.strategies.implementations.stochastic_reversal.SignalBuilder.create_hold_signal")
    def test_analyze_hold_signal_middle_range(self, mock_hold_signal):
        """HOLD信号生成テスト - Stochastic中央付近"""
        # HOLD条件: stoch_k/d = 50（中央）
        df = self._create_test_data(stoch_k=50, stoch_d=50, rsi=50, adx=15)

        mock_signal = Mock()
        mock_signal.action = EntryAction.HOLD
        mock_hold_signal.return_value = mock_signal

        # レンジ相場だがStochastic中央なのでHOLD
        signal = self.strategy.analyze(df)

        # SignalBuilderが呼ばれる（HOLDシグナル生成）
        self.assertEqual(signal.action, EntryAction.HOLD)

    def test_analyze_hold_signal_trend_market(self):
        """HOLD信号生成テスト - トレンド相場"""
        # トレンド相場条件: ADX >= 20
        df = self._create_test_data(stoch_k=85, stoch_d=84, rsi=70, adx=30, crossover_type="bear")

        # トレンド相場なので即HOLD
        signal = self.strategy.analyze(df)
        self.assertEqual(signal.action, EntryAction.HOLD)
        self.assertIn("not_range_market", signal.reason)

    def test_analyze_stochastic_reversal_signal_sell(self):
        """Stochastic反転シグナル分析テスト - SELL（Phase 54.5: stoch > 90, RSI > 70）"""
        # Phase 54.5: クロスオーバー不要
        df = self._create_test_data(stoch_k=92, stoch_d=91, rsi=75)
        decision = self.strategy._analyze_stochastic_reversal_signal(df)

        self.assertEqual(decision["action"], EntryAction.SELL)
        self.assertGreater(decision["confidence"], 0.25)
        self.assertGreater(decision["strength"], 0)
        self.assertIn("Stochastic反転SELL", decision["reason"])

    def test_analyze_stochastic_reversal_signal_buy(self):
        """Stochastic反転シグナル分析テスト - BUY（Phase 54.5: stoch < 10, RSI < 30）"""
        # Phase 54.5: クロスオーバー不要
        df = self._create_test_data(stoch_k=8, stoch_d=9, rsi=25)
        decision = self.strategy._analyze_stochastic_reversal_signal(df)

        self.assertEqual(decision["action"], EntryAction.BUY)
        self.assertGreater(decision["confidence"], 0.25)
        self.assertGreater(decision["strength"], 0)
        self.assertIn("Stochastic反転BUY", decision["reason"])

    def test_analyze_stochastic_reversal_signal_hold(self):
        """Stochastic反転シグナル分析テスト - HOLD"""
        df = self._create_test_data(stoch_k=50, stoch_d=50, rsi=50)
        decision = self.strategy._analyze_stochastic_reversal_signal(df)

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
                "stoch_k": [50],
                # 他の特徴量が欠落
            }
        )
        signal = self.strategy.analyze(df)

        self.assertEqual(signal.action, EntryAction.HOLD)
        self.assertIn("insufficient_data", signal.reason)

    def test_confidence_increases_with_extreme_stochastic_sell(self):
        """信頼度テスト - 極端なStochastic値で信頼度上昇（SELL）"""
        # Phase 54.5: Stochastic値が極端なほど信頼度が高い
        # SELL: stoch_k = 92 vs 95
        df_92 = self._create_test_data(stoch_k=92, stoch_d=91, rsi=75)
        decision_92 = self.strategy._analyze_stochastic_reversal_signal(df_92)

        df_95 = self._create_test_data(stoch_k=95, stoch_d=94, rsi=75)
        decision_95 = self.strategy._analyze_stochastic_reversal_signal(df_95)

        self.assertGreater(decision_95["confidence"], decision_92["confidence"])

    def test_confidence_increases_with_extreme_stochastic_buy(self):
        """信頼度テスト - 極端なStochastic値で信頼度上昇（BUY）"""
        # Phase 54.5: BUY: stoch_k = 8 vs 5
        df_8 = self._create_test_data(stoch_k=8, stoch_d=9, rsi=25)
        decision_8 = self.strategy._analyze_stochastic_reversal_signal(df_8)

        df_5 = self._create_test_data(stoch_k=5, stoch_d=6, rsi=25)
        decision_5 = self.strategy._analyze_stochastic_reversal_signal(df_5)

        self.assertGreater(decision_5["confidence"], decision_8["confidence"])

    def test_strength_calculation_sell(self):
        """強度計算テスト - SELL（Phase 54.5）"""
        df = self._create_test_data(stoch_k=92, stoch_d=91, rsi=75)
        decision = self.strategy._analyze_stochastic_reversal_signal(df)

        # strength = (stoch_k - 50) / 50.0
        actual_stoch_k = 92
        expected_strength = (actual_stoch_k - 50) / 50.0
        self.assertAlmostEqual(decision["strength"], expected_strength, places=2)

    def test_strength_calculation_buy(self):
        """強度計算テスト - BUY（Phase 54.5）"""
        df = self._create_test_data(stoch_k=8, stoch_d=9, rsi=25)
        decision = self.strategy._analyze_stochastic_reversal_signal(df)

        # strength = (50 - stoch_k) / 50.0
        actual_stoch_k = 8
        expected_strength = (50 - actual_stoch_k) / 50.0
        self.assertAlmostEqual(decision["strength"], expected_strength, places=2)

    def test_bb_width_filter(self):
        """Phase 54.5: BB幅フィルタテスト - BB幅が広いとHOLD"""
        # BB幅 3% > 2% なのでトレンド相場と判定
        df = self._create_test_data(stoch_k=92, stoch_d=91, rsi=75, adx=15, bb_width_ratio=0.03)
        is_range = self.strategy._is_range_market(df)
        self.assertFalse(is_range)  # BB幅が広いのでレンジ相場ではない

    def test_bb_width_filter_range_ok(self):
        """Phase 54.5: BB幅フィルタテスト - BB幅が狭いとレンジ"""
        # BB幅 1.5% < 2% なのでレンジ相場と判定
        df = self._create_test_data(stoch_k=92, stoch_d=91, rsi=75, adx=15, bb_width_ratio=0.015)
        is_range = self.strategy._is_range_market(df)
        self.assertTrue(is_range)  # BB幅が狭いのでレンジ相場


# pytest実行用
if __name__ == "__main__":
    unittest.main()

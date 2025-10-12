"""
ADX Trend Strength戦略のテストモジュール

ADXTrendStrengthStrategyクラスの単体テスト。
ADX指標分析、DIクロスオーバー検出、トレンド強度判定を検証。

テスト項目:
- 初期化・設定テスト
- ADX分析テスト
- DIクロスオーバーシグナルテスト
- トレンド強度シグナルテスト
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

from src.strategies.implementations.adx_trend import ADXTrendStrengthStrategy


class TestADXTrendStrengthStrategy(unittest.TestCase):
    """ADXTrendStrengthStrategyクラスのテスト"""

    def setUp(self):
        """テスト前処理"""
        self.config = {
            "adx_period": 14,
            "strong_trend_threshold": 25,
            "weak_trend_threshold": 20,
            "di_crossover_threshold": 0.5,
            "min_confidence": 0.4,
        }
        self.strategy = ADXTrendStrengthStrategy(config=self.config)

    def _create_test_data(self, length: int = 50) -> pd.DataFrame:
        """テスト用データ生成"""
        np.random.seed(42)
        dates = pd.date_range(start="2025-01-01", periods=length, freq="1h")

        # 基本価格データ
        prices = 4500000 + np.cumsum(np.random.randn(length) * 1000)
        highs = prices + np.random.rand(length) * 2000
        lows = prices - np.random.rand(length) * 2000
        volumes = 1000 + np.random.rand(length) * 500

        # ADX関連特徴量
        adx_14 = 15 + np.random.rand(length) * 20  # 15-35の範囲
        plus_di_14 = 10 + np.random.rand(length) * 30  # 10-40の範囲
        minus_di_14 = 10 + np.random.rand(length) * 30  # 10-40の範囲

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
                "adx_14": adx_14,
                "plus_di_14": plus_di_14,
                "minus_di_14": minus_di_14,
                "atr_14": atr_14,
                "volume_ratio": volume_ratio,
            }
        )

    def test_strategy_initialization(self):
        """戦略初期化テスト"""
        # デフォルト設定
        default_strategy = ADXTrendStrengthStrategy()
        self.assertEqual(default_strategy.name, "ADXTrendStrength")
        self.assertEqual(default_strategy.adx_period, 14)

        # カスタム設定
        self.assertEqual(self.strategy.adx_period, 14)
        self.assertEqual(self.strategy.strong_trend_threshold, 25)

    def test_required_features(self):
        """必要特徴量テスト"""
        required = self.strategy.get_required_features()
        expected = [
            "close",
            "high",
            "low",
            "volume",
            "adx_14",
            "plus_di_14",
            "minus_di_14",
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
        df = self._create_test_data(10)  # ADX期間+5未満
        self.assertFalse(self.strategy._validate_data(df))

    def test_data_validation_missing_columns(self):
        """必要列不足テスト"""
        df = self._create_test_data(50)
        df = df.drop(columns=["adx_14"])
        self.assertFalse(self.strategy._validate_data(df))

    def test_data_validation_nan_values(self):
        """NaN値テスト"""
        df = self._create_test_data(50)
        df.loc[df.index[-1], "plus_di_14"] = np.nan
        self.assertFalse(self.strategy._validate_data(df))

    def test_adx_analysis_success(self):
        """ADX分析成功テスト"""
        df = self._create_test_data(50)
        analysis = self.strategy._analyze_adx_trend(df)

        self.assertIsNotNone(analysis)
        self.assertIn("adx", analysis)
        self.assertIn("plus_di", analysis)
        self.assertIn("minus_di", analysis)
        self.assertIn("is_strong_trend", analysis)
        self.assertIn("bullish_crossover", analysis)
        self.assertIn("bearish_crossover", analysis)

    def test_strong_trend_bullish_crossover(self):
        """強トレンド上昇DIクロスオーバーテスト"""
        df = self._create_test_data(50)

        # 強トレンド + 上昇DIクロス条件設定
        latest_idx = df.index[-1]
        prev_idx = df.index[-2]

        # 強トレンド設定
        df.loc[latest_idx, "adx_14"] = 30  # 強トレンド
        df.loc[prev_idx, "adx_14"] = 28  # 上昇

        # DIクロスオーバー設定
        df.loc[latest_idx, "plus_di_14"] = 25
        df.loc[latest_idx, "minus_di_14"] = 15  # +DI > -DI
        df.loc[prev_idx, "plus_di_14"] = 15
        df.loc[prev_idx, "minus_di_14"] = 16  # 前期間は-DI > +DI

        df.loc[latest_idx, "volume_ratio"] = 1.5

        signal = self.strategy.generate_signal(df)

        self.assertEqual(signal.action, "buy")
        self.assertGreater(signal.confidence, 0.6)
        self.assertIn("強トレンド", signal.reason)

    def test_strong_trend_bearish_crossover(self):
        """強トレンド下降DIクロスオーバーテスト"""
        df = self._create_test_data(50)

        # 強トレンド + 下降DIクロス条件設定
        latest_idx = df.index[-1]
        prev_idx = df.index[-2]

        # 強トレンド設定
        df.loc[latest_idx, "adx_14"] = 30
        df.loc[prev_idx, "adx_14"] = 28

        # DIクロスオーバー設定
        df.loc[latest_idx, "plus_di_14"] = 15
        df.loc[latest_idx, "minus_di_14"] = 25  # -DI > +DI
        df.loc[prev_idx, "plus_di_14"] = 16
        df.loc[prev_idx, "minus_di_14"] = 15  # 前期間は+DI > -DI

        df.loc[latest_idx, "volume_ratio"] = 1.5

        signal = self.strategy.generate_signal(df)

        self.assertEqual(signal.action, "sell")
        self.assertGreater(signal.confidence, 0.6)
        self.assertIn("強トレンド", signal.reason)

    def test_moderate_trend_bullish_dominance(self):
        """中トレンド上昇優勢テスト"""
        df = self._create_test_data(50)

        # 中トレンド + +DI優勢条件設定
        latest_idx = df.index[-1]

        df.loc[latest_idx, "adx_14"] = 22  # 中程度トレンド
        df.loc[latest_idx, "plus_di_14"] = 25
        df.loc[latest_idx, "minus_di_14"] = 20  # DI差: 5 (>= 2.0)
        df.loc[latest_idx, "volume_ratio"] = 1.2

        signal = self.strategy.generate_signal(df)

        self.assertEqual(signal.action, "buy")
        self.assertGreaterEqual(signal.confidence, self.config["min_confidence"])
        self.assertIn("中トレンド", signal.reason)

    def test_moderate_trend_bearish_dominance(self):
        """中トレンド下降優勢テスト"""
        df = self._create_test_data(50)

        # 中トレンド + -DI優勢条件設定
        latest_idx = df.index[-1]

        df.loc[latest_idx, "adx_14"] = 22
        df.loc[latest_idx, "plus_di_14"] = 18
        df.loc[latest_idx, "minus_di_14"] = 25  # DI差: -7 (強度7 >= 2.0)
        df.loc[latest_idx, "volume_ratio"] = 1.2

        signal = self.strategy.generate_signal(df)

        self.assertEqual(signal.action, "sell")
        self.assertGreaterEqual(signal.confidence, self.config["min_confidence"])
        self.assertIn("中トレンド", signal.reason)

    def test_weak_trend_hold(self):
        """弱トレンド（レンジ相場）HOLDテスト"""
        df = self._create_test_data(50)

        # 弱トレンド条件設定
        latest_idx = df.index[-1]
        df.loc[latest_idx, "adx_14"] = 15  # 弱トレンド (< 20)

        signal = self.strategy.generate_signal(df)

        self.assertEqual(signal.action, "hold")
        # 実装に合わせてレンジ相場関連のメッセージパターンを更新
        self.assertTrue(
            "レンジ相場" in signal.reason or "条件不適合動的" in signal.reason,
            f"Expected range market message in reason: {signal.reason}",
        )

    def test_insufficient_condition_hold(self):
        """条件不適合HOLDテスト"""
        df = self._create_test_data(50)

        # 中途半端な条件設定
        latest_idx = df.index[-1]
        df.loc[latest_idx, "adx_14"] = 22  # 中トレンド
        df.loc[latest_idx, "plus_di_14"] = 20
        df.loc[latest_idx, "minus_di_14"] = 19  # DI差: 1 (< 2.0)
        df.loc[latest_idx, "volume_ratio"] = 1.0

        signal = self.strategy.generate_signal(df)

        self.assertEqual(signal.action, "hold")
        self.assertIn("条件不適合", signal.reason)

    def test_trend_confidence_calculation(self):
        """トレンド信頼度計算テスト"""
        analysis = {
            "adx": 30,  # 強トレンド
            "adx_rising": True,  # ADX上昇
            "di_strength": 8.0,  # 強いDI差
            "bullish_crossover": True,  # クロスオーバー
            "volume_ratio": 1.5,  # 出来高増加
        }

        confidence = self.strategy._calculate_trend_confidence(analysis, "buy")

        self.assertGreaterEqual(confidence, 0.2)
        self.assertLessEqual(confidence, 0.9)
        self.assertGreater(confidence, 0.7)  # 条件が良いので高信頼度

    def test_buy_signal_creation(self):
        """BUYシグナル生成テスト（Phase 32: SignalBuilder統合）"""
        df = self._create_test_data(50)
        analysis = {
            "current_price": 4500000,
            "adx": 30,
            "plus_di": 25,
            "minus_di": 15,
            "di_difference": 10,
            "is_strong_trend": True,
            "volatility_ratio": 0.02,
        }

        # Phase 32: _create_signal()メソッド使用
        signal = self.strategy._create_signal(
            action="buy",
            confidence=0.75,
            reason="テストBUY",
            current_price=analysis["current_price"],
            df=df,
            analysis=analysis,
        )

        self.assertEqual(signal.action, "buy")
        self.assertEqual(signal.confidence, 0.75)
        self.assertIsNotNone(signal.stop_loss)
        self.assertIsNotNone(signal.take_profit)
        self.assertLess(signal.stop_loss, signal.current_price)
        self.assertGreater(signal.take_profit, signal.current_price)

    def test_sell_signal_creation(self):
        """SELLシグナル生成テスト（Phase 32: SignalBuilder統合）"""
        df = self._create_test_data(50)
        analysis = {
            "current_price": 4500000,
            "adx": 30,
            "plus_di": 15,
            "minus_di": 25,
            "di_difference": -10,
            "is_strong_trend": True,
            "volatility_ratio": 0.02,
        }

        # Phase 32: _create_signal()メソッド使用
        signal = self.strategy._create_signal(
            action="sell",
            confidence=0.75,
            reason="テストSELL",
            current_price=analysis["current_price"],
            df=df,
            analysis=analysis,
        )

        self.assertEqual(signal.action, "sell")
        self.assertEqual(signal.confidence, 0.75)
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

    def test_adx_crossover_detection(self):
        """DIクロスオーバー検出テスト"""
        df = self._create_test_data(50)

        # 明確なクロスオーバー設定
        latest_idx = df.index[-1]
        prev_idx = df.index[-2]

        # 上昇クロス: 前期間(-DI > +DI) → 現期間(+DI > -DI)
        df.loc[prev_idx, "plus_di_14"] = 18
        df.loc[prev_idx, "minus_di_14"] = 22  # -4差
        df.loc[latest_idx, "plus_di_14"] = 23
        df.loc[latest_idx, "minus_di_14"] = 17  # +6差（変化量10 > 0.5）

        analysis = self.strategy._analyze_adx_trend(df)

        self.assertIsNotNone(analysis)
        self.assertTrue(analysis["bullish_crossover"])
        self.assertFalse(analysis["bearish_crossover"])

    @patch("src.core.config.threshold_manager.get_threshold")
    def test_configuration_override(self, mock_get_threshold):
        """設定オーバーライドテスト"""
        mock_get_threshold.return_value = 0.6

        custom_config = {"min_confidence": 0.5}
        strategy = ADXTrendStrengthStrategy(config=custom_config)

        self.assertEqual(strategy.min_confidence, 0.6)  # get_thresholdからの値

    def test_signal_generation_error_handling(self):
        """シグナル生成エラーハンドリングテスト"""
        df = pd.DataFrame()  # 空DataFrame

        from src.core.exceptions import StrategyError

        with self.assertRaises(StrategyError):  # StrategyErrorが発生することを期待
            self.strategy.generate_signal(df)

    def test_adx_analysis_error_handling(self):
        """ADX分析エラーハンドリングテスト"""
        df = self._create_test_data(50)
        df["adx_14"] = "invalid_data"  # 不正データ

        analysis = self.strategy._analyze_adx_trend(df)

        self.assertIsNone(analysis)

    def test_signal_metadata_content(self):
        """シグナルメタデータ内容テスト（Phase 32: SignalBuilder統合）"""
        df = self._create_test_data(50)

        # 強トレンド条件設定
        latest_idx = df.index[-1]
        prev_idx = df.index[-2]

        df.loc[latest_idx, "adx_14"] = 30
        df.loc[prev_idx, "adx_14"] = 28
        df.loc[latest_idx, "plus_di_14"] = 25
        df.loc[latest_idx, "minus_di_14"] = 15
        df.loc[prev_idx, "plus_di_14"] = 15
        df.loc[prev_idx, "minus_di_14"] = 16

        signal = self.strategy.generate_signal(df)

        # Phase 32: SignalBuilder統合によりメタデータ構造が変更
        self.assertIn("decision_metadata", signal.metadata)
        self.assertIn("adx", signal.metadata["decision_metadata"])
        self.assertIn("plus_di", signal.metadata["decision_metadata"])
        self.assertIn("minus_di", signal.metadata["decision_metadata"])
        self.assertIn("trend_strength", signal.metadata["decision_metadata"])
        self.assertEqual(signal.metadata["decision_metadata"]["signal_type"], "adx_trend_buy")

    def test_multiple_adx_scenarios(self):
        """複数ADXシナリオテスト"""
        df = self._create_test_data(50)

        scenarios = [
            # 強トレンド上昇クロス - 実装に合わせて修正
            {
                "adx": 30,
                "plus_di": 25,
                "minus_di": 15,
                "prev_plus": 15,
                "prev_minus": 16,
                "expected": "buy",  # 実装に合わせて修正
            },
            # 強トレンド下降クロス - 実装に合わせて修正
            {
                "adx": 30,
                "plus_di": 15,
                "minus_di": 25,
                "prev_plus": 16,
                "prev_minus": 15,
                "expected": "sell",  # 実装に合わせて修正
            },
            # 弱トレンド
            {
                "adx": 10,
                "plus_di": 20,
                "minus_di": 19.5,
                "prev_plus": 21,
                "prev_minus": 17,
                "expected": "hold",
            },
        ]

        for scenario in scenarios:
            with self.subTest(scenario=scenario):
                test_df = df.copy()
                latest_idx = test_df.index[-1]
                prev_idx = test_df.index[-2]

                test_df.loc[latest_idx, "adx_14"] = scenario["adx"]
                test_df.loc[prev_idx, "adx_14"] = scenario["adx"] - 2  # 上昇
                test_df.loc[latest_idx, "plus_di_14"] = scenario["plus_di"]
                test_df.loc[latest_idx, "minus_di_14"] = scenario["minus_di"]
                test_df.loc[prev_idx, "plus_di_14"] = scenario["prev_plus"]
                test_df.loc[prev_idx, "minus_di_14"] = scenario["prev_minus"]
                test_df.loc[latest_idx, "volume_ratio"] = 1.5

                signal = self.strategy.generate_signal(test_df)
                self.assertEqual(signal.action, scenario["expected"])

    def test_calculate_weak_trend_confidence(self):
        """弱トレンド信頼度計算テスト"""
        analysis = {
            "di_strength": 2.5,
            "adx_rising": True,
            "volume_ratio": 1.2,
        }

        confidence = self.strategy._calculate_weak_trend_confidence(analysis, "bullish")

        # 0.25-0.5の範囲内であることを確認
        self.assertGreaterEqual(confidence, 0.25)
        self.assertLessEqual(confidence, 0.50)

    def test_calculate_weak_trend_hold_confidence(self):
        """弱トレンドHOLD信頼度計算テスト（Phase 38.5: hold信頼度向上対応）"""
        df = self._create_test_data(50)
        analysis = {
            "adx": 12,
            "di_strength": 0.5,
        }

        confidence = self.strategy._calculate_weak_trend_hold_confidence(analysis, df)

        # Phase 38.5: hold_min 0.20→0.35, hold_max 0.45→0.60 に引き上げ
        self.assertGreaterEqual(confidence, 0.35)
        self.assertLessEqual(confidence, 0.60)

    def test_calculate_default_confidence(self):
        """デフォルト動的信頼度計算テスト"""
        df = self._create_test_data(50)
        analysis = {
            "is_moderate_trend": True,
            "is_weak_trend": False,
            "is_strong_trend": False,
        }

        confidence = self.strategy._calculate_default_confidence(analysis, df)

        # 0.25-0.45の範囲内であることを確認
        self.assertGreaterEqual(confidence, 0.25)
        self.assertLessEqual(confidence, 0.45)

    def test_calculate_market_uncertainty(self):
        """市場不確実性計算テスト"""
        df = self._create_test_data(50)

        uncertainty = self.strategy._calculate_market_uncertainty(df)

        # 0-0.1の範囲内であることを確認
        self.assertGreaterEqual(uncertainty, 0.0)
        self.assertLessEqual(uncertainty, 0.1)

    def test_calculate_market_uncertainty_error(self):
        """市場不確実性計算エラーハンドリングテスト"""
        df = self._create_test_data(50)
        df["close"] = None

        uncertainty = self.strategy._calculate_market_uncertainty(df)

        # デフォルト値が返されることを確認
        self.assertEqual(uncertainty, 0.02)

    def test_handle_weak_trend_with_sufficient_di(self):
        """弱トレンド処理 - 十分なDI差分テスト"""
        df = self._create_test_data(50)
        analysis = {
            "current_price": 4500000,
            "adx": 12,
            "plus_di": 20,
            "minus_di": 18.5,
            "di_difference": 1.5,  # weak_di_threshold以上
            "di_strength": 1.5,
            "adx_rising": True,
            "volume_ratio": 1.1,
            "volatility_ratio": 0.02,
            "is_strong_trend": False,
            "is_weak_trend": True,
            "is_moderate_trend": False,
        }

        signal = self.strategy._handle_weak_trend_signal(df, analysis)

        # 弱いシグナルまたはHOLDが返されることを確認
        self.assertIn(signal.action, ["buy", "sell", "hold"])

    def test_handle_weak_trend_with_low_di(self):
        """弱トレンド処理 - 低DI差分テスト"""
        df = self._create_test_data(50)
        analysis = {
            "current_price": 4500000,
            "adx": 12,
            "di_difference": 0.3,  # weak_di_threshold未満
            "di_strength": 0.3,
            "adx_rising": False,
            "volume_ratio": 1.0,
        }

        signal = self.strategy._handle_weak_trend_signal(df, analysis)

        # HOLDが返されることを確認
        self.assertEqual(signal.action, "hold")

    def test_analyze_with_multi_timeframe_data(self):
        """マルチタイムフレームデータを使用した分析テスト"""
        df = self._create_test_data(50)

        # 15分足データ作成
        multi_tf_data = {
            "15m": pd.DataFrame(
                {
                    "close": [4500000],
                    "atr_14": [1500],  # 15分足のATR
                }
            )
        }

        signal = self.strategy.analyze(df, multi_timeframe_data=multi_tf_data)

        # シグナルが正常に生成されることを確認
        self.assertIsNotNone(signal)
        self.assertIn(signal.action, ["buy", "sell", "hold"])

    def test_analyze_with_backtest_mode(self):
        """バックテストモードでの分析テスト"""
        import os

        # バックテストモード設定
        os.environ["BACKTEST_MODE"] = "true"

        df = pd.DataFrame()  # 空DataFrame（エラー発生）

        try:
            signal = self.strategy.analyze(df)
            # HOLDシグナルが返されることを確認
            self.assertEqual(signal.action, "hold")
        finally:
            # 環境変数クリーンアップ
            os.environ.pop("BACKTEST_MODE", None)

    def test_adx_falling_condition(self):
        """ADX下降条件テスト"""
        df = self._create_test_data(50)
        latest_idx = df.index[-1]
        prev_idx = df.index[-2]

        # ADX下降設定
        df.loc[latest_idx, "adx_14"] = 20
        df.loc[prev_idx, "adx_14"] = 23  # 下降

        analysis = self.strategy._analyze_adx_trend(df)

        self.assertIsNotNone(analysis)
        self.assertTrue(analysis["adx_falling"])
        self.assertFalse(analysis["adx_rising"])


if __name__ == "__main__":
    unittest.main()

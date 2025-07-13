# =============================================================================
# テストファイル: tests/unit/strategy/test_ensemble_ml_strategy.py
# 説明:
# 取引特化型アンサンブル戦略のユニットテスト
# 既存MLStrategyとの統合・勝率向上機能の検証
# =============================================================================

import unittest
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from crypto_bot.execution.engine import Position, Signal
from crypto_bot.strategy.ensemble_ml_strategy import EnsembleMLStrategy


class TestEnsembleMLStrategy(unittest.TestCase):
    """アンサンブルML戦略のテスト"""

    def setUp(self):
        """テストセットアップ"""
        # テスト用価格データ生成
        np.random.seed(42)
        dates = pd.date_range("2024-01-01", periods=100, freq="1h")
        prices = 50000 + np.cumsum(np.random.randn(100) * 100)

        self.price_df = pd.DataFrame(
            {
                "open": prices + np.random.randn(100) * 50,
                "high": prices + np.abs(np.random.randn(100) * 100),
                "low": prices - np.abs(np.random.randn(100) * 100),
                "close": prices,
                "volume": np.random.randint(1000, 10000, 100),
            },
            index=dates,
        )

        # テスト用設定
        self.ensemble_config = {
            "ml": {
                "ensemble": {
                    "enabled": True,
                    "method": "trading_stacking",
                    "risk_adjustment": True,
                    "confidence_threshold": 0.65,
                    "trading_metrics": {
                        "sharpe_ratio": 0.4,
                        "win_rate": 0.3,
                        "max_drawdown": -0.2,
                        "profit_factor": 0.1,
                    },
                },
                "dynamic_threshold": {"enabled": True, "vix_adjustment": True},
                "extra_features": ["rsi_14", "macd", "vix"],
            }
        }

        self.fallback_config = {
            "ml": {"ensemble": {"enabled": False}, "extra_features": ["rsi_14", "macd"]}
        }

    @patch("crypto_bot.strategy.ensemble_ml_strategy.create_trading_ensemble")
    @patch("crypto_bot.ml.preprocessor.FeatureEngineer")
    def test_ensemble_strategy_initialization(
        self, mock_feature_engineer, mock_create_ensemble
    ):
        """アンサンブル戦略初期化テスト"""
        # モック設定
        mock_ensemble = MagicMock()
        mock_create_ensemble.return_value = mock_ensemble
        mock_feature_engineer.return_value = MagicMock()

        strategy = EnsembleMLStrategy(config=self.ensemble_config)

        self.assertTrue(strategy.ensemble_enabled)
        self.assertTrue(strategy.is_ensemble)
        self.assertEqual(strategy.base_threshold, 0.45)  # より保守的
        mock_create_ensemble.assert_called_once()

    @patch("crypto_bot.strategy.ml_strategy.MLStrategy.__init__")
    def test_fallback_to_ml_strategy(self, mock_ml_init):
        """MLStrategyへのフォールバックテスト"""
        mock_ml_init.return_value = None

        strategy = EnsembleMLStrategy(config=self.fallback_config)

        self.assertFalse(strategy.ensemble_enabled)
        mock_ml_init.assert_called_once()

    @patch("crypto_bot.strategy.ensemble_ml_strategy.create_trading_ensemble")
    @patch("crypto_bot.ml.preprocessor.FeatureEngineer")
    def test_ensemble_signal_generation(
        self, mock_feature_engineer, mock_create_ensemble
    ):
        """アンサンブルシグナル生成テスト"""
        # モック設定
        mock_ensemble = MagicMock()
        mock_ensemble.predict_with_trading_confidence.return_value = (
            np.array([1]),  # predictions
            np.array([[0.3, 0.7]]),  # probabilities
            np.array([0.8]),  # confidence_scores
            {  # trading_info
                "dynamic_threshold": 0.6,
                "market_regime": "normal",
                "risk_level": "low",
            },
        )
        mock_create_ensemble.return_value = mock_ensemble

        mock_fe = MagicMock()
        mock_fe.transform.return_value = pd.DataFrame(np.random.randn(100, 5))
        mock_feature_engineer.return_value = mock_fe

        strategy = EnsembleMLStrategy(config=self.ensemble_config)

        # ポジションなしでのシグナル生成
        position = Position()
        position.exist = False

        signal = strategy.logic_signal(self.price_df, position)

        self.assertIsInstance(signal, Signal)
        mock_ensemble.predict_with_trading_confidence.assert_called_once()

    @patch("crypto_bot.strategy.ensemble_ml_strategy.create_trading_ensemble")
    @patch("crypto_bot.ml.preprocessor.FeatureEngineer")
    def test_high_confidence_long_signal(
        self, mock_feature_engineer, mock_create_ensemble
    ):
        """高信頼度ロングシグナルテスト"""
        # 高信頼度ロング予測のモック
        mock_ensemble = MagicMock()
        mock_ensemble.predict_with_trading_confidence.return_value = (
            np.array([1]),  # ロング予測
            np.array([[0.2, 0.8]]),  # 高確率
            np.array([0.9]),  # 高信頼度
            {"dynamic_threshold": 0.6, "market_regime": "calm"},
        )
        mock_create_ensemble.return_value = mock_ensemble

        mock_fe = MagicMock()
        mock_fe.transform.return_value = pd.DataFrame(np.random.randn(100, 5))
        mock_feature_engineer.return_value = mock_fe

        strategy = EnsembleMLStrategy(config=self.ensemble_config)
        position = Position()
        position.exist = False

        signal = strategy.logic_signal(self.price_df, position)

        self.assertEqual(signal.side, "BUY")
        self.assertIsNotNone(signal.price)

    @patch("crypto_bot.strategy.ensemble_ml_strategy.create_trading_ensemble")
    @patch("crypto_bot.ml.preprocessor.FeatureEngineer")
    def test_low_confidence_no_signal(
        self, mock_feature_engineer, mock_create_ensemble
    ):
        """低信頼度でシグナルなしテスト"""
        # 低信頼度予測のモック
        mock_ensemble = MagicMock()
        mock_ensemble.predict_with_trading_confidence.return_value = (
            np.array([1]),
            np.array([[0.4, 0.6]]),  # 微妙な確率
            np.array([0.4]),  # 低信頼度
            {"dynamic_threshold": 0.6, "market_regime": "volatile"},
        )
        mock_create_ensemble.return_value = mock_ensemble

        mock_fe = MagicMock()
        mock_fe.transform.return_value = pd.DataFrame(np.random.randn(100, 5))
        mock_feature_engineer.return_value = mock_fe

        strategy = EnsembleMLStrategy(config=self.ensemble_config)
        position = Position()
        position.exist = False

        signal = strategy.logic_signal(self.price_df, position)

        self.assertIsNone(signal.side)  # シグナルなし

    @patch("crypto_bot.strategy.ensemble_ml_strategy.create_trading_ensemble")
    @patch("crypto_bot.ml.preprocessor.FeatureEngineer")
    def test_exit_signal_generation(self, mock_feature_engineer, mock_create_ensemble):
        """エグジットシグナル生成テスト"""
        # 低確率予測（エグジット条件）
        mock_ensemble = MagicMock()
        mock_ensemble.predict_with_trading_confidence.return_value = (
            np.array([0]),
            np.array([[0.8, 0.2]]),  # 低い正例確率
            np.array([0.7]),
            {"dynamic_threshold": 0.6, "market_regime": "crisis"},
        )
        mock_create_ensemble.return_value = mock_ensemble

        mock_fe = MagicMock()
        mock_fe.transform.return_value = pd.DataFrame(np.random.randn(100, 5))
        mock_feature_engineer.return_value = mock_fe

        strategy = EnsembleMLStrategy(config=self.ensemble_config)

        # ポジション保有中
        position = Position()
        position.exist = True
        position.side = "BUY"

        signal = strategy.logic_signal(self.price_df, position)

        self.assertEqual(signal.side, "SELL")

    def test_market_context_generation(self):
        """市場コンテキスト生成テスト"""
        strategy = EnsembleMLStrategy(config=self.ensemble_config)
        strategy.vix_adjustment_enabled = True

        # VIX情報のモック
        strategy.get_vix_adjustment = MagicMock(
            return_value=(
                0.05,  # adjustment
                {"current_vix": 25.0, "vix_change": 0.1, "market_regime": "volatile"},
            )
        )

        context = strategy._generate_market_context(self.price_df)

        # 基本的な市場コンテキストが生成されることを確認
        self.assertIn("volatility", context)
        self.assertIn("trend_strength", context)
        self.assertIsInstance(context["volatility"], float)
        self.assertIsInstance(context["trend_strength"], float)

    def test_exit_threshold_calculation(self):
        """エグジット閾値計算テスト"""
        strategy = EnsembleMLStrategy(config=self.ensemble_config)

        # 危機的市場でのエグジット閾値
        crisis_info = {"market_regime": "crisis"}
        crisis_threshold = strategy._calculate_exit_threshold(crisis_info, 0.7)

        # 安定市場でのエグジット閾値
        calm_info = {"market_regime": "calm"}
        calm_threshold = strategy._calculate_exit_threshold(calm_info, 0.7)

        # 危機時の方が早めのエグジット（高い閾値）
        self.assertGreater(crisis_threshold, calm_threshold)

    @patch("crypto_bot.strategy.ensemble_ml_strategy.create_trading_ensemble")
    @patch("crypto_bot.ml.preprocessor.FeatureEngineer")
    def test_signal_history_tracking(self, mock_feature_engineer, mock_create_ensemble):
        """シグナル履歴追跡テスト"""
        mock_ensemble = MagicMock()
        mock_ensemble.predict_with_trading_confidence.return_value = (
            np.array([1]),
            np.array([[0.3, 0.7]]),
            np.array([0.8]),
            {"dynamic_threshold": 0.6, "market_regime": "normal"},
        )
        mock_create_ensemble.return_value = mock_ensemble

        mock_fe = MagicMock()
        mock_fe.transform.return_value = pd.DataFrame(np.random.randn(100, 5))
        mock_feature_engineer.return_value = mock_fe

        strategy = EnsembleMLStrategy(config=self.ensemble_config)
        position = Position()
        position.exist = False

        # 複数回シグナル生成
        for _ in range(3):
            strategy.logic_signal(self.price_df, position)

        # シグナル履歴が記録されていることを確認
        self.assertEqual(len(strategy.recent_signals), 3)

        # 履歴の内容確認
        signal_record = strategy.recent_signals[0]
        self.assertIn("type", signal_record)
        self.assertIn("probability", signal_record)
        self.assertIn("confidence", signal_record)
        self.assertIn("trading_info", signal_record)

    @patch("crypto_bot.strategy.ensemble_ml_strategy.create_trading_ensemble")
    @patch("crypto_bot.ml.preprocessor.FeatureEngineer")
    def test_ensemble_performance_info(
        self, mock_feature_engineer, mock_create_ensemble
    ):
        """アンサンブルパフォーマンス情報テスト"""
        mock_fe = MagicMock()
        mock_feature_engineer.return_value = mock_fe

        strategy = EnsembleMLStrategy(config=self.ensemble_config)

        # アンサンブル無効の場合
        strategy.ensemble_enabled = False
        info = strategy.get_ensemble_performance_info()
        self.assertFalse(info["ensemble_enabled"])

        # アンサンブル有効の場合（モック）
        strategy.ensemble_enabled = True
        strategy.ensemble_model = MagicMock()
        strategy.ensemble_model.get_trading_ensemble_info.return_value = {
            "num_base_models": 3,
            "trading_weights": [0.3, 0.4, 0.3],
        }
        strategy.recent_signals = [
            {"confidence": 0.8, "type": "ENTRY_LONG"},
            {"confidence": 0.7, "type": "ENTRY_LONG"},
            {"confidence": 0.9, "type": "EXIT"},
        ]

        info = strategy.get_ensemble_performance_info()

        self.assertIn("recent_signals_count", info)
        self.assertIn("average_confidence", info)
        self.assertIn("trading_confidence_threshold", info)

    def test_config_update(self):
        """設定動的更新テスト"""
        strategy = EnsembleMLStrategy(config=self.ensemble_config)
        strategy.ensemble_enabled = True

        new_config = {
            "ml": {"ensemble": {"confidence_threshold": 0.75, "risk_adjustment": False}}
        }

        strategy.update_ensemble_config(new_config)

        self.assertEqual(strategy.trading_confidence_threshold, 0.75)
        self.assertFalse(strategy.risk_adjustment_enabled)


class TestEnsembleMLStrategyIntegration(unittest.TestCase):
    """アンサンブルML戦略統合テスト"""

    def setUp(self):
        """統合テストセットアップ"""
        # より現実的な価格データ
        np.random.seed(42)
        dates = pd.date_range("2024-01-01", periods=200, freq="1h")
        trend = np.linspace(50000, 55000, 200)
        noise = np.random.randn(200) * 200
        prices = trend + noise

        self.price_df = pd.DataFrame(
            {
                "open": prices + np.random.randn(200) * 50,
                "high": prices + np.abs(np.random.randn(200) * 150),
                "low": prices - np.abs(np.random.randn(200) * 150),
                "close": prices,
                "volume": np.random.randint(1000, 10000, 200),
            },
            index=dates,
        )

        self.integration_config = {
            "ml": {
                "ensemble": {
                    "enabled": True,
                    "method": "trading_stacking",
                    "confidence_threshold": 0.6,
                },
                "extra_features": ["rsi_14", "macd", "bb_percent"],
            }
        }

    @patch("crypto_bot.strategy.ensemble_ml_strategy.create_trading_ensemble")
    @patch("crypto_bot.ml.preprocessor.FeatureEngineer")
    def test_full_trading_workflow(self, mock_feature_engineer, mock_create_ensemble):
        """完全な取引ワークフローテスト"""
        # アンサンブルモデルのモック（段階的予測）
        predictions_sequence = [
            # エントリーシグナル
            (
                np.array([1]),
                np.array([[0.2, 0.8]]),
                np.array([0.85]),
                {"dynamic_threshold": 0.6, "market_regime": "normal"},
            ),
            # ホールド
            (
                np.array([1]),
                np.array([[0.4, 0.6]]),
                np.array([0.7]),
                {"dynamic_threshold": 0.6, "market_regime": "normal"},
            ),
            # エグジット
            (
                np.array([0]),
                np.array([[0.7, 0.3]]),
                np.array([0.8]),
                {"dynamic_threshold": 0.6, "market_regime": "volatile"},
            ),
        ]

        mock_ensemble = MagicMock()
        mock_ensemble.predict_with_trading_confidence.side_effect = predictions_sequence
        mock_create_ensemble.return_value = mock_ensemble

        mock_fe = MagicMock()
        mock_fe.transform.return_value = pd.DataFrame(np.random.randn(200, 3))
        mock_feature_engineer.return_value = mock_fe

        strategy = EnsembleMLStrategy(config=self.integration_config)

        # 取引シーケンス
        position = Position()
        position.exist = False

        # 1. エントリーシグナル
        signal1 = strategy.logic_signal(self.price_df[:50], position)
        self.assertEqual(signal1.side, "BUY")

        # 2. ポジション保有中（ホールド）
        position.exist = True
        position.side = "BUY"
        signal2 = strategy.logic_signal(self.price_df[50:100], position)
        self.assertIsNone(signal2.side)

        # 3. エグジットシグナル
        signal3 = strategy.logic_signal(self.price_df[100:150], position)
        self.assertEqual(signal3.side, "SELL")

        # シグナル履歴が正しく記録されていることを確認
        self.assertEqual(len(strategy.recent_signals), 2)  # エントリーとエグジット


if __name__ == "__main__":
    unittest.main()

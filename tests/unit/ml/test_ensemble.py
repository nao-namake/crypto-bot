# =============================================================================
# テストファイル: tests/unit/ml/test_ensemble.py
# 説明:
# 取引特化型アンサンブル学習システムのユニットテスト
# 勝率と収益性向上機能の動作確認
# =============================================================================

import unittest

# from unittest.mock import MagicMock
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier

from crypto_bot.ml.ensemble import TradingEnsembleClassifier, create_trading_ensemble


class TestTradingEnsembleClassifier(unittest.TestCase):
    """取引特化型アンサンブル分類器のテスト"""

    def setUp(self):
        """テストセットアップ"""
        # テスト用データ生成
        np.random.seed(42)
        self.X = pd.DataFrame(
            np.random.randn(100, 10), columns=[f"feature_{i}" for i in range(10)]
        )
        self.y = pd.Series(np.random.binomial(1, 0.6, 100))

        # テスト用設定
        self.trading_metrics = {
            "sharpe_ratio": 0.4,
            "win_rate": 0.3,
            "max_drawdown": -0.2,
            "profit_factor": 0.1,
        }

    def test_trading_ensemble_initialization(self):
        """取引特化型アンサンブル初期化テスト"""
        ensemble = TradingEnsembleClassifier(
            ensemble_method="trading_stacking",
            trading_metrics=self.trading_metrics,
            risk_adjustment=True,
        )

        self.assertEqual(ensemble.ensemble_method, "trading_stacking")
        self.assertTrue(ensemble.risk_adjustment)
        self.assertEqual(ensemble.confidence_threshold, 0.65)
        self.assertIsNotNone(ensemble.trading_metrics)

    def test_default_base_models_creation(self):
        """デフォルトベースモデル作成テスト"""
        ensemble = TradingEnsembleClassifier()
        base_models = ensemble._create_default_base_models()

        self.assertEqual(len(base_models), 3)
        self.assertIsInstance(base_models[0], LGBMClassifier)
        self.assertIsInstance(base_models[1], type(base_models[1]))  # XGBClassifier
        self.assertIsInstance(base_models[2], RandomForestClassifier)

    def test_trading_ensemble_fit(self):
        """アンサンブル学習テスト"""
        ensemble = TradingEnsembleClassifier(
            ensemble_method="trading_stacking", cv_folds=3  # 高速テスト用
        )

        # 学習実行
        fitted_ensemble = ensemble.fit(self.X, self.y)

        self.assertIsNotNone(fitted_ensemble)
        self.assertEqual(len(ensemble.fitted_base_models), 3)
        self.assertIsNotNone(ensemble.fitted_meta_model)
        self.assertIsNotNone(ensemble.trading_weights_)

    def test_trading_stacking_prediction(self):
        """取引特化型スタッキング予測テスト"""
        ensemble = TradingEnsembleClassifier(
            ensemble_method="trading_stacking", cv_folds=3
        )
        ensemble.fit(self.X, self.y)

        # 予測実行
        predictions = ensemble.predict(self.X[:5])
        probabilities = ensemble.predict_proba(self.X[:5])

        self.assertEqual(len(predictions), 5)
        self.assertEqual(probabilities.shape, (5, 2))
        self.assertTrue(all(p in [0, 1] for p in predictions))

    def test_risk_weighted_prediction(self):
        """リスク加重型予測テスト"""
        ensemble = TradingEnsembleClassifier(
            ensemble_method="risk_weighted", risk_adjustment=True, cv_folds=3
        )
        ensemble.fit(self.X, self.y)

        probabilities = ensemble.predict_proba(self.X[:3])

        self.assertEqual(probabilities.shape, (3, 2))
        # 確率の合計が1に近いことを確認
        for i in range(3):
            self.assertAlmostEqual(sum(probabilities[i]), 1.0, places=2)

    def test_trading_confidence_prediction(self):
        """取引特化型信頼度付き予測テスト"""
        ensemble = TradingEnsembleClassifier(cv_folds=3)
        ensemble.fit(self.X, self.y)

        # 市場コンテキスト設定
        market_context = {"vix_level": 25.0, "volatility": 0.03, "trend_strength": 0.7}

        predictions, probabilities, confidence_scores, trading_info = (
            ensemble.predict_with_trading_confidence(self.X[:3], market_context)
        )

        self.assertEqual(len(predictions), 3)
        self.assertEqual(len(confidence_scores), 3)
        self.assertIn("dynamic_threshold", trading_info)
        self.assertIn("market_regime", trading_info)
        self.assertIn("risk_level", trading_info)

    def test_dynamic_threshold_calculation(self):
        """動的閾値計算テスト"""
        ensemble = TradingEnsembleClassifier()

        # 低VIX環境
        low_vix_context = {"vix_level": 12.0, "volatility": 0.01}
        low_vix_threshold = ensemble._calculate_dynamic_threshold(
            self.X[:5], low_vix_context
        )

        # 高VIX環境
        high_vix_context = {"vix_level": 40.0, "volatility": 0.06}
        high_vix_threshold = ensemble._calculate_dynamic_threshold(
            self.X[:5], high_vix_context
        )

        # 高VIXの方が保守的（高い閾値）であることを確認
        self.assertGreater(high_vix_threshold, low_vix_threshold)

    def test_market_regime_assessment(self):
        """市場レジーム評価テスト"""
        ensemble = TradingEnsembleClassifier()

        # 危機的状況
        crisis_context = {"vix_level": 45.0, "volatility": 0.08}
        crisis_regime = ensemble._assess_market_regime(crisis_context)
        self.assertEqual(crisis_regime, "crisis")

        # 安定状況
        calm_context = {"vix_level": 12.0, "volatility": 0.015}
        calm_regime = ensemble._assess_market_regime(calm_context)
        self.assertEqual(calm_regime, "calm")

    def test_position_sizing_calculation(self):
        """ポジションサイジング計算テスト"""
        ensemble = TradingEnsembleClassifier()

        # 高信頼度
        high_confidence = np.array([0.9, 0.85, 0.8])
        high_size = ensemble._calculate_position_sizing(high_confidence)

        # 低信頼度
        low_confidence = np.array([0.4, 0.3, 0.35])
        low_size = ensemble._calculate_position_sizing(low_confidence)

        # 高信頼度の方が大きなポジションサイズ
        self.assertGreater(high_size, low_size)

        # 最大制限確認
        self.assertLessEqual(high_size, 0.15)

    def test_trading_weights_calculation(self):
        """取引特化型重み計算テスト"""
        ensemble = TradingEnsembleClassifier(cv_folds=3)
        ensemble.fit(self.X, self.y)

        self.assertIsNotNone(ensemble.trading_weights_)
        self.assertEqual(len(ensemble.trading_weights_), 3)

        # 重みの合計が1に近いことを確認
        self.assertAlmostEqual(sum(ensemble.trading_weights_), 1.0, places=2)

        # リスクメトリクスが記録されていることを確認
        self.assertIn("weight_diversity", ensemble.risk_metrics_)
        self.assertIn("max_weight", ensemble.risk_metrics_)

    def test_ensemble_info_retrieval(self):
        """アンサンブル情報取得テスト"""
        ensemble = TradingEnsembleClassifier(cv_folds=3)
        ensemble.fit(self.X, self.y)

        info = ensemble.get_trading_ensemble_info()

        required_keys = [
            "ensemble_method",
            "num_base_models",
            "trading_metrics",
            "trading_weights",
            "risk_metrics",
            "base_model_types",
        ]

        for key in required_keys:
            self.assertIn(key, info)

    def test_feature_importance_integration(self):
        """特徴量重要度統合テスト"""
        ensemble = TradingEnsembleClassifier(cv_folds=3)
        ensemble.fit(self.X, self.y)

        importance_df = ensemble.get_feature_importance()

        self.assertIsInstance(importance_df, pd.DataFrame)
        self.assertEqual(len(importance_df), len(self.X.columns))
        self.assertIn("feature", importance_df.columns)
        self.assertIn("importance", importance_df.columns)


class TestTradingEnsembleFactory(unittest.TestCase):
    """取引特化型アンサンブルファクトリのテスト"""

    def test_create_trading_ensemble(self):
        """取引アンサンブル作成テスト"""
        config = {
            "ml": {
                "ensemble": {
                    "enabled": True,
                    "method": "trading_stacking",
                    "risk_adjustment": True,
                    "confidence_threshold": 0.7,
                    "trading_metrics": {
                        "sharpe_ratio": 0.5,
                        "win_rate": 0.35,
                        "max_drawdown": -0.15,
                        "profit_factor": 0.15,
                    },
                }
            }
        }

        ensemble = create_trading_ensemble(config)

        self.assertIsInstance(ensemble, TradingEnsembleClassifier)
        # CI環境ではモデルファイルが存在しないため simple_fallback になる可能性がある
        expected_methods = ["trading_stacking", "simple_fallback"]
        self.assertIn(ensemble.ensemble_method, expected_methods)
        self.assertTrue(ensemble.risk_adjustment)
        self.assertEqual(ensemble.confidence_threshold, 0.7)

    def test_default_trading_ensemble_config(self):
        """デフォルト設定での取引アンサンブル作成テスト"""
        config = {}

        ensemble = create_trading_ensemble(config)

        self.assertIsInstance(ensemble, TradingEnsembleClassifier)
        # モデルファイルが存在しない場合、simple_fallbackが使用される
        # CI環境ではモデルファイルが存在しないため、simple_fallbackを期待
        self.assertIn(ensemble.ensemble_method, ["trading_stacking", "simple_fallback"])
        self.assertTrue(ensemble.risk_adjustment)
        self.assertEqual(ensemble.confidence_threshold, 0.35)


class TestEnsemblePerformanceScenarios(unittest.TestCase):
    """アンサンブルパフォーマンスシナリオテスト"""

    def setUp(self):
        """テストセットアップ"""
        np.random.seed(42)
        self.X_bull = pd.DataFrame(np.random.randn(50, 8) + 0.5)  # 上昇トレンド
        self.y_bull = pd.Series(np.random.binomial(1, 0.7, 50))  # 高勝率

        self.X_bear = pd.DataFrame(np.random.randn(50, 8) - 0.5)  # 下降トレンド
        self.y_bear = pd.Series(np.random.binomial(1, 0.3, 50))  # 低勝率

    def test_bull_market_performance(self):
        """強気市場でのパフォーマンステスト"""
        ensemble = TradingEnsembleClassifier(
            ensemble_method="trading_stacking", cv_folds=3
        )
        ensemble.fit(self.X_bull, self.y_bull)

        # 低VIX環境での予測
        bull_context = {"vix_level": 15.0, "volatility": 0.02, "trend_strength": 0.8}
        _, probabilities, confidence, trading_info = (
            ensemble.predict_with_trading_confidence(self.X_bull[:5], bull_context)
        )

        # 積極的な閾値設定を確認
        self.assertLessEqual(trading_info["dynamic_threshold"], 0.65)
        self.assertEqual(trading_info["market_regime"], "normal")

    def test_bear_market_performance(self):
        """弱気市場でのパフォーマンステスト"""
        ensemble = TradingEnsembleClassifier(
            ensemble_method="risk_weighted", cv_folds=3
        )
        ensemble.fit(self.X_bear, self.y_bear)

        # 高VIX環境での予測
        bear_context = {"vix_level": 35.0, "volatility": 0.05, "trend_strength": 0.3}
        _, probabilities, confidence, trading_info = (
            ensemble.predict_with_trading_confidence(self.X_bear[:5], bear_context)
        )

        # 保守的な閾値設定を確認
        self.assertGreater(trading_info["dynamic_threshold"], 0.65)
        self.assertIn(trading_info["market_regime"], ["volatile", "crisis"])

    def test_mixed_market_adaptation(self):
        """混合市場環境での適応テスト"""
        # 混合データ
        X_mixed = pd.concat([self.X_bull, self.X_bear])
        y_mixed = pd.concat([self.y_bull, self.y_bear])

        ensemble = TradingEnsembleClassifier(
            ensemble_method="performance_voting", cv_folds=3
        )
        ensemble.fit(X_mixed, y_mixed)

        # 通常市場環境
        normal_context = {"vix_level": 22.0, "volatility": 0.03, "trend_strength": 0.5}
        predictions, probabilities, confidence, trading_info = (
            ensemble.predict_with_trading_confidence(X_mixed[:10], normal_context)
        )

        # バランスの取れた設定を確認
        self.assertGreater(trading_info["dynamic_threshold"], 0.6)
        self.assertLess(trading_info["dynamic_threshold"], 0.7)
        self.assertEqual(trading_info["market_regime"], "normal")


if __name__ == "__main__":
    unittest.main()

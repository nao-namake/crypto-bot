#!/usr/bin/env python3
"""
A/Bテストシステム テスト

戦略・モデル性能比較のA/Bテスト機能テスト
"""

import unittest

import numpy as np

from crypto_bot.validation.ab_testing_system import (
    ABTestFramework,
    MetricType,
    StatisticalTest,
    TestResult,
)


class TestABTestingSystem(unittest.TestCase):
    """A/Bテストシステム テスト"""

    def setUp(self):
        """テスト用設定"""
        self.config = {
            "ab_testing": {
                "confidence_level": 0.95,
                "minimum_sample_size": 100,
                "test_duration_days": 7,
            }
        }

        self.ab_framework = ABTestFramework(self.config)

        # サンプルデータ生成
        np.random.seed(42)
        self.sample_size = 200

        # グループA（従来戦略）
        self.group_a_returns = np.random.normal(0.02, 0.1, self.sample_size)

        # グループB（新戦略 - わずかに良い性能）
        self.group_b_returns = np.random.normal(0.025, 0.095, self.sample_size)

    def test_ab_framework_initialization(self):
        """A/Bテストフレームワーク初期化テスト"""
        framework = ABTestFramework(self.config)

        self.assertIsNotNone(framework.config)
        self.assertEqual(framework.confidence_level, 0.95)
        self.assertEqual(framework.minimum_sample_size, 100)

    def test_create_ab_test(self):
        """A/Bテスト作成テスト"""
        test_id = self.ab_framework.create_test(
            name="Strategy Comparison",
            description="Compare old vs new ML strategy",
            metric_type=MetricType.RETURNS,
            allocation_ratio=0.5,
        )

        self.assertIsNotNone(test_id)
        self.assertIsInstance(test_id, str)
        self.assertTrue(len(test_id) > 10)  # UUID形式

    def test_sample_size_calculation(self):
        """サンプルサイズ計算テスト"""
        # 効果サイズ5%、検出力80%での必要サンプル数
        required_samples = self.ab_framework.calculate_sample_size(
            effect_size=0.05, power=0.8, alpha=0.05
        )

        self.assertIsInstance(required_samples, int)
        self.assertGreater(required_samples, 0)
        self.assertLess(required_samples, 10000)  # 現実的な範囲

    def test_statistical_significance_test(self):
        """統計的有意性検定テスト"""
        # t検定
        result = self.ab_framework.run_statistical_test(
            group_a=self.group_a_returns,
            group_b=self.group_b_returns,
            test_type=StatisticalTest.T_TEST,
        )

        self.assertIsInstance(result, dict)
        self.assertIn("statistic", result)
        self.assertIn("p_value", result)
        self.assertIn("significant", result)

        # p値は0-1の範囲
        self.assertGreaterEqual(result["p_value"], 0)
        self.assertLessEqual(result["p_value"], 1)

    def test_mann_whitney_test(self):
        """マン・ホイットニーU検定テスト"""
        result = self.ab_framework.run_statistical_test(
            group_a=self.group_a_returns,
            group_b=self.group_b_returns,
            test_type=StatisticalTest.MANN_WHITNEY,
        )

        self.assertIsInstance(result, dict)
        self.assertIn("statistic", result)
        self.assertIn("p_value", result)
        self.assertIn("significant", result)

    def test_effect_size_calculation(self):
        """効果サイズ計算テスト"""
        effect_size = self.ab_framework.calculate_effect_size(
            group_a=self.group_a_returns, group_b=self.group_b_returns
        )

        self.assertIsInstance(effect_size, float)
        self.assertTrue(np.isfinite(effect_size))

    def test_confidence_interval(self):
        """信頼区間計算テスト"""
        ci = self.ab_framework.calculate_confidence_interval(
            data=self.group_a_returns, confidence_level=0.95
        )

        self.assertIsInstance(ci, tuple)
        self.assertEqual(len(ci), 2)

        lower, upper = ci
        self.assertLess(lower, upper)
        self.assertTrue(np.isfinite(lower))
        self.assertTrue(np.isfinite(upper))

    def test_metric_calculation(self):
        """メトリクス計算テスト"""
        # リターン系メトリクス
        returns_metrics = self.ab_framework.calculate_metrics(
            data=self.group_a_returns, metric_type=MetricType.RETURNS
        )

        expected_keys = ["mean", "std", "sharpe_ratio", "max_drawdown", "win_rate"]
        for key in expected_keys:
            self.assertIn(key, returns_metrics)
            self.assertTrue(np.isfinite(returns_metrics[key]))

    def test_conversion_rate_metrics(self):
        """コンバージョン率メトリクステスト"""
        # バイナリデータ（成功/失敗）
        binary_data = np.random.binomial(1, 0.3, self.sample_size)

        conversion_metrics = self.ab_framework.calculate_metrics(
            data=binary_data, metric_type=MetricType.CONVERSION_RATE
        )

        self.assertIn("conversion_rate", conversion_metrics)
        self.assertIn("confidence_interval", conversion_metrics)

        # コンバージョン率は0-1の範囲
        self.assertGreaterEqual(conversion_metrics["conversion_rate"], 0)
        self.assertLessEqual(conversion_metrics["conversion_rate"], 1)

    def test_test_result_generation(self):
        """テスト結果生成テスト"""
        test_id = "test_123"

        result = self.ab_framework.generate_test_result(
            test_id=test_id,
            group_a_data=self.group_a_returns,
            group_b_data=self.group_b_returns,
            metric_type=MetricType.RETURNS,
        )

        self.assertIsInstance(result, TestResult)
        self.assertEqual(result.test_id, test_id)
        self.assertIn("group_a", result.metrics)
        self.assertIn("group_b", result.metrics)
        self.assertIn("statistical_test", result.results)

    def test_minimum_sample_size_validation(self):
        """最小サンプルサイズ検証テスト"""
        # サンプル数が少ない場合
        small_sample = np.random.normal(0, 1, 50)

        with self.assertRaises(ValueError):
            self.ab_framework.run_statistical_test(
                group_a=small_sample,
                group_b=small_sample,
                test_type=StatisticalTest.T_TEST,
            )

    def test_data_quality_validation(self):
        """データ品質検証テスト"""
        # 異常値を含むデータ
        data_with_outliers = np.concatenate(
            [self.group_a_returns, [100, -100]]  # 極端な異常値
        )

        is_valid = self.ab_framework.validate_data_quality(data_with_outliers)

        # 異常値検出により品質チェックが作動
        self.assertIsInstance(is_valid, bool)

    def test_test_power_calculation(self):
        """検定力計算テスト"""
        power = self.ab_framework.calculate_power(
            effect_size=0.5, sample_size=100, alpha=0.05
        )

        self.assertIsInstance(power, float)
        self.assertGreaterEqual(power, 0)
        self.assertLessEqual(power, 1)

    def test_sequential_testing(self):
        """逐次テスティングテスト"""
        # データを段階的に追加してテスト
        partial_a = self.group_a_returns[:50]
        partial_b = self.group_b_returns[:50]

        early_result = self.ab_framework.check_early_stopping(
            group_a=partial_a, group_b=partial_b, alpha_spending=0.01
        )

        self.assertIn("stop_test", early_result)
        self.assertIn("reason", early_result)
        self.assertIsInstance(early_result["stop_test"], bool)

    def test_multiple_comparison_correction(self):
        """多重比較補正テスト"""
        # 複数のメトリクスでの同時比較
        p_values = [0.01, 0.03, 0.05, 0.08, 0.12]

        corrected_p_values = self.ab_framework.apply_multiple_comparison_correction(
            p_values=p_values, method="bonferroni"
        )

        self.assertEqual(len(corrected_p_values), len(p_values))

        # Bonferroni補正により元のp値以上になる
        for original, corrected in zip(p_values, corrected_p_values):
            self.assertGreaterEqual(corrected, original)

    def test_bayesian_analysis(self):
        """ベイズ分析テスト"""
        bayesian_result = self.ab_framework.run_bayesian_analysis(
            group_a=self.group_a_returns, group_b=self.group_b_returns
        )

        self.assertIn("probability_b_better", bayesian_result)
        self.assertIn("expected_loss", bayesian_result)
        self.assertIn("credible_interval", bayesian_result)

        # 確率は0-1の範囲
        prob = bayesian_result["probability_b_better"]
        self.assertGreaterEqual(prob, 0)
        self.assertLessEqual(prob, 1)

    def test_report_generation(self):
        """レポート生成テスト"""
        test_result = self.ab_framework.generate_test_result(
            test_id="test_report",
            group_a_data=self.group_a_returns,
            group_b_data=self.group_b_returns,
            metric_type=MetricType.RETURNS,
        )

        report = self.ab_framework.generate_report(test_result)

        self.assertIsInstance(report, dict)
        self.assertIn("summary", report)
        self.assertIn("recommendations", report)
        self.assertIn("statistical_details", report)


if __name__ == "__main__":
    unittest.main()

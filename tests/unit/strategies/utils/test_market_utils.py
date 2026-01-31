"""
市場データ分析ユーティリティのテスト

MarketUncertaintyCalculatorクラスのテスト。
市場不確実性計算ロジック（ATR・ボリューム・価格変動率）を検証。
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../"))

from src.strategies.utils.market_utils import MarketUncertaintyCalculator


class TestMarketUncertaintyCalculator(unittest.TestCase):
    """MarketUncertaintyCalculatorのテストクラス."""

    def setUp(self):
        """テスト前準備."""
        # テスト用のデータを作成（20行以上必要: rolling(20)のため）
        self.test_df = self._create_test_dataframe()

        # ロガーをリセット
        MarketUncertaintyCalculator._logger = None

    def _create_test_dataframe(
        self,
        close_values=None,
        atr_values=None,
        volume_values=None,
        num_rows=25,
    ):
        """テスト用DataFrameを作成."""
        if close_values is None:
            close_values = [10000000.0] * num_rows  # 1000万円
        if atr_values is None:
            atr_values = [100000.0] * num_rows  # 10万円（1%相当）
        if volume_values is None:
            volume_values = [100.0] * num_rows

        return pd.DataFrame({
            "close": close_values,
            "atr_14": atr_values,
            "volume": volume_values,
        })

    def _get_mock_threshold(self, key, default):
        """テスト用のget_threshold関数."""
        threshold_values = {
            "dynamic_confidence.market_uncertainty.volatility_factor_max": 0.05,
            "dynamic_confidence.market_uncertainty.volume_factor_max": 0.03,
            "dynamic_confidence.market_uncertainty.volume_multiplier": 0.1,
            "dynamic_confidence.market_uncertainty.price_factor_max": 0.02,
            "dynamic_confidence.market_uncertainty.uncertainty_max": 0.10,
        }
        return threshold_values.get(key, default)

    # ==================== calculate() テスト ====================

    @patch("src.core.config.threshold_manager.get_threshold")
    def test_calculate_normal_case(self, mock_get_threshold):
        """正常系: 基本的な不確実性計算."""
        mock_get_threshold.side_effect = self._get_mock_threshold

        result = MarketUncertaintyCalculator.calculate(self.test_df)

        # 結果が数値であること
        self.assertIsInstance(result, float)
        # 結果が0以上であること
        self.assertGreaterEqual(result, 0.0)
        # 結果が上限以下であること
        self.assertLessEqual(result, 0.10)

    @patch("src.core.config.threshold_manager.get_threshold")
    def test_calculate_volatility_factor(self, mock_get_threshold):
        """ボラティリティ要因の計算テスト."""
        mock_get_threshold.side_effect = self._get_mock_threshold

        # ATRが価格の2%の場合
        df = self._create_test_dataframe(
            close_values=[10000000.0] * 25,
            atr_values=[200000.0] * 25,  # 2%のATR
            volume_values=[100.0] * 25,
        )

        result = MarketUncertaintyCalculator.calculate(df)

        # ボラティリティ要因は min(0.05, 0.02) = 0.02
        # ボリューム・価格要因は微小なので、結果は約0.02前後
        self.assertGreater(result, 0.0)
        self.assertLessEqual(result, 0.10)

    @patch("src.core.config.threshold_manager.get_threshold")
    def test_calculate_volatility_capped(self, mock_get_threshold):
        """ボラティリティ要因の上限制限テスト."""
        mock_get_threshold.side_effect = self._get_mock_threshold

        # ATRが価格の10%（非常に高い）
        df = self._create_test_dataframe(
            close_values=[10000000.0] * 25,
            atr_values=[1000000.0] * 25,  # 10%のATR
            volume_values=[100.0] * 25,
        )

        result = MarketUncertaintyCalculator.calculate(df)

        # 上限0.05でキャップされる
        self.assertLessEqual(result, 0.10)

    @patch("src.core.config.threshold_manager.get_threshold")
    def test_calculate_volume_factor(self, mock_get_threshold):
        """ボリューム要因の計算テスト."""
        mock_get_threshold.side_effect = self._get_mock_threshold

        # 最新ボリュームが平均の2倍
        volumes = [100.0] * 24 + [200.0]  # 最後のボリュームが2倍
        df = self._create_test_dataframe(volume_values=volumes)

        result = MarketUncertaintyCalculator.calculate(df)

        # ボリューム乖離率 |2.0 - 1.0| * 0.1 = 0.1 → min(0.03, 0.1) = 0.03
        self.assertGreater(result, 0.0)
        self.assertLessEqual(result, 0.10)

    @patch("src.core.config.threshold_manager.get_threshold")
    def test_calculate_volume_zero_average(self, mock_get_threshold):
        """ボリューム平均がゼロの場合のテスト."""
        mock_get_threshold.side_effect = self._get_mock_threshold

        # 全てゼロボリューム
        df = self._create_test_dataframe(volume_values=[0.0] * 25)

        result = MarketUncertaintyCalculator.calculate(df)

        # ゼロ除算を回避してvolume_ratio=1.0になる
        self.assertIsInstance(result, float)
        self.assertGreaterEqual(result, 0.0)

    @patch("src.core.config.threshold_manager.get_threshold")
    def test_calculate_price_factor(self, mock_get_threshold):
        """価格変動要因の計算テスト."""
        mock_get_threshold.side_effect = self._get_mock_threshold

        # 最新の価格変動が1%
        close_values = [10000000.0] * 24 + [10100000.0]  # 1%上昇
        df = self._create_test_dataframe(close_values=close_values)

        result = MarketUncertaintyCalculator.calculate(df)

        # 価格変動1% → min(0.02, 0.01) = 0.01
        self.assertGreater(result, 0.0)
        self.assertLessEqual(result, 0.10)

    @patch("src.core.config.threshold_manager.get_threshold")
    def test_calculate_uncertainty_max_cap(self, mock_get_threshold):
        """総合不確実性の上限制限テスト."""
        mock_get_threshold.side_effect = self._get_mock_threshold

        # 全ての要因が最大値になるケース
        volumes = [100.0] * 24 + [500.0]  # 5倍のボリューム
        close_values = [10000000.0] * 24 + [10500000.0]  # 5%上昇
        df = self._create_test_dataframe(
            close_values=close_values,
            atr_values=[1000000.0] * 25,  # 10%のATR
            volume_values=volumes,
        )

        result = MarketUncertaintyCalculator.calculate(df)

        # 総合上限0.10でキャップ
        self.assertLessEqual(result, 0.10)

    def test_calculate_missing_columns(self):
        """必要な列が不足している場合のテスト."""
        # close列がない
        df_no_close = pd.DataFrame({
            "atr_14": [100000.0] * 25,
            "volume": [100.0] * 25,
        })

        result = MarketUncertaintyCalculator.calculate(df_no_close)
        self.assertEqual(result, 0.02)  # デフォルト値

    def test_calculate_missing_atr_column(self):
        """ATR列が不足している場合のテスト."""
        df_no_atr = pd.DataFrame({
            "close": [10000000.0] * 25,
            "volume": [100.0] * 25,
        })

        result = MarketUncertaintyCalculator.calculate(df_no_atr)
        self.assertEqual(result, 0.02)  # デフォルト値

    def test_calculate_missing_volume_column(self):
        """volume列が不足している場合のテスト."""
        df_no_volume = pd.DataFrame({
            "close": [10000000.0] * 25,
            "atr_14": [100000.0] * 25,
        })

        result = MarketUncertaintyCalculator.calculate(df_no_volume)
        self.assertEqual(result, 0.02)  # デフォルト値

    def test_calculate_empty_dataframe(self):
        """空のDataFrameの場合のテスト."""
        empty_df = pd.DataFrame()

        result = MarketUncertaintyCalculator.calculate(empty_df)
        self.assertEqual(result, 0.02)  # デフォルト値

    def test_calculate_single_row_dataframe(self):
        """1行のみのDataFrameの場合のテスト."""
        single_row_df = pd.DataFrame({
            "close": [10000000.0],
            "atr_14": [100000.0],
            "volume": [100.0],
        })

        # rolling(20)の計算でNaNが発生する可能性がある
        result = MarketUncertaintyCalculator.calculate(single_row_df)
        # 結果が数値であること（デフォルト値か計算結果）
        self.assertIsInstance(result, float)
        self.assertGreaterEqual(result, 0.0)

    def test_calculate_with_nan_values(self):
        """NaN値を含むDataFrameの場合のテスト."""
        df_with_nan = self._create_test_dataframe()
        df_with_nan.loc[df_with_nan.index[-1], "atr_14"] = np.nan

        result = MarketUncertaintyCalculator.calculate(df_with_nan)
        # NaNの場合でもfloat()変換でnanになり、計算は続行される可能性がある
        # 結果が数値であること（デフォルト値または計算結果）
        self.assertIsInstance(result, float)
        self.assertGreaterEqual(result, 0.0)

    # ==================== calculate_with_breakdown() テスト ====================

    @patch("src.core.config.threshold_manager.get_threshold")
    def test_calculate_with_breakdown_normal(self, mock_get_threshold):
        """内訳付き計算の正常系テスト."""
        mock_get_threshold.side_effect = self._get_mock_threshold

        result = MarketUncertaintyCalculator.calculate_with_breakdown(self.test_df)

        # 結果が辞書であること
        self.assertIsInstance(result, dict)

        # 必要なキーが含まれていること
        self.assertIn("total", result)
        self.assertIn("volatility", result)
        self.assertIn("volume", result)
        self.assertIn("price", result)

        # 各値が数値であること
        self.assertIsInstance(result["total"], float)
        self.assertIsInstance(result["volatility"], float)
        self.assertIsInstance(result["volume"], float)
        self.assertIsInstance(result["price"], float)

        # 各値が適切な範囲内であること
        self.assertGreaterEqual(result["total"], 0.0)
        self.assertLessEqual(result["total"], 0.10)
        self.assertGreaterEqual(result["volatility"], 0.0)
        self.assertLessEqual(result["volatility"], 0.05)
        self.assertGreaterEqual(result["volume"], 0.0)
        self.assertLessEqual(result["volume"], 0.03)
        self.assertGreaterEqual(result["price"], 0.0)
        self.assertLessEqual(result["price"], 0.02)

    @patch("src.core.config.threshold_manager.get_threshold")
    def test_calculate_with_breakdown_sum_equals_total(self, mock_get_threshold):
        """内訳の合計がtotalと一致するか（上限前）のテスト."""
        def high_limit_threshold(key, default):
            threshold_values = {
                "dynamic_confidence.market_uncertainty.volatility_factor_max": 0.05,
                "dynamic_confidence.market_uncertainty.volume_factor_max": 0.03,
                "dynamic_confidence.market_uncertainty.volume_multiplier": 0.1,
                "dynamic_confidence.market_uncertainty.price_factor_max": 0.02,
                "dynamic_confidence.market_uncertainty.uncertainty_max": 1.00,  # 高い上限
            }
            return threshold_values.get(key, default)

        mock_get_threshold.side_effect = high_limit_threshold

        result = MarketUncertaintyCalculator.calculate_with_breakdown(self.test_df)

        # 内訳の合計がtotalと一致
        expected_sum = result["volatility"] + result["volume"] + result["price"]
        self.assertAlmostEqual(result["total"], expected_sum, places=10)

    @patch("src.core.config.threshold_manager.get_threshold")
    def test_calculate_with_breakdown_high_volatility(self, mock_get_threshold):
        """高ボラティリティ時の内訳テスト."""
        mock_get_threshold.side_effect = self._get_mock_threshold

        # 高ATR（10%）
        df = self._create_test_dataframe(
            atr_values=[1000000.0] * 25,  # 10%のATR
        )

        result = MarketUncertaintyCalculator.calculate_with_breakdown(df)

        # ボラティリティ要因が上限に達していること
        self.assertEqual(result["volatility"], 0.05)

    @patch("src.core.config.threshold_manager.get_threshold")
    def test_calculate_with_breakdown_high_volume_deviation(self, mock_get_threshold):
        """ボリューム乖離が大きい場合の内訳テスト."""
        mock_get_threshold.side_effect = self._get_mock_threshold

        # 最新ボリュームが5倍
        volumes = [100.0] * 24 + [500.0]
        df = self._create_test_dataframe(volume_values=volumes)

        result = MarketUncertaintyCalculator.calculate_with_breakdown(df)

        # ボリューム要因が上限に達していること
        # |5.0 - 1.0| * 0.1 = 0.4 → min(0.03, 0.4) = 0.03
        self.assertEqual(result["volume"], 0.03)

    @patch("src.core.config.threshold_manager.get_threshold")
    def test_calculate_with_breakdown_high_price_change(self, mock_get_threshold):
        """価格変動が大きい場合の内訳テスト."""
        mock_get_threshold.side_effect = self._get_mock_threshold

        # 5%の価格変動
        close_values = [10000000.0] * 24 + [10500000.0]
        df = self._create_test_dataframe(close_values=close_values)

        result = MarketUncertaintyCalculator.calculate_with_breakdown(df)

        # 価格要因が上限に達していること
        # 5%変動 → min(0.02, 0.05) = 0.02
        self.assertEqual(result["price"], 0.02)

    def test_calculate_with_breakdown_error_handling(self):
        """内訳付き計算のエラーハンドリングテスト."""
        empty_df = pd.DataFrame()

        result = MarketUncertaintyCalculator.calculate_with_breakdown(empty_df)

        # デフォルト値が返されること
        self.assertEqual(result["total"], 0.02)
        self.assertEqual(result["volatility"], 0.01)
        self.assertEqual(result["volume"], 0.005)
        self.assertEqual(result["price"], 0.005)

    def test_calculate_with_breakdown_missing_columns(self):
        """必要な列が不足している場合の内訳計算テスト."""
        df_incomplete = pd.DataFrame({
            "close": [10000000.0] * 25,
            # atr_14とvolumeが不足
        })

        result = MarketUncertaintyCalculator.calculate_with_breakdown(df_incomplete)

        # デフォルト値が返されること
        self.assertEqual(result["total"], 0.02)

    # ==================== _get_logger() テスト ====================

    def test_get_logger_lazy_initialization(self):
        """ロガーの遅延初期化テスト."""
        # ロガーをリセット
        MarketUncertaintyCalculator._logger = None

        # 最初の呼び出しでロガーが初期化される
        logger1 = MarketUncertaintyCalculator._get_logger()
        self.assertIsNotNone(logger1)

        # 2回目の呼び出しで同じロガーが返される
        logger2 = MarketUncertaintyCalculator._get_logger()
        self.assertIs(logger1, logger2)

    @patch("src.strategies.utils.market_utils.get_logger")
    def test_get_logger_calls_get_logger_once(self, mock_get_logger):
        """get_loggerが一度だけ呼ばれることのテスト."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger

        # ロガーをリセット
        MarketUncertaintyCalculator._logger = None

        # 複数回呼び出し
        MarketUncertaintyCalculator._get_logger()
        MarketUncertaintyCalculator._get_logger()
        MarketUncertaintyCalculator._get_logger()

        # get_loggerは1回だけ呼ばれる
        mock_get_logger.assert_called_once()

    # ==================== 統合テスト ====================

    @patch("src.core.config.threshold_manager.get_threshold")
    def test_calculate_and_breakdown_consistency(self, mock_get_threshold):
        """calculate()とcalculate_with_breakdown()の一貫性テスト."""
        mock_get_threshold.side_effect = self._get_mock_threshold

        # 両方のメソッドで同じ結果が返されること
        simple_result = MarketUncertaintyCalculator.calculate(self.test_df)
        breakdown_result = MarketUncertaintyCalculator.calculate_with_breakdown(self.test_df)

        self.assertAlmostEqual(simple_result, breakdown_result["total"], places=10)

    @patch("src.core.config.threshold_manager.get_threshold")
    def test_calculate_with_real_world_like_data(self, mock_get_threshold):
        """実際の市場データに近いデータでのテスト."""
        mock_get_threshold.side_effect = self._get_mock_threshold

        # BTC/JPYの実際のデータに近い値
        np.random.seed(42)
        base_price = 10000000.0  # 1000万円
        close_values = [base_price + np.random.normal(0, 50000) for _ in range(25)]
        atr_values = [abs(np.random.normal(100000, 10000)) for _ in range(25)]
        volume_values = [abs(np.random.normal(100, 20)) for _ in range(25)]

        df = pd.DataFrame({
            "close": close_values,
            "atr_14": atr_values,
            "volume": volume_values,
        })

        result = MarketUncertaintyCalculator.calculate(df)

        # 結果が妥当な範囲内であること
        self.assertIsInstance(result, float)
        self.assertGreaterEqual(result, 0.0)
        self.assertLessEqual(result, 0.10)

    @patch("src.core.config.threshold_manager.get_threshold")
    def test_calculate_negative_price_change(self, mock_get_threshold):
        """価格が下落した場合のテスト."""
        mock_get_threshold.side_effect = self._get_mock_threshold

        # 2%の価格下落
        close_values = [10000000.0] * 24 + [9800000.0]
        df = self._create_test_dataframe(close_values=close_values)

        result = MarketUncertaintyCalculator.calculate(df)

        # 絶対値を使うので正の値が返される
        self.assertGreater(result, 0.0)
        self.assertLessEqual(result, 0.10)

    @patch("src.core.config.threshold_manager.get_threshold")
    def test_calculate_volume_below_average(self, mock_get_threshold):
        """ボリュームが平均以下の場合のテスト."""
        mock_get_threshold.side_effect = self._get_mock_threshold

        # 最新ボリュームが平均の半分
        volumes = [100.0] * 24 + [50.0]
        df = self._create_test_dataframe(volume_values=volumes)

        result = MarketUncertaintyCalculator.calculate(df)

        # 乖離率 |0.5 - 1.0| * 0.1 = 0.05 → min(0.03, 0.05) = 0.03
        self.assertGreater(result, 0.0)
        self.assertLessEqual(result, 0.10)


class TestMarketUncertaintyCalculatorEdgeCases(unittest.TestCase):
    """MarketUncertaintyCalculatorのエッジケーステスト."""

    def setUp(self):
        """テスト前準備."""
        MarketUncertaintyCalculator._logger = None

    def _get_mock_threshold(self, key, default):
        """テスト用のget_threshold関数."""
        threshold_values = {
            "dynamic_confidence.market_uncertainty.volatility_factor_max": 0.05,
            "dynamic_confidence.market_uncertainty.volume_factor_max": 0.03,
            "dynamic_confidence.market_uncertainty.volume_multiplier": 0.1,
            "dynamic_confidence.market_uncertainty.price_factor_max": 0.02,
            "dynamic_confidence.market_uncertainty.uncertainty_max": 0.10,
        }
        return threshold_values.get(key, default)

    def test_calculate_with_inf_values(self):
        """無限大の値を含むDataFrameのテスト."""
        df = pd.DataFrame({
            "close": [10000000.0] * 25,
            "atr_14": [float("inf")] * 25,
            "volume": [100.0] * 25,
        })

        result = MarketUncertaintyCalculator.calculate(df)
        # 無限大の場合、volatility_factor = inf / price = inf
        # min(0.05, inf) = 0.05 となり、計算が続行される
        self.assertIsInstance(result, float)
        self.assertGreaterEqual(result, 0.0)

    def test_calculate_with_negative_atr(self):
        """負のATR値のテスト（異常データ）."""
        df = pd.DataFrame({
            "close": [10000000.0] * 25,
            "atr_14": [-100000.0] * 25,
            "volume": [100.0] * 25,
        })

        # 負のATRでも計算は続行される（ボラティリティは負になる可能性）
        result = MarketUncertaintyCalculator.calculate(df)
        self.assertIsInstance(result, float)

    def test_calculate_with_zero_price(self):
        """価格がゼロの場合のテスト."""
        df = pd.DataFrame({
            "close": [0.0] * 25,
            "atr_14": [100000.0] * 25,
            "volume": [100.0] * 25,
        })

        result = MarketUncertaintyCalculator.calculate(df)
        # ゼロ除算でエラー→デフォルト値
        self.assertEqual(result, 0.02)

    @patch("src.core.config.threshold_manager.get_threshold")
    def test_calculate_with_very_small_values(self, mock_get_threshold):
        """非常に小さい値でのテスト."""
        mock_get_threshold.side_effect = self._get_mock_threshold

        df = pd.DataFrame({
            "close": [1e-10] * 25,
            "atr_14": [1e-12] * 25,
            "volume": [1e-10] * 25,
        })

        result = MarketUncertaintyCalculator.calculate(df)
        self.assertIsInstance(result, float)

    @patch("src.core.config.threshold_manager.get_threshold")
    def test_calculate_with_constant_values(self, mock_get_threshold):
        """全て同じ値のDataFrameでのテスト."""
        mock_get_threshold.side_effect = self._get_mock_threshold

        # 全て同じ値（価格変動なし、ボリューム乖離なし）
        df = pd.DataFrame({
            "close": [10000000.0] * 25,
            "atr_14": [100000.0] * 25,
            "volume": [100.0] * 25,
        })

        result = MarketUncertaintyCalculator.calculate(df)

        # 価格変動0、ボリューム乖離0、ATR/価格=0.01
        # 結果は約0.01（ボラティリティ要因のみ）
        self.assertGreaterEqual(result, 0.0)
        self.assertLess(result, 0.05)  # ボラティリティ要因のみなので低い値

    @patch("src.core.config.threshold_manager.get_threshold")
    def test_calculate_with_large_volume_spike(self, mock_get_threshold):
        """大きなボリュームスパイクのテスト."""
        mock_get_threshold.side_effect = self._get_mock_threshold

        # 最新ボリュームが10倍
        volumes = [100.0] * 24 + [1000.0]
        df = pd.DataFrame({
            "close": [10000000.0] * 25,
            "atr_14": [100000.0] * 25,
            "volume": volumes,
        })

        result = MarketUncertaintyCalculator.calculate(df)

        # ボリューム要因は上限でキャップされる
        self.assertGreater(result, 0.0)
        self.assertLessEqual(result, 0.10)

    @patch("src.core.config.threshold_manager.get_threshold")
    def test_calculate_with_price_crash(self, mock_get_threshold):
        """価格が大幅に下落した場合のテスト."""
        mock_get_threshold.side_effect = self._get_mock_threshold

        # 10%の価格下落
        close_values = [10000000.0] * 24 + [9000000.0]
        df = pd.DataFrame({
            "close": close_values,
            "atr_14": [100000.0] * 25,
            "volume": [100.0] * 25,
        })

        result = MarketUncertaintyCalculator.calculate(df)

        # 価格要因は上限0.02でキャップされる
        self.assertGreater(result, 0.0)
        self.assertLessEqual(result, 0.10)

    @patch("src.core.config.threshold_manager.get_threshold")
    def test_calculate_breakdown_with_extreme_values(self, mock_get_threshold):
        """全ての要因が極端な値の場合の内訳テスト."""
        mock_get_threshold.side_effect = self._get_mock_threshold

        # 全ての要因が極端
        volumes = [100.0] * 24 + [1000.0]  # 10倍のボリューム
        close_values = [10000000.0] * 24 + [11000000.0]  # 10%上昇
        df = pd.DataFrame({
            "close": close_values,
            "atr_14": [1000000.0] * 25,  # 10%のATR
            "volume": volumes,
        })

        result = MarketUncertaintyCalculator.calculate_with_breakdown(df)

        # 各要因が上限でキャップされていること
        self.assertEqual(result["volatility"], 0.05)
        self.assertEqual(result["volume"], 0.03)
        self.assertEqual(result["price"], 0.02)
        self.assertEqual(result["total"], 0.10)  # 総合上限でキャップ

    def test_calculate_with_insufficient_data_for_rolling(self):
        """rollingに必要なデータが不足している場合のテスト."""
        # 19行（rolling(20)に足りない）
        df = pd.DataFrame({
            "close": [10000000.0] * 19,
            "atr_14": [100000.0] * 19,
            "volume": [100.0] * 19,
        })

        result = MarketUncertaintyCalculator.calculate(df)
        # rolling(20)でNaNになるが、avg_volume > 0の条件で1.0が使用される
        # 結果が数値であること
        self.assertIsInstance(result, float)
        self.assertGreaterEqual(result, 0.0)


def run_market_utils_tests():
    """市場ユーティリティテスト実行関数."""
    print("=" * 50)
    print("市場データ分析ユーティリティ テスト開始")
    print("=" * 50)

    unittest.main(verbosity=2, exit=False)

    print("\n" + "=" * 50)
    print("市場データ分析ユーティリティ テスト完了")
    print("=" * 50)


if __name__ == "__main__":
    run_market_utils_tests()

#!/usr/bin/env python3
"""
Phase 16.3-A 分割システム: FeatureEngineer テスト

preprocessing分割システムの特徴量エンジニアリングテスト
"""

import unittest

import numpy as np
import pandas as pd

from crypto_bot.ml.preprocessing.feature_engineer import FeatureEngineer

# from unittest.mock import MagicMock, patch  # unused


class TestFeatureEngineer(unittest.TestCase):
    """FeatureEngineer テスト"""

    def setUp(self):
        """テスト用データ準備"""
        # テスト用設定
        self.config = {
            "ml": {
                "features": {
                    "extra_features": [
                        "ema_5",
                        "ema_10",
                        "rsi_14",
                        "bb_upper",
                        "bb_lower",
                        "volume_sma_20",
                        "atr",
                        "returns_1",
                    ]
                }
            }
        }

        self.engineer = FeatureEngineer(self.config)

        # テスト用OHLCV データ
        dates = pd.date_range("2024-01-01", periods=100, freq="1H")
        np.random.seed(42)
        base_price = 5000000

        self.df = pd.DataFrame(
            {
                "timestamp": dates,
                "open": base_price + np.random.normal(0, 50000, 100),
                "high": base_price + np.random.normal(25000, 50000, 100),
                "low": base_price - np.random.normal(25000, 50000, 100),
                "close": base_price + np.random.normal(0, 50000, 100),
                "volume": np.random.uniform(10, 100, 100),
            }
        )

        # 価格が正の値になるように調整
        self.df[["open", "high", "low", "close"]] = np.abs(
            self.df[["open", "high", "low", "close"]]
        )

    def test_engineer_initialization(self):
        """FeatureEngineer初期化テスト"""
        engineer = FeatureEngineer(self.config)

        self.assertIsNotNone(engineer.config)
        self.assertIn("ml", engineer.config)

    def test_basic_feature_engineering(self):
        """基本特徴量エンジニアリングテスト"""
        result = self.engineer.engineer_features(self.df)

        # 基本OHLCVカラムが保持されていること
        for col in ["open", "high", "low", "close", "volume"]:
            self.assertIn(col, result.columns)

        # データサイズが変わらないこと
        self.assertEqual(len(result), len(self.df))

        # タイムスタンプカラムが保持されていること
        self.assertIn("timestamp", result.columns)

    def test_extra_features_generation(self):
        """追加特徴量生成テスト"""
        # VWAPを追加（一部特徴量で必要）
        enhanced_df = self.df.copy()
        enhanced_df["vwap"] = enhanced_df["close"] * 1.001

        result = self.engineer.engineer_features(enhanced_df)

        # 設定で指定した追加特徴量が生成されていることを確認
        expected_features = self.config["ml"]["features"]["extra_features"]

        for feature in expected_features:
            if feature in result.columns:  # 生成できる特徴量のみチェック
                values = result[feature].dropna()
                if len(values) > 0:
                    # 数値であることを確認
                    self.assertTrue(
                        np.isfinite(values).all(),
                        f"{feature} に非有限値が含まれています",
                    )

    def test_missing_value_handling(self):
        """欠損値処理テスト"""
        # 欠損値を含むデータを作成
        df_with_missing = self.df.copy()
        df_with_missing.loc[0:5, "close"] = np.nan

        result = self.engineer.engineer_features(df_with_missing)

        # 結果にNaNが適切に処理されているかを確認
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), len(df_with_missing))

    def test_feature_scaling_options(self):
        """特徴量スケーリングオプションテスト"""
        # スケーリング設定を追加
        config_with_scaling = self.config.copy()
        config_with_scaling["ml"]["preprocessing"] = {
            "scaling": {"enabled": True, "method": "standard"}
        }

        engineer = FeatureEngineer(config_with_scaling)
        result = engineer.engineer_features(self.df)

        # スケーリングが適用されてもデータ構造は保持される
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), len(self.df))

    def test_feature_validation(self):
        """特徴量検証テスト"""
        result = self.engineer.engineer_features(self.df)

        # すべてのカラムが数値型または日時型であること
        for col in result.columns:
            if col != "timestamp":
                if col in result.columns:
                    dtype = result[col].dtype
                    self.assertTrue(
                        pd.api.types.is_numeric_dtype(dtype)
                        or pd.api.types.is_datetime64_any_dtype(dtype),
                        f"カラム {col} が適切な型ではありません: {dtype}",
                    )

    def test_empty_dataframe_handling(self):
        """空のDataFrame処理テスト"""
        empty_df = pd.DataFrame()

        # エラーが発生しないか、適切にハンドリングされることを確認
        try:
            result = self.engineer.engineer_features(empty_df)
            # 空のDataFrameが返される、またはエラー処理される
            self.assertIsInstance(result, pd.DataFrame)
        except ValueError:
            # 適切なエラーメッセージでのValueErrorは許容
            pass

    def test_minimal_data_handling(self):
        """最小限データ処理テスト"""
        # 最小限のデータ（1行のみ）
        minimal_df = self.df.iloc[:1].copy()

        result = self.engineer.engineer_features(minimal_df)

        # 最低限のデータでも処理が完了すること
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1)

    def test_large_dataset_performance(self):
        """大規模データセット性能テスト"""
        # より大きなデータセット（1000行）
        dates = pd.date_range("2024-01-01", periods=1000, freq="1H")
        large_df = pd.DataFrame(
            {
                "timestamp": dates,
                "open": np.random.uniform(4000000, 6000000, 1000),
                "high": np.random.uniform(4000000, 6000000, 1000),
                "low": np.random.uniform(4000000, 6000000, 1000),
                "close": np.random.uniform(4000000, 6000000, 1000),
                "volume": np.random.uniform(10, 100, 1000),
            }
        )

        # 処理時間の測定は行わないが、正常に完了することを確認
        result = self.engineer.engineer_features(large_df)

        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1000)

    def test_configuration_override(self):
        """設定オーバーライドテスト"""
        # 異なる設定でFeatureEngineerを初期化
        custom_config = {
            "ml": {
                "features": {
                    "extra_features": ["ema_20", "rsi_7"]  # 異なる特徴量セット
                }
            }
        }

        custom_engineer = FeatureEngineer(custom_config)
        result = custom_engineer.engineer_features(self.df)

        # カスタム設定が適用されることを確認
        self.assertIsInstance(result, pd.DataFrame)

    def test_backward_compatibility(self):
        """後方互換性テスト"""
        # 古い形式の設定でも動作することを確認
        legacy_config = {
            "features": {"technical_indicators": True, "market_features": True}
        }

        try:
            legacy_engineer = FeatureEngineer(legacy_config)
            result = legacy_engineer.engineer_features(self.df)
            self.assertIsInstance(result, pd.DataFrame)
        except (KeyError, ValueError):
            # 古い設定形式は適切にエラーハンドリングされる
            pass


if __name__ == "__main__":
    unittest.main()

"""
Phase H.17: 特徴量順序一貫性テスト
学習→保存→読込→予測の全工程で特徴量順序が一致することを検証
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

# プロジェクトルートをPYTHONPATHに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto_bot.ml.feature_order_manager import (  # noqa: E402
    FeatureOrderManager,
    get_feature_order_manager,
)
from crypto_bot.ml.timeframe_ensemble import TimeframeEnsembleProcessor  # noqa: E402


class TestFeatureConsistency(unittest.TestCase):
    """特徴量順序一貫性テストクラス"""

    def setUp(self):
        """テスト前の準備"""
        self.test_config = {
            "ml": {
                "ensemble": {
                    "enabled": True,
                    "method": "trading_stacking",
                    "confidence_threshold": 0.65,
                }
            }
        }

        # テスト用の一時ファイル作成
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_file.close()

    def tearDown(self):
        """テスト後のクリーンアップ"""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    def test_feature_order_manager_basic(self):
        """FeatureOrderManagerの基本機能テスト"""
        manager = FeatureOrderManager(self.temp_file.name)

        # テスト用特徴量リスト
        test_features = [
            "feature_3",
            "feature_1",
            "feature_2",
            "feature_5",
            "feature_4",
        ]

        # 特徴量順序を保存
        manager.save_feature_order(test_features)

        # 新しいマネージャーインスタンスで読み込み
        new_manager = FeatureOrderManager(self.temp_file.name)

        # 保存された順序が読み込まれることを確認
        self.assertIsNotNone(new_manager.stored_order)
        self.assertEqual(new_manager.stored_order, test_features)

    def test_feature_order_alignment(self):
        """特徴量順序のアライメントテスト"""
        manager = FeatureOrderManager(self.temp_file.name)

        # 学習時の特徴量順序
        train_features = ["close", "volume", "rsi", "macd", "bb_upper"]
        manager.save_feature_order(train_features)

        # 予測時の特徴量（順序が異なる）
        predict_features = ["macd", "close", "bb_upper", "volume", "rsi"]

        # 順序を整合
        aligned_features = manager.get_consistent_order(predict_features)

        # 学習時と同じ順序になることを確認
        self.assertEqual(aligned_features, train_features)

    def test_feature_order_with_missing_features(self):
        """不足特徴量がある場合のテスト"""
        manager = FeatureOrderManager(self.temp_file.name)

        # 学習時の特徴量
        train_features = ["close", "volume", "rsi", "macd", "bb_upper"]
        manager.save_feature_order(train_features)

        # 予測時の特徴量（'macd'が不足）
        predict_features = ["close", "volume", "rsi", "bb_upper"]

        # 順序を整合
        aligned_features = manager.get_consistent_order(predict_features)

        # 存在する特徴量のみが含まれることを確認
        self.assertEqual(len(aligned_features), 4)
        self.assertNotIn("macd", aligned_features)

    def test_feature_order_with_extra_features(self):
        """追加特徴量がある場合のテスト"""
        manager = FeatureOrderManager(self.temp_file.name)

        # 学習時の特徴量
        train_features = ["close", "volume", "rsi"]
        manager.save_feature_order(train_features)

        # 予測時の特徴量（'macd', 'bb_upper'が追加）
        predict_features = ["close", "volume", "rsi", "macd", "bb_upper"]

        # 順序を整合
        aligned_features = manager.get_consistent_order(predict_features)

        # 元の順序＋新しい特徴量が追加されることを確認
        self.assertEqual(len(aligned_features), 5)
        self.assertEqual(aligned_features[:3], train_features)
        self.assertIn("macd", aligned_features[3:])
        self.assertIn("bb_upper", aligned_features[3:])

    def test_dataframe_column_order(self):
        """DataFrameの列順序調整テスト"""
        manager = FeatureOrderManager(self.temp_file.name)

        # 学習時の特徴量順序を保存
        train_features = ["close", "volume", "rsi", "macd"]
        manager.save_feature_order(train_features)

        # 予測時のDataFrame（列順序が異なる）
        df_data = {
            "macd": [0.1, 0.2, 0.3],
            "close": [100, 101, 102],
            "rsi": [50, 51, 52],
            "volume": [1000, 1100, 1200],
        }
        df = pd.DataFrame(df_data)

        # 列順序を調整
        aligned_df = manager.ensure_column_order(df)

        # 列順序が正しいことを確認
        self.assertEqual(list(aligned_df.columns), train_features)

        # データの整合性を確認
        self.assertTrue((aligned_df["close"] == df["close"]).all())
        self.assertTrue((aligned_df["volume"] == df["volume"]).all())

    @patch("crypto_bot.ml.ensemble.create_trading_ensemble")
    @patch("crypto_bot.ml.preprocessor.FeatureEngineer")
    def test_timeframe_ensemble_processor_integration(
        self, mock_feature_engineer, mock_create_ensemble
    ):
        """TimeframeEnsembleProcessorとの統合テスト"""
        # モックの設定
        mock_ensemble = MagicMock()
        mock_create_ensemble.return_value = mock_ensemble

        mock_fe = MagicMock()
        mock_feature_engineer.return_value = mock_fe

        # テスト用の特徴量データ
        feature_columns = ["close", "volume", "rsi", "macd", "bb_upper"]
        feature_data = pd.DataFrame(
            np.random.randn(100, 5),
            columns=feature_columns,
            index=pd.date_range("2025-01-01", periods=100, freq="H"),
        )

        mock_fe.transform.return_value = feature_data

        # プロセッサー初期化
        processor = TimeframeEnsembleProcessor("1h", self.test_config)

        # モデル学習
        price_df = pd.DataFrame(
            {
                "open": np.random.randn(100),
                "high": np.random.randn(100),
                "low": np.random.randn(100),
                "close": np.random.randn(100),
                "volume": np.random.randn(100),
            },
            index=pd.date_range("2025-01-01", periods=100, freq="H"),
        )

        y = pd.Series(np.random.randint(0, 2, 100), index=price_df.index)

        # 学習実行
        processor.fit(price_df, y)

        # 特徴量順序が保存されたことを確認
        self.assertTrue(os.path.exists("feature_order.json"))

        # 予測時に異なる順序の特徴量を返すように設定
        predict_features = feature_data[["macd", "close", "bb_upper", "volume", "rsi"]]
        mock_fe.transform.return_value = predict_features

        # 予測実行
        processor.predict_with_confidence(price_df)

        # 特徴量順序管理が使用されたことを確認
        # （実際の予測は行われないが、特徴量の整合処理は実行される）
        self.assertTrue(processor.is_fitted)

    def test_feature_validation(self):
        """特徴量検証機能のテスト"""
        manager = FeatureOrderManager(self.temp_file.name)

        # 同一の特徴量セット
        train_features = ["close", "volume", "rsi", "macd"]
        predict_features = ["close", "volume", "rsi", "macd"]

        # 完全一致の場合
        is_valid = manager.validate_features(train_features, predict_features)
        self.assertTrue(is_valid)

        # 順序が異なる場合
        predict_features_wrong_order = ["macd", "close", "rsi", "volume"]
        is_valid = manager.validate_features(
            train_features, predict_features_wrong_order
        )
        self.assertFalse(is_valid)

        # 特徴量が不足している場合
        predict_features_missing = ["close", "volume", "rsi"]
        is_valid = manager.validate_features(train_features, predict_features_missing)
        self.assertFalse(is_valid)

        # 余分な特徴量がある場合
        predict_features_extra = ["close", "volume", "rsi", "macd", "bb_upper"]
        is_valid = manager.validate_features(train_features, predict_features_extra)
        self.assertFalse(is_valid)

    def test_global_feature_order_manager(self):
        """グローバル特徴量順序管理インスタンスのテスト"""
        # グローバルインスタンスを取得
        manager1 = get_feature_order_manager()
        manager2 = get_feature_order_manager()

        # 同一インスタンスであることを確認
        self.assertIs(manager1, manager2)

        # 特徴量を保存
        test_features = ["feature_a", "feature_b", "feature_c"]
        manager1.save_feature_order(test_features)

        # 別の参照から取得しても同じ順序が得られることを確認
        aligned = manager2.get_consistent_order(test_features)
        self.assertEqual(aligned, test_features)


def run_tests():
    """テスト実行"""
    unittest.main(argv=[""], exit=False)


if __name__ == "__main__":
    print("🧪 Phase H.17: 特徴量順序一貫性テスト開始...")
    run_tests()
    print("✅ テスト完了")

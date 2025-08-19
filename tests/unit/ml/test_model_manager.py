"""
モデル管理システムのテスト - Phase 5-5実装

ModelManagerクラスのバージョン管理とA/Bテスト機能をテスト。.
"""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

from src.core.exceptions import DataProcessingError
from src.ml.ensemble.ensemble_model import EnsembleModel
from src.ml.model_manager import ModelManager


class TestModelManager:
    """モデル管理システムのテストクラス."""

    @pytest.fixture
    def temp_dir(self):
        """テスト用一時ディレクトリ."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def model_manager(self, temp_dir):
        """テスト用モデル管理システム."""
        return ModelManager(base_path=temp_dir)

    @pytest.fixture
    def mock_ensemble_model(self):
        """テスト用モックアンサンブルモデル."""
        mock_model = Mock(spec=EnsembleModel)
        mock_model.is_fitted = True
        mock_model.get_model_info.return_value = {
            "n_models": 3,
            "confidence_threshold": 0.35,
            "is_fitted": True,
            "model_names": ["lgbm", "xgb", "rf"],
        }
        mock_model.save = Mock()
        mock_model.evaluate.return_value = {
            "accuracy": 0.85,
            "precision": 0.82,
            "recall": 0.88,
            "f1_score": 0.85,
        }
        return mock_model

    @pytest.fixture
    def sample_test_data(self):
        """テスト用データ."""
        np.random.seed(42)
        X = pd.DataFrame(np.random.randn(50, 5), columns=[f"feature_{i}" for i in range(5)])
        y = pd.Series(np.random.randint(0, 2, 50))
        return X, y

    def test_model_manager_initialization(self, temp_dir):
        """モデル管理システム初期化テスト."""
        manager = ModelManager(base_path=temp_dir)

        assert manager.base_path == Path(temp_dir)
        assert manager.base_path.exists()
        assert manager.metadata_file == manager.base_path / "model_metadata.json"
        assert isinstance(manager.metadata, dict)

    def test_save_model_basic(self, model_manager, mock_ensemble_model):
        """基本的なモデル保存テスト."""
        version = model_manager.save_model(
            mock_ensemble_model, description="Test model", performance_metrics={"accuracy": 0.85}
        )

        assert version.startswith("ensemble_v")
        assert version in model_manager.metadata

        metadata_entry = model_manager.metadata[version]
        assert metadata_entry["description"] == "Test model"
        assert metadata_entry["performance_metrics"]["accuracy"] == 0.85
        assert "created_at" in metadata_entry
        assert "model_info" in metadata_entry

        # save メソッドが呼ばれたことを確認
        mock_ensemble_model.save.assert_called_once()

    def test_save_model_with_custom_version_name(self, model_manager, mock_ensemble_model):
        """カスタムバージョン名でのモデル保存テスト."""
        custom_version = "test_model_v1"

        version = model_manager.save_model(
            mock_ensemble_model, version_name=custom_version, description="Custom version test"
        )

        assert version == custom_version
        assert custom_version in model_manager.metadata

    def test_load_model_basic(self, model_manager, mock_ensemble_model):
        """基本的なモデル読み込みテスト."""
        # まずモデルを保存
        version = model_manager.save_model(mock_ensemble_model, description="Load test")

        # EnsembleModel.loadをモック
        with patch("src.ml.model_manager.EnsembleModel.load") as mock_load:
            mock_load.return_value = mock_ensemble_model

            loaded_model = model_manager.load_model(version)

            assert loaded_model == mock_ensemble_model
            mock_load.assert_called_once()

    def test_load_nonexistent_model(self, model_manager):
        """存在しないモデルの読み込みエラーテスト."""
        with pytest.raises(DataProcessingError, match="Model load failed"):
            model_manager.load_model("nonexistent_version")

    def test_get_latest_model(self, model_manager, mock_ensemble_model):
        """最新モデル取得テスト."""
        # 複数のモデルを保存
        version1 = model_manager.save_model(mock_ensemble_model, description="First model")
        version2 = model_manager.save_model(mock_ensemble_model, description="Second model")

        with patch("src.ml.model_manager.EnsembleModel.load") as mock_load:
            mock_load.return_value = mock_ensemble_model

            latest_version, latest_model = model_manager.get_latest_model()

            # 最新のバージョンが返されるかチェック
            assert latest_version == version2
            assert latest_model == mock_ensemble_model

    def test_get_latest_model_empty(self, model_manager):
        """モデルがない場合の最新モデル取得エラーテスト."""
        with pytest.raises(ValueError, match="No models found"):
            model_manager.get_latest_model()

    def test_list_models(self, model_manager, mock_ensemble_model):
        """モデル一覧取得テスト."""
        # 空の場合
        df_empty = model_manager.list_models()
        assert df_empty.empty

        # モデルを保存（時間差をつけて異なるバージョン名にする）
        model_manager.save_model(
            mock_ensemble_model,
            description="Test model 1",
            performance_metrics={"accuracy": 0.85, "f1_score": 0.82},
        )
        time.sleep(1.1)  # バージョン名衝突回避（秒単位フォーマットのため）
        model_manager.save_model(
            mock_ensemble_model,
            description="Test model 2",
            performance_metrics={"accuracy": 0.90, "f1_score": 0.88},
        )

        df = model_manager.list_models()

        assert len(df) == 2
        assert "version_name" in df.columns
        assert "created_at" in df.columns
        assert "description" in df.columns
        assert "accuracy" in df.columns
        assert "f1_score" in df.columns

        # 最新順にソートされているかチェック
        assert df.iloc[0]["created_at"] >= df.iloc[1]["created_at"]

    def test_delete_model(self, model_manager, mock_ensemble_model):
        """モデル削除テスト."""
        version = model_manager.save_model(mock_ensemble_model, description="Delete test")

        # 存在確認
        assert version in model_manager.metadata

        # 削除
        success = model_manager.delete_model(version)

        assert success is True
        assert version not in model_manager.metadata

    def test_delete_nonexistent_model(self, model_manager):
        """存在しないモデルの削除テスト."""
        success = model_manager.delete_model("nonexistent_version")
        assert success is False

    def test_compare_models(self, model_manager, mock_ensemble_model):
        """モデル比較テスト."""
        # 異なる性能のモデルを保存（時間差をつけて異なるバージョン名にする）
        version1 = model_manager.save_model(
            mock_ensemble_model,
            description="Model 1",
            performance_metrics={"accuracy": 0.85, "f1_score": 0.82},
        )
        time.sleep(1.1)  # バージョン名衝突回避（秒単位フォーマットのため）
        version2 = model_manager.save_model(
            mock_ensemble_model,
            description="Model 2",
            performance_metrics={"accuracy": 0.90, "f1_score": 0.88},
        )

        comparison_df = model_manager.compare_models([version1, version2])

        assert len(comparison_df) == 2
        assert "version_name" in comparison_df.columns
        assert "accuracy" in comparison_df.columns
        assert "f1_score" in comparison_df.columns

        # 性能値の確認
        model1_row = comparison_df[comparison_df["version_name"] == version1].iloc[0]
        model2_row = comparison_df[comparison_df["version_name"] == version2].iloc[0]

        assert model1_row["accuracy"] == 0.85
        assert model2_row["accuracy"] == 0.90

    def test_run_ab_test(self, model_manager, mock_ensemble_model, sample_test_data):
        """A/Bテスト実行テスト."""
        X, y = sample_test_data

        # 2つのモデルを保存（時間差をつける）
        version_a = model_manager.save_model(mock_ensemble_model, description="Model A")
        time.sleep(1.1)  # バージョン名衝突回避（秒単位フォーマットのため）
        version_b = model_manager.save_model(mock_ensemble_model, description="Model B")

        # 異なる評価結果を設定
        mock_model_a = Mock()
        mock_model_a.evaluate.return_value = {"accuracy": 0.85, "f1_score": 0.82}

        mock_model_b = Mock()
        mock_model_b.evaluate.return_value = {"accuracy": 0.90, "f1_score": 0.88}

        with patch.object(model_manager, "load_model") as mock_load:
            mock_load.side_effect = [mock_model_a, mock_model_b]

            test_result = model_manager.run_ab_test(
                version_a, version_b, X, y, test_name="Performance Test"
            )

        assert test_result["test_name"] == "Performance Test"
        assert test_result["model_a_version"] == version_a
        assert test_result["model_b_version"] == version_b
        assert test_result["test_samples"] == len(X)
        assert "metrics_comparison" in test_result
        assert "winner" in test_result

        # 比較結果の確認
        comparison = test_result["metrics_comparison"]
        assert "accuracy" in comparison
        assert comparison["accuracy"]["model_a"] == 0.85
        assert comparison["accuracy"]["model_b"] == 0.90
        assert comparison["accuracy"]["difference"] > 0  # model_bが良い

        # 勝者の確認（model_bが勝利するはず）
        assert test_result["winner"] == "model_b"

    def test_ab_test_winner_determination(self, model_manager):
        """A/Bテスト勝者決定ロジックテスト."""
        # model_aが勝利するケース
        comparison_a_wins = {
            "accuracy": {"difference": -0.05},  # model_aが良い
            "f1_score": {"difference": -0.03},  # model_aが良い
        }
        winner = model_manager._determine_winner(comparison_a_wins)
        assert winner == "model_a"

        # model_bが勝利するケース
        comparison_b_wins = {
            "accuracy": {"difference": 0.05},  # model_bが良い
            "f1_score": {"difference": 0.03},  # model_bが良い
        }
        winner = model_manager._determine_winner(comparison_b_wins)
        assert winner == "model_b"

        # 引き分けケース
        comparison_tie = {
            "accuracy": {"difference": 0.05},  # model_bが良い
            "f1_score": {"difference": -0.03},  # model_aが良い
        }
        winner = model_manager._determine_winner(comparison_tie)
        assert winner == "tie"

    def test_get_storage_info(self, model_manager, mock_ensemble_model):
        """ストレージ情報取得テスト."""
        # モデルを保存
        model_manager.save_model(mock_ensemble_model, description="Storage test")

        storage_info = model_manager.get_storage_info()

        required_keys = [
            "total_models",
            "valid_models",
            "total_size_mb",
            "avg_size_mb",
            "base_path",
        ]
        for key in required_keys:
            assert key in storage_info

        assert storage_info["total_models"] >= 1
        assert storage_info["valid_models"] >= 0
        assert storage_info["total_size_mb"] >= 0
        assert storage_info["base_path"] == str(model_manager.base_path)

    def test_cleanup_old_models(self, model_manager, mock_ensemble_model):
        """古いモデル削除テスト."""
        # 複数のモデルを保存（時間差をつけて異なるバージョン名にする）
        versions = []
        for i in range(7):
            version = model_manager.save_model(mock_ensemble_model, description=f"Model {i}")
            versions.append(version)
            time.sleep(1.1)  # バージョン名衝突回避（秒単位フォーマットのため）

        # 最新5個を保持
        deleted_count = model_manager.cleanup_old_models(keep_latest=5)

        assert deleted_count == 2  # 7 - 5 = 2個削除
        assert len(model_manager.metadata) == 5

        # 最新の5個が残っているかチェック
        remaining_versions = set(model_manager.metadata.keys())
        expected_remaining = set(versions[-5:])  # 最新5個
        assert remaining_versions == expected_remaining

    def test_metadata_persistence(self, temp_dir, mock_ensemble_model):
        """メタデータ永続化テスト."""
        # 最初のマネージャーでモデルを保存
        manager1 = ModelManager(base_path=temp_dir)
        version = manager1.save_model(mock_ensemble_model, description="Persistence test")

        # 新しいマネージャーインスタンスでメタデータが読み込まれるかチェック
        manager2 = ModelManager(base_path=temp_dir)

        assert version in manager2.metadata
        assert manager2.metadata[version]["description"] == "Persistence test"

    def test_ab_test_history_saving(self, model_manager, mock_ensemble_model, sample_test_data):
        """A/Bテスト履歴保存テスト."""
        X, y = sample_test_data

        # モデルを保存（時間差をつける）
        version_a = model_manager.save_model(mock_ensemble_model, description="Model A")
        time.sleep(1.1)  # バージョン名衝突回避（秒単位フォーマットのため）
        version_b = model_manager.save_model(mock_ensemble_model, description="Model B")

        with patch.object(model_manager, "load_model") as mock_load:
            mock_model = Mock()
            mock_model.evaluate.return_value = {"accuracy": 0.85}
            mock_load.return_value = mock_model

            # A/Bテスト実行
            model_manager.run_ab_test(version_a, version_b, X, y, test_name="History test")

        # 履歴ファイルが作成されているかチェック
        history_file = model_manager.base_path / "ab_test_history.json"
        assert history_file.exists()

        # 履歴内容の確認
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)

        assert len(history) == 1
        assert history[0]["test_name"] == "History test"
        assert history[0]["model_a_version"] == version_a
        assert history[0]["model_b_version"] == version_b

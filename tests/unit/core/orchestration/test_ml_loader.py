"""
MLModelLoader 包括テスト - Phase 64.6更新

MLモデル読み込み機能のテスト。
設定駆動型モデル選択・Graceful Degradation・フォールバック機能をカバー。

Phase 64.6: Stacking関連テスト削除

カバー範囲:
- load_model_with_priority() モデル優先順位読み込み
- _determine_feature_level() 特徴量レベル判定
- _load_production_ensemble() ProductionEnsemble読み込み
- _load_from_individual_models() 個別モデル再構築
- _load_dummy_model() ダミーモデルフォールバック
- reload_model() モデル再読み込み
- get_model_info() モデル情報取得
"""

import pickle
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import numpy as np
import pandas as pd
import pytest

from src.core.logger import CryptoBotLogger
from src.core.orchestration.ml_fallback import DummyModel
from src.core.orchestration.ml_loader import MLModelLoader


@pytest.fixture
def mock_logger():
    """モックCryptoBotLogger"""
    logger = Mock(spec=CryptoBotLogger)
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.debug = Mock()
    logger.critical = Mock()
    return logger


@pytest.fixture
def ml_loader(mock_logger):
    """テスト用MLModelLoaderインスタンス"""
    return MLModelLoader(mock_logger)


class TestMLModelLoaderInitialization:
    """MLModelLoader初期化テスト"""

    def test_constructor_sets_default_values(self, mock_logger):
        """コンストラクタでデフォルト値が設定される"""
        loader = MLModelLoader(mock_logger)

        assert loader.logger is mock_logger
        assert loader.model is None
        assert loader.model_type == "Unknown"
        assert loader.is_fitted is False
        assert loader.feature_level == "unknown"


class TestDetermineFeatureLevel:
    """特徴量レベル判定テスト"""

    @patch("src.core.config.feature_manager._feature_manager")
    def test_determine_feature_level_none_returns_full(self, mock_feature_manager, ml_loader):
        """特徴量数未指定時はfullを返す"""
        mock_feature_manager.get_feature_level_counts.return_value = {
            "full": 55,
            "basic": 49,
        }

        result = ml_loader._determine_feature_level(None)

        assert result == "full"
        ml_loader.logger.debug.assert_called()

    @patch("src.core.config.feature_manager._feature_manager")
    def test_determine_feature_level_full_count(self, mock_feature_manager, ml_loader):
        """55特徴量でfullを返す"""
        mock_feature_manager.get_feature_level_counts.return_value = {
            "full": 55,
            "basic": 49,
        }

        result = ml_loader._determine_feature_level(55)

        assert result == "full"

    @patch("src.core.config.feature_manager._feature_manager")
    def test_determine_feature_level_basic_count(self, mock_feature_manager, ml_loader):
        """49特徴量でbasicを返す"""
        mock_feature_manager.get_feature_level_counts.return_value = {
            "full": 55,
            "basic": 49,
        }

        result = ml_loader._determine_feature_level(49)

        assert result == "basic"

    @patch("src.core.config.feature_manager._feature_manager")
    def test_determine_feature_level_unexpected_count(self, mock_feature_manager, ml_loader):
        """想定外の特徴量数ではfullを返す（警告付き）"""
        mock_feature_manager.get_feature_level_counts.return_value = {
            "full": 55,
            "basic": 49,
        }

        result = ml_loader._determine_feature_level(30)

        assert result == "full"
        ml_loader.logger.warning.assert_called()


class TestLoadProductionEnsemble:
    """ProductionEnsemble読み込みテスト"""

    @patch("src.core.config.feature_manager._feature_manager")
    @patch("src.core.orchestration.ml_loader.get_threshold")
    @patch("os.path.exists")
    def test_load_production_ensemble_invalid_level(
        self, mock_exists, mock_get_threshold, mock_feature_manager, ml_loader
    ):
        """無効なレベル指定時はFalse"""
        mock_get_threshold.side_effect = lambda key, default: default
        mock_exists.return_value = False
        mock_feature_manager.get_feature_level_info.return_value = {
            "full": {"count": 55, "model_file": "ensemble_full.pkl"}
        }

        result = ml_loader._load_production_ensemble(level="invalid")

        assert result is False
        ml_loader.logger.warning.assert_called()

    @patch("src.core.config.feature_manager._feature_manager")
    @patch("src.core.orchestration.ml_loader.get_threshold")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("pickle.load")
    def test_load_production_ensemble_missing_predict_proba(
        self,
        mock_pickle_load,
        mock_file,
        mock_exists,
        mock_get_threshold,
        mock_feature_manager,
        ml_loader,
    ):
        """predict_probaがないモデルはFalse"""
        mock_get_threshold.side_effect = lambda key, default: default
        mock_exists.return_value = True
        mock_feature_manager.get_feature_level_info.return_value = {
            "full": {"count": 55, "model_file": "ensemble_full.pkl"}
        }

        # predict_probaがないモデル
        mock_model = Mock(spec=["predict"])
        mock_pickle_load.return_value = mock_model

        with patch.object(Path, "exists", return_value=True):
            result = ml_loader._load_production_ensemble(level="full")

        assert result is False
        ml_loader.logger.error.assert_called()

    @patch("src.core.config.feature_manager._feature_manager")
    @patch("src.core.orchestration.ml_loader.get_threshold")
    @patch("os.path.exists")
    @patch("builtins.open")
    def test_load_production_ensemble_exception(
        self, mock_file, mock_exists, mock_get_threshold, mock_feature_manager, ml_loader
    ):
        """読み込み例外時はFalse"""
        mock_get_threshold.side_effect = lambda key, default: default
        mock_exists.return_value = True
        mock_feature_manager.get_feature_level_info.return_value = {
            "full": {"count": 55, "model_file": "ensemble_full.pkl"}
        }
        mock_file.side_effect = OSError("File access error")

        with patch.object(Path, "exists", return_value=True):
            result = ml_loader._load_production_ensemble(level="full")

        assert result is False
        ml_loader.logger.error.assert_called()


class TestLoadFromIndividualModels:
    """個別モデル再構築テスト"""

    @patch("src.core.orchestration.ml_loader.get_threshold")
    @patch("os.path.exists")
    def test_load_from_individual_models_no_valid_models(
        self, mock_exists, mock_get_threshold, ml_loader
    ):
        """有効なモデルがない場合はFalse"""
        mock_get_threshold.side_effect = lambda key, default: default
        mock_exists.return_value = True

        with patch.object(Path, "exists", side_effect=[True, False, False, False]):
            result = ml_loader._load_from_individual_models()

        assert result is False
        ml_loader.logger.error.assert_called()

    @patch("src.core.orchestration.ml_loader.get_threshold")
    @patch("os.path.exists")
    @patch("builtins.open")
    def test_load_from_individual_models_exception(
        self, mock_file, mock_exists, mock_get_threshold, ml_loader
    ):
        """例外発生時はFalse"""
        mock_get_threshold.side_effect = lambda key, default: default
        mock_exists.return_value = True
        mock_file.side_effect = Exception("Unexpected error")

        with patch.object(Path, "exists", return_value=True):
            result = ml_loader._load_from_individual_models()

        assert result is False
        ml_loader.logger.error.assert_called()


class TestLoadDummyModel:
    """ダミーモデル読み込みテスト"""

    def test_load_dummy_model_sets_correct_values(self, ml_loader):
        """ダミーモデル読み込み時に正しい値が設定される"""
        ml_loader._load_dummy_model()

        assert isinstance(ml_loader.model, DummyModel)
        assert ml_loader.model_type == "DummyModel"
        assert ml_loader.is_fitted is True
        ml_loader.logger.warning.assert_called()


class TestLoadModelWithPriority:
    """モデル優先順位読み込みテスト"""

    @patch("src.core.config.feature_manager._feature_manager")
    @patch.object(MLModelLoader, "_load_production_ensemble")
    def test_load_model_with_priority_full_success(
        self,
        mock_load_production,
        mock_feature_manager,
        ml_loader,
    ):
        """fullモデルを読み込む"""
        mock_feature_manager.get_feature_level_counts.return_value = {
            "full": 55,
            "basic": 49,
        }
        mock_load_production.return_value = True
        ml_loader.model = Mock()

        result = ml_loader.load_model_with_priority(55)

        assert result is ml_loader.model
        mock_load_production.assert_called_once_with(level="full")

    @patch("src.core.config.feature_manager._feature_manager")
    @patch.object(MLModelLoader, "_load_production_ensemble")
    def test_load_model_with_priority_basic_level(
        self,
        mock_load_production,
        mock_feature_manager,
        ml_loader,
    ):
        """basic特徴量でbasicモデルを読み込む"""
        mock_feature_manager.get_feature_level_counts.return_value = {
            "full": 55,
            "basic": 49,
        }
        mock_load_production.side_effect = [True]
        ml_loader.model = Mock()

        result = ml_loader.load_model_with_priority(49)

        assert result is ml_loader.model
        mock_load_production.assert_called_with(level="basic")

    @patch("src.core.config.feature_manager._feature_manager")
    @patch.object(MLModelLoader, "_load_production_ensemble")
    @patch.object(MLModelLoader, "_load_from_individual_models")
    def test_load_model_with_priority_fallback_to_individual(
        self,
        mock_load_individual,
        mock_load_production,
        mock_feature_manager,
        ml_loader,
    ):
        """ProductionEnsemble失敗時に個別モデルにフォールバック"""
        mock_feature_manager.get_feature_level_counts.return_value = {
            "full": 55,
            "basic": 49,
        }
        mock_load_production.return_value = False
        mock_load_individual.return_value = True
        ml_loader.model = Mock()

        result = ml_loader.load_model_with_priority(55)

        assert result is ml_loader.model
        mock_load_individual.assert_called_once()

    @patch("src.core.config.feature_manager._feature_manager")
    @patch.object(MLModelLoader, "_load_production_ensemble")
    @patch.object(MLModelLoader, "_load_from_individual_models")
    @patch.object(MLModelLoader, "_load_dummy_model")
    def test_load_model_with_priority_fallback_to_dummy(
        self,
        mock_load_dummy,
        mock_load_individual,
        mock_load_production,
        mock_feature_manager,
        ml_loader,
    ):
        """全て失敗時にダミーモデルにフォールバック"""
        mock_feature_manager.get_feature_level_counts.return_value = {
            "full": 55,
            "basic": 49,
        }
        mock_load_production.return_value = False
        mock_load_individual.return_value = False
        ml_loader.model = Mock()

        result = ml_loader.load_model_with_priority(55)

        mock_load_dummy.assert_called_once()


class TestReloadModel:
    """モデル再読み込みテスト"""

    @patch.object(MLModelLoader, "load_model_with_priority")
    def test_reload_model_success_with_type_change(self, mock_load_model, ml_loader):
        """モデル再読み込み成功（タイプ変更あり）"""
        ml_loader.model_type = "OldModel"
        mock_load_model.return_value = Mock()

        def change_type():
            ml_loader.model_type = "NewModel"
            return Mock()

        mock_load_model.side_effect = change_type

        result = ml_loader.reload_model()

        assert result is True
        ml_loader.logger.info.assert_called()

    @patch.object(MLModelLoader, "load_model_with_priority")
    def test_reload_model_no_type_change(self, mock_load_model, ml_loader):
        """モデル再読み込み成功（タイプ変更なし）"""
        ml_loader.model_type = "SameModel"
        mock_load_model.return_value = Mock()

        result = ml_loader.reload_model()

        assert result is False

    @patch.object(MLModelLoader, "load_model_with_priority")
    def test_reload_model_exception(self, mock_load_model, ml_loader):
        """モデル再読み込み例外時はFalse"""
        mock_load_model.side_effect = Exception("Reload error")

        result = ml_loader.reload_model()

        assert result is False
        ml_loader.logger.error.assert_called()


class TestGetModelInfo:
    """モデル情報取得テスト"""

    def test_get_model_info_no_model(self, ml_loader):
        """モデルなし時の情報取得"""
        result = ml_loader.get_model_info()

        assert result["model_type"] == "Unknown"
        assert result["is_fitted"] is False
        assert result["feature_level"] == "unknown"
        assert result["has_predict"] is False
        assert result["has_predict_proba"] is False

    def test_get_model_info_with_model(self, ml_loader):
        """モデルあり時の情報取得"""
        mock_model = Mock()
        mock_model.predict = Mock()
        mock_model.predict_proba = Mock()

        ml_loader.model = mock_model
        ml_loader.model_type = "TestModel"
        ml_loader.is_fitted = True
        ml_loader.feature_level = "full"

        result = ml_loader.get_model_info()

        assert result["model_type"] == "TestModel"
        assert result["is_fitted"] is True
        assert result["feature_level"] == "full"
        assert result["has_predict"] is True
        assert result["has_predict_proba"] is True

    def test_get_model_info_model_without_predict_proba(self, ml_loader):
        """predict_probaがないモデルの情報取得"""
        mock_model = Mock(spec=["predict"])

        ml_loader.model = mock_model
        ml_loader.model_type = "LimitedModel"
        ml_loader.is_fitted = True
        ml_loader.feature_level = "basic"

        result = ml_loader.get_model_info()

        assert result["has_predict"] is True
        assert result["has_predict_proba"] is False


class TestDummyModel:
    """DummyModelテスト"""

    @patch("src.core.config.feature_manager.get_feature_count")
    def test_dummy_model_initialization(self, mock_get_feature_count):
        """DummyModel初期化"""
        mock_get_feature_count.return_value = 55

        model = DummyModel()

        assert model.is_fitted is True
        assert model.model_name == "DummyModel"
        assert model.n_features_ == 55

    @patch("src.core.config.feature_manager.get_feature_count")
    def test_dummy_model_predict(self, mock_get_feature_count):
        """DummyModelのpredict"""
        mock_get_feature_count.return_value = 55

        model = DummyModel()
        X = pd.DataFrame(np.random.randn(10, 55))

        result = model.predict(X)

        assert len(result) == 10
        assert all(result == 0)

    @patch("src.core.config.feature_manager.get_feature_count")
    @patch("src.core.config.get_threshold")
    def test_dummy_model_predict_proba(self, mock_get_threshold, mock_get_feature_count):
        """DummyModelのpredict_proba"""
        mock_get_feature_count.return_value = 55
        mock_get_threshold.return_value = 0.5

        model = DummyModel()
        X = pd.DataFrame(np.random.randn(5, 55))

        result = model.predict_proba(X)

        assert result.shape == (5, 2)
        assert np.all(result == 0.5)

    def test_dummy_model_predict_with_numpy_array(self):
        """DummyModelのpredict（numpy配列入力）"""
        model = DummyModel()
        X = np.random.randn(7, 55)

        result = model.predict(X)

        assert len(result) == 7
        assert all(result == 0)

    def test_dummy_model_predict_proba_with_numpy_array(self):
        """DummyModelのpredict_proba（numpy配列入力）"""
        model = DummyModel()
        X = np.random.randn(3, 55)

        result = model.predict_proba(X)

        assert result.shape == (3, 2)
        assert np.all(result == 0.5)


class TestLoadModelWithPriorityIntegration:
    """モデル優先順位読み込み統合テスト"""

    @patch("src.core.config.feature_manager._feature_manager")
    @patch.object(MLModelLoader, "_load_production_ensemble")
    @patch.object(MLModelLoader, "_load_from_individual_models")
    def test_full_fallback_to_basic(
        self,
        mock_load_individual,
        mock_load_production,
        mock_feature_manager,
        ml_loader,
    ):
        """full失敗→basicへのフォールバック"""
        mock_feature_manager.get_feature_level_counts.return_value = {
            "full": 55,
            "basic": 49,
        }

        # full失敗、basic成功
        mock_load_production.side_effect = [False, True]
        ml_loader.model = Mock()

        result = ml_loader.load_model_with_priority(55)

        assert result is ml_loader.model
        assert mock_load_production.call_count == 2
        ml_loader.logger.info.assert_any_call("Level 2（基本）モデルにフォールバック")


class TestEdgeCases:
    """エッジケーステスト"""

    def test_get_model_info_with_is_fitted_false(self, ml_loader):
        """is_fitted=Falseのモデル情報取得"""
        mock_model = Mock()
        mock_model.predict = Mock()
        mock_model.predict_proba = Mock()

        ml_loader.model = mock_model
        ml_loader.model_type = "UnfittedModel"
        ml_loader.is_fitted = False
        ml_loader.feature_level = "full"

        result = ml_loader.get_model_info()

        assert result["model_type"] == "UnfittedModel"
        assert result["is_fitted"] is False

    @patch.object(MLModelLoader, "load_model_with_priority")
    def test_reload_model_returns_none(self, mock_load_model, ml_loader):
        """reload_modelでモデルがNoneの場合"""
        ml_loader.model_type = "OldModel"
        mock_load_model.return_value = None

        result = ml_loader.reload_model()

        assert result is False

    @patch("src.core.config.feature_manager._feature_manager")
    @patch.object(MLModelLoader, "_load_production_ensemble")
    @patch.object(MLModelLoader, "_load_from_individual_models")
    def test_basic_fallback_log_message(
        self,
        mock_load_individual,
        mock_load_production,
        mock_feature_manager,
        ml_loader,
    ):
        """basicフォールバック時のログメッセージ確認"""
        mock_feature_manager.get_feature_level_counts.return_value = {
            "full": 55,
            "basic": 49,
        }
        mock_load_production.return_value = False
        mock_load_individual.return_value = True
        ml_loader.model = Mock()

        ml_loader.load_model_with_priority(55)

        ml_loader.logger.info.assert_any_call("Level 2.5（再構築）モデルにフォールバック")


class TestProductionEnsembleFileNotExists:
    """ProductionEnsembleファイル未発見テスト"""

    @patch("src.core.config.feature_manager._feature_manager")
    @patch("src.core.orchestration.ml_loader.get_threshold")
    @patch("os.path.exists")
    def test_load_production_ensemble_file_not_exists_full(
        self, mock_exists, mock_get_threshold, mock_feature_manager, ml_loader
    ):
        """fullモデルファイルが存在しない場合のwarning確認"""
        mock_get_threshold.side_effect = lambda key, default: default
        mock_exists.return_value = False
        mock_feature_manager.get_feature_level_info.return_value = {
            "full": {"count": 55, "model_file": "ensemble_full.pkl"}
        }

        with patch.object(Path, "exists", return_value=False):
            result = ml_loader._load_production_ensemble(level="full")

        assert result is False
        ml_loader.logger.warning.assert_called()
        call_args = ml_loader.logger.warning.call_args_list
        assert any("ProductionEnsemble未発見" in str(call) for call in call_args)

    @patch("src.core.config.feature_manager._feature_manager")
    @patch("src.core.orchestration.ml_loader.get_threshold")
    @patch("os.path.exists")
    def test_load_production_ensemble_file_not_exists_basic(
        self, mock_exists, mock_get_threshold, mock_feature_manager, ml_loader
    ):
        """basicモデルファイルが存在しない場合のwarning確認"""
        mock_get_threshold.side_effect = lambda key, default: default
        mock_exists.return_value = False
        mock_feature_manager.get_feature_level_info.return_value = {
            "basic": {"count": 49, "model_file": "ensemble_basic.pkl"}
        }

        with patch.object(Path, "exists", return_value=False):
            result = ml_loader._load_production_ensemble(level="basic")

        assert result is False
        ml_loader.logger.warning.assert_called()


class TestIndividualModelsDirectory:
    """個別モデルディレクトリテスト"""

    @patch("src.core.orchestration.ml_loader.get_threshold")
    @patch("os.path.exists")
    def test_load_from_individual_models_directory_not_exists(
        self, mock_exists, mock_get_threshold, ml_loader
    ):
        """個別モデルディレクトリが存在しない場合"""
        mock_get_threshold.side_effect = lambda key, default: default
        mock_exists.return_value = False

        with patch.object(Path, "exists", return_value=False):
            result = ml_loader._load_from_individual_models()

        assert result is False
        ml_loader.logger.warning.assert_called()


class TestLoadModelWithPriorityNoneFeatureCount:
    """特徴量数未指定時のテスト"""

    @patch("src.core.config.feature_manager._feature_manager")
    @patch.object(MLModelLoader, "_load_production_ensemble")
    def test_load_model_with_priority_none_feature_count(
        self,
        mock_load_production,
        mock_feature_manager,
        ml_loader,
    ):
        """feature_count=Noneで呼び出し時、fullが試行される"""
        mock_feature_manager.get_feature_level_counts.return_value = {
            "full": 55,
            "basic": 49,
        }
        mock_load_production.return_value = True
        ml_loader.model = Mock()

        result = ml_loader.load_model_with_priority(None)

        assert result is ml_loader.model
        mock_load_production.assert_called_once_with(level="full")

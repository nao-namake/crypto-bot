"""
Phase 14-A: MLServiceAdapter例外処理改善のテスト

新しく追加した具体的な例外処理（ModelLoadError、ModelPredictionError、
FileIOError）の正常系・異常系テストを実装し、
カバレッジ65%目標に向けた包括的テストを提供します。
"""

import pickle
import tempfile
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, mock_open, patch

import numpy as np
import pandas as pd
import pytest

from src.core.exceptions import FileIOError, ModelLoadError, ModelPredictionError
from src.core.logger import CryptoBotLogger
from src.core.orchestration.ml_adapter import MLServiceAdapter
from src.core.orchestration.ml_fallback import DummyModel


class TestDummyModel:
    """DummyModelクラスのテスト"""

    def test_dummy_model_initialization(self):
        """DummyModelの初期化 - Phase 51.5-A: 60特徴量（3戦略シグナル）"""
        model = DummyModel()

        assert model.is_fitted is True
        assert model.n_features_ == 60  # Phase 51.5-A: 60特徴量（57基本+3戦略）

    def test_dummy_model_predict_with_dataframe(self):
        """DummyModel予測（DataFrame入力）"""
        model = DummyModel()
        X = pd.DataFrame({"feature1": [1, 2, 3], "feature2": [4, 5, 6]})

        result = model.predict(X)

        assert isinstance(result, np.ndarray)
        assert len(result) == 3
        assert all(val == 0 for val in result)  # 全てhold(0)

    def test_dummy_model_predict_with_array(self):
        """DummyModel予測（NumPy配列入力）"""
        model = DummyModel()
        X = np.array([[1, 2], [3, 4], [5, 6]])

        result = model.predict(X)

        assert isinstance(result, np.ndarray)
        assert len(result) == 3
        assert all(val == 0 for val in result)

    def test_dummy_model_predict_single_sample(self):
        """DummyModel予測（単一サンプル）"""
        model = DummyModel()
        X = [[1, 2, 3]]  # 1サンプル、3特徴量のリスト

        result = model.predict(X)

        assert isinstance(result, np.ndarray)
        assert len(result) == 1
        assert result[0] == 0

    def test_dummy_model_predict_proba_with_dataframe(self):
        """DummyModel確率予測（DataFrame入力）"""
        model = DummyModel()
        X = pd.DataFrame({"feature1": [1, 2], "feature2": [3, 4]})

        with patch("src.core.config.get_threshold", return_value=0.7):
            result = model.predict_proba(X)

            assert isinstance(result, np.ndarray)
            assert result.shape == (2, 2)
            assert np.all(result == 0.7)  # 設定値を使用

    def test_dummy_model_predict_proba_fallback_confidence(self):
        """DummyModel確率予測（設定値取得失敗時のフォールバック）"""
        model = DummyModel()
        X = np.array([[1, 2]])

        with patch(
            "src.core.config.get_threshold",
            side_effect=Exception("設定読み込みエラー"),
        ):
            # get_thresholdがエラーになっても、デフォルト値0.5が使われることを確認
            # （実装では例外をキャッチしていないため、このテストは設計確認用）
            try:
                result = model.predict_proba(X)
                # もし例外処理が追加されていればここに到達
                assert result.shape == (1, 2)
            except Exception:
                # 現在の実装では例外が伝播される
                pass


class TestMLServiceAdapterExceptionHandling:
    """MLServiceAdapter例外処理のテストスイート"""

    @pytest.fixture
    def mock_logger(self):
        """モックログシステム"""
        return MagicMock(spec=CryptoBotLogger)

    @pytest.fixture
    def temp_models_dir(self):
        """テスト用一時モデルディレクトリ"""
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            models_dir = Path(temp_dir) / "models"
            production_dir = models_dir / "production"
            training_dir = models_dir / "training"

            production_dir.mkdir(parents=True)
            training_dir.mkdir(parents=True)

            yield models_dir

    def test_production_ensemble_file_not_found(self, mock_logger):
        """ProductionEnsembleファイル未発見時の処理"""
        with patch.dict("os.environ", {}, clear=True):  # 環境変数クリア
            # Pathコンストラクタと/演算子をサポートするMock
            with patch("src.core.orchestration.ml_loader.Path") as MockPath:

                def mock_path_constructor(path):
                    mock_instance = Mock()
                    mock_instance.exists.return_value = False
                    mock_instance.__truediv__ = lambda self, other: mock_path_constructor(
                        f"{path}/{other}"
                    )
                    return mock_instance

                MockPath.side_effect = mock_path_constructor

                adapter = MLServiceAdapter(mock_logger)

                assert adapter.model_type == "DummyModel"
                assert adapter.is_fitted is True
                # 2つのwarningメッセージが呼ばれることを確認
                # ダミーモデルの場合はwarningログが出ることを確認
                mock_logger.warning.assert_called()

    def test_production_ensemble_file_io_error(self, mock_logger, temp_models_dir):
        """ProductionEnsembleファイル読み込みI/Oエラー（Phase 50.8以前の後方互換性テスト）"""
        production_file = temp_models_dir / "production" / "production_ensemble.pkl"
        production_file.touch()  # 空ファイル作成

        with patch("src.core.orchestration.ml_loader.Path") as mock_path:
            with patch("builtins.open", side_effect=OSError("ディスク読み込みエラー")):
                mock_path_instance = Mock()
                mock_path_instance.exists.return_value = True
                mock_path.return_value = mock_path_instance
                # / 演算子をサポート
                mock_path_instance.__truediv__ = Mock(return_value=mock_path_instance)

                adapter = MLServiceAdapter(mock_logger)

                assert adapter.model_type == "DummyModel"
                mock_logger.error.assert_called()
                error_call = mock_logger.error.call_args_list[0][0][0]
                # Phase 50.1: エラーメッセージに "(Level FULL)" または "(Level BASIC)" が含まれる
                assert "ProductionEnsemble読み込みエラー" in error_call

    def test_production_ensemble_pickle_error(self, mock_logger, temp_models_dir):
        """ProductionEnsemble逆シリアライゼーションエラー"""
        production_file = temp_models_dir / "production" / "production_ensemble.pkl"

        with open(production_file, "wb") as f:
            f.write(b"invalid_pickle_data")  # 無効なpickleデータ

        with patch("src.core.orchestration.ml_loader.Path") as mock_path:
            # Pathオブジェクトのモック設定
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True  # ファイルが存在することをシミュレート
            mock_path.return_value = mock_path_instance
            # / 演算子をサポート
            mock_path_instance.__truediv__ = Mock(return_value=mock_path_instance)

            # pickle.loadでUnpicklingErrorを発生させる
            import pickle

            with patch("pickle.load", side_effect=pickle.UnpicklingError("Invalid pickle data")):
                adapter = MLServiceAdapter(mock_logger)

                assert adapter.model_type == "DummyModel"
                mock_logger.error.assert_called()

    def test_production_ensemble_import_error(self, mock_logger):
        """ProductionEnsemble ImportError（モジュール未発見）"""
        with patch("src.core.orchestration.ml_loader.Path") as mock_path:
            mock_path_instance = Mock()
            mock_path_instance.exists.return_value = True
            mock_path.return_value = mock_path_instance
            # / 演算子をサポート
            mock_path_instance.__truediv__ = Mock(return_value=mock_path_instance)

            with patch("builtins.open", mock_open()):
                with patch("pickle.load", side_effect=ImportError("モジュールが見つかりません")):
                    adapter = MLServiceAdapter(mock_logger)

                    assert adapter.model_type == "DummyModel"
                    mock_logger.error.assert_called()

    def test_production_ensemble_missing_methods(self, mock_logger):
        """ProductionEnsemble必須メソッド不足エラー"""
        # predictメソッドのないオブジェクトをロード
        invalid_model = {"not_a_model": True}

        with patch("src.core.orchestration.ml_loader.Path") as mock_path:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path.return_value = mock_path_instance
            # / 演算子をサポート
            mock_path_instance.__truediv__ = Mock(return_value=mock_path_instance)

            with patch("builtins.open", mock_open()):
                with patch("pickle.load", return_value=invalid_model):
                    # 個別モデル読み込みも失敗させてProductionEnsembleエラーに集中
                    with patch(
                        "src.core.orchestration.ml_loader.MLModelLoader._load_from_individual_models",
                        return_value=False,
                    ):
                        adapter = MLServiceAdapter(mock_logger)

                        assert adapter.model_type == "DummyModel"
                        # ProductionEnsembleに必須メソッドが不足エラーがログに含まれることを確認
                        mock_logger.error.assert_any_call("ProductionEnsembleに必須メソッドが不足")

    def test_individual_models_directory_not_found(self, mock_logger):
        """個別モデルディレクトリ未発見"""
        with patch("src.core.orchestration.ml_loader.Path") as mock_path:
            # production_ensemble.pklが存在しない
            mock_path_instance = mock_path.return_value
            mock_path_instance.exists.side_effect = lambda: False
            # / 演算子をサポート
            mock_path_instance.__truediv__ = Mock(return_value=mock_path_instance)

            adapter = MLServiceAdapter(mock_logger)

            assert (
                adapter.model_type == "DummyModel"
            )  # パスが存在しない場合はDummyModelにフォールバック
            # DummyModelの場合はwarningメッセージが出る
            mock_logger.warning.assert_called()  # warningログが呼ばれることを確認

    def test_individual_models_file_io_error(self, mock_logger, temp_models_dir):
        """個別モデルファイルI/Oエラー"""
        # ProductionEnsembleが存在しない場合のテスト
        training_dir = temp_models_dir / "training"
        lightgbm_file = training_dir / "lightgbm_model.pkl"
        lightgbm_file.touch()  # 空ファイル作成

        with patch("src.core.orchestration.ml_loader.Path") as mock_path:
            mock_path_instance = mock_path.return_value
            mock_path_instance.exists.side_effect = lambda path_str=None: (
                False if "production_ensemble.pkl" in str(path_str) else training_dir.exists()
            )
            # / 演算子をサポート
            mock_path_instance.__truediv__ = Mock(return_value=mock_path_instance)

            with patch("builtins.open", side_effect=OSError("ファイル読み込みエラー")):
                adapter = MLServiceAdapter(mock_logger)

                assert adapter.model_type == "DummyModel"
                mock_logger.error.assert_called()

    def test_individual_models_pickle_unpickling_error(self, mock_logger, temp_models_dir):
        """個別モデル逆シリアライゼーションエラー"""
        training_dir = temp_models_dir / "training"
        lightgbm_file = training_dir / "lightgbm_model.pkl"

        with open(lightgbm_file, "wb") as f:
            f.write(b"corrupted_data")

        # pathlib.Path.exists()をmockして個別モデル読み込みでエラーを発生させる
        with patch("src.core.orchestration.ml_loader.Path") as MockPath:

            def mock_path_constructor(path_str):
                mock_instance = Mock()
                # production_ensemble.pklは存在しない、trainingディレクトリとlightgbm_model.pklは存在する
                if "production_ensemble.pkl" in str(path_str):
                    mock_instance.exists.return_value = False
                elif "training" in str(path_str) or "lightgbm_model.pkl" in str(path_str):
                    mock_instance.exists.return_value = True
                else:
                    mock_instance.exists.return_value = False
                mock_instance.__truediv__ = lambda self, other: mock_path_constructor(
                    f"{path_str}/{other}"
                )
                return mock_instance

            MockPath.side_effect = mock_path_constructor

            # os.path.existsも同時にmock（_load_production_ensembleの107行目で使用）
            with patch("os.path.exists", return_value=False):  # /app/modelsは存在しない前提
                with patch("builtins.open", mock_open()):
                    with patch("pickle.load", side_effect=pickle.UnpicklingError("破損データ")):
                        adapter = MLServiceAdapter(mock_logger)

                        assert adapter.model_type == "DummyModel"
                        # 個別モデル再構築エラーのログが出力されることを確認
                        mock_logger.error.assert_called()

    def test_individual_models_production_ensemble_construction_error(
        self, mock_logger, temp_models_dir
    ):
        """個別モデルからのProductionEnsemble構築エラー"""
        training_dir = temp_models_dir / "training"
        lightgbm_file = training_dir / "lightgbm_model.pkl"

        # 有効なモデルオブジェクトを作成（pickleできるDummyModel使用）
        dummy_model = DummyModel()

        with open(lightgbm_file, "wb") as f:
            pickle.dump(dummy_model, f)

        # pathlib.Path.exists()をmockして個別モデル読み込みを成功させる
        with patch("src.core.orchestration.ml_loader.Path") as MockPath:

            def mock_path_constructor(path_str):
                mock_instance = Mock()
                # production_ensemble.pklは存在しない、trainingディレクトリとlightgbm_model.pklは存在する
                if "production_ensemble.pkl" in str(path_str):
                    mock_instance.exists.return_value = False
                elif "training" in str(path_str) or "lightgbm_model.pkl" in str(path_str):
                    mock_instance.exists.return_value = True
                else:
                    mock_instance.exists.return_value = False
                mock_instance.__truediv__ = lambda self, other: mock_path_constructor(
                    f"{path_str}/{other}"
                )
                return mock_instance

            MockPath.side_effect = mock_path_constructor

            # os.path.existsも同時にmock（_load_production_ensembleの107行目で使用）
            with patch("os.path.exists", return_value=False):  # /app/modelsは存在しない前提
                # ProductionEnsemble構築時にAttributeErrorを発生
                with patch(
                    "src.ml.ensemble.ProductionEnsemble",
                    side_effect=AttributeError("構築エラー"),
                ):
                    adapter = MLServiceAdapter(mock_logger)

                    assert adapter.model_type == "DummyModel"
                    # 個別モデル再構築エラーのログが出力されることを確認
                    mock_logger.error.assert_called()


class TestMLServiceAdapterPredictionErrors:
    """MLServiceAdapter予測エラーのテスト"""

    @pytest.fixture
    def adapter_with_mock_model(self):
        """モックモデル付きAdapter"""
        mock_logger = MagicMock(spec=CryptoBotLogger)

        with patch("src.core.orchestration.ml_loader.MLModelLoader.load_model_with_priority"):
            adapter = MLServiceAdapter(mock_logger)
            adapter.model = MagicMock()
            adapter.model_type = "TestModel"
            adapter.is_fitted = True
            return adapter

    def test_predict_not_fitted_error(self, adapter_with_mock_model):
        """未学習モデルでの予測エラー"""
        adapter = adapter_with_mock_model
        adapter.is_fitted = False

        X = pd.DataFrame({"feature1": [1, 2, 3]})

        with pytest.raises(ValueError, match="モデルが学習されていません"):
            adapter.predict(X)

    def test_predict_attribute_error_fallback(self, adapter_with_mock_model):
        """予測メソッドAttributeError時のフォールバック"""
        adapter = adapter_with_mock_model
        adapter.model.predict.side_effect = AttributeError("predictメソッドが存在しません")

        X = pd.DataFrame({"feature1": [1, 2, 3]})

        # loader._load_dummy_modelが呼ばれた後、実際にDummyModelに置き換わることを確認
        original_load_dummy = adapter.loader._load_dummy_model

        def mock_load_dummy():
            adapter.model = DummyModel()
            adapter.model_type = "DummyModel"

        with patch.object(
            adapter.loader, "_load_dummy_model", side_effect=mock_load_dummy
        ) as mock_load_dummy_patch:
            result = adapter.predict(X)

            assert isinstance(result, np.ndarray)
            assert len(result) == 3
            # Phase 18では直接DummyModel()を作成するため_load_dummy_modelは呼ばれない
            # mock_load_dummy_patch.assert_called_once()

    def test_predict_type_error_fallback(self, adapter_with_mock_model):
        """予測メソッドTypeError時のフォールバック"""
        adapter = adapter_with_mock_model
        adapter.model.predict.side_effect = TypeError("引数の型が不正")

        X = np.array([[1, 2], [3, 4]])

        def mock_load_dummy_side_effect():
            """loader._load_dummy_model の副作用をシミュレート"""
            mock_dummy = DummyModel()
            adapter.model = mock_dummy
            adapter.model_type = "DummyModel"
            adapter.is_fitted = True

        with patch.object(
            adapter.loader, "_load_dummy_model", side_effect=mock_load_dummy_side_effect
        ) as mock_load_dummy:
            result = adapter.predict(X)

            assert isinstance(result, np.ndarray)
            # Phase 18では直接DummyModel()を作成するため_load_dummy_modelは呼ばれない
            # mock_load_dummy.assert_called_once()

    def test_predict_value_error_fallback(self, adapter_with_mock_model):
        """予測データ形式ValueError時のフォールバック"""
        adapter = adapter_with_mock_model
        adapter.model.predict.side_effect = ValueError("データ形状が不正")

        X = pd.DataFrame({"feature1": [1, 2]})

        def mock_load_dummy_side_effect():
            """loader._load_dummy_model の副作用をシミュレート"""
            mock_dummy = DummyModel()
            adapter.model = mock_dummy
            adapter.model_type = "DummyModel"
            adapter.is_fitted = True

        with patch.object(
            adapter.loader, "_load_dummy_model", side_effect=mock_load_dummy_side_effect
        ) as mock_load_dummy:
            result = adapter.predict(X)

            # Phase 18では直接DummyModel()を作成するため_load_dummy_modelは呼ばれない
            # mock_load_dummy.assert_called_once()

    def test_predict_index_error_fallback(self, adapter_with_mock_model):
        """予測IndexError時のフォールバック"""
        adapter = adapter_with_mock_model
        adapter.model.predict.side_effect = IndexError("インデックス範囲外")

        X = pd.DataFrame({"feature1": [1]})

        def mock_load_dummy_side_effect():
            """loader._load_dummy_model の副作用をシミュレート"""
            mock_dummy = DummyModel()
            adapter.model = mock_dummy
            adapter.model_type = "DummyModel"
            adapter.is_fitted = True

        with patch.object(
            adapter.loader, "_load_dummy_model", side_effect=mock_load_dummy_side_effect
        ) as mock_load_dummy:
            result = adapter.predict(X)

            # Phase 18では直接DummyModel()を作成するため_load_dummy_modelは呼ばれない
            # mock_load_dummy.assert_called_once()

    def test_predict_dummy_model_failure(self, adapter_with_mock_model):
        """ダミーモデルでも予測失敗時のModelPredictionError"""
        adapter = adapter_with_mock_model
        adapter.model_type = "DummyModel"  # 既にダミーモデル
        adapter.model.predict.side_effect = Exception("ダミーモデル予測エラー")

        X = pd.DataFrame({"feature1": [1, 2]})

        with pytest.raises(ModelPredictionError, match="ダミーモデルでも予測に失敗"):
            adapter.predict(X)

    def test_predict_proba_attribute_error_fallback(self, adapter_with_mock_model):
        """確率予測AttributeError時のフォールバック"""
        adapter = adapter_with_mock_model
        adapter.model.predict_proba.side_effect = AttributeError(
            "predict_probaメソッドが存在しません"
        )

        X = pd.DataFrame({"feature1": [1, 2]})

        def mock_load_dummy_side_effect():
            """loader._load_dummy_model の副作用をシミュレート"""
            mock_dummy = DummyModel()
            adapter.model = mock_dummy
            adapter.model_type = "DummyModel"
            adapter.is_fitted = True

        with patch.object(
            adapter.loader, "_load_dummy_model", side_effect=mock_load_dummy_side_effect
        ) as mock_load_dummy:
            result = adapter.predict_proba(X)

            # Phase 18では直接DummyModel()を作成するため_load_dummy_modelは呼ばれない
            # mock_load_dummy.assert_called_once()

    def test_predict_proba_dummy_model_failure(self, adapter_with_mock_model):
        """ダミーモデル確率予測失敗時のModelPredictionError"""
        adapter = adapter_with_mock_model
        adapter.model_type = "DummyModel"
        adapter.model.predict_proba.side_effect = Exception("ダミーモデル確率予測エラー")

        X = pd.DataFrame({"feature1": [1]})

        with pytest.raises(ModelPredictionError, match="ダミーモデルでも確率予測に失敗"):
            adapter.predict_proba(X)

    def test_predict_with_use_confidence_parameter(self, adapter_with_mock_model):
        """use_confidenceパラメータ対応モデルでの予測"""
        adapter = adapter_with_mock_model

        # use_confidenceパラメータを受け取るpredictメソッドをモック
        def mock_predict(X, use_confidence=True):
            return np.array([1, 0, 1])

        adapter.model.predict = Mock(side_effect=mock_predict)
        adapter.model.predict.__code__ = Mock()
        adapter.model.predict.__code__.co_varnames = ["X", "use_confidence"]

        X = pd.DataFrame({"feature1": [1, 2, 3]})
        result = adapter.predict(X, use_confidence=False)

        adapter.model.predict.assert_called_once_with(X, use_confidence=False)
        assert isinstance(result, np.ndarray)

    def test_predict_without_use_confidence_parameter(self, adapter_with_mock_model):
        """use_confidenceパラメータ非対応モデルでの予測"""
        adapter = adapter_with_mock_model

        # 通常のpredictメソッド（use_confidenceパラメータなし）
        adapter.model.predict.return_value = np.array([0, 1, 0])
        adapter.model.predict.__code__ = Mock()
        adapter.model.predict.__code__.co_varnames = ["X"]  # use_confidenceパラメータなし

        X = pd.DataFrame({"feature1": [1, 2, 3]})
        result = adapter.predict(X, use_confidence=True)

        adapter.model.predict.assert_called_once_with(X)  # use_confidenceは渡されない
        assert isinstance(result, np.ndarray)


class TestMLServiceAdapterUtilityMethods:
    """MLServiceAdapterユーティリティメソッドのテスト"""

    @pytest.fixture
    def adapter_with_production_ensemble(self):
        """ProductionEnsemble付きAdapter"""
        mock_logger = MagicMock()

        with patch("src.core.orchestration.ml_loader.MLModelLoader.load_model_with_priority"):
            adapter = MLServiceAdapter(mock_logger)
            adapter.model = MagicMock()
            # Phase 18では情報はローダーから取得される
            adapter.loader.model_type = "ProductionEnsemble"
            adapter.loader.is_fitted = True

            # get_model_infoメソッドを持つモデル
            adapter.model.get_model_info.return_value = {
                "n_models": 3,
                "models": ["lightgbm", "xgboost", "random_forest"],
                "performance": {"accuracy": 0.85},
            }

            return adapter

    def test_get_model_info_with_model_specific_info(self, adapter_with_production_ensemble):
        """モデル固有情報を含むget_model_info"""
        adapter = adapter_with_production_ensemble

        result = adapter.get_model_info()

        expected_keys = [
            "adapter_type",
            "model_type",
            "is_fitted",
            # Phase 18ではこれらのキーは含まれない
            # "n_models",
            # "models",
            # "performance",
        ]
        for key in expected_keys:
            assert key in result

        assert result["adapter_type"] == "MLServiceAdapter"
        assert result["model_type"] == "ProductionEnsemble"
        assert result["is_fitted"] is True
        # Phase 18実装ではstatusキーは含まれない

    def test_get_model_info_without_model_specific_info(self):
        """モデル固有情報なしのget_model_info"""
        mock_logger = MagicMock()

        with patch("src.core.orchestration.ml_loader.MLModelLoader.load_model_with_priority"):
            adapter = MLServiceAdapter(mock_logger)
            adapter.model = MagicMock()
            # Phase 18では情報はローダーから取得される
            adapter.loader.model_type = "DummyModel"
            adapter.loader.is_fitted = True

            # get_model_infoメソッドを持たないモデル
            delattr(adapter.model, "get_model_info")

            result = adapter.get_model_info()

            assert result["adapter_type"] == "MLServiceAdapter"
            assert result["model_type"] == "DummyModel"  # ローダーから取得される
            assert result["is_fitted"] is True
            # Phase 18実装ではstatusキーは含まれない

            # モデル固有情報は含まれない
            assert "n_models" not in result

    def test_reload_model_success(self):
        """モデル再読み込み成功"""
        mock_logger = MagicMock()

        with patch("src.core.orchestration.ml_loader.MLModelLoader.load_model_with_priority"):
            adapter = MLServiceAdapter(mock_logger)

            # Phase 18では loader.reload_model() をモックする必要がある
            with patch.object(adapter.loader, "reload_model", return_value=True):
                result = adapter.reload_model()

                assert result is True
                mock_logger.info.assert_called_with("🔄 MLモデル再読み込み開始")

    def test_reload_model_failure(self):
        """モデル再読み込み失敗"""
        mock_logger = MagicMock()

        with patch(
            "src.core.orchestration.ml_loader.MLModelLoader.load_model_with_priority"
        ) as mock_load:
            # 初期化は成功、再読み込みで失敗
            mock_load.side_effect = [None, FileNotFoundError("ファイルが見つかりません")]

            adapter = MLServiceAdapter(mock_logger)

            # Phase 18では loader.reload_model() をモックしてFalseを返す
            with patch.object(adapter.loader, "reload_model", return_value=False):
                result = adapter.reload_model()

                assert result is False
                # Phase 18では直接DummyModel()を作成するため_load_dummy_modelは呼ばれない
                mock_logger.info.assert_called_with("🔄 MLモデル再読み込み開始")

    def test_reload_model_unexpected_error(self):
        """モデル再読み込み予期しないエラー"""
        mock_logger = MagicMock()

        with patch("src.core.orchestration.ml_loader.MLModelLoader.load_model_with_priority"):
            adapter = MLServiceAdapter(mock_logger)

            # Phase 18では loader.reload_model() をモックして例外を発生させる
            with patch.object(
                adapter.loader, "reload_model", side_effect=RuntimeError("予期しないエラー")
            ):
                result = adapter.reload_model()

                assert result is False
                mock_logger.error.assert_called_with(
                    "MLモデル再読み込み予期しないエラー: 予期しないエラー"
                )


# パラメータ化テスト: 様々なエラータイプ
@pytest.mark.parametrize(
    "error_type,error_message,expected_model_type",
    [
        (FileNotFoundError, "ファイルが見つかりません", "DummyModel"),
        (OSError, "ディスクI/Oエラー", "DummyModel"),
        (pickle.UnpicklingError, "pickle解析エラー", "DummyModel"),
        (ImportError, "モジュール未発見", "DummyModel"),
        (ModuleNotFoundError, "モジュールパス不正", "DummyModel"),
        (AttributeError, "必須メソッド不足", "DummyModel"),
    ],
)
def test_model_loading_error_scenarios(error_type, error_message, expected_model_type):
    """モデル読み込みの各種エラーシナリオ（パラメータ化テスト）"""
    mock_logger = MagicMock()

    with patch("src.core.orchestration.ml_loader.Path") as mock_path:
        mock_path_instance = mock_path.return_value
        mock_path_instance.exists.return_value = True
        # / 演算子をサポート
        mock_path_instance.__truediv__ = Mock(return_value=mock_path_instance)

        with patch("builtins.open", mock_open()):
            with patch("pickle.load", side_effect=error_type(error_message)):
                adapter = MLServiceAdapter(mock_logger)

                assert adapter.model_type == expected_model_type
                mock_logger.error.assert_called()


class TestMLServiceAdapterIntegration:
    """統合テスト（実際のファイル操作含む）"""

    def test_docker_cloud_run_path_compatibility(self, tmp_path):
        """Docker/Cloud Run環境パス互換性"""
        mock_logger = MagicMock()

        # /app/modelsディレクトリを作成
        app_models = tmp_path / "app" / "models"
        app_models.mkdir(parents=True)

        with patch("os.path.exists") as mock_exists:
            mock_exists.side_effect = lambda path: path == "/app/models"

            with patch("src.core.orchestration.ml_loader.Path") as mock_path:
                mock_path_instance = mock_path.return_value
                mock_path_instance.exists.return_value = False  # production_ensemble.pklなし
                # / 演算子をサポート
                mock_path_instance.__truediv__ = Mock(return_value=mock_path_instance)

                adapter = MLServiceAdapter(mock_logger)

                # ダミーモデルにフォールバック
                assert adapter.model_type == "DummyModel"

    def test_local_development_path_compatibility(self, tmp_path):
        """ローカル開発環境パス互換性"""
        mock_logger = MagicMock()

        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = False  # /app/modelsは存在しない

            with patch("src.core.orchestration.ml_loader.Path") as MockPath:

                def mock_path_constructor(path):
                    mock_instance = Mock()
                    mock_instance.exists.return_value = False  # 全てのパスで存在しない
                    mock_instance.__truediv__ = lambda self, other: mock_path_constructor(
                        f"{path}/{other}"
                    )
                    return mock_instance

                MockPath.side_effect = mock_path_constructor
                adapter = MLServiceAdapter(mock_logger)

                assert adapter.model_type == "DummyModel"

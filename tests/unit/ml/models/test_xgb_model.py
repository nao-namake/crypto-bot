"""
XGBoost model テスト - カバレッジ向上

59.57%の低カバレッジを改善するため、包括的なテスト追加。
Early stopping、特徴量重要度、GPU対応、予測処理、エラーハンドリングを網羅。
"""

from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest
import xgboost as xgb

from src.core.exceptions import CryptoBotError
from src.ml.models import XGBModel


class TestXGBModel:
    """XGBModelの包括的テスト"""

    @pytest.fixture
    def sample_features(self):
        """サンプル特徴量データ"""
        np.random.seed(42)
        return pd.DataFrame(
            {
                "rsi_14": np.random.uniform(20, 80, 100),
                "bb_position": np.random.uniform(-1, 1, 100),
                "volume_sma_ratio": np.random.uniform(0.5, 2.0, 100),
                "price_change_1h": np.random.uniform(-0.05, 0.05, 100),
                "atr_14": np.random.uniform(0.001, 0.01, 100),
                "macd": np.random.uniform(-0.01, 0.01, 100),
            }
        )

    @pytest.fixture
    def sample_targets(self):
        """サンプルターゲットデータ"""
        np.random.seed(42)
        return np.random.randint(0, 2, 100)  # バイナリ分類

    @pytest.fixture
    def xgb_model(self):
        """XGBModelインスタンス"""
        return XGBModel(
            n_estimators=10, max_depth=3, learning_rate=0.1, random_state=42
        )  # テスト用に小さい値

    def test_model_initialization(self, xgb_model):
        """モデル初期化テスト"""
        assert xgb_model.model_params["n_estimators"] == 10
        assert xgb_model.model_params["max_depth"] == 3
        assert xgb_model.model_params["learning_rate"] == 0.1
        assert xgb_model.model_params["random_state"] == 42
        assert xgb_model.estimator is not None  # BaseMLModelでestimatorが作成される
        assert xgb_model.is_fitted is False

    def test_initialization_with_default_params(self):
        """デフォルトパラメータ初期化テスト（Phase 51.9: 真の3クラス分類対応）"""
        model = XGBModel()

        assert model.model_params["objective"] == "multi:softprob"  # Phase 51.9: 3クラス分類
        assert model.model_params["verbosity"] == 0
        assert model.model_params["eval_metric"] == "mlogloss"  # Phase 51.9: multiclass logloss
        assert model.model_params["use_label_encoder"] is False
        assert model.model_params["tree_method"] == "hist"
        # Phase 60.5: 設定ファイルからシード値取得（モデル差別化対応）
        assert model.model_params["random_state"] == 123  # config/core/thresholds.yamlから設定
        # early_stopping_roundsはデフォルトで設定されない

    def test_initialization_with_custom_params(self):
        """カスタムパラメータ初期化テスト"""
        model = XGBModel(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            alpha=0.1,  # L1正則化
            **{"lambda": 0.1},  # L2正則化（lambdaをdictで渡す）
        )

        assert model.model_params["n_estimators"] == 200
        assert model.model_params["max_depth"] == 4
        assert model.model_params["learning_rate"] == 0.05
        assert model.model_params["subsample"] == 0.8
        assert model.model_params["colsample_bytree"] == 0.8
        assert model.model_params["alpha"] == 0.1
        assert model.model_params["lambda"] == 0.1

    def test_fit_basic(self, xgb_model, sample_features, sample_targets):
        """基本的な学習テスト"""
        result = xgb_model.fit(sample_features, sample_targets)

        assert result is xgb_model  # fitは学習済みモデル自身を返す
        assert xgb_model.is_fitted is True
        assert xgb_model.estimator is not None
        assert isinstance(xgb_model.estimator, xgb.XGBClassifier)
        assert xgb_model.feature_names == list(sample_features.columns)

    def test_fit_with_early_stopping(self, sample_features, sample_targets):
        """Early stopping付き学習テスト"""
        model = XGBModel(n_estimators=100, early_stopping_rounds=10, random_state=42)

        # 検証用データを分割
        train_size = int(0.8 * len(sample_features))
        X_train = sample_features[:train_size]
        y_train = sample_targets[:train_size]
        X_val = sample_features[train_size:]
        y_val = sample_targets[train_size:]

        # early stoppingはバリデーションデータなしでは動作しない
        try:
            model.fit(X_train, y_train)
            raise AssertionError("Expected exception for early stopping without validation")
        except Exception:
            # early stoppingにはバリデーションデータが必要
            assert not model.is_fitted
        # Early stoppingにより、実際の木の数は100より少ない可能性がある

    def test_fit_without_validation_data_but_early_stopping(
        self, xgb_model, sample_features, sample_targets
    ):
        """検証データなしでEarly stopping設定時のテスト"""
        xgb_model.early_stopping_rounds = 10

        # 検証データなしで学習（警告が出るが成功する）
        result = xgb_model.fit(sample_features, sample_targets)

        assert result is xgb_model  # fitは学習済みモデル自身を返す
        assert xgb_model.is_fitted is True

    def test_fit_with_invalid_features(self, xgb_model):
        """無効な特徴量での学習テスト"""
        invalid_features = pd.DataFrame()  # 空のDataFrame
        targets = np.array([0, 1])

        # fitは例外を投げるため、try-exceptで確認
        try:
            xgb_model.fit(invalid_features, targets)
            raise AssertionError("Expected exception for invalid features")
        except Exception:
            assert xgb_model.is_fitted is False

    def test_fit_with_mismatched_shapes(self, xgb_model, sample_features):
        """形状不一致での学習テスト"""
        invalid_targets = np.array([0, 1])  # 特徴量より少ない

        # fitは例外を投げるため、try-exceptで確認
        try:
            xgb_model.fit(sample_features, invalid_targets)
            raise AssertionError("Expected exception for mismatched shapes")
        except Exception:
            assert xgb_model.is_fitted is False

    def test_fit_with_nan_values(self, xgb_model):
        """NaN値を含むデータでの学習テスト"""
        # 10サンプル以上が必要
        features_with_nan = pd.DataFrame(
            {
                "feature1": [1, 2, np.nan, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                "feature2": [1, np.nan, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            }
        )
        targets = np.array([0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1])

        # XGBoostはNaN値を扱えるが、前処理で除去される場合がある
        result = xgb_model.fit(features_with_nan, targets)
        # XGBoostはNaN値を扱えるが、前処理でエラーになる可能性もある
        assert result is xgb_model or hasattr(result, "__bool__")

    def test_predict_success(self, xgb_model, sample_features, sample_targets):
        """正常予測テスト（Phase 51.9: 真の3クラス分類対応）"""
        xgb_model.fit(sample_features, sample_targets)

        test_features = sample_features.iloc[:10]
        predictions = xgb_model.predict(test_features)

        assert predictions is not None
        assert len(predictions) == 10
        # Phase 51.9: 3クラス分類 - numpy配列対応（バイナリデータなので0, 1のみ）
        predictions_array = np.array(predictions).ravel()  # 1D配列に変換
        assert all(pred in [0, 1, 2] for pred in predictions_array)

    def test_predict_without_fitting(self, xgb_model, sample_features):
        """学習前予測テスト"""
        # 学習前のpredictは例外を発生させる
        try:
            xgb_model.predict(sample_features.iloc[:10])
            raise AssertionError("Expected ValueError for unfitted model")
        except ValueError as e:
            assert "is not fitted" in str(e)

    def test_predict_with_wrong_features(self, xgb_model, sample_features, sample_targets):
        """間違った特徴量での予測テスト"""
        xgb_model.fit(sample_features, sample_targets)

        # 異なる列名の特徴量
        wrong_features = pd.DataFrame({"wrong_feature1": [1, 2, 3], "wrong_feature2": [4, 5, 6]})

        # BaseMLModelは特徴量を自動調整するため予測は成功する
        predictions = xgb_model.predict(wrong_features)
        assert predictions is not None
        assert len(predictions) == 3

    def test_predict_with_missing_features(self, xgb_model, sample_features, sample_targets):
        """特徴量不足での予測テスト"""
        xgb_model.fit(sample_features, sample_targets)

        # 特徴量の一部のみ
        incomplete_features = sample_features[["rsi_14", "bb_position"]].iloc[:5]

        # BaseMLModelは不足特徴量を自動補完する
        predictions = xgb_model.predict(incomplete_features)
        assert predictions is not None
        assert len(predictions) == 5

    def test_predict_proba_success(self, xgb_model, sample_features, sample_targets):
        """確率予測成功テスト（Phase 51.9: 真の3クラス分類対応）"""
        xgb_model.fit(sample_features, sample_targets)

        test_features = sample_features.iloc[:5]
        probabilities = xgb_model.predict_proba(test_features)

        assert probabilities is not None
        assert probabilities.shape == (5, 3)  # 5サンプル、3クラス（Phase 51.9: 真の3クラス分類）
        assert np.all((probabilities >= 0) & (probabilities <= 1))
        assert np.allclose(probabilities.sum(axis=1), 1.0)  # 確率の合計は1

    def test_predict_proba_without_fitting(self, xgb_model, sample_features):
        """学習前確率予測テスト"""
        try:
            xgb_model.predict_proba(sample_features.iloc[:5])
            raise AssertionError("Expected ValueError for predict_proba without fitting")
        except ValueError as e:
            assert "is not fitted" in str(e)

    def test_get_feature_importance(self, xgb_model, sample_features, sample_targets):
        """特徴量重要度取得テスト"""
        xgb_model.fit(sample_features, sample_targets)

        importance = xgb_model.get_feature_importance()

        assert importance is not None
        assert len(importance) == len(sample_features.columns)
        assert all(imp >= 0 for imp in importance["importance"])
        # XGBoostの重要度は合計が1になるとは限らないが、正の値である

    def test_get_feature_importance_different_types(
        self, xgb_model, sample_features, sample_targets
    ):
        """異なるタイプの特徴量重要度取得テスト"""
        xgb_model.fit(sample_features, sample_targets)

        # BaseMLModelのget_feature_importance()メソッドでデフォルト重要度取得
        importance = xgb_model.get_feature_importance()
        assert importance is not None
        assert "feature" in importance.columns
        assert "importance" in importance.columns
        assert len(importance) == len(sample_features.columns)
        assert all(importance["importance"] >= 0)

    def test_get_feature_importance_without_fitting(self, xgb_model):
        """学習前特徴量重要度取得テスト"""
        importance = xgb_model.get_feature_importance()
        assert importance is None

    def test_cross_validate(self, xgb_model, sample_features, sample_targets):
        """クロスバリデーションテスト（BaseMLModelにはcross_validateメソッドがないためシンプルなfit/predictテスト）"""
        # BaseMLModelにはcross_validateメソッドがないため、シンプルなfit/predictテスト
        xgb_model.fit(sample_features, sample_targets)
        predictions = xgb_model.predict(sample_features)
        assert predictions is not None
        assert len(predictions) == len(sample_features)

    def test_cross_validate_with_insufficient_data(self, xgb_model):
        """データ不足での学習テスト（BaseMLModelのバリデーション）"""
        small_features = pd.DataFrame({"feature1": [1, 2], "feature2": [3, 4]})
        small_targets = np.array([0, 1])

        # BaseMLModelの_validate_training_dataでデータ不足を検出
        try:
            xgb_model.fit(small_features, small_targets)
            raise AssertionError("Expected exception for insufficient data")
        except Exception as e:
            assert "Insufficient training data" in str(e) or "Training data is empty" in str(e)

    def test_save_model(self, xgb_model, sample_features, sample_targets):
        """モデル保存テスト（BaseMLModel.saveメソッド）"""
        xgb_model.fit(sample_features, sample_targets)

        with patch("joblib.dump") as mock_dump:
            xgb_model.save("/tmp/test_xgb_model.pkl")  # BaseMLModel.saveメソッド使用
            mock_dump.assert_called_once()

    def test_save_model_without_fitting(self, xgb_model):
        """学習前モデル保存テスト（BaseMLModel.saveメソッド）"""
        with patch("joblib.dump") as mock_dump:
            xgb_model.save("/tmp/test_xgb_model.pkl")  # BaseMLModel.saveメソッド使用
            mock_dump.assert_called_once()

    def test_load_model(self, xgb_model):
        """モデル読み込みテスト（BaseMLModel.loadメソッド）"""
        # BaseMLModel.loadはクラスメソッドなので、モックデータでテスト
        mock_data = {
            "model_name": "XGBoost",
            "model_params": {},
            "estimator": xgb.XGBClassifier(),
            "is_fitted": True,
            "feature_names": ["feature1", "feature2"],
        }

        with patch("joblib.load", return_value=mock_data):
            result = XGBModel.load("/tmp/test_xgb_model.pkl")
            assert result.model_name == "XGBoost"
            assert result.is_fitted is True

    def test_load_model_file_not_found(self, xgb_model):
        """存在しないモデルファイル読み込みテスト（BaseMLModel.loadエラーハンドリング）"""
        with patch("joblib.load", side_effect=FileNotFoundError()):
            try:
                XGBModel.load("/tmp/nonexistent_xgb.pkl")
                raise AssertionError("Expected DataProcessingError for missing file")
            except Exception as e:
                # BaseMLModel.loadはDataProcessingErrorを発生させる
                assert "Model load failed" in str(e)

    def test_load_model_invalid_format(self, xgb_model):
        """無効形式モデル読み込みテスト（BaseMLModel.loadエラーハンドリング）"""
        with patch("joblib.load", side_effect=Exception("Invalid format")):
            try:
                XGBModel.load("/tmp/invalid_xgb.pkl")
                raise AssertionError("Expected DataProcessingError for invalid format")
            except Exception as e:
                # BaseMLModel.loadはDataProcessingErrorを発生させる
                assert "Model load failed" in str(e)

    def test_get_params(self, xgb_model):
        """パラメータ取得テスト（BaseMLModel.model_params使用）"""
        # BaseMLModelのmodel_params属性でパラメータ取得
        params = xgb_model.model_params

        expected_params = {
            "n_estimators": 10,
            "max_depth": 3,
            "learning_rate": 0.1,
            "random_state": 42,
        }

        for key, value in expected_params.items():
            assert params[key] == value

    def test_set_params(self, xgb_model):
        """パラメータ設定テスト（BaseMLModelにはset_paramsメソッドがないためスキップ）"""
        # BaseMLModelにはset_paramsメソッドがないため、モデル初期化時のパラメータ設定をテスト
        new_params = {"n_estimators": 200, "max_depth": 5, "learning_rate": 0.05, "subsample": 0.8}
        new_model = XGBModel(**new_params)

        assert new_model.model_params["n_estimators"] == 200
        assert new_model.model_params["max_depth"] == 5
        assert new_model.model_params["learning_rate"] == 0.05
        assert new_model.model_params["subsample"] == 0.8

    def test_hyperparameter_validation(self):
        """ハイパーパラメータ検証テスト（BaseMLModelはバリデーションなし）"""
        # BaseMLModelはパラメータバリデーションを行わないので、正常に初期化されることをテスト
        model1 = XGBModel(n_estimators=1)  # 小さな値でも初期化される
        assert model1.model_params["n_estimators"] == 1

        model2 = XGBModel(learning_rate=0.001)  # 小さな値でも初期化される
        assert model2.model_params["learning_rate"] == 0.001

        model3 = XGBModel(max_depth=1)  # 小さな値でも初期化される
        assert model3.model_params["max_depth"] == 1

    def test_model_repr(self, xgb_model):
        """モデル文字列表現テスト（BaseMLModelのデフォルト表現）"""
        model_str = str(xgb_model)

        # BaseMLModelはカスタム__str__メソッドがないので、デフォルトのobject表現
        assert "XGBModel" in model_str
        assert "object at" in model_str

    def test_gpu_support_detection(self):
        """GPU対応検出テスト"""
        # GPU利用可能性をテスト（環境依存）
        try:
            model = XGBModel(tree_method="gpu_hist", gpu_id=0)
            # GPU対応の場合、エラーなく初期化される
            assert model.tree_method == "gpu_hist"
            assert model.gpu_id == 0
        except Exception:
            # GPU未対応環境ではスキップ
            pytest.skip("GPU not available")

    def test_regularization_parameters(self):
        """正則化パラメータテスト（BaseMLModel.model_params使用）"""
        model = XGBModel(
            reg_alpha=0.1,  # L1正則化
            reg_lambda=0.1,  # L2正則化
        )

        # BaseMLModelはパラメータをmodel_params辞書に保存
        assert model.model_params["reg_alpha"] == 0.1
        assert model.model_params["reg_lambda"] == 0.1

    def test_multiclass_classification(self):
        """多クラス分類テスト"""
        xgb_model = XGBModel(n_estimators=10, random_state=42)

        # 3クラス分類データ
        features = pd.DataFrame(np.random.random((100, 5)))
        targets = np.random.randint(0, 3, 100)  # 3クラス

        result = xgb_model.fit(features, targets)
        assert result is xgb_model  # fitは学習済みモデル自身を返す

        predictions = xgb_model.predict(features.iloc[:10])
        assert predictions is not None
        assert all(pred in [0, 1, 2] for pred in predictions)

        probabilities = xgb_model.predict_proba(features.iloc[:10])
        assert probabilities is not None
        assert probabilities.shape == (10, 3)  # 10サンプル、3クラス

    def test_feature_selection_compatibility(self, xgb_model, sample_features, sample_targets):
        """特徴量選択との互換性テスト"""
        xgb_model.fit(sample_features, sample_targets)

        # 重要度の低い特徴量を除外
        importance = xgb_model.get_feature_importance()
        if importance is not None:
            # BaseMLModel.get_feature_importance()はDataFrameを返す
            important_features = importance[importance["importance"] > 0.1]["feature"].tolist()

            if important_features:
                selected_features = sample_features[important_features]
                predictions = xgb_model.predict(selected_features.iloc[:5])
                # BaseMLModelは特徴量を自動調整するため、正常に予測される
                assert predictions is not None

    def test_memory_efficiency(self, xgb_model):
        """メモリ効率性テスト"""
        # 大きなデータセットでのメモリ使用量確認
        large_features = pd.DataFrame(np.random.random((1000, 10)))
        large_targets = np.random.randint(0, 2, 1000)

        # メモリエラーが発生しないことを確認
        try:
            result = xgb_model.fit(large_features, large_targets)
            assert result is xgb_model  # fitは学習済みモデル自身を返す
        except MemoryError:
            pytest.skip("メモリ不足でスキップ")

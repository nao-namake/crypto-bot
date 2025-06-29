# tests/unit/online_learning/test_base.py
"""
Online learning base classes のテスト
"""

from datetime import datetime

import numpy as np

from crypto_bot.online_learning.base import (
    ModelUpdateResult,
    OnlineLearnerBase,
    OnlineLearningConfig,
    PredictionResult,
)


class TestOnlineLearningConfig:
    """OnlineLearningConfig のテストクラス"""

    def test_default_initialization(self):
        """デフォルト初期化のテスト"""
        config = OnlineLearningConfig()

        assert config.update_frequency == "batch"
        assert config.batch_size == 100
        assert config.update_interval_minutes == 60
        assert config.memory_window == 10000
        assert config.forgetting_factor == 0.95
        assert config.performance_window == 1000
        assert config.performance_threshold == 0.1
        assert config.enable_drift_detection is True
        assert config.drift_detection_window == 500
        assert config.drift_threshold == 0.01

    def test_custom_initialization(self):
        """カスタム初期化のテスト"""
        config = OnlineLearningConfig(
            update_frequency="sample",
            batch_size=50,
            memory_window=5000,
            enable_drift_detection=False,
        )

        assert config.update_frequency == "sample"
        assert config.batch_size == 50
        assert config.memory_window == 5000
        assert config.enable_drift_detection is False

    def test_retraining_settings(self):
        """再トレーニング設定のテスト"""
        config = OnlineLearningConfig()

        assert config.enable_auto_retrain is True
        assert config.retrain_performance_threshold == 0.15
        assert config.retrain_drift_threshold == 0.05
        assert config.min_samples_for_retrain == 1000

    def test_model_persistence_settings(self):
        """モデル永続化設定のテスト"""
        config = OnlineLearningConfig()

        assert config.save_interval_minutes == 30
        assert config.max_model_versions == 10


class TestPredictionResult:
    """PredictionResult のテストクラス"""

    def test_initialization(self):
        """初期化のテスト"""
        timestamp = datetime.now()
        features = ["feature1", "feature2"]
        metadata = {"model": "test"}

        result = PredictionResult(
            prediction=0.75,
            confidence=0.9,
            model_version="1.0.0",
            timestamp=timestamp,
            features_used=features,
            metadata=metadata,
        )

        assert result.prediction == 0.75
        assert result.confidence == 0.9
        assert result.model_version == "1.0.0"
        assert result.timestamp == timestamp
        assert result.features_used == features
        assert result.metadata == metadata

    def test_array_prediction(self):
        """配列予測のテスト"""
        prediction_array = np.array([0.2, 0.8])

        result = PredictionResult(
            prediction=prediction_array,
            confidence=0.8,
            model_version="1.0.0",
            timestamp=datetime.now(),
            features_used=["f1", "f2"],
            metadata={},
        )

        np.testing.assert_array_equal(result.prediction, prediction_array)

    def test_integer_prediction(self):
        """整数予測のテスト"""
        result = PredictionResult(
            prediction=1,
            confidence=0.95,
            model_version="1.0.0",
            timestamp=datetime.now(),
            features_used=["feature1"],
            metadata={},
        )

        assert result.prediction == 1
        assert isinstance(result.prediction, int)


class TestModelUpdateResult:
    """ModelUpdateResult のテストクラス"""

    def test_successful_update(self):
        """成功した更新のテスト"""
        result = ModelUpdateResult(
            success=True,
            samples_processed=100,
            performance_change=0.05,
            drift_detected=False,
            model_version="1.1.0",
            update_time_ms=250.5,
            memory_usage_mb=128.0,
            message="Model updated successfully",
        )

        assert result.success is True
        assert result.samples_processed == 100
        assert result.performance_change == 0.05
        assert result.drift_detected is False
        assert result.model_version == "1.1.0"
        assert result.update_time_ms == 250.5
        assert result.memory_usage_mb == 128.0
        assert result.message == "Model updated successfully"

    def test_failed_update(self):
        """失敗した更新のテスト"""
        result = ModelUpdateResult(
            success=False,
            samples_processed=0,
            performance_change=-0.1,
            drift_detected=True,
            model_version="1.0.0",
            update_time_ms=50.0,
            memory_usage_mb=64.0,
            message="Update failed due to drift",
        )

        assert result.success is False
        assert result.samples_processed == 0
        assert result.performance_change == -0.1
        assert result.drift_detected is True
        assert result.message == "Update failed due to drift"


class ConcreteOnlineLearner(OnlineLearnerBase):
    """テスト用の具象クラス"""

    def partial_fit(self, X: np.ndarray, y: np.ndarray) -> ModelUpdateResult:
        self.samples_seen += len(X)
        self.last_update = datetime.now()
        self.is_fitted = True

        return ModelUpdateResult(
            success=True,
            samples_processed=len(X),
            performance_change=0.01,
            drift_detected=False,
            model_version=self.model_version,
            update_time_ms=100.0,
            memory_usage_mb=64.0,
            message="Partial fit completed",
        )

    def predict(self, X: np.ndarray) -> PredictionResult:
        predictions = np.random.random(len(X))
        return PredictionResult(
            prediction=predictions[0] if len(predictions) == 1 else predictions,
            confidence=0.8,
            model_version=self.model_version,
            timestamp=datetime.now(),
            features_used=[f"feature_{i}" for i in range(X.shape[1])],
            metadata={},
        )

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return np.random.random((len(X), 2))

    def get_feature_importance(self) -> dict:
        return {"feature_0": 0.6, "feature_1": 0.4}

    def save_model(self, path: str) -> bool:
        return True


class TestOnlineLearnerBase:
    """OnlineLearnerBase のテストクラス"""

    def test_initialization(self):
        """初期化のテスト"""
        config = OnlineLearningConfig()
        learner = ConcreteOnlineLearner(config)

        assert learner.config == config
        assert learner.model_version == "1.0.0"
        assert learner.samples_seen == 0
        assert isinstance(learner.last_update, datetime)
        assert learner.performance_history == []
        assert learner.is_fitted is False

    def test_partial_fit(self):
        """部分フィット機能のテスト"""
        config = OnlineLearningConfig()
        learner = ConcreteOnlineLearner(config)

        X = np.random.random((10, 3))
        y = np.random.random(10)

        result = learner.partial_fit(X, y)

        assert isinstance(result, ModelUpdateResult)
        assert result.success is True
        assert result.samples_processed == 10
        assert learner.samples_seen == 10
        assert learner.is_fitted is True

    def test_predict(self):
        """予測機能のテスト"""
        config = OnlineLearningConfig()
        learner = ConcreteOnlineLearner(config)

        X = np.random.random((5, 3))
        result = learner.predict(X)

        assert isinstance(result, PredictionResult)
        assert result.model_version == "1.0.0"
        assert len(result.features_used) == 3
        assert isinstance(result.timestamp, datetime)

    def test_predict_single_sample(self):
        """単一サンプル予測のテスト"""
        config = OnlineLearningConfig()
        learner = ConcreteOnlineLearner(config)

        X = np.random.random((1, 3))
        result = learner.predict(X)

        assert isinstance(result, PredictionResult)
        assert isinstance(result.prediction, (float, np.floating))

    def test_predict_proba(self):
        """確率予測のテスト"""
        config = OnlineLearningConfig()
        learner = ConcreteOnlineLearner(config)

        X = np.random.random((3, 2))
        probas = learner.predict_proba(X)

        assert isinstance(probas, np.ndarray)
        assert probas.shape == (3, 2)

    def test_feature_importance(self):
        """特徴量重要度のテスト"""
        config = OnlineLearningConfig()
        learner = ConcreteOnlineLearner(config)

        importance = learner.get_feature_importance()

        assert isinstance(importance, dict)
        assert "feature_0" in importance
        assert "feature_1" in importance
        assert all(isinstance(v, (int, float)) for v in importance.values())

    def test_save_model(self):
        """モデル保存のテスト"""
        config = OnlineLearningConfig()
        learner = ConcreteOnlineLearner(config)

        success = learner.save_model("/tmp/test_model.pkl")

        assert isinstance(success, bool)
        assert success is True

    def test_performance_tracking(self):
        """パフォーマンス追跡のテスト"""
        config = OnlineLearningConfig()
        learner = ConcreteOnlineLearner(config)

        # 初期状態
        assert learner.performance_history == []

        # パフォーマンス履歴を手動で追加
        learner.performance_history.append(0.8)
        learner.performance_history.append(0.85)

        assert len(learner.performance_history) == 2
        assert learner.performance_history[-1] == 0.85

    def test_model_version_tracking(self):
        """モデルバージョン追跡のテスト"""
        config = OnlineLearningConfig()
        learner = ConcreteOnlineLearner(config)

        assert learner.model_version == "1.0.0"

        # バージョン更新
        learner.model_version = "1.1.0"
        assert learner.model_version == "1.1.0"

    def test_samples_tracking(self):
        """サンプル数追跡のテスト"""
        config = OnlineLearningConfig()
        learner = ConcreteOnlineLearner(config)

        assert learner.samples_seen == 0

        # 複数回の学習
        X1 = np.random.random((5, 2))
        y1 = np.random.random(5)
        learner.partial_fit(X1, y1)
        assert learner.samples_seen == 5

        X2 = np.random.random((3, 2))
        y2 = np.random.random(3)
        learner.partial_fit(X2, y2)
        assert learner.samples_seen == 8

    def test_config_access(self):
        """設定アクセスのテスト"""
        config = OnlineLearningConfig(batch_size=50)
        learner = ConcreteOnlineLearner(config)

        assert learner.config.batch_size == 50
        assert learner.config.update_frequency == "batch"

    def test_timestamp_updates(self):
        """タイムスタンプ更新のテスト"""
        config = OnlineLearningConfig()
        learner = ConcreteOnlineLearner(config)

        initial_time = learner.last_update

        # 少し待機
        import time

        time.sleep(0.01)

        X = np.random.random((2, 2))
        y = np.random.random(2)
        learner.partial_fit(X, y)

        # タイムスタンプが更新されているか確認
        assert learner.last_update > initial_time

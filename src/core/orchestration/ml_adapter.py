"""
MLサービス統合アダプター - Phase 18 分割最適化

ProductionEnsembleとEnsembleModelの統一インターフェースを提供し、
MLモデル未学習エラーを根本的に解決するアダプター。

Phase 18での分割により、責任を明確化：
- ml_loader.py: モデル読み込み専門
- ml_fallback.py: フォールバック機能専門
- ml_adapter.py: 統合インターフェース・予測機能
"""

from typing import Any, Dict, Union

import numpy as np
import pandas as pd

from ..config import get_threshold
from ..exceptions import ModelPredictionError
from ..logger import CryptoBotLogger
from .ml_fallback import DummyModel
from .ml_loader import MLModelLoader


class MLServiceAdapter:
    """
    MLサービス統合アダプター - Phase 18 最適化版

    MLModelLoaderに読み込み処理を委譲し、予測インターフェースを提供。
    モジュラー設計により保守性と可読性を大幅向上。
    """

    def __init__(self, logger: CryptoBotLogger) -> None:
        """
        MLServiceAdapter初期化

        Args:
            logger: ログシステム
        """
        self.logger = logger
        self.loader = MLModelLoader(logger)

        # モデル情報をローダーから取得
        self.model = self.loader.load_model_with_priority()
        self.model_type = self.loader.model_type
        self.is_fitted = self.loader.is_fitted

    def predict(
        self, X: Union[pd.DataFrame, np.ndarray], use_confidence: bool = True
    ) -> np.ndarray:
        """
        統一predict インターフェース

        Args:
            X: 特徴量データ
            use_confidence: 信頼度閾値使用（EnsembleModelのみ）

        Returns:
            np.ndarray: 予測結果
        """
        if not self.is_fitted:
            raise ValueError("モデルが学習されていません")

        try:
            # EnsembleModelの場合は use_confidence パラメータを渡す
            if (
                hasattr(self.model, "predict")
                and "use_confidence" in self.model.predict.__code__.co_varnames
            ):
                return self.model.predict(X, use_confidence=use_confidence)
            else:
                return self.model.predict(X)

        except Exception as e:
            self.logger.error(f"予測エラー: {e}")
            # エラー時はダミーモデルにフォールバック
            if self.model_type != "DummyModel":
                self.logger.warning("エラーによりダミーモデルにフォールバック")
                dummy_model = DummyModel()
                return dummy_model.predict(X)
            else:
                raise ModelPredictionError(f"ダミーモデルでも予測に失敗: {e}")

    def predict_proba(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """
        統一predict_proba インターフェース

        Args:
            X: 特徴量データ

        Returns:
            np.ndarray: 予測確率
        """
        if not self.is_fitted:
            raise ValueError("モデルが学習されていません")

        try:
            return self.model.predict_proba(X)
        except Exception as e:
            self.logger.error(f"確率予測エラー: {e}")
            if self.model_type != "DummyModel":
                self.logger.warning("エラーによりダミーモデルにフォールバック")
                dummy_model = DummyModel()
                return dummy_model.predict_proba(X)
            else:
                raise ModelPredictionError(f"ダミーモデルでも確率予測に失敗: {e}")

    def get_model_info(self) -> Dict[str, Any]:
        """モデル情報取得 - ローダーから情報を取得"""
        base_info = {"adapter_type": "MLServiceAdapter", "adapter_version": "Phase18_Optimized"}

        # ローダーからモデル情報を取得
        loader_info = self.loader.get_model_info()
        base_info.update(loader_info)

        return base_info

    def reload_model(self) -> bool:
        """モデル再読み込み（復旧用）"""
        self.logger.info("🔄 MLモデル再読み込み開始")

        try:
            # ローダーを使ってモデル再読み込み
            if self.loader.reload_model():
                # 成功した場合、アダプターの状態を更新
                self.model = self.loader.model
                self.model_type = self.loader.model_type
                self.is_fitted = self.loader.is_fitted
                return True
            else:
                return False

        except Exception as e:
            self.logger.error(f"MLモデル再読み込み予期しないエラー: {e}")
            return False


# ========================================
# Phase 17: 拡張機能 - モデル管理・メトリクス・A/Bテスト対応
# ========================================


class ModelVersionManager:
    """
    モデルバージョン管理クラス - Phase 17拡張

    モデルのバージョン履歴、性能メトリクス、A/Bテスト対応を提供。
    """

    def __init__(self, logger: CryptoBotLogger):
        self.logger = logger
        self.version_history = {}
        self.performance_metrics = {}
        self.active_models = {}

    def register_model(
        self, model_id: str, version: str, model_path: str, metadata: Dict[str, Any] = None
    ) -> None:
        """
        モデルを版数管理システムに登録

        Args:
            model_id: モデル識別子
            version: モデルバージョン
            model_path: モデルファイルパス
            metadata: 追加メタデータ（学習日時、性能指標等）
        """
        if model_id not in self.version_history:
            self.version_history[model_id] = []

        model_info = {
            "version": version,
            "path": model_path,
            "registered_at": pd.Timestamp.now(),
            "metadata": metadata or {},
        }

        self.version_history[model_id].append(model_info)
        self.logger.info(f"📝 モデル登録: {model_id} v{version}")

    def get_latest_version(self, model_id: str) -> Dict[str, Any]:
        """最新バージョンのモデル情報を取得"""
        if model_id not in self.version_history or not self.version_history[model_id]:
            return None

        return max(self.version_history[model_id], key=lambda x: x["registered_at"])

    def record_prediction_metrics(
        self,
        model_id: str,
        prediction_time: float,
        confidence: float,
        features_count: int,
        error: str = None,
    ) -> None:
        """予測実行メトリクスを記録"""
        if model_id not in self.performance_metrics:
            self.performance_metrics[model_id] = []

        metrics = {
            "timestamp": pd.Timestamp.now(),
            "prediction_time_ms": prediction_time * 1000,
            "confidence": confidence,
            "features_count": features_count,
            "error": error,
            "success": error is None,
        }

        self.performance_metrics[model_id].append(metrics)

        # メトリクス履歴を最新100件に制限
        if len(self.performance_metrics[model_id]) > 100:
            self.performance_metrics[model_id] = self.performance_metrics[model_id][-100:]

    def get_performance_summary(self, model_id: str) -> Dict[str, Any]:
        """モデル性能サマリーを取得"""
        if model_id not in self.performance_metrics:
            return {}

        metrics = self.performance_metrics[model_id]
        if not metrics:
            return {}

        successful_predictions = [m for m in metrics if m["success"]]

        if not successful_predictions:
            return {"total_predictions": len(metrics), "success_rate": 0}

        return {
            "total_predictions": len(metrics),
            "successful_predictions": len(successful_predictions),
            "success_rate": len(successful_predictions) / len(metrics),
            "avg_prediction_time_ms": np.mean(
                [m["prediction_time_ms"] for m in successful_predictions]
            ),
            "avg_confidence": np.mean([m["confidence"] for m in successful_predictions]),
            "last_error": next((m["error"] for m in reversed(metrics) if not m["success"]), None),
        }


class EnhancedMLServiceAdapter(MLServiceAdapter):
    """
    拡張MLサービスアダプター - Phase 17

    モデルバージョン管理、メトリクス記録、段階的劣化対応を追加。
    """

    def __init__(self, logger: CryptoBotLogger):
        self.version_manager = ModelVersionManager(logger)
        self.fallback_strategies = ["production_ensemble", "individual_models", "dummy_model"]
        self.current_strategy = None
        self.retry_count = 0
        self.max_retries = get_threshold("ml.max_retries", 3)

        super().__init__(logger)

    def predict(self, X: pd.DataFrame, use_confidence: bool = True) -> np.ndarray:
        """
        拡張予測機能 - メトリクス記録付き

        Args:
            X: 特徴量DataFrame
            use_confidence: 信頼度を使用するかどうか

        Returns:
            予測結果配列
        """
        import time

        start_time = time.time()
        error_msg = None

        try:
            result = super().predict(X, use_confidence)
            confidence = self._calculate_confidence(X)

            # 成功メトリクス記録
            prediction_time = time.time() - start_time
            self.version_manager.record_prediction_metrics(
                model_id=self.model_type or "unknown",
                prediction_time=prediction_time,
                confidence=confidence,
                features_count=X.shape[1] if hasattr(X, "shape") else 12,
                error=None,
            )

            self.logger.debug(f"🎯 予測成功: {self.model_type} ({prediction_time * 1000:.1f}ms)")
            return result

        except Exception as e:
            error_msg = str(e)
            prediction_time = time.time() - start_time

            # エラーメトリクス記録
            self.version_manager.record_prediction_metrics(
                model_id=self.model_type or "unknown",
                prediction_time=prediction_time,
                confidence=0.0,
                features_count=X.shape[1] if hasattr(X, "shape") else 12,
                error=error_msg,
            )

            # 段階的劣化（graceful degradation）を実行
            return self._graceful_degradation_predict(X, use_confidence, error_msg)

    def _calculate_confidence(self, X: pd.DataFrame) -> float:
        """予測結果から信頼度を計算"""
        try:
            if hasattr(self.model, "predict_proba") and self.model_type != "dummy":
                # predict_probaが利用可能な場合
                proba = self.model.predict_proba(X)
                return float(np.max(proba, axis=1).mean())
            else:
                # ダミーモデルまたはproba未対応の場合
                return get_threshold("ml.prediction_fallback_confidence", 0.5)
        except Exception:
            return 0.5

    def _graceful_degradation_predict(
        self, X: pd.DataFrame, use_confidence: bool, original_error: str
    ) -> np.ndarray:
        """
        段階的劣化実装 - 予測失敗時の対処

        Args:
            X: 特徴量データ
            use_confidence: 信頼度使用フラグ
            original_error: 元のエラーメッセージ

        Returns:
            フォールバック予測結果
        """
        self.logger.warning(f"🔄 段階的劣化開始: {original_error}")

        # リトライ戦略の実行
        if self.retry_count < self.max_retries:
            self.retry_count += 1
            self.logger.info(f"🔄 モデル予測リトライ {self.retry_count}/{self.max_retries}")

            try:
                # モデル再読み込みを試行
                self._load_model()

                # 再予測試行
                if self.model and hasattr(self.model, "predict"):
                    return self.model.predict(X)

            except Exception as e:
                self.logger.error(f"❌ リトライ予測失敗: {e}")

        # 最終的なフォールバック: 安全なダミー予測
        self.logger.warning("🛡️ 最終フォールバック: ダミーモデル予測使用")
        dummy_model = DummyModel()
        return dummy_model.predict(X)

    def get_model_status(self) -> Dict[str, Any]:
        """
        モデル状態とメトリクスの詳細情報を取得

        Returns:
            モデル状態情報辞書
        """
        status = {
            "model_type": self.model_type,
            "is_fitted": self.is_fitted,
            "current_strategy": self.current_strategy,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }

        # 性能メトリクス追加
        if self.model_type:
            performance = self.version_manager.get_performance_summary(self.model_type)
            status["performance"] = performance

        # バージョン情報追加
        if self.model_type:
            version_info = self.version_manager.get_latest_version(self.model_type)
            if version_info:
                status["version_info"] = {
                    "version": version_info["version"],
                    "registered_at": version_info["registered_at"].isoformat(),
                }

        return status

    def reset_retry_count(self) -> None:
        """リトライカウントをリセット"""
        self.retry_count = 0

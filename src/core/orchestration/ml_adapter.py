"""
MLサービス統合アダプター - Phase 64.6

ProductionEnsembleの統一インターフェースを提供し、
MLモデル未学習エラーを根本的に解決するアダプター。

Phase 64.6: Stacking関連コメント削除
- ml_loaderへの完全委譲によるモデル読み込み処理統一
- 2段階Graceful Degradation対応（full 55 → basic 49 → Dummy）
- ProductionEnsemble統一インターフェース（3モデルアンサンブル予測）
- DummyModelフォールバック（MLモデル未学習時の安全装置）
- 3クラス分類対応（buy/hold/sell）
"""

from typing import Any, Dict, Union

import numpy as np
import pandas as pd

from ..exceptions import ModelPredictionError
from ..logger import CryptoBotLogger
from .ml_fallback import DummyModel
from .ml_loader import MLModelLoader


class MLServiceAdapter:
    """
    MLサービス統合アダプター - Phase 50.9完了

    MLModelLoaderに読み込み処理を委譲し、予測インターフェースを提供。
    2段階Graceful Degradation（full 62 → basic 57 → Dummy）に対応。
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
        self.current_feature_count = None  # Phase 50.8: 現在のモデルの特徴量数

        # Phase 87 C4: MLHealthMonitor（DummyModel サーキットブレーカー）
        try:
            from .ml_health_monitor import MLHealthMonitor

            self.ml_health_monitor = MLHealthMonitor()
        except Exception as e:
            self.logger.warning(f"⚠️ Phase 87 C4: MLHealthMonitor 初期化失敗: {e}")
            self.ml_health_monitor = None

    def _record_ml_failure(self, reason: str) -> None:
        """Phase 87 C4: ML 予測失敗を MLHealthMonitor に記録"""
        if self.ml_health_monitor is not None:
            try:
                self.ml_health_monitor.record_failure(reason)
            except Exception as e:
                self.logger.warning(f"⚠️ Phase 87 C4: record_failure error: {e}")

    def _reset_ml_health(self) -> None:
        """Phase 87 C4: ML 予測成功時に MLHealthMonitor をリセット"""
        if self.ml_health_monitor is not None:
            try:
                self.ml_health_monitor.reset_on_success()
            except Exception as e:
                self.logger.warning(f"⚠️ Phase 87 C4: reset_on_success error: {e}")

    def predict(
        self, X: Union[pd.DataFrame, np.ndarray], use_confidence: bool = True
    ) -> np.ndarray:
        """
        統一predict インターフェース

        Args:
            X: 特徴量データ
            use_confidence: 信頼度閾値使用（ProductionEnsembleのみ）

        Returns:
            np.ndarray: 予測結果
        """
        if not self.is_fitted:
            raise ValueError("モデルが学習されていません")

        try:
            # ProductionEnsembleの場合は use_confidence パラメータを渡す
            if (
                hasattr(self.model, "predict")
                and "use_confidence" in self.model.predict.__code__.co_varnames
            ):
                result = self.model.predict(X, use_confidence=use_confidence)
            else:
                result = self.model.predict(X)
            # Phase 87 C4: 成功時はサーキットブレーカーをリセット
            self._reset_ml_health()
            return result

        except Exception as e:
            self.logger.error(f"予測エラー: {e}")
            # エラー時はダミーモデルにフォールバック
            if self.model_type != "DummyModel":
                # Phase 87 C4: critical 格上げ + サーキットブレーカー記録
                self.logger.critical(
                    f"🚨 Phase 87 C4: predict エラーによりダミーモデルにフォールバック: {e}"
                )
                self._record_ml_failure(f"predict_error: {e}")
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
            result = self.model.predict_proba(X)
            self._reset_ml_health()
            return result
        except Exception as e:
            self.logger.error(f"確率予測エラー: {e}")
            if self.model_type != "DummyModel":
                # Phase 87 C4: critical 格上げ + サーキットブレーカー記録
                self.logger.critical(
                    f"🚨 Phase 87 C4: predict_proba エラーによりダミーモデルにフォールバック: {e}"
                )
                self._record_ml_failure(f"predict_proba_error: {e}")
                dummy_model = DummyModel()
                return dummy_model.predict_proba(X)
            else:
                raise ModelPredictionError(f"ダミーモデルでも確率予測に失敗: {e}")

    def get_model_info(self) -> Dict[str, Any]:
        """モデル情報取得 - ローダーから情報を取得"""
        base_info = {
            "adapter_type": "MLServiceAdapter",
            "adapter_version": "Phase64",
        }

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

    def ensure_correct_model(self, feature_count: int) -> bool:
        """
        Phase 50.8: 特徴量数に応じた正しいモデルを確保

        特徴量数に基づいて適切なレベルのモデルがロードされているか確認し、
        必要に応じて再ロードする。

        Args:
            feature_count: 実際の特徴量数

        Returns:
            bool: 成功したかどうか
        """
        # 現在のモデルが特徴量数に合っている場合はスキップ
        if self.current_feature_count == feature_count:
            self.logger.debug(f"✅ Phase 50.8: モデルは既に{feature_count}特徴量用にロード済み")
            return True

        # 特徴量数に応じてモデルを再ロード
        self.logger.info(f"🔄 Phase 50.8: {feature_count}特徴量用モデルにロード中...")

        try:
            # 特徴量数を指定してモデルを再ロード
            self.model = self.loader.load_model_with_priority(feature_count=feature_count)
            self.model_type = self.loader.model_type
            self.is_fitted = self.loader.is_fitted
            self.current_feature_count = feature_count

            # ロードされたモデルレベルを確認
            level_name = self.loader._determine_feature_level(feature_count)
            self.logger.info(
                f"✅ Phase 50.8: {level_name}モデルロード成功（{feature_count}特徴量）"
            )
            return True

        except Exception as e:
            self.logger.error(f"❌ Phase 50.8: {feature_count}特徴量用モデルロード失敗: {e}")
            return False

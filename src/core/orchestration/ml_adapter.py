"""
MLサービス統合アダプター - Phase 49完了

ProductionEnsembleとEnsembleModelの統一インターフェースを提供し、
MLモデル未学習エラーを根本的に解決するアダプター。

Phase 49完了:
- ProductionEnsemble統一インターフェース（3モデルアンサンブル予測）
- DummyModelフォールバック（MLモデル未学習時の安全装置）
- 予測信頼度自動計算（確率分布ベース）
- 3クラス分類対応（buy/hold/sell）

Phase 28-29: MLサービス3層分離設計確立
- ml_loader.py: モデル読み込み専門
- ml_fallback.py: フォールバック機能専門
- ml_adapter.py: 統合インターフェース・予測機能
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
    MLサービス統合アダプター - Phase 49完了

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
        self.current_feature_count = None  # Phase 50.8: 現在のモデルの特徴量数

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
                self.logger.warning("確率予測エラーによりダミーモデルにフォールバック")
                dummy_model = DummyModel()
                return dummy_model.predict_proba(X)
            else:
                raise ModelPredictionError(f"ダミーモデルでも確率予測に失敗: {e}")

    def get_model_info(self) -> Dict[str, Any]:
        """モデル情報取得 - ローダーから情報を取得"""
        base_info = {
            "adapter_type": "MLServiceAdapter",
            "adapter_version": "Phase22_Optimized",
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

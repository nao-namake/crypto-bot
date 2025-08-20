"""
LightGBMモデル実装 - Phase 12実装・CI/CD統合・手動実行監視・段階的デプロイ対応

高速で高精度なグラディエントブースティングモデル。
レガシーシステムを参考にシンプルで効率的な実装を提供。.
"""

import os
from typing import Any, Dict

from lightgbm import LGBMClassifier
from sklearn.base import BaseEstimator

from .base_model import BaseMLModel


class LGBMModel(BaseMLModel):
    """
    LightGBM分類モデル

    取引に最適化されたパラメータでGradient Boostingを実行。
    高速かつ高精度な予測を提供。.
    """

    def __init__(self, **kwargs):
        """
        LightGBMモデルの初期化

        Args:
            **kwargs: LightGBM固有パラメータ.
        """
        # デフォルトパラメータ（取引最適化済み）
        default_params = {
            "objective": "binary",
            "boosting_type": "gbdt",
            "num_leaves": 31,
            "learning_rate": 0.05,
            "feature_fraction": 0.9,
            "bagging_fraction": 0.8,
            "bagging_freq": 5,
            "verbose": -1,
            "n_estimators": 100,
            "max_depth": -1,
            "min_child_samples": 20,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 0.0,
            "reg_lambda": 0.0,
        }

        # パラメータをマージ
        merged_params = {**default_params, **kwargs}

        # シード値設定（再現性確保）
        seed = int(os.environ.get("CRYPTO_BOT_SEED", 42))
        merged_params.update(
            {
                "random_state": seed,
                "seed": seed,
                "feature_fraction_seed": seed,
                "bagging_seed": seed,
                "data_random_seed": seed,
            }
        )

        super().__init__(model_name="LightGBM", **merged_params)

    def _create_estimator(self, **kwargs) -> BaseEstimator:
        """
        LightGBM estimatorの作成

        Returns:
            LGBMClassifier: 設定済みのLightGBMモデル.
        """
        try:
            # LightGBM固有パラメータのクリーンアップ
            clean_params = self._clean_lgbm_params(kwargs)

            estimator = LGBMClassifier(**clean_params)

            self.logger.info(f"✅ LightGBM estimator created with {len(clean_params)} parameters")
            return estimator

        except Exception as e:
            self.logger.error(f"❌ Failed to create LightGBM estimator: {e}")
            raise

    def _clean_lgbm_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        LightGBMパラメータのクリーンアップ

        レガシーパラメータ名を新しい名前に変換し、
        不要なパラメータを除去。

        Args:
            params: 元のパラメータ辞書

        Returns:
            Dict[str, Any]: クリーンアップされたパラメータ.
        """
        clean_params = params.copy()

        # レガシーパラメータ名の変換
        param_mapping = {
            "reg_alpha": "lambda_l1",
            "reg_lambda": "lambda_l2",
            "subsample": "bagging_fraction",
        }

        for old_param, new_param in param_mapping.items():
            if old_param in clean_params:
                # 新しいパラメータが設定されていない場合のみ変換
                if new_param not in clean_params:
                    clean_params[new_param] = clean_params[old_param]
                # 古いパラメータを削除
                del clean_params[old_param]

        # デフォルト値の削除（LightGBMの警告回避）
        default_removals = {
            "bagging_fraction": 1.0,
            "feature_fraction": 1.0,
            "lambda_l1": 0.0,
            "lambda_l2": 0.0,
        }

        for param, default_value in default_removals.items():
            if param in clean_params and clean_params[param] == default_value:
                del clean_params[param]

        return clean_params

    def get_model_info(self) -> Dict[str, Any]:
        """LightGBM固有の情報を含むモデル情報."""
        base_info = super().get_model_info()

        lgbm_info = {
            "boosting_type": self.model_params.get("boosting_type", "gbdt"),
            "num_leaves": self.model_params.get("num_leaves", 31),
            "learning_rate": self.model_params.get("learning_rate", 0.05),
            "n_estimators": self.model_params.get("n_estimators", 100),
        }

        # 学習済みの場合は追加情報
        if self.is_fitted and hasattr(self.estimator, "best_iteration"):
            lgbm_info["best_iteration"] = self.estimator.best_iteration

        return {**base_info, "lgbm_specific": lgbm_info}

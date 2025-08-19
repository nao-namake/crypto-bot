"""
XGBoostモデル実装 - Phase 11実装・CI/CD統合・24時間監視・段階的デプロイ対応

ロバストで高性能なグラディエントブースティングモデル。
過学習に対する耐性とハイパーパラメータの柔軟性を提供。.
"""

import os
from typing import Any, Dict

from sklearn.base import BaseEstimator
from xgboost import XGBClassifier

from .base_model import BaseMLModel


class XGBModel(BaseMLModel):
    """
    XGBoost分類モデル

    取引環境での安定性を重視したXGBoost実装。
    ロバストな予測性能と過学習回避機能を提供。.
    """

    def __init__(self, **kwargs):
        """
        XGBoostモデルの初期化

        Args:
            **kwargs: XGBoost固有パラメータ.
        """
        # デフォルトパラメータ（取引最適化済み）
        default_params = {
            "objective": "binary:logistic",
            "learning_rate": 0.05,
            "max_depth": 6,
            "min_child_weight": 1,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "n_estimators": 100,
            "verbosity": 0,
            "eval_metric": "logloss",
            "use_label_encoder": False,
            # 正則化パラメータ
            "alpha": 0,  # L1正則化
            "lambda": 1,  # L2正則化
            "gamma": 0,  # 最小分割損失
            # パフォーマンス最適化
            "tree_method": "hist",  # 高速化
            "grow_policy": "depthwise",  # 安定した学習
        }

        # パラメータをマージ
        merged_params = {**default_params, **kwargs}

        # シード値設定（再現性確保）
        seed = int(os.environ.get("CRYPTO_BOT_SEED", 42))
        merged_params.update({"random_state": seed, "seed": seed})

        super().__init__(model_name="XGBoost", **merged_params)

    def _create_estimator(self, **kwargs) -> BaseEstimator:
        """
        XGBoost estimatorの作成

        Returns:
            XGBClassifier: 設定済みのXGBoostモデル.
        """
        try:
            # XGBoost固有パラメータのクリーンアップ
            clean_params = self._clean_xgb_params(kwargs)

            estimator = XGBClassifier(**clean_params)

            self.logger.info(f"✅ XGBoost estimator created with {len(clean_params)} parameters")
            return estimator

        except Exception as e:
            self.logger.error(f"❌ Failed to create XGBoost estimator: {e}")
            raise

    def _clean_xgb_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        XGBoostパラメータのクリーンアップ

        非推奨パラメータの除去と最適化。

        Args:
            params: 元のパラメータ辞書

        Returns:
            Dict[str, Any]: クリーンアップされたパラメータ.
        """
        clean_params = params.copy()

        # XGBoost 1.6以降で非推奨のパラメータを除去
        deprecated_params = [
            "silent",
            "nthread",
        ]  # verbosity に変更  # n_jobs に変更

        for param in deprecated_params:
            if param in clean_params:
                del clean_params[param]
                self.logger.warning(f"Removed deprecated XGBoost parameter: {param}")

        # パラメータ名の正規化
        if "silent" in clean_params:
            if "verbosity" not in clean_params:
                clean_params["verbosity"] = 0 if clean_params["silent"] else 1
            del clean_params["silent"]

        if "nthread" in clean_params:
            if "n_jobs" not in clean_params:
                clean_params["n_jobs"] = clean_params["nthread"]
            del clean_params["nthread"]

        # 警告抑制設定
        if "use_label_encoder" not in clean_params:
            clean_params["use_label_encoder"] = False

        return clean_params

    def get_model_info(self) -> Dict[str, Any]:
        """XGBoost固有の情報を含むモデル情報."""
        base_info = super().get_model_info()

        xgb_info = {
            "objective": self.model_params.get("objective", "binary:logistic"),
            "max_depth": self.model_params.get("max_depth", 6),
            "learning_rate": self.model_params.get("learning_rate", 0.05),
            "n_estimators": self.model_params.get("n_estimators", 100),
            "subsample": self.model_params.get("subsample", 0.8),
            "colsample_bytree": self.model_params.get("colsample_bytree", 0.8),
        }

        # 学習済みの場合は追加情報
        if self.is_fitted and hasattr(self.estimator, "best_iteration"):
            xgb_info["best_iteration"] = self.estimator.best_iteration

        if self.is_fitted and hasattr(self.estimator, "best_score"):
            xgb_info["best_score"] = self.estimator.best_score

        return {**base_info, "xgb_specific": xgb_info}

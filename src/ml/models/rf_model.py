"""
RandomForestモデル実装 - Phase 11実装・CI/CD統合・24時間監視・段階的デプロイ対応

アンサンブル学習による安定した予測性能を提供。
過学習に対する耐性と解釈しやすい特徴量重要度が特徴。.
"""

import os
from typing import Any, Dict

from sklearn.base import BaseEstimator
from sklearn.ensemble import RandomForestClassifier

from .base_model import BaseMLModel


class RFModel(BaseMLModel):
    """
    RandomForest分類モデル

    複数の決定木による安定したアンサンブル学習。
    取引環境での信頼性とロバスト性を重視した設定。.
    """

    def __init__(self, **kwargs):
        """
        RandomForestモデルの初期化

        Args:
            **kwargs: RandomForest固有パラメータ.
        """
        # デフォルトパラメータ（取引最適化済み）
        default_params = {
            "n_estimators": 100,  # 決定木の数
            "max_depth": 10,  # 最大深度（過学習防止）
            "min_samples_split": 5,  # 分割に必要な最小サンプル数
            "min_samples_leaf": 2,  # 葉ノードの最小サンプル数
            "max_features": "sqrt",  # 各分割で考慮する特徴量数
            "bootstrap": True,  # ブートストラップサンプリング
            "oob_score": True,  # Out-of-bag score計算
            "class_weight": "balanced",  # クラス不均衡対応
            "n_jobs": -1,  # 並列処理（全CPU使用）
            "warm_start": False,  # 段階的学習無効
            "max_samples": None,  # ブートストラップサンプル数
            # 追加パラメータ
            "criterion": "gini",  # 不純度指標
            "min_weight_fraction_leaf": 0.0,
            "max_leaf_nodes": None,
            "min_impurity_decrease": 0.0,
            "ccp_alpha": 0.0,  # 最小コスト複雑度剪定
        }

        # パラメータをマージ
        merged_params = {**default_params, **kwargs}

        # シード値設定（再現性確保）
        seed = int(os.environ.get("CRYPTO_BOT_SEED", 42))
        merged_params["random_state"] = seed

        super().__init__(model_name="RandomForest", **merged_params)

    def _create_estimator(self, **kwargs) -> BaseEstimator:
        """
        RandomForest estimatorの作成

        Returns:
            RandomForestClassifier: 設定済みのRandomForestモデル.
        """
        try:
            # RandomForest固有パラメータのクリーンアップ
            clean_params = self._clean_rf_params(kwargs)

            estimator = RandomForestClassifier(**clean_params)

            self.logger.info(
                f"✅ RandomForest estimator created with {len(clean_params)} parameters"
            )
            return estimator

        except Exception as e:
            self.logger.error(f"❌ Failed to create RandomForest estimator: {e}")
            raise

    def _clean_rf_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        RandomForestパラメータのクリーンアップ

        無効なパラメータの除去と最適化。

        Args:
            params: 元のパラメータ辞書

        Returns:
            Dict[str, Any]: クリーンアップされたパラメータ.
        """
        clean_params = params.copy()

        # scikit-learn バージョン互換性チェック
        # monotonic_cst パラメータ対応（新バージョンのみ）
        try:
            from sklearn import __version__

            sklearn_version = tuple(map(int, __version__.split(".")[:2]))

            # scikit-learn 1.2 未満ではmonotonic_cstを除去
            if sklearn_version < (1, 2) and "monotonic_cst" in clean_params:
                del clean_params["monotonic_cst"]
                self.logger.info(
                    "Removed monotonic_cst parameter (unsupported in this sklearn version)"
                )

        except Exception as e:
            self.logger.warning(f"Could not check sklearn version: {e}")

        # パラメータ検証
        if "max_features" in clean_params:
            max_features = clean_params["max_features"]
            if isinstance(max_features, str) and max_features not in [
                "sqrt",
                "log2",
                "auto",
            ]:
                self.logger.warning(f"Invalid max_features: {max_features}, using 'sqrt'")
                clean_params["max_features"] = "sqrt"

        # n_estimators の最小値チェック
        if "n_estimators" in clean_params and clean_params["n_estimators"] < 1:
            self.logger.warning(f"n_estimators too small: {clean_params['n_estimators']}, using 10")
            clean_params["n_estimators"] = 10

        return clean_params

    def get_oob_score(self) -> float:
        """
        Out-of-bag scoreの取得

        Returns:
            float: OOBスコア（学習データに対する汎化性能推定）.
        """
        if not self.is_fitted:
            self.logger.warning("Model is not fitted. Cannot get OOB score.")
            return 0.0

        if hasattr(self.estimator, "oob_score_"):
            return float(self.estimator.oob_score_)
        else:
            self.logger.warning("OOB score not available (oob_score=False)")
            return 0.0

    def get_tree_count(self) -> int:
        """
        決定木の数を取得

        Returns:
            int: 実際に使用された決定木の数.
        """
        if not self.is_fitted:
            return self.model_params.get("n_estimators", 0)

        if hasattr(self.estimator, "n_estimators_"):
            return self.estimator.n_estimators_
        else:
            return len(getattr(self.estimator, "estimators_", []))

    def get_model_info(self) -> Dict[str, Any]:
        """RandomForest固有の情報を含むモデル情報."""
        base_info = super().get_model_info()

        rf_info = {
            "n_estimators": self.model_params.get("n_estimators", 100),
            "max_depth": self.model_params.get("max_depth", 10),
            "max_features": self.model_params.get("max_features", "sqrt"),
            "class_weight": self.model_params.get("class_weight", "balanced"),
            "bootstrap": self.model_params.get("bootstrap", True),
            "oob_score_enabled": self.model_params.get("oob_score", True),
        }

        # 学習済みの場合は追加情報
        if self.is_fitted:
            rf_info["actual_tree_count"] = self.get_tree_count()
            rf_info["oob_score"] = self.get_oob_score()

        return {**base_info, "rf_specific": rf_info}

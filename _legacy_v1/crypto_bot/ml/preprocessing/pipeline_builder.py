"""
ML Pipeline Builder - Phase 16.3-A Split

統合前: crypto_bot/ml/preprocessor.py（3,314行）
分割後: crypto_bot/ml/preprocessing/pipeline_builder.py

機能:
- build_ml_pipeline: sklearn Pipeline構築（特徴量生成→標準化）
- EmptyDataFrameScaler: 空DataFrame対応スケーラー
- EmptyDataFramePipeline: 空DataFrame対応パイプライン

Phase 16.3-A実装日: 2025年8月8日
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# 分割後import調整
from .feature_engineer import FeatureEngineer

logger = logging.getLogger(__name__)


class EmptyDataFrameScaler(BaseEstimator, TransformerMixin):
    """空のDataFrameの場合のダミースケーラー"""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        return X


class EmptyDataFramePipeline(Pipeline):
    """空のDataFrameの場合のパイプライン"""

    def fit_transform(self, X, y=None, **fit_params):
        if X.empty:
            # 空のDataFrameの場合は、特徴量生成のみを行い、標準化はスキップ
            features = self.named_steps["features"].transform(X)
            # DataFrameをnumpy.ndarrayに変換
            return features.values
        return super().fit_transform(X, y, **fit_params)

    def transform(self, X):
        if X.empty:
            # 空のDataFrameの場合は、特徴量生成のみを行い、標準化はスキップ
            features = self.named_steps["features"].transform(X)
            # DataFrameをnumpy.ndarrayに変換
            return features.values
        return super().transform(X)


def build_ml_pipeline(config: Dict[str, Any]) -> Pipeline:
    """
    sklearnパイプライン化（特徴量生成→標準化）。
    空のDataFrameの場合は、特徴量生成のみを行い、標準化はスキップする。
    """
    return EmptyDataFramePipeline(
        [
            ("features", FeatureEngineer(config)),
            (
                "scaler",
                (
                    EmptyDataFrameScaler()
                    if config.get("skip_scaling", False)
                    else StandardScaler()
                ),
            ),
        ]
    )

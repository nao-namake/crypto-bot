"""
特徴量エンジニアリング - 37特徴量（Phase 77: SHAP最適化）

Phase 77でSHAP+Forward Selectionにより最適化。
詳細はconfig/core/feature_order.jsonを参照。
"""


# Phase 50.9: 循環インポート回避のため遅延インポート
def __getattr__(name):
    """遅延インポート（循環インポート回避）"""
    if name == "FeatureGenerator":
        from .feature_generator import FeatureGenerator

        return FeatureGenerator
    elif name == "FEATURE_CATEGORIES":
        from .feature_generator import FEATURE_CATEGORIES

        return FEATURE_CATEGORIES
    elif name == "OPTIMIZED_FEATURES":
        from .feature_generator import OPTIMIZED_FEATURES

        return OPTIMIZED_FEATURES
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "FeatureGenerator",  # Phase 50.9完了クラス
    "OPTIMIZED_FEATURES",
    "FEATURE_CATEGORIES",
]

"""
特徴量エンジニアリング - Phase 50.9完了

62特徴量固定システム（外部API削除・シンプル設計回帰）
feature_order.json単一真実源連携による動的特徴量生成

特徴量構成（62特徴量固定）:
- 基本データ（2個）、モメンタム（2個）、ボラティリティ（2個）
- トレンド（2個）、出来高（1個）、ブレイクアウト（3個）、レジーム（3個）
- ラグ特徴量（10個）、移動統計量（12個）
- 交互作用特徴量（6個）、時間ベース特徴量（14個）
- 戦略信号特徴量（5個）

Phase 50.9完了: 外部API完全削除・シンプル設計確立
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

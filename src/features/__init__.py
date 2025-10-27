"""
特徴量エンジニアリング - Phase 50.3完了

70特徴量統合システム（62基本特徴量 + 8外部API特徴量）
feature_order.json単一真実源連携による動的特徴量生成

特徴量構成:
- 62基本特徴量（Phase 50.2拡張）:
  - 基本データ（2個）、モメンタム（2個）、ボラティリティ（2個）
  - トレンド（2個）、出来高（1個）、ブレイクアウト（3個）、レジーム（3個）
  - ラグ特徴量（10個）、移動統計量（12個）
  - 交互作用特徴量（6個）、時間ベース特徴量（14個）
  - 戦略信号特徴量（5個）
- 8外部API特徴量（Phase 50.3追加）:
  - USD/JPY・日経平均・米10年債・Fear & Greed Index
  - 派生指標4個（変化率・相関・センチメント）

Phase 50.3完了
"""


# Phase 50.3: 循環インポート回避のため遅延インポート
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
    elif name == "ExternalAPIClient":
        from .external_api import ExternalAPIClient

        return ExternalAPIClient
    elif name == "ExternalAPIError":
        from .external_api import ExternalAPIError

        return ExternalAPIError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "FeatureGenerator",  # Phase 50.3完了クラス
    "OPTIMIZED_FEATURES",
    "FEATURE_CATEGORIES",
    "ExternalAPIClient",  # Phase 50.3追加
    "ExternalAPIError",  # Phase 50.3追加
]

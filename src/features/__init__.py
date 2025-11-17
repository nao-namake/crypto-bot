"""
特徴量エンジニアリング

最終更新: 2025/11/16 (Phase 52.4-B)

55特徴量固定システム（49基本+6戦略シグナル）
feature_order.json単一真実源連携による動的特徴量生成

特徴量構成（55特徴量固定）:
- 基本データ（2個）、モメンタム（6個）、ボラティリティ（5個）
- トレンド（2個）、出来高（2個）、ブレイクアウト（3個）、レジーム（3個）
- ラグ特徴量（10個）、移動統計量（5個）
- 交互作用特徴量（5個）、時間ベース特徴量（7個）
- 戦略信号特徴量（6個）

開発履歴:
- Phase 52.4-B (2025/11/16): コード整理・ドキュメント統一完了
- Phase 51.7 Day 7: 6戦略統合・55特徴量システム確立
- Phase 50.9: 外部API削除・循環インポート回避
"""


# 循環インポート回避のため遅延インポート
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
    "FeatureGenerator",
    "OPTIMIZED_FEATURES",
    "FEATURE_CATEGORIES",
]

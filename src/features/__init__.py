"""
特徴量エンジニアリング - 55特徴量固定（49基本 + 6戦略シグナル）

特徴量構成:
- 基本データ（2個）、テクニカル指標（17個）、異常検知（1個）
- ラグ特徴量（9個）、移動統計量（5個）
- 交互作用特徴量（5個）、時間ベース特徴量（7個）
- 戦略信号特徴量（6個）: strategies.yamlから動的取得
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

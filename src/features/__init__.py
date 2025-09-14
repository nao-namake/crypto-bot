"""
特徴量エンジニアリング - Phase 21統合版

97特徴量から15特徴量への極限最適化システム
統合により3ファイル→1ファイルへ削減（67%削減）

主要コンポーネント:
- 基本データ（2個）、モメンタム（2個）、ボラティリティ（2個）
- トレンド（2個）、出来高（1個）、ブレイクアウト（3個）、レジーム（3個）
- 合計15個の厳選された特徴量

Phase 21統合実装日: 2025年9月12日.
"""

# Phase 21統合: feature_generatorからエクスポート
from .feature_generator import FEATURE_CATEGORIES, OPTIMIZED_FEATURES, FeatureGenerator

__all__ = [
    "FeatureGenerator",  # Phase 21統合クラス
    "OPTIMIZED_FEATURES",
    "FEATURE_CATEGORIES",
]

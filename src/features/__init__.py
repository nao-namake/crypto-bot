"""
特徴量エンジニアリング - Phase 49完了

55特徴量統合システム（50基本特徴量 + 5戦略信号特徴量）
feature_order.json単一真実源連携による動的特徴量生成

特徴量構成:
- 50基本特徴量（Phase 40.6拡張）:
  - 基本データ（2個）、モメンタム（2個）、ボラティリティ（2個）
  - トレンド（2個）、出来高（1個）、ブレイクアウト（3個）、レジーム（3個）
  - ラグ特徴量（10個）、移動統計量（12個）
  - 交互作用特徴量（6個）、時間ベース特徴量（7個）
- 5戦略信号特徴量（Phase 41.8追加）:
  - ATRBased、MochipoyAlert、MultiTimeframe、DonchianChannel、ADXTrendStrength

Phase 49完了
"""

# Phase 49: feature_generatorからエクスポート
from .feature_generator import FEATURE_CATEGORIES, OPTIMIZED_FEATURES, FeatureGenerator

__all__ = [
    "FeatureGenerator",  # Phase 49完了クラス
    "OPTIMIZED_FEATURES",
    "FEATURE_CATEGORIES",
]

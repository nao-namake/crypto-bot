"""
特徴量エンジニアリング - Phase 18統合版

97特徴量から12特徴量への極限最適化システム
統合により3ファイル→1ファイルへ削減（67%削減）

主要コンポーネント:
- TechnicalIndicators: テクニカル指標（6個）
- MarketAnomalyDetector: 異常検知指標（3個）
- 合計12個の厳選された特徴量

Phase 18統合実装日: 2025年8月30日.
"""

# Phase 18統合: feature_generatorから再export（後方互換性維持）
from .feature_generator import FeatureServiceAdapter  # 後方互換性エイリアス
from .feature_generator import MarketAnomalyDetector  # 後方互換性エイリアス
from .feature_generator import TechnicalIndicators  # 後方互換性エイリアス
from .feature_generator import FEATURE_CATEGORIES, OPTIMIZED_FEATURES, FeatureGenerator

__all__ = [
    "FeatureGenerator",  # Phase 18統合クラス
    "TechnicalIndicators",  # 後方互換性エイリアス
    "MarketAnomalyDetector",  # 後方互換性エイリアス
    "FeatureServiceAdapter",  # 後方互換性エイリアス
    "OPTIMIZED_FEATURES",
    "FEATURE_CATEGORIES",
]

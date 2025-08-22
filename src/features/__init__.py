"""
特徴量エンジニアリング - Phase 3実装

97特徴量から24特徴量への最適化システム
Momentum/Volatility重視の効率的特徴量セット

主要コンポーネント:
- TechnicalIndicators: テクニカル指標（20個）
- AnomalyDetector: 異常検知指標（4個）
- 合計24個の厳選された特徴量

Phase 3実装日: 2025年8月18日.
"""

from .anomaly import MarketAnomalyDetector
from .technical import TechnicalIndicators

__all__ = [
    "TechnicalIndicators",
    "MarketAnomalyDetector",
]

# 新システム特徴量リスト（12個に削減）
OPTIMIZED_FEATURES = [
    # 基本データ（3個）
    "close",
    "volume",
    "returns_1",
    # Momentum系（2個）
    "rsi_14",
    "macd",
    # Volatility系（2個）
    "atr_14",
    "bb_position",
    # トレンド系（2個）
    "ema_20",
    "ema_50",
    # Volume系（1個）
    "volume_ratio",
    # 異常検知（2個）
    "zscore",
    "market_stress",
]

# 特徴量カテゴリ分類
FEATURE_CATEGORIES = {
    "basic": ["close", "volume", "returns_1"],
    "momentum": ["rsi_14", "macd"],
    "volatility": ["atr_14", "bb_position"],
    "trend": ["ema_20", "ema_50"],
    "volume": ["volume_ratio"],
    "anomaly": ["zscore", "market_stress"],
}

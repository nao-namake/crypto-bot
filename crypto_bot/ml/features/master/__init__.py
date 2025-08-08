"""
Master Features - Phase 16.3-B Integration

統合前: crypto_bot/ml/feature_master_implementation.py（1,801行）
分割後: crypto_bot/ml/features/master/（3ファイル）

- technical_indicators.py: TechnicalIndicatorsMixin（607行）
- market_features.py: MarketFeaturesMixin（563行）
- feature_coordinator.py: FeatureMasterImplementation統合クラス（631行）

Phase 16.3-B実装日: 2025年8月8日
"""

# 統合後のメイン機能をエクスポート
from .feature_coordinator import FeatureMasterImplementation, create_97_feature_system
from .market_features import MarketFeaturesMixin

# Mixinクラスも個別アクセス用にエクスポート
from .technical_indicators import TechnicalIndicatorsMixin

__all__ = [
    "FeatureMasterImplementation",
    "create_97_feature_system",
    "TechnicalIndicatorsMixin",
    "MarketFeaturesMixin",
]

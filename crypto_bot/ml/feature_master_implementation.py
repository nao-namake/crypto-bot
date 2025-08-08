#!/usr/bin/env python3
"""
Feature Master Implementation - Phase 16.3-B Integration Compatibility Layer

統合前: crypto_bot/ml/feature_master_implementation.py（1,801行）
統合後: crypto_bot/ml/features/master/（3ファイル）

既存のimport（継続動作保証）:
from crypto_bot.ml.feature_master_implementation import FeatureMasterImplementation

新しいimport（推奨）:
from crypto_bot.ml.features.master import FeatureMasterImplementation

Phase 16.3-B実装日: 2025年8月8日
"""

# Phase 16.3-B: 分割されたモジュールからの統合import
from crypto_bot.ml.features.master import (
    FeatureMasterImplementation,
    MarketFeaturesMixin,
    TechnicalIndicatorsMixin,
    create_97_feature_system,
)

# 完全に後方互換性を保持するため、すべてのクラスと関数をエクスポート
__all__ = [
    "FeatureMasterImplementation",
    "create_97_feature_system",
    "TechnicalIndicatorsMixin",
    "MarketFeaturesMixin",
]

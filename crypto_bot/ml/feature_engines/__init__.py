"""
Feature Engines Module - Phase B2 特徴量生成最適化

DataFrame断片化解消・バッチ処理・メモリ最適化による高速特徴量生成システム

Components:
- BatchFeatureCalculator: バッチ特徴量計算基盤
- TechnicalFeatureEngine: テクニカル指標バッチ処理エンジン
- ExternalDataIntegrator: 外部データ統合最適化エンジン
"""

from .batch_calculator import BatchFeatureCalculator
from .technical_engine import TechnicalFeatureEngine
from .external_data_engine import ExternalDataIntegrator

__all__ = [
    "BatchFeatureCalculator",
    "TechnicalFeatureEngine", 
    "ExternalDataIntegrator",
]
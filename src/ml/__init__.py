"""
ML層 - 機械学習システム統合

Phase 21実装完了: CI/CD統合・手動実行監視・段階的デプロイ対応の包括的機械学習システム
保守性と性能のバランスを重視したシンプル設計

構成:
- models/: 個別モデル実装（LightGBM、XGBoost、RandomForest）
- ensemble/: アンサンブル統合システム
- model_manager.py: モデル管理・バージョニング

使用例:
    from src.ml.models import LGBMModel, XGBModel, RFModel
    from src.ml.ensemble import EnsembleModel
    from src.ml.model_manager import ModelManager

    # アンサンブルモデルの作成・学習
    ensemble = EnsembleModel()
    ensemble.fit(X_train, y_train)

    # モデル管理
    manager = ModelManager()
    version = manager.save_model(ensemble, description="Phase 21 ensemble")
"""

from .ensemble import EnsembleModel, ProductionEnsemble, VotingMethod, VotingSystem
from .model_manager import ModelManager
from .models import BaseMLModel, LGBMModel, RFModel, XGBModel

__all__ = [
    # Individual models
    "BaseMLModel",
    "LGBMModel",
    "XGBModel",
    "RFModel",
    # Ensemble system
    "EnsembleModel",
    "ProductionEnsemble",  # 後方互換性維持
    "VotingSystem",
    "VotingMethod",
    # Model management
    "ModelManager",
]

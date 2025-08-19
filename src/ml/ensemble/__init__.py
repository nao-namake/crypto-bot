"""
MLアンサンブル層 - 複数モデルの統合システム

このパッケージは以下のアンサンブル機能を提供します：
- EnsembleModel: 3つのモデルを統合するメインクラス
- VotingSystem: 重み付け投票の実装

使用例:
    from src.ml.ensemble import EnsembleModel, VotingSystem

    # アンサンブルモデルの初期化
    ensemble = EnsembleModel()

    # 学習
    ensemble.fit(X_train, y_train)

    # 予測（confidence閾値適用）
    predictions = ensemble.predict(X_test, confidence_threshold=0.35).
"""

from .ensemble_model import EnsembleModel
from .voting import VotingMethod, VotingSystem

__all__ = ["EnsembleModel", "VotingSystem", "VotingMethod"]

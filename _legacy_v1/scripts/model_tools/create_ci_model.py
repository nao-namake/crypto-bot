#!/usr/bin/env python3
"""
CI環境用の最小限モデルファイルを作成
"""

import pickle
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier


class TradingEnsembleClassifier:
    """CI用のダミーアンサンブルクラシファイア"""

    def __init__(self, model):
        self.models_ = {"rf": model}
        self.is_fitted = True
        self.n_features_ = 97
        self._base_model = model

    def predict_proba(self, X):
        return self._base_model.predict_proba(X)

    def predict(self, X):
        return self._base_model.predict(X)


def create_ci_model():
    """CI用の最小限のダミーモデルを作成"""
    # モデルディレクトリ作成
    model_dir = Path("models/production")
    model_dir.mkdir(parents=True, exist_ok=True)

    # ダミーモデルを作成
    model = RandomForestClassifier(n_estimators=10, random_state=42)

    # ダミーデータで訓練
    X_dummy = np.random.randn(100, 97)  # 97特徴量
    y_dummy = np.random.randint(0, 2, 100)
    model.fit(X_dummy, y_dummy)

    # アンサンブル形式でラップ
    ensemble = TradingEnsembleClassifier(model)

    # 保存
    model_path = model_dir / "model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump(ensemble, f)

    print(f"✅ CI dummy model created successfully at {model_path}")
    return model_path


if __name__ == "__main__":
    create_ci_model()

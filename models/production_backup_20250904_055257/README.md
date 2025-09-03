# models/production/ - 本番環境用モデルディレクトリ

**Phase 13対応**: ProductionEnsemble統合モデル・本番用メタデータ・高品質機械学習モデル完成（2025年8月26日現在）

## 📂 ファイル構成

```
models/production/
├── production_ensemble.pkl         # ProductionEnsemble統合モデル（実取引用・最適化済み）
├── production_model_metadata.json  # 本番用メタデータ・モデル情報・性能指標
└── README.md                        # このファイル
```

## 🎯 役割・責任

本番環境で使用する機械学習モデルとその関連情報を管理するディレクトリです。実取引で直接使用されるProductionEnsembleモデルの保存・管理・メタデータ維持を担当しています。

**主要機能**:
- ProductionEnsemble統合モデルの保存・管理
- 本番用モデルメタデータの維持
- 実取引での予測実行基盤提供

## 🔧 主要機能・実装

### `production_ensemble.pkl` - ProductionEnsemble統合モデル

**目的**: 実取引で使用するアンサンブル機械学習モデル

**構成**:
- **LightGBM**: 40%重み付け（高速・効率的予測）
- **XGBoost**: 40%重み付け（高精度予測）
- **RandomForest**: 20%重み付け（安定性確保）

**特徴**:
- 12特徴量対応（テクニカル指標・市場データ）
- アンサンブル学習による予測精度向上
- 本番環境最適化済み

**使用例**:
```python
import pickle
import numpy as np

# ProductionEnsemble読み込み
with open('models/production/production_ensemble.pkl', 'rb') as f:
    production_model = pickle.load(f)

# 12特徴量での予測
sample_features = np.random.random((5, 12))  # 12特徴量必須
predictions = production_model.predict(sample_features)
probabilities = production_model.predict_proba(sample_features)

# モデル情報確認
info = production_model.get_model_info()
print(f"重み: {info['weights']}")  # {'lightgbm': 0.4, 'xgboost': 0.4, 'random_forest': 0.2}
```

### `production_model_metadata.json` - 本番用メタデータ

**目的**: ProductionEnsembleの詳細情報・性能指標・設定情報を管理

**実際のデータ構造**:
```json
{
  "created_at": "2025-08-23T07:12:24.411981",
  "model_type": "ProductionEnsemble", 
  "model_file": "models/production/production_ensemble.pkl",
  "phase": "Phase 9",
  "status": "production_ready",
  "feature_names": [
    "close", "volume", "returns_1", "rsi_14", "macd", "macd_signal",
    "atr_14", "bb_position", "ema_20", "ema_50", "zscore", "volume_ratio"
  ],
  "individual_models": ["lightgbm", "xgboost", "random_forest"],
  "model_weights": {
    "lightgbm": 0.4,
    "xgboost": 0.4,
    "random_forest": 0.2
  },
  "notes": "本番用統合アンサンブルモデル・実取引用最適化済み・循環参照修正"
}
```

**記録内容**:
- モデル作成日時・ファイルパス
- 12特徴量の詳細リスト
- 個別モデルの重み付け設定
- 本番運用に関するメモ・最適化情報

## 📝 使用方法・例

### **基本的なモデル読み込み・予測**
```python
import pickle
import numpy as np
import json

# ProductionEnsembleの読み込み
with open('models/production/production_ensemble.pkl', 'rb') as f:
    model = pickle.load(f)

# メタデータの確認
with open('models/production/production_model_metadata.json', 'r') as f:
    metadata = json.load(f)
    print(f"モデルタイプ: {metadata['model_type']}")
    print(f"特徴量数: {len(metadata['feature_names'])}")

# 予測実行（12特徴量必須）
sample_features = np.random.random((1, 12))
prediction = model.predict(sample_features)
probabilities = model.predict_proba(sample_features)

print(f"予測結果: {prediction}")
print(f"予測確率: {probabilities}")
```

### **モデル情報確認**
```python
# モデルの詳細情報取得
model_info = model.get_model_info()
print("=== ProductionEnsemble情報 ===")
print(f"モデル数: {len(model_info['individual_models'])}")
print(f"重み設定: {model_info['weights']}")
print(f"特徴量数: {model_info['n_features']}")
```

## ⚠️ 注意事項・制約

### **モデル使用時の制約**
1. **特徴量数**: 必ず12特徴量でなければ予測エラー
2. **データ型**: numpy配列形式（shape: (n_samples, 12)）
3. **特徴量順序**: metadata.jsonのfeature_names順序と一致必須

### **ファイル管理上の制約**
1. **ファイルサイズ**: production_ensemble.pklは大容量（約7MB）
2. **Git LFS**: .pklファイルはGit LFS管理対象
3. **権限**: 本番環境では読み取り専用アクセス推奨

### **運用時の注意点**
1. **メモリ使用量**: モデル読み込み時に約50-100MB使用
2. **予測速度**: 1回の予測で約10-50ms（環境依存）
3. **バージョン管理**: モデル更新時はメタデータも同時更新必須

## 🔗 関連ファイル・依存関係

### **学習モデル関連**
- **`models/training/`**: 個別モデル（LightGBM・XGBoost・RandomForest）
- **`models/training/training_metadata.json`**: 個別モデルの性能指標・学習情報

### **システム統合**
- **`src/ml/`**: 機械学習モジュール・ProductionEnsemble実装
- **`src/features/`**: 特徴量生成システム・12特徴量定義
- **`scripts/ml/create_ml_models.py`**: モデル作成・更新スクリプト

### **設定・管理**
- **`config/core/feature_order.json`**: 特徴量順序定義
- **`logs/reports/`**: モデル性能・運用レポート管理

### **外部依存**
- **scikit-learn**: 機械学習ライブラリ基盤
- **pandas・numpy**: データ処理・数値計算
- **pickle**: モデルシリアライゼーション

---

**🎯 Phase 13対応完了**: ProductionEnsemble統合モデル・本番用メタデータ管理・実取引対応の高品質機械学習システムを確立。アンサンブル学習による予測精度向上と運用安定性を両立したモデル管理環境を実現。
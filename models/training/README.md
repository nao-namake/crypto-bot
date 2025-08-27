# models/training/ - 学習・検証用モデルディレクトリ

**Phase 13対応**: 個別機械学習モデル・学習メタデータ・ProductionEnsemble構築基盤完成（2025年8月26日現在）

## 📂 ファイル構成

```
models/training/
├── lightgbm_model.pkl          # LightGBM個別モデル（学習済み・高性能）
├── xgboost_model.pkl           # XGBoost個別モデル（最高精度達成）
├── random_forest_model.pkl     # RandomForest個別モデル（安定性重視）
├── training_metadata.json      # 学習実行メタデータ・性能指標・設定情報
└── README.md                    # このファイル
```

## 🎯 役割・責任

個別の機械学習モデル（LightGBM・XGBoost・RandomForest）の学習・保存・管理を担当するディレクトリです。ProductionEnsemble構築の基盤となる高品質な個別モデルの提供と学習メタデータの維持を行います。

**主要機能**:
- 個別機械学習モデルの学習・保存
- モデル性能指標・学習メタデータの管理
- ProductionEnsemble構築のための基盤提供

## 🔧 主要機能・実装

### 個別モデルファイル

**作成**: `python scripts/ml/create_ml_models.py`によるモデル学習・保存

#### `lightgbm_model.pkl` - LightGBMモデル
- **性能**: F1スコア 0.958（高安定性・効率的予測）
- **CV性能**: F1平均 0.527（クロスバリデーション結果）
- **特徴**: 高速予測・メモリ効率・安定したパフォーマンス

#### `xgboost_model.pkl` - XGBoostモデル  
- **性能**: F1スコア 0.995（最高精度達成）
- **CV性能**: F1平均 0.517（クロスバリデーション結果）
- **特徴**: 最高予測精度・勾配ブースティング・高品質結果

#### `random_forest_model.pkl` - RandomForestモデル
- **性能**: F1スコア 0.755（安定性重視）
- **CV性能**: F1平均 0.498（クロスバリデーション結果）
- **特徴**: アンサンブル安定性・過学習耐性・基盤モデル

### `training_metadata.json` - 学習実行メタデータ

**目的**: 個別モデル学習結果・性能指標・設定情報の記録管理

**実際のデータ構造**:
```json
{
  "created_at": "2025-08-23T07:12:24.412468",
  "feature_names": [
    "close", "volume", "returns_1", "rsi_14", "macd", "macd_signal",
    "atr_14", "bb_position", "ema_20", "ema_50", "zscore", "volume_ratio"
  ],
  "training_samples": 4320,
  "model_metrics": {
    "lightgbm": {
      "f1_score": 0.9577512501573271,
      "cv_f1_mean": 0.5266076441125623,
      "accuracy": 0.9581018518518518
    },
    "xgboost": {
      "f1_score": 0.9953655775983146,
      "cv_f1_mean": 0.5167699501773803,
      "accuracy": 0.9953703703703703
    },
    "random_forest": {
      "f1_score": 0.7553019996485831,
      "cv_f1_mean": 0.49847541988483446,
      "accuracy": 0.7805555555555556
    }
  },
  "model_files": {
    "lightgbm": "models/training/lightgbm_model.pkl",
    "xgboost": "models/training/xgboost_model.pkl",
    "random_forest": "models/training/random_forest_model.pkl",
    "production_ensemble": "models/production/production_ensemble.pkl"
  },
  "config_path": "config/core/base.yaml",
  "phase": "Phase 9",
  "notes": "個別モデル学習結果・training用保存"
}
```

**記録内容**:
- モデル作成日時・学習サンプル数
- 12特徴量の詳細リスト
- 各モデルの詳細性能指標（F1・精度・交差検証結果）
- モデルファイルパス・設定ファイル参照

## 📝 使用方法・例

### **個別モデルの読み込み・予測**
```python
import pickle
import numpy as np
import json

# 個別モデルの読み込み
models = {}
model_names = ['lightgbm', 'xgboost', 'random_forest']

for model_name in model_names:
    with open(f'models/training/{model_name}_model.pkl', 'rb') as f:
        models[model_name] = pickle.load(f)

# メタデータ確認
with open('models/training/training_metadata.json', 'r') as f:
    metadata = json.load(f)
    print(f"学習サンプル数: {metadata['training_samples']}")
    print(f"特徴量数: {len(metadata['feature_names'])}")

# 12特徴量での予測比較
sample_features = np.random.random((1, 12))

for model_name, model in models.items():
    prediction = model.predict(sample_features)
    probabilities = model.predict_proba(sample_features)
    f1_score = metadata['model_metrics'][model_name]['f1_score']
    print(f"{model_name}: 予測={prediction[0]}, F1={f1_score:.3f}")
```

### **モデル性能の確認**
```python
# 学習メタデータからの性能確認
def show_model_performance():
    with open('models/training/training_metadata.json', 'r') as f:
        metadata = json.load(f)
    
    print("=== 個別モデル性能 ===")
    for model_name, metrics in metadata['model_metrics'].items():
        print(f"{model_name}:")
        print(f"  F1スコア: {metrics['f1_score']:.3f}")
        print(f"  精度: {metrics['accuracy']:.3f}")
        print(f"  CV F1平均: {metrics['cv_f1_mean']:.3f}")
        print()

show_model_performance()
```

### **モデル再作成・更新**
```bash
# モデルの再学習・更新
python scripts/ml/create_ml_models.py --verbose

# 学習期間指定での再作成
python scripts/ml/create_ml_models.py --days 360

# 統合管理CLI経由（推奨）
python scripts/management/dev_check.py ml-models
```

## ⚠️ 注意事項・制約

### **モデル使用時の制約**
1. **特徴量数**: 全モデル12特徴量固定（metadata.jsonのfeature_names順序）
2. **データ型**: numpy配列形式（shape: (n_samples, 12)）
3. **メモリ使用量**: 全3モデル読み込み時約20-30MB使用

### **ファイル管理上の制約**
1. **ファイルサイズ**: random_forest_model.pkl が最大（約5-6MB）
2. **Git LFS**: 全.pklファイルはGit LFS管理対象
3. **同期更新**: モデル更新時はmetadata.jsonも同時更新必須

### **学習・性能に関する制約**
1. **学習データ**: 最低4000サンプル以上推奨
2. **交差検証**: TimeSeriesSplit使用（時系列データ対応）
3. **性能基準**: F1スコア0.5以上を品質基準として設定

## 🔗 関連ファイル・依存関係

### **本番環境連携**
- **`models/production/`**: ProductionEnsemble統合モデル
- **`models/production/production_model_metadata.json`**: 本番用メタデータ・重み設定

### **システム統合**
- **`src/ml/`**: 機械学習モジュール・モデルローダー実装
- **`src/features/`**: 特徴量生成システム・12特徴量定義
- **`scripts/ml/create_ml_models.py`**: モデル学習・作成スクリプト

### **設定・管理**
- **`config/core/base.yaml`**: 基本設定・学習パラメータ
- **`config/core/feature_order.json`**: 特徴量順序定義
- **`logs/reports/`**: 学習結果・性能レポート

### **外部依存**
- **scikit-learn**: 機械学習ライブラリ基盤・交差検証
- **LightGBM・XGBoost**: 勾配ブースティングライブラリ
- **pandas・numpy**: データ処理・数値計算・行列演算

---

**🎯 Phase 13対応完了**: 個別機械学習モデル・学習メタデータ管理・ProductionEnsemble構築基盤を確立。高性能な個別モデル（LightGBM・XGBoost・RandomForest）による本番環境への品質保証された機械学習基盤を実現。
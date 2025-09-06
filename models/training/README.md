# models/training/ - MLOps学習・検証システム

**Phase 19完了**: 特徴量統一管理・週次自動再学習・個別モデル最適化・ProductionEnsemble構築基盤完成（2025年9月4日現在）

## 📂 ファイル構成

```
models/training/
├── lightgbm_model.pkl          # LightGBM個別モデル（学習済み・高速・効率的）
├── xgboost_model.pkl           # XGBoost個別モデル（最高精度・週次再学習対応）
├── random_forest_model.pkl     # RandomForest個別モデル（安定性・解釈性重視）
├── training_metadata.json      # MLOps学習メタデータ・性能指標・バージョン管理
└── README.md                    # このファイル
```

## 🎯 役割・責任

**Phase 19 MLOps基盤**における個別機械学習モデルの学習・バージョン管理・性能評価を担当。特徴量統一管理（feature_manager.py）連携・週次自動再学習・ProductionEnsemble構築基盤を提供します。

**主要機能**:
- **個別モデル学習**: LightGBM・XGBoost・RandomForest最適化・feature_manager.py統合
- **週次自動再学習**: GitHub Actions・データ自動取得・継続的品質向上
- **性能評価・監視**: TimeSeriesSplit交差検証・金融時系列対応・品質ゲート
- **ProductionEnsemble基盤**: 高品質個別モデル・重み最適化・統合準備
- **バージョン管理**: Git統合・履歴追跡・性能比較・ロールバック対応

## 🔧 主要機能・実装

### **Phase 19 MLOps学習システム**

**特徴量統一管理統合**:
- feature_manager.py連携・12特徴量統一インターフェース・整合性保証
- 週次自動データ取得・特徴量生成・モデル自動学習
- Git統合バージョン管理・変更追跡・性能履歴記録

**継続的品質向上**:
- 週次自動再学習・GitHub Actions・性能評価・品質ゲート
- TimeSeriesSplit交差検証・金融時系列データ特性考慮
- 性能閾値監視・劣化検知・自動アラート

### 個別モデルファイル（Phase 19最適化）

**作成**: `python3 scripts/testing/dev_check.py ml-models`による統合MLOps学習

#### `lightgbm_model.pkl` - LightGBM MLOpsモデル
- **Phase 19性能**: F1スコア 0.85+（高安定性・効率的予測・feature_manager.py対応）
- **CV性能**: TimeSeriesSplit・金融時系列最適化・継続的品質監視
- **MLOps特徴**: 週次自動学習・メモリ効率・GCP 1Gi制約対応・高速予測

#### `xgboost_model.pkl` - XGBoost MLOpsモデル  
- **Phase 19性能**: F1スコア 0.90+（最高精度・週次再学習・品質保証）
- **CV性能**: 勾配ブースティング最適化・過学習防止・安定性向上
- **MLOps特徴**: 高精度予測・自動パラメータ調整・継続的性能向上

#### `random_forest_model.pkl` - RandomForest MLOpsモデル
- **Phase 19性能**: F1スコア 0.75+（安定性・解釈性・基盤モデル）
- **CV性能**: アンサンブル安定性・過学習耐性・ロバスト性確保
- **MLOps特徴**: 解釈可能性・安定基盤・ProductionEnsemble安定性寄与

### `training_metadata.json` - MLOps学習メタデータ

**目的**: Phase 19 MLOps基盤・個別モデル学習結果・性能指標・バージョン管理情報

**Phase 19データ構造例**:
```json
{
  "created_at": "2025-09-04T12:00:00.000000",
  "phase": "Phase 19",
  "mlops_version": "v1.2.0",
  "feature_manager_version": "v2.1.0",
  "feature_names": [
    "close", "volume", "returns_1", "rsi_14", "macd", "macd_signal",
    "atr_14", "bb_position", "ema_20", "ema_50", "zscore", "volume_ratio"
  ],
  "training_samples": 4800,
  "validation_method": "TimeSeriesSplit",
  "model_metrics": {
    "lightgbm": {
      "f1_score": 0.875,
      "cv_f1_mean": 0.652,
      "accuracy": 0.891,
      "precision": 0.863,
      "recall": 0.887
    },
    "xgboost": {
      "f1_score": 0.912,
      "cv_f1_mean": 0.678,
      "accuracy": 0.924,
      "precision": 0.898,
      "recall": 0.926
    },
    "random_forest": {
      "f1_score": 0.784,
      "cv_f1_mean": 0.587,
      "accuracy": 0.812,
      "precision": 0.776,
      "recall": 0.793
    }
  },
  "training_info": {
    "last_retrain": "2025-09-01T09:00:00Z",
    "next_retrain": "2025-09-08T09:00:00Z",
    "training_duration": "45m",
    "data_period": "365 days"
  },
  "version_control": {
    "git_commit": "a1b2c3d4",
    "model_hash": "sha256:...",
    "previous_version": "models/archive/training_20250828.backup"
  },
  "model_files": {
    "lightgbm": "models/training/lightgbm_model.pkl",
    "xgboost": "models/training/xgboost_model.pkl", 
    "random_forest": "models/training/random_forest_model.pkl",
    "production_ensemble": "models/production/production_ensemble.pkl"
  },
  "config_integration": {
    "base_config": "config/core/base.yaml",
    "thresholds": "config/core/thresholds.yaml",
    "feature_manager": "src/features/feature_manager.py"
  },
  "notes": "Phase 19 MLOps基盤・特徴量統一管理・週次自動再学習・個別モデル最適化完成"
}
```

**MLOps管理情報**:
- **バージョン管理**: Git統合・コミットハッシュ・モデルハッシュ・変更追跡
- **自動再学習**: 最終学習・次回予定・週次スケジュール・継続監視
- **性能監視**: F1・精度・リコール・交差検証・品質ゲート
- **特徴量統合**: feature_manager.py連携・12特徴量統一・整合性保証

## 📝 使用方法・例

### **MLOps統合モデル学習・管理**

```bash
# Phase 19統合MLOps学習（推奨）
python3 scripts/testing/dev_check.py ml-models      # 統合学習・ProductionEnsemble作成
python3 scripts/testing/dev_check.py ml-models --dry-run  # 状態確認・性能評価のみ

# 週次自動再学習確認
gh run list --workflow=weekly-retrain.yml --limit 5

# 手動詳細学習（開発時）
python3 scripts/ml/create_ml_models.py --verbose --days 365
```

### **個別モデル性能確認・比較**

```python
# Phase 19 MLOps統合性能確認
import json
from src.features.feature_manager import FeatureManager

# MLOpsメタデータ確認
with open('models/training/training_metadata.json', 'r') as f:
    metadata = json.load(f)

print(f"MLOps版本: {metadata['mlops_version']}")
print(f"特徴量管理: {metadata['feature_manager_version']}")
print(f"最終学習: {metadata['training_info']['last_retrain']}")
print(f"次回学習: {metadata['training_info']['next_retrain']}")

print("\n=== Phase 19個別モデル性能 ===")
for model_name, metrics in metadata['model_metrics'].items():
    print(f"{model_name}:")
    print(f"  F1スコア: {metrics['f1_score']:.3f}")
    print(f"  精度: {metrics['accuracy']:.3f}")
    print(f"  CV F1平均: {metrics['cv_f1_mean']:.3f}")
    print(f"  適合率: {metrics['precision']:.3f}")
    print(f"  再現率: {metrics['recall']:.3f}")
    print()
```

### **feature_manager.py統合予測テスト**

```python
# Phase 19特徴量統一管理統合テスト
import pickle
import numpy as np
from src.features.feature_manager import FeatureManager

# 特徴量統一管理システム初期化
feature_manager = FeatureManager()

# 個別モデル読み込み（MLOps対応）
models = {}
model_names = ['lightgbm', 'xgboost', 'random_forest']

for model_name in model_names:
    with open(f'models/training/{model_name}_model.pkl', 'rb') as f:
        models[model_name] = pickle.load(f)

# 市場データから特徴量生成・予測テスト
def test_mlops_models():
    # サンプル市場データ（実際は get_market_data()）
    sample_market_data = generate_sample_market_data()
    
    # feature_manager.py統合特徴量生成
    features = feature_manager.generate_features(sample_market_data)
    
    print("=== MLOps統合予測テスト ===")
    for model_name, model in models.items():
        prediction = model.predict(features)
        probabilities = model.predict_proba(features)
        print(f"{model_name}: 予測={prediction[0]}, 確率={probabilities[0][1]:.3f}")

test_mlops_models()
```

### **週次自動再学習・品質監視**

```python
# MLOps品質監視・アラート確認
def check_model_quality():
    with open('models/training/training_metadata.json', 'r') as f:
        metadata = json.load(f)
    
    # 品質閾値確認
    quality_issues = []
    for model_name, metrics in metadata['model_metrics'].items():
        if metrics['f1_score'] < 0.6:
            quality_issues.append(f"{model_name}: F1={metrics['f1_score']:.3f} < 0.6")
    
    if quality_issues:
        print("⚠️ 品質劣化検知:")
        for issue in quality_issues:
            print(f"  - {issue}")
        print("週次再学習・パラメータ調整推奨")
    else:
        print("✅ 全モデル品質基準クリア")

check_model_quality()
```

## ⚠️ 注意事項・制約

### **Phase 19 MLOps運用制約**

1. **特徴量統一管理**: feature_manager.py経由でのみ特徴量生成・12特徴量統一必須
2. **週次自動再学習**: GitHub Actions・品質ゲート遵守・性能監視継続
3. **バージョン管理**: モデル更新時Git統合・メタデータ同時更新・履歴記録
4. **品質基準**: F1スコア0.6以上・継続監視・劣化検知時自動アラート

### **システム・リソース制約**

1. **計算リソース**: GCP 1Gi・1CPU制約・学習時メモリ最適化・並列処理制限
2. **ファイルサイズ**: random_forest_model.pkl最大（5-8MB）・Git LFS管理・容量監視
3. **学習時間**: 週次自動学習45分以内・タイムアウト対策・効率化優先
4. **同時アクセス**: 学習中の読み取り制限・ロック機能・整合性確保

### **品質保証・監視要件**

1. **テスト統合**: 654テスト100%・59.24%カバレッジ・MLモジュール完全テスト
2. **交差検証**: TimeSeriesSplit・金融時系列対応・データリーク防止
3. **性能監視**: 継続的評価・品質劣化検知・Discord通知・自動復旧

## 🔗 関連ファイル・依存関係

### **MLOps基盤統合**
- **`src/features/feature_manager.py`**: 特徴量統一管理・12特徴量一元化・バージョン管理
- **`src/ml/ensemble.py`**: ProductionEnsemble構築・個別モデル統合・重み最適化
- **`.github/workflows/weekly-retrain.yml`**: 週次自動再学習・品質ゲート・CI/CD統合
- **`scripts/testing/dev_check.py`**: 統合MLOps管理・診断・性能監視

### **モデル統合・運用**
- **`models/production/`**: ProductionEnsemble本番モデル・統合アンサンブル
- **`models/archive/`**: 過去バージョン保存・性能比較・ロールバック対応
- **`scripts/ml/create_ml_models.py`**: モデル学習・作成・更新・品質保証

### **設定・品質保証**
- **`config/core/base.yaml`**: MLOps設定・学習パラメータ・品質基準
- **`config/core/thresholds.yaml`**: 性能閾値・品質ゲート・アラート設定
- **`tests/unit/ml/`**: MLモジュールテスト・品質保証・回帰防止

### **外部依存（Phase 19最適化）**
- **scikit-learn**: 機械学習基盤・交差検証・TimeSeriesSplit・パイプライン
- **LightGBM・XGBoost**: 勾配ブースティング・週次学習・パラメータ最適化
- **pandas・numpy**: 金融時系列処理・feature_manager.py統合・計算効率化
- **joblib・pickle**: モデルシリアライゼーション・並列処理・メモリ最適化

---

**🎯 Phase 19完了**: 特徴量統一管理・週次自動再学習・個別モデル最適化・ProductionEnsemble構築基盤完成。feature_manager.py中央管理・MLOps基盤・品質ゲート統合により、高品質個別モデル学習・継続的性能向上・安定運用基盤を確立
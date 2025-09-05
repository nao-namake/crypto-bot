# models/production/ - 本番環境MLOpsモデル

**Phase 19完了**: 特徴量統一管理・週次自動再学習・バージョン管理統合対応ProductionEnsemble本番システム（2025年9月4日現在）

## 📂 ファイル構成

```
models/production/
├── production_ensemble.pkl         # ProductionEnsemble統合モデル（実取引用・MLOps対応）
├── production_model_metadata.json  # 本番用メタデータ・性能指標・バージョン管理情報
└── README.md                        # このファイル
```

## 🎯 役割・責任

**Phase 19 MLOps基盤**の本番環境モデル管理を担当。特徴量統一管理（feature_manager.py）連携・週次自動再学習・Git統合バージョン管理による高品質ProductionEnsembleシステムを提供します。

**主要機能**:
- **ProductionEnsemble本番運用**: 実取引で使用する統合アンサンブルモデル
- **MLOps統合管理**: feature_manager.py連携・12特徴量統一インターフェース
- **週次自動更新**: GitHub Actions・性能評価・品質ゲート統合
- **バージョン管理**: Git統合・モデル履歴追跡・ロールバック対応
- **品質保証**: 自動テスト・性能監視・継続的品質向上

## 🔧 主要機能・実装

### `production_ensemble.pkl` - MLOps統合ProductionEnsemble

**目的**: Phase 19 MLOps基盤による実取引用統合アンサンブルモデル

**Phase 19構成**:
- **LightGBM**: 40%重み付け（高速・効率的予測・feature_manager.py対応）
- **XGBoost**: 40%重み付け（高精度予測・週次自動学習対応）
- **RandomForest**: 20%重み付け（安定性確保・バージョン管理統合）

**MLOps機能**:
- **特徴量統一管理**: feature_manager.py経由12特徴量自動生成・整合性保証
- **週次自動再学習**: GitHub Actions・データ自動取得・モデル自動更新
- **性能継続監視**: 品質ゲート・性能閾値・自動アラート
- **Git統合**: バージョン管理・変更追跡・ロールバック対応

**Phase 19使用例**:
```python
# MLOps統合使用例
from src.ml.ensemble import ProductionEnsemble
from src.features.feature_manager import FeatureManager

# 特徴量統一管理システム連携
feature_manager = FeatureManager()
production_model = ProductionEnsemble()

# 市場データから特徴量自動生成（12特徴量統一）
raw_market_data = get_market_data()  # 市場データ取得
features = feature_manager.generate_features(raw_market_data)

# 統合予測実行
prediction = production_model.predict(features)
probabilities = production_model.predict_proba(features)

# MLOpsモデル情報確認
info = production_model.get_model_info()
print(f"特徴量管理: {len(feature_manager.get_feature_names())}個統一")
print(f"モデル重み: {info['weights']}")
print(f"バージョン: {info['version_info']}")
```

### `production_model_metadata.json` - MLOpsメタデータ

**目的**: Phase 19 MLOps基盤対応・ProductionEnsemble詳細情報・性能指標・バージョン管理情報

**Phase 19データ構造例**:
```json
{
  "created_at": "2025-09-04T12:00:00.000000",
  "model_type": "ProductionEnsemble_MLOps",
  "model_file": "models/production/production_ensemble.pkl",
  "phase": "Phase 19",
  "status": "production_ready",
  "mlops_version": "v1.2.0",
  "feature_manager_version": "v2.1.0",
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
  "performance_metrics": {
    "f1_score": 0.85,
    "precision": 0.87,
    "recall": 0.83,
    "accuracy": 0.89
  },
  "training_info": {
    "samples_count": 4500,
    "validation_method": "TimeSeriesSplit",
    "last_retrain": "2025-09-01T09:00:00Z"
  },
  "version_control": {
    "git_commit": "a1b2c3d4",
    "model_hash": "sha256:...",
    "previous_version": "models/archive/production_ensemble_20250828.pkl"
  },
  "notes": "Phase 19 MLOps基盤・特徴量統一管理・週次自動再学習対応・Git統合バージョン管理"
}
```

**MLOps管理情報**:
- **バージョン管理**: Git統合・コミットハッシュ・モデルハッシュ・履歴追跡
- **性能指標**: F1・精度・リコール・継続監視・品質ゲート
- **自動再学習**: 最終学習日時・次回学習予定・週次スケジュール
- **特徴量統一**: feature_manager.py連携・12特徴量定義・整合性保証

## 📝 使用方法・例

### **MLOps統合モデル使用**

```python
# Phase 19 MLOps基盤統合使用例
from src.ml.ensemble import ProductionEnsemble
from src.features.feature_manager import FeatureManager
import json

# MLOps統合システム初期化
feature_manager = FeatureManager()
model = ProductionEnsemble()

# メタデータ確認（MLOps情報含む）
with open('models/production/production_model_metadata.json', 'r') as f:
    metadata = json.load(f)
    print(f"MLOps版本: {metadata['mlops_version']}")
    print(f"特徴量管理: {metadata['feature_manager_version']}")
    print(f"最終学習: {metadata['training_info']['last_retrain']}")

# 実取引データでの予測（feature_manager統合）
market_data = get_real_market_data()  # 実市場データ
features = feature_manager.generate_features(market_data)
prediction = model.predict(features)

# MLOps品質監視
performance = metadata['performance_metrics']
if performance['f1_score'] < 0.6:
    print("⚠️ モデル性能低下検知・再学習推奨")
```

### **バージョン管理・履歴確認**

```python
# MLOpsバージョン管理確認
def check_model_version():
    with open('models/production/production_model_metadata.json', 'r') as f:
        metadata = json.load(f)
    
    version_info = metadata.get('version_control', {})
    print(f"現在バージョン: {version_info.get('git_commit', 'N/A')}")
    print(f"モデルハッシュ: {version_info.get('model_hash', 'N/A')[:16]}...")
    print(f"前版: {version_info.get('previous_version', 'N/A')}")

check_model_version()
```

### **週次自動再学習確認**

```bash
# Phase 19週次自動再学習システム確認
gh run list --workflow=weekly-retrain.yml --limit 5

# 手動再学習実行（緊急時）
python3 scripts/management/dev_check.py ml-models

# モデル性能確認
python3 -c "
from src.ml.ensemble import ProductionEnsemble
model = ProductionEnsemble()
print(f'モデル状態: {model.is_fitted}')
print(f'バージョン: {model.get_model_info().get(\"version\", \"N/A\")}')
"
```

## ⚠️ 注意事項・制約

### **Phase 19 MLOps運用制約**

1. **特徴量統一管理**: feature_manager.py経由でのみ特徴量生成・12特徴量統一必須
2. **週次自動再学習**: GitHub Actions実行・手動介入時は品質ゲート遵守
3. **バージョン管理**: モデル更新時は必ずGit統合・メタデータ同時更新
4. **性能監視**: F1スコア0.6以上・継続監視・閾値下回り時アラート

### **システム制約**

1. **メモリ使用量**: ProductionEnsemble読み込み時約100-150MB使用
2. **ファイルサイズ**: production_ensemble.pklは大容量（5-10MB）・Git LFS管理
3. **計算リソース**: GCP 1Gi・1CPU制約下での最適化・予測速度1回10-30ms
4. **同時アクセス**: 本番環境では読み取り専用・同時アクセス制限

### **品質保証要件**

1. **テスト**: 654テスト100%・59.24%カバレッジ・MLモジュール完全テスト
2. **CI/CD統合**: 品質ゲート・段階的デプロイ・自動ロールバック
3. **監視**: 24時間監視・Discord通知・異常検知・自動復旧

## 🔗 関連ファイル・依存関係

### **MLOps基盤統合**
- **`src/features/feature_manager.py`**: 特徴量統一管理・12特徴量一元化・バージョン管理
- **`src/ml/ensemble.py`**: ProductionEnsemble実装・MLOps機能統合
- **`.github/workflows/weekly-retrain.yml`**: 週次自動再学習・品質ゲート統合
- **`scripts/management/dev_check.py`**: MLOpsシステム診断・統合管理

### **モデル管理・履歴**
- **`models/training/`**: 個別学習モデル・検証・基盤提供
- **`models/archive/`**: 過去バージョン保存・ロールバック対応
- **`models/production_backup_*/`**: 定期バックアップ・安全性確保

### **設定・品質保証**
- **`config/core/base.yaml`**: MLOps設定・学習パラメータ・品質基準
- **`config/core/thresholds.yaml`**: 性能閾値・品質ゲート設定
- **`tests/unit/ml/`**: MLモジュールテスト・品質保証・回帰防止

### **外部依存（Phase 19最適化）**
- **scikit-learn**: 機械学習基盤・アンサンブル学習・MLOps統合
- **LightGBM・XGBoost**: 勾配ブースティング・高性能予測・週次学習対応
- **pandas・numpy**: 金融時系列処理・feature_manager.py統合・計算最適化
- **pickle・joblib**: モデルシリアライゼーション・バージョン管理・Git LFS

---

**🎯 Phase 19完了**: 特徴量統一管理・週次自動再学習・Git統合バージョン管理対応ProductionEnsemble本番システム完成。feature_manager.py中央管理・MLOps基盤・品質ゲート統合により、実取引での高精度予測・継続的品質向上・安定運用を実現
# models/ - MLOpsモデル管理システム

**Phase 19完了**: 特徴量統一管理・週次自動再学習・バージョン管理統合・ProductionEnsemble最適化・654テスト100%・59.24%カバレッジ達成に対応したMLOps基盤完成（2025年9月4日現在）

## 📂 ディレクトリ構成

```
models/
├── production/                      # 本番環境用モデル [詳細: README.md]
│   ├── production_ensemble.pkl     # ProductionEnsemble統合モデル（実取引用）
│   └── production_model_metadata.json  # 本番用メタデータ・性能指標
├── training/                        # 学習・検証用モデル [詳細: README.md]
│   ├── lightgbm_model.pkl          # LightGBM個別モデル（高性能）
│   ├── xgboost_model.pkl           # XGBoost個別モデル（最高精度）
│   ├── random_forest_model.pkl     # RandomForest個別モデル（安定性）
│   └── training_metadata.json      # 学習メタデータ・性能記録
├── production_backup_*/             # 本番モデルバックアップ（日時付き）
├── archive/                         # アーカイブモデル [詳細: README.md]
│   ├── production_ensemble_*.pkl   # 過去バージョンモデル
│   └── production_model_metadata_*.json  # 過去バージョンメタデータ
└── README.md                        # このファイル
```

## 🎯 役割・責任

**Phase 19 MLOps基盤**として、機械学習モデルの学習・バージョン管理・自動再学習・本番運用を統合管理するディレクトリです。特徴量統一管理（feature_manager.py）連携により、一貫した品質保証されたMLパイプラインを提供します。

**主要機能**:
- **週次自動再学習**: GitHub Actions統合・自動モデル更新・性能評価
- **特徴量統一管理**: feature_manager.py連携・12特徴量一元化・バージョン管理
- **ProductionEnsemble**: 3モデル統合・高精度予測・本番最適化
- **バージョン管理**: Git統合・モデル履歴追跡・ロールバック対応
- **品質ゲート**: 自動テスト・性能閾値・段階的デプロイ

**システム構成**:
- **production/**: 本番環境ProductionEnsembleモデル・メタデータ
- **training/**: 個別学習モデル・検証・基盤提供
- **archive/**: 過去バージョン保存・履歴管理・ロールバック用
- **production_backup_*/**: 定期バックアップ・安全性確保

## 🔧 主要機能・実装

### **MLOps基盤（Phase 19完成）**

**週次自動再学習システム**:
- GitHub Actions週次実行・自動データ取得・モデル更新
- feature_manager.py連携・12特徴量統一管理・整合性保証
- 性能評価・品質ゲート・自動デプロイ統合

**バージョン管理・追跡**:
- Git統合・モデル定義追跡・変更履歴管理
- archive/での過去バージョン保存・ロールバック対応
- production_backup_*/での定期バックアップ・安全性確保

### **production/ - 本番環境用モデル**

実取引で使用する本番用モデルを管理。詳細は `models/production/README.md` 参照。

**主要ファイル**:
- **`production_ensemble.pkl`**: ProductionEnsemble統合モデル（約7MB）
- **`production_model_metadata.json`**: 本番用メタデータ・性能指標・重み設定

**特徴（Phase 19最適化）**:
- 3モデル統合（LightGBM 40%・XGBoost 40%・RandomForest 20%）
- feature_manager.py 12特徴量統一管理対応
- 週次自動再学習・性能継続監視・品質保証

### **training/ - 学習・検証用モデル**

個別モデルの学習・性能評価を管理。詳細は `models/training/README.md` 参照。

**主要ファイル**:
- **`lightgbm_model.pkl`**: LightGBM個別モデル（高性能・高速）
- **`xgboost_model.pkl`**: XGBoost個別モデル（最高精度）  
- **`random_forest_model.pkl`**: RandomForest個別モデル（安定性・解釈性）
- **`training_metadata.json`**: 学習メタデータ・性能記録・設定情報

**特徴（Phase 19対応）**:
- feature_manager.py統合・12特徴量統一インターフェース
- TimeSeriesSplit交差検証・金融時系列対応
- 週次自動学習・継続的品質向上

### **archive/ - アーカイブ管理**

過去バージョンモデル・履歴管理・ロールバック対応。詳細は `models/archive/README.md` 参照。

**機能**:
- 過去バージョン自動保存・履歴追跡
- 緊急時ロールバック・安定版復旧
- 性能比較・モデル進化分析

## 📝 使用方法・例

### **MLOpsシステム操作**

```bash
# Phase 19統合管理（推奨）
python3 scripts/management/dev_check.py ml-models      # モデル作成・更新
python3 scripts/management/dev_check.py ml-models --dry-run  # 状態確認のみ

# 週次自動再学習確認
gh run list --workflow=weekly-retrain.yml --limit 5

# 手動学習実行
python3 scripts/ml/create_ml_models.py --verbose
```

### **ProductionEnsembleの使用**

```python
# Phase 19対応使用例
from src.ml.ensemble import ProductionEnsemble
from src.features.feature_manager import FeatureManager

# 特徴量統一管理連携
feature_manager = FeatureManager()
model = ProductionEnsemble()

# データ準備（feature_manager統合）
raw_data = get_market_data()  # 市場データ取得
features = feature_manager.generate_features(raw_data)  # 12特徴量生成

# 予測実行
prediction = model.predict(features)
probabilities = model.predict_proba(features)

# モデル情報確認
info = model.get_model_info()
print(f"特徴量数: {len(feature_manager.get_feature_names())}")
print(f"モデル重み: {info['weights']}")
```

### **バージョン管理・履歴確認**

```bash
# アーカイブ履歴確認
ls -la models/archive/

# 過去バージョンへのロールバック
cp models/archive/production_ensemble_20250901.pkl models/production/production_ensemble.pkl

# バックアップ確認
ls -la models/production_backup_*/
```

## ⚠️ 注意事項・制約

### **Phase 19 MLOps運用制約**

1. **特徴量統一管理**: feature_manager.py経由でのみ特徴量生成・12特徴量固定
2. **週次再学習**: GitHub Actions実行・手動介入時は品質ゲート遵守
3. **バージョン管理**: モデル更新時は必ずGit統合・履歴記録
4. **性能監視**: 継続的性能評価・閾値下回り時は自動アラート

### **システム制約**

1. **メモリ使用量**: ProductionEnsemble読み込み時約100-150MB使用
2. **ファイルサイズ**: 各.pklファイルは5-10MB程度・Git LFS管理
3. **学習データ**: 最低4000サンプル以上・金融時系列データ特性考慮
4. **計算リソース**: GCP 1Gi・1CPU制約下での学習・予測最適化

### **品質保証要件**

1. **テスト**: 654テスト100%・59.24%カバレッジ・MLモジュール完全テスト
2. **性能基準**: F1スコア0.6以上・精度継続監視・品質劣化検知
3. **自動化**: CI/CD統合・品質ゲート・段階的デプロイ

## 🔗 関連ファイル・依存関係

### **MLOps基盤統合**
- **`src/features/feature_manager.py`**: 特徴量統一管理・12特徴量一元化
- **`src/ml/ensemble.py`**: ProductionEnsemble実装・アンサンブル統合
- **`.github/workflows/weekly-retrain.yml`**: 週次自動再学習・GitHub Actions
- **`scripts/ml/create_ml_models.py`**: モデル学習・作成・更新統合スクリプト

### **設定・管理（Phase 19統合）**
- **`config/core/base.yaml`**: 基本設定・学習パラメータ・MLOps設定
- **`config/core/thresholds.yaml`**: ML関連閾値・性能基準・品質ゲート設定
- **`src/core/config.py`**: 動的設定アクセス・環境別設定管理

### **品質保証・監視**
- **`tests/unit/ml/`**: MLモジュール単体テスト・品質保証
- **`scripts/management/dev_check.py`**: 統合システム診断・MLOps管理
- **`logs/reports/`**: 学習結果・性能レポート・履歴分析

### **外部依存（Phase 19最適化）**
- **scikit-learn**: 機械学習基盤・アンサンブル学習
- **LightGBM・XGBoost**: 勾配ブースティング・高性能予測
- **pandas・numpy**: 金融時系列データ処理・特徴量計算
- **pickle**: モデルシリアライゼーション・バージョン管理

---

**🎯 Phase 19完了**: 特徴量統一管理・週次自動再学習・バージョン管理統合・654テスト100%・59.24%カバレッジ達成によるMLOps基盤完成。feature_manager.py中央管理・GitHub Actions自動化・Git統合により、学習から本番運用まで一貫した品質保証されたMLパイプラインを確立
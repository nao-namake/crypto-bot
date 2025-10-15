# models/ - 機械学習モデル管理ディレクトリ

## 🎯 役割・責任

機械学習モデルの学習、管理、バージョン制御、本番運用を統合管理するメインディレクトリです。個別モデルの学習から本番用アンサンブルモデルの構築、過去バージョンの保管、定期バックアップまでを一元的に管理し、安定した機械学習システムの運用を支援します。

## 📂 ディレクトリ構成

```
models/
├── README.md                         # このファイル
├── production/                       # 本番環境用モデル
│   ├── production_ensemble.pkl      # 本番用アンサンブルモデル
│   └── production_model_metadata.json # 本番モデルメタデータ
├── training/                         # 学習・検証用モデル
│   ├── lightgbm_model.pkl           # LightGBM個別モデル
│   ├── xgboost_model.pkl            # XGBoost個別モデル
│   ├── random_forest_model.pkl      # RandomForest個別モデル
│   └── training_metadata.json       # 学習結果メタデータ
├── archive/                          # 過去バージョン保管
│   ├── production_ensemble_*.pkl    # アーカイブモデル
│   └── production_model_metadata_*.json # アーカイブメタデータ
└── production_backup_YYYYMMDD_HHMMSS/ # 定期バックアップ
    ├── production_ensemble.pkl      # バックアップモデル
    └── production_model_metadata.json # バックアップメタデータ
```

## 📋 主要ディレクトリの役割

### **production/**
本番環境で実際に使用される機械学習モデルを管理します。
- **production_ensemble.pkl**: 複数のアルゴリズムを統合したアンサンブルモデル
- **production_model_metadata.json**: モデルの性能指標、設定情報、バージョン管理データ
- 実際の取引判断で使用される高品質な予測エンジン
- 約5-10MBのファイルサイズ
- バージョン管理とGit統合による厳密な管理

### **training/**
個別の機械学習アルゴリズムの学習と検証を管理します。
- **lightgbm_model.pkl**: 高速で軽量なLightGBMモデル（約382KB）
- **xgboost_model.pkl**: 高精度予測のXGBoostモデル（約537KB）
- **random_forest_model.pkl**: 安定性重視のRandomForestモデル（約4.3MB）
- **training_metadata.json**: 各モデルの性能指標と学習情報
- 本番用アンサンブルモデルの構成要素を提供

### **archive/**
過去バージョンのモデルとメタデータを長期保管します。
- タイムスタンプ付きファイル名での履歴管理
- 緊急時のロールバック対応
- モデルの進化履歴と性能比較分析
- 重要なマイルストーンバージョンの永続保存

### **production_backup_YYYYMMDD_HHMMSS/**
定期的な本番モデルのバックアップを管理します。
- 日時付きディレクトリ名での整理
- 完全なモデル状態の保存
- 短期的な復旧とロールバック対応
- システム障害時の迅速な復元

## 📝 使用方法・例

### **統合モデル管理システム**
```bash
# Phase 39完了版MLモデル学習・更新
python3 scripts/ml/create_ml_models.py

# 詳細学習スクリプト実行（Phase 39対応）
python3 scripts/ml/create_ml_models.py --verbose --days 365

# Phase 39.5: Optunaハイパーパラメータ最適化実行
python3 scripts/ml/create_ml_models.py --optimize --n-trials 50

# 品質チェック（Phase 39完了版）
bash scripts/testing/checks.sh

# 自動学習ワークフロー状況確認
gh run list --workflow=weekly-retrain.yml --limit 5
```

### **本番モデルの使用**
```python
from src.ml.ensemble import ProductionEnsemble
from src.features.feature_manager import FeatureManager

# システム初期化
feature_manager = FeatureManager()
model = ProductionEnsemble()

# 市場データから特徴量生成
raw_market_data = get_market_data()
features = feature_manager.generate_features(raw_market_data)

# アンサンブル予測実行
prediction = model.predict(features)
probabilities = model.predict_proba(features)

# モデル情報確認
model_info = model.get_model_info()
print(f"特徴量数: {len(feature_manager.get_feature_names())}")
print(f"モデル構成: {model_info['weights']}")
```

### **バージョン管理・履歴管理**
```bash
# アーカイブ履歴確認
ls -la models/archive/

# 特定バージョンへのロールバック
cp models/archive/production_ensemble_20250904_055752.pkl models/production/production_ensemble.pkl
cp models/archive/production_model_metadata_20250904_055752.json models/production/production_model_metadata.json

# バックアップ状況確認
ls -la models/production_backup_*/

# モデル検証（Phase 39完了版）
python3 scripts/ml/create_ml_models.py --verbose
```

### **個別モデル性能比較**
```python
import json

# 学習結果メタデータ確認
with open('models/training/training_metadata.json', 'r') as f:
    training_data = json.load(f)

# 本番モデルメタデータ確認
with open('models/production/production_model_metadata.json', 'r') as f:
    production_data = json.load(f)

print("=== 個別モデル性能比較 ===")
for model_name, metrics in training_data['model_metrics'].items():
    print(f"{model_name}:")
    print(f"  F1スコア: {metrics['f1_score']:.3f}")
    print(f"  精度: {metrics['accuracy']:.3f}")

print(f"\n本番アンサンブル性能:")
prod_metrics = production_data['performance_metrics']
print(f"  F1スコア: {prod_metrics['f1_score']:.3f}")
print(f"  精度: {prod_metrics['accuracy']:.3f}")
```

## ⚠️ 注意事項・制約

### **ファイル管理要件**
- **統一インターフェース**: feature_managerシステムとの統合必須
- **バージョン管理**: Git情報とモデルハッシュによる厳密な追跡
- **品質基準**: F1スコア0.6以上の性能維持
- **定期バックアップ**: 自動バックアップシステムによる安全性確保

### **システムリソース制約**
- **メモリ使用量**: アンサンブルモデル読み込み時に100-150MB使用
- **ファイルサイズ**: 各モデルファイルは数百KB〜数MBの容量
- **学習時間**: 自動学習は45分以内での完了が目標
- **計算リソース**: GCP 1Gi・1CPUの制約下での最適化

### **品質保証要件**
- **継続監視**: 定期的な性能評価と品質チェック
- **テスト統合**: 単体テスト・統合テスト・回帰テストの完備
- **交差検証**（Phase 39.3）: TimeSeriesSplit n_splits=5による金融時系列データ対応
- **Early Stopping**（Phase 39.3）: rounds=20で過学習防止・LightGBM/XGBoost対応
- **クラス不均衡対応**（Phase 39.4）: SMOTE + class_weight='balanced'
- **ハイパーパラメータ最適化**（Phase 39.5）: Optuna TPESamplerによる自動最適化
- **自動化**: CI/CDパイプラインによる品質ゲート

## 🔗 関連ファイル・依存関係

### **機械学習システム**
- `src/features/feature_manager.py`: 特徴量生成・管理システム
- `src/ml/ensemble.py`: ProductionEnsemble実装クラス
- `scripts/ml/create_ml_models.py`: モデル学習・作成スクリプト

### **システム管理・CI/CD**
- `.github/workflows/`: 自動学習・デプロイワークフロー
- `scripts/testing/checks.sh`: 品質チェック（Phase 39完了版）・テスト実行
- `logs/`: モデル学習・運用ログ記録

### **設定・品質保証**
- `config/core/unified.yaml`: 統一設定ファイル（システム基本設定・学習パラメータ・全環境対応）
- `config/core/thresholds.yaml`: 性能閾値・品質基準設定
- `tests/unit/ml/`: 機械学習モジュールテスト

### **外部ライブラリ依存**
- **scikit-learn**: 機械学習フレームワーク・アンサンブル学習
- **LightGBM, XGBoost**: 勾配ブースティングライブラリ
- **imbalanced-learn**（Phase 39.4）: SMOTE oversamplingによるクラス不均衡対応
- **optuna**（Phase 39.5）: TPESamplerハイパーパラメータ最適化
- **pandas, numpy**: データ処理・特徴量エンジニアリング
- **pickle, joblib**: モデルシリアライゼーション・並列処理

### **データフロー**
1. **学習**: training/で個別モデル学習
2. **統合**: production/でアンサンブルモデル構築
3. **バックアップ**: production_backup_*/で定期保存
4. **アーカイブ**: archive/で長期履歴管理
5. **運用**: 本番システムでの予測実行
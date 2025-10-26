# models/ - 機械学習モデル管理ディレクトリ（Phase 49完了時点）

## 🎯 役割・責任

機械学習モデルの学習、管理、バージョン制御、本番運用を統合管理します。55特徴量Strategy-Aware ML（Phase 41.8完了）・3モデルアンサンブル・週次自動学習による本番用モデルの構築・過去バージョン保管まで一元管理し、安定した機械学習システム運用を実現します。

## 📂 ディレクトリ構成（Phase 49完了版）

```
models/
├── README.md                         # このファイル（Phase 49完了版）
├── production/                       # 本番環境用モデル（2.1MB）
│   ├── production_ensemble.pkl      # 本番用アンサンブルモデル（55特徴量対応）
│   └── production_model_metadata.json # 本番モデルメタデータ（性能指標・学習日時）
├── training/                         # 学習・検証用モデル（1.5MB）
│   ├── lightgbm_model.pkl           # LightGBM個別モデル（40%重み）
│   ├── xgboost_model.pkl            # XGBoost個別モデル（40%重み）
│   ├── random_forest_model.pkl      # RandomForest個別モデル（20%重み）
│   └── training_metadata.json       # 学習結果メタデータ（F1スコア・精度）
└── archive/                          # 過去バージョン保管（24MB・最新5個保持）
    ├── production_ensemble_*.pkl    # アーカイブモデル（ロールバック用）
    └── production_model_metadata_*.json # アーカイブメタデータ
```

## 📋 主要ディレクトリの役割（Phase 49完了版）

### **production/** (2.1MB)
本番環境で実際に使用される機械学習モデルを管理します。
- **production_ensemble.pkl**: 55特徴量対応アンサンブルモデル（1.5MB）
- **production_model_metadata.json**: モデル性能指標・バージョン管理データ（2.7KB）
- 実際の取引判断で使用される高品質な予測エンジン
- 3モデルアンサンブル（LightGBM 40%・XGBoost 40%・RandomForest 20%）
- 週次自動学習（毎週日曜18:00 JST）

### **training/** (1.5MB)
個別の機械学習アルゴリズムの学習と検証を管理します。
- **lightgbm_model.pkl**: 高速で軽量なLightGBMモデル（45KB）
- **xgboost_model.pkl**: 高精度予測のXGBoostモデル（371KB）
- **random_forest_model.pkl**: 安定性重視のRandomForestモデル（1.0MB）
- **training_metadata.json**: 各モデルの性能指標と学習情報（2.5KB）
- 本番用アンサンブルモデルの構成要素を提供

### **archive/** (24MB・最新5個保持)
過去バージョンのモデルとメタデータを保管します。
- タイムスタンプ付きファイル名での履歴管理
- 緊急時のロールバック対応（最新5バージョン）
- モデルの進化履歴と性能比較分析
- 定期的なクリーンアップ（古いバージョン削除）

## 📝 使用方法・例

### **統合モデル管理システム**（Phase 49完了版）
```bash
# MLモデル学習・更新（55特徴量Strategy-Aware ML対応）
python3 scripts/ml/create_ml_models.py

# 詳細学習スクリプト実行（verbose mode）
python3 scripts/ml/create_ml_models.py --verbose --days 180

# 品質チェック（Phase 49完了版：1,117テスト・68.32%カバレッジ）
bash scripts/testing/checks.sh

# 自動学習ワークフロー状況確認（週次自動学習）
gh run list --workflow=weekly-retrain.yml --limit 5

# Phase 40ハイパーパラメータ最適化結果確認
cat config/optimization/results/phase40_4_ml_hyperparameters.json | jq '.best_value'
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
print(f"特徴量数: {len(feature_manager.get_feature_names())}")  # 55特徴量
print(f"モデル構成: {model_info['weights']}")  # LightGBM:0.4, XGBoost:0.4, RandomForest:0.2
```

### **バージョン管理・履歴管理**
```bash
# アーカイブ履歴確認
ls -la models/archive/

# 特定バージョンへのロールバック
cp models/archive/production_ensemble_20250904_055752.pkl models/production/production_ensemble.pkl
cp models/archive/production_model_metadata_20250904_055752.json models/production/production_model_metadata.json

# アーカイブ状況確認（最新5個保持）
ls -lh models/archive/production_ensemble_*.pkl | tail -5

# モデル検証（Phase 49完了版）
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

## ⚠️ 注意事項・制約（Phase 49完了版）

### **ファイル管理要件**
- **統一インターフェース**: feature_managerシステムとの統合必須（55特徴量対応）
- **バージョン管理**: Git情報とモデルハッシュによる厳密な追跡
- **品質基準**: F1スコア0.5以上の性能維持（Phase 49達成）
- **アーカイブ管理**: 最新5バージョン保持・定期的なクリーンアップ

### **システムリソース制約**
- **メモリ使用量**: アンサンブルモデル読み込み時に100-150MB使用
- **ファイルサイズ**: 合計3.6MB（production 2.1MB + training 1.5MB）
- **学習時間**: 週次自動学習は45分以内での完了
- **計算リソース**: GCP 1Gi・1CPUの制約下での最適化

### **品質保証要件**
- **継続監視**: 定期的な性能評価と品質チェック（1,117テスト・68.32%カバレッジ）
- **テスト統合**: 単体テスト・統合テスト・回帰テストの完備
- **交差検証**: TimeSeriesSplit n_splits=5による金融時系列データ対応
- **Early Stopping**: rounds=20で過学習防止・LightGBM/XGBoost対応
- **クラス不均衡対応**: SMOTE + class_weight='balanced'
- **ハイパーパラメータ最適化**: Phase 40統合（79パラメータ自動最適化）
- **自動化**: CI/CDパイプラインによる品質ゲート・週次自動学習

## 🔗 関連ファイル・依存関係

### **機械学習システム**
- `src/features/feature_manager.py`: 特徴量生成・管理システム
- `src/ml/ensemble.py`: ProductionEnsemble実装クラス
- `scripts/ml/create_ml_models.py`: モデル学習・作成スクリプト

### **システム管理・CI/CD**
- `.github/workflows/`: 週次自動学習・デプロイワークフロー
- `scripts/testing/checks.sh`: 品質チェック（Phase 49完了版：1,117テスト・68.32%カバレッジ）
- `logs/`: モデル学習・運用ログ記録
- `config/optimization/`: Phase 40最適化結果管理（79パラメータ）

### **設定・品質保証**
- `config/core/unified.yaml`: 統一設定ファイル（55特徴量・3モデルアンサンブル設定）
- `config/core/thresholds.yaml`: 性能閾値・品質基準設定（Phase 40最適化対応）
- `config/core/feature_order.json`: 55特徴量定義（v2.5.0・Strategy-Aware ML対応）
- `tests/unit/ml/`: 機械学習モジュールテスト

### **外部ライブラリ依存**
- **scikit-learn**: 機械学習フレームワーク・アンサンブル学習
- **LightGBM, XGBoost**: 勾配ブースティングライブラリ
- **imbalanced-learn**: SMOTE oversamplingによるクラス不均衡対応
- **optuna**: TPESamplerハイパーパラメータ最適化（Phase 40統合）
- **pandas, numpy**: データ処理・特徴量エンジニアリング
- **pickle, joblib**: モデルシリアライゼーション・並列処理

### **データフロー**（Phase 49完了版）
1. **学習**: training/で個別モデル学習（55特徴量・Phase 40最適化パラメータ）
2. **統合**: production/でアンサンブルモデル構築（LightGBM 40%・XGBoost 40%・RandomForest 20%）
3. **アーカイブ**: archive/で履歴管理（最新5バージョン保持）
4. **運用**: 本番システムでの予測実行（24時間稼働・Cloud Run）
5. **自動学習**: 週次自動学習（毎週日曜18:00 JST・GitHub Actions）

## 🎯 Phase 49完了まとめ

**機械学習モデル管理システム**: 55特徴量Strategy-Aware ML（Phase 41.8実装）・3モデルアンサンブル・Phase 40ハイパーパラメータ最適化（79パラメータ）・週次自動学習・最新5バージョンアーカイブ管理により、企業級品質のAI予測システムが24時間安定稼働中 🚀
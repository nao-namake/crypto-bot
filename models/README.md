# models/ - 機械学習モデル管理ディレクトリ

**Phase 52.4**

**最終更新**: 2025年11月15日

## 🎯 役割・責任

機械学習モデルの学習、管理、バージョン制御、本番運用を統合管理します。**2段階Graceful Degradation**により、特徴量レベルに応じた最適なモデルを提供し、安定した取引システム運用を実現します。

## 📂 ディレクトリ構成

```
models/
├── README.md                         # このファイル
├── production/                       # 本番環境用モデル
│   ├── ensemble_full.pkl            # Full model（デフォルト）
│   ├── ensemble_basic.pkl           # Basic model（フォールバック）
│   ├── production_model_metadata.json         # Full model メタデータ
│   └── production_model_metadata_basic.json   # Basic model メタデータ
├── training/                         # 学習・検証用個別モデル
│   ├── lightgbm_model.pkl           # LightGBM個別モデル（40%重み）
│   ├── xgboost_model.pkl            # XGBoost個別モデル（40%重み）
│   ├── random_forest_model.pkl      # RandomForest個別モデル（20%重み）
│   └── training_metadata.json       # 学習結果メタデータ
└── archive/                          # 過去バージョン保管（7日間保持）
    ├── ensemble_full_*.pkl          # アーカイブモデル（ロールバック用）
    └── ensemble_basic_*.pkl         # アーカイブモデル（ロールバック用）
```

**注**: 特徴量数・戦略数・ファイルサイズ等は`config/core/feature_order.json`・`config/core/strategies.yaml`を参照

## 📋 主要ディレクトリの役割

### **production/**
本番環境で実際に使用される機械学習モデルを管理します。

**2段階Graceful Degradation**
- **ensemble_full.pkl**: Full Model（デフォルト）
  - 特徴量構成: feature_order.jsonの`feature_levels.full`に定義
  - 本番環境での通常運用
  - フォールバック: 読み込み失敗時は自動的にensemble_basic.pklにフォールバック

- **ensemble_basic.pkl**: Basic Model（フォールバック）
  - 特徴量構成: feature_order.jsonの`feature_levels.basic`に定義
  - Full Model使用不可時の自動フォールバック
  - フォールバック: 読み込み失敗時はDummyModelにフォールバック（全holdシグナル）

**Graceful Degradation Flow**
```
ensemble_full.pkl (Full) → ensemble_basic.pkl (Basic) → DummyModel (Hold)
```

**共通機能**
- **production_model_metadata.json**: モデル性能指標・バージョン管理データ
- 実際の取引判断で使用される高品質な予測エンジン
- 3モデルアンサンブル（LightGBM 40%・XGBoost 40%・RandomForest 20%）
- 週次自動学習（毎週日曜18:00 JST）

### **training/**
個別の機械学習アルゴリズムの学習と検証を管理します。
- **lightgbm_model.pkl**: 高速で軽量なLightGBMモデル
- **xgboost_model.pkl**: 高精度予測のXGBoostモデル
- **random_forest_model.pkl**: 安定性重視のRandomForestモデル
- **training_metadata.json**: 各モデルの性能指標と学習情報
- 本番用アンサンブルモデルの構成要素を提供
- 訓練時自動生成（`scripts/ml/create_ml_models.py`）

### **archive/**
過去バージョンのモデルとメタデータを保管します。
- タイムスタンプ付きファイル名での履歴管理
- 緊急時のロールバック対応（7日間保持）
- モデルの進化履歴と性能比較分析
- 定期的なクリーンアップ（7日超過分削除）

## 📝 使用方法・例

### **モデル学習**
```bash
# 標準コマンド（Full + Basic両方生成）
python3 scripts/ml/create_ml_models.py \
  --n-classes 3 \
  --threshold 0.005 \
  --optimize \
  --n-trials 50

# 詳細ログ出力
python3 scripts/ml/create_ml_models.py --verbose

# 品質チェック
bash scripts/testing/checks.sh

# 自動学習ワークフロー状況確認（週次自動学習）
gh run list --workflow=model-training.yml --limit 5
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
print(f"モデル構成: {model_info['weights']}")  # LightGBM:0.4, XGBoost:0.4, RandomForest:0.2
```

### **バージョン管理・履歴管理**
```bash
# アーカイブ履歴確認
ls -lah models/archive/

# 特定バージョンへのロールバック
cp models/archive/ensemble_full_YYYYMMDD_HHMMSS.pkl models/production/ensemble_full.pkl
cp models/archive/production_model_metadata_YYYYMMDD_HHMMSS.json models/production/production_model_metadata.json

# アーカイブ状況確認（7日間保持）
ls -lh models/archive/ensemble_*.pkl
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
for model_name, metrics in training_data.get('model_metrics', {}).items():
    print(f"{model_name}:")
    print(f"  F1スコア: {metrics.get('f1_score', 'N/A'):.3f}")
    print(f"  精度: {metrics.get('accuracy', 'N/A'):.3f}")

print(f"\n本番アンサンブル性能:")
prod_metrics = production_data.get('performance_metrics', {})
print(f"  F1スコア: {prod_metrics.get('f1_score', 'N/A'):.3f}")
print(f"  精度: {prod_metrics.get('accuracy', 'N/A'):.3f}")
```

## ⚠️ 注意事項・制約

### **ファイル管理要件**
- **統一インターフェース**: feature_managerシステムとの統合必須
- **バージョン管理**: Git情報とモデルハッシュによる厳密な追跡
- **アーカイブ管理**: 7日間保持・定期的なクリーンアップ
- **自動生成**: 全モデルファイルは訓練時自動生成
- **読み取り専用**: 本番環境では基本的に読み取り専用

### **品質保証要件**
- **継続監視**: 定期的な性能評価と品質チェック
- **テスト統合**: 単体テスト・統合テスト・回帰テストの完備
- **交差検証**: TimeSeriesSplit n_splits=5による金融時系列データ対応
- **Early Stopping**: rounds=20で過学習防止・LightGBM/XGBoost対応
- **クラス不均衡対応**: SMOTE + class_weight='balanced'
- **ハイパーパラメータ最適化**: Optuna TPESamplerによる自動最適化（`thresholds.yaml:optuna_optimized`参照）
- **自動化**: CI/CDパイプラインによる品質ゲート・週次自動学習

## 🔗 関連ファイル・依存関係

### **機械学習システム**
- `src/features/feature_manager.py`: 特徴量生成・管理システム
- `src/ml/ensemble.py`: ProductionEnsemble実装クラス
- `scripts/ml/create_ml_models.py`: モデル学習・作成スクリプト
- `src/core/orchestration/ml_loader.py`: 2段階Graceful Degradation実装

### **システム管理・CI/CD**
- `.github/workflows/model-training.yml`: 週次自動学習ワークフロー
- `scripts/testing/checks.sh`: 品質チェック
- `logs/`: モデル学習・運用ログ記録

### **設定ファイル**
- `config/core/feature_order.json`: 特徴量定義（Single Source of Truth）
- `config/core/strategies.yaml`: 戦略定義（Single Source of Truth）
- `config/core/unified.yaml`: 統一設定ファイル
- `config/core/thresholds.yaml`: 性能閾値・Optuna最適化結果

### **外部ライブラリ依存**
- **scikit-learn**: 機械学習フレームワーク・アンサンブル学習
- **LightGBM, XGBoost**: 勾配ブースティングライブラリ
- **imbalanced-learn**: SMOTE oversamplingによるクラス不均衡対応
- **optuna**: TPESamplerハイパーパラメータ最適化
- **pandas, numpy**: データ処理・特徴量エンジニアリング
- **pickle, joblib**: モデルシリアライゼーション・並列処理

### **データフロー**
1. **学習**: training/で個別モデル学習（feature_order.json定義の特徴量・thresholds.yaml最適化パラメータ）
2. **統合**: production/でアンサンブルモデル構築（LightGBM 40%・XGBoost 40%・RandomForest 20%）
3. **アーカイブ**: archive/で履歴管理（7日間保持）
4. **運用**: 本番システムでの予測実行（24時間稼働・Cloud Run）
5. **自動学習**: 週次自動学習（毎週日曜18:00 JST・GitHub Actions）

---

**最終更新**: Phase 52.4完了（2025年11月15日）

**機械学習モデル管理システム**: Strategy-Aware ML・3モデルアンサンブル・Optunaハイパーパラメータ最適化・週次自動学習・2段階Graceful Degradation・7日間アーカイブ管理により、企業級品質のAI予測システムが24時間安定稼働中 🚀

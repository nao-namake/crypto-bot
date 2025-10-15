# models/training/ - 機械学習モデル学習・管理

## 🎯 役割・責任

個別の機械学習モデルの学習、検証、管理を担当します。LightGBM、XGBoost、RandomForestの3つのアルゴリズムを個別に学習・最適化し、本番環境で使用するアンサンブルモデルの構成要素を提供します。モデルの性能評価、バージョン管理、品質保証を通じて高品質な予測モデルの開発を支援します。

## 📂 ファイル構成

```
models/training/
├── README.md                    # このファイル
├── lightgbm_model.pkl          # LightGBM個別学習モデル
├── xgboost_model.pkl           # XGBoost個別学習モデル
├── random_forest_model.pkl     # RandomForest個別学習モデル
└── training_metadata.json      # 学習結果とメタデータ
```

## 📋 主要ファイル・フォルダの役割

### **lightgbm_model.pkl**
LightGBMアルゴリズムで学習された個別モデルファイルです。
- 高速な予測処理と効率的なメモリ使用が特徴
- 勾配ブースティング手法による高精度予測
- 約382KBのコンパクトなファイルサイズ
- アンサンブルモデルでの40%重み付け予定
- GCP環境での1Gi制約に適合した軽量設計

### **xgboost_model.pkl**
XGBoostアルゴリズムで学習された個別モデルファイルです。
- 高精度予測を重視したアルゴリズム設計
- 過学習防止機能と安定した性能
- 約537KBのファイルサイズ
- アンサンブルモデルでの40%重み付け予定
- 金融時系列データに最適化されたパラメータ

### **random_forest_model.pkl**
RandomForestアルゴリズムで学習された個別モデルファイルです。
- アンサンブル学習による安定性と解釈性
- 過学習に対する高い耐性
- 約4.3MBの最大ファイルサイズ
- アンサンブルモデルでの20%重み付け予定
- 基盤的な安定性を提供する役割

### **training_metadata.json**
学習結果の詳細情報とメタデータを管理するファイルです。
- 各モデルの性能指標（F1スコア、精度、再現率など）
- 学習に使用した特徴量の定義と数
- 交差検証結果とバリデーション手法
- 学習実行日時とバージョン情報
- Git情報とモデルハッシュ
- 学習データのサンプル数と期間
- 次回学習スケジュール情報

## 📝 使用方法・例

### **モデル学習・管理の基本操作**
```bash
# Phase 39完了版MLモデル学習
python3 scripts/ml/create_ml_models.py

# 詳細学習スクリプト実行（Phase 39対応）
python3 scripts/ml/create_ml_models.py --verbose --days 365

# Phase 39.5: Optunaハイパーパラメータ最適化実行
python3 scripts/ml/create_ml_models.py --optimize --n-trials 50

# 品質チェック（Phase 39完了版）
bash scripts/testing/checks.sh

# 自動学習ワークフローの確認
gh run list --workflow=weekly-retrain.yml --limit 5
```

### **個別モデル性能確認**
```python
import json
import pickle

# メタデータから性能指標確認
with open('models/training/training_metadata.json', 'r') as f:
    metadata = json.load(f)

print("=== 個別モデル性能 ===")
for model_name, metrics in metadata['model_metrics'].items():
    print(f"{model_name}:")
    print(f"  F1スコア: {metrics['f1_score']:.3f}")
    print(f"  精度: {metrics['accuracy']:.3f}")
    print(f"  適合率: {metrics['precision']:.3f}")
    print(f"  再現率: {metrics['recall']:.3f}")
    print()

print(f"学習サンプル数: {metadata['training_samples']}")
print(f"最終学習日時: {metadata['training_info']['last_retrain']}")
```

### **個別モデルでの予測テスト**
```python
from src.features.feature_manager import FeatureManager
import numpy as np

# システム初期化
feature_manager = FeatureManager()

# 個別モデル読み込み
models = {}
model_names = ['lightgbm', 'xgboost', 'random_forest']

for model_name in model_names:
    with open(f'models/training/{model_name}_model.pkl', 'rb') as f:
        models[model_name] = pickle.load(f)

# 予測テスト実行
def test_individual_models():
    # サンプルデータ（実際は市場データを使用）
    sample_data = generate_sample_market_data()
    features = feature_manager.generate_features(sample_data)
    
    print("=== 個別モデル予測テスト ===")
    for model_name, model in models.items():
        prediction = model.predict(features)
        probabilities = model.predict_proba(features)
        print(f"{model_name}: 予測={prediction[0]}, 確率={probabilities[0][1]:.3f}")

test_individual_models()
```

### **モデル品質監視**
```python
def check_model_quality():
    """モデル品質の監視と警告"""
    with open('models/training/training_metadata.json', 'r') as f:
        metadata = json.load(f)
    
    quality_threshold = 0.6
    quality_issues = []
    
    for model_name, metrics in metadata['model_metrics'].items():
        f1_score = metrics['f1_score']
        if f1_score < quality_threshold:
            quality_issues.append(f"{model_name}: F1={f1_score:.3f} < {quality_threshold}")
    
    if quality_issues:
        print("⚠️ モデル品質劣化検知:")
        for issue in quality_issues:
            print(f"  - {issue}")
        print("再学習またはパラメータ調整を推奨")
    else:
        print("✅ 全モデルが品質基準をクリア")

check_model_quality()
```

## ⚠️ 注意事項・制約

### **学習プロセス要件**（Phase 39完了）
- **特徴量統一管理**: feature_managerシステムとの統合が必須
- **実データ学習**（Phase 39.1）: CSV実データ読み込み・過去180日分15分足データ（17,271件）
- **3クラス分類**（Phase 39.2）: BUY/HOLD/SELL分類・閾値0.5%（ノイズ削減最適化）
- **TimeSeriesSplit**（Phase 39.3）: n_splits=5による金融時系列データに適したCV
- **Early Stopping**（Phase 39.3）: rounds=20で過学習防止・LightGBM/XGBoost対応
- **Train/Val/Test分割**（Phase 39.3）: 70/15/15比率・厳格な評価体系
- **品質基準**: F1スコア0.6以上を維持する必要性
- **バージョン管理**: Git情報とモデルハッシュによる厳密な管理

### **システムリソース制約**
- **計算リソース**: GCP 1Gi・1CPUの制約下での学習最適化
- **メモリ使用量**: 学習時の大容量メモリ使用に注意
- **ファイルサイズ**: RandomForestが最大（4.3MB）、適切な容量管理が必要
- **学習時間**: 自動学習は45分以内での完了が目標

### **品質保証要件**（Phase 39完了）
- **継続監視**: 定期的な性能評価と品質チェック
- **データリーク防止**: TimeSeriesSplit n_splits=5による適切な分割
- **過学習対策**（Phase 39.3）: Early Stopping rounds=20・正則化による汎化性能確保
- **クラス不均衡対応**（Phase 39.4）: SMOTE + class_weight='balanced'
- **ハイパーパラメータ最適化**（Phase 39.5）: Optuna TPESamplerによる自動最適化
- **テスト統合**: 単体テストと統合テストの完備

## 🔗 関連ファイル・依存関係

### **機械学習システム**
- `src/features/feature_manager.py`: 特徴量生成・管理システム
- `src/ml/ensemble.py`: ProductionEnsemble構築（これらのモデルを統合）
- `scripts/ml/create_ml_models.py`: モデル学習・作成スクリプト

### **モデル管理システム**
- `models/production/`: 本番用アンサンブルモデル（統合先）
- `models/archive/`: 過去バージョン保存・履歴管理
- `scripts/testing/checks.sh`: 品質チェック（Phase 39完了版）
- `scripts/ml/create_ml_models.py`: モデル学習・作成スクリプト

### **設定・品質保証**
- `config/core/unified.yaml`: 統一設定ファイル（学習パラメータ・システム設定・全環境対応）
- `config/core/thresholds.yaml`: 性能閾値・品質基準設定
- `tests/unit/ml/`: 機械学習モジュールテスト

### **CI/CDシステム**
- `.github/workflows/`: 自動学習・品質チェックワークフロー
- 週次自動再学習による継続的モデル更新
- 品質ゲートによる自動デプロイ制御

### **外部ライブラリ依存**
- **scikit-learn**: 機械学習フレームワーク・交差検証
- **LightGBM, XGBoost**: 勾配ブースティングライブラリ
- **imbalanced-learn**（Phase 39.4）: SMOTE oversamplingによるクラス不均衡対応
- **optuna**（Phase 39.5）: TPESamplerハイパーパラメータ最適化
- **pandas, numpy**: データ処理・特徴量エンジニアリング
- **joblib, pickle**: モデルシリアライゼーション・並列処理
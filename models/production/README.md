# models/production/ - 本番環境モデル管理

## 🎯 役割・責任

実際の取引で使用される本番用機械学習モデルを管理します。モデルファイルとメタデータの一元管理、バージョン管理、性能監視、品質保証を担当し、安定した取引システムの運用を支援します。

## 📂 ファイル構成

```
models/production/
├── README.md                        # このファイル
├── production_ensemble.pkl          # 本番用アンサンブルモデルファイル
└── production_model_metadata.json   # モデル情報とメタデータ
```

## 📋 主要ファイル・フォルダの役割

### **production_ensemble.pkl**
本番環境で使用されるアンサンブル学習モデルファイルです。
- 複数の機械学習アルゴリズムを統合したアンサンブルモデル
- LightGBM、XGBoost、RandomForestを組み合わせた構成
- 実際の取引判断で使用される予測エンジン
- pickle形式でシリアライズされたモデルオブジェクト
- 約5-10MBのファイルサイズ

### **production_model_metadata.json**
モデルの詳細情報とメタデータを管理するファイルです。
- モデルの性能指標（F1スコア、精度、再現率など）
- 特徴量の定義と構成情報
- 学習データとバリデーション情報
- バージョン管理とGit統合情報
- モデル作成日時と更新履歴
- 各アルゴリズムの重み設定
- システム設定とパラメーター情報

### **モデル構成と特徴**（Phase 39完了）
ProductionEnsembleは複数のアルゴリズムを統合しています。
- **アンサンブル手法**: 重み付き投票によるアンサンブル学習
- **実データ学習**（Phase 39.1）: CSV実データ読み込み・過去180日分15分足データ（17,271件）
- **3クラス分類**（Phase 39.2）: BUY/HOLD/SELL分類・閾値0.5%（ノイズ削減最適化）
- **TimeSeriesSplit**（Phase 39.3）: n_splits=5による堅牢なCross Validation
- **Early Stopping**（Phase 39.3）: rounds=20で過学習防止・LightGBM/XGBoost対応
- **SMOTE oversampling**（Phase 39.4）: クラス不均衡対応・少数派クラス増強
- **Optunaハイパーパラメータ最適化**（Phase 39.5）: TPESampler・3モデル自動最適化
- **特徴量管理**: 統一されたfeature_managerシステムとの連携
- **バージョン管理**: Git情報とモデルハッシュによる管理
- **性能監視**: 継続的な品質監視と自動アラート機能

## 📝 使用方法・例

### **モデルの基本使用方法**
```python
from src.ml.ensemble import ProductionEnsemble
from src.features.feature_manager import FeatureManager
import json

# システム初期化
feature_manager = FeatureManager()
model = ProductionEnsemble()

# メタデータ確認
with open('models/production/production_model_metadata.json', 'r') as f:
    metadata = json.load(f)
    print(f"モデルタイプ: {metadata['model_type']}")
    print(f"作成日時: {metadata['created_at']}")
    print(f"F1スコア: {metadata['performance_metrics']['f1_score']}")

# 市場データでの予測
market_data = get_market_data()
features = feature_manager.generate_features(market_data)
prediction = model.predict(features)
probabilities = model.predict_proba(features)
```

### **メタデータとバージョン確認**
```python
def check_model_info():
    """モデル情報の確認"""
    with open('models/production/production_model_metadata.json', 'r') as f:
        metadata = json.load(f)
    
    print(f"モデルファイル: {metadata['model_file']}")
    print(f"特徴量数: {len(metadata['feature_names'])}")
    print(f"学習サンプル数: {metadata['training_info']['samples_count']}")
    
    # 性能指標表示
    metrics = metadata['performance_metrics']
    for metric, value in metrics.items():
        print(f"{metric}: {value}")

check_model_info()
```

### **モデルファイルの管理**
```bash
# モデルファイルサイズ確認
ls -lh models/production/*.pkl

# メタデータ確認
cat models/production/production_model_metadata.json | jq '.performance_metrics'

# 品質チェック（Phase 39完了版）
bash scripts/testing/checks.sh
```

## ⚠️ 注意事項・制約

### **ファイル管理要件**
- **読み取り専用**: 本番環境では基本的に読み取り専用として扱う
- **バックアップ**: 定期的なバックアップとarchiveフォルダへの保存
- **メタデータ同期**: モデル更新時はメタデータファイルも同時更新必須
- **バージョン管理**: Git情報とモデルハッシュによる厳密なバージョン管理

### **システムリソース制約**
- **メモリ使用量**: モデル読み込み時に約100-150MBのメモリを使用
- **ファイルサイズ**: モデルファイルは5-10MB程度の大容量
- **読み込み時間**: 初回読み込み時に数秒の待機時間が発生
- **同時アクセス**: 複数プロセスからの同時アクセス時の排他制御

### **品質保証要件**
- **性能監視**: 定期的な性能指標の監視と品質チェック
- **テスト実行**: モデル更新時の動作確認とテスト実行
- **ログ記録**: モデル使用状況とエラーの適切なログ記録
- **アラート機能**: 性能劣化や異常動作の検知と通知

## 🔗 関連ファイル・依存関係

### **機械学習システム**
- `src/features/feature_manager.py`: 特徴量生成と管理システム
- `src/ml/ensemble.py`: ProductionEnsemble実装クラス
- `scripts/ml/create_ml_models.py`: モデル学習・更新スクリプト

### **モデル管理システム**
- `models/training/`: 学習用個別モデル格納フォルダ
- `models/archive/`: 過去バージョン保存フォルダ
- `scripts/testing/checks.sh`: 品質チェック（Phase 39完了版）
- `scripts/ml/create_ml_models.py`: モデル学習・更新スクリプト

### **設定ファイル**
- `config/core/unified.yaml`: 統一設定ファイル（システム基本設定・本番環境設定・全環境対応）
- `config/core/thresholds.yaml`: 性能閾値設定

### **CI/CDとワークフロー**
- `.github/workflows/`: 自動学習・デプロイワークフロー
- `tests/unit/ml/`: 機械学習モジュールテスト

### **外部ライブラリ依存**
- **scikit-learn**: 機械学習フレームワーク
- **LightGBM, XGBoost**: 勾配ブースティングライブラリ
- **imbalanced-learn**（Phase 39.4）: SMOTE oversamplingによるクラス不均衡対応
- **optuna**（Phase 39.5）: TPESamplerハイパーパラメータ最適化
- **pandas, numpy**: データ処理ライブラリ
- **pickle**: モデルシリアライゼーション
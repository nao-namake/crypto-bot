# models/production/ - 本番環境モデル管理

**Phase 52.4**

**最終更新**: 2025年11月15日

## 🎯 役割・責任

実際の取引で使用される本番用機械学習モデルを管理します。**2段階Graceful Degradation**により、特徴量レベルに応じた最適なモデルを提供し、安定した取引システム運用を実現します。

## 📂 ファイル構成

```
models/production/
├── README.md                             # このファイル
├── ensemble_full.pkl                     # Full model: 55特徴量（デフォルト）
├── ensemble_basic.pkl                    # Basic model: 49特徴量（フォールバック）
├── production_model_metadata.json        # Full model メタデータ
└── production_model_metadata_basic.json  # Basic model メタデータ
```

**注**: 特徴量数・戦略数は`config/core/feature_order.json`・`config/core/strategies.yaml`を参照

## 📋 主要ファイル・フォルダの役割

### **2段階Graceful Degradationシステム**

#### **ensemble_full.pkl** - Full Model（デフォルト）
完全装備モデルです。
- **特徴量構成**: feature_order.jsonの`feature_levels.full`に定義
- **使用場面**: 本番環境での通常運用
- **フォールバック**: 読み込み失敗時は自動的にensemble_basic.pklにフォールバック

#### **ensemble_basic.pkl** - Basic Model（フォールバック）
基本構成の安定モデルです。
- **特徴量構成**: feature_order.jsonの`feature_levels.basic`に定義
- **使用場面**: Full Model使用不可時の自動フォールバック
- **フォールバック**: 読み込み失敗時はDummyModelにフォールバック（全holdシグナル）

#### **Graceful Degradation Flow**
```
ensemble_full.pkl (Full) → ensemble_basic.pkl (Basic) → DummyModel (Hold)
```

### **production_model_metadata.json**
モデルの詳細情報とメタデータを管理するファイルです。
- モデルの性能指標（F1スコア、精度、再現率など）
- 特徴量定義リスト（feature_order.jsonと同期）
- 学習データとバリデーション情報（TimeSeriesSplit n_splits=5）
- バージョン管理とGit統合情報
- モデル作成日時と更新履歴
- 各アルゴリズムの重み設定（LightGBM: 0.4, XGBoost: 0.4, RandomForest: 0.2）
- Phase情報とステータス

### **モデル構成と特徴**

#### **アンサンブル学習基盤**
- **アンサンブル手法**: 重み付き投票によるアンサンブル学習
- **実データ学習**: CSV実データ読み込み・過去データ15分足
- **3クラス分類**: BUY/HOLD/SELL分類・閾値±0.5%
- **TimeSeriesSplit**: n_splits=5による堅牢なCross Validation
- **Early Stopping**: rounds=20で過学習防止・LightGBM/XGBoost対応
- **SMOTE oversampling**: クラス不均衡対応・少数派クラス増強
- **Optunaハイパーパラメータ最適化**: TPESampler・3モデル自動最適化（`config/core/thresholds.yaml:optuna_optimized`参照）

#### **Strategy-Aware ML**
実戦略信号を学習データに統合した高度なML学習システム。
- **訓練/推論一貫性**: 訓練時0-fill問題解決・実戦略信号を学習データに統合
- **Look-ahead bias防止**: 過去データのみ使用・未来データリーク防止
- **戦略信号統合**: strategies.yamlで定義された戦略の信号を特徴量化
- **信号エンコーディング**: action × confidence方式（buy=+confidence, hold=0, sell=-confidence）

#### **システム統合・運用**
- **特徴量管理**: 統一されたfeature_managerシステムとの連携・2段階Graceful Degradation対応
- **バージョン管理**: Git情報とモデルハッシュによる管理
- **性能監視**: 継続的な品質監視と自動アラート機能
- **週次自動学習**: GitHub Actions自動学習ワークフロー（毎週日曜18:00 JST）

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

### **モデル学習・更新**
```bash
# 標準コマンド（Full + Basic両方生成）
python3 scripts/ml/create_ml_models.py \
  --n-classes 3 \
  --threshold 0.005 \
  --optimize \
  --n-trials 50

# モデルファイル確認
ls -lh models/production/ensemble_*.pkl

# メタデータ確認
cat models/production/production_model_metadata.json | jq '.performance_metrics'

# 品質チェック
bash scripts/testing/checks.sh
```

## ⚠️ 注意事項・制約

### **ファイル管理要件**
- **読み取り専用**: 本番環境では基本的に読み取り専用として扱う
- **バックアップ**: 定期的なバックアップとarchiveフォルダへの保存
- **メタデータ同期**: モデル更新時はメタデータファイルも同時更新必須
- **バージョン管理**: Git情報とモデルハッシュによる厳密なバージョン管理

### **システムリソース制約**
- **メモリ使用量**: モデル読み込み時にメモリを使用
- **読み込み時間**: 初回読み込み時に待機時間が発生
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
- `src/core/orchestration/ml_loader.py`: 2段階Graceful Degradation実装

### **モデル管理システム**
- `models/training/`: 学習用個別モデル格納フォルダ
- `models/archive/`: 過去バージョン保存フォルダ（7日間保持）
- `scripts/testing/checks.sh`: 品質チェック

### **設定ファイル**
- `config/core/feature_order.json`: 特徴量定義（Single Source of Truth）
- `config/core/strategies.yaml`: 戦略定義（Single Source of Truth）
- `config/core/unified.yaml`: 統一設定ファイル
- `config/core/thresholds.yaml`: 性能閾値設定・Optuna最適化結果

### **CI/CDとワークフロー**
- `.github/workflows/model-training.yml`: 自動学習ワークフロー（週次実行）
- `tests/unit/ml/`: 機械学習モジュールテスト

### **外部ライブラリ依存**
- **scikit-learn**: 機械学習フレームワーク
- **LightGBM, XGBoost**: 勾配ブースティングライブラリ
- **imbalanced-learn**: SMOTE oversamplingによるクラス不均衡対応
- **optuna**: TPESamplerハイパーパラメータ最適化
- **pandas, numpy**: データ処理ライブラリ
- **pickle**: モデルシリアライゼーション

---

**最終更新**: Phase 52.4完了（2025年11月15日）

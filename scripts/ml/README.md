# scripts/ml/ - 機械学習モデル学習・管理スクリプト

## 🎯 役割・責任

機械学習モデルの学習、管理、品質保証を担当するスクリプトディレクトリです。個別モデルの学習からアンサンブルモデルの構築、性能評価、バージョン管理までを一元的に管理し、安定した機械学習システムの運用を支援します。特徴量生成から予測モデルの構築まで、包括的な機械学習パイプラインを提供します。

## 📂 ファイル構成

```
scripts/ml/
├── README.md              # このファイル
└── create_ml_models.py    # 機械学習モデル学習・構築メインスクリプト
```

## 📋 主要ファイル・フォルダの役割

### **create_ml_models.py**（Phase 41.8完了）
機械学習モデルの学習・構築・管理を担当するメインスクリプトです。
- **個別モデル学習**: LightGBM・XGBoost・RandomForest の3つのアルゴリズム学習
- **Phase 39.1**: 実データ学習（CSV読み込み・過去180日分15分足データ・17,271件）
- **Phase 39.2**: 閾値最適化（0.3% → 0.5%）・3クラス分類（BUY/HOLD/SELL）
- **Phase 39.3**: TimeSeriesSplit n_splits=5・Early Stopping rounds=20・Train/Val/Test 70/15/15
- **Phase 39.4**: SMOTE oversampling・class_weight='balanced'・クラス不均衡対応
- **Phase 39.5**: Optunaハイパーパラメータ最適化（TPESampler・自動最適化）
- **Phase 41.8**: 実戦略信号学習（訓練時/推論時一貫性確保・Look-ahead bias防止・55特徴量対応）
  - **実戦略信号生成**: `_generate_real_strategy_signals_for_training()`メソッド実装・過去データから5戦略実行
  - **訓練/推論一貫性**: 訓練時0-fill問題解決・実際の戦略信号を学習データに統合
  - **Look-ahead bias防止**: `df.iloc[: i + 1]`による過去データのみ使用・未来データリーク防止
  - **55特徴量対応**: 50基本特徴量 + 5戦略信号特徴量（ATRBased/MochipoyAlert/MultiTimeframe/DonchianChannel/ADXTrendStrength）
  - **信号エンコーディング**: `action × confidence`方式・buy=+1.0、hold=0.0、sell=-1.0
- **アンサンブル構築**: ProductionEnsemble作成・重み付け投票・モデル統合
- **特徴量統合**: feature_manager連携・55特徴量生成・データパイプライン統合
- **品質保証**: モデル検証・予測テスト・性能評価・品質ゲート
- **バージョン管理**: メタデータ管理・モデル保存・履歴追跡・自動アーカイブ
- **CI/CD統合**: GitHub Actions連携・自動学習・週次再学習・Discord通知

### **主要機能と特徴**
- **統合学習システム**: 特徴量生成→モデル学習→アンサンブル構築の完全自動化
- **金融特化最適化**: 時系列データ対応・過学習防止・クロスバリデーション
- **品質管理**: F1スコア・精度・再現率による性能評価・品質閾値管理
- **自動化対応**: コマンドライン引数・設定ファイル・ログ出力・エラーハンドリング
- **スケーラブル**: 大量データ処理・メモリ効率・並列処理・クラウド対応

## 📝 使用方法・例

### **基本的なモデル学習**
```bash
# デフォルト設定での学習（推奨）
python3 scripts/ml/create_ml_models.py

# 期間指定での学習（365日間）
python3 scripts/ml/create_ml_models.py --days 365

# 詳細ログ表示での学習
python3 scripts/ml/create_ml_models.py --verbose
```

### **統合管理システム経由実行**
```bash
# 統合管理CLI経由（推奨）
python3 scripts/testing/dev_check.py ml-models

# ドライラン（実行前確認）
python3 scripts/testing/dev_check.py ml-models --dry-run

# テスト統合実行
python3 scripts/testing/dev_check.py ml-models --test
```

### **カスタム設定での学習**
```bash
# カスタム期間・詳細ログ
python3 scripts/ml/create_ml_models.py --days 180 --verbose

# カスタム設定ファイル指定
python3 scripts/ml/create_ml_models.py --config config/core/unified.yaml --verbose

# ドライラン（学習前の検証）
python3 scripts/ml/create_ml_models.py --dry-run --verbose

# 1年間データでの大規模学習
python3 scripts/ml/create_ml_models.py --days 365 --verbose
```

### **学習結果確認**
```python
import json
import pickle

# メタデータ確認
with open('models/training/training_metadata.json', 'r') as f:
    metadata = json.load(f)

print("=== 学習結果 ===")
for model_name, metrics in metadata['model_metrics'].items():
    print(f"{model_name}:")
    print(f"  F1スコア: {metrics['f1_score']:.3f}")
    print(f"  精度: {metrics['accuracy']:.3f}")

# ProductionEnsemble確認
with open('models/production/production_model_metadata.json', 'r') as f:
    prod_data = json.load(f)

print(f"\nProductionEnsemble性能:")
print(f"  F1スコア: {prod_data['performance_metrics']['f1_score']:.3f}")
print(f"  精度: {prod_data['performance_metrics']['accuracy']:.3f}")
```

## ⚠️ 注意事項・制約

### **実行環境要件**
- **Python環境**: Python 3.12以上（Phase 22標準）・機械学習ライブラリ完全インストール
- **実行場所**: プロジェクトルートディレクトリからの実行必須
- **メモリ要件**: 最低2GB RAM・大規模学習時は4GB以上推奨
- **計算時間**: 10-30分（データ量・モデル複雑度による）

### **データ要件**
- **最低データ量**: 2000サンプル以上の市場データ・時系列順序維持
- **特徴量品質**: feature_manager生成15特徴量（Phase 22統合）・欠損値処理済み
- **ラベル品質**: buy/sell/holdバランス・クラス不均衡対応・検証データ分離
- **データ新鮮性**: 定期的なデータ更新・市場変動対応・学習データ更新

### **品質保証要件（Phase 22標準）**
- **性能閾値**: F1スコア0.6以上・精度維持・過学習防止・15特徴量最適化
- **交差検証**: TimeSeriesSplit・金融時系列データ対応・リーク防止
- **テスト統合**: 625テスト100%成功・58.64%カバレッジ維持・品質ゲート通過
- **監視**: 学習ログ・Discord通知・性能追跡・異常検知・アラート通知

### **システム統合制約**
- **特徴量統合**: feature_manager.pyとの完全統合（Phase 22・15特徴量）・データパイプライン統合
- **モデル統合**: ProductionEnsemble・アンサンブル学習・重み最適化
- **CI/CD統合**: GitHub Actions・自動学習・品質ゲート・デプロイ連携
- **ストレージ**: モデルファイル・メタデータ・ログの適切な管理

## 🔗 関連ファイル・依存関係

### **機械学習システム**
- `src/features/feature_generator.py`: 特徴量生成・15特徴量管理（Phase 22統合）・データ前処理
- `src/ml/ensemble.py`: ProductionEnsemble・アンサンブル学習・予測エンジン
- `models/`: モデル保存・バージョン管理・アーカイブシステム

### **品質保証・テスト**
- `scripts/testing/checks.sh`: 品質チェック・テスト実行・カバレッジ確認
- `scripts/testing/dev_check.py`: 統合管理・ml-modelsコマンド・開発支援
- `tests/unit/ml/`: 機械学習テスト・モデル検証・品質保証

### **設定・データ管理**
- `config/core/`: 機械学習設定・アルゴリズムパラメータ・学習設定
- `data/`: 市場データ・学習データ・前処理データ・キャッシュ
- `logs/`: 学習ログ・性能メトリクス・エラーログ・履歴管理

### **CI/CD・自動化**
- `.github/workflows/`: 自動学習ワークフロー・週次再学習・CI/CDパイプライン
- `scripts/deployment/`: デプロイメント・Cloud Run・本番環境統合
- GCP Secret Manager・Cloud Run・GitHub Actions統合

### **外部ライブラリ依存**
- **scikit-learn**: 機械学習フレームワーク・交差検証・評価指標
- **LightGBM・XGBoost**: 勾配ブースティング・高性能学習・GPU対応
- **pandas・numpy**: データ処理・数値計算・特徴量エンジニアリング
- **joblib・pickle**: モデルシリアライゼーション・並列処理・最適化

### **監視・通知システム**
- `src/monitoring/discord_notifier.py`: 学習結果通知・アラート・レポート
- Cloud Run監視・ヘルスチェック・性能メトリクス・運用監視
- `scripts/analysis/`: 学習分析・性能評価・ML信頼度分析・レポート生成
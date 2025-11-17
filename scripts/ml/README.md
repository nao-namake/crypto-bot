# scripts/ml/ - 機械学習モデル学習・管理スクリプト（Phase 52.4）

**最終更新**: 2025年11月15日 - Phase 52.4コード整理完了

## 🎯 役割・責任

機械学習モデルの学習、管理、品質保証を担当するスクリプトディレクトリです。個別モデルの学習からアンサンブルモデルの構築、性能評価、バージョン管理までを一元的に管理し、安定した機械学習システムの運用を支援します。特徴量生成から予測モデルの構築まで、包括的な機械学習パイプラインを提供します。

**Phase 52.4完了成果**: 6戦略統合・55特徴量Strategy-Aware ML・週次自動再学習・GitHub Actions統合

## 📂 ファイル構成（Phase 52.4）

```
scripts/ml/
├── README.md              # このファイル（Phase 52.4）
├── create_ml_models.py    # 機械学習モデル学習・構築メインスクリプト（Phase 52.4）
└── archive/               # 過去の実験的スクリプト（使用頻度低）
    └── train_meta_learning_model.py  # Meta-Learning学習パイプライン（実験的・未使用）
```

**注**: archive/は過去の実験的実装を保持（現在未使用・将来の参考用）

## 📋 主要ファイル・フォルダの役割

### **create_ml_models.py**（Phase 52.4）
機械学習モデルの学習・構築・管理を担当するメインスクリプトです。
- **個別モデル学習**: LightGBM・XGBoost・RandomForest の3つのアルゴリズム学習
- **実データ学習**: CSV読み込み・過去180日分15分足データ
- **3クラス分類**: BUY/HOLD/SELL・閾値最適化
- **TimeSeriesSplit**: n_splits=5・Early Stopping・Train/Val/Test 70/15/15
- **クラス不均衡対応**: SMOTE oversampling・class_weight='balanced'
- **ハイパーパラメータ最適化**: Optuna TPESampler・自動最適化
- **Strategy-Aware ML**: 実戦略信号学習（訓練時/推論時一貫性確保・Look-ahead bias防止）
  - **実戦略信号生成**: `_generate_real_strategy_signals_for_training()`メソッド実装・過去データから6戦略実行
  - **訓練/推論一貫性**: 実際の戦略信号を学習データに統合
  - **Look-ahead bias防止**: `df.iloc[: i + 1]`による過去データのみ使用・未来データリーク防止
  - **55特徴量対応**: 49基本特徴量 + 6戦略信号特徴量（ATRBased/DonchianChannel/ADXTrendStrength/BBReversal/StochasticReversal/MACDEMACrossover）
  - **信号エンコーディング**: `action × confidence`方式・buy=+1.0、hold=0.0、sell=-1.0
- **アンサンブル構築**: ProductionEnsemble作成・重み付け投票（LightGBM 40%・XGBoost 40%・RandomForest 20%）
- **特徴量統合**: feature_manager連携・feature_order.json準拠
- **品質保証**: モデル検証・予測テスト・性能評価
- **バージョン管理**: メタデータ管理・モデル保存・履歴追跡
- **CI/CD統合**: GitHub Actions連携・自動学習・週次再学習・Discord通知

### **Phase 52.4モデル再学習対応状況**
✅ **完全対応済み** - 問題なし

**GitHub Actions週次自動再学習**（`.github/workflows/model-training.yml`）:
- ✅ **週次自動実行**: 毎週日曜18:00 JST（UTC 09:00）
- ✅ **55特徴量Strategy-Aware ML**: 49基本特徴量 + 6戦略信号特徴量完全対応
- ✅ **3クラス分類**: SELL/HOLD/BUY・閾値±0.5%
- ✅ **Optunaハイパーパラメータ最適化**: 50試行デフォルト・100試行高精度オプション
- ✅ **自動コミット・プッシュ**: モデル更新の自動バージョン管理
- ✅ **デプロイトリガー**: モデル更新時の本番環境自動デプロイ
- ✅ **モデル品質検証**: 特徴量数≥50・モデルタイプ確認・メタデータ検証
- ✅ **実行時間**: 約4-8分（50-100 trials）・タイムアウト30分

### **archive/ - 過去の実験的スクリプト**（Phase 49整理）
過去の実験的実装を保持するディレクトリです。現在は使用されていませんが、将来の参考用に保管しています。

**train_meta_learning_model.py**（Phase 45.3実装・未使用）:
- Meta-Learning学習パイプライン（実験的機能）
- バックテストデータから学習データ生成
- 市場状況特徴量活用・事後的最適重み計算
- **使用状況**: 現在未使用・GitHub Actions統合なし
- **保持理由**: 将来の参考用・実験記録

### **主要機能と特徴**
- **統合学習システム**: 特徴量生成→モデル学習→アンサンブル構築の完全自動化
- **金融特化最適化**: 時系列データ対応・過学習防止・クロスバリデーション
- **品質管理**: F1スコア・精度・再現率による性能評価・品質閾値管理
- **自動化対応**: コマンドライン引数・設定ファイル・ログ出力・エラーハンドリング
- **スケーラブル**: 大量データ処理・メモリ効率・並列処理・クラウド対応
- **週次自動再学習**: GitHub Actions統合・市場変動対応・モデル鮮度維持

## 📝 使用方法・例

### **基本的なモデル学習**（Phase 52.4推奨コマンド）
```bash
# Phase 52.4推奨: 55特徴量Strategy-Aware ML・3クラス分類・Optuna最適化
python3 scripts/ml/create_ml_models.py \
  --n-classes 3 \
  --threshold 0.005 \
  --optimize \
  --n-trials 50 \
  --verbose

# 高精度学習（100試行・約8分）
python3 scripts/ml/create_ml_models.py \
  --n-classes 3 \
  --threshold 0.005 \
  --optimize \
  --n-trials 100 \
  --verbose

# テスト用（30試行・約2分）
python3 scripts/ml/create_ml_models.py \
  --n-classes 3 \
  --threshold 0.005 \
  --optimize \
  --n-trials 30 \
  --verbose
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

### **学習結果確認**（Phase 49完了版）
```python
import json
import pickle

# メタデータ確認
with open('models/training/training_metadata.json', 'r') as f:
    metadata = json.load(f)

print("=== Phase 49完了: 学習結果 ===")
for model_name, metrics in metadata['model_metrics'].items():
    print(f"{model_name}:")
    print(f"  F1スコア: {metrics['f1_score']:.3f}")
    print(f"  精度: {metrics['accuracy']:.3f}")

# ProductionEnsemble確認
with open('models/production/production_model_metadata.json', 'r') as f:
    prod_data = json.load(f)

print(f"\nProductionEnsemble性能 (55特徴量):")
print(f"  モデルタイプ: {prod_data['model_type']}")
print(f"  特徴量数: {len(prod_data['feature_names'])}")
print(f"  作成日時: {prod_data['created_at']}")
print(f"  F1スコア: {prod_data['performance_metrics']['f1_score']:.3f}")
print(f"  精度: {prod_data['performance_metrics']['accuracy']:.3f}")
```

### **GitHub Actions週次再学習の手動実行**
```bash
# GitHub Actionsワークフローの手動トリガー:
# 1. GitHub リポジトリページを開く
# 2. "Actions" タブをクリック
# 3. "ML Model Training" ワークフローを選択
# 4. "Run workflow" をクリック
# 5. パラメータ設定:
#    - n_trials: 50（推奨）/ 100（高精度）/ 30（テスト）
#    - dry_run: false（本番）/ true（テスト）
# 6. "Run workflow" ボタンをクリック

# 実行結果確認:
# - 約4-8分で完了
# - モデル自動コミット・プッシュ
# - 本番環境自動デプロイトリガー
```

## ⚠️ 注意事項・制約

### **実行環境要件**
- **Python環境**: Python 3.13以上（Phase 49標準）・機械学習ライブラリ完全インストール
- **実行場所**: プロジェクトルートディレクトリからの実行必須
- **メモリ要件**: 最低2GB RAM・大規模学習時は4GB以上推奨
- **計算時間**: 4-8分（50-100 trials・Optuna最適化）・30分タイムアウト

### **データ要件**
- **最低データ量**: 2000サンプル以上の市場データ・時系列順序維持
- **特徴量品質**: feature_manager生成55特徴量（49基本+6戦略信号）・欠損値処理済み
- **ラベル品質**: buy/sell/holdバランス・クラス不均衡対応・検証データ分離
- **データ新鮮性**: 週次自動再学習・市場変動対応・学習データ更新

### **品質保証要件（Phase 52.4）**
- **性能閾値**: F1スコア最適化・精度維持・過学習防止・55特徴量最適化
- **交差検証**: TimeSeriesSplit・金融時系列データ対応・リーク防止
- **テスト統合**: 品質ゲート通過・カバレッジ基準達成
- **監視**: 学習ログ・Discord通知・性能追跡・異常検知・アラート通知

### **システム統合制約**
- **特徴量統合**: feature_manager.pyとの完全統合（Phase 52.4・55特徴量）・データパイプライン統合
- **モデル統合**: ProductionEnsemble・アンサンブル学習・重み最適化（LightGBM 40%・XGBoost 40%・RandomForest 20%）
- **CI/CD統合**: GitHub Actions・週次自動再学習・品質ゲート・デプロイ連携
- **ストレージ**: モデルファイル・メタデータ・ログの適切な管理

### **週次自動再学習制約**
- **実行タイミング**: 毎週日曜18:00 JST（UTC 09:00）
- **実行時間**: 約4-8分（Optuna 50-100 trials）
- **自動コミット**: モデル更新の自動バージョン管理・自動プッシュ
- **デプロイトリガー**: モデル更新時の本番環境自動デプロイ
- **失敗時対応**: 既存モデル継続使用・アラート通知・手動介入必要

## 🔗 関連ファイル・依存関係

### **機械学習システム**
- `src/features/feature_generator.py`: 特徴量生成・55特徴量管理（49基本+6戦略信号）・データ前処理
- `src/ml/ensemble.py`: ProductionEnsemble・アンサンブル学習・予測エンジン
- `models/`: モデル保存・バージョン管理・アーカイブシステム
- `src/strategies/`: 6戦略実装（ATRBased/DonchianChannel/ADXTrendStrength/BBReversal/StochasticReversal/MACDEMACrossover）

### **品質保証・テスト**（Phase 52.4）
- `scripts/testing/checks.sh`: 品質チェック
- `scripts/testing/validate_system.sh`: システム整合性検証・特徴量数検証
- `tests/unit/ml/`: 機械学習テスト・モデル検証・品質保証

### **設定・データ管理**
- `config/core/`: 機械学習設定・アルゴリズムパラメータ・学習設定
- `config/core/feature_manager.py`: 55特徴量定義管理（Phase 52.4）
- `data/`: 市場データ・学習データ・前処理データ・キャッシュ
- `logs/`: 学習ログ・性能メトリクス・エラーログ・履歴管理

### **CI/CD・自動化**
- `.github/workflows/model-training.yml`: 週次自動再学習ワークフロー（Phase 52.4完全対応）
- `scripts/deployment/`: デプロイメント・Cloud Run・本番環境統合
- GCP Secret Manager・Cloud Run・GitHub Actions統合

### **外部ライブラリ依存**
- **scikit-learn**: 機械学習フレームワーク・交差検証・評価指標
- **LightGBM・XGBoost**: 勾配ブースティング・高性能学習・GPU対応
- **pandas・numpy**: データ処理・数値計算・特徴量エンジニアリング
- **joblib・pickle**: モデルシリアライゼーション・並列処理・最適化
- **Optuna**: ハイパーパラメータ最適化・TPESampler・自動最適化

### **監視・通知システム**
- `src/monitoring/discord_notifier.py`: 学習結果通知・アラート・レポート
- Cloud Run監視・ヘルスチェック・性能メトリクス・運用監視
- GitHub Actions実行結果・週次再学習ステータス・モデル更新通知

---

**🎯 重要**:
- **Phase 52.4完了**: 6戦略統合・55特徴量Strategy-Aware ML・週次自動再学習・GitHub Actions統合
- **最新モデル再学習対応**: 完全対応済み・問題なし
- **週次自動実行**: 毎週日曜18:00 JST・自動コミット・デプロイトリガー
- **品質保証**: 品質ゲート通過・カバレッジ基準達成・F1スコア最適化

**推奨運用方法**:
1. **週次自動再学習**: GitHub Actionsで自動実行（手動介入不要）
2. **手動実行**: モデル品質問題時・緊急再学習時のみ
3. **品質確認**: `bash scripts/testing/checks.sh` でテスト実行
4. **性能確認**: models/production/production_model_metadata.json でメトリクス確認

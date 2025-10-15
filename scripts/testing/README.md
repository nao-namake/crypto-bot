# scripts/testing/ - 品質保証・テストシステム

## 🎯 役割・責任

システム全体の品質保証、テスト実行、コード品質チェックを担当するテストシステムです。単体テストから統合テスト、カバレッジ測定、コードスタイルチェック、機械学習モデル検証まで、包括的な品質保証機能を提供し、継続的な品質向上と回帰防止を支援します。

## 📂 ファイル構成

```
scripts/testing/
├── README.md              # このファイル
└── checks.sh              # 品質チェック・テスト実行スクリプト（Phase 39完了版）
```

## 📋 主要ファイル・フォルダの役割

### **checks.sh**（Phase 39完了版）
システム全体の品質チェックとテスト実行を管理するメインスクリプトです。

**Phase 39完了機能**:
- **テスト実行**: pytest による全テストスイート実行・**1,097テスト・100%成功**
- **カバレッジ測定**: coverage による網羅率測定（**70.56%達成**・65%目標超過）・HTML/JSON/Term出力
- **コードスタイル**: flake8・black・isort によるPEP8準拠チェック
- **ML学習データ確認**: Phase 39.1実データファイル存在確認（data/btc_jpy/15m_sample.csv）
- **必須ライブラリ確認**: Phase 39.4-39.5対応（imbalanced-learn・optuna）
- **機能トグル設定**: Phase 31.1対応（config/core/features.yaml）
- **trading層アーキテクチャ**: Phase 38完了（4層分離・core/balance/execution/position/risk）
- **ディレクトリ構造確認**: プロジェクト構造・ファイル存在確認
- **品質ゲート**: 品質基準チェック・CI/CD統合・デプロイ前確認
- **レポート生成**: coverage-reports/への詳細レポート出力

**実行時間**: 約80秒（Phase 39完了・1,097テスト）

### **主要機能と特徴**
- **継続的品質保証**: 開発サイクルでの品質維持・回帰防止・自動化
- **包括的検証**: ML実データ学習・trading層アーキテクチャ・機能トグル設定の完全確認
- **CI/CD統合**: GitHub Actions・品質ゲート・段階的デプロイ対応
- **Phase 39対応**: ML信頼度向上期の全機能を品質保証

## 📝 使用方法・例

### **日常開発での品質チェック**
```bash
# 基本的な品質チェック（開発時必須）
bash scripts/testing/checks.sh

# 期待結果（Phase 39完了版）:
# ✅ 1,097テスト100%成功
# ✅ 70.56%カバレッジ達成（目標65%超過）
# ✅ コードスタイル準拠（flake8・black・isort）
# ✅ ML学習データ確認（Phase 39.1実データ対応）
# ✅ 必須ライブラリ確認（imbalanced-learn・optuna）
# ✅ 機能トグル設定確認（features.yaml）
# ✅ trading層4層分離アーキテクチャ確認
# ✅ 約80秒で完了

# カバレッジレポート確認
open coverage-reports/htmlcov/index.html
```

### **CI/CD統合使用**
```bash
# CI前品質チェック（必須）
bash scripts/testing/checks.sh
if [ $? -eq 0 ]; then
    echo "✅ 品質チェック成功 - CI実行可能"
else
    echo "❌ 品質チェック失敗 - 修正必要"
    exit 1
fi

# GitHub Actions自動実行
# .github/workflows/ci.yml で自動実行されます
```

### **機械学習モデル管理**
```bash
# Phase 39完了版MLモデル学習
python3 scripts/ml/create_ml_models.py

# Phase 39.5: Optunaハイパーパラメータ最適化
python3 scripts/ml/create_ml_models.py --optimize --n-trials 50

# 期待結果:
# ✅ CSV実データ読み込み（Phase 39.1・17,271件）
# ✅ 3クラス分類（Phase 39.2・閾値0.5%）
# ✅ TimeSeriesSplit n_splits=5（Phase 39.3）
# ✅ SMOTE oversampling（Phase 39.4）
# ✅ Optuna最適化（Phase 39.5）
# ✅ ProductionEnsemble作成
```

### **トラブルシューティング**
```bash
# テスト失敗時の詳細確認
bash scripts/testing/checks.sh 2>&1 | tee test_output.log

# 個別テスト実行
python3 -m pytest tests/unit/ml/ -v

# カバレッジ確認
python3 -m pytest tests/ --cov=src --cov-report=html

# コードスタイル修正
python3 -m black src/ tests/ scripts/
python3 -m isort src/ tests/ scripts/

# ML学習データ確認
ls -lh data/btc_jpy/15m_sample.csv
wc -l data/btc_jpy/15m_sample.csv

# 必須ライブラリインストール
pip install imbalanced-learn optuna
```

## ⚠️ 注意事項・制約

### **実行環境要件**
- **Python環境**: Python 3.12以上・pytest・coverage・flake8・black・isort
- **Phase 39ライブラリ**: imbalanced-learn（SMOTE）・optuna（ハイパーパラメータ最適化）
- **実行場所**: プロジェクトルートディレクトリからの実行必須
- **依存関係**: 全システムモジュール・機械学習ライブラリ・設定ファイル
- **権限**: テスト実行・ファイル作成・ネットワークアクセス権限

### **品質基準**（Phase 39完了）
- **テスト成功率**: 1,097テスト100%成功・回帰防止・継続的品質維持
- **カバレッジ基準**: 65%以上維持（Phase 39: 70.56%達成）・新機能でのテスト追加必須
- **コードスタイル**: PEP8準拠・flake8・black・isort通過必須
- **実行時間**: checks.sh約80秒（1,097テスト実行時間含む）

### **CI/CD統合制約**
- **品質ゲート**: 全チェック通過後のデプロイ実行・失敗時停止
- **自動実行**: GitHub Actions・CI/CD パイプライン統合
- **段階的デプロイ**: 各段階での品質確認・問題時ロールバック
- **監視統合**: Discord通知・アラート・レポート自動送信

### **機械学習検証制約**（Phase 39完了）
- **データ要件**: CSV実データ（Phase 39.1・17,271件・180日分15分足）
- **モデル品質**: TimeSeriesSplit n_splits=5（Phase 39.3）・SMOTE（Phase 39.4）・Optuna最適化（Phase 39.5）
- **リソース制限**: メモリ使用量・計算時間・ストレージ容量管理
- **バージョン管理**: モデル保存・メタデータ・履歴追跡・週次自動再学習

## 🔗 関連ファイル・依存関係

### **テスト・品質保証システム**
- `tests/`: 単体テスト・統合テスト・機械学習テスト・全テストスイート
- `coverage-reports/`: カバレッジレポート・HTML・JSON・統計データ
- `logs/reports/ci_checks/`: 品質チェックレポート・履歴・分析データ

### **機械学習システム**（Phase 39完了）
- `src/features/feature_generator.py`: 特徴量生成・15特徴量管理
- `src/ml/ensemble.py`: ProductionEnsemble・3モデル統合（LightGBM・XGBoost・RandomForest）
- `models/production/`: 本番モデル（Phase 39完了・実データ学習・Optuna最適化済み）
- `models/training/`: 学習用個別モデル（Phase 39.1-39.5対応）
- `models/optuna/`: Optunaハイパーパラメータ最適化結果（Phase 39.5将来拡張用）
- `scripts/ml/create_ml_models.py`: モデル学習・Phase 39完了版

### **設定・環境管理**
- `config/core/unified.yaml`: 統一設定ファイル（全環境対応）
- `config/core/thresholds.yaml`: 動的閾値・ML統合設定
- `config/core/features.yaml`: 機能トグル設定（Phase 31.1）
- `config/core/feature_order.json`: 15特徴量順序定義
- `.flake8`: コードスタイル設定・品質基準・除外ルール
- `pyproject.toml`: プロジェクト設定・依存関係・ツール設定

### **CI/CD・デプロイシステム**
- `.github/workflows/`: CI/CDパイプライン・自動テスト・品質ゲート
- `scripts/deployment/`: デプロイメント・Cloud Run・本番環境統合
- `src/monitoring/discord_notifier.py`: 通知・アラート・レポート送信

### **外部システム統合**
- **GitHub Actions**: CI/CDパイプライン・自動テスト・品質ゲート・週次モデル再学習
- **GCP Cloud Run**: 本番環境（asia-northeast1）・1Gi・1CPU
- **Discord API**: 3階層通知（Critical/Warning/Info）
- **Bitbank API**: BTC/JPY信用取引・市場データ取得

### **品質管理ツール**（Phase 39完了）
- **pytest**: テストフレームワーク・1,097テスト・単体/統合テスト
- **coverage**: カバレッジ測定（70.56%達成）・HTML/JSON出力
- **flake8**: コードスタイル・PEP8準拠・品質チェック
- **black・isort**: コード整形・インポート整理・一貫性確保
- **imbalanced-learn**: SMOTE oversampling（Phase 39.4）
- **optuna**: TPESamplerハイパーパラメータ最適化（Phase 39.5）
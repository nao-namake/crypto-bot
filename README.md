# 🚀 Crypto-Bot - AI自動取引システム

**bitbank信用取引専用のAI自動取引システム**

[![Python](https://img.shields.io/badge/python-3.13-blue)](https://python.org) [![Tests](https://img.shields.io/badge/tests-625%20passed-success)](tests/) [![Coverage](https://img.shields.io/badge/coverage-64.74%25-green)](coverage-reports/) [![Cloud Run](https://img.shields.io/badge/Cloud%20Run-Running-success)](https://cloud.google.com/run) [![Unified Config](https://img.shields.io/badge/Config%20System-Unified-brightgreen)](config/) [![GCP Optimized](https://img.shields.io/badge/GCP%20Resources-Optimized-blue)](docs/)

---

## 🎯 システム概要

**AI自動取引システム**は、bitbank信用取引専用のBTC/JPY自動取引ボットです。5つの取引戦略と機械学習を組み合わせ、15の技術指標を統合分析することで、24時間自動取引を実現します。

### **主要仕様**
- **対象市場**: bitbank信用取引・BTC/JPY専用
- **資金規模**: 1万円スタート → 最大50万円（段階的拡大）
- **取引頻度**: 月100-200回・3分間隔実行（高頻度取引）
- **稼働体制**: 24時間自動取引・Cloud Run稼働
- **品質保証**: 625テスト100%成功・64.74%カバレッジ・CI/CD統合
- **Kelly基準Silent Failure修正**: 2025/09/19完了（取引ブロック問題根本解決・初期固定サイズ実装）
- **Discord Webhook修正**: 2025/09/19完了（GCP version 6適用・401エラー解決）
- **GCPリソース最適化**: 2025/09/17完了（古いイメージ削除・容量最適化）
- **Secret Manager**: 2025/09/15修正完了（key:latest問題解決）

## 🌟 主要機能

### **🤖 AI取引システム**
- **5戦略統合**: ATRBased・MochiPoy・MultiTimeframe・DonchianChannel・ADXTrendStrength
- **動的信頼度計算**: 市場適応型信頼度0.25-0.6・フォールバック完全回避
- **機械学習予測**: 3モデルアンサンブル（LightGBM・XGBoost・RandomForest）
- **15特徴量分析**: RSI・MACD・ボリンジャーバンド・ATR・EMA・Donchianチャネル・ADX等の統合技術分析

### **📊 リスク管理システム**
- **Kelly基準Silent Failure修正（2025/09/19完了）**: 取引ブロック問題根本解決・初期固定サイズで確実実行保証
- **動的設定管理**: ハードコード完全排除・get_threshold()による運用中調整対応
- **Bitbank仕様対応**: 最小取引単位0.0001BTC・Kelly履歴不足時の確実実行システム
- **ドローダウン制御**: 20%制限・連続損失5回で自動停止
- **3段階判定**: APPROVED・CONDITIONAL・DENIED の安全判定
- **異常検知**: スプレッド・価格スパイク・API遅延の自動検知

### **🔧 運用監視システム**
- **24時間稼働**: Google Cloud Run・自動スケーリング
- **Discord監視**: 3階層通知（Critical/Warning/Info）・リアルタイムアラート
- **GCPリソース最適化（2025/09/17完了）**: 古いDockerイメージ削除・容量最適化・コスト削減
- **品質保証**: 自動テスト・コードカバレッジ・継続的品質監視
- **週次学習**: 過去180日データで毎回ゼロから再学習・市場変化に継続的適応

## 🚀 クイックスタート

### **前提条件**
- Python 3.13以上
- bitbankアカウント・API認証情報
- Discord Webhook URL（通知用）
- Google Cloud Platform アカウント（本番環境）

### **1. セットアップ**
```bash
# 1. リポジトリクローン
git clone https://github.com/your-repo/crypto-bot.git
cd crypto-bot

# 2. 依存関係インストール  
pip install -r requirements.txt

# 3. 設定ファイル作成
cp config/secrets/.env.example config/secrets/.env
# API認証情報・Discord Webhook URLを設定

# 4. 品質チェック（必須）
bash scripts/testing/checks.sh
```

### **2. 実行**
```bash
# ペーパートレード（推奨・初回）
python3 main.py --mode paper

# ライブトレード（実資金）
python3 main.py --mode live

# バックテスト
python3 main.py --mode backtest
```

### **3. 監視・確認**
```bash
# システム状態確認
python3 scripts/testing/dev_check.py status

# 本番環境ログ確認（GCP）
gcloud logging read "resource.type=cloud_run_revision" --limit=10

# Discord通知でリアルタイム監視
```

## 📊 システムアーキテクチャ

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Layer    │───▶│  Feature Layer  │───▶│ Strategy Layer  │
│  (Bitbank API)  │    │ (15 Indicators) │    │ (5 Strategies)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
          │                       │                       │
          ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   ML Layer      │───▶│   Risk Layer    │───▶│ Execution Layer │
│ (3 Model Ens.)  │    │ (Kelly Crit.)   │    │ (Order Mgmt.)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🛠️ 技術スタック

### **言語・フレームワーク**
- **Python 3.13**: メイン開発言語・MLライブラリ互換性最適化
- **ccxt**: bitbank API統合・信用取引対応
- **pandas/numpy**: データ処理・数値計算
- **scikit-learn/XGBoost/LightGBM**: 機械学習モデル

### **インフラストラクチャ**  
- **Google Cloud Run**: 24時間稼働・自動スケーリング
- **Secret Manager**: API認証情報管理・具体的バージョン使用
- **Artifact Registry**: Dockerイメージ管理
- **Cloud Logging**: ログ管理・監視

### **CI/CD・品質管理**
- **GitHub Actions**: 自動テスト・品質チェック・デプロイ
- **pytest**: テストフレームワーク・625テスト
- **coverage**: コードカバレッジ測定・64.74%達成
- **flake8/black/isort**: コード品質・スタイル統一

## 📈 パフォーマンス

### **取引成果（目標）**
- **月間取引回数**: 100-200回
- **リスク管理**: 最大ドローダウン20%以下
- **稼働率**: 99%以上（24時間365日）

### **システム性能**
- **テスト成功率**: 100%（625テスト）
- **コードカバレッジ**: 64.74%
- **Kelly基準最適化**: 20→5取引緩和で実用性向上・取引機会拡大
- **実行時間**: 品質チェック約30秒
- **API応答時間**: 平均3秒以下
- **GCPリソース効率**: 古いイメージ削除・ストレージ最適化

## 🔧 設定・カスタマイズ

### **主要設定ファイル**
```
config/
├── core/
│   ├── unified.yaml         # 統合設定ファイル
│   ├── thresholds.yaml      # 閾値・パラメータ設定
│   └── feature_order.json   # 特徴量定義・順序管理
└── secrets/
    └── .env                 # API認証情報（要作成）
```

### **モード設定**
- **paper**: ペーパートレード（実資金なし）
- **live**: ライブトレード（実資金使用）
- **backtest**: 過去データでのバックテスト

### **戦略・ML調整**
- 各戦略の重み調整: `config/core/unified.yaml`
- 信頼度閾値調整: `strategies.confidence_threshold`
- MLモデル重み: `ensemble.weights`

## 📝 ドキュメント

### **開発者向け**
- **[システム詳細](src/README.md)**: アーキテクチャ・実装詳細
- **[戦略システム](src/strategies/README.md)**: 5戦略の詳細説明
- **[取引システム](src/trading/README.md)**: リスク管理・実行制御

### **運用者向け**
- **[要件定義](docs/開発計画/要件定義.md)**: システム仕様・技術要件
- **[運用手順](docs/運用手順/)**: デプロイ・監視・トラブル対応
- **[CI/CD設定](docs/CI-CD設定/)**: GitHub Actions・品質管理

## ⚠️ リスク・免責事項

- **投資リスク**: 仮想通貨取引には元本割れのリスクがあります
- **システムリスク**: 自動取引システムの不具合による損失の可能性
- **市場リスク**: 急激な市場変動への対応限界
- **免責**: 本システムの使用による損失について作成者は責任を負いません

**推奨**: 少額資金でのテスト運用から開始し、システム理解後に段階的に拡大

## 📞 サポート

- **Issues**: GitHub Issues での問題報告
- **Discussion**: 機能要望・質問
- **Security**: セキュリティ問題は非公開で報告

---

**⚡ 高頻度AI自動取引システム** - 15特徴量・5戦略・3MLモデル・Kelly基準最適化・GCPリソース最適化による企業級BTC取引ボット 🚀
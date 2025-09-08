# 🚀 Crypto-Bot - AI自動取引システム

**bitbank信用取引専用のAI自動取引システム**

[![Python](https://img.shields.io/badge/python-3.12-blue)](https://python.org) [![Tests](https://img.shields.io/badge/tests-625%20passed-success)](tests/) [![Coverage](https://img.shields.io/badge/coverage-58.64%25-green)](coverage-reports/) [![Cloud Run](https://img.shields.io/badge/Cloud%20Run-Running-success)](https://cloud.google.com/run)

---

## 🎯 システム概要

**AI自動取引システム**は、bitbank信用取引専用のBTC/JPY自動取引ボットです。4つの取引戦略と機械学習を組み合わせ、12の技術指標を統合分析することで、24時間自動取引を実現します。

### **主要仕様**
- **対象市場**: bitbank信用取引・BTC/JPY専用
- **資金規模**: 1万円スタート → 最大50万円（段階的拡大）
- **取引頻度**: 月100-200回・高頻度取引
- **稼働体制**: 24時間自動取引・Cloud Run稼働
- **品質保証**: 625テスト・58.64%カバレッジ・CI/CD統合

## 🌟 主要機能

### **🤖 AI取引システム**
- **4戦略統合**: ATRベース・フィボナッチ・もちぽよアラート・マルチタイムフレーム戦略
- **機械学習予測**: 3モデルアンサンブル（LightGBM・XGBoost・RandomForest）
- **12特徴量分析**: RSI・MACD・ボリンジャーバンド・ATR・EMA等の技術指標統合
- **競合解決システム**: 戦略間の判定競合を重み付けで自動解決

### **📊 リスク管理システム**
- **Kelly基準**: 数学的最適ポジションサイズ計算
- **ドローダウン制御**: 20%制限・連続損失5回で自動停止
- **3段階判定**: APPROVED・CONDITIONAL・DENIED の安全判定
- **異常検知**: スプレッド・価格スパイク・API遅延の自動検知

### **🔧 運用監視システム**
- **24時間稼働**: Google Cloud Run・自動スケーリング
- **Discord監視**: 3階層通知（Critical/Warning/Info）・リアルタイムアラート
- **品質保証**: 自動テスト・コードカバレッジ・継続的品質監視
- **週次学習**: 機械学習モデルの自動再学習・性能向上

## 🚀 クイックスタート

### **📋 前提条件**
```bash
# Python 3.12（MLライブラリ互換性最適化）
python3 --version

# 依存関係インストール
pip install -r requirements.txt
```

### **🔑 環境設定**
```bash
# 必須環境変数（.env作成）
BITBANK_API_KEY=your_api_key
BITBANK_API_SECRET=your_api_secret
DISCORD_WEBHOOK_URL=your_webhook_url
```

### **🎮 基本実行**
```bash
# ペーパートレード（推奨・安全）
python3 main.py --mode paper

# 本番取引（十分な検証後のみ）
python3 main.py --mode live

# バックテスト実行
python3 main.py --mode backtest
```

### **🔍 動作確認**
```bash
# 品質チェック（開発時推奨）
bash scripts/testing/checks.sh                    # 625テスト・約30秒

# システム状態確認
python3 scripts/testing/dev_check.py validate     # 設定・整合性チェック
```

## 🏗️ システム構成

### **📊 システムアーキテクチャ**
```
📊 monitoring/     ← Discord監視・3階層通知
    ↕️
🎯 trading/        ← リスク管理・Kelly基準・注文実行
    ↕️
📈 strategies/     ← 4戦略統合・競合解決・重み付け判定
    ↕️
🤖 ml/            ← 3モデルアンサンブル・週次学習
    ↕️
⚙️  features/      ← 12特徴量生成・技術指標統合
    ↕️
📡 data/           ← Bitbank API・市場データ取得
    ↕️
🏗️  core/          ← 基盤システム・統合制御
```

### **🎯 データフロー**
```
1. Bitbank API → 市場データ取得（4h/15m足）
        ↓
2. 12特徴量生成 → 技術指標・統計指標
        ↓
3. 4戦略実行 → シグナル統合・重み付け
        ↓
4. ML予測 → 3モデルアンサンブル予測
        ↓
5. リスク評価 → Kelly基準・3段階判定
        ↓
6. 取引実行 → ペーパートレード・実取引
        ↓
7. Discord通知 → 実行結果・異常通知
```

### **🛠️ 技術スタック**
- **言語**: Python 3.13・asyncio・型注釈
- **AI/ML**: LightGBM・XGBoost・RandomForest・scikit-learn
- **取引所**: Bitbank API・ccxt・信用取引対応
- **インフラ**: Google Cloud Run・Secret Manager・Logging
- **監視**: Discord Webhooks・構造化ログ・アラート
- **品質**: pytest・GitHub Actions・自動CI/CD

## 📚 ドキュメント

### **システム実装**
- **[システム全体](src/README.md)**: レイヤードアーキテクチャ・データフロー・使用方法
- **[戦略システム](src/strategies/README.md)**: 4戦略統合・競合解決・重み付け判定
- **[取引システム](src/trading/README.md)**: リスク管理・Kelly基準・異常検知・注文実行

### **開発・運用**
- **[開発ガイド](CLAUDE.md)**: システム詳細・開発手順・トラブルシューティング
- **[プロジェクト仕様](docs/)**: 要件定義・開発履歴・運用マニュアル・CI/CD設定

### **設定・テスト**
- **設定管理**: [config/core/unified.yaml](config/core/unified.yaml) - 統合設定ファイル
- **テスト仕様**: [tests/](tests/) - 625テスト構成・品質基準
- **品質チェック**: [scripts/testing/checks.sh](scripts/testing/checks.sh) - 開発必須

## 🔧 開発・メンテナンス

### **開発コマンド**
```bash
# 開発環境セットアップ
pip install -r requirements.txt
python3 scripts/ml/create_ml_models.py --verbose

# コード品質チェック
bash scripts/testing/checks.sh              # 全品質チェック
python3 -m pytest tests/ -v                 # 個別テスト実行

# 本番デプロイ
git add . && git commit -m "feat: 機能追加"
git push origin main                         # CI/CD自動実行
```

### **トラブルシューティング**
```bash
# システム状態確認
bash scripts/testing/checks.sh                    # 品質・設定チェック
python3 scripts/testing/dev_check.py validate     # 設定整合性確認

# 本番環境確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1
gcloud logging read "resource.type=cloud_run_revision" --limit=10
```

## 📊 品質・運用実績

### **品質指標**
- **テスト**: 625テスト100%成功・58.64%カバレッジ・回帰防止
- **コード品質**: flake8・black・isort・型注釈・JST対応
- **CI/CD**: GitHub Actions・自動品質ゲート・30秒実行
- **設定管理**: ハードコード排除・階層化設定・保守性重視

### **運用状況**
- **稼働率**: 24時間連続・Cloud Run自動スケーリング
- **監視体制**: Discord 3階層通知・異常検知・リアルタイムアラート
- **データ処理**: 4h/15m足取得・12特徴量生成・リアルタイム分析
- **取引実行**: Kelly基準・ドローダウン制御・自動ポジション管理

## ⚠️ 重要事項

### **リスク・注意事項**
- **投資リスク**: 暗号資産取引にはリスクが伴います
- **資金管理**: 必ず余裕資金での運用を推奨
- **段階的運用**: 少額から開始し、十分な検証後に拡大
- **監視必須**: Discord通知・ログ監視による継続的確認

### **システム要件**
- **Python**: 3.11以上・async/await対応
- **メモリ**: 本番運用1GB・バックテスト2GB推奨
- **API制限**: Bitbank レート制限対応・接続数制限管理
- **環境変数**: API認証・Discord通知設定必須

### **サポート・問い合わせ**
- **システム問題**: [CLAUDE.md](CLAUDE.md) のトラブルシューティング参照
- **設定問題**: [docs/](docs/) の運用マニュアル確認
- **開発相談**: [開発ガイド](CLAUDE.md) の開発手順参照

---

**🚀 AI自動取引システム**: 4戦略統合・3モデルアンサンブル・Kelly基準リスク管理・Discord監視による完全自動化。625テスト品質保証・58.64%カバレッジ・CI/CD統合により、安全で効率的な24時間自動取引を実現。

**最終更新**: 2025年9月8日
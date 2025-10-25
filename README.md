# 🚀 Crypto-Bot - AI自動取引システム

**Phase 49完了・bitbank BTC/JPY専用・企業級品質達成**

[![Tests](https://img.shields.io/badge/tests-1065%20passed-success)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-66.72%25-green)](coverage-reports/)
[![Phase 49](https://img.shields.io/badge/Phase%2049-Completed-brightgreen)](docs/)

---

## ⚡ クイックスタート

### 💻 ローカル実行

```bash
# 1. 依存関係インストール
pip install -r requirements.txt

# 2. 環境設定（API認証情報設定）
cp config/secrets/.env.example config/secrets/.env
# → .envファイルにbitbank API・Discord Webhook設定

# 3. Phase 49品質チェック
bash scripts/testing/checks.sh  # 1,065テスト・66.72%カバレッジ・約80秒

# 4. システム実行
bash scripts/management/run_safe.sh local paper  # ペーパートレード
bash scripts/management/run_safe.sh local live   # ライブトレード
```

### ☁️ 本番環境確認

```bash
# Cloud Run稼働確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1

# システムログ確認
gcloud logging read "resource.type=cloud_run_revision" --limit=10
```

---

## 🎯 システム概要

AI自動取引システムは、**bitbank信用取引専用のBTC/JPY自動取引ボット**です。5つの取引戦略と機械学習を統合し、55の特徴量を総合分析することで、24時間自動取引を実現します。

### 運用仕様

- **対象市場**: bitbank信用取引・BTC/JPY専用
- **資金規模**: 1万円スタート → 最大50万円（段階的拡大）
- **取引頻度**: 月100-200回・5分間隔実行
- **稼働体制**: 24時間自動取引・Cloud Run稼働
- **インフラコスト**: 月額700-900円（GCP）
- **品質保証**: 1,065テスト100%成功・66.72%カバレッジ

### 最新Phase完了

**Phase 49（2025/10/26）**: バックテスト完全改修
- TradeTracker実装（エントリー/エグジットペアリング・損益計算）
- matplotlib可視化（エクイティカーブ・損益分布・ドローダウン・価格チャート）
- バックテスト信頼性100%達成・維持率80%確実遵守

**Phase 48（2025/10/22）**: Discord週間レポート実装
- 通知99%削減（300-1,500回/月 → 4回/月）
- 損益曲線グラフ・コスト35%削減

**Phase 47（2025/10/22）**: 確定申告対応システム実装
- SQLite取引記録・移動平均法損益計算
- 作業時間95%削減（10時間 → 30分）

**Phase 46（2025/10/22）**: デイトレード特化・シンプル設計回帰
- スイングトレード機能削除・個別TP/SL管理回帰
- コードベース-1,041行削減（シンプル性・保守性大幅向上）

詳細: [開発履歴](docs/開発履歴/)

---

## 🤖 主要機能

### AI取引システム

- **5戦略統合**: ATRBased・MochiPoy・MultiTimeframe・DonchianChannel・ADXTrendStrength
- **動的信頼度計算**: 市場適応型信頼度0.25-0.6・フォールバック回避
- **Strategy-Aware ML**: 55特徴量学習（50基本+5戦略信号）・ML統合率100%達成
- **3モデルアンサンブル**: LightGBM 40%・XGBoost 40%・RandomForest 20%
- **F1スコア**: 0.56-0.61達成

### リスク管理・取引実行

- **個別TP/SL管理**: SL 1.5%・TP 2%・RR比1.33:1（デイトレード特化・Phase 46）
- **適応型ATR**: ボラティリティ別SL調整（低2.5x・通常2.0x・高1.5x）
- **完全指値オンリー**: 100%指値注文・年間¥150,000削減・約定率90-95%
- **Kelly基準最適化**: 初期固定サイズ・5取引で実用性向上
- **証拠金チェックリトライ**: Error 20001対策・3回リトライ上限

### 運用監視システム

- **24時間稼働**: Google Cloud Run・自動スケーリング
- **週間レポート**: 損益曲線グラフ・毎週月曜9時自動送信
- **確定申告システム**: SQLite取引記録・移動平均法損益計算・CSV出力
- **品質保証**: 1,065テスト自動実行・66.72%カバレッジ
- **週次ML学習**: 過去180日データで毎回ゼロから再学習・市場変化適応

---

## 📂 システムアーキテクチャ

```
🏗️ レイヤードアーキテクチャ設計
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  📊 Data Layer  │───▶│ 📈 Feature Layer│───▶│ 🎯 Strategy Layer│
│  (Bitbank API)  │    │ (15 Indicators) │    │ (5 Strategies)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
          │                       │                       │
          ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  🧠 ML Layer    │───▶│ ⚖️ Risk Layer   │───▶│🛡️ExecutionService│
│ (3 Model Ens.)  │    │ (Kelly Crit.)   │    │(BitbankClient)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### ディレクトリ構成

```
src/
├── core/                   # 基盤システム（設定・実行制御・レポート）
├── data/                   # データ層（Bitbank API・キャッシュ）
├── features/               # 特徴量生成（15指標）
├── strategies/             # 5戦略統合システム
├── ml/                     # ML統合（3モデルアンサンブル）
├── trading/                # 取引管理層（5層アーキテクチャ）
├── backtest/               # バックテストシステム（Phase 49完全改修）
└── monitoring/             # 週間レポート（Phase 48）

tax/                        # 確定申告システム（Phase 47）
scripts/                    # 品質チェック・最適化・レポート生成
config/                     # 統一設定管理（features/unified/thresholds）
```

詳細: [システム詳細](src/README.md)

---

## 🛠️ 技術スタック

### 言語・フレームワーク

- **Python 3.13**: メイン開発言語・MLライブラリ互換性最適化
- **ccxt**: bitbank API統合・信用取引対応・非同期処理
- **pandas/numpy**: データ処理・特徴量生成
- **scikit-learn/XGBoost/LightGBM**: 機械学習モデル・ProductionEnsemble

### インフラストラクチャ（GCP）

- **Google Cloud Run**: 24時間稼働・自動スケーリング・1Gi・1CPU
- **Secret Manager**: API認証情報管理
- **Artifact Registry**: Dockerイメージ管理
- **Cloud Logging**: ログ管理・監視・JST時刻対応

### CI/CD・品質管理

- **GitHub Actions**: 自動テスト・品質チェック・週次ML学習・デプロイ
- **pytest**: テストフレームワーク・1,065テスト100%成功
- **coverage**: コードカバレッジ測定・66.72%達成
- **flake8/black/isort**: コード品質・スタイル統一

---

## ⚙️ 設定・カスタマイズ

### 主要設定ファイル

```
config/
├── core/
│   ├── unified.yaml         # 統合設定ファイル（一元管理）
│   ├── thresholds.yaml      # 閾値・パラメータ設定（ML統合設定含む）
│   ├── features.yaml        # 機能トグル設定
│   └── feature_order.json   # 特徴量定義・順序管理
└── secrets/
    └── .env                 # API認証情報（要作成）
```

### 実行モード設定

- **paper**: ペーパートレード（実資金なし・検証用）
- **live**: ライブトレード（実資金使用・本番取引）
- **backtest**: 過去データでのバックテスト（戦略検証）

### 初期残高設定

**1万円→10万円・50万円への変更が`config/core/unified.yaml` 1箇所のみで完結**

```yaml
# config/core/unified.yaml
mode_balances:
  paper:
    initial_balance: 10000.0    # 1万円 → 10万円なら 100000.0
  live:
    initial_balance: 10000.0    # 段階的拡大: 1万→10万→50万
  backtest:
    initial_balance: 10000.0
```

### 戦略・ML調整

- **各戦略の重み調整**: `config/core/unified.yaml`
- **信頼度閾値調整**: `strategies.confidence_threshold`（0.25-0.6）
- **MLモデル重み**: `ensemble.weights`（LightGBM 40%・XGBoost 40%・RandomForest 20%）
- **ML統合設定**: `config/core/thresholds.yaml`

---

## 📚 ドキュメント

### 開発者向け

- **[CLAUDE.md](CLAUDE.md)**: 開発ガイド・品質基準・Phase履歴
- **[システム詳細](src/README.md)**: アーキテクチャ・実装詳細・レイヤード設計
- **[戦略システム](src/strategies/README.md)**: 5戦略の詳細説明・動的信頼度計算
- **[取引システム](src/trading/README.md)**: リスク管理・ExecutionService実行制御

### 運用者向け

- **[統合運用ガイド](docs/運用手順/統合運用ガイド.md)**: デプロイ・監視・トラブル対応
- **[開発履歴](docs/開発履歴/)**: Phase 1-49の詳細な開発経緯・技術変遷
- **[要件定義](docs/開発計画/要件定義.md)**: システム仕様・技術要件
- **[稼働チェック](docs/稼働チェック/)**: システム診断・緊急対応マニュアル

---

## 📈 パフォーマンス・品質指標

### システム性能

- **テスト成功率**: 100%（1,065テスト）・CI/CD品質ゲート通過
- **コードカバレッジ**: 66.72%・品質基準大幅超過
- **ML統合率**: 100%達成（3段階統合ロジック）
- **ML性能**: F1スコア0.56-0.61
- **バックテスト性能**: 45分実行（10倍高速化達成）
- **システム安定性**: Container exit(1)完全解消・Graceful Degradation実装

### コスト・収益最適化

- **インフラコスト**: 月額700-900円（35%削減達成）
- **手数料最適化**: 年間¥150,000削減（完全指値オンリー）
- **パラメータ最適化**: 79パラメータOptuna自動最適化・期待効果+50-70%収益向上

---

## ⚠️ リスク・免責事項

- **💰 投資リスク**: 仮想通貨取引には元本割れのリスクがあります
- **🤖 システムリスク**: 自動取引システムの不具合による損失の可能性
- **📊 市場リスク**: 急激な市場変動への対応限界・ボラティリティ影響
- **📋 免責**: 本システムの使用による損失について作成者は責任を負いません

**🎯 推奨**: 少額資金（1万円）でのテスト運用から開始し、システム理解後に段階的拡大（10万→50万円）

---

## 📞 サポート

- **🐛 Issues**: GitHub Issuesでの問題報告
- **💬 Discussion**: 機能要望・質問・フィードバック
- **🔒 Security**: セキュリティ問題は非公開で報告

---

**📅 最終更新**: 2025年10月26日 - Phase 49完了

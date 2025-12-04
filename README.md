# 🚀 Crypto-Bot - AI自動取引システム

**bitbank BTC/JPY専用・企業級品質達成・本番環境稼働中**

[![Tests](https://img.shields.io/badge/tests-1294%20passed-success)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-68.95%25-green)](coverage-reports/)
[![System](https://img.shields.io/badge/system-stable-brightgreen)](docs/)
[![Production](https://img.shields.io/badge/status-Production-success)](docs/)

---

## ⚡ クイックスタート

### 💻 ローカル実行

```bash
# 1. 依存関係インストール
pip install -r requirements.txt

# 2. 環境設定（API認証情報設定）
cp config/secrets/.env.example config/secrets/.env
# → .envファイルにbitbank API・Discord Webhook設定

# 3. 品質チェック
bash scripts/testing/checks.sh  # 1,294テスト・68.95%カバレッジ

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

AI自動取引システムは、**bitbank信用取引専用のBTC/JPY自動取引ボット**です。7つの取引戦略と機械学習を統合し、**56の特徴量**（49基本+7戦略シグナル）を総合分析することで、24時間自動取引を実現します。

**最新状態（2025/12/03）**: Phase 58.5完了・bitbank API 20001エラー緊急修正・Optuna最適化基盤修正・Phase 59戦略分析進行中。

### 運用仕様

- **対象市場**: bitbank信用取引・BTC/JPY専用
- **資金規模**: 1万円スタート → 最大50万円（段階的拡大）
- **取引頻度**: 月100-200回・5分間隔実行
- **稼働体制**: 24時間自動取引・Cloud Run稼働・ゼロダウンタイム
- **インフラコスト**: 月額700-900円（GCP）
- **品質保証**: 1,294テスト100%成功・68.95%カバレッジ・稼働率99.94%

### 最新システム状態（2025/12/03）

**Phase 58.5完了 - bitbank API 20001エラー緊急修正**:
- **問題**: 約23時間の取引停止（12/2 07:56〜12/3 06:55 JST）
- **修正**: GETリクエスト署名に`/v1`プレフィックス追加
- **詳細**: [Phase 58開発履歴](docs/開発履歴/Phase_58.md)

**Phase 58完了 - Optuna最適化基盤修正**:
- **Sharpe計算修正**: 年率換算削除・境界値クリッピング追加
- **PFベーススコア**: 安定した最適化スコア計算導入
- **詳細**: [Phase 58開発履歴](docs/開発履歴/Phase_58.md)

**Phase 56完了 - 99%稼働率達成**:
- **Phase 56.2**: 自動タイムアウト無効化・Container crash 50回/24h → 0回
- **Phase 56.3**: 緊急停止ワークフロー・GCPクリーンアップ改善
- **Phase 56.4**: 本番エントリーゼロ問題解決（戦略条件緩和・Atomic Entry補償）
- **詳細**: [Phase 56開発履歴](docs/開発履歴/Phase_56.md)

**Phase 53.8.3完了 - 48時間エントリーゼロ問題解決**:
- **修正**: ML統合設定最適化・最新180日データ再学習・CV F1: 0.52-0.59達成
- **詳細**: [Phase 53開発履歴](docs/開発履歴/Phase_53.md)

**主要システム改善**:
- **バックテスト完全改修**（2025/10/26）: TradeTracker・matplotlib可視化・証拠金維持率80%遵守
- **Discord週間レポート**（2025/10/22）: 通知99%削減・損益曲線グラフ
- **確定申告対応**（2025/10/22）: SQLite取引記録・作業時間95%削減
- **外部API削除**（2025/11/01）: システム安定性向上・保守性+20%
- **デイトレード特化**（2025/10/22）: コードベース-1,041行削減

**開発基盤**:
- **品質**: 1,294テスト・68.95%カバレッジ・技術的負債ゼロ・稼働率99.94%
- **拡張性**: Registry Pattern実装（93%向上）
- **システム**: 7戦略・56特徴量・レジーム別動的TP/SL

詳細: [開発履歴](docs/開発履歴/)

---

## 🤖 主要機能

### AI取引システム

- **7戦略統合**: ATRBased・BBReversal・StochasticReversal・MeanReversion・ADXTrendStrength（有効5戦略）+ DonchianChannel・MACDEMACrossover（無効化2戦略）
- **動的戦略管理**: Registry Pattern・93%削減達成・戦略追加が2ファイルのみ
- **Strategy-Aware ML**: **56特徴量学習**（49基本+7戦略シグナル）・ML統合率30-40%達成（Phase 60.7最適化）
- **3モデルアンサンブル**: LightGBM 50%・XGBoost 30%・RandomForest 20%（**n_jobs=1設定**・**CV F1: 0.52-0.59**）
- **真の3クラス分類**: SELL/HOLD/BUY・F1スコア改善+9.7%
- **2段階Graceful Degradation**: ensemble_full.pkl（56特徴量）→ensemble_basic.pkl（49特徴量）→DummyModel・ゼロダウンタイム保証

### リスク管理・取引実行

- **レジーム別動的TP/SL**: tight_range（TP 0.6%/SL 0.8%）・normal_range（TP 1.0%/SL 0.7%）・trending（TP 2.0%/SL 2.0%）
- **Atomic Entry管理**: エントリー・TP・SL同時配置・孤児注文完全防止
- **適応型ATR**: ボラティリティ別SL調整（低2.5x・通常2.0x・高1.5x）
- **完全指値オンリー**: 100%指値注文・年間¥150,000削減・約定率90-95%
- **Kelly基準最適化**: 初期固定サイズ・5取引で実用性向上
- **証拠金維持率80%遵守**: API直接取得・過剰レバレッジ防止
- **ドローダウン管理**: 連続損失8回制限・クールダウン6時間・最大DD 20%

### 運用監視システム

- **24時間稼働**: Google Cloud Run・自動スケーリング・99%稼働率目標
- **週間レポート**: 損益曲線グラフ・毎週月曜9時自動送信・通知99%削減
- **週次バックテスト**: GitHub Actions自動実行・180日データ検証
- **確定申告システム**: SQLite取引記録・移動平均法損益計算・CSV出力
- **品質保証**: 1,252テスト自動実行・66.78%カバレッジ・CI/CD完全自動化
- **週次ML学習**: 過去180日データで毎回ゼロから再学習・市場変化適応

---

## 📂 システムアーキテクチャ

```
🏗️ レイヤードアーキテクチャ設計
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  📊 Data Layer  │───▶│ 📈 Feature Layer│───▶│ 🎯 Strategy Layer│
│  (Bitbank API)  │    │ (15 Indicators) │    │ (6 Strategies)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
          │                       │                       │
          ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  🧠 ML Layer    │───▶│ ⚖️ Risk Layer   │───▶│🛡️ExecutionService│
│ (3 Model Ens.)  │    │ (Kelly/DD管理)  │    │(Atomic Entry)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### ディレクトリ構成

```
src/
├── core/                   # 基盤システム（設定・実行制御・レポート）
├── data/                   # データ層（Bitbank API・キャッシュ）
├── features/               # 特徴量生成（15指標・49基本特徴量）
├── strategies/             # 6戦略統合システム（Phase 51.7・Registry Pattern）
├── ml/                     # ML統合（3モデルアンサンブル・55特徴量）
├── trading/                # 取引管理層（5層アーキテクチャ・Atomic Entry）
├── backtest/               # バックテストシステム（Phase 49完全改修）
└── monitoring/             # 週間レポート（Phase 48・通知99%削減）

tax/                        # 確定申告システム（Phase 47・作業時間95%削減）
scripts/                    # 品質チェック・最適化・レポート生成
config/core/                # 統一設定管理（Phase 52.5最適化完了）
  ├── unified.yaml          # 基本設定（モード別残高・戦略・ML）
  ├── thresholds.yaml       # 動的閾値（ML統合・リスク管理）
  ├── features.yaml         # 機能トグル設定
  ├── feature_order.json    # 特徴量定義（55特徴量・Single Source of Truth）
  └── strategies.yaml       # 戦略定義（6戦略・動的ロード）
```

詳細: [システム詳細](src/README.md)

---

## 🛠️ 技術スタック

### 言語・フレームワーク

- **Python 3.11**: メイン開発言語・GCP gVisor互換性確保・99%稼働率達成（Phase 53.5/53.8）
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
- **pytest**: テストフレームワーク・1,294テスト100%成功
- **coverage**: コードカバレッジ測定・68.95%達成
- **flake8/black/isort**: コード品質・スタイル統一

---

## ⚙️ 設定・カスタマイズ

### 主要設定ファイル（Phase 52.5最適化完了）

```
config/core/                      # 統一設定管理（Single Source of Truth確立）
├── unified.yaml                  # 基本設定（モード別残高・戦略・ML・重複削除済み）
├── thresholds.yaml               # 動的閾値（ML統合・リスク管理・視覚的改善）
├── features.yaml                 # 機能トグル設定
├── feature_order.json            # 特徴量定義（55特徴量・唯一の真実源）
└── strategies.yaml               # 戦略定義（6戦略・動的ロード・Registry Pattern）

config/secrets/
└── .env                          # API認証情報（要作成・gitignore対象）
```

**Phase 52.5改善点**:
- **重複削除**: 110行削減（特徴量リスト・consecutive_loss_limit等）
- **Single Source of Truth**: feature_order.json（55特徴量）が唯一の真実源
- **使用箇所ドキュメント**: 10+主要設定に使用箇所コメント追加
- **視覚的改善**: 12個のセクション区切り追加（thresholds.yaml）

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

### システム性能（Phase 55完了時点）

- **テスト成功率**: 100%（1,294テスト）・CI/CD品質ゲート通過
- **コードカバレッジ**: 68.95%・品質基準達成（65%目標超過）
- **稼働率**: 99.94%達成（Phase 55.9）
- **ML統合率**: 100%達成（3段階統合ロジック）
- **ML性能**: 真の3クラス分類・F1スコア改善+9.7%（Phase 51.9）
- **バックテスト性能**: 45分実行（10倍高速化達成）・週次自動実行（Phase 52.1）
- **システム安定性**: Container exit(1)完全解消・Graceful Degradation実装・ゼロダウンタイム保証
- **設定管理**: Phase 55最適化完了・重複削除110行・Single Source of Truth確立
- **バックテスト**: Phase 55クールダウン修正・エントリー数20倍改善（1-2→43回/7日）

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

**📅 最終更新**: 2025年12月3日 - Phase 58.5完了（bitbank API 20001エラー緊急修正・/v1署名プレフィックス対応）

**🚀 現在の状態**:
- **Phase 58.5完了**: bitbank API認証エラー緊急修正・23時間の取引停止を解消
- **Phase 58完了**: Optuna最適化基盤修正（Sharpe計算・PFベーススコア・2段階最適化）
- **Phase 59進行中**: 戦略分析・改良（ADX閾値調整・HOLD率改善）
- **本番稼働中**: GCP Cloud Run・24時間自動取引・6戦略・55特徴量
- **品質保証**: 1,294テスト100%成功・68.95%カバレッジ・CI/CD完全自動化

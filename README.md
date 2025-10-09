# 🚀 **Crypto-Bot** - Phase 37.4完了・AI自動取引システム

**🎯 bitbank信用取引専用・BTC/JPY高頻度自動取引ボット・SL配置問題完全解決・コスト最適化35-45%達成**

[![Python](https://img.shields.io/badge/python-3.13-blue)](https://python.org) [![Tests](https://img.shields.io/badge/tests-653%20passed-success)](tests/) [![Coverage](https://img.shields.io/badge/coverage-58.62%25-green)](coverage-reports/) [![Phase](https://img.shields.io/badge/Phase%2037.4-Completed-brightgreen)](docs/) [![ML Integration](https://img.shields.io/badge/ML%20Integration-Active-blue)](src/core/services/) [![Cloud Run](https://img.shields.io/badge/Cloud%20Run-Running-success)](https://cloud.google.com/run) [![Config](https://img.shields.io/badge/Unified%20Config-Complete-orange)](config/) [![GCP](https://img.shields.io/badge/GCP%20Optimized-Complete-blue)](docs/)

---

## ⚡ **クイックスタート**（即座実行）

### **💻 ローカル実行**
```bash
# 1. 依存関係インストール
pip install -r requirements.txt

# 2. 環境設定（API認証情報設定）
cp config/secrets/.env.example config/secrets/.env
# → .envファイルにbitbank API・Discord Webhook設定

# 3. Phase 37.4品質チェック
bash scripts/testing/checks.sh  # 653テスト・58.62%カバレッジ・約72秒

# 4. システム実行
bash scripts/management/run_safe.sh local paper  # ペーパートレード
bash scripts/management/run_safe.sh local live   # ライブトレード
```

### **☁️ 本番環境確認**
```bash
# Cloud Run稼働確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1

# システムログ確認
gcloud logging read "resource.type=cloud_run_revision" --limit=10
```

---

## 🎯 **システム概要**（Phase 37.4完了）

**AI自動取引システム**は、bitbank信用取引専用のBTC/JPY自動取引ボットです。5つの取引戦略と機械学習を**真に統合**し、15の技術指標を総合分析することで、24時間自動取引を実現する**真のハイブリッドMLbot**です。

### **✅ 最新Phase完了ステータス**

**Phase 37.4（2025/10/09）**: SL未配置問題根本解決（エラー30101解消・trigger_price修正・bitbank API完全準拠）

**Phase 37.3（2025/10/08）**: Discord通知最適化・実行頻度最適化（3分→5分間隔・コスト削減35-45%）

**詳細な開発履歴**: [Phase_31-37.md](docs/開発履歴/Phase_31-37.md) 参照

### **🎯 運用仕様**
- **🏦 対象市場**: bitbank信用取引・BTC/JPY専用
- **💰 資金規模**: 1万円スタート → 最大50万円（段階的拡大）
- **📊 取引頻度**: 月100-200回・**5分間隔実行**（Phase 37.3最適化完了）
- **🕐 稼働体制**: 24時間自動取引・Cloud Run稼働
- **🏗️ インフラコスト**: **月額1,100-1,300円**（Phase 37.3コスト削減35-45%達成）
- **🤖 ML統合**: 戦略とMLが融合した真のハイブリッドMLbot・市場適応性向上
- **🧪 品質保証**: 653テスト100%成功・58.62%カバレッジ・CI/CD統合

---

## 🤖 **主要機能**（技術仕様）

### **🧠 AI取引システム（核心機能）**
- **📈 5戦略統合**: ATRBased・MochiPoy・MultiTimeframe・DonchianChannel・ADXTrendStrength
- **🎯 動的信頼度計算**: 市場適応型信頼度0.25-0.6・フォールバック完全回避
- **🤖 ML予測統合**: 戦略70% + ML30%加重平均・一致ボーナス/不一致ペナルティ・真のハイブリッドMLbot実現
- **🧠 機械学習予測**: 3モデルアンサンブル（LightGBM 50%・XGBoost 30%・RandomForest 20%）
- **📊 15特徴量分析**: RSI・MACD・ボリンジャーバンド・ATR・EMA・Donchianチャネル・ADX等統合

### **⚙️ リスク管理・取引実行システム**
- **💰 TP/SL自動配置**: テイクプロフィット/ストップロス・完全トレーディングサイクル実現
- **🛡️ ExecutionService**: Silent Failure根本解決・実取引実行確保
- **📈 Kelly基準最適化**: 初期固定サイズ・5取引で実用性向上
- **📊 ポジション制限**: 最大3ポジション・1日20取引・30%資本使用制限
- **🚨 緊急ストップロス**: 3%価格変動・5%含み損で強制決済・急騰急落対応
- **📈 保証金監視**: 維持率監視・4段階判定・新規エントリー影響予測
- **💱 指値注文オプション**: ML信頼度連動・Maker手数料-0.02%獲得

### **☁️ 運用監視システム（24時間稼働）**
- **🕐 Cloud Run稼働**: Google Cloud Run・自動スケーリング・ヘルスチェック
- **📢 Discord監視**: 3階層通知（Critical/Warning/Info）・リアルタイムアラート
- **🗂️ GCPリソース最適化**: 古いイメージ削除・容量最適化・コスト削減
- **🧪 品質保証**: 653テスト自動実行・58.62%カバレッジ・継続的品質監視
- **🔄 週次学習**: 過去180日データで毎回ゼロから再学習・市場変化適応

---

## 📂 **システムアーキテクチャ**

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

### **📁 コードベース構造**
```
src/
├── core/                   # 🔧 基盤システム（統一設定管理）
│   ├── orchestration/          # システム統合制御・TradingOrchestrator
│   ├── config/                 # 設定管理・unified.yaml・特徴量管理
│   ├── execution/              # 取引実行制御・ExecutionService
│   ├── reporting/              # Discord通知・レポーティング
│   └── services/               # GracefulShutdown・システムサービス
├── data/                   # 📊 データ層（Bitbank API・キャッシュ）
├── features/               # 📈 15特徴量生成システム
├── strategies/             # 🎯 5戦略統合システム
├── ml/                     # 🧠 ProductionEnsemble・3モデル統合
├── trading/                # ⚖️ リスク管理・ExecutionService取引実行
├── backtest/               # 📉 バックテストシステム
└── monitoring/             # 📢 Discord 3階層監視

📋 重要ファイル:
├── scripts/testing/checks.sh       # 653テスト品質チェック（開発必須）
├── config/core/unified.yaml        # 統一設定ファイル
└── models/production/              # 本番MLモデル（週次自動更新）
```

---

## 🛠️ **技術スタック**

### **🐍 言語・フレームワーク**
- **Python 3.13**: メイン開発言語・MLライブラリ互換性最適化・GitHub Actions安定版
- **ccxt**: bitbank API統合・信用取引対応・非同期処理完全対応
- **pandas/numpy**: データ処理・数値計算・15特徴量生成基盤
- **scikit-learn/XGBoost/LightGBM**: 機械学習モデル・ProductionEnsemble 3モデル統合

### **☁️ インフラストラクチャ（GCP最適化）**
- **Google Cloud Run**: 24時間稼働・自動スケーリング・1Gi・1CPU
- **Secret Manager**: API認証情報管理・具体的バージョン使用（key:latest禁止）
- **Artifact Registry**: Dockerイメージ管理・GCPリソース最適化完了
- **Cloud Logging**: ログ管理・監視・JST時刻対応

### **🔄 CI/CD・品質管理**
- **GitHub Actions**: 自動テスト・品質チェック・週次ML学習・デプロイ
- **pytest**: テストフレームワーク・653テスト100%成功
- **coverage**: コードカバレッジ測定・58.62%達成・品質ゲート
- **flake8/black/isort**: コード品質・スタイル統一

---

## 📈 **パフォーマンス・品質指標**

### **🎯 取引成果（運用目標）**
- **📊 月間取引回数**: 100-200回・**5分間隔実行**（Phase 37.3最適化完了）
- **⚖️ リスク管理**: 最大ドローダウン20%以下・Kelly基準最適化
- **🕐 稼働率**: 99%以上（24時間365日）・Cloud Run自動スケーリング

### **🧪 システム性能**
- **✅ テスト成功率**: 100%（653テスト）・CI/CD品質ゲート通過
- **📊 コードカバレッジ**: 58.62%・品質基準維持・全機能テストカバー
- **⚡ バックテスト性能**: 45分実行（10倍高速化達成）・特徴量/ML予測バッチ化完了
- **🛡️ システム安定性**: Container exit(1)完全解消・Graceful Degradation実装
- **🤖 ML統合効果**: 戦略とMLの融合による市場適応性向上・真のハイブリッドMLbot実現
- **⚡ 実行時間**: 品質チェック約72秒・653テスト高速実行
- **🔗 API応答時間**: 平均3秒以下・bitbank API統合最適化
- **☁️ GCPコスト**: 月額1,100-1,300円（35-45%削減達成）

---

## ⚙️ **設定・カスタマイズ**

### **📁 主要設定ファイル**
```
config/
├── core/                           # 統一設定管理体系
│   ├── unified.yaml               # 🎯 統合設定ファイル（一元管理）
│   ├── thresholds.yaml            # ⚖️ 閾値・パラメータ設定（ML統合設定含む）
│   └── feature_order.json         # 📊 15特徴量定義・順序管理
└── secrets/
    └── .env                       # 🔐 API認証情報（要作成）
```

### **🎮 実行モード設定**
- **📝 paper**: ペーパートレード（実資金なし・検証用）
- **💰 live**: ライブトレード（実資金使用・本番取引）
- **📉 backtest**: 過去データでのバックテスト（戦略検証）

### **💰 初期残高設定**
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

### **🎯 戦略・ML調整**
- **📈 各戦略の重み調整**: `config/core/unified.yaml`
- **🎛️ 信頼度閾値調整**: `strategies.confidence_threshold`（0.25-0.6）
- **🧠 MLモデル重み**: `ensemble.weights`（LightGBM 50%・XGBoost 30%・RandomForest 20%）

---

## 📚 **ドキュメント**

### **🔧 開発者向け**
- **[CLAUDE.md](CLAUDE.md)**: Claude Code最適化ガイド・開発指針
- **[システム詳細](src/README.md)**: アーキテクチャ・実装詳細・レイヤード設計
- **[戦略システム](src/strategies/README.md)**: 5戦略の詳細説明・動的信頼度計算
- **[取引システム](src/trading/README.md)**: リスク管理・ExecutionService実行制御

### **👥 運用者向け**
- **[要件定義](docs/開発計画/要件定義.md)**: システム仕様・技術要件
- **[運用手順](docs/運用手順/)**: デプロイ・監視・トラブル対応・GCP運用
- **[開発履歴](docs/開発履歴/)**: Phase 1-37の詳細な開発経緯・技術変遷
- **[CI/CD設定](docs/CI-CD設定/)**: GitHub Actions・653テスト品質管理

---

## ⚠️ **リスク・免責事項**

- **💰 投資リスク**: 仮想通貨取引には元本割れのリスクがあります
- **🤖 システムリスク**: 自動取引システムの不具合による損失の可能性
- **📊 市場リスク**: 急激な市場変動への対応限界・ボラティリティ影響
- **📋 免責**: 本システムの使用による損失について作成者は責任を負いません

**🎯 推奨**: 少額資金（1万円）でのテスト運用から開始し、システム理解後に段階的拡大（10万→50万円）

---

## 📞 **サポート**

- **🐛 Issues**: [GitHub Issues](https://github.com/your-repo/crypto-bot/issues) での問題報告
- **💬 Discussion**: 機能要望・質問・フィードバック
- **🔒 Security**: セキュリティ問題は非公開で報告

---

**🎯 Phase 37.4完了・AI自動取引システム**: 15特徴量統合・5戦略SignalBuilder統合・ProductionEnsemble 3モデル・ML予測統合（戦略70% + ML30%）・TP/SL自動配置（stop注文・trigger_price完全対応）・SL配置問題完全解決（エラー50062・30101解消）・bitbank API完全対応（GET/POST認証・snake_case準拠）・コスト最適化（月700-900円削減・35-45%削減・月額1,100-1,300円）・バックテスト10倍高速化（45分実行）・特徴量バッチ化（無限倍高速化）・ML予測バッチ化（3,000倍高速化）・Graceful Degradation（Container exit解消）・15m ATR優先実装・柔軟クールダウン・features.yaml機能管理・3層設定体系・Discord 3階層監視による真のハイブリッドMLbot・企業級品質・収益最適化・デイトレード対応・少額運用対応・実用的バックテスト環境を実現した完全自動化AI取引システムが24時間稼働継続中。653テスト100%成功・58.62%カバレッジ・CI/CD統合・本番環境安定稼働により企業級品質を完全達成 🚀

**📅 最終更新**: 2025年10月9日 - Phase 37.4完了
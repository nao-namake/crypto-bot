# 🚀 **Crypto-Bot** - Phase 29.5完了・真のハイブリッドMLbot

**🎯 bitbank信用取引専用・BTC/JPY高頻度自動取引ボット・Phase 29.5 ML予測統合実装完了**

[![Python](https://img.shields.io/badge/python-3.13-blue)](https://python.org) [![Tests](https://img.shields.io/badge/tests-625%20passed-success)](tests/) [![Coverage](https://img.shields.io/badge/coverage-64.74%25-green)](coverage-reports/) [![Phase](https://img.shields.io/badge/Phase%2029.5-Completed-brightgreen)](docs/) [![ML Integration](https://img.shields.io/badge/ML%20Integration-Active-blue)](src/core/services/) [![Cloud Run](https://img.shields.io/badge/Cloud%20Run-Running-success)](https://cloud.google.com/run) [![Config](https://img.shields.io/badge/Unified%20Config-Complete-orange)](config/) [![GCP](https://img.shields.io/badge/GCP%20Optimized-Complete-blue)](docs/)

---

## ⚡ **クイックスタート**（即座実行）

### **💻 ローカル実行**
```bash
# 1. 依存関係インストール
pip install -r requirements.txt

# 2. 環境設定（API認証情報設定）
cp config/secrets/.env.example config/secrets/.env
# → .envファイルにbitbank API・Discord Webhook設定

# 3. Phase 29.5品質チェック
bash scripts/testing/checks.sh  # 625テスト・64.74%カバレッジ・約30秒

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

## 🎯 **システム概要**（Phase 29.5完了）

**AI自動取引システム**は、bitbank信用取引専用のBTC/JPY自動取引ボットです。5つの取引戦略と機械学習を**真に統合**し、15の技術指標を総合分析することで、24時間自動取引を実現する**真のハイブリッドMLbot**です。

### **✅ Phase 29.5完了ステータス（2025/09/30）**
- **🤖 ML予測統合実装**: 戦略シグナル（70%）+ ML予測（30%）の加重平均統合・真のハイブリッドMLbot実現
- **📊 一致/不一致判定**: ML高信頼度（80%以上）時のボーナス（1.2倍）/ペナルティ（0.7倍）適用
- **⚙️ 動的制御設定**: thresholds.yaml `ml.strategy_integration.*` 7項目新設・運用中パラメータ調整対応
- **🧪 テスト品質**: 625テスト100%成功・64.74%カバレッジ・ML統合テスト8個追加・CI/CD統合
- **📋 統一設定管理体系**: 15特徴量→5戦略→ML予測→リスク管理→取引実行の完全自動化・設定不整合完全解消

### **🎯 運用仕様**
- **🏦 対象市場**: bitbank信用取引・BTC/JPY専用
- **💰 資金規模**: 1万円スタート → 最大50万円（段階的拡大）
- **📊 取引頻度**: 月100-200回・3分間隔実行（高頻度取引）
- **🕐 稼働体制**: 24時間自動取引・Cloud Run稼働
- **🤖 ML統合**: 戦略とMLが融合した真のハイブリッドMLbot・市場適応性向上
- **🧪 品質保証**: 625テスト100%成功・64.74%カバレッジ・CI/CD統合

---

## 🤖 **主要機能・Phase履歴**（技術仕様）

### **🧠 AI取引システム（核心機能・Phase 29.5完了）**
- **📈 5戦略統合**: ATRBased・MochiPoy・MultiTimeframe・DonchianChannel・ADXTrendStrength
- **🎯 動的信頼度計算**: 市場適応型信頼度0.25-0.6・フォールバック完全回避
- **🤖 ML予測統合（Phase 29.5新規）**: 戦略70% + ML30%加重平均・一致ボーナス/不一致ペナルティ・真のハイブリッドMLbot実現
- **🧠 機械学習予測**: 3モデルアンサンブル（LightGBM 50%・XGBoost 30%・RandomForest 20%）
- **📊 15特徴量分析**: RSI・MACD・ボリンジャーバンド・ATR・EMA・Donchianチャネル・ADX等統合

### **🆕 Phase 29.5完了機能（2025/09/30）**
- **🤖 ML予測統合実装**: ML予測が実際の取引判断に統合・戦略とMLの真の融合実現
- **📊 加重平均統合**: 戦略シグナル70% + ML予測30%のベース信頼度計算
- **⚡ 高信頼度強化判定**: ML信頼度80%以上で一致ボーナス（1.2倍）・不一致ペナルティ（0.7倍）
- **🛡️ 安全措置**: 統合後信頼度0.4未満時の自動hold変更・リスク回避
- **⚙️ 動的制御**: thresholds.yaml `ml.strategy_integration.*` による運用中パラメータ調整

### **💰 Phase 28完了機能（2025/09/27）**
- **🎯 テイクプロフィット/ストップロス**: 標準的な利益確定・損切りシステム・完全トレーディングサイクル実現
- **⚖️ リスクリワード比管理**: デフォルト2.5:1・最小利益率1%・ATR倍率2.0による適応的決済

### **🧠 Phase 27完了機能（2025/09/26）**
- **🎛️ ML信頼度連動取引制限**: 低3%・中5%・高10%の動的制御・少額運用完全対応
- **⚡ 最小ロット優先**: 制限金額 < 最小ロット価値時、0.0001 BTC優先許可・1万円運用確実実行
- **🔗 bitbank API統合**: `/v1/user/margin/status`直接取得・保証金維持率・計算誤差排除
- **🔧 フォールバック値修正**: ドローダウン・維持率計算異常値対策・83.2%/128,077%異常解決

### **⚙️ リスク管理・取引実行システム**
- **🛡️ ExecutionService（2025/09/20実装）**: Silent Failure根本解決・実取引実行確保
- **📈 Kelly基準最適化（2025/09/19修正）**: 初期固定サイズ・5取引で実用性向上
- **📊 ポジション制限**: 最大3ポジション・1日20取引・30%資本使用制限
- **🚨 緊急ストップロス**: 3%価格変動・5%含み損で強制決済・急騰急落対応
- **📈 保証金監視（Phase 26）**: 維持率監視・4段階判定・新規エントリー影響予測
- **💱 指値注文オプション（Phase 26）**: ML信頼度連動・Maker手数料-0.02%獲得

### **☁️ 運用監視システム（24時間稼働）**
- **🕐 Cloud Run稼働**: Google Cloud Run・自動スケーリング・ヘルスチェック
- **📢 Discord監視**: 3階層通知（Critical/Warning/Info）・リアルタイムアラート
- **🗂️ GCPリソース最適化（2025/09/17完了）**: 古いイメージ削除・容量最適化・コスト削減
- **🧪 品質保証**: 625テスト自動実行・64.74%カバレッジ・継続的品質監視
- **🔄 週次学習**: 過去180日データで毎回ゼロから再学習・市場変化適応

---

## 📂 **システムアーキテクチャ**（Phase 29統合設計）

```
🏗️ レイヤードアーキテクチャ設計（統一設定管理体系）
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
src/                        # Phase 29統合最適化完了
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

📋 重要ファイル（Phase 29最適化）:
├── scripts/testing/checks.sh       # 625テスト品質チェック（開発必須）
├── config/core/unified.yaml        # 統一設定ファイル（Phase 29完了）
└── models/production/              # 本番MLモデル（週次自動更新）
```

---

## 🛠️ **技術スタック**（Phase 29最適化済み）

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

### **🔄 CI/CD・品質管理（Phase 29.5完了）**
- **GitHub Actions**: 自動テスト・品質チェック・週次ML学習・デプロイ
- **pytest**: テストフレームワーク・625テスト100%成功（ML統合テスト8個追加）
- **coverage**: コードカバレッジ測定・64.74%達成・品質ゲート
- **flake8/black/isort**: コード品質・スタイル統一・Phase 29.5対応

---

## 📈 **パフォーマンス・品質指標**（Phase 29.5実績）

### **🎯 取引成果（運用目標）**
- **📊 月間取引回数**: 100-200回・3分間隔実行・高頻度取引
- **⚖️ リスク管理**: 最大ドローダウン20%以下・Kelly基準最適化
- **🕐 稼働率**: 99%以上（24時間365日）・Cloud Run自動スケーリング

### **🧪 システム性能（Phase 29.5品質保証）**
- **✅ テスト成功率**: 100%（625テスト）・ML統合テスト8個追加・CI/CD品質ゲート通過
- **📊 コードカバレッジ**: 64.74%・品質基準向上・ML統合ロジック100%カバー
- **🤖 ML統合効果**: 戦略とMLの融合による市場適応性向上・真のハイブリッドMLbot実現
- **📈 Kelly基準最適化**: 20→5取引緩和・実用性向上・取引機会拡大
- **⚡ 実行時間**: 品質チェック約30秒・625テスト高速実行
- **🔗 API応答時間**: 平均3秒以下・bitbank API統合最適化
- **☁️ GCPリソース効率**: 古いイメージ削除・ストレージ最適化・コスト削減実現

---

## ⚙️ **設定・カスタマイズ**（Phase 29.5統一設定管理）

### **📁 主要設定ファイル（Phase 29.5最適化完了）**
```
config/
├── core/                           # Phase 29.5統一設定管理体系
│   ├── unified.yaml               # 🎯 統合設定ファイル（一元管理）
│   ├── thresholds.yaml            # ⚖️ 閾値・パラメータ設定（Phase 29.5: ML統合設定追加）
│   └── feature_order.json         # 📊 15特徴量定義・順序管理
└── secrets/
    └── .env                       # 🔐 API認証情報（要作成）
```

### **🎮 実行モード設定**
- **📝 paper**: ペーパートレード（実資金なし・検証用）
- **💰 live**: ライブトレード（実資金使用・本番取引）
- **📉 backtest**: 過去データでのバックテスト（戦略検証）

### **💰 初期残高設定（Phase 29一元管理）**
**1万円→10万円・50万円への変更が`config/core/unified.yaml` 1箇所のみで完結**

```yaml
# config/core/unified.yaml（Phase 29統一設定管理体系）
mode_balances:
  paper:
    initial_balance: 10000.0    # 1万円 → 10万円なら 100000.0
  live:
    initial_balance: 10000.0    # 段階的拡大: 1万→10万→50万
  backtest:
    initial_balance: 10000.0
```

### **🎯 戦略・ML調整（Phase 29設定統一）**
- **📈 各戦略の重み調整**: `config/core/unified.yaml`
- **🎛️ 信頼度閾値調整**: `strategies.confidence_threshold`（0.25-0.6）
- **🧠 MLモデル重み**: `ensemble.weights`（LightGBM 50%・XGBoost 30%・RandomForest 20%）

---

## 📚 **ドキュメント**（Phase 29体系化）

### **🔧 開発者向け**
- **[CLAUDE.md](CLAUDE.md)**: Claude Code最適化ガイド・Phase 29作業指針
- **[システム詳細](src/README.md)**: アーキテクチャ・実装詳細・レイヤード設計
- **[戦略システム](src/strategies/README.md)**: 5戦略の詳細説明・動的信頼度計算
- **[取引システム](src/trading/README.md)**: リスク管理・ExecutionService実行制御

### **👥 運用者向け**
- **[要件定義](docs/開発計画/要件定義.md)**: システム仕様・技術要件・Phase履歴
- **[運用手順](docs/運用手順/)**: デプロイ・監視・トラブル対応・GCP運用
- **[CI/CD設定](docs/CI-CD設定/)**: GitHub Actions・625テスト品質管理

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
- **💬 Discussion**: 機能要望・質問・Phase 29フィードバック
- **🔒 Security**: セキュリティ問題は非公開で報告

---

**🎯 Phase 29.5完了・AI自動取引システム** - 15特徴量統合・5戦略統合・ProductionEnsemble 3モデル・**ML予測統合（戦略70% + ML30%）**・ExecutionService取引実行・Kelly基準最適化・テイクプロフィット/ストップロス実装・完全なトレーディングサイクル実現・ML信頼度連動取引制限・最小ロット優先・bitbank API統合・統一設定管理体系確立・Discord 3階層監視による完全自動化システムが24時間稼働中。625テスト100%成功・64.74%カバレッジ・CI/CD統合・GCPリソース最適化・Silent Failure根本解決・async/await完全対応・設定不整合完全解消・**真のハイブリッドMLbot実現**により企業級品質・収益最適化・少額運用対応を完全達成。 🚀
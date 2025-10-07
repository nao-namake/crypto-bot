# 🚀 **Crypto-Bot** - Phase 37.2完了・bitbank API完全対応

**🎯 bitbank信用取引専用・BTC/JPY高頻度自動取引ボット・Phase 37.2 bitbank API GET認証対応・Phase 37 SL注文stop対応完了**

[![Python](https://img.shields.io/badge/python-3.13-blue)](https://python.org) [![Tests](https://img.shields.io/badge/tests-653%20passed-success)](tests/) [![Coverage](https://img.shields.io/badge/coverage-58.62%25-green)](coverage-reports/) [![Phase](https://img.shields.io/badge/Phase%2037.2-Completed-brightgreen)](docs/) [![ML Integration](https://img.shields.io/badge/ML%20Integration-Active-blue)](src/core/services/) [![Cloud Run](https://img.shields.io/badge/Cloud%20Run-Running-success)](https://cloud.google.com/run) [![Config](https://img.shields.io/badge/Unified%20Config-Complete-orange)](config/) [![GCP](https://img.shields.io/badge/GCP%20Optimized-Complete-blue)](docs/)

---

## ⚡ **クイックスタート**（即座実行）

### **💻 ローカル実行**
```bash
# 1. 依存関係インストール
pip install -r requirements.txt

# 2. 環境設定（API認証情報設定）
cp config/secrets/.env.example config/secrets/.env
# → .envファイルにbitbank API・Discord Webhook設定

# 3. Phase 37.2品質チェック
bash scripts/testing/checks.sh  # 653テスト・58.62%カバレッジ・約30秒

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

## 🎯 **システム概要**（Phase 37.2完了）

**AI自動取引システム**は、bitbank信用取引専用のBTC/JPY自動取引ボットです。5つの取引戦略と機械学習を**真に統合**し、15の技術指標を総合分析することで、24時間自動取引を実現する**真のハイブリッドMLbot**です。

### **✅ Phase 37.2完了ステータス（2025/10/08）**
- **🔐 bitbank API GET認証対応**: _call_private_api() GET/POST両対応実装
- **✅ エラー20003解消**: fetch_margin_status() GETメソッド化・署名ロジック分岐・bitbank API完全準拠
- **🛡️ Phase 36完全動作化**: 証拠金残高チェック正常化・Container exit(1)削減実現
- **🧪 テスト品質**: 653テスト100%成功・58.62%カバレッジ・CI/CD統合

### **✅ Phase 37完了ステータス（2025/10/08）**
- **🛡️ SL注文stop対応**: create_stop_loss_order() limit→stop変更・逆指値成行注文実装
- **✅ エラー50062解消**: trigger_price追加・create_order() stop/stop_limit対応
- **💰 損切り機能完全化**: 全ポジションに確実な損切り保護実現・TP/SL両建てシステム完成
- **🧪 テスト品質**: 652テスト100%成功・57.22%カバレッジ

### **✅ Phase 36完了ステータス（2025/10/07）**
- **🛡️ Graceful Degradation**: 残高不足時Container exit(1)回避・取引スキップ実装（Phase 37.2で完全動作）
- **📊 残高チェック機能**: ExecutionService拡張・Discord通知統合・証拠金残高自動確認
- **💰 コスト削減**: Container exit(1) 63回/日→0回・月369円削減（年4,428円）

### **✅ Phase 35完了内容（2025/10/07）**
- **⚡ 10倍高速化達成**: 6-8時間→47分（特徴量バッチ化+ML予測バッチ化）
- **📊 特徴量バッチ化**: 288分→0秒（無限倍高速化）・265,130件/秒処理
- **🧠 ML予測バッチ化**: 15分→0.3秒（3,000倍高速化）・10,063件/秒処理
- **💰 価格データ正常化**: entry_price追加・¥0問題解決

### **✅ Phase 34完了内容（2025/10/05）**
- **📊 15分足データ収集80倍改善**: 216件→17,271件（99.95%成功率）
- **🔧 Bitbank Public API直接使用**: 日別イテレーション実装・ccxt制限回避
- **✅ バックテストシステム完成**: 過去180日データ分析実行可能・実用的環境確立

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

### **🧪 システム性能（Phase 35.7品質保証）**
- **✅ テスト成功率**: 100%（653テスト）・Phase 35-36テスト追加・CI/CD品質ゲート通過
- **📊 コードカバレッジ**: 59.56%・品質基準維持・全機能テストカバー
- **⚡ バックテスト性能**: 47分実行（10倍高速化達成）・特徴量/ML予測バッチ化完了
- **📉 ログ最適化**: 70%削減・可読性大幅向上・重要情報視認性確保
- **🛡️ システム安定性**: Container exit(1)完全解消・Graceful Degradation実装
- **🤖 ML統合効果**: 戦略とMLの融合による市場適応性向上・真のハイブリッドMLbot実現
- **⚡ 実行時間**: 品質チェック約30秒・653テスト高速実行
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

**🎯 Phase 35.7完了・AI自動取引システム** - 15特徴量統合・5戦略統合・ProductionEnsemble 3モデル・**ML予測統合（戦略70% + ML30%）**・**バックテストログ最適化70%削減**・**バックテスト10倍高速化（6-8時間→47分）**・**特徴量バッチ化（無限倍高速化）**・**ML予測バッチ化（3,000倍高速化）**・**Phase 36 Graceful Degradation（Container exit解消）**・**適応型ATR倍率（低2.5x・通常2.0x・高1.5x）**・**TP/SL自動配置**・**指値注文切替**・**クールダウン30分**・**最小SL距離保証1%**・ExecutionService取引実行・Kelly基準最適化・完全なトレーディングサイクル実現・ML信頼度連動取引制限・最小ロット優先・bitbank API統合・統一設定管理体系確立・Discord 3階層監視による完全自動化システムが24時間稼働中。653テスト100%成功・59.56%カバレッジ・CI/CD統合・GCPリソース最適化・Silent Failure根本解決・async/await完全対応・設定不整合完全解消・**真のハイブリッドMLbot実現・実用的バックテスト環境完成・本番環境安定稼働**により企業級品質・収益最適化・少額運用対応を完全達成。 🚀
# CLAUDE.md - Phase 32完了・Claude Code最適化ガイド

**🎯 即座に理解すべき重要事項：本システムはPhase 32完了済み・5戦略SignalBuilder統一・15m ATR優先実装・柔軟クールダウン・features.yaml設定管理・646テスト100%成功・59.75%カバレッジ・CI/CD品質保証完了の企業級AI自動取引システム**

---

## 🚨 **現在のシステム状態**（重要・必読）

### **✅ Phase 32完了ステータス**
- **📅 2025/10/02完了**: 5戦略SignalBuilder統一・15m ATR優先実装・柔軟クールダウン・features.yaml設定管理・品質保証完了
- **🧪 テスト品質**: 646テスト100%成功（1 skipped）・59.75%カバレッジ・CI/CD品質ゲート通過
- **🎯 Phase 32機能**: DonchianChannel・ADXTrend SignalBuilder統合・全5戦略で15m ATR使用統一・SL/TP機能完全化
- **⚙️ Phase 31.1機能**: features.yaml作成（7カテゴリー・~50機能トグル）・柔軟クールダウン実装（トレンド強度ベース）
- **⚖️ リスク管理**: 適応型ATR倍率（低2.5x・通常2.0x・高1.5x）・最小SL距離保証1%・15m ATR優先で2%距離改善
- **💰 取引機能**: TP/SL自動配置・指値注文・柔軟クールダウン（強度>=0.7でスキップ）・ポジション追跡完了
- **🤖 ML統合システム**: 戦略70% + ML30%加重平均・一致ボーナス/不一致ペナルティ・動的制御対応
- **⚙️ 統一設定管理体系**: features.yaml + unified.yaml + thresholds.yaml 3層管理・15特徴量→5戦略→ML予測→リスク管理→取引実行の完全自動化

### **🎯 運用システム概要**
- **🤖 AI自動取引システム**: bitbank信用取引・BTC/JPY専用・24時間稼働（Cloud Run）
- **💰 資金規模**: 1万円スタート → 最大50万円（段階的拡大）
- **📊 取引頻度**: 月100-200回・3分間隔実行（高頻度取引）
- **🏗️ インフラ**: GCP Cloud Run・1Gi・1CPU・月額2,000円以内

### **🔧 技術仕様**
- **🐍 Python**: 3.13・MLライブラリ互換性最適化・GitHub Actions安定版
- **📈 戦略**: 5戦略統合（ATR・MochiPoy・MultiTimeframe・DonchianChannel・ADX）・動的信頼度計算
- **🧠 ML**: 3モデルアンサンブル（LightGBM 50%・XGBoost 30%・RandomForest 20%）
- **⏰ 時間軸**: 4時間足（トレンド）+ 15分足（エントリー）

---

## 🚀 **クイックスタート・必須コマンド**（開発時必読）

### **🧪 品質チェック（開発前後必須）**
```bash
# Phase 32品質チェック - 開発前後に必ず実行
bash scripts/testing/checks.sh

# 期待結果: ✅ 646テスト100%成功（1 skipped）・59.75%カバレッジ通過・約72秒で完了
```

### **🔄 システム実行（Claude Code最適化済み）**
```bash
# ✅ 推奨: フォアグラウンド実行（Claude Code誤認識回避）
bash scripts/management/run_safe.sh local paper  # ペーパートレード
bash scripts/management/run_safe.sh local live   # ライブトレード

# 実行状況確認（実プロセス確認）
bash scripts/management/bot_manager.sh check

# 停止
bash scripts/management/run_safe.sh stop
```

### **⚠️ Claude Code使用時の重要注意事項**
```bash
# ❌ 避けるべき: バックグラウンド実行（Claude Code誤認識の原因）
# bash scripts/management/run_safe.sh local paper --background

# ✅ 正しい方法: フォアグラウンド実行使用（デフォルト）
bash scripts/management/run_safe.sh local paper

# 実プロセス状況確認（Claude Code表示を無視して実際の状況を確認）
bash scripts/management/bot_manager.sh check
# → 「✅ システム完全停止状態」が表示されれば実際には停止中
```

### **☁️ 本番環境確認（GCP）**
```bash
# Cloud Run稼働状況
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1

# システムログ確認
gcloud logging read "resource.type=cloud_run_revision" --limit=10

# 残高確認（Secret Manager修正後）
gcloud logging read "textPayload:\"残高\" OR textPayload:\"balance\"" --limit=5
```

---

## 📂 **システム構造**（アーキテクチャ理解）

```
src/                        # メイン実装・レイヤードアーキテクチャ
├── core/                   # 🔧 基盤システム（Phase 29統合最適化完了）
│   ├── orchestration/          # システム統合制御・TradingOrchestrator
│   ├── config/                 # 設定管理・特徴量管理・unified.yaml
│   ├── execution/              # 取引実行制御・ExecutionService
│   ├── reporting/              # レポーティング・Discord通知
│   └── services/               # システムサービス・GracefulShutdown
├── data/                   # 📊 データ層（Bitbank API・キャッシュ）
├── features/               # 📈 15特徴量生成システム
├── strategies/             # 🎯 5戦略統合システム
├── ml/                     # 🧠 ProductionEnsemble・3モデル統合
├── trading/                # ⚖️ リスク管理・ExecutionService（2025/09/20実装）
├── backtest/               # 📉 バックテストシステム
└── monitoring/             # 📢 Discord 3階層監視

📁 重要ファイル:
scripts/testing/checks.sh       # 品質チェック（開発必須・646テスト）
config/core/features.yaml       # 機能トグル設定（Phase 31.1新規追加・7カテゴリー~50機能）
config/core/unified.yaml        # 統合設定ファイル（Phase 30最適化完了・指値/クールダウン設定）
config/core/thresholds.yaml     # ML統合・適応型ATR設定（Phase 30拡張）
models/production/              # 本番MLモデル（週次自動更新）
```

---

## 🎯 **開発原則・品質基準**（Phase 29.5確立済み）

### **🧪 品質保証（必須遵守）**
- **🔬 テスト実行**: 開発前後に`checks.sh`必須実行・625テスト100%維持・64.74%カバレッジ
- **📈 カバレッジ**: 64.74%以上維持・新機能は必ずテスト追加
- **🔄 CI/CD**: GitHub Actions自動品質ゲート・失敗時は修正必須

### **🏗️ システム理解（必須知識）**
- **📋 アーキテクチャ**: レイヤードアーキテクチャ・各層責任明確
- **🔄 データフロー**: データ取得→特徴量生成→戦略実行→ML予測→リスク評価→取引判断
- **⚠️ エラーハンドリング**: カスタム例外・適切なログ・復旧機能

### **⚙️ 設定管理統一（Phase 29確立）**
- **🚫 ハードコード禁止**: すべて設定ファイル・環境変数で管理
- **📂 階層化設定**: core/production/development環境別設定
- **🔐 Secret Manager**: 具体的バージョン番号使用（key:latest禁止）

### **✅ 実装品質基準**
- **📝 コード品質**: flake8・black・isort通過必須
- **📊 ログ品質**: JST時刻・構造化ログ・Discord通知対応
- **🧪 テスト品質**: 単体・統合・エラーケーステスト完備

---

## 🔧 **重要技術ポイント・Phase履歴**（必須理解事項）

### **🎯 Phase 32完了事項（2025/10/02）**
- **🎯 5戦略SignalBuilder統一**: DonchianChannel・ADXTrend統合完了・全5戦略でSignalBuilder使用
- **📏 15m ATR優先実装**: 全戦略で15m足ATR使用統一・SL距離2%改善実現
- **🔧 SL/TP機能完全化**: Phase 31で3戦略統合済み・Phase 32で残り2戦略統合・全戦略で一貫したリスク管理
- **🧪 品質保証**: 646テスト100%成功（1 skipped）・59.75%カバレッジ達成・CI/CD統合

### **🎯 Phase 31.1完了事項（2025/10/02）**
- **📋 features.yaml作成**: 7カテゴリー・~50機能トグル・機能視認性向上・設定一元化実現
- **⏰ 柔軟クールダウン実装**: トレンド強度ベース（ADX 50%・DI 30%・EMA 20%）・強度>=0.7でスキップ
- **🚀 機会損失削減**: 強トレンド時のクールダウンスキップにより取引機会確保・通常時は30分維持
- **⚙️ 設定管理3層化**: features.yaml（機能トグル）+ unified.yaml（基本設定）+ thresholds.yaml（動的値）

### **🎯 Phase 29.5完了事項（2025/09/30）**
- **🤖 ML予測統合実装**: 戦略70% + ML30%加重平均統合・一致ボーナス/不一致ペナルティ実装
- **📊 統合アルゴリズム**: ML信頼度80%以上で強化判定・0.4未満でhold強制変更
- **⚙️ 設定管理拡張**: thresholds.yaml `ml.strategy_integration.*` 7項目新設・動的制御対応
- **🧪 品質保証**: 625テスト100%成功・64.74%カバレッジ達成・ML統合テスト8個追加
- **🎯 真のハイブリッドMLbot実現**: ML予測が実際の取引判断に統合・戦略とMLの融合完成

### **🎯 Phase 29完了事項（2025/09/28）**
- **📋 戦略設定値一元化**: Multi-timeframe・ATRBased戦略のハードコード値を完全除去・thresholds.yaml統一管理
- **⚙️ 動的パラメータ管理**: get_threshold()関数による設定値の動的取得・循環インポート回避
- **🧪 テスト最適化**: 625テスト100%成功・CI/CD統合
- **📋 デプロイ前最終最適化**: 全設定ファイル統一・品質保証完了
- **⚙️ 統一設定管理体系**: 15特徴量→5戦略→ML予測→リスク管理→取引実行の完全自動化・設定不整合完全解消

### **🎯 Phase 28完了事項（2025/09/27）**
- **💰 テイクプロフィット/ストップロス実装**: 標準的な利益確定・損切りシステム
- **🔄 完全なトレーディングサイクル実現**: エントリー→決済までの完全自動化
- **⚖️ リスクリワード比管理**: デフォルト2.5:1・最小利益率1%・ATR倍率2.0

### **🎯 Phase 27完了事項（2025/09/26）**
- **🧠 ML信頼度連動取引制限**: 低3%・中5%・高10%の動的制御・少額運用完全対応
- **⚡ 最小ロット優先**: 制限金額 < 最小ロット価値時、0.0001 BTC優先許可
- **🔗 bitbank API統合**: `/v1/user/margin/status`直接取得・計算誤差排除
- **🔧 フォールバック値修正**: ドローダウン・維持率計算の異常値対策

### **🔑 核心システム基盤**
- **📊 feature_manager**: 15特徴量統一管理・config/core/feature_order.json参照
- **🧠 ProductionEnsemble**: 3モデルアンサンブル（LightGBM 50%・XGBoost 30%・RandomForest 20%）
- **🎯 動的信頼度計算**: フォールバック回避・市場適応型0.25-0.6信頼度
- **⚙️ ExecutionService**: Silent Failure根本解決・実取引実行確保（2025/09/20実装）
- **📈 Kelly基準最適化**: 5取引で実用性向上・初期固定サイズ実装（2025/09/19修正）

### **🤖 ML学習システム**
- **🔄 全体再学習方式**: 過去180日データで毎回ゼロから学習
- **⏰ 週次自動学習**: 毎週日曜18:00(JST) GitHub Actionsワークフロー
- **🛡️ 安全更新**: models/archive/自動バックアップ・625テスト品質ゲート

### **🔐 Secret Manager管理（重要）**
- **✅ 修正済み**: 2025/09/15にkey:latest問題解決
- **⚙️ 現行設定**: 具体的バージョン使用
  - `bitbank-api-key:3`
  - `bitbank-api-secret:3`
  - `discord-webhook-url:5`
- **⚠️ 注意**: Secret更新時はci.yml:319も同時更新必須

### **☁️ 本番運用システム（GCP）**
- **🕐 24時間稼働**: Cloud Run自動スケーリング・ヘルスチェック
- **📢 Discord監視**: 3階層通知（Critical/Warning/Info）・運用アラート
- **📊 データ取得**: Bitbank API・4h/15m足・キャッシュ最適化・残高取得正常化済み
- **🗂️ GCPリソース最適化（2025/09/17完了）**: 古いイメージ削除・容量最適化・コスト削減

---

## 🛠️ **トラブルシューティング**（問題解決ガイド）

### **🔧 開発時問題**
```bash
# Phase 32品質チェック実行（詳細エラー確認）
bash scripts/testing/checks.sh

# import エラー時（モジュール確認）
python3 -c "import sys; sys.path.insert(0, '.'); from src.core.logger import CryptoBotLogger"

# 設定エラー時（整合性確認）
python3 scripts/testing/dev_check.py validate
```

### **⚠️ Claude Code特有問題**
```bash
# 🚨 バックグラウンドプロセス誤認識問題
# 原因: Claude Code内部トラッキングシステムの制限事項
# 解決策: フォアグラウンド実行使用（デフォルト推奨）

# ✅ 正しい実行方法
bash scripts/management/run_safe.sh local paper

# 📊 実プロセス状況確認（Claude Code表示を無視）
bash scripts/management/bot_manager.sh check
# → 「✅ システム完全停止状態」なら実際には停止中
```

### **☁️ 本番環境問題（GCP）**
```bash
# システム稼働状況確認
gcloud run services describe crypto-bot-service-prod --region=asia-northeast1

# エラーログ確認
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --limit=20

# 残高取得確認（Secret Manager修正後）
gcloud logging read "textPayload:\"残高\" OR textPayload:\"balance\"" --limit=10
```

---

## ✅ **Phase 32作業時チェックリスト**（次回作業用）

### **🔍 必須確認事項**
1. **🧪 品質チェック**: `bash scripts/testing/checks.sh`で646テスト・59.75%カバレッジ確認
2. **☁️ 本番稼働**: Cloud Run・Discord通知・取引ログ確認
3. **🎯 Phase 32機能**: 5戦略SignalBuilder統一・15m ATR優先実装・SL/TP機能完全化確認
4. **⚙️ Phase 31.1機能**: features.yaml機能トグル・柔軟クールダウン・トレンド強度判定確認
5. **⚖️ Phase 30機能**: 適応型ATR倍率・最小SL距離保証1%・15m足ATR基盤確認
6. **💰 Phase 29.6機能**: TP/SL自動配置・指値注文・ポジション追跡確認
7. **🤖 Phase 29.5機能**: ML予測統合・戦略70%+ML30%加重平均・一致/不一致判定確認
8. **🎯 Phase 29機能**: 統一設定管理体系・設定不整合解消確認

### **🚀 開発開始前チェック**
1. **📊 最新状況把握**: システム状況・エラー状況・Phase 32ステータス確認
2. **🧪 品質基準**: 646テスト・59.75%カバレッジ・コード品質確認
3. **⚙️ 設定整合性**: config整合性・環境変数・features.yaml・unified.yaml・thresholds.yaml確認

---

**🎯 Phase 32完了・AI自動取引システム**: 15特徴量統合・5戦略統合・ProductionEnsemble 3モデル・**ML予測統合（戦略70% + ML30%）**・**5戦略SignalBuilder統一・15m ATR優先実装**・**SL/TP機能完全化**・**柔軟クールダウン（トレンド強度ベース）**・**features.yaml機能トグル管理**・適応型ATR倍率（低2.5x・通常2.0x・高1.5x）・最小SL距離保証1%・指値注文切替・ExecutionService取引実行・Kelly基準最適化・完全なトレーディングサイクル実現・ML信頼度連動取引制限・最小ロット優先・bitbank API統合・3層設定管理体系（features/unified/thresholds）・Discord 3階層監視による完全自動化システムが24時間稼働中。646テスト100%成功（1 skipped）・59.75%カバレッジ・CI/CD統合・GCPリソース最適化・Silent Failure根本解決・async/await完全対応・設定不整合完全解消・**真のハイブリッドMLbot実現・本番環境安定稼働**により企業級品質・収益最適化・少額運用対応を完全達成。 🚀
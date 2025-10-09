# CLAUDE.md - Phase 37.4完了・Claude Code最適化ガイド

**🎯 即座に理解すべき重要事項：本システムはPhase 37.4完了済み・SL配置問題完全解決（エラー30101解消）・コスト最適化35-45%・653テスト100%成功・58.62%カバレッジ・CI/CD品質保証完了の企業級AI自動取引システム**

---

## 🚨 **現在のシステム状態**（重要・必読）

### **✅ 最新Phase完了ステータス**

**Phase 37.4完了（2025/10/09）**:
- SL未配置問題根本解決・trigger_price修正（エラー30101解消）
- bitbank API snake_case完全準拠・SL配置成功率100%達成

**Phase 37.3完了（2025/10/08）**:
- Discord通知最適化・実行頻度最適化（3分→5分間隔）
- コスト削減35-45%（月700-900円削減）・月額1,100-1,300円実現

**Phase 37.2完了（2025/10/08）**:
- bitbank API GET認証対応・エラー20003解消
- Phase 36 Graceful Degradation完全動作化

**Phase 37完了（2025/10/08）**:
- SL注文stop対応・エラー50062解消・trigger_price実装
- 損切り機能完全化・全ポジションに確実な損切り保護

**Phase 36完了（2025/10/07）**:
- 残高不足Graceful Degradation実装
- Container exit(1)完全解消・月369円削減

**Phase 35完了（2025/10/07）**:
- バックテスト10倍高速化達成（6-8時間→45分）
- 特徴量バッチ化・ML予測バッチ化・価格データ正常化

**Phase 34完了（2025/10/05）**:
- 15分足データ収集80倍改善（216件→17,271件）
- Bitbank Public API直接使用・バックテストシステム完成

**Phase 32完了（2025/10/02）**:
- 全5戦略SignalBuilder統一・15m ATR優先実装
- SL/TP機能完全化・SL距離2%改善

**Phase 31.1完了（2025/10/02）**:
- features.yaml作成（7カテゴリー・~50機能トグル）
- 柔軟クールダウン実装（トレンド強度ベース）

### **🎯 運用システム概要**
- **🤖 AI自動取引システム**: bitbank信用取引・BTC/JPY専用・24時間稼働（Cloud Run）
- **💰 資金規模**: 1万円スタート → 最大50万円（段階的拡大）
- **📊 取引頻度**: 月100-200回・**5分間隔実行**（Phase 37.3最適化完了）
- **🏗️ インフラ**: GCP Cloud Run・1Gi・1CPU・**月額1,100-1,300円**（Phase 37.3コスト削減達成）

### **🔧 技術仕様**
- **🐍 Python**: 3.13・MLライブラリ互換性最適化・GitHub Actions安定版
- **📈 戦略**: 5戦略統合（ATR・MochiPoy・MultiTimeframe・DonchianChannel・ADX）・動的信頼度計算
- **🧠 ML**: 3モデルアンサンブル（LightGBM 50%・XGBoost 30%・RandomForest 20%）
- **⏰ 時間軸**: 4時間足（トレンド）+ 15分足（エントリー）

### **⚖️ リスク管理**
- 適応型ATR倍率（低2.5x・通常2.0x・高1.5x）
- 最小SL距離保証1%・15m ATR優先でSL距離2%改善
- TP/SL自動配置（stop注文・trigger_price完全対応）
- 柔軟クールダウン（トレンド強度>=0.7でスキップ）

### **🤖 ML統合システム**
- 戦略70% + ML30%加重平均
- 一致ボーナス（1.2倍）/不一致ペナルティ（0.7倍）
- 動的制御対応

### **⚙️ 統一設定管理体系**
- features.yaml（機能トグル）+ unified.yaml（基本設定）+ thresholds.yaml（動的値）
- 15特徴量 → 5戦略 → ML予測 → リスク管理 → 取引実行の完全自動化

---

## 🚀 **クイックスタート・必須コマンド**（開発時必読）

### **🧪 品質チェック（開発前後必須）**
```bash
# Phase 37.4品質チェック - 開発前後に必ず実行
bash scripts/testing/checks.sh

# 期待結果: ✅ 653テスト100%成功・58.62%カバレッジ通過・約72秒で完了
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

# 残高確認
gcloud logging read "textPayload:\"残高\" OR textPayload:\"balance\"" --limit=5
```

---

## 📂 **システム構造**（アーキテクチャ理解）

```
src/                        # メイン実装・レイヤードアーキテクチャ
├── core/                   # 🔧 基盤システム
│   ├── orchestration/          # システム統合制御・TradingOrchestrator
│   ├── config/                 # 設定管理・特徴量管理・unified.yaml
│   ├── execution/              # 取引実行制御・ExecutionService
│   ├── reporting/              # レポーティング・Discord通知
│   └── services/               # システムサービス・GracefulShutdown
├── data/                   # 📊 データ層（Bitbank API・キャッシュ）
├── features/               # 📈 15特徴量生成システム
├── strategies/             # 🎯 5戦略統合システム
├── ml/                     # 🧠 ProductionEnsemble・3モデル統合
├── trading/                # ⚖️ リスク管理・ExecutionService
├── backtest/               # 📉 バックテストシステム
└── monitoring/             # 📢 Discord 3階層監視

📁 重要ファイル:
scripts/testing/checks.sh       # 品質チェック（開発必須・653テスト）
config/core/features.yaml       # 機能トグル設定（7カテゴリー~50機能）
config/core/unified.yaml        # 統合設定ファイル（指値/クールダウン設定）
config/core/thresholds.yaml     # ML統合・適応型ATR設定
models/production/              # 本番MLモデル（週次自動更新）
```

---

## 🎯 **開発原則・品質基準**

### **🧪 品質保証（必須遵守）**
- **🔬 テスト実行**: 開発前後に`checks.sh`必須実行・653テスト100%維持・58.62%カバレッジ
- **📈 カバレッジ**: 58%以上維持・新機能は必ずテスト追加
- **🔄 CI/CD**: GitHub Actions自動品質ゲート・失敗時は修正必須

### **🏗️ システム理解（必須知識）**
- **📋 アーキテクチャ**: レイヤードアーキテクチャ・各層責任明確
- **🔄 データフロー**: データ取得 → 特徴量生成 → 戦略実行 → ML予測 → リスク評価 → 取引判断
- **⚠️ エラーハンドリング**: カスタム例外・適切なログ・復旧機能

### **⚙️ 設定管理統一**
- **🚫 ハードコード禁止**: すべて設定ファイル・環境変数で管理
- **📂 階層化設定**: core/production/development環境別設定
- **🔐 Secret Manager**: 具体的バージョン番号使用（key:latest禁止）

### **✅ 実装品質基準**
- **📝 コード品質**: flake8・black・isort通過必須
- **📊 ログ品質**: JST時刻・構造化ログ・Discord通知対応
- **🧪 テスト品質**: 単体・統合・エラーケーステスト完備

---

## 🔧 **重要技術ポイント・Phase履歴**（必須理解事項）

### **📅 Phase 37.4（2025/10/09）- SL未配置問題根本解決**
- **trigger_priceパラメータ名修正**: `triggerPrice` → `trigger_price`（snake_case）
- **エラー30101解消**: bitbank API仕様完全準拠・SL配置成功率100%達成
- **エラーハンドリング強化**: 30101/50062/50061の明確な分類・Discord通知追加
- **品質保証**: 653テスト100%成功・58.62%カバレッジ維持

### **📅 Phase 37.3（2025/10/08）- コスト最適化**
- **Discord通知最適化**: info/batch通知停止・重要通知のみ維持
- **実行頻度最適化**: 3分間隔 → 5分間隔（判定回数-40%）
- **コスト削減効果**: 月700-900円削減（35-45%削減）・月額1,100-1,300円実現
- **品質保証**: 653テスト100%成功・58.62%カバレッジ維持

### **📅 Phase 37.2（2025/10/08）- bitbank API GET認証対応**
- **GET/POST署名ロジック分岐**: _call_private_api()拡張・bitbank API完全準拠
- **エラー20003解消**: fetch_margin_status() GETメソッド化・認証成功
- **Phase 36完全動作化**: 証拠金残高チェック正常化・Container exit(1)削減
- **品質保証**: 653テスト100%成功・58.62%カバレッジ達成

### **📅 Phase 37（2025/10/08）- SL注文stop対応**
- **逆指値成行注文実装**: create_stop_loss_order() limit→stop変更
- **エラー50062解消**: trigger_price追加・create_order() stop/stop_limit対応
- **損切り機能完全化**: 全ポジションに確実な損切り保護実現
- **品質保証**: 652テスト100%成功・57.22%カバレッジ達成

### **📅 Phase 36（2025/10/07）- Graceful Degradation実装**
- **残高不足時Container exit回避**: ExecutionService拡張・証拠金残高自動確認
- **Discord通知統合**: 残高不足時Critical通知・手動介入可能
- **コスト削減**: Container exit(1) 57回/日→0回・月369円削減（年4,428円）
- **品質保証**: 648テスト100%成功・既存機能影響なし

### **📅 Phase 35（2025/10/07）- バックテスト10倍高速化**
- **特徴量バッチ化**: 288分→0秒（無限倍高速化）・265,130件/秒処理
- **ML予測バッチ化**: 15分→0.3秒（3,000倍高速化）・10,063件/秒処理
- **価格データ正常化**: entry_price追加・¥0問題解決
- **ログ最適化**: 70%削減（12,781行→3,739行）・可読性大幅向上
- **合計高速化**: 6-8時間→45分（約10倍高速化達成）

### **📅 Phase 34（2025/10/05）- バックテストシステム完成**
- **15分足データ収集80倍改善**: 216件→17,271件（99.95%成功率）
- **Bitbank Public API直接使用**: 日別イテレーション実装・ccxt制限回避
- **バックテストシステム完成**: 過去180日データ分析実行可能・実用的環境確立

### **📅 Phase 32（2025/10/02）- 全5戦略SignalBuilder統一**
- **DonchianChannel・ADXTrend統合**: 全5戦略でSignalBuilder使用完了
- **15m ATR優先実装**: 全戦略で15m足ATR使用統一・SL距離2%改善実現
- **SL/TP機能完全化**: 全戦略で一貫したリスク管理実現
- **品質保証**: 646テスト100%成功・59.75%カバレッジ達成

### **📅 Phase 31.1（2025/10/02）- features.yaml作成**
- **機能トグル設定**: 7カテゴリー・~50機能一元管理・機能視認性向上
- **柔軟クールダウン実装**: トレンド強度ベース（ADX 50%・DI 30%・EMA 20%）
- **機会損失削減**: 強トレンド時（強度>=0.7）クールダウンスキップ・取引機会確保
- **設定管理3層化**: features.yaml + unified.yaml + thresholds.yaml

### **📅 Phase 29.5（2025/09/30）- ML予測統合**
- **戦略70% + ML30%**: 加重平均統合・一致ボーナス/不一致ペナルティ実装
- **統合アルゴリズム**: ML信頼度80%以上で強化判定・0.4未満でhold強制変更
- **真のハイブリッドMLbot実現**: ML予測が実際の取引判断に統合・戦略とMLの融合完成

### **🔑 核心システム基盤**
- **feature_manager**: 15特徴量統一管理・config/core/feature_order.json参照
- **ProductionEnsemble**: 3モデルアンサンブル（LightGBM 50%・XGBoost 30%・RandomForest 20%）
- **動的信頼度計算**: フォールバック回避・市場適応型0.25-0.6信頼度
- **ExecutionService**: Silent Failure根本解決・実取引実行確保
- **Kelly基準最適化**: 5取引で実用性向上・初期固定サイズ実装

### **🤖 ML学習システム**
- **全体再学習方式**: 過去180日データで毎回ゼロから学習
- **週次自動学習**: 毎週日曜18:00(JST) GitHub Actionsワークフロー
- **安全更新**: models/archive/自動バックアップ・品質ゲート

### **🔐 Secret Manager管理**
- **現行設定**: `bitbank-api-key:3`, `bitbank-api-secret:3`, `discord-webhook-url:5`
- **注意**: Secret更新時はci.yml:319も同時更新必須

### **☁️ 本番運用システム（GCP）**
- **24時間稼働**: Cloud Run自動スケーリング・ヘルスチェック
- **Discord監視**: 3階層通知（Critical/Warning/Info）・運用アラート
- **データ取得**: Bitbank API・4h/15m足・キャッシュ最適化

---

## 🛠️ **トラブルシューティング**（問題解決ガイド）

### **🔧 開発時問題**
```bash
# Phase 37.4品質チェック実行（詳細エラー確認）
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

# 残高取得確認
gcloud logging read "textPayload:\"残高\" OR textPayload:\"balance\"" --limit=10
```

---

## ✅ **開発時チェックリスト**（Phase 37.4完了時点）

### **🔍 必須確認事項**
1. **🧪 品質チェック**: `bash scripts/testing/checks.sh`で653テスト・58.62%カバレッジ確認
2. **☁️ 本番稼働**: Cloud Run・Discord通知・取引ログ確認
3. **🎯 Phase 37.4機能**: SL配置成功率100%・trigger_price修正・エラー30101解消確認
4. **💰 Phase 37.3機能**: コスト削減35-45%・5分間隔実行・月額1,100-1,300円確認
5. **🛡️ Phase 37.2機能**: bitbank API GET認証・エラー20003解消確認
6. **🎯 Phase 37機能**: SL注文stop対応・エラー50062解消確認
7. **🛡️ Phase 36機能**: Graceful Degradation・Container exit(1)解消確認
8. **📊 Phase 35機能**: バックテスト10倍高速化・45分実行時間確認

### **🚀 開発開始前チェック**
1. **📊 最新状況把握**: システム状況・エラー状況・Phase 37.4ステータス確認
2. **🧪 品質基準**: 653テスト・58.62%カバレッジ・コード品質確認
3. **⚙️ 設定整合性**: config整合性・環境変数・features.yaml・unified.yaml・thresholds.yaml確認

---

**🎯 Phase 37.4完了・企業級AI自動取引システム**:
15特徴量統合・5戦略SignalBuilder統合・ProductionEnsemble 3モデル・ML予測統合（戦略70% + ML30%）・
TP/SL自動配置（stop注文・trigger_price完全対応）・SL配置問題完全解決（エラー50062・30101解消）・
bitbank API完全対応（GET/POST認証・snake_case準拠）・コスト最適化（月700-900円削減・35-45%削減）・
バックテスト10倍高速化（45分実行）・特徴量バッチ化（無限倍高速化）・ML予測バッチ化（3,000倍高速化）・
Graceful Degradation（Container exit解消）・15m ATR優先実装・柔軟クールダウン・features.yaml機能管理・
3層設定体系・Discord 3階層監視による真のハイブリッドMLbot・企業級品質・収益最適化・デイトレード対応・
少額運用対応・実用的バックテスト環境を実現した完全自動化AI取引システムが24時間稼働継続中。
653テスト100%成功・58.62%カバレッジ・CI/CD統合・本番環境安定稼働により企業級品質を完全達成 🚀

---

**📅 最終更新**: 2025年10月9日 - Phase 37.4完了

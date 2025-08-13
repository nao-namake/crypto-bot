# scripts/monitoring/ - 監視・検証・修復・Discord通知ツール

## 📋 概要

Phase 2-3・Phase 3・Discord通知システムで実装された高度な監視・検証・エラー修復・通知機能を集約したディレクトリです。  
リアルタイム監視から事後分析、Discord通知テストまで、システムの健全性と通知システムを保つツールを提供します。

## 🎊 2025年8月13日 Discord通知システム完成

メール通知を完全廃止し、Discord通知システムに移行完了。デプロイ時の大量メール通知問題を根本解決。

## 🎯 ツール一覧

### **discord_notification_test.py** (Discord通知システム) 🆕 ⭐ 最重要
Discord通知システムのテスト・動作確認

```bash
# Discord直接テスト（最簡単）
python scripts/monitoring/discord_notification_test.py --type direct

# 各アラート種別テスト
python scripts/monitoring/discord_notification_test.py --type loss         # 損失アラート
python scripts/monitoring/discord_notification_test.py --type error        # エラー率アラート  
python scripts/monitoring/discord_notification_test.py --type trade_failure # 取引失敗アラート
python scripts/monitoring/discord_notification_test.py --type system_down  # システム停止アラート
python scripts/monitoring/discord_notification_test.py --type memory       # メモリ異常アラート
python scripts/monitoring/discord_notification_test.py --type data_fetch   # データ停止アラート
```

**テスト対象:**
- Discord Webhook URL接続確認
- GCP Pub/Sub → Cloud Functions → Discord完全フロー
- 6種類のアラート種別（色分け・メッセージ形式）
- JST時刻表示・エラーハンドリング

**出力:** Discordチャンネルにテストメッセージ送信・コンソールに送信結果表示

### **signal_monitor.py** (Phase 2-2) ⭐ 重要
シグナル生成の健全性監視

```bash
# 直近24時間のシグナルを監視
python scripts/monitoring/signal_monitor.py --hours 24

# アラート閾値を変更
python scripts/monitoring/signal_monitor.py --hours 48 --threshold-alert 60
```

**監視項目:**
- シグナル生成頻度（1時間以上なし → アラート）
- 連続パターン異常（30回連続HOLD等）
- Confidence値異常（常に0.0または1.0）
- 予測精度の低下

**出力:** `logs/monitoring/signal_analysis_*.html`

### **future_leak_detector.py** (Phase 2-3) ⭐ 重要
未来データリーク検出

```bash
# プロジェクト全体をスキャン
python scripts/monitoring/future_leak_detector.py --project-root .. --html

# 特定ファイルをチェック
python scripts/monitoring/future_leak_detector.py --file ../crypto_bot/ml/feature_master_implementation.py
```

**検出パターン:**
- `shift(-1)` などの未来参照
- `center=True` のrolling window
- 不適切なインデックス操作
- データ分割の時系列違反

**出力:** `logs/leak_detection/leak_report_*.html`

### **error_analyzer.py** (Phase 3)
エラーパターン分析・学習

```bash
# GCPとローカルログを分析
python scripts/monitoring/error_analyzer.py --source both --hours 24

# GCPログのみ分析
python scripts/monitoring/error_analyzer.py --source gcp --hours 48
```

**機能:**
- 10種類の既知エラーパターン検出
- 修復提案の自動生成
- 成功率学習機能
- HTMLレポート生成

**出力:** `logs/error_analysis/error_analysis_*.html`

### **analyze_and_fix.py** (Phase 3) ⭐ 統合ツール
エラー分析と修復の統合実行

```bash
# インタラクティブ修復モード
python scripts/monitoring/analyze_and_fix.py --interactive

# CRITICALエラーの自動修復
python scripts/monitoring/analyze_and_fix.py --auto-fix

# 修復スクリプト生成
python scripts/monitoring/analyze_and_fix.py --generate-script
```

**機能:**
- エラー分析実行
- 対話的修復サポート
- 自動修復（安全なもののみ）
- 修復スクリプト生成

### **paper_trade_with_monitoring.sh**
ペーパートレード＋監視の統合実行

```bash
# 24時間のペーパートレード＋1時間毎の監視
bash scripts/monitoring/paper_trade_with_monitoring.sh --duration 24
```

**実行内容:**
1. バックグラウンドでペーパートレード
2. 1時間毎にシグナル監視
3. 異常検出時のアラート
4. 終了時の統合レポート

## 💡 推奨ワークフロー

### **日常監視（推奨：毎日）**

```bash
# 1. Discord通知テスト（🆕 最重要）
python scripts/monitoring/discord_notification_test.py --type direct

# 2. シグナル監視
python scripts/monitoring/signal_monitor.py --hours 24

# 3. エラーチェック
python scripts/monitoring/error_analyzer.py --source both --hours 24

# 4. 問題があれば修復
python scripts/monitoring/analyze_and_fix.py --interactive
```

### **開発時の検証（コミット前）**

```bash
# 1. 未来データリーク検出
python scripts/monitoring/future_leak_detector.py --project-root ..

# 2. ペーパートレードでテスト
bash scripts/monitoring/paper_trade_with_monitoring.sh --duration 1

# 3. 統合チェック
python scripts/bot_manager.py full-check
```

### **デプロイ後の確認（🆕 Discord通知システム）**

```bash
# 1. Discord通知システム動作確認（必須）
python scripts/monitoring/discord_notification_test.py --type direct

# 2. 各アラート種別テスト
python scripts/monitoring/discord_notification_test.py --type loss
python scripts/monitoring/discord_notification_test.py --type trade_failure

# 3. Cloud Functions状態確認
gcloud functions describe webhook-notifier --region=asia-northeast1

# 4. 完璧稼働状況確認システム
python scripts/operational_status_checker.py --verbose
```

### **トラブル発生時**

```bash
# 1. エラー分析
python scripts/monitoring/analyze_and_fix.py --source both

# 2. 自動修復試行
python scripts/monitoring/analyze_and_fix.py --auto-fix

# 3. 手動修復が必要な場合
python scripts/monitoring/analyze_and_fix.py --interactive

# 4. 修復後の確認
python scripts/monitoring/signal_monitor.py --hours 1
```

## 📊 監視指標

### **シグナル健全性**
- **生成頻度:** 1時間に1回以上
- **信頼度:** 0.1 < confidence < 0.9
- **バランス:** BUY/SELL比率 0.3〜3.0
- **異常パターン:** 連続30回未満

### **データ整合性**
- **未来リーク:** 0件
- **時系列順序:** 厳密に過去→現在
- **データ分割:** train < test の時刻

### **エラー率**
- **CRITICAL:** 0件/日
- **ERROR:** < 10件/日
- **WARNING:** < 100件/日

## ⚠️ 注意事項

- **ペーパートレード** は本番と同じ設定で実行
- **リーク検出** は新機能追加時に必ず実行
- **エラー修復** は自動修復でも確認必須
- **監視レポート** は定期的に確認

## 🔍 トラブルシューティング

### **シグナルが生成されない**
```bash
# 監視実行
python scripts/monitoring/signal_monitor.py --hours 24

# 詳細ログ確認
grep "SIGNAL" logs/trading_signals.csv | tail -20
```

### **未来データリーク検出**
```bash
# 全体スキャン
python scripts/monitoring/future_leak_detector.py --project-root .. --html

# レポート確認
open logs/leak_detection/leak_report_*.html
```

### **頻繁なエラー発生**
```bash
# パターン分析
python scripts/monitoring/error_analyzer.py --source both

# 自動修復
python scripts/monitoring/analyze_and_fix.py --auto-fix
```

## 📈 統合CLIからの実行

```bash
# 監視実行
python scripts/bot_manager.py monitor --hours 24

# リーク検出
python scripts/bot_manager.py leak-detect

# エラー修復
python scripts/bot_manager.py fix-errors --auto-fix
```

---

*最終更新: 2025年8月13日 - Discord通知システム実装・メール通知廃止・アラート最適化*
# src/core/reporting - レポート生成・通知システム 📋 Phase 52.4

AI自動取引システムのレポート生成とDiscord週間レポート送信機能を提供。
Phase 48で通知システムを99%削減し、週間レポート送信に特化したシンプル設計。

---

## 📂 ファイル構成

### 主要ファイル

- **`discord_notifier.py`** (585行・45%): Discord週間レポート送信・DiscordClient・DiscordManager
- **`paper_trading_reporter.py`** (342行・26%): ペーパートレードレポート生成・Markdown/JSON出力
- **`base_reporter.py`** (204行・16%): 基底レポーター・統一インターフェース
- **`__init__.py`** (28行): モジュールエクスポート

**総行数**: 1,159行（Python）

---

## 🏗️ アーキテクチャ

### レポーティング層設計

reporting層は**週間レポート送信特化**として設計され、Phase 48で大幅簡略化されました。

```
┌─────────────────────────────────────────────────────────┐
│              reporting層（週間レポート特化）             │
├─────────────────────────────────────────────────────────┤
│  DiscordManager                                         │
│  ├─ 週間レポート送信（毎週月曜9:00 JST）                 │
│  ├─ 損益グラフファイル送信（matplotlib画像）             │
│  └─ レート制限対応（1000ms間隔）                        │
│                                                         │
│  DiscordClient                                          │
│  ├─ シンプルWebhook通知                                 │
│  ├─ 画像ファイル送信（Pillow統合）                       │
│  └─ Webhook URL自動取得（.env優先）                     │
│                                                         │
│  PaperTradingReporter                                   │
│  ├─ セッションレポート生成（Markdown）                   │
│  ├─ 取引履歴レポート生成（JSON）                         │
│  └─ BaseReporter統一インターフェース継承                │
└─────────────────────────────────────────────────────────┘
```

**Phase 48大幅簡略化**:
- **Before**: 複雑な通知システム（300-1,500通知/月・6クラス統合）
- **After**: 週間レポート送信のみ（4通知/月・2クラスシンプル設計）
- **削除機能**: エラー通知・取引シグナル通知・取引実行結果通知・システム状態通知・バッチ処理・日次サマリー
- **効果**: 通知99%削減・コスト35%削減（月額700-900円削減）

---

## 🎯 コンポーネント詳細

### 1. DiscordClient（discord_notifier.py）

**責任**: シンプルなDiscord Webhook通知クライアント

**主要機能**:
- **Webhook URL自動取得**: .env → 環境変数 → discord_webhook.txt（優先順位付き）
- **画像ファイル送信**: Pillow統合・損益グラフ送信対応
- **Webhook検証**: URL形式・ID・トークン妥当性チェック
- **エラーハンドリング**: 通信失敗時のログ記録・再試行なし（週間レポート特化）

**設計原則**:
- シンプル設計（複雑な機能削除）
- 週間レポート送信最適化
- 設定駆動型（webhook URL外部化）

**使用例**:
```python
from src.core.reporting.discord_notifier import DiscordClient

# 初期化（WebhookURL自動取得）
client = DiscordClient()

# シンプルメッセージ送信
client.send_message("システム起動完了", level="info")

# 埋め込み形式送信
client.send_embed(
    title="週間レポート",
    description="取引実績サマリー",
    color=0x00FF00
)

# 画像ファイル送信（週間損益グラフ）
client.send_file(
    file_path="reports/weekly_pnl.png",
    message="週間損益グラフ"
)
```

---

### 2. DiscordManager（discord_notifier.py）

**責任**: 週間レポート専用通知マネージャー

**主要機能**:
- **週間レポート送信**: GitHub Actions毎週月曜9:00 JST実行
- **損益グラフ送信**: matplotlib生成グラフのファイル送信
- **レート制限対応**: 1000ms間隔（Discord API制限遵守）
- **設定駆動型**: `get_monitoring_config()`による動的設定

**Phase 48最適化**:
- 複雑な通知ロジック削除（バッチ処理・日次サマリー等）
- 週間レポート送信のみに特化
- シンプルな依存関係（DiscordClient利用）

**使用例**:
```python
from src.core.reporting.discord_notifier import DiscordManager

# 初期化
manager = DiscordManager()

# 週間レポート送信（scripts/reports/weekly_report.pyから呼び出し）
manager.send_weekly_report(
    title="週間取引レポート（2025/11/11-11/17）",
    summary_text="総取引: 15回\n利益: ¥8,500\n勝率: 60%",
    graph_path="reports/weekly_pnl.png"
)
```

---

### 3. BaseReporter（base_reporter.py）

**責任**: レポート生成の統一インターフェース

**主要機能**:
- **統一保存インターフェース**: JSON・Markdownレポート保存
- **Discord埋め込み形式**: format_discord_embed()によるEmbed生成
- **ディレクトリ管理**: レポート保存先自動作成
- **設定駆動型**: `get_threshold("reporting.base_dir")`によるパス管理

**設計原則**:
- 単一責任原則（レポート保存のみ）
- 設定外部化（ハードコード排除）
- 継承可能設計（PaperTradingReporter等）

**使用例**:
```python
from src.core.reporting.base_reporter import BaseReporter

reporter = BaseReporter(logger)

# JSONレポート保存
data = {"trades": 10, "profit": 5000}
report_path = await reporter.save_report(
    data=data,
    report_type="session_summary"
)
# → logs/reports/session_summary_20251117_120000.json

# Discord埋め込み形式生成
embed = reporter.format_discord_embed(
    data=data,
    title="セッションレポート",
    color=0x00FF00
)
```

---

### 4. PaperTradingReporter（paper_trading_reporter.py）

**責任**: ペーパートレード専用レポート生成

**主要機能**:
- **セッションレポート**: Markdown形式・取引サマリー・損益集計
- **取引履歴レポート**: JSON形式・全取引詳細記録
- **パフォーマンスレポート**: 勝率・平均利益・最大ドローダウン等
- **BaseReporter継承**: 統一インターフェース活用

**Phase 49最適化**:
- BaseReporter統一インターフェース継承
- 設定駆動型レポートディレクトリ
- Markdown/JSON両対応

**使用例**:
```python
from src.core.reporting import PaperTradingReporter

reporter = PaperTradingReporter(logger)

# ペーパートレードセッションレポート生成
session_stats = {
    "trades": 10,
    "profit": 5000,
    "duration": "2h",
    "win_rate": 0.6
}
report_path = await reporter.generate_session_report(session_stats)
# → logs/paper_trading_reports/session_20251117_120000.md
```

---

## 📊 データフロー

### 週間レポート送信フロー（Phase 48実装）

```
1. GitHub Actions定期実行（毎週月曜9:00 JST）
   ↓
2. scripts/reports/weekly_report.py実行
   ↓
3. 週間取引データ集計（SQLite trade_history.db）
   ↓
4. matplotlib損益グラフ生成（weekly_pnl.png）
   ↓
5. DiscordManager.send_weekly_report()呼び出し
   ↓
6. DiscordClient.send_file()でグラフ送信
   ↓
7. DiscordClient.send_embed()でサマリー送信
   ↓
8. レート制限対応（1000ms間隔）
```

### ペーパートレードレポート生成フロー

```
1. PaperTradingRunner実行完了
   ↓
2. PaperTradingReporter.generate_session_report()呼び出し
   ↓
3. Markdownレポート生成（取引サマリー・損益集計）
   ↓
4. BaseReporter.save_report()でファイル保存
   ↓
5. logs/paper_trading_reports/に保存完了
```

---

## ⚙️ 設定ファイル連携

### config/core/thresholds.yaml

**Discord設定**:
```yaml
monitoring:
  discord:
    timeout: 10           # Webhook送信タイムアウト（秒）
    min_interval: 2       # 最小送信間隔（秒）
    rate_limit_ms: 1000   # レート制限（ミリ秒）
```

**レポート設定**:
```yaml
reporting:
  base_dir: logs/reports                      # 基本レポート保存先
  paper_trading_dir: logs/paper_trading_reports  # ペーパートレードレポート保存先
```

### 環境変数（config/secrets/.env）

```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

**優先順位**:
1. .envファイル（推奨）
2. 環境変数
3. discord_webhook.txt（後方互換性）

---

## 🚀 使用方法

### 週間レポート送信（GitHub Actions）

```yaml
# .github/workflows/weekly_report.yml
- name: 週間レポート送信
  run: python scripts/reports/weekly_report.py
  env:
    DISCORD_WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_URL }}
```

### ペーパートレードレポート生成

```python
from src.core.reporting import PaperTradingReporter
from src.core.logger import CryptoBotLogger

logger = CryptoBotLogger.get_logger("paper_trading")
reporter = PaperTradingReporter(logger)

# セッション完了後にレポート生成
session_stats = {
    "start_time": "2025-11-17 10:00:00",
    "end_time": "2025-11-17 12:00:00",
    "trades": 5,
    "profit": 2500,
    "win_rate": 0.8
}

report_path = await reporter.generate_session_report(session_stats)
logger.info(f"レポート保存完了: {report_path}")
```

### Discord通知カスタマイズ

```python
from src.core.reporting.discord_notifier import DiscordClient

# カスタムWebhook URL指定
client = DiscordClient(webhook_url="https://discord.com/api/webhooks/...")

# カスタム色の埋め込み送信
client.send_embed(
    title="システムアラート",
    description="証拠金維持率が80%を下回りました",
    color=0xFF0000  # 赤色
)
```

---

## 🔧 設計原則

### シンプル設計（Phase 48回帰）

**原則**: 週間レポート送信のみに特化・複雑性排除

**❌ 削除された複雑機能（Phase 48）**:
- NotificationBatcher（バッチ処理）
- DailySummaryCollector（日次サマリー）
- EnhancedDiscordManager（拡張マネージャー）
- DiscordFormatter（フォーマッター）
- エラー通知・取引シグナル通知・取引実行結果通知・システム状態通知

**✅ Phase 48シンプル設計**:
```python
# 2クラスのみ（DiscordClient, DiscordManager）
# 週間レポート送信機能のみ
# 300-1,500通知/月 → 4通知/月（99%削減）
```

### 設定外部化

**原則**: ハードコード排除・設定駆動型

```python
# ✅ 推奨: get_threshold()パターン
from src.core.config import get_threshold
base_dir = get_threshold("reporting.base_dir", "logs/reports")

# ✅ 推奨: get_monitoring_config()パターン
from src.core.config import get_monitoring_config
timeout = get_monitoring_config("discord.timeout", 10)
```

### レート制限対応

**原則**: Discord API制限遵守・1000ms間隔

```python
import time

# レート制限対応（DiscordManager実装）
rate_limit_ms = get_monitoring_config("discord.rate_limit_ms", 1000)
time.sleep(rate_limit_ms / 1000)
```

---

## 🧪 テスト戦略

### 関連テストファイル

```bash
# Discord通知テスト
tests/unit/monitoring/test_discord_client.py

# 週間レポートテスト
tests/unit/scripts/test_weekly_report.py
```

**注意**: `tests/unit/core/reporting/` ディレクトリは存在しません。
Discord通知テストは `tests/unit/monitoring/` に配置されています。

### 統合テスト

```bash
# Discord通知統合テスト
pytest tests/unit/monitoring/test_discord_client.py -v

# 週間レポート統合テスト
pytest tests/unit/scripts/test_weekly_report.py -v
```

---

## 🔍 トラブルシューティング

### Discord通知送信失敗

**症状**: DiscordClient.send_message()がFalseを返却

**原因確認**:
```python
# Webhook URL確認
echo $DISCORD_WEBHOOK_URL

# .envファイル確認
cat config/secrets/.env | grep DISCORD_WEBHOOK_URL
```

**解決策**:
1. Webhook URL形式確認（`https://discord.com/api/webhooks/`で開始）
2. Webhook ID・トークン妥当性確認（ID: 18-19桁、Token: 3文字以上）
3. Discord側Webhook有効性確認（削除されていないか）

### 週間レポート送信エラー

**症状**: GitHub Actions週間レポートワークフロー失敗

**原因確認**:
```bash
# GitHub Actions実行ログ確認
gh run list --workflow=weekly_report.yml

# 最新実行ログ確認
gh run view --log
```

**解決策**:
1. `DISCORD_WEBHOOK_URL` Secretsが設定されているか確認
2. `scripts/reports/weekly_report.py` 実行可能性確認
3. `tax/trade_history.db` 存在確認（週間データ集計元）

### レポート保存先エラー

**症状**: FileNotFoundError: `logs/reports/` or `logs/paper_trading_reports/`

**原因**: ディレクトリ未作成

**解決策**:
```bash
# ディレクトリ作成（BaseReporterが自動作成するはずだが、手動作成も可能）
mkdir -p logs/reports
mkdir -p logs/paper_trading_reports
```

### レート制限エラー

**症状**: Discord API 429 Too Many Requests

**原因**: 送信頻度が高すぎる

**解決策**:
```yaml
# config/core/thresholds.yaml
monitoring:
  discord:
    rate_limit_ms: 2000  # 1000 → 2000に変更（間隔を広げる）
```

---

## 📊 Phase履歴（抜粋）

- **Phase 52.4**: Phase参照統一・ハードコード値削減・README.md完全書き直し
- **Phase 49**: BaseReporter統一インターフェース実装・PaperTradingReporter最適化
- **Phase 48**: Discord週間レポート実装（通知99%削減・コスト35%削減・複雑機能削除）
- **Phase 28-29**: 初期Discord通知システム実装（Phase 48で大幅簡略化）

---

## 🔗 関連ファイル

### 呼び出し元

- `scripts/reports/weekly_report.py`: 週間レポート生成・Discord送信スクリプト
- `src/core/execution/paper_trading_runner.py`: ペーパートレードレポート生成呼び出し

### 設定管理

- `config/core/thresholds.yaml`: Discord・レポート設定
- `config/secrets/.env`: Webhook URL環境変数

### GitHub Actions

- `.github/workflows/weekly_report.yml`: 週間レポート定期実行（毎週月曜9:00 JST）

---

**🎯 Phase 52.4完了**: Phase参照統一・README.md正確性修正（削除済みクラス削除）により、reporting層の理解促進・保守性向上が実現されています。

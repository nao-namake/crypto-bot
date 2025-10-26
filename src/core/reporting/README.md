# src/core/reporting/ - レポート生成・通知システム（Phase 49完了）

## 🎯 役割・責任

AI自動取引システムのレポート生成とDiscord通知システム。週間レポート送信機能（Phase 48）とペーパートレードレポート生成機能を提供。

**Phase 49完了**: BaseReporter統一インターフェース・PaperTradingReporter・Discord週間レポート専用通知システム
**Phase 48完了**: Discord通知99%削減（300-1,500回/月 → 4回/月）・コスト35%削減（月額700-900円削減）・週間レポート特化

## 📂 ファイル構成

```
src/core/reporting/
├── __init__.py               # レポート・通知システムエクスポート
├── base_reporter.py          # 基底レポーター（統一インターフェース）
├── paper_trading_reporter.py # ペーパートレードレポート生成
└── discord_notifier.py       # Discord通知統合システム（Phase 28完了・Phase 29最適化）
```

## 🔧 主要コンポーネント

### **discord_notifier.py**

6つのクラスを統合したDiscord通知システム：

```python
class DiscordClient:
    def send_message(self, message, level) -> bool        # シンプルメッセージ送信
    def send_embed(self, title, description) -> bool      # 埋め込み形式送信

class DiscordFormatter:
    @staticmethod
    def format_trading_signal(signal_data) -> Dict        # 取引シグナル形式
    @staticmethod
    def format_system_status(status_data) -> Dict         # システム状態形式

class DiscordManager:
    def send_trading_signal(self, signal_data) -> bool    # 取引シグナル送信
    def send_system_status(self, status_data) -> bool     # システム状態送信
    def send_error_notification(self, error_data) -> bool # エラー通知送信

class NotificationBatcher:
    def add_notification(self, data, level) -> bool       # 通知をキューに追加
    def process_batch(self) -> bool                       # バッチ通知の処理・送信

class DailySummaryCollector:
    def add_daily_event(self, event_data)                 # 日次イベント追加
    def generate_daily_summary(self) -> Dict              # 日次サマリー生成

class EnhancedDiscordManager(DiscordManager):
    def send_simple_message(self, message, level) -> bool # 拡張版シンプル送信
    def process_pending_notifications(self)               # 保留中通知の処理
```

### **base_reporter.py**

レポート生成の統一インターフェース：

```python
class BaseReporter:
    async def save_report(self, data, report_type) -> Path # 統一レポート保存
    async def generate_error_report(self, error_data) -> Path # エラーレポート生成
```

### **paper_trading_reporter.py**

ペーパートレード専用レポート生成：

```python
class PaperTradingReporter(BaseReporter):
    async def generate_session_report(self, session_stats) -> Path # セッションレポート
    async def generate_trade_history_report(self, trades) -> Path  # 取引履歴レポート
    async def generate_performance_report(self, performance) -> Path # パフォーマンスレポート
```

## 🚀 使用方法

### **基本的な通知送信**

```python
from src.core.reporting.discord_notifier import DiscordManager

# 初期化（WebhookURLは自動取得）
manager = DiscordManager()

# シンプルメッセージ送信
manager.send_simple_message("システム起動完了", "info")

# 取引シグナル送信
signal_data = {
    "action": "BUY",
    "confidence": 0.85,
    "price": 4800000,
    "strategy": "ATRBased"
}
manager.send_trading_signal(signal_data)
```

### **拡張機能（バッチ処理・日次サマリー）**

```python
from src.core.reporting.discord_notifier import EnhancedDiscordManager

# 拡張マネージャー使用
enhanced_manager = EnhancedDiscordManager()

# バッチ処理で複数通知を効率送信
enhanced_manager.send_simple_message("通知1", "info")
enhanced_manager.send_simple_message("通知2", "warning")
enhanced_manager.process_pending_notifications()  # 一括送信
```

### **レポート生成**

```python
from src.core.reporting import PaperTradingReporter

reporter = PaperTradingReporter(logger)

# ペーパートレードセッションレポート生成
session_stats = {"trades": 10, "profit": 5000, "duration": "2h"}
report_path = await reporter.generate_session_report(session_stats)
```

## ⚙️ 設定管理

Discord通知設定は `config/core/thresholds.yaml` で一元管理：

```yaml
monitoring:
  discord:
    min_interval: 2
    rate_limit_per_minute: 30
  health_check:
    interval_seconds: 60
```

## 特徴・制約

- **統合設計**: 6クラス1ファイルによる効率的管理
- **レート制限**: Discord API制限対応・自動調整
- **バッチ処理**: 複数通知の効率的送信
- **日次サマリー**: 取引結果の自動集計・送信
- **エラー処理**: 通信失敗時の自動再試行・フォールバック
- **設定外部化**: ハードコード排除・動的設定変更

---

**レポート生成・通知システム（Phase 28完了・Phase 29最適化）**: Discord通知統合・レポート生成・バッチ処理による包括的監視・通知システム。
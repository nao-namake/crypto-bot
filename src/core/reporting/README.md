# src/core/reporting/ - レポート生成・通知システム

## 🎯 役割・責任

AI自動取引システムのレポート生成とDiscord通知システム。取引シグナル、システム状態、エラー情報をDiscordチャンネルにリアルタイム通知。Phase 22統合により、レポート生成機能とDiscord通知機能を統合管理。

## 📂 ファイル構成

```
src/core/reporting/
├── __init__.py               # レポート・通知システムエクスポート
├── base_reporter.py          # 基底レポーター（統一インターフェース）
├── paper_trading_reporter.py # ペーパートレードレポート生成
└── discord_notifier.py       # Discord通知統合システム（Phase 22統合）
    ├── DiscordClient         # Discord Webhook送信・基盤層
    ├── DiscordFormatter      # メッセージフォーマット・表現層
    └── DiscordManager        # 通知制御・Rate Limit・制御層
```

## 🔧 主要コンポーネント

### **discord_notifier.py（Phase 22統合）**

**目的**: Discord通知の統合システム（3クラス統合）

**主要クラス**:
```python
class DiscordClient:
    def __init__(self, webhook_url: Optional[str] = None)  # 優先順位付きURL取得
    def send_message(self, message, level) -> bool        # シンプルメッセージ送信
    def send_embed(self, title, description) -> bool      # 埋め込み形式送信
    def _validate_webhook_url(self, url) -> bool          # URL形式検証
    
class DiscordFormatter:
    @staticmethod
    def format_trading_signal(signal_data) -> Dict        # 取引シグナル形式
    @staticmethod
    def format_system_status(status_data) -> Dict         # システム状態形式
    @staticmethod
    def format_error_notification(error_data) -> Dict     # エラー通知形式
    
class DiscordManager:
    def __init__(self, webhook_url: Optional[str] = None) # 通知管理初期化
    def send_simple_message(self, message, level) -> bool # シンプル送信
    def send_trading_signal(self, signal_data) -> bool    # 取引シグナル送信
    def send_system_status(self, status_data) -> bool     # システム状態送信
    def send_error_notification(self, error_data) -> bool # エラー通知送信
```

### **base_reporter.py**

**目的**: レポート生成の統一インターフェース

**主要機能**:
```python
class BaseReporter:
    def __init__(self, logger: CryptoBotLogger)          # 基底レポーター初期化
    async def save_report(self, data, report_type) -> Path # 統一レポート保存
    async def generate_error_report(self, error_data) -> Path # エラーレポート生成
```

### **paper_trading_reporter.py**

**目的**: ペーパートレード専用レポート生成

**主要機能**:
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
manager.send_simple_message("警告: API制限に近づいています", "warning")
manager.send_simple_message("緊急: システム停止", "critical")
```

### **取引シグナル通知**
```python
# 取引シグナルデータ準備
signal_data = {
    "action": "buy",           # buy/sell/hold
    "confidence": 0.75,        # 信頼度 (0-1)
    "price": 1000000,          # 価格
    "symbol": "BTC/JPY",       # 通貨ペア
    "features_used": 12,       # 使用特徴量数
    "model": "ProductionEnsemble"
}

# 取引シグナル送信
manager.send_trading_signal(signal_data)
```

### **レポート生成**
```python
from src.core.reporting import PaperTradingReporter

# ペーパートレードレポート生成
reporter = PaperTradingReporter(logger)
report_path = await reporter.generate_session_report(session_stats)
```

## ⚙️ 設定・Webhook URL管理

### **優先順位付きWebhook URL取得**

Discord Webhook URLは以下の優先順位で自動取得されます：

1. **引数**（最優先）: `DiscordManager(webhook_url="https://...")`
2. **`.env`ファイル**（推奨）: `config/secrets/.env`
3. **環境変数**: `DISCORD_WEBHOOK_URL`
4. **txtファイル**（後方互換性）: `config/secrets/discord_webhook.txt`

### **.env ファイル設定（推奨方法）**

`config/secrets/.env`:
```bash
# Discord通知設定
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN

# その他の環境変数
BITBANK_API_KEY=your_api_key
BITBANK_API_SECRET=your_api_secret
```

### **Phase 22統合設定**

`config/core/unified.yaml`:
```yaml
# レポート設定（Phase 22 ハードコード値外出し）
reporting:
  base_dir: "logs/reports"
  paper_trading_dir: "logs/paper_trading_reports"
  error_dir: "logs/reports/errors"
  max_report_size_mb: 10
  retention_days: 30

# Discord通知設定（Phase 22 統合）
discord:
  max_retries: 3
  timeout_seconds: 10
  rate_limit_delay: 1.0
  embed_color:
    success: 0x00FF00
    warning: 0xFFFF00
    error: 0xFF0000
```

## 🛡️ エラーハンドリング・制限対応

### **401エラー（認証失敗）対応**

```python
# 401エラー発生時の自動処理
# - URLハッシュをログ出力（セキュリティ考慮）
# - 通知システムを自動無効化
# - 連続エラーを防止
```

### **Rate Limit対応**

- **最小送信間隔**: 2秒（設定で変更可能）
- **起動時抑制**: 30秒間（システム安定化のため）
- **429エラー**: 自動的に送信抑制

### **JSON形式エラー（50109）対応**

- **事前検証**: JSON送信前に形式チェック
- **文字エンコーディング**: UTF-8対応
- **特殊文字処理**: Discord API準拠の処理

## 🎨 メッセージフォーマット

### **レベル別色設定**

```python
LEVEL_COLORS = {
    "info": 0x3498DB,      # 青色（情報）
    "warning": 0xF39C12,   # 黄色（警告）
    "critical": 0xE74C3C,  # 赤色（緊急）
}
```

## ⚠️ 重要事項

### **セキュリティ**

- **機密保護**: `config/secrets/`は`.gitignore`で保護済み
- **権限設定**: `chmod 600 config/secrets/discord_webhook.txt`推奨
- **URLハッシュ**: 401エラー時はハッシュのみログ出力

### **Phase 22統合の利点**

- **統一管理**: レポート生成とDiscord通知を一元化
- **設定統合**: `unified.yaml`での設定管理
- **保守性向上**: 機能関連性に基づく適切な配置
- **後方互換性**: 既存のインポートパスも対応

### **依存関係**

- **外部ライブラリ**: requests（HTTP送信）、python-dotenv（.env読み込み）
- **内部依存**: src.core.config（設定管理）、src.core.logger（ログシステム）
- **設定ファイル**: config/core/unified.yaml、config/secrets/.env

---

**レポート生成・通知システム**: Phase 22統合により、レポート生成とDiscord通知機能を統合管理。3層アーキテクチャによる堅牢なDiscord通知システムと統一レポート生成インターフェースを提供。
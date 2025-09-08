# src/monitoring/ - システム監視・通知層

## 🎯 役割・責任

AI自動取引システムのDiscord通知システム。取引シグナル、システム状態、エラー情報をDiscordチャンネルにリアルタイム通知。3層アーキテクチャによる高い保守性と401エラー・Rate Limitに対応した堅牢な通知機能を提供。

## 📂 ファイル構成

```
src/monitoring/
├── __init__.py           # 監視システムエクスポート（15行）
└── discord_notifier.py   # Discord通知統合システム（763行）
    ├── DiscordClient     # Discord Webhook送信・基盤層
    ├── DiscordFormatter  # メッセージフォーマット・表現層
    └── DiscordManager    # 通知制御・Rate Limit・制御層
```

## 🔧 主要コンポーネント

### **discord_notifier.py（763行）**

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

## 🚀 使用方法

### **基本的な通知送信**
```python
from src.monitoring import DiscordManager

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

### **システム状態通知**
```python
# システム状態データ
status_data = {
    "status": "healthy",       # healthy/warning/error
    "uptime": 7200,           # 稼働時間（秒）
    "trades_today": 5,        # 本日の取引数
    "current_balance": 1050000, # 現在残高
    "last_trade_time": "2025-09-08 14:30:00"
}

# システム状態送信
manager.send_system_status(status_data)
```

### **エラー通知**
```python
# エラーデータ
error_data = {
    "error_type": "MLModelError",
    "message": "ProductionEnsemble読み込み失敗",
    "traceback": "...",        # スタックトレース
    "timestamp": "2025-09-08 14:35:00"
}

# エラー通知送信
manager.send_error_notification(error_data)
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

**使用方法**:
```python
# main.py等で.envファイルを読み込み
from dotenv import load_dotenv
load_dotenv('config/secrets/.env')

# 自動的に環境変数が設定される
manager = DiscordManager()  # DISCORD_WEBHOOK_URLが自動取得される
```

### **txtファイル設定（後方互換性）**

`config/secrets/discord_webhook.txt`:
```
https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN
```

### **Webhook URL取得確認**

```python
# URL取得状況の確認
manager = DiscordManager()
if manager.enabled:
    print("✅ Discord通知が有効です")
else:
    print("❌ Discord通知が無効です - Webhook URLを確認してください")
```

## 🛡️ エラーハンドリング・制限対応

### **401エラー（認証失敗）対応**

```python
# 401エラー発生時の自動処理
# - URLハッシュをログ出力（セキュリティ考慮）
# - 通知システムを自動無効化
# - 連続エラーを防止
```

**ログ例**:
```
❌ Discord Webhook無効 (401): URLが無効または削除されています
   使用URL長: 121文字
   URLハッシュ: a1b2c3d4
⚠️ Discord通知を自動無効化しました
```

### **Rate Limit対応**

- **最小送信間隔**: 2秒（設定で変更可能）
- **起動時抑制**: 30秒間（システム安定化のため）
- **429エラー**: 自動的に送信抑制

```python
# Rate Limit設定
manager._min_interval = 3        # 最小送信間隔を3秒に変更
manager._startup_grace_period = 60  # 起動時抑制を60秒に変更
```

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

### **絵文字設定**

```python
LEVEL_EMOJIS = {
    "info": "ℹ️",
    "warning": "⚠️", 
    "critical": "🚨",
}
```

## ⚠️ 重要事項

### **セキュリティ**

- **機密保護**: `config/secrets/`は`.gitignore`で保護済み
- **権限設定**: `chmod 600 config/secrets/discord_webhook.txt`推奨
- **URLハッシュ**: 401エラー時はハッシュのみログ出力

### **URL形式要件**

- **形式**: `https://discord.com/api/webhooks/ID/TOKEN`
- **ID**: 18-19桁の数字
- **TOKEN**: 3文字以上の文字列
- **文字数**: 通常120-130文字程度

### **パフォーマンス**

- **非同期対応**: すべての送信処理は非ブロッキング
- **タイムアウト**: HTTP送信タイムアウト設定済み
- **メモリ効率**: 軽量設計でメモリ使用量最小化

### **依存関係**

- **外部ライブラリ**: requests（HTTP送信）、python-dotenv（.env読み込み）
- **内部依存**: src.core.config（設定管理）
- **設定ファイル**: config/secrets/.env、config/secrets/discord_webhook.txt

---

**システム監視・通知層**: 3層アーキテクチャによる堅牢なDiscord通知システム。優先順位付きWebhook URL取得、401エラー・Rate Limit対応、JSON形式エラー防止機能を備えた高信頼性通知システム。
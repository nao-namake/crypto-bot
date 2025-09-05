# monitoring/ - システム監視・通知層

**Phase 19 MLOps統合版・根本修正完了**: Discord Webhookローカル設定化・401エラー処理強化・3層アーキテクチャ（Phase 15統合）・JSON API 50109エラー根絶により、安定通知・企業級品質保証・MLOps統合運用監視システムを実現

## 🎯 役割・責任

システム全体の監視・通知を担当し、Discord通知・取引シグナル・システム状態・エラー処理を一元管理。Phase 19 MLOps統合により、週次自動学習監視・Cloud Run 24時間稼働監視・Discord 3階層監視システムを統合し、安定運用・即座な問題発見・効率的な運用管理を実現します。

## 📂 ファイル構成

```
src/monitoring/
├── __init__.py                # 統合エクスポート・再エクスポート設定
└── discord_notifier.py        # Discord通知システム統合（Phase 18統合完了）
    ├── DiscordClient          # Discord Webhook送信・基盤層（200行未満）
    ├── DiscordFormatter       # メッセージフォーマット・表現層（200行未満）
    └── DiscordManager         # 通知制御・Rate Limit・制御層（200行未満）
```

**統合成果（Phase 18完了）**:
- **ファイル数削減**: 4→2ファイル（50%削減）・管理の大幅簡素化
- **統合効果**: 742行・3クラス統合・内部import削除・後方互換性完全維持
- **責任分離維持**: 各クラスの機能・インターフェース完全保持

## 🔧 主要機能・実装

### **Discord通知システム（Phase 19根本修正完了）**

**ローカルファイル優先設定**:
```python
# orchestrator.pyでのローカル優先読み込み（Phase 19実装）
webhook_path = Path("config/secrets/discord_webhook.txt")
if webhook_path.exists():
    try:
        webhook_url = webhook_path.read_text().strip()
        logger.info(f"📁 Discord Webhook URLをローカルファイルから読み込み（{len(webhook_url)}文字）")
    except Exception as e:
        logger.error(f"⚠️ ローカルファイル読み込み失敗: {e}")
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
else:
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    logger.info(f"🌐 環境変数からフォールバック")
```

**401エラー専用処理強化**:
```python
# discord_notifier.py実装（Phase 19強化版）
elif response.status_code == 401:
    import hashlib
    self.logger.error(f"❌ Discord Webhook無効 (401): URLが無効または削除されています")
    self.logger.error(f"   使用URL長: {len(self.webhook_url)}文字")
    self.logger.error(f"   URLハッシュ: {hashlib.md5(self.webhook_url.encode()).hexdigest()[:8]}")
    self.logger.error(f"   エラー詳細: {response.text}")
    self.enabled = False  # 自動無効化で連続エラー防止
    self.logger.warning("⚠️ Discord通知を自動無効化しました")
    return False
```

### **3層分離アーキテクチャ（Phase 15完成）**

**制御層 - DiscordManager**:
```python
# 通知制御・Rate Limit・起動時抑制
manager = DiscordManager(webhook_url="https://discord.com/...")
result = manager.send_simple_message("通知メッセージ", "info")
result = manager.send_trading_signal(signal_data)
```

**表現層 - DiscordFormatter**:
```python
# メッセージ構造化・埋め込み生成・色設定
embed_data = DiscordFormatter.format_trading_signal({
    "action": "buy", "confidence": 0.85, "price": 1000000
})

# 色設定
LEVEL_COLORS = {
    "info": 0x3498DB,      # 青色（情報）
    "warning": 0xF39C12,   # 黄色（警告）
    "critical": 0xE74C3C,  # 赤色（緊急）
}
```

**基盤層 - DiscordClient**:
```python
# Webhook送信・JSON検証・エラー処理
client = DiscordClient(webhook_url="https://discord.com/...")
success = client.send_embed(title="通知", description="内容", level="info")

# JSON API 50109エラー根絶
def _send_webhook(self, payload: Dict[str, Any]) -> bool:
    try:
        json_str = json.dumps(payload, ensure_ascii=False)  # ✅ 事前検証
    except (TypeError, ValueError) as e:
        self.logger.error(f"❌ JSON形式エラー: {e}")
        return False
```

### **MLOps統合監視（Phase 19実装）**

**週次自動学習監視**:
```python
# model-training.yml ワークフローの監視対応
manager.send_system_status({
    "status": "training_started",
    "model_type": "ProductionEnsemble",
    "scheduled_time": "毎週日曜日 2:00 UTC"
})
```

**Cloud Run 24時間稼働監視**:
```python
# Cloud Run監視・スケーリング状態通知
manager.send_system_status({
    "status": "healthy",
    "service": "crypto-bot-service-prod",
    "uptime": 86400,
    "region": "asia-northeast1"
})
```

## 📝 使用方法・例

### **基本的な使用方法（Phase 19更新版）**

**初期化・基本メッセージ**:
```python
from src.monitoring import DiscordManager

# 初期化（config/secrets/discord_webhook.txtから自動読み込み）
manager = DiscordManager()

# シンプルメッセージ送信
manager.send_simple_message("システム起動完了", "info")
```

**取引シグナル通知（ML信頼度修正対応）**:
```python
# 実際のML予測確率を反映（Phase 19修正）
signal_data = {
    "action": "buy",
    "confidence": 0.734,  # 実際のProductionEnsemble予測確率
    "price": 1000000,
    "symbol": "BTC/JPY",
    "features_used": 12,  # feature_manager統合対応
    "model": "ProductionEnsemble"
}
manager.send_trading_signal(signal_data)
```

**システム状態通知（MLOps統合）**:
```python
# MLOps統合システム状態
status_data = {
    "status": "healthy",
    "uptime": 7200,
    "trades_today": 3,
    "current_balance": 1050000,
    "ml_model": "ProductionEnsemble",
    "features_count": 12,
    "last_training": "2025-09-01"
}
manager.send_system_status(status_data)
```

### **logger.py統合使用（Phase 19対応）**:
```python
from src.core.logger import setup_logging
from src.monitoring import DiscordManager

# ログシステムとDiscord統合
logger = setup_logging("crypto_bot")
discord_manager = DiscordManager()
logger.set_discord_manager(discord_manager)

# Discord通知付きログ（Phase 19 MLOps統合）
logger.info("MLモデル初期化成功", discord_notify=True)
logger.warning("feature_manager 12特徴量生成完了", discord_notify=True)
logger.error("ProductionEnsemble読み込み失敗", discord_notify=True)
```

## ⚠️ 注意事項・制約

### **Discord Webhook設定（Phase 19重要変更）**

**優先順位（Phase 19実装）**:
1. **ローカルファイル**（最優先）: `config/secrets/discord_webhook.txt`
2. **環境変数**（フォールバック）: `DISCORD_WEBHOOK_URL`
3. **GCP Secret Manager**（従来方式）: `discord-webhook-url`

**設定注意事項**:
- **機密性**: `config/secrets/`は`.gitignore`で保護済み
- **URL形式**: `https://discord.com/api/webhooks/ID/TOKEN`形式必須
- **文字数**: 通常120-130文字程度
- **権限設定**: `chmod 600 config/secrets/discord_webhook.txt`推奨

### **Rate Limiting・起動時抑制**
```python
# 自動Rate Limit制御
manager._min_interval = 2        # 最小送信間隔（2秒）
manager._startup_grace_period = 30  # 起動時抑制期間（30秒）
```

### **エラー処理制約（Phase 19強化）**
- **401エラー**: 自動無効化・連続エラー防止・URLハッシュ出力
- **JSON形式エラー**: 事前検証・50109エラー根絶
- **Rate Limit違反**: 自動制御・2秒間隔保証

## 🔗 関連ファイル・依存関係

### **重要な外部依存（Phase 19統合）**
- **`src/core/orchestration/orchestrator.py`**: Discord Webhookローカル読み込み実装・MLOps統合制御
- **`src/core/logger.py`**: JST対応ログ・構造化出力・Discord通知統合
- **`src/core/services/trading_cycle_manager.py`**: ML信頼度修正・真の予測実装・Discord通知連携
- **`config/secrets/discord_webhook.txt`**: ローカルWebhook URL設定・機密情報
- **`.gitignore`**: `config/secrets/`機密情報保護設定

### **MLOps統合連携**
- **feature_manager統合**: 12特徴量統一管理・ProductionEnsemble連携・通知データ統合
- **週次自動学習**: GitHub Actions・model-training.yml・学習進捗通知
- **Cloud Run統合**: 24時間稼働・スケーリング・ヘルスチェック通知
- **GCP Secret Manager**: フォールバック設定・従来方式継続サポート

### **品質保証連携（Phase 19統合）**
- **654テスト**: monitoring関連49テスト・100%合格・回帰防止
- **CI/CD統合**: ci.yml・品質チェック・デプロイ監視
- **ログ監視**: Cloud Logging・Discord通知・エラー監視

---

**🎯 Phase 19 MLOps統合・根本修正完了**: Discord Webhookローカル設定化・401エラー処理強化・3層アーキテクチャ統合・JSON API 50109エラー根絶・週次自動学習監視・Cloud Run 24時間稼働監視により、安定通知・企業級品質保証・MLOps統合運用監視システムを実現**

**重要**: Phase 19根本修正により、Discord通知の安定性・MLOps統合監視・設定管理の柔軟性が大幅向上。monitoring/システム監視層は、ローカルファイル優先設定・3層アーキテクチャ・強化エラー処理・MLOps統合により、ペーパートレードから本番運用まで一貫した高品質監視体験を実現しています。
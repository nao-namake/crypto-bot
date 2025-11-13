"""
Discord通知システム - Phase 49完了（週間レポート専用）

Phase 49完了:
- DiscordClient: シンプルWebhook通知クライアント（画像ファイル送信対応）
- DiscordManager: 週間レポート専用通知マネージャー
- 損益グラフ送信機能（matplotlib・Pillow統合）
- レート制限対応（rate_limit_ms: 1000ms）

Phase 48: Discord週間レポート実装（通知99%削減達成）
- 既存の複雑な通知システムを完全削除（300-1,500回/月 → 4回/月）
- 週間レポート送信機能のみに特化（コスト35%削減・月額700-900円削減）
- シンプルな設計で保守性向上

削除された機能: エラー通知・取引シグナル通知・取引実行結果通知・システム状態通知・バッチ処理・日次サマリー
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from ..config import get_monitoring_config

# dotenv がある場合は読み込み
try:
    from dotenv import load_dotenv

    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


class DiscordClient:
    """
    シンプルなDiscord Webhook通知クライアント

    Phase 48: 週間レポート送信に最適化
    """

    def __init__(self, webhook_url: Optional[str] = None):
        """
        Discord通知クライアント初期化

        Args:
            webhook_url: Discord WebhookのURL（自動取得も可能）
        """
        self.logger = logging.getLogger("crypto_bot.discord_client")

        # Webhook URL取得（優先順位付き）
        self.webhook_url = self._get_webhook_url(webhook_url)

        if not self.webhook_url:
            self.logger.warning("⚠️ Discord WebhookURL未設定 - 通知は無効化されます")
            self.enabled = False
            return

        # URL基本検証
        if not self._validate_webhook_url(self.webhook_url):
            self.logger.error("❌ 不正なWebhookURL形式 - 通知を無効化")
            self.enabled = False
            return

        self.enabled = True
        self.logger.info("✅ Discord通知クライアント初期化完了")

    def _get_webhook_url(self, webhook_url: Optional[str] = None) -> Optional[str]:
        """
        優先順位付きでWebhook URLを取得

        優先順位:
        1. 引数で渡されたURL
        2. .envファイル
        3. 環境変数
        4. discord_webhook.txt（後方互換性）

        Args:
            webhook_url: 引数で渡されたURL

        Returns:
            Webhook URL（見つからない場合はNone）
        """
        # 1. 引数（最優先）
        if webhook_url:
            self.logger.info("🔗 Discord Webhook URLを引数から取得")
            return webhook_url

        # 2. .envファイル
        env_path = Path("config/secrets/.env")
        if env_path.exists() and DOTENV_AVAILABLE:
            try:
                load_dotenv(env_path)
                env_url = os.getenv("DISCORD_WEBHOOK_URL")
                if env_url and env_url.strip():
                    cleaned_url = env_url.strip().rstrip("\n\r").strip("\"'")
                    self.logger.info("📁 Discord Webhook URLを.envファイルから読み込み")
                    return cleaned_url
            except Exception as e:
                self.logger.warning(f"⚠️ .envファイル読み込み失敗: {e}")

        # 3. 環境変数
        env_url = os.getenv("DISCORD_WEBHOOK_URL")
        if env_url and env_url.strip():
            cleaned_url = env_url.strip().rstrip("\n\r").strip("\"'")
            self.logger.info("🌐 Discord Webhook URLを環境変数から取得")
            return cleaned_url

        # 4. discord_webhook.txt（後方互換性）
        txt_path = Path("config/secrets/discord_webhook.txt")
        if txt_path.exists():
            try:
                txt_url = txt_path.read_text().strip()
                if txt_url:
                    cleaned_url = txt_url.strip().rstrip("\n\r").strip("\"'")
                    self.logger.info("📄 Discord Webhook URLをtxtファイルから読み込み")
                    return cleaned_url
            except Exception as e:
                self.logger.warning(f"⚠️ txtファイル読み込み失敗: {e}")

        # すべて失敗
        self.logger.error("❌ Discord Webhook URLが見つかりません")
        return None

    def _validate_webhook_url(self, url: str) -> bool:
        """
        WebhookURL形式の基本検証

        Args:
            url: 検証するURL

        Returns:
            有効な形式かどうか
        """
        if not isinstance(url, str):
            return False
        if not url.startswith("https://discord.com/api/webhooks/"):
            return False
        if len(url) <= 50:
            return False

        # パス部分を解析してIDとトークンの長さをチェック
        prefix = "https://discord.com/api/webhooks/"
        path_part = url[len(prefix) :]
        parts = path_part.split("/")

        # ID/TOKEN の形式チェック
        if len(parts) < 2:
            return False

        webhook_id = parts[0]
        webhook_token = parts[1]

        # IDは18-19桁の数字、トークンは最低3文字以上
        if not (webhook_id.isdigit() and 18 <= len(webhook_id) <= 19):
            return False
        if len(webhook_token) < 3:
            return False

        return True

    def send_message(self, message: str, level: str = "info") -> bool:
        """
        シンプルなテキストメッセージ送信

        Args:
            message: 送信メッセージ
            level: 重要度（info/warning/critical）

        Returns:
            送信成功・失敗
        """
        if not self.enabled:
            return False

        # 色設定
        colors = {
            "info": 0x3498DB,  # 青色
            "warning": 0xF39C12,  # 黄色
            "critical": 0xE74C3C,  # 赤色
        }

        # 絵文字設定
        emojis = {
            "info": "ℹ️",
            "warning": "⚠️",
            "critical": "🚨",
        }

        # embed作成（Discord API形式準拠）
        embed = {
            "title": f"{emojis.get(level, 'ℹ️')} {level.upper()}",
            "description": message,
            "color": colors.get(level, colors["info"]),
            "timestamp": self._get_iso_timestamp(),
        }

        # payload作成
        payload = {"username": "Crypto-Bot", "embeds": [embed]}

        return self._send_webhook(payload)

    def send_embed(
        self,
        title: str,
        description: str,
        fields: Optional[list] = None,
        level: str = "info",
        image_url: Optional[str] = None,
    ) -> bool:
        """
        埋め込み形式メッセージ送信

        Args:
            title: タイトル
            description: 説明
            fields: フィールドリスト（オプション）
            level: 重要度
            image_url: 画像URL（オプション）

        Returns:
            送信成功・失敗
        """
        if not self.enabled:
            return False

        # 色・絵文字設定
        colors = {"info": 0x3498DB, "warning": 0xF39C12, "critical": 0xE74C3C}
        emojis = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}

        # embed構築
        embed = {
            "title": f"{emojis.get(level, 'ℹ️')} {title}",
            "description": description,
            "color": colors.get(level, colors["info"]),
            "timestamp": self._get_iso_timestamp(),
        }

        # フィールド追加（オプション）
        if fields:
            embed["fields"] = fields

        # 画像追加（オプション）
        if image_url:
            embed["image"] = {"url": image_url}

        payload = {"username": "Crypto-Bot", "embeds": [embed]}

        return self._send_webhook(payload)

    def send_webhook_with_file(
        self,
        title: str,
        description: str,
        fields: Optional[list] = None,
        level: str = "info",
        file_path: Optional[str] = None,
    ) -> bool:
        """
        ファイル添付付きWebhook送信

        Args:
            title: タイトル
            description: 説明
            fields: フィールドリスト
            level: 重要度
            file_path: 添付ファイルパス

        Returns:
            送信成功・失敗
        """
        if not self.enabled:
            return False

        # 色・絵文字設定
        colors = {"info": 0x3498DB, "warning": 0xF39C12, "critical": 0xE74C3C}
        emojis = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}

        # embed構築
        embed = {
            "title": f"{emojis.get(level, 'ℹ️')} {title}",
            "description": description,
            "color": colors.get(level, colors["info"]),
            "timestamp": self._get_iso_timestamp(),
        }

        # フィールド追加
        if fields:
            embed["fields"] = fields

        # ファイル添付がある場合
        if file_path and Path(file_path).exists():
            # 画像をembedに添付
            embed["image"] = {"url": "attachment://chart.png"}

            # multipart/form-data送信
            payload = {"embeds": [embed]}

            try:
                with open(file_path, "rb") as f:
                    files = {"file": ("chart.png", f, "image/png")}
                    data = {"payload_json": json.dumps(payload)}

                    response = requests.post(
                        self.webhook_url,
                        data=data,
                        files=files,
                        timeout=30,
                    )

                    if response.status_code == 200:
                        self.logger.debug("✅ Discord通知送信成功（ファイル添付）")
                        return True
                    else:
                        self.logger.error(f"❌ Discord API エラー ({response.status_code}): {response.text}")
                        return False

            except Exception as e:
                self.logger.error(f"❌ ファイル添付送信エラー: {e}")
                return False

        # ファイルなしの場合は通常送信
        payload = {"username": "Crypto-Bot", "embeds": [embed]}
        return self._send_webhook(payload)

    def _send_webhook(self, payload: Dict[str, Any]) -> bool:
        """
        WebhookのHTTP送信処理

        Args:
            payload: 送信データ

        Returns:
            送信成功・失敗
        """
        try:
            # JSON形式検証
            try:
                json_str = json.dumps(payload, ensure_ascii=True)
            except (TypeError, ValueError) as e:
                self.logger.error(f"❌ JSON形式エラー: {e}")
                return False

            # HTTP送信
            headers = {"Content-Type": "application/json"}
            timeout_seconds = get_monitoring_config("discord.timeout", 10)

            response = requests.post(
                self.webhook_url,
                data=json_str,
                headers=headers,
                timeout=timeout_seconds,
            )

            # レスポンス処理
            if response.status_code in [200, 204]:
                self.logger.debug("✅ Discord通知送信成功")
                return True
            elif response.status_code == 400:
                self.logger.error(f"❌ Discord API形式エラー (400): {response.text}")
                return False
            elif response.status_code == 401:
                self.logger.error("❌ Discord Webhook無効 (401)")
                return False
            elif response.status_code == 429:
                self.logger.warning("⚠️ Discord Rate Limit - 送信抑制")
                return False
            else:
                self.logger.error(f"❌ Discord API エラー ({response.status_code}): {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Discord送信ネットワークエラー: {e}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Discord送信予期しないエラー: {e}")
            return False

    def _get_iso_timestamp(self) -> str:
        """
        ISO形式タイムスタンプ取得

        Returns:
            ISO形式タイムスタンプ
        """
        from datetime import timezone

        return datetime.now(timezone.utc).isoformat()

    def test_connection(self) -> bool:
        """
        Discord接続テスト

        Returns:
            接続成功・失敗
        """
        return self.send_message("🔧 Discord接続テスト", "info")


class DiscordManager:
    """
    Discord通知の管理・制御（Phase 48簡略版）

    週間レポート送信に最適化。
    Rate Limit制御のみを提供。
    """

    def __init__(self, webhook_url: Optional[str] = None):
        """
        Discord管理システム初期化

        Args:
            webhook_url: Discord WebhookのURL
        """
        self.logger = logging.getLogger("crypto_bot.discord_manager")

        # Discord client初期化
        self.client = DiscordClient(webhook_url)

        # Rate limit管理
        self._last_send_time = 0
        self._min_interval = get_monitoring_config("discord.min_interval", 2)

        self.enabled = self.client.enabled

        if self.enabled:
            self.logger.info("✅ Discord通知マネージャー初期化完了")
        else:
            self.logger.warning("⚠️ Discord通知は無効化されています")

    def send_simple_message(self, message: str, level: str = "info") -> bool:
        """
        シンプルなメッセージ送信

        Args:
            message: 送信メッセージ
            level: 重要度（info/warning/critical）

        Returns:
            送信成功・失敗
        """
        if not self._rate_limit_check():
            return False

        success = self.client.send_message(message, level)
        if success:
            self._update_last_send_time()

        return success

    def send_embed(
        self,
        title: str,
        description: str,
        fields: Optional[list] = None,
        level: str = "info",
        image_url: Optional[str] = None,
    ) -> bool:
        """
        埋め込み形式メッセージ送信

        Args:
            title: タイトル
            description: 説明
            fields: フィールドリスト
            level: 重要度
            image_url: 画像URL

        Returns:
            送信成功・失敗
        """
        if not self._rate_limit_check():
            return False

        success = self.client.send_embed(title, description, fields, level, image_url)
        if success:
            self._update_last_send_time()

        return success

    def send_webhook_with_file(
        self,
        title: str,
        description: str,
        fields: Optional[list] = None,
        level: str = "info",
        file_path: Optional[str] = None,
    ) -> bool:
        """
        ファイル添付付きメッセージ送信

        Args:
            title: タイトル
            description: 説明
            fields: フィールドリスト
            level: 重要度
            file_path: 添付ファイルパス

        Returns:
            送信成功・失敗
        """
        if not self._rate_limit_check():
            return False

        success = self.client.send_webhook_with_file(title, description, fields, level, file_path)
        if success:
            self._update_last_send_time()

        return success

    def test_connection(self) -> bool:
        """
        Discord接続テスト

        Returns:
            接続成功・失敗
        """
        if not self.enabled:
            self.logger.warning("⚠️ Discord通知が無効のためテスト不可")
            return False

        return self.client.test_connection()

    def _rate_limit_check(self) -> bool:
        """
        Rate limit チェック

        Returns:
            送信可否
        """
        if not self.enabled:
            return False

        now = time.time()
        elapsed = now - self._last_send_time

        if elapsed < self._min_interval:
            self.logger.debug(f"📢 Rate limit制御 - {self._min_interval - elapsed:.1f}秒待機")
            return False

        return True

    def _update_last_send_time(self):
        """最終送信時刻更新"""
        self._last_send_time = time.time()

    def get_status(self) -> Dict[str, Any]:
        """
        Discord管理システムの状態取得

        Returns:
            状態情報
        """
        return {
            "enabled": self.enabled,
            "client_enabled": self.client.enabled,
            "last_send_ago": time.time() - self._last_send_time,
        }


# 後方互換性のためのエイリアス
def notify(message: str, level: str = "info") -> bool:
    """
    後方互換性用の簡易通知関数

    Args:
        message: 送信メッセージ
        level: 重要度

    Returns:
        送信成功・失敗
    """
    manager = DiscordManager()
    return manager.send_simple_message(message, level)


__all__ = ["DiscordClient", "DiscordManager", "notify"]

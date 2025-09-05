"""
Discord通知システム統合版 - Phase 18統合実装

3ファイル（discord_client.py, discord_formatter.py, discord_manager.py）を
1ファイルに統合し、管理の簡素化と保守性の向上を実現。

統合効果:
- ファイル数削減: 4→2（50%削減）
- 管理簡素化: Discord関連処理の一元化
- import簡素化: 内部import不要

Phase 18統合実装日: 2025年8月30日.
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

from ..core.config import get_monitoring_config


class DiscordClient:
    """
    シンプルなDiscord Webhook通知クライアント

    Phase 15での完全再設計により、必要最小限の機能のみを提供。
    JSON形式エラー（50109）の根本解決と高い保守性を実現。
    """

    def __init__(self, webhook_url: Optional[str] = None):
        """
        Discord通知クライアント初期化

        Args:
            webhook_url: Discord WebhookのURL（環境変数から自動取得も可能）
        """
        self.logger = logging.getLogger(f"crypto_bot.discord_client")

        # Webhook URL取得（優先順位: 引数 > 環境変数 > None）
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")

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
        self, title: str, description: str, fields: Optional[list] = None, level: str = "info"
    ) -> bool:
        """
        埋め込み形式メッセージ送信

        Args:
            title: タイトル
            description: 説明
            fields: フィールドリスト（オプション）
            level: 重要度

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
            # JSON形式検証（50109エラー防止）
            try:
                json_str = json.dumps(payload, ensure_ascii=False)
            except (TypeError, ValueError) as e:
                self.logger.error(f"❌ JSON形式エラー: {e}")
                return False

            # HTTP送信
            headers = {"Content-Type": "application/json"}
            timeout_seconds = get_monitoring_config("discord.timeout", 10)
            response = requests.post(
                self.webhook_url, data=json_str, headers=headers, timeout=timeout_seconds
            )

            # レスポンス処理
            if response.status_code == 204:
                self.logger.debug("✅ Discord通知送信成功")
                return True
            elif response.status_code == 400:
                self.logger.error(f"❌ Discord API形式エラー (400): {response.text}")
                return False
            elif response.status_code == 401:
                import hashlib
                self.logger.error(f"❌ Discord Webhook無効 (401): URLが無効または削除されています")
                self.logger.error(f"   使用URL長: {len(self.webhook_url)}文字")
                self.logger.error(f"   URLハッシュ: {hashlib.md5(self.webhook_url.encode()).hexdigest()[:8]}")
                self.logger.error(f"   エラー詳細: {response.text}")
                self.enabled = False  # 自動無効化で連続エラー防止
                self.logger.warning("⚠️ Discord通知を自動無効化しました")
                return False
            elif response.status_code == 429:
                self.logger.warning("⚠️ Discord Rate Limit - 送信抑制")
                return False
            else:
                self.logger.error(
                    f"❌ Discord API エラー ({response.status_code}): {response.text}"
                )
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


class DiscordFormatter:
    """
    Discord通知メッセージのフォーマッター

    各種通知タイプに応じたメッセージ整形機能を提供。
    統一されたフォーマットで保守性と可読性を向上。
    """

    @staticmethod
    def format_trading_signal(signal_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        取引シグナル通知のフォーマット

        Args:
            signal_data: シグナル情報

        Returns:
            Discord embed形式データ
        """
        action = signal_data.get("action", "UNKNOWN")
        confidence = signal_data.get("confidence", 0)
        price = signal_data.get("price", 0)

        # アクション絵文字
        action_emojis = {"buy": "📈", "sell": "📉", "hold": "⏸️"}

        # 信頼度に応じた色（Phase 16-B：設定ファイル参照）
        high_threshold = get_monitoring_config("discord.confidence_thresholds.high", 0.8)
        medium_threshold = get_monitoring_config("discord.confidence_thresholds.medium", 0.6)

        if confidence >= high_threshold:
            color = 0x27AE60  # 緑色（高信頼度）
        elif confidence >= medium_threshold:
            color = 0xF39C12  # 黄色（中信頼度）
        else:
            color = 0xE67E22  # オレンジ色（低信頼度）

        emoji = action_emojis.get(action.lower() if action else "", "❓")

        return {
            "title": f"{emoji} 取引シグナル",
            "description": f"**{action.upper() if action else 'UNKNOWN'}** シグナル検出",
            "color": color,
            "fields": [
                {
                    "name": "💰 価格",
                    "value": f"¥{price:,.0f}" if price > 0 else "未設定",
                    "inline": True,
                },
                {"name": "🎯 信頼度", "value": f"{confidence:.1%}", "inline": True},
            ],
        }

    @staticmethod
    def format_trade_execution(execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        取引実行結果のフォーマット

        Args:
            execution_data: 実行結果情報

        Returns:
            Discord embed形式データ
        """
        success = execution_data.get("success", False)
        side = execution_data.get("side", "unknown")
        amount = execution_data.get("amount", 0)
        price = execution_data.get("price", 0)
        pnl = execution_data.get("pnl")

        # 成功・失敗による色分け
        color = 0x27AE60 if success else 0xE74C3C  # 緑 or 赤
        status_emoji = "✅" if success else "❌"
        side_emoji = "📈" if side == "buy" else "📉"

        title = f"{status_emoji} {side_emoji} 取引{'成功' if success else '失敗'}"

        fields = [
            {"name": "📊 取引タイプ", "value": side.upper(), "inline": True},
            {
                "name": "💎 数量",
                "value": f"{amount:.4f} BTC" if amount > 0 else "未設定",
                "inline": True,
            },
            {
                "name": "💰 価格",
                "value": f"¥{price:,.0f}" if price > 0 else "未設定",
                "inline": True,
            },
        ]

        # PnL情報追加
        if pnl is not None:
            pnl_emoji = "💰" if pnl > 0 else "💸"
            fields.append({"name": f"{pnl_emoji} 損益", "value": f"¥{pnl:,.0f}", "inline": True})

        return {
            "title": title,
            "description": "取引実行結果をお知らせします",
            "color": color,
            "fields": fields,
        }

    @staticmethod
    def format_system_status(status_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        システム状態通知のフォーマット

        Args:
            status_data: システム状態情報

        Returns:
            Discord embed形式データ
        """
        status = status_data.get("status", "unknown")
        uptime = status_data.get("uptime", 0)
        trades_today = status_data.get("trades_today", 0)
        current_balance = status_data.get("current_balance")

        # ステータス絵文字・色
        status_config = {
            "healthy": {"emoji": "🟢", "color": 0x27AE60},
            "warning": {"emoji": "🟡", "color": 0xF39C12},
            "error": {"emoji": "🔴", "color": 0xE74C3C},
            "starting": {"emoji": "🔄", "color": 0x3498DB},
        }

        config = status_config.get(status, status_config["warning"])

        fields = [
            {
                "name": "⏱️ 稼働時間",
                "value": f"{uptime // 3600}時間{(uptime % 3600) // 60}分",
                "inline": True,
            },
            {"name": "📈 本日取引数", "value": f"{trades_today}回", "inline": True},
        ]

        # 残高情報追加
        if current_balance is not None:
            fields.append(
                {"name": "💰 現在残高", "value": f"¥{current_balance:,.0f}", "inline": True}
            )

        return {
            "title": f"{config['emoji']} システム状態",
            "description": f"ステータス: **{status.upper()}**",
            "color": config["color"],
            "fields": fields,
        }

    @staticmethod
    def format_error_notification(error_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        エラー通知のフォーマット

        Args:
            error_data: エラー情報

        Returns:
            Discord embed形式データ
        """
        error_type = error_data.get("type", "UnknownError")
        message = error_data.get("message", "詳細不明")
        component = error_data.get("component", "システム")
        severity = error_data.get("severity", "warning")

        # 重要度による色分け
        severity_config = {
            "critical": {"emoji": "🚨", "color": 0xE74C3C},
            "error": {"emoji": "❌", "color": 0xE67E22},
            "warning": {"emoji": "⚠️", "color": 0xF39C12},
        }

        config = severity_config.get(severity, severity_config["warning"])

        return {
            "title": f"{config['emoji']} エラー発生",
            "description": f"**{component}** でエラーが発生しました",
            "color": config["color"],
            "fields": [
                {"name": "🏷️ エラータイプ", "value": error_type, "inline": False},
                {
                    "name": "📝 メッセージ",
                    "value": message[:100] + ("..." if len(message) > 100 else ""),
                    "inline": False,
                },
            ],
        }

    @staticmethod
    def format_statistics_summary(stats_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        取引統計サマリーのフォーマット

        Args:
            stats_data: 統計情報

        Returns:
            Discord embed形式データ
        """
        total_trades = stats_data.get("total_trades", 0)
        winning_trades = stats_data.get("winning_trades", 0)
        win_rate = stats_data.get("win_rate", 0) * 100
        return_rate = stats_data.get("return_rate", 0) * 100
        current_balance = stats_data.get("current_balance", 0)

        # リターン率による色分け
        if return_rate > 5:
            color = 0x27AE60  # 緑色（良好）
        elif return_rate > 0:
            color = 0xF39C12  # 黄色（普通）
        else:
            color = 0xE67E22  # オレンジ色（注意）

        return {
            "title": "📊 取引統計サマリー",
            "description": "本日の取引パフォーマンス",
            "color": color,
            "fields": [
                {"name": "🔢 総取引数", "value": f"{total_trades}回", "inline": True},
                {"name": "🏆 勝ち取引", "value": f"{winning_trades}回", "inline": True},
                {"name": "📈 勝率", "value": f"{win_rate:.1f}%", "inline": True},
                {"name": "💰 現在残高", "value": f"¥{current_balance:,.0f}", "inline": True},
                {"name": "📊 リターン率", "value": f"{return_rate:+.2f}%", "inline": True},
            ],
        }


class DiscordManager:
    """
    Discord通知の管理・制御

    Rate Limit制御、通知抑制、logger.pyとの統合を担当。
    シンプルな設計により保守性と信頼性を重視。
    """

    def __init__(self, webhook_url: Optional[str] = None):
        """
        Discord管理システム初期化

        Args:
            webhook_url: Discord WebhookのURL
        """
        self.logger = logging.getLogger("crypto_bot.discord_manager")

        # Discord clientとformatter初期化（Phase 18統合：内部インスタンス化）
        self.client = DiscordClient(webhook_url)
        self.formatter = DiscordFormatter()

        # Rate limit管理
        self._last_send_time = 0
        self._min_interval = get_monitoring_config(
            "discord.min_interval", 2
        )  # 設定ファイルから取得

        # 起動時通知抑制（システム安定化のため）
        self._startup_time = time.time()
        self._startup_grace_period = get_monitoring_config(
            "discord.startup_grace_period", 30
        )  # 設定ファイルから取得

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
        if not self._should_send():
            return False

        success = self.client.send_message(message, level)
        if success:
            self._update_last_send_time()

        return success

    def send_trading_signal(self, signal_data: Dict[str, Any]) -> bool:
        """
        取引シグナル通知送信

        Args:
            signal_data: シグナル情報

        Returns:
            送信成功・失敗
        """
        if not self._should_send():
            return False

        embed_data = self.formatter.format_trading_signal(signal_data)
        success = self.client.send_embed(
            title=embed_data["title"],
            description=embed_data["description"],
            fields=embed_data.get("fields"),
            level="info",
        )

        if success:
            self._update_last_send_time()

        return success

    def send_trade_execution(self, execution_data: Dict[str, Any]) -> bool:
        """
        取引実行結果通知送信

        Args:
            execution_data: 実行結果情報

        Returns:
            送信成功・失敗
        """
        if not self._should_send():
            return False

        embed_data = self.formatter.format_trade_execution(execution_data)
        level = "info" if execution_data.get("success", False) else "warning"

        success = self.client.send_embed(
            title=embed_data["title"],
            description=embed_data["description"],
            fields=embed_data.get("fields"),
            level=level,
        )

        if success:
            self._update_last_send_time()

        return success

    def send_system_status(self, status_data: Dict[str, Any]) -> bool:
        """
        システム状態通知送信

        Args:
            status_data: システム状態情報

        Returns:
            送信成功・失敗
        """
        if not self._should_send():
            return False

        embed_data = self.formatter.format_system_status(status_data)
        level = {"healthy": "info", "warning": "warning", "error": "critical"}.get(
            status_data.get("status", "warning"), "warning"
        )

        success = self.client.send_embed(
            title=embed_data["title"],
            description=embed_data["description"],
            fields=embed_data.get("fields"),
            level=level,
        )

        if success:
            self._update_last_send_time()

        return success

    def send_error_notification(self, error_data: Dict[str, Any]) -> bool:
        """
        エラー通知送信

        Args:
            error_data: エラー情報

        Returns:
            送信成功・失敗
        """
        # エラー通知は起動時抑制を無視（重要な通知のため）
        if not self.enabled or not self._rate_limit_check():
            return False

        embed_data = self.formatter.format_error_notification(error_data)
        level = error_data.get("severity", "warning")

        success = self.client.send_embed(
            title=embed_data["title"],
            description=embed_data["description"],
            fields=embed_data.get("fields"),
            level=level,
        )

        if success:
            self._update_last_send_time()

        return success

    def send_statistics_summary(self, stats_data: Dict[str, Any]) -> bool:
        """
        統計サマリー通知送信

        Args:
            stats_data: 統計情報

        Returns:
            送信成功・失敗
        """
        if not self._should_send():
            return False

        embed_data = self.formatter.format_statistics_summary(stats_data)

        success = self.client.send_embed(
            title=embed_data["title"],
            description=embed_data["description"],
            fields=embed_data.get("fields"),
            level="info",
        )

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

    def _should_send(self) -> bool:
        """
        送信可否判定（Rate limit + 起動時抑制）

        Returns:
            送信可否
        """
        if not self.enabled:
            return False

        # 起動時抑制チェック
        if time.time() - self._startup_time < self._startup_grace_period:
            self.logger.debug("🔇 起動時抑制中 - Discord通知をスキップ")
            return False

        return self._rate_limit_check()

    def _rate_limit_check(self) -> bool:
        """
        Rate limit チェック

        Returns:
            送信可否
        """
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
            "startup_grace_remaining": max(
                0, self._startup_grace_period - (time.time() - self._startup_time)
            ),
        }


# 後方互換性のためのエイリアス（必要に応じて）
__all__ = [
    "DiscordClient",
    "DiscordFormatter",
    "DiscordManager",
]

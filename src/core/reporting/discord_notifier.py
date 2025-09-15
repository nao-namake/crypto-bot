"""
Discord通知システム統合版 - Phase 22統合実装

3ファイル（discord_client.py, discord_formatter.py, discord_manager.py）を
1ファイルに統合し、管理の簡素化と保守性の向上を実現。

統合効果:
- ファイル数削減: 4→2（50%削減）
- 管理簡素化: Discord関連処理の一元化
- import簡素化: 内部import不要

Phase 22統合実装日: 2025年9月12日.
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

    Phase 22での完全再設計により、必要最小限の機能のみを提供。
    JSON形式エラー（50109）の根本解決と高い保守性を実現。
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
                # .envファイルを読み込み
                load_dotenv(env_path)
                env_url = os.getenv("DISCORD_WEBHOOK_URL")
                if env_url and env_url.strip():
                    # 制御文字・改行文字完全除去
                    cleaned_url = env_url.strip().rstrip("\n\r").strip("\"'")
                    self.logger.info(
                        f"📁 Discord Webhook URLを.envファイルから読み込み（{len(cleaned_url)}文字）"
                    )
                    return cleaned_url
            except Exception as e:
                self.logger.warning(f"⚠️ .envファイル読み込み失敗: {e}")

        # 3. 環境変数（Cloud Run対応・制御文字完全除去・強化デバッグ）
        env_url = os.getenv("DISCORD_WEBHOOK_URL")
        self.logger.info(
            f"🌍 環境変数DISCORD_WEBHOOK_URL取得: 存在={bool(env_url)}, 型={type(env_url)}"
        )

        if env_url and env_url.strip():
            # Cloud Run環境でのデバッグ強化：詳細分析
            self.logger.info(
                f"🔍 元環境変数詳細: 長さ={len(env_url)}, 最初50文字={env_url[:50]}..."
            )

            # 制御文字・改行文字の詳細検出
            import re

            control_chars = re.findall(r"[\x00-\x1f\x7f-\x9f]", env_url)
            if control_chars:
                self.logger.warning(f"⚠️ 制御文字検出: {[hex(ord(c)) for c in control_chars]}")

            # Cloud Runでの制御文字・改行文字完全除去
            cleaned_url = env_url.strip().rstrip("\n\r").strip("\"'")

            # デバッグ情報（文字数変化の追跡）
            if len(cleaned_url) != len(env_url.strip()):
                self.logger.warning(
                    f"🔧 環境変数URL清浄化: {len(env_url)}文字 -> {len(cleaned_url)}文字"
                )
                # ハッシュ値で検証
                import hashlib

                original_hash = hashlib.md5(env_url.encode()).hexdigest()[:8]
                cleaned_hash = hashlib.md5(cleaned_url.encode()).hexdigest()[:8]
                self.logger.info(f"   元ハッシュ: {original_hash} -> 清浄後: {cleaned_hash}")

            # URL形式の詳細検証（Cloud Run専用）
            if cleaned_url.startswith("https://discord.com/api/webhooks/"):
                self.logger.info("✅ DiscordWebhook URL形式確認: 正常")
            else:
                self.logger.error(f"❌ DiscordWebhook URL形式エラー: {cleaned_url[:50]}...")

            self.logger.info("🌐 Discord Webhook URLを環境変数から取得（Cloud Run対応済み）")
            return cleaned_url
        else:
            self.logger.error("❌ 環境変数DISCORD_WEBHOOK_URLが空またはNone")

        # 4. discord_webhook.txt（後方互換性）
        txt_path = Path("config/secrets/discord_webhook.txt")
        if txt_path.exists():
            try:
                txt_url = txt_path.read_text().strip()
                if txt_url:
                    # 制御文字・改行文字完全除去
                    cleaned_url = txt_url.strip().rstrip("\n\r").strip("\"'")
                    self.logger.info(
                        f"📄 Discord Webhook URLをtxtファイルから読み込み（{len(cleaned_url)}文字）"
                    )
                    return cleaned_url
            except Exception as e:
                self.logger.warning(f"⚠️ txtファイル読み込み失敗: {e}")

        # すべて失敗
        self.logger.error("❌ Discord Webhook URLが見つかりません")
        self.logger.error(
            "   設定ファイル: config/secrets/.env または config/secrets/discord_webhook.txt"
        )
        self.logger.error("   環境変数: DISCORD_WEBHOOK_URL")
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

            # HTTP送信（Cloud Run環境デバッグ強化）
            headers = {"Content-Type": "application/json"}
            timeout_seconds = get_monitoring_config("discord.timeout", 10)

            # Cloud Run環境での送信前デバッグ
            self.logger.info(
                f"🚀 Discord送信開始: URL長={len(self.webhook_url)}, ペイロード={len(json_str)}文字"
            )
            self.logger.debug(f"🔗 送信先URL（最初50文字）: {self.webhook_url[:50]}...")

            response = requests.post(
                self.webhook_url,
                data=json_str,
                headers=headers,
                timeout=timeout_seconds,
            )

            # Cloud Run環境での送信後デバッグ
            try:
                elapsed_time = response.elapsed.total_seconds()
                self.logger.info(
                    f"📨 Discord応答: ステータス={response.status_code}, 時間={elapsed_time:.3f}秒"
                )
            except (AttributeError, TypeError):
                # テスト環境でのMockオブジェクト対応
                self.logger.info(f"📨 Discord応答: ステータス={response.status_code}")

            # レスポンス処理
            if response.status_code == 204:
                self.logger.debug("✅ Discord通知送信成功")
                return True
            elif response.status_code == 400:
                self.logger.error(f"❌ Discord API形式エラー (400): {response.text}")
                return False
            elif response.status_code == 401:
                import hashlib

                self.logger.error("❌ Discord Webhook無効 (401): URLが無効または削除されています")
                self.logger.error(f"   使用URL長: {len(self.webhook_url)}文字")
                self.logger.error(
                    f"   URLハッシュ: {hashlib.md5(self.webhook_url.encode()).hexdigest()[:8]}"
                )
                self.logger.error(f"   エラー詳細: {response.text}")
                # self.enabled = False  # 自動無効化を一時停止（WebhookURL修正後の再試行を許可）
                self.logger.warning("⚠️ Discord通知エラー（継続試行します）")
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

        # 信頼度に応じた色（Phase 22：設定ファイル参照）
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
                {
                    "name": "💰 現在残高",
                    "value": f"¥{current_balance:,.0f}",
                    "inline": True,
                }
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
                {
                    "name": "💰 現在残高",
                    "value": f"¥{current_balance:,.0f}",
                    "inline": True,
                },
                {
                    "name": "📊 リターン率",
                    "value": f"{return_rate:+.2f}%",
                    "inline": True,
                },
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

        # Discord clientとformatter初期化（Phase 22統合：内部インスタンス化）
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


class NotificationBatcher:
    """
    Discord通知のバッチ処理とキューイング

    機能:
    - 通知のキューイング
    - 定期的なバッチ送信
    - レート制限管理
    - 重複通知の除去
    """

    def __init__(self, discord_client: DiscordClient):
        """
        バッチャー初期化

        Args:
            discord_client: Discord送信クライアント
        """
        self.client = discord_client
        self.logger = logging.getLogger("crypto_bot.notification_batcher")

        # キューとタイマー
        self.notification_queue = []
        self.last_batch_time = time.time()
        self.batch_interval = get_monitoring_config("discord.batch_interval_minutes", 60) * 60

        # レート制限
        self.rate_limit_config = get_monitoring_config("discord.rate_limit", {})
        self.max_per_hour = self.rate_limit_config.get("max_per_hour", 12)
        self.hourly_count = 0
        self.hour_start_time = time.time()

        self.logger.info(f"✅ 通知バッチャー初期化完了: 間隔={self.batch_interval}秒")

    def add_notification(self, notification_data: Dict[str, Any], level: str = "info") -> bool:
        """
        通知をキューに追加

        Args:
            notification_data: 通知データ
            level: 通知レベル

        Returns:
            bool: キューイング成功・失敗
        """
        # レベル判定
        level_config = get_monitoring_config("discord.notification_levels", {})
        notification_mode = level_config.get(level, "batch")

        # 即時通知の場合
        if notification_mode == "immediate":
            return self._send_immediate(notification_data, level)

        # 日次サマリーの場合
        if notification_mode == "daily":
            return self._add_to_daily_queue(notification_data, level)

        # バッチ通知の場合
        return self._add_to_batch_queue(notification_data, level)

    def _send_immediate(self, notification_data: Dict[str, Any], level: str) -> bool:
        """即時通知送信"""
        if not self._check_rate_limit():
            self.logger.warning("⚠️ レート制限により即時通知をスキップ")
            return False

        success = self.client.send_embed(
            title=notification_data.get("title", "通知"),
            description=notification_data.get("description", ""),
            fields=notification_data.get("fields", []),
            level=level,
        )

        if success:
            self._increment_rate_counter()

        return success

    def _add_to_batch_queue(self, notification_data: Dict[str, Any], level: str) -> bool:
        """バッチキューに追加"""
        # 重複除去のための簡単なハッシュ
        notification_hash = hash(str(notification_data.get("title", "")) + str(notification_data.get("description", "")))

        # 重複チェック
        for existing in self.notification_queue:
            if existing.get("hash") == notification_hash:
                self.logger.debug("🔄 重複通知のため統合")
                existing["count"] = existing.get("count", 1) + 1
                return True

        # 新規追加
        notification_item = {
            "data": notification_data,
            "level": level,
            "timestamp": time.time(),
            "hash": notification_hash,
            "count": 1,
        }
        self.notification_queue.append(notification_item)

        self.logger.debug(f"📝 バッチキューに追加: {len(self.notification_queue)}件")

        # 時間到達でバッチ送信
        if time.time() - self.last_batch_time >= self.batch_interval:
            self.process_batch()

        return True

    def _add_to_daily_queue(self, notification_data: Dict[str, Any], level: str) -> bool:
        """日次サマリーキューに追加"""
        # 日次サマリーは別途 DailySummaryCollector で処理
        self.logger.debug("📅 日次サマリーキューに追加")
        return True

    def process_batch(self) -> bool:
        """
        バッチ通知の処理

        Returns:
            bool: 送信成功・失敗
        """
        if not self.notification_queue:
            self.logger.debug("📭 バッチキューが空のためスキップ")
            return True

        if not self._check_rate_limit():
            self.logger.warning("⚠️ レート制限によりバッチ送信を延期")
            return False

        # バッチメッセージ生成
        batch_summary = self._generate_batch_summary()

        # 送信
        success = self.client.send_embed(
            title="📊 通知サマリー",
            description=f"過去{self.batch_interval // 60}分間の通知をまとめてお送りします",
            fields=batch_summary,
            level="info",
        )

        if success:
            self.logger.info(f"✅ バッチ通知送信完了: {len(self.notification_queue)}件")
            self.notification_queue.clear()
            self.last_batch_time = time.time()
            self._increment_rate_counter()
        else:
            self.logger.error("❌ バッチ通知送信失敗")

        return success

    def _generate_batch_summary(self) -> List[Dict[str, Any]]:
        """バッチサマリー生成"""
        if not self.notification_queue:
            return []

        # レベル別集計
        level_counts = {}
        recent_items = []

        for item in self.notification_queue:
            level = item["level"]
            level_counts[level] = level_counts.get(level, 0) + item.get("count", 1)

            # 最新3件を表示用に保存
            if len(recent_items) < 3:
                recent_items.append(item)

        # サマリーフィールド作成
        fields = []

        # 統計情報
        stats_text = []
        for level, count in level_counts.items():
            emoji = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️"}.get(level, "📝")
            stats_text.append(f"{emoji} {level.upper()}: {count}件")

        fields.append({
            "name": "📈 統計",
            "value": "\n".join(stats_text),
            "inline": True
        })

        # 最新の通知
        if recent_items:
            recent_text = []
            for item in recent_items[:3]:
                title = item["data"].get("title", "通知")[:30]
                count_text = f" (×{item['count']})" if item.get("count", 1) > 1 else ""
                recent_text.append(f"• {title}{count_text}")

            fields.append({
                "name": "📋 最新の通知",
                "value": "\n".join(recent_text),
                "inline": True
            })

        return fields

    def _check_rate_limit(self) -> bool:
        """レート制限チェック"""
        current_time = time.time()

        # 1時間経過でカウンターリセット
        if current_time - self.hour_start_time >= 3600:
            self.hourly_count = 0
            self.hour_start_time = current_time

        return self.hourly_count < self.max_per_hour

    def _increment_rate_counter(self):
        """レート制限カウンター増加"""
        self.hourly_count += 1

    def get_status(self) -> Dict[str, Any]:
        """バッチャー状態取得"""
        return {
            "queue_size": len(self.notification_queue),
            "last_batch_ago": time.time() - self.last_batch_time,
            "next_batch_in": self.batch_interval - (time.time() - self.last_batch_time),
            "hourly_count": self.hourly_count,
            "rate_limit_remaining": self.max_per_hour - self.hourly_count,
        }


class DailySummaryCollector:
    """
    日次サマリー収集・送信

    機能:
    - 日次統計の収集
    - 定時サマリー送信
    - パフォーマンス指標の集約
    """

    def __init__(self, discord_client: DiscordClient):
        """
        サマリーコレクター初期化

        Args:
            discord_client: Discord送信クライアント
        """
        self.client = discord_client
        self.logger = logging.getLogger("crypto_bot.daily_summary")

        # 日次データ
        self.daily_data = {
            "start_time": time.time(),
            "notifications": [],
            "system_events": [],
            "performance_metrics": {},
        }

        # 設定
        self.summary_hour = get_monitoring_config("discord.daily_summary_hour", 18)
        self.logger.info(f"✅ 日次サマリー初期化完了: 送信時刻={self.summary_hour}:00 JST")

    def add_daily_event(self, event_data: Dict[str, Any]):
        """日次イベント追加"""
        event_data["timestamp"] = time.time()
        self.daily_data["notifications"].append(event_data)

    def should_send_daily_summary(self) -> bool:
        """日次サマリー送信タイミング判定"""
        from datetime import datetime, timedelta, timezone

        # JST時刻取得
        jst = timezone(timedelta(hours=9))
        now_jst = datetime.now(jst)

        # 指定時刻（例: 18:00）の判定
        target_time = now_jst.replace(hour=self.summary_hour, minute=0, second=0, microsecond=0)

        # 1時間以内かつまだ送信していない場合
        time_diff = abs((now_jst - target_time).total_seconds())
        return time_diff <= 3600  # 1時間以内

    def generate_daily_summary(self) -> Dict[str, Any]:
        """日次サマリー生成"""
        # 統計計算
        total_notifications = len(self.daily_data["notifications"])
        uptime_hours = (time.time() - self.daily_data["start_time"]) / 3600

        # サマリーデータ
        summary = {
            "title": "📊 日次システムサマリー",
            "description": f"本日（{uptime_hours:.1f}時間）の活動報告",
            "fields": [
                {
                    "name": "📈 通知統計",
                    "value": f"総通知数: {total_notifications}件",
                    "inline": True
                },
                {
                    "name": "⏱️ 稼働時間",
                    "value": f"{uptime_hours:.1f}時間",
                    "inline": True
                }
            ]
        }

        return summary


class EnhancedDiscordManager(DiscordManager):
    """
    拡張Discord通知マネージャー

    既存のDiscordManagerを拡張し、バッチ処理と日次サマリー機能を追加。
    後方互換性を完全に維持しながら新機能を提供。
    """

    def __init__(self, webhook_url: Optional[str] = None):
        """
        拡張マネージャー初期化

        Args:
            webhook_url: Discord WebhookのURL
        """
        # 親クラス初期化
        super().__init__(webhook_url)

        # バッチ処理機能
        if get_monitoring_config("discord.batch_notifications", False):
            self.batcher = NotificationBatcher(self.client)
            self.daily_summary = DailySummaryCollector(self.client)
            self.batch_enabled = True
            self.logger.info("✅ バッチ処理機能が有効化されました")
        else:
            self.batcher = None
            self.daily_summary = None
            self.batch_enabled = False
            self.logger.info("ℹ️ バッチ処理機能は無効です（従来モード）")

    def send_simple_message(self, message: str, level: str = "info") -> bool:
        """
        拡張版シンプルメッセージ送信

        Args:
            message: 送信メッセージ
            level: 重要度

        Returns:
            送信成功・失敗
        """
        # バッチ処理が有効の場合
        if self.batch_enabled and self.batcher:
            notification_data = {
                "title": f"{level.upper()} 通知",
                "description": message,
            }
            return self.batcher.add_notification(notification_data, level)

        # 従来処理（後方互換）
        return super().send_simple_message(message, level)

    def send_trading_signal(self, signal_data: Dict[str, Any]) -> bool:
        """拡張版取引シグナル通知"""
        if self.batch_enabled and self.batcher:
            embed_data = self.formatter.format_trading_signal(signal_data)
            return self.batcher.add_notification(embed_data, "warning")

        return super().send_trading_signal(signal_data)

    def send_system_status(self, status_data: Dict[str, Any]) -> bool:
        """拡張版システム状態通知"""
        if self.batch_enabled and self.batcher:
            embed_data = self.formatter.format_system_status(status_data)
            level = {"healthy": "info", "warning": "warning", "error": "critical"}.get(
                status_data.get("status", "warning"), "warning"
            )
            return self.batcher.add_notification(embed_data, level)

        return super().send_system_status(status_data)

    def process_pending_notifications(self):
        """保留中通知の処理（定期実行用）"""
        if not self.batch_enabled:
            return

        # バッチ処理
        if self.batcher:
            self.batcher.process_batch()

        # 日次サマリー
        if self.daily_summary and self.daily_summary.should_send_daily_summary():
            summary = self.daily_summary.generate_daily_summary()
            self.client.send_embed(
                title=summary["title"],
                description=summary["description"],
                fields=summary.get("fields", []),
                level="info"
            )

    def get_enhanced_status(self) -> Dict[str, Any]:
        """拡張状態情報取得"""
        status = super().get_status()

        if self.batch_enabled:
            status["batch_enabled"] = True
            if self.batcher:
                status["batcher"] = self.batcher.get_status()
        else:
            status["batch_enabled"] = False

        return status


# 後方互換性のためのエイリアス（必要に応じて）
__all__ = [
    "DiscordClient",
    "DiscordFormatter",
    "DiscordManager",
    "NotificationBatcher",
    "DailySummaryCollector",
    "EnhancedDiscordManager",
]

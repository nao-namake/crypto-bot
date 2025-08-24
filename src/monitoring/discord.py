"""
Discord通知システム - 3階層通知でシンプル化

レガシーシステムの複雑なDiscord通知を整理し、
Critical/Warning/Infoの3階層で効率的な通知を実現。.
"""

import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import requests

from ..core.config import get_config
from ..core.exceptions import CryptoBotError, ErrorSeverity, NotificationError
from ..core.logger import get_logger


class NotificationLevel(Enum):
    """通知レベル定義."""

    INFO = "info"  # 情報通知（青色）
    WARNING = "warning"  # 警告通知（黄色）
    CRITICAL = "critical"  # 緊急通知（赤色）


class DiscordNotifier:
    """
    Discord通知システム

    レガシーシステムの複雑な通知設定を整理し、
    重要度に応じた3階層通知を実現.
    """

    # Discord埋め込み色設定
    COLORS = {
        NotificationLevel.INFO: 0x3498DB,  # 青色
        NotificationLevel.WARNING: 0xF39C12,  # 黄色
        NotificationLevel.CRITICAL: 0xE74C3C,  # 赤色
    }

    # 絵文字設定
    EMOJIS = {
        NotificationLevel.INFO: "ℹ️",
        NotificationLevel.WARNING: "⚠️",
        NotificationLevel.CRITICAL: "🚨",
    }

    def __init__(self, webhook_url: Optional[str] = None):
        """
        Discord通知システムを初期化

        Args:
            webhook_url: Discord WebhookのURL（環境変数から取得も可能）.
        """
        self.logger = get_logger("discord")
        
        # 強化された環境変数取得（Cloud Run Secret Manager対応）
        env_webhook = os.getenv("DISCORD_WEBHOOK_URL")
        self.webhook_url = webhook_url or env_webhook
        
        # 詳細デバッグ情報をloggerで出力（Cloud Run対応・401エラー解決用）
        self.logger.info(f"🔍 Discord初期化デバッグ: webhook_url引数={webhook_url is not None}")
        self.logger.info(f"🔍 環境変数チェック: DISCORD_WEBHOOK_URL={env_webhook is not None}")
        
        # 環境変数の全リスト確認（Discord関連のみ）
        discord_env_vars = {k: v for k, v in os.environ.items() if 'DISCORD' in k.upper()}
        self.logger.info(f"🔍 Discord関連環境変数: {list(discord_env_vars.keys())}")
        
        if env_webhook:
            # URL形式の基本検証
            cleaned_url = env_webhook.strip()
            if cleaned_url != env_webhook:
                self.logger.warning(f"⚠️ URL前後に空白文字検出・自動除去: '{env_webhook}' -> '{cleaned_url}'")
                self.webhook_url = cleaned_url
                
            self.logger.info(f"🔗 環境変数URL長: {len(self.webhook_url)} 文字")
            
            # Discord webhook URL形式の検証
            if not self.webhook_url.startswith('https://discord.com/api/webhooks/'):
                self.logger.error(f"❌ 不正なwebhook URL形式: {self.webhook_url[:50]}...")
            else:
                self.logger.info("✅ Discord webhook URL形式確認済み")
                
            # URLの構造確認（401エラー解決用）
            url_parts = self.webhook_url.split('/')
            if len(url_parts) >= 7:
                webhook_id = url_parts[-2] if len(url_parts) > 6 else "不明"
                webhook_token_present = len(url_parts[-1]) > 10 if len(url_parts) > 6 else False
                self.logger.info(f"🔗 Webhook ID: {webhook_id[:8]}...")
                self.logger.info(f"🔗 Token存在: {webhook_token_present}")
            
        else:
            self.logger.error("❌ DISCORD_WEBHOOK_URL環境変数が見つかりません")
        
        if not self.webhook_url:
            self.logger.error("❌ Discord webhook URLが設定されていません。Discord通知は無効です。")
            self.enabled = False
        else:
            self.logger.info(f"✅ Discord通知有効化: URL長={len(self.webhook_url)} 文字")
            self.enabled = True

        # レート制限管理
        self._last_notification_time = {}
        self._min_interval_seconds = 60  # 同じメッセージは60秒間隔

    def _should_send_notification(self, message: str, level: NotificationLevel) -> bool:
        """
        レート制限チェック

        同じメッセージの連続送信を防ぐ.
        """
        now = datetime.now()
        key = f"{level.value}_{hash(message)}"

        if key in self._last_notification_time:
            time_diff = (now - self._last_notification_time[key]).total_seconds()
            if time_diff < self._min_interval_seconds:
                return False

        self._last_notification_time[key] = now
        return True

    def _create_embed(
        self,
        title: str,
        message: str,
        level: NotificationLevel,
        fields: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Discord埋め込みメッセージを作成

        Args:
            title: タイトル
            message: メッセージ本文
            level: 通知レベル
            fields: 追加フィールド

        Returns:
            Discord埋め込み辞書.
        """
        # 日本時間での時刻表示
        jst_time = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S JST")

        embed = {
            "title": f"{self.EMOJIS[level]} {title}",
            "description": message,
            "color": self.COLORS[level],
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "footer": {"text": f"Crypto-Bot • {jst_time}"},
        }

        # 追加フィールド
        if fields:
            embed["fields"] = fields

        return embed

    def _send_webhook(self, embeds: List[Dict[str, Any]]) -> bool:
        """
        Discord Webhookにメッセージを送信

        Args:
            embeds: 送信する埋め込みリスト

        Returns:
            送信成功の可否.
        """
        if not self.enabled:
            return False

        payload = {
            "embeds": embeds,
            "username": "Crypto-Bot",
            "avatar_url": None,  # アバターURL（必要に応じて設定）
        }

        try:
            # 送信前の詳細デバッグ（401エラー解決強化版）
            self.logger.info(f"🚀 Discord送信開始: URL長={len(self.webhook_url)}, タイムアウト=10秒")
            self.logger.info(f"📤 送信ペイロード: {len(embeds)}個の埋め込み")
            
            # URL構造の最終確認（401エラー解決用）
            url_parts = self.webhook_url.split('/')
            if len(url_parts) >= 7:
                self.logger.info(f"🔗 URL構造: .../{url_parts[-3]}/{url_parts[-2][:8]}.../[TOKEN]")
            
            # リクエストヘッダー設定（401エラー対策）
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'Crypto-Bot/1.0'
            }
            
            self.logger.info(f"📡 リクエストヘッダー: {headers}")
            
            response = requests.post(
                self.webhook_url, 
                json=payload, 
                headers=headers,
                timeout=10
            )
            
            # 応答の詳細ログ出力（401エラー解決用）
            self.logger.info(f"📡 Discord応答: status={response.status_code}")
            self.logger.info(f"📡 応答ヘッダー: {dict(response.headers)}")

            if response.status_code in [200, 204]:
                self.logger.info("✅ Discord通知送信成功")
                return True
            elif response.status_code == 401:
                # 401エラーの詳細解析
                self.logger.error("🚨 Discord 401 Unauthorized エラー - Webhook認証失敗")
                self.logger.error(f"🔍 応答内容: {response.text}")
                
                # URL形式の再確認
                if not self.webhook_url.startswith('https://discord.com/api/webhooks/'):
                    self.logger.error("❌ 無効なWebhook URL形式")
                elif len(url_parts) < 7:
                    self.logger.error("❌ Webhook URLにトークンが不足")
                else:
                    self.logger.error("❌ Webhook IDまたはトークンが無効")
                
                self.logger.error("💡 解決方法: Discord側でWebhook URLを再生成してください")
                return False
            else:
                self.logger.error(f"❌ Discord通知送信失敗: {response.status_code} - {response.text}")
                self.logger.error(f"🔍 応答詳細: {response.text[:500]}")
                return False

        except requests.exceptions.Timeout:
            self.logger.error("⏰ Discord通知送信タイムアウト（10秒）")
            return False
        except requests.exceptions.ConnectionError:
            self.logger.error("🌐 Discord通知送信接続エラー - ネットワーク確認必要")
            return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"🚨 Discord通知送信例外エラー: {type(e).__name__}: {e}")
            return False

    def send_notification(
        self,
        message: str,
        severity: str = ErrorSeverity.MEDIUM,
        title: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        error: Optional[Exception] = None,
    ) -> bool:
        """
        通知を送信

        Args:
            message: メッセージ本文
            severity: エラー重要度
            title: タイトル（自動生成も可能）
            extra_data: 追加データ
            error: 例外オブジェクト

        Returns:
            送信成功の可否.
        """
        # 重要度を通知レベルにマッピング
        level_map = {
            ErrorSeverity.LOW: NotificationLevel.INFO,
            ErrorSeverity.MEDIUM: NotificationLevel.WARNING,
            ErrorSeverity.HIGH: NotificationLevel.WARNING,
            ErrorSeverity.CRITICAL: NotificationLevel.CRITICAL,
        }

        level = level_map.get(severity, NotificationLevel.WARNING)

        # レート制限チェック
        if not self._should_send_notification(message, level):
            return False

        # タイトル自動生成
        if not title:
            title_map = {
                NotificationLevel.INFO: "システム情報",
                NotificationLevel.WARNING: "警告",
                NotificationLevel.CRITICAL: "緊急アラート",
            }
            title = title_map[level]

        # 追加フィールド作成
        fields = []

        # エラー情報
        if error:
            if isinstance(error, CryptoBotError):
                error_info = error.to_dict()
                fields.append(
                    {
                        "name": "エラー詳細",
                        "value": f"種別: {error_info['error_type']}\\nコード: {error_info.get('error_code', 'N/A')}",
                        "inline": True,
                    }
                )
            else:
                fields.append(
                    {
                        "name": "エラー詳細",
                        "value": f"種別: {type(error).__name__}\\n内容: {str(error)}",
                        "inline": True,
                    }
                )

        # 追加データ
        if extra_data:
            # 重要なデータのみ表示
            important_keys = [
                "symbol",
                "amount",
                "price",
                "confidence",
                "strategy",
                "pnl",
            ]
            for key in important_keys:
                if key in extra_data:
                    fields.append(
                        {
                            "name": key.capitalize(),
                            "value": str(extra_data[key]),
                            "inline": True,
                        }
                    )

        # 埋め込み作成
        embed = self._create_embed(title, message, level, fields)

        # 送信
        return self._send_webhook([embed])

    def send_trade_notification(
        self,
        action: str,
        symbol: str,
        amount: float,
        price: float,
        success: bool = True,
        order_id: Optional[str] = None,
    ) -> bool:
        """
        取引通知を送信

        Args:
            action: 取引アクション（buy/sell）
            symbol: 通貨ペア
            amount: 取引量
            price: 価格
            success: 成功/失敗
            order_id: 注文ID

        Returns:
            送信成功の可否.
        """
        if success:
            title = "取引実行完了"
            level = NotificationLevel.INFO
            message = f"✅ {action.upper()} {symbol} {amount}@{price:,.0f}"
        else:
            title = "取引実行失敗"
            level = NotificationLevel.WARNING
            message = f"❌ {action.upper()} {symbol} {amount}@{price:,.0f}"

        fields = [
            {"name": "通貨ペア", "value": symbol, "inline": True},
            {"name": "アクション", "value": action.upper(), "inline": True},
            {"name": "数量", "value": f"{amount}", "inline": True},
            {"name": "価格", "value": f"{price:,.0f} JPY", "inline": True},
        ]

        if order_id:
            fields.append({"name": "注文ID", "value": order_id, "inline": True})

        embed = self._create_embed(title, message, level, fields)
        return self._send_webhook([embed])

    def send_performance_notification(
        self,
        total_pnl: float,
        win_rate: float,
        trade_count: int,
        max_drawdown: float,
    ) -> bool:
        """
        パフォーマンス通知を送信

        Args:
            total_pnl: 総損益
            win_rate: 勝率
            trade_count: 取引数
            max_drawdown: 最大ドローダウン

        Returns:
            送信成功の可否.
        """
        # 損益に応じて通知レベル決定
        if total_pnl >= 0:
            level = NotificationLevel.INFO
            title = "📈 パフォーマンスレポート"
            pnl_emoji = "💰" if total_pnl > 1000 else "📊"
        else:
            level = NotificationLevel.WARNING
            title = "📉 パフォーマンスレポート"
            pnl_emoji = "📉"

        message = f"{pnl_emoji} 損益: {total_pnl:+,.0f} JPY | 勝率: {win_rate:.1%}"

        fields = [
            {
                "name": "総損益",
                "value": f"{total_pnl:+,.0f} JPY",
                "inline": True,
            },
            {"name": "勝率", "value": f"{win_rate:.1%}", "inline": True},
            {"name": "取引数", "value": f"{trade_count}回", "inline": True},
            {"name": "最大DD", "value": f"{max_drawdown:.1%}", "inline": True},
        ]

        embed = self._create_embed(title, message, level, fields)
        return self._send_webhook([embed])

    def send_system_notification(self, message: str, system_status: str = "normal") -> bool:
        """
        システム状態通知を送信

        Args:
            message: システムメッセージ
            system_status: システム状態（normal/warning/critical）

        Returns:
            送信成功の可否.
        """
        status_map = {
            "normal": NotificationLevel.INFO,
            "warning": NotificationLevel.WARNING,
            "critical": NotificationLevel.CRITICAL,
        }

        level = status_map.get(system_status, NotificationLevel.INFO)
        title = "🔧 システム通知"

        embed = self._create_embed(title, message, level)
        return self._send_webhook([embed])

    def test_connection(self) -> bool:
        """
        Discord接続テスト

        Returns:
            接続成功の可否.
        """
        test_message = "🧪 Discord通知システム接続テスト"
        embed = self._create_embed(
            "接続テスト",
            test_message,
            NotificationLevel.INFO,
            [{"name": "ステータス", "value": "正常", "inline": True}],
        )

        success = self._send_webhook([embed])
        if success:
            print("✅ Discord通知テスト成功")
        else:
            print("❌ Discord通知テスト失敗")

        return success


# グローバルDiscord通知インスタンス
_discord_notifier: Optional[DiscordNotifier] = None


def get_discord_notifier() -> DiscordNotifier:
    """グローバルDiscord通知インスタンスを取得."""
    global _discord_notifier
    if _discord_notifier is None:
        _discord_notifier = DiscordNotifier()
    return _discord_notifier


def setup_discord_notifier(
    webhook_url: Optional[str] = None,
) -> DiscordNotifier:
    """Discord通知システムを初期化."""
    global _discord_notifier
    _discord_notifier = DiscordNotifier(webhook_url)
    return _discord_notifier

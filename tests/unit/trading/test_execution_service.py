"""
ExecutionServiceテスト

Phase 37: 残高不足Graceful Degradation機能のテスト

テスト範囲:
- 証拠金残高チェック機能
- 残高不足時のgraceful degradation
- Discord通知送信
- Container exit(1)回避確認
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.trading import ExecutionService
from src.trading import ExecutionMode, ExecutionResult, OrderStatus, TradeEvaluation


class TestExecutionServiceBalanceCheck:
    """ExecutionService残高チェック機能テスト（Phase 37）"""

    def setup_method(self):
        """各テスト前の初期化"""
        # モックBitbankClientを作成
        self.mock_bitbank_client = AsyncMock()
        self.mock_bitbank_client.fetch_margin_status = AsyncMock()

        # ExecutionService初期化（ライブモード）
        with patch("src.trading.execution_service.DiscordManager") as mock_discord:
            self.mock_discord_notifier = Mock()
            mock_discord.return_value = self.mock_discord_notifier

            self.service = ExecutionService(mode="live", bitbank_client=self.mock_bitbank_client)

        # テスト用TradeEvaluation
        from src.trading import RiskDecision

        self.evaluation = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",
            risk_score=0.1,
            position_size=0.0001,
            stop_loss=14000000.0,
            take_profit=14500000.0,
            confidence_level=0.65,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.03,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
        )

    @pytest.mark.asyncio
    async def test_sufficient_balance_allows_trade(self):
        """残高十分時は取引続行"""
        # モック設定: 残高十分（20,000円）
        self.mock_bitbank_client.fetch_margin_status.return_value = {"available_balance": 20000}

        # 残高チェック実行
        result = await self.service._validate_margin_balance()

        # 検証
        assert result["sufficient"] is True
        assert result["available"] == 20000
        assert result["required"] == 14000.0

    @pytest.mark.asyncio
    async def test_insufficient_balance_graceful_degradation(self):
        """残高不足時のgraceful degradation"""
        # モック設定: 残高不足（5,000円）
        self.mock_bitbank_client.fetch_margin_status.return_value = {"available_balance": 5000}

        # 残高チェック実行
        result = await self.service._validate_margin_balance()

        # 検証
        assert result["sufficient"] is False
        assert result["available"] == 5000
        assert result["required"] == 14000.0

    @pytest.mark.asyncio
    async def test_balance_check_sends_discord_alert(self):
        """残高不足時にDiscord通知送信"""
        # モック設定: 残高不足
        self.mock_bitbank_client.fetch_margin_status.return_value = {"available_balance": 5000}

        # 残高チェック実行
        await self.service._validate_margin_balance()

        # Discord通知送信確認
        self.mock_discord_notifier.send_error_notification.assert_called_once()
        call_args = self.mock_discord_notifier.send_error_notification.call_args[0][0]

        assert call_args["error_type"] == "INSUFFICIENT_MARGIN_BALANCE"
        assert "証拠金不足検出" in call_args["message"]
        assert "5000円" in call_args["details"]
        assert "14000円" in call_args["details"]

    @pytest.mark.asyncio
    async def test_execute_trade_skips_when_insufficient_balance(self):
        """execute_trade()が残高不足時に取引スキップ（Container exit回避）"""
        # モック設定: 残高不足
        self.mock_bitbank_client.fetch_margin_status.return_value = {"available_balance": 5000}

        # 取引実行試行
        result = await self.service.execute_trade(self.evaluation)

        # 検証: ExecutionResultが返却される（exit(1)せず）
        assert isinstance(result, ExecutionResult)
        assert result.success is False
        assert result.status == OrderStatus.REJECTED
        assert "証拠金不足" in result.error_message
        assert "5000円" in result.error_message
        assert result.order_id is None

    @pytest.mark.asyncio
    async def test_paper_mode_skips_balance_check(self):
        """ペーパーモードでは残高チェックをスキップ"""
        # ペーパーモードのExecutionService
        paper_service = ExecutionService(mode="paper", bitbank_client=None)

        # 残高チェック実行
        result = await paper_service._validate_margin_balance()

        # 検証: チェックスキップ（sufficient=True）
        assert result["sufficient"] is True
        assert result["available"] == 0
        assert result["required"] == 0

    @pytest.mark.asyncio
    async def test_balance_check_error_continues_trading(self):
        """残高チェックエラー時は既存動作維持（取引続行）"""
        # モック設定: API エラー発生
        self.mock_bitbank_client.fetch_margin_status.side_effect = Exception("API エラー")

        # 残高チェック実行
        result = await self.service._validate_margin_balance()

        # 検証: エラー時は取引続行（sufficient=True）
        assert result["sufficient"] is True

    @pytest.mark.asyncio
    async def test_balance_alert_disabled_skips_check(self):
        """balance_alert.enabled=falseでチェックスキップ"""
        # モック設定: 設定無効化
        with patch("src.trading.execution_service.get_threshold") as mock_threshold:
            mock_threshold.return_value = False  # balance_alert.enabled=false

            # 残高チェック実行
            result = await self.service._validate_margin_balance()

            # 検証: チェックスキップ
            assert result["sufficient"] is True

    @pytest.mark.asyncio
    async def test_discord_notifier_none_skips_alert(self):
        """discord_notifier=Noneの場合、通知スキップ"""
        # Discord通知を無効化
        self.service.discord_notifier = None

        # Discord通知送信試行
        await self.service._send_balance_alert(available=5000, required=14000)

        # エラーが発生しないことを確認（正常終了）
        # 通知は送信されない


class TestExecutionServiceInitialization:
    """ExecutionService初期化テスト（Phase 37）"""

    @patch("src.trading.execution_service.DiscordManager")
    def test_live_mode_initializes_discord_manager(self, mock_discord):
        """ライブモードでDiscordManager初期化"""
        mock_discord.return_value = Mock()

        service = ExecutionService(mode="live", bitbank_client=Mock())

        # 検証
        assert service.discord_notifier is not None
        mock_discord.assert_called_once()

    def test_paper_mode_skips_discord_manager(self):
        """ペーパーモードではDiscordManager初期化スキップ"""
        service = ExecutionService(mode="paper", bitbank_client=None)

        # 検証
        assert service.discord_notifier is None

    @patch("src.trading.execution_service.DiscordManager")
    def test_discord_manager_initialization_error_continues(self, mock_discord):
        """DiscordManager初期化エラー時も起動継続"""
        # Discord初期化エラー
        mock_discord.side_effect = Exception("Discord初期化失敗")

        # ExecutionService初期化（エラーが発生しないことを確認）
        service = ExecutionService(mode="live", bitbank_client=Mock())

        # 検証: discord_notifierはNoneだが、サービスは正常起動
        assert service.discord_notifier is None

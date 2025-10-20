"""
ExecutionService (executor.py) 包括的テストスイート

Phase 38対応 - 依存注入パターン完全テスト
目標: 85%+カバレッジ達成

テスト範囲:
1. inject_services() - 依存注入機能
2. execute_trade() - メイン実行ロジック（成功・失敗・バリデーション）
3. Paper/Live/Backtest モード分岐
4. 注文作成・確認・エラーハンドリング
5. TP/SL注文配置連携（StopManager統合）
6. 指値/成行注文分岐（OrderStrategy統合）
7. BalanceMonitor統合
8. PositionLimits統合
9. レート制限・cooldown処理
10. 取引履歴・統計管理
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.trading import (
    ExecutionMode,
    ExecutionResult,
    ExecutionService,
    OrderStatus,
    RiskDecision,
    TradeEvaluation,
)


@pytest.fixture
def mock_bitbank_client():
    """BitbankClientモック"""
    client = AsyncMock()
    client.fetch_ticker = AsyncMock(return_value={"last": 14000000.0})
    client.create_order = MagicMock(
        return_value={
            "id": "order_123",
            "price": 14000000.0,
            "amount": 0.0001,
            "filled_price": 14000000.0,
            "filled_amount": 0.0001,
            "fee": 168.0,
        }
    )
    return client


@pytest.fixture
def sample_evaluation():
    """サンプルTradeEvaluation"""
    return TradeEvaluation(
        decision=RiskDecision.APPROVED,
        side="buy",
        risk_score=0.1,
        position_size=0.0001,
        stop_loss=13500000.0,
        take_profit=14500000.0,
        confidence_level=0.65,
        warnings=[],
        denial_reasons=[],
        evaluation_timestamp=datetime.now(),
        kelly_recommendation=0.03,
        drawdown_status="normal",
        anomaly_alerts=[],
        market_conditions={},
        entry_price=14000000.0,
    )


@pytest.fixture
def hold_evaluation():
    """holdシグナル用TradeEvaluation"""
    return TradeEvaluation(
        decision=RiskDecision.APPROVED,  # holdの場合でもdecisionはAPPROVED
        side="hold",
        risk_score=0.0,
        position_size=0.0,
        stop_loss=None,
        take_profit=None,
        confidence_level=0.0,
        warnings=[],
        denial_reasons=[],
        evaluation_timestamp=datetime.now(),
        kelly_recommendation=0.0,
        drawdown_status="normal",
        anomaly_alerts=[],
        market_conditions={},
    )


class TestExecutionServiceInjection:
    """依存注入機能テスト（Phase 38新機能）"""

    @patch("src.trading.execution.executor.DiscordManager")
    def test_inject_order_strategy(self, mock_discord):
        """OrderStrategy注入テスト"""
        service = ExecutionService(mode="live", bitbank_client=Mock())
        mock_strategy = Mock()

        # 注入前
        assert service.order_strategy is None

        # 注入
        service.inject_services(order_strategy=mock_strategy)

        # 検証
        assert service.order_strategy is mock_strategy

    @patch("src.trading.execution.executor.DiscordManager")
    def test_inject_stop_manager(self, mock_discord):
        """StopManager注入テスト"""
        service = ExecutionService(mode="live", bitbank_client=Mock())
        mock_stop_manager = Mock()

        service.inject_services(stop_manager=mock_stop_manager)

        assert service.stop_manager is mock_stop_manager

    @patch("src.trading.execution.executor.DiscordManager")
    def test_inject_position_limits(self, mock_discord):
        """PositionLimits注入テスト"""
        service = ExecutionService(mode="live", bitbank_client=Mock())
        mock_position_limits = Mock()

        service.inject_services(position_limits=mock_position_limits)

        assert service.position_limits is mock_position_limits

    @patch("src.trading.execution.executor.DiscordManager")
    def test_inject_balance_monitor(self, mock_discord):
        """BalanceMonitor注入テスト"""
        service = ExecutionService(mode="live", bitbank_client=Mock())
        mock_balance_monitor = Mock()

        service.inject_services(balance_monitor=mock_balance_monitor)

        assert service.balance_monitor is mock_balance_monitor

    @patch("src.trading.execution.executor.DiscordManager")
    def test_inject_all_services_at_once(self, mock_discord):
        """全サービス同時注入テスト"""
        service = ExecutionService(mode="live", bitbank_client=Mock())

        mock_order_strategy = Mock()
        mock_stop_manager = Mock()
        mock_position_limits = Mock()
        mock_balance_monitor = Mock()

        service.inject_services(
            order_strategy=mock_order_strategy,
            stop_manager=mock_stop_manager,
            position_limits=mock_position_limits,
            balance_monitor=mock_balance_monitor,
        )

        assert service.order_strategy is mock_order_strategy
        assert service.stop_manager is mock_stop_manager
        assert service.position_limits is mock_position_limits
        assert service.balance_monitor is mock_balance_monitor

    def test_inject_services_with_none_values(self):
        """Noneを渡しても既存の値を維持"""
        service = ExecutionService(mode="paper")
        existing_strategy = Mock()
        service.order_strategy = existing_strategy

        # Noneを渡しても上書きされない
        service.inject_services(order_strategy=None)

        assert service.order_strategy is existing_strategy


class TestExecuteTradeHoldSignal:
    """holdシグナル処理テスト"""

    @pytest.mark.asyncio
    async def test_hold_signal_skips_trade(self, hold_evaluation):
        """holdシグナルは取引スキップ"""
        service = ExecutionService(mode="paper")
        result = await service.execute_trade(hold_evaluation)

        assert result.success is True
        assert result.order_id is None
        assert result.price == 0.0
        assert result.amount == 0.0
        assert result.status == OrderStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_hold_signal_different_variations(self):
        """hold/none/空文字列のバリエーションテスト"""
        service = ExecutionService(mode="paper")

        for side_value in ["hold", "HOLD", "none", "NONE", ""]:
            eval_obj = TradeEvaluation(
                decision=RiskDecision.APPROVED,  # holdの場合でもdecisionはAPPROVED
                side=side_value,
                risk_score=0.0,
                position_size=0.0,
                stop_loss=None,
                take_profit=None,
                confidence_level=0.0,
                warnings=[],
                denial_reasons=[],
                evaluation_timestamp=datetime.now(),
                kelly_recommendation=0.0,
                drawdown_status="normal",
                anomaly_alerts=[],
                market_conditions={},
            )

            result = await service.execute_trade(eval_obj)

            assert result.success is True
            assert result.status == OrderStatus.CANCELLED


class TestExecuteTradeBalanceMonitor:
    """BalanceMonitor統合テスト"""

    @pytest.mark.asyncio
    @patch("src.trading.execution.executor.DiscordManager")
    async def test_balance_monitor_sufficient_balance(
        self, mock_discord, sample_evaluation, mock_bitbank_client
    ):
        """残高十分時は取引実行"""
        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)

        # BalanceMonitor注入（残高十分）
        mock_balance_monitor = AsyncMock()
        mock_balance_monitor.validate_margin_balance = AsyncMock(
            return_value={"sufficient": True, "available": 20000, "required": 14000}
        )
        service.inject_services(balance_monitor=mock_balance_monitor)

        result = await service.execute_trade(sample_evaluation)

        # 残高チェックが呼ばれることを確認
        mock_balance_monitor.validate_margin_balance.assert_called_once()
        # 取引が実行されることを確認
        assert result.success is True

    @pytest.mark.asyncio
    @patch("src.trading.execution.executor.DiscordManager")
    async def test_balance_monitor_insufficient_balance(
        self, mock_discord, sample_evaluation, mock_bitbank_client
    ):
        """残高不足時は取引拒否（Container exit回避）"""
        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)

        # BalanceMonitor注入（残高不足）
        mock_balance_monitor = AsyncMock()
        mock_balance_monitor.validate_margin_balance = AsyncMock(
            return_value={"sufficient": False, "available": 5000, "required": 14000}
        )
        service.inject_services(balance_monitor=mock_balance_monitor)

        result = await service.execute_trade(sample_evaluation)

        # 検証: 取引拒否
        assert result.success is False
        assert result.status == OrderStatus.REJECTED
        assert "証拠金不足" in result.error_message
        assert "5000円" in result.error_message
        assert result.order_id is None

    @pytest.mark.asyncio
    async def test_no_balance_monitor_skips_check(self, sample_evaluation, mock_bitbank_client):
        """BalanceMonitorなしでは残高チェックスキップ"""
        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)
        # balance_monitor注入なし

        result = await service.execute_trade(sample_evaluation)

        # エラーなく実行される
        assert result.success is True


class TestExecuteTradePositionLimits:
    """PositionLimits統合テスト"""

    @pytest.mark.asyncio
    @patch("src.trading.execution.executor.DiscordManager")
    async def test_position_limits_allowed(
        self, mock_discord, sample_evaluation, mock_bitbank_client
    ):
        """ポジション制限内なら取引実行"""
        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)

        # PositionLimits注入（許可）
        mock_position_limits = AsyncMock()
        mock_position_limits.check_limits = AsyncMock(
            return_value={"allowed": True, "reason": "OK"}
        )
        service.inject_services(position_limits=mock_position_limits)

        result = await service.execute_trade(sample_evaluation)

        # 制限チェックが呼ばれることを確認
        mock_position_limits.check_limits.assert_called_once()
        # 取引実行
        assert result.success is True

    @pytest.mark.asyncio
    @patch("src.trading.execution.executor.DiscordManager")
    async def test_position_limits_rejected(
        self, mock_discord, sample_evaluation, mock_bitbank_client
    ):
        """ポジション制限超過時は取引拒否"""
        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)

        # PositionLimits注入（拒否）
        mock_position_limits = AsyncMock()
        mock_position_limits.check_limits = AsyncMock(
            return_value={"allowed": False, "reason": "最大ポジション数超過"}
        )
        service.inject_services(position_limits=mock_position_limits)

        result = await service.execute_trade(sample_evaluation)

        # 検証: 取引拒否
        assert result.success is False
        assert result.status == OrderStatus.REJECTED
        assert "最大ポジション数超過" in result.error_message

    @pytest.mark.asyncio
    async def test_no_position_limits_skips_check(self, sample_evaluation, mock_bitbank_client):
        """PositionLimitsなしでは制限チェックスキップ"""
        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)
        # position_limits注入なし

        result = await service.execute_trade(sample_evaluation)

        # エラーなく実行される
        assert result.success is True


class TestExecuteTradeLiveMode:
    """ライブトレード実行テスト"""

    @pytest.mark.asyncio
    @patch("src.trading.execution.executor.DiscordManager")
    async def test_live_trade_success_market_order(
        self, mock_discord, sample_evaluation, mock_bitbank_client
    ):
        """ライブ成行注文成功テスト"""
        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)

        result = await service.execute_trade(sample_evaluation)

        # 検証
        assert result.success is True
        assert result.mode == ExecutionMode.LIVE
        assert result.order_id == "order_123"
        assert result.status == OrderStatus.FILLED
        assert service.executed_trades == 1
        assert service.last_order_time is not None

    @pytest.mark.asyncio
    @patch("src.trading.execution.executor.DiscordManager")
    @patch("src.trading.execution.executor.get_threshold")
    async def test_live_trade_with_order_strategy_limit(
        self, mock_threshold, mock_discord, sample_evaluation, mock_bitbank_client
    ):
        """OrderStrategy経由の指値注文テスト"""
        mock_threshold.return_value = "BTC/JPY"
        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)

        # OrderStrategy注入（指値注文設定）
        mock_order_strategy = AsyncMock()
        mock_order_strategy.get_optimal_execution_config = AsyncMock(
            return_value={
                "order_type": "limit",
                "price": 13950000.0,
                "strategy": "limit_maker",
            }
        )
        service.inject_services(order_strategy=mock_order_strategy)

        # 指値注文レスポンス設定
        mock_bitbank_client.create_order.return_value = {
            "id": "limit_order_456",
            "price": 13950000.0,
            "amount": 0.0001,
            "filled_price": None,
            "filled_amount": None,
            "fee": 0,
        }

        result = await service.execute_trade(sample_evaluation)

        # 検証
        assert result.success is True
        assert result.status == OrderStatus.SUBMITTED  # 指値はSUBMITTED
        assert result.order_id == "limit_order_456"
        mock_order_strategy.get_optimal_execution_config.assert_called_once()

    # Phase 43.5: test_live_trade_with_stop_manager削除（place_tp_sl_orders廃止のため）

    @pytest.mark.asyncio
    async def test_live_trade_no_bitbank_client_error(self, sample_evaluation):
        """BitbankClientなしでライブトレード実行時エラー"""
        service = ExecutionService(mode="live", bitbank_client=None)

        result = await service.execute_trade(sample_evaluation)

        # エラー結果確認
        assert result.success is False
        assert result.status == OrderStatus.FAILED
        assert "BitbankClient" in result.error_message

    @pytest.mark.asyncio
    @patch("src.trading.execution.executor.DiscordManager")
    async def test_live_trade_error_50061_balance_insufficient(
        self, mock_discord, sample_evaluation, mock_bitbank_client
    ):
        """エラー50061（残高不足）の明示的検出"""
        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)

        # エラー50061発生
        mock_bitbank_client.create_order.side_effect = Exception(
            "API Error 50061: 新規注文に必要な利用可能証拠金が不足しています"
        )

        result = await service.execute_trade(sample_evaluation)

        # エラー検出確認
        assert result.success is False
        assert result.status == OrderStatus.FAILED
        assert "50061" in result.error_message


class TestExecuteTradePaperMode:
    """ペーパートレード実行テスト"""

    @pytest.mark.asyncio
    async def test_paper_trade_success(self, sample_evaluation, mock_bitbank_client):
        """ペーパートレード成功テスト"""
        service = ExecutionService(mode="paper", bitbank_client=mock_bitbank_client)

        result = await service.execute_trade(sample_evaluation)

        # 検証
        assert result.success is True
        assert result.mode == ExecutionMode.PAPER
        assert result.status == OrderStatus.FILLED
        assert result.order_id.startswith("paper_")
        assert result.price == 14000000.0  # entry_priceから
        assert result.amount == 0.0001
        assert result.fee == 0.0  # ペーパーは手数料なし

    @pytest.mark.asyncio
    async def test_paper_trade_fetches_real_price(self, sample_evaluation):
        """ペーパートレードで実価格取得テスト"""
        # entry_price=0の場合、Bitbank公開APIから価格取得
        eval_no_price = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",
            risk_score=0.1,
            position_size=0.0001,
            stop_loss=13500000.0,
            take_profit=14500000.0,
            confidence_level=0.65,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.03,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
            entry_price=0.0,  # 価格なし
        )

        # AsyncMock with proper return value
        mock_client = MagicMock()
        mock_client.fetch_ticker = MagicMock(return_value={"last": 14000000.0})

        service = ExecutionService(mode="paper", bitbank_client=mock_client)
        result = await service.execute_trade(eval_no_price)

        # Bitbank APIから取得した価格
        assert result.price == 14000000.0
        mock_client.fetch_ticker.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.trading.execution.executor.get_threshold")
    async def test_paper_trade_fallback_price(self, mock_threshold, sample_evaluation):
        """ペーパートレードのフォールバック価格テスト"""
        mock_threshold.return_value = 16500000.0

        # BitbankClientなし
        eval_no_price = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="sell",
            risk_score=0.1,
            position_size=0.0001,
            stop_loss=None,
            take_profit=None,
            confidence_level=0.65,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.03,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
            entry_price=0.0,
        )

        service = ExecutionService(mode="paper", bitbank_client=None)
        result = await service.execute_trade(eval_no_price)

        # フォールバック価格使用
        assert result.price == 16500000.0
        mock_threshold.assert_called()

    @pytest.mark.asyncio
    async def test_paper_trade_position_tracking(self, sample_evaluation, mock_bitbank_client):
        """ペーパートレードのポジション記録テスト"""
        service = ExecutionService(mode="paper", bitbank_client=mock_bitbank_client)

        result = await service.execute_trade(sample_evaluation)

        # ポジション記録確認
        assert len(service.virtual_positions) == 1
        position = service.virtual_positions[0]
        assert position["side"] == "buy"
        assert position["amount"] == 0.0001
        assert position["price"] == 14000000.0
        assert position["take_profit"] == 14500000.0
        assert position["stop_loss"] == 13500000.0

    @pytest.mark.asyncio
    async def test_paper_trade_cooldown_update(self, sample_evaluation, mock_bitbank_client):
        """ペーパートレードでクールダウン時刻更新テスト"""
        service = ExecutionService(mode="paper", bitbank_client=mock_bitbank_client)

        assert service.last_order_time is None

        await service.execute_trade(sample_evaluation)

        # クールダウン時刻更新
        assert service.last_order_time is not None
        assert isinstance(service.last_order_time, datetime)


class TestExecuteTradeBacktestMode:
    """バックテスト実行テスト"""

    @pytest.mark.asyncio
    async def test_backtest_trade_success(self, sample_evaluation):
        """バックテスト成功テスト"""
        service = ExecutionService(mode="backtest")

        result = await service.execute_trade(sample_evaluation)

        # 検証
        assert result.success is True
        assert result.mode == ExecutionMode.PAPER  # バックテストはペーパー扱い
        assert result.status == OrderStatus.FILLED
        assert result.order_id == "backtest_1"
        assert result.price == 14000000.0
        assert result.fee == 0.0

    @pytest.mark.asyncio
    async def test_backtest_multiple_trades(self, sample_evaluation):
        """バックテスト複数取引テスト"""
        service = ExecutionService(mode="backtest")

        # 3回取引実行
        for i in range(3):
            result = await service.execute_trade(sample_evaluation)
            assert result.order_id == f"backtest_{i + 1}"

        assert service.executed_trades == 3


class TestMinimumTradeSize:
    """最小ロットサイズ保証テスト"""

    @pytest.mark.asyncio
    @patch("src.trading.execution.executor.get_threshold")
    async def test_minimum_trade_size_enforcement(self, mock_threshold, mock_bitbank_client):
        """最小ロットサイズ保証適用テスト"""
        mock_threshold.side_effect = lambda key, default: {
            "position_management.dynamic_position_sizing.enabled": True,
            "position_management.min_trade_size": 0.0001,
            "trading_constraints.currency_pair": "BTC/JPY",
            "trading_constraints.default_order_type": "market",
        }.get(key, default)

        # 最小サイズ未満のevaluation
        small_eval = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",
            risk_score=0.1,
            position_size=0.00005,  # 最小サイズ未満
            stop_loss=13500000.0,
            take_profit=14500000.0,
            confidence_level=0.65,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.01,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
            entry_price=14000000.0,
        )

        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)
        result = await service.execute_trade(small_eval)

        # 最小サイズに調整されることを確認
        assert result.amount == 0.0001

    @pytest.mark.asyncio
    @patch("src.trading.execution.executor.DiscordManager")
    @patch("src.trading.execution.executor.get_threshold")
    async def test_minimum_trade_size_disabled(
        self, mock_threshold, mock_discord, mock_bitbank_client
    ):
        """動的サイジング無効時は最小サイズ保証なし"""
        mock_threshold.side_effect = lambda key, default: {
            "position_management.dynamic_position_sizing.enabled": False,
            "trading_constraints.currency_pair": "BTC/JPY",
            "trading_constraints.default_order_type": "market",
        }.get(key, default)

        small_eval = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",
            risk_score=0.1,
            position_size=0.00005,
            stop_loss=None,
            take_profit=None,
            confidence_level=0.65,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.01,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
            entry_price=14000000.0,
        )

        # Mock create_order to return small amount
        mock_bitbank_client.create_order.return_value = {
            "id": "order_small",
            "price": 14000000.0,
            "amount": 0.00005,
            "filled_price": 14000000.0,
            "filled_amount": 0.00005,
            "fee": 84.0,
        }

        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)
        result = await service.execute_trade(small_eval)

        # 元のサイズのまま
        assert result.amount == 0.00005


class TestTradingStatistics:
    """取引統計管理テスト"""

    def test_get_trading_statistics_paper_mode(self):
        """ペーパーモードの統計取得"""
        service = ExecutionService(mode="paper")
        service.executed_trades = 5
        service.session_pnl = 1000.0
        service.virtual_balance = 11000.0

        stats = service.get_trading_statistics()

        assert stats["mode"] == "paper"
        assert stats["executed_trades"] == 5
        assert stats["session_pnl"] == 1000.0
        assert stats["virtual_positions"] == 0
        assert stats["virtual_balance"] == 11000.0

    @patch("src.trading.execution.executor.DiscordManager")
    def test_get_trading_statistics_live_mode(self, mock_discord):
        """ライブモードの統計取得"""
        service = ExecutionService(mode="live", bitbank_client=Mock())
        service.executed_trades = 10
        service.current_balance = 50000.0

        stats = service.get_trading_statistics()

        assert stats["mode"] == "live"
        assert stats["executed_trades"] == 10
        assert stats["current_balance"] == 50000.0
        assert stats["virtual_positions"] == 0  # ライブモードは0

    def test_update_balance_paper_mode(self):
        """残高更新（ペーパーモード）"""
        service = ExecutionService(mode="paper")

        service.update_balance(15000.0)

        assert service.current_balance == 15000.0
        assert service.virtual_balance == 15000.0

    @patch("src.trading.execution.executor.DiscordManager")
    def test_update_balance_live_mode(self, mock_discord):
        """残高更新（ライブモード）"""
        service = ExecutionService(mode="live", bitbank_client=Mock())

        service.update_balance(100000.0)

        assert service.current_balance == 100000.0
        # ライブモードはvirtual_balanceは初期値のまま

    @pytest.mark.asyncio
    async def test_get_position_summary_paper_mode(self, sample_evaluation, mock_bitbank_client):
        """ポジションサマリー取得（ペーパーモード）"""
        service = ExecutionService(mode="paper", bitbank_client=mock_bitbank_client)

        # 3取引実行
        for _ in range(3):
            await service.execute_trade(sample_evaluation)

        summary = service.get_position_summary()

        assert summary["positions"] == 3
        assert len(summary["latest_trades"]) == 3

    @patch("src.trading.execution.executor.DiscordManager")
    def test_get_position_summary_live_mode(self, mock_discord):
        """ポジションサマリー取得（ライブモード）"""
        service = ExecutionService(mode="live", bitbank_client=Mock())

        summary = service.get_position_summary()

        # ライブモードは0
        assert summary["positions"] == 0
        assert summary["latest_trades"] == []


class TestCheckStopConditions:
    """ストップ条件チェックテスト"""

    @pytest.mark.asyncio
    async def test_check_stop_conditions_with_stop_manager(self):
        """StopManager経由のストップ条件チェック"""
        service = ExecutionService(mode="paper")

        # StopManager注入
        mock_stop_manager = AsyncMock()
        mock_result = ExecutionResult(
            success=True,
            mode=ExecutionMode.PAPER,
            order_id="stop_123",
            side="sell",
            amount=0.0001,
            price=13000000.0,
            status=OrderStatus.FILLED,
        )
        mock_stop_manager.check_stop_conditions = AsyncMock(return_value=mock_result)
        service.inject_services(stop_manager=mock_stop_manager)

        result = await service.check_stop_conditions()

        # StopManager呼び出し確認
        mock_stop_manager.check_stop_conditions.assert_called_once_with(
            service.virtual_positions,
            service.bitbank_client,
            service.mode,
            service.executed_trades,
            service.session_pnl,
        )
        assert result is mock_result

    @pytest.mark.asyncio
    async def test_check_stop_conditions_without_stop_manager(self):
        """StopManagerなしではNone返却"""
        service = ExecutionService(mode="paper")

        result = await service.check_stop_conditions()

        assert result is None


class TestErrorHandling:
    """エラーハンドリングテスト"""

    @pytest.mark.asyncio
    @patch("src.trading.execution.executor.DiscordManager")
    async def test_execute_trade_exception_handling(
        self, mock_discord, sample_evaluation, mock_bitbank_client
    ):
        """execute_trade内部例外の適切なハンドリング"""
        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)

        # 予期せぬ例外発生
        mock_bitbank_client.create_order.side_effect = Exception("予期せぬエラー")

        result = await service.execute_trade(sample_evaluation)

        # エラー結果返却（例外は発生しない）
        assert result.success is False
        assert result.status == OrderStatus.FAILED
        assert "予期せぬエラー" in result.error_message

    @pytest.mark.asyncio
    async def test_paper_trade_exception_handling(self, mock_bitbank_client):
        """ペーパートレード内部例外のハンドリング"""
        service = ExecutionService(mode="paper", bitbank_client=mock_bitbank_client)

        # ticker取得エラー
        mock_bitbank_client.fetch_ticker.side_effect = Exception("Ticker取得失敗")

        eval_no_price = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",
            risk_score=0.1,
            position_size=0.0001,
            stop_loss=None,
            take_profit=None,
            confidence_level=0.65,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.03,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
            entry_price=0.0,
        )

        # フォールバック価格使用で正常実行
        with patch("src.trading.execution.executor.get_threshold") as mock_threshold:
            mock_threshold.return_value = 16500000.0
            result = await service.execute_trade(eval_no_price)

            # フォールバック価格で実行成功
            assert result.success is True
            assert result.price == 16500000.0

    @pytest.mark.asyncio
    async def test_backtest_trade_error_handling(self):
        """バックテストエラーハンドリング"""
        service = ExecutionService(mode="backtest")

        # 不正なevaluation
        invalid_eval = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",
            risk_score=0.1,
            position_size=0.0001,
            stop_loss=None,
            take_profit=None,
            confidence_level=0.65,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.03,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
            entry_price=None,  # None価格
        )

        # AttributeErrorなどをキャッチして適切に処理
        result = await service.execute_trade(invalid_eval)

        # エラー結果確認
        assert result.success is False
        assert result.status == OrderStatus.FAILED


class TestModeSpecificBehavior:
    """モード別動作テスト"""

    @pytest.mark.asyncio
    async def test_live_mode_requires_bitbank_client(self, sample_evaluation):
        """ライブモードはBitbankClient必須"""
        service = ExecutionService(mode="live", bitbank_client=None)

        result = await service.execute_trade(sample_evaluation)

        assert result.success is False
        assert "BitbankClient" in result.error_message

    @pytest.mark.asyncio
    async def test_paper_mode_works_without_bitbank_client(self):
        """ペーパーモードはBitbankClientなしでも動作"""
        service = ExecutionService(mode="paper", bitbank_client=None)

        eval_obj = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",
            risk_score=0.1,
            position_size=0.0001,
            stop_loss=None,
            take_profit=None,
            confidence_level=0.65,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.03,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
            entry_price=14000000.0,
        )

        with patch("src.trading.execution.executor.get_threshold") as mock_threshold:
            mock_threshold.return_value = 16500000.0
            result = await service.execute_trade(eval_obj)

            # 正常実行
            assert result.success is True

    @pytest.mark.asyncio
    async def test_backtest_mode_simple_execution(self):
        """バックテストモードのシンプル実行"""
        service = ExecutionService(mode="backtest")

        eval_obj = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="sell",
            risk_score=0.1,
            position_size=0.0002,
            stop_loss=None,
            take_profit=None,
            confidence_level=0.65,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.03,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
            entry_price=14200000.0,
        )

        result = await service.execute_trade(eval_obj)

        # 簡易実行成功
        assert result.success is True
        assert result.side == "sell"
        assert result.amount == 0.0002
        assert result.price == 14200000.0


class TestInitializationModes:
    """初期化モード別テスト"""

    def test_paper_mode_initialization(self):
        """ペーパーモード初期化テスト"""
        service = ExecutionService(mode="paper")

        assert service.mode == "paper"
        assert service.discord_notifier is None
        assert service.virtual_balance == 10000.0  # デフォルト初期残高

    @patch("src.trading.execution.executor.DiscordManager")
    def test_live_mode_initialization(self, mock_discord):
        """ライブモード初期化テスト"""
        mock_discord.return_value = Mock()

        service = ExecutionService(mode="live", bitbank_client=Mock())

        assert service.mode == "live"
        assert service.discord_notifier is not None
        mock_discord.assert_called_once()

    def test_backtest_mode_initialization(self):
        """バックテストモード初期化テスト"""
        service = ExecutionService(mode="backtest")

        assert service.mode == "backtest"
        assert service.discord_notifier is None

    @patch("src.trading.execution.executor.load_config")
    def test_custom_initial_balance(self, mock_load_config):
        """カスタム初期残高設定テスト"""

        class MockConfig:
            mode_balances = {"paper": {"initial_balance": 50000.0}}

        mock_load_config.return_value = MockConfig()

        service = ExecutionService(mode="paper")

        assert service.virtual_balance == 50000.0


class TestTickerEdgeCases:
    """Ticker取得エッジケーステスト"""

    @pytest.mark.asyncio
    async def test_paper_trade_ticker_without_last(self):
        """ticker返却時にlastキーがない場合"""
        eval_no_price = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",
            risk_score=0.1,
            position_size=0.0001,
            stop_loss=None,
            take_profit=None,
            confidence_level=0.65,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.03,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
            entry_price=0.0,
        )

        # ticker返却するが"last"キーなし
        mock_client = MagicMock()
        mock_client.fetch_ticker = MagicMock(return_value={"bid": 14000000.0})

        with patch("src.trading.execution.executor.get_threshold") as mock_threshold:
            mock_threshold.return_value = 16500000.0
            service = ExecutionService(mode="paper", bitbank_client=mock_client)
            result = await service.execute_trade(eval_no_price)

            # フォールバック価格使用
            assert result.price == 16500000.0


class TestMinimumTradeSizeEdgeCases:
    """最小ロットサイズエッジケーステスト"""

    @pytest.mark.asyncio
    @patch("src.trading.execution.executor.get_threshold")
    async def test_minimum_trade_size_with_dataclass(self, mock_threshold):
        """dataclass型のevaluation調整テスト"""
        mock_threshold.side_effect = lambda key, default: {
            "position_management.dynamic_position_sizing.enabled": True,
            "position_management.min_trade_size": 0.0001,
        }.get(key, default)

        # dataclass形式
        small_eval = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",
            risk_score=0.1,
            position_size=0.00005,
            stop_loss=None,
            take_profit=None,
            confidence_level=0.65,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.01,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
            entry_price=14000000.0,
        )

        service = ExecutionService(mode="backtest")
        result = await service.execute_trade(small_eval)

        # dataclass replaceで調整される
        assert result.amount == 0.0001

    @pytest.mark.asyncio
    @patch("src.trading.execution.executor.get_threshold")
    async def test_minimum_trade_size_error_handling(self, mock_threshold):
        """最小ロット保証処理エラー時のハンドリング"""
        # get_thresholdでエラー発生
        mock_threshold.side_effect = Exception("設定取得エラー")

        eval_obj = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",
            risk_score=0.1,
            position_size=0.00005,
            stop_loss=None,
            take_profit=None,
            confidence_level=0.65,
            warnings=[],
            denial_reasons=[],
            evaluation_timestamp=datetime.now(),
            kelly_recommendation=0.01,
            drawdown_status="normal",
            anomaly_alerts=[],
            market_conditions={},
            entry_price=14000000.0,
        )

        service = ExecutionService(mode="backtest")
        result = await service.execute_trade(eval_obj)

        # エラー時も元のサイズで実行される
        assert result.amount == 0.00005

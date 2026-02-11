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
    async def test_live_trade_success_limit_order(
        self, mock_discord, sample_evaluation, mock_bitbank_client
    ):
        """ライブ指値注文成功テスト（デフォルト指値注文）"""
        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)

        result = await service.execute_trade(sample_evaluation)

        # 検証
        assert result.success is True
        assert result.mode == ExecutionMode.LIVE
        assert result.order_id == "order_123"
        # Phase 57.7: デフォルトで指値注文を使用するためSUBMITTEDステータス
        assert result.status == OrderStatus.SUBMITTED
        assert service.executed_trades == 1
        assert service.last_order_time is not None

    @pytest.mark.asyncio
    @patch("src.trading.execution.executor.DiscordManager")
    @patch("src.trading.execution.executor.get_threshold")
    async def test_live_trade_with_order_strategy_limit(
        self, mock_threshold, mock_discord, sample_evaluation, mock_bitbank_client
    ):
        """OrderStrategy経由の指値注文テスト"""

        # Phase 51.5-C: mock_thresholdを適切な値マップに変更
        def mock_get_threshold(key, default=None):
            threshold_map = {
                "data.symbol": "BTC/JPY",
                "risk.fallback_atr": 500000,
                "risk.require_tpsl_recalculation": False,  # テストではTP/SL再計算を任意に
            }
            return threshold_map.get(key, default)

        mock_threshold.side_effect = mock_get_threshold
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
        # Phase 62.9: Maker戦略モック（無効化）
        mock_order_strategy.get_maker_execution_config = AsyncMock(
            return_value={"use_maker": False, "disable_reason": "test_disabled"}
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
        """バックテスト成功テスト（Phase 62.8: 手数料はreporter.pyで一括計算）"""
        service = ExecutionService(mode="backtest")

        result = await service.execute_trade(sample_evaluation)

        # 検証
        assert result.success is True
        assert result.mode == ExecutionMode.PAPER  # バックテストはペーパー扱い
        assert result.status == OrderStatus.FILLED
        assert result.order_id == "backtest_1"
        assert result.price == 14000000.0
        # Phase 62.8: 手数料はreporter.pyで一括計算（多重計算バグ修正）
        # executor.pyでは手数料控除しない（fee=0）
        assert result.fee == 0

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
        mock_threshold.side_effect = lambda key, default=None: {
            "position_management.dynamic_position_sizing.enabled": True,
            "position_management.min_trade_size": 0.0001,
            "trading_constraints.currency_pair": "BTC/JPY",
            "trading_constraints.default_order_type": "market",
            # Phase 51.6: TP/SL再計算で使用される設定
            "position_management.take_profit.default_ratio": 1.29,
            "position_management.take_profit.min_profit_ratio": 0.009,
            "position_management.stop_loss.max_loss_ratio": 0.007,
            "position_management.stop_loss.min_distance.ratio": 0.007,
            "position_management.stop_loss.default_atr_multiplier": 2.0,
            "risk.require_tpsl_recalculation": False,
            "risk.fallback_atr": 500000,
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
        mock_threshold.side_effect = lambda key, default=None: {
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

    @patch("src.trading.execution.executor.get_threshold")
    def test_paper_mode_initialization(self, mock_get_threshold):
        """ペーパーモード初期化テスト"""
        # Phase 57.7: get_thresholdをモック（unified.yamlから読み込み）
        mock_get_threshold.return_value = 500000.0

        service = ExecutionService(mode="paper")

        assert service.mode == "paper"
        assert service.discord_notifier is None
        assert service.virtual_balance == 500000.0  # Phase 57.7: unified.yamlから読み込み

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

    @patch("src.trading.execution.executor.get_threshold")
    def test_custom_initial_balance(self, mock_get_threshold):
        """カスタム初期残高設定テスト（Phase 55.9: get_threshold使用）"""

        def threshold_side_effect(key, default):
            if key == "mode_balances.paper.initial_balance":
                return 50000.0
            return default

        mock_get_threshold.side_effect = threshold_side_effect

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
        mock_threshold.side_effect = lambda key, default=None: {
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
    async def test_minimum_trade_size_error_handling(self):
        """最小ロット保証処理エラー時のハンドリング（Phase 62.8: テスト修正）"""
        # サービスを先に作成してから、execute_trade時のみエラーを発生させる
        service = ExecutionService(mode="backtest")

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

        with patch("src.trading.execution.executor.get_threshold") as mock_threshold:
            mock_threshold.side_effect = Exception("設定取得エラー")
            result = await service.execute_trade(eval_obj)

        # Phase 62.8: get_threshold例外時は最小サイズ調整がスキップされる
        # バックテストモードでは手数料計算もスキップされるため、取引自体は成功する
        # ただし、最小サイズへの調整は行われず、元のposition_sizeがそのまま使われる
        assert result.success is True
        assert result.amount == 0.00005  # 最小サイズ調整スキップ（エラー時のフォールバック）


# ========================================
# Phase 51.6: Atomic Entry Pattern テスト
# ========================================


@pytest.mark.asyncio
class TestPhase516AtomicEntry:
    """Phase 51.6: Atomic Entry Pattern機能のテスト"""

    @pytest.fixture
    def mock_bitbank_client(self):
        """BitbankClientのモック"""
        client = MagicMock()
        client.create_order = MagicMock(
            return_value={"order_id": "entry123", "price": 14000000.0, "amount": 0.0001}
        )
        client.cancel_order = MagicMock(return_value={"success": True})
        return client

    @pytest.fixture
    def mock_stop_manager(self):
        """StopManagerのモック"""
        manager = MagicMock()
        return manager

    @pytest.fixture
    def sample_execution_result(self):
        """ExecutionResultサンプル"""
        return ExecutionResult(
            success=True,
            order_id="entry123",
            side="buy",
            amount=0.0001,
            price=14000000.0,
            filled_price=14000000.0,
            status=OrderStatus.FILLED,
            mode=ExecutionMode.LIVE,
            timestamp=datetime.now(),
        )

    @pytest.fixture
    def sample_evaluation(self):
        """TradeEvaluationサンプル"""
        return TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",
            risk_score=0.1,
            position_size=0.0001,
            stop_loss=13900000.0,  # SL 0.7%
            take_profit=14126000.0,  # TP 0.9%
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

    async def test_place_tp_with_retry_success_first_attempt(
        self, mock_bitbank_client, mock_stop_manager
    ):
        """Phase 51.6: TP注文配置リトライ - 初回成功"""
        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)
        service.stop_manager = mock_stop_manager

        # TP注文成功をモック
        mock_stop_manager.place_take_profit = AsyncMock(
            return_value={"order_id": "tp123", "price": 14126000.0}
        )

        result = await service._place_tp_with_retry(
            side="buy",
            amount=0.0001,
            entry_price=14000000.0,
            take_profit_price=14126000.0,
            symbol="BTC/JPY",
            max_retries=3,
        )

        assert result is not None
        assert result["order_id"] == "tp123"
        mock_stop_manager.place_take_profit.assert_called_once()

    async def test_place_tp_with_retry_success_second_attempt(
        self, mock_bitbank_client, mock_stop_manager
    ):
        """Phase 51.6: TP注文配置リトライ - 2回目成功"""
        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)
        service.stop_manager = mock_stop_manager

        # 1回目失敗、2回目成功をモック
        mock_stop_manager.place_take_profit = AsyncMock(
            side_effect=[
                Exception("一時的エラー"),
                {"order_id": "tp123", "price": 14126000.0},
            ]
        )

        result = await service._place_tp_with_retry(
            side="buy",
            amount=0.0001,
            entry_price=14000000.0,
            take_profit_price=14126000.0,
            symbol="BTC/JPY",
            max_retries=3,
        )

        assert result is not None
        assert result["order_id"] == "tp123"
        assert mock_stop_manager.place_take_profit.call_count == 2

    async def test_place_tp_with_retry_all_attempts_failed(
        self, mock_bitbank_client, mock_stop_manager
    ):
        """Phase 51.6: TP注文配置リトライ - 全て失敗"""
        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)
        service.stop_manager = mock_stop_manager

        # 全ての試行で失敗
        mock_stop_manager.place_take_profit = AsyncMock(side_effect=Exception("永続的エラー"))

        with pytest.raises(Exception, match="永続的エラー"):
            await service._place_tp_with_retry(
                side="buy",
                amount=0.0001,
                entry_price=14000000.0,
                take_profit_price=14126000.0,
                symbol="BTC/JPY",
                max_retries=3,
            )

        assert mock_stop_manager.place_take_profit.call_count == 3

    async def test_place_sl_with_retry_success(self, mock_bitbank_client, mock_stop_manager):
        """Phase 51.6: SL注文配置リトライ - 成功"""
        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)
        service.stop_manager = mock_stop_manager

        # SL注文成功をモック
        mock_stop_manager.place_stop_loss = AsyncMock(
            return_value={"order_id": "sl123", "trigger_price": 13900000.0}
        )

        result = await service._place_sl_with_retry(
            side="buy",
            amount=0.0001,
            entry_price=14000000.0,
            stop_loss_price=13900000.0,
            symbol="BTC/JPY",
            max_retries=3,
        )

        assert result is not None
        assert result["order_id"] == "sl123"
        mock_stop_manager.place_stop_loss.assert_called_once()

    async def test_rollback_entry_cancels_all_orders(self, mock_bitbank_client):
        """Phase 51.6: Atomic Entryロールバック - 全注文キャンセル"""
        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)

        # キャンセル成功をモック
        mock_bitbank_client.cancel_order = MagicMock(return_value={"success": True})

        await service._rollback_entry(
            entry_order_id="entry123",
            tp_order_id="tp123",
            sl_order_id="sl123",
            symbol="BTC/JPY",
            error=Exception("TP配置失敗"),
        )

        # 3つの注文すべてキャンセルされることを確認
        assert mock_bitbank_client.cancel_order.call_count == 3
        mock_bitbank_client.cancel_order.assert_any_call("tp123", "BTC/JPY")
        mock_bitbank_client.cancel_order.assert_any_call("sl123", "BTC/JPY")
        mock_bitbank_client.cancel_order.assert_any_call("entry123", "BTC/JPY")

    async def test_rollback_entry_partial_orders(self, mock_bitbank_client):
        """Phase 51.6: Atomic Entryロールバック - 部分的な注文のみキャンセル"""
        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)

        # TP注文のみ存在（SLは配置前に失敗）
        await service._rollback_entry(
            entry_order_id="entry123",
            tp_order_id="tp123",
            sl_order_id=None,  # SL未配置
            symbol="BTC/JPY",
            error=Exception("SL配置失敗"),
        )

        # TP注文とエントリー注文のみキャンセル
        assert mock_bitbank_client.cancel_order.call_count == 2
        mock_bitbank_client.cancel_order.assert_any_call("tp123", "BTC/JPY")
        mock_bitbank_client.cancel_order.assert_any_call("entry123", "BTC/JPY")

    @patch("src.trading.execution.executor.get_threshold")
    async def test_calculate_tp_sl_for_live_trade_success(
        self, mock_threshold, sample_evaluation, sample_execution_result
    ):
        """Phase 51.6: TP/SL再計算メソッド - 成功"""
        service = ExecutionService(mode="live")

        # thresholds設定をモック（Phase 51.6設定）
        mock_threshold.side_effect = lambda key, default=None: {
            "position_management.take_profit.default_ratio": 1.29,
            "position_management.take_profit.min_profit_ratio": 0.009,
            "position_management.stop_loss.max_loss_ratio": 0.007,
            "position_management.stop_loss.min_distance.ratio": 0.007,
            "position_management.stop_loss.default_atr_multiplier": 2.0,
            "risk.require_tpsl_recalculation": False,  # 任意モード
        }.get(key, default)

        final_tp, final_sl = await service._calculate_tp_sl_for_live_trade(
            evaluation=sample_evaluation,
            result=sample_execution_result,
            side="buy",
            amount=0.0001,
        )

        # TP/SLが返されることを確認
        assert final_tp is not None
        assert final_sl is not None
        assert final_tp > sample_execution_result.filled_price  # TPは約定価格より高い
        assert final_sl < sample_execution_result.filled_price  # SLは約定価格より低い

    # ========================================
    # Phase 51.10-A: エントリー前TP/SLクリーンアップテスト
    # ========================================

    async def test_cleanup_old_tp_sl_before_entry_success(self, mock_bitbank_client):
        """Phase 51.10-A: エントリー前クリーンアップ - 古いTP/SL削除成功"""
        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)

        # Phase 53.7: fetch_active_ordersに変更（リスト形式・idキー）
        mock_bitbank_client.fetch_active_orders.return_value = [
            # 削除対象: 古いBUY側のTP（SELL limit注文）
            {"id": "old_tp_1", "side": "sell", "type": "limit", "price": 15600000},
            # 削除対象: 古いBUY側のSL（SELL stop注文）
            {"id": "old_sl_1", "side": "sell", "type": "stop", "price": 15400000},
            # 保護対象: 他のエントリー注文（BUY limit）
            {"id": "other_entry", "side": "buy", "type": "limit", "price": 15500000},
        ]

        # virtual_positionsは空（新規エントリー想定）
        service.virtual_positions = []

        await service._cleanup_old_tp_sl_before_entry(
            side="buy",
            symbol="BTC/JPY",
            entry_order_id="entry123",
        )

        # 2件の古いTP/SL注文が削除される
        assert mock_bitbank_client.cancel_order.call_count == 2
        mock_bitbank_client.cancel_order.assert_any_call("old_tp_1", "BTC/JPY")
        mock_bitbank_client.cancel_order.assert_any_call("old_sl_1", "BTC/JPY")

    async def test_cleanup_old_tp_sl_before_entry_with_protected_orders(self, mock_bitbank_client):
        """Phase 51.10-A: エントリー前クリーンアップ - アクティブポジションのTP/SL保護"""
        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)

        # Phase 53.7: fetch_active_ordersに変更（リスト形式・idキー）
        mock_bitbank_client.fetch_active_orders.return_value = [
            # 保護対象: アクティブポジションのTP
            {"id": "active_tp", "side": "sell", "type": "limit", "price": 15600000},
            # 保護対象: アクティブポジションのSL
            {"id": "active_sl", "side": "sell", "type": "stop", "price": 15400000},
            # 削除対象: 古いTP
            {"id": "old_tp", "side": "sell", "type": "limit", "price": 15550000},
        ]

        # アクティブポジションのTP/SL注文ID（保護対象）
        service.virtual_positions = [
            {
                "side": "buy",
                "amount": 0.0001,
                "tp_order_id": "active_tp",
                "sl_order_id": "active_sl",
            }
        ]

        await service._cleanup_old_tp_sl_before_entry(
            side="buy",
            symbol="BTC/JPY",
            entry_order_id="entry123",
        )

        # 古いTP注文のみ削除（アクティブポジションのTP/SLは保護）
        assert mock_bitbank_client.cancel_order.call_count == 1
        mock_bitbank_client.cancel_order.assert_called_once_with("old_tp", "BTC/JPY")

    async def test_cleanup_old_tp_sl_before_entry_no_orders(self, mock_bitbank_client):
        """Phase 51.10-A: エントリー前クリーンアップ - アクティブ注文なし"""
        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)

        # アクティブ注文なし - Phase 53.7: fetch_active_ordersに変更、リスト形式
        mock_bitbank_client.fetch_active_orders.return_value = []

        await service._cleanup_old_tp_sl_before_entry(
            side="buy",
            symbol="BTC/JPY",
            entry_order_id="entry123",
        )

        # 削除実行されない
        assert mock_bitbank_client.cancel_order.call_count == 0

    async def test_cleanup_old_tp_sl_before_entry_error_handling(self, mock_bitbank_client):
        """Phase 51.10-A: エントリー前クリーンアップ - エラーハンドリング"""
        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)

        # fetch_active_orders失敗 - Phase 53.7: メソッド名変更
        mock_bitbank_client.fetch_active_orders.side_effect = Exception("API error")

        # エラーが発生してもクリーンアップメソッド自体は例外をraiseしない
        # （警告ログのみ・処理継続）
        try:
            await service._cleanup_old_tp_sl_before_entry(
                side="buy",
                symbol="BTC/JPY",
                entry_order_id="entry123",
            )
            # 正常終了（例外raiseされない）
        except Exception:
            pytest.fail("Cleanup should not raise exception on error")

    async def test_cleanup_old_tp_sl_before_entry_sell_side(self, mock_bitbank_client):
        """Phase 51.10-A: エントリー前クリーンアップ - SELLエントリー側"""
        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)

        # アクティブ注文モック（SELLエントリー想定）- Phase 53.7: fetch_active_ordersに変更、リスト形式
        mock_bitbank_client.fetch_active_orders.return_value = [
            # 削除対象: 古いSELL側のTP（BUY limit注文）
            {"id": "old_tp_sell", "side": "buy", "type": "limit", "price": 15400000},
            # 削除対象: 古いSELL側のSL（BUY stop注文）
            {"id": "old_sl_sell", "side": "buy", "type": "stop", "price": 15600000},
            # 非対象: BUY側のTP（SELL limit）
            {"id": "buy_tp", "side": "sell", "type": "limit", "price": 15700000},
        ]

        service.virtual_positions = []

        await service._cleanup_old_tp_sl_before_entry(
            side="sell",  # SELLエントリー
            symbol="BTC/JPY",
            entry_order_id="entry123",
        )

        # SELL側の古いTP/SL注文（BUY側）のみ削除
        assert mock_bitbank_client.cancel_order.call_count == 2
        mock_bitbank_client.cancel_order.assert_any_call("old_tp_sell", "BTC/JPY")
        mock_bitbank_client.cancel_order.assert_any_call("old_sl_sell", "BTC/JPY")


# ========================================
# Phase 53.6: ポジション復元テスト
# ========================================


@pytest.mark.asyncio
class TestRestorePositionsFromAPI:
    """Phase 53.6: 起動時ポジション復元テスト"""

    @pytest.fixture
    def mock_bitbank_client(self):
        """BitbankClientモック"""
        client = AsyncMock()
        client.fetch_margin_positions = AsyncMock(return_value=[])
        client.fetch_active_orders = MagicMock(return_value=[])
        return client

    async def test_restore_positions_paper_mode_skips(self, mock_bitbank_client):
        """ペーパーモードは復元スキップ"""
        service = ExecutionService(mode="paper", bitbank_client=mock_bitbank_client)

        await service.restore_positions_from_api()

        # ペーパーモードではAPI呼び出しなし
        mock_bitbank_client.fetch_margin_positions.assert_not_called()

    @patch("src.trading.execution.executor.DiscordManager")
    async def test_restore_positions_no_active_orders(self, mock_discord, mock_bitbank_client):
        """アクティブ注文なし時のスキップ"""
        mock_bitbank_client.fetch_margin_positions = AsyncMock(return_value=[])
        mock_bitbank_client.fetch_active_orders = MagicMock(return_value=[])

        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)
        await service.restore_positions_from_api()

        assert len(service.virtual_positions) == 0

    @patch("src.trading.execution.executor.DiscordManager")
    async def test_restore_positions_with_active_orders(self, mock_discord, mock_bitbank_client):
        """Phase 63.4: 実ポジションベースの復元（1ポジション=1エントリ）"""
        # 信用建玉
        mock_bitbank_client.fetch_margin_positions = AsyncMock(
            return_value=[
                {
                    "side": "long",
                    "amount": 0.0001,
                    "average_price": 14000000,
                    "unrealized_pnl": 100,
                }
            ]
        )
        # アクティブ注文（TP/SLマッチング用）
        mock_bitbank_client.fetch_active_orders = MagicMock(
            return_value=[
                {
                    "id": "tp_123",
                    "type": "limit",
                    "side": "sell",
                    "amount": 0.0001,
                    "price": 14500000,
                },
                {
                    "id": "sl_123",
                    "type": "stop",
                    "side": "sell",
                    "amount": 0.0001,
                    "price": 13500000,
                },
            ]
        )

        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)
        await service.restore_positions_from_api()

        # Phase 63.4: 1実ポジション → 1 virtual_position
        assert len(service.virtual_positions) == 1
        vp = service.virtual_positions[0]
        assert vp["side"] == "buy"  # long → buy
        assert vp["amount"] == 0.0001
        assert vp["price"] == 14000000
        assert vp["tp_order_id"] == "tp_123"
        assert vp["sl_order_id"] == "sl_123"
        assert vp["take_profit"] == 14500000.0
        assert vp["stop_loss"] == 13500000.0
        assert vp["restored"] is True
        assert vp["sl_placed_at"] is not None

    @patch("src.trading.execution.executor.DiscordManager")
    async def test_restore_positions_no_real_positions(self, mock_discord, mock_bitbank_client):
        """Phase 63.4: 実ポジションなしの場合は復元なし"""
        mock_bitbank_client.fetch_margin_positions = AsyncMock(return_value=[])
        # アクティブ注文があっても実ポジションがなければ復元しない
        mock_bitbank_client.fetch_active_orders = MagicMock(
            return_value=[
                {
                    "id": "orphan_order",
                    "type": "limit",
                    "side": "sell",
                    "amount": 0.0001,
                    "price": 14500000,
                },
            ]
        )

        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)
        await service.restore_positions_from_api()

        # 実ポジションなし → 復元なし
        assert len(service.virtual_positions) == 0

    @patch("src.trading.execution.executor.DiscordManager")
    async def test_restore_positions_api_error_handling(self, mock_discord, mock_bitbank_client):
        """API呼び出しエラー時のハンドリング"""
        mock_bitbank_client.fetch_margin_positions = AsyncMock(side_effect=Exception("API error"))

        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)

        # エラーでも例外発生しない
        await service.restore_positions_from_api()
        assert len(service.virtual_positions) == 0


# ========================================
# Phase 56.5: 既存ポジションTP/SL確保テスト
# ========================================


@pytest.mark.asyncio
class TestEnsureTpSlForExistingPositions:
    """Phase 56.5: 既存ポジションTP/SL確保テスト"""

    @pytest.fixture
    def mock_bitbank_client(self):
        """BitbankClientモック"""
        client = AsyncMock()
        client.fetch_margin_positions = AsyncMock(return_value=[])
        client.fetch_active_orders = MagicMock(return_value=[])
        return client

    async def test_ensure_tp_sl_paper_mode_skips(self, mock_bitbank_client):
        """ペーパーモードはスキップ"""
        service = ExecutionService(mode="paper", bitbank_client=mock_bitbank_client)

        await service.ensure_tp_sl_for_existing_positions()

        mock_bitbank_client.fetch_margin_positions.assert_not_called()

    @patch("src.trading.execution.executor.DiscordManager")
    async def test_ensure_tp_sl_no_positions(self, mock_discord, mock_bitbank_client):
        """ポジションなし時のスキップ"""
        mock_bitbank_client.fetch_margin_positions = AsyncMock(return_value=[])

        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)
        await service.ensure_tp_sl_for_existing_positions()

        mock_bitbank_client.fetch_active_orders.assert_not_called()

    @patch("src.trading.execution.executor.DiscordManager")
    async def test_ensure_tp_sl_position_with_existing_tp_sl(
        self, mock_discord, mock_bitbank_client
    ):
        """TP/SL既存のポジションはスキップ"""
        mock_bitbank_client.fetch_margin_positions = AsyncMock(
            return_value=[{"side": "long", "amount": 0.0001, "average_price": 14000000}]
        )
        # TP/SL注文存在
        mock_bitbank_client.fetch_active_orders = MagicMock(
            return_value=[
                {"id": "tp", "side": "sell", "type": "limit", "amount": 0.0001},
                {"id": "sl", "side": "sell", "type": "stop", "amount": 0.0001},
            ]
        )

        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)
        service.stop_manager = AsyncMock()

        await service.ensure_tp_sl_for_existing_positions()

        # TP/SL配置はスキップ
        service.stop_manager.place_take_profit.assert_not_called()
        service.stop_manager.place_stop_loss.assert_not_called()

    @patch("src.trading.execution.executor.DiscordManager")
    async def test_ensure_tp_sl_places_missing_orders(self, mock_discord, mock_bitbank_client):
        """TP/SLなしポジションに注文配置"""
        mock_bitbank_client.fetch_margin_positions = AsyncMock(
            return_value=[{"side": "long", "amount": 0.0001, "average_price": 14000000}]
        )
        # TP/SL注文なし
        mock_bitbank_client.fetch_active_orders = MagicMock(return_value=[])

        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)
        mock_stop_manager = AsyncMock()
        mock_stop_manager.place_take_profit = AsyncMock(return_value={"order_id": "tp_new"})
        mock_stop_manager.place_stop_loss = AsyncMock(return_value={"order_id": "sl_new"})
        service.stop_manager = mock_stop_manager

        await service.ensure_tp_sl_for_existing_positions()

        # TP/SL両方配置される
        mock_stop_manager.place_take_profit.assert_called_once()
        mock_stop_manager.place_stop_loss.assert_called_once()
        # virtual_positionsにも追加される
        assert len(service.virtual_positions) == 1
        assert service.virtual_positions[0]["recovered"] is True

    @patch("src.trading.execution.executor.DiscordManager")
    async def test_ensure_tp_sl_short_position(self, mock_discord, mock_bitbank_client):
        """Shortポジションのtp/sl配置テスト"""
        mock_bitbank_client.fetch_margin_positions = AsyncMock(
            return_value=[{"side": "short", "amount": 0.0001, "average_price": 14000000}]
        )
        mock_bitbank_client.fetch_active_orders = MagicMock(return_value=[])

        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)
        mock_stop_manager = AsyncMock()
        mock_stop_manager.place_take_profit = AsyncMock(return_value={"order_id": "tp_short"})
        mock_stop_manager.place_stop_loss = AsyncMock(return_value={"order_id": "sl_short"})
        service.stop_manager = mock_stop_manager

        await service.ensure_tp_sl_for_existing_positions()

        # shortポジションの場合はentry_side="sell"が渡される
        call_args = mock_stop_manager.place_take_profit.call_args
        assert call_args.kwargs["side"] == "sell"

    @patch("src.trading.execution.executor.DiscordManager")
    async def test_ensure_tp_sl_api_error_handling(self, mock_discord, mock_bitbank_client):
        """API呼び出しエラー時のハンドリング"""
        mock_bitbank_client.fetch_margin_positions = AsyncMock(side_effect=Exception("API error"))

        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)

        # エラーでも例外発生しない
        await service.ensure_tp_sl_for_existing_positions()


# ========================================
# TP/SL存在確認テスト
# ========================================


class TestCheckTpSlOrdersExist:
    """_check_tp_sl_orders_existテスト"""

    def test_check_tp_sl_exist_long_position_both_exist(self):
        """Longポジション: TP/SL両方存在"""
        service = ExecutionService(mode="paper")

        active_orders = [
            {"side": "sell", "type": "limit", "amount": 0.0001},  # TP
            {"side": "sell", "type": "stop", "amount": 0.0001},  # SL
        ]

        has_tp, has_sl = service._check_tp_sl_orders_exist(
            position_side="long", position_amount=0.0001, active_orders=active_orders
        )

        assert has_tp is True
        assert has_sl is True

    def test_check_tp_sl_exist_long_position_only_tp(self):
        """Longポジション: TPのみ存在"""
        service = ExecutionService(mode="paper")

        active_orders = [
            {"side": "sell", "type": "limit", "amount": 0.0001},  # TP
        ]

        has_tp, has_sl = service._check_tp_sl_orders_exist(
            position_side="long", position_amount=0.0001, active_orders=active_orders
        )

        assert has_tp is True
        assert has_sl is False

    def test_check_tp_sl_exist_short_position(self):
        """Shortポジション: TP/SL確認"""
        service = ExecutionService(mode="paper")

        active_orders = [
            {"side": "buy", "type": "limit", "amount": 0.0001},  # TP
            {"side": "buy", "type": "stop", "amount": 0.0001},  # SL
        ]

        has_tp, has_sl = service._check_tp_sl_orders_exist(
            position_side="short", position_amount=0.0001, active_orders=active_orders
        )

        assert has_tp is True
        assert has_sl is True

    def test_check_tp_sl_exist_amount_mismatch(self):
        """Phase 63: ポジション集約対応 - 数量不一致でもサイド一致ならマッチ"""
        service = ExecutionService(mode="paper")

        active_orders = [
            {"side": "sell", "type": "limit", "amount": 0.0002},  # 2倍の数量
        ]

        has_tp, has_sl = service._check_tp_sl_orders_exist(
            position_side="long", position_amount=0.0001, active_orders=active_orders
        )

        # Phase 63: Bug 2修正 - 集約ポジション対応のため数量マッチング緩和
        # サイド一致のみでTP/SLとして検出
        assert has_tp is True


# ========================================
# Phase 61.9: TP/SL自動執行検知テスト
# ========================================


@pytest.mark.asyncio
class TestCheckStopConditionsWithAutoExecution:
    """Phase 61.9: 自動執行検知を含むcheck_stop_conditionsテスト"""

    @pytest.fixture
    def mock_bitbank_client(self):
        """BitbankClientモック"""
        client = AsyncMock()
        client.fetch_margin_positions = AsyncMock(return_value=[])
        return client

    @patch("src.trading.execution.executor.DiscordManager")
    async def test_check_stop_conditions_detects_auto_execution(
        self, mock_discord, mock_bitbank_client
    ):
        """自動執行検知テスト"""
        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)

        # StopManager設定
        mock_stop_manager = AsyncMock()
        mock_stop_manager.detect_auto_executed_orders = AsyncMock(
            return_value=[
                {
                    "order_id": "auto_exec_1",
                    "execution_type": "take_profit",
                    "side": "buy",
                    "amount": 0.0001,
                    "exit_price": 14500000,
                    "pnl": 500,
                    "strategy_name": "BBReversal",
                }
            ]
        )
        mock_stop_manager.check_stop_conditions = AsyncMock(return_value=None)
        service.stop_manager = mock_stop_manager

        # TradeRecorderモック
        service.trade_recorder = MagicMock()
        service.trade_recorder.record_trade = MagicMock()

        # virtual_positionsに対象ポジション追加
        service.virtual_positions = [{"order_id": "auto_exec_1", "side": "buy", "amount": 0.0001}]

        await service.check_stop_conditions()

        # 自動執行検知が呼ばれる
        mock_stop_manager.detect_auto_executed_orders.assert_called_once()
        # virtual_positionsから削除される
        assert len(service.virtual_positions) == 0
        # Phase 61.12: exit記録が追加される
        service.trade_recorder.record_trade.assert_called_once()

    @patch("src.trading.execution.executor.DiscordManager")
    async def test_check_stop_conditions_auto_execution_error_handling(
        self, mock_discord, mock_bitbank_client
    ):
        """自動執行検知エラー時のハンドリング"""
        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)

        mock_stop_manager = AsyncMock()
        mock_stop_manager.detect_auto_executed_orders = AsyncMock(
            side_effect=Exception("Detection error")
        )
        mock_stop_manager.check_stop_conditions = AsyncMock(return_value=None)
        service.stop_manager = mock_stop_manager

        # エラーでも例外発生しない
        result = await service.check_stop_conditions()

        # check_stop_conditionsは呼ばれる
        mock_stop_manager.check_stop_conditions.assert_called_once()


# ========================================
# 初期化・設定テスト追加
# ========================================


class TestExecutionServiceInitialization:
    """ExecutionService初期化詳細テスト"""

    @patch("src.trading.execution.executor.TradeHistoryRecorder")
    @patch("src.trading.execution.executor.TradeTracker")
    def test_trade_recorder_init_failure(self, mock_tracker, mock_recorder):
        """TradeHistoryRecorder初期化失敗時のハンドリング"""
        mock_recorder.side_effect = Exception("DB connection failed")
        mock_tracker.return_value = MagicMock()

        service = ExecutionService(mode="paper")

        # 初期化失敗してもサービスは起動
        assert service.trade_recorder is None
        assert service.trade_tracker is not None

    @patch("src.trading.execution.executor.TradeHistoryRecorder")
    @patch("src.trading.execution.executor.TradeTracker")
    def test_trade_tracker_init_failure(self, mock_tracker, mock_recorder):
        """TradeTracker初期化失敗時のハンドリング"""
        mock_recorder.return_value = MagicMock()
        mock_tracker.side_effect = Exception("Tracker init failed")

        service = ExecutionService(mode="paper")

        # 初期化失敗してもサービスは起動
        assert service.trade_recorder is not None
        assert service.trade_tracker is None

    @patch("src.trading.execution.executor.DiscordManager")
    def test_discord_notifier_init_failure(self, mock_discord):
        """Discord通知初期化失敗時のハンドリング"""
        mock_discord.side_effect = Exception("Discord connection failed")

        service = ExecutionService(mode="live", bitbank_client=MagicMock())

        # 初期化失敗してもサービスは起動
        assert service.discord_notifier is None


# ========================================
# バックテストモード詳細テスト
# ========================================


@pytest.mark.asyncio
class TestBacktestModeDetailedBehavior:
    """バックテストモード詳細動作テスト"""

    async def test_backtest_insufficient_balance_rejection(self):
        """残高不足時の取引拒否"""
        service = ExecutionService(mode="backtest")
        service.virtual_balance = 100  # 非常に少ない残高

        eval_obj = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",
            risk_score=0.1,
            position_size=0.001,  # 大きなポジション
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
            entry_price=14000000.0,  # 高い価格
        )

        result = await service.execute_trade(eval_obj)

        # 残高不足で拒否
        assert result.success is False
        assert "残高不足" in result.error_message

    async def test_backtest_uses_current_time_for_timestamp(self):
        """バックテスト時のcurrent_time使用テスト"""
        service = ExecutionService(mode="backtest")
        service.current_time = datetime(2026, 1, 15, 12, 0, 0)

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

        result = await service.execute_trade(eval_obj)

        # 成功
        assert result.success is True
        # virtual_positionsにcurrent_timeが使用される
        assert service.virtual_positions[0]["timestamp"] == service.current_time

    async def test_backtest_position_tracker_integration(self):
        """バックテストでのPositionTracker連携テスト"""
        service = ExecutionService(mode="backtest")

        # PositionTrackerモック
        mock_tracker = MagicMock()
        mock_tracker.add_position = MagicMock()
        service.position_tracker = mock_tracker

        eval_obj = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="sell",
            risk_score=0.1,
            position_size=0.0001,
            stop_loss=14200000.0,
            take_profit=13800000.0,
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

        await service.execute_trade(eval_obj)

        # PositionTrackerに追加される
        mock_tracker.add_position.assert_called_once()


# ========================================
# データサービス注入テスト
# ========================================


class TestDataServiceInjection:
    """Phase 54.6: DataService注入テスト"""

    def test_inject_data_service(self):
        """DataService注入テスト"""
        service = ExecutionService(mode="paper")
        mock_data_service = MagicMock()

        service.inject_services(data_service=mock_data_service)

        assert service.data_service is mock_data_service

    def test_inject_position_tracker(self):
        """PositionTracker注入テスト"""
        service = ExecutionService(mode="paper")
        mock_tracker = MagicMock()

        service.inject_services(position_tracker=mock_tracker)

        assert service.position_tracker is mock_tracker


# ========================================
# ライブモード追加テスト
# ========================================


@pytest.mark.asyncio
class TestLiveModeAdditionalBehavior:
    """ライブモード追加動作テスト"""

    @pytest.fixture
    def mock_bitbank_client(self):
        """BitbankClientモック"""
        client = MagicMock()
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

    @patch("src.trading.execution.executor.DiscordManager")
    async def test_live_trade_with_position_tracker(self, mock_discord, mock_bitbank_client):
        """PositionTracker連携テスト"""
        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)

        mock_tracker = MagicMock()
        mock_tracker.add_position = MagicMock()
        service.position_tracker = mock_tracker

        # StopManager設定（Atomic Entry用）
        mock_stop_manager = AsyncMock()
        mock_stop_manager.place_take_profit = AsyncMock(return_value={"order_id": "tp_123"})
        mock_stop_manager.place_stop_loss = AsyncMock(return_value={"order_id": "sl_123"})
        mock_stop_manager.cleanup_old_unfilled_orders = AsyncMock(
            return_value={"cancelled_count": 0}
        )
        service.stop_manager = mock_stop_manager

        # fetch_active_ordersモック追加
        mock_bitbank_client.fetch_active_orders = MagicMock(return_value=[])

        eval_obj = TradeEvaluation(
            decision=RiskDecision.APPROVED,
            side="buy",
            risk_score=0.1,
            position_size=0.0001,
            stop_loss=13900000.0,
            take_profit=14100000.0,
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

        await service.execute_trade(eval_obj)

        # PositionTrackerに追加
        mock_tracker.add_position.assert_called_once()

    @patch("src.trading.execution.executor.DiscordManager")
    async def test_live_trade_records_to_trade_tracker(self, mock_discord, mock_bitbank_client):
        """TradeTracker記録テスト"""
        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)

        # TradeTrackerモック
        mock_trade_tracker = MagicMock()
        mock_trade_tracker.record_entry = MagicMock()
        service.trade_tracker = mock_trade_tracker

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
            market_conditions={"regime_value": "tight_range"},
            entry_price=14000000.0,
        )

        await service.execute_trade(eval_obj)

        # TradeTrackerに記録
        mock_trade_tracker.record_entry.assert_called_once()

    @patch("src.trading.execution.executor.DiscordManager")
    async def test_live_trade_records_to_trade_recorder(self, mock_discord, mock_bitbank_client):
        """TradeHistoryRecorder記録テスト"""
        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)

        # TradeRecorderモック
        mock_recorder = MagicMock()
        mock_recorder.record_trade = MagicMock()
        service.trade_recorder = mock_recorder

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

        await service.execute_trade(eval_obj)

        # TradeRecorderに記録
        mock_recorder.record_trade.assert_called_once()


# ========================================
# ペーパーモード追加テスト
# ========================================


@pytest.mark.asyncio
class TestPaperModeAdditionalBehavior:
    """ペーパーモード追加動作テスト"""

    async def test_paper_trade_records_to_trade_tracker(self):
        """ペーパートレードのTradeTracker記録テスト"""
        mock_client = MagicMock()
        mock_client.fetch_ticker = MagicMock(return_value={"last": 14000000.0})

        service = ExecutionService(mode="paper", bitbank_client=mock_client)

        # TradeTrackerモック
        mock_trade_tracker = MagicMock()
        mock_trade_tracker.record_entry = MagicMock()
        service.trade_tracker = mock_trade_tracker

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
            market_conditions={"regime_value": "normal_range"},
            entry_price=14000000.0,
        )

        await service.execute_trade(eval_obj)

        # TradeTrackerに記録
        mock_trade_tracker.record_entry.assert_called_once()

    async def test_paper_trade_records_to_trade_recorder(self):
        """ペーパートレードのTradeHistoryRecorder記録テスト"""
        mock_client = MagicMock()
        mock_client.fetch_ticker = MagicMock(return_value={"last": 14000000.0})

        service = ExecutionService(mode="paper", bitbank_client=mock_client)

        # TradeRecorderモック
        mock_recorder = MagicMock()
        mock_recorder.record_trade = MagicMock()
        service.trade_recorder = mock_recorder

        eval_obj = TradeEvaluation(
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
            entry_price=14000000.0,
        )

        await service.execute_trade(eval_obj)

        # TradeRecorderに記録
        mock_recorder.record_trade.assert_called_once()

    async def test_paper_trade_position_tracker_error_handling(self):
        """ペーパートレードのPositionTrackerエラーハンドリング"""
        mock_client = MagicMock()
        mock_client.fetch_ticker = MagicMock(return_value={"last": 14000000.0})

        service = ExecutionService(mode="paper", bitbank_client=mock_client)

        # PositionTrackerモック（エラー発生）
        mock_tracker = MagicMock()
        mock_tracker.add_position = MagicMock(side_effect=Exception("Tracker error"))
        service.position_tracker = mock_tracker

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

        # エラーが発生してもトレードは成功
        result = await service.execute_trade(eval_obj)
        assert result.success is True


# ========================================
# クリーンアップ関連追加テスト
# ========================================


@pytest.mark.asyncio
class TestCleanupOldTpSlAdditional:
    """Phase 51.10-A: クリーンアップ追加テスト"""

    async def test_cleanup_cancel_order_failure_handling(self):
        """注文キャンセル失敗時のハンドリング"""
        mock_client = MagicMock()
        mock_client.fetch_active_orders = MagicMock(
            return_value=[
                {"id": "order_1", "side": "sell", "type": "limit", "price": 14500000},
            ]
        )
        # キャンセル失敗
        mock_client.cancel_order = MagicMock(side_effect=Exception("Cancel failed"))

        service = ExecutionService(mode="live", bitbank_client=mock_client)
        service.virtual_positions = []

        # エラーでも例外発生しない
        await service._cleanup_old_tp_sl_before_entry(
            side="buy", symbol="BTC/JPY", entry_order_id="entry123"
        )

    async def test_cleanup_protected_restored_positions(self):
        """Phase 53.12: 復元されたポジションの保護"""
        mock_client = MagicMock()
        mock_client.fetch_active_orders = MagicMock(
            return_value=[
                {"id": "restored_order", "side": "sell", "type": "limit", "price": 14500000},
            ]
        )
        mock_client.cancel_order = MagicMock()

        service = ExecutionService(mode="live", bitbank_client=mock_client)
        # 復元されたポジション
        service.virtual_positions = [{"order_id": "restored_order", "restored": True}]

        await service._cleanup_old_tp_sl_before_entry(
            side="buy", symbol="BTC/JPY", entry_order_id="entry123"
        )

        # 復元されたポジションは保護される
        mock_client.cancel_order.assert_not_called()


# ========================================
# ロールバック追加テスト
# ========================================


@pytest.mark.asyncio
class TestRollbackEntryAdditional:
    """Phase 51.6: ロールバック追加テスト"""

    async def test_rollback_entry_cancel_failure_continues(self):
        """キャンセル失敗しても処理継続"""
        mock_client = MagicMock()
        # TPキャンセル失敗
        mock_client.cancel_order = MagicMock(
            side_effect=[
                Exception("TP cancel failed"),  # TP失敗
                {"success": True},  # SL成功
                {"success": True},  # Entry成功
            ]
        )

        service = ExecutionService(mode="live", bitbank_client=mock_client)

        await service._rollback_entry(
            entry_order_id="entry123",
            tp_order_id="tp123",
            sl_order_id="sl123",
            symbol="BTC/JPY",
            error=Exception("Test error"),
        )

        # 3回呼ばれる（失敗しても続行）
        assert mock_client.cancel_order.call_count == 3

    async def test_rollback_entry_retries_on_entry_cancel_failure(self):
        """Phase 57.11: エントリー注文キャンセルのリトライ"""
        mock_client = MagicMock()
        # エントリーキャンセル3回失敗
        mock_client.cancel_order = MagicMock(side_effect=Exception("Entry cancel failed"))

        service = ExecutionService(mode="live", bitbank_client=mock_client)

        await service._rollback_entry(
            entry_order_id="entry123",
            tp_order_id=None,
            sl_order_id=None,
            symbol="BTC/JPY",
            error=Exception("Test error"),
        )

        # エントリーキャンセルは3回リトライ
        assert mock_client.cancel_order.call_count == 3

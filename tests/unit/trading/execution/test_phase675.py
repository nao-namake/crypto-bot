"""
Phase 67.5: TP/SL損失問題の根本解決テスト

テスト範囲:
1. 約定ポーリング（executor.py）
   - limit注文→SUBMITTED→ポーリングで約定確認→FILLEDに更新
   - ポーリング5回全て未約定→_last_tp_sl_check_timeリセット→return
   - ポーリング中にfetch_orderエラー→継続→最終的にreturnケース
2. Phase 67.4バグ修正（tp_sl_manager.py）
   - fetch_tickerがasyncio.to_thread経由で呼ばれること
   - SL超過時の成行決済がcreate_order(order_type="market")で実行されること
3. Phase 65.2レースコンディション修正
   - SL超過がキャンセル前に検出→成行決済→_cancel_partial_exit_orders未呼出
   - SL未超過→通常フロー（キャンセル→SL配置→TP配置）
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.trading import (
    ExecutionMode,
    ExecutionResult,
    ExecutionService,
    OrderStatus,
    RiskDecision,
    TradeEvaluation,
)
from src.trading.execution.tp_sl_manager import TPSLManager

pytestmark = pytest.mark.asyncio


def _make_evaluation(side="buy"):
    """テスト用TradeEvaluation生成"""
    return TradeEvaluation(
        decision=RiskDecision.APPROVED,
        side=side,
        risk_score=0.1,
        position_size=0.01,
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


def _setup_service_for_limit_order(mock_bitbank_client):
    """limit注文テスト用のExecutionServiceをセットアップ"""
    service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)

    mock_order_strategy = MagicMock()
    mock_order_strategy.get_maker_execution_config = AsyncMock(return_value={"use_maker": False})
    mock_order_strategy.get_optimal_execution_config = AsyncMock(
        return_value={
            "order_type": "limit",
            "price": 14000000.0,
            "strategy": "default",
        }
    )
    mock_order_strategy.determine_order_type = MagicMock(
        return_value={
            "order_type": "limit",
            "price": 14000000.0,
            "strategy": "default",
        }
    )

    mock_tp_sl_manager = MagicMock()
    mock_tp_sl_manager.calculate_tp_sl_for_live_trade = AsyncMock(
        return_value=(14500000.0, 13500000.0)
    )
    mock_tp_sl_manager._last_tp_sl_check_time = datetime.now()

    mock_position_tracker = MagicMock()
    mock_position_tracker.add_position.return_value = {
        "order_id": "order_123",
        "side": "buy",
        "amount": 0.01,
        "price": 14000000.0,
    }

    service.inject_services(
        order_strategy=mock_order_strategy,
        tp_sl_manager=mock_tp_sl_manager,
        position_tracker=mock_position_tracker,
    )
    service._attempt_atomic_entry = AsyncMock(return_value=None)

    return service


# ========================================
# Part A: 約定ポーリングテスト
# ========================================


class TestPhase675OrderFillPolling:
    """Phase 67.5: limit注文の約定ポーリングテスト"""

    @patch("src.trading.execution.executor.asyncio.sleep", new_callable=AsyncMock)
    async def test_polling_finds_fill_on_third_attempt(self, mock_sleep):
        """ポーリング3回目で約定確認→FILLEDに更新"""
        mock_bitbank_client = MagicMock()
        mock_bitbank_client.create_order = MagicMock(
            return_value={
                "id": "order_123",
                "price": 14000000.0,
                "amount": 0.01,
                "filled_price": 0,
                "filled_amount": 0,
                "fee": 0,
            }
        )
        mock_bitbank_client.fetch_order = MagicMock(
            side_effect=[
                {"filled": 0, "status": "open", "average": 0, "price": 14000000.0},
                {"filled": 0, "status": "open", "average": 0, "price": 14000000.0},
                {
                    "filled": 0.01,
                    "status": "closed",
                    "average": 14000000.0,
                    "price": 14000000.0,
                },
            ]
        )

        service = _setup_service_for_limit_order(mock_bitbank_client)

        result = await service.execute_trade(_make_evaluation())

        # fetch_orderが3回呼ばれること（3回目で約定）
        assert mock_bitbank_client.fetch_order.call_count == 3
        # 結果がFILLEDであること
        assert result.status == OrderStatus.FILLED
        assert result.filled_amount == 0.01

    @patch("src.trading.execution.executor.asyncio.sleep", new_callable=AsyncMock)
    async def test_polling_all_unfilled_resets_check_time(self, mock_sleep):
        """ポーリング5回全て未約定→_last_tp_sl_check_timeリセット"""
        mock_bitbank_client = MagicMock()
        mock_bitbank_client.create_order = MagicMock(
            return_value={
                "id": "order_123",
                "price": 14000000.0,
                "amount": 0.01,
                "filled_price": 0,
                "filled_amount": 0,
                "fee": 0,
            }
        )
        mock_bitbank_client.fetch_order = MagicMock(
            return_value={
                "filled": 0,
                "status": "open",
                "average": 0,
                "price": 14000000.0,
            }
        )

        service = _setup_service_for_limit_order(mock_bitbank_client)

        result = await service.execute_trade(_make_evaluation())

        # 5回ポーリング（全部未約定）
        assert mock_bitbank_client.fetch_order.call_count == 5
        # _last_tp_sl_check_time がリセットされていること
        assert service.tp_sl_manager._last_tp_sl_check_time is None
        # filled_amountは0のまま
        assert result.filled_amount == 0

    @patch("src.trading.execution.executor.asyncio.sleep", new_callable=AsyncMock)
    async def test_polling_fetch_order_error_continues(self, mock_sleep):
        """ポーリング中にfetch_orderエラー→継続→最終的にreturn"""
        mock_bitbank_client = MagicMock()
        mock_bitbank_client.create_order = MagicMock(
            return_value={
                "id": "order_123",
                "price": 14000000.0,
                "amount": 0.01,
                "filled_price": 0,
                "filled_amount": 0,
                "fee": 0,
            }
        )
        mock_bitbank_client.fetch_order = MagicMock(
            side_effect=[
                Exception("Network error"),
                Exception("Timeout"),
                {
                    "filled": 0.01,
                    "status": "closed",
                    "average": 14000000.0,
                    "price": 14000000.0,
                },
            ]
        )

        service = _setup_service_for_limit_order(mock_bitbank_client)

        result = await service.execute_trade(_make_evaluation())

        # 3回呼ばれる（エラー2回 + 約定1回）
        assert mock_bitbank_client.fetch_order.call_count == 3
        assert result.filled_amount == 0.01
        assert result.status == OrderStatus.FILLED

    @patch("src.trading.execution.executor.asyncio.sleep", new_callable=AsyncMock)
    async def test_polling_canceled_order_stops_early(self, mock_sleep):
        """注文がキャンセル済みの場合はポーリング早期終了"""
        mock_bitbank_client = MagicMock()
        mock_bitbank_client.create_order = MagicMock(
            return_value={
                "id": "order_123",
                "price": 14000000.0,
                "amount": 0.01,
                "filled_price": 0,
                "filled_amount": 0,
                "fee": 0,
            }
        )
        mock_bitbank_client.fetch_order = MagicMock(
            return_value={
                "filled": 0,
                "status": "canceled",
                "average": 0,
                "price": 14000000.0,
            }
        )

        service = _setup_service_for_limit_order(mock_bitbank_client)

        result = await service.execute_trade(_make_evaluation())

        # キャンセル済みなので1回で終了
        assert mock_bitbank_client.fetch_order.call_count == 1
        assert result.filled_amount == 0

    @patch("src.trading.execution.executor.asyncio.sleep", new_callable=AsyncMock)
    async def test_market_order_skips_polling(self, mock_sleep):
        """成行注文はポーリングをスキップ"""
        mock_bitbank_client = MagicMock()
        mock_bitbank_client.create_order = MagicMock(
            return_value={
                "id": "order_123",
                "price": 14000000.0,
                "amount": 0.01,
                "filled_price": 14000000.0,
                "filled_amount": 0.01,
                "fee": 14.0,
            }
        )

        service = ExecutionService(mode="live", bitbank_client=mock_bitbank_client)
        mock_order_strategy = MagicMock()
        mock_order_strategy.get_maker_execution_config = AsyncMock(
            return_value={"use_maker": False}
        )
        mock_order_strategy.get_optimal_execution_config = AsyncMock(
            return_value={
                "order_type": "market",
                "price": None,
                "strategy": "default",
            }
        )

        mock_tp_sl_manager = MagicMock()
        mock_tp_sl_manager.calculate_tp_sl_for_live_trade = AsyncMock(
            return_value=(14500000.0, 13500000.0)
        )

        mock_position_tracker = MagicMock()
        mock_position_tracker.add_position.return_value = {
            "order_id": "order_123",
            "side": "buy",
            "amount": 0.01,
            "price": 14000000.0,
        }

        service.inject_services(
            order_strategy=mock_order_strategy,
            tp_sl_manager=mock_tp_sl_manager,
            position_tracker=mock_position_tracker,
        )
        service._attempt_atomic_entry = AsyncMock(return_value=None)

        result = await service.execute_trade(_make_evaluation())

        # 成行注文ではfetch_orderは呼ばれない
        mock_bitbank_client.fetch_order.assert_not_called()
        assert result.status == OrderStatus.FILLED


# ========================================
# Part C: Phase 67.4バグ修正テスト
# ========================================


class TestPhase675BugFixTPSLManager:
    """Phase 67.5: Phase 67.4バグ修正の検証"""

    @pytest.fixture
    def tp_sl_manager(self):
        return TPSLManager()

    @pytest.fixture
    def mock_bitbank_client(self):
        """BitbankClientのモック（sync API）"""
        client = MagicMock()
        client.fetch_ticker = MagicMock(return_value={"last": 13800000.0})
        client.create_order = MagicMock(return_value={"id": "market_close_1"})
        client.fetch_active_orders = MagicMock(return_value=[])
        client.create_stop_loss_order = MagicMock(
            return_value={"id": "sl_123", "trigger_price": 13900000.0}
        )
        client.create_take_profit_order = MagicMock(return_value={"id": "tp_123"})
        return client

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_sl_breach_pre_cancel_uses_asyncio_to_thread(
        self, mock_threshold, tp_sl_manager, mock_bitbank_client
    ):
        """SL超過事前チェックでfetch_tickerがasyncio.to_thread経由で呼ばれること"""
        # long position, current price below SL → breached
        mock_bitbank_client.fetch_ticker = MagicMock(return_value={"last": 13800000.0})

        mock_threshold.side_effect = lambda key, default=None: {
            "currency_pair": "BTC/JPY",
        }.get(key, default)

        tp_sl_manager._is_fixed_amount_tp_enabled = MagicMock(return_value=False)
        tp_sl_manager.calculate_recovery_tp_sl_prices = MagicMock(
            return_value=(14500000.0, 13900000.0)
        )

        await tp_sl_manager._place_missing_tp_sl(
            position_side="long",
            amount=0.01,
            avg_price=14000000.0,
            has_tp=False,
            has_sl=False,
            virtual_positions=[],
            bitbank_client=mock_bitbank_client,
        )

        # fetch_tickerが呼ばれること（asyncio.to_thread経由なのでsyncモックで十分）
        mock_bitbank_client.fetch_ticker.assert_called()
        # SL超過で成行決済が呼ばれること
        mock_bitbank_client.create_order.assert_called_once()
        call_kwargs = mock_bitbank_client.create_order.call_args
        assert call_kwargs[1]["order_type"] == "market"
        assert call_kwargs[1]["side"] == "sell"
        assert call_kwargs[1]["is_closing_order"] is True

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_sl_breach_uses_create_order_not_create_market_order(
        self, mock_threshold, tp_sl_manager, mock_bitbank_client
    ):
        """SL超過時にcreate_order(market)が使われること（create_market_orderではない）"""
        mock_bitbank_client.fetch_ticker = MagicMock(
            return_value={"last": 14200000.0}  # short position, price above SL
        )

        mock_threshold.side_effect = lambda key, default=None: {
            "currency_pair": "BTC/JPY",
        }.get(key, default)

        tp_sl_manager._is_fixed_amount_tp_enabled = MagicMock(return_value=False)
        tp_sl_manager.calculate_recovery_tp_sl_prices = MagicMock(
            return_value=(13500000.0, 14100000.0)
        )

        await tp_sl_manager._place_missing_tp_sl(
            position_side="short",
            amount=0.01,
            avg_price=14000000.0,
            has_tp=False,
            has_sl=False,
            virtual_positions=[],
            bitbank_client=mock_bitbank_client,
        )

        # create_orderが呼ばれること
        mock_bitbank_client.create_order.assert_called_once()
        call_kwargs = mock_bitbank_client.create_order.call_args[1]
        assert call_kwargs["order_type"] == "market"
        assert call_kwargs["side"] == "buy"
        assert call_kwargs["entry_position_side"] == "short"


# ========================================
# Part D: レースコンディション修正テスト
# ========================================


class TestPhase675RaceConditionFix:
    """Phase 67.5: SL超過事前チェック（キャンセル前）テスト"""

    @pytest.fixture
    def tp_sl_manager(self):
        return TPSLManager()

    @pytest.fixture
    def mock_bitbank_client(self):
        """BitbankClientのモック"""
        client = MagicMock()
        client.fetch_ticker = MagicMock(return_value={"last": 14000000.0})
        client.create_order = MagicMock(return_value={"id": "market_close_1"})
        client.fetch_active_orders = MagicMock(return_value=[])
        client.cancel_order = MagicMock()
        client.create_stop_loss_order = MagicMock(
            return_value={"id": "sl_123", "trigger_price": 13900000.0}
        )
        client.create_take_profit_order = MagicMock(return_value={"id": "tp_123"})
        return client

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_sl_breached_after_cancel_triggers_market_close(
        self, mock_threshold, tp_sl_manager, mock_bitbank_client
    ):
        """Phase 68.2: キャンセル後にSL超過検出→成行決済"""
        # SL超過状態: long position, current price (13800000) < SL (13900000)
        mock_bitbank_client.fetch_ticker = MagicMock(return_value={"last": 13800000.0})

        mock_threshold.side_effect = lambda key, default=None: {
            "currency_pair": "BTC/JPY",
        }.get(key, default)

        tp_sl_manager._is_fixed_amount_tp_enabled = MagicMock(return_value=False)
        tp_sl_manager.calculate_recovery_tp_sl_prices = MagicMock(
            return_value=(14500000.0, 13900000.0)
        )
        tp_sl_manager._cancel_partial_exit_orders = AsyncMock(return_value=0)

        await tp_sl_manager._place_missing_tp_sl(
            position_side="long",
            amount=0.01,
            avg_price=14000000.0,
            has_tp=False,
            has_sl=False,
            virtual_positions=[],
            bitbank_client=mock_bitbank_client,
        )

        # 成行決済が実行されること
        mock_bitbank_client.create_order.assert_called_once()
        call_kwargs = mock_bitbank_client.create_order.call_args[1]
        assert call_kwargs["order_type"] == "market"
        assert call_kwargs["side"] == "sell"

        # Phase 68.2: キャンセル後のPre-Checkで検出するため、キャンセルは実行される
        tp_sl_manager._cancel_partial_exit_orders.assert_called_once()

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_no_sl_breach_proceeds_to_normal_flow(
        self, mock_threshold, tp_sl_manager, mock_bitbank_client
    ):
        """SL未超過→通常フロー（キャンセル→SL配置→TP配置）"""
        # SL未超過: long position, current price (14100000) > SL (13900000)
        mock_bitbank_client.fetch_ticker = MagicMock(return_value={"last": 14100000.0})

        mock_threshold.side_effect = lambda key, default=None: {
            "currency_pair": "BTC/JPY",
        }.get(key, default)

        tp_sl_manager._is_fixed_amount_tp_enabled = MagicMock(return_value=False)
        tp_sl_manager.calculate_recovery_tp_sl_prices = MagicMock(
            return_value=(14500000.0, 13900000.0)
        )
        tp_sl_manager._cancel_partial_exit_orders = AsyncMock(return_value=2)
        tp_sl_manager.place_sl_or_market_close = AsyncMock(return_value={"order_id": "sl_new"})
        tp_sl_manager.place_take_profit = AsyncMock(return_value={"order_id": "tp_new"})

        virtual_positions = []
        await tp_sl_manager._place_missing_tp_sl(
            position_side="long",
            amount=0.01,
            avg_price=14000000.0,
            has_tp=False,
            has_sl=False,
            virtual_positions=virtual_positions,
            bitbank_client=mock_bitbank_client,
        )

        # キャンセルが実行されること
        tp_sl_manager._cancel_partial_exit_orders.assert_called_once()
        # SL配置が実行されること
        tp_sl_manager.place_sl_or_market_close.assert_called_once()
        # TP配置が実行されること
        tp_sl_manager.place_take_profit.assert_called_once()
        # 成行決済は呼ばれないこと
        mock_bitbank_client.create_order.assert_not_called()

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_sl_breach_after_cancel_triggers_market_close(
        self, mock_threshold, tp_sl_manager, mock_bitbank_client
    ):
        """キャンセル後のSL超過再チェックで検出→成行決済"""
        # 1回目のfetch_ticker: SL未超過
        # 2回目のfetch_ticker: SL超過（キャンセル中に価格変動）
        mock_bitbank_client.fetch_ticker = MagicMock(
            side_effect=[
                {"last": 14100000.0},  # 事前チェック: 未超過
                {"last": 13800000.0},  # キャンセル後チェック: 超過
            ]
        )

        mock_threshold.side_effect = lambda key, default=None: {
            "currency_pair": "BTC/JPY",
        }.get(key, default)

        tp_sl_manager._is_fixed_amount_tp_enabled = MagicMock(return_value=False)
        tp_sl_manager.calculate_recovery_tp_sl_prices = MagicMock(
            return_value=(14500000.0, 13900000.0)
        )
        tp_sl_manager._cancel_partial_exit_orders = AsyncMock(return_value=2)

        await tp_sl_manager._place_missing_tp_sl(
            position_side="long",
            amount=0.01,
            avg_price=14000000.0,
            has_tp=False,
            has_sl=False,
            virtual_positions=[],
            bitbank_client=mock_bitbank_client,
        )

        # fetch_tickerが2回呼ばれること（事前+キャンセル後）
        assert mock_bitbank_client.fetch_ticker.call_count == 2
        # キャンセルが実行されること
        tp_sl_manager._cancel_partial_exit_orders.assert_called_once()
        # 成行決済が実行されること（キャンセル後のSL超過で）
        mock_bitbank_client.create_order.assert_called_once()

    @patch("src.trading.execution.tp_sl_manager.get_threshold")
    async def test_pre_check_error_continues_to_cancel(
        self, mock_threshold, tp_sl_manager, mock_bitbank_client
    ):
        """SL超過事前チェック失敗→キャンセルに進む（エラー耐性）"""
        # 1回目のfetch_ticker: エラー
        # 2回目のfetch_ticker: 正常（SL未超過）
        mock_bitbank_client.fetch_ticker = MagicMock(
            side_effect=[
                Exception("Network error"),  # 事前チェック失敗
                {"last": 14100000.0},  # キャンセル後チェック: 未超過
            ]
        )

        mock_threshold.side_effect = lambda key, default=None: {
            "currency_pair": "BTC/JPY",
        }.get(key, default)

        tp_sl_manager._is_fixed_amount_tp_enabled = MagicMock(return_value=False)
        tp_sl_manager.calculate_recovery_tp_sl_prices = MagicMock(
            return_value=(14500000.0, 13900000.0)
        )
        tp_sl_manager._cancel_partial_exit_orders = AsyncMock(return_value=0)
        tp_sl_manager.place_sl_or_market_close = AsyncMock(return_value={"order_id": "sl_new"})
        tp_sl_manager.place_take_profit = AsyncMock(return_value={"order_id": "tp_new"})

        virtual_positions = []
        await tp_sl_manager._place_missing_tp_sl(
            position_side="long",
            amount=0.01,
            avg_price=14000000.0,
            has_tp=False,
            has_sl=False,
            virtual_positions=virtual_positions,
            bitbank_client=mock_bitbank_client,
        )

        # エラーにもかかわらずキャンセルに進むこと
        tp_sl_manager._cancel_partial_exit_orders.assert_called_once()
        # SL配置も実行されること
        tp_sl_manager.place_sl_or_market_close.assert_called_once()

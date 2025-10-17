"""
StopManager Phase 42 テストスイート

Phase 42: 統合TP/SL実装

テスト範囲:
- cancel_existing_tp_sl(): 既存TP/SL注文キャンセル（6テスト）
- place_consolidated_tp_sl(): 統合TP/SL配置（6テスト）
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.trading.execution.stop_manager import StopManager


@pytest.fixture
def stop_manager():
    """StopManager fixture"""
    return StopManager()


@pytest.fixture
def mock_bitbank_client():
    """BitbankClient mock fixture"""
    client = AsyncMock()
    client.cancel_order = AsyncMock(return_value={"success": True})
    client.create_take_profit_order = Mock(return_value={"id": "tp_consolidated_123"})
    client.create_stop_loss_order = Mock(return_value={"id": "sl_consolidated_456"})
    return client


# ========================================
# cancel_existing_tp_sl() テスト - 6ケース
# ========================================


class TestCancelExistingTpSl:
    """cancel_existing_tp_sl() テスト - Phase 42"""

    @pytest.mark.asyncio
    @patch("asyncio.to_thread")
    async def test_both_tp_sl_cancel_success(
        self, mock_to_thread, stop_manager, mock_bitbank_client
    ):
        """TP/SL両方キャンセル成功"""

        # asyncio.to_thread()のモック（cancel_order 2回呼ばれる）
        async def mock_to_thread_impl(func, *args):
            return {"success": True}

        mock_to_thread.side_effect = mock_to_thread_impl

        result = await stop_manager.cancel_existing_tp_sl(
            tp_order_id="tp_order_999",
            sl_order_id="sl_order_888",
            symbol="btc_jpy",
            bitbank_client=mock_bitbank_client,
        )

        assert result["cancelled_count"] == 2
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    @patch("asyncio.to_thread")
    async def test_tp_only_cancel_success(self, mock_to_thread, stop_manager, mock_bitbank_client):
        """TPのみキャンセル成功（SL注文なし）"""

        async def mock_to_thread_impl(func, *args):
            return {"success": True}

        mock_to_thread.side_effect = mock_to_thread_impl

        result = await stop_manager.cancel_existing_tp_sl(
            tp_order_id="tp_order_999",
            sl_order_id=None,  # SLなし
            symbol="btc_jpy",
            bitbank_client=mock_bitbank_client,
        )

        assert result["cancelled_count"] == 1
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    @patch("asyncio.to_thread")
    async def test_sl_only_cancel_success(self, mock_to_thread, stop_manager, mock_bitbank_client):
        """SLのみキャンセル成功（TP注文なし）"""

        async def mock_to_thread_impl(func, *args):
            return {"success": True}

        mock_to_thread.side_effect = mock_to_thread_impl

        result = await stop_manager.cancel_existing_tp_sl(
            tp_order_id=None,  # TPなし
            sl_order_id="sl_order_888",
            symbol="btc_jpy",
            bitbank_client=mock_bitbank_client,
        )

        assert result["cancelled_count"] == 1
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    @patch("asyncio.to_thread")
    async def test_order_not_found_graceful_handling(
        self, mock_to_thread, stop_manager, mock_bitbank_client
    ):
        """OrderNotFoundエラー時のGraceful handling（debug level）"""

        async def mock_to_thread_impl(func, *args):
            raise Exception("OrderNotFound: order not found")

        mock_to_thread.side_effect = mock_to_thread_impl

        result = await stop_manager.cancel_existing_tp_sl(
            tp_order_id="tp_order_999",
            sl_order_id="sl_order_888",
            symbol="btc_jpy",
            bitbank_client=mock_bitbank_client,
        )

        # エラーだがcancelled_count=0で正常終了
        assert result["cancelled_count"] == 0
        # OrderNotFoundはerrorsに追加されない（debug levelのみ）
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    @patch("asyncio.to_thread")
    async def test_api_exception_error_list(
        self, mock_to_thread, stop_manager, mock_bitbank_client
    ):
        """その他API例外はエラーリストに追加"""

        call_count = 0

        async def mock_to_thread_impl(func, *args):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # TP cancel時
                raise Exception("API Error: Rate limit exceeded")
            else:  # SL cancel時
                return {"success": True}

        mock_to_thread.side_effect = mock_to_thread_impl

        result = await stop_manager.cancel_existing_tp_sl(
            tp_order_id="tp_order_999",
            sl_order_id="sl_order_888",
            symbol="btc_jpy",
            bitbank_client=mock_bitbank_client,
        )

        # TP失敗・SL成功
        assert result["cancelled_count"] == 1
        assert len(result["errors"]) == 1
        assert "Rate limit exceeded" in result["errors"][0]

    @pytest.mark.asyncio
    async def test_both_none_no_operation(self, stop_manager, mock_bitbank_client):
        """両方None時は何もしない"""
        result = await stop_manager.cancel_existing_tp_sl(
            tp_order_id=None,
            sl_order_id=None,
            symbol="btc_jpy",
            bitbank_client=mock_bitbank_client,
        )

        assert result["cancelled_count"] == 0
        assert len(result["errors"]) == 0


# ========================================
# place_consolidated_tp_sl() テスト - 6ケース
# ========================================


class TestPlaceConsolidatedTpSl:
    """place_consolidated_tp_sl() テスト - Phase 42"""

    @pytest.mark.asyncio
    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_both_tp_sl_placement_success(
        self, mock_threshold, stop_manager, mock_bitbank_client
    ):
        """TP/SL両方配置成功"""
        # TP/SL有効化
        mock_threshold.side_effect = lambda key, default=None: (
            {"enabled": True} if "take_profit" in key or "stop_loss" in key else default
        )

        result = await stop_manager.place_consolidated_tp_sl(
            average_price=14000000.0,
            total_amount=0.003,
            side="buy",
            take_profit_price=14300000.0,
            stop_loss_price=13700000.0,
            symbol="btc_jpy",
            bitbank_client=mock_bitbank_client,
        )

        assert result["tp_order_id"] == "tp_consolidated_123"
        assert result["sl_order_id"] == "sl_consolidated_456"
        mock_bitbank_client.create_take_profit_order.assert_called_once()
        mock_bitbank_client.create_stop_loss_order.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_tp_only_success_sl_failed(self, mock_threshold, stop_manager):
        """TPのみ成功・SL失敗時の警告"""
        mock_threshold.side_effect = lambda key, default=None: (
            {"enabled": True} if "take_profit" in key or "stop_loss" in key else default
        )

        mock_client = Mock()
        mock_client.create_take_profit_order = Mock(return_value={"id": "tp_123"})
        mock_client.create_stop_loss_order = Mock(
            side_effect=Exception("API Error: SL placement failed")
        )

        result = await stop_manager.place_consolidated_tp_sl(
            average_price=14000000.0,
            total_amount=0.003,
            side="buy",
            take_profit_price=14300000.0,
            stop_loss_price=13700000.0,
            symbol="btc_jpy",
            bitbank_client=mock_client,
        )

        # TPのみ成功
        assert result["tp_order_id"] == "tp_123"
        assert result["sl_order_id"] is None

    @pytest.mark.asyncio
    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_sl_only_success_tp_failed(self, mock_threshold, stop_manager):
        """SLのみ成功・TP失敗時の警告"""
        mock_threshold.side_effect = lambda key, default=None: (
            {"enabled": True} if "take_profit" in key or "stop_loss" in key else default
        )

        mock_client = Mock()
        mock_client.create_take_profit_order = Mock(
            side_effect=Exception("API Error: TP placement failed")
        )
        mock_client.create_stop_loss_order = Mock(return_value={"id": "sl_456"})

        result = await stop_manager.place_consolidated_tp_sl(
            average_price=14000000.0,
            total_amount=0.003,
            side="buy",
            take_profit_price=14300000.0,
            stop_loss_price=13700000.0,
            symbol="btc_jpy",
            bitbank_client=mock_client,
        )

        # SLのみ成功
        assert result["tp_order_id"] is None
        assert result["sl_order_id"] == "sl_456"

    @pytest.mark.asyncio
    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_both_failed(self, mock_threshold, stop_manager):
        """TP/SL両方失敗時の警告ログ"""
        mock_threshold.side_effect = lambda key, default=None: (
            {"enabled": True} if "take_profit" in key or "stop_loss" in key else default
        )

        mock_client = Mock()
        mock_client.create_take_profit_order = Mock(side_effect=Exception("TP API Error"))
        mock_client.create_stop_loss_order = Mock(side_effect=Exception("SL API Error"))

        result = await stop_manager.place_consolidated_tp_sl(
            average_price=14000000.0,
            total_amount=0.003,
            side="buy",
            take_profit_price=14300000.0,
            stop_loss_price=13700000.0,
            symbol="btc_jpy",
            bitbank_client=mock_client,
        )

        # 両方失敗
        assert result["tp_order_id"] is None
        assert result["sl_order_id"] is None

    @pytest.mark.asyncio
    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_error_code_30101_trigger_price_missing(self, mock_threshold, stop_manager):
        """エラーコード30101（トリガー価格未指定）検出"""
        mock_threshold.side_effect = lambda key, default=None: (
            {"enabled": True} if "take_profit" in key or "stop_loss" in key else default
        )

        mock_client = Mock()
        mock_client.create_take_profit_order = Mock(return_value={"id": "tp_123"})
        mock_client.create_stop_loss_order = Mock(
            side_effect=Exception("bitbank API Error 30101: trigger_price is required")
        )

        result = await stop_manager.place_consolidated_tp_sl(
            average_price=14000000.0,
            total_amount=0.003,
            side="buy",
            take_profit_price=14300000.0,
            stop_loss_price=13700000.0,
            symbol="btc_jpy",
            bitbank_client=mock_client,
        )

        # TP成功、SL失敗（30101エラー）
        assert result["tp_order_id"] == "tp_123"
        assert result["sl_order_id"] is None

    @pytest.mark.asyncio
    @patch("src.trading.execution.stop_manager.get_threshold")
    async def test_error_code_50061_insufficient_balance(self, mock_threshold, stop_manager):
        """エラーコード50061（残高不足）検出"""
        mock_threshold.side_effect = lambda key, default=None: (
            {"enabled": True} if "take_profit" in key or "stop_loss" in key else default
        )

        mock_client = Mock()
        mock_client.create_take_profit_order = Mock(
            side_effect=Exception("bitbank API Error 50061: Insufficient funds")
        )
        mock_client.create_stop_loss_order = Mock(return_value={"id": "sl_456"})

        result = await stop_manager.place_consolidated_tp_sl(
            average_price=14000000.0,
            total_amount=0.003,
            side="buy",
            take_profit_price=14300000.0,
            stop_loss_price=13700000.0,
            symbol="btc_jpy",
            bitbank_client=mock_client,
        )

        # TP失敗（50061エラー）、SL成功
        assert result["tp_order_id"] is None
        assert result["sl_order_id"] == "sl_456"

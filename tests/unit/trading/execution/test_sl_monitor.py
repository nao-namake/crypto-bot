"""Phase 87 C1/H1: SLMonitor テスト

SL CANCELED_UNFILLED 検出 + 緊急成行決済 + 24h タイムアウト判定の単体テスト。
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from src.trading.execution.sl_monitor import (
    DEFAULT_SL_TIMEOUT_HOURS,
    SLHealthResult,
    SLMonitor,
)

# ============================================================
# 純粋関数のテスト
# ============================================================


class TestStatusJudgement:
    """is_canceled_unfilled / is_expired / is_rejected の判定"""

    def test_canceled_unfilled_detected(self):
        order = {"info": {"status": "CANCELED_UNFILLED"}}
        assert SLMonitor.is_canceled_unfilled(order) is True

    def test_canceled_unfilled_lowercase(self):
        order = {"info": {"status": "canceled_unfilled"}}
        assert SLMonitor.is_canceled_unfilled(order) is True

    def test_canceled_unfilled_negative_for_filled(self):
        order = {"info": {"status": "FULLY_FILLED"}}
        assert SLMonitor.is_canceled_unfilled(order) is False

    def test_canceled_unfilled_no_info(self):
        assert SLMonitor.is_canceled_unfilled({}) is False
        assert SLMonitor.is_canceled_unfilled({"info": None}) is False

    def test_expired(self):
        assert SLMonitor.is_expired({"info": {"status": "EXPIRED"}}) is True
        assert SLMonitor.is_expired({"info": {"status": "ACTIVE"}}) is False

    def test_rejected(self):
        assert SLMonitor.is_rejected({"info": {"status": "REJECTED"}}) is True
        assert SLMonitor.is_rejected({"info": {"status": "ACTIVE"}}) is False


class TestTimeoutJudgement:
    """_is_timed_out (H1 24h タイムアウト判定)"""

    def test_no_placed_at_returns_false(self):
        monitor = SLMonitor(logger=MagicMock())
        assert monitor._is_timed_out(None) is False
        assert monitor._is_timed_out("") is False

    def test_invalid_iso_returns_false(self):
        monitor = SLMonitor(logger=MagicMock())
        assert monitor._is_timed_out("not-an-iso") is False

    def test_recent_returns_false(self):
        monitor = SLMonitor(logger=MagicMock(), timeout_hours=24)
        recent = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        assert monitor._is_timed_out(recent) is False

    def test_exceeded_returns_true(self):
        monitor = SLMonitor(logger=MagicMock(), timeout_hours=24)
        old = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        assert monitor._is_timed_out(old) is True

    def test_custom_timeout_hours(self):
        monitor = SLMonitor(logger=MagicMock(), timeout_hours=1)
        past = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        assert monitor._is_timed_out(past) is True

    def test_naive_datetime_is_treated_as_utc(self):
        """naive な ISO 文字列も UTC として解釈される"""
        monitor = SLMonitor(logger=MagicMock(), timeout_hours=1)
        past_naive = (
            (datetime.now(timezone.utc) - timedelta(hours=2)).replace(tzinfo=None).isoformat()
        )
        assert monitor._is_timed_out(past_naive) is True


# ============================================================
# check_sl_health
# ============================================================


def _make_client(order_response=None, raise_exc=None):
    """fetch_order のレスポンスを差し替えた擬似 BitbankClient を返す"""
    client = MagicMock()
    if raise_exc is not None:
        client.fetch_order.side_effect = raise_exc
    else:
        client.fetch_order.return_value = order_response or {"info": {"status": "ACTIVE"}}
    return client


class TestCheckSLHealth:
    @pytest.mark.asyncio
    async def test_empty_order_id_returns_not_found(self):
        monitor = SLMonitor(logger=MagicMock())
        result = await monitor.check_sl_health(None, None, MagicMock())
        assert result.is_healthy is False
        assert result.failure_reason == "not_found"
        assert result.requires_emergency_close is True

    @pytest.mark.asyncio
    async def test_healthy_order(self):
        monitor = SLMonitor(logger=MagicMock())
        client = _make_client({"info": {"status": "ACTIVE"}})
        recent = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        result = await monitor.check_sl_health("OID-1", recent, client)
        assert result.is_healthy is True
        assert result.requires_emergency_close is False

    @pytest.mark.asyncio
    async def test_canceled_unfilled_triggers_emergency(self):
        monitor = SLMonitor(logger=MagicMock())
        client = _make_client({"info": {"status": "CANCELED_UNFILLED"}})
        result = await monitor.check_sl_health(
            "OID-2",
            (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
            client,
        )
        assert result.is_healthy is False
        assert result.failure_reason == "canceled_unfilled"
        assert result.requires_emergency_close is True

    @pytest.mark.asyncio
    async def test_expired_triggers_emergency(self):
        monitor = SLMonitor(logger=MagicMock())
        client = _make_client({"info": {"status": "EXPIRED"}})
        result = await monitor.check_sl_health("OID-3", None, client)
        assert result.failure_reason == "expired"
        assert result.requires_emergency_close is True

    @pytest.mark.asyncio
    async def test_rejected_triggers_emergency(self):
        monitor = SLMonitor(logger=MagicMock())
        client = _make_client({"info": {"status": "REJECTED"}})
        result = await monitor.check_sl_health("OID-4", None, client)
        assert result.failure_reason == "rejected"
        assert result.requires_emergency_close is True

    @pytest.mark.asyncio
    async def test_timeout_24h_triggers_emergency(self):
        monitor = SLMonitor(logger=MagicMock(), timeout_hours=24)
        client = _make_client({"info": {"status": "ACTIVE"}})
        old = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        result = await monitor.check_sl_health("OID-5", old, client)
        assert result.failure_reason == "timeout_24h"
        assert result.requires_emergency_close is True

    @pytest.mark.asyncio
    async def test_fetch_error_returns_healthy_no_emergency(self):
        """一時的なAPIエラーで誤発火させない"""
        monitor = SLMonitor(logger=MagicMock())
        client = _make_client(raise_exc=RuntimeError("API down"))
        result = await monitor.check_sl_health("OID-6", None, client)
        assert result.is_healthy is True
        assert result.failure_reason == "fetch_error"
        assert result.requires_emergency_close is False


# ============================================================
# emergency_market_close
# ============================================================


class TestEmergencyMarketClose:
    @pytest.mark.asyncio
    async def test_invalid_side_returns_none(self):
        monitor = SLMonitor(logger=MagicMock())
        result = await monitor.emergency_market_close(
            entry_side="invalid", amount=0.01, reason="test", bitbank_client=MagicMock()
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_zero_amount_returns_none(self):
        monitor = SLMonitor(logger=MagicMock())
        result = await monitor.emergency_market_close(
            entry_side="buy", amount=0.0, reason="test", bitbank_client=MagicMock()
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_dry_run_does_not_send_order(self):
        client = MagicMock()
        monitor = SLMonitor(logger=MagicMock(), dry_run=True)
        result = await monitor.emergency_market_close(
            entry_side="buy", amount=0.01, reason="test", bitbank_client=client
        )
        assert result == {"order_id": None, "dry_run": True, "reason": "test"}
        client.create_order.assert_not_called()
        client.fetch_active_orders.assert_not_called()

    @pytest.mark.asyncio
    async def test_actual_close_buy_side_sells(self):
        client = MagicMock()
        client.fetch_active_orders.return_value = []
        client.create_order.return_value = {"id": "close-id-1"}
        monitor = SLMonitor(logger=MagicMock(), dry_run=False)

        result = await monitor.emergency_market_close(
            entry_side="buy",
            amount=0.015,
            reason="canceled_unfilled",
            bitbank_client=client,
        )
        assert result is not None
        assert result["order_id"] == "close-id-1"
        assert result["dry_run"] is False
        # buy ポジション → sell で決済
        client.create_order.assert_called_once()
        call_kwargs = client.create_order.call_args.kwargs
        assert call_kwargs["side"] == "sell"
        assert call_kwargs["order_type"] == "market"
        assert call_kwargs["is_closing_order"] is True
        assert call_kwargs["entry_position_side"] == "long"

    @pytest.mark.asyncio
    async def test_actual_close_sell_side_buys(self):
        client = MagicMock()
        client.fetch_active_orders.return_value = []
        client.create_order.return_value = {"id": "close-id-2"}
        monitor = SLMonitor(logger=MagicMock(), dry_run=False)

        result = await monitor.emergency_market_close(
            entry_side="sell",
            amount=0.01,
            reason="timeout_24h",
            bitbank_client=client,
        )
        assert result["order_id"] == "close-id-2"
        call_kwargs = client.create_order.call_args.kwargs
        assert call_kwargs["side"] == "buy"
        assert call_kwargs["entry_position_side"] == "short"

    @pytest.mark.asyncio
    async def test_pre_cancels_active_orders(self):
        client = MagicMock()
        client.fetch_active_orders.return_value = [{"id": "A"}, {"id": "B"}]
        client.create_order.return_value = {"id": "close-id"}
        monitor = SLMonitor(logger=MagicMock(), dry_run=False)

        await monitor.emergency_market_close(
            entry_side="buy", amount=0.01, reason="x", bitbank_client=client
        )
        assert client.cancel_order.call_count == 2

    @pytest.mark.asyncio
    async def test_clears_sl_persistence(self):
        persistence = MagicMock()
        client = MagicMock()
        client.fetch_active_orders.return_value = []
        client.create_order.return_value = {"id": "close-id"}
        monitor = SLMonitor(logger=MagicMock(), sl_persistence=persistence, dry_run=False)

        await monitor.emergency_market_close(
            entry_side="buy", amount=0.01, reason="x", bitbank_client=client
        )
        persistence.clear.assert_called_once_with("buy")

    @pytest.mark.asyncio
    async def test_create_order_failure_returns_none(self):
        client = MagicMock()
        client.fetch_active_orders.return_value = []
        client.create_order.side_effect = RuntimeError("API down")
        monitor = SLMonitor(logger=MagicMock(), dry_run=False)

        result = await monitor.emergency_market_close(
            entry_side="buy", amount=0.01, reason="x", bitbank_client=client
        )
        assert result is None


# ============================================================
# SLHealthResult / default constants
# ============================================================


def test_default_timeout_constant():
    assert DEFAULT_SL_TIMEOUT_HOURS == 24


def test_sl_health_result_defaults():
    r = SLHealthResult(is_healthy=True)
    assert r.failure_reason is None
    assert r.requires_emergency_close is False
    assert r.order_info is None

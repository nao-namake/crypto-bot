"""Phase 87 C1/H1: SLMonitor テスト

SL CANCELED_UNFILLED 検出 + 緊急成行決済 + 24h タイムアウト判定の単体テスト。
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

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


class TestPhase89C7PlaceholderAndPersistentFailure:
    """Phase 89 C7: placeholder ID 検出 + fetch_order 連続失敗の緊急決済昇格"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("placeholder", ["existing", "EXISTING", "Existing", " existing "])
    async def test_placeholder_existing_triggers_emergency(self, placeholder):
        """sl_order_id='existing' 等の placeholder は即時緊急決済判定"""
        monitor = SLMonitor(logger=MagicMock())
        # fetch_order が呼ばれてはいけない（placeholder 検出で即 return）
        client = _make_client(raise_exc=AssertionError("fetch_order must not be called"))
        result = await monitor.check_sl_health(placeholder, None, client)
        assert result.is_healthy is False
        assert result.failure_reason == "placeholder_id"
        assert result.requires_emergency_close is True

    @pytest.mark.asyncio
    @pytest.mark.parametrize("placeholder", ["none", "null", "unknown"])
    async def test_placeholder_other_keywords_triggers_emergency(self, placeholder):
        """他の placeholder キーワードも検出"""
        monitor = SLMonitor(logger=MagicMock())
        client = _make_client(raise_exc=AssertionError("fetch_order must not be called"))
        result = await monitor.check_sl_health(placeholder, None, client)
        assert result.failure_reason == "placeholder_id"
        assert result.requires_emergency_close is True

    @pytest.mark.asyncio
    async def test_fetch_error_single_returns_healthy(self):
        """1 回の fetch_error では既存挙動どおり healthy 返却"""
        monitor = SLMonitor(logger=MagicMock(), max_fetch_failures=3)
        client = _make_client(raise_exc=RuntimeError("transient"))
        result = await monitor.check_sl_health("OID-PERSIST", None, client)
        assert result.is_healthy is True
        assert result.failure_reason == "fetch_error"
        assert monitor._fetch_failure_counts["OID-PERSIST"] == 1

    @pytest.mark.asyncio
    async def test_fetch_error_repeated_triggers_emergency(self):
        """同一 ID で連続失敗 max_fetch_failures 回 → 緊急決済昇格"""
        monitor = SLMonitor(logger=MagicMock(), max_fetch_failures=3)
        client = _make_client(raise_exc=RuntimeError("API down"))

        r1 = await monitor.check_sl_health("OID-FAIL", None, client)
        r2 = await monitor.check_sl_health("OID-FAIL", None, client)
        r3 = await monitor.check_sl_health("OID-FAIL", None, client)

        assert r1.is_healthy is True
        assert r2.is_healthy is True
        assert r3.is_healthy is False
        assert r3.failure_reason == "fetch_error_persistent"
        assert r3.requires_emergency_close is True
        # 緊急決済判定後はカウンタリセット（次回以降の重複発動防止）
        assert "OID-FAIL" not in monitor._fetch_failure_counts

    @pytest.mark.asyncio
    async def test_fetch_success_resets_failure_counter(self):
        """fetch_order 成功で連続失敗カウンタがリセット"""
        monitor = SLMonitor(logger=MagicMock(), max_fetch_failures=3)
        fail_client = _make_client(raise_exc=RuntimeError("transient"))
        ok_client = _make_client({"info": {"status": "ACTIVE"}})
        recent = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()

        await monitor.check_sl_health("OID-RESET", recent, fail_client)
        await monitor.check_sl_health("OID-RESET", recent, fail_client)
        assert monitor._fetch_failure_counts["OID-RESET"] == 2

        result = await monitor.check_sl_health("OID-RESET", recent, ok_client)
        assert result.is_healthy is True
        assert "OID-RESET" not in monitor._fetch_failure_counts

    @pytest.mark.asyncio
    async def test_max_fetch_failures_configurable(self):
        """max_fetch_failures=1 で 1 回目から緊急決済"""
        monitor = SLMonitor(logger=MagicMock(), max_fetch_failures=1)
        client = _make_client(raise_exc=RuntimeError("API down"))
        result = await monitor.check_sl_health("OID-AGGRESSIVE", None, client)
        assert result.is_healthy is False
        assert result.failure_reason == "fetch_error_persistent"
        assert result.requires_emergency_close is True


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
# Phase 90η: 緊急決済前ポジション残量ガード（誤発火率100%の根本修正）
# ============================================================

# get_threshold をパッチして設定非依存にする（enabled=true / ratio=0.5）
_GUARD_CFG = {"enabled": True, "position_exists_threshold_ratio": 0.5}


def _guard_threshold(key, default=None):
    # Phase 90θ: 連続検出カウンタ閾値は int を返す（dict の _GUARD_CFG を返すと int() で失敗）
    if key.endswith("max_canceled_unfilled_retries"):
        return 3
    if "position_close_guard" in key:
        return _GUARD_CFG
    return default


def _make_client_with_positions(order_response, positions=None, pos_exc=None):
    """fetch_order + fetch_margin_positions(async) を備えた擬似 BitbankClient"""
    client = MagicMock()
    client.fetch_order.return_value = order_response
    if pos_exc is not None:
        client.fetch_margin_positions = AsyncMock(side_effect=pos_exc)
    else:
        client.fetch_margin_positions = AsyncMock(
            return_value=positions if positions is not None else []
        )
    return client


class TestPhase90EtaPositionGuard:
    """緊急決済の前に実ポジ残量を確認し、既決済を canceled_unfilled 等と誤判定しない"""

    @pytest.mark.asyncio
    @patch("src.trading.execution.sl_monitor.get_threshold", side_effect=_guard_threshold)
    async def test_canceled_unfilled_but_position_closed_skips(self, _gt):
        """CANCELED_UNFILLED 検出でも建玉消滅なら既決済とみなしスキップ"""
        monitor = SLMonitor(logger=MagicMock())
        client = _make_client_with_positions(
            {"info": {"status": "CANCELED_UNFILLED"}}, positions=[]
        )
        result = await monitor.check_sl_health("OID-H1", None, client, amount=0.015)
        assert result.is_healthy is True
        assert result.failure_reason == "already_closed"
        assert result.requires_emergency_close is False

    @pytest.mark.asyncio
    @patch("src.trading.execution.sl_monitor.get_threshold", side_effect=_guard_threshold)
    async def test_canceled_unfilled_position_remains_escalates_after_retries(self, _gt):
        """Phase 90θ: CANCELED_UNFILLED + 建玉残あり → 即発火せず N 回連続でのみ緊急決済へ昇格。

        CANCELED_UNFILLED は stop約定の中間状態で建玉が一時残存するため、1回目は pending、
        max_canceled_unfilled_retries(=3) 回連続で残存し続けた時のみ真の裸ポジと判定する。
        """
        monitor = SLMonitor(logger=MagicMock())
        client = _make_client_with_positions(
            {"info": {"status": "CANCELED_UNFILLED"}},
            positions=[{"side": "long", "amount": 0.015}],
        )
        # 1回目・2回目は pending（誤発火させない）
        for _ in range(2):
            result = await monitor.check_sl_health("OID-H2", None, client, amount=0.015)
            assert result.is_healthy is True
            assert result.failure_reason == "canceled_unfilled_pending"
            assert result.requires_emergency_close is False
        # 3回目（max 到達）で真の裸ポジと判定し緊急決済へ昇格
        result = await monitor.check_sl_health("OID-H2", None, client, amount=0.015)
        assert result.is_healthy is False
        assert result.failure_reason == "canceled_unfilled"
        assert result.requires_emergency_close is True

    @pytest.mark.asyncio
    @patch("src.trading.execution.sl_monitor.get_threshold", side_effect=_guard_threshold)
    async def test_canceled_unfilled_pending_resets_when_position_closes(self, _gt):
        """Phase 90θ: pending 途中で建玉消滅 → already_closed スキップ + カウンタリセット"""
        monitor = SLMonitor(logger=MagicMock())
        remains = _make_client_with_positions(
            {"info": {"status": "CANCELED_UNFILLED"}},
            positions=[{"side": "long", "amount": 0.015}],
        )
        # 1回目: 残存 → pending（カウント=1）
        r1 = await monitor.check_sl_health("OID-H2b", None, remains, amount=0.015)
        assert r1.failure_reason == "canceled_unfilled_pending"
        # 2回目: 建玉消滅 → already_closed スキップ
        closed = _make_client_with_positions(
            {"info": {"status": "CANCELED_UNFILLED"}}, positions=[]
        )
        r2 = await monitor.check_sl_health("OID-H2b", None, closed, amount=0.015)
        assert r2.failure_reason == "already_closed"
        assert r2.requires_emergency_close is False
        # カウンタがリセットされている（内部状態確認）
        assert "OID-H2b" not in monitor._canceled_unfilled_counts

    @pytest.mark.asyncio
    @patch("src.trading.execution.sl_monitor.get_threshold", side_effect=_guard_threshold)
    async def test_canceled_unfilled_counter_resets_on_recovery(self, _gt):
        """Phase 90θ: pending 後に SL が ACTIVE 復帰 → カウンタリセットで誤発火しない"""
        monitor = SLMonitor(logger=MagicMock())
        remains = _make_client_with_positions(
            {"info": {"status": "CANCELED_UNFILLED"}},
            positions=[{"side": "long", "amount": 0.015}],
        )
        await monitor.check_sl_health("OID-H2c", None, remains, amount=0.015)  # pending(1)
        # SL が ACTIVE に復帰
        active = _make_client_with_positions({"info": {"status": "ACTIVE"}}, positions=[])
        recent = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        r = await monitor.check_sl_health("OID-H2c", recent, active, amount=0.015)
        assert r.is_healthy is True
        assert r.requires_emergency_close is False
        assert "OID-H2c" not in monitor._canceled_unfilled_counts

    @pytest.mark.asyncio
    @patch("src.trading.execution.sl_monitor.get_threshold", side_effect=_guard_threshold)
    async def test_expired_position_closed_skips(self, _gt):
        monitor = SLMonitor(logger=MagicMock())
        client = _make_client_with_positions({"info": {"status": "EXPIRED"}}, positions=[])
        result = await monitor.check_sl_health("OID-H3", None, client, amount=0.015)
        assert result.is_healthy is True
        assert result.failure_reason == "already_closed"

    @pytest.mark.asyncio
    @patch("src.trading.execution.sl_monitor.get_threshold", side_effect=_guard_threshold)
    async def test_rejected_always_triggers_emergency(self, _gt):
        """Phase 90θ: REJECTED は「注文却下＝SL未配置・ポジ健在」で中間状態を経由しないため、
        残量ガードを通さず無条件に緊急決済必須。実0でも既決済スキップしない（逆リスク回避）。"""
        monitor = SLMonitor(logger=MagicMock())
        # 実ポジ0でも REJECTED は緊急決済必須（ガードを通さない）
        closed = _make_client_with_positions({"info": {"status": "REJECTED"}}, positions=[])
        r_closed = await monitor.check_sl_health("OID-H4", None, closed, amount=0.015)
        assert r_closed.is_healthy is False
        assert r_closed.failure_reason == "rejected"
        assert r_closed.requires_emergency_close is True
        # ガードを通さない＝ポジ残量確認は呼ばれない
        closed.fetch_margin_positions.assert_not_called()
        # 実ポジ残存でも当然緊急決済必須
        remains = _make_client_with_positions(
            {"info": {"status": "REJECTED"}}, positions=[{"side": "long", "amount": 0.015}]
        )
        r_remains = await monitor.check_sl_health("OID-H4b", None, remains, amount=0.015)
        assert r_remains.failure_reason == "rejected"
        assert r_remains.requires_emergency_close is True

    @pytest.mark.asyncio
    @patch("src.trading.execution.sl_monitor.get_threshold", side_effect=_guard_threshold)
    async def test_position_fetch_failure_suppresses_emergency(self, _gt):
        """フェイルセーフ=抑止優先: 残量取得失敗時は緊急決済を見送る（既決済扱い）"""
        monitor = SLMonitor(logger=MagicMock())
        client = _make_client_with_positions(
            {"info": {"status": "CANCELED_UNFILLED"}}, pos_exc=RuntimeError("API down")
        )
        result = await monitor.check_sl_health("OID-H5", None, client, amount=0.015)
        assert result.is_healthy is True
        assert result.failure_reason == "already_closed"
        assert result.requires_emergency_close is False

    @pytest.mark.asyncio
    async def test_amount_none_keeps_legacy_emergency(self):
        """amount 未指定（既存呼び出し）はガード未実行で従来の緊急決済（後方互換）"""
        monitor = SLMonitor(logger=MagicMock())
        client = _make_client_with_positions(
            {"info": {"status": "CANCELED_UNFILLED"}}, positions=[]
        )
        result = await monitor.check_sl_health("OID-H6", None, client)  # amount 未指定
        assert result.is_healthy is False
        assert result.failure_reason == "canceled_unfilled"
        assert result.requires_emergency_close is True
        # ガード未実行＝ポジ取得は呼ばれない
        client.fetch_margin_positions.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.trading.execution.sl_monitor.get_threshold", side_effect=_guard_threshold)
    async def test_partial_fill_below_ratio_treated_as_closed(self, _gt):
        """残量が期待の 0.5 倍未満なら既決済扱い（0.004 < 0.015*0.5=0.0075）"""
        monitor = SLMonitor(logger=MagicMock())
        client = _make_client_with_positions(
            {"info": {"status": "CANCELED_UNFILLED"}},
            positions=[{"side": "long", "amount": 0.004}],
        )
        result = await monitor.check_sl_health("OID-H7", None, client, amount=0.015)
        assert result.is_healthy is True
        assert result.failure_reason == "already_closed"

    @pytest.mark.asyncio
    @patch("src.trading.execution.sl_monitor.get_threshold", side_effect=_guard_threshold)
    async def test_timeout_24h_with_position_remains(self, _gt):
        """timeout_24h 経路も残ありなら緊急決済（ガード適用しても残ありで発動）"""
        monitor = SLMonitor(logger=MagicMock(), timeout_hours=24)
        client = _make_client_with_positions(
            {"info": {"status": "ACTIVE"}},
            positions=[{"side": "long", "amount": 0.015}],
        )
        old = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        result = await monitor.check_sl_health("OID-H8", old, client, amount=0.015)
        assert result.is_healthy is False
        assert result.failure_reason == "timeout_24h"
        assert result.requires_emergency_close is True


# ============================================================
# Phase 90μ: C7 fetch_error_persistent 昇格に残量ガードを対称適用
# ============================================================


def _make_fetch_error_client(positions=None):
    """fetch_order が常に失敗し、fetch_margin_positions を備えた擬似 BitbankClient"""
    client = MagicMock()
    client.fetch_order.side_effect = RuntimeError("注文が見つかりません: market_close_123")
    client.fetch_margin_positions = AsyncMock(
        return_value=positions if positions is not None else []
    )
    return client


class TestPhase90MuFetchErrorPositionGuard:
    """Phase 90μ: fetch_error_persistent 昇格でもポジ既消滅なら緊急決済を抑止する。

    合成ID market_close_* を fetch_order できず3連続失敗するが建玉は既に0、という
    誤発火（Fire #2）を止める。canceled_unfilled / expired / timeout と同じ残量ガードを通す。
    """

    @pytest.mark.asyncio
    @patch("src.trading.execution.sl_monitor.get_threshold", side_effect=_guard_threshold)
    async def test_fetch_error_persistent_but_position_closed_skips(self, _gt):
        """3連続失敗（実0）→ already_closed・緊急決済抑止"""
        monitor = SLMonitor(logger=MagicMock(), max_fetch_failures=3)
        client = _make_fetch_error_client(positions=[])
        r1 = await monitor.check_sl_health("market_close_123", None, client, amount=0.015)
        r2 = await monitor.check_sl_health("market_close_123", None, client, amount=0.015)
        r3 = await monitor.check_sl_health("market_close_123", None, client, amount=0.015)
        assert r1.requires_emergency_close is False  # 1/3 fetch_error
        assert r2.requires_emergency_close is False  # 2/3 fetch_error
        # 3/3 到達でもポジ既消滅 → 抑止
        assert r3.is_healthy is True
        assert r3.failure_reason == "already_closed"
        assert r3.requires_emergency_close is False

    @pytest.mark.asyncio
    @patch("src.trading.execution.sl_monitor.get_threshold", side_effect=_guard_threshold)
    async def test_fetch_error_persistent_position_remains_escalates(self, _gt):
        """3連続失敗かつ建玉残存 → 従来どおり fetch_error_persistent で緊急決済昇格"""
        monitor = SLMonitor(logger=MagicMock(), max_fetch_failures=3)
        client = _make_fetch_error_client(positions=[{"side": "long", "amount": 0.015}])
        for _ in range(2):
            await monitor.check_sl_health("OID-MU", None, client, amount=0.015)
        result = await monitor.check_sl_health("OID-MU", None, client, amount=0.015)
        assert result.is_healthy is False
        assert result.failure_reason == "fetch_error_persistent"
        assert result.requires_emergency_close is True

    @pytest.mark.asyncio
    async def test_fetch_error_persistent_amount_none_keeps_legacy(self):
        """amount 未指定（既存呼び出し）はガード未実行で従来の緊急決済昇格（後方互換）"""
        monitor = SLMonitor(logger=MagicMock(), max_fetch_failures=1)
        client = _make_fetch_error_client(positions=[])
        result = await monitor.check_sl_health("OID-MU-LEGACY", None, client)  # amount 未指定
        assert result.is_healthy is False
        assert result.failure_reason == "fetch_error_persistent"
        assert result.requires_emergency_close is True
        client.fetch_margin_positions.assert_not_called()


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

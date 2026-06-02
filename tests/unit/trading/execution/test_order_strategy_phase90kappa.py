"""Phase 90κ: Maker注文のリトライ実動化 + best気配追従テスト。

旧実装は初回試行に残り総時間(~120秒)をフルで渡し、試行1回で全体timeoutを消費して
リトライに進まなかった（30日データで試行2が2件のみ=max_retries=5が機能せず）。また
リトライ時の価格調整が「板の奥へ」で約定から遠ざかっていた。本テストは:
- per_attempt 分割でリトライが実際に max_retries 回まわること
- リトライ毎に最新 best 気配を再取得して価格追従すること
- 初期価格からの乖離上限ガードが効くこと
を検証する。
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.trading.execution.order_strategy import OrderStrategy

_GT = "src.trading.execution.order_strategy.get_threshold"


def _cfg(max_retries=4, timeout=60, max_adj=0.1):
    return {
        "max_retries": max_retries,
        "retry_interval_ms": 0,
        "timeout_seconds": timeout,
        "price_adjustment_tick": 5,
        "max_price_adjustment_ratio": max_adj,
    }


def _make_strategy(fill=None, conditions=None):
    os_ = OrderStrategy()
    os_.logger = Mock()
    os_._wait_for_maker_fill = AsyncMock(return_value=fill)
    os_._assess_maker_conditions = AsyncMock(
        return_value=conditions or {"maker_viable": True, "best_bid": 100.0, "best_ask": 102.0}
    )
    os_._resolve_fill_type = AsyncMock(return_value=("maker", 0.0))
    return os_


def _client():
    c = Mock()
    c.create_order = Mock(return_value={"id": "OID"})
    c.cancel_order = Mock()
    return c


class TestPhase90KappaRetry:
    @pytest.mark.asyncio
    @patch(_GT)
    async def test_retries_actually_loop(self, mock_gt):
        """未約定が続くと create_order が max_retries 回呼ばれる（真因A回帰防止）。"""
        mock_gt.return_value = _cfg(max_retries=4)
        os_ = _make_strategy(fill=None)
        client = _client()
        result = await os_.execute_maker_order("BTC/JPY", "buy", 0.015, {"price": 100.0}, client)
        assert result is None
        assert client.create_order.call_count == 4

    @pytest.mark.asyncio
    @patch(_GT)
    async def test_per_attempt_timeout_passed(self, mock_gt):
        """_wait_for_maker_fill に per_attempt_timeout(=timeout//max_retries) が渡る。"""
        mock_gt.return_value = _cfg(max_retries=4, timeout=60)
        os_ = _make_strategy(fill=None)
        client = _client()
        await os_.execute_maker_order("BTC/JPY", "buy", 0.015, {"price": 100.0}, client)
        first_call = os_._wait_for_maker_fill.call_args_list[0]
        # args: (order_id, symbol, wait_timeout, bitbank_client)
        assert first_call.args[2] == 15  # 60 // 4

    @pytest.mark.asyncio
    @patch(_GT)
    async def test_retry_refetches_orderbook_and_follows_best(self, mock_gt):
        """リトライ毎に板を再取得し、price が最新 best へ追従する（真因B）。"""
        mock_gt.return_value = _cfg(max_retries=4, max_adj=0.1)
        os_ = _make_strategy(fill=None)
        client = _client()
        await os_.execute_maker_order("BTC/JPY", "buy", 0.015, {"price": 100.0}, client)
        assert os_._assess_maker_conditions.call_count >= 1
        # 2回目の create_order は best 追従後の価格（buy: best_bid 100 + improvement 1 = 101）
        second_price = client.create_order.call_args_list[1].kwargs["price"]
        assert second_price == 101

    @pytest.mark.asyncio
    @patch(_GT)
    async def test_max_adjustment_ratio_aborts(self, mock_gt):
        """板が乖離上限を超えて動いたら中止（create_order は初回のみ）。"""
        mock_gt.return_value = _cfg(max_retries=4, max_adj=0.001)  # 0.1%
        # 初期100に対し best_bid=200（大きく乖離）
        os_ = _make_strategy(
            fill=None,
            conditions={"maker_viable": True, "best_bid": 200.0, "best_ask": 202.0},
        )
        client = _client()
        result = await os_.execute_maker_order("BTC/JPY", "buy", 0.015, {"price": 100.0}, client)
        assert result is None
        assert client.create_order.call_count == 1

    @pytest.mark.asyncio
    @patch(_GT)
    async def test_fills_on_first_attempt(self, mock_gt):
        """初回試行で約定したら即成功 return（create_order 1回）。"""
        mock_gt.return_value = _cfg()
        os_ = _make_strategy(fill={"price": 100.0, "amount": 0.015})
        client = _client()
        result = await os_.execute_maker_order("BTC/JPY", "buy", 0.015, {"price": 100.0}, client)
        assert result is not None
        assert result.success is True
        assert client.create_order.call_count == 1

    @pytest.mark.asyncio
    @patch(_GT)
    async def test_retry_aborts_when_maker_not_viable(self, mock_gt):
        """リトライ時の板再取得で maker_viable=False なら中止。"""
        mock_gt.return_value = _cfg()
        os_ = _make_strategy(
            fill=None, conditions={"maker_viable": False, "disable_reason": "high_volatility"}
        )
        client = _client()
        result = await os_.execute_maker_order("BTC/JPY", "buy", 0.015, {"price": 100.0}, client)
        assert result is None
        assert client.create_order.call_count == 1

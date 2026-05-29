"""Phase 90δ: 決済発注前ポジション存在確認（50062 レース対策）テスト。

SL トリガー成行決済（Phase 64.12）等で同サイクル内に建玉が既に消滅している場合、
消滅済みポジへの重複決済発注が bitbank 50062「保有建玉数量超過」を誘発していた。
_execute_position_exit の発注直前にポジ再確認ガードを追加し、消滅検出時は発注を
スキップして「既決済」として正常終了する。フェイルオープン（確認 API 失敗時は決済続行）。
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.trading.execution.stop_manager import StopManager


def _make_client(positions, raise_on_fetch=False):
    client = AsyncMock()
    if raise_on_fetch:
        client.fetch_margin_positions = AsyncMock(side_effect=Exception("api down"))
    else:
        client.fetch_margin_positions = AsyncMock(return_value=positions)
    # create_order は asyncio.to_thread 経由で同期呼び出しされるため同期 Mock
    client.create_order = Mock(return_value={"id": "close_1"})
    return client


def _position():
    return {
        "order_id": "o1",
        "side": "buy",
        "amount": 0.001,
        "price": 14_000_000.0,
    }


class TestPhase90DeltaPositionExitGuard:
    """決済発注前ポジ再確認ガードの分岐検証。"""

    @pytest.mark.asyncio
    async def test_skips_order_when_position_vanished(self):
        sm = StopManager()
        client = _make_client([])  # 建玉消滅
        result = await sm._execute_position_exit(
            _position(), 13_900_000.0, "stop_loss", "live", client
        )
        assert result.success is True
        assert "exit_already_closed" in result.order_id
        client.create_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_places_order_when_position_exists(self):
        sm = StopManager()
        client = _make_client([{"amount": 0.001}])  # 建玉あり
        await sm._execute_position_exit(_position(), 13_900_000.0, "stop_loss", "live", client)
        client.create_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_places_order_when_partial_remains(self):
        sm = StopManager()
        # 0.6× 期待量（0.0006 >= 0.001 * 0.5）→ 閾値以上で決済続行
        client = _make_client([{"amount": 0.0006}])
        await sm._execute_position_exit(_position(), 13_900_000.0, "stop_loss", "live", client)
        client.create_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_fail_open_on_fetch_error(self):
        sm = StopManager()
        client = _make_client(None, raise_on_fetch=True)  # 確認 API 失敗
        await sm._execute_position_exit(_position(), 13_900_000.0, "stop_loss", "live", client)
        # フェイルオープン: 決済を取りこぼさず続行
        client.create_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_guard_disabled_skips_check(self):
        sm = StopManager()
        client = _make_client([])  # 建玉消滅だがガード無効なら発注する

        def gt(key, default=None):
            if key == "position_management.position_exit_guard":
                return {"enabled": False, "position_exists_threshold_ratio": 0.5}
            return default

        with patch("src.trading.execution.stop_manager.get_threshold", side_effect=gt):
            await sm._execute_position_exit(_position(), 13_900_000.0, "stop_loss", "live", client)
        client.create_order.assert_called_once()

"""
Phase 89-δ: BitbankClient の WebSocket ライフサイクル + マルチペア基盤テスト 5 件
"""

import os
from unittest.mock import MagicMock, patch

import pytest

# bitbank API 認証情報なしでも初期化エラーを回避するため、環境変数を mock
os.environ.setdefault("BITBANK_API_KEY", "test_key_for_unit_tests")
os.environ.setdefault("BITBANK_API_SECRET", "test_secret_for_unit_tests")

from src.data.bitbank_client import BitbankClient
from src.data.bitbank_websocket_client import reset_bitbank_websocket_client


@pytest.fixture(autouse=True)
def _reset_ws_singleton():
    reset_bitbank_websocket_client()
    yield
    reset_bitbank_websocket_client()


@pytest.fixture
def client():
    """BitbankClient（テスト用・ccxt は実初期化されるが API 呼び出しはしない）."""
    return BitbankClient(api_key="test", api_secret="test", leverage=1.0)


def test_get_websocket_client_returns_singleton(client):
    """get_websocket_client は遅延初期化シングルトンを返す."""
    ws1 = client.get_websocket_client()
    ws2 = client.get_websocket_client()
    assert ws1 is not None
    assert ws1 is ws2


@pytest.mark.asyncio
async def test_disconnect_websocket_when_not_connected(client):
    """未接続状態で disconnect_websocket() を呼んでもエラーなし."""
    await client.disconnect_websocket()
    assert client._ws_task is None


@pytest.mark.asyncio
async def test_connect_websocket_skips_when_already_running(client):
    """既に task 起動中なら 2 回目の connect は False を返す."""
    import asyncio

    ws = client.get_websocket_client()

    async def fake_long_connect():
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            pass

    ws.connect = fake_long_connect

    try:
        r1 = await client.connect_websocket()
        assert r1 is True
        assert client._ws_task is not None
        r2 = await client.connect_websocket()
        assert r2 is False
    finally:
        # task キャンセル（CancelledError は catch）
        if client._ws_task and not client._ws_task.done():
            client._ws_task.cancel()
            try:
                await client._ws_task
            except (asyncio.CancelledError, Exception):
                pass
        client._ws_task = None

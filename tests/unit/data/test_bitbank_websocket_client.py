"""
Phase 89-δ: BitbankWebSocketClient テスト 12 件
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("websockets")

from src.data.bitbank_websocket_client import (
    BitbankWebSocketClient,
    get_bitbank_websocket_client,
    has_websockets,
    reset_bitbank_websocket_client,
)


@pytest.fixture(autouse=True)
def _reset_singleton():
    reset_bitbank_websocket_client()
    yield
    reset_bitbank_websocket_client()


def test_has_websockets_when_installed():
    assert has_websockets() is True


def test_initial_state():
    """新規クライアントは未接続・キャッシュ空."""
    client = BitbankWebSocketClient()
    assert client.is_connected() is False
    assert client.get_ticker() is None
    assert client.get_orderbook_diff() is None
    status = client.get_status()
    assert status["is_connected"] is False
    assert "ticker_btc_jpy" in status["subscribed_channels"]


def test_process_ticker_message_updates_cache():
    """Socket.IO ticker メッセージで cache 更新."""
    client = BitbankWebSocketClient()
    raw = (
        '42["message",{"room_name":"ticker_btc_jpy",'
        '"message":{"data":{"last":"12500000","buy":"12499000","sell":"12501000"}}}]'
    )
    client._process_message(raw)
    ticker = client.get_ticker("btc_jpy")
    assert ticker is not None
    assert ticker["last"] == "12500000"


def test_process_orderbook_diff_message_updates_cache():
    """Socket.IO orderbook diff メッセージで cache 更新."""
    client = BitbankWebSocketClient()
    raw = (
        '42["message",{"room_name":"depth_diff_btc_jpy",'
        '"message":{"data":{"b":[["12499000","0.5"]],"a":[["12501000","0.3"]]}}}]'
    )
    client._process_message(raw)
    diff = client.get_orderbook_diff("btc_jpy")
    assert diff is not None
    assert "b" in diff and "a" in diff


def test_process_heartbeat_message_ignored():
    """Socket.IO heartbeat ('3' / handshake) はキャッシュ更新しない."""
    client = BitbankWebSocketClient()
    client._process_message("3")  # heartbeat
    client._process_message("0{...}")  # handshake
    client._process_message("40")  # namespace connection
    assert client.get_ticker() is None
    assert client.get_orderbook_diff() is None


def test_process_malformed_json_safe():
    """不正 JSON でも例外を投げない（warning ログのみ）."""
    client = BitbankWebSocketClient()
    # 例外なく完了
    client._process_message("42[malformed")
    client._process_message("42null")
    client._process_message("42{}")
    # キャッシュ更新もされない
    assert client.get_ticker() is None


def test_bytes_message_decoded():
    """bytes でも UTF-8 デコードして処理."""
    client = BitbankWebSocketClient()
    raw_bytes = (
        b'42["message",{"room_name":"ticker_btc_jpy",' b'"message":{"data":{"last":"12500000"}}}]'
    )
    client._process_message(raw_bytes)
    ticker = client.get_ticker("btc_jpy")
    assert ticker is not None


def test_unknown_room_name_ignored():
    """未知の room_name は無視（ticker_ / depth_diff_ プレフィックス以外）."""
    client = BitbankWebSocketClient()
    raw = '42["message",{"room_name":"trades_btc_jpy","message":{"data":{"foo":1}}}]'
    client._process_message(raw)
    assert client.get_ticker() is None
    assert client.get_orderbook_diff() is None


def test_get_status_returns_full_info():
    """get_status は接続状態とサブスクライブチャンネルを返す."""
    client = BitbankWebSocketClient(channels=["ticker_btc_jpy"])
    status = client.get_status()
    assert status["is_connected"] is False
    assert status["subscribed_channels"] == ["ticker_btc_jpy"]
    assert status["ticker_symbols"] == []


def test_singleton_pattern():
    """get_bitbank_websocket_client() は同一インスタンスを返す."""
    c1 = get_bitbank_websocket_client()
    c2 = get_bitbank_websocket_client()
    assert c1 is c2
    reset_bitbank_websocket_client()
    c3 = get_bitbank_websocket_client()
    assert c3 is not c1


def test_thread_safety_concurrent_cache_access():
    """並行 _process_message + get_ticker でも例外なし."""
    import threading

    client = BitbankWebSocketClient()
    errors = []

    def writer():
        for i in range(50):
            raw = (
                f'42["message",{{"room_name":"ticker_btc_jpy",'
                f'"message":{{"data":{{"last":"{12500000 + i}"}}}}}}]'
            )
            try:
                client._process_message(raw)
            except Exception as e:
                errors.append(e)

    def reader():
        for _ in range(50):
            try:
                client.get_ticker()
                client.get_status()
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=writer) for _ in range(3)] + [
        threading.Thread(target=reader) for _ in range(3)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors


@pytest.mark.asyncio
async def test_disconnect_sets_stop_requested():
    """disconnect() で stop_requested フラグが True に."""
    client = BitbankWebSocketClient()
    assert client._stop_requested is False
    await client.disconnect()
    assert client._stop_requested is True

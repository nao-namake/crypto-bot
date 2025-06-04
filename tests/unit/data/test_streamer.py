# tests/unit/data/test_streamer.py
# テスト対象: crypto_bot/data/streamer.py
# 説明:
#   - RealTimeFetcherの主な機能（初期化、受信キュー、コールバック連携）のユニットテスト
#   - WebSocket通信部分はすべてモック化し、非同期IOもpytest-asyncioを利用

import json

import pytest

from crypto_bot.data.streamer import RealTimeFetcher


@pytest.mark.asyncio
async def test_realtimefetcher_enqueue_and_callback(monkeypatch):
    # モックWebSocket
    class DummyWS:
        def __init__(self):
            self.sent = []
            self._closed = False
            # サンプルTickデータをjson文字列で2件だけ返す
            self._messages = iter([
                json.dumps({"type": "trade", "price": 100}),
                json.dumps({"type": "trade", "price": 101}),
            ])

        async def send(self, msg):
            self.sent.append(msg)

        def __aiter__(self):
            return self

        async def __anext__(self):
            try:
                return next(self._messages)
            except StopIteration:
                raise StopAsyncIteration()

        async def close(self):
            self._closed = True

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self.close()

    # websockets.connectを差し替え
    async def mock_connect(url):
        return DummyWS()
    monkeypatch.setattr("websockets.connect", mock_connect)

    # コールバックのテスト用
    received_msgs = []

    def on_msg(data):
        received_msgs.append(data)

    fetcher = RealTimeFetcher(
        url="wss://dummy",
        symbol="BTCUSDT",
        on_message=on_msg
    )

    # connect, _recv_loopまで呼び出し
    await fetcher.connect()
    # WebSocketに正しいsubscribe送信
    assert fetcher._ws.sent
    assert "trade.BTCUSDT" in fetcher._ws.sent[0]

    # 受信ループ（2件だけ受信）
    await fetcher._recv_loop()

    # キューにも格納されている
    msg1 = await fetcher._queue.get()
    msg2 = await fetcher._queue.get()
    assert msg1["price"] == 100
    assert msg2["price"] == 101
    # コールバックも2回呼ばれている
    assert len(received_msgs) == 2
    assert received_msgs[0]["price"] == 100


@pytest.mark.asyncio
async def test_get_message():
    fetcher = RealTimeFetcher(url="wss://dummy", symbol="BTCUSDT")
    test_data = {"type": "trade", "price": 123}
    # 内部キューに直接put
    await fetcher._queue.put(test_data)
    msg = await fetcher.get_message()
    assert msg == test_data

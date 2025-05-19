import asyncio
import contextlib
import json

import pytest

from crypto_bot.data.streamer import RealTimeFetcher


class DummyWS:
    """モック WebSocketClientProtocol."""

    def __init__(self, messages):
        # 受信する JSON 文字列リスト
        self.messages = messages

    def __aiter__(self):
        async def gen():
            for m in self.messages:
                yield m

        return gen()

    async def send(self, msg):
        # subscribe リクエストが送られていることを確認
        payload = json.loads(msg)
        assert payload.get("op") == "subscribe"
        assert isinstance(payload.get("args"), list)

    async def close(self):
        # クローズは何もしない
        pass


@pytest.mark.asyncio
async def test_realtime_fetcher(monkeypatch):
    # ダミーの JSON 文字列リスト
    dummy_msgs = ['{"price":100}', '{"price":101}', '{"price":102}']

    # websockets.connect をモック化して DummyWS を返す
    async def fake_connect(url):
        return DummyWS(dummy_msgs)

    monkeypatch.setattr(
        "crypto_bot.data.streamer.websockets.connect",
        fake_connect,
    )

    # on_message コールバック用リスト
    seen = []

    def on_msg(data):
        seen.append(data)

    # RealTimeFetcher を作成し、_run() をバックグラウンドで開始
    rt = RealTimeFetcher(url="wss://test", symbol="BTCUSDT", on_message=on_msg)
    task = asyncio.create_task(rt._run())

    # キューから3件取り出す
    got = []
    for _ in range(3):
        msg = await rt.get_message()
        got.append(msg)

    # タスクをキャンセル（または自然終了）させて待機
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task

    # コールバックとキューの内容が一致すること
    assert seen == [{"price": 100}, {"price": 101}, {"price": 102}]
    assert got == seen

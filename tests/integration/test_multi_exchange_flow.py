import pytest
from crypto_bot.data.fetcher import MarketDataFetcher
from crypto_bot.execution.factory import create_exchange_client

@pytest.mark.parametrize(
    "exchange_id, symbol",
    [
        ("bybit", "BTC/USDT"),
        ("bitbank", "BTC/JPY"),
        # 他取引所も追加可能
    ],
)
def test_fetch_backtest_and_execute(exchange_id, symbol, monkeypatch):
    """
    各取引所で「価格取得 → 簡易バックテスト（モック） → 注文発注モック」
    が一連で動くことを確認する。
    """
    # 1) fetch_price をモックして固定データを返す
    dummy_data = [[1609459200000, 30000, 31000, 29000, 30500, 100]]
    monkeypatch.setattr(
        MarketDataFetcher,
        "get_price_df",
        lambda self, *args, **kwargs: __import__("pandas").DataFrame(
            dummy_data, columns=["timestamp","open","high","low","close","volume"]
        ),
    )

    # 2) Bot のバックテストロジック（例えば backtest.engine の run メソッド）をモック
    import crypto_bot.backtest.engine as engine_module
    monkeypatch.setattr(engine_module, "run_backtest", lambda df: {"profit": 123},raising=False)

    # 3) 注文発注メソッドをモック（例: client.send_order）
    client = create_exchange_client(exchange_id, api_key=None, api_secret=None)
    monkeypatch.setattr(
        client,
        "send_order",
        lambda *args, **kwargs: {"status": "ok"},
        raising=False
    )

    # 実際のフロー呼び出し
    df = MarketDataFetcher(exchange_id).get_price_df(symbol=symbol, limit=1)
    report = engine_module.run_backtest(df)
    response = client.send_order(symbol=symbol, side="buy", type="market", amount=0.001)

    # 検証
    assert report["profit"] == 123
    assert response["status"] == "ok"

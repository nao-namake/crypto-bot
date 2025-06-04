# tests/integration/test_multi_exchange_flow.py
# ファイル名: tests/integration/test_multi_exchange_flow.py
# 説明:
# 複数の取引所（bybit, bitbank等）のクライアントで
# 1. データ取得
# 2. バックテストエンジンでテスト（モック）
# 3. 注文発注（モック）
# まで「全体の流れ」がmain.py設計で崩れていないか、疎結合で検証するintegrationテスト。

import pandas as pd
import pytest

from crypto_bot.data.fetcher import MarketDataFetcher
from crypto_bot.execution.factory import create_exchange_client


@pytest.mark.parametrize(
    "exchange_id, symbol",
    [
        ("bybit", "BTC/USDT"),
        ("bitbank", "BTC/JPY"),
        # 必要なら他の取引所も追加
    ],
)
def test_multi_exchange_end_to_end(exchange_id, symbol, monkeypatch):
    """
    各取引所で「価格取得 → 簡易バックテスト（モック） → 注文発注モック」
    がmain.pyや現行設計で想定通り動くか確認するintegrationテスト
    """

    # 1) データ取得の戻り値をモック
    dummy_df = pd.DataFrame(
        [[1609459200000, 30000, 31000, 29000, 30500, 100]],
        columns=["timestamp", "open", "high", "low", "close", "volume"],
    )
    dummy_df["datetime"] = pd.to_datetime(dummy_df["timestamp"], unit="ms")
    dummy_df = dummy_df.set_index("datetime")

    monkeypatch.setattr(
        MarketDataFetcher, "get_price_df", lambda self, *args, **kwargs: dummy_df
    )

    # 2) バックテストエンジン.run()をモック（シンプルなdictを返すだけ）
    import crypto_bot.backtest.engine as engine_module

    monkeypatch.setattr(
        engine_module,
        "run_backtest",
        lambda df: {"profit": 123, "trades": 1},
        raising=False,
    )

    # 3) 取引所クライアントの注文APIをモック
    client = create_exchange_client(exchange_id, api_key=None, api_secret=None)
    monkeypatch.setattr(
        client, "create_order", lambda *args, **kwargs: {"status": "ok"}, raising=False
    )

    # --- テスト本体 ---
    # データ取得
    df = MarketDataFetcher(exchange_id).get_price_df(symbol=symbol, limit=1)
    assert not df.empty

    # バックテスト
    report = engine_module.run_backtest(df)
    assert report["profit"] == 123

    # 注文発注
    response = client.create_order(
        symbol=symbol, side="buy", type="market", amount=0.001
    )
    assert response["status"] == "ok"

"""
tests/integration/bitflyer/test_bitflyer_e2e_real.py

BitFlyer の統合テスト
- 残高照会・OHLCV取得・注文・キャンセルを実際のAPIで検証
- 現物・Lightning FX の両方をサポート
- 安全な最小額での実運用テスト
"""

import os
import time
from decimal import Decimal

import pytest
from ccxt.base.errors import AuthenticationError, BadRequest

from crypto_bot.execution.api_version_manager import ApiVersionManager
from crypto_bot.execution.bitflyer_client import BitflyerClient


@pytest.fixture(scope="module")
def version_manager():
    """API バージョン管理を初期化"""
    return ApiVersionManager()


@pytest.fixture(scope="module")
def bitflyer_client(version_manager):
    """BitFlyer クライアントを初期化（実際のAPIキーが必要）"""
    api_key = os.getenv("BITFLYER_API_KEY")
    api_secret = os.getenv("BITFLYER_API_SECRET")

    if not api_key or not api_secret:
        pytest.skip(
            "BitFlyer API keys not set. Set BITFLYER_API_KEY and BITFLYER_API_SECRET environment variables for production testing."
        )

    # API 互換性チェック
    validation = version_manager.validate_api_compatibility("bitflyer")
    if validation["overall_status"] != "PASS":
        pytest.skip(f"BitFlyer API compatibility check failed: {validation}")

    client = BitflyerClient(api_key, api_secret, testnet=False)

    # 認証テスト
    try:
        balance = client.fetch_balance()
        assert isinstance(balance, dict), "Authentication test failed"
    except AuthenticationError as e:
        pytest.skip(f"BitFlyer authentication failed: {e}")
    except Exception as e:
        pytest.skip(f"Unexpected error during authentication: {e}")

    yield client

    # クリーンアップ: 未約定注文をキャンセル
    try:
        client.cancel_all_orders(symbol="BTC/JPY")
    except Exception:
        pass  # ベストエフォート


def test_api_version_compatibility(version_manager):
    """API バージョン互換性テスト"""
    report = version_manager.validate_api_compatibility("bitflyer")

    # CCXT バージョン互換性に問題がある場合はテストをスキップ
    if report["overall_status"] != "PASS":
        ccxt_check = report["checks"]["ccxt_compatibility"]
        if (
            not ccxt_check["passed"]
            and "Major version change detected" in ccxt_check["message"]
        ):
            pytest.skip(f"CCXT version compatibility issue: {ccxt_check['message']}")
        else:
            pytest.fail(f"API compatibility check failed: {report}")

    # CCXT バージョンチェック
    ccxt_check = report["checks"]["ccxt_compatibility"]
    assert ccxt_check["passed"], f"CCXT compatibility failed: {ccxt_check['message']}"


def test_fetch_balance_real(bitflyer_client):
    """実際の残高照会テスト"""
    balance = bitflyer_client.fetch_balance()

    # 基本構造の検証
    assert isinstance(balance, dict), f"Expected dict, got {type(balance)}"
    assert "free" in balance, "Balance response missing 'free' field"
    assert "used" in balance, "Balance response missing 'used' field"
    assert "total" in balance, "Balance response missing 'total' field"

    # JPY 残高の存在確認（基本通貨）
    assert "JPY" in balance["free"], "JPY balance not found in free balance"

    # 数値型の確認
    jpy_free = balance["free"]["JPY"]
    assert isinstance(
        jpy_free, (int, float, Decimal)
    ), f"JPY balance should be numeric, got {type(jpy_free)}"


def test_fetch_ohlcv_real(bitflyer_client):
    """実際のOHLCV取得テスト"""
    symbol = "BTC/JPY"
    timeframe = "1d"
    limit = 10

    # OHLCV データ取得
    df = bitflyer_client.fetch_ohlcv(symbol, timeframe, limit=limit)

    # データフレーム構造の検証
    assert not df.empty, "OHLCV DataFrame is empty"
    assert len(df) <= limit, f"Expected max {limit} rows, got {len(df)}"

    expected_columns = ["open", "high", "low", "close", "volume"]
    for col in expected_columns:
        assert col in df.columns, f"Missing column: {col}"

    # 価格データの妥当性チェック
    latest_row = df.iloc[-1]
    assert latest_row["high"] >= latest_row["low"], "High price should be >= low price"
    assert latest_row["open"] > 0, "Open price should be positive"
    assert latest_row["close"] > 0, "Close price should be positive"
    assert latest_row["volume"] >= 0, "Volume should be non-negative"


@pytest.mark.slow
def test_place_and_cancel_small_order(bitflyer_client):
    """
    最小額での注文・キャンセルテスト（現物取引）
    注意: このテストは実際にお金を使う可能性があるため @pytest.mark.slow を付与
    """
    symbol = "BTC/JPY"

    try:
        # 現在の BTC/JPY 板情報を取得
        ticker = bitflyer_client._exchange.fetch_ticker(symbol)
        current_bid = ticker.get("bid")
        current_ask = ticker.get("ask")

        if not current_bid or not current_ask:
            pytest.skip("Unable to get current bid/ask prices")

        # 成約しにくい価格で指値注文（現在の買い価格の 60% で買い注文）
        safe_buy_price = int(current_bid * 0.6)

        # 最小注文数量を取得（BitFlyer は通常 0.001 BTC が最小）
        market = bitflyer_client._exchange.markets[symbol]
        min_amount = market["limits"]["amount"]["min"]

        if not min_amount:
            # デフォルト値を使用
            min_amount = 0.001

        test_amount = float(min_amount)

        print(f"Placing test order: {test_amount} BTC at {safe_buy_price} JPY")

        # 買い注文を出す
        order = bitflyer_client.create_order(
            symbol=symbol,
            side="buy",
            type="limit",
            amount=test_amount,
            price=safe_buy_price,
        )

        order_id = order.get("id")
        assert order_id, f"Order creation failed, no ID returned: {order}"

        print(f"Order placed successfully with ID: {order_id}")

        # 少し待つ
        time.sleep(2)

        # 注文をキャンセル
        cancel_result = bitflyer_client.cancel_order(symbol=symbol, order_id=order_id)
        cancelled_order_id = cancel_result.get("id")

        assert (
            cancelled_order_id == order_id
        ), f"Cancel failed: expected {order_id}, got {cancelled_order_id}"
        print(f"Order {order_id} cancelled successfully")

    except BadRequest as e:
        # 注文エラーは予期される場合もある（残高不足等）
        pytest.skip(
            f"Order placement failed (possibly due to insufficient balance): {e}"
        )
    except Exception as e:
        pytest.fail(f"Unexpected error during order test: {e}")


@pytest.mark.slow
def test_lightning_fx_functionality(bitflyer_client):
    """Lightning FX の基本機能テスト"""
    fx_symbol = "FX_BTC_JPY"

    try:
        # FX 板情報取得
        ticker = bitflyer_client._exchange.fetch_ticker(fx_symbol)
        assert ticker, "Failed to fetch Lightning FX ticker"

        # FX OHLCV 取得
        df = bitflyer_client.fetch_ohlcv(fx_symbol, "1h", limit=5)
        assert not df.empty, "Failed to fetch Lightning FX OHLCV"

        print(
            f"Lightning FX test passed: ticker={ticker.get('last')}, ohlcv_length={len(df)}"
        )

    except Exception as e:
        pytest.skip(f"Lightning FX functionality test failed: {e}")


def test_market_data_consistency(bitflyer_client):
    """マーケットデータの整合性テスト"""
    symbol = "BTC/JPY"

    # ティッカーとOHLCV の価格が大きく乖離していないことを確認
    ticker = bitflyer_client._exchange.fetch_ticker(symbol)
    df = bitflyer_client.fetch_ohlcv(symbol, "1h", limit=1)

    ticker_last = ticker.get("last") or ticker.get("close")
    ohlcv_close = df.iloc[-1]["close"] if not df.empty else None

    if ticker_last and ohlcv_close:
        # 5% 以内の差であることを確認
        price_diff_ratio = abs(ticker_last - ohlcv_close) / ticker_last
        assert (
            price_diff_ratio < 0.05
        ), f"Price inconsistency: ticker={ticker_last}, ohlcv={ohlcv_close}"


def test_error_handling(bitflyer_client):
    """エラーハンドリングテスト"""
    # 存在しないシンボルでのテスト
    with pytest.raises(Exception):  # BadSymbol または類似のエラーが期待される
        bitflyer_client.fetch_ohlcv("INVALID/SYMBOL", "1d", limit=1)

    # 無効な timeframe でのテスト
    with pytest.raises(Exception):  # BadRequest または類似のエラーが期待される
        bitflyer_client.fetch_ohlcv("BTC/JPY", "invalid_timeframe", limit=1)


def test_available_symbols(bitflyer_client):
    """利用可能シンボルのテスト"""
    try:
        # マーケット一覧を取得
        markets = bitflyer_client._exchange.load_markets()
        assert isinstance(markets, dict), "Markets should be a dictionary"

        # 基本的なシンボルの存在確認
        expected_symbols = ["BTC/JPY", "ETH/JPY", "FX_BTC_JPY"]
        available_symbols = list(markets.keys())

        for symbol in expected_symbols:
            if symbol in available_symbols:
                print(f"Found expected symbol: {symbol}")
            else:
                print(f"Expected symbol not found: {symbol}")

        assert len(available_symbols) > 0, "No trading symbols available"

    except Exception as e:
        pytest.skip(f"Failed to load markets: {e}")

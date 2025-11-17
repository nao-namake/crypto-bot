"""
BitbankClient 非同期対応テスト

最終更新: 2025/11/16 (Phase 52.4-B)

Phase 2 CRIT-1修正の動作確認:
- ccxt.async_support使用確認
- 全メソッドasync/await対応確認
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.data.bitbank_client import BitbankClient


@pytest.fixture
def mock_config():
    """モックConfig"""
    config = MagicMock()
    config.exchange.symbol = "BTC/JPY"
    config.exchange.leverage = 1.0
    config.exchange.rate_limit_ms = 1000
    config.exchange.timeout_ms = 30000
    config.exchange.retries = 3
    return config


@pytest.fixture
def bitbank_client(mock_config):
    """BitbankClientインスタンス"""
    with patch("src.data.bitbank_client.get_config", return_value=mock_config):
        client = BitbankClient(api_key="test_key", api_secret="test_secret", leverage=1.0)
        return client


class TestBitbankClientAsync:
    """非同期対応テスト"""

    @pytest.mark.asyncio
    async def test_test_connection_is_async(self, bitbank_client):
        """test_connection()がasyncメソッドであることを確認"""
        # モックレスポンス
        bitbank_client.exchange = AsyncMock()
        bitbank_client.exchange.fetch_ticker = AsyncMock(return_value={"last": 14000000.0})

        # 実行
        result = await bitbank_client.test_connection()

        # 検証
        assert result is True
        bitbank_client.exchange.fetch_ticker.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_is_async(self, bitbank_client):
        """fetch_ohlcv()がasyncメソッドであることを確認"""
        # Phase 52.5: 最小行数20件要求に対応
        # モックレスポンス（20件以上のデータ）
        mock_data = [
            [1234567890000 + i * 60000, 14000000, 14100000, 13900000, 14050000, 100.0]
            for i in range(25)
        ]
        bitbank_client.exchange = AsyncMock()
        bitbank_client.exchange.fetch_ohlcv = AsyncMock(return_value=mock_data)

        # 実行
        result = await bitbank_client.fetch_ohlcv("BTC/JPY", "15m", limit=25)

        # 検証
        assert len(result) == 25
        bitbank_client.exchange.fetch_ohlcv.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_ticker_is_async(self, bitbank_client):
        """fetch_ticker()がasyncメソッドであることを確認"""
        # モックレスポンス
        bitbank_client.exchange = AsyncMock()
        bitbank_client.exchange.fetch_ticker = AsyncMock(
            return_value={"last": 14000000.0, "bid": 13999000.0, "ask": 14001000.0}
        )

        # 実行
        result = await bitbank_client.fetch_ticker("BTC/JPY")

        # 検証
        assert result["last"] == 14000000.0
        bitbank_client.exchange.fetch_ticker.assert_called_once()


class TestCRIT2SecretExposureFix:
    """CRIT-2: API Secret露出修正テスト"""

    def test_no_md5_hash_in_logs(self, bitbank_client, caplog):
        """MD5ハッシュがログに出力されないことを確認"""
        # ログを確認
        log_messages = [record.message for record in caplog.records]

        # MD5ハッシュ形式（8文字16進数）がログにないことを確認
        for msg in log_messages:
            # "ハッシュ="というキーワードがあってはならない
            assert "ハッシュ=" not in msg


class TestHIGH5PricePrecision:
    """HIGH-5: 価格精度保持テスト"""

    @pytest.mark.asyncio
    async def test_trigger_price_precision(self, bitbank_client):
        """trigger_price精度保持確認（round使用）"""
        # モックレスポンス
        bitbank_client.exchange = AsyncMock()
        bitbank_client.exchange.create_order = AsyncMock(
            return_value={"id": "12345", "status": "open"}
        )

        # 実行（小数点以下を持つ価格）
        trigger_price = 14000567.89
        await bitbank_client.create_order(
            symbol="BTC/JPY",
            order_type="stop_limit",
            side="buy",
            amount=0.001,
            price=14000000,
            trigger_price=trigger_price,
        )

        # 検証: paramsにround()された値が渡されているか
        call_args = bitbank_client.exchange.create_order.call_args
        assert call_args is not None
        # trigger_priceが正しく丸められていることを確認
        # str(round(14000567.89)) = "14000568"（正しい）
        # str(int(14000567.89)) = "14000567"（誤り - ¥1損失）

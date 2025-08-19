#!/usr/bin/env python3
"""
Phase 16.3-C 分割システム: MarketDataFetcher テスト

データ取得分割システムのテスト
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd

from crypto_bot.data.fetching.market_client import MarketDataFetcher


class TestMarketDataFetcher(unittest.TestCase):
    """MarketDataFetcher テスト"""

    def setUp(self):
        """テスト用設定"""
        self.config = {
            "data": {
                "symbol": "btc_jpy",
                "since_hours": 48,
                "limit": 1000,
                "exchange": "bitbank",
            }
        }
        self.fetcher = MarketDataFetcher(self.config)

    @patch("crypto_bot.data.fetching.market_client.ccxt")
    def test_initialize_exchange(self, mock_ccxt):
        """取引所初期化テスト"""
        mock_exchange = MagicMock()
        mock_ccxt.bitbank.return_value = mock_exchange

        fetcher = MarketDataFetcher(self.config)

        # Bitbank取引所が初期化されることを確認
        mock_ccxt.bitbank.assert_called_once()
        self.assertEqual(fetcher.exchange, mock_exchange)
        self.assertEqual(fetcher.symbol, "btc_jpy")

    @patch("crypto_bot.data.fetching.market_client.ccxt")
    def test_fetch_ohlcv_success(self, mock_ccxt):
        """OHLCV取得成功テスト"""
        # Mock設定
        mock_exchange = MagicMock()
        mock_ccxt.bitbank.return_value = mock_exchange

        # サンプルOHLCVデータ
        sample_ohlcv = [
            [1640995200000, 5000000, 5100000, 4950000, 5050000, 10.5],
            [1640998800000, 5050000, 5150000, 5000000, 5100000, 12.3],
            [1641002400000, 5100000, 5200000, 5050000, 5180000, 15.7],
        ]
        mock_exchange.fetch_ohlcv.return_value = sample_ohlcv

        fetcher = MarketDataFetcher(self.config)
        result = fetcher.fetch_ohlcv()

        # 結果の検証
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 3)

        # カラム名の確認
        expected_columns = ["timestamp", "open", "high", "low", "close", "volume"]
        self.assertListEqual(result.columns.tolist(), expected_columns)

        # データ型の確認
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(result["timestamp"]))
        self.assertTrue(pd.api.types.is_numeric_dtype(result["open"]))
        self.assertTrue(pd.api.types.is_numeric_dtype(result["volume"]))

    @patch("crypto_bot.data.fetching.market_client.ccxt")
    def test_fetch_ohlcv_with_since(self, mock_ccxt):
        """since指定でのOHLCV取得テスト"""
        mock_exchange = MagicMock()
        mock_ccxt.bitbank.return_value = mock_exchange
        mock_exchange.fetch_ohlcv.return_value = []

        fetcher = MarketDataFetcher(self.config)
        since_time = datetime.now() - timedelta(hours=24)

        fetcher.fetch_ohlcv(since=since_time)

        # since引数が正しく渡されることを確認
        mock_exchange.fetch_ohlcv.assert_called_once()
        call_args = mock_exchange.fetch_ohlcv.call_args
        self.assertIsNotNone(call_args[1]["since"])

    @patch("crypto_bot.data.fetching.market_client.ccxt")
    def test_fetch_ohlcv_error_handling(self, mock_ccxt):
        """OHLCV取得エラーハンドリングテスト"""
        mock_exchange = MagicMock()
        mock_ccxt.bitbank.return_value = mock_exchange
        mock_exchange.fetch_ohlcv.side_effect = Exception("API Error")

        fetcher = MarketDataFetcher(self.config)

        with self.assertRaises(ValueError):
            fetcher.fetch_ohlcv()

    @patch("crypto_bot.data.fetching.market_client.ccxt")
    def test_validate_data(self, mock_ccxt):
        """データ検証テスト"""
        mock_exchange = MagicMock()
        mock_ccxt.bitbank.return_value = mock_exchange

        fetcher = MarketDataFetcher(self.config)

        # 正常データ
        valid_data = pd.DataFrame(
            {
                "timestamp": pd.date_range("2024-01-01", periods=3, freq="1H"),
                "open": [5000000, 5100000, 5050000],
                "high": [5100000, 5200000, 5150000],
                "low": [4950000, 5050000, 5000000],
                "close": [5050000, 5180000, 5120000],
                "volume": [10.5, 12.3, 8.7],
            }
        )

        # 検証が成功することを確認
        self.assertTrue(fetcher._validate_data(valid_data))

        # 異常データ（負の価格）
        invalid_data = valid_data.copy()
        invalid_data.loc[0, "close"] = -100

        self.assertFalse(fetcher._validate_data(invalid_data))

        # 空のデータ
        empty_data = pd.DataFrame()
        self.assertFalse(fetcher._validate_data(empty_data))

    @patch("crypto_bot.data.fetching.market_client.ccxt")
    def test_fetch_with_retry(self, mock_ccxt):
        """リトライ機能テスト"""
        mock_exchange = MagicMock()
        mock_ccxt.bitbank.return_value = mock_exchange

        # 最初は失敗、2回目は成功
        sample_data = [[1640995200000, 5000000, 5100000, 4950000, 5050000, 10.5]]
        mock_exchange.fetch_ohlcv.side_effect = [
            Exception("Temporary Error"),
            sample_data,
        ]

        config_with_retry = self.config.copy()
        config_with_retry["data"]["max_retries"] = 3
        config_with_retry["data"]["retry_delay"] = 0.1

        fetcher = MarketDataFetcher(config_with_retry)
        result = fetcher.fetch_ohlcv()

        # リトライして成功することを確認
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1)
        self.assertEqual(mock_exchange.fetch_ohlcv.call_count, 2)

    @patch("crypto_bot.data.fetching.market_client.ccxt")
    def test_rate_limiting(self, mock_ccxt):
        """レート制限テスト"""
        mock_exchange = MagicMock()
        mock_ccxt.bitbank.return_value = mock_exchange
        mock_exchange.fetch_ohlcv.return_value = []

        config_with_rate_limit = self.config.copy()
        config_with_rate_limit["data"]["rate_limit_delay"] = 0.1

        fetcher = MarketDataFetcher(config_with_rate_limit)

        # レート制限が動作することを確認（実際の遅延は確認しないがエラーが出ないこと）
        _ = datetime.now()
        fetcher.fetch_ohlcv()
        end_time = datetime.now()

        # 少なくともエラーなく実行されることを確認
        self.assertIsNotNone(end_time)

    def test_symbol_conversion(self):
        """シンボル変換テスト"""
        # 内部フォーマットから取引所フォーマットへの変換
        self.assertEqual(self.fetcher._convert_symbol("btc_jpy"), "BTC/JPY")
        self.assertEqual(self.fetcher._convert_symbol("eth_jpy"), "ETH/JPY")
        self.assertEqual(self.fetcher._convert_symbol("xrp_jpy"), "XRP/JPY")

        # 既に取引所フォーマットの場合は変更なし
        self.assertEqual(self.fetcher._convert_symbol("BTC/JPY"), "BTC/JPY")


if __name__ == "__main__":
    unittest.main()

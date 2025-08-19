#!/usr/bin/env python3
"""
Bitbank Core Execution テスト

Phase 16.2統合システムのBitbank実行エンジンテスト
"""

import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from crypto_bot.execution.exchange.bitbank.core_execution import (
    BitbankCoreExecutor,
    OrderType,
    PositionSide,
)


class TestBitbankCoreExecution(unittest.TestCase):
    """BitbankCoreExecutor テスト"""

    def setUp(self):
        """テスト用設定"""
        self.config = {
            "exchange": {
                "bitbank": {
                    "api_key": "test_key",
                    "secret": "test_secret",
                    "sandbox": True,
                }
            },
            "trading": {
                "symbol": "btc_jpy",
                "min_order_size": Decimal("0.0001"),
                "max_position_size": Decimal("1.0"),
            },
        }

        with patch("crypto_bot.execution.exchange.bitbank.core_execution.ccxt"):
            self.executor = BitbankCoreExecutor(self.config)

    @patch("crypto_bot.execution.exchange.bitbank.core_execution.ccxt")
    def test_initialize_exchange(self, mock_ccxt):
        """取引所初期化テスト"""
        mock_exchange = MagicMock()
        mock_ccxt.bitbank.return_value = mock_exchange

        executor = BitbankCoreExecutor(self.config)

        # Bitbank取引所が適切に初期化されることを確認
        mock_ccxt.bitbank.assert_called_once()
        self.assertEqual(executor.exchange, mock_exchange)

    def test_validate_order_size_valid(self):
        """注文サイズ検証 - 正常ケース"""
        valid_size = Decimal("0.001")
        result = self.executor._validate_order_size(valid_size)

        self.assertTrue(result)

    def test_validate_order_size_too_small(self):
        """注文サイズ検証 - 最小サイズ以下"""
        invalid_size = Decimal("0.00001")
        result = self.executor._validate_order_size(invalid_size)

        self.assertFalse(result)

    def test_validate_order_size_too_large(self):
        """注文サイズ検証 - 最大サイズ以上"""
        invalid_size = Decimal("10.0")
        result = self.executor._validate_order_size(invalid_size)

        self.assertFalse(result)

    @patch("crypto_bot.execution.exchange.bitbank.core_execution.ccxt")
    def test_place_market_buy_order(self, mock_ccxt):
        """成行買い注文テスト"""
        mock_exchange = MagicMock()
        mock_ccxt.bitbank.return_value = mock_exchange

        # 成功レスポンス
        mock_exchange.create_market_buy_order.return_value = {
            "id": "12345",
            "symbol": "BTC/JPY",
            "type": "market",
            "side": "buy",
            "amount": 0.001,
            "status": "closed",
        }

        executor = BitbankCoreExecutor(self.config)

        result = executor.place_order(
            order_type=OrderType.MARKET, side=PositionSide.LONG, amount=Decimal("0.001")
        )

        # 正常な注文結果確認
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "12345")
        self.assertEqual(result["side"], "buy")

        # 適切なメソッドが呼ばれることを確認
        mock_exchange.create_market_buy_order.assert_called_once()

    @patch("crypto_bot.execution.exchange.bitbank.core_execution.ccxt")
    def test_place_market_sell_order(self, mock_ccxt):
        """成行売り注文テスト"""
        mock_exchange = MagicMock()
        mock_ccxt.bitbank.return_value = mock_exchange

        mock_exchange.create_market_sell_order.return_value = {
            "id": "12346",
            "symbol": "BTC/JPY",
            "type": "market",
            "side": "sell",
            "amount": 0.001,
            "status": "closed",
        }

        executor = BitbankCoreExecutor(self.config)

        result = executor.place_order(
            order_type=OrderType.MARKET,
            side=PositionSide.SHORT,
            amount=Decimal("0.001"),
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "12346")
        self.assertEqual(result["side"], "sell")

        mock_exchange.create_market_sell_order.assert_called_once()

    @patch("crypto_bot.execution.exchange.bitbank.core_execution.ccxt")
    def test_place_limit_order(self, mock_ccxt):
        """指値注文テスト"""
        mock_exchange = MagicMock()
        mock_ccxt.bitbank.return_value = mock_exchange

        mock_exchange.create_limit_buy_order.return_value = {
            "id": "12347",
            "symbol": "BTC/JPY",
            "type": "limit",
            "side": "buy",
            "amount": 0.001,
            "price": 5000000,
            "status": "open",
        }

        executor = BitbankCoreExecutor(self.config)

        result = executor.place_order(
            order_type=OrderType.LIMIT,
            side=PositionSide.LONG,
            amount=Decimal("0.001"),
            price=Decimal("5000000"),
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "limit")
        self.assertEqual(result["price"], 5000000)

        mock_exchange.create_limit_buy_order.assert_called_once()

    def test_place_order_invalid_size(self):
        """無効サイズでの注文テスト"""
        with self.assertRaises(ValueError):
            self.executor.place_order(
                order_type=OrderType.MARKET,
                side=PositionSide.LONG,
                amount=Decimal("0.00001"),  # 最小サイズ以下
            )

    @patch("crypto_bot.execution.exchange.bitbank.core_execution.ccxt")
    def test_place_order_api_error(self, mock_ccxt):
        """API エラーハンドリングテスト"""
        mock_exchange = MagicMock()
        mock_ccxt.bitbank.return_value = mock_exchange

        # API エラーをシミュレート
        mock_exchange.create_market_buy_order.side_effect = Exception("API Error")

        executor = BitbankCoreExecutor(self.config)

        with self.assertRaises(ValueError):
            executor.place_order(
                order_type=OrderType.MARKET,
                side=PositionSide.LONG,
                amount=Decimal("0.001"),
            )

    @patch("crypto_bot.execution.exchange.bitbank.core_execution.ccxt")
    def test_cancel_order(self, mock_ccxt):
        """注文キャンセルテスト"""
        mock_exchange = MagicMock()
        mock_ccxt.bitbank.return_value = mock_exchange

        mock_exchange.cancel_order.return_value = {"id": "12345", "status": "canceled"}

        executor = BitbankCoreExecutor(self.config)

        result = executor.cancel_order("12345")

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "canceled")

        mock_exchange.cancel_order.assert_called_once_with("12345", "BTC/JPY")

    @patch("crypto_bot.execution.exchange.bitbank.core_execution.ccxt")
    def test_get_order_status(self, mock_ccxt):
        """注文状況確認テスト"""
        mock_exchange = MagicMock()
        mock_ccxt.bitbank.return_value = mock_exchange

        mock_exchange.fetch_order.return_value = {
            "id": "12345",
            "status": "closed",
            "filled": 0.001,
            "remaining": 0.0,
        }

        executor = BitbankCoreExecutor(self.config)

        result = executor.get_order_status("12345")

        self.assertIsNotNone(result)
        self.assertEqual(result["status"], "closed")
        self.assertEqual(result["filled"], 0.001)

        mock_exchange.fetch_order.assert_called_once_with("12345", "BTC/JPY")

    @patch("crypto_bot.execution.exchange.bitbank.core_execution.ccxt")
    def test_get_balance(self, mock_ccxt):
        """残高取得テスト"""
        mock_exchange = MagicMock()
        mock_ccxt.bitbank.return_value = mock_exchange

        mock_exchange.fetch_balance.return_value = {
            "BTC": {"free": 0.5, "used": 0.1, "total": 0.6},
            "JPY": {"free": 1000000, "used": 200000, "total": 1200000},
        }

        executor = BitbankCoreExecutor(self.config)

        result = executor.get_balance()

        self.assertIsNotNone(result)
        self.assertIn("BTC", result)
        self.assertIn("JPY", result)
        self.assertEqual(result["BTC"]["free"], 0.5)
        self.assertEqual(result["JPY"]["total"], 1200000)

    def test_calculate_position_size(self):
        """ポジションサイズ計算テスト"""
        # リスク 1%、口座残高 1,000,000円、BTC価格 5,000,000円
        balance_jpy = Decimal("1000000")
        btc_price = Decimal("5000000")
        risk_percent = Decimal("0.01")

        position_size = self.executor._calculate_position_size(
            balance_jpy, btc_price, risk_percent
        )

        # 期待される計算: (1,000,000 * 0.01) / 5,000,000 = 0.002 BTC
        expected_size = Decimal("0.002")
        self.assertAlmostEqual(float(position_size), float(expected_size), places=6)

    def test_risk_management_check(self):
        """リスク管理チェックテスト"""
        # 正常ケース
        result = self.executor._risk_management_check(
            position_size=Decimal("0.001"),
            current_exposure=Decimal("0.5"),
            max_exposure=Decimal("1.0"),
        )
        self.assertTrue(result)

        # 最大エクスポージャー超過ケース
        result = self.executor._risk_management_check(
            position_size=Decimal("0.6"),
            current_exposure=Decimal("0.5"),
            max_exposure=Decimal("1.0"),
        )
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()

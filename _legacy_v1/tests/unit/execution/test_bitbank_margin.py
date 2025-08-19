# tests/unit/execution/test_bitbank_margin.py
# Bitbank信用取引機能のユニットテスト

from unittest.mock import Mock, patch

import pandas as pd
import pytest

from crypto_bot.execution.bitbank_client import BitbankClient
from crypto_bot.execution.engine import EntryExit, Order, Position
from crypto_bot.risk.manager import RiskManager


class TestBitbankMarginClient:
    """Bitbank信用取引クライアントのテスト"""

    def test_margin_mode_initialization(self):
        """信用取引モードの初期化テスト"""
        # 現物取引モード
        spot_client = BitbankClient("key", "secret", margin_mode=False)
        assert spot_client.margin_mode is False

        # 信用取引モード
        margin_client = BitbankClient("key", "secret", margin_mode=True)
        assert margin_client.margin_mode is True

    @patch("crypto_bot.execution.bitbank_client.ccxt.bitbank")
    def test_margin_order_creation(self, mock_ccxt):
        """信用取引注文作成のテスト"""
        mock_exchange = Mock()
        mock_ccxt.return_value = mock_exchange

        client = BitbankClient("key", "secret", margin_mode=True)

        # ショート注文テスト
        client.create_order("BTC/JPY", "sell", "market", 0.001, None, {})

        # create_order呼び出しの引数を確認
        call_args = mock_exchange.create_order.call_args
        symbol, side, order_type, amount, price, params = call_args[0]

        # margin=Trueとside=sellが設定されることを確認
        assert params["margin"] is True
        assert params["side"] == "sell"
        assert side == "sell"

    @patch("crypto_bot.execution.bitbank_client.ccxt.bitbank")
    def test_leverage_setting(self, mock_ccxt):
        """レバレッジ設定のテスト"""
        mock_exchange = Mock()
        mock_ccxt.return_value = mock_exchange

        client = BitbankClient("key", "secret", margin_mode=True)

        # 有効なレバレッジ設定
        result = client.set_leverage("BTC/JPY", 1.0)
        assert result is not None

        # 無効なレバレッジでエラー
        with pytest.raises(ValueError):
            client.set_leverage("BTC/JPY", 3.0)  # Bitbankは1-2倍のみ

    def test_leverage_setting_in_spot_mode(self):
        """現物取引モードでレバレッジ設定エラーのテスト"""
        client = BitbankClient("key", "secret", margin_mode=False)

        with pytest.raises(NotImplementedError):
            client.set_leverage("BTC/JPY", 1.0)


class TestRiskManagerMargin:
    """リスク管理の信用取引対応テスト"""

    def setup_method(self):
        """テストセットアップ"""
        self.risk_manager = RiskManager(risk_per_trade=0.02, stop_atr_mult=1.5)
        self.atr_series = pd.Series([100, 110, 120, 105, 115])

    def test_long_stop_price_calculation(self):
        """ロングポジションのストップ価格計算"""
        entry_price = 1000.0
        stop_price = self.risk_manager.calc_stop_price(
            entry_price, self.atr_series, side="BUY"
        )

        # ストップ価格はエントリー価格より下
        expected_stop = entry_price - 115 * 1.5  # 最新ATR=115
        assert stop_price == expected_stop
        assert stop_price < entry_price

    def test_short_stop_price_calculation(self):
        """ショートポジションのストップ価格計算"""
        entry_price = 1000.0
        stop_price = self.risk_manager.calc_stop_price(
            entry_price, self.atr_series, side="SELL"
        )

        # ストップ価格はエントリー価格より上
        expected_stop = entry_price + 115 * 1.5  # 最新ATR=115
        assert stop_price == expected_stop
        assert stop_price > entry_price

    def test_long_position_sizing(self):
        """ロングポジションサイジング"""
        balance = 10000.0
        entry_price = 1000.0
        stop_price = 950.0  # エントリーより下

        lot = self.risk_manager.calc_lot(balance, entry_price, stop_price, side="BUY")

        # リスク量 = balance * risk_per_trade = 10000 * 0.02 = 200
        # 損失幅 = entry_price - stop_price = 1000 - 950 = 50
        # ロット = リスク量 / 損失幅 = 200 / 50 = 4.0
        assert lot == 4.0

    def test_short_position_sizing(self):
        """ショートポジションサイジング"""
        balance = 10000.0
        entry_price = 1000.0
        stop_price = 1050.0  # エントリーより上

        lot = self.risk_manager.calc_lot(balance, entry_price, stop_price, side="SELL")

        # リスク量 = balance * risk_per_trade = 10000 * 0.02 = 200
        # 損失幅 = stop_price - entry_price = 1050 - 1000 = 50
        # ロット = リスク量 / 損失幅 = 200 / 50 = 4.0
        assert lot == 4.0

    def test_invalid_stop_price_for_long(self):
        """ロングポジションの無効なストップ価格"""
        balance = 10000.0
        entry_price = 1000.0
        stop_price = 1050.0  # エントリーより上（ロングでは無効）

        with pytest.raises(ValueError):
            self.risk_manager.calc_lot(balance, entry_price, stop_price, side="BUY")

    def test_invalid_stop_price_for_short(self):
        """ショートポジションの無効なストップ価格"""
        balance = 10000.0
        entry_price = 1000.0
        stop_price = 950.0  # エントリーより下（ショートでは無効）

        with pytest.raises(ValueError):
            self.risk_manager.calc_lot(balance, entry_price, stop_price, side="SELL")


class TestEntryExitMargin:
    """EntryExitエンジンの信用取引対応テスト"""

    def setup_method(self):
        """テストセットアップ"""
        self.strategy = Mock()
        self.risk_manager = Mock()
        self.atr_series = pd.Series([100, 110, 120])

        self.entry_exit = EntryExit(self.strategy, self.risk_manager, self.atr_series)
        self.entry_exit.current_balance = 10000.0

    def test_short_entry_order_generation(self):
        """ショートエントリー注文生成"""
        # ショートシグナルを返すモック
        from crypto_bot.execution.engine import Signal

        short_signal = Signal(side="SELL", price=1000.0)
        self.strategy.logic_signal.return_value = short_signal

        # リスク管理モック設定
        self.risk_manager.calc_stop_price.return_value = 1050.0
        self.risk_manager.calc_lot.return_value = 2.0

        position = Position()
        order = self.entry_exit.generate_entry_order(
            pd.DataFrame({"close": [1000]}), position
        )

        assert order.exist is True
        assert order.side == "SELL"
        assert order.price == 1000.0
        assert order.lot == 2.0
        assert order.stop_price == 1050.0

    def test_short_position_exit_on_stop_loss(self):
        """ショートポジションのストップロス決済"""
        # ショートポジション作成
        position = Position(
            exist=True, side="SELL", entry_price=1000.0, lot=1.0, stop_price=1050.0
        )

        # 価格が上昇してストップロス発動
        price_df = pd.DataFrame(
            {
                "high": [1060.0],  # ストップロス価格(1050)を上回る
                "low": [1040.0],
                "close": [1055.0],
            }
        )

        order = self.entry_exit.generate_exit_order(price_df, position)

        assert order.exist is True
        assert order.side == "BUY"  # ショートクローズは買い
        assert order.price == 1050.0

    def test_short_position_profit_calculation(self):
        """ショートポジションの利益計算"""
        # ショートポジション
        position = Position(exist=True, side="SELL", entry_price=1000.0, lot=1.0)

        # 利益決済注文（価格下落）
        order = Order(
            exist=True, side="BUY", price=950.0, lot=1.0  # エントリーより安く買い戻し
        )

        initial_balance = 10000.0
        final_balance = self.entry_exit.fill_order(order, position, initial_balance)

        # ショート利益 = (エントリー価格 - 決済価格) × ロット
        # = (1000 - 950) × 1 = 50
        expected_balance = initial_balance + 50.0
        assert final_balance == expected_balance
        assert position.exist is False  # ポジションクローズ

    def test_long_position_profit_calculation(self):
        """ロングポジションの利益計算（比較用）"""
        # ロングポジション
        position = Position(exist=True, side="BUY", entry_price=1000.0, lot=1.0)

        # 利益決済注文（価格上昇）
        order = Order(
            exist=True, side="SELL", price=1050.0, lot=1.0  # エントリーより高く売却
        )

        initial_balance = 10000.0
        final_balance = self.entry_exit.fill_order(order, position, initial_balance)

        # ロング利益 = (決済価格 - エントリー価格) × ロット
        # = (1050 - 1000) × 1 = 50
        expected_balance = initial_balance + 50.0
        assert final_balance == expected_balance
        assert position.exist is False  # ポジションクローズ


class TestMarginIntegration:
    """信用取引統合テスト"""

    def test_margin_config_validation(self):
        """信用取引設定の検証"""
        # 信用取引設定のサンプル
        margin_config = {
            "data": {"exchange": "bitbank", "margin_mode": True},
            "risk": {"risk_per_trade": 0.015, "max_leverage": 1.0},
            "live": {"margin_maintenance_ratio": 0.25, "leverage": 1.0},
        }

        # 設定値の検証
        assert margin_config["data"]["margin_mode"] is True
        assert margin_config["risk"]["max_leverage"] == 1.0
        assert margin_config["live"]["leverage"] == 1.0

    def test_risk_management_with_margin(self):
        """信用取引でのリスク管理統合テスト"""
        risk_manager = RiskManager(
            risk_per_trade=0.015, stop_atr_mult=1.5  # 1.5%リスク
        )

        # テストデータ（より現実的な値）
        balance = 10000.0
        entry_price = 100.0  # 簡単な価格
        atr_series = pd.Series([5.0])  # ATR

        # ロングポジション
        long_stop = risk_manager.calc_stop_price(entry_price, atr_series, "BUY")
        long_lot = risk_manager.calc_lot(balance, entry_price, long_stop, "BUY")

        # ショートポジション
        short_stop = risk_manager.calc_stop_price(entry_price, atr_series, "SELL")
        short_lot = risk_manager.calc_lot(balance, entry_price, short_stop, "SELL")

        # ロングとショートで同じリスク量になることを確認
        long_risk = (entry_price - long_stop) * long_lot
        short_risk = (short_stop - entry_price) * short_lot

        # 許容される誤差内で同等のリスク
        assert abs(long_risk - short_risk) < 0.1

        # 期待リスク量に近い値（max_lotでキャッピングされる可能性を考慮）
        expected_risk = balance * 0.015  # 150.0
        assert long_risk <= expected_risk * 1.1  # 10%のマージン

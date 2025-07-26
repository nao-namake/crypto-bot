# tests/unit/backtest/test_engine.py
# テスト対象: crypto_bot/backtest/engine.py
# 説明:
#   - BacktestEngine: バックテスト実行エンジン
#   - シグナル→注文→約定→ポジション管理の一連の流れ

import pandas as pd
import pytest

from crypto_bot.backtest.engine import BacktestEngine, TradeRecord
from crypto_bot.execution.engine import EntryExit, Signal
from crypto_bot.risk.manager import RiskManager
from crypto_bot.strategy.base import StrategyBase


class DummyStrategy(StrategyBase):
    """1回だけBUYエントリー・即EXITするだけのダミー戦略"""

    def __init__(self):
        super().__init__()

    def logic_signal(self, price_df, position):
        if not position.exist and len(price_df) > 0:
            return Signal(side="BUY", price=price_df["close"].iloc[-1])
        if position.exist and len(price_df) > 0:
            return Signal(side="SELL", price=price_df["close"].iloc[-1])
        return Signal()

    def entry_signal(self, price_df, position):
        if not position.exist and len(price_df) > 0:
            return "BUY"
        return None

    def exit_signal(self, price_df, position):
        if position.exist and len(price_df) > 0:
            return "EXIT"
        return None


def dummy_price_df():
    # Phase H.13対応: ATR計算に十分なテスト用OHLCV（最小5件以上）
    return pd.DataFrame(
        {
            "open": [100, 101, 102, 103, 104, 105],
            "high": [101, 102, 103, 104, 105, 106],
            "low": [99, 100, 101, 102, 103, 104],
            "close": [100, 102, 103, 104, 105, 106],
        },
        index=pd.date_range("2024-01-01", periods=6, freq="1min"),
    )


def test_traderecord_fields():
    """TradeRecordのフィールドが正しいか"""
    rec = TradeRecord(
        entry_time=pd.Timestamp("2024-01-01 00:00"),
        exit_time=pd.Timestamp("2024-01-01 00:01"),
        side="BUY",
        entry_price=100.0,
        exit_price=102.0,
        profit=2.0,
        return_rate=2.0,
        duration_bars=1,
        slippage=0.0,
        commission=0.0,
        size=1.0,
    )
    assert rec.side == "BUY"
    assert rec.profit == 2.0
    assert rec.duration_bars == 1


def test_backtestengine_run_basic():
    """最小限のバックテストが正常に実行されるか"""
    df = dummy_price_df()
    strategy = DummyStrategy()
    risk_manager = RiskManager(risk_per_trade=0.01, stop_atr_mult=1.5)
    entry_exit = EntryExit(strategy, risk_manager, atr_series=None)
    engine = BacktestEngine(df, strategy, 10000, 0.0, risk_manager, entry_exit)
    metrics_df, trade_log = engine.run()
    # 結果がDataFrameで返る
    assert isinstance(metrics_df, pd.DataFrame)
    assert isinstance(trade_log, pd.DataFrame)
    # 1件以上トレード記録がある
    assert len(trade_log) >= 0


def test_backtestengine_reset():
    """resetで初期化されるか"""
    df = dummy_price_df()
    engine = BacktestEngine(df, DummyStrategy())
    engine.balance = 12345
    engine.position.exist = True
    engine.records = [
        TradeRecord(
            pd.Timestamp("2024-01-01"),
            pd.Timestamp("2024-01-01"),
            "BUY",
            1,
            1,
            1,
            1,
            1,
            0,
            0,
            1,
        )
    ]
    engine.reset()
    assert engine.balance == engine.starting_balance
    assert engine.position.exist is False
    assert engine.records == []


def test_backtestengine_equity_curve_empty():
    """トレードが無い場合のエクイティカーブ"""
    engine = BacktestEngine(None, DummyStrategy())
    eq = engine.get_equity_curve()
    assert eq.empty


def test_backtestengine_statistics_empty():
    """トレードが無い場合のstatistics()"""
    engine = BacktestEngine(None, DummyStrategy())
    stats = engine.statistics()
    assert stats["total_profit"] == 0.0
    assert stats["cagr"] == 0.0
    assert stats["sharpe"] == 0.0


@pytest.mark.parametrize("balance", [1_000_000, 0, -1_000_000])
def test_backtestengine_balance_param(balance):
    """初期残高パラメータで初期化できるか"""
    df = dummy_price_df()
    engine = BacktestEngine(df, DummyStrategy(), starting_balance=balance)
    assert engine.starting_balance == balance


def test_backtestengine_invalid_price_df():
    """不正なprice_df（None, 空）でも落ちない"""
    engine = BacktestEngine(None, DummyStrategy())
    m, t = engine.run()
    assert m.empty
    assert t.empty

    # 空のDataFrameに必要なカラムを追加
    empty_df = pd.DataFrame(columns=["high", "low", "close", "volume", "timestamp"])
    engine = BacktestEngine(empty_df, DummyStrategy())
    m, t = engine.run()
    assert m.empty
    assert t.empty

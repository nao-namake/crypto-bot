import pandas as pd
import pytest

from crypto_bot.risk.manager import RiskManager


@pytest.fixture
def sample_atr():
    # ATR の時系列データ (末尾だけ使われる)
    idx = pd.date_range("2024-01-01", periods=5, freq="D")
    # 適当に増減させた ATR
    return pd.Series([1.2, 1.1, 1.3, 1.4, 1.5], index=idx)


def test_calc_stop_price(sample_atr):
    rm = RiskManager(risk_per_trade=0.02, stop_atr_mult=2.0)
    entry = 100.0
    # 最新 ATR=1.5, マルチプライヤ=2.0 → ストップ幅=3.0
    stop = rm.calc_stop_price(entry_price=entry, atr=sample_atr)
    assert pytest.approx(stop, rel=1e-6) == 97.0


def test_calc_lot_positive():
    rm = RiskManager(risk_per_trade=0.01, stop_atr_mult=1.5)
    entry = 50.0
    stop_price = 48.0
    balance = 10000.0
    # 許容リスク = 10000 * 0.01 = 100
    # 損失幅 = 50 - 48 = 2 → lot = 100 / 2 = 50
    lots = rm.calc_lot(balance=balance, entry_price=entry, stop_price=stop_price)
    assert pytest.approx(lots, rel=1e-6) == 50.0


def test_calc_lot_zero_or_negative_loss():
    rm = RiskManager(risk_per_trade=0.05)
    # entry_price − stop_price が 0 以下のときは 0 を返す
    assert rm.calc_lot(10000, entry_price=10.0, stop_price=10.0) == 0.0
    assert rm.calc_lot(10000, entry_price=8.0, stop_price=10.0) == 0.0


def test_integration_stop_and_lot(sample_atr):
    rm = RiskManager(risk_per_trade=0.015, stop_atr_mult=1.0)
    entry = 200.0
    balance = 5000.0
    stop_price = rm.calc_stop_price(entry, sample_atr)
    # stop_price = 200 - 1.5 * 1.0 = 198.5
    assert pytest.approx(stop_price, rel=1e-6) == 198.5

    # 許容リスク = 5000 * 0.015 = 75
    # 損失幅 = 200 - 198.5 = 1.5 → lot = 75 / 1.5 = 50
    lot = rm.calc_lot(balance, entry, stop_price)
    assert pytest.approx(lot, rel=1e-6) == 50.0

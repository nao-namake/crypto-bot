import pandas as pd
import pytest

from crypto_bot.backtest.metrics import cagr, max_drawdown, sharpe_ratio


@pytest.fixture
def equity_series():
    # 等比に増加する Series: 100→110→121→133.1
    idx = pd.date_range("2020-01-01", periods=4, freq="D")
    vals = [100, 110, 121, 133.1]
    return pd.Series(vals, index=idx)


def test_max_drawdown_flat():
    eq = pd.Series([100, 105, 110, 115])
    assert max_drawdown(eq) == 0.0


def test_max_drawdown():
    eq = pd.Series([100, 120, 80, 130])
    # Peak→Trough = 120→80 ⇒ DD = (80−120)/120 = −0.3333
    assert pytest.approx(max_drawdown(eq), rel=1e-3) == -0.3333


def test_cagr(equity_series):
    # 初期100→最終133.1 over 3日を1年に見立て CAGR=10%
    c = cagr(equity_series)
    assert pytest.approx(c, rel=1e-3) == 0.10


def test_sharpe_ratio(equity_series):
    # returns = [0.1,0.1,0.1], 平均=0.1, sd=0.0 ⇒ sharpe は 0
    rets = equity_series.pct_change().dropna()
    sr = sharpe_ratio(rets, periods_per_year=252)
    assert sr == 0.0

import pandas as pd
import pytest

from crypto_bot.backtest.optimizer import ParameterOptimizer


class DummyStrategy:
    """Dummy substitute for BollingerStrategy."""

    def __init__(self, period, nbdevup, nbdevdn=None):
        self.period = period
        self.nbdevup = nbdevup
        self.nbdevdn = nbdevdn or nbdevup


class DummyEngine:
    """
    scan() 内で使われる BacktestEngine の dummy実装。
    statistics() は適当な数値を返すだけ。
    """

    def __init__(self, price_df, strategy, starting_balance, slippage_rate):
        pass

    def run(self):
        pass

    def statistics(self):
        # period/nbdev は渡されないので固定値
        return {
            "total_profit": 42.0,
            "cagr": 0.123,
            "sharpe": 0.456,
            "max_drawdown": 0.789,
        }


@pytest.fixture(autouse=True)
def patch_engines_and_strategies(monkeypatch):
    # ParameterOptimizer モジュール内の BacktestEngine/BollingerStrategy をダミー化
    monkeypatch.setattr(
        "crypto_bot.backtest.optimizer.BacktestEngine",
        DummyEngine,
        raising=True,
    )
    monkeypatch.setattr(
        "crypto_bot.backtest.optimizer.BollingerStrategy",
        DummyStrategy,
        raising=True,
    )


def test_scan_grid_and_columns_minimal_call():
    # ダミーの価格 DataFrame（中身は使われない）
    dummy_df = pd.DataFrame({"price": [1, 2, 3, 4, 5]})

    po = ParameterOptimizer(
        price_df=dummy_df,
        starting_balance=1000.0,
        slippage_rate=0.01,
    )

    periods = [5, 10, 20]
    nbdevs = [1.0, 2.0]

    # scan を実行（minimal call）
    result_df = po.scan(periods, nbdevs)

    # グリッド数 = 3×2 = 6
    assert len(result_df) == len(periods) * len(nbdevs)

    # 必須カラム(period, nbdev, total_profit) が含まれること
    basic_cols = {"period", "nbdev", "total_profit"}
    assert basic_cols.issubset(set(result_df.columns))

    # total_profit が全て float であること
    assert pd.api.types.is_float_dtype(result_df["total_profit"])
    # period と nbdev がそれぞれリスト順に並んでいること
    assert set(result_df["period"].unique()) == set(periods)
    assert set(result_df["nbdev"].unique()) == set(nbdevs)

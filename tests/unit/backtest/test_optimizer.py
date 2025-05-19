import pandas as pd
import pytest

from crypto_bot.backtest.optimizer import ParameterOptimizer


# モンキーパッチ用のダミー ExecutionEngine
class DummyEngine:
    def __init__(self, price_df, strategy, starting_balance, slippage_rate):
        # 何もしない
        pass

    def run(self):
        # 空の取引結果を返す
        return []


@pytest.fixture(autouse=True)
def patch_engine(monkeypatch):
    # backtest.optimizer 内の BacktestEngine を DummyEngine に置き換え
    monkeypatch.setattr("crypto_bot.backtest.optimizer.BacktestEngine", DummyEngine)


def test_scan_returns_dataframe():
    # 単純な価格データ
    df = pd.DataFrame({"close": [1, 2, 3, 4, 5]})

    # オプティマイザ生成
    opt = ParameterOptimizer(price_df=df, starting_balance=1000.0, slippage_rate=0.0)

    # periods/nbdevs を１組だけ与えて scan
    result = opt.scan(periods=[2], nbdevs=[1.5])

    # DataFrame で返ってくること
    assert isinstance(result, pd.DataFrame)

    # 組合せが１通りなので１行
    assert result.shape[0] == 1

    # 必須カラムが含まれていること
    expected_cols = {
        "period",
        "nbdev",
        "timeframe",
        "n_trades",
        "win_rate",
        "avg_return",
        "total_profit",
        "max_drawdown",
        "cagr",
    }
    assert expected_cols.issubset(set(result.columns))

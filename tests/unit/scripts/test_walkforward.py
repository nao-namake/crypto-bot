import pandas as pd

from crypto_bot.scripts.walk_forward import walk_forward_test


# ダミー Optimizer: scan() は DataFrame(period, nbdev, total_profit) を返す
class DummyOptimizer:
    def __init__(self, price_df, starting_balance, slippage_rate):
        # 必要なら price_df を検証してもよい
        self.price_df = price_df

    def scan(self, periods, nbdevs):
        # 最初の組み合わせだけ返す
        return pd.DataFrame(
            [{"period": periods[0], "nbdev": nbdevs[0], "total_profit": 1.0}]
        )


# ダミー Strategy: コンストラクタ引数を保持するだけ
class DummyStrategy:
    def __init__(self, period, nbdevup, nbdevdn):
        self.period = period
        self.nbdevup = nbdevup
        self.nbdevdn = nbdevdn


# ダミー Engine: run() → nothing, statistics() → 固定結果を返す
class DummyEngine:
    def __init__(self, price_df, strategy, starting_balance, slippage_rate):
        self.price_df = price_df
        self.strategy = strategy

    def run(self):
        pass

    def statistics(self):
        # 任意のキーと値を返す
        return {"foo": 42}


def test_walk_forward_test(monkeypatch):
    # 依存クラスをダミー実装に置き換え
    monkeypatch.setattr(
        "crypto_bot.scripts.walk_forward.ParameterOptimizer", DummyOptimizer
    )
    monkeypatch.setattr(
        "crypto_bot.scripts.walk_forward.BollingerStrategy", DummyStrategy
    )
    monkeypatch.setattr("crypto_bot.scripts.walk_forward.BacktestEngine", DummyEngine)

    # テスト用データフレーム (7行)
    dates = pd.date_range("2020-01-01", periods=7, freq="D")
    df = pd.DataFrame({"close": list(range(7))}, index=dates)

    # walk_forward_test 実行 (train=3, test=2, step=3)
    result_df = walk_forward_test(
        df=df,
        train_window=3,
        test_window=2,
        step=3,
        periods=[5],
        nbdevs=[1.0],
        starting_balance=1_000.0,
        slippage_rate=0.0,
    )

    # df length=7 かつ train=3,test=2,step=3 なので 1 分割だけ生成されるはず
    assert len(result_df) == 1

    row = result_df.iloc[0]
    # fold は 0 から始まる
    assert row["fold"] == 0
    # train/test の開始・終了時刻が正しい
    assert row["train_start"] == dates[0]
    assert row["train_end"] == dates[2]
    assert row["test_start"] == dates[3]
    assert row["test_end"] == dates[4]
    # best パラメータが反映されている
    assert row["period"] == 5
    assert row["nbdev"] == 1.0
    # ダミー Engine.statistics() の結果がマージされている
    assert row["foo"] == 42

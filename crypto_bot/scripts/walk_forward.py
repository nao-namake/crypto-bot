import pandas as pd

from crypto_bot.data.fetcher      import MarketDataFetcher, DataPreprocessor
from crypto_bot.backtest.metrics  import split_walk_forward
from crypto_bot.backtest.engine   import BacktestEngine
from crypto_bot.strategy.bollinger import BollingerStrategy
from crypto_bot.backtest.optimizer import ParameterOptimizer

def walk_forward_test(
    df: pd.DataFrame,
    train_window:     int,
    test_window:      int,
    step:             int,
    periods:          list,
    nbdevs:           list,
    starting_balance: float,
    slippage_rate:    float
) -> pd.DataFrame:
    """
    df をスライドさせながら (train, test) を分割し、
    train→optimize → test→backtest を繰り返す。
    """
    results = []
    splits = split_walk_forward(df, train_window, test_window, step)

    for i, (train_df, test_df) in enumerate(splits):
        # 1) 訓練用データでパラメータ最適化
        opt = ParameterOptimizer(
            price_df=train_df,
            starting_balance=starting_balance,
            slippage_rate=slippage_rate
        )
        scan_df = opt.scan(periods=periods, nbdevs=nbdevs)
        best    = scan_df.sort_values("total_profit", ascending=False).iloc[0]

        # 2) 検証用データでバックテスト
        strat = BollingerStrategy(
            period=int(best.period),
            nbdevup=float(best.nbdev),
            nbdevdn=float(best.nbdev)
        )
        engine = BacktestEngine(
            price_df=test_df,
            strategy=strat,
            starting_balance=starting_balance,
            slippage_rate=slippage_rate
        )
        engine.run()
        stats = engine.statistics()

        # 3) 結果を格納
        results.append({
            "fold":        i,
            "train_start": train_df.index[0],
            "train_end":   train_df.index[-1],
            "test_start":  test_df.index[0],
            "test_end":    test_df.index[-1],
            "period":      best.period,
            "nbdev":       best.nbdev,
            **stats
        })

    return pd.DataFrame(results)


def main():
    # 1) データ取得（ページング）
    fetcher = MarketDataFetcher("BTC/USDT")
    ts = int(pd.Timestamp("2022-01-01T00:00:00Z").value // 10**6)
    df = fetcher.get_price_df(
        timeframe="1h",
        after=ts,
        limit=3000,
        paginate=True,
        per_page=500
    )

    # 2) 前処理
    df = DataPreprocessor.clean(df, timeframe="1h", z_thresh=5.0, window=20)

    # 3) Walk-Forward テスト
    wf_df = walk_forward_test(
        df=df,
        train_window=500,      # 学習バー数
        test_window=100,       # 検証バー数
        step=100,              # スライド幅
        periods=[10, 20, 30],  # BB period 候補
        nbdevs=[1.5, 2.0, 2.5],# σ幅 候補
        starting_balance=10_000.0,
        slippage_rate=0.0
    )

    # 4) 結果表示
    pd.set_option("display.expand_frame_repr", False)
    print(wf_df.to_string(index=False))


if __name__ == "__main__":
    main()
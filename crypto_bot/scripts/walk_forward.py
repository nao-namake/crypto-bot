# crypto_bot/scripts/walk_forward.py

import argparse
import sys
from copy import deepcopy
from typing import List, Tuple

import pandas as pd

from crypto_bot.backtest.engine import BacktestEngine
from crypto_bot.backtest.optimizer import ParameterOptimizer
from crypto_bot.data.fetcher import DataPreprocessor, MarketDataFetcher
from crypto_bot.ml.optimizer import optimize_ml
from crypto_bot.strategy.bollinger import BollingerStrategy


def split_walk_forward(
    df: pd.DataFrame, train_window: int, test_window: int, step: int
) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
    """
    Walk-forward 分割を行い、
    (train_df, test_df) のタプルリストを返す。
    """
    splits: List[Tuple[pd.DataFrame, pd.DataFrame]] = []
    n = len(df)
    start = 0
    while start + train_window + test_window <= n:
        train = df.iloc[start : start + train_window]
        test = df.iloc[start + train_window : start + train_window + test_window]
        splits.append((train, test))
        start += step
    return splits


def walk_forward_test(
    df: pd.DataFrame,
    train_window: int,
    test_window: int,
    step: int,
    periods: list,
    nbdevs: list,
    starting_balance: float,
    slippage_rate: float,
) -> pd.DataFrame:
    """
    df を train_window + test_window の窓でスライドしながら
    パラメータ最適化 → バックテスト を繰り返し、
    結果をまとめた DataFrame を返す。
    （戦略：Bollinger）
    """
    results = []
    splits = split_walk_forward(df, train_window, test_window, step)

    for i, (train_df, test_df) in enumerate(splits):
        # 1) 訓練データで最適化（戦略パラメータスキャン）
        opt = ParameterOptimizer(
            price_df=train_df,
            starting_balance=starting_balance,
            slippage_rate=slippage_rate,
        )
        scan_df = opt.scan(periods=periods, nbdevs=nbdevs)
        best = scan_df.sort_values("total_profit", ascending=False).iloc[0]

        # 2) テストデータでバックテスト実行
        strat = BollingerStrategy(
            period=int(best.period),
            nbdevup=float(best.nbdev),
            nbdevdn=float(best.nbdev),
        )
        engine = BacktestEngine(
            price_df=test_df,
            strategy=strat,
            starting_balance=starting_balance,
            slippage_rate=slippage_rate,
        )
        engine.run()
        stats = engine.statistics()

        # 3) 結果を格納
        results.append(
            {
                "fold": i,
                "train_start": train_df.index[0],
                "train_end": train_df.index[-1],
                "test_start": test_df.index[0],
                "test_end": test_df.index[-1],
                "period": best.period,
                "nbdev": best.nbdev,
                **stats,
            }
        )

    return pd.DataFrame(results)


def walk_forward_optuna(config: dict) -> pd.DataFrame:
    """
    設定辞書 (config) を受け取り、
    - config['data'] でデータ取得 or DataFrame を受け取り
    - config['walk_forward'] でウィンドウを決定
    - config['ml']['optuna'] を用いて ML ハイパーパラ最適化を各 fold ごとに実行
    結果として各 fold の best_params をまとめた DataFrame を返す。
    """
    # --- データ取得 or 既存 DataFrame 取り出し ---
    data_cfg = config.get("data", {})
    if "df" in data_cfg and isinstance(data_cfg["df"], pd.DataFrame):
        df = data_cfg["df"]
    else:
        fetcher = MarketDataFetcher(
            exchange_id=data_cfg.get("exchange", "bybit"),
            symbol=data_cfg["symbol"],
        )
        df = fetcher.get_price_df(
            timeframe=data_cfg.get("timeframe"),
            since=data_cfg.get("since"),
            limit=data_cfg.get("limit"),
            paginate=data_cfg.get("paginate", False),
            per_page=data_cfg.get("per_page", 0),
        )
    # --- ウォークフォワード分割設定 ---
    wf = config["walk_forward"]
    splits = split_walk_forward(df, wf["train_window"], wf["test_window"], wf["step"])

    results = []
    for i, (train_df, _) in enumerate(splits):
        # 各 fold 用に設定をクローンして train_df を埋め込む
        cfg_i = deepcopy(config)
        cfg_i["data"] = {"df": train_df}

        # ML のハイパーパラ最適化（Optuna）
        study = optimize_ml(cfg_i)
        best = study.best_params

        results.append({"fold": i, **best})

    return pd.DataFrame(results)


def main():
    """
    デフォルト動作: Bybit 1h データを取得し、
    Preprocessor＋Bollinger＋ウォークフォワードテストを実行。
    """
    # 1) データ取得
    fetcher = MarketDataFetcher(exchange_id="bybit", symbol="BTC/USDT")
    ts = int(pd.Timestamp("2022-01-01T00:00:00Z").value // 10**6)
    df = fetcher.get_price_df(
        timeframe="1h", since=ts, limit=3000, paginate=True, per_page=500
    )

    # 2) 前処理
    df = DataPreprocessor.clean(df, timeframe="1h", z_thresh=5.0, window=20)

    # 3) Walk-Forward テスト
    wf_df = walk_forward_test(
        df=df,
        train_window=500,
        test_window=100,
        step=100,
        periods=[10, 20, 30],
        nbdevs=[1.5, 2.0, 2.5],
        starting_balance=10_000.0,
        slippage_rate=0.0,
    )

    # 4) 結果表示
    pd.set_option("display.expand_frame_repr", False)
    print(wf_df.to_string(index=False))


if __name__ == "__main__":
    # CLI版を用意
    parser = argparse.ArgumentParser(
        description="Walk-forward テスト / Optuna ML 最適化"
    )
    parser.add_argument(
        "--config", "-c", dest="config", help="YAML 設定ファイル (ML 用)"
    )
    args = parser.parse_args()

    if args.config:
        # config を読み込んで ML walk-forward 最適化を実行
        import yaml

        with open(args.config, "r") as f:
            cfg = yaml.safe_load(f)
        df_best = walk_forward_optuna(cfg)
        print(df_best.to_string(index=False))
        sys.exit(0)

    # config 未指定 → デフォルト main() 動作
    main()

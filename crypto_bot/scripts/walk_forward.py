# =============================================================================
# ファイル名: crypto_bot/scripts/walk_forward.py
# 説明:
# このスクリプトは、時系列データの「ウォークフォワードテスト」を自動で行うものです。
# ・機械学習戦略(MLStrategy)などを用いて、指定した「学習期間→テスト期間」を
#   繰り返しスライドさせて検証します。
# ・結果をCSVで保存し、パフォーマンス評価ができます。
#
# 例: 2か月分学習→10日テスト、を1歩ずつずらして全期間テスト
#
# 利用方法:
#   python scripts/walk_forward.py -c ./config/yourconfig.yml
#   -o ./results/walk_forward_metrics.csv
# =============================================================================

import argparse
from pathlib import Path
from typing import Callable, List, Tuple

import pandas as pd
import yaml

from crypto_bot.backtest.engine import BacktestEngine
from crypto_bot.data.fetcher import DataPreprocessor, MarketDataFetcher
from crypto_bot.strategy.base import StrategyBase
from crypto_bot.strategy.ml_strategy import MLStrategy


def split_walk_forward(
    df: pd.DataFrame, train_window: int, test_window: int, step: int
) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
    """
    時系列データを「学習期間」と「テスト期間」で分割し、窓をスライドさせて
    (train_df, test_df) のペアをリストで返します。
    例: 2000本学習+250本テストを250本ずつスライド
    """
    # --- parameter validation ---
    if train_window <= 0 or test_window <= 0:
        raise ValueError("train_window and test_window must be positive.")
    if step <= 0:
        raise ValueError("step must be positive.")
    # 十分なデータ長が無い場合は空リストを返す
    if len(df) < train_window + test_window:
        return []
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
    strategy_factory: Callable[[], StrategyBase],
    starting_balance: float,
    slippage_rate: float,
) -> pd.DataFrame:
    """
    ウォークフォワードで複数の学習+テスト窓をスライドし、
    各テスト期間でバックテスト→結果をDataFrameで返します。
    """
    results = []
    splits = split_walk_forward(df, train_window, test_window, step)

    for i, (train_df, test_df) in enumerate(splits):
        strat = strategy_factory()
        engine = BacktestEngine(
            price_df=test_df,
            strategy=strat,
            starting_balance=starting_balance,
            slippage_rate=slippage_rate,
        )
        engine.run()
        stats = engine.statistics()

        results.append(
            {
                "fold": i,
                "train_start": train_df.index[0],
                "train_end": train_df.index[-1],
                "test_start": test_df.index[0],
                "test_end": test_df.index[-1],
                **stats,
            }
        )

    return pd.DataFrame(results)


def make_strategy_factory(model_path, threshold, cfg):
    """MLStrategyインスタンスを返すファクトリ関数（lambda回避）"""

    def factory():
        return MLStrategy(model_path=model_path, threshold=threshold, config=cfg)

    return factory


def main(config_path=None, output_path=None):
    """
    設定ファイルから各種パラメータを読み込んでウォークフォワードテストを実行し、
    結果をCSV保存します。
    """
    # Load config
    if config_path is not None:
        cfg_path = Path(config_path)
        project_root = (
            cfg_path.parent.parent
            if cfg_path.parent.name == "config"
            else Path(__file__).resolve().parents[2]
        )
        cfg = yaml.safe_load(open(cfg_path))
    else:
        project_root = Path(__file__).resolve().parents[2]
        cfg = yaml.safe_load(open(project_root / "config" / "default.yml"))

    # 1) データ取得
    fetch_cfg = cfg["data"]
    fetcher = MarketDataFetcher(
        exchange_id=fetch_cfg["exchange"],
        symbol=fetch_cfg["symbol"],
        ccxt_options=fetch_cfg.get("ccxt_options", {}),
    )
    df = fetcher.get_price_df(
        timeframe=fetch_cfg["timeframe"],
        since=fetch_cfg["since"],
        limit=fetch_cfg["limit"],
        paginate=fetch_cfg["paginate"],
        per_page=fetch_cfg["per_page"],
    )

    # 2) 前処理
    df = DataPreprocessor.clean(
        df, timeframe=fetch_cfg["timeframe"], thresh=5.0, window=20
    )

    # 3) 戦略インスタンス生成関数
    strat_cfg = cfg["strategy"]["params"]
    model_path = strat_cfg["model_path"]
    threshold = strat_cfg.get("threshold", 0.0)
    strategy_factory = make_strategy_factory(model_path, threshold, cfg)

    # 4) テスト実行
    wf_df = walk_forward_test(
        df=df,
        train_window=cfg["walk_forward"]["train_window"],
        test_window=cfg["walk_forward"]["test_window"],
        step=cfg["walk_forward"]["step"],
        strategy_factory=strategy_factory,
        starting_balance=cfg["backtest"]["starting_balance"],
        slippage_rate=cfg["backtest"]["slippage_rate"],
    )

    # 5) 結果表示と保存
    pd.set_option("display.expand_frame_repr", False)
    print(wf_df.to_string(index=False))
    if output_path is not None:
        output_file = Path(output_path)
        output_dir = output_file.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        wf_df.to_csv(output_file, index=False)
        print(f"Walk-forward metrics saved to {output_file}")
    else:
        output_dir = project_root / "results"
        output_file = output_dir / "walk_forward_metrics.csv"
        output_dir.mkdir(parents=True, exist_ok=True)
        wf_df.to_csv(output_file, index=False)
        print(f"Walk-forward metrics saved to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Walk-forward テスト (MLStrategy)")
    parser.add_argument(
        "-c", "--config", dest="config", default=None, help="Path to config YAML"
    )
    parser.add_argument(
        "-o", "--output", dest="output", default=None, help="CSV file to save metrics"
    )
    args = parser.parse_args()
    main_args = {}
    if args.config is not None:
        main_args["config_path"] = args.config
    if args.output is not None:
        main_args["output_path"] = args.output
    main(**main_args)

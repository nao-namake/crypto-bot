"""
Optimization related CLI commands
"""

import logging
import os

# Backtest engine import - 統合バックテストエンジン使用
import sys
from typing import Any, Dict, List

import click
import pandas as pd

# プロジェクトルートからの相対パスでbacktestディレクトリを追加
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, os.path.join(project_root, "backtest"))
from engine.backtest_engine import BacktestEngine

from crypto_bot.data.fetcher import DataPreprocessor, MarketDataFetcher
from crypto_bot.scripts.walk_forward import split_walk_forward
from crypto_bot.strategy.factory import StrategyFactory
from crypto_bot.utils.config import load_config
from crypto_bot.utils.config_state import set_current_config
from crypto_bot.utils.file import ensure_dir_for_file

logger = logging.getLogger(__name__)


def run_optimization(
    cfg: Dict[str, Any], param_grid: Dict[str, List[Any]]
) -> pd.DataFrame:
    """パラメータグリッドでバックテスト最適化を実行"""
    # データ取得
    dd = cfg.get("data", {})

    if dd.get("exchange") == "csv" or dd.get("csv_path"):
        fetcher = MarketDataFetcher(csv_path=dd.get("csv_path"))
        df = fetcher.get_price_df(
            since=dd.get("since"),
            limit=dd.get("limit"),
        )
    else:
        fetcher = MarketDataFetcher(
            exchange_id=dd.get("exchange"),
            symbol=dd.get("symbol"),
            ccxt_options=dd.get("ccxt_options"),
        )
        # ベースタイムフレーム決定
        base_timeframe = "1h"  # デフォルト
        if (
            "multi_timeframe_data" in dd
            and "base_timeframe" in dd["multi_timeframe_data"]
        ):
            base_timeframe = dd["multi_timeframe_data"]["base_timeframe"]
        else:
            timeframe_raw = dd.get("timeframe", "1h")
            if timeframe_raw == "4h":
                base_timeframe = "1h"  # 4h要求を強制的に1hに変換
            else:
                base_timeframe = timeframe_raw

        df = fetcher.get_price_df(
            timeframe=base_timeframe,
            since=dd.get("since"),
            limit=dd.get("limit"),
            paginate=dd.get("paginate", False),
            per_page=dd.get("per_page", 0),
        )

    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    # データクリーニング
    window = cfg["ml"].get("feat_period", 0)
    df = DataPreprocessor.clean(df, timeframe=dd.get("timeframe", "1h"), window=window)

    # Walk-forward分割
    wf = cfg["walk_forward"]
    splits = split_walk_forward(df, wf["train_window"], wf["test_window"], wf["step"])

    # パラメータ組み合わせを生成
    from itertools import product

    param_names = list(param_grid.keys())
    param_values = [param_grid[name] for name in param_names]
    param_combinations = list(product(*param_values))

    results = []

    for params in param_combinations:
        param_dict = dict(zip(param_names, params))

        # 設定を更新
        test_cfg = cfg.copy()
        for key, value in param_dict.items():
            # ネストしたキーに対応（例: "ml.threshold" -> cfg["ml"]["threshold"]）
            keys = key.split(".")
            target = test_cfg
            for k in keys[:-1]:
                target = target.setdefault(k, {})
            target[keys[-1]] = value

        # 戦略作成
        strategy_config = test_cfg.get("strategy", {})
        strategy_type = strategy_config.get("type", "single")

        if strategy_type == "multi":
            strategies_config = strategy_config.get("strategies", [])
            combination_mode = strategy_config.get(
                "combination_mode", "weighted_average"
            )
            strategy = StrategyFactory.create_multi_strategy(
                strategies_config, combination_mode
            )
        else:
            strategy = StrategyFactory.create_strategy(strategy_config, test_cfg)

        # Walk-forward バックテスト
        metrics_list = []
        for _, test_df in splits:
            engine = BacktestEngine(
                price_df=test_df,
                strategy=strategy,
                starting_balance=test_cfg["backtest"]["starting_balance"],
                slippage_rate=test_cfg["backtest"].get("slippage_rate", 0.0),
            )
            m_df, _ = engine.run()

            if not m_df.empty:
                metrics_list.append(m_df)

        # 結果集計
        if metrics_list:
            all_metrics = pd.concat(metrics_list, ignore_index=True)
            result = {
                **param_dict,
                "total_return": (
                    all_metrics["total_return"].mean()
                    if "total_return" in all_metrics
                    else 0
                ),
                "sharpe_ratio": (
                    all_metrics["sharpe_ratio"].mean()
                    if "sharpe_ratio" in all_metrics
                    else 0
                ),
                "max_drawdown": (
                    all_metrics["max_drawdown"].mean()
                    if "max_drawdown" in all_metrics
                    else 0
                ),
                "win_rate": (
                    all_metrics["win_rate"].mean() if "win_rate" in all_metrics else 0
                ),
                "trade_count": (
                    all_metrics["trade_count"].sum()
                    if "trade_count" in all_metrics
                    else 0
                ),
            }
            results.append(result)

    return pd.DataFrame(results)


@click.command()
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option(
    "--output",
    "-o",
    "output_csv",
    default="results/optimization_results.csv",
    type=click.Path(),
)
def optimize_backtest_command(config_path: str, output_csv: str):
    """バックテスト最適化"""
    cfg = load_config(config_path)
    set_current_config(cfg)  # Phase H.22.3: ATR期間統一
    ensure_dir_for_file(output_csv)

    # 最適化パラメータグリッド（設定ファイルから読み込み）
    param_grid = cfg.get("optimization", {}).get(
        "param_grid",
        {
            "ml.threshold": [0.5, 0.55, 0.6, 0.65],
            "risk.risk_per_trade": [0.005, 0.01, 0.02],
            "risk.stop_atr_mult": [1.0, 1.5, 2.0, 2.5],
        },
    )

    click.echo("🔍 Starting backtest optimization...")
    click.echo(f"Parameter grid: {param_grid}")

    # 最適化実行
    results_df = run_optimization(cfg, param_grid)

    if results_df.empty:
        click.echo("❌ No valid results from optimization", err=True)
        return

    # 結果を保存
    results_df.to_csv(output_csv, index=False)
    click.echo(f"✅ Optimization results saved to {output_csv}")

    # ベスト結果を表示
    best_by_return = results_df.loc[results_df["total_return"].idxmax()]
    best_by_sharpe = results_df.loc[results_df["sharpe_ratio"].idxmax()]

    click.echo("\n=== Best Parameters ===")
    click.echo("\n📈 By Total Return:")
    for key, value in best_by_return.items():
        if not key.startswith(
            ("total_return", "sharpe_ratio", "max_drawdown", "win_rate", "trade_count")
        ):
            click.echo(f"  {key}: {value}")
    click.echo(f"  → Total Return: {best_by_return['total_return']:.2%}")
    click.echo(f"  → Sharpe Ratio: {best_by_return['sharpe_ratio']:.3f}")

    click.echo("\n📊 By Sharpe Ratio:")
    for key, value in best_by_sharpe.items():
        if not key.startswith(
            ("total_return", "sharpe_ratio", "max_drawdown", "win_rate", "trade_count")
        ):
            click.echo(f"  {key}: {value}")
    click.echo(f"  → Total Return: {best_by_sharpe['total_return']:.2%}")
    click.echo(f"  → Sharpe Ratio: {best_by_sharpe['sharpe_ratio']:.3f}")

    # 上位10結果を表示
    click.echo("\n=== Top 10 Results by Sharpe Ratio ===")
    top_10 = results_df.nlargest(10, "sharpe_ratio")[
        ["total_return", "sharpe_ratio", "max_drawdown", "win_rate", "trade_count"]
    ]
    click.echo(top_10.to_string(index=False))

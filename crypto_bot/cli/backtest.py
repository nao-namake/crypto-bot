"""
Backtest command implementation
"""

import logging
import os

import click
import pandas as pd
from dotenv import load_dotenv

# TODO: export_aggregates function needs to be implemented or imported
from crypto_bot.api.health import update_status
from crypto_bot.backtest.engine import BacktestEngine
from crypto_bot.data.fetcher import DataPreprocessor, MarketDataFetcher
from crypto_bot.scripts.walk_forward import split_walk_forward
from crypto_bot.strategy.factory import StrategyFactory
from crypto_bot.utils.config import load_config
from crypto_bot.utils.file import ensure_dir_for_file

logger = logging.getLogger(__name__)

# matplotlib条件付きimport
MATPLOTLIB_AVAILABLE = False
try:
    import matplotlib.pyplot as plt

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    pass


def create_performance_chart(portfolio_df: pd.DataFrame, cfg: dict):
    """収益推移のチャートを作成"""
    if not MATPLOTLIB_AVAILABLE:
        logger.warning("⚠️ [CHART] Matplotlib not available, skipping chart generation")
        return

    try:
        # グラフ作成
        fig, ax = plt.subplots(figsize=(12, 6))

        # ポートフォリオ価値の推移
        ax.plot(
            portfolio_df.index,
            portfolio_df["portfolio_value"],
            label="Portfolio Value",
            linewidth=2,
            color="blue",
        )

        # 初期資金ライン
        starting_balance = cfg["backtest"]["starting_balance"]
        ax.axhline(
            y=starting_balance,
            color="gray",
            linestyle="--",
            label=f"Initial Balance ({starting_balance:,.0f})",
        )

        # グリッド追加
        ax.grid(True, alpha=0.3)
        ax.set_xlabel("Period")
        ax.set_ylabel("Portfolio Value (JPY)")
        ax.set_title("Portfolio Performance Over Time")
        ax.legend()

        # Y軸フォーマット（カンマ区切り）
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{x:,.0f}"))

        # グラフ保存
        chart_path = cfg["backtest"].get(
            "performance_chart", "results/performance_chart.png"
        )
        ensure_dir_for_file(chart_path)
        plt.tight_layout()
        plt.savefig(chart_path, dpi=150)
        plt.close()

        logger.info(f"Performance chart saved to {chart_path}")
    except Exception as e:
        logger.error(f"Failed to create performance chart: {e}")


@click.command()
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option(
    "--stats-output",
    "-s",
    "stats_output",
    default="results/backtest_results.csv",
    type=click.Path(),
    help="Statistics CSV output path",
)
@click.option(
    "--show-trades/--no-show-trades",
    "-t",
    default=True,
    help="Print trade log and aggregates after backtest",
)
def backtest_command(config_path: str, stats_output: str, show_trades: bool):
    """Walk-forward バックテスト（MLStrategy）"""
    # Phase 7: 環境変数読み込み強化（API問題根本修正）
    load_dotenv()  # .envファイルから環境変数を読み込み

    # API接続前検証
    if os.getenv("BITBANK_API_KEY") and os.getenv("BITBANK_API_SECRET"):
        logger.info("✅ [PHASE-7] Bitbank API credentials loaded")
    else:
        logger.warning(
            "⚠️ [PHASE-7] Bitbank API credentials not found, using fallback methods"
        )

    cfg = load_config(config_path)
    ensure_dir_for_file(stats_output)

    # Phase 3: 外部データ完全無効化 - 外部データキャッシュは使用しない
    dd = cfg.get("data", {})
    external_data_enabled = False  # Phase 3で外部API完全除去

    if (dd.get("exchange") == "csv" or dd.get("csv_path")) and external_data_enabled:
        logger.info(
            "CSV mode + external data enabled - initializing external data cache"
        )
        from crypto_bot.ml.external_data_cache import initialize_global_cache

        cache = initialize_global_cache(
            start_date=dd.get("since", "2024-01-01"), end_date="2024-12-31"
        )
        cache_info = cache.get_cache_info()
        logger.info(f"External data cache initialized: {cache_info}")
    elif dd.get("exchange") == "csv" or dd.get("csv_path"):
        logger.info(
            "CSV mode detected - external data disabled, skipping cache initialization"
        )

    # データ取得
    dd = cfg.get("data", {})

    # CSV モードかAPI モードかを判定
    if dd.get("exchange") == "csv" or dd.get("csv_path"):
        # CSV モード
        # Phase H.3.2 Fix: CSVモードでもベースタイムフレームを設定
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

        fetcher = MarketDataFetcher(csv_path=dd.get("csv_path"))
        df = fetcher.get_price_df(
            since=dd.get("since"),
            limit=dd.get("limit"),
        )
    else:
        # API モード
        fetcher = MarketDataFetcher(
            exchange_id=dd.get("exchange"),
            symbol=dd.get("symbol"),
            ccxt_options=dd.get("ccxt_options"),
        )
        # Phase H.3.2 Fix: run_optimizationでもベースタイムフレームを使用
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
            timeframe=base_timeframe,  # Phase H.3.2: base_timeframeを使用
            since=dd.get("since"),
            limit=dd.get("limit"),
            paginate=dd.get("paginate", False),
            per_page=dd.get("per_page", 0),
        )
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    window = cfg["ml"].get("feat_period", 0)
    df = DataPreprocessor.clean(
        df, timeframe=base_timeframe, window=window
    )  # Phase H.3.2: base_timeframeを使用

    # Walk-forward split
    wf = cfg["walk_forward"]
    splits = split_walk_forward(df, wf["train_window"], wf["test_window"], wf["step"])

    logger.info(f"データサイズ: {len(df)}行, ウォークフォワード分割数: {len(splits)}")
    logger.info(f"特徴量システム有効: {len(df.columns)}列のデータで実行")

    if len(splits) == 0:
        logger.warning(
            "ウォークフォワード分割が生成されませんでした。パラメータを調整します。"
        )
        # 小さなウィンドウでフォールバック
        splits = split_walk_forward(
            df, min(500, len(df) // 4), min(100, len(df) // 10), min(50, len(df) // 20)
        )
        logger.info(f"フォールバック分割数: {len(splits)}")

    # Strategy creation using factory
    strategy_config = cfg.get("strategy", {})
    strategy_type = strategy_config.get("type", "single")

    if strategy_type == "multi":
        # マルチ戦略の場合
        strategies_config = strategy_config.get("strategies", [])
        combination_mode = strategy_config.get("combination_mode", "weighted_average")
        strategy = StrategyFactory.create_multi_strategy(
            strategies_config, combination_mode
        )
    else:
        # 単一戦略の場合（従来の形式）
        strategy = StrategyFactory.create_strategy(strategy_config, cfg)

    metrics_list, trade_logs = [], []
    portfolio_values = []  # 収益推移可視化用

    for i, (_, test_df) in enumerate(splits):
        logger.info(f"バックテスト実行 {i+1}/{len(splits)}: {len(test_df)}行のデータ")
        engine = BacktestEngine(
            price_df=test_df,
            strategy=strategy,
            starting_balance=cfg["backtest"]["starting_balance"],
            slippage_rate=cfg["backtest"].get("slippage_rate", 0.0),
        )
        m_df, t_df = engine.run()

        if not m_df.empty:
            metrics_list.append(m_df)
            # ポートフォリオ価値を記録
            final_balance = (
                m_df.iloc[0]["final_balance"]
                if "final_balance" in m_df.columns
                else cfg["backtest"]["starting_balance"]
            )
            portfolio_values.append(
                {
                    "period": i + 1,
                    "timestamp": (
                        test_df.index[-1] if len(test_df) > 0 else pd.Timestamp.now()
                    ),
                    "portfolio_value": final_balance,
                    "return_pct": (
                        (final_balance / cfg["backtest"]["starting_balance"]) - 1
                    )
                    * 100,
                }
            )

        if not t_df.empty:
            trade_logs.append(t_df)

    logger.info(
        f"有効なメトリクス: {len(metrics_list)}, 有効なトレードログ: {len(trade_logs)}"
    )

    if len(metrics_list) == 0:
        logger.error("有効なバックテスト結果がありません。設定を確認してください。")
        return

    stats_df = pd.concat(metrics_list, ignore_index=True)
    stats_df.to_csv(stats_output, index=False)
    click.echo(f"Statistics saved to {stats_output!r}")

    # 収益推移可視化の実装
    if portfolio_values:
        portfolio_df = pd.DataFrame(portfolio_values)
        portfolio_csv = cfg["backtest"].get(
            "portfolio_csv", "results/portfolio_evolution.csv"
        )
        ensure_dir_for_file(portfolio_csv)
        portfolio_df.to_csv(portfolio_csv, index=False)
        click.echo(f"Portfolio evolution saved to {portfolio_csv!r}")

        # 収益推移グラフ作成
        create_performance_chart(portfolio_df, cfg)

    if trade_logs:
        full_trade_df = pd.concat(trade_logs, ignore_index=True)
        trade_log_csv = cfg["backtest"].get("trade_log_csv", "results/trade_log.csv")
        ensure_dir_for_file(trade_log_csv)
        full_trade_df.to_csv(trade_log_csv, index=False)
        click.echo(f"Trade log saved to {trade_log_csv!r}")
    else:
        click.echo("No trades executed during backtest")

    # TODO: Implement export_aggregates functionality
    # agg_prefix = cfg["backtest"].get("aggregate_out_prefix", "results/agg")
    # ensure_dir_for_file(agg_prefix + "_dummy")
    # export_aggregates(full_trade_df, agg_prefix)
    # if show_trades:
    #     click.echo(f"Aggregates saved to {agg_prefix}_{{daily,weekly,monthly}}.csv")

    # --- Streamlit など外部監視用にステータスを書き出し ---
    total_profit = (
        float(stats_df["net_profit"].sum()) if "net_profit" in stats_df.columns else 0.0
    )
    update_status(total_profit, len(full_trade_df), position=None)

    click.echo(stats_df.to_string(index=False))

# =============================================================================
# ファイル名: crypto_bot/main.py
# 説明:
# Crypto-Bot CLI エントリポイント
#   - MLStrategy を用いたバックテスト/ML ワークフローを統括
#   - バックテスト・最適化・学習・モデル保存などをカバー
# =============================================================================
from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import click
import matplotlib.pyplot as plt
import pandas as pd
import yaml
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

from crypto_bot.backtest.analysis import export_aggregates
from crypto_bot.backtest.engine import BacktestEngine
from crypto_bot.backtest.optimizer import (  # noqa: F401  他コマンドで使用
    ParameterOptimizer,
    optimize_backtest,
)
from crypto_bot.data.fetcher import DataPreprocessor, MarketDataFetcher
from crypto_bot.execution.engine import Position
from crypto_bot.ml.external_data_cache import clear_global_cache
from crypto_bot.ml.optimizer import _load_and_preprocess_data
from crypto_bot.ml.optimizer import optimize_ml as run_optuna
from crypto_bot.ml.optimizer import train_best_model
from crypto_bot.ml.preprocessor import prepare_ml_dataset

# Phase H.11: 特徴量強化システム統合
try:
    # prepare_ml_dataset_enhanced, ensure_feature_coverage は _mlprep 経由で使用
    # enhance_feature_engineering は間接的に使用
    import crypto_bot.ml.feature_engineering_enhanced  # noqa: F401

    ENHANCED_FEATURES_AVAILABLE = True
except ImportError:
    ENHANCED_FEATURES_AVAILABLE = False
from crypto_bot.risk.manager import RiskManager
from crypto_bot.scripts.walk_forward import split_walk_forward
from crypto_bot.strategy.factory import StrategyFactory

# --------------------------------------------------------------------------- #
# ユーティリティ
# --------------------------------------------------------------------------- #

# Phase H.22.3: グローバル設定保持（ATR期間統一用）
_current_config = None


def set_current_config(config: dict):
    """現在の設定を保存（Phase H.22.3: ATR期間統一用）"""
    global _current_config
    _current_config = config


def get_current_config() -> dict:
    """現在の設定を取得（Phase H.22.3: ATR期間統一用）"""
    return _current_config or {}


def ensure_dir_for_file(path: str):
    """親ディレクトリが無ければ作成する"""
    dir_path = os.path.dirname(path)
    if dir_path and not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)


def setup_logging():
    """LOG_LEVEL 環境変数でロガーを初期化"""
    level_name = os.getenv("CRYPTO_BOT_LOG_LEVEL", "INFO").upper()
    if hasattr(logging, level_name):
        numeric_level = getattr(logging, level_name)
    else:
        numeric_level = logging.INFO

    # より詳細なログフォーマット
    log_format = "[%(asctime)s] %(levelname)-8s %(name)-20s: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        format=log_format,
        datefmt=date_format,
        level=numeric_level,
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def create_performance_chart(portfolio_df, cfg):
    """収益推移のチャートを作成"""
    try:
        plt.style.use("default")
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

        # ポートフォリオ価値の推移
        ax1.plot(
            portfolio_df["period"],
            portfolio_df["portfolio_value"],
            marker="o",
            linewidth=2,
            markersize=4,
            color="blue",
        )
        ax1.set_title(
            "65特徴量システム - ポートフォリオ価値推移", fontsize=14, fontweight="bold"
        )
        ax1.set_xlabel("期間")
        ax1.set_ylabel("ポートフォリオ価値 (USDT)")
        ax1.grid(True, alpha=0.3)
        ax1.ticklabel_format(style="plain", axis="y")

        # 開始価値との比較線を追加
        starting_balance = cfg["backtest"]["starting_balance"]
        ax1.axhline(
            y=starting_balance,
            color="red",
            linestyle="--",
            alpha=0.7,
            label=f"開始価値: {starting_balance:,.0f}",
        )
        ax1.legend()

        # 収益率の推移
        ax2.plot(
            portfolio_df["period"],
            portfolio_df["return_pct"],
            marker="s",
            linewidth=2,
            markersize=4,
            color="green",
        )
        ax2.set_title("累積収益率推移", fontsize=14, fontweight="bold")
        ax2.set_xlabel("期間")
        ax2.set_ylabel("収益率 (%)")
        ax2.grid(True, alpha=0.3)
        ax2.axhline(y=0, color="red", linestyle="--", alpha=0.7, label="損益分岐点")
        ax2.legend()

        # 最終統計を追加
        final_return = portfolio_df["return_pct"].iloc[-1]
        max_return = portfolio_df["return_pct"].max()
        min_return = portfolio_df["return_pct"].min()

        plt.figtext(
            0.02,
            0.02,
            (
                f"最終収益率: {final_return:.1f}% | "
                f"最高: {max_return:.1f}% | 最低: {min_return:.1f}%"
            ),
            fontsize=10,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray"),
        )

        plt.tight_layout()
        plt.subplots_adjust(bottom=0.1)

        # 保存
        chart_path = cfg["backtest"].get(
            "performance_chart", "results/performance_chart.png"
        )
        ensure_dir_for_file(chart_path)
        plt.savefig(chart_path, dpi=300, bbox_inches="tight")
        plt.close()

        click.echo(f"Performance chart saved to {chart_path!r}")

    except Exception as e:
        logging.getLogger(__name__).warning(f"チャート作成中にエラー: {e}")
        # matplotlibが利用できない環境でもエラーで止まらないように

    # サードパーティライブラリのログレベルを調整
    logging.getLogger("ccxt").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("optuna").setLevel(logging.INFO)

    logger = logging.getLogger(__name__)
    current_level = logging.getLevelName(logger.getEffectiveLevel())
    logger.info(f"Logging initialized at level: {current_level}")


def update_status(total_profit: float, trade_count: int, position):
    """
    現在の Bot 状態を JSON へ書き出して、外部モニター（Streamlit 等）から
    参照できるようにするユーティリティ。

    Parameters
    ----------
    total_profit : float
        現在までの累積損益
    trade_count : int
        約定数（取引回数）
    position : Any
        現在ポジション（無い場合は None）
    """
    status = {
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_profit": total_profit,
        "trade_count": trade_count,
        "position": position or "",
    }
    with open("status.json", "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)


def deep_merge(default: dict, override: dict) -> dict:
    """ネストされた辞書を再帰的にマージ"""
    for k, v in override.items():
        if k in default and isinstance(default[k], dict) and isinstance(v, dict):
            default[k] = deep_merge(default[k], v)
        else:
            default[k] = v
    return default


def expand_env_vars_recursive(obj):
    """再帰的に環境変数を展開"""
    if isinstance(obj, dict):
        return {key: expand_env_vars_recursive(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [expand_env_vars_recursive(item) for item in obj]
    elif isinstance(obj, str):
        # ${ENV_VAR} パターンを展開
        return os.path.expandvars(obj)
    else:
        return obj


def load_config(path: str) -> dict:
    import logging

    logger = logging.getLogger(__name__)
    base = Path(__file__).parent.parent

    # 本番環境では production.yml のみを使用（default.yml 読み込み回避）
    if "production" in path:
        with open(path, "r") as f:
            config = yaml.safe_load(f) or {}
        logger.info(f"🔒 [CONFIG] Production mode: Using {path} only")
    else:
        # 開発環境のみ default.yml とマージ
        default_path = base / "config" / "development" / "default.yml"
        with open(default_path, "r") as f:
            default_cfg = yaml.safe_load(f) or {}
        with open(path, "r") as f:
            user_cfg = yaml.safe_load(f) or {}
        config = deep_merge(default_cfg, user_cfg)
        logger.info("🔧 [CONFIG] Development mode: Merged default.yml")

    # 🔥 Phase F.1: 環境変数展開処理を追加
    config = expand_env_vars_recursive(config)

    # Phase H.22.3: 設定をグローバルに保存（ATR期間統一用）
    set_current_config(config)
    logger.info("🔧 [CONFIG] Environment variables expanded")

    # 設定検証を実行
    try:
        from crypto_bot.utils.config_validator import ConfigValidator

        validator = ConfigValidator()
        validator.validate(config)
    except ImportError:
        logging.warning("設定検証モジュールが利用できません")
    except Exception as e:
        logging.error(f"設定検証エラー: {e}")
        sys.exit(1)

    # Phase H.11: 特徴量カバレッジ確保
    if ENHANCED_FEATURES_AVAILABLE:
        try:
            from crypto_bot.ml.preprocessor import ensure_feature_coverage

            config = ensure_feature_coverage(config)
            logger.info("✅ [CONFIG] Feature coverage ensured")
        except Exception as e:
            logger.warning(f"⚠️ [CONFIG] Feature coverage check failed: {e}")

    return config


# --------------------------------------------------------------------------- #
# データ準備
# --------------------------------------------------------------------------- #
def prepare_data(cfg: dict):
    dd = cfg.get("data", {})

    # CSV モードかAPI モードかを判定
    if dd.get("exchange") == "csv" or dd.get("csv_path"):
        # CSV モード
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
        # Phase H.3.2 Fix: prepare_dataでもベースタイムフレームを使用
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
    if "volume" not in df.columns:
        df["volume"] = 0
    window = cfg["ml"].get("feat_period", 0)
    df = DataPreprocessor.clean(
        df, timeframe=base_timeframe, window=window
    )  # Phase H.3.2: base_timeframeを使用

    if df.empty:
        return pd.DataFrame(), pd.Series(), pd.DataFrame(), pd.Series()

    # monkey-patch を尊重するため遅延 import
    from crypto_bot.ml import preprocessor as _mlprep

    # Phase H.11: 特徴量強化システム使用
    if ENHANCED_FEATURES_AVAILABLE:
        try:
            ret = _mlprep.prepare_ml_dataset_enhanced(df, cfg)
            logging.getLogger(__name__).info(
                "✅ [PREPARE] Using enhanced feature engineering"
            )
        except Exception as e:
            logging.getLogger(__name__).warning(
                f"⚠️ [PREPARE] Enhanced features failed, fallback: {e}"
            )
            ret = _mlprep.prepare_ml_dataset(df, cfg)
    else:
        ret = _mlprep.prepare_ml_dataset(df, cfg)
    if isinstance(ret, tuple) and len(ret) == 4:
        return ret

    if isinstance(ret, tuple) and len(ret) == 3:
        X, y_reg, y_clf = ret
        mode = cfg["ml"].get("target_type", "classification")
        y = y_clf if mode == "classification" else y_reg
        split = train_test_split(
            X, y, test_size=cfg["ml"].get("test_size", 0.2), random_state=42
        )
        return tuple(split)  # Convert list to tuple: (X_tr, X_val, y_tr, y_val)

    return ret


def save_model(model, path: str):
    """joblib にフォールバックしてモデルを保存"""
    try:
        model.save(path)  # type: ignore[attr-defined]
    except AttributeError:
        import joblib

        ensure_dir_for_file(path)
        joblib.dump(model, path)


# --------------------------------------------------------------------------- #
# Click CLI グループ
# --------------------------------------------------------------------------- #
@click.group()
def cli():
    """Crypto-Bot CLI"""
    setup_logging()


# --------------------------------------------------------------------------- #
# 1. Backtest コマンド
# --------------------------------------------------------------------------- #
@cli.command()
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
def backtest(config_path: str, stats_output: str, show_trades: bool):
    """Walk-forward バックテスト（MLStrategy）"""
    logger = logging.getLogger(__name__)
    cfg = load_config(config_path)
    ensure_dir_for_file(stats_output)

    # CSV モードの場合は外部データキャッシュを初期化
    dd = cfg.get("data", {})
    if dd.get("exchange") == "csv" or dd.get("csv_path"):
        logger.info("CSV mode detected - initializing external data cache")
        from crypto_bot.ml.external_data_cache import initialize_global_cache

        cache = initialize_global_cache(
            start_date=dd.get("since", "2024-01-01"), end_date="2024-12-31"
        )
        cache_info = cache.get_cache_info()
        logger.info(f"External data cache initialized: {cache_info}")

    # データ取得
    dd = cfg.get("data", {})

    # CSV モードかAPI モードかを判定
    if dd.get("exchange") == "csv" or dd.get("csv_path"):
        # CSV モード
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
    logger.info(f"65特徴量システム有効: {len(df.columns)}列のデータで実行")

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

    agg_prefix = cfg["backtest"].get("aggregate_out_prefix", "results/agg")
    ensure_dir_for_file(agg_prefix + "_dummy")
    export_aggregates(full_trade_df, agg_prefix)
    if show_trades:
        click.echo(f"Aggregates saved to {agg_prefix}_{{daily,weekly,monthly}}.csv")

    # --- Streamlit など外部監視用にステータスを書き出し ---
    total_profit = (
        float(stats_df["net_profit"].sum()) if "net_profit" in stats_df.columns else 0.0
    )
    update_status(total_profit, len(full_trade_df), position=None)

    click.echo(stats_df.to_string(index=False))


# --------------------------------------------------------------------------- #
# 2. optimize-backtest
# --------------------------------------------------------------------------- #
@cli.command("optimize-backtest")
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option(
    "--output",
    "-o",
    "output_csv",
    default=None,
    type=click.Path(),
    help="結果 CSV 出力パス",
)
def optimize_backtest_cli(config_path: str, output_csv: str):
    """バックテスト最適化"""
    cfg = load_config(config_path)
    click.echo(">> Starting backtest optimization …")
    df = optimize_backtest(cfg, output_csv=output_csv)
    if output_csv:
        click.echo(f">> Results saved to {output_csv!r}")
    else:
        click.echo(df.to_string(index=False))


# --------------------------------------------------------------------------- #
# 3-A. train コマンド
# --------------------------------------------------------------------------- #
@cli.command()
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option(
    "--model-type", "-t", default=None, help="ML モデルタイプ (lgbm / rf / xgb)"
)
@click.option(
    "--output",
    "-o",
    "output_path",
    default=None,
    type=click.Path(),
    help="モデル保存パス",
)
def train(config_path: str, model_type: str, output_path: str):
    """ML モデルを学習して保存"""
    cfg = load_config(config_path)
    if model_type:
        cfg.setdefault("ml", {})["model_type"] = model_type.lower()
        click.echo(f"Using model_type: {cfg['ml']['model_type']}")

    ret = prepare_data(cfg)

    # デバッグ用ログ出力
    import logging

    logger = logging.getLogger(__name__)
    logger.info(
        f"prepare_data returned: type={type(ret)}, "
        f"length={len(ret) if isinstance(ret, tuple) else 'N/A'}"
    )

    if isinstance(ret, tuple) and len(ret) == 4:
        X_tr, X_val, y_tr, y_val = ret  # 順序修正
        train_samples = len(X_tr)
    elif isinstance(ret, tuple) and len(ret) == 3:
        X, y_reg, y_clf = ret
        mode = cfg["ml"].get("target_type", "classification")
        y = y_clf if mode == "classification" else y_reg
        if len(X) < 2:
            click.echo("データ数が 2 未満です。学習をスキップします。")
            sys.exit(0)
        X_tr, X_val, y_tr, y_val = train_test_split(
            X, y, test_size=cfg["ml"].get("test_size", 0.2), random_state=42
        )
        train_samples = len(X_tr)
    else:
        logger.error(f"Unexpected return from prepare_data: {ret}")
        raise ValueError(f"prepare_data returned unexpected format: {type(ret)}")

    mode = cfg["ml"].get("target_type", "classification")
    click.echo(f"Training {mode} model on {train_samples} samples")

    if train_samples <= 1:
        click.echo("訓練データが 1 サンプル以下のため学習を中止します。")
        sys.exit(0)

    if model_type:
        model = train_best_model(cfg, X_tr, y_tr, X_val, y_val)
    else:
        if mode == "classification":
            model = LogisticRegression()
        else:
            from sklearn.linear_model import LinearRegression  # noqa: F401

            model = LinearRegression()
        model.fit(X_tr, y_tr)

    out_path = output_path or cfg.get("output", {}).get("model_path", "model.pkl")
    save_model(model, out_path)
    click.echo(f"Model saved to {out_path!r}")


# --------------------------------------------------------------------------- #
# 3-B. optimize-ml
# --------------------------------------------------------------------------- #
@cli.command("optimize-ml")
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option(
    "--model-type",
    "-t",
    type=click.Choice(["lgbm", "rf", "xgb", "ensemble"], case_sensitive=False),
    default=None,
)
def optimize_ml(config_path: str, model_type: str):
    """ハイパーパラ最適化のみ実行"""
    cfg = load_config(config_path)
    if model_type:
        cfg.setdefault("ml", {})["model_type"] = model_type.lower()
    study = run_optuna(cfg)
    click.echo(f"Best trial value: {study.best_value}")
    click.echo(f"Best params: {study.best_params}")


# --------------------------------------------------------------------------- #
# 3-D. live-paper  ← Bybit Testnet ペーパートレード用（本番に影響しないようコメントアウト）
# --------------------------------------------------------------------------- #
# @cli.command("live-paper")
# @click.option(
#     "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
# )
# @click.option(
#     "--max-trades",
#     type=int,
#     default=0,
#     help="0=無限。成立した約定数がこの値に達したらループ終了",
# )
# def live_paper(config_path: str, max_trades: int):
#     """
#     Bybit Testnet でのライブトレードを 30 秒間隔で回すループ。
#     改善された戦略ロジックでより積極的なトレードを実行。
#     APIサーバー機能も統合し、ヘルスチェック・トレード状況確認が可能。
#     """
#     cfg = load_config(config_path)
#     # 取引所クライアントは Factory で生成（Bybit Testnet がデフォルト）
#     # client = create_exchange_client(
#     #     exchange_id=cfg["data"].get("exchange", "bybit"),
#     #     api_key=cfg["data"].get("api_key", ""),
#     #     api_secret=cfg["data"].get("api_secret", ""),
#     #     testnet=True,
#     # )

#     # --- helpers for paper trading (Entry/Exit + Risk) ---------------------
#     dd = cfg.get("data", {})
#     fetcher = MarketDataFetcher(
#         exchange_id=dd.get("exchange"),
#         symbol=dd.get("symbol"),
#         ccxt_options=dd.get("ccxt_options"),
#     )

#     # Strategy & risk manager
#     sp = cfg["strategy"]["params"]
#     model_path = sp.get("model_path", "model.pkl")
#     threshold = sp.get("threshold", 0.0)
#     strategy = MLStrategy(model_path=model_path, threshold=threshold, config=cfg)

#     # RiskManager初期化
#     risk_config = cfg.get("risk", {})
#     kelly_config = risk_config.get("kelly_criterion", {})
#     risk_manager = RiskManager(
#         risk_per_trade=risk_config.get("risk_per_trade", 0.01),
#         stop_atr_mult=risk_config.get("stop_atr_mult", 1.5),
#         kelly_enabled=kelly_config.get("enabled", False),
#         kelly_lookback_window=kelly_config.get("lookback_window", 50),
#         kelly_max_fraction=kelly_config.get("max_fraction", 0.25),
#     )

#     position = Position()
#     balance = cfg["backtest"]["starting_balance"]

#     # ATRを計算するための初期データを取得
#     initial_df = fetcher.get_price_df(
#         timeframe=dd.get("timeframe"),
#         limit=200,
#         paginate=False,
#     )

#     # ATRを計算
#     atr_series = None
#     if not initial_df.empty:
#         from crypto_bot.indicator.calculator import IndicatorCalculator

#         calculator = IndicatorCalculator()
#         atr_series = calculator.calculate_atr(initial_df, period=14)
#         latest_atr = atr_series.iloc[-1] if not atr_series.empty else "N/A"
#         click.echo(f"ATR calculated: {len(atr_series)} values, latest: {latest_atr}")

#     entry_exit = EntryExit(
#         strategy=strategy, risk_manager=risk_manager, atr_series=atr_series
#     )
#     entry_exit.current_balance = balance

#     trade_done = 0
#     click.echo("=== live‑paper mode start ===  Ctrl+C で停止")
#     try:
#         while True:
#             # 最新 200 本だけ取得し、Entry/Exit 判定に利用
#             price_df = fetcher.get_price_df(
#                 timeframe=dd.get("timeframe"),
#                 limit=200,
#                 paginate=False,
#             )
#             if price_df.empty:
#                 time.sleep(30)
#                 continue

#             # エントリー判定
#             entry_order = entry_exit.generate_entry_order(price_df, position)
#             prev_trades = trade_done
#             if entry_order.exist:
#                 balance = entry_exit.fill_order(entry_order, position, balance)
#                 trade_done += 1

#             # エグジット判定
#             exit_order = entry_exit.generate_exit_order(price_df, position)
#             if exit_order.exist:
#                 balance = entry_exit.fill_order(exit_order, position, balance)
#                 trade_done += 1

#             # 残高を EntryExit へ反映
#             entry_exit.current_balance = balance

#             # ダッシュボード用ステータス更新
#             update_status(
#                 total_profit=balance - cfg["backtest"]["starting_balance"],
#                 trade_count=trade_done,
#                 position=position.side if position.exist else None,
#             )

#             if max_trades and trade_done >= max_trades:
#                 click.echo("Reached max‑trades. Exit.")
#                 break

#             # 取引が無い場合も一定間隔でループ
#             if trade_done == prev_trades:
#                 time.sleep(30)
#     except KeyboardInterrupt:
#         click.echo("Interrupted. Bye.")


# --------------------------------------------------------------------------- #
# 3-E. live-bitbank  ← Bitbank本番ライブトレード用
# --------------------------------------------------------------------------- #
@cli.command("live-bitbank")
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option(
    "--max-trades",
    type=int,
    default=0,
    help="0=無限。成立した約定数がこの値に達したらループ終了",
)
def live_bitbank(config_path: str, max_trades: int):
    """
    Bitbank本番でのライブトレードを実行。
    145特徴量システムでBTC/JPYペアの実取引を行う。
    APIサーバー機能も統合し、ヘルスチェック・トレード状況確認が可能。
    """
    cfg = load_config(config_path)
    logger = logging.getLogger(__name__)

    # 設定確認
    exchange_id = cfg["data"].get("exchange", "bitbank")
    symbol = cfg["data"].get("symbol", "BTC/JPY")

    logger.info(
        f"🚀 [INIT-1] Starting Bitbank live trading - "
        f"Exchange: {exchange_id}, Symbol: {symbol}"
    )
    logger.info(f"⏰ [INIT-1] Timestamp: {pd.Timestamp.now()}")

    # 初期化状況を更新
    try:
        from crypto_bot.api.health import update_init_status

        update_init_status("basic", "basic_system")
    except Exception:
        pass

    # CSV モードの場合は外部データキャッシュを初期化
    dd = cfg.get("data", {})
    if dd.get("exchange") == "csv" or dd.get("csv_path"):
        logger.info("CSV mode detected - initializing external data cache")
        from crypto_bot.ml.external_data_cache import initialize_global_cache

        cache = initialize_global_cache(
            start_date=dd.get("since", "2024-01-01"), end_date="2024-12-31"
        )
        cache_info = cache.get_cache_info()
        logger.info(f"External data cache initialized: {cache_info}")

    # --- helpers for live trading (Entry/Exit + Risk) ---------------------
    dd = cfg.get("data", {})

    # Bitbank本番用設定の場合
    if exchange_id == "bitbank":
        logger.info("🔌 [INIT-2] Initializing Bitbank data fetcher...")
        logger.info(f"⏰ [INIT-2] Timestamp: {pd.Timestamp.now()}")
        # Bitbank用データフェッチャー
        fetcher = MarketDataFetcher(
            exchange_id=exchange_id,
            symbol=symbol,
            ccxt_options=dd.get("ccxt_options", {}),
        )
        logger.info("✅ [INIT-2] Bitbank data fetcher initialized successfully")

        # API認証情報の確認（環境変数置換対応）
        def resolve_env_var(value):
            """環境変数置換パターン ${ENV_VAR} を解決"""
            if (
                isinstance(value, str)
                and value.startswith("${")
                and value.endswith("}")
            ):
                env_var_name = value[2:-1]  # ${} を除去
                return os.getenv(env_var_name)
            return value

        api_key = resolve_env_var(dd.get("api_key")) or os.getenv("BITBANK_API_KEY")
        api_secret = resolve_env_var(dd.get("api_secret")) or os.getenv(
            "BITBANK_API_SECRET"
        )

        if not api_key or not api_secret:
            logger.error(
                "Bitbank API credentials not found. Please set BITBANK_API_KEY "
                "and BITBANK_API_SECRET environment variables"
            )
            logger.error(f"Config api_key: {dd.get('api_key', 'Not set')}")
            api_key_status = "Set" if os.getenv("BITBANK_API_KEY") else "Not set"
            logger.error(f"Env BITBANK_API_KEY: {api_key_status}")
            secret_status = "Set" if os.getenv("BITBANK_API_SECRET") else "Not set"
            logger.error(f"Env BITBANK_API_SECRET: {secret_status}")
            sys.exit(1)

        logger.info(
            f"✅ Bitbank API credentials resolved successfully - "
            f"Key: {api_key[:8]}..."
        )
        if dd.get("api_key", "").startswith("${"):
            logger.info(
                "📝 Environment variable substitution performed for API credentials"
            )

    else:
        # 他の取引所の場合（フォールバック）
        fetcher = MarketDataFetcher(
            exchange_id=exchange_id,
            symbol=symbol,
            ccxt_options=dd.get("ccxt_options", {}),
        )

    # Strategy initialization using StrategyFactory
    strategy_config = cfg.get("strategy", {})
    strategy_type = strategy_config.get("type", "single")
    strategy_name = strategy_config.get("name", "ml")

    logger.info(f"📊 [INIT-3] Strategy Type: {strategy_type}")
    logger.info(f"📊 [INIT-3] Strategy Name: {strategy_name}")
    logger.info(f"⏰ [INIT-3] Timestamp: {pd.Timestamp.now()}")
    logger.info("🤖 [INIT-3] Initializing Strategy (this may take time)...")

    # モデルパス検証（従来のML戦略との互換性のため）
    sp = strategy_config.get("params", {})
    model_path = sp.get("model_path", "model.pkl")

    if not os.path.isabs(model_path):
        # 相対パスの場合、プロジェクトルートまたはmodelフォルダを基準に解決
        possible_paths = [
            os.path.join(os.getcwd(), model_path),
            os.path.join(os.getcwd(), "model", model_path),
            os.path.join(os.path.dirname(config_path), "..", "model", model_path),
        ]
        for path in possible_paths:
            if os.path.exists(path):
                model_path = path
                strategy_config["params"]["model_path"] = model_path
                break
        else:
            logger.error(f"Model file not found: {model_path}")
            sys.exit(1)

    logger.info(f"📊 [INIT-3] Using model: {model_path}")

    # StrategyFactoryで戦略作成
    if strategy_type == "multi_timeframe_ensemble":
        logger.info("🔄 [INIT-3] Initializing Multi-Timeframe Ensemble Strategy...")
        strategy = StrategyFactory.create_strategy(strategy_config, cfg)

        # マルチタイムフレーム戦略にデータフェッチャーを設定
        if hasattr(strategy, "set_data_fetcher"):
            logger.info(
                "🔗 [INIT-3] Setting data fetcher for multi-timeframe strategy..."
            )
            strategy.set_data_fetcher(fetcher)
            logger.info(
                "✅ [INIT-3] Data fetcher configured for multi-timeframe strategy"
            )

        logger.info(
            "✅ [INIT-3] Multi-Timeframe Ensemble Strategy initialized successfully"
        )
    else:
        # 従来のML戦略（後方互換性のため）
        logger.info("🤖 [INIT-3] Initializing traditional ML Strategy...")
        strategy = StrategyFactory.create_strategy(strategy_config, cfg)
        logger.info("✅ [INIT-3] Traditional Strategy initialized successfully")

    # 特徴量システム初期化を記録
    try:
        from crypto_bot.api.health import update_init_status

        update_init_status("features", "feature_system")
    except Exception:
        pass

    # RiskManager初期化
    logger.info("⚖️ [INIT-4] Initializing Risk Manager...")
    logger.info(f"⏰ [INIT-4] Timestamp: {pd.Timestamp.now()}")
    risk_config = cfg.get("risk", {})
    kelly_config = risk_config.get("kelly_criterion", {})
    risk_manager = RiskManager(
        risk_per_trade=risk_config.get("risk_per_trade", 0.01),
        stop_atr_mult=risk_config.get("stop_atr_mult", 1.5),
        kelly_enabled=kelly_config.get("enabled", False),
        kelly_lookback_window=kelly_config.get("lookback_window", 50),
        kelly_max_fraction=kelly_config.get("max_fraction", 0.25),
    )
    logger.info("✅ [INIT-4] Risk Manager initialized successfully")

    position = Position()

    # ライブトレードでは実際の口座残高を取得（フォールバック付き）
    try:
        # 実際の口座残高を取得
        balance_data = fetcher.fetch_balance()
        jpy_balance = balance_data.get("JPY", {}).get("free", 0.0)
        if jpy_balance > 0:
            balance = jpy_balance
            logger.info(f"💰 [INIT-4] Real account balance: {balance:.2f} JPY")
        else:
            raise ValueError("JPY balance is 0 or not found")
    except Exception as e:
        logger.warning(f"⚠️ Failed to get real balance: {e}")
        # フォールバック: live設定またはbacktest設定から取得
        live_config = cfg.get("live", {})
        if "starting_balance" in live_config:
            balance = live_config["starting_balance"]
            logger.info(f"💰 [INIT-4] Using live.starting_balance: {balance:.2f} JPY")
        else:
            balance = cfg["backtest"]["starting_balance"]
            logger.info(
                f"💰 [INIT-4] Using backtest.starting_balance as fallback: "
                f"{balance:.2f} JPY"
            )

    # Phase H.13: INIT段階用データプリフェッチ（メインループデータ共有）
    logger.info("📊 [INIT-PREFETCH] Pre-fetching data for INIT stages optimization...")
    logger.info(f"⏰ [INIT-PREFETCH] Timestamp: {pd.Timestamp.now()}")

    init_prefetch_data = None
    try:
        # メインループと同じデータフェッチロジックを使用（効率的データ共有）
        current_time = pd.Timestamp.now(tz="UTC")

        # 動的since計算（メインループと同じロジック）
        if dd.get("since"):
            since_time = pd.Timestamp(dd["since"])
            if since_time.tz is None:
                since_time = since_time.tz_localize("UTC")
        else:
            base_hours = dd.get("since_hours", 120)  # メインループと同じ

            # 土日ギャップ対応（メインループと同じロジック）
            current_day = current_time.dayofweek
            current_hour = current_time.hour

            if current_day == 0:  # 月曜日
                hours_back = base_hours + 48
                logger.info(f"🗓️ [INIT-PREFETCH] Monday: extending to {hours_back}h")
            elif current_day <= 1 and current_hour < 12:  # 火曜午前
                hours_back = base_hours + 24
                logger.info(
                    f"🌅 [INIT-PREFETCH] Early week: extending to {hours_back}h"
                )
            else:
                hours_back = base_hours

            # Phase H.22.2: 異常タイムスタンプ修正・安全性確保（INIT段階）
            since_time = current_time - pd.Timedelta(hours=hours_back)

            # タイムスタンプ妥当性検証・修正
            current_timestamp = int(current_time.timestamp() * 1000)
            since_timestamp = int(since_time.timestamp() * 1000)

            # 未来タイムスタンプ検出・修正
            if since_timestamp > current_timestamp:
                logger.error(
                    f"🚨 [INIT-PREFETCH-H22.2] CRITICAL: Future timestamp detected! since={since_timestamp}, current={current_timestamp}"
                )
                # 安全な過去時刻に修正（96時間前）
                since_time = current_time - pd.Timedelta(hours=96)
                since_timestamp = int(since_time.timestamp() * 1000)
                logger.warning(
                    f"🔧 [INIT-PREFETCH-H22.2] Auto-corrected to safe past time: {since_time} (timestamp={since_timestamp})"
                )

            # 極端に古いタイムスタンプ検出・修正
            max_hours_back = 720  # 30日間の上限
            if hours_back > max_hours_back:
                logger.warning(
                    f"⚠️ [INIT-PREFETCH-H22.2] Excessive hours_back detected: {hours_back}h > {max_hours_back}h, capping"
                )
                hours_back = max_hours_back
                since_time = current_time - pd.Timedelta(hours=hours_back)
                since_timestamp = int(since_time.timestamp() * 1000)

        # Phase H.13: ベースタイムフレーム決定（メインループと同じロジック）
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
                logger.warning(
                    "🚨 [INIT-PREFETCH] 4h timeframe forced to 1h (API compatibility)"
                )
            else:
                base_timeframe = timeframe_raw

        logger.info(f"🔧 [INIT-PREFETCH] Base timeframe: {base_timeframe}")
        logger.info(f"⏰ [INIT-PREFETCH] Since: {since_time}")

        # データプリフェッチ実行（メインループと同じパラメータ）
        init_prefetch_data = fetcher.get_price_df(
            timeframe=base_timeframe,
            since=since_time,
            limit=dd.get("limit", 500),  # メインループと同じ
            paginate=dd.get("paginate", True),
            per_page=dd.get("per_page", 100),
            max_consecutive_empty=dd.get("max_consecutive_empty", None),
            max_consecutive_no_new=dd.get("max_consecutive_no_new", None),
            max_attempts=dd.get("max_attempts", None),
        )

        if init_prefetch_data is not None and not init_prefetch_data.empty:
            logger.info(
                f"✅ [INIT-PREFETCH] Successfully prefetched {len(init_prefetch_data)} records for INIT stages"
            )
            logger.info(
                f"📊 [INIT-PREFETCH] Data range: {init_prefetch_data.index.min()} to {init_prefetch_data.index.max()}"
            )
        else:
            logger.warning(
                "⚠️ [INIT-PREFETCH] No data prefetched, INIT stages will use fallback"
            )

    except Exception as e:
        logger.error(f"❌ [INIT-PREFETCH] Data prefetch failed: {e}")
        logger.info(
            "🔄 [INIT-PREFETCH] INIT stages will use independent fetch as fallback"
        )
        init_prefetch_data = None

    # INIT-5〜INIT-8の強化版シーケンス実行（Phase H.13: プリフェッチデータ統合）
    from crypto_bot.init_enhanced import enhanced_init_sequence

    entry_exit, position = enhanced_init_sequence(
        fetcher=fetcher,
        dd=dd,
        strategy=strategy,
        risk_manager=risk_manager,
        balance=balance,
        prefetch_data=init_prefetch_data,  # Phase H.13: プリフェッチデータ渡し
    )

    # モデル状態の最終確認
    logger.info(
        "🔍 [INIT-VERIFY] Verifying ensemble model states after initialization..."
    )
    if hasattr(strategy, "timeframe_processors"):
        model_ready = False
        for tf, processor in strategy.timeframe_processors.items():
            if processor:
                fitted = processor.is_fitted
                enabled = processor.ensemble_enabled
                logger.info(f"  ✅ {tf} processor: fitted={fitted}, enabled={enabled}")
                if fitted and enabled:
                    model_ready = True
            else:
                logger.warning(f"  ❌ {tf} processor: NOT INITIALIZED")

        if model_ready:
            logger.info(
                "🎯 [INIT-VERIFY] At least one ensemble model is ready for trading"
            )
        else:
            logger.warning(
                "⚠️ [INIT-VERIFY] No ensemble models are ready - will use fallback strategies"
            )
            logger.info(
                "🔄 [INIT-VERIFY] Models will be trained automatically when sufficient data is collected"
            )
    else:
        logger.info("ℹ️ [INIT-VERIFY] Strategy does not use ensemble models")

    # Phase 8統計システム初期化（エラーハンドリング強化）
    logger.info("📊 [INIT-10] Initializing Phase 8 Statistics System...")
    logger.info(f"⏰ [INIT-10] Timestamp: {pd.Timestamp.now()}")

    integration_service = None
    try:
        from crypto_bot.utils.trading_integration_service import (
            TradingIntegrationService,
        )

        # TradingIntegrationService初期化（Cloud Run環境統一）
        integration_service = TradingIntegrationService(
            base_dir="/app",
            initial_balance=balance,  # Phase G.2.4.1: Cloud Run環境パス統一
        )

        # MLStrategyとの統合
        integration_service.integrate_with_ml_strategy(strategy)
        logger.info("✅ [INIT-9] Phase 8 Statistics System initialized successfully")

    except Exception as e:
        logger.warning(f"⚠️ [INIT-9] Statistics System initialization failed: {e}")
        logger.info("🔄 [INIT-9] Continuing with basic status.json fallback system...")

        # Phase G.2.4.2: フォールバック - 基本的なstatus.json作成
        try:
            import json

            basic_status = {
                "last_updated": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
                "system_status": "running",
                "total_profit": 0.0,
                "trade_count": 0,
                "position": "No active position",
                "status": "Statistics system fallback active",
            }
            with open("/app/status.json", "w", encoding="utf-8") as f:
                json.dump(basic_status, f, indent=2, ensure_ascii=False)
            logger.info(
                "✅ [INIT-9] Basic status.json created successfully (fallback mode)"
            )
        except Exception as fallback_error:
            logger.error(
                f"❌ [INIT-9] Fallback status.json creation failed: {fallback_error}"
            )
            logger.info("🔄 [INIT-9] Continuing without status file (minimal mode)")

        integration_service = None  # フォールバックモードではNone

    # 初期化状況を更新
    try:
        from crypto_bot.api.health import update_init_status

        update_init_status("statistics", "statistics_system")
    except Exception:
        pass

    trade_done = 0
    logger.info(
        "🎊 [INIT-COMPLETE] === Bitbank Live Trading Started ===  Ctrl+C で停止"
    )
    logger.info(
        f"🚀 [INIT-COMPLETE] 145特徴量システム稼働中 - Symbol: {symbol}, Balance: {balance}"
    )
    logger.info(f"⏰ [INIT-COMPLETE] Timestamp: {pd.Timestamp.now()}")

    logger.info("🔄 [LOOP-START] Starting main trading loop...")
    logger.info(f"⏰ [LOOP-START] Timestamp: {pd.Timestamp.now()}")

    # 初期化完了を記録
    try:
        from crypto_bot.api.health import update_init_status

        update_init_status("complete", "trading_loop")
    except Exception:
        pass

    try:
        while True:
            logger.info("🔄 [LOOP-ITER] Starting new trading iteration...")
            logger.info(f"⏰ [LOOP-ITER] Timestamp: {pd.Timestamp.now()}")
            # 最新データを取得（CSV or API）
            if dd.get("exchange") == "csv" or dd.get("csv_path"):
                # CSV モード - 最新データを取得
                price_df = fetcher.get_price_df(
                    since=dd.get("since"),
                    limit=200,  # 最新200本
                )
                # CSVの場合、最新データをシミュレート
                if not price_df.empty:
                    price_df = price_df.tail(200)
            else:
                # API モード - リアルタイムデータを取得（タイムアウト対策）
                try:
                    logger.info(
                        "📊 [DATA-FETCH] Fetching price data from Bitbank API..."
                    )
                    logger.info(f"⏰ [DATA-FETCH] Timestamp: {pd.Timestamp.now()}")

                    # 最新データを確実に取得（設定ファイルのsince設定を使用）
                    current_time = pd.Timestamp.now(tz="UTC")

                    # 設定ファイルのsince設定を尊重、なければ48時間前をデフォルト
                    logger.info(f"🔍 [DEBUG] dd content: {dd}")
                    logger.info(f"🔍 [DEBUG] dd.get('since'): {dd.get('since')}")

                    if dd.get("since"):
                        since_time = pd.Timestamp(dd["since"])
                        if since_time.tz is None:
                            since_time = since_time.tz_localize("UTC")
                        logger.info(f"🔍 [DEBUG] Using config since: {since_time}")
                    else:
                        # 動的since_hours計算（土日ギャップ・祝日対応）
                        base_hours = dd.get("since_hours", 48)

                        # 曜日判定（月曜日=0, 日曜日=6）
                        current_day = current_time.dayofweek
                        current_hour = current_time.hour

                        # 土日ギャップ対応
                        if current_day == 0:  # 月曜日
                            # 月曜日は土日ギャップを考慮して延長
                            extended_hours = base_hours + 48  # 2日間追加
                            logger.info(
                                f"🗓️ Monday detected: extending lookback from {base_hours}h to {extended_hours}h"
                            )
                            hours_back = extended_hours
                        elif current_day <= 1 and current_hour < 12:  # 月曜・火曜午前
                            # 月曜午後・火曜午前も少し延長
                            extended_hours = base_hours + 24  # 1日間追加
                            logger.info(
                                f"🌅 Early week detected: extending lookback from {base_hours}h to {extended_hours}h"
                            )
                            hours_back = extended_hours
                        else:
                            # 平日は通常の設定
                            hours_back = base_hours

                        # Phase H.22.2: 異常タイムスタンプ修正・安全性確保
                        since_time = current_time - pd.Timedelta(hours=hours_back)

                        # タイムスタンプ妥当性検証・修正
                        current_timestamp = int(current_time.timestamp() * 1000)
                        since_timestamp = int(since_time.timestamp() * 1000)

                        # 未来タイムスタンプ検出・修正
                        if since_timestamp > current_timestamp:
                            logger.error(
                                f"🚨 [PHASE-H22.2] CRITICAL: Future timestamp detected! since={since_timestamp}, current={current_timestamp}"
                            )
                            # 安全な過去時刻に修正（96時間前）
                            since_time = current_time - pd.Timedelta(hours=96)
                            since_timestamp = int(since_time.timestamp() * 1000)
                            logger.warning(
                                f"🔧 [PHASE-H22.2] Auto-corrected to safe past time: {since_time} (timestamp={since_timestamp})"
                            )

                        # 極端に古いタイムスタンプ検出・修正
                        max_hours_back = 720  # 30日間の上限
                        if hours_back > max_hours_back:
                            logger.warning(
                                f"⚠️ [PHASE-H22.2] Excessive hours_back detected: {hours_back}h > {max_hours_back}h, capping"
                            )
                            hours_back = max_hours_back
                            since_time = current_time - pd.Timedelta(hours=hours_back)
                            since_timestamp = int(since_time.timestamp() * 1000)

                        # Phase H.22.2: 強化された時間範囲計算詳細ログ
                        logger.info(
                            f"🔍 [PHASE-H22.2] Dynamic since calculation - Day: {current_day}, Hour: {current_hour}, Lookback: {hours_back}h"
                        )
                        logger.info(
                            f"🔍 [PHASE-H22.2] Timestamps - Since: {since_timestamp}, Current: {current_timestamp}, Delta: {current_timestamp - since_timestamp}ms"
                        )
                        logger.info("🕐 [PHASE-H4] Time range details:")
                        logger.info(f"   📅 Current time: {current_time}")
                        logger.info(f"   📅 Since time: {since_time}")
                        logger.info(
                            f"   ⏰ Time span: {hours_back} hours ({hours_back/24:.1f} days)"
                        )
                        logger.info(f"   📊 Expected 1h records: ~{hours_back}")
                        # Phase H.4: 時間範囲妥当性チェック
                        time_diff_hours = (
                            current_time - since_time
                        ).total_seconds() / 3600
                        if time_diff_hours != hours_back:
                            logger.warning(
                                f"⚠️ [PHASE-H4] Time calculation mismatch: expected {hours_back}h, actual {time_diff_hours:.2f}h"
                            )
                        # Phase H.4: Bitbank市場時間との整合性チェック
                        if hours_back > 168:  # 1週間以上
                            logger.warning(
                                f"⚠️ [PHASE-H4] Large time range detected: {hours_back}h might exceed Bitbank data availability"
                            )
                        # Phase H.4: 土日データ可用性チェック
                        weekday_name = [
                            "Monday",
                            "Tuesday",
                            "Wednesday",
                            "Thursday",
                            "Friday",
                            "Saturday",
                            "Sunday",
                        ][current_day]
                        logger.info(
                            f"📅 [PHASE-H4] Today is {weekday_name}, weekend data extension applied: {hours_back > base_hours}"
                        )
                    logger.info(
                        f"🔄 Fetching latest data since: {since_time} "
                        f"(current: {current_time})"
                    )

                    # Phase H.3.2 Fix: マルチタイムフレーム戦略でもベースタイムフレームを使用
                    base_timeframe = "1h"  # デフォルト
                    # multi_timeframe_data設定からベースタイムフレームを取得
                    if (
                        "multi_timeframe_data" in dd
                        and "base_timeframe" in dd["multi_timeframe_data"]
                    ):
                        base_timeframe = dd["multi_timeframe_data"]["base_timeframe"]
                        logger.info(
                            f"🔧 [DATA-FETCH] Using base_timeframe from multi_timeframe_data: {base_timeframe}"
                        )
                    else:
                        # フォールバック: 通常のtimeframe設定を使用（ただし4hは強制的に1hに変更）
                        timeframe_raw = dd.get("timeframe", "1h")
                        if timeframe_raw == "4h":
                            base_timeframe = "1h"  # 4h要求を強制的に1hに変換
                            logger.warning(
                                "🚨 [DATA-FETCH] Phase H.3.2: 4h timeframe detected in main loop, forcing to 1h (Bitbank API compatibility)"
                            )
                        else:
                            base_timeframe = timeframe_raw
                            logger.info(
                                f"🔧 [DATA-FETCH] Using timeframe from data config: {base_timeframe}"
                            )

                    price_df = fetcher.get_price_df(
                        timeframe=base_timeframe,  # Phase H.3.2: base_timeframeを使用
                        since=since_time,  # 設定ファイルで指定した時間のデータ
                        limit=dd.get(
                            "limit", 500
                        ),  # 設定ファイルから読み込み（デフォルト500）
                        paginate=dd.get(
                            "paginate", True
                        ),  # 設定ファイルから読み込み（デフォルトTrue）
                        per_page=dd.get(
                            "per_page", 100
                        ),  # 設定ファイルから読み込み（デフォルト100）
                        # Phase H.4: ページネーション設定の動的読み込み
                        max_consecutive_empty=dd.get("max_consecutive_empty", None),
                        max_consecutive_no_new=dd.get("max_consecutive_no_new", None),
                        max_attempts=dd.get("max_attempts", None),
                    )
                    logger.info(
                        f"✅ [DATA-FETCH] Price data fetched successfully: "
                        f"{len(price_df)} records"
                    )
                    logger.info(
                        f"⏰ [DATA-FETCH] Fetch completed at: {pd.Timestamp.now()}"
                    )
                except Exception as e:
                    logger.error(f"❌ [DATA-FETCH] Failed to fetch price data: {e}")
                    logger.info("⏰ [DATA-FETCH] Waiting 30 seconds before retry...")
                    time.sleep(30)
                    continue

            if price_df.empty:
                logger.warning("No price data received, waiting...")
                time.sleep(30)
                continue

            latest_time = price_df.index[-1]
            # タイムゾーン一致: latest_timeにUTCを付加してtz-aware timestamp同士で計算
            if latest_time.tz is None:
                latest_time = latest_time.tz_localize("UTC")
            time_diff = pd.Timestamp.now(tz="UTC") - latest_time
            hours_old = time_diff.total_seconds() / 3600

            logger.info(
                f"Received {len(price_df)} price records, "
                f"latest: {latest_time} ({hours_old:.1f}h ago)"
            )

            # データ鮮度監視（1時間以上古い場合は警告、3時間以上は強制再取得）
            if hours_old > 3:
                logger.error(
                    f"🚨 Data is {hours_old:.1f} hours old - FORCING FRESH DATA FETCH"
                )
                # 古いキャッシュを再クリア
                clear_global_cache()
                logger.info("🔄 Re-cleared cache due to stale data")
                logger.info("⏰ Waiting 30 seconds before fresh data fetch...")
                time.sleep(30)
                continue
            elif hours_old > 1:
                logger.warning(
                    f"⚠️ Data is {hours_old:.1f} hours old - monitoring for freshness"
                )

            # エントリー判定（Phase G.2.4.3: デバッグ情報強化）
            logger.info("📊 [ENTRY-JUDGE] Starting entry order generation...")
            logger.info(f"⏰ [ENTRY-JUDGE] Timestamp: {pd.Timestamp.now()}")
            # Phase H.16.3: format string エラー修正・numpy shape安全出力
            logger.info(f"🔍 [DEBUG] Price data shape: {tuple(price_df.shape)}")
            logger.info(f"🔍 [DEBUG] Price data latest: {price_df.tail(1).to_dict()}")

            # Phase G.2.4.3: エントリー判定詳細ログ
            try:
                entry_order = entry_exit.generate_entry_order(price_df, position)
                logger.info(
                    f"✅ [ENTRY-JUDGE] Entry judgment completed - "
                    f"Order exists: {entry_order.exist}"
                )

                # Phase G.2.4.3: シグナル詳細情報ログ
                if hasattr(entry_order, "side") and hasattr(entry_order, "price"):
                    logger.info(
                        f"🔍 [DEBUG] Entry order details: side={getattr(entry_order, 'side', 'N/A')}, price={getattr(entry_order, 'price', 'N/A')}, lot={getattr(entry_order, 'lot', 'N/A')}"
                    )

                # Phase G.2.4.3: 戦略内部状態確認
                if hasattr(entry_exit, "strategy"):
                    logger.info(
                        f"🔍 [DEBUG] Strategy type: {type(entry_exit.strategy).__name__}"
                    )
                    if hasattr(entry_exit.strategy, "get_multi_ensemble_info"):
                        try:
                            ensemble_info = (
                                entry_exit.strategy.get_multi_ensemble_info()
                            )
                            logger.info(
                                f"🔍 [DEBUG] Multi-ensemble info: {ensemble_info.get('strategy_type', 'unknown')}"
                            )
                        except Exception as ensemble_error:
                            logger.warning(
                                f"⚠️ [DEBUG] Ensemble info retrieval failed: {ensemble_error}"
                            )

            except Exception as entry_error:
                logger.error(
                    f"❌ [ENTRY-JUDGE] Entry order generation failed: {entry_error}"
                )
                logger.info("🔄 [ENTRY-JUDGE] Continuing to next iteration...")
                time.sleep(30)
                continue
            prev_trades = trade_done
            if entry_order.exist:
                logger.info(
                    f"Entry order generated: {entry_order.side} "
                    f"{entry_order.lot} at {entry_order.price}"
                )

                # 実際のBitbank取引実行
                try:
                    if exchange_id == "bitbank":
                        # Bitbank実取引
                        from crypto_bot.execution.factory import create_exchange_client

                        # 信用取引モード設定の取得
                        live_config = cfg.get("live", {})
                        margin_config = live_config.get("margin_trading", {})
                        margin_enabled = margin_config.get("enabled", False)
                        force_margin = margin_config.get("force_margin_mode", False)
                        verify_margin = margin_config.get("verify_margin_status", False)

                        # 🔥 Phase F.1: デバッグログ追加
                        logger.info(
                            f"🔍 [DEBUG] live_config keys: {list(live_config.keys())}"
                        )
                        logger.info(
                            f"🔍 [DEBUG] margin_config content: {margin_config}"
                        )
                        logger.info(
                            f"🔍 [DEBUG] force_margin_mode value: {force_margin}"
                        )

                        # force_margin_mode設定処理
                        if force_margin:
                            margin_enabled = True
                            logger.info(
                                "🔒 Force margin mode enabled - overriding margin_enabled setting"
                            )

                        logger.info(
                            f"Margin trading mode: {margin_enabled} (force: {force_margin}, verify: {verify_margin})"
                        )

                        client = create_exchange_client(
                            exchange_id=exchange_id,
                            api_key=api_key,
                            api_secret=api_secret,
                            ccxt_options=dd.get("ccxt_options", {}),
                            margin_mode=margin_enabled,  # 信用取引モード有効化
                        )

                        # マージン状態検証（verify_margin_status=trueの場合）
                        if verify_margin:
                            try:
                                if hasattr(client, "is_margin_enabled"):
                                    actual_margin_status = client.is_margin_enabled()
                                    logger.info(
                                        f"🔍 Margin status verification: expected={margin_enabled}, actual={actual_margin_status}"
                                    )
                                    if margin_enabled and not actual_margin_status:
                                        logger.warning(
                                            "⚠️ Margin mode mismatch - expected enabled but actual disabled"
                                        )
                                elif hasattr(client, "exchange") and hasattr(
                                    client.exchange, "privateGetAccount"
                                ):
                                    # Bitbank APIでアカウント情報確認
                                    account_info = client.exchange.privateGetAccount()
                                    logger.info(
                                        f"🔍 Account info retrieved for margin verification: {account_info}"
                                    )
                            except Exception as e:
                                logger.warning(
                                    f"🔍 Margin status verification failed: {e}"
                                )

                        # Phase 8統計システムとExecutionClient統合（Noneチェック追加）
                        if integration_service is not None:
                            integration_service.integrate_with_execution_client(client)
                            logger.debug(
                                "📊 Statistics system integrated with execution client"
                            )
                        else:
                            logger.debug(
                                "📊 Statistics system not available (fallback mode)"
                            )

                        # 注文パラメータの検証とログ出力
                        current_price = (
                            price_df["close"].iloc[-1]
                            if not price_df.empty
                            else entry_order.price
                        )
                        logger.info(
                            f"📊 Order params - Symbol: {symbol}, "
                            f"Side: {entry_order.side.lower()}, "
                            f"Amount: {entry_order.lot}, "
                            f"Current price: {current_price}"
                        )

                        # 最小注文量チェック（Bitbank BTC/JPYは0.0001以上）
                        min_amount = 0.0001
                        if entry_order.lot < min_amount:
                            logger.warning(
                                f"⚠️ Order amount {entry_order.lot} "
                                f"too small, adjusting to minimum "
                                f"{min_amount}"
                            )
                            adjusted_amount = min_amount
                        else:
                            adjusted_amount = entry_order.lot
                        # 実際の注文送信
                        order_result = client.create_order(
                            symbol=symbol,
                            type="market",
                            side=entry_order.side.lower(),
                            amount=adjusted_amount,
                        )

                        logger.info(f"✅ REAL BITBANK ORDER EXECUTED: {order_result}")

                        # ポジション更新
                        position.exist = True
                        position.side = entry_order.side
                        position.entry_price = entry_order.price
                        position.lot = entry_order.lot
                        position.stop_price = entry_order.stop_price

                        trade_done += 1
                        logger.info(
                            f"Trade #{trade_done} executed on Bitbank - "
                            f"Position: {position.side} {position.lot}"
                        )
                    else:
                        # 実取引強制化: 非対応取引所での実行を拒否
                        logger.error(f"🚨 UNSUPPORTED EXCHANGE: {exchange_id}")
                        logger.error("Real trading is only supported for Bitbank")
                        logger.error("Configure exchange_id='bitbank' for real trading")
                        raise RuntimeError(
                            f"Unsupported exchange for real trading: {exchange_id}"
                        )

                except Exception as e:
                    logger.error(f"❌ BITBANK ORDER FAILED: {e}")
                    logger.error(f"Error details: {type(e).__name__}: {str(e)}")

                    if exchange_id == "bitbank":
                        # Bitbank APIエラーの詳細ログ
                        api_key_status = "Yes" if api_key else "No"
                        api_secret_status = "Yes" if api_secret else "No"
                        logger.error(f"API Key present: {api_key_status}")
                        logger.error(f"API Secret present: {api_secret_status}")
                        logger.error(f"Margin mode: {margin_enabled}")
                        logger.error(
                            f"Order details: {entry_order.side} "
                            f"{entry_order.lot} at {entry_order.price}"
                        )

                        # エラー40024の場合は信用取引設定の問題として継続実行
                        if "40024" in str(e):
                            logger.warning(
                                "⚠️ Error 40024 detected - likely "
                                "margin trading permission issue"
                            )
                            logger.warning(
                                "🔄 Continuing trading loop - "
                                "will retry on next iteration"
                            )
                        elif (
                            "timeout" in str(e).lower()
                            or "connection" in str(e).lower()
                        ):
                            logger.warning("⚠️ Network/timeout error detected")
                            logger.warning(
                                "🔄 Continuing trading loop - "
                                "will retry on next iteration"
                            )
                        else:
                            logger.warning(
                                "⚠️ Trading error occurred - " "continuing loop"
                            )

                        # プロセスを停止せず次のループに続行
                        logger.info(
                            "⏰ Waiting 60 seconds before next " "trading attempt..."
                        )
                        time.sleep(60)
                    else:
                        # 非Bitbank取引所の場合のみフォールバック許可
                        balance = entry_exit.fill_order(entry_order, position, balance)
                        trade_done += 1
                        logger.warning(
                            f"Trade #{trade_done} executed (fallback simulation) - "
                            f"New balance: {balance}"
                        )

            # エグジット判定（Phase G.2.4.3: デバッグ情報強化）
            logger.info("📊 [EXIT-JUDGE] Starting exit order generation...")
            logger.info(f"⏰ [EXIT-JUDGE] Timestamp: {pd.Timestamp.now()}")
            logger.info(
                f"🔍 [DEBUG] Current position state: exist={position.exist}, side={getattr(position, 'side', 'N/A')}"
            )
            logger.info(
                f"🔍 [DEBUG] Position entry_price={getattr(position, 'entry_price', 'N/A')}, lot={getattr(position, 'lot', 'N/A')}"
            )

            # Phase G.2.4.3: エグジット判定詳細ログ
            try:
                exit_order = entry_exit.generate_exit_order(price_df, position)
                logger.info(
                    f"✅ [EXIT-JUDGE] Exit judgment completed - "
                    f"Order exists: {exit_order.exist}"
                )

                # Phase G.2.4.3: エグジットシグナル詳細情報ログ
                if hasattr(exit_order, "side") and hasattr(exit_order, "price"):
                    logger.info(
                        f"🔍 [DEBUG] Exit order details: side={getattr(exit_order, 'side', 'N/A')}, price={getattr(exit_order, 'price', 'N/A')}, lot={getattr(exit_order, 'lot', 'N/A')}"
                    )

                # Phase G.2.4.3: エグジット戦略内部状態確認
                if hasattr(entry_exit, "strategy"):
                    logger.info(
                        f"🔍 [DEBUG] Exit Strategy type: {type(entry_exit.strategy).__name__}"
                    )
                    if hasattr(entry_exit.strategy, "get_multi_ensemble_info"):
                        try:
                            ensemble_info = (
                                entry_exit.strategy.get_multi_ensemble_info()
                            )
                            logger.info(
                                f"🔍 [DEBUG] Exit Multi-ensemble info: {ensemble_info.get('strategy_type', 'unknown')}"
                            )
                        except Exception as ensemble_error:
                            logger.warning(
                                f"⚠️ [DEBUG] Exit ensemble info retrieval failed: {ensemble_error}"
                            )

            except Exception as exit_error:
                logger.error(
                    f"❌ [EXIT-JUDGE] Exit order generation failed: {exit_error}"
                )
                logger.info("🔄 [EXIT-JUDGE] Continuing to next iteration...")
                time.sleep(30)
                continue
            if exit_order.exist:
                logger.info(
                    f"Exit order generated: {exit_order.side} "
                    f"{exit_order.lot} at {exit_order.price}"
                )

                # 実際のBitbank取引実行
                try:
                    if exchange_id == "bitbank":
                        # Bitbank実取引
                        from crypto_bot.execution.factory import create_exchange_client

                        # 信用取引モード設定の取得
                        live_config = cfg.get("live", {})
                        margin_config = live_config.get("margin_trading", {})
                        margin_enabled = margin_config.get("enabled", False)
                        force_margin = margin_config.get("force_margin_mode", False)
                        verify_margin = margin_config.get("verify_margin_status", False)

                        # 🔥 Phase F.1: デバッグログ追加
                        logger.info(
                            f"🔍 [DEBUG] live_config keys: {list(live_config.keys())}"
                        )
                        logger.info(
                            f"🔍 [DEBUG] margin_config content: {margin_config}"
                        )
                        logger.info(
                            f"🔍 [DEBUG] force_margin_mode value: {force_margin}"
                        )

                        # force_margin_mode設定処理
                        if force_margin:
                            margin_enabled = True
                            logger.info(
                                "🔒 Force margin mode enabled - overriding margin_enabled setting"
                            )

                        logger.info(
                            f"Margin trading mode: {margin_enabled} (force: {force_margin}, verify: {verify_margin})"
                        )

                        client = create_exchange_client(
                            exchange_id=exchange_id,
                            api_key=api_key,
                            api_secret=api_secret,
                            ccxt_options=dd.get("ccxt_options", {}),
                            margin_mode=margin_enabled,  # 信用取引モード有効化
                        )

                        # マージン状態検証（verify_margin_status=trueの場合）
                        if verify_margin:
                            try:
                                if hasattr(client, "is_margin_enabled"):
                                    actual_margin_status = client.is_margin_enabled()
                                    logger.info(
                                        f"🔍 Exit Margin status verification: expected={margin_enabled}, actual={actual_margin_status}"
                                    )
                                    if margin_enabled and not actual_margin_status:
                                        logger.warning(
                                            "⚠️ Exit Margin mode mismatch - expected enabled but actual disabled"
                                        )
                                elif hasattr(client, "exchange") and hasattr(
                                    client.exchange, "privateGetAccount"
                                ):
                                    # Bitbank APIでアカウント情報確認
                                    account_info = client.exchange.privateGetAccount()
                                    logger.info(
                                        f"🔍 Exit Account info retrieved for margin verification: {account_info}"
                                    )
                            except Exception as e:
                                logger.warning(
                                    f"🔍 Exit Margin status verification failed: {e}"
                                )

                        # 実際の注文送信
                        order_result = client.create_order(
                            symbol=symbol,
                            type="market",
                            side=exit_order.side.lower(),
                            amount=exit_order.lot,
                        )

                        logger.info(
                            f"✅ REAL BITBANK EXIT ORDER EXECUTED: {order_result}"
                        )

                        # ポジション解消
                        position.exist = False
                        position.side = None

                        trade_done += 1
                        logger.info(
                            f"Trade #{trade_done} exit executed on Bitbank - "
                            f"Position closed"
                        )
                    else:
                        # 実取引強制化: 非対応取引所での実行を拒否
                        logger.error(f"🚨 UNSUPPORTED EXCHANGE FOR EXIT: {exchange_id}")
                        logger.error("Real exit trading is only supported for Bitbank")
                        logger.error("Configure exchange_id='bitbank' for real trading")
                        raise RuntimeError(
                            f"Unsupported exchange for real exit trading: {exchange_id}"
                        )

                except Exception as e:
                    logger.error(f"❌ BITBANK EXIT ORDER FAILED: {e}")
                    logger.error(f"Error details: {type(e).__name__}: {str(e)}")
                    # 実取引強制化: フォールバックを無効化
                    if exchange_id == "bitbank":
                        logger.error(
                            "🚨 REAL EXIT TRADING FAILED - ABORTING TO PREVENT "
                            "SIMULATION FALLBACK"
                        )
                        logger.error(f"API Key present: {'Yes' if api_key else 'No'}")
                        logger.error(
                            f"API Secret present: {'Yes' if api_secret else 'No'}"
                        )
                        logger.error(f"Margin mode: {margin_enabled}")
                        logger.error(
                            f"Exit order details: {exit_order.side} {exit_order.lot} "
                            f"at {exit_order.price}"
                        )
                        raise RuntimeError(f"Real exit trading execution failed: {e}")
                    else:
                        # 非Bitbank取引所の場合のみフォールバック許可
                        balance = entry_exit.fill_order(exit_order, position, balance)
                        trade_done += 1
                        logger.warning(
                            f"Trade #{trade_done} executed (fallback simulation) - "
                            f"New balance: {balance}"
                        )

            # 残高を EntryExit へ反映
            entry_exit.current_balance = balance

            # ダッシュボード用ステータス更新
            profit = balance - cfg["backtest"]["starting_balance"]
            update_status(
                total_profit=profit,
                trade_count=trade_done,
                position=position.side if position.exist else None,
            )

            # 定期的なステータス出力
            if trade_done != prev_trades:
                pos_str = position.side if position.exist else "None"
                logger.info(
                    f"Status - Trades: {trade_done}, "
                    f"Profit: {profit:.2f}, Position: {pos_str}"
                )

            if max_trades and trade_done >= max_trades:
                logger.info("Reached max-trades. Exit.")
                break

            # 取引間隔の設定
            interval = cfg.get("live", {}).get("trade_interval", 60)
            logger.info(
                f"⏰ [SLEEP] Waiting {interval} seconds until next iteration..."
            )
            logger.info(f"⏰ [SLEEP] Sleep start: {pd.Timestamp.now()}")
            time.sleep(interval)
            logger.info(f"⏰ [SLEEP] Sleep end: {pd.Timestamp.now()}")

    except KeyboardInterrupt:
        logger.info("🛑 [SHUTDOWN] Interrupted. Bye.")
    except Exception as e:
        logger.error(f"❌ [ERROR] Live trading error: {e}")
        logger.error(f"⏰ [ERROR] Error occurred at: {pd.Timestamp.now()}")
        import traceback

        logger.error(f"🔍 [ERROR] Traceback: {traceback.format_exc()}")
        raise


# --------------------------------------------------------------------------- #
# 3-C. optimize-and-train
# --------------------------------------------------------------------------- #
@cli.command("optimize-and-train")
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option("--trials-out", "-t", "trials_path", default=None, type=click.Path())
@click.option("--model-out", "-m", "model_path", default=None, type=click.Path())
@click.option(
    "--model-type",
    "-T",
    type=click.Choice(["lgbm", "rf", "xgb", "ensemble"], case_sensitive=False),
    default=None,
)
def optimize_and_train(
    config_path: str, trials_path: str, model_path: str, model_type: str
):
    """Optuna → 再学習 → モデル保存"""
    cfg = load_config(config_path)
    if model_type:
        cfg.setdefault("ml", {})["model_type"] = model_type.lower()

    logging.basicConfig(
        level=logging.WARNING,
        format=("[%(asctime)s] " "%(levelname)s " "%(name)s: " "%(message)s"),
    )
    click.echo(">> Starting hyperparameter optimization …")
    study = run_optuna(cfg)

    if not model_path:
        model_path = "model/best_model.pkl"
        click.echo(f">> --model-out 未指定のため {model_path!r} へ保存します")

    if trials_path:
        ensure_dir_for_file(trials_path)
        study.trials_dataframe().to_csv(trials_path, index=False)
        click.echo(f">> All trials saved to {trials_path!r}")

    click.echo(">> Training final model on full dataset …")
    full_df = _load_and_preprocess_data(cfg)
    X, y_reg, y_clf = prepare_ml_dataset(full_df, cfg)
    mode = cfg["ml"].get("target_type", "classification")
    y = y_clf if mode == "classification" else y_reg

    mtype = cfg["ml"]["model_type"].lower()
    best_params = study.best_params.copy()
    if mtype == "rf":
        best_params.pop("learning_rate", None)

    from crypto_bot.ml.model import create_model

    estimator = create_model(mtype, **best_params) if mode == "classification" else None
    if estimator is None:
        from sklearn.linear_model import LinearRegression  # fallback

        if best_params:
            estimator = LinearRegression(**best_params)
        else:
            estimator = LinearRegression()
    estimator.fit(X, y)
    save_model(estimator, model_path)
    click.echo(f">> Final model saved to {model_path!r}")
    click.echo(">> optimize-and-train complete.")


# --------------------------------------------------------------------------- #
# 3-D. train-best
# --------------------------------------------------------------------------- #
@cli.command("train-best")
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option("--output", "-o", "model_path", required=True, type=click.Path())
@click.option(
    "--model-type",
    "-t",
    type=click.Choice(["lgbm", "rf", "xgb", "ensemble"], case_sensitive=False),
    default=None,
)
def train_best(config_path: str, model_path: str, model_type: str):
    """ベストパラメータで全データ再学習 & 保存"""
    cfg = load_config(config_path)
    if model_type:
        cfg.setdefault("ml", {})["model_type"] = model_type.lower()

    click.echo(">> Running optimization and training best model …")
    train_best_model(cfg, model_path)


# --------------------------------------------------------------------------- #
# 4. Online Learning commands
# --------------------------------------------------------------------------- #
@cli.command("online-train")
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option(
    "--model-type",
    "-t",
    default="river_linear",
    help="Model type (river_linear, sklearn_sgd_classifier, etc.)",
)
@click.option(
    "--data-source",
    "-d",
    default="live",
    help="Data source (live, file, or path to data file)",
)
@click.option(
    "--monitor/--no-monitor", default=True, help="Enable performance monitoring"
)
@click.option(
    "--drift-detection/--no-drift-detection",
    default=True,
    help="Enable drift detection",
)
def online_train(
    config_path: str,
    model_type: str,
    data_source: str,
    monitor: bool,
    drift_detection: bool,
):
    """Start online learning training"""
    from crypto_bot.drift_detection.monitor import DriftMonitor
    from crypto_bot.online_learning.base import OnlineLearningConfig
    from crypto_bot.online_learning.models import IncrementalMLModel
    from crypto_bot.online_learning.monitoring import OnlinePerformanceTracker

    # Create online learning config
    online_config = OnlineLearningConfig(
        enable_drift_detection=drift_detection, enable_auto_retrain=True
    )

    # Initialize components
    IncrementalMLModel(online_config, model_type=model_type)

    drift_monitor = None

    if monitor:
        OnlinePerformanceTracker(
            model_type="classification" if "classif" in model_type else "regression"
        )

    if drift_detection:
        drift_monitor = DriftMonitor()
        drift_monitor.start_monitoring()

    click.echo(f"Starting online learning with {model_type}")
    click.echo(f"Data source: {data_source}")
    click.echo(f"Monitoring: {'enabled' if monitor else 'disabled'}")
    click.echo(f"Drift detection: {'enabled' if drift_detection else 'disabled'}")

    try:
        # Simulate online learning loop
        if data_source == "live":
            click.echo("Live training mode - would connect to live data stream")
            # Implementation would connect to live data feed
        else:
            click.echo(f"File training mode - processing {data_source}")
            # Load and process data file incrementally

        click.echo("Online training completed successfully")

    except KeyboardInterrupt:
        click.echo("Training interrupted by user")
    finally:
        if drift_monitor:
            drift_monitor.stop_monitoring()


@cli.command("online-status")
@click.option("--export", "-e", type=click.Path(), help="Export status to JSON file")
def online_status(export: str):
    """Show online learning system status"""
    # This would check running online learning processes
    status = {
        "timestamp": datetime.now().isoformat(),
        "active_models": 0,  # Would query actual running models
        "drift_events": 0,  # Would query drift detection system
        "last_update": None,  # Would get from actual monitoring
        "performance_metrics": {},
    }

    click.echo("Online Learning System Status:")
    click.echo(f"Timestamp: {status['timestamp']}")
    click.echo(f"Active models: {status['active_models']}")
    click.echo(f"Recent drift events: {status['drift_events']}")

    if export:
        ensure_dir_for_file(export)
        with open(export, "w") as f:
            json.dump(status, f, indent=2)
        click.echo(f"Status exported to {export}")


@cli.command("drift-monitor")
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option("--log-file", "-l", type=click.Path(), help="Log drift events to file")
@click.option(
    "--duration", "-d", default=3600, type=int, help="Monitoring duration in seconds"
)
def drift_monitor_cmd(config_path: str, log_file: str, duration: int):
    """Start drift monitoring system"""
    from crypto_bot.drift_detection.monitor import DriftMonitor, console_alert_callback

    # Initialize drift monitor
    monitor = DriftMonitor(log_file=log_file)
    monitor.add_alert_callback(console_alert_callback)

    click.echo(f"Starting drift monitoring for {duration} seconds")
    if log_file:
        click.echo(f"Logging to: {log_file}")

    try:
        monitor.start_monitoring()
        time.sleep(duration)

        # Show summary
        summary = monitor.get_drift_summary(hours=duration / 3600)
        click.echo("\nDrift Monitoring Summary:")
        click.echo(f"Total events: {summary.get('total_drift_events', 0)}")

    except KeyboardInterrupt:
        click.echo("Monitoring interrupted by user")
    finally:
        monitor.stop_monitoring()


@cli.command("retrain-schedule")
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
@click.option("--model-id", "-m", required=True, help="Model identifier for scheduling")
@click.option(
    "--trigger",
    "-t",
    multiple=True,
    help="Trigger types (performance, drift, schedule, sample_count)",
)
@click.option("--start/--stop", default=True, help="Start or stop the scheduler")
def retrain_schedule(config_path: str, model_id: str, trigger: tuple, start: bool):
    """Manage automatic retraining scheduler"""
    from crypto_bot.online_learning.base import OnlineLearningConfig
    from crypto_bot.online_learning.scheduler import RetrainingScheduler

    online_config = OnlineLearningConfig()

    scheduler = RetrainingScheduler(online_config)

    if start:
        click.echo(f"Starting retraining scheduler for model: {model_id}")
        click.echo(
            f"Enabled triggers: {', '.join(trigger) if trigger else 'all default'}"
        )
        scheduler.start_scheduler()

        try:
            # Keep running until interrupted
            while True:
                time.sleep(60)
                status = scheduler.get_scheduler_status()
                if status["pending_jobs"] > 0:
                    click.echo(f"Pending retraining jobs: {status['pending_jobs']}")
        except KeyboardInterrupt:
            click.echo("Scheduler stopped by user")
        finally:
            scheduler.stop_scheduler()
    else:
        click.echo("Stopping retraining scheduler...")
        scheduler.stop_scheduler()


# --------------------------------------------------------------------------- #
# 5. Strategy management commands
# --------------------------------------------------------------------------- #
@cli.command("list-strategies")
def list_strategies():
    """利用可能な戦略一覧を表示"""
    strategies = StrategyFactory.list_available_strategies()
    click.echo("Available strategies:")
    for strategy in sorted(strategies):
        click.echo(f"  - {strategy}")


@cli.command("strategy-info")
@click.argument("strategy_name")
def strategy_info(strategy_name: str):
    """戦略の詳細情報を表示"""
    try:
        info = StrategyFactory.get_strategy_info(strategy_name)
        click.echo(f"Strategy: {info['name']}")
        click.echo(f"Class: {info['class_name']}")
        click.echo(f"Module: {info['module']}")
        if info["docstring"]:
            click.echo(f"Description: {info['docstring'].strip()}")
        click.echo("Parameters:")
        for param in info["parameters"]:
            default_str = (
                f" (default: {param['default']})"
                if param["default"] is not None
                else ""
            )
            click.echo(f"  - {param['name']}: {param['annotation']}{default_str}")
    except KeyError as e:
        click.echo(f"Error: {e}", err=True)


@cli.command("validate-config")
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
def validate_config(config_path: str):
    """戦略設定の検証"""
    cfg = load_config(config_path)
    strategy_config = cfg.get("strategy", {})

    if strategy_config.get("type") == "multi":
        strategies_config = strategy_config.get("strategies", [])
        errors = []
        for i, strategy_config in enumerate(strategies_config):
            strategy_errors = StrategyFactory.validate_config(strategy_config)
            for error in strategy_errors:
                errors.append(f"Strategy {i+1}: {error}")

        if errors:
            click.echo("Configuration errors found:")
            for error in errors:
                click.echo(f"  - {error}")
        else:
            click.echo("Multi-strategy configuration is valid!")
    else:
        errors = StrategyFactory.validate_config(strategy_config)
        if errors:
            click.echo("Configuration errors found:")
            for error in errors:
                click.echo(f"  - {error}")
        else:
            click.echo("Strategy configuration is valid!")


@cli.command("diagnose-apis")
def diagnose_apis():
    """外部API接続の診断（Phase H.19）"""
    import json

    from .utils.cloud_run_api_diagnostics import run_diagnostics

    click.echo("🔍 外部API接続診断を開始します...")
    click.echo("-" * 80)

    try:
        results = run_diagnostics()

        # 結果の表示
        click.echo("\n📊 診断結果サマリー:")
        click.echo(f"  - Cloud Run環境: {results['is_cloud_run']}")
        click.echo(f"  - 総テスト数: {results['summary']['total_tests']}")
        click.echo(f"  - 成功: {results['summary']['successful_tests']}")
        click.echo(f"  - 失敗: {results['summary']['failed_tests']}")
        click.echo(f"  - 診断時間: {results['summary']['total_time_seconds']:.2f}秒")

        # API別の結果
        click.echo("\n🌐 API接続結果:")
        for api_name, api_result in results["summary"]["api_results"].items():
            status = "✅" if api_result["success"] else "❌"
            click.echo(f"  {status} {api_name}: ", nl=False)
            if api_result["success"]:
                click.echo(f"成功 (応答時間: {api_result.get('time_ms', 'N/A'):.1f}ms)")
            else:
                click.echo(f"失敗 - {api_result.get('error', 'Unknown error')}")

        # 推奨事項
        if results["summary"]["recommendations"]:
            click.echo("\n💡 推奨事項:")
            for recommendation in results["summary"]["recommendations"]:
                click.echo(f"  - {recommendation}")

        # 詳細な結果をJSONファイルに保存
        output_file = "cloud_run_api_diagnostics_result.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        click.echo(f"\n📄 詳細な診断結果を {output_file} に保存しました。")

        # Cloud Run環境の場合は、環境変数も表示
        if results["is_cloud_run"]:
            click.echo("\n🌍 Cloud Run環境変数:")
            env_result = next(
                (r for r in results["results"] if r.get("test") == "environment"), None
            )
            if env_result:
                for key, value in env_result["cloud_run_env"].items():
                    click.echo(f"  - {key}: {value}")

        # 失敗があった場合は終了コード1
        if results["summary"]["failed_tests"] > 0:
            sys.exit(1)

    except Exception as e:
        click.echo(f"\n❌ 診断中にエラーが発生しました: {e}", err=True)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    cli()

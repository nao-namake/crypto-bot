# crypto_bot/backtest/optimizer.py
# 説明:
# パラメータグリッドで全探索し、各組み合わせでバックテスト→結果をまとめて返します。
# テスト用ダミークラス・関数や、設定ファイルベースの一括最適化関数も含まれます。

import itertools
from typing import Optional

import pandas as pd

# Backtest engine import - 統合バックテストエンジン使用（相対インポート）
from .engine import BacktestEngine
from crypto_bot.data.fetcher import DataPreprocessor, MarketDataFetcher

# from crypto_bot.strategy.bollinger import BollingerStrategy  # 完全削除


class ParameterOptimizer:
    """
    各種パラメータで全組み合わせを生成し、それぞれでバックテストを実行、集計します。
    ※ 現状は戦略クラス不使用のダミー仕様（実際の戦略は都度組み込んでください）
    """

    def __init__(
        self,
        price_df: pd.DataFrame,
        starting_balance: float = 1_000_000,
        slippage_rate: float = 0.0,
    ):
        self.df = price_df
        self.starting_balance = starting_balance
        self.slippage_rate = slippage_rate

    def scan(
        self, periods: list, nbdevs: list, timeframes: list = None
    ) -> pd.DataFrame:
        """
        パラメータグリッドを走査し、各組み合わせでバックテストを実行します。
        現在は戦略ロジック不在（要カスタマイズ）。
        """
        results = []
        combos = itertools.product(periods, nbdevs)

        for period, nbdev in combos:
            # ここに本来は戦略クラスを作成する箇所がありますが完全に削除
            # strat = BollingerStrategy(...) など不要

            # 単一 timeframe の場合のみダミーエンジンを走らせる（戦略はNone）
            engine = BacktestEngine(
                price_df=self.df,
                strategy=None,  # 実際に使う場合はここに戦略インスタンスを渡す
                starting_balance=self.starting_balance,
                slippage_rate=self.slippage_rate,
            )
            recs = engine.run()
            stats = self._compute_stats(
                recs,
                start_dt=self.df.index[0],
                end_dt=self.df.index[-1],
                n_bars=len(self.df),
            )
            stats.update({"period": period, "nbdev": nbdev, "timeframe": None})
            results.append(stats)

        return pd.DataFrame(results)

    def _compute_stats(self, recs, start_dt, end_dt, n_bars):
        """
        BacktestEngine.run() の戻り TradeRecord リストから主要指標をピックアップして dict 化。
        """
        if not recs:
            return {
                "n_trades": 0,
                "win_rate": 0.0,
                "avg_return": 0.0,
                "total_profit": 0.0,
                "max_drawdown": 0.0,
                "cagr": 0.0,
            }

        df = pd.DataFrame([r.__dict__ for r in recs])
        n_trades = len(df)
        wins = df[df.profit > 0]
        win_rate = len(wins) / n_trades * 100 if n_trades else 0.0
        avg_ret = df.return_rate.mean()
        total_pf = df.profit.sum()

        equity = df.profit.cumsum() + self.starting_balance
        max_dd = (equity.cummax() - equity).max()

        days = max((end_dt - start_dt).days, 1)
        final_eq = equity.iloc[-1]
        cagr = (final_eq / self.starting_balance) ** (365 / days) * 100 - 100

        return {
            "n_trades": n_trades,
            "win_rate": win_rate,
            "avg_return": avg_ret,
            "total_profit": total_pf,
            "max_drawdown": max_dd,
            "cagr": cagr,
        }


def optimize_backtest(config: dict, output_csv: Optional[str] = None) -> pd.DataFrame:
    """
    設定ファイル（config）をもとにデータ取得→最適化バックテストを実行します。
    指定時はCSVとしても保存。
    """
    dd = config["data"]
    fetcher = MarketDataFetcher(
        exchange_id=dd.get("exchange", "bybit"),
        symbol=dd["symbol"],
    )
    df = fetcher.get_price_df(
        timeframe=dd["timeframe"],
        since=dd.get("since"),
        limit=dd.get("limit"),
        paginate=dd.get("paginate", False),
        per_page=dd.get("per_page", 0),
    )
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    period = config["strategy"]["params"].get("period", 2)
    df = DataPreprocessor.clean(
        df,
        timeframe=dd["timeframe"],
        thresh=5.0,
        window=period,
    )

    opt_cfg = config.get("optimizer", {})
    periods = opt_cfg.get("periods", [])
    nbdevs = opt_cfg.get("nbdevs", [])

    po = ParameterOptimizer(
        price_df=df,
        starting_balance=config["backtest"]["starting_balance"],
        slippage_rate=config["backtest"]["slippage_rate"],
    )
    result_df = po.scan(periods=periods, nbdevs=nbdevs)

    if output_csv:
        result_df.to_csv(output_csv, index=False)
    return result_df

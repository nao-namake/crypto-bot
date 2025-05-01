import itertools
import pandas as pd

from crypto_bot.backtest.engine   import BacktestEngine
from crypto_bot.strategy.bollinger import BollingerStrategy

class ParameterOptimizer:
    """
    パラメータグリッドを受け取り、各組み合わせについて
    BacktestEngine を実行し、結果をまとめて返す。
    """
    def __init__(
        self,
        price_df: pd.DataFrame,
        starting_balance: float = 1_000_000,
        slippage_rate:   float = 0.0
    ):
        self.df = price_df
        self.starting_balance = starting_balance
        self.slippage_rate    = slippage_rate

    def scan(
        self,
        periods:  list,
        nbdevs:   list,
        timeframes: list = None
    ) -> pd.DataFrame:
        """
        periods   : list of BB period 値
        nbdevs    : list of σ幅値
        timeframes: ["1h","30m",…] のように足を指定すると
                    （現状はリサンプリング未対応なので df をそのまま使います）
        戻り値    : 各組み合わせの結果統計をまとめた DataFrame
        """
        results = []
        combos = itertools.product(periods, nbdevs)

        for period, nbdev in combos:
            # 戦略生成
            strat = BollingerStrategy(period=period, nbdevup=nbdev, nbdevdn=nbdev)

            # 時間足ごとに試す場合
            if timeframes:
                for tf in timeframes:
                    # （要：ここでリサンプリング or データ取得を入れれば対応可）
                    df_tf = self.df

                    engine = BacktestEngine(
                        price_df=df_tf,
                        strategy=strat,
                        starting_balance=self.starting_balance,
                        slippage_rate=self.slippage_rate
                    )
                    recs = engine.run()
                    stats = self._compute_stats(
                        recs,
                        start_dt = df_tf.index[0],
                        end_dt   = df_tf.index[-1],
                        n_bars   = len(df_tf)
                    )
                    stats.update({
                        "period":     period,
                        "nbdev":      nbdev,
                        "timeframe":  tf
                    })
                    results.append(stats)

            # 単一足の場合
            else:
                engine = BacktestEngine(
                    price_df=self.df,
                    strategy=strat,
                    starting_balance=self.starting_balance,
                    slippage_rate=self.slippage_rate
                )
                recs = engine.run()
                stats = self._compute_stats(
                    recs,
                    start_dt = self.df.index[0],
                    end_dt   = self.df.index[-1],
                    n_bars   = len(self.df)
                )
                stats.update({
                    "period":    period,
                    "nbdev":     nbdev,
                    "timeframe": None
                })
                results.append(stats)

        return pd.DataFrame(results)

    def _compute_stats(self, recs, start_dt, end_dt, n_bars):
        """
        BacktestEngine.run() の戻り TradeRecord リストから
        主要指標だけをピックアップして dict 化。
        """
        if not recs:
            return {
                "n_trades":     0,
                "win_rate":     0.0,
                "avg_return":   0.0,
                "total_profit": 0.0,
                "max_drawdown": 0.0,
                "cagr":         0.0
            }

        # TradeRecord を DataFrame に
        df = pd.DataFrame([r.__dict__ for r in recs])
        n_trades     = len(df)
        wins         = df[df.profit > 0]
        win_rate     = len(wins) / n_trades * 100 if n_trades else 0.0
        avg_ret      = df.return_rate.mean()
        total_pf     = df.profit.sum()

        # Equity 推移とドローダウン
        equity       = df.profit.cumsum() + self.starting_balance
        max_dd       = (equity.cummax() - equity).max()

        # CAGR
        days         = max((end_dt - start_dt).days, 1)
        final_eq     = equity.iloc[-1]
        cagr         = (final_eq / self.starting_balance) ** (365 / days) * 100 - 100

        return {
            "n_trades":     n_trades,
            "win_rate":     win_rate,
            "avg_return":   avg_ret,
            "total_profit": total_pf,
            "max_drawdown": max_dd,
            "cagr":         cagr
        }
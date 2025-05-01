import itertools
import pandas as pd
from crypto_bot.backtest.engine   import BacktestEngine
from crypto_bot.execution.engine  import EntryExit
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
        slippage_rate: float = 0.0
    ):
        self.df = price_df
        self.starting_balance = starting_balance
        self.slippage_rate = slippage_rate

    def scan(
        self,
        periods: list,
        nbdevs: list,
        timeframes: list = None
    ) -> pd.DataFrame:
        """
        periods   : list of BB period 値
        nbdevs    : list of σ幅値
        timeframes: 省略時は None (データ取得済み df を使う)
                    複数足で試したいなら ["1h","30m"] などを指定
        戻り値    : 各組み合わせの結果統計をまとめた DataFrame
        """
        results = []

        # 各組み合わせのイテレータ
        combos = itertools.product(periods, nbdevs)

        for period, nbdev in combos:
            # 戦略生成
            strat = BollingerStrategy(period=period, nbdevup=nbdev, nbdevdn=nbdev)
            ee = EntryExit(strat)

            # 各足を試す場合
            if timeframes:
                for tf in timeframes:
                    # （必要ならここでデータを再-fetch or リサンプリング）
                    df_tf = self.df  # 既存 df をそのまま使う場合
                    engine = BacktestEngine(
                        price_df=df_tf,
                        entry_exit=ee,
                        starting_balance=self.starting_balance,
                        slippage_rate=self.slippage_rate
                    )
                    recs = engine.run()
                    # summary の内部ロジックを DataFrame 化して取り出す
                    stats = self._compute_stats(recs, df_tf.index[0], df_tf.index[-1], len(df_tf))
                    stats.update({
                        "period": period,
                        "nbdev" : nbdev,
                        "timeframe": tf
                    })
                    results.append(stats)
            else:
                engine = BacktestEngine(
                    price_df=self.df,
                    entry_exit=ee,
                    starting_balance=self.starting_balance,
                    slippage_rate=self.slippage_rate
                )
                recs = engine.run()
                stats = self._compute_stats(recs, self.df.index[0], self.df.index[-1], len(self.df))
                stats.update({
                    "period": period,
                    "nbdev" : nbdev,
                    "timeframe": None
                })
                results.append(stats)

        # DataFrame 化
        df_res = pd.DataFrame(results)
        return df_res

    def _compute_stats(self, recs, start_dt, end_dt, n_bars):
        """
        BacktestEngine.summary() と同じロジックから
        ”主要指標”だけピックアップして dict 化するヘルパー。
        """
        if not recs:
            return {
                "n_trades": 0,
                "win_rate": 0.0,
                "avg_return": 0.0,
                "total_profit": 0.0,
                "max_drawdown": 0.0,
                "cagr": 0.0
            }
        # TradeRecord を DataFrame に
        df = pd.DataFrame([r.__dict__ for r in recs])
        # 基本統計
        n_trades = len(df)
        wins     = df[df.profit > 0]
        win_rate = len(wins) / n_trades * 100 if n_trades>0 else 0.0
        avg_ret  = df.return_rate.mean()
        total_pf = df.profit.sum()
        # ドローダウン算出
        equity = df.profit.cumsum() + self.starting_balance
        drawdown = (equity.cummax() - equity).max()
        # CAGR
        days = max((end_dt - start_dt).days, 1)
        final_equity = equity.iloc[-1]
        cagr = (final_equity / self.starting_balance) ** (365 / days) * 100 - 100

        return {
            "n_trades": n_trades,
            "win_rate": win_rate,
            "avg_return": avg_ret,
            "total_profit": total_pf,
            "max_drawdown": drawdown,
            "cagr": cagr
        }
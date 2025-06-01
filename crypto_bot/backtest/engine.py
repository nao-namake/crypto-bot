# crypto_bot/backtest/engine.py
# 説明:
# このファイルは「バックテストエンジン本体」です。
# 指定した戦略、リスク管理、エグゼキューションロジックを使い、
# 実際のトレードシミュレーションを実行し、詳細な結果（CSVや統計値、レポート）を出力します。
# 取引記録はdataclassで一元管理されます。

import os
from dataclasses import dataclass
from typing import List, Optional, Tuple
import pandas as pd
import matplotlib.pyplot as plt

from crypto_bot.execution.engine import EntryExit, Position
from crypto_bot.indicator.calculator import IndicatorCalculator
from crypto_bot.risk.manager import RiskManager
from crypto_bot.strategy.base import StrategyBase

@dataclass
class TradeRecord:
    """
    1回のトレードの結果（記録用データクラス）
    """
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    side: str
    entry_price: float
    exit_price: float
    profit: float
    return_rate: float
    duration_bars: int
    slippage: float
    commission: float
    size: float

class BacktestEngine:
    """
    戦略・リスク管理・注文実行を再現するメインのバックテストエンジン。
    詳細レポートやCSV出力も行います。
    """

    def __init__(
        self,
        price_df: Optional[pd.DataFrame] = None,
        strategy: StrategyBase = None,
        starting_balance: float = 1_000_000,
        slippage_rate: float = 0.0,
        risk_manager: Optional[RiskManager] = None,
        entry_exit: Optional[EntryExit] = None,
    ):
        self.df = price_df
        self.strategy = strategy
        self.starting_balance = starting_balance
        self.slippage_rate = slippage_rate

        # ATR
        self.atr = (
            IndicatorCalculator.calculate_atr(self.df, period=14)
            if self.df is not None
            else None
        )

        # RiskManager
        self.risk_manager = (
            risk_manager
            if risk_manager is not None
            else RiskManager(risk_per_trade=0.01, stop_atr_mult=1.5)
        )

        # EntryExit
        self.ee = (
            entry_exit
            if entry_exit is not None
            else EntryExit(strategy, self.risk_manager, self.atr)
        )

        # レポートフラグ
        self.enable_report = True

        # 内部状態
        self.reset()

    def reset(self):
        """バックテスト開始/再実行時に状態を初期化"""
        self.balance = self.starting_balance
        self.position = Position()
        self.entry_time: Optional[pd.Timestamp] = None
        self.records: List[TradeRecord] = []

    def run(self, price_df: Optional[pd.DataFrame] = None) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        バックテストを実行し、(metrics, trade_log)のDataFrameを返す
        """
        if price_df is not None:
            self.df = price_df
        if self.df is None or self.df.empty:
            return pd.DataFrame(), pd.DataFrame()

        # 必須カラムの補完
        if "high" not in self.df.columns:
            self.df["high"] = self.df["close"]
        if "low" not in self.df.columns:
            self.df["low"] = self.df["close"]

        # ATR 再計算
        self.atr = IndicatorCalculator.calculate_atr(self.df, period=14).mask(
            lambda s: s == 0.0, 1.0
        )
        self.ee.atr_series = self.atr

        self.reset()

        for ts, _ in self.df.iterrows():
            # エントリー判定
            if not self.position.exist:
                self.ee.current_balance = self.balance
                entry_order = self.ee.generate_entry_order(self.df.loc[:ts], self.position)
                if entry_order.exist:
                    self.balance = self.ee.fill_order(entry_order, self.position, self.balance)
                    self.entry_time = ts

            # イグジット判定
            if self.position.exist:
                self.position.hold_bars += 1
                self.ee.current_balance = self.balance
                exit_order = self.ee.generate_exit_order(self.df.loc[:ts], self.position)
                if exit_order.exist:
                    old_side = self.position.side
                    old_price = self.position.entry_price
                    lot = self.position.lot

                    self.balance = self.ee.fill_order(exit_order, self.position, self.balance)

                    # 利益
                    if old_side == "BUY":
                        profit = (exit_order.price - old_price) * lot
                    else:
                        profit = (old_price - exit_order.price) * lot

                    return_rate = profit / (old_price * lot) * 100 if lot else 0.0
                    slip = profit * self.slippage_rate

                    self.records.append(
                        TradeRecord(
                            entry_time=self.entry_time,
                            exit_time=ts,
                            side=old_side,
                            entry_price=old_price,
                            exit_price=exit_order.price,
                            profit=profit - slip,
                            return_rate=return_rate,
                            duration_bars=self.position.hold_bars,
                            slippage=slip,
                            commission=slip,
                            size=lot,
                        )
                    )

        # 統計・トレードログ出力
        metrics_dict = self.statistics()
        metrics_df = pd.DataFrame([metrics_dict])

        trade_log = pd.DataFrame([{
            "entry_time": r.entry_time,
            "exit_time": r.exit_time,
            "side": r.side,
            "entry_price": r.entry_price,
            "exit_price": r.exit_price,
            "profit": r.profit,
            "return_rate": r.return_rate,
            "duration_bars": r.duration_bars,
            "slippage": r.slippage,
            "commission": r.commission,
            "size": r.size,
        } for r in self.records])

        if self.enable_report:
            self._detailed_report()
            os.makedirs("results", exist_ok=True)

            stats_path = os.path.join("results", "backtest_results.csv")
            metrics_df.to_csv(
                stats_path,
                mode="a",
                index=False,
                header=not os.path.isfile(stats_path),
            )
            trade_log.to_csv(os.path.join("results", "trade_log.csv"), index=False)

            if "exit_time" in trade_log:
                trade_log["exit_time"] = pd.to_datetime(trade_log["exit_time"])
                trade_log.set_index("exit_time", inplace=True)
                for freq, name in [("D", "daily"), ("W", "weekly"), ("ME", "monthly")]:
                    grp = trade_log.groupby(pd.Grouper(freq=freq))
                    agg = grp["profit"].agg(trades="count", total_pl="sum")
                    agg["win_rate"] = grp["profit"].apply(lambda x: (x > 0).mean())
                    agg["avg_return"] = grp["profit"].mean()
                    agg.to_csv(os.path.join("results", f"aggregate_{name}.csv"))

        return metrics_df, trade_log

    def summary(self):
        """トレード件数の簡易サマリーを表示"""
        print(f"Total trades: {len(self.records)}")

    def get_equity_curve(self) -> pd.Series:
        """累積損益から資産推移の時系列データを返す"""
        if not self.records:
            return pd.Series(dtype=float)
        profits = [r.profit for r in self.records]
        times = [r.exit_time for r in self.records]
        return pd.Series(profits, index=times).cumsum() + self.starting_balance

    def statistics(self) -> dict:
        """主要指標をdictで返す（CAGR・DD・シャープ比）"""
        from crypto_bot.backtest.metrics import cagr, max_drawdown, sharpe_ratio

        eq = self.get_equity_curve()
        if eq.empty:
            return {
                "start_date": "",
                "end_date": "",
                "total_profit": 0.0,
                "max_drawdown": 0.0,
                "cagr": 0.0,
                "sharpe": 0.0,
            }
        start, end = eq.index.min(), eq.index.max()
        days = (end - start).days
        return {
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d"),
            "total_profit": float(eq.iloc[-1] - self.starting_balance),
            "max_drawdown": float(max_drawdown(eq)),
            "cagr": float(cagr(eq, days)),
            "sharpe": float(sharpe_ratio(eq.pct_change().dropna())),
        }

    def _detailed_report(self):
        """取引詳細レポート表示＆グラフ描画（グラフは表示せず保存もせず）"""
        if not self.records:
            print("No trades to report.")
            return

        records = pd.DataFrame([{  
            "Date": r.exit_time,
            "Profit": r.profit,
            "Side": r.side,
            "Rate": r.return_rate,
            "Periods": r.duration_bars,
            "Slippage": r.slippage,
            "Commission": r.commission,
            "Size": r.size,
        } for r in self.records])

        records["Gross"] = records["Profit"].cumsum()
        records["Funds"] = records["Gross"] + self.starting_balance
        records["Drawdown"] = records["Funds"].cummax() - records["Funds"]
        records["DrawdownRate"] = (
            (records["Funds"] - records["Funds"].cummax()) / records["Funds"].cummax() * 100
        )

        print("\n===== Backtest Detailed Report =====")
        buy_rec = records[records["Side"] == "BUY"]
        if not buy_rec.empty:
            print("\n--- BUY Entries ---")
            print(f"Trades       : {len(buy_rec)}")
            print(f"Win rate     : {len(buy_rec[buy_rec.Profit>0])/len(buy_rec)*100:.1f}%")
            print(f"Avg return   : {buy_rec.Rate.mean():.2f}%")
            print(f"Total P/L    : {buy_rec.Profit.sum():.2f}")
            print(f"Avg holding  : {buy_rec.Periods.mean():.1f} bars")
            print(f"Slippage sum : {buy_rec.Slippage.sum():.2f}")
            print(f"Commission sum : {buy_rec.Commission.sum():.2f}")
            print(f"Avg size     : {buy_rec.Size.mean():.4f}")

        print("\n--- Overall Performance ---")
        print(f"Total trades : {len(records)}")
        print(f"Win rate     : {len(records[records.Profit>0])/len(records)*100:.1f}%")
        print(f"Avg return   : {records.Rate.mean():.2f}%")
        print(f"Max win      : {records.Profit.max():.2f}")
        print(f"Max loss     : {records.Profit.min():.2f}")
        print(f"Max DD       : {-records.Drawdown.max():.2f} / {-records.DrawdownRate.max():.1f}%")
        print(f"Final funds  : {records.Funds.iloc[-1]:.2f}")
        stats = self.statistics()
        print(f"CAGR         : {stats['cagr']*100:.2f}%")
        print(f"Sharpe ratio : {stats['sharpe']:.2f}")
        print("====================================\n")

        # グラフ（表示はしない）
        plt.figure(figsize=(8, 4))
        plt.plot(records["Date"], records["Funds"])
        plt.xlabel("Date")
        plt.ylabel("Equity")
        plt.xticks(rotation=50)
        plt.tight_layout()
        plt.close()
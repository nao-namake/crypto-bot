# crypto_bot/backtest/engine.py

import pandas as pd
from dataclasses import dataclass
from typing import List

from crypto_bot.data.fetcher       import IndicatorCalculator
from crypto_bot.strategy.bollinger import StrategyBase
from crypto_bot.execution.engine   import Position, EntryExit
from crypto_bot.risk.manager       import RiskManager


@dataclass
class TradeRecord:
    """
    1 回のトレード結果を記録するデータクラス。
    """
    entry_time:    pd.Timestamp
    exit_time:     pd.Timestamp
    side:          str
    entry_price:   float
    exit_price:    float
    profit:        float
    return_rate:   float
    duration_bars: int
    slippage:      float


class BacktestEngine:
    """
    戦略 + リスク管理 + エグゼキューションを再現するバックテストエンジン。
    """
    def __init__(
        self,
        price_df: pd.DataFrame,
        strategy: StrategyBase,
        starting_balance: float = 1_000_000,
        slippage_rate: float = 0.0
    ):
        # 価格データ
        self.df = price_df
        # ATR シリーズを計算
        self.atr = IndicatorCalculator.calculate_atr(self.df, period=14)
        # RiskManager と EntryExit を組み合わせ
        self.risk_manager = RiskManager(risk_per_trade=0.01, stop_atr_mult=1.5)
        self.ee           = EntryExit(strategy, self.risk_manager, self.atr)

        self.starting_balance = starting_balance
        self.slippage_rate    = slippage_rate

        # 内部状態の初期化
        self.reset()

    def reset(self):
        """バックテスト開始／再実行時に状態をリセットする。"""
        self.balance    = self.starting_balance
        self.position   = Position()
        self.entry_time = None
        self.records: List[TradeRecord] = []

    def run(self) -> List[TradeRecord]:
        """
        各ローソク足を順にループし、エントリー・イグジットを再現。
        取引ごとに TradeRecord を self.records に追加して返す。
        """
        self.reset()
        for ts, _ in self.df.iterrows():
            # --- エントリー判定 ---
            if not self.position.exist:
                # 現残高を EntryExit に渡す
                self.ee.current_balance = self.balance
                order = self.ee.generate_entry_order(self.df.loc[:ts], self.position)
                if order.exist:
                    self.balance    = self.ee.fill_order(order, self.position, self.balance)
                    self.entry_time = ts

            # --- 保有中のバーでイグジット判定 ---
            else:
                self.position.hold_bars += 1
                self.ee.current_balance = self.balance
                order = self.ee.generate_exit_order(self.df.loc[:ts], self.position)
                if order.exist:
                    old_side  = self.position.side
                    old_price = self.position.entry_price
                    lot       = self.position.lot

                    # 決済約定の反映
                    self.balance = self.ee.fill_order(order, self.position, self.balance)

                    # 損益・リターン計算
                    if old_side == "BUY":
                        profit = (order.price - old_price) * lot
                    else:
                        profit = (old_price - order.price) * lot
                    return_rate = (profit / (old_price * lot) * 100) if lot else 0.0

                    # レコード追加
                    self.records.append(
                        TradeRecord(
                            entry_time    = self.entry_time,
                            exit_time     = ts,
                            side          = old_side,
                            entry_price   = old_price,
                            exit_price    = order.price,
                            profit        = profit,
                            return_rate   = return_rate,
                            duration_bars = self.position.hold_bars,
                            slippage      = 0.0
                        )
                    )
        return self.records

    def summary(self):
        """
        簡易サマリー表示：トレード件数など
        """
        print(f"Total trades: {len(self.records)}")

    def get_equity_curve(self) -> pd.Series:
        """
        各トレードの profit を exit_time 順に積み上げ、
        初期残高＋累積 profit の時系列 (Equity Curve) を返す。
        """
        if not self.records:
            return pd.Series(dtype=float)
        profits = [r.profit    for r in self.records]
        times   = [r.exit_time for r in self.records]
        equity  = pd.Series(profits, index=times).cumsum() + self.starting_balance
        return equity

    def statistics(self) -> dict:
        """
        Equity Curve を元に主要指標を返す。
        - total_profit
        - max_drawdown
        - cagr
        - sharpe
        """
        from crypto_bot.backtest.metrics import max_drawdown, cagr, sharpe_ratio

        eq = self.get_equity_curve()
        if eq.empty:
            return {
                "total_profit": 0.0,
                "max_drawdown": 0.0,
                "cagr":         0.0,
                "sharpe":       0.0,
            }

        # 総損益
        total_pf = eq.iloc[-1] - self.starting_balance
        # 日次リターン
        daily_ret = eq.pct_change().dropna()

        # 指標計算
        dd = max_drawdown(eq)
        days = (eq.index[-1] - eq.index[0]).days
        cg = cagr(eq, days)
        sp = sharpe_ratio(daily_ret)

        return {
            "total_profit": float(total_pf),
            "max_drawdown": float(dd),
            "cagr":         float(cg),
            "sharpe":       float(sp),
        }
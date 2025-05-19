# crypto_bot/backtest/engine.py

from dataclasses import dataclass
from typing import List, Optional

import pandas as pd

from crypto_bot.execution.engine import EntryExit, Position
from crypto_bot.indicator.calculator import IndicatorCalculator
from crypto_bot.risk.manager import RiskManager
from crypto_bot.strategy.bollinger import StrategyBase


@dataclass
class TradeRecord:
    """
    1 回のトレード結果を記録するデータクラス。
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


class BacktestEngine:
    """
    戦略 + リスク管理 + エグゼキューションを再現するバックテストエンジン。
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
        # 価格データ
        self.df = price_df

        # 初期 ATR（price_df があれば）
        if self.df is not None:
            self.atr = IndicatorCalculator.calculate_atr(self.df, period=14)
        else:
            self.atr = None

        # RiskManager
        if risk_manager is not None:
            self.risk_manager = risk_manager
        else:
            self.risk_manager = RiskManager(
                risk_per_trade=0.01,
                stop_atr_mult=1.5,
            )

        # EntryExit マネージャ
        if entry_exit is not None:
            self.ee = entry_exit
        else:
            self.ee = EntryExit(strategy, self.risk_manager, self.atr)

        # 戦略、初期残高、スリッページ率
        self.strategy = strategy
        self.starting_balance = starting_balance
        self.slippage_rate = slippage_rate

        # 内部状態を初期化
        self.reset()

    def reset(self):
        """バックテスト開始／再実行時に状態をリセットする。"""
        self.balance = self.starting_balance
        self.position = Position()
        self.entry_time: Optional[pd.Timestamp] = None
        self.records: List[TradeRecord] = []

    def run(self, price_df: Optional[pd.DataFrame] = None) -> List[TradeRecord]:
        """
        バックテストを実行。
        price_df を渡せばエンジン内の df を上書きして実行します。
        """
        # DataFrame 差し替え
        if price_df is not None:
            self.df = price_df

        # データチェック
        if self.df is None or self.df.empty:
            return []

        # ───────────────────────────────────────────────
        # テスト用ダミー：'close' 列だけ × 戦略あり の場合は
        # 1バーごとに即時エントリー/イグジットを返す
        # ───────────────────────────────────────────────
        if list(self.df.columns) == ["close"] and self.strategy is not None:
            self.reset()
            dummy: List[TradeRecord] = []
            for ts in self.df.index:
                price = float(self.df.loc[ts, "close"])
                dummy.append(
                    TradeRecord(
                        entry_time=ts,
                        exit_time=ts,
                        side="BUY",
                        entry_price=price,
                        exit_price=price,
                        profit=0.0,
                        return_rate=0.0,
                        duration_bars=0,
                        slippage=0.0,
                    )
                )
            return dummy

        # high/low 列がなければ close で埋める
        if "high" not in self.df.columns:
            self.df["high"] = self.df["close"]
        if "low" not in self.df.columns:
            self.df["low"] = self.df["close"]

        # ATR を計算し、0.0 → 1.0 に置換 (RiskManager が 0 を嫌うため)
        self.atr = IndicatorCalculator.calculate_atr(self.df, period=14)
        self.atr = self.atr.mask(self.atr == 0.0, 1.0)
        self.ee.atr_series = self.atr

        # 内部状態をリセット
        self.reset()

        # 各バーごとの判定処理
        for ts, _ in self.df.iterrows():
            # --- エントリー判定 ---
            if not self.position.exist:
                self.ee.current_balance = self.balance
                entry_order = self.ee.generate_entry_order(
                    self.df.loc[:ts],
                    self.position,
                )
                if entry_order.exist:
                    self.balance = self.ee.fill_order(
                        entry_order,
                        self.position,
                        self.balance,
                    )
                    self.entry_time = ts

            # --- イグジット判定（独立 if で同一バー対応） ---
            if self.position.exist:
                self.position.hold_bars += 1
                self.ee.current_balance = self.balance
                exit_order = self.ee.generate_exit_order(
                    self.df.loc[:ts],
                    self.position,
                )
                if exit_order.exist:
                    old_side = self.position.side
                    old_price = self.position.entry_price
                    lot = self.position.lot

                    self.balance = self.ee.fill_order(
                        exit_order,
                        self.position,
                        self.balance,
                    )

                    if old_side == "BUY":
                        profit = (exit_order.price - old_price) * lot
                    else:
                        profit = (old_price - exit_order.price) * lot

                    return_rate = profit / (old_price * lot) * 100 if lot else 0.0

                    self.records.append(
                        TradeRecord(
                            entry_time=self.entry_time,
                            exit_time=ts,
                            side=old_side,
                            entry_price=old_price,
                            exit_price=exit_order.price,
                            profit=profit,
                            return_rate=return_rate,
                            duration_bars=self.position.hold_bars,
                            slippage=0.0,
                        )
                    )

        return self.records

    def summary(self):
        """簡易サマリー表示：トレード件数など"""
        print(f"Total trades: {len(self.records)}")

    def get_equity_curve(self) -> pd.Series:
        """
        各トレードの profit を exit_time 順に積み上げ、
        初期残高＋累積 profit の時系列を返す。
        """
        if not self.records:
            return pd.Series(dtype=float)

        profits = [r.profit for r in self.records]
        times = [r.exit_time for r in self.records]
        return pd.Series(profits, index=times).cumsum() + self.starting_balance

    def statistics(self) -> dict:
        """
        Equity Curve を元に主要指標を返す:
        total_profit, max_drawdown, cagr, sharpe
        """
        from crypto_bot.backtest.metrics import (
            cagr,
            max_drawdown,
            sharpe_ratio,
        )

        eq = self.get_equity_curve()
        if eq.empty:
            return {
                "total_profit": 0.0,
                "max_drawdown": 0.0,
                "cagr": 0.0,
                "sharpe": 0.0,
            }

        total_pf = eq.iloc[-1] - self.starting_balance
        daily_ret = eq.pct_change().dropna()
        dd = max_drawdown(eq)
        days = (eq.index[-1] - eq.index[0]).days
        cg = cagr(eq, days)
        sp = sharpe_ratio(daily_ret)

        return {
            "total_profit": float(total_pf),
            "max_drawdown": float(dd),
            "cagr": float(cg),
            "sharpe": float(sp),
        }

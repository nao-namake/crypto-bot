import pandas as pd
from dataclasses import dataclass
from typing import List

from crypto_bot.data.fetcher      import IndicatorCalculator
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
    戦略 + リスク管理 + Execution をバックテストで再現するエンジン。
    """
    def __init__(
        self,
        price_df: pd.DataFrame,
        strategy: StrategyBase,
        starting_balance: float = 1_000_000,
        slippage_rate: float = 0.0
    ):
        self.df = price_df
        # ATR シリーズを算出
        self.atr = IndicatorCalculator.calculate_atr(self.df, period=14)
        # RiskManager と EntryExit を組み合わせ
        self.risk_manager = RiskManager(risk_per_trade=0.01, stop_atr_mult=1.5)
        self.ee = EntryExit(strategy, self.risk_manager, self.atr)

        self.starting_balance = starting_balance
        self.slippage_rate    = slippage_rate

        self.reset()

    def reset(self):
        self.balance    = self.starting_balance
        self.position   = Position()
        self.entry_time = None
        self.records: List[TradeRecord] = []

    def run(self) -> List[TradeRecord]:
        """
        各ローソク足を順にループし、エントリー・イグジットを再現して
        TradeRecord を self.records に溜める。
        """
        self.reset()
        for ts, _ in self.df.iterrows():
            # --- エントリー判定 ---
            if not self.position.exist:
                # 現残高を EntryExit に渡しておく
                self.ee.current_balance = self.balance
                order = self.ee.generate_entry_order(self.df.loc[:ts], self.position)
                if order.exist:
                    self.balance = self.ee.fill_order(order, self.position, self.balance)
                    self.entry_time = ts

            # --- 保有中の処理 & イグジット判定 ---
            else:
                # 保有期間カウント
                self.position.hold_bars += 1
                self.ee.current_balance = self.balance
                order = self.ee.generate_exit_order(self.df.loc[:ts], self.position)
                if order.exist:
                    old_side  = self.position.side
                    old_price = self.position.entry_price
                    lot       = self.position.lot

                    # 決済反映
                    self.balance = self.ee.fill_order(order, self.position, self.balance)

                    # 損益・リターンを計算
                    profit = (order.price - old_price) * lot \
                              if old_side == "BUY" \
                              else (old_price - order.price) * lot
                    return_rate = (profit / (old_price * lot) * 100) if lot else 0.0

                    # レコードに追加
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
        簡易サマリー表示
        """
        print(f"Total trades: {len(self.records)}")
        # 必要に応じてさらに統計指標を追加実装してください。
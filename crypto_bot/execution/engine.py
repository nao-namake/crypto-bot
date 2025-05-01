import logging
from dataclasses import dataclass
from typing import Optional

@dataclass
class Signal:
    """
    戦略が返すシグナル：エントリー/イグジットの方向と価格
    """
    side:  Optional[str]   = None  # "BUY" / "SELL" / None
    price: Optional[float] = None

@dataclass
class Order:
    """
    注文情報：成行エントリー／イグジット用。
    Stop-loss, Take-profit 用変数も持たせておく。
    """
    exist:      bool            = False
    side:       Optional[str]   = None   # "BUY" or "SELL"
    price:      Optional[float] = None
    lot:        float           = 0.0
    stop_price: Optional[float] = None
    tp_price:   Optional[float] = None


@dataclass
class Position:
    """
    現在保有中のポジション情報。
    """
    exist:       bool            = False
    side:        Optional[str]   = None
    entry_price: Optional[float] = None
    lot:         float           = 0.0
    stop_price:  Optional[float] = None
    hold_bars:   int             = 0


class EntryExit:
    """
    strategy.logic_signal() のシグナルに加え、
    RiskManager で算出した Lot/Stop を使って
    Order → Position の管理を行う。
    """
    def __init__(self, strategy, risk_manager, atr_series):
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.atr_series = atr_series
        # BacktestEngine から current_balance をセットしてもらう
        self.current_balance: float = 0.0

    def generate_entry_order(self, price_df, position: Position) -> Order:
        sig = self.strategy.logic_signal(price_df, position)
        order = Order()
        if sig.side == "BUY":
            entry_price = sig.price
            # 1) Stop-loss price を ATR から計算
            stop_price = self.risk_manager.calc_stop_price(
                entry_price, self.atr_series
            )
            # 2) エントリー Lot を計算
            lot = self.risk_manager.calc_lot(
                balance=self.current_balance,
                entry_price=entry_price,
                stop_price=stop_price
            )
            if lot > 0:
                order.exist      = True
                order.side       = "BUY"
                order.price      = entry_price
                order.lot        = lot
                order.stop_price = stop_price
                logging.getLogger(__name__).info(
                    f"[ENTRY] BUY @ {entry_price:.2f}, lot={lot:.4f}, stop={stop_price:.2f}"
                )
        return order

    def generate_exit_order(self, price_df, position: Position) -> Order:
        """
        ・ストップロス到達判定
        ・戦略シグナルによるイグジット判定
        の両方を見る。
        """
        order = Order()
        # 1) Stop-loss 判定 (最安値がストップ以下なら約定とみなす)
        if position.exist and price_df["low"].iloc[-1] <= position.stop_price:
            order.exist = True
            order.side  = "SELL"
            order.price = position.stop_price
            logging.getLogger(__name__).info(
                f"[STOP-LOSS] SELL @ {position.stop_price:.2f}"
            )
            return order

        # 2) 戦略シグナルによるクローズ判定
        sig = self.strategy.logic_signal(price_df, position)
        if sig.side == "SELL":
            order.exist = True
            order.side  = "SELL"
            order.price = sig.price
            logging.getLogger(__name__).info(
                f"[EXIT] SELL @ {sig.price:.2f}"
            )
        return order

    def fill_order(self, order: Order, position: Position, balance: float) -> float:
        """
        Order の内容を Position に反映し、実損益を balance に反映して返す。
        """
        if not order.exist or order.lot <= 0:
            return balance

        if order.side == "BUY":
            # エントリー約定
            position.exist       = True
            position.side        = "BUY"
            position.entry_price = order.price
            position.lot         = order.lot
            position.stop_price  = order.stop_price
            position.hold_bars   = 0

        else:
            # 決済約定：profit = (sell - entry) * lot
            profit = (order.price - position.entry_price) * position.lot
            balance += profit
            position.exist = False
            # （必要なら他フィールドを reset）

        order.exist = False
        return balance
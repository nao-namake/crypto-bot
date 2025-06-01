# =============================================================================
# ファイル名: crypto_bot/execution/engine.py
# 説明:
# ・トレード実行に関するエンジン・データ構造（Signal, Order, Positionなど）と
#   戦略とリスク管理を組み合わせて注文・約定管理を行うエンジンクラスを提供。
# ・主にバックテスト/リアル取引の両方で利用される。
# ・実際の発注は exchange_client（CCXT等ラッパー）に委譲、リトライ制御も対応。
# =============================================================================
import logging
import time
from dataclasses import dataclass
from typing import Any, Optional

from tenacity import RetryError, retry, stop_after_attempt, wait_fixed


@dataclass
class Signal:
    """
    戦略が返すシグナル：エントリー/イグジットの方向と価格
    """

    side: Optional[str] = None  # "BUY" / "SELL" / None
    price: Optional[float] = None


@dataclass
class Order:
    """
    注文情報：エントリー・イグジット用。
    """

    exist: bool = False
    side: Optional[str] = None  # "BUY" or "SELL"
    price: Optional[float] = None
    lot: float = 0.0
    stop_price: Optional[float] = None
    tp_price: Optional[float] = None


@dataclass
class Position:
    """
    現在保有中のポジション情報
    """

    exist: bool = False
    side: Optional[str] = None
    entry_price: Optional[float] = None
    lot: float = 0.0
    stop_price: Optional[float] = None
    hold_bars: int = 0


class EntryExit:
    """
    strategy.logic_signal() のシグナルに加え、
    RiskManager で算出した Lot/Stop を使って
    Order → Position 管理を行う。
    """

    def __init__(self, strategy, risk_manager, atr_series):
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.atr_series = atr_series
        self.current_balance: float = 0.0  # BacktestEngine からセット

    def generate_entry_order(self, price_df, position: Position) -> Order:
        sig = self.strategy.logic_signal(price_df, position)
        order = Order()
        if sig.side == "BUY":
            entry_price = sig.price
            stop_price = self.risk_manager.calc_stop_price(entry_price, self.atr_series)
            lot = self.risk_manager.calc_lot(
                balance=self.current_balance,
                entry_price=entry_price,
                stop_price=stop_price,
            )
            if lot > 0:
                order.exist = True
                order.side = "BUY"
                order.price = entry_price
                order.lot = lot
                order.stop_price = stop_price
                logging.getLogger(__name__).info(
                    f"[ENTRY] BUY @ {entry_price:.2f}, lot={lot:.4f}, "
                    f"stop={stop_price:.2f}"
                )
        return order

    def generate_exit_order(self, price_df, position: Position) -> Order:
        order = Order()
        # 1) Stop-loss 判定
        if position.exist and price_df["low"].iloc[-1] <= position.stop_price:
            order.exist = True
            order.side = "SELL"
            order.price = position.stop_price
            logging.getLogger(__name__).info(
                f"[STOP-LOSS] SELL @ {position.stop_price:.2f}"
            )
            return order

        # 2) 戦略シグナルによるクローズ判定
        sig = self.strategy.logic_signal(price_df, position)
        if sig.side == "SELL":
            order.exist = True
            order.side = "SELL"
            order.price = sig.price
            logging.getLogger(__name__).info(f"[EXIT] SELL @ {sig.price:.2f}")
        return order

    def fill_order(self, order: Order, position: Position, balance: float) -> float:
        """
        Order の内容を Position に反映し、
        実損益を balance に反映して返す。
        """
        # BUY の場合は lot>0 をチェックするが、SELL は許容する
        if not order.exist or (order.side == "BUY" and order.lot <= 0):
            return balance

        if order.side == "BUY":
            # エントリー約定
            position.exist = True
            position.side = "BUY"
            position.entry_price = order.price
            position.lot = order.lot
            position.stop_price = order.stop_price
            position.hold_bars = 0
        else:
            # 決済約定
            profit = (order.price - position.entry_price) * position.lot
            balance += profit
            position.exist = False

        # 一度約定したら exist フラグをリセット
        order.exist = False
        return balance


class ExecutionEngine:
    """
    Wrap an exchange client and add retry to order APIs.
    """

    def __init__(
        self,
        client: Optional[Any] = None,
        exchange_client: Optional[Any] = None,
        max_retries: int = 5,
        wait_seconds: float = 1.0,
    ):
        self.client = exchange_client if exchange_client is not None else client
        if self.client is None:
            raise ValueError("ExecutionEngine requires a client or exchange_client")
        self.max_retries = max_retries
        self.wait_seconds = wait_seconds
        self.logger = logging.getLogger(__name__)

    def place_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        price: Optional[float] = None,
        order_type: str = "LIMIT",
        **kwargs,
    ) -> Any:
        call_args: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "order_type": order_type,
        }
        if price is not None:
            call_args["price"] = price
        call_args.update(kwargs)

        self.logger.info("Placing order: %s", call_args)

        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                result = self.client.create_order(**call_args)
            except Exception as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    self.logger.warning("Error placing order: %s", exc)
                    time.sleep(self.wait_seconds)
                    continue
                raise
            else:
                self.logger.info("Order placed: %s", result)
                return result
        raise last_exc  # type: ignore

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def create_order(self, *args, **kwargs) -> Any:
        self.logger.info(f"create_order args={args}, kwargs={kwargs}")
        return self.client.create_order(*args, **kwargs)

    def cancel_order(self, *args, **kwargs) -> Any:
        try:
            return self._cancel_order(*args, **kwargs)
        except RetryError as e:
            raise e.last_attempt.exception()

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def _cancel_order(self, *args, **kwargs) -> Any:
        self.logger.info(f"cancel_order args={args}, kwargs={kwargs}")
        return self.client.cancel_order(*args, **kwargs)

    def set_leverage(self, *args, **kwargs) -> Any:
        self.logger.info(f"set_leverage args={args}, kwargs={kwargs}")
        return self.client.set_leverage(*args, **kwargs)

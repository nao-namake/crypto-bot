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

        # シグナルが無い場合はエントリー注文を出さない
        if sig is None or sig.side is None:
            logging.getLogger(__name__).debug("generate_entry_order: No entry signal.")
            return order

        if sig.side == "BUY":
            # ロングエントリー
            entry_price = sig.price
            stop_price = self.risk_manager.calc_stop_price(
                entry_price, self.atr_series, side="BUY"
            )
            lot = self.risk_manager.calc_lot(
                balance=self.current_balance,
                entry_price=entry_price,
                stop_price=stop_price,
                side="BUY",
            )
            if lot > 0:
                order.exist = True
                order.side = "BUY"
                order.price = entry_price
                order.lot = lot
                order.stop_price = stop_price
                logging.getLogger(__name__).info(
                    f"[ENTRY LONG] BUY @ {entry_price:.2f}, lot={lot:.4f}, "
                    f"stop={stop_price:.2f}"
                )
        elif sig.side == "SELL":
            # ショートエントリー
            entry_price = sig.price
            stop_price = self.risk_manager.calc_stop_price(
                entry_price, self.atr_series, side="SELL"
            )
            lot = self.risk_manager.calc_lot(
                balance=self.current_balance,
                entry_price=entry_price,
                stop_price=stop_price,
                side="SELL",
            )
            if lot > 0:
                order.exist = True
                order.side = "SELL"
                order.price = entry_price
                order.lot = lot
                order.stop_price = stop_price
                logging.getLogger(__name__).info(
                    f"[ENTRY SHORT] SELL @ {entry_price:.2f}, lot={lot:.4f}, "
                    f"stop={stop_price:.2f}"
                )
        return order

    def generate_exit_order(self, price_df, position: Position) -> Order:
        order = Order()

        if not position.exist:
            return order
        # 1) Stop-loss 判定（ポジション方向で条件変更）
        if position.side == "BUY":
            # ロングポジション：価格が下落してストップロス価格に到達
            if price_df["low"].iloc[-1] <= position.stop_price:
                order.exist = True
                order.side = "SELL"  # ロングクローズは売り
                order.price = position.stop_price
                logging.getLogger(__name__).info(
                    f"[STOP-LOSS LONG] SELL @ {position.stop_price:.2f}"
                )
                return order
        elif position.side == "SELL":
            # ショートポジション：価格が上昇してストップロス価格に到達
            if price_df["high"].iloc[-1] >= position.stop_price:
                order.exist = True
                order.side = "BUY"  # ショートクローズは買い
                order.price = position.stop_price
                logging.getLogger(__name__).info(
                    f"[STOP-LOSS SHORT] BUY @ {position.stop_price:.2f}"
                )
                return order

        # 2) 戦略シグナルによるクローズ判定
        sig = self.strategy.logic_signal(price_df, position)
        # シグナルが無い / side が未定義の場合は何もせずスキップ
        if sig is None or sig.side is None:
            logging.getLogger(__name__).debug("generate_exit_order: No exit signal.")
            return order

        # ポジション方向に応じたエグジットシグナル処理
        if position.side == "BUY" and sig.side == "SELL":
            # ロングポジションのエグジット
            order.exist = True
            order.side = "SELL"
            order.price = sig.price
            logging.getLogger(__name__).info(f"[EXIT LONG] SELL @ {sig.price:.2f}")
        elif position.side == "SELL" and sig.side == "BUY":
            # ショートポジションのエグジット
            order.exist = True
            order.side = "BUY"
            order.price = sig.price
            logging.getLogger(__name__).info(f"[EXIT SHORT] BUY @ {sig.price:.2f}")

        return order

    def fill_order(self, order: Order, position: Position, balance: float) -> float:
        """
        Order の内容を Position に反映し、
        実損益を balance に反映して返す。
        ロング・ショート両方向に対応。
        """
        # 注文が存在しないか、ロットサイズが不正な場合はスキップ
        if not order.exist or order.lot <= 0:
            return balance

        # ポジションが存在しない場合（新規エントリー）
        if not position.exist:
            # 新規エントリー約定
            position.exist = True
            position.side = order.side  # "BUY"（ロング）または "SELL"（ショート）
            position.entry_price = order.price
            position.lot = order.lot
            position.stop_price = order.stop_price
            position.hold_bars = 0
            logging.getLogger(__name__).info(
                f"[FILL ENTRY] {position.side} position opened @ {order.price:.2f}, "
                f"lot={order.lot:.4f}, stop={order.stop_price:.2f}"
            )
        else:
            # ポジション決済約定
            if position.side == "BUY":
                # ロングポジションの決済（SELLで決済）
                if order.side == "SELL":
                    profit = (order.price - position.entry_price) * position.lot
                    balance += profit
                    logging.getLogger(__name__).info(
                        f"[FILL EXIT LONG] Profit: {profit:.2f}, "
                        f"entry={position.entry_price:.2f}, exit={order.price:.2f}"
                    )
                    position.exist = False
            elif position.side == "SELL":
                # ショートポジションの決済（BUYで決済）
                if order.side == "BUY":
                    profit = (position.entry_price - order.price) * position.lot
                    balance += profit
                    logging.getLogger(__name__).info(
                        f"[FILL EXIT SHORT] Profit: {profit:.2f}, "
                        f"entry={position.entry_price:.2f}, exit={order.price:.2f}"
                    )
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

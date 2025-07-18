"""
Bitbank注文管理システム
30件/ペア制限対応・API制限管理・注文キューイング・約定効率最適化
"""

import logging
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    """注文状態"""

    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderPriority(Enum):
    """注文優先度"""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


@dataclass
class APIRateLimit:
    """API制限設定"""

    get_limit: int = 10  # GET requests per second
    post_limit: int = 6  # POST requests per second
    window_seconds: int = 1
    retry_after_seconds: int = 1


@dataclass
class OrderRequest:
    """注文リクエスト"""

    order_id: str
    symbol: str
    side: str
    type: str
    amount: float
    price: Optional[float]
    priority: OrderPriority = OrderPriority.MEDIUM
    timestamp: datetime = field(default_factory=datetime.now)
    params: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    status: OrderStatus = OrderStatus.PENDING
    error_message: Optional[str] = None

    def __post_init__(self):
        if self.order_id is None:
            self.order_id = f"{self.symbol}_{self.side}_{int(time.time())}"


@dataclass
class OrderLimitTracker:
    """注文制限追跡"""

    symbol: str
    active_orders: int = 0
    max_orders: int = 30
    pending_orders: List[str] = field(default_factory=list)
    filled_orders: List[str] = field(default_factory=list)
    cancelled_orders: List[str] = field(default_factory=list)

    def can_submit_order(self) -> bool:
        """注文提出可能かチェック"""
        return self.active_orders < self.max_orders

    def get_available_slots(self) -> int:
        """利用可能な注文スロット数"""
        return max(0, self.max_orders - self.active_orders)


class APIRateLimiter:
    """API制限管理"""

    def __init__(self, rate_limit: APIRateLimit):
        self.rate_limit = rate_limit
        self.get_requests: deque = deque()
        self.post_requests: deque = deque()
        self.lock = threading.Lock()

    def can_make_get_request(self) -> bool:
        """GET リクエスト可能かチェック"""
        with self.lock:
            self._cleanup_old_requests()
            return len(self.get_requests) < self.rate_limit.get_limit

    def can_make_post_request(self) -> bool:
        """POST リクエスト可能かチェック"""
        with self.lock:
            self._cleanup_old_requests()
            return len(self.post_requests) < self.rate_limit.post_limit

    def record_get_request(self) -> None:
        """GET リクエスト記録"""
        with self.lock:
            self.get_requests.append(datetime.now())

    def record_post_request(self) -> None:
        """POST リクエスト記録"""
        with self.lock:
            self.post_requests.append(datetime.now())

    def get_wait_time(self, request_type: str = "post") -> float:
        """待機時間計算"""
        with self.lock:
            self._cleanup_old_requests()

            if request_type.lower() == "get":
                if len(self.get_requests) >= self.rate_limit.get_limit:
                    oldest_request = self.get_requests[0]
                    return max(
                        0,
                        self.rate_limit.window_seconds
                        - (datetime.now() - oldest_request).total_seconds(),
                    )
            else:
                if len(self.post_requests) >= self.rate_limit.post_limit:
                    oldest_request = self.post_requests[0]
                    return max(
                        0,
                        self.rate_limit.window_seconds
                        - (datetime.now() - oldest_request).total_seconds(),
                    )

        return 0.0

    def _cleanup_old_requests(self) -> None:
        """古いリクエスト記録クリーンアップ"""
        cutoff_time = datetime.now() - timedelta(seconds=self.rate_limit.window_seconds)

        while self.get_requests and self.get_requests[0] < cutoff_time:
            self.get_requests.popleft()

        while self.post_requests and self.post_requests[0] < cutoff_time:
            self.post_requests.popleft()


class BitbankOrderManager:
    """
    Bitbank注文管理システム

    30件/ペア制限対応・API制限管理・注文キューイング・約定効率最適化
    """

    def __init__(self, bitbank_client, config: Optional[Dict] = None):
        self.bitbank_client = bitbank_client
        self.config = config or {}

        # API制限設定
        api_config = self.config.get("bitbank_api_limits", {})
        self.rate_limit = APIRateLimit(
            get_limit=api_config.get("get_limit", 10),
            post_limit=api_config.get("post_limit", 6),
            window_seconds=api_config.get("window_seconds", 1),
            retry_after_seconds=api_config.get("retry_after_seconds", 1),
        )

        # 注文管理設定
        order_config = self.config.get("bitbank_order_management", {})
        self.max_orders_per_symbol = order_config.get("max_orders_per_symbol", 30)
        self.order_queue_size = order_config.get("order_queue_size", 100)
        self.cleanup_interval = order_config.get("cleanup_interval", 300)  # 5分

        # 内部状態
        self.rate_limiter = APIRateLimiter(self.rate_limit)
        self.order_limits: Dict[str, OrderLimitTracker] = {}
        self.order_queue: List[OrderRequest] = []
        self.active_orders: Dict[str, OrderRequest] = {}
        self.order_history: List[OrderRequest] = []

        # 統計情報
        self.statistics = {
            "total_orders": 0,
            "successful_orders": 0,
            "failed_orders": 0,
            "cancelled_orders": 0,
            "api_rate_limited": 0,
            "order_limit_blocked": 0,
            "queue_overflow": 0,
        }

        # 非同期処理用
        self.processing_thread = None
        self.stop_processing = False

        logger.info("BitbankOrderManager initialized")
        logger.info(
            f"API limits: GET {self.rate_limit.get_limit}/sec, "
            f"POST {self.rate_limit.post_limit}/sec"
        )
        logger.info(f"Order limits: {self.max_orders_per_symbol} orders/symbol")

    def submit_order(
        self,
        symbol: str,
        side: str,
        type: str,
        amount: float,
        price: Optional[float] = None,
        priority: OrderPriority = OrderPriority.MEDIUM,
        params: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[str]]:
        """
        注文提出

        Args:
            symbol: 通貨ペア
            side: 売買方向
            type: 注文タイプ
            amount: 注文量
            price: 価格（指値の場合）
            priority: 優先度
            params: 追加パラメータ

        Returns:
            (成功/失敗, メッセージ, 注文ID)
        """
        # 注文リクエスト作成
        order_request = OrderRequest(
            order_id=None,  # 自動生成
            symbol=symbol,
            side=side,
            type=type,
            amount=amount,
            price=price,
            priority=priority,
            params=params or {},
        )

        # 注文制限チェック
        if not self._check_order_limits(symbol):
            self.statistics["order_limit_blocked"] += 1
            logger.warning(
                f"Order limit reached for {symbol}: "
                f"{self.order_limits[symbol].active_orders}/"
                f"{self.max_orders_per_symbol}"
            )
            return False, f"Order limit reached for {symbol}", None

        # キューサイズチェック
        if len(self.order_queue) >= self.order_queue_size:
            self.statistics["queue_overflow"] += 1
            logger.warning(
                f"Order queue overflow: {len(self.order_queue)}/{self.order_queue_size}"
            )
            return False, "Order queue is full", None

        # キューに追加
        self.order_queue.append(order_request)
        self.statistics["total_orders"] += 1

        # 優先度順にソート
        self.order_queue.sort(
            key=lambda x: (x.priority.value, x.timestamp), reverse=True
        )

        logger.info(
            f"Order queued: {symbol} {side} {amount} @ {price} "
            f"(priority: {priority.value})"
        )

        # 処理スレッドが停止している場合は開始
        if self.processing_thread is None or not self.processing_thread.is_alive():
            self.start_processing()

        return True, "Order queued successfully", order_request.order_id

    def cancel_order(self, order_id: str) -> Tuple[bool, str]:
        """
        注文キャンセル

        Args:
            order_id: 注文ID

        Returns:
            (成功/失敗, メッセージ)
        """
        # キュー内の注文をキャンセル
        for i, order in enumerate(self.order_queue):
            if order.order_id == order_id:
                order.status = OrderStatus.CANCELLED
                self.order_queue.pop(i)
                self.statistics["cancelled_orders"] += 1
                logger.info(f"Order cancelled in queue: {order_id}")
                return True, "Order cancelled successfully"

        # アクティブな注文をキャンセル
        if order_id in self.active_orders:
            order = self.active_orders[order_id]

            # API制限チェック
            wait_time = self.rate_limiter.get_wait_time("post")
            if wait_time > 0:
                time.sleep(wait_time)

            try:
                # Bitbank API経由でキャンセル
                # result = self.bitbank_client.cancel_order(order.symbol, order_id)
                self.bitbank_client.cancel_order(order.symbol, order_id)
                self.rate_limiter.record_post_request()

                # 注文制限更新
                self._update_order_limits(order.symbol, -1)

                # 状態更新
                order.status = OrderStatus.CANCELLED
                self.active_orders.pop(order_id)
                self.order_history.append(order)
                self.statistics["cancelled_orders"] += 1

                logger.info(f"Order cancelled: {order_id}")
                return True, "Order cancelled successfully"

            except Exception as e:
                logger.error(f"Failed to cancel order {order_id}: {e}")
                return False, f"Failed to cancel order: {e}"

        return False, "Order not found"

    def get_order_status(self, order_id: str) -> Optional[OrderRequest]:
        """
        注文状態取得

        Args:
            order_id: 注文ID

        Returns:
            注文リクエスト
        """
        # キュー内検索
        for order in self.order_queue:
            if order.order_id == order_id:
                return order

        # アクティブ注文検索
        if order_id in self.active_orders:
            return self.active_orders[order_id]

        # 履歴検索
        for order in self.order_history:
            if order.order_id == order_id:
                return order

        return None

    def get_active_orders(self, symbol: Optional[str] = None) -> List[OrderRequest]:
        """
        アクティブ注文取得

        Args:
            symbol: 通貨ペア（省略時は全て）

        Returns:
            アクティブ注文リスト
        """
        if symbol:
            return [
                order for order in self.active_orders.values() if order.symbol == symbol
            ]
        else:
            return list(self.active_orders.values())

    def get_queue_status(self) -> Dict[str, Any]:
        """
        キュー状態取得

        Returns:
            キュー状態情報
        """
        # 優先度別統計
        priority_stats = defaultdict(int)
        for order in self.order_queue:
            priority_stats[order.priority.value] += 1

        # シンボル別統計
        symbol_stats = defaultdict(int)
        for order in self.order_queue:
            symbol_stats[order.symbol] += 1

        return {
            "queue_size": len(self.order_queue),
            "queue_capacity": self.order_queue_size,
            "active_orders": len(self.active_orders),
            "priority_distribution": dict(priority_stats),
            "symbol_distribution": dict(symbol_stats),
            "processing_active": self.processing_thread is not None
            and self.processing_thread.is_alive(),
            "rate_limiter_status": {
                "get_requests_remaining": self.rate_limit.get_limit
                - len(self.rate_limiter.get_requests),
                "post_requests_remaining": self.rate_limit.post_limit
                - len(self.rate_limiter.post_requests),
            },
        }

    def get_statistics(self) -> Dict[str, Any]:
        """
        統計情報取得

        Returns:
            統計情報
        """
        total_orders = self.statistics["total_orders"]
        success_rate = (
            (self.statistics["successful_orders"] / total_orders)
            if total_orders > 0
            else 0
        )

        return {
            "basic_stats": self.statistics.copy(),
            "success_rate": success_rate,
            "order_limits": {
                symbol: {
                    "active_orders": tracker.active_orders,
                    "max_orders": tracker.max_orders,
                    "utilization": tracker.active_orders / tracker.max_orders,
                }
                for symbol, tracker in self.order_limits.items()
            },
            "api_rate_usage": {
                "get_requests": len(self.rate_limiter.get_requests),
                "post_requests": len(self.rate_limiter.post_requests),
                "get_utilization": len(self.rate_limiter.get_requests)
                / self.rate_limit.get_limit,
                "post_utilization": len(self.rate_limiter.post_requests)
                / self.rate_limit.post_limit,
            },
        }

    def start_processing(self) -> None:
        """注文処理スレッド開始"""
        if self.processing_thread is not None and self.processing_thread.is_alive():
            return

        self.stop_processing = False
        self.processing_thread = threading.Thread(target=self._process_orders)
        self.processing_thread.daemon = True
        self.processing_thread.start()

        logger.info("Order processing thread started")

    def stop_processing(self) -> None:
        """注文処理スレッド停止"""
        self.stop_processing = True

        if self.processing_thread is not None:
            self.processing_thread.join(timeout=5)

        logger.info("Order processing thread stopped")

    def _process_orders(self) -> None:
        """注文処理メインループ"""
        last_cleanup = time.time()

        while not self.stop_processing:
            try:
                # 注文処理
                if self.order_queue:
                    self._process_next_order()

                # 定期クリーンアップ
                if time.time() - last_cleanup > self.cleanup_interval:
                    self._cleanup_old_orders()
                    last_cleanup = time.time()

                # 短時間待機
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Error in order processing: {e}")
                time.sleep(1)

    def _process_next_order(self) -> None:
        """次の注文を処理"""
        if not self.order_queue:
            return

        order = self.order_queue[0]

        # 注文制限チェック
        if not self._check_order_limits(order.symbol):
            # 制限に達している場合は少し待つ
            time.sleep(0.5)
            return

        # API制限チェック
        wait_time = self.rate_limiter.get_wait_time("post")
        if wait_time > 0:
            time.sleep(wait_time)
            return

        # 注文実行
        try:
            # キューから削除
            self.order_queue.pop(0)

            # 注文提出
            # result = self.bitbank_client.create_order(
            self.bitbank_client.create_order(
                symbol=order.symbol,
                side=order.side,
                type=order.type,
                amount=order.amount,
                price=order.price,
                params=order.params,
            )

            self.rate_limiter.record_post_request()

            # 注文制限更新
            self._update_order_limits(order.symbol, 1)

            # 状態更新
            order.status = OrderStatus.SUBMITTED
            self.active_orders[order.order_id] = order
            self.statistics["successful_orders"] += 1

            logger.info(
                f"Order submitted: {order.order_id} - {order.symbol} "
                f"{order.side} {order.amount}"
            )

        except Exception as e:
            logger.error(f"Failed to submit order {order.order_id}: {e}")

            # リトライ判定
            if order.retry_count < order.max_retries:
                order.retry_count += 1
                order.error_message = str(e)
                self.order_queue.append(order)  # 再キューイング
                logger.info(
                    f"Order requeued for retry: {order.order_id} "
                    f"(attempt {order.retry_count})"
                )
            else:
                # 最大リトライ回数に達した場合
                order.status = OrderStatus.REJECTED
                order.error_message = str(e)
                self.order_history.append(order)
                self.statistics["failed_orders"] += 1
                logger.error(f"Order rejected after max retries: {order.order_id}")

    def _check_order_limits(self, symbol: str) -> bool:
        """注文制限チェック"""
        if symbol not in self.order_limits:
            self.order_limits[symbol] = OrderLimitTracker(
                symbol=symbol, max_orders=self.max_orders_per_symbol
            )

        return self.order_limits[symbol].can_submit_order()

    def _update_order_limits(self, symbol: str, delta: int) -> None:
        """注文制限更新"""
        if symbol not in self.order_limits:
            self.order_limits[symbol] = OrderLimitTracker(
                symbol=symbol, max_orders=self.max_orders_per_symbol
            )

        self.order_limits[symbol].active_orders += delta
        self.order_limits[symbol].active_orders = max(
            0, self.order_limits[symbol].active_orders
        )

    def _cleanup_old_orders(self) -> None:
        """古い注文データクリーンアップ"""
        cutoff_time = datetime.now() - timedelta(hours=24)

        # 古い履歴を削除
        self.order_history = [
            order for order in self.order_history if order.timestamp > cutoff_time
        ]

        # 古いキューエントリを削除
        self.order_queue = [
            order for order in self.order_queue if order.timestamp > cutoff_time
        ]

        logger.debug(
            f"Cleaned up old orders: history={len(self.order_history)}, "
            f"queue={len(self.order_queue)}"
        )

    def __del__(self):
        """デストラクタ"""
        self.stop_processing()

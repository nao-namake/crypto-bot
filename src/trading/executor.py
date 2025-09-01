"""
注文実行システム - Phase 12・CI/CD統合・手動実行監視・段階的デプロイ対応

レガシーシステムの良いところを取り入れつつ、シンプルな実装を実現。
段階的に機能を拡張し、ペーパートレードから実取引まで対応。

レガシーから継承した良い機能:
- VirtualPosition（ポジション管理）
- VirtualTrade（取引記録）
- OrderStatus（注文状態管理）
- パフォーマンス統計・CSV出力

新システムでの改善:
- ccxt直接利用によるシンプル化
- Phase 12リスク管理との統合・CI/CD対応
- Protocol（インターフェース）準拠・GitHub Actions統合
- 1秒以内レイテンシー目標・手動実行監視対応.
"""

import asyncio
import csv
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

# 循環インポート回避のため、型ヒントでのみ使用
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from ..core.config import get_threshold
from ..core.exceptions import CryptoBotError, ExchangeAPIError
from ..core.logger import get_logger

if TYPE_CHECKING:
    from ..data.bitbank_client import BitbankClient

from .risk_manager import RiskDecision, TradeEvaluation


class ExecutionMode(Enum):
    """実行モード."""

    PAPER = "paper"  # ペーパートレード
    LIVE = "live"  # 実取引


class OrderStatus(Enum):
    """注文状態（レガシーから継承・簡素化）."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    CANCELLED = "cancelled"
    FAILED = "failed"


class OrderSide(Enum):
    """注文方向."""

    BUY = "buy"
    SELL = "sell"


@dataclass
class VirtualPosition:
    """
    仮想ポジション管理（レガシーから継承・改良）

    ペーパートレード用のポジション管理。
    実取引と同じロジックで動作し、デプロイ前検証を可能にする。.
    """

    exist: bool = False
    side: str = ""  # "buy" or "sell"
    entry_price: float = 0.0
    amount: float = 0.0  # BTC数量
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    entry_time: Optional[datetime] = None
    unrealized_pnl: float = 0.0

    def calculate_pnl(self, current_price: float) -> float:
        """含み損益を計算."""
        if not self.exist or self.amount == 0:
            return 0.0

        if self.side == "buy":
            # ロングポジション: (現在価格 - エントリー価格) * 数量
            self.unrealized_pnl = (current_price - self.entry_price) * self.amount
        elif self.side == "sell":
            # ショートポジション: (エントリー価格 - 現在価格) * 数量
            self.unrealized_pnl = (self.entry_price - current_price) * self.amount

        return self.unrealized_pnl

    def check_stop_conditions(self, current_price: float) -> Optional[str]:
        """ストップロス・テイクプロフィット条件チェック."""
        if not self.exist:
            return None

        if self.side == "buy":
            if self.stop_loss and current_price <= self.stop_loss:
                return "stop_loss"
            if self.take_profit and current_price >= self.take_profit:
                return "take_profit"
        elif self.side == "sell":
            if self.stop_loss and current_price >= self.stop_loss:
                return "stop_loss"
            if self.take_profit and current_price <= self.take_profit:
                return "take_profit"

        return None


@dataclass
class ExecutionResult:
    """
    注文実行結果（レガシーから継承・構造化改良）.
    """

    success: bool
    mode: ExecutionMode
    order_id: Optional[str] = None
    side: Optional[str] = None
    amount: Optional[float] = None
    price: Optional[float] = None
    filled_amount: Optional[float] = None
    filled_price: Optional[float] = None
    fee: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    timestamp: datetime = field(default_factory=datetime.now)
    error_message: Optional[str] = None

    # ペーパートレード用追加情報
    paper_balance_before: Optional[float] = None
    paper_balance_after: Optional[float] = None
    paper_pnl: Optional[float] = None

    # Phase 12追加: レイテンシー監視・デバッグ情報
    execution_time_ms: Optional[float] = None
    notes: Optional[str] = None


@dataclass
class TradingStatistics:
    """
    取引統計情報（レガシーから継承・メトリクス拡張）.
    """

    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    total_fees: float = 0.0
    max_drawdown: float = 0.0
    current_balance: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    start_time: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)


class OrderExecutor:
    """
    注文実行システム - Phase 12メイン実装・CI/CD統合・手動実行監視・段階的デプロイ対応

    レガシーシステムの良い機能を継承しつつ、
    シンプルで高速な注文実行を実現。

    特徴:
    - ペーパートレード→実取引の段階的移行・CI/CD統合
    - レイテンシー1秒以内（ccxt直接利用）・手動実行監視
    - Phase 12リスク管理との完全統合・GitHub Actions対応
    - 包括的なログ・統計機能・段階的デプロイ対応.
    """

    def __init__(
        self,
        mode: ExecutionMode = ExecutionMode.PAPER,
        initial_balance: Optional[float] = None,  # thresholds.yamlから取得
        fee_rate: Optional[float] = None,  # thresholds.yamlから取得
        log_dir: str = "logs/trading",
    ):
        """
        OrderExecutor初期化

        Args:
            mode: 実行モード（paper/live）
            initial_balance: 初期残高（Noneの場合、thresholds.yamlから取得）
            fee_rate: 取引手数料率（Noneの場合、thresholds.yamlから取得）
            log_dir: ログ出力ディレクトリ.
        """
        self.mode = mode
        self.logger = get_logger()

        # Phase 16-B: 設定ファイルから動的取得（1万円運用対応）
        if initial_balance is None:
            initial_balance = get_threshold("trading.initial_balance_jpy", 10000.0)
        if fee_rate is None:
            fee_rate = get_threshold("trading.fee_rate", 0.0012)

        self.fee_rate = fee_rate

        # ペーパートレード用状態管理
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.virtual_position = VirtualPosition()
        self.statistics = TradingStatistics(current_balance=initial_balance)

        # 実取引用BitbankClient（必要時に初期化）
        self._bitbank_client: Optional["BitbankClient"] = None

        # ログ・記録管理
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._initialize_logging()

        self.logger.info(
            f"OrderExecutor初期化完了 - モード: {mode.value}, " f"初期残高: ¥{initial_balance:,.0f}"
        )

    def _initialize_logging(self):
        """ログファイル初期化（レガシーから継承）."""
        self.trades_csv = self.log_dir / f"trades_{datetime.now().strftime('%Y%m%d')}.csv"
        self.stats_json = self.log_dir / "trading_statistics.json"

        # CSVヘッダー作成
        if not self.trades_csv.exists():
            with open(self.trades_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "timestamp",
                        "mode",
                        "side",
                        "amount",
                        "price",
                        "filled_amount",
                        "filled_price",
                        "fee",
                        "pnl",
                        "balance_before",
                        "balance_after",
                        "status",
                        "order_id",
                        "notes",
                    ]
                )

    async def execute_trade(self, evaluation: TradeEvaluation) -> ExecutionResult:
        """
        取引実行メイン処理

        Phase 12のリスク管理評価結果を受けて、実際の注文実行を行う。
        ペーパートレード・実取引両対応・CI/CD統合・手動実行監視・段階的デプロイ対応。

        Args:
            evaluation: Phase 12リスク管理評価結果

        Returns:
            注文実行結果.
        """
        start_time = time.time()

        try:
            self.logger.info(
                f"取引実行開始 - 判定: {evaluation.decision.value}, "
                f"サイド: {evaluation.side}, ポジションサイズ: {evaluation.position_size:.4f}"
            )

            # 承認された取引のみ実行
            if evaluation.decision != RiskDecision.APPROVED:
                return ExecutionResult(
                    success=False,
                    mode=self.mode,
                    error_message=f"取引が承認されていません: {evaluation.decision.value}",
                )

            # モード別実行
            if self.mode == ExecutionMode.PAPER:
                result = await self._execute_paper_trade(evaluation)
            else:
                result = await self._execute_live_trade(evaluation)

            # 実行時間ログ（レイテンシー監視）
            execution_time = time.time() - start_time
            self.logger.info(
                f"取引実行完了 - 成功: {result.success}, " f"実行時間: {execution_time:.3f}秒"
            )

            # レイテンシー目標チェック
            if execution_time > 1.0:
                self.logger.warning(f"レイテンシー目標超過: {execution_time:.3f}秒 > 1.0秒")

            # 取引記録・統計更新
            await self._record_trade(result)

            return result

        except Exception as e:
            self.logger.error(f"取引実行エラー: {e}", discord_notify=True)
            return ExecutionResult(success=False, mode=self.mode, error_message=str(e))

    async def _execute_paper_trade(self, evaluation: TradeEvaluation) -> ExecutionResult:
        """
        ペーパートレード実行（レガシーから継承・改良）

        実取引と同じロジックで仮想取引を実行。
        実際のBitbank価格を使用して現実的なシミュレーション。.
        """
        try:
            # 現在価格取得（実際のBitbank価格）
            current_price = await self._get_current_price()
            if current_price is None:
                raise ExchangeAPIError("現在価格取得失敗")

            # 手数料計算
            trade_amount_jpy = evaluation.position_size * current_price
            fee = trade_amount_jpy * self.fee_rate

            # 残高チェック
            required_balance = trade_amount_jpy + fee
            if evaluation.side == "buy" and self.current_balance < required_balance:
                raise ExchangeAPIError(
                    f"残高不足: 必要額 ¥{required_balance:,.0f} > 残高 ¥{self.current_balance:,.0f}"
                )

            balance_before = self.current_balance

            # ポジション管理
            if evaluation.side == "buy":
                # 買い注文（ロング）
                if self.virtual_position.exist and self.virtual_position.side == "sell":
                    # ショートポジション決済
                    pnl = self._close_position(current_price)
                else:
                    # 新規ロングポジション
                    self.virtual_position = VirtualPosition(
                        exist=True,
                        side="buy",
                        entry_price=current_price,
                        amount=evaluation.position_size,
                        stop_loss=evaluation.stop_loss,
                        take_profit=evaluation.take_profit,
                        entry_time=datetime.now(),
                    )
                    pnl = 0.0

                self.current_balance -= trade_amount_jpy + fee

            else:  # sell
                # 売り注文（ショート）
                if self.virtual_position.exist and self.virtual_position.side == "buy":
                    # ロングポジション決済
                    pnl = self._close_position(current_price)
                else:
                    # 新規ショートポジション
                    self.virtual_position = VirtualPosition(
                        exist=True,
                        side="sell",
                        entry_price=current_price,
                        amount=evaluation.position_size,
                        stop_loss=evaluation.stop_loss,
                        take_profit=evaluation.take_profit,
                        entry_time=datetime.now(),
                    )
                    pnl = 0.0

                self.current_balance += trade_amount_jpy - fee

            # 実行結果作成
            result = ExecutionResult(
                success=True,
                mode=self.mode,
                order_id=f"paper_{int(time.time())}",
                side=evaluation.side,
                amount=evaluation.position_size,
                price=current_price,
                filled_amount=evaluation.position_size,
                filled_price=current_price,
                fee=fee,
                status=OrderStatus.FILLED,
                paper_balance_before=balance_before,
                paper_balance_after=self.current_balance,
                paper_pnl=pnl,
            )

            self.logger.info(
                f"ペーパートレード実行: {evaluation.side.upper()} "
                f"{evaluation.position_size:.4f} BTC @ ¥{current_price:,.0f}, "
                f"手数料: ¥{fee:,.0f}, 残高: ¥{self.current_balance:,.0f}"
            )

            return result

        except Exception as e:
            self.logger.error(f"ペーパートレード実行エラー: {e}")
            return ExecutionResult(success=False, mode=self.mode, error_message=str(e))

    async def _execute_live_trade(self, evaluation: TradeEvaluation) -> ExecutionResult:
        """
        実取引実行（Phase 12実装・CI/CD統合・手動実行監視対応）

        BitbankClientを使用した実際の信用取引注文実行。
        レガシーシステムの実証済み機能を活用した安全な実装。

        Args:
            evaluation: Phase 12リスク管理評価結果

        Returns:
            実取引実行結果.
        """
        start_time = time.time()  # Phase 12バグ修正: start_time変数定義追加
        try:
            # BitbankClient初期化（認証キー必須）
            if self._bitbank_client is None:
                # 環境変数から認証情報取得
                api_key = os.getenv("BITBANK_API_KEY")
                api_secret = os.getenv("BITBANK_API_SECRET")

                if not api_key or not api_secret:
                    raise ExchangeAPIError(
                        "実取引にはBitbank API認証が必要です",
                        context={
                            "env_vars": [
                                "BITBANK_API_KEY",
                                "BITBANK_API_SECRET",
                            ]
                        },
                    )

                from ..data.bitbank_client import BitbankClient

                self._bitbank_client = BitbankClient(
                    api_key=api_key,
                    api_secret=api_secret,
                    leverage=1.0,  # 保守的なレバレッジから開始
                )

                self.logger.info("実取引用BitbankClient初期化完了", discord_notify=True)

            # 現在価格・残高取得
            current_price = await self._get_current_price()
            if current_price is None:
                raise ExchangeAPIError("現在価格取得失敗")

            balance_info = await asyncio.to_thread(self._bitbank_client.fetch_balance)
            available_jpy = balance_info.get("JPY", {}).get("free", 0)

            # 残高チェック（売買方向別）
            trade_amount_jpy = evaluation.position_size * current_price
            fee_estimate = trade_amount_jpy * self.fee_rate  # 手数料概算

            if evaluation.side == "buy":
                required_balance = trade_amount_jpy + fee_estimate
                if available_jpy < required_balance:
                    raise ExchangeAPIError(
                        f"残高不足（買い注文）: 必要額 ¥{required_balance:,.0f} > 利用可能残高 ¥{available_jpy:,.0f}",
                        context={
                            "required": required_balance,
                            "available": available_jpy,
                            "position_size": evaluation.position_size,
                            "current_price": current_price,
                        },
                    )

            self.logger.info(
                f"実取引実行準備完了 - {evaluation.side.upper()} {evaluation.position_size:.4f} BTC @ ¥{current_price:,.0f}",
                extra_data={
                    "side": evaluation.side,
                    "amount": evaluation.position_size,
                    "price": current_price,
                    "available_balance": available_jpy,
                    "estimated_cost": trade_amount_jpy,
                },
            )

            # 実際の注文実行
            order_type = "market"  # Phase 12は成行注文から開始（確実性重視・段階的デプロイ対応）

            try:
                order = await asyncio.to_thread(
                    self._bitbank_client.create_order,
                    symbol="BTC/JPY",
                    side=evaluation.side,
                    order_type=order_type,
                    amount=evaluation.position_size,
                    price=None,  # 成行注文
                )

                self.logger.info(
                    f"実取引注文成功: {order['id']}",
                    extra_data={
                        "order_id": order["id"],
                        "side": evaluation.side,
                        "amount": evaluation.position_size,
                        "price": current_price,
                    },
                    discord_notify=True,
                )

                # 注文約定確認（設定ファイルから取得）
                order_timeout = get_threshold("performance.order_wait_timeout", 30)
                filled_order = await self._wait_for_order_fill(order["id"], timeout=order_timeout)

                if filled_order and filled_order["status"] == "closed":
                    # 約定成功
                    filled_price = filled_order.get("average", current_price)
                    filled_amount = filled_order.get("filled", evaluation.position_size)
                    actual_fee = filled_order.get("fee", {}).get("cost", 0)

                    self.logger.info(
                        f"実取引約定成功: {order['id']} - ¥{filled_price:,.0f} × {filled_amount:.4f} BTC",
                        extra_data={
                            "order_id": order["id"],
                            "filled_price": filled_price,
                            "filled_amount": filled_amount,
                            "fee": actual_fee,
                        },
                        discord_notify=True,
                    )

                    # 実取引後の残高更新
                    updated_balance_info = await asyncio.to_thread(
                        self._bitbank_client.fetch_balance
                    )
                    updated_balance_jpy = updated_balance_info.get("JPY", {}).get(
                        "free", available_jpy
                    )

                    # Phase 12: 実取引でのポジション管理追加
                    # LIVEモードでも統計とPnL計算のためVirtualPositionを活用
                    if evaluation.side == "buy":
                        if self.virtual_position.exist and self.virtual_position.side == "sell":
                            # ショートポジション決済
                            pnl = self._close_position(filled_price)
                        else:
                            # 新規ロングポジション
                            self.virtual_position = VirtualPosition(
                                exist=True,
                                side="buy",
                                entry_price=filled_price,
                                amount=filled_amount,
                                stop_loss=evaluation.stop_loss,
                                take_profit=evaluation.take_profit,
                                entry_time=datetime.now(),
                            )
                            pnl = 0.0
                    else:  # sell
                        if self.virtual_position.exist and self.virtual_position.side == "buy":
                            # ロングポジション決済
                            pnl = self._close_position(filled_price)
                        else:
                            # 新規ショートポジション
                            self.virtual_position = VirtualPosition(
                                exist=True,
                                side="sell",
                                entry_price=filled_price,
                                amount=filled_amount,
                                stop_loss=evaluation.stop_loss,
                                take_profit=evaluation.take_profit,
                                entry_time=datetime.now(),
                            )
                            pnl = 0.0

                    # 実行結果作成
                    return ExecutionResult(
                        success=True,
                        mode=self.mode,
                        order_id=order["id"],
                        side=evaluation.side,
                        amount=filled_amount,
                        price=current_price,
                        filled_amount=filled_amount,
                        filled_price=filled_price,
                        fee=actual_fee,
                        status=OrderStatus.FILLED,
                        paper_balance_before=available_jpy,
                        paper_balance_after=updated_balance_jpy,
                        paper_pnl=pnl,
                        execution_time_ms=(time.time() - start_time) * 1000,
                        notes=f"実取引約定成功: {evaluation.side.upper()} {filled_amount:.4f} BTC @ ¥{filled_price:,.0f}",
                    )

                else:
                    # 約定失敗またはタイムアウト
                    self.logger.warning(
                        f"注文約定タイムアウト: {order['id']} - 注文キャンセルを試行",
                        discord_notify=True,
                    )

                    # 約定していない注文をキャンセル
                    try:
                        await asyncio.to_thread(self._bitbank_client.cancel_order, order["id"])
                        self.logger.info(f"未約定注文キャンセル成功: {order['id']}")
                    except Exception as cancel_error:
                        self.logger.error(f"注文キャンセル失敗: {cancel_error}")

                    return ExecutionResult(
                        success=False,
                        mode=self.mode,
                        order_id=order["id"],
                        error_message="注文約定タイムアウト（30秒）- 注文キャンセル済み",
                    )

            except ExchangeAPIError as api_error:
                self.logger.error(
                    f"実取引API エラー: {api_error}",
                    error=api_error,
                    discord_notify=True,
                )
                return ExecutionResult(
                    success=False,
                    mode=self.mode,
                    error_message=f"取引所APIエラー: {api_error}",
                )

        except Exception as e:
            self.logger.error(f"実取引実行エラー: {e}", error=e, discord_notify=True)
            return ExecutionResult(
                success=False,
                mode=self.mode,
                error_message=f"実取引実行失敗: {str(e)}",
            )

    async def _wait_for_order_fill(
        self, order_id: str, timeout: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        注文約定待機

        Args:
            order_id: 注文ID
            timeout: タイムアウト秒数（None時は設定ファイルから取得）
        """
        if timeout is None:
            timeout = get_threshold("performance.order_wait_timeout", 30)
        """
        注文約定待機

        Args:
            order_id: 注文ID
            timeout: タイムアウト時間（秒）

        Returns:
            約定済み注文情報（タイムアウト時はNone）.
        """
        start_time = time.time()

        while (time.time() - start_time) < timeout:
            try:
                order = await asyncio.to_thread(self._bitbank_client.fetch_order, order_id)

                if order["status"] in ["closed", "canceled"]:
                    return order

                # 1秒間隔でポーリング
                await asyncio.sleep(1)

            except Exception as e:
                self.logger.warning(f"注文状況確認エラー: {e}")
                await asyncio.sleep(1)

        self.logger.warning(f"注文約定タイムアウト: {order_id} ({timeout}秒)")
        return None

    async def _get_current_price(self) -> Optional[float]:
        """現在価格取得."""
        try:
            # BitbankClientを使用して現在価格取得
            if self._bitbank_client is None:
                from ..data.bitbank_client import BitbankClient

                self._bitbank_client = BitbankClient()

            ticker = await asyncio.to_thread(self._bitbank_client.exchange.fetch_ticker, "BTC/JPY")
            return float(ticker["last"])

        except Exception as e:
            self.logger.error(f"現在価格取得エラー: {e}")
            return None

    def _close_position(self, current_price: float) -> float:
        """ポジション決済（レガシーから継承）."""
        if not self.virtual_position.exist:
            return 0.0

        pnl = self.virtual_position.calculate_pnl(current_price)
        self.current_balance += pnl

        self.logger.info(
            f"ポジション決済: {self.virtual_position.side.upper()} "
            f"{self.virtual_position.amount:.4f} BTC, PnL: ¥{pnl:,.0f}"
        )

        # ポジションクリア
        self.virtual_position = VirtualPosition()

        return pnl

    async def _record_trade(self, result: ExecutionResult):
        """取引記録・統計更新（レガシーから継承・改良）."""
        try:
            # CSV記録
            with open(self.trades_csv, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        result.timestamp.isoformat(),
                        result.mode.value,
                        result.side,
                        result.amount,
                        result.price,
                        result.filled_amount,
                        result.filled_price,
                        result.fee,
                        result.paper_pnl or 0.0,
                        result.paper_balance_before,
                        result.paper_balance_after,
                        result.status.value,
                        result.order_id,
                        result.error_message or "",
                    ]
                )

            # 統計更新
            if result.success:
                self.statistics.total_trades += 1
                if result.paper_pnl and result.paper_pnl > 0:
                    self.statistics.winning_trades += 1
                elif result.paper_pnl and result.paper_pnl < 0:
                    self.statistics.losing_trades += 1

                self.statistics.total_pnl += result.paper_pnl or 0.0
                self.statistics.total_fees += result.fee or 0.0
                self.statistics.current_balance = self.current_balance
                self.statistics.last_update = datetime.now()

                # 勝率計算
                if self.statistics.total_trades > 0:
                    self.statistics.win_rate = (
                        self.statistics.winning_trades / self.statistics.total_trades
                    )

            # 統計JSON保存
            with open(self.stats_json, "w", encoding="utf-8") as f:
                stats_dict = {
                    "total_trades": self.statistics.total_trades,
                    "winning_trades": self.statistics.winning_trades,
                    "losing_trades": self.statistics.losing_trades,
                    "win_rate": self.statistics.win_rate,
                    "total_pnl": self.statistics.total_pnl,
                    "total_fees": self.statistics.total_fees,
                    "current_balance": self.statistics.current_balance,
                    "initial_balance": self.initial_balance,
                    "return_rate": (self.current_balance - self.initial_balance)
                    / self.initial_balance,
                    "last_update": self.statistics.last_update.isoformat(),
                }
                json.dump(stats_dict, f, indent=2, ensure_ascii=False)

        except Exception as e:
            self.logger.error(f"取引記録エラー: {e}")

    def get_trading_statistics(self) -> Dict[str, Any]:
        """取引統計情報取得."""
        return {
            "mode": self.mode.value,
            "statistics": self.statistics,
            "virtual_position": (
                self.virtual_position if self.mode == ExecutionMode.PAPER else None
            ),
            "current_balance": self.current_balance,
            "initial_balance": self.initial_balance,
            "return_rate": (self.current_balance - self.initial_balance) / self.initial_balance,
            "unrealized_pnl": (
                self.virtual_position.unrealized_pnl if self.virtual_position.exist else 0.0
            ),
        }

    async def check_stop_conditions(self) -> Optional[ExecutionResult]:
        """
        ストップロス・テイクプロフィット条件チェック

        定期的に呼び出して、自動決済条件をチェックする。.
        """
        if not self.virtual_position.exist:
            return None

        try:
            current_price = await self._get_current_price()
            if current_price is None:
                return None

            stop_reason = self.virtual_position.check_stop_conditions(current_price)
            if stop_reason:
                self.logger.info(f"自動決済条件検出: {stop_reason} @ ¥{current_price:,.0f}")

                # 反対売買で決済
                opposite_side = "sell" if self.virtual_position.side == "buy" else "buy"

                # ダミーの評価結果作成（自動決済用）
                dummy_evaluation = TradeEvaluation(
                    decision=RiskDecision.APPROVED,
                    side=opposite_side,
                    risk_score=0.1,  # 必須フィールド追加
                    position_size=self.virtual_position.amount,
                    stop_loss=None,
                    take_profit=None,
                    confidence_level=1.0,
                    warnings=[f"自動決済: {stop_reason}"],
                    denial_reasons=[],
                    evaluation_timestamp=datetime.now(),
                    kelly_recommendation=0.0,
                    drawdown_status="unknown",
                    anomaly_alerts=[],
                    market_conditions={},
                )

                return await self.execute_trade(dummy_evaluation)

        except Exception as e:
            self.logger.error(f"ストップ条件チェックエラー: {e}")

        return None


# ファクトリー関数（orchestrator.pyからの利用用）
def create_order_executor(
    mode: str = "paper", initial_balance: Optional[float] = None, **kwargs
) -> OrderExecutor:
    """
    OrderExecutor作成用ファクトリー関数

    Args:
        mode: 実行モード（"paper" or "live"）
        initial_balance: 初期残高
        **kwargs: その他のOrderExecutor引数

    Returns:
        OrderExecutor インスタンス
    """
    execution_mode = ExecutionMode.PAPER if mode.lower() == "paper" else ExecutionMode.LIVE
    return OrderExecutor(mode=execution_mode, initial_balance=initial_balance, **kwargs)

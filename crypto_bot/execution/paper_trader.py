"""
ペーパートレード実行システム

ChatGPT提案採用: リアルタイムデータ＋仮想取引実行
ローカルで本番同等の動作検証を実現し、デプロイ前エラーを防止
"""

import csv
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class VirtualPosition:
    """仮想ポジション管理"""

    exist: bool = False
    side: str = ""  # "BUY" or "SELL"
    entry_price: float = 0.0
    lot: float = 0.0
    stop_price: float = 0.0
    entry_time: Optional[datetime] = None
    unrealized_pnl: float = 0.0

    def calculate_pnl(self, current_price: float) -> float:
        """含み損益を計算"""
        if not self.exist:
            return 0.0

        if self.side == "BUY":
            self.unrealized_pnl = (current_price - self.entry_price) * self.lot
        elif self.side == "SELL":
            self.unrealized_pnl = (self.entry_price - current_price) * self.lot

        return self.unrealized_pnl


@dataclass
class VirtualTrade:
    """仮想取引記録"""

    timestamp: datetime
    trade_type: str  # "ENTRY" or "EXIT"
    side: str  # "BUY" or "SELL"
    price: float
    lot: float
    balance_before: float
    balance_after: float
    position_before: str
    position_after: str
    pnl: float = 0.0
    fee: float = 0.0
    signal_confidence: float = 0.0
    stop_price: float = 0.0
    notes: str = ""


class PaperTrader:
    """
    ペーパートレード実行管理クラス

    実取引と同じロジックで仮想取引を実行し、
    結果をCSV/JSONに記録する
    """

    def __init__(
        self,
        initial_balance: float = 1000000.0,
        fee_rate: float = 0.0012,  # Bitbank maker手数料
        log_dir: str = "logs",
    ):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.fee_rate = fee_rate
        self.position = VirtualPosition()
        self.trades: List[VirtualTrade] = []

        # ログディレクトリ設定
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # ファイルパス
        self.trades_csv = self.log_dir / "paper_trades.csv"
        self.performance_json = self.log_dir / "paper_performance.json"

        # CSVヘッダー初期化
        self._initialize_csv()

        # パフォーマンス統計
        self.stats = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "total_fees": 0.0,
            "max_drawdown": 0.0,
            "peak_balance": initial_balance,
            "win_rate": 0.0,
            "average_win": 0.0,
            "average_loss": 0.0,
            "profit_factor": 0.0,
            "start_time": datetime.now().isoformat(),
            "last_update": datetime.now().isoformat(),
        }

        logger.info(
            f"📝 PaperTrader initialized with balance: {initial_balance:.2f} JPY"
        )

    def _initialize_csv(self) -> None:
        """CSVファイルのヘッダー初期化"""
        if not self.trades_csv.exists():
            headers = [
                "timestamp",
                "trade_type",
                "side",
                "price",
                "lot",
                "balance_before",
                "balance_after",
                "position_before",
                "position_after",
                "pnl",
                "fee",
                "signal_confidence",
                "stop_price",
                "notes",
            ]
            with open(self.trades_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(headers)

    def execute_virtual_trade(
        self,
        order: Any,  # Order オブジェクト
        position: Any,  # Position オブジェクト（実際のもの）
        is_exit: bool = False,
        signal_confidence: float = 0.0,
        notes: str = "",
    ) -> bool:
        """
        仮想取引を実行

        Parameters:
        -----------
        order : Order
            注文情報
        position : Position
            現在のポジション（実際のPositionオブジェクト）
        is_exit : bool
            エグジット注文かどうか
        signal_confidence : float
            シグナル信頼度
        notes : str
            メモ

        Returns:
        --------
        bool
            取引成功フラグ（ペーパートレードでは常にTrue）
        """
        if not order.exist:
            return False

        # 取引手数料計算
        trade_value = order.price * order.lot
        fee = trade_value * self.fee_rate

        # 仮想取引記録作成
        trade = VirtualTrade(
            timestamp=datetime.now(),
            trade_type="EXIT" if is_exit else "ENTRY",
            side=order.side,
            price=order.price,
            lot=order.lot,
            balance_before=self.current_balance,
            balance_after=self.current_balance,  # 後で更新
            position_before=(
                f"{self.position.side}:{self.position.lot:.4f}"
                if self.position.exist
                else "NONE"
            ),
            position_after="",  # 後で更新
            fee=fee,
            signal_confidence=signal_confidence,
            stop_price=getattr(order, "stop_price", 0.0),
            notes=notes,
        )

        # ポジション・残高更新
        if is_exit:
            # エグジット処理
            if self.position.exist:
                # 実現損益計算
                pnl = self.position.calculate_pnl(order.price)
                trade.pnl = pnl

                # 残高更新（損益と手数料を反映）
                self.current_balance += pnl - fee
                trade.balance_after = self.current_balance

                # ポジションクローズ
                self.position.exist = False
                self.position.side = ""
                self.position.lot = 0.0
                trade.position_after = "NONE"

                # 統計更新
                self._update_statistics(pnl, fee)

                logger.info(
                    f"💰 [PAPER EXIT] {order.side} @ {order.price:.2f}, "
                    f"PnL: {pnl:+.2f} JPY, Fee: {fee:.2f} JPY"
                )
        else:
            # エントリー処理
            # 手数料を引いて残高更新
            self.current_balance -= fee
            trade.balance_after = self.current_balance

            # 新規ポジション設定
            self.position.exist = True
            self.position.side = order.side
            self.position.entry_price = order.price
            self.position.lot = order.lot
            self.position.stop_price = getattr(order, "stop_price", 0.0)
            self.position.entry_time = datetime.now()
            trade.position_after = f"{order.side}:{order.lot:.4f}"

            logger.info(
                f"📈 [PAPER ENTRY] {order.side} {order.lot:.4f} @ {order.price:.2f}, "
                f"Stop: {self.position.stop_price:.2f}, Fee: {fee:.2f} JPY"
            )

        # 取引記録追加
        self.trades.append(trade)

        # CSV記録
        self._save_trade_to_csv(trade)

        # パフォーマンス統計更新
        self._update_performance_stats()

        # 実際のPositionオブジェクトも更新（互換性のため）
        if not is_exit:
            position.exist = True
            position.side = order.side
            position.entry_price = order.price
            position.lot = order.lot
            position.stop_price = getattr(order, "stop_price", 0.0)
        else:
            position.exist = False
            position.side = ""
            position.lot = 0.0

        return True

    def _save_trade_to_csv(self, trade: VirtualTrade) -> None:
        """取引をCSVに記録"""
        try:
            row = [
                trade.timestamp.isoformat(),
                trade.trade_type,
                trade.side,
                trade.price,
                trade.lot,
                trade.balance_before,
                trade.balance_after,
                trade.position_before,
                trade.position_after,
                trade.pnl,
                trade.fee,
                trade.signal_confidence,
                trade.stop_price,
                trade.notes,
            ]

            with open(self.trades_csv, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(row)
        except Exception as e:
            logger.warning(f"Failed to save trade to CSV: {e}")

    def _update_statistics(self, pnl: float, fee: float) -> None:
        """取引統計を更新"""
        self.stats["total_trades"] += 1
        self.stats["total_pnl"] += pnl
        self.stats["total_fees"] += fee

        if pnl > 0:
            self.stats["winning_trades"] += 1
        elif pnl < 0:
            self.stats["losing_trades"] += 1

    def _update_performance_stats(self) -> None:
        """パフォーマンス統計を更新・保存"""
        # 最高残高・ドローダウン更新
        if self.current_balance > self.stats["peak_balance"]:
            self.stats["peak_balance"] = self.current_balance

        drawdown = (self.stats["peak_balance"] - self.current_balance) / self.stats[
            "peak_balance"
        ]
        if drawdown > self.stats["max_drawdown"]:
            self.stats["max_drawdown"] = drawdown

        # 勝率計算
        total = self.stats["winning_trades"] + self.stats["losing_trades"]
        if total > 0:
            self.stats["win_rate"] = self.stats["winning_trades"] / total

        # 現在残高・収益率
        self.stats["current_balance"] = self.current_balance
        self.stats["total_return"] = (
            self.current_balance - self.initial_balance
        ) / self.initial_balance
        self.stats["last_update"] = datetime.now().isoformat()

        # JSON保存
        try:
            with open(self.performance_json, "w", encoding="utf-8") as f:
                json.dump(self.stats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to save performance stats: {e}")

    def get_summary(self) -> Dict[str, Any]:
        """現在のサマリー情報を取得"""
        return {
            "current_balance": self.current_balance,
            "initial_balance": self.initial_balance,
            "total_pnl": self.stats["total_pnl"],
            "total_fees": self.stats["total_fees"],
            "total_trades": self.stats["total_trades"],
            "win_rate": self.stats["win_rate"],
            "max_drawdown": self.stats["max_drawdown"],
            "position": {
                "exist": self.position.exist,
                "side": self.position.side,
                "lot": self.position.lot,
                "entry_price": self.position.entry_price,
                "unrealized_pnl": (
                    self.position.calculate_pnl(
                        self.position.entry_price  # 現在価格が必要
                    )
                    if self.position.exist
                    else 0.0
                ),
            },
        }

    def print_summary(self) -> None:
        """サマリー情報を出力"""
        summary = self.get_summary()

        logger.info("=" * 50)
        logger.info("📊 PAPER TRADING SUMMARY")
        logger.info("=" * 50)
        logger.info(f"💰 Current Balance: {summary['current_balance']:.2f} JPY")
        logger.info(f"📈 Total PnL: {summary['total_pnl']:+.2f} JPY")
        logger.info(f"💸 Total Fees: {summary['total_fees']:.2f} JPY")
        logger.info(f"📊 Total Trades: {summary['total_trades']}")
        logger.info(f"🎯 Win Rate: {summary['win_rate']:.1%}")
        logger.info(f"📉 Max Drawdown: {summary['max_drawdown']:.1%}")

        if summary["position"]["exist"]:
            logger.info(
                f"📍 Current Position: {summary['position']['side']} "
                f"{summary['position']['lot']:.4f} @ "
                f"{summary['position']['entry_price']:.2f}"
            )
        else:
            logger.info("📍 No Position")
        logger.info("=" * 50)

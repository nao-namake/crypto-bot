"""
取引統計管理システム
パフォーマンス指標追跡・リアルタイム統計更新・詳細レポート生成
"""

import csv
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd


@dataclass
class TradeRecord:
    """個別取引記録"""

    trade_id: str
    timestamp: datetime
    symbol: str
    side: str  # 'buy' or 'sell'
    entry_price: float
    exit_price: Optional[float] = None
    quantity: float = 0.0
    profit_loss: float = 0.0
    profit_loss_percentage: float = 0.0
    duration_seconds: Optional[int] = None
    entry_fee: float = 0.0
    exit_fee: float = 0.0
    net_profit: float = 0.0
    strategy_type: str = "unknown"
    confidence_score: float = 0.0
    market_conditions: Dict[str, Any] = None
    status: str = "open"  # 'open', 'closed', 'cancelled'

    def __post_init__(self):
        if self.market_conditions is None:
            self.market_conditions = {}


@dataclass
class DailyStatistics:
    """日次統計"""

    date: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    break_even_trades: int = 0
    win_rate: float = 0.0
    total_profit: float = 0.0
    total_fees: float = 0.0
    net_profit: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    average_profit_per_trade: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    total_volume: float = 0.0
    trading_duration_minutes: int = 0


@dataclass
class PerformanceMetrics:
    """包括的パフォーマンス指標"""

    # 基本統計
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0

    # 損益統計
    total_profit: float = 0.0
    total_fees: float = 0.0
    net_profit: float = 0.0
    roi: float = 0.0

    # リスク指標
    max_drawdown: float = 0.0
    current_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0

    # 効率性指標
    profit_factor: float = 0.0
    recovery_factor: float = 0.0
    payoff_ratio: float = 0.0

    # 取引パターン
    average_trade_duration: float = 0.0
    average_profit_per_trade: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0

    # 手数料効率
    fee_to_profit_ratio: float = 0.0
    net_profit_margin: float = 0.0

    # 時間効率
    trades_per_day: float = 0.0
    active_trading_days: int = 0

    # 市場効率
    market_correlation: float = 0.0
    alpha: float = 0.0
    beta: float = 0.0


class TradingStatisticsManager:
    """取引統計管理メインクラス"""

    def __init__(
        self, base_dir: str = "/app", initial_balance: float = 100000.0
    ):  # Phase G.2.4.1: Cloud Run環境統一
        self.base_dir = Path(base_dir)
        self.results_dir = self.base_dir / "results"
        self.results_dir.mkdir(exist_ok=True)

        self.initial_balance = initial_balance
        self.current_balance = initial_balance

        # ファイルパス設定
        self.status_file = self.base_dir / "status.json"
        self.trade_log_file = self.results_dir / "trade_log.csv"
        self.daily_stats_file = self.results_dir / "daily_statistics.csv"
        self.performance_file = self.results_dir / "performance_metrics.json"
        self.detailed_log_file = self.results_dir / "detailed_trade_log.csv"

        # 内部データ
        self.trades: List[TradeRecord] = []
        self.daily_stats: Dict[str, DailyStatistics] = {}
        self.performance_metrics = PerformanceMetrics()

        # ログ設定
        self.logger = logging.getLogger(__name__)

        # 既存データ読み込み
        self._load_existing_data()

    def _load_existing_data(self):
        """既存データの読み込み"""
        try:
            # 詳細取引ログ読み込み
            if self.detailed_log_file.exists():
                self._load_detailed_trades()

            # 日次統計読み込み
            if self.daily_stats_file.exists():
                self._load_daily_statistics()

            # パフォーマンス指標読み込み
            if self.performance_file.exists():
                self._load_performance_metrics()

        except Exception as e:
            self.logger.error(f"既存データ読み込みエラー: {e}")

    def _load_detailed_trades(self):
        """詳細取引データ読み込み"""
        try:
            df = pd.read_csv(self.detailed_log_file)
            for _, row in df.iterrows():
                trade = TradeRecord(
                    trade_id=row["trade_id"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    symbol=row["symbol"],
                    side=row["side"],
                    entry_price=row["entry_price"],
                    exit_price=row.get("exit_price"),
                    quantity=row["quantity"],
                    profit_loss=row["profit_loss"],
                    profit_loss_percentage=row["profit_loss_percentage"],
                    duration_seconds=row.get("duration_seconds"),
                    entry_fee=row["entry_fee"],
                    exit_fee=row["exit_fee"],
                    net_profit=row["net_profit"],
                    strategy_type=row.get("strategy_type", "unknown"),
                    confidence_score=row.get("confidence_score", 0.0),
                    market_conditions=json.loads(row.get("market_conditions", "{}")),
                    status=row.get("status", "closed"),
                )
                self.trades.append(trade)
        except Exception as e:
            self.logger.error(f"詳細取引データ読み込みエラー: {e}")

    def _load_daily_statistics(self):
        """日次統計読み込み"""
        try:
            df = pd.read_csv(self.daily_stats_file)
            for _, row in df.iterrows():
                date_str = row["date"]
                self.daily_stats[date_str] = DailyStatistics(
                    date=date_str,
                    total_trades=row["total_trades"],
                    winning_trades=row["winning_trades"],
                    losing_trades=row["losing_trades"],
                    break_even_trades=row["break_even_trades"],
                    win_rate=row["win_rate"],
                    total_profit=row["total_profit"],
                    total_fees=row["total_fees"],
                    net_profit=row["net_profit"],
                    largest_win=row["largest_win"],
                    largest_loss=row["largest_loss"],
                    average_profit_per_trade=row["average_profit_per_trade"],
                    average_win=row["average_win"],
                    average_loss=row["average_loss"],
                    profit_factor=row["profit_factor"],
                    sharpe_ratio=row["sharpe_ratio"],
                    max_consecutive_wins=row["max_consecutive_wins"],
                    max_consecutive_losses=row["max_consecutive_losses"],
                    total_volume=row["total_volume"],
                    trading_duration_minutes=row["trading_duration_minutes"],
                )
        except Exception as e:
            self.logger.error(f"日次統計読み込みエラー: {e}")

    def _load_performance_metrics(self):
        """パフォーマンス指標読み込み"""
        try:
            with open(self.performance_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.performance_metrics = PerformanceMetrics(**data)
        except Exception as e:
            self.logger.error(f"パフォーマンス指標読み込みエラー: {e}")

    def record_trade(self, trade: TradeRecord) -> str:
        """新規取引記録"""
        if not trade.trade_id:
            trade.trade_id = f"trade_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        # 取引リストに追加
        self.trades.append(trade)

        # ファイルに保存
        self._save_detailed_trade(trade)

        # 統計更新
        if trade.status == "closed":
            self._update_statistics(trade)

        self.logger.info(
            f"取引記録: {trade.trade_id} - {trade.side} {trade.symbol} @ "
            f"{trade.entry_price}"
        )

        return trade.trade_id

    def close_trade(
        self, trade_id: str, exit_price: float, exit_fee: float = 0.0
    ) -> bool:
        """取引決済"""
        for trade in self.trades:
            if trade.trade_id == trade_id and trade.status == "open":
                # 決済情報更新
                trade.exit_price = exit_price
                trade.exit_fee = exit_fee
                trade.status = "closed"

                # 損益計算
                if trade.side.lower() == "buy":
                    trade.profit_loss = (
                        exit_price - trade.entry_price
                    ) * trade.quantity
                else:  # sell
                    trade.profit_loss = (
                        trade.entry_price - exit_price
                    ) * trade.quantity

                trade.profit_loss_percentage = (
                    trade.profit_loss / (trade.entry_price * trade.quantity)
                ) * 100
                trade.net_profit = trade.profit_loss - trade.entry_fee - trade.exit_fee

                # 期間計算
                if trade.timestamp:
                    trade.duration_seconds = int(
                        (datetime.now() - trade.timestamp).total_seconds()
                    )

                # 統計更新
                self._update_statistics(trade)

                # ファイル保存
                self._save_detailed_trade(trade)

                self.logger.info(f"取引決済: {trade_id} - 損益: {trade.net_profit:.2f}")
                return True

        return False

    def _update_statistics(self, trade: TradeRecord):
        """統計データ更新"""
        # 日次統計更新
        date_str = trade.timestamp.strftime("%Y-%m-%d")
        if date_str not in self.daily_stats:
            self.daily_stats[date_str] = DailyStatistics(date=date_str)

        daily_stat = self.daily_stats[date_str]
        daily_stat.total_trades += 1
        daily_stat.total_profit += trade.profit_loss
        daily_stat.total_fees += trade.entry_fee + trade.exit_fee
        daily_stat.net_profit += trade.net_profit
        daily_stat.total_volume += trade.quantity * trade.entry_price

        if trade.net_profit > 0:
            daily_stat.winning_trades += 1
            daily_stat.largest_win = max(daily_stat.largest_win, trade.net_profit)
        elif trade.net_profit < 0:
            daily_stat.losing_trades += 1
            daily_stat.largest_loss = min(daily_stat.largest_loss, trade.net_profit)
        else:
            daily_stat.break_even_trades += 1

        # 勝率計算
        daily_stat.win_rate = (
            daily_stat.winning_trades / daily_stat.total_trades
            if daily_stat.total_trades > 0
            else 0
        )

        # 平均損益計算
        daily_stat.average_profit_per_trade = (
            daily_stat.net_profit / daily_stat.total_trades
            if daily_stat.total_trades > 0
            else 0
        )

        # パフォーマンス指標更新
        self._update_performance_metrics()

        # ファイル保存
        self._save_daily_statistics()
        self._save_performance_metrics()
        self._update_status_file()

    def _update_performance_metrics(self):
        """包括的パフォーマンス指標更新"""
        if not self.trades:
            return

        closed_trades = [t for t in self.trades if t.status == "closed"]
        if not closed_trades:
            return

        # 基本統計
        self.performance_metrics.total_trades = len(closed_trades)
        self.performance_metrics.winning_trades = len(
            [t for t in closed_trades if t.net_profit > 0]
        )
        self.performance_metrics.losing_trades = len(
            [t for t in closed_trades if t.net_profit < 0]
        )
        self.performance_metrics.win_rate = (
            self.performance_metrics.winning_trades
            / self.performance_metrics.total_trades
        )

        # 損益統計
        profits = [t.net_profit for t in closed_trades]
        self.performance_metrics.total_profit = sum(
            [t.profit_loss for t in closed_trades]
        )
        self.performance_metrics.total_fees = sum(
            [t.entry_fee + t.exit_fee for t in closed_trades]
        )
        self.performance_metrics.net_profit = sum(profits)
        self.performance_metrics.roi = (
            self.performance_metrics.net_profit / self.initial_balance
        ) * 100

        # リスク指標
        self._calculate_risk_metrics(profits)

        # 効率性指標
        self._calculate_efficiency_metrics(closed_trades, profits)

        # 取引パターン
        self._calculate_trading_patterns(closed_trades, profits)

        # 手数料効率
        if self.performance_metrics.total_profit != 0:
            self.performance_metrics.fee_to_profit_ratio = (
                self.performance_metrics.total_fees
                / abs(self.performance_metrics.total_profit)
            )
            self.performance_metrics.net_profit_margin = (
                self.performance_metrics.net_profit
                / self.performance_metrics.total_profit
            ) * 100

        # 時間効率
        self._calculate_time_efficiency(closed_trades)

    def _calculate_risk_metrics(self, profits: List[float]):
        """リスク指標計算"""
        if not profits:
            return

        # ドローダウン計算
        cumulative = np.cumsum(profits)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = cumulative - running_max

        self.performance_metrics.max_drawdown = abs(np.min(drawdown))
        self.performance_metrics.current_drawdown = (
            abs(drawdown[-1]) if len(drawdown) > 0 else 0
        )

        # シャープレシオ
        if len(profits) > 1:
            returns_std = np.std(profits)
            if returns_std > 0:
                self.performance_metrics.sharpe_ratio = np.mean(profits) / returns_std

        # ソルティノレシオ
        negative_returns = [p for p in profits if p < 0]
        if negative_returns:
            downside_deviation = np.std(negative_returns)
            if downside_deviation > 0:
                self.performance_metrics.sortino_ratio = (
                    np.mean(profits) / downside_deviation
                )

        # カルマーレシオ
        if self.performance_metrics.max_drawdown > 0:
            annual_return = self.performance_metrics.roi
            self.performance_metrics.calmar_ratio = (
                annual_return / self.performance_metrics.max_drawdown
            )

    def _calculate_efficiency_metrics(
        self, trades: List[TradeRecord], profits: List[float]
    ):
        """効率性指標計算"""
        winning_profits = [p for p in profits if p > 0]
        losing_profits = [p for p in profits if p < 0]

        # プロフィットファクター
        if losing_profits:
            total_wins = sum(winning_profits)
            total_losses = abs(sum(losing_profits))
            if total_losses > 0:
                self.performance_metrics.profit_factor = total_wins / total_losses

        # リカバリーファクター
        if self.performance_metrics.max_drawdown > 0:
            self.performance_metrics.recovery_factor = (
                self.performance_metrics.net_profit
                / self.performance_metrics.max_drawdown
            )

        # ペイオフレシオ
        if losing_profits and winning_profits:
            avg_win = np.mean(winning_profits)
            avg_loss = abs(np.mean(losing_profits))
            if avg_loss > 0:
                self.performance_metrics.payoff_ratio = avg_win / avg_loss

    def _calculate_trading_patterns(
        self, trades: List[TradeRecord], profits: List[float]
    ):
        """取引パターン計算"""
        # 平均取引期間
        durations = [t.duration_seconds for t in trades if t.duration_seconds]
        if durations:
            self.performance_metrics.average_trade_duration = (
                np.mean(durations) / 60
            )  # 分単位

        # 平均利益
        self.performance_metrics.average_profit_per_trade = (
            np.mean(profits) if profits else 0
        )

        # 最大勝ち・負け
        if profits:
            self.performance_metrics.largest_win = max(profits)
            self.performance_metrics.largest_loss = min(profits)

        # 連続勝ち・負け
        consecutive_wins = 0
        consecutive_losses = 0
        max_wins = 0
        max_losses = 0

        for profit in profits:
            if profit > 0:
                consecutive_wins += 1
                consecutive_losses = 0
                max_wins = max(max_wins, consecutive_wins)
            elif profit < 0:
                consecutive_losses += 1
                consecutive_wins = 0
                max_losses = max(max_losses, consecutive_losses)
            else:
                consecutive_wins = 0
                consecutive_losses = 0

        self.performance_metrics.max_consecutive_wins = max_wins
        self.performance_metrics.max_consecutive_losses = max_losses

    def _calculate_time_efficiency(self, trades: List[TradeRecord]):
        """時間効率計算"""
        if not trades:
            return

        # 取引日数計算
        dates = set(t.timestamp.date() for t in trades)
        self.performance_metrics.active_trading_days = len(dates)

        # 1日あたりの取引数
        if self.performance_metrics.active_trading_days > 0:
            self.performance_metrics.trades_per_day = (
                len(trades) / self.performance_metrics.active_trading_days
            )

    def _save_detailed_trade(self, trade: TradeRecord):
        """詳細取引ログ保存"""
        file_exists = self.detailed_log_file.exists()

        with open(self.detailed_log_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            if not file_exists:
                # ヘッダー書き込み
                writer.writerow(
                    [
                        "trade_id",
                        "timestamp",
                        "symbol",
                        "side",
                        "entry_price",
                        "exit_price",
                        "quantity",
                        "profit_loss",
                        "profit_loss_percentage",
                        "duration_seconds",
                        "entry_fee",
                        "exit_fee",
                        "net_profit",
                        "strategy_type",
                        "confidence_score",
                        "market_conditions",
                        "status",
                    ]
                )

            # データ書き込み
            writer.writerow(
                [
                    trade.trade_id,
                    trade.timestamp.isoformat(),
                    trade.symbol,
                    trade.side,
                    trade.entry_price,
                    trade.exit_price,
                    trade.quantity,
                    trade.profit_loss,
                    trade.profit_loss_percentage,
                    trade.duration_seconds,
                    trade.entry_fee,
                    trade.exit_fee,
                    trade.net_profit,
                    trade.strategy_type,
                    trade.confidence_score,
                    json.dumps(trade.market_conditions),
                    trade.status,
                ]
            )

    def _save_daily_statistics(self):
        """日次統計保存"""
        with open(self.daily_stats_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # ヘッダー
            writer.writerow(
                [
                    "date",
                    "total_trades",
                    "winning_trades",
                    "losing_trades",
                    "break_even_trades",
                    "win_rate",
                    "total_profit",
                    "total_fees",
                    "net_profit",
                    "largest_win",
                    "largest_loss",
                    "average_profit_per_trade",
                    "average_win",
                    "average_loss",
                    "profit_factor",
                    "sharpe_ratio",
                    "max_consecutive_wins",
                    "max_consecutive_losses",
                    "total_volume",
                    "trading_duration_minutes",
                ]
            )

            # データ
            for daily_stat in self.daily_stats.values():
                writer.writerow(
                    [
                        daily_stat.date,
                        daily_stat.total_trades,
                        daily_stat.winning_trades,
                        daily_stat.losing_trades,
                        daily_stat.break_even_trades,
                        daily_stat.win_rate,
                        daily_stat.total_profit,
                        daily_stat.total_fees,
                        daily_stat.net_profit,
                        daily_stat.largest_win,
                        daily_stat.largest_loss,
                        daily_stat.average_profit_per_trade,
                        daily_stat.average_win,
                        daily_stat.average_loss,
                        daily_stat.profit_factor,
                        daily_stat.sharpe_ratio,
                        daily_stat.max_consecutive_wins,
                        daily_stat.max_consecutive_losses,
                        daily_stat.total_volume,
                        daily_stat.trading_duration_minutes,
                    ]
                )

    def _save_performance_metrics(self):
        """パフォーマンス指標保存"""
        with open(self.performance_file, "w", encoding="utf-8") as f:
            json.dump(asdict(self.performance_metrics), f, indent=2, ensure_ascii=False)

    def _update_status_file(self):
        """ステータスファイル更新"""
        status_data = {
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "system_status": "running",
            "initial_balance": self.initial_balance,
            "current_balance": self.current_balance,
            # 基本統計
            "total_trades": self.performance_metrics.total_trades,
            "winning_trades": self.performance_metrics.winning_trades,
            "losing_trades": self.performance_metrics.losing_trades,
            "win_rate": round(self.performance_metrics.win_rate, 4),
            # 損益
            "total_profit": round(self.performance_metrics.total_profit, 2),
            "total_fees": round(self.performance_metrics.total_fees, 2),
            "net_profit": round(self.performance_metrics.net_profit, 2),
            "roi_percentage": round(self.performance_metrics.roi, 2),
            # リスク指標
            "max_drawdown": round(self.performance_metrics.max_drawdown, 2),
            "current_drawdown": round(self.performance_metrics.current_drawdown, 2),
            "sharpe_ratio": round(self.performance_metrics.sharpe_ratio, 4),
            "sortino_ratio": round(self.performance_metrics.sortino_ratio, 4),
            # 効率性
            "profit_factor": round(self.performance_metrics.profit_factor, 4),
            "payoff_ratio": round(self.performance_metrics.payoff_ratio, 4),
            # 取引パターン
            "average_profit_per_trade": round(
                self.performance_metrics.average_profit_per_trade, 2
            ),
            "largest_win": round(self.performance_metrics.largest_win, 2),
            "largest_loss": round(self.performance_metrics.largest_loss, 2),
            "max_consecutive_wins": self.performance_metrics.max_consecutive_wins,
            "max_consecutive_losses": self.performance_metrics.max_consecutive_losses,
            # 手数料効率
            "fee_to_profit_ratio": round(
                self.performance_metrics.fee_to_profit_ratio, 4
            ),
            "net_profit_margin": round(self.performance_metrics.net_profit_margin, 2),
            # 時間効率
            "trades_per_day": round(self.performance_metrics.trades_per_day, 2),
            "active_trading_days": self.performance_metrics.active_trading_days,
            "average_trade_duration_minutes": round(
                self.performance_metrics.average_trade_duration, 2
            ),
            # 最近のパフォーマンス
            "recent_24h": self._get_recent_performance(24),
            "recent_7d": self._get_recent_performance(24 * 7),
            "recent_30d": self._get_recent_performance(24 * 30),
            # システム情報
            "total_data_files": len(list(self.results_dir.glob("*.csv")))
            + len(list(self.results_dir.glob("*.json"))),
            "last_trade_time": self._get_last_trade_time(),
            "system_uptime_hours": self._calculate_system_uptime(),
        }

        with open(self.status_file, "w", encoding="utf-8") as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)

    def _get_recent_performance(self, hours: int) -> Dict[str, Any]:
        """指定時間内のパフォーマンス取得"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_trades = [
            t
            for t in self.trades
            if t.timestamp >= cutoff_time and t.status == "closed"
        ]

        if not recent_trades:
            return {"trades": 0, "net_profit": 0.0, "win_rate": 0.0}

        profits = [t.net_profit for t in recent_trades]
        wins = len([p for p in profits if p > 0])

        return {
            "trades": len(recent_trades),
            "net_profit": round(sum(profits), 2),
            "win_rate": round(wins / len(recent_trades), 4),
            "largest_win": round(max(profits), 2) if profits else 0.0,
            "largest_loss": round(min(profits), 2) if profits else 0.0,
        }

    def _get_last_trade_time(self) -> Optional[str]:
        """最後の取引時刻取得"""
        if self.trades:
            last_trade = max(self.trades, key=lambda t: t.timestamp)
            return last_trade.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        return None

    def _calculate_system_uptime(self) -> float:
        """システム稼働時間計算"""
        if self.trades:
            first_trade_time = min(self.trades, key=lambda t: t.timestamp).timestamp
            return (datetime.now() - first_trade_time).total_seconds() / 3600
        return 0.0

    def get_performance_summary(self) -> Dict[str, Any]:
        """パフォーマンス要約取得"""
        return {
            "metrics": asdict(self.performance_metrics),
            "daily_stats": {
                date: asdict(stats) for date, stats in self.daily_stats.items()
            },
            "recent_performance": {
                "24h": self._get_recent_performance(24),
                "7d": self._get_recent_performance(24 * 7),
                "30d": self._get_recent_performance(24 * 30),
            },
            "system_info": {
                "total_trades": len(self.trades),
                "open_trades": len([t for t in self.trades if t.status == "open"]),
                "last_updated": datetime.now().isoformat(),
            },
        }

    def generate_detailed_report(self) -> str:
        """詳細レポート生成"""
        report = []
        report.append("=" * 80)
        report.append("🎯 取引統計詳細レポート")
        report.append("=" * 80)
        report.append(f"📅 生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # 基本統計
        report.append("📊 基本統計:")
        report.append(f"   総取引数: {self.performance_metrics.total_trades:,}")
        report.append(f"   勝ち取引: {self.performance_metrics.winning_trades:,}")
        report.append(f"   負け取引: {self.performance_metrics.losing_trades:,}")
        report.append(f"   勝率: {self.performance_metrics.win_rate:.2%}")
        report.append("")

        # 損益統計
        report.append("💰 損益統計:")
        report.append(f"   総利益: {self.performance_metrics.total_profit:,.2f}円")
        report.append(f"   総手数料: {self.performance_metrics.total_fees:,.2f}円")
        report.append(f"   純利益: {self.performance_metrics.net_profit:,.2f}円")
        report.append(f"   ROI: {self.performance_metrics.roi:.2f}%")
        report.append("")

        # リスク指標
        report.append("⚠️ リスク指標:")
        report.append(
            f"   最大ドローダウン: {self.performance_metrics.max_drawdown:,.2f}円"
        )
        report.append(
            f"   現在ドローダウン: {self.performance_metrics.current_drawdown:,.2f}円"
        )
        report.append(f"   シャープレシオ: {self.performance_metrics.sharpe_ratio:.4f}")
        report.append(
            f"   ソルティノレシオ: {self.performance_metrics.sortino_ratio:.4f}"
        )
        report.append("")

        # 効率性指標
        report.append("⚡ 効率性指標:")
        report.append(
            f"   プロフィットファクター: {self.performance_metrics.profit_factor:.4f}"
        )
        report.append(f"   ペイオフレシオ: {self.performance_metrics.payoff_ratio:.4f}")
        report.append(
            f"   手数料効率: {self.performance_metrics.fee_to_profit_ratio:.4f}"
        )
        report.append("")

        # 最近のパフォーマンス
        recent_24h = self._get_recent_performance(24)
        recent_7d = self._get_recent_performance(24 * 7)
        report.append("🕒 最近のパフォーマンス:")
        report.append(
            f"   24時間: {recent_24h['trades']}取引, {recent_24h['net_profit']:,.2f}円"
        )
        report.append(
            f"   7日間: {recent_7d['trades']}取引, {recent_7d['net_profit']:,.2f}円"
        )
        report.append("")

        report.append("=" * 80)

        return "\n".join(report)


def main():
    """テスト実行"""
    # 統計管理システム初期化
    stats_manager = TradingStatisticsManager()

    # テスト取引追加
    trade1 = TradeRecord(
        trade_id="test_001",
        timestamp=datetime.now(),
        symbol="BTC/JPY",
        side="buy",
        entry_price=3000000.0,
        quantity=0.0001,
        entry_fee=150.0,
        strategy_type="ML_Strategy",
        confidence_score=0.8,
        market_conditions={"volatility": 0.02, "trend": "bullish"},
    )

    # 取引記録
    trade_id = stats_manager.record_trade(trade1)

    # 取引決済
    stats_manager.close_trade(trade_id, 3005000.0, 150.0)

    # レポート生成
    print(stats_manager.generate_detailed_report())


if __name__ == "__main__":
    main()

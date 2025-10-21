"""
損益計算エンジン - Phase 47.3実装

移動平均法による暗号資産損益計算（国税庁推奨方式）
"""

from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional

from .trade_history_recorder import TradeHistoryRecorder


class PnLCalculator:
    """
    損益計算エンジン

    移動平均法による暗号資産の損益計算を実行。
    国税庁推奨方式に準拠。
    """

    def __init__(self, trade_recorder: Optional[TradeHistoryRecorder] = None):
        """
        PnLCalculator初期化

        Args:
            trade_recorder: TradeHistoryRecorderインスタンス
        """
        self.trade_recorder = trade_recorder or TradeHistoryRecorder()

    def calculate_annual_pnl(self, year: int) -> Dict:
        """
        年間損益計算

        Args:
            year: 対象年（例: 2025）

        Returns:
            Dict: 年間損益データ
        """
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"

        trades = self.trade_recorder.get_trades(start_date=start_date, end_date=end_date)

        if not trades:
            return {
                "year": year,
                "total_pnl": 0.0,
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "max_profit": 0.0,
                "max_loss": 0.0,
                "monthly_summary": {},
            }

        # 移動平均法による損益計算
        inventory = 0.0  # 保有数量 (BTC)
        avg_cost = 0.0  # 平均取得単価 (円/BTC)
        total_pnl = 0.0
        winning_trades = 0
        losing_trades = 0
        max_profit = 0.0
        max_loss = 0.0

        monthly_pnl = defaultdict(float)
        monthly_trades = defaultdict(int)

        for trade in trades:
            month_key = trade["timestamp"][:7]  # YYYY-MM

            if trade["trade_type"] == "entry":
                # エントリー: 移動平均法で平均取得単価を更新
                amount = trade["amount"]
                price = trade["price"]
                fee = trade["fee"] or 0.0

                if inventory == 0:
                    # 新規購入
                    avg_cost = price + (fee / amount if amount > 0 else 0)
                else:
                    # 追加購入: 移動平均法
                    total_cost = (inventory * avg_cost) + (amount * price) + fee
                    inventory += amount
                    avg_cost = total_cost / inventory if inventory > 0 else 0

                inventory += amount

            elif trade["trade_type"] in ["exit", "tp", "sl"]:
                # エグジット: 損益確定
                amount = trade["amount"]
                price = trade["price"]
                fee = trade["fee"] or 0.0

                if inventory >= amount:
                    # 売却益 = (売却価格 - 平均取得単価) × 数量 - 手数料
                    pnl = (price - avg_cost) * amount - fee
                    total_pnl += pnl
                    inventory -= amount

                    # 統計更新
                    if pnl > 0:
                        winning_trades += 1
                        max_profit = max(max_profit, pnl)
                    else:
                        losing_trades += 1
                        max_loss = min(max_loss, pnl)

                    # 月別集計
                    monthly_pnl[month_key] += pnl
                    monthly_trades[month_key] += 1

        # 勝率計算
        total_exits = winning_trades + losing_trades
        win_rate = (winning_trades / total_exits * 100) if total_exits > 0 else 0.0

        # 月別サマリー生成
        monthly_summary = {}
        for month in sorted(monthly_pnl.keys()):
            monthly_summary[month] = {
                "pnl": monthly_pnl[month],
                "trades": monthly_trades[month],
            }

        return {
            "year": year,
            "total_pnl": total_pnl,
            "total_trades": len(trades),
            "entry_trades": sum(1 for t in trades if t["trade_type"] == "entry"),
            "exit_trades": sum(1 for t in trades if t["trade_type"] in ["exit", "tp", "sl"]),
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "max_profit": max_profit,
            "max_loss": max_loss,
            "remaining_inventory": inventory,
            "avg_cost": avg_cost,
            "monthly_summary": monthly_summary,
        }

    def calculate_monthly_summary(self, year: int, month: int) -> Dict:
        """
        月別サマリー計算

        Args:
            year: 対象年
            month: 対象月 (1-12)

        Returns:
            Dict: 月別サマリーデータ
        """
        start_date = f"{year}-{month:02d}-01"
        # 月末日の計算（簡易版）
        if month == 12:
            end_date = f"{year}-12-31"
        else:
            end_date = f"{year}-{month + 1:02d}-01"

        trades = self.trade_recorder.get_trades(start_date=start_date, end_date=end_date)

        total_pnl = sum(
            trade.get("pnl", 0.0) or 0.0
            for trade in trades
            if trade["trade_type"] in ["exit", "tp", "sl"]
        )

        return {
            "year": year,
            "month": month,
            "total_trades": len(trades),
            "entry_trades": sum(1 for t in trades if t["trade_type"] == "entry"),
            "exit_trades": sum(1 for t in trades if t["trade_type"] in ["exit", "tp", "sl"]),
            "total_pnl": total_pnl,
        }

    def get_top_profitable_trades(self, year: int, limit: int = 10) -> List[Dict]:
        """
        最も利益が大きかった取引を取得

        Args:
            year: 対象年
            limit: 取得件数

        Returns:
            List[Dict]: 取引リスト（利益降順）
        """
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"

        trades = self.trade_recorder.get_trades(start_date=start_date, end_date=end_date)

        # exit取引のみフィルター
        exit_trades = [
            t for t in trades if t["trade_type"] in ["exit", "tp", "sl"] and t.get("pnl")
        ]

        # 損益降順ソート
        exit_trades.sort(key=lambda t: t["pnl"], reverse=True)

        return exit_trades[:limit]

    def get_top_losing_trades(self, year: int, limit: int = 10) -> List[Dict]:
        """
        最も損失が大きかった取引を取得

        Args:
            year: 対象年
            limit: 取得件数

        Returns:
            List[Dict]: 取引リスト（損失昇順）
        """
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"

        trades = self.trade_recorder.get_trades(start_date=start_date, end_date=end_date)

        # exit取引のみフィルター
        exit_trades = [
            t for t in trades if t["trade_type"] in ["exit", "tp", "sl"] and t.get("pnl")
        ]

        # 損益昇順ソート
        exit_trades.sort(key=lambda t: t["pnl"])

        return exit_trades[:limit]

"""
週間レポート生成・Discord送信スクリプト - Phase 48.2実装

過去7日間の取引統計を集計し、損益曲線グラフを生成してDiscordに送信。
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib

matplotlib.use("Agg")  # ヘッドレス環境対応
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.logger import get_logger
from src.core.reporting.discord_notifier import DiscordManager
from tax.pnl_calculator import PnLCalculator
from tax.trade_history_recorder import TradeHistoryRecorder


class WeeklyReportGenerator:
    """
    週間レポート生成システム

    過去7日間の取引データから統計を計算し、Discord通知を送信。
    """

    def __init__(
        self,
        db_path: str = "tax/trade_history.db",
        discord_webhook_url: Optional[str] = None,
    ):
        """
        WeeklyReportGenerator初期化

        Args:
            db_path: TradeHistoryRecorderデータベースパス
            discord_webhook_url: Discord Webhook URL（None時は環境変数から取得）
        """
        self.logger = get_logger()
        self.recorder = TradeHistoryRecorder(db_path=db_path)
        self.calculator = PnLCalculator(db_path=db_path)
        self.discord = DiscordManager(webhook_url=discord_webhook_url)

        self.logger.info("📊 WeeklyReportGenerator初期化完了")

    def generate_and_send_report(self) -> bool:
        """
        週間レポート生成・Discord送信

        Returns:
            bool: 送信成功時True
        """
        try:
            self.logger.info("📈 週間レポート生成開始...")

            # 過去7日間のデータ取得
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)

            stats = self._calculate_weekly_stats(start_date, end_date)

            if stats["trade_count"] == 0:
                self.logger.warning("⚠️ 過去7日間に取引データがありません")
                return self._send_no_data_report()

            # 損益曲線グラフ生成
            chart_path = self._generate_pnl_chart(start_date, end_date, stats)

            # Discord送信
            success = self._send_discord_report(stats, chart_path)

            if success:
                self.logger.info("✅ 週間レポート送信完了")
            else:
                self.logger.error("❌ 週間レポート送信失敗")

            # 一時ファイル削除
            if chart_path and Path(chart_path).exists():
                Path(chart_path).unlink()

            return success

        except Exception as e:
            self.logger.error(f"❌ 週間レポート生成エラー: {e}", exc_info=True)
            return False

    def _calculate_weekly_stats(self, start_date: datetime, end_date: datetime) -> Dict:
        """
        週間統計計算

        Args:
            start_date: 開始日時
            end_date: 終了日時

        Returns:
            Dict: 統計データ
        """
        # 週間取引データ取得
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        trades = self.recorder.get_trades(start_date=start_str, end_date=end_str)

        # 累積損益取得（運用開始から現在まで）
        current_year = datetime.now().year
        annual_pnl = self.calculator.calculate_annual_pnl(current_year)
        cumulative_pnl = annual_pnl.get("total_pnl", 0.0)

        # 週間損益計算
        weekly_pnl = sum(
            trade.get("pnl", 0.0) or 0.0
            for trade in trades
            if trade["trade_type"] in ["exit", "tp", "sl"]
        )

        # 取引回数
        entry_count = len([t for t in trades if t["trade_type"] == "entry"])
        exit_count = len([t for t in trades if t["trade_type"] in ["exit", "tp", "sl"]])

        # 勝率計算
        winning_trades = [
            t
            for t in trades
            if t["trade_type"] in ["exit", "tp", "sl"] and (t.get("pnl", 0) or 0) > 0
        ]
        win_rate = len(winning_trades) / exit_count * 100 if exit_count > 0 else 0.0

        # 最大ドローダウン計算
        max_drawdown = self._calculate_max_drawdown(trades)

        # 日別損益データ（グラフ用）
        daily_pnl = self._calculate_daily_pnl(trades, start_date, end_date)

        return {
            "weekly_pnl": weekly_pnl,
            "cumulative_pnl": cumulative_pnl,
            "trade_count": len(trades),
            "entry_count": entry_count,
            "exit_count": exit_count,
            "win_rate": win_rate,
            "max_drawdown": max_drawdown,
            "daily_pnl": daily_pnl,
            "start_date": start_date,
            "end_date": end_date,
        }

    def _calculate_max_drawdown(self, trades: List[Dict]) -> float:
        """
        最大ドローダウン計算

        Args:
            trades: 取引リスト

        Returns:
            float: 最大ドローダウン（%）
        """
        if not trades:
            return 0.0

        # 累積損益曲線作成
        cumulative = 0.0
        peak = 0.0
        max_dd = 0.0

        for trade in sorted(trades, key=lambda t: t["timestamp"]):
            if trade["trade_type"] in ["exit", "tp", "sl"]:
                pnl = trade.get("pnl", 0.0) or 0.0
                cumulative += pnl

                # 最高値更新
                if cumulative > peak:
                    peak = cumulative

                # ドローダウン計算
                if peak > 0:
                    drawdown = (peak - cumulative) / abs(peak) * 100
                    max_dd = max(max_dd, drawdown)

        return max_dd

    def _calculate_daily_pnl(
        self, trades: List[Dict], start_date: datetime, end_date: datetime
    ) -> List[Dict]:
        """
        日別損益計算

        Args:
            trades: 取引リスト
            start_date: 開始日時
            end_date: 終了日時

        Returns:
            List[Dict]: 日別損益データ [{date, pnl, cumulative}, ...]
        """
        # 日付ごとに損益を集計
        daily_data = {}
        current_date = start_date.date()
        end_date_obj = end_date.date()

        # 全日付を初期化
        while current_date <= end_date_obj:
            daily_data[current_date] = {"pnl": 0.0, "cumulative": 0.0}
            current_date += timedelta(days=1)

        # 取引データを日別に集計
        for trade in trades:
            if trade["trade_type"] in ["exit", "tp", "sl"]:
                trade_date = datetime.fromisoformat(trade["timestamp"]).date()
                pnl = trade.get("pnl", 0.0) or 0.0
                if trade_date in daily_data:
                    daily_data[trade_date]["pnl"] += pnl

        # 累積損益計算
        cumulative = 0.0
        result = []
        for date in sorted(daily_data.keys()):
            cumulative += daily_data[date]["pnl"]
            result.append(
                {
                    "date": date,
                    "pnl": daily_data[date]["pnl"],
                    "cumulative": cumulative,
                }
            )

        return result

    def _generate_pnl_chart(
        self, start_date: datetime, end_date: datetime, stats: Dict
    ) -> Optional[str]:
        """
        損益曲線グラフ生成

        Args:
            start_date: 開始日時
            end_date: 終了日時
            stats: 統計データ

        Returns:
            Optional[str]: 生成されたPNGファイルパス（失敗時None）
        """
        try:
            daily_pnl = stats["daily_pnl"]

            if not daily_pnl:
                self.logger.warning("⚠️ グラフ生成: 日別データなし")
                return None

            # フォント設定（日本語対応）
            plt.rcParams["font.sans-serif"] = [
                "Hiragino Sans",
                "Yu Gothic",
                "Meirio",
                "Takao",
                "IPAexGothic",
                "IPAPGothic",
                "Noto Sans CJK JP",
            ]
            plt.rcParams["axes.unicode_minus"] = False

            # グラフ作成
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

            dates = [d["date"] for d in daily_pnl]
            daily_values = [d["pnl"] for d in daily_pnl]
            cumulative_values = [d["cumulative"] for d in daily_pnl]

            # 日別損益グラフ
            colors = ["green" if v >= 0 else "red" for v in daily_values]
            ax1.bar(dates, daily_values, color=colors, alpha=0.6, width=0.8)
            ax1.axhline(y=0, color="black", linestyle="-", linewidth=0.5)
            ax1.set_title("日別損益 (Daily P&L)", fontsize=14, fontweight="bold")
            ax1.set_ylabel("損益 (円)", fontsize=12)
            ax1.grid(True, alpha=0.3)
            ax1.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
            ax1.xaxis.set_major_locator(mdates.DayLocator())
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

            # 累積損益グラフ
            line_color = "green" if cumulative_values[-1] >= 0 else "red"
            ax2.plot(dates, cumulative_values, color=line_color, linewidth=2, marker="o")
            ax2.fill_between(dates, cumulative_values, 0, alpha=0.2, color=line_color)
            ax2.axhline(y=0, color="black", linestyle="-", linewidth=0.5)
            ax2.set_title("累積損益 (Cumulative P&L)", fontsize=14, fontweight="bold")
            ax2.set_xlabel("日付", fontsize=12)
            ax2.set_ylabel("累積損益 (円)", fontsize=12)
            ax2.grid(True, alpha=0.3)
            ax2.xaxis.set_major_formatter(mdates.DateFormatter("%m/%d"))
            ax2.xaxis.set_major_locator(mdates.DayLocator())
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)

            plt.tight_layout()

            # PNG保存
            output_path = "/tmp/weekly_pnl_curve.png"
            plt.savefig(output_path, dpi=150, bbox_inches="tight")
            plt.close()

            self.logger.info(f"📊 グラフ生成完了: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"❌ グラフ生成エラー: {e}", exc_info=True)
            return None

    def _send_discord_report(self, stats: Dict, chart_path: Optional[str]) -> bool:
        """
        Discord週間レポート送信

        Args:
            stats: 統計データ
            chart_path: グラフ画像パス

        Returns:
            bool: 送信成功時True
        """
        # タイトル・説明文
        title = "📊 週間レポート (Weekly Trading Report)"
        description = (
            f"**期間**: {stats['start_date'].strftime('%Y/%m/%d')} 〜 "
            f"{stats['end_date'].strftime('%Y/%m/%d')}"
        )

        # フィールド作成
        weekly_pnl = stats["weekly_pnl"]
        cumulative_pnl = stats["cumulative_pnl"]

        fields = [
            {
                "name": "📈 週間損益 (Weekly P&L)",
                "value": f"**{weekly_pnl:+,.0f}円**",
                "inline": True,
            },
            {
                "name": "💰 累積損益 (Cumulative P&L)",
                "value": f"**{cumulative_pnl:+,.0f}円**",
                "inline": True,
            },
            {
                "name": "📊 勝率 (Win Rate)",
                "value": f"**{stats['win_rate']:.1f}%**",
                "inline": True,
            },
            {
                "name": "🔢 取引回数 (Trades)",
                "value": (
                    f"エントリー: {stats['entry_count']}回\n" f"エグジット: {stats['exit_count']}回"
                ),
                "inline": True,
            },
            {
                "name": "📉 最大ドローダウン (Max DD)",
                "value": f"**{stats['max_drawdown']:.2f}%**",
                "inline": True,
            },
        ]

        # レベル判定（週間損益ベース）
        if weekly_pnl > 0:
            level = "info"
        elif weekly_pnl < 0:
            level = "warning"
        else:
            level = "info"

        # Discord送信
        return self.discord.send_webhook_with_file(
            title=title,
            description=description,
            fields=fields,
            level=level,
            file_path=chart_path,
        )

    def _send_no_data_report(self) -> bool:
        """
        データなし時のレポート送信

        Returns:
            bool: 送信成功時True
        """
        title = "📊 週間レポート (Weekly Trading Report)"
        description = "過去7日間に取引データがありませんでした。"

        return self.discord.send_webhook(
            title=title,
            description=description,
            level="info",
        )


def main():
    """週間レポート生成メインエントリーポイント"""
    import argparse

    parser = argparse.ArgumentParser(description="週間レポート生成・Discord送信")
    parser.add_argument(
        "--db-path",
        default="tax/trade_history.db",
        help="TradeHistoryRecorderデータベースパス",
    )
    parser.add_argument(
        "--discord-webhook-url",
        default=None,
        help="Discord Webhook URL（未指定時は環境変数DISCORD_WEBHOOK_URLを使用）",
    )

    args = parser.parse_args()

    generator = WeeklyReportGenerator(
        db_path=args.db_path,
        discord_webhook_url=args.discord_webhook_url,
    )

    success = generator.generate_and_send_report()

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()

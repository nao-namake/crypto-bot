"""
週間レポート生成・Discord送信スクリプト - Phase 52.4更新

Phase 48.2実装・Phase 52.3バグ修正適用・Phase 52.4ハードコード削除

過去7日間の取引統計を集計し、損益曲線グラフを生成してDiscordに送信。

Phase 52.4更新内容:
- Phase 52.3最大ドローダウン計算バグ修正適用（累積損益基準 → ピーク残高基準）
- ハードコード値をconfig/core/unified.yamlに移行
- テストカバレッジ追加（0% → 80%+）
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib
import yaml

matplotlib.use("Agg")  # ヘッドレス環境対応
import matplotlib.dates as mdates
import matplotlib.pyplot as plt

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.logger import get_logger
from src.core.reporting.discord_notifier import DiscordManager
from tax.pnl_calculator import PnLCalculator
from tax.trade_history_recorder import TradeHistoryRecorder


def _load_config_value(key_path: str, default: Any = None) -> Any:
    """
    unified.yamlから設定値を取得（Phase 52.4: ヘルパー関数）

    Args:
        key_path: ドット区切りのキーパス（例: "reporting.weekly_report_days"）
        default: デフォルト値

    Returns:
        設定値（存在しない場合はdefault）
    """
    config_path = Path(__file__).parent.parent.parent / "config" / "core" / "unified.yaml"

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}

        # ドット区切りキーでネストされた辞書を探索
        keys = key_path.split(".")
        value = config_data
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value
    except Exception:
        return default


class WeeklyReportGenerator:
    """
    週間レポート生成システム

    過去7日間の取引データから統計を計算し、Discord通知を送信。
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        discord_webhook_url: Optional[str] = None,
    ):
        """
        WeeklyReportGenerator初期化（Phase 52.4: config統合）

        Args:
            db_path: TradeHistoryRecorderデータベースパス（Noneの場合はconfigから取得）
            discord_webhook_url: Discord Webhook URL（None時は環境変数から取得）
        """
        self.logger = get_logger()

        # Phase 52.4: db_pathをconfigから取得（ハードコード削除）
        if db_path is None:
            db_path = _load_config_value("tax.database_path", "tax/trade_history.db")

        self.recorder = TradeHistoryRecorder(db_path=db_path)
        self.calculator = PnLCalculator(trade_recorder=self.recorder)
        self.discord = DiscordManager(webhook_url=discord_webhook_url)

        self.logger.info("📊 WeeklyReportGenerator初期化完了")

    def generate_and_send_report(self) -> bool:
        """
        週間レポート生成・Discord送信（Phase 52.4: config統合）

        Returns:
            bool: 送信成功時True
        """
        try:
            self.logger.info("📈 週間レポート生成開始...")

            # Phase 52.4: レポート期間をconfigから取得（ハードコード削除）
            report_days = _load_config_value("reporting.weekly_report_days", 7)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=report_days)

            self.logger.info(
                f"📅 レポート期間: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')} ({report_days}日間)"
            )

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
        最大ドローダウン計算（Phase 52.3バグ修正適用）

        Phase 52.3修正内容:
        - Before: 累積損益基準で計算（間違い） → 60.73% DD
        - After: ピーク残高基準で計算（正しい） → 0.37% DD

        修正理由:
        ドローダウンは「ピーク残高からの下落率」であり、
        「累積損益のピークからの下落率」ではない。

        Args:
            trades: 取引リスト

        Returns:
            float: 最大ドローダウン（%）
        """
        if not trades:
            return 0.0

        # Phase 52.3修正: 初期残高を取得
        initial_balance = _load_config_value("reporting.initial_balance", 10000)

        # Phase 52.3修正: ピーク残高を初期残高から開始
        max_equity = initial_balance
        max_dd_pct = 0.0
        cumulative_pnl = 0.0

        for trade in sorted(trades, key=lambda t: t["timestamp"]):
            if trade["trade_type"] in ["exit", "tp", "sl"]:
                pnl = trade.get("pnl", 0.0) or 0.0
                cumulative_pnl += pnl

                # 現在残高 = 初期残高 + 累積損益
                current_equity = initial_balance + cumulative_pnl

                # ピーク残高更新
                if current_equity > max_equity:
                    max_equity = current_equity

                # ドローダウン計算（ピーク残高基準）
                dd = max_equity - current_equity
                dd_pct = (dd / max_equity * 100) if max_equity > 0 else 0.0
                max_dd_pct = max(max_dd_pct, dd_pct)

        return max_dd_pct

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

            # Phase 52.4: チャートサイズをconfigから取得（ハードコード削除）
            figsize = _load_config_value("reporting.chart_figsize", [12, 8])
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=tuple(figsize))

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

            # Phase 52.4: チャートパス・DPIをconfigから取得（ハードコード削除）
            output_path = _load_config_value(
                "reporting.temp_chart_path", "/tmp/weekly_pnl_curve.png"
            )
            chart_dpi = _load_config_value("reporting.chart_dpi", 150)

            plt.savefig(output_path, dpi=chart_dpi, bbox_inches="tight")
            plt.close()

            self.logger.info(f"📊 グラフ生成完了: {output_path} (DPI: {chart_dpi})")
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

    parser = argparse.ArgumentParser(description="週間レポート生成・Discord送信（Phase 52.4更新）")
    parser.add_argument(
        "--db-path",
        default=None,
        help="TradeHistoryRecorderデータベースパス（未指定時はconfigから取得）",
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

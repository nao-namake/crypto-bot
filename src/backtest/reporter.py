"""
バックテストレポートシステム - Phase 11・CI/CD統合・24時間監視・段階的デプロイ対応

包括的なバックテスト結果のレポート生成機能。
CSV・HTML・Discord通知による多形式出力をサポート。

主要機能:
- CSV形式詳細レポート・GitHub Actions対応
- HTML可視化レポート・CI/CD品質ゲート対応
- Discord通知サマリー・24時間監視対応
- 比較分析レポート・段階的デプロイ対応
- パフォーマンス統計出力・CI/CD統合.
"""

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from ..core.logger import get_logger
from ..monitoring.discord import DiscordNotifier
from .engine import TradeRecord
from .evaluator import PerformanceMetrics


class BacktestReporter:
    """
    バックテストレポート生成システム

    バックテスト結果を様々な形式で出力し、
    分析・共有・記録保持を支援する。.
    """

    def __init__(self, output_dir: str = "reports/backtest"):
        self.logger = get_logger(__name__)

        # 出力ディレクトリ設定
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # サブディレクトリ作成
        (self.output_dir / "csv").mkdir(exist_ok=True)
        (self.output_dir / "html").mkdir(exist_ok=True)
        (self.output_dir / "json").mkdir(exist_ok=True)

        # Discord通知（オプション）
        try:
            self.discord_notifier = DiscordNotifier()
        except Exception as e:
            self.logger.debug(f"Discord通知無効: {e}")
            self.discord_notifier = None

        self.logger.info(f"BacktestReporter初期化完了: {self.output_dir}")

    async def generate_full_report(
        self,
        test_name: str,
        trade_records: List[TradeRecord],
        performance_metrics: PerformanceMetrics,
        equity_curve: List[tuple],
        market_data: Optional[pd.DataFrame] = None,
        strategy_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """
        包括的レポート生成

        Args:
            test_name: テスト名
            trade_records: 取引記録
            performance_metrics: パフォーマンス指標
            equity_curve: エクイティカーブ
            market_data: 市場データ（オプション）
            strategy_info: 戦略情報（オプション）

        Returns:
            生成されたファイルパスの辞書.
        """
        self.logger.info(f"包括的レポート生成開始: {test_name}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{test_name}_{timestamp}"

        generated_files = {}

        try:
            # 1. CSVレポート生成
            csv_files = await self._generate_csv_reports(
                base_filename, trade_records, performance_metrics, equity_curve
            )
            generated_files.update(csv_files)

            # 2. JSONサマリー生成
            json_file = await self._generate_json_summary(
                base_filename, performance_metrics, strategy_info
            )
            generated_files["json"] = json_file

            # 3. HTMLレポート生成
            html_file = await self._generate_html_report(
                base_filename,
                trade_records,
                performance_metrics,
                equity_curve,
                market_data,
            )
            generated_files["html"] = html_file

            # 4. Discord通知送信
            if self.discord_notifier:
                await self._send_discord_summary(test_name, performance_metrics, generated_files)

            self.logger.info(f"レポート生成完了: {len(generated_files)}ファイル")
            return generated_files

        except Exception as e:
            self.logger.error(f"レポート生成エラー: {e}")
            raise

    async def _generate_csv_reports(
        self,
        base_filename: str,
        trade_records: List[TradeRecord],
        performance_metrics: PerformanceMetrics,
        equity_curve: List[tuple],
    ) -> Dict[str, str]:
        """CSV形式レポート生成."""

        csv_files = {}

        # 1. 取引記録CSV
        if trade_records:
            trades_file = self.output_dir / "csv" / f"{base_filename}_trades.csv"

            with open(trades_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                # ヘッダー
                writer.writerow(
                    [
                        "Entry Time",
                        "Exit Time",
                        "Side",
                        "Entry Price",
                        "Exit Price",
                        "Amount",
                        "Profit JPY",
                        "Profit Rate",
                        "Duration Hours",
                        "Slippage",
                        "Commission",
                        "Stop Loss",
                        "Take Profit",
                        "Strategy Signal",
                        "ML Confidence",
                        "Risk Score",
                    ]
                )

                # データ行
                for trade in trade_records:
                    duration_hours = 0.0
                    if trade.exit_time and trade.entry_time:
                        duration_hours = (trade.exit_time - trade.entry_time).total_seconds() / 3600

                    writer.writerow(
                        [
                            trade.entry_time.strftime("%Y-%m-%d %H:%M:%S"),
                            (
                                trade.exit_time.strftime("%Y-%m-%d %H:%M:%S")
                                if trade.exit_time
                                else ""
                            ),
                            trade.side,
                            trade.entry_price,
                            trade.exit_price or "",
                            trade.amount,
                            trade.profit_jpy,
                            f"{trade.profit_rate:.4f}",
                            f"{duration_hours:.2f}",
                            trade.slippage,
                            trade.commission,
                            trade.stop_loss or "",
                            trade.take_profit or "",
                            trade.strategy_signal,
                            f"{trade.ml_confidence:.3f}",
                            f"{trade.risk_score:.3f}",
                        ]
                    )

            csv_files["trades"] = str(trades_file)

        # 2. エクイティカーブCSV
        if equity_curve:
            equity_file = self.output_dir / "csv" / f"{base_filename}_equity.csv"

            with open(equity_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Timestamp", "Equity"])

                for timestamp, equity in equity_curve:
                    writer.writerow(
                        [
                            timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                            f"{equity:.2f}",
                        ]
                    )

            csv_files["equity"] = str(equity_file)

        # 3. パフォーマンスサマリーCSV
        summary_file = self.output_dir / "csv" / f"{base_filename}_summary.csv"

        with open(summary_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Metric", "Value"])

            metrics_data = [
                ("Total Trades", performance_metrics.total_trades),
                ("Win Rate", f"{performance_metrics.win_rate:.2%}"),
                ("Total Return", f"{performance_metrics.total_return:.2%}"),
                (
                    "Annualized Return",
                    f"{performance_metrics.annualized_return:.2%}",
                ),
                ("CAGR", f"{performance_metrics.cagr:.2%}"),
                ("Max Drawdown", f"{performance_metrics.max_drawdown:.2%}"),
                ("Sharpe Ratio", f"{performance_metrics.sharpe_ratio:.3f}"),
                ("Sortino Ratio", f"{performance_metrics.sortino_ratio:.3f}"),
                ("Profit Factor", f"{performance_metrics.profit_factor:.3f}"),
                (
                    "Average Trade Duration",
                    f"{performance_metrics.average_trade_duration:.1f} hours",
                ),
                (
                    "Max Consecutive Wins",
                    performance_metrics.max_consecutive_wins,
                ),
                (
                    "Max Consecutive Losses",
                    performance_metrics.max_consecutive_losses,
                ),
                (
                    "Analysis Period",
                    f"{performance_metrics.analysis_period_days} days",
                ),
                (
                    "Start Date",
                    performance_metrics.start_date.strftime("%Y-%m-%d"),
                ),
                (
                    "End Date",
                    performance_metrics.end_date.strftime("%Y-%m-%d"),
                ),
            ]

            for metric, value in metrics_data:
                writer.writerow([metric, value])

        csv_files["summary"] = str(summary_file)

        return csv_files

    async def _generate_json_summary(
        self,
        base_filename: str,
        performance_metrics: PerformanceMetrics,
        strategy_info: Optional[Dict[str, Any]],
    ) -> str:
        """JSON形式サマリー生成."""

        json_file = self.output_dir / "json" / f"{base_filename}_summary.json"

        # メトリクスをJSONシリアライズ可能な形式に変換
        summary_data = {
            "test_info": {
                "test_name": base_filename,
                "generated_at": datetime.now().isoformat(),
                "strategy_info": strategy_info or {},
            },
            "performance": {
                "basic_stats": {
                    "total_trades": performance_metrics.total_trades,
                    "winning_trades": performance_metrics.winning_trades,
                    "losing_trades": performance_metrics.losing_trades,
                    "win_rate": performance_metrics.win_rate,
                },
                "returns": {
                    "total_return": performance_metrics.total_return,
                    "annualized_return": performance_metrics.annualized_return,
                    "cagr": performance_metrics.cagr,
                    "total_profit": performance_metrics.total_profit,
                    "average_profit": performance_metrics.average_profit,
                },
                "risk_metrics": {
                    "max_drawdown": performance_metrics.max_drawdown,
                    "max_drawdown_duration": performance_metrics.max_drawdown_duration,
                    "volatility": performance_metrics.volatility,
                    "sharpe_ratio": performance_metrics.sharpe_ratio,
                    "sortino_ratio": performance_metrics.sortino_ratio,
                },
                "trade_metrics": {
                    "profit_factor": performance_metrics.profit_factor,
                    "average_trade_duration": performance_metrics.average_trade_duration,
                    "max_consecutive_wins": performance_metrics.max_consecutive_wins,
                    "max_consecutive_losses": performance_metrics.max_consecutive_losses,
                },
            },
            "analysis_period": {
                "start_date": performance_metrics.start_date.isoformat(),
                "end_date": performance_metrics.end_date.isoformat(),
                "period_days": performance_metrics.analysis_period_days,
            },
            "detailed_stats": {
                "trade_distribution": performance_metrics.trade_distribution,
                "monthly_returns": performance_metrics.monthly_returns,
                "drawdown_periods_count": len(performance_metrics.drawdown_periods),
            },
        }

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)

        return str(json_file)

    async def _generate_html_report(
        self,
        base_filename: str,
        trade_records: List[TradeRecord],
        performance_metrics: PerformanceMetrics,
        equity_curve: List[tuple],
        market_data: Optional[pd.DataFrame],
    ) -> str:
        """HTML形式レポート生成."""

        html_file = self.output_dir / "html" / f"{base_filename}_report.html"

        # HTMLテンプレート（シンプル版）
        html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>バックテストレポート - {base_filename}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .metric-card {{ background: #f8f9fa; padding: 15px; border-radius: 6px; border-left: 4px solid #007bff; }}
        .metric-title {{ font-weight: bold; color: #333; margin-bottom: 5px; }}
        .metric-value {{ font-size: 1.5em; color: #007bff; }}
        .positive {{ color: #28a745; }}
        .negative {{ color: #dc3545; }}
        .section {{ margin-bottom: 30px; }}
        .section-title {{ font-size: 1.3em; font-weight: bold; margin-bottom: 15px; padding-bottom: 5px; border-bottom: 2px solid #007bff; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f8f9fa; font-weight: bold; }}
        .trade-profit {{ color: #28a745; }}
        .trade-loss {{ color: #dc3545; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 バックテストレポート</h1>
            <h2>{base_filename}</h2>
            <p>生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        </div>
        
        <div class="section">
            <div class="section-title">📊 パフォーマンス概要</div>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-title">総取引数</div>
                    <div class="metric-value">{performance_metrics.total_trades:,}回</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">勝率</div>
                    <div class="metric-value {'positive' if performance_metrics.win_rate >= 0.5 else 'negative'}">{performance_metrics.win_rate:.1%}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">総リターン</div>
                    <div class="metric-value {'positive' if performance_metrics.total_return >= 0 else 'negative'}">{performance_metrics.total_return:.2%}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">年率リターン</div>
                    <div class="metric-value {'positive' if performance_metrics.cagr >= 0 else 'negative'}">{performance_metrics.cagr:.2%}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">最大ドローダウン</div>
                    <div class="metric-value negative">{performance_metrics.max_drawdown:.2%}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">シャープレシオ</div>
                    <div class="metric-value {'positive' if performance_metrics.sharpe_ratio >= 1.0 else 'negative'}">{performance_metrics.sharpe_ratio:.3f}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">プロフィットファクター</div>
                    <div class="metric-value {'positive' if performance_metrics.profit_factor >= 1.0 else 'negative'}">{performance_metrics.profit_factor:.3f}</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">分析期間</div>
                    <div class="metric-value">{performance_metrics.analysis_period_days}日</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">📈 取引詳細</div>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-title">勝ち取引</div>
                    <div class="metric-value positive">{performance_metrics.winning_trades}回</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">負け取引</div>
                    <div class="metric-value negative">{performance_metrics.losing_trades}回</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">平均取引時間</div>
                    <div class="metric-value">{performance_metrics.average_trade_duration:.1f}時間</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">最大連勝</div>
                    <div class="metric-value positive">{performance_metrics.max_consecutive_wins}回</div>
                </div>
                <div class="metric-card">
                    <div class="metric-title">最大連敗</div>
                    <div class="metric-value negative">{performance_metrics.max_consecutive_losses}回</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">📋 最近の取引記録（最新10件）</div>
            <table>
                <thead>
                    <tr>
                        <th>エントリー時刻</th>
                        <th>方向</th>
                        <th>エントリー価格</th>
                        <th>エグジット価格</th>
                        <th>損益</th>
                        <th>損益率</th>
                        <th>取引時間</th>
                    </tr>
                </thead>
                <tbody>
        """

        # 最新10件の取引記録
        recent_trades = sorted(trade_records, key=lambda x: x.entry_time, reverse=True)[:10]
        for trade in recent_trades:
            duration_hours = 0.0
            if trade.exit_time and trade.entry_time:
                duration_hours = (trade.exit_time - trade.entry_time).total_seconds() / 3600

            profit_class = "trade-profit" if trade.profit_jpy >= 0 else "trade-loss"

            html_content += f"""
                    <tr>
                        <td>{trade.entry_time.strftime('%m/%d %H:%M')}</td>
                        <td>{trade.side.upper()}</td>
                        <td>¥{trade.entry_price:,.0f}</td>
                        <td>¥{trade.exit_price:,.0f}</td>
                        <td class="{profit_class}">¥{trade.profit_jpy:,.0f}</td>
                        <td class="{profit_class}">{trade.profit_rate:.2%}</td>
                        <td>{duration_hours:.1f}h</td>
                    </tr>
            """

        html_content += """
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <div class="section-title">📅 分析期間情報</div>
            <p><strong>開始日:</strong> {start_date}</p>
            <p><strong>終了日:</strong> {end_date}</p>
            <p><strong>分析期間:</strong> {period_days}日間</p>
        </div>
        
        <div style="text-align: center; margin-top: 40px; color: #666; font-size: 0.9em;">
            <p>🤖 Generated by Crypto Bot Phase 11 Backtest System・CI/CD統合・24時間監視・段階的デプロイ対応</p>
        </div>
    </div>
</body>
</html>
        """.format(
            start_date=performance_metrics.start_date.strftime("%Y年%m月%d日"),
            end_date=performance_metrics.end_date.strftime("%Y年%m月%d日"),
            period_days=performance_metrics.analysis_period_days,
        )

        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        return str(html_file)

    async def _send_discord_summary(
        self,
        test_name: str,
        performance_metrics: PerformanceMetrics,
        generated_files: Dict[str, str],
    ):
        """Discord通知サマリー送信."""

        if not self.discord_notifier:
            return

        try:
            # 基本情報
            win_rate_emoji = "📈" if performance_metrics.win_rate >= 0.55 else "📉"
            return_emoji = "🟢" if performance_metrics.total_return >= 0 else "🔴"

            message = f"""
🚀 **バックテストレポート完了**

**📊 テスト名:** `{test_name}`
**📅 期間:** {performance_metrics.analysis_period_days}日間 ({performance_metrics.start_date.strftime('%Y/%m/%d')} - {performance_metrics.end_date.strftime('%Y/%m/%d')})

**💯 主要指標:**
{win_rate_emoji} **勝率:** {performance_metrics.win_rate:.1%} ({performance_metrics.winning_trades}/{performance_metrics.total_trades}勝)
{return_emoji} **総リターン:** {performance_metrics.total_return:.2%}
📊 **年率リターン (CAGR):** {performance_metrics.cagr:.2%}
⚠️ **最大ドローダウン:** {performance_metrics.max_drawdown:.2%}
⚡ **シャープレシオ:** {performance_metrics.sharpe_ratio:.3f}

**📁 生成ファイル数:** {len(generated_files)}個.
            """.strip()

            await self.discord_notifier.send_info(message)

        except Exception as e:
            self.logger.warning(f"Discord通知送信エラー: {e}")

    async def compare_backtests(
        self,
        test_results: List[Dict[str, Any]],
        comparison_name: str = "backtest_comparison",
    ) -> str:
        """複数バックテスト結果の比較レポート生成."""

        if len(test_results) < 2:
            raise ValueError("比較には最低2つのテスト結果が必要です")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        comparison_file = self.output_dir / "html" / f"{comparison_name}_{timestamp}.html"

        # 比較HTMLテンプレート（簡略版）
        html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>バックテスト比較レポート</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .comparison-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        .comparison-table th, .comparison-table td {{ padding: 10px; text-align: center; border: 1px solid #ddd; }}
        .comparison-table th {{ background-color: #f8f9fa; }}
        .best-value {{ background-color: #d4edda; font-weight: bold; }}
    </style>
</head>
<body>
    <h1>📊 バックテスト比較レポート</h1>
    <p>生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
    
    <table class="comparison-table">
        <thead>
            <tr>
                <th>指標</th>
        """

        # テスト名ヘッダー
        for i, result in enumerate(test_results):
            test_name = result.get("test_name", f"Test {i+1}")
            html_content += f"<th>{test_name}</th>"

        html_content += """
            </tr>
        </thead>
        <tbody>.
        """

        # 比較指標
        comparison_metrics = [
            ("総取引数", "total_trades", False),
            ("勝率", "win_rate", True, "%"),
            ("総リターン", "total_return", True, "%"),
            ("年率リターン", "cagr", True, "%"),
            ("最大ドローダウン", "max_drawdown", False, "%"),  # 低い方が良い
            ("シャープレシオ", "sharpe_ratio", True),
            ("プロフィットファクター", "profit_factor", True),
        ]

        for (
            metric_name,
            metric_key,
            higher_is_better,
            *format_args,
        ) in comparison_metrics:
            html_content += f"<tr><td><strong>{metric_name}</strong></td>"

            values = []
            for result in test_results:
                metrics = result.get("performance_metrics")
                if metrics and hasattr(metrics, metric_key):
                    values.append(getattr(metrics, metric_key))
                else:
                    values.append(0.0)

            # 最良値を特定
            if higher_is_better:
                best_value = max(values) if values else 0.0
            else:
                best_value = min(values) if values else 0.0

            # 値を表示
            for value in values:
                is_best = (value == best_value) and (len(set(values)) > 1)
                css_class = ' class="best-value"' if is_best else ""

                if format_args and format_args[0] == "%":
                    formatted_value = f"{value:.2%}"
                else:
                    formatted_value = f"{value:.3f}" if isinstance(value, float) else str(value)

                html_content += f"<td{css_class}>{formatted_value}</td>"

            html_content += "</tr>"

        html_content += """
        </tbody>
    </table>
    
    <p><em>🟢 緑色のセルは最良値を示しています</em></p>
</body>
</html>.
        """

        with open(comparison_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        self.logger.info(f"比較レポート生成完了: {comparison_file}")
        return str(comparison_file)

#!/usr/bin/env python3
"""
Phase 12-2: 取引成果ダッシュボード（可視化・レポート生成）

リアルタイム取引統計・パフォーマンス指標・HTMLレポート生成システム。
実データ収集・A/Bテスト結果の可視化とDiscord通知統合。

機能:
- HTMLダッシュボード生成
- 取引統計可視化
- パフォーマンス推移分析
- Discord通知連携
- A/Bテスト結果統合表示
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

# base_analyzer.py活用
sys.path.append(str(Path(__file__).parent.parent / "analytics"))
from base_analyzer import BaseAnalyzer

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TradingDashboard(BaseAnalyzer):
    """取引成果ダッシュボードメインクラス（Phase 12-2版・base_analyzer.py活用）"""
    
    def __init__(
        self, 
        data_dir: str = "logs", 
        output_dir: str = "dashboard",
        project_id: str = "my-crypto-bot-project",
        service_name: str = "crypto-bot-service",
        region: str = "asia-northeast1"
    ):
        # base_analyzer.py初期化
        super().__init__(project_id, service_name, region)
        
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        
        # データ格納
        self.trading_data = []
        self.daily_stats = []
        self.ab_test_results = []
        self.performance_metrics = {}
        
        logger.info("TradingDashboard初期化完了（base_analyzer.py活用版）")

    def load_data_collection_results(self) -> bool:
        """データ収集結果を読み込み"""
        logger.info("データ収集結果読み込み開始")
        
        try:
            # 最新のデータ収集結果を検索
            data_collection_dir = self.data_dir / "data_collection"
            if not data_collection_dir.exists():
                logger.warning("データ収集ディレクトリが見つかりません")
                return False
            
            # 取引データCSV
            trade_files = list(data_collection_dir.glob("trades_*.csv"))
            if trade_files:
                latest_trade_file = max(trade_files, key=lambda f: f.stat().st_mtime)
                try:
                    df = pd.read_csv(latest_trade_file)
                    self.trading_data = df.to_dict('records')
                    logger.info(f"取引データ読み込み: {len(self.trading_data)}件")
                except Exception as e:
                    logger.warning(f"取引データ読み込み失敗: {e}")
            
            # 日次統計CSV
            stats_files = list(data_collection_dir.glob("daily_stats_*.csv"))
            if stats_files:
                latest_stats_file = max(stats_files, key=lambda f: f.stat().st_mtime)
                try:
                    df = pd.read_csv(latest_stats_file)
                    self.daily_stats = df.to_dict('records')
                    logger.info(f"日次統計読み込み: {len(self.daily_stats)}件")
                except Exception as e:
                    logger.warning(f"日次統計読み込み失敗: {e}")
            
            # パフォーマンス指標JSON
            perf_files = list(data_collection_dir.glob("performance_metrics_*.json"))
            if perf_files:
                latest_perf_file = max(perf_files, key=lambda f: f.stat().st_mtime)
                try:
                    with open(latest_perf_file) as f:
                        self.performance_metrics = json.load(f)
                    logger.info("パフォーマンス指標読み込み完了")
                except Exception as e:
                    logger.warning(f"パフォーマンス指標読み込み失敗: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"データ読み込みエラー: {e}")
            return False

    def load_ab_test_results(self) -> bool:
        """A/Bテスト結果を読み込み"""
        logger.info("A/Bテスト結果読み込み開始")
        
        try:
            ab_testing_dir = self.data_dir / "ab_testing"
            if not ab_testing_dir.exists():
                logger.warning("A/Bテストディレクトリが見つかりません")
                return False
            
            ab_test_files = list(ab_testing_dir.glob("ab_test_*.json"))
            for file in ab_test_files:
                try:
                    with open(file) as f:
                        result = json.load(f)
                        self.ab_test_results.append(result)
                except Exception as e:
                    logger.warning(f"A/Bテスト結果読み込み失敗 {file}: {e}")
            
            logger.info(f"A/Bテスト結果読み込み: {len(self.ab_test_results)}件")
            return True
            
        except Exception as e:
            logger.error(f"A/Bテスト結果読み込みエラー: {e}")
            return False

    def generate_trading_summary(self) -> Dict:
        """取引サマリー生成"""
        logger.info("取引サマリー生成")
        
        summary = {
            "last_updated": datetime.now().isoformat(),
            "data_period": "Unknown",
            "total_signals": 0,
            "signal_breakdown": {"buy": 0, "sell": 0, "hold": 0},
            "avg_confidence": 0.0,
            "high_confidence_signals": 0,
            "signal_frequency_per_hour": 0.0,
            "daily_stats_available": len(self.daily_stats),
            "trading_days": 0
        }
        
        if self.trading_data:
            summary["total_signals"] = len(self.trading_data)
            
            # シグナル分布
            for trade in self.trading_data:
                side = trade.get("side", "unknown")
                if side in summary["signal_breakdown"]:
                    summary["signal_breakdown"][side] += 1
            
            # 信頼度分析
            confidences = [float(trade.get("signal_confidence", 0)) for trade in self.trading_data if trade.get("signal_confidence")]
            if confidences:
                summary["avg_confidence"] = sum(confidences) / len(confidences)
                summary["high_confidence_signals"] = len([c for c in confidences if c > 0.7])
        
        # パフォーマンス指標から追加情報
        if self.performance_metrics:
            perf = self.performance_metrics.get("performance_metrics", {})
            summary["signal_frequency_per_hour"] = perf.get("signals_per_hour", 0.0)
            summary["data_period"] = f"{perf.get('analysis_period_hours', 0)}時間"
        
        # 日次統計から取引日数
        summary["trading_days"] = len(self.daily_stats)
        
        return summary

    def generate_daily_stats_chart_data(self) -> Dict:
        """日次統計チャートデータ生成"""
        if not self.daily_stats:
            return {"dates": [], "signals": [], "frequencies": []}
        
        # 日付順ソート
        sorted_stats = sorted(self.daily_stats, key=lambda x: x.get("date", ""))
        
        dates = [stat.get("date", "") for stat in sorted_stats]
        signals = [stat.get("total_signals", 0) for stat in sorted_stats]
        frequencies = [stat.get("signal_frequency", 0.0) for stat in sorted_stats]
        
        return {
            "dates": dates,
            "signals": signals,
            "frequencies": frequencies
        }

    def generate_ab_test_summary(self) -> List[Dict]:
        """A/Bテストサマリー生成"""
        summaries = []
        
        for result in self.ab_test_results:
            try:
                summary = {
                    "test_name": result.get("test_name", "Unknown"),
                    "winner": result.get("winner", "Unknown"),
                    "improvement_percentage": result.get("improvement_percentage", 0.0),
                    "confidence_level": result.get("confidence_level", 0.0),
                    "practical_significance": result.get("practical_significance", False),
                    "variant_a_signals": result.get("variant_a", {}).get("total_signals", 0),
                    "variant_b_signals": result.get("variant_b", {}).get("total_signals", 0),
                    "recommendation": result.get("recommendation", "")
                }
                summaries.append(summary)
            except Exception as e:
                logger.warning(f"A/Bテスト結果解析失敗: {e}")
        
        return summaries

    def generate_html_dashboard(self) -> str:
        """HTMLダッシュボード生成"""
        logger.info("HTMLダッシュボード生成開始")
        
        # データ準備
        trading_summary = self.generate_trading_summary()
        chart_data = self.generate_daily_stats_chart_data()
        ab_test_summaries = self.generate_ab_test_summary()
        
        # HTMLテンプレート
        html_content = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Phase 12-2 取引成果ダッシュボード</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: 'Helvetica Neue', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f7fa;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .stat-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin: 10px 0;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .chart-container {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .chart-title {{
            font-size: 1.5em;
            margin-bottom: 20px;
            color: #333;
        }}
        .ab-test-section {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .ab-test-item {{
            border-left: 4px solid #667eea;
            padding: 15px;
            margin: 15px 0;
            background: #f8f9fa;
            border-radius: 0 5px 5px 0;
        }}
        .winner {{
            font-weight: bold;
            color: #28a745;
        }}
        .improvement {{
            color: #17a2b8;
            font-weight: bold;
        }}
        .signal-breakdown {{
            display: flex;
            justify-content: space-around;
            margin: 20px 0;
        }}
        .signal-type {{
            text-align: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            flex: 1;
            margin: 0 5px;
        }}
        .signal-type.buy {{ border-left: 4px solid #28a745; }}
        .signal-type.sell {{ border-left: 4px solid #dc3545; }}
        .signal-type.hold {{ border-left: 4px solid #ffc107; }}
        .footer {{
            text-align: center;
            margin-top: 50px;
            padding: 20px;
            color: #666;
            border-top: 1px solid #eee;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- ヘッダー -->
        <div class="header">
            <h1>🚀 Phase 12-2 取引成果ダッシュボード</h1>
            <p>最終更新: {trading_summary['last_updated'][:19]} | データ期間: {trading_summary['data_period']}</p>
        </div>

        <!-- 統計サマリー -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">総シグナル数</div>
                <div class="stat-value">{trading_summary['total_signals']:,}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">シグナル頻度</div>
                <div class="stat-value">{trading_summary['signal_frequency_per_hour']:.1f}/h</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">平均信頼度</div>
                <div class="stat-value">{trading_summary['avg_confidence']:.3f}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">高信頼シグナル</div>
                <div class="stat-value">{trading_summary['high_confidence_signals']}</div>
            </div>
        </div>

        <!-- シグナル種別分布 -->
        <div class="chart-container">
            <h2 class="chart-title">📊 シグナル種別分布</h2>
            <div class="signal-breakdown">
                <div class="signal-type buy">
                    <div style="font-size: 1.8em; font-weight: bold; color: #28a745;">
                        {trading_summary['signal_breakdown']['buy']}
                    </div>
                    <div>BUY シグナル</div>
                </div>
                <div class="signal-type sell">
                    <div style="font-size: 1.8em; font-weight: bold; color: #dc3545;">
                        {trading_summary['signal_breakdown']['sell']}
                    </div>
                    <div>SELL シグナル</div>
                </div>
                <div class="signal-type hold">
                    <div style="font-size: 1.8em; font-weight: bold; color: #ffc107;">
                        {trading_summary['signal_breakdown']['hold']}
                    </div>
                    <div>HOLD シグナル</div>
                </div>
            </div>
        </div>

        <!-- 日次推移チャート -->
        <div class="chart-container">
            <h2 class="chart-title">📈 日次シグナル推移</h2>
            <canvas id="dailyChart" width="400" height="200"></canvas>
        </div>

        <!-- A/Bテスト結果 -->
        <div class="ab-test-section">
            <h2 class="chart-title">🧪 A/Bテスト結果</h2>
            {self._generate_ab_test_html(ab_test_summaries)}
        </div>

        <!-- システム情報 -->
        <div class="chart-container">
            <h2 class="chart-title">ℹ️ システム情報</h2>
            <p><strong>データ収集期間:</strong> {trading_summary['data_period']}</p>
            <p><strong>分析対象日数:</strong> {trading_summary['trading_days']}日</p>
            <p><strong>A/Bテスト実行数:</strong> {len(ab_test_summaries)}件</p>
            <p><strong>Phase 12-2機能:</strong> 実データ収集・A/Bテスト・ダッシュボード可視化</p>
        </div>

        <div class="footer">
            <p>Phase 12-2: レガジー知見活用・シンプル性と性能のバランス重視 | 
               Generated by Claude Code Trading Dashboard</p>
        </div>
    </div>

    <script>
        // 日次チャート描画
        const ctx = document.getElementById('dailyChart').getContext('2d');
        const dailyChart = new Chart(ctx, {{
            type: 'line',
            data: {{
                labels: {json.dumps(chart_data['dates'])},
                datasets: [{{
                    label: 'シグナル数',
                    data: {json.dumps(chart_data['signals'])},
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        display: true,
                        position: 'top'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            stepSize: 1
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
        
        # HTMLファイル保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_file = self.output_dir / f"trading_dashboard_{timestamp}.html"
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTMLダッシュボード生成完了: {html_file}")
        return str(html_file)

    def _generate_ab_test_html(self, ab_test_summaries: List[Dict]) -> str:
        """A/BテストHTML部分生成"""
        if not ab_test_summaries:
            return "<p>A/Bテスト結果がありません。</p>"
        
        html_parts = []
        
        for i, test in enumerate(ab_test_summaries, 1):
            winner_class = "winner" if test['winner'] != "No significant difference" else ""
            improvement_text = f"{test['improvement_percentage']:+.1f}%" if test['improvement_percentage'] != 0 else "0%"
            
            html_parts.append(f"""
            <div class="ab-test-item">
                <h4>テスト {i}: {test['test_name']}</h4>
                <p><strong>勝者:</strong> <span class="{winner_class}">{test['winner']}</span></p>
                <p><strong>改善率:</strong> <span class="improvement">{improvement_text}</span></p>
                <p><strong>信頼度:</strong> {test['confidence_level']:.0f}%</p>
                <p><strong>バリアントA:</strong> {test['variant_a_signals']}シグナル | 
                   <strong>バリアントB:</strong> {test['variant_b_signals']}シグナル</p>
                <p><strong>推奨:</strong> {test['recommendation']}</p>
            </div>
            """)
        
        return "".join(html_parts)

    def generate_discord_notification(self, summary: Dict) -> str:
        """Discord通知メッセージ生成"""
        message = f"""
🚀 **Phase 12-2 取引成果レポート**

📊 **基本統計**
• 総シグナル数: {summary['total_signals']:,}
• シグナル頻度: {summary['signal_frequency_per_hour']:.1f}/時間
• 平均信頼度: {summary['avg_confidence']:.3f}
• 高信頼シグナル: {summary['high_confidence_signals']}件

📈 **シグナル分布**
• BUY: {summary['signal_breakdown']['buy']}
• SELL: {summary['signal_breakdown']['sell']}
• HOLD: {summary['signal_breakdown']['hold']}

ℹ️ **データ期間**: {summary['data_period']} | **分析日数**: {summary['trading_days']}日

🎯 **Phase 12-2**: 実データ収集・A/Bテスト・ダッシュボード稼働中
"""
        return message.strip()

    def run_dashboard_generation(self) -> Tuple[str, str]:
        """ダッシュボード生成実行"""
        logger.info("Phase 12-2ダッシュボード生成開始")
        
        try:
            # データ読み込み
            self.load_data_collection_results()
            self.load_ab_test_results()
            
            # サマリー生成
            summary = self.generate_trading_summary()
            
            # HTMLダッシュボード生成
            html_file = self.generate_html_dashboard()
            
            # Discord通知メッセージ生成
            discord_message = self.generate_discord_notification(summary)
            
            logger.info("ダッシュボード生成完了")
            return html_file, discord_message
            
        except Exception as e:
            logger.error(f"ダッシュボード生成エラー: {e}")
            raise
    
    # ===== base_analyzer.py抽象メソッド実装 =====
    
    def run_analysis(self, **kwargs) -> Dict:
        """ダッシュボード分析実行（base_analyzer.py要求）"""
        try:
            html_file, discord_message = self.run_dashboard_generation()
            summary = self.generate_trading_summary()
            
            return {
                "timestamp": datetime.now().isoformat(),
                "analysis_type": "dashboard_generation",
                "html_file": html_file,
                "discord_message": discord_message[:200] + "..." if len(discord_message) > 200 else discord_message,
                "trading_summary": summary,
                "success": True
            }
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "analysis_type": "dashboard_generation",
                "error": str(e),
                "success": False
            }
    
    def generate_report(self, analysis_result: Dict) -> str:
        """ダッシュボードレポート生成（base_analyzer.py要求）"""
        if analysis_result.get("success"):
            summary = analysis_result.get("trading_summary", {})
            return f"""
=== Phase 12-2 ダッシュボードレポート ===
生成日時: {analysis_result.get('timestamp', '')}
HTMLファイル: {analysis_result.get('html_file', '')}
総シグナル数: {summary.get('total_signals', 0)}
シグナル頻度: {summary.get('signal_frequency_per_hour', 0):.1f}/時間
平均信頼度: {summary.get('avg_confidence', 0):.3f}
取引日数: {summary.get('trading_days', 0)}日
======================================"""
        else:
            return f"ダッシュボード生成失敗: {analysis_result.get('error', 'Unknown error')}"


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="Phase 12-2 取引成果ダッシュボード")
    parser.add_argument("--data-dir", default="logs",
                       help="データディレクトリ")
    parser.add_argument("--output-dir", default="dashboard",
                       help="出力ディレクトリ")
    parser.add_argument("--discord", action="store_true",
                       help="Discord通知メッセージ表示")
    
    args = parser.parse_args()
    
    try:
        dashboard = TradingDashboard(
            data_dir=args.data_dir,
            output_dir=args.output_dir
        )
        
        html_file, discord_message = dashboard.run_dashboard_generation()
        
        print("=" * 60)
        print("🎉 Phase 12-2 ダッシュボード生成完了！")
        print("=" * 60)
        print(f"📋 HTMLダッシュボード: {html_file}")
        print(f"📁 出力ディレクトリ: {args.output_dir}")
        
        if args.discord:
            print("\\n📢 Discord通知メッセージ:")
            print("-" * 40)
            print(discord_message)
        
        print("\\n🚀 ダッシュボードをブラウザで開いて確認してください！")
        
    except Exception as e:
        logger.error(f"ダッシュボード生成失敗: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
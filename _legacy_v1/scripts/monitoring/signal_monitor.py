#!/usr/bin/env python
"""
定期シグナル監視スクリプト

Phase 2-2: ChatGPT提案採用
1時間毎にシグナル生成状況を監視し、異常パターンを検出
デプロイ前のローカル検証でエラーを早期発見
"""

import csv
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SignalMonitor:
    """シグナル生成状況を監視するクラス"""

    def __init__(
        self,
        csv_path: str = "logs/trading_signals.csv",
        report_dir: str = "logs/monitoring_reports",
    ):
        self.csv_path = Path(csv_path)
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(exist_ok=True, parents=True)

        # 監視閾値
        self.thresholds = {
            "max_silence_hours": 1.0,  # 1時間以上シグナルなし→警告
            "max_consecutive_holds": 30,  # 30回連続HOLD→警告
            "min_confidence": 0.35,  # confidence常に0.35未満→警告
            "max_weak_signal_ratio": 0.8,  # weak_signal比率80%超→警告
            "min_signal_interval_seconds": 30,  # 最小シグナル間隔
        }

        # 統計情報
        self.stats = {
            "total_signals": 0,
            "last_signal_time": None,
            "signal_types": {},
            "confidence_values": [],
            "anomalies": [],
            "health_score": 100,
        }

    def load_signals(self, hours: int = 24) -> pd.DataFrame:
        """指定時間分のシグナルデータを読み込み"""
        if not self.csv_path.exists():
            logger.warning(f"Signal CSV not found: {self.csv_path}")
            return pd.DataFrame()

        try:
            # CSVを読み込み
            df = pd.read_csv(self.csv_path)

            if df.empty:
                logger.warning("Signal CSV is empty")
                return df

            # タイムスタンプをdatetime型に変換
            df["timestamp"] = pd.to_datetime(df["timestamp"])

            # 指定時間分のデータをフィルタ
            cutoff_time = datetime.now() - timedelta(hours=hours)
            df = df[df["timestamp"] >= cutoff_time]

            # 時間順にソート
            df = df.sort_values("timestamp")

            logger.info(f"Loaded {len(df)} signals from last {hours} hours")
            return df

        except Exception as e:
            logger.error(f"Failed to load signals: {e}")
            return pd.DataFrame()

    def check_signal_silence(self, df: pd.DataFrame) -> Optional[Dict]:
        """シグナル生成が停止していないかチェック"""
        if df.empty:
            return {
                "type": "NO_SIGNALS",
                "severity": "CRITICAL",
                "message": "No signals found in CSV",
                "duration_hours": 24,
            }

        last_signal_time = df["timestamp"].max()
        current_time = datetime.now()

        # タイムゾーン調整（pandasのTimestamp用）
        if hasattr(last_signal_time, "tz") and last_signal_time.tz is None:
            last_signal_time = last_signal_time.tz_localize("UTC")
        if not hasattr(current_time, "tz"):
            # datetimeオブジェクトの場合
            import pytz

            current_time = (
                pytz.UTC.localize(current_time)
                if current_time.tzinfo is None
                else current_time
            )

        silence_duration = (current_time - last_signal_time).total_seconds() / 3600

        if silence_duration > self.thresholds["max_silence_hours"]:
            return {
                "type": "SIGNAL_SILENCE",
                "severity": "WARNING",
                "message": f"No signals for {silence_duration:.1f} hours",
                "last_signal": str(last_signal_time),
                "duration_hours": silence_duration,
            }

        self.stats["last_signal_time"] = last_signal_time
        return None

    def check_consecutive_patterns(self, df: pd.DataFrame) -> List[Dict]:
        """連続する同一シグナルパターンを検出"""
        anomalies = []

        if df.empty:
            return anomalies

        # 連続HOLDチェック
        consecutive_count = 0
        last_signal = None

        for _, row in df.iterrows():
            signal_type = row.get("signal_type", "")

            if signal_type == last_signal:
                consecutive_count += 1
            else:
                # パターンが変わった時点でチェック
                if (
                    last_signal == "HOLD"
                    and consecutive_count > self.thresholds["max_consecutive_holds"]
                ):
                    anomalies.append(
                        {
                            "type": "CONSECUTIVE_HOLDS",
                            "severity": "WARNING",
                            "message": f"{consecutive_count} consecutive HOLD signals",
                            "count": consecutive_count,
                        }
                    )
                consecutive_count = 1
                last_signal = signal_type

        # 最後のパターンもチェック
        if (
            last_signal == "HOLD"
            and consecutive_count > self.thresholds["max_consecutive_holds"]
        ):
            anomalies.append(
                {
                    "type": "CONSECUTIVE_HOLDS",
                    "severity": "WARNING",
                    "message": f"{consecutive_count} consecutive HOLD signals",
                    "count": consecutive_count,
                }
            )

        return anomalies

    def check_confidence_levels(self, df: pd.DataFrame) -> List[Dict]:
        """Confidence値の異常を検出"""
        anomalies = []

        if df.empty or "confidence" not in df.columns:
            return anomalies

        confidence_values = df["confidence"].dropna()

        if confidence_values.empty:
            return anomalies

        # 統計計算
        mean_confidence = confidence_values.mean()
        min_confidence = confidence_values.min()
        max_confidence = confidence_values.max()

        self.stats["confidence_values"] = {
            "mean": mean_confidence,
            "min": min_confidence,
            "max": max_confidence,
            "count": len(confidence_values),
        }

        # 常に低いconfidence
        if mean_confidence < self.thresholds["min_confidence"]:
            anomalies.append(
                {
                    "type": "LOW_CONFIDENCE",
                    "severity": "WARNING",
                    "message": f"Average confidence {mean_confidence:.3f} below threshold",
                    "mean": mean_confidence,
                    "threshold": self.thresholds["min_confidence"],
                }
            )

        # confidence値が全て同じ（モデル問題の可能性）
        if min_confidence == max_confidence:
            anomalies.append(
                {
                    "type": "STATIC_CONFIDENCE",
                    "severity": "ERROR",
                    "message": f"All confidence values are identical: {min_confidence:.3f}",
                    "value": min_confidence,
                }
            )

        return anomalies

    def check_signal_distribution(self, df: pd.DataFrame) -> List[Dict]:
        """シグナルタイプの分布を分析"""
        anomalies = []

        if df.empty or "signal_type" not in df.columns:
            return anomalies

        # シグナルタイプ別カウント
        signal_counts = df["signal_type"].value_counts()
        total_signals = len(df)

        self.stats["signal_types"] = signal_counts.to_dict()
        self.stats["total_signals"] = total_signals

        # weak_signal比率チェック
        weak_signals = signal_counts.get("WEAK_BUY", 0) + signal_counts.get(
            "WEAK_SELL", 0
        )
        weak_ratio = weak_signals / total_signals if total_signals > 0 else 0

        if weak_ratio > self.thresholds["max_weak_signal_ratio"]:
            anomalies.append(
                {
                    "type": "HIGH_WEAK_SIGNAL_RATIO",
                    "severity": "WARNING",
                    "message": f"Weak signal ratio {weak_ratio:.1%} exceeds threshold",
                    "ratio": weak_ratio,
                    "threshold": self.thresholds["max_weak_signal_ratio"],
                }
            )

        # エントリーシグナルが全くない
        entry_signals = signal_counts.get("BUY", 0) + signal_counts.get("SELL", 0)
        if total_signals > 100 and entry_signals == 0:
            anomalies.append(
                {
                    "type": "NO_ENTRY_SIGNALS",
                    "severity": "ERROR",
                    "message": "No BUY/SELL signals generated",
                    "total_signals": total_signals,
                }
            )

        return anomalies

    def check_price_data(self, df: pd.DataFrame) -> List[Dict]:
        """価格データの異常を検出"""
        anomalies = []

        if df.empty or "price" not in df.columns:
            return anomalies

        prices = df["price"].dropna()

        if prices.empty:
            return anomalies

        # 価格が変化していない（データ取得エラーの可能性）
        unique_prices = prices.nunique()
        if unique_prices == 1 and len(prices) > 10:
            anomalies.append(
                {
                    "type": "STATIC_PRICE",
                    "severity": "CRITICAL",
                    "message": f"Price has not changed ({prices.iloc[0]:.2f})",
                    "price": prices.iloc[0],
                    "count": len(prices),
                }
            )

        # 価格の急激な変動（スパイク）
        price_changes = prices.pct_change().dropna()
        if not price_changes.empty:
            max_change = price_changes.abs().max()
            if max_change > 0.1:  # 10%以上の変動
                anomalies.append(
                    {
                        "type": "PRICE_SPIKE",
                        "severity": "WARNING",
                        "message": f"Price spike detected: {max_change:.1%} change",
                        "max_change": max_change,
                    }
                )

        return anomalies

    def calculate_health_score(self, anomalies: List[Dict]) -> int:
        """システムの健全性スコアを計算（0-100）"""
        score = 100

        severity_penalties = {"CRITICAL": 30, "ERROR": 20, "WARNING": 10, "INFO": 5}

        for anomaly in anomalies:
            severity = anomaly.get("severity", "INFO")
            penalty = severity_penalties.get(severity, 0)
            score -= penalty

        return max(0, score)

    def generate_report(self, df: pd.DataFrame, anomalies: List[Dict]) -> Dict:
        """監視レポートを生成"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "period_hours": 24,
            "stats": self.stats,
            "anomalies": anomalies,
            "health_score": self.calculate_health_score(anomalies),
            "recommendations": self.generate_recommendations(anomalies),
        }

        # 時間帯別分析
        if not df.empty:
            df["hour"] = pd.to_datetime(df["timestamp"]).dt.hour
            hourly_counts = df.groupby("hour").size().to_dict()
            report["hourly_distribution"] = hourly_counts

        return report

    def generate_recommendations(self, anomalies: List[Dict]) -> List[str]:
        """異常に基づく推奨アクションを生成"""
        recommendations = []

        anomaly_types = {a["type"] for a in anomalies}

        if "NO_SIGNALS" in anomaly_types or "SIGNAL_SILENCE" in anomaly_types:
            recommendations.append("🚨 Check if trading system is running")
            recommendations.append("🔍 Verify data feed connection")
            recommendations.append("📊 Check model loading and initialization")

        if "LOW_CONFIDENCE" in anomaly_types:
            recommendations.append("🤖 Consider retraining the model")
            recommendations.append("📈 Check market conditions for unusual patterns")
            recommendations.append("🔧 Verify feature calculation pipeline")

        if "CONSECUTIVE_HOLDS" in anomaly_types:
            recommendations.append("⚙️ Review entry threshold settings")
            recommendations.append("📊 Check if confidence threshold is too high")

        if "STATIC_PRICE" in anomaly_types:
            recommendations.append("🌐 Check API connection to exchange")
            recommendations.append("🔄 Verify data fetching logic")

        if "NO_ENTRY_SIGNALS" in anomaly_types:
            recommendations.append("📉 Market may be in consolidation")
            recommendations.append("🎯 Consider adjusting strategy parameters")

        if not recommendations:
            recommendations.append("✅ System appears to be functioning normally")

        return recommendations

    def save_html_report(self, report: Dict) -> Path:
        """HTMLレポートを生成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_path = self.report_dir / f"signal_monitor_{timestamp}.html"

        # 健全性スコアに基づく色
        score = report["health_score"]
        if score >= 80:
            score_color = "green"
        elif score >= 60:
            score_color = "orange"
        else:
            score_color = "red"

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Signal Monitoring Report - {timestamp}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .header {{ background-color: #333; color: white; padding: 20px; border-radius: 5px; }}
        .score {{ font-size: 48px; color: {score_color}; font-weight: bold; }}
        .section {{ background-color: white; padding: 15px; margin: 15px 0; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .anomaly {{ padding: 10px; margin: 10px 0; border-left: 4px solid; }}
        .CRITICAL {{ border-color: red; background-color: #ffebee; }}
        .ERROR {{ border-color: orange; background-color: #fff3e0; }}
        .WARNING {{ border-color: yellow; background-color: #fffde7; }}
        .INFO {{ border-color: blue; background-color: #e3f2fd; }}
        .recommendation {{ padding: 8px; margin: 5px 0; background-color: #e8f5e9; border-radius: 3px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f0f0f0; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Signal Monitoring Report</h1>
        <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        <div class="score">Health Score: {score}/100</div>
    </div>
    
    <div class="section">
        <h2>📈 Statistics (Last 24 Hours)</h2>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Total Signals</td><td>{report['stats'].get('total_signals', 0)}</td></tr>
            <tr><td>Last Signal</td><td>{report['stats'].get('last_signal_time', 'N/A')}</td></tr>
        </table>
    </div>
    
    <div class="section">
        <h2>🔔 Signal Distribution</h2>
        <table>
            <tr><th>Signal Type</th><th>Count</th></tr>
"""

        for signal_type, count in report["stats"].get("signal_types", {}).items():
            html_content += (
                f"            <tr><td>{signal_type}</td><td>{count}</td></tr>\n"
            )

        html_content += """
        </table>
    </div>
    
    <div class="section">
        <h2>⚠️ Anomalies Detected</h2>
"""

        if report["anomalies"]:
            for anomaly in report["anomalies"]:
                html_content += f"""
        <div class="anomaly {anomaly.get('severity', 'INFO')}">
            <strong>{anomaly.get('type', 'UNKNOWN')}</strong>: {anomaly.get('message', '')}
        </div>
"""
        else:
            html_content += "        <p>✅ No anomalies detected</p>\n"

        html_content += """
    </div>
    
    <div class="section">
        <h2>💡 Recommendations</h2>
"""

        for rec in report["recommendations"]:
            html_content += f"        <div class='recommendation'>{rec}</div>\n"

        html_content += """
    </div>
    
    <div class="section">
        <h2>📊 Hourly Distribution</h2>
        <table>
            <tr><th>Hour</th><th>Signal Count</th></tr>
"""

        hourly_dist = report.get("hourly_distribution", {})
        for hour in range(24):
            count = hourly_dist.get(hour, 0)
            html_content += (
                f"            <tr><td>{hour:02d}:00</td><td>{count}</td></tr>\n"
            )

        html_content += """
        </table>
    </div>
</body>
</html>
"""

        with open(html_path, "w") as f:
            f.write(html_content)

        logger.info(f"HTML report saved: {html_path}")
        return html_path

    def save_json_report(self, report: Dict) -> Path:
        """JSONレポートを保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = self.report_dir / f"signal_monitor_{timestamp}.json"

        with open(json_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        logger.info(f"JSON report saved: {json_path}")
        return json_path

    def run_monitoring(self, hours: int = 24) -> Tuple[Dict, int]:
        """監視を実行"""
        logger.info("=" * 50)
        logger.info("🔍 Starting Signal Monitoring")
        logger.info("=" * 50)

        # データ読み込み
        df = self.load_signals(hours)

        # 各種チェック実行
        all_anomalies = []

        # シグナル停止チェック
        silence_anomaly = self.check_signal_silence(df)
        if silence_anomaly:
            all_anomalies.append(silence_anomaly)

        # 連続パターンチェック
        pattern_anomalies = self.check_consecutive_patterns(df)
        all_anomalies.extend(pattern_anomalies)

        # Confidence値チェック
        confidence_anomalies = self.check_confidence_levels(df)
        all_anomalies.extend(confidence_anomalies)

        # シグナル分布チェック
        distribution_anomalies = self.check_signal_distribution(df)
        all_anomalies.extend(distribution_anomalies)

        # 価格データチェック
        price_anomalies = self.check_price_data(df)
        all_anomalies.extend(price_anomalies)

        # レポート生成
        report = self.generate_report(df, all_anomalies)

        # レポート保存
        self.save_json_report(report)
        html_path = self.save_html_report(report)

        # サマリー出力
        logger.info("=" * 50)
        logger.info(f"📊 Monitoring Complete")
        logger.info(f"🎯 Health Score: {report['health_score']}/100")
        logger.info(f"⚠️  Anomalies Found: {len(all_anomalies)}")
        logger.info(f"📁 Report saved: {html_path}")

        # 異常がある場合は詳細出力
        if all_anomalies:
            logger.warning("⚠️ Anomalies detected:")
            for anomaly in all_anomalies:
                logger.warning(
                    f"  - [{anomaly['severity']}] {anomaly['type']}: {anomaly['message']}"
                )

        # 推奨事項出力
        logger.info("💡 Recommendations:")
        for rec in report["recommendations"]:
            logger.info(f"  {rec}")

        logger.info("=" * 50)

        return report, report["health_score"]


def main():
    """メイン実行関数"""
    import argparse

    parser = argparse.ArgumentParser(description="Monitor trading signal generation")
    parser.add_argument(
        "--csv-path",
        default="logs/trading_signals.csv",
        help="Path to trading signals CSV",
    )
    parser.add_argument(
        "--report-dir",
        default="logs/monitoring_reports",
        help="Directory for monitoring reports",
    )
    parser.add_argument(
        "--hours", type=int, default=24, help="Hours of history to analyze"
    )
    parser.add_argument(
        "--threshold-alert",
        type=int,
        default=60,
        help="Health score threshold for alerts",
    )

    args = parser.parse_args()

    # モニター実行
    monitor = SignalMonitor(args.csv_path, args.report_dir)
    report, health_score = monitor.run_monitoring(args.hours)

    # 閾値以下の場合はエラーコードで終了
    if health_score < args.threshold_alert:
        logger.error(
            f"🚨 ALERT: Health score {health_score} below threshold {args.threshold_alert}"
        )
        sys.exit(1)
    else:
        logger.info(f"✅ System health OK: {health_score}/100")
        sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Phase 12-2: 実データ収集システム（レガシーTradingStatisticsManager改良版）

Cloud Runログから取引データを収集・分析し、体系的な統計管理を実現。
シンプルさと実用性のバランスを重視した個人開発最適化版。

レガジーの良い部分を活用:
- TradingStatisticsManager: 包括的統計管理・データ構造設計
- TradeRecord・DailyStatistics: 実績のあるデータクラス設計
- PerformanceMetrics: 包括的パフォーマンス指標定義
"""

import argparse
import csv
import json
import logging
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

# base_analyzer.py活用
sys.path.append(str(Path(__file__).parent.parent / "analytics"))
from base_analyzer import BaseAnalyzer

# ログ設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """個別取引記録（レガシー互換・シンプル版）"""

    trade_id: str
    timestamp: str
    symbol: str = "BTC_JPY"
    side: str = "unknown"  # 'buy', 'sell', 'hold'
    signal_confidence: float = 0.0
    entry_price: Optional[float] = None
    quantity: float = 0.0
    strategy_type: str = "unknown"
    status: str = "detected"  # 'detected', 'executed', 'completed'

    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return asdict(self)


@dataclass
class DailyStatistics:
    """日次統計（レガシー準拠・簡素化版）"""

    date: str
    total_signals: int = 0
    buy_signals: int = 0
    sell_signals: int = 0
    hold_signals: int = 0
    signal_frequency: float = 0.0  # signals per hour
    avg_confidence: float = 0.0
    total_entries: int = 0
    total_logs: int = 0
    system_uptime_hours: float = 0.0

    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return asdict(self)


@dataclass
class PerformanceMetrics:
    """パフォーマンス指標（レガシー簡素版）"""

    # 基本統計
    total_signals: int = 0
    total_buy: int = 0
    total_sell: int = 0
    total_hold: int = 0

    # 頻度分析
    signals_per_hour: float = 0.0
    signals_per_day: float = 0.0

    # 信頼度分析
    avg_confidence: float = 0.0
    high_confidence_signals: int = 0  # confidence > 0.7

    # 時間効率
    analysis_period_hours: float = 0.0
    data_collection_success_rate: float = 0.0

    # システム指標
    log_entries_processed: int = 0
    error_rate: float = 0.0

    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return asdict(self)


class TradingDataCollector(BaseAnalyzer):
    """実データ収集メインクラス（Phase 12-2版・base_analyzer.py活用）"""

    def __init__(
        self,
        project_id: str = "my-crypto-bot-project",
        service_name: str = "crypto-bot-service",
        region: str = "asia-northeast1",
        output_dir: str = "logs/data_collection",
    ):
        # base_analyzer.py初期化
        super().__init__(project_id, service_name, region)

        # 出力ディレクトリ設定
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)

        # ファイルパス設定
        timestamp = datetime.now().strftime("%Y%m%d")
        self.trades_file = self.output_dir / f"trades_{timestamp}.csv"
        self.daily_stats_file = self.output_dir / f"daily_stats_{timestamp}.csv"
        self.performance_file = self.output_dir / f"performance_metrics_{timestamp}.json"

        # データ格納
        self.trades: List[TradeRecord] = []
        self.daily_stats: Dict[str, DailyStatistics] = {}
        self.performance_metrics = PerformanceMetrics()

        logger.info(f"TradingDataCollector初期化完了（base_analyzer.py活用版）: {output_dir}")

    def collect_trading_logs(self, hours: int = 24) -> Tuple[bool, int]:
        """Cloud Runログから取引データを収集（base_analyzer.py活用版）"""
        logger.info(f"取引ログ収集開始（過去{hours}時間）")

        try:
            # base_analyzer.pyのメソッドを活用（重複コード削除）
            success, logs = self.fetch_trading_logs(hours=hours, limit=500)

            if not success:
                logger.error("ログ取得失敗")
                return False, 0

            logger.info(f"ログ取得成功: {len(logs)}件")

            # ログ解析・TradeRecord生成
            processed_count = 0
            for log_entry in logs:
                trade_record = self._parse_log_entry(log_entry)
                if trade_record:
                    self.trades.append(trade_record)
                    processed_count += 1

            logger.info(f"取引レコード生成: {processed_count}件")
            return True, processed_count

        except Exception as e:
            logger.error(f"ログ収集エラー: {e}")
            return False, 0

    def _convert_to_trade_record(self, log_entry: Dict, parsed_log: Dict) -> Optional[TradeRecord]:
        """解析済みログをTradeRecordに変換（base_analyzer.py活用版）"""
        try:
            # base_analyzer.pyで解析済みの情報を活用
            timestamp = parsed_log.get("timestamp", "")
            side = parsed_log.get("signal_type", "unknown")
            confidence = parsed_log.get("confidence", 0.0)
            strategy_type = parsed_log.get("strategy_type", "unknown")

            if side == "unknown" and confidence == 0.0:
                return None  # 有効なシグナルではない

            # TradeRecord生成
            trade_id = f"{timestamp.replace(':', '').replace('-', '').replace('T', '').replace('Z', '')}_{side}"

            return TradeRecord(
                trade_id=trade_id,
                timestamp=timestamp,
                side=side,
                signal_confidence=confidence,
                strategy_type=strategy_type,
                status="detected",
            )

        except Exception as e:
            logger.warning(f"ログ解析失敗: {e}")
            return None

    def calculate_daily_statistics(self) -> Dict[str, DailyStatistics]:
        """日次統計を計算"""
        logger.info("日次統計計算開始")

        # 日付別にグループ化
        daily_groups = {}
        for trade in self.trades:
            try:
                date = trade.timestamp[:10]  # YYYY-MM-DD
                if date not in daily_groups:
                    daily_groups[date] = []
                daily_groups[date].append(trade)
            except Exception:
                continue

        # 各日の統計計算
        for date, trades in daily_groups.items():
            stats = DailyStatistics(date=date)

            stats.total_signals = len(trades)
            stats.buy_signals = len([t for t in trades if t.side == "buy"])
            stats.sell_signals = len([t for t in trades if t.side == "sell"])
            stats.hold_signals = len([t for t in trades if t.side == "hold"])

            # 信頼度平均
            confidences = [t.signal_confidence for t in trades if t.signal_confidence > 0]
            stats.avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            # 1日を24時間として頻度計算
            stats.signal_frequency = stats.total_signals / 24.0
            stats.system_uptime_hours = 24.0  # 簡易実装

            self.daily_stats[date] = stats

        logger.info(f"日次統計計算完了: {len(self.daily_stats)}日分")
        return self.daily_stats

    def calculate_performance_metrics(self, hours: int = 24) -> PerformanceMetrics:
        """パフォーマンス指標を計算"""
        logger.info("パフォーマンス指標計算開始")

        self.performance_metrics.total_signals = len(self.trades)
        self.performance_metrics.total_buy = len([t for t in self.trades if t.side == "buy"])
        self.performance_metrics.total_sell = len([t for t in self.trades if t.side == "sell"])
        self.performance_metrics.total_hold = len([t for t in self.trades if t.side == "hold"])

        # 頻度分析
        self.performance_metrics.analysis_period_hours = hours
        self.performance_metrics.signals_per_hour = (
            self.performance_metrics.total_signals / hours if hours > 0 else 0
        )
        self.performance_metrics.signals_per_day = self.performance_metrics.signals_per_hour * 24

        # 信頼度分析
        confidences = [t.signal_confidence for t in self.trades if t.signal_confidence > 0]
        if confidences:
            self.performance_metrics.avg_confidence = sum(confidences) / len(confidences)
            self.performance_metrics.high_confidence_signals = len(
                [c for c in confidences if c > 0.7]
            )

        # データ収集成功率
        self.performance_metrics.log_entries_processed = len(self.trades)
        self.performance_metrics.data_collection_success_rate = 100.0 if self.trades else 0.0

        logger.info(f"パフォーマンス指標計算完了: {self.performance_metrics.total_signals}シグナル")
        return self.performance_metrics

    def export_to_csv(self) -> Tuple[str, str]:
        """CSV形式でエクスポート"""
        logger.info("CSV形式エクスポート開始")

        # 取引データCSV
        with open(self.trades_file, "w", newline="", encoding="utf-8") as f:
            if self.trades:
                writer = csv.DictWriter(f, fieldnames=self.trades[0].to_dict().keys())
                writer.writeheader()
                for trade in self.trades:
                    writer.writerow(trade.to_dict())

        # 日次統計CSV
        with open(self.daily_stats_file, "w", newline="", encoding="utf-8") as f:
            if self.daily_stats:
                first_stat = next(iter(self.daily_stats.values()))
                writer = csv.DictWriter(f, fieldnames=first_stat.to_dict().keys())
                writer.writeheader()
                for stats in self.daily_stats.values():
                    writer.writerow(stats.to_dict())

        logger.info(f"CSV保存完了: {self.trades_file}, {self.daily_stats_file}")
        return str(self.trades_file), str(self.daily_stats_file)

    def export_performance_json(self) -> str:
        """パフォーマンス指標をJSON形式でエクスポート"""
        logger.info("パフォーマンス指標JSON保存開始")

        report_data = {
            "timestamp": datetime.now().isoformat(),
            "collection_period_hours": self.performance_metrics.analysis_period_hours,
            "performance_metrics": self.performance_metrics.to_dict(),
            "daily_stats_summary": {
                "total_days": len(self.daily_stats),
                "avg_signals_per_day": (
                    sum(stats.total_signals for stats in self.daily_stats.values())
                    / len(self.daily_stats)
                    if self.daily_stats
                    else 0
                ),
            },
            "data_files": {
                "trades_csv": str(self.trades_file),
                "daily_stats_csv": str(self.daily_stats_file),
            },
        }

        with open(self.performance_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        logger.info(f"パフォーマンス指標保存完了: {self.performance_file}")
        return str(self.performance_file)

    def generate_summary_report(self) -> str:
        """サマリーレポート生成"""
        logger.info("サマリーレポート生成")

        report = []
        report.append("=" * 60)
        report.append("Phase 12-2 実データ収集レポート")
        report.append("=" * 60)
        report.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"分析期間: {self.performance_metrics.analysis_period_hours}時間")
        report.append("")

        # 基本統計
        report.append("📊 基本統計:")
        report.append(f"  総シグナル数: {self.performance_metrics.total_signals}")
        report.append(f"  BUYシグナル: {self.performance_metrics.total_buy}")
        report.append(f"  SELLシグナル: {self.performance_metrics.total_sell}")
        report.append(f"  HOLDシグナル: {self.performance_metrics.total_hold}")
        report.append("")

        # 頻度分析
        report.append("📈 頻度分析:")
        report.append(f"  シグナル頻度: {self.performance_metrics.signals_per_hour:.2f}/時間")
        report.append(f"  日次推定: {self.performance_metrics.signals_per_day:.1f}/日")
        report.append("")

        # 信頼度分析
        report.append("🎯 信頼度分析:")
        report.append(f"  平均信頼度: {self.performance_metrics.avg_confidence:.3f}")
        report.append(
            f"  高信頼シグナル: {self.performance_metrics.high_confidence_signals}件 (>0.7)"
        )
        report.append("")

        # データ品質
        report.append("✅ データ品質:")
        report.append(f"  処理成功率: {self.performance_metrics.data_collection_success_rate:.1f}%")
        report.append(f"  日次統計: {len(self.daily_stats)}日分")
        report.append("")

        # ファイル出力
        report.append("📁 出力ファイル:")
        report.append(f"  取引データ: {self.trades_file}")
        report.append(f"  日次統計: {self.daily_stats_file}")
        report.append(f"  性能指標: {self.performance_file}")
        report.append("=" * 60)

        return "\n".join(report)

    def run_collection(self, hours: int = 24) -> bool:
        """完全データ収集実行（base_analyzer.py活用版）"""
        logger.info(f"Phase 12-2実データ収集開始（期間: {hours}時間）")

        try:
            # 1. ログ収集（base_analyzer.py活用）
            success, count = self.collect_trading_logs(hours)
            if not success:
                logger.error("ログ収集失敗")
                return False

            # 2. 統計計算
            self.calculate_daily_statistics()
            self.calculate_performance_metrics(hours)

            # 3. エクスポート（base_analyzer.pyメソッド活用）
            self.export_to_csv()
            self.export_performance_json()

            # 4. サマリー出力
            summary = self.generate_summary_report()
            print(summary)

            logger.info("Phase 12-2実データ収集完了")
            return True

        except Exception as e:
            logger.error(f"データ収集エラー: {e}")
            return False

    # ===== base_analyzer.py抽象メソッド実装 =====

    def run_analysis(self, hours: int = 24) -> Dict:
        """データ収集分析実行（base_analyzer.py要求）"""
        success = self.run_collection(hours)
        return {
            "success": success,
            "trade_count": len(self.trades),
            "daily_stats_count": len(self.daily_stats),
            "analysis_period_hours": hours,
            "performance_metrics": self.performance_metrics.to_dict(),
        }

    def generate_report(self, analysis_result: Dict) -> str:
        """データ収集レポート生成（base_analyzer.py要求）"""
        if analysis_result.get("success"):
            return f"""
=== Phase 12-2 データ収集レポート ===
取引件数: {analysis_result.get('trade_count', 0)}
統計日数: {analysis_result.get('daily_stats_count', 0)}
分析期間: {analysis_result.get('analysis_period_hours', 0)}時間
シグナル頻度: {analysis_result.get('performance_metrics', {}).get('signals_per_hour', 0):.2f}/h
==================================="""
        else:
            return "データ収集失敗"


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="Phase 12-2 実データ収集システム")
    parser.add_argument("--hours", type=int, default=24, help="収集期間（時間）")
    parser.add_argument("--service", default="crypto-bot-service", help="Cloud Runサービス名")
    parser.add_argument("--project", default="my-crypto-bot-project", help="GCPプロジェクトID")
    parser.add_argument("--region", default="asia-northeast1", help="GCPリージョン")
    parser.add_argument("--output", default="logs/data_collection", help="出力ディレクトリ")

    args = parser.parse_args()

    try:
        collector = TradingDataCollector(
            project_id=args.project,
            service_name=args.service,
            region=args.region,
            output_dir=args.output,
        )

        success = collector.run_collection(args.hours)

        if success:
            print("\\n🎉 Phase 12-2実データ収集成功！")
            print("📊 データ分析・A/Bテスト・ダッシュボード活用が可能です")
        else:
            print("\\n❌ データ収集失敗")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("データ収集中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"実行エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

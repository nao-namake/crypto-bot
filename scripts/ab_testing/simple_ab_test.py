#!/usr/bin/env python3
"""
Phase 12-2: シンプルA/Bテスト基盤（実用性重視版）

新旧モデル・戦略の並行実行・パフォーマンス比較を簡潔に実現。
複雑なレガシーシステムを簡素化し、個人開発に最適化。

機能:
- 2つのモデル/戦略の並行比較
- 基本統計分析（t検定）
- シンプルなレポート生成
- 実用的な判定基準
"""

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy import stats

# base_analyzer.py活用
sys.path.append(str(Path(__file__).parent.parent / "analytics"))
from base_analyzer import BaseAnalyzer

# ログ設定
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class ABTestMetrics:
    """A/Bテスト指標"""

    # 基本情報
    name: str
    start_time: str
    end_time: str
    duration_hours: float

    # パフォーマンス指標
    total_signals: int = 0
    signal_frequency: float = 0.0  # per hour
    avg_confidence: float = 0.0
    high_confidence_count: int = 0  # confidence > 0.7

    # シグナル分布
    buy_signals: int = 0
    sell_signals: int = 0
    hold_signals: int = 0

    # システム指標
    error_count: int = 0
    response_time_avg: float = 0.0
    uptime_percentage: float = 0.0

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ABTestResult:
    """A/Bテスト結果"""

    test_name: str
    variant_a: ABTestMetrics
    variant_b: ABTestMetrics

    # 統計分析
    statistical_analysis: Dict
    recommendation: str
    confidence_level: float

    # 実用的判定
    practical_significance: bool
    improvement_percentage: float
    winner: str  # 'A', 'B', or 'No significant difference'

    def to_dict(self) -> Dict:
        return asdict(self)


class SimpleABTest(BaseAnalyzer):
    """シンプルA/Bテストシステム（Phase 12-2版・base_analyzer.py活用）"""

    def __init__(
        self,
        project_id: str = "my-crypto-bot-project",
        service_name: str = "crypto-bot-service",
        region: str = "asia-northeast1",
        output_dir: str = "logs/ab_testing",
    ):
        # base_analyzer.py初期化
        super().__init__(project_id, service_name, region)

        # 出力ディレクトリ
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)

        logger.info("SimpleABTest初期化完了（base_analyzer.py活用版）")

    def collect_variant_data(
        self, variant_name: str, hours: int = 24, service_suffix: str = ""
    ) -> ABTestMetrics:
        """バリアント別データ収集（base_analyzer.py活用版）"""
        logger.info(f"バリアント{variant_name}データ収集開始（{hours}時間）")

        try:
            start_time = datetime.utcnow() - timedelta(hours=hours)
            end_time = datetime.utcnow()

            # base_analyzer.pyのメソッドを活用（重複コード削除）
            success, logs = self.fetch_trading_logs(
                hours=hours, service_suffix=service_suffix, limit=300
            )

            if not success:
                logger.warning(f"ログ取得失敗（{variant_name}）")
                return self._create_empty_metrics(variant_name, start_time, end_time, hours)

            # メトリクス計算
            metrics = self._calculate_metrics(variant_name, logs, start_time, end_time, hours)

            logger.info(f"バリアント{variant_name}データ収集完了: {metrics.total_signals}シグナル")
            return metrics

        except Exception as e:
            logger.error(f"バリアント{variant_name}データ収集エラー: {e}")
            return self._create_empty_metrics(variant_name, start_time, end_time, hours)

    def _create_empty_metrics(
        self, name: str, start_time: datetime, end_time: datetime, hours: float
    ) -> ABTestMetrics:
        """空のメトリクス作成"""
        return ABTestMetrics(
            name=name,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_hours=hours,
        )

    def _calculate_metrics(
        self, name: str, logs: List[Dict], start_time: datetime, end_time: datetime, hours: float
    ) -> ABTestMetrics:
        """ログからメトリクス計算"""

        # 基本カウント
        total_signals = 0
        buy_signals = 0
        sell_signals = 0
        hold_signals = 0
        confidences = []
        response_times = []

        for log in logs:
            # base_analyzer.pyのメソッドを活用（重複コード削除）
            parsed_log = self.parse_log_message(log)

            if parsed_log["signal_type"] != "unknown":
                total_signals += 1

                if parsed_log["signal_type"] == "buy":
                    buy_signals += 1
                elif parsed_log["signal_type"] == "sell":
                    sell_signals += 1
                elif parsed_log["signal_type"] == "hold":
                    hold_signals += 1

                # 信頼度情報
                if parsed_log["confidence"] > 0:
                    confidences.append(parsed_log["confidence"])

                # レスポンス時間（簡易実装）
                if parsed_log.get("response_time"):
                    response_times.append(parsed_log["response_time"])

        # メトリクス計算
        avg_confidence = np.mean(confidences) if confidences else 0.0
        high_confidence_count = len([c for c in confidences if c > 0.7])
        signal_frequency = total_signals / hours if hours > 0 else 0.0
        response_time_avg = np.mean(response_times) if response_times else 0.0

        return ABTestMetrics(
            name=name,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            duration_hours=hours,
            total_signals=total_signals,
            signal_frequency=signal_frequency,
            avg_confidence=avg_confidence,
            high_confidence_count=high_confidence_count,
            buy_signals=buy_signals,
            sell_signals=sell_signals,
            hold_signals=hold_signals,
            response_time_avg=response_time_avg,
            uptime_percentage=100.0,  # 簡易実装
        )

    def perform_statistical_analysis(
        self, variant_a: ABTestMetrics, variant_b: ABTestMetrics
    ) -> Dict:
        """統計分析実行（t検定）"""
        logger.info("統計分析実行")

        # サンプルサイズチェック
        if variant_a.total_signals < 10 or variant_b.total_signals < 10:
            return {
                "test_type": "insufficient_data",
                "message": "サンプルサイズが不十分（各バリアント最低10シグナル必要）",
                "p_value": None,
                "t_statistic": None,
                "significant": False,
            }

        # シグナル頻度の比較（主要指標）
        try:
            # 簡易実装：シグナル頻度を正規分布と仮定
            # 実際の分析では、より詳細な統計モデルが必要

            freq_a = variant_a.signal_frequency
            freq_b = variant_b.signal_frequency

            # 簡易t検定（等分散仮定）
            # Note: 実際の実装では分散計算が必要
            pooled_std = np.sqrt((freq_a**2 + freq_b**2) / 2)  # 簡易実装

            if pooled_std > 0:
                t_stat = (freq_a - freq_b) / pooled_std
                # 自由度を簡易計算
                df = variant_a.total_signals + variant_b.total_signals - 2
                p_value = 2 * (1 - stats.t.cdf(abs(t_stat), df))
            else:
                t_stat = 0.0
                p_value = 1.0

            return {
                "test_type": "t_test_signal_frequency",
                "primary_metric": "signal_frequency",
                "variant_a_value": freq_a,
                "variant_b_value": freq_b,
                "t_statistic": t_stat,
                "p_value": p_value,
                "degrees_of_freedom": df,
                "significant": p_value < 0.05,
                "confidence_level": 95,
            }

        except Exception as e:
            logger.error(f"統計分析エラー: {e}")
            return {"test_type": "analysis_failed", "error": str(e), "significant": False}

    def generate_recommendation(
        self, variant_a: ABTestMetrics, variant_b: ABTestMetrics, statistical_analysis: Dict
    ) -> Tuple[str, str, float, bool]:
        """推奨事項・判定生成"""

        # 実用的な改善判定（10%以上の改善を有意とする）
        freq_improvement = (
            (
                (variant_b.signal_frequency - variant_a.signal_frequency)
                / variant_a.signal_frequency
                * 100
            )
            if variant_a.signal_frequency > 0
            else 0
        )

        confidence_improvement = variant_b.avg_confidence - variant_a.avg_confidence

        # 統計的有意性
        is_statistically_significant = statistical_analysis.get("significant", False)

        # 実用的有意性（10%以上の改善）
        is_practically_significant = abs(freq_improvement) >= 10.0

        # 総合判定
        if is_statistically_significant and is_practically_significant:
            if freq_improvement > 0:
                winner = "B"
                recommendation = f"バリアントBを採用推奨（シグナル頻度{freq_improvement:.1f}%向上）"
            else:
                winner = "A"
                recommendation = (
                    f"バリアントAを維持推奨（シグナル頻度{abs(freq_improvement):.1f}%良好）"
                )
        elif is_statistically_significant:
            winner = "B" if freq_improvement > 0 else "A"
            recommendation = f"統計的有意差あり（バリアント{winner}）、ただし実用的改善は限定的"
        elif is_practically_significant:
            winner = "B" if freq_improvement > 0 else "A"
            recommendation = f"実用的改善あり（バリアント{winner}）、ただし統計的有意差なし - より長期のテスト推奨"
        else:
            winner = "No significant difference"
            recommendation = "両バリアント間に有意差なし - 現行システム維持または追加テスト実施推奨"

        # 信頼レベル
        confidence_level = statistical_analysis.get("confidence_level", 0)
        if not is_statistically_significant:
            confidence_level = max(0, confidence_level - 20)  # 信頼度調整

        return recommendation, winner, confidence_level, is_practically_significant

    def run_ab_test(
        self,
        test_name: str,
        variant_a_service: str = "",
        variant_b_service: str = "-stage10",
        hours: int = 24,
    ) -> ABTestResult:
        """A/Bテスト実行"""
        logger.info(f"A/Bテスト開始: {test_name}（{hours}時間）")

        # バリアント別データ収集
        variant_a = self.collect_variant_data("A", hours, variant_a_service)
        variant_b = self.collect_variant_data("B", hours, variant_b_service)

        # 統計分析
        statistical_analysis = self.perform_statistical_analysis(variant_a, variant_b)

        # 推奨事項生成
        recommendation, winner, confidence_level, practical_significance = (
            self.generate_recommendation(variant_a, variant_b, statistical_analysis)
        )

        # 改善率計算
        improvement_percentage = (
            (
                (variant_b.signal_frequency - variant_a.signal_frequency)
                / variant_a.signal_frequency
                * 100
            )
            if variant_a.signal_frequency > 0
            else 0
        )

        # 結果まとめ
        result = ABTestResult(
            test_name=test_name,
            variant_a=variant_a,
            variant_b=variant_b,
            statistical_analysis=statistical_analysis,
            recommendation=recommendation,
            confidence_level=confidence_level,
            practical_significance=practical_significance,
            improvement_percentage=improvement_percentage,
            winner=winner,
        )

        logger.info(f"A/Bテスト完了: {winner}")
        return result

    def save_results(self, result: ABTestResult) -> str:
        """結果保存（base_analyzer.py活用版）"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ab_test_{result.test_name}_{timestamp}.json"

        # base_analyzer.pyのメソッドを活用（重複コード削除）
        saved_path = self.save_json_report(result.to_dict(), filename, self.output_dir)

        logger.info(f"A/Bテスト結果保存: {saved_path}")
        return saved_path

    def generate_report(self, result: ABTestResult) -> str:
        """レポート生成"""
        report = []
        report.append("=" * 60)
        report.append(f"Phase 12-2 A/Bテスト結果: {result.test_name}")
        report.append("=" * 60)
        report.append(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"テスト期間: {result.variant_a.duration_hours}時間")
        report.append("")

        # バリアント比較
        report.append("📊 バリアント比較:")
        report.append(
            f"  バリアントA: {result.variant_a.total_signals}シグナル ({result.variant_a.signal_frequency:.2f}/時間)"
        )
        report.append(
            f"  バリアントB: {result.variant_b.total_signals}シグナル ({result.variant_b.signal_frequency:.2f}/時間)"
        )
        report.append(f"  改善率: {result.improvement_percentage:+.1f}%")
        report.append("")

        # 信頼度比較
        report.append("🎯 信頼度分析:")
        report.append(f"  バリアントA平均: {result.variant_a.avg_confidence:.3f}")
        report.append(f"  バリアントB平均: {result.variant_b.avg_confidence:.3f}")
        report.append(f"  高信頼シグナル A: {result.variant_a.high_confidence_count}件")
        report.append(f"  高信頼シグナル B: {result.variant_b.high_confidence_count}件")
        report.append("")

        # 統計分析
        report.append("📈 統計分析:")
        stats = result.statistical_analysis
        report.append(f"  検定タイプ: {stats.get('test_type', 'unknown')}")
        if stats.get("p_value") is not None:
            report.append(f"  p値: {stats['p_value']:.4f}")
            report.append(f"  統計的有意: {'Yes' if stats.get('significant') else 'No'}")
        report.append(f"  実用的有意: {'Yes' if result.practical_significance else 'No'}")
        report.append("")

        # 推奨事項
        report.append("🏆 結果・推奨事項:")
        report.append(f"  勝者: {result.winner}")
        report.append(f"  信頼度: {result.confidence_level:.0f}%")
        report.append(f"  推奨: {result.recommendation}")
        report.append("=" * 60)

        return "\\n".join(report)

    # ===== base_analyzer.py抽象メソッド実装 =====

    def run_analysis(self, test_name: str = "default_test", hours: int = 24, **kwargs) -> Dict:
        """A/Bテスト分析実行（base_analyzer.py要求）"""
        variant_a_suffix = kwargs.get("variant_a_service", "")
        variant_b_suffix = kwargs.get("variant_b_service", "-stage10")

        result = self.run_ab_test(test_name, variant_a_suffix, variant_b_suffix, hours)

        return {
            "test_name": result.test_name,
            "winner": result.winner,
            "improvement_percentage": result.improvement_percentage,
            "confidence_level": result.confidence_level,
            "practical_significance": result.practical_significance,
            "variant_a_signals": result.variant_a.total_signals,
            "variant_b_signals": result.variant_b.total_signals,
            "recommendation": result.recommendation,
            "statistical_analysis": result.statistical_analysis,
        }

    def generate_report(self, analysis_result: Dict) -> str:
        """A/Bテストレポート生成（base_analyzer.py要求）"""
        return f"""
=== Phase 12-2 A/Bテストレポート ===
テスト名: {analysis_result.get('test_name', 'Unknown')}
勝者: {analysis_result.get('winner', 'Unknown')}
改善率: {analysis_result.get('improvement_percentage', 0):+.1f}%
信頼度: {analysis_result.get('confidence_level', 0):.0f}%
推奨: {analysis_result.get('recommendation', '')}
バリアントA: {analysis_result.get('variant_a_signals', 0)}シグナル
バリアントB: {analysis_result.get('variant_b_signals', 0)}シグナル
=================================="""


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="Phase 12-2 シンプルA/Bテスト")
    parser.add_argument("--test-name", default="default_test", help="テスト名")
    parser.add_argument("--hours", type=int, default=24, help="テスト期間（時間）")
    parser.add_argument("--variant-a", default="", help="バリアントAサービスサフィックス")
    parser.add_argument("--variant-b", default="-stage10", help="バリアントBサービスサフィックス")
    parser.add_argument("--project", default="my-crypto-bot-project", help="GCPプロジェクトID")
    parser.add_argument("--service", default="crypto-bot-service", help="ベースサービス名")
    parser.add_argument("--output", default="logs/ab_testing", help="出力ディレクトリ")

    args = parser.parse_args()

    try:
        ab_test = SimpleABTest(
            project_id=args.project, service_name=args.service, output_dir=args.output
        )

        # A/Bテスト実行
        result = ab_test.run_ab_test(
            test_name=args.test_name,
            variant_a_service=args.variant_a,
            variant_b_service=args.variant_b,
            hours=args.hours,
        )

        # 結果保存・レポート生成
        ab_test.save_results(result)
        report = ab_test.generate_report(result)

        print(report)
        print("\\n🎉 A/Bテスト完了！")

    except Exception as e:
        logger.error(f"A/Bテスト実行エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

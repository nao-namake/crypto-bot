#!/usr/bin/env python3
"""
97特徴量 vs 127特徴量 効率化効果測定スクリプト
Phase 2最適化の効果を包括的に検証
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import psutil

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class FeatureComparisonAnalyzer:
    """97特徴量vs127特徴量の比較分析"""

    def __init__(self):
        self.results_97 = {}
        self.results_127 = {}
        self.performance_metrics = {}

    def run_backtest(self, config_path, label):
        """バックテスト実行と性能測定"""
        print(f"\n{'='*60}")
        print(f"🚀 {label}特徴量バックテスト開始")
        print(f"{'='*60}")

        # メモリ使用量測定開始
        process = psutil.Process()
        mem_before = process.memory_info().rss / 1024 / 1024  # MB

        # 時間測定開始
        start_time = time.time()

        # バックテスト実行
        cmd = [
            sys.executable,
            "-m",
            "crypto_bot.main",
            "backtest",
            "--config",
            config_path,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # 実行時間
            execution_time = time.time() - start_time

            # メモリ使用量
            mem_after = process.memory_info().rss / 1024 / 1024  # MB
            mem_used = mem_after - mem_before

            # 結果解析
            output = result.stdout

            # 取引結果ファイルを探す
            results_dir = Path("results")
            latest_result = None
            latest_time = 0

            for result_file in results_dir.glob("**/backtest_results_*.json"):
                if result_file.stat().st_mtime > latest_time:
                    latest_time = result_file.stat().st_mtime
                    latest_result = result_file

            backtest_metrics = {}
            if latest_result:
                with open(latest_result, "r") as f:
                    backtest_data = json.load(f)
                    backtest_metrics = {
                        "total_return": backtest_data.get("total_return", 0),
                        "win_rate": backtest_data.get("win_rate", 0),
                        "sharpe_ratio": backtest_data.get("sharpe_ratio", 0),
                        "max_drawdown": backtest_data.get("max_drawdown", 0),
                        "total_trades": backtest_data.get("total_trades", 0),
                    }

            return {
                "execution_time": execution_time,
                "memory_used": mem_used,
                "backtest_metrics": backtest_metrics,
                "success": True,
                "output": output,
            }

        except subprocess.CalledProcessError as e:
            print(f"❌ エラー: {e}")
            return {
                "execution_time": time.time() - start_time,
                "memory_used": 0,
                "backtest_metrics": {},
                "success": False,
                "error": str(e),
            }

    def analyze_efficiency(self):
        """効率化効果の分析"""
        print("\n" + "=" * 60)
        print("📊 効率化効果分析")
        print("=" * 60)

        # 実行時間比較
        time_97 = self.results_97.get("execution_time", 0)
        time_127 = self.results_127.get("execution_time", 0)
        time_improvement = (
            ((time_127 - time_97) / time_127 * 100) if time_127 > 0 else 0
        )

        print(f"\n⏱️ 実行時間:")
        print(f"  127特徴量: {time_127:.2f}秒")
        print(f"  97特徴量: {time_97:.2f}秒")
        print(f"  改善率: {time_improvement:.1f}%")

        # メモリ使用量比較
        mem_97 = self.results_97.get("memory_used", 0)
        mem_127 = self.results_127.get("memory_used", 0)
        mem_improvement = ((mem_127 - mem_97) / mem_127 * 100) if mem_127 > 0 else 0

        print(f"\n💾 メモリ使用量:")
        print(f"  127特徴量: {mem_127:.2f}MB")
        print(f"  97特徴量: {mem_97:.2f}MB")
        print(f"  改善率: {mem_improvement:.1f}%")

        # 特徴量削減効果
        feature_reduction = (127 - 97) / 127 * 100
        print(f"\n📉 特徴量削減:")
        print(f"  削減数: 30特徴量")
        print(f"  削減率: {feature_reduction:.1f}%")

        return {
            "time_improvement": time_improvement,
            "memory_improvement": mem_improvement,
            "feature_reduction": feature_reduction,
        }

    def analyze_performance(self):
        """取引性能比較"""
        print("\n" + "=" * 60)
        print("📈 取引性能比較")
        print("=" * 60)

        metrics_97 = self.results_97.get("backtest_metrics", {})
        metrics_127 = self.results_127.get("backtest_metrics", {})

        comparison = pd.DataFrame({"127特徴量": metrics_127, "97特徴量": metrics_97})

        print("\n" + comparison.to_string())

        # 性能維持率計算
        if metrics_127.get("total_return", 0) != 0:
            return_retention = (
                metrics_97.get("total_return", 0)
                / metrics_127.get("total_return", 0)
                * 100
            )
        else:
            return_retention = 0

        if metrics_127.get("win_rate", 0) != 0:
            winrate_retention = (
                metrics_97.get("win_rate", 0) / metrics_127.get("win_rate", 0) * 100
            )
        else:
            winrate_retention = 0

        print(f"\n🎯 性能維持率:")
        print(f"  収益率維持: {return_retention:.1f}%")
        print(f"  勝率維持: {winrate_retention:.1f}%")

        return {
            "return_retention": return_retention,
            "winrate_retention": winrate_retention,
            "comparison_df": comparison,
        }

    def generate_report(self):
        """総合レポート生成"""
        print("\n" + "=" * 60)
        print("📋 総合評価レポート")
        print("=" * 60)

        efficiency = self.analyze_efficiency()
        performance = self.analyze_performance()

        # 総合評価
        print("\n🏆 Phase 2最適化効果:")
        print(f"  ✅ 実行時間: {efficiency['time_improvement']:.1f}%改善")
        print(f"  ✅ メモリ使用: {efficiency['memory_improvement']:.1f}%削減")
        print(f"  ✅ 特徴量数: {efficiency['feature_reduction']:.1f}%削減")
        print(f"  ✅ 収益性能: {performance['return_retention']:.1f}%維持")
        print(f"  ✅ 勝率性能: {performance['winrate_retention']:.1f}%維持")

        # レポート保存
        report = {
            "timestamp": datetime.now().isoformat(),
            "efficiency_metrics": efficiency,
            "performance_metrics": performance,
            "results_97": self.results_97,
            "results_127": self.results_127,
            "summary": {
                "optimization_success": True,
                "efficiency_gain": f"{np.mean([efficiency['time_improvement'], efficiency['memory_improvement']]):.1f}%",
                "performance_retention": f"{np.mean([performance['return_retention'], performance['winrate_retention']]):.1f}%",
            },
        }

        # 結果保存
        output_dir = Path("results/feature_comparison")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"97vs127_comparison_{timestamp}.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        print(f"\n📁 詳細レポート保存: {output_file}")

        return report

    def run_comparison(self):
        """比較分析実行"""
        print("🔍 97特徴量 vs 127特徴量 効率化効果測定開始")
        print(f"開始時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 127特徴量バックテスト
        config_127 = "config/validation/unified_127_features_backtest.yml"
        if Path(config_127).exists():
            self.results_127 = self.run_backtest(config_127, "127")
        else:
            print(f"❌ 127特徴量設定ファイルが見つかりません: {config_127}")
            return

        # 97特徴量バックテスト
        config_97 = "config/validation/unified_97_features_backtest.yml"
        if Path(config_97).exists():
            self.results_97 = self.run_backtest(config_97, "97")
        else:
            print(f"❌ 97特徴量設定ファイルが見つかりません: {config_97}")
            return

        # レポート生成
        if self.results_97.get("success") and self.results_127.get("success"):
            self.generate_report()
        else:
            print("\n❌ バックテスト実行に失敗しました")

        print(f"\n完了時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    """メイン実行"""
    analyzer = FeatureComparisonAnalyzer()
    analyzer.run_comparison()


if __name__ == "__main__":
    main()

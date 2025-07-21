#!/usr/bin/env python3
"""
統合パフォーマンステストスクリプト
Phase 5.1: 統合テスト・検証の一環として、
151特徴量 + マルチタイムフレーム統合システムの性能評価
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
import gc
import json
import tracemalloc
from typing import Dict, List, Optional, Tuple

from crypto_bot.data.multi_timeframe_fetcher import MultiTimeframeDataFetcher
from crypto_bot.data.timeframe_synchronizer import TimeframeSynchronizer
from crypto_bot.main import load_config
from crypto_bot.ml.preprocessor import FeatureEngineer

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class IntegratedPerformanceTester:
    """統合システムパフォーマンステストクラス"""

    def __init__(self, config_path: str = "config/production/production.yml"):
        """
        Args:
            config_path: 設定ファイルパス
        """
        self.config = load_config(config_path)
        self.feature_engineer = FeatureEngineer(self.config)
        self.test_results = {
            "system_info": self._get_system_info(),
            "performance_metrics": {},
            "memory_profile": {},
            "scalability_tests": {},
            "bottleneck_analysis": {},
            "test_status": "PENDING",
            "execution_time": 0,
        }

    def _get_system_info(self) -> Dict:
        """システム情報を取得"""
        try:
            if PSUTIL_AVAILABLE:
                cpu_count = psutil.cpu_count()
                memory_total = psutil.virtual_memory().total / (1024**3)  # GB
            else:
                cpu_count = "N/A"
                memory_total = "N/A"

            return {
                "cpu_count": cpu_count,
                "memory_total_gb": memory_total,
                "python_version": sys.version,
                "platform": sys.platform,
                "psutil_available": PSUTIL_AVAILABLE,
            }
        except Exception:
            return {"error": "Failed to get system info"}

    def generate_scaled_test_data(self, scale_factor: int = 1) -> pd.DataFrame:
        """スケールしたテストデータを生成"""
        base_samples = 500
        n_samples = base_samples * scale_factor

        logger.info(
            f"📊 Generating {n_samples} test samples (scale factor: {scale_factor})..."
        )

        end_time = datetime.now().replace(minute=0, second=0, microsecond=0)
        timestamps = [end_time - timedelta(hours=i) for i in range(n_samples)]
        timestamps.reverse()

        # ベクトル化された高速データ生成
        price_changes = np.random.normal(0, 0.01, n_samples)
        base_price = 5000000
        prices = base_price * np.cumprod(1 + price_changes * 0.02)

        volatilities = np.abs(np.random.normal(0.005, 0.002, n_samples))
        highs = prices * (1 + volatilities)
        lows = prices * (1 - volatilities)
        opens = prices + np.random.normal(0, volatilities * 0.5, n_samples) * prices
        volumes = np.abs(np.random.normal(50, 20, n_samples))

        df = pd.DataFrame(
            {
                "open": opens,
                "high": highs,
                "low": lows,
                "close": prices,
                "volume": volumes,
            },
            index=timestamps,
        )

        logger.info(
            f"✅ Generated test data: {len(df)} rows, {df.memory_usage(deep=True).sum() / 1024**2:.1f} MB"
        )
        return df

    def measure_feature_generation_performance(self, data: pd.DataFrame) -> Dict:
        """特徴量生成のパフォーマンス測定"""
        logger.info("🔧 Measuring feature generation performance...")

        # メモリトレースの開始
        tracemalloc.start()
        if PSUTIL_AVAILABLE:
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024**2  # MB
        else:
            process = None
            initial_memory = 0

        perf_metrics = {
            "preprocessing_time": 0,
            "feature_count": 0,
            "memory_usage": {},
            "cpu_usage": [],
            "throughput": {},
        }

        try:
            # CPU使用率監視開始
            if PSUTIL_AVAILABLE:
                cpu_start = psutil.cpu_percent()
            else:
                cpu_start = 0

            start_time = time.time()

            # 特徴量生成実行
            logger.info("  Executing feature generation...")
            features_df = self.feature_engineer.transform(data)

            end_time = time.time()

            # CPU使用率終了
            if PSUTIL_AVAILABLE:
                cpu_end = psutil.cpu_percent()
            else:
                cpu_end = 0

            # メトリクス計算
            processing_time = end_time - start_time
            if PSUTIL_AVAILABLE:
                final_memory = process.memory_info().rss / 1024**2  # MB
            else:
                final_memory = 0
            memory_increase = final_memory - initial_memory

            # メモリトレース終了
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            perf_metrics.update(
                {
                    "preprocessing_time": processing_time,
                    "feature_count": (
                        len(features_df.columns) if features_df is not None else 0
                    ),
                    "memory_usage": {
                        "initial_mb": initial_memory,
                        "final_mb": final_memory,
                        "increase_mb": memory_increase,
                        "peak_traced_mb": peak / 1024**2,
                        "psutil_available": PSUTIL_AVAILABLE,
                    },
                    "cpu_usage": {
                        "start": cpu_start,
                        "end": cpu_end,
                        "delta": cpu_end - cpu_start,
                    },
                    "throughput": {
                        "samples_per_second": (
                            len(data) / processing_time if processing_time > 0 else 0
                        ),
                        "features_per_second": (
                            (len(features_df.columns) * len(features_df))
                            / processing_time
                            if processing_time > 0 and features_df is not None
                            else 0
                        ),
                    },
                }
            )

            logger.info(f"  ⚡ Processing time: {processing_time:.2f}s")
            logger.info(f"  📊 Features generated: {perf_metrics['feature_count']}")
            logger.info(f"  💾 Memory increase: {memory_increase:.1f} MB")
            logger.info(
                f"  🔄 Throughput: {perf_metrics['throughput']['samples_per_second']:.1f} samples/s"
            )

            return perf_metrics

        except Exception as e:
            logger.error(f"❌ Feature generation performance test failed: {str(e)}")
            perf_metrics["error"] = str(e)
            return perf_metrics
        finally:
            if tracemalloc.is_tracing():
                tracemalloc.stop()

    def measure_multiframe_performance(self, data: pd.DataFrame) -> Dict:
        """マルチタイムフレーム処理のパフォーマンス測定"""
        logger.info("⏱️ Measuring multi-timeframe performance...")

        if PSUTIL_AVAILABLE:
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024**2  # MB
        else:
            process = None
            initial_memory = 0

        mtf_metrics = {
            "conversion_times": {},
            "synchronization_time": 0,
            "total_time": 0,
            "memory_usage": {},
            "data_sizes": {},
        }

        try:
            total_start = time.time()

            # MultiTimeframeDataFetcher初期化
            fetcher = MultiTimeframeDataFetcher(config=self.config)
            synchronizer = TimeframeSynchronizer()

            # 各タイムフレーム変換の性能測定
            timeframes = ["15m", "4h"]
            converted_data = {"1h": data}

            for tf in timeframes:
                start_time = time.time()

                if tf == "15m":
                    result = fetcher._interpolate_to_15m(data.copy())
                elif tf == "4h":
                    result = fetcher._aggregate_to_4h(data.copy())

                conversion_time = time.time() - start_time
                mtf_metrics["conversion_times"][tf] = conversion_time

                if result is not None:
                    converted_data[tf] = result
                    mtf_metrics["data_sizes"][tf] = len(result)
                    logger.info(
                        f"  🔄 {tf} conversion: {conversion_time:.2f}s → {len(result)} samples"
                    )
                else:
                    logger.warning(f"  ⚠️ {tf} conversion failed")

            # 同期処理の性能測定
            if len(converted_data) > 1:
                sync_start = time.time()
                synchronized_data = synchronizer.synchronize_multi_timeframe_data(
                    converted_data
                )
                sync_time = time.time() - sync_start
                mtf_metrics["synchronization_time"] = sync_time

                if synchronized_data:
                    logger.info(f"  🔗 Synchronization: {sync_time:.2f}s")
                    mtf_metrics["synchronized_count"] = len(synchronized_data)
                else:
                    logger.warning("  ⚠️ Synchronization failed")

            total_time = time.time() - total_start
            if PSUTIL_AVAILABLE:
                final_memory = process.memory_info().rss / 1024**2  # MB
            else:
                final_memory = 0

            mtf_metrics.update(
                {
                    "total_time": total_time,
                    "memory_usage": {
                        "initial_mb": initial_memory,
                        "final_mb": final_memory,
                        "increase_mb": final_memory - initial_memory,
                        "psutil_available": PSUTIL_AVAILABLE,
                    },
                }
            )

            logger.info(f"  ⚡ Total multi-timeframe time: {total_time:.2f}s")

            return mtf_metrics

        except Exception as e:
            logger.error(f"❌ Multi-timeframe performance test failed: {str(e)}")
            mtf_metrics["error"] = str(e)
            return mtf_metrics

    def run_scalability_tests(self) -> Dict:
        """スケーラビリティテスト"""
        logger.info("📈 Running scalability tests...")

        scale_factors = [1, 2, 4]  # 500, 1000, 2000サンプル
        scalability_results = {}

        for scale in scale_factors:
            logger.info(f"  Testing scale factor: {scale}x")

            try:
                # スケールされたデータ生成
                scaled_data = self.generate_scaled_test_data(scale)

                # パフォーマンステスト実行
                start_time = time.time()

                # 特徴量生成
                feature_perf = self.measure_feature_generation_performance(scaled_data)

                # マルチタイムフレーム処理
                mtf_perf = self.measure_multiframe_performance(scaled_data)

                total_time = time.time() - start_time

                scalability_results[f"scale_{scale}x"] = {
                    "data_size": len(scaled_data),
                    "feature_performance": feature_perf,
                    "multiframe_performance": mtf_perf,
                    "total_time": total_time,
                    "efficiency_ratio": (
                        len(scaled_data) / total_time if total_time > 0 else 0
                    ),
                }

                logger.info(
                    f"    ✅ Scale {scale}x: {total_time:.2f}s, Efficiency: {scalability_results[f'scale_{scale}x']['efficiency_ratio']:.1f} samples/s"
                )

                # メモリクリーンアップ
                del scaled_data
                gc.collect()

            except Exception as e:
                logger.error(f"    ❌ Scale {scale}x failed: {str(e)}")
                scalability_results[f"scale_{scale}x"] = {"error": str(e)}

        return scalability_results

    def analyze_bottlenecks(self, performance_data: Dict) -> Dict:
        """ボトルネック分析"""
        logger.info("🔍 Analyzing performance bottlenecks...")

        bottlenecks = {
            "slowest_operations": [],
            "memory_intensive_operations": [],
            "efficiency_concerns": [],
            "recommendations": [],
        }

        try:
            # 処理時間分析
            if "feature_performance" in performance_data:
                fp = performance_data["feature_performance"]
                if "preprocessing_time" in fp and fp["preprocessing_time"] > 10:
                    bottlenecks["slowest_operations"].append(
                        {
                            "operation": "feature_generation",
                            "time_seconds": fp["preprocessing_time"],
                            "severity": (
                                "high" if fp["preprocessing_time"] > 30 else "medium"
                            ),
                        }
                    )

            # メモリ使用量分析
            for test_name, test_data in performance_data.items():
                if isinstance(test_data, dict) and "memory_usage" in test_data:
                    memory_increase = test_data["memory_usage"].get("increase_mb", 0)
                    if memory_increase > 100:  # 100MB以上の増加
                        bottlenecks["memory_intensive_operations"].append(
                            {
                                "operation": test_name,
                                "memory_increase_mb": memory_increase,
                                "severity": (
                                    "high" if memory_increase > 500 else "medium"
                                ),
                            }
                        )

            # 推奨事項の生成
            if bottlenecks["slowest_operations"]:
                bottlenecks["recommendations"].append(
                    "Consider optimizing feature generation algorithms"
                )
            if bottlenecks["memory_intensive_operations"]:
                bottlenecks["recommendations"].append(
                    "Implement memory-efficient data processing strategies"
                )

            # 効率性の評価
            if "scalability_tests" in performance_data:
                scales = list(performance_data["scalability_tests"].keys())
                if len(scales) >= 2:
                    scale_1 = performance_data["scalability_tests"].get("scale_1x", {})
                    scale_2 = performance_data["scalability_tests"].get("scale_2x", {})

                    if "efficiency_ratio" in scale_1 and "efficiency_ratio" in scale_2:
                        efficiency_degradation = (
                            scale_1["efficiency_ratio"] - scale_2["efficiency_ratio"]
                        ) / scale_1["efficiency_ratio"]

                        if efficiency_degradation > 0.3:  # 30%以上の効率低下
                            bottlenecks["efficiency_concerns"].append(
                                {
                                    "issue": "Poor scalability",
                                    "degradation_percentage": efficiency_degradation
                                    * 100,
                                    "recommendation": "Review algorithms for O(n²) complexity",
                                }
                            )

            logger.info(
                f"  🔍 Found {len(bottlenecks['slowest_operations'])} slow operations"
            )
            logger.info(
                f"  💾 Found {len(bottlenecks['memory_intensive_operations'])} memory-intensive operations"
            )

            return bottlenecks

        except Exception as e:
            logger.error(f"❌ Bottleneck analysis failed: {str(e)}")
            return {"error": str(e)}

    def run_comprehensive_performance_test(self) -> Dict:
        """包括的パフォーマンステストを実行"""
        start_time = time.time()

        try:
            logger.info("🚀 Starting comprehensive performance test...")

            # Step 1: 基本パフォーマンステスト
            base_data = self.generate_scaled_test_data(scale_factor=1)

            logger.info("🔧 Testing feature generation performance...")
            self.test_results["performance_metrics"]["feature_performance"] = (
                self.measure_feature_generation_performance(base_data)
            )

            logger.info("⏱️ Testing multi-timeframe performance...")
            self.test_results["performance_metrics"]["multiframe_performance"] = (
                self.measure_multiframe_performance(base_data)
            )

            # Step 2: スケーラビリティテスト
            logger.info("📈 Running scalability tests...")
            self.test_results["scalability_tests"] = self.run_scalability_tests()

            # Step 3: ボトルネック分析
            logger.info("🔍 Analyzing bottlenecks...")
            all_performance_data = {
                **self.test_results["performance_metrics"],
                "scalability_tests": self.test_results["scalability_tests"],
            }
            self.test_results["bottleneck_analysis"] = self.analyze_bottlenecks(
                all_performance_data
            )

            # 総合判定
            errors = sum(
                1
                for test_result in [
                    self.test_results["performance_metrics"].get(
                        "feature_performance", {}
                    ),
                    self.test_results["performance_metrics"].get(
                        "multiframe_performance", {}
                    ),
                    self.test_results["scalability_tests"],
                    self.test_results["bottleneck_analysis"],
                ]
                if "error" in test_result
            )

            if errors == 0:
                self.test_results["test_status"] = "PASSED"
                logger.info("✅ All performance tests PASSED!")
            else:
                self.test_results["test_status"] = "FAILED"
                logger.error(f"❌ Performance tests FAILED! Errors: {errors}")

            # 実行時間
            self.test_results["execution_time"] = time.time() - start_time
            logger.info(
                f"\n⏱️ Performance test completed in {self.test_results['execution_time']:.2f} seconds"
            )

            # 結果保存
            self.save_results()

            return self.test_results

        except Exception as e:
            logger.error(f"❌ Comprehensive performance test failed: {str(e)}")
            self.test_results["test_status"] = "ERROR"
            self.test_results["error"] = str(e)
            return self.test_results

    def save_results(self):
        """テスト結果をファイルに保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_results/performance_test_{timestamp}.json"

        os.makedirs("test_results", exist_ok=True)

        with open(filename, "w") as f:
            json.dump(self.test_results, f, indent=2, default=str)

        logger.info(f"💾 Performance test results saved to: {filename}")


def main():
    """メイン実行関数"""
    logger.info("=" * 80)
    logger.info("Integrated Performance Test - Phase 5.1")
    logger.info("=" * 80)

    # テスト実行
    tester = IntegratedPerformanceTester()
    results = tester.run_comprehensive_performance_test()

    # 最終サマリー
    logger.info("\n" + "=" * 80)
    logger.info("📊 FINAL PERFORMANCE SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Status: {results['test_status']}")
    logger.info(f"Execution Time: {results.get('execution_time', 0):.2f}s")

    # パフォーマンス要約
    if "performance_metrics" in results:
        perf = results["performance_metrics"]
        if "feature_performance" in perf:
            fp = perf["feature_performance"]
            logger.info(
                f"Feature Generation: {fp.get('preprocessing_time', 0):.2f}s, {fp.get('feature_count', 0)} features"
            )

        if "multiframe_performance" in perf:
            mp = perf["multiframe_performance"]
            logger.info(f"Multi-timeframe: {mp.get('total_time', 0):.2f}s")

    # テスト失敗時は非ゼロで終了
    if results["test_status"] not in ["PASSED"]:
        sys.exit(1)


if __name__ == "__main__":
    main()

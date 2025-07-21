#!/usr/bin/env python3
"""
マルチタイムフレーム機能テストスクリプト
Phase 5.1: 統合テスト・検証の一環として、
マルチタイムフレーム（15m/1h/4h）データ同期・変換を検証
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from crypto_bot.data.multi_timeframe_fetcher import MultiTimeframeDataFetcher
from crypto_bot.data.timeframe_synchronizer import TimeframeSynchronizer
from crypto_bot.main import load_config

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class MultiTimeframeTester:
    """マルチタイムフレーム機能のテスト・検証クラス"""

    def __init__(self, config_path: str = "config/production/production.yml"):
        """
        Args:
            config_path: 設定ファイルパス
        """
        self.config = load_config(config_path)
        self.test_results = {
            "timeframe_tests": {},
            "synchronization_tests": {},
            "data_quality_tests": {},
            "performance_metrics": {},
            "test_status": "PENDING",
            "execution_time": 0,
            "errors": [],
        }

    def generate_hourly_test_data(self, n_hours: int = 200) -> pd.DataFrame:
        """1時間足のテストデータを生成（ベースデータ）"""
        logger.info(f"📊 Generating {n_hours} hourly OHLCV samples...")

        end_time = datetime.now().replace(minute=0, second=0, microsecond=0)
        timestamps = [end_time - timedelta(hours=i) for i in range(n_hours)]
        timestamps.reverse()

        # リアルなOHLCVデータ生成
        base_price = 5000000  # BTC/JPY
        ohlcv_data = []

        for i, ts in enumerate(timestamps):
            # 価格の変動
            price_change = np.random.normal(0, 0.01) * base_price * 0.02
            base_price += price_change

            # OHLC
            volatility = abs(np.random.normal(0.005, 0.002))
            high = base_price * (1 + volatility)
            low = base_price * (1 - volatility)
            open_price = base_price + np.random.normal(0, volatility * 0.5) * base_price
            close_price = base_price
            volume = abs(np.random.normal(50, 20))

            ohlcv_data.append(
                {
                    "timestamp": ts,
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close_price,
                    "volume": volume,
                }
            )

        df = pd.DataFrame(ohlcv_data)
        df.set_index("timestamp", inplace=True)

        logger.info(f"✅ Generated hourly test data: {len(df)} rows")
        return df

    def test_timeframe_conversion(self, hourly_data: pd.DataFrame) -> Dict:
        """タイムフレーム変換テスト"""
        logger.info("🔄 Testing timeframe conversion...")
        conversion_results = {}

        try:
            # MultiTimeframeDataFetcher初期化
            fetcher = MultiTimeframeDataFetcher(self.config)

            # 15分足への変換テスト（補間）
            logger.info("  Testing 1h → 15m conversion (interpolation)...")
            data_15m = fetcher._interpolate_to_15m(hourly_data.copy())
            conversion_results["15m"] = {
                "input_size": len(hourly_data),
                "output_size": len(data_15m) if data_15m is not None else 0,
                "expected_ratio": 4,  # 1時間 = 4×15分
                "actual_ratio": (
                    len(data_15m) / len(hourly_data)
                    if data_15m is not None and len(hourly_data) > 0
                    else 0
                ),
                "success": data_15m is not None and len(data_15m) > 0,
            }

            # 4時間足への変換テスト（集約）
            logger.info("  Testing 1h → 4h conversion (aggregation)...")
            data_4h = fetcher._aggregate_to_4h(hourly_data.copy())
            conversion_results["4h"] = {
                "input_size": len(hourly_data),
                "output_size": len(data_4h) if data_4h is not None else 0,
                "expected_ratio": 0.25,  # 4時間 = 1/4
                "actual_ratio": (
                    len(data_4h) / len(hourly_data)
                    if data_4h is not None and len(hourly_data) > 0
                    else 0
                ),
                "success": data_4h is not None and len(data_4h) > 0,
            }

            # 品質チェック
            for timeframe, result in conversion_results.items():
                if result["success"]:
                    logger.info(
                        f"    ✅ {timeframe}: {result['output_size']} samples (ratio: {result['actual_ratio']:.2f})"
                    )
                else:
                    logger.error(f"    ❌ {timeframe}: Conversion failed")

            return conversion_results

        except Exception as e:
            logger.error(f"❌ Timeframe conversion test failed: {str(e)}")
            self.test_results["errors"].append(f"Timeframe conversion: {str(e)}")
            return {"error": str(e)}

    def test_data_synchronization(self, hourly_data: pd.DataFrame) -> Dict:
        """データ同期テスト"""
        logger.info("🔄 Testing data synchronization...")
        sync_results = {}

        try:
            # TimeframeSynchronizer初期化
            synchronizer = TimeframeSynchronizer(self.config)

            # 異なるタイムフレームのデータを生成
            fetcher = MultiTimeframeDataFetcher(self.config)
            data_15m = fetcher._interpolate_to_15m(hourly_data.copy())
            data_1h = hourly_data.copy()
            data_4h = fetcher._aggregate_to_4h(hourly_data.copy())

            if data_15m is None or data_4h is None:
                raise ValueError("Failed to generate multi-timeframe data")

            # 同期テスト
            timeframe_data = {"15m": data_15m, "1h": data_1h, "4h": data_4h}

            logger.info("  Synchronizing timeframes...")
            synchronized_data = synchronizer.synchronize_multi_timeframe_data(
                timeframe_data
            )

            # 同期結果の分析
            if synchronized_data:
                sync_results["success"] = True
                sync_results["synchronized_timeframes"] = len(synchronized_data)
                sync_results["common_timestamps"] = {}

                # 共通タイムスタンプの分析
                for timeframe, data in synchronized_data.items():
                    sync_results["common_timestamps"][timeframe] = len(data)
                    logger.info(
                        f"    ✅ {timeframe}: {len(data)} synchronized timestamps"
                    )

                # データ品質チェック（簡易版）
                total_records = sum(len(data) for data in synchronized_data.values())
                avg_records = (
                    total_records / len(synchronized_data) if synchronized_data else 0
                )
                sync_results["quality_score"] = min(
                    avg_records / 100, 1.0
                )  # 簡易スコア
                logger.info(
                    f"    📊 Avg synchronized records per timeframe: {avg_records:.1f}"
                )

            else:
                sync_results["success"] = False
                logger.error("    ❌ Synchronization failed - no output data")

            return sync_results

        except Exception as e:
            logger.error(f"❌ Data synchronization test failed: {str(e)}")
            self.test_results["errors"].append(f"Data synchronization: {str(e)}")
            return {"error": str(e)}

    def test_data_quality(self, hourly_data: pd.DataFrame) -> Dict:
        """データ品質テスト"""
        logger.info("🔍 Testing data quality...")
        quality_results = {}

        try:
            # MultiTimeframeFetcher で統合データ取得
            fetcher = MultiTimeframeDataFetcher(self.config)

            # モックデータを使用した品質テスト
            timeframes = ["15m", "1h", "4h"]

            for timeframe in timeframes:
                logger.info(f"  Checking {timeframe} data quality...")

                if timeframe == "15m":
                    data = fetcher._interpolate_to_15m(hourly_data.copy())
                elif timeframe == "1h":
                    data = hourly_data.copy()
                elif timeframe == "4h":
                    data = fetcher._aggregate_to_4h(hourly_data.copy())

                if data is not None and not data.empty:
                    quality_metrics = {
                        "total_records": len(data),
                        "nan_percentage": (
                            data.isna().sum().sum() / (len(data) * len(data.columns))
                        )
                        * 100,
                        "duplicate_timestamps": data.index.duplicated().sum(),
                        "price_range_check": {
                            "min_price": float(
                                data[["open", "high", "low", "close"]].min().min()
                            ),
                            "max_price": float(
                                data[["open", "high", "low", "close"]].max().max()
                            ),
                            "price_variance": float(data["close"].var()),
                        },
                        "volume_stats": {
                            "min_volume": float(data["volume"].min()),
                            "max_volume": float(data["volume"].max()),
                            "avg_volume": float(data["volume"].mean()),
                        },
                    }

                    quality_results[timeframe] = quality_metrics
                    logger.info(
                        f"    ✅ {timeframe}: {quality_metrics['total_records']} records, "
                        f"NaN: {quality_metrics['nan_percentage']:.2f}%"
                    )
                else:
                    quality_results[timeframe] = {"error": "No data generated"}
                    logger.error(f"    ❌ {timeframe}: No data generated")

            return quality_results

        except Exception as e:
            logger.error(f"❌ Data quality test failed: {str(e)}")
            self.test_results["errors"].append(f"Data quality: {str(e)}")
            return {"error": str(e)}

    def test_performance(self, hourly_data: pd.DataFrame) -> Dict:
        """パフォーマンステスト"""
        logger.info("⚡ Testing performance...")
        perf_results = {}

        try:
            # メモリ使用量測定（簡易）
            try:
                import psutil

                process = psutil.Process()
                initial_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_available = True
            except ImportError:
                logger.warning("⚠️ psutil not available, skipping memory monitoring")
                initial_memory = 0
                memory_available = False

            start_time = time.time()

            # MultiTimeframeDataFetcher初期化と実行
            fetcher = MultiTimeframeDataFetcher(self.config)

            # 複数タイムフレーム処理時間測定
            conversion_times = {}

            # 15分足変換
            conv_start = time.time()
            data_15m = fetcher._interpolate_to_15m(hourly_data.copy())
            conversion_times["15m"] = time.time() - conv_start

            # 4時間足変換
            conv_start = time.time()
            data_4h = fetcher._aggregate_to_4h(hourly_data.copy())
            conversion_times["4h"] = time.time() - conv_start

            # 同期処理時間
            if data_15m is not None and data_4h is not None:
                sync_start = time.time()
                synchronizer = TimeframeSynchronizer(self.config)
                timeframe_data = {"15m": data_15m, "1h": hourly_data, "4h": data_4h}
                synchronized_data = synchronizer.synchronize_multi_timeframe_data(
                    timeframe_data
                )
                sync_time = time.time() - sync_start
            else:
                sync_time = 0
                logger.warning("  ⚠️ Skipping sync performance test (missing data)")

            total_time = time.time() - start_time
            if memory_available:
                final_memory = process.memory_info().rss / 1024 / 1024  # MB
            else:
                final_memory = 0

            perf_results = {
                "total_execution_time": total_time,
                "conversion_times": conversion_times,
                "synchronization_time": sync_time,
                "memory_usage": {
                    "initial_mb": initial_memory,
                    "final_mb": final_memory,
                    "increase_mb": (
                        final_memory - initial_memory if memory_available else 0
                    ),
                    "monitoring_available": memory_available,
                },
                "throughput": {
                    "records_per_second": (
                        len(hourly_data) / total_time if total_time > 0 else 0
                    )
                },
            }

            logger.info(f"  ⚡ Total time: {total_time:.2f}s")
            if memory_available:
                logger.info(
                    f"  💾 Memory increase: {final_memory - initial_memory:.1f} MB"
                )
            else:
                logger.info("  💾 Memory monitoring: Not available (psutil missing)")
            logger.info(
                f"  📊 Throughput: {perf_results['throughput']['records_per_second']:.1f} records/s"
            )

            return perf_results

        except Exception as e:
            logger.error(f"❌ Performance test failed: {str(e)}")
            self.test_results["errors"].append(f"Performance: {str(e)}")
            return {"error": str(e)}

    def run_comprehensive_test(self) -> Dict:
        """包括的マルチタイムフレームテストを実行"""
        start_time = time.time()

        try:
            logger.info("🚀 Starting comprehensive multi-timeframe test...")

            # Step 1: テストデータ生成
            test_data = self.generate_hourly_test_data(n_hours=200)

            # Step 2: タイムフレーム変換テスト
            self.test_results["timeframe_tests"] = self.test_timeframe_conversion(
                test_data
            )

            # Step 3: データ同期テスト
            self.test_results["synchronization_tests"] = self.test_data_synchronization(
                test_data
            )

            # Step 4: データ品質テスト
            self.test_results["data_quality_tests"] = self.test_data_quality(test_data)

            # Step 5: パフォーマンステスト
            self.test_results["performance_metrics"] = self.test_performance(test_data)

            # 総合判定
            errors = len(self.test_results["errors"])
            failed_tests = sum(
                1
                for test_result in [
                    self.test_results["timeframe_tests"],
                    self.test_results["synchronization_tests"],
                    self.test_results["data_quality_tests"],
                    self.test_results["performance_metrics"],
                ]
                if "error" in test_result
            )

            if errors == 0 and failed_tests == 0:
                self.test_results["test_status"] = "PASSED"
                logger.info("✅ All multi-timeframe tests PASSED!")
            else:
                self.test_results["test_status"] = "FAILED"
                logger.error(
                    f"❌ Multi-timeframe tests FAILED! Errors: {errors}, Failed tests: {failed_tests}"
                )

            # 実行時間
            self.test_results["execution_time"] = time.time() - start_time
            logger.info(
                f"\n⏱️ Multi-timeframe test completed in {self.test_results['execution_time']:.2f} seconds"
            )

            # 結果保存
            self.save_results()

            return self.test_results

        except Exception as e:
            logger.error(f"❌ Comprehensive test failed: {str(e)}")
            self.test_results["test_status"] = "ERROR"
            self.test_results["error"] = str(e)
            return self.test_results

    def save_results(self):
        """テスト結果をファイルに保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_results/multi_timeframe_test_{timestamp}.json"

        os.makedirs("test_results", exist_ok=True)

        with open(filename, "w") as f:
            json.dump(self.test_results, f, indent=2, default=str)

        logger.info(f"💾 Test results saved to: {filename}")


def main():
    """メイン実行関数"""
    logger.info("=" * 80)
    logger.info("Multi-Timeframe Integration Test - Phase 5.1")
    logger.info("=" * 80)

    # テスト実行
    tester = MultiTimeframeTester()
    results = tester.run_comprehensive_test()

    # 最終サマリー
    logger.info("\n" + "=" * 80)
    logger.info("📊 FINAL TEST SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Status: {results['test_status']}")
    logger.info(f"Execution Time: {results.get('execution_time', 0):.2f}s")
    logger.info(f"Errors: {len(results.get('errors', []))}")

    # テスト失敗時は非ゼロで終了
    if results["test_status"] not in ["PASSED"]:
        sys.exit(1)


if __name__ == "__main__":
    main()

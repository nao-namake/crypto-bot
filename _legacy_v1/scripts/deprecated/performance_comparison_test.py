#!/usr/bin/env python3
"""
Phase B2.6.1: パフォーマンス検証スクリプト

新旧特徴量生成システムの性能比較:
- 新システム: BatchFeatureCalculator + TechnicalFeatureEngine + ExternalDataIntegrator
- 旧システム: 個別df[column] = value操作 (151回断片化)

期待効果:
- 処理速度: 75%向上 (2-4秒 → 0.5-1.0秒)
- メモリ使用量: 50%削減
"""

import json
import logging
import os
import sys
import time
import tracemalloc
from typing import Any, Dict, Tuple

# プロジェクトルートを追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import pandas as pd

# 設定ファイル読み込み
import yaml
from memory_profiler import memory_usage

# 新システムコンポーネント（Phase B2実装）
from crypto_bot.ml.feature_engines.batch_calculator import BatchFeatureCalculator
from crypto_bot.ml.feature_engines.external_data_engine import ExternalDataIntegrator
from crypto_bot.ml.feature_engines.technical_engine import TechnicalFeatureEngine

# 旧システム比較用（preprocessor.pyのlegacy部分）
from crypto_bot.ml.preprocessor import FeatureEngineer

# テストデータ生成（直接pandas使用）


# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PerformanceTestRunner:
    """パフォーマンステスト実行クラス"""

    def __init__(self):
        self.results = {
            "test_metadata": {
                "timestamp": time.time(),
                "python_version": sys.version,
            },
            "legacy_system": {},
            "batch_system": {},
            "comparison": {},
        }

        # 設定ファイル読み込み
        self.config = self._load_config()

        # テストデータ準備
        self.test_data = self._prepare_test_data()

        logger.info("🧪 PerformanceTestRunner initialized")

    def _load_config(self) -> Dict[str, Any]:
        """設定ファイル読み込み"""
        config_path = "/Users/nao/Desktop/bot/config/production/production.yml"
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            # パフォーマンステスト用設定調整
            # 外部データソースを制限してテスト時間を短縮
            test_features = [
                "rsi_14",
                "rsi_7",
                "rsi_21",
                "sma_20",
                "sma_50",
                "ema_12",
                "ema_26",
                "macd",
                "atr_14",
                "stoch",
                "adx",  # 高速なテクニカル指標のみ
            ]

            config["ml"]["extra_features"] = test_features

            logger.info(
                f"📋 Configuration loaded for testing: {len(test_features)} features"
            )

            return config
        except Exception as e:
            logger.error(f"❌ Failed to load config: {e}")
            # フォールバック設定
            return {
                "ml": {
                    "extra_features": ["rsi_14", "sma_20", "ema_12", "macd"],
                    "feat_period": 14,
                    "lags": [1, 2, 3],
                    "rolling_window": 14,
                }
            }

    def _prepare_test_data(self) -> pd.DataFrame:
        """テストデータ準備"""
        try:
            # CSVデータロード
            csv_path = "data/btc_usd_2024_hourly.csv"

            if os.path.exists(csv_path):
                logger.info("📊 Loading test data from CSV...")
                df = pd.read_csv(csv_path)

                # timestampカラムをDatetimeIndexに変換
                if "timestamp" in df.columns:
                    df["timestamp"] = pd.to_datetime(df["timestamp"])
                    df.set_index("timestamp", inplace=True)
                elif df.index.name != "timestamp":
                    # 最初の列をtimestampとして使用
                    df.index = pd.to_datetime(df.iloc[:, 0])
                    df.index.name = "timestamp"

                # データサイズを測定用に調整（パフォーマンステスト用に小さく）
                test_size = min(200, len(df))
                test_df = df.tail(test_size).copy()

                logger.info(
                    f"✅ Test data prepared: {len(test_df)} rows × {len(test_df.columns)} columns"
                )
                return test_df
            else:
                # モックデータ生成
                logger.warning("⚠️ CSV not found, generating mock data...")
                return self._generate_mock_data()

        except Exception as e:
            logger.error(f"❌ Failed to prepare test data: {e}")
            return self._generate_mock_data()

    def _generate_mock_data(self, n_rows: int = 200) -> pd.DataFrame:
        """モックデータ生成"""
        dates = pd.date_range("2024-01-01", periods=n_rows, freq="H")

        # 基本OHLCV生成（リアルな価格動作）
        base_price = 50000.0
        returns = np.random.normal(0, 0.02, n_rows)
        prices = base_price * np.exp(returns.cumsum())

        # OHLCV計算
        df = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices * (1 + np.random.normal(0, 0.001, n_rows)),
                "high": prices * (1 + np.abs(np.random.normal(0, 0.005, n_rows))),
                "low": prices * (1 - np.abs(np.random.normal(0, 0.005, n_rows))),
                "close": prices,
                "volume": np.random.lognormal(10, 1, n_rows),
            }
        )

        df.set_index("timestamp", inplace=True)

        logger.info(f"📊 Mock data generated: {len(df)} rows")
        return df

    def test_legacy_system_performance(self) -> Dict[str, Any]:
        """旧システム（個別処理）パフォーマンステスト"""
        logger.info("🕰️ Testing Legacy System Performance...")

        try:
            # メモリトレース開始
            tracemalloc.start()
            start_time = time.time()

            # FeatureEnginer初期化
            fe = FeatureEngineer(self.config)

            # 旧方式での特徴量生成（バッチエンジン無効化）
            if hasattr(fe, "batch_engines_enabled"):
                fe.batch_engines_enabled = False  # レガシーモード強制

            # メモリ監視付き特徴量生成
            def legacy_transform():
                return fe.transform(self.test_data.copy())

            # memory_profilerによるメモリ使用量測定
            memory_before = memory_usage()[0]
            memory_during = memory_usage((legacy_transform, ()))
            memory_after = memory_usage()[0]

            # 結果取得
            result_df = legacy_transform()

            # 時間測定
            processing_time = time.time() - start_time

            # メモリ統計
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # 結果記録
            legacy_results = {
                "processing_time_seconds": processing_time,
                "input_rows": len(self.test_data),
                "input_columns": len(self.test_data.columns),
                "output_columns": (
                    len(result_df.columns) if result_df is not None else 0
                ),
                "features_generated": (
                    len(result_df.columns) - len(self.test_data.columns)
                    if result_df is not None
                    else 0
                ),
                "memory_before_mb": memory_before,
                "memory_peak_mb": max(memory_during),
                "memory_after_mb": memory_after,
                "tracemalloc_current_mb": current / 1024 / 1024,
                "tracemalloc_peak_mb": peak / 1024 / 1024,
                "features_per_second": (
                    (len(result_df.columns) - len(self.test_data.columns))
                    / processing_time
                    if processing_time > 0 and result_df is not None
                    else 0
                ),
            }

            self.results["legacy_system"] = legacy_results

            logger.info(f"📊 Legacy System Results:")
            logger.info(f"  • Processing Time: {processing_time:.3f}s")
            logger.info(
                f"  • Features Generated: {legacy_results['features_generated']}"
            )
            logger.info(f"  • Memory Peak: {legacy_results['memory_peak_mb']:.1f} MB")
            logger.info(
                f"  • Features/Second: {legacy_results['features_per_second']:.1f}"
            )

            return legacy_results

        except Exception as e:
            error_result = {"error": str(e), "traceback": traceback.format_exc()}
            self.results["legacy_system"] = error_result
            logger.error(f"❌ Legacy system test failed: {e}")
            return error_result

    def test_batch_system_performance(self) -> Dict[str, Any]:
        """新システム（バッチ処理）パフォーマンステスト"""
        logger.info("🚀 Testing Batch System Performance...")

        try:
            # メモリトレース開始
            tracemalloc.start()
            start_time = time.time()

            # バッチシステム初期化
            batch_calc = BatchFeatureCalculator(self.config)
            technical_engine = TechnicalFeatureEngine(self.config, batch_calc)
            external_integrator = ExternalDataIntegrator(self.config, batch_calc)

            # メモリ監視付きバッチ処理（FeatureEngineer統合テスト）
            def batch_transform():
                # FeatureEngineer経由でのバッチ処理テスト
                fe_batch = FeatureEngineer(self.config)

                # バッチエンジンが有効であることを確認
                if hasattr(fe_batch, "batch_engines_enabled"):
                    if not fe_batch.batch_engines_enabled:
                        logger.warning("🔧 Force enabling batch engines for batch test")
                        fe_batch.batch_engines_enabled = True

                return fe_batch.transform(self.test_data.copy())

            # memory_profilerによるメモリ使用量測定
            memory_before = memory_usage()[0]
            memory_during = memory_usage((batch_transform, ()))
            memory_after = memory_usage()[0]

            # 結果取得
            result_df = batch_transform()

            # 時間測定
            processing_time = time.time() - start_time

            # メモリ統計
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # バッチシステム統計取得
            batch_stats = batch_calc.calculate_batch_efficiency_metrics()

            # 結果記録
            batch_results = {
                "processing_time_seconds": processing_time,
                "input_rows": len(self.test_data),
                "input_columns": len(self.test_data.columns),
                "output_columns": (
                    len(result_df.columns) if result_df is not None else 0
                ),
                "features_generated": (
                    len(result_df.columns) - len(self.test_data.columns)
                    if result_df is not None
                    else 0
                ),
                "memory_before_mb": memory_before,
                "memory_peak_mb": max(memory_during),
                "memory_after_mb": memory_after,
                "tracemalloc_current_mb": current / 1024 / 1024,
                "tracemalloc_peak_mb": peak / 1024 / 1024,
                "features_per_second": (
                    (len(result_df.columns) - len(self.test_data.columns))
                    / processing_time
                    if processing_time > 0 and result_df is not None
                    else 0
                ),
                "batch_system_stats": batch_stats,
            }

            self.results["batch_system"] = batch_results

            logger.info(f"🚀 Batch System Results:")
            logger.info(f"  • Processing Time: {processing_time:.3f}s")
            logger.info(
                f"  • Features Generated: {batch_results['features_generated']}"
            )
            logger.info(f"  • Memory Peak: {batch_results['memory_peak_mb']:.1f} MB")
            logger.info(
                f"  • Features/Second: {batch_results['features_per_second']:.1f}"
            )

            return batch_results

        except Exception as e:
            error_result = {"error": str(e), "traceback": traceback.format_exc()}
            self.results["batch_system"] = error_result
            logger.error(f"❌ Batch system test failed: {e}")
            return error_result

    def calculate_performance_comparison(self):
        """性能比較計算"""
        if (
            "error" in self.results["legacy_system"]
            or "error" in self.results["batch_system"]
        ):
            logger.warning("⚠️ Cannot calculate comparison due to errors in tests")
            return

        legacy = self.results["legacy_system"]
        batch = self.results["batch_system"]

        # 速度改善計算
        time_improvement = 0
        if legacy["processing_time_seconds"] > 0:
            time_improvement = (
                (legacy["processing_time_seconds"] - batch["processing_time_seconds"])
                / legacy["processing_time_seconds"]
            ) * 100

        # メモリ改善計算
        memory_improvement = 0
        if legacy["memory_peak_mb"] > 0:
            memory_improvement = (
                (legacy["memory_peak_mb"] - batch["memory_peak_mb"])
                / legacy["memory_peak_mb"]
            ) * 100

        # 特徴量生成効率改善
        efficiency_improvement = 0
        if legacy["features_per_second"] > 0:
            efficiency_improvement = (
                (batch["features_per_second"] - legacy["features_per_second"])
                / legacy["features_per_second"]
            ) * 100

        comparison_results = {
            "speed_improvement_percent": time_improvement,
            "memory_improvement_percent": memory_improvement,
            "efficiency_improvement_percent": efficiency_improvement,
            "target_speed_improvement": 75.0,  # 75%目標
            "target_memory_improvement": 50.0,  # 50%目標
            "speed_target_achieved": time_improvement >= 75.0,
            "memory_target_achieved": memory_improvement >= 50.0,
            "overall_success": time_improvement >= 75.0 and memory_improvement >= 50.0,
        }

        self.results["comparison"] = comparison_results

        # 結果表示
        logger.info("🎯 Performance Comparison Results:")
        logger.info(f"  • Speed Improvement: {time_improvement:.1f}% (Target: 75%)")
        logger.info(f"  • Memory Improvement: {memory_improvement:.1f}% (Target: 50%)")
        logger.info(f"  • Efficiency Improvement: {efficiency_improvement:.1f}%")
        logger.info(
            f"  • Speed Target Achieved: {'✅' if comparison_results['speed_target_achieved'] else '❌'}"
        )
        logger.info(
            f"  • Memory Target Achieved: {'✅' if comparison_results['memory_target_achieved'] else '❌'}"
        )
        logger.info(
            f"  • Overall Success: {'✅' if comparison_results['overall_success'] else '❌'}"
        )

    def save_results(
        self,
        output_path: str = "/Users/nao/Desktop/bot/test_results/performance_comparison.json",
    ):
        """結果保存"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)

            logger.info(f"💾 Results saved to: {output_path}")
        except Exception as e:
            logger.error(f"❌ Failed to save results: {e}")

    def run_complete_test(self):
        """完全パフォーマンステスト実行"""
        logger.info("🧪 Starting Complete Performance Test...")

        # 旧システムテスト
        self.test_legacy_system_performance()

        # 新システムテスト
        self.test_batch_system_performance()

        # 比較計算
        self.calculate_performance_comparison()

        # 結果保存
        self.save_results()

        logger.info("🎉 Performance Test Completed!")

        return self.results


def main():
    """メイン実行"""
    try:
        runner = PerformanceTestRunner()
        results = runner.run_complete_test()

        # サマリー表示
        print("\n" + "=" * 80)
        print("🎯 PHASE B2.6.1 PERFORMANCE VERIFICATION RESULTS")
        print("=" * 80)

        if "comparison" in results and "overall_success" in results["comparison"]:
            if results["comparison"]["overall_success"]:
                print("🎉 SUCCESS: Performance targets achieved!")
                print(
                    f"   • Speed improvement: {results['comparison']['speed_improvement_percent']:.1f}%"
                )
                print(
                    f"   • Memory improvement: {results['comparison']['memory_improvement_percent']:.1f}%"
                )
            else:
                print("⚠️  PARTIAL SUCCESS: Some targets not achieved")
                print(
                    f"   • Speed improvement: {results['comparison']['speed_improvement_percent']:.1f}% (Target: 75%)"
                )
                print(
                    f"   • Memory improvement: {results['comparison']['memory_improvement_percent']:.1f}% (Target: 50%)"
                )
        else:
            print("❌ TEST FAILED: Could not complete comparison")

        print("=" * 80)
        return results

    except Exception as e:
        logger.error(f"❌ Test execution failed: {e}")
        return None


if __name__ == "__main__":
    main()

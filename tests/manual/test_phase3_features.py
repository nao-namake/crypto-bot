#!/usr/bin/env python3
"""
Phase 3 特徴量エンジニアリング テスト

新システムの24特徴量システムの動作確認
- TechnicalIndicators: 20個のテクニカル指標
- AnomalyDetector: 4個の異常検知指標

実行方法:
    python3 tests/manual/test_phase3_features.py

Phase 3テスト実装日: 2025年8月18日.
"""

import os
import sys
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# プロジェクトルートのパス追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# テスト対象のインポート
try:
    from src.core.logger import get_logger
    from src.features import FEATURE_CATEGORIES, OPTIMIZED_FEATURES
    from src.features.anomaly import AnomalyDetector
    from src.features.technical import TechnicalIndicators
except ImportError as e:
    print(f"❌ インポートエラー: {e}")
    print("プロジェクトルートから実行してください: python3 tests/manual/test_phase3_features.py")
    sys.exit(1)


def create_sample_data(rows: int = 100) -> pd.DataFrame:
    """
    テスト用のサンプルOHLCVデータ生成

    Args:
        rows: データ行数

    Returns:
        サンプルデータフレーム.
    """
    np.random.seed(42)  # 再現性のために固定

    # 基準価格からランダムウォーク
    base_price = 1000.0
    price_changes = np.random.normal(0, 0.02, rows)  # 2%の標準偏差
    prices = [base_price]

    for change in price_changes[1:]:
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, 1.0))  # 負の価格を防ぐ

    prices = np.array(prices)

    # OHLCV生成
    data = []
    for i in range(rows):
        close = prices[i]
        volatility = np.random.uniform(0.005, 0.03)  # 0.5-3%の変動

        high = close * (1 + volatility * np.random.uniform(0, 1))
        low = close * (1 - volatility * np.random.uniform(0, 1))
        open_price = np.random.uniform(low, high)
        volume = np.random.uniform(1000, 10000)

        data.append(
            {
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "timestamp": datetime.now() - timedelta(hours=rows - i),
            }
        )

    return pd.DataFrame(data)


def test_technical_indicators():
    """テクニカル指標テスト."""
    print("\n🔧 === テクニカル指標テスト ===")

    try:
        # サンプルデータ生成
        df = create_sample_data(100)
        print(f"📊 サンプルデータ: {len(df)}行")

        # TechnicalIndicators初期化
        tech_indicators = TechnicalIndicators()

        # 特徴量生成実行
        start_time = time.time()
        result_df = tech_indicators.generate_all_features(df)
        generation_time = time.time() - start_time

        # 結果検証
        feature_info = tech_indicators.get_feature_info()
        computed_features = feature_info["computed_features"]

        print(f"⏱️  生成時間: {generation_time:.3f}秒")
        print(f"📈 生成特徴量数: {len(computed_features)}")
        print(f"🎯 期待特徴量数: 20")

        # 各カテゴリの特徴量確認
        categories = feature_info["categories"]
        for category, features in categories.items():
            actual_features = [f for f in features if f in computed_features]
            print(f"  {category}: {len(actual_features)}/{len(features)}")

        # データ品質チェック
        nan_count = result_df[computed_features].isna().sum().sum()
        inf_count = (
            np.isinf(result_df[computed_features].select_dtypes(include=[np.number])).sum().sum()
        )

        print(f"🔍 データ品質:")
        print(f"  NaN値: {nan_count}")
        print(f"  無限値: {inf_count}")

        # テスト結果判定
        success = (
            len(computed_features) >= 17  # 最低17個（20個のうち一部失敗許容）
            and nan_count == 0
            and inf_count == 0
        )

        if success:
            print("✅ テクニカル指標テスト: PASS")
        else:
            print("❌ テクニカル指標テスト: FAIL")
            print(f"   期待: >=17特徴量、NaN=0、無限値=0")
            print(f"   実際: {len(computed_features)}特徴量、NaN={nan_count}、無限値={inf_count}")

        return success, result_df

    except Exception as e:
        print(f"❌ テクニカル指標テストエラー: {e}")
        import traceback

        traceback.print_exc()
        return False, None


def test_anomaly_detector():
    """異常検知指標テスト."""
    print("\n🔍 === 異常検知指標テスト ===")

    try:
        # サンプルデータ生成
        df = create_sample_data(100)
        print(f"📊 サンプルデータ: {len(df)}行")

        # AnomalyDetector初期化
        anomaly_detector = AnomalyDetector(lookback_period=20, threshold_multiplier=2.0)

        # 特徴量生成実行
        start_time = time.time()
        result_df = anomaly_detector.generate_all_features(df)
        generation_time = time.time() - start_time

        # 結果検証
        feature_info = anomaly_detector.get_feature_info()
        computed_features = feature_info["computed_features"]

        print(f"⏱️  生成時間: {generation_time:.3f}秒")
        print(f"📈 生成特徴量数: {len(computed_features)}")
        print(f"🎯 期待特徴量数: 4")

        # データ品質チェック
        nan_count = result_df[computed_features].isna().sum().sum()
        inf_count = (
            np.isinf(result_df[computed_features].select_dtypes(include=[np.number])).sum().sum()
        )

        print(f"🔍 データ品質:")
        print(f"  NaN値: {nan_count}")
        print(f"  無限値: {inf_count}")

        # 異常検知テスト
        if "market_stress" in computed_features:
            anomaly_flags = anomaly_detector.detect_anomalies(result_df, "market_stress")
            anomaly_rate = anomaly_flags.sum() / len(anomaly_flags) * 100
            print(f"🚨 異常検知結果: {anomaly_rate:.1f}%の期間で異常検出")

        # テスト結果判定
        success = (
            len(computed_features) >= 3  # 最低3個（4個のうち一部失敗許容）
            and nan_count == 0
            and inf_count == 0
        )

        if success:
            print("✅ 異常検知指標テスト: PASS")
        else:
            print("❌ 異常検知指標テスト: FAIL")
            print(f"   期待: >=3特徴量、NaN=0、無限値=0")
            print(f"   実際: {len(computed_features)}特徴量、NaN={nan_count}、無限値={inf_count}")

        return success, result_df

    except Exception as e:
        print(f"❌ 異常検知指標テストエラー: {e}")
        import traceback

        traceback.print_exc()
        return False, None


def test_integrated_system():
    """統合システムテスト."""
    print("\n🚀 === 統合システムテスト ===")

    try:
        # サンプルデータ生成
        df = create_sample_data(100)
        print(f"📊 サンプルデータ: {len(df)}行")

        # 両システム初期化
        tech_indicators = TechnicalIndicators()
        anomaly_detector = AnomalyDetector()

        # 統合特徴量生成
        start_time = time.time()

        # テクニカル指標生成
        result_df = tech_indicators.generate_all_features(df)

        # 異常検知指標追加
        result_df = anomaly_detector.generate_all_features(result_df)

        generation_time = time.time() - start_time

        # 統合結果検証
        tech_features = tech_indicators.get_feature_info()["computed_features"]
        anomaly_features = anomaly_detector.get_feature_info()["computed_features"]
        total_features = set(tech_features) | set(anomaly_features)

        print(f"⏱️  総生成時間: {generation_time:.3f}秒")
        print(f"📈 テクニカル指標: {len(tech_features)}個")
        print(f"🔍 異常検知指標: {len(anomaly_features)}個")
        print(f"🎯 総特徴量数: {len(total_features)}")

        # データ品質最終チェック
        all_feature_cols = [col for col in result_df.columns if col != "timestamp"]
        final_nan_count = result_df[all_feature_cols].isna().sum().sum()
        final_inf_count = (
            np.isinf(result_df[all_feature_cols].select_dtypes(include=[np.number])).sum().sum()
        )

        print(f"🔍 最終データ品質:")
        print(f"  総NaN値: {final_nan_count}")
        print(f"  総無限値: {final_inf_count}")

        # パフォーマンス評価
        rows_per_second = len(df) / generation_time
        print(f"⚡ パフォーマンス: {rows_per_second:.1f} 行/秒")

        # テスト結果判定
        success = (
            len(total_features) >= 20  # 最低20個（24個のうち一部失敗許容）
            and final_nan_count == 0
            and final_inf_count == 0
            and generation_time < 5.0  # 5秒以内
        )

        if success:
            print("✅ 統合システムテスト: PASS")
        else:
            print("❌ 統合システムテスト: FAIL")
            print(f"   期待: >=20特徴量、NaN=0、無限値=0、<5秒")
            print(
                f"   実際: {len(total_features)}特徴量、NaN={final_nan_count}、無限値={final_inf_count}、{generation_time:.1f}秒"
            )

        return success

    except Exception as e:
        print(f"❌ 統合システムテストエラー: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """メインテスト実行."""
    print("🎯 Phase 3 特徴量エンジニアリング テスト開始")
    print("=" * 60)

    # ログ設定
    logger = get_logger()
    logger.info("Phase 3テスト開始")

    # テスト実行
    test_results = []

    # 1. テクニカル指標テスト
    tech_success, tech_df = test_technical_indicators()
    test_results.append(("テクニカル指標", tech_success))

    # 2. 異常検知指標テスト
    anomaly_success, anomaly_df = test_anomaly_detector()
    test_results.append(("異常検知指標", anomaly_success))

    # 3. 統合システムテスト
    integrated_success = test_integrated_system()
    test_results.append(("統合システム", integrated_success))

    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 テスト結果サマリー")
    print("=" * 60)

    passed_tests = 0
    total_tests = len(test_results)

    for test_name, success in test_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:20} : {status}")
        if success:
            passed_tests += 1

    print(f"\n🎯 合格率: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)")

    if passed_tests == total_tests:
        print("🎉 Phase 3 特徴量エンジニアリング実装完了！")
        logger.info("Phase 3テスト全合格")
    else:
        print("⚠️  一部テストが失敗しました。実装を確認してください。")
        logger.warning(f"Phase 3テスト: {passed_tests}/{total_tests}合格")

    return passed_tests == total_tests


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

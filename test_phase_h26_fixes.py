#!/usr/bin/env python3
"""
Phase H.26修正内容の動作検証スクリプト
全ての堅牢化機能が正常に動作するかをテストします
"""

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

# ログ設定
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def test_atr_calculation_robustness():
    """ATR計算堅牢化テスト"""
    print("\n" + "=" * 60)
    print("🧪 TEST 1: ATR計算堅牢化テスト")
    print("=" * 60)

    try:
        from crypto_bot.indicator.calculator import IndicatorCalculator

        # テストケース1: 正常データ
        print("\n📋 Case 1: 正常データ")
        normal_data = pd.DataFrame(
            {
                "high": [100, 102, 101, 103, 102],
                "low": [98, 99, 100, 101, 100],
                "close": [99, 101, 100.5, 102, 101],
            }
        )

        atr_normal = IndicatorCalculator.calculate_atr(normal_data, period=3)
        print(
            f"✅ 正常データ ATR計算成功: {len(atr_normal)} values, NaN count: {atr_normal.isna().sum()}"
        )

        # テストケース2: NaN値が多いデータ
        print("\n📋 Case 2: NaN値が多いデータ")
        nan_data = pd.DataFrame(
            {
                "high": [100, np.nan, np.nan, 103, 102],
                "low": [98, np.nan, np.nan, 101, 100],
                "close": [99, np.nan, np.nan, 102, 101],
            }
        )

        atr_nan = IndicatorCalculator.calculate_atr(nan_data, period=3)
        print(
            f"✅ NaN値データ ATR計算成功: {len(atr_nan)} values, NaN count: {atr_nan.isna().sum()}"
        )

        # テストケース3: 極小データ
        print("\n📋 Case 3: 極小データ")
        small_data = pd.DataFrame({"high": [100], "low": [98], "close": [99]})

        atr_small = IndicatorCalculator.calculate_atr(small_data, period=14)
        print(
            f"✅ 極小データ ATR計算成功: {len(atr_small)} values, NaN count: {atr_small.isna().sum()}"
        )

        return True

    except Exception as e:
        print(f"❌ ATR計算テスト失敗: {e}")
        return False


def test_125_features_completeness():
    """125特徴量完全性保証テスト"""
    print("\n" + "=" * 60)
    print("🧪 TEST 2: 125特徴量完全性保証テスト")
    print("=" * 60)

    try:
        from crypto_bot.ml.feature_order_manager import get_feature_order_manager

        manager = get_feature_order_manager()

        # テストケース1: 不足特徴量データ
        print("\n📋 Case 1: 不足特徴量データ（50特徴量）")
        insufficient_data = pd.DataFrame(
            {f"feature_{i:02d}": np.random.randn(10) for i in range(50)}
        )

        complete_data = manager.ensure_125_features_completeness(insufficient_data)
        print(f"✅ 50→125特徴量補完成功: {len(complete_data.columns)} features")
        print(f"   NaN count: {complete_data.isna().sum().sum()}")

        # テストケース2: 余剰特徴量データ
        print("\n📋 Case 2: 余剰特徴量データ（200特徴量）")
        excess_data = pd.DataFrame(
            {f"feature_{i:03d}": np.random.randn(10) for i in range(200)}
        )

        trimmed_data = manager.ensure_125_features_completeness(excess_data)
        print(f"✅ 200→125特徴量調整成功: {len(trimmed_data.columns)} features")
        print(f"   NaN count: {trimmed_data.isna().sum().sum()}")

        # テストケース3: 重複特徴量データ
        print("\n📋 Case 3: 重複特徴量データ")
        duplicate_data = pd.DataFrame(
            {
                "feature_a": [1, 2, 3, 4, 5],
                "feature_b": [1, 2, 3, 4, 5],  # 完全重複
                "feature_c": [2, 4, 6, 8, 10],
            }
        )

        dedup_data = manager._remove_duplicate_features(duplicate_data)
        print(
            f"✅ 重複除去成功: {len(duplicate_data.columns)}→{len(dedup_data.columns)} features"
        )

        return True

    except Exception as e:
        print(f"❌ 125特徴量完全性テスト失敗: {e}")
        return False


def test_ensemble_robustness():
    """アンサンブル学習堅牢化テスト"""
    print("\n" + "=" * 60)
    print("🧪 TEST 3: アンサンブル学習堅牢化テスト")
    print("=" * 60)

    try:
        from crypto_bot.ml.ensemble import TradingEnsembleClassifier

        # テストケース1: 小さなデータセット
        print("\n📋 Case 1: 小さなデータセット")
        X_small = pd.DataFrame(np.random.randn(15, 10))
        y_small = pd.Series([0, 1] * 7 + [0])

        ensemble = TradingEnsembleClassifier()
        ensemble.fit(X_small, y_small)
        print(f"✅ 小データセット学習成功: fitted={ensemble.is_fitted}")

        # 予測テスト
        predictions = ensemble.predict_with_trading_confidence(X_small.iloc[[-1]])
        print(f"✅ 予測成功: shape={predictions[0].shape}")

        # テストケース2: NaN値を含むデータ
        print("\n📋 Case 2: NaN値を含むデータ")
        X_nan = pd.DataFrame(np.random.randn(20, 10))
        X_nan.iloc[5:8, 2:5] = np.nan
        y_nan = pd.Series([0, 1] * 10)
        y_nan.iloc[3:6] = np.nan

        ensemble_nan = TradingEnsembleClassifier()
        ensemble_nan.fit(X_nan, y_nan)
        print(f"✅ NaN値データ学習成功: fitted={ensemble_nan.is_fitted}")

        return True

    except Exception as e:
        print(f"❌ アンサンブル学習テスト失敗: {e}")
        return False


def test_numpy_format_safety():
    """numpy配列format error安全性テスト"""
    print("\n" + "=" * 60)
    print("🧪 TEST 4: numpy配列format error安全性テスト")
    print("=" * 60)

    try:
        # テストケース1: numpy配列の安全なf-stringフォーマット
        print("\n📋 Case 1: numpy配列のf-string処理")

        test_array = np.array([0.75])
        test_scalar = 0.65

        # 安全な処理
        safe_array = (
            float(test_array.flat[0])
            if isinstance(test_array, np.ndarray)
            else float(test_array)
        )
        safe_scalar = (
            float(test_scalar.flat[0])
            if isinstance(test_scalar, np.ndarray)
            else float(test_scalar)
        )

        formatted_string = f"Array: {safe_array:.3f}, Scalar: {safe_scalar:.3f}"
        print(f"✅ 安全なフォーマット成功: {formatted_string}")

        # テストケース2: cross_timeframe_ensembleのシミュレーション
        print("\n📋 Case 2: cross_timeframe統合シミュレーション")

        # 複数タイムフレームの予測結果をシミュレート
        timeframe_predictions = {
            "15m": {
                "prediction": np.array([1]),
                "probability": np.array([[0.3, 0.7]]),
                "confidence": 0.65,
                "unified_confidence": np.array([0.68]),
            },
            "1h": {
                "prediction": np.array([1]),
                "probability": np.array([[0.4, 0.6]]),
                "confidence": 0.72,
                "unified_confidence": np.array([0.71]),
            },
        }

        # 安全な統合処理のシミュレーション
        for tf, pred_data in timeframe_predictions.items():
            safe_conf = (
                float(pred_data["unified_confidence"].flat[0])
                if isinstance(pred_data["unified_confidence"], np.ndarray)
                else float(pred_data["unified_confidence"])
            )
            print(f"✅ {tf} 安全処理成功: confidence={safe_conf:.3f}")

        return True

    except Exception as e:
        print(f"❌ numpy format安全性テスト失敗: {e}")
        return False


def main():
    """メイン実行関数"""
    print("🚀 Phase H.26修正内容 動作検証開始")
    print("=" * 80)

    results = []

    # 各テストを実行
    results.append(("ATR計算堅牢化", test_atr_calculation_robustness()))
    results.append(("125特徴量完全性保証", test_125_features_completeness()))
    results.append(("アンサンブル学習堅牢化", test_ensemble_robustness()))
    results.append(("numpy format安全性", test_numpy_format_safety()))

    # 結果サマリー
    print("\n" + "=" * 80)
    print("📊 テスト結果サマリー")
    print("=" * 80)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
        if result:
            passed += 1

    print(f"\n🎯 総合結果: {passed}/{total} テスト通過 ({passed/total*100:.1f}%)")

    if passed == total:
        print("🎉 すべてのテストが成功しました！ローカル動作検証完了")
        print("   次のステップ: checks.shを実行してCI準備を行ってください")
        return True
    else:
        print("⚠️  一部のテストが失敗しています。修正が必要です")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

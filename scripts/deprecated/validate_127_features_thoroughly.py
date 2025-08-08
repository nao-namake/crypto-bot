#!/usr/bin/env python3
"""
127特徴量徹底検証スクリプト
ダミー値・フォールバック値・不自然なパターンを厳格に検出

検証項目:
1. 定数値・ゼロ埋め検出
2. 不自然に均一な分布の検出
3. NaN値過多の検出
4. 統計的妥当性の検証
5. テクニカル指標間の期待される関係性の検証
"""

import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from crypto_bot.ml.feature_order_manager import FeatureOrderManager
from crypto_bot.ml.preprocessor import FeatureEngineer


def create_realistic_test_data():
    """より現実的なテスト用OHLCVデータを生成"""
    np.random.seed(42)
    n_rows = 1000  # より多くのデータで検証

    # リアルなBTC価格動きをシミュレート
    base_price = 45000
    returns = np.random.normal(0, 0.015, n_rows)  # 1.5%標準偏差
    log_returns = np.cumsum(returns)
    close_prices = base_price * np.exp(log_returns)

    # OHLCを現実的に生成
    intraday_ranges = np.random.exponential(0.01, n_rows)  # 日中レンジ

    data = pd.DataFrame(
        {
            "timestamp": pd.date_range(start="2024-01-01", periods=n_rows, freq="1H"),
            "close": close_prices,
        }
    )

    # Open: 前のcloseの近辺
    data["open"] = data["close"].shift(1).fillna(close_prices[0]) * (
        1 + np.random.normal(0, 0.002, n_rows)
    )

    # High/Low: Open/Closeを考慮した現実的な値
    oc_max = np.maximum(data["open"], data["close"])
    oc_min = np.minimum(data["open"], data["close"])
    data["high"] = oc_max * (1 + np.abs(np.random.normal(0, 0.005, n_rows)))
    data["low"] = oc_min * (1 - np.abs(np.random.normal(0, 0.005, n_rows)))

    # Volume: 現実的な分布
    data["volume"] = np.random.lognormal(np.log(500), 0.5, n_rows)

    return data


def detect_suspicious_patterns(series, feature_name):
    """疑わしいパターンを検出（バイナリ・イベント特徴量考慮版）"""
    issues = []

    # 基本統計
    non_null_values = series.dropna()
    if len(non_null_values) == 0:
        return ["All NaN values"]

    unique_count = non_null_values.nunique()
    total_count = len(non_null_values)

    # バイナリ・イベント系特徴量の判定
    is_binary_feature = (
        "overbought" in feature_name
        or "oversold" in feature_name
        or "cross_" in feature_name
        or "breakout" in feature_name
        or "is_" in feature_name
        or feature_name in ["hammer", "doji", "pinbar", "engulfing"]
        or "weekend" in feature_name
        or "session" in feature_name
        or feature_name == "bb_squeeze"
        or feature_name == "volatility_regime"
        or feature_name in ["market_phase", "trend_direction"]
    )

    # 1. 定数値検出
    if unique_count == 1:
        issues.append(f"Constant value: {non_null_values.iloc[0]}")

    # 2. 異常に少ないユニーク値（バイナリ特徴量は除外）
    elif not is_binary_feature and unique_count < max(5, total_count * 0.01):
        issues.append(
            f"Too few unique values: {unique_count}/{total_count} ({unique_count/total_count*100:.1f}%)"
        )

    # 3. ゼロ埋めパターン（バイナリ・イベント特徴量は除外）
    zero_ratio = (non_null_values == 0).sum() / len(non_null_values)
    if not is_binary_feature and zero_ratio > 0.9:
        issues.append(f"Mostly zeros: {zero_ratio*100:.1f}%")
    elif (
        is_binary_feature and zero_ratio > 0.995
    ):  # バイナリ特徴量は99.5%以上で疑わしい
        issues.append(f"Almost all zeros (binary): {zero_ratio*100:.1f}%")

    # 4. NaN値過多
    nan_ratio = series.isna().sum() / len(series)
    if nan_ratio > 0.5:
        issues.append(f"Too many NaN: {nan_ratio*100:.1f}%")

    # 5. 不自然に均一な分布（連続値特徴量のみ）
    if not is_binary_feature and unique_count > 10:
        try:
            # Kolmogorov-Smirnov test for uniformity
            normalized = (non_null_values - non_null_values.min()) / (
                non_null_values.max() - non_null_values.min() + 1e-8
            )
            ks_stat, p_value = stats.kstest(normalized, "uniform")
            if p_value > 0.95:  # 均一すぎる分布
                issues.append(f"Suspiciously uniform distribution (p={p_value:.3f})")
        except:
            pass

    # 6. 明らかにダミーな値パターン
    if feature_name.startswith("enhanced_default_"):
        issues.append("Enhanced default feature name pattern")

    # 7. 特定の特徴量に対する妥当性チェック（より正確に）
    if feature_name.lower().startswith("rsi_") and not any(
        x in feature_name for x in ["overbought", "oversold"]
    ):
        if non_null_values.min() < 0 or non_null_values.max() > 100:
            issues.append(
                f"RSI out of valid range [0,100]: [{non_null_values.min():.2f}, {non_null_values.max():.2f}]"
            )

    if feature_name.lower().startswith("stoch_") and not any(
        x in feature_name for x in ["overbought", "oversold"]
    ):
        if non_null_values.min() < 0 or non_null_values.max() > 100:
            issues.append(
                f"Stochastic out of valid range [0,100]: [{non_null_values.min():.2f}, {non_null_values.max():.2f}]"
            )

    # 8. 明らかに不自然な値範囲（フォールバック値検出）
    if not is_binary_feature:
        # 全て同じ値に近い（標準偏差が非常に小さい）
        if len(non_null_values) > 10:
            std_dev = non_null_values.std()
            mean_val = non_null_values.mean()
            if abs(mean_val) > 1e-6 and std_dev / abs(mean_val) < 1e-6:
                issues.append(
                    f"Suspiciously low variance: std/mean = {std_dev/abs(mean_val):.2e}"
                )

    return issues


def validate_technical_relationships(features):
    """テクニカル指標間の期待される関係性を検証"""
    relationship_issues = []

    # SMA関係の検証 (短期 > 長期 in uptrend, vice versa)
    sma_features = {k: v for k, v in features.items() if k.startswith("sma_")}
    if len(sma_features) >= 2:
        sma_periods = []
        for name, series in sma_features.items():
            try:
                period = int(name.split("_")[1])
                sma_periods.append((period, name, series))
            except:
                continue

        sma_periods.sort()  # 期間順にソート

        # 短期と長期SMAの関係をチェック
        for i in range(len(sma_periods) - 1):
            short_period, short_name, short_series = sma_periods[i]
            long_period, long_name, long_series = sma_periods[i + 1]

            # 非常に近い値の場合は疑わしい
            if len(short_series) > 50:
                correlation = short_series.tail(50).corr(long_series.tail(50))
                if correlation > 0.999:  # ほぼ完全相関は不自然
                    relationship_issues.append(
                        f"{short_name} and {long_name} too similar (corr={correlation:.4f})"
                    )

    # EMA関係の検証
    ema_features = {k: v for k, v in features.items() if k.startswith("ema_")}
    if len(ema_features) >= 2:
        # Similar logic for EMA...
        pass

    # RSI overbought/oversold関係の検証
    if "rsi_14" in features and "rsi_overbought" in features:
        rsi_14 = features["rsi_14"].dropna()
        rsi_ob = features["rsi_overbought"].dropna()
        if len(rsi_14) > 0 and len(rsi_ob) > 0:
            # RSI > 70の時にrsi_overbought = 1である割合をチェック
            high_rsi_mask = rsi_14 > 70
            if high_rsi_mask.sum() > 0:
                agreement_ratio = (
                    rsi_ob[high_rsi_mask] == 1
                ).sum() / high_rsi_mask.sum()
                if agreement_ratio < 0.8:  # 80%未満の一致は疑わしい
                    relationship_issues.append(
                        f"RSI_14 and rsi_overbought inconsistent (agreement={agreement_ratio:.2f})"
                    )

    return relationship_issues


def thorough_validation():
    """徹底的な検証を実行"""
    print("=" * 100)
    print("127特徴量徹底検証（ダミー値・フォールバック検出）")
    print("=" * 100)

    # より厳しいテスト条件でデータ生成
    data = create_realistic_test_data()
    print(
        f"テストデータ: {len(data)}行 x {len(data.columns)}列（より現実的なBTC価格シミュレーション）"
    )

    # FeatureEngineer初期化（127特徴量対応設定）
    config = {
        "ml": {
            "feat_period": 14,
            "lags": [1, 2, 3],
            "rolling_window": 10,
            "horizon": 5,
            "target_type": "classification",
            # 127特徴量の主要なテクニカル指標を設定
            "extra_features": [
                # 基本OHLCV
                "open",
                "high",
                "low",
                "close",
                "volume",
                # RSI系
                "rsi_7",
                "rsi_14",
                "rsi_21",
                "rsi_overbought",
                "rsi_oversold",
                # SMA系
                "sma_5",
                "sma_10",
                "sma_20",
                "sma_50",
                "sma_100",
                "sma_200",
                # EMA系
                "ema_5",
                "ema_10",
                "ema_20",
                "ema_50",
                "ema_100",
                "ema_200",
                # ATR系
                "atr_7",
                "atr_14",
                "atr_21",
                # MACD系
                "macd",
                "macd_signal",
                "macd_hist",
                "macd_cross_up",
                "macd_cross_down",
                # Bollinger Bands
                "bb_upper",
                "bb_middle",
                "bb_lower",
                "bb_width",
                "bb_position",
                "bb_squeeze",
                # Stochastic
                "stoch_k",
                "stoch_d",
                "stoch_overbought",
                "stoch_oversold",
                # ADX
                "adx_14",
                "plus_di",
                "minus_di",
                # ボラティリティ
                "volatility_20",
                "volatility_50",
                "volatility_ratio",
                # ボリューム関連
                "volume_sma_20",
                "volume_ratio",
                "volume_trend",
                # その他の重要な指標
                "williams_r",
                "cci_20",
                "mfi",
                "obv",
                "obv_sma",
                "true_range",
                "high_low_ratio",
                "vwap",
                "vwap_distance",
                # 価格位置・リターン
                "price_position_20",
                "price_position_50",
                "price_vs_sma20",
                "returns_1",
                "returns_2",
                "returns_3",
                "returns_5",
                "returns_10",
                "log_returns_1",
                "log_returns_2",
                "log_returns_3",
                "log_returns_5",
                "log_returns_10",
                # ラグ特徴量
                "close_lag_1",
                "close_lag_2",
                "close_lag_3",
                "close_lag_4",
                "close_lag_5",
                "volume_lag_1",
                "volume_lag_2",
                "volume_lag_3",
                "volume_lag_4",
                "volume_lag_5",
                # 時間特徴量
                "hour",
                "day_of_week",
                "is_weekend",
                "is_asian_session",
                "is_european_session",
                "is_us_session",
                # その他
                "momentum_14",
                "trend_strength",
                "trend_direction",
                "close_mean_10",
                "close_std_10",
            ],
        }
    }

    engineer = FeatureEngineer(config)

    # 特徴量生成実行
    print("\n特徴量生成実行中（厳格検証モード）...")
    features = engineer.fit_transform(data)

    print(f"生成された特徴量: {len(features.columns)}列")

    # 127特徴量との比較
    expected_features = set(FeatureOrderManager.FEATURE_ORDER_127)
    generated_features = set(features.columns)

    # 実装状況分析
    implemented = expected_features & generated_features
    missing = expected_features - generated_features
    extra = generated_features - expected_features

    print(f"\n【基本実装状況】")
    print(f"期待特徴量数: {len(expected_features)}")
    print(f"実装済み特徴量数: {len(implemented)}")
    print(f"実装率: {len(implemented)/len(expected_features)*100:.1f}%")

    # 厳格な品質検証
    print(f"\n【厳格品質検証】")
    suspicious_features = {}
    clean_features = {}

    for feature in implemented:
        if feature in features.columns:
            issues = detect_suspicious_patterns(features[feature], feature)
            if issues:
                suspicious_features[feature] = issues
            else:
                clean_features[feature] = features[feature]

    print(f"\n疑わしい特徴量: {len(suspicious_features)}個")
    if suspicious_features:
        for feature, issues in suspicious_features.items():
            print(f"  ⚠️ {feature}:")
            for issue in issues:
                print(f"    - {issue}")
    else:
        print(f"  なし（全て健全）")

    print(f"\n健全な特徴量: {len(clean_features)}個")

    # テクニカル指標間の関係性検証
    print(f"\n【テクニカル指標関係性検証】")
    relationship_issues = validate_technical_relationships(features)
    if relationship_issues:
        print(f"関係性の問題: {len(relationship_issues)}個")
        for issue in relationship_issues:
            print(f"  ⚠️ {issue}")
    else:
        print("テクニカル指標間の関係性は正常")

    # 統計サマリー（上位10特徴量）
    print(f"\n【健全特徴量統計サマリー（上位10）】")
    for i, (feature, series) in enumerate(list(clean_features.items())[:10]):
        non_null = series.dropna()
        if len(non_null) > 0:
            print(
                f"  ✅ {feature}: unique={non_null.nunique()}, "
                f"range=[{non_null.min():.3f}, {non_null.max():.3f}], "
                f"mean={non_null.mean():.3f}, std={non_null.std():.3f}"
            )

    # 最終評価
    true_implementation_rate = len(clean_features) / len(expected_features) * 100
    total_issues = len(suspicious_features) + len(relationship_issues)

    print(f"\n【最終評価】")
    print(
        f"真の実装率: {true_implementation_rate:.1f}% ({len(clean_features)}/{len(expected_features)})"
    )
    print(f"総問題数: {total_issues}")

    if true_implementation_rate >= 95 and total_issues == 0:
        print("✅ 127特徴量システムは真に完全実装されています！")
        return True
    elif true_implementation_rate >= 80 and total_issues <= 5:
        print("⚠️ 概ね良好ですが、いくつかの改善点があります")
        return False
    else:
        print("❌ 重大な問題があります。ダミー値・フォールバック値が多用されています")
        return False


if __name__ == "__main__":
    try:
        success = thorough_validation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"検証エラー: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

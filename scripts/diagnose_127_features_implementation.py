#!/usr/bin/env python3
"""
127特徴量実装率完全診断スクリプト
デフォルト値依存特徴量を特定し、実装率100%達成のためのガイドを提供
"""

import os
import sys

import numpy as np
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from crypto_bot.ml.feature_order_manager import FeatureOrderManager
from crypto_bot.ml.preprocessor import FeatureEngineer


def create_test_data():
    """テスト用のOHLCVデータを生成"""
    np.random.seed(42)
    n_rows = 500  # 十分なデータサイズ

    # リアルな価格データを生成
    base_price = 45000  # BTC/JPY基準価格
    price_changes = np.random.normal(0, 0.02, n_rows)  # 2%標準偏差
    cumulative_changes = np.cumsum(price_changes)

    # OHLCV生成
    close_prices = base_price * (1 + cumulative_changes)

    data = pd.DataFrame(
        {
            "timestamp": pd.date_range(start="2024-01-01", periods=n_rows, freq="1H"),
            "open": close_prices * (1 + np.random.normal(0, 0.005, n_rows)),
            "high": close_prices * (1 + np.abs(np.random.normal(0, 0.01, n_rows))),
            "low": close_prices * (1 - np.abs(np.random.normal(0, 0.01, n_rows))),
            "close": close_prices,
            "volume": np.random.uniform(100, 1000, n_rows),
        }
    )

    # high >= close >= low の論理修正
    data["high"] = np.maximum(data["high"], data[["open", "close"]].max(axis=1))
    data["low"] = np.minimum(data["low"], data[["open", "close"]].min(axis=1))

    return data


def analyze_feature_implementation():
    """127特徴量の実装状況を完全分析"""
    print("=" * 80)
    print("127特徴量実装状況完全診断")
    print("=" * 80)

    # テストデータ作成
    data = create_test_data()
    print(f"テストデータ: {len(data)}行 x {len(data.columns)}列")

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
    print("\n特徴量生成実行中...")
    # FeatureEngineerのfit_transform使用
    features = engineer.fit_transform(data)

    print(f"生成された特徴量: {len(features.columns)}列")

    # 127特徴量との比較
    expected_features = set(FeatureOrderManager.FEATURE_ORDER_127)
    generated_features = set(features.columns)

    # 実装状況分析
    implemented = expected_features & generated_features
    missing = expected_features - generated_features
    extra = generated_features - expected_features

    print(f"\n【実装状況サマリー】")
    print(f"期待特徴量数: {len(expected_features)}")
    print(f"実装済み特徴量数: {len(implemented)}")
    print(f"実装率: {len(implemented)/len(expected_features)*100:.1f}%")

    # デフォルト値依存チェック
    default_dependent = []
    properly_implemented = []

    for feature in implemented:
        if feature in features.columns:
            values = features[feature].dropna()
            if len(values) > 0:
                # デフォルト値パターンをチェック
                unique_values = values.nunique()
                is_constant = unique_values <= 1
                is_zero_filled = (values == 0).all()
                is_default_pattern = is_constant or is_zero_filled

                if is_default_pattern:
                    default_dependent.append(
                        {
                            "feature": feature,
                            "unique_values": unique_values,
                            "sample_value": values.iloc[0] if len(values) > 0 else None,
                            "is_zero_filled": is_zero_filled,
                        }
                    )
                else:
                    properly_implemented.append(
                        {
                            "feature": feature,
                            "unique_values": unique_values,
                            "min_value": values.min(),
                            "max_value": values.max(),
                            "mean_value": values.mean(),
                        }
                    )

    print(f"\n【デフォルト値依存特徴量】({len(default_dependent)}個)")
    if default_dependent:
        for item in default_dependent:
            print(
                f"  - {item['feature']}: unique={item['unique_values']}, "
                f"sample={item['sample_value']}, zero_filled={item['is_zero_filled']}"
            )
    else:
        print("  なし（素晴らしい！）")

    print(f"\n【適切に実装された特徴量】({len(properly_implemented)}個)")
    for item in properly_implemented[:10]:  # 最初の10個を表示
        print(
            f"  - {item['feature']}: unique={item['unique_values']}, "
            f"range=[{item['min_value']:.3f}, {item['max_value']:.3f}], "
            f"mean={item['mean_value']:.3f}"
        )
    if len(properly_implemented) > 10:
        print(f"  ... および他{len(properly_implemented)-10}個")

    print(f"\n【未実装特徴量】({len(missing)}個)")
    if missing:
        for feature in sorted(missing):
            print(f"  - {feature}")
    else:
        print("  なし（完璧！）")

    print(f"\n【余剰特徴量】({len(extra)}個)")
    if extra:
        for feature in sorted(extra):
            print(f"  - {feature}")
    else:
        print("  なし")

    # 実装優先度の提案
    print(f"\n【実装優先度ガイド】")
    if missing:
        print("1. 未実装特徴量の実装（technical_engine.pyに追加）")
        # 基本的なテクニカル指標を優先
        basic_indicators = [
            f
            for f in missing
            if any(
                keyword in f.lower()
                for keyword in ["sma", "ema", "rsi", "macd", "bb", "atr", "stoch"]
            )
        ]
        if basic_indicators:
            print(f"   優先度高: {basic_indicators}")

    if default_dependent:
        print("2. デフォルト値依存特徴量の修正")
        print("   - ゼロ埋めや定数値の特徴量を実際の計算で置き換える")

    # 最終推奨アクション
    current_quality = len(properly_implemented) / len(expected_features) * 100
    print(f"\n【現在のシステム品質】")
    print(
        f"真の実装率: {current_quality:.1f}% ({len(properly_implemented)}/{len(expected_features)})"
    )

    if current_quality < 80:
        print("⚠️  実装率が低すぎます。バックテスト損失の主要因と考えられます。")
        print("   technical_engine.pyの大幅な改修が必要です。")
    elif current_quality < 95:
        print("⚠️  実装率改善の余地があります。")
        print("   重要な特徴量の実装により取引性能が向上する可能性があります。")
    else:
        print("✅ 実装率は良好です！")

    return {
        "implemented": len(implemented),
        "missing": len(missing),
        "default_dependent": len(default_dependent),
        "properly_implemented": len(properly_implemented),
        "implementation_rate": len(implemented) / len(expected_features) * 100,
        "quality_rate": current_quality,
    }


if __name__ == "__main__":
    try:
        result = analyze_feature_implementation()
        print(f"\n診断完了:")
        print(f"実装率: {result['implementation_rate']:.1f}%")
        print(f"品質率: {result['quality_rate']:.1f}%")

        # 深刻な問題がある場合は終了コード1
        if result["quality_rate"] < 50:
            sys.exit(1)

    except Exception as e:
        print(f"診断エラー: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

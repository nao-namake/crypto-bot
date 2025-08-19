#!/usr/bin/env python3
"""
127特徴量詳細分析・重複特徴量特定・厳選スクリプト
段階的特徴量最適化アプローチ
"""

import json
import logging
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_current_127_features():
    """現在の127特徴量リスト取得"""
    features_127 = [
        # 基本OHLCV + ラグ (13特徴量)
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_lag_1",
        "close_lag_2",
        "close_lag_3",
        "close_lag_4",
        "close_lag_5",
        "volume_lag_1",
        "volume_lag_2",
        "volume_lag_3",
        # リターン系 (10特徴量)
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
        # 移動平均系 (12特徴量)
        "sma_5",
        "sma_10",
        "sma_20",
        "sma_50",
        "sma_100",
        "sma_200",
        "ema_5",
        "ema_10",
        "ema_20",
        "ema_50",
        "ema_100",
        "ema_200",
        # 価格ポジション (5特徴量)
        "price_position_20",
        "price_position_50",
        "price_vs_sma20",
        "bb_position",
        "intraday_position",
        # ボリンジャーバンド (5特徴量)
        "bb_upper",
        "bb_middle",
        "bb_lower",
        "bb_width",
        "bb_squeeze",
        # RSI系 (5特徴量)
        "rsi_14",
        "rsi_7",
        "rsi_21",
        "rsi_oversold",
        "rsi_overbought",
        # MACD系 (5特徴量)
        "macd",
        "macd_signal",
        "macd_hist",
        "macd_cross_up",
        "macd_cross_down",
        # ストキャスティクス (4特徴量)
        "stoch_k",
        "stoch_d",
        "stoch_oversold",
        "stoch_overbought",
        # ATR・ボラティリティ (8特徴量)
        "atr_14",
        "atr_7",
        "atr_21",
        "volatility_20",
        "volatility_50",
        "high_low_ratio",
        "true_range",
        "volatility_ratio",
        # ボリューム分析 (10特徴量)
        "volume_sma_20",
        "volume_ratio",
        "volume_trend",
        "vwap",
        "vwap_distance",
        "obv",
        "obv_sma",
        "cmf",
        "mfi",
        "ad_line",
        # トレンド・モメンタム (9特徴量)
        "adx_14",
        "plus_di",
        "minus_di",
        "trend_strength",
        "trend_direction",
        "cci_20",
        "williams_r",
        "ultimate_oscillator",
        "momentum_14",
        # サポート・レジスタンス (6特徴量)
        "support_distance",
        "resistance_distance",
        "support_strength",
        "volume_breakout",
        "price_breakout_up",
        "price_breakout_down",
        # ローソク足パターン (4特徴量)
        "doji",
        "hammer",
        "engulfing",
        "pinbar",
        # 統計・高度分析 (5特徴量)
        "skewness_20",
        "kurtosis_20",
        "zscore",
        "mean_reversion_20",
        "mean_reversion_50",
        # 時間特徴量 (6特徴量)
        "hour",
        "day_of_week",
        "is_weekend",
        "is_asian_session",
        "is_european_session",
        "is_us_session",
        # 追加テクニカル (16特徴量)
        "roc_10",
        "roc_20",
        "trix",
        "mass_index",
        "keltner_upper",
        "keltner_lower",
        "donchian_upper",
        "donchian_lower",
        "ichimoku_conv",
        "ichimoku_base",
        "price_efficiency",
        "trend_consistency",
        "volume_price_correlation",
        "volatility_regime",
        "momentum_quality",
        "market_phase",
        # 追加統計 (2特徴量)
        "close_mean_10",
        "close_std_10",
    ]

    return features_127


def categorize_features(features):
    """特徴量をカテゴリ別に分類"""
    categories = {
        "basic_ohlcv": [],
        "lag_features": [],
        "returns": [],
        "moving_averages": [],
        "price_position": [],
        "bollinger_bands": [],
        "rsi_family": [],
        "macd_family": [],
        "stochastic": [],
        "volatility_atr": [],
        "volume_analysis": [],
        "trend_momentum": [],
        "support_resistance": [],
        "candlestick_patterns": [],
        "statistical": [],
        "time_features": [],
        "advanced_technical": [],
        "other": [],
    }

    for feature in features:
        categorized = False

        # 基本OHLCV
        if feature in ["open", "high", "low", "close", "volume"]:
            categories["basic_ohlcv"].append(feature)
            categorized = True

        # ラグ特徴量
        elif "lag_" in feature:
            categories["lag_features"].append(feature)
            categorized = True

        # リターン系
        elif "returns_" in feature or "log_returns_" in feature:
            categories["returns"].append(feature)
            categorized = True

        # 移動平均
        elif feature.startswith(("sma_", "ema_")):
            categories["moving_averages"].append(feature)
            categorized = True

        # 価格ポジション
        elif "position" in feature or "price_vs_" in feature:
            categories["price_position"].append(feature)
            categorized = True

        # ボリンジャーバンド
        elif feature.startswith("bb_"):
            categories["bollinger_bands"].append(feature)
            categorized = True

        # RSI系
        elif feature.startswith("rsi_") or "rsi_" in feature:
            categories["rsi_family"].append(feature)
            categorized = True

        # MACD系
        elif feature.startswith("macd"):
            categories["macd_family"].append(feature)
            categorized = True

        # ストキャスティクス
        elif feature.startswith("stoch_"):
            categories["stochastic"].append(feature)
            categorized = True

        # ボラティリティ・ATR
        elif feature.startswith(("atr_", "volatility_")) or feature in [
            "true_range",
            "high_low_ratio",
            "volatility_ratio",
        ]:
            categories["volatility_atr"].append(feature)
            categorized = True

        # ボリューム分析
        elif "volume" in feature or feature in [
            "vwap",
            "vwap_distance",
            "obv",
            "obv_sma",
            "cmf",
            "mfi",
            "ad_line",
        ]:
            categories["volume_analysis"].append(feature)
            categorized = True

        # トレンド・モメンタム
        elif feature in [
            "adx_14",
            "plus_di",
            "minus_di",
            "trend_strength",
            "trend_direction",
            "cci_20",
            "williams_r",
            "ultimate_oscillator",
            "momentum_14",
            "momentum_quality",
        ]:
            categories["trend_momentum"].append(feature)
            categorized = True

        # サポート・レジスタンス
        elif "support" in feature or "resistance" in feature or "breakout" in feature:
            categories["support_resistance"].append(feature)
            categorized = True

        # ローソク足パターン
        elif feature in ["doji", "hammer", "engulfing", "pinbar"]:
            categories["candlestick_patterns"].append(feature)
            categorized = True

        # 統計系
        elif feature in [
            "skewness_20",
            "kurtosis_20",
            "zscore",
            "mean_reversion_20",
            "mean_reversion_50",
            "close_mean_10",
            "close_std_10",
        ]:
            categories["statistical"].append(feature)
            categorized = True

        # 時間特徴量
        elif feature in [
            "hour",
            "day_of_week",
            "is_weekend",
            "is_asian_session",
            "is_european_session",
            "is_us_session",
        ]:
            categories["time_features"].append(feature)
            categorized = True

        # 高度テクニカル
        elif feature in [
            "roc_10",
            "roc_20",
            "trix",
            "mass_index",
            "keltner_upper",
            "keltner_lower",
            "donchian_upper",
            "donchian_lower",
            "ichimoku_conv",
            "ichimoku_base",
            "price_efficiency",
            "trend_consistency",
            "volume_price_correlation",
            "volatility_regime",
            "market_phase",
        ]:
            categories["advanced_technical"].append(feature)
            categorized = True

        # その他
        if not categorized:
            categories["other"].append(feature)

    return categories


def identify_redundant_features(categories):
    """重複・冗長特徴量の特定"""
    redundant_groups = []

    # 1. 同一期間の移動平均（SMA vs EMA）
    sma_periods = set()
    ema_periods = set()

    for feature in categories["moving_averages"]:
        if feature.startswith("sma_"):
            period = feature.split("_")[1]
            sma_periods.add(period)
        elif feature.startswith("ema_"):
            period = feature.split("_")[1]
            ema_periods.add(period)

    common_periods = sma_periods.intersection(ema_periods)
    if common_periods:
        redundant_groups.append(
            {
                "type": "moving_average_duplication",
                "description": "同一期間のSMAとEMA（高相関）",
                "features": [f"sma_{p}" for p in common_periods]
                + [f"ema_{p}" for p in common_periods],
                "recommendation": f"各期間でSMAまたはEMAのどちらか一方を選択。推奨：EMA（より反応が早い）",
                "redundant_count": len(common_periods),
            }
        )

    # 2. 類似ATR計算（複数期間）
    atr_features = [f for f in categories["volatility_atr"] if f.startswith("atr_")]
    if len(atr_features) > 1:
        redundant_groups.append(
            {
                "type": "atr_multiple_periods",
                "description": "複数期間のATR（高相関）",
                "features": atr_features,
                "recommendation": "ATR_14のみ残す（標準的な期間）",
                "redundant_count": len(atr_features) - 1,
            }
        )

    # 3. 類似ボラティリティ指標
    volatility_features = [f for f in categories["volatility_atr"] if "volatility" in f]
    volatility_features.extend(["true_range", "high_low_ratio"])
    if len(volatility_features) > 2:
        redundant_groups.append(
            {
                "type": "volatility_indicators",
                "description": "複数のボラティリティ指標（概念的に類似）",
                "features": volatility_features,
                "recommendation": "volatility_20とatr_14を残す",
                "redundant_count": len(volatility_features) - 2,
            }
        )

    # 4. 類似RSI指標
    rsi_features = [
        f
        for f in categories["rsi_family"]
        if f.startswith("rsi_") and f not in ["rsi_oversold", "rsi_overbought"]
    ]
    if len(rsi_features) > 1:
        redundant_groups.append(
            {
                "type": "rsi_multiple_periods",
                "description": "複数期間のRSI（高相関）",
                "features": rsi_features,
                "recommendation": "rsi_14のみ残す（標準期間）",
                "redundant_count": len(rsi_features) - 1,
            }
        )

    # 5. 類似リターン計算
    returns_simple = [f for f in categories["returns"] if f.startswith("returns_")]
    returns_log = [f for f in categories["returns"] if f.startswith("log_returns_")]
    if len(returns_simple) > 0 and len(returns_log) > 0:
        redundant_groups.append(
            {
                "type": "returns_calculation_methods",
                "description": "単純リターンと対数リターン（類似情報）",
                "features": returns_simple + returns_log,
                "recommendation": "returns_1, returns_5のみ残す（log_returnsは削除）",
                "redundant_count": len(returns_log),
            }
        )

    # 6. 過剰なラグ特徴量
    lag_features = categories["lag_features"]
    if len(lag_features) > 3:
        redundant_groups.append(
            {
                "type": "excessive_lag_features",
                "description": "過剰なラグ特徴量（短期相関高）",
                "features": lag_features,
                "recommendation": "close_lag_1, close_lag_3, volume_lag_1のみ残す",
                "redundant_count": len(lag_features) - 3,
            }
        )

    # 7. 類似セッション時間
    session_features = [f for f in categories["time_features"] if "session" in f]
    if len(session_features) > 1:
        redundant_groups.append(
            {
                "type": "session_time_overlap",
                "description": "複数セッション時間（一部重複あり）",
                "features": session_features,
                "recommendation": "is_us_session, is_asian_sessionのみ残す",
                "redundant_count": len(session_features) - 2,
            }
        )

    # 8. 類似統計指標
    if len(categories["statistical"]) > 3:
        redundant_groups.append(
            {
                "type": "statistical_indicators",
                "description": "複数の統計指標（一部重複情報）",
                "features": categories["statistical"],
                "recommendation": "zscore, close_std_10のみ残す",
                "redundant_count": len(categories["statistical"]) - 2,
            }
        )

    return redundant_groups


def select_essential_features(categories):
    """取引に必要不可欠な特徴量の厳選"""
    essential_features = {
        "core_price_action": {
            "features": ["close", "volume", "high", "low"],
            "reason": "コア価格情報・必須",
        },
        "trend_identification": {
            "features": ["sma_20", "ema_50", "price_vs_sma20"],
            "reason": "トレンド判定・方向性確認",
        },
        "momentum_oscillators": {
            "features": ["rsi_14", "macd", "macd_signal"],
            "reason": "モメンタム・オシレーター分析",
        },
        "volatility_risk": {
            "features": ["atr_14", "volatility_20", "bb_width"],
            "reason": "ボラティリティ・リスク管理",
        },
        "volume_confirmation": {
            "features": ["volume_ratio", "vwap", "obv"],
            "reason": "ボリューム確認・流動性分析",
        },
        "short_term_momentum": {
            "features": ["returns_1", "close_lag_1"],
            "reason": "短期モメンタム・直近動向",
        },
        "support_resistance": {
            "features": ["bb_upper", "bb_lower", "support_distance"],
            "reason": "サポート・レジスタンス判定",
        },
        "market_timing": {
            "features": ["hour", "is_us_session"],
            "reason": "市場時間・流動性タイミング",
        },
        "advanced_signals": {
            "features": ["adx_14", "stoch_k", "williams_r"],
            "reason": "高度シグナル・確認指標",
        },
    }

    return essential_features


def create_optimized_feature_sets():
    """最適化された特徴量セット作成"""
    features_127 = get_current_127_features()
    categories = categorize_features(features_127)
    redundant_groups = identify_redundant_features(categories)
    essential_features = select_essential_features(categories)

    # 厳選特徴量リスト（Essential Set）
    essential_list = []
    for category, info in essential_features.items():
        essential_list.extend(info["features"])

    # 重複除去後特徴量リスト（Reduced Set）
    reduced_features = features_127.copy()

    # 重複特徴量を削除
    for group in redundant_groups:
        if group["type"] == "moving_average_duplication":
            # SMAを削除、EMAを残す
            for feature in group["features"]:
                if (
                    feature.startswith("sma_")
                    and feature.replace("sma_", "ema_") in reduced_features
                ):
                    if feature in reduced_features:
                        reduced_features.remove(feature)

        elif group["type"] == "atr_multiple_periods":
            # atr_14以外を削除
            for feature in group["features"]:
                if feature != "atr_14" and feature in reduced_features:
                    reduced_features.remove(feature)

        elif group["type"] == "rsi_multiple_periods":
            # rsi_14以外を削除
            for feature in group["features"]:
                if feature != "rsi_14" and feature in reduced_features:
                    reduced_features.remove(feature)

        elif group["type"] == "returns_calculation_methods":
            # log_returnsを削除
            for feature in group["features"]:
                if feature.startswith("log_returns_") and feature in reduced_features:
                    reduced_features.remove(feature)

        elif group["type"] == "excessive_lag_features":
            # 必要最小限のラグのみ残す
            keep_lags = ["close_lag_1", "close_lag_3", "volume_lag_1"]
            for feature in group["features"]:
                if feature not in keep_lags and feature in reduced_features:
                    reduced_features.remove(feature)

    return {
        "original_127": features_127,
        "categories": categories,
        "redundant_groups": redundant_groups,
        "essential_features": essential_features,
        "essential_list": list(set(essential_list)),
        "reduced_features": reduced_features,
    }


def main():
    """メイン実行"""
    logger.info("=" * 80)
    logger.info("127特徴量詳細分析・重複特徴量特定・最適化")
    logger.info("=" * 80)

    # 分析実行
    analysis_result = create_optimized_feature_sets()

    # 結果表示
    logger.info(f"元の特徴量数: {len(analysis_result['original_127'])}")

    print("\n" + "=" * 80)
    print("📊 127特徴量カテゴリ別分析結果")
    print("=" * 80)

    for category, features in analysis_result["categories"].items():
        if features:
            print(f"\n🔍 {category.replace('_', ' ').title()}: {len(features)}個")
            for i, feature in enumerate(features, 1):
                print(f"  {i:2d}. {feature}")

    print("\n" + "=" * 80)
    print("⚠️  重複・冗長特徴量分析")
    print("=" * 80)

    total_redundant = 0
    for i, group in enumerate(analysis_result["redundant_groups"], 1):
        print(f"\n{i}. {group['description']}")
        print(f"   影響特徴量: {len(group['features'])}個")
        print(f"   削除推奨: {group['redundant_count']}個")
        print(f"   推奨対応: {group['recommendation']}")
        print(f"   特徴量: {', '.join(group['features'])}")
        total_redundant += group["redundant_count"]

    print(f"\n📉 削除可能な重複特徴量: {total_redundant}個")
    print(f"📊 重複削除後特徴量数: {len(analysis_result['reduced_features'])}個")

    print("\n" + "=" * 80)
    print("🎯 取引に必要不可欠な特徴量（厳選版）")
    print("=" * 80)

    for category, info in analysis_result["essential_features"].items():
        print(f"\n🔹 {category.replace('_', ' ').title()}: {len(info['features'])}個")
        print(f"   理由: {info['reason']}")
        print(f"   特徴量: {', '.join(info['features'])}")

    print(f"\n🎯 厳選特徴量合計: {len(analysis_result['essential_list'])}個")

    # 結果保存
    results_dir = Path("results/feature_analysis")
    results_dir.mkdir(parents=True, exist_ok=True)

    # 詳細分析結果保存
    analysis_path = results_dir / "feature_analysis_detailed.json"
    with open(analysis_path, "w", encoding="utf-8") as f:
        # JSON serializable形式に変換
        save_data = {
            "original_127": analysis_result["original_127"],
            "categories": analysis_result["categories"],
            "redundant_groups": analysis_result["redundant_groups"],
            "essential_list": analysis_result["essential_list"],
            "reduced_features": analysis_result["reduced_features"],
            "summary": {
                "original_count": len(analysis_result["original_127"]),
                "reduced_count": len(analysis_result["reduced_features"]),
                "essential_count": len(analysis_result["essential_list"]),
                "redundant_count": total_redundant,
            },
        }
        json.dump(save_data, f, indent=2, ensure_ascii=False)

    logger.info(f"詳細分析結果保存: {analysis_path}")

    # 最適化特徴量セット保存
    feature_sets = {
        "essential_features": analysis_result["essential_list"],
        "reduced_features": analysis_result["reduced_features"],
        "original_features": analysis_result["original_127"],
    }

    sets_path = results_dir / "optimized_feature_sets.json"
    with open(sets_path, "w") as f:
        json.dump(feature_sets, f, indent=2)

    logger.info(f"最適化特徴量セット保存: {sets_path}")

    print("\n" + "=" * 80)
    print("📋 次のステップ推奨")
    print("=" * 80)
    print("1. 🔍 重複削除版（~80特徴量）でバックテスト実行")
    print("2. 🎯 厳選版（~30特徴量）でバックテスト実行")
    print("3. 📊 1ヶ月間ウォークフォワードバックテストで性能比較")
    print("4. 🏆 最適な特徴量セットを選定")

    return analysis_result


if __name__ == "__main__":
    main()

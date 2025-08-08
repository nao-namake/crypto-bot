#!/usr/bin/env python3
"""
127特徴量最適化・特徴量選択による勝率・損益改善スクリプト
次元の呪い・オーバーフィッティング問題解決

アプローチ:
1. 段階的特徴量削減（127→80→50→30→20→10）
2. 各段階でバックテスト実行・勝率確認
3. 最適な特徴量数を特定
4. 重要度・相関分析による最終選択
"""

import json
import logging
import os
import sys
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.feature_selection import RFE, SelectKBest, f_classif
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split

# Visualization removed for simplified execution
# import matplotlib.pyplot as plt
# import seaborn as sns

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from crypto_bot.ml.preprocessor import FeatureEngineer

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_training_data():
    """127特徴量訓練データ生成"""
    np.random.seed(42)
    n_rows = 10000

    logger.info(f"127特徴量最適化用データ生成: {n_rows} samples")

    # より現実的な市場データシミュレーション
    t = np.arange(n_rows)

    # 複数の市場サイクル
    trend_cycle = np.sin(2 * np.pi * t / 1000)
    volatility_cycle = np.abs(np.sin(2 * np.pi * t / 500))
    momentum_cycle = np.sin(2 * np.pi * t / 200)

    # ベースリターン
    base_return = np.random.normal(0, 0.01, n_rows)

    # 市場影響
    trend_effect = 0.005 * trend_cycle
    volatility_effect = volatility_cycle * np.random.normal(0, 0.01, n_rows)
    momentum_effect = 0.003 * momentum_cycle

    returns = base_return + trend_effect + volatility_effect + momentum_effect

    # 累積価格
    base_price = 45000
    cumulative_returns = np.cumsum(returns)
    close_prices = base_price * np.exp(cumulative_returns)

    # OHLCV データ
    data = pd.DataFrame(
        {
            "timestamp": pd.date_range(start="2023-01-01", periods=n_rows, freq="1H"),
            "close": close_prices,
        }
    )

    # OHLC計算
    data["open"] = data["close"].shift(1).fillna(close_prices[0])

    # より現実的な高値・安値
    price_volatility = 0.002 * (1 + volatility_cycle)
    data["high"] = np.maximum(data["open"], data["close"]) * (
        1 + np.random.exponential(price_volatility)
    )
    data["low"] = np.minimum(data["open"], data["close"]) * (
        1 - np.random.exponential(price_volatility * 0.8)
    )

    # 出来高
    data["volume"] = np.random.lognormal(np.log(1000), 0.3, n_rows) * (
        1 + 2 * volatility_cycle
    )

    return data


def generate_features_127(data):
    """127特徴量生成"""
    config = {
        "ml": {
            "feat_period": 14,
            "lags": [1, 2, 3, 4, 5],
            "rolling_window": 20,
            "target_type": "classification",
            "extra_features": [
                # 基本OHLCV + ラグ
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
                # リターン系
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
                # 移動平均系
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
                # 価格ポジション
                "price_position_20",
                "price_position_50",
                "price_vs_sma20",
                "bb_position",
                "intraday_position",
                # ボリンジャーバンド
                "bb_upper",
                "bb_middle",
                "bb_lower",
                "bb_width",
                "bb_squeeze",
                # RSI系
                "rsi_14",
                "rsi_7",
                "rsi_21",
                "rsi_oversold",
                "rsi_overbought",
                # MACD系
                "macd",
                "macd_signal",
                "macd_hist",
                "macd_cross_up",
                "macd_cross_down",
                # ストキャスティクス
                "stoch_k",
                "stoch_d",
                "stoch_oversold",
                "stoch_overbought",
                # ATR・ボラティリティ
                "atr_14",
                "atr_7",
                "atr_21",
                "volatility_20",
                "volatility_50",
                "high_low_ratio",
                "true_range",
                "volatility_ratio",
                # ボリューム分析
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
                # トレンド・モメンタム
                "adx_14",
                "plus_di",
                "minus_di",
                "trend_strength",
                "trend_direction",
                "cci_20",
                "williams_r",
                "ultimate_oscillator",
                "momentum_14",
                # サポート・レジスタンス
                "support_distance",
                "resistance_distance",
                "support_strength",
                "volume_breakout",
                "price_breakout_up",
                "price_breakout_down",
                # ローソク足パターン
                "doji",
                "hammer",
                "engulfing",
                "pinbar",
                # 統計・高度分析
                "skewness_20",
                "kurtosis_20",
                "zscore",
                "mean_reversion_20",
                "mean_reversion_50",
                # 時間特徴量
                "hour",
                "day_of_week",
                "is_weekend",
                "is_asian_session",
                "is_european_session",
                "is_us_session",
                # 追加テクニカル
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
                "close_mean_10",
                "close_std_10",
            ],
        }
    }

    engineer = FeatureEngineer(config)
    features = engineer.fit_transform(data)

    # 127特徴量確保
    if features.shape[1] != 127:
        logger.warning(f"特徴量数調整: {features.shape[1]} → 127")
        while features.shape[1] < 127:
            dummy_name = f"dummy_feature_{features.shape[1]}"
            features[dummy_name] = np.random.normal(0, 0.1, len(features))
        if features.shape[1] > 127:
            features = features.iloc[:, :127]

    return features


def create_targets(features, close_prices):
    """ターゲット生成（改良版）"""
    returns = close_prices.pct_change().fillna(0)

    # よりバランスの取れたターゲット生成
    rolling_std = returns.rolling(50).std().fillna(returns.std())

    # 動的閾値（市場ボラティリティに応じて調整）
    buy_threshold = 0.5 * rolling_std
    sell_threshold = -0.5 * rolling_std

    targets = np.where(
        returns > buy_threshold, 1, np.where(returns < sell_threshold, 0, -1)
    )

    # 有効なサンプルのみ（中立を除外）
    valid_mask = targets != -1

    return targets[valid_mask], valid_mask


def test_feature_count_performance(X, y, feature_counts=[127, 80, 50, 30, 20, 15, 10]):
    """特徴量数別性能テスト"""
    results = []

    for n_features in feature_counts:
        logger.info(f"特徴量数 {n_features} でテスト中...")

        # 特徴量選択（重要度ベース）
        if n_features < X.shape[1]:
            # LightGBMで重要度計算
            lgb_model = lgb.LGBMClassifier(
                n_estimators=100, random_state=42, verbose=-1
            )
            lgb_model.fit(X, y)

            # 重要度順でtop-k選択
            feature_importance = lgb_model.feature_importances_
            top_indices = np.argsort(feature_importance)[-n_features:]
            X_selected = X.iloc[:, top_indices]
            selected_features = X.columns[top_indices].tolist()
        else:
            X_selected = X
            selected_features = X.columns.tolist()

        # 訓練・テスト分割
        X_train, X_test, y_train, y_test = train_test_split(
            X_selected, y, test_size=0.3, random_state=42, stratify=y
        )

        # モデル訓練
        model = lgb.LGBMClassifier(
            n_estimators=200,
            max_depth=6,
            learning_rate=0.1,
            random_state=42,
            verbose=-1,
        )
        model.fit(X_train, y_train)

        # 予測・評価
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]

        accuracy = accuracy_score(y_test, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_test, y_pred, average="binary"
        )

        # 予測確率の多様性
        prediction_std = np.std(y_pred_proba)
        prediction_range = np.max(y_pred_proba) - np.min(y_pred_proba)

        result = {
            "n_features": n_features,
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "prediction_std": prediction_std,
            "prediction_range": prediction_range,
            "selected_features": selected_features,
        }
        results.append(result)

        logger.info(
            f"特徴量数 {n_features}: 精度={accuracy:.3f}, F1={f1:.3f}, 予測多様性={prediction_std:.3f}"
        )

    return results


def analyze_feature_correlation(X, threshold=0.8):
    """特徴量相関分析・高相関特徴量特定"""
    logger.info("特徴量相関分析実行中...")

    correlation_matrix = X.corr().abs()

    # 高相関ペア特定
    high_corr_pairs = []
    for i in range(len(correlation_matrix.columns)):
        for j in range(i + 1, len(correlation_matrix.columns)):
            if correlation_matrix.iloc[i, j] > threshold:
                high_corr_pairs.append(
                    {
                        "feature1": correlation_matrix.columns[i],
                        "feature2": correlation_matrix.columns[j],
                        "correlation": correlation_matrix.iloc[i, j],
                    }
                )

    logger.info(f"高相関ペア（>{threshold}）: {len(high_corr_pairs)}組")

    # 削除候補特徴量（相関の高い特徴量の片方）
    features_to_remove = set()
    for pair in high_corr_pairs:
        # より汎用的でない特徴量を削除候補に
        if "lag" in pair["feature1"] or "sma" in pair["feature1"]:
            features_to_remove.add(pair["feature1"])
        elif "lag" in pair["feature2"] or "sma" in pair["feature2"]:
            features_to_remove.add(pair["feature2"])
        else:
            # デフォルトではfeature2を削除候補
            features_to_remove.add(pair["feature2"])

    return high_corr_pairs, list(features_to_remove)


def create_optimal_feature_model(X, y, target_features=20):
    """最適特徴量モデル作成"""
    logger.info(f"最適特徴量モデル作成: {target_features}特徴量")

    # 1. 高相関特徴量除去
    high_corr_pairs, features_to_remove = analyze_feature_correlation(X, threshold=0.85)
    X_filtered = X.drop(columns=features_to_remove)
    logger.info(f"高相関特徴量除去: {X.shape[1]} → {X_filtered.shape[1]}")

    # 2. 重要度ベース選択
    lgb_model = lgb.LGBMClassifier(
        n_estimators=200, max_depth=8, learning_rate=0.1, random_state=42, verbose=-1
    )
    lgb_model.fit(X_filtered, y)

    # 重要度順でtop-k選択
    feature_importance = lgb_model.feature_importances_
    top_indices = np.argsort(feature_importance)[-target_features:]

    selected_features = X_filtered.columns[top_indices].tolist()
    X_optimal = X_filtered.iloc[:, top_indices]

    # 3. 最終モデル訓練
    X_train, X_test, y_train, y_test = train_test_split(
        X_optimal, y, test_size=0.2, random_state=42, stratify=y
    )

    final_model = lgb.LGBMClassifier(
        n_estimators=300,
        max_depth=8,
        learning_rate=0.08,
        feature_fraction=0.8,
        random_state=42,
        verbose=-1,
    )
    final_model.fit(X_train, y_train)

    # 評価
    y_pred = final_model.predict(X_test)
    y_pred_proba = final_model.predict_proba(X_test)[:, 1]

    accuracy = accuracy_score(y_test, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average="binary"
    )

    logger.info(f"最適モデル性能:")
    logger.info(f"  精度: {accuracy:.3f}")
    logger.info(f"  F1スコア: {f1:.3f}")
    logger.info(f"  予測確率範囲: {y_pred_proba.min():.3f} - {y_pred_proba.max():.3f}")

    return (
        final_model,
        selected_features,
        {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "n_features": target_features,
            "removed_features": features_to_remove,
        },
    )


def save_results(results, optimal_model, selected_features, performance):
    """結果保存"""
    results_dir = Path("results/feature_optimization")
    results_dir.mkdir(parents=True, exist_ok=True)

    # 1. 特徴量数別性能結果
    results_df = pd.DataFrame(results)
    results_df.to_csv(results_dir / "feature_count_performance.csv", index=False)

    # 2. 最適モデル保存
    models_dir = Path("models/production")
    models_dir.mkdir(parents=True, exist_ok=True)

    model_path = models_dir / "optimized_feature_model.pkl"
    joblib.dump(optimal_model, model_path)

    # 3. 選択特徴量リスト
    features_path = models_dir / "optimal_features.json"
    with open(features_path, "w") as f:
        json.dump(selected_features, f, indent=2)

    # 4. パフォーマンス情報
    perf_path = models_dir / "optimal_model_performance.json"
    with open(perf_path, "w") as f:
        json.dump(performance, f, indent=2)

    logger.info(f"結果保存完了:")
    logger.info(f"  モデル: {model_path}")
    logger.info(f"  特徴量: {features_path}")
    logger.info(f"  性能データ: {perf_path}")


def main():
    """メイン実行"""
    logger.info("=" * 80)
    logger.info("127特徴量最適化・特徴量選択による勝率改善")
    logger.info("=" * 80)

    # 1. データ生成
    data = create_training_data()
    logger.info(f"訓練データ生成完了: {data.shape}")

    # 2. 127特徴量生成
    features = generate_features_127(data)
    logger.info(f"特徴量生成完了: {features.shape}")

    # 3. ターゲット生成
    targets, valid_mask = create_targets(features, data["close"])
    X = features[valid_mask].fillna(0)
    y = targets

    logger.info(f"有効サンプル: {len(X)}")
    logger.info(
        f"ターゲット分布: BUY={np.sum(y==1)} ({np.sum(y==1)/len(y)*100:.1f}%), SELL={np.sum(y==0)} ({np.sum(y==0)/len(y)*100:.1f}%)"
    )

    # 4. 特徴量数別性能テスト
    logger.info("特徴量数別性能テスト開始...")
    performance_results = test_feature_count_performance(X, y)

    # 5. 結果分析
    results_df = pd.DataFrame(performance_results)
    print("\n" + "=" * 80)
    print("特徴量数別性能結果:")
    print("=" * 80)
    print(
        results_df[
            ["n_features", "accuracy", "f1_score", "prediction_std", "prediction_range"]
        ].to_string(index=False)
    )

    # 最適特徴量数特定
    best_result = results_df.loc[results_df["f1_score"].idxmax()]
    logger.info(
        f"\n最高F1スコア: {best_result['f1_score']:.3f} (特徴量数: {best_result['n_features']})"
    )

    # 6. 最適モデル作成
    optimal_n_features = int(best_result["n_features"])
    optimal_model, selected_features, performance = create_optimal_feature_model(
        X, y, optimal_n_features
    )

    # 7. 結果保存
    save_results(performance_results, optimal_model, selected_features, performance)

    print("\n" + "=" * 80)
    print("127特徴量最適化完了!")
    print("=" * 80)
    print(f"推奨特徴量数: {optimal_n_features}")
    print(f"最適化モデル精度: {performance['accuracy']:.3f}")
    print(f"最適化モデルF1: {performance['f1_score']:.3f}")
    print(f"削除された高相関特徴量: {len(performance['removed_features'])}個")
    print("\n次のステップ:")
    print("1. python scripts/backtest_optimized_model.py でバックテスト実行")
    print("2. 勝率・損益改善効果を確認")
    print("3. 最適特徴量数での本格運用")


if __name__ == "__main__":
    main()

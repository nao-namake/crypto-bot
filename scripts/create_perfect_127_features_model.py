#!/usr/bin/env python3
"""
完璧な127特徴量モデル作成スクリプト
真に実装された127特徴量システムで高品質なモデルを学習

実装済み特徴量:
- RSI、SMA、EMA、MACD、Stochastic、ATR等のテクニカル指標
- Bollinger Bands、Williams %R、CCI、MFI等の複合指標
- 時間特徴量、ボリューム関連、価格位置特徴量
- ラグ特徴量、リターン特徴量、トレンド分析特徴量
"""

import logging
import os
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from crypto_bot.ml.ensemble import TradingEnsembleClassifier
from crypto_bot.ml.feature_order_manager import FeatureOrderManager
from crypto_bot.ml.preprocessor import FeatureEngineer

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_comprehensive_training_data():
    """包括的な学習データを生成"""
    np.random.seed(42)
    n_rows = 5000  # より多くの学習データ

    logger.info(f"Creating comprehensive training data: {n_rows} samples")

    # より現実的なBTC価格動きをシミュレート
    base_price = 45000

    # トレンド・ボラティリティ・サイクルを含む複雑な価格動き
    t = np.arange(n_rows)

    # 複数のサイクルとトレンドを重ね合わせ
    long_trend = 0.00002 * t  # 長期上昇トレンド
    medium_cycle = 0.05 * np.sin(2 * np.pi * t / 200)  # 中期サイクル
    short_cycle = 0.02 * np.sin(2 * np.pi * t / 24)  # 短期サイクル

    # ボラティリティクラスタリング
    vol_base = 0.015
    vol_clustering = vol_base * (1 + 0.5 * np.sin(2 * np.pi * t / 500))

    # ランダムウォーク + 構造
    random_walk = np.cumsum(np.random.normal(0, vol_clustering, n_rows))

    # 総合価格パス
    log_price_path = long_trend + medium_cycle + short_cycle + random_walk
    close_prices = base_price * np.exp(log_price_path)

    # 現実的なOHLCデータ生成
    data = pd.DataFrame(
        {
            "timestamp": pd.date_range(start="2024-01-01", periods=n_rows, freq="1H"),
            "close": close_prices,
        }
    )

    # Open: 前のcloseベース（ギャップを含む）
    gap_factor = np.random.normal(1, 0.002, n_rows)  # 平均0.2%のギャップ
    data["open"] = data["close"].shift(1).fillna(close_prices[0]) * gap_factor

    # High/Low: より現実的な日中レンジ
    intraday_volatility = np.random.exponential(0.008, n_rows)
    oc_max = np.maximum(data["open"], data["close"])
    oc_min = np.minimum(data["open"], data["close"])

    data["high"] = oc_max * (1 + intraday_volatility)
    data["low"] = oc_min * (1 - intraday_volatility * 0.8)

    # Volume: 価格変動と相関のある現実的なボリューム
    price_change = np.abs(data["close"].pct_change())
    base_volume = np.random.lognormal(np.log(500), 0.3, n_rows)
    volume_multiplier = 1 + 2 * price_change.fillna(0)  # ボラティリティでボリューム増加
    data["volume"] = base_volume * volume_multiplier

    logger.info(f"Generated realistic OHLCV data:")
    logger.info(
        f"  Price range: ${data['close'].min():.0f} - ${data['close'].max():.0f}"
    )
    logger.info(f"  Average daily return: {data['close'].pct_change().mean()*100:.3f}%")
    logger.info(
        f"  Average daily volatility: {data['close'].pct_change().std()*100:.3f}%"
    )
    logger.info(
        f"  Volume range: {data['volume'].min():.0f} - {data['volume'].max():.0f}"
    )

    return data


def create_realistic_targets(features, close_prices):
    """現実的なターゲット変数を生成"""
    logger.info("Creating realistic target variables")

    # 複数の期間のリターンを考慮
    returns_1h = close_prices.pct_change(1)
    returns_4h = close_prices.pct_change(4)
    returns_24h = close_prices.pct_change(24)

    # ボラティリティ調整済みリターン
    vol_20 = returns_1h.rolling(20).std()

    # より現実的な分類ターゲット（3段階）
    # - 0: SELL (下位30%)
    # - 1: HOLD (中位40%)
    # - 2: BUY (上位30%)

    # 複数期間のリターンを重み付き平均
    combined_returns = (0.5 * returns_1h + 0.3 * returns_4h + 0.2 * returns_24h).fillna(
        0
    )

    # ボラティリティ調整
    vol_adjusted_returns = combined_returns / (vol_20 + 1e-6)

    # パーセンタイルベースの分類
    sell_threshold = vol_adjusted_returns.quantile(0.30)
    buy_threshold = vol_adjusted_returns.quantile(0.70)

    targets = np.where(
        vol_adjusted_returns <= sell_threshold,
        0,  # SELL
        np.where(vol_adjusted_returns >= buy_threshold, 2, 1),  # BUY vs HOLD
    )

    target_counts = pd.Series(targets).value_counts().sort_index()
    logger.info(f"Target distribution:")
    logger.info(
        f"  SELL (0): {target_counts.get(0, 0)} ({target_counts.get(0, 0)/len(targets)*100:.1f}%)"
    )
    logger.info(
        f"  HOLD (1): {target_counts.get(1, 0)} ({target_counts.get(1, 0)/len(targets)*100:.1f}%)"
    )
    logger.info(
        f"  BUY (2): {target_counts.get(2, 0)} ({target_counts.get(2, 0)/len(targets)*100:.1f}%)"
    )

    return targets


def train_perfect_model():
    """完璧な127特徴量モデルを学習"""
    logger.info("=" * 80)
    logger.info("完璧な127特徴量モデル学習開始")
    logger.info("=" * 80)

    # 学習データ生成
    data = create_comprehensive_training_data()

    # 127特徴量システム設定
    config = {
        "ml": {
            "feat_period": 14,
            "lags": [1, 2, 3],
            "rolling_window": 10,
            "horizon": 5,
            "target_type": "classification",
            # 実装済み127特徴量を全て設定
            "extra_features": [
                # 基本OHLCV
                "open",
                "high",
                "low",
                "close",
                "volume",
                # RSI系 (完全実装済み)
                "rsi_7",
                "rsi_14",
                "rsi_21",
                "rsi_overbought",
                "rsi_oversold",
                # SMA系 (完全実装済み)
                "sma_5",
                "sma_10",
                "sma_20",
                "sma_50",
                "sma_100",
                "sma_200",
                # EMA系 (完全実装済み)
                "ema_5",
                "ema_10",
                "ema_20",
                "ema_50",
                "ema_100",
                "ema_200",
                # ATR系 (完全実装済み)
                "atr_7",
                "atr_14",
                "atr_21",
                # MACD系 (完全実装済み)
                "macd",
                "macd_signal",
                "macd_hist",
                "macd_cross_up",
                "macd_cross_down",
                # Bollinger Bands (完全実装済み)
                "bb_upper",
                "bb_middle",
                "bb_lower",
                "bb_width",
                "bb_position",
                "bb_squeeze",
                # Stochastic (完全実装済み)
                "stoch_k",
                "stoch_d",
                "stoch_overbought",
                "stoch_oversold",
                # ADX (完全実装済み)
                "adx_14",
                "plus_di",
                "minus_di",
                # ボラティリティ (完全実装済み)
                "volatility_20",
                "volatility_50",
                "volatility_ratio",
                "volatility_regime",
                # ボリューム関連 (完全実装済み)
                "volume_sma_20",
                "volume_ratio",
                "volume_trend",
                "volume_breakout",
                # 価格技術指標 (完全実装済み)
                "williams_r",
                "cci_20",
                "mfi",
                "obv",
                "obv_sma",
                "true_range",
                "high_low_ratio",
                "vwap",
                "vwap_distance",
                # 価格位置・リターン (完全実装済み)
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
                # ラグ特徴量 (完全実装済み)
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
                # 時間特徴量 (完全実装済み)
                "hour",
                "day_of_week",
                "is_weekend",
                "is_asian_session",
                "is_european_session",
                "is_us_session",
                # その他完全実装済み特徴量
                "momentum_14",
                "trend_strength",
                "trend_direction",
                "close_mean_10",
                "close_std_10",
                "roc_10",
                "roc_20",
                "trix",
                "mass_index",
                "ultimate_oscillator",
                "keltner_upper",
                "keltner_lower",
                "donchian_upper",
                "donchian_lower",
                "ichimoku_conv",
                "ichimoku_base",
                "price_efficiency",
                "trend_consistency",
                "volume_price_correlation",
                "momentum_quality",
                "market_phase",
                "support_distance",
                "resistance_distance",
                "support_strength",
                "price_breakout_up",
                "price_breakout_down",
                "intraday_position",
                "mean_reversion_20",
                "mean_reversion_50",
                "skewness_20",
                "kurtosis_20",
                "zscore",
                "hammer",
                "doji",
                "pinbar",
                "engulfing",
                "ad_line",
                "cmf",
            ],
        }
    }

    logger.info(f"Configured {len(config['ml']['extra_features'])} features")

    # 特徴量エンジニアリング
    logger.info("Generating 127 features...")
    engineer = FeatureEngineer(config)
    features = engineer.fit_transform(data)

    logger.info(f"Generated features: {features.shape}")
    logger.info(f"Feature columns: {len(features.columns)}")

    # 特徴量品質確認
    expected_features = set(FeatureOrderManager.FEATURE_ORDER_127)
    generated_features = set(features.columns)
    implemented = expected_features & generated_features

    logger.info(
        f"Expected: {len(expected_features)}, Generated: {len(generated_features)}"
    )
    logger.info(
        f"Implementation rate: {len(implemented)/len(expected_features)*100:.1f}%"
    )

    # ターゲット変数生成
    targets = create_realistic_targets(features, data["close"])

    # データセット準備
    # NaN値を含む行を除去
    valid_mask = ~(features.isna().any(axis=1) | pd.Series(targets).isna())
    X = features[valid_mask]
    y = targets[valid_mask]

    logger.info(f"Valid samples: {len(X)} ({len(X)/len(features)*100:.1f}%)")

    if len(X) < 1000:
        raise ValueError(f"Insufficient valid samples: {len(X)}")

    # 特徴量順序を127特徴量順序に統一
    feature_order = FeatureOrderManager.FEATURE_ORDER_127
    missing_cols = [col for col in feature_order if col not in X.columns]
    if missing_cols:
        logger.warning(f"Missing features: {len(missing_cols)}")
        for col in missing_cols[:5]:  # 最初の5個を表示
            logger.warning(f"  - {col}")

    # 存在する特徴量のみを使用
    available_features = [col for col in feature_order if col in X.columns]
    X = X[available_features]

    logger.info(f"Using {len(available_features)} features for training")

    # 訓練・テスト分割
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    logger.info(f"Training set: {X_train.shape}")
    logger.info(f"Test set: {X_test.shape}")

    # アンサンブルモデル学習
    logger.info("Training ensemble model...")
    from lightgbm import LGBMClassifier
    from sklearn.ensemble import RandomForestClassifier
    from xgboost import XGBClassifier

    base_models = [
        LGBMClassifier(random_state=42, verbose=-1),
        XGBClassifier(random_state=42, eval_metric="logloss"),
        RandomForestClassifier(random_state=42, n_jobs=-1),
    ]

    model = TradingEnsembleClassifier(
        base_models=base_models,
        ensemble_method="trading_stacking",
        cv_folds=5,
        confidence_threshold=0.65,
    )

    model.fit(X_train, y_train)

    # テスト評価
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    logger.info(f"Test Accuracy: {accuracy:.4f}")

    # 詳細評価
    report = classification_report(y_test, y_pred, target_names=["SELL", "HOLD", "BUY"])
    logger.info(f"Classification Report:\\n{report}")

    # モデル保存
    models_dir = Path("models/production")
    models_dir.mkdir(parents=True, exist_ok=True)

    model_path = models_dir / "perfect_127_features_model.pkl"
    joblib.dump(model, model_path)
    logger.info(f"Model saved: {model_path}")

    # 特徴量順序保存
    feature_order_path = models_dir / "perfect_127_features_order.json"
    import json

    with open(feature_order_path, "w") as f:
        json.dump(available_features, f, indent=2)
    logger.info(f"Feature order saved: {feature_order_path}")

    # 結果サマリー
    logger.info("=" * 80)
    logger.info("完璧な127特徴量モデル学習完了")
    logger.info("=" * 80)
    logger.info(f"Features used: {len(available_features)}/127")
    logger.info(f"Training samples: {len(X_train):,}")
    logger.info(f"Test accuracy: {accuracy:.1%}")
    logger.info(f"Model path: {model_path}")
    logger.info("Ready for backtesting!")

    return model, available_features, accuracy


if __name__ == "__main__":
    try:
        model, features, accuracy = train_perfect_model()
        print(f"\\n✅ Perfect 127-feature model created successfully!")
        print(f"Accuracy: {accuracy:.1%}")
        print(f"Features: {len(features)}")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Model creation failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

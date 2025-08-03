#!/usr/bin/env python3
"""
実装済み特徴量のみでのモデル作成スクリプト
本番と完全同等の環境でモデル学習を実行
"""

import logging
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# プロジェクトルートをPYTHONPATHに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto_bot.ml.ensemble import TradingEnsembleClassifier
from crypto_bot.ml.target import make_classification_target

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_realistic_features_model():
    """実装済み特徴量のみでのモデル作成"""

    print("🚀 Realistic Features Model Creation Starting...")

    # 1. データ読み込み
    logger.info("📊 Loading real data...")
    data_path = Path("data/btc_usd_2024_hourly.csv")
    df = pd.read_csv(data_path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    df.set_index("datetime", inplace=True)

    # 最初の4320件（6ヶ月分）を使用
    df = df.head(4320)
    logger.info(f"✅ Training data: {len(df)} records")

    # 2. 実装済み特徴量のみ生成（バックテストログから確認された特徴量）
    logger.info("🔧 Generating only implemented features...")

    # 基本OHLCV
    features_df = df[["open", "high", "low", "close", "volume"]].copy()

    # 実装済みのテクニカル指標のみ
    # RSI (14期間のみ)
    def calculate_rsi(prices, period):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    features_df["rsi_14"] = calculate_rsi(df["close"], 14)

    # SMA (基本的なもののみ)
    features_df["sma_20"] = df["close"].rolling(20).mean()
    features_df["sma_50"] = df["close"].rolling(50).mean()

    # EMA (基本的なもののみ)
    features_df["ema_20"] = df["close"].ewm(span=20).mean()
    features_df["ema_50"] = df["close"].ewm(span=50).mean()

    # ATR
    high_low = df["high"] - df["low"]
    high_close = np.abs(df["high"] - df["close"].shift())
    low_close = np.abs(df["low"] - df["close"].shift())
    true_range = np.maximum(high_low, np.maximum(high_close, low_close))
    features_df["atr_14"] = true_range.rolling(14).mean()

    # MACD
    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()
    features_df["macd"] = ema12 - ema26

    # Volatility
    features_df["volatility_20"] = df["close"].pct_change().rolling(20).std()

    # Volume ratio
    features_df["volume_sma_20"] = df["volume"].rolling(20).mean()
    features_df["volume_ratio"] = df["volume"] / features_df["volume_sma_20"]

    # High-Low ratio
    features_df["high_low_ratio"] = df["high"] / df["low"]

    # True range
    features_df["true_range"] = true_range

    # Trend strength (simplified)
    features_df["trend_strength"] = abs(features_df["macd"])

    # 時間特徴量（常に利用可能）
    features_df["hour"] = features_df.index.hour
    features_df["day_of_week"] = features_df.index.dayofweek

    # Momentum
    features_df["momentum_14"] = df["close"] / df["close"].shift(14) - 1

    # NaN値を除去
    features_df = features_df.dropna()
    logger.info(f"📊 Generated features: {len(features_df.columns)} features")
    logger.info(f"✅ Clean data: {len(features_df)} samples")
    logger.info(f"✅ Feature list: {list(features_df.columns)}")

    # 3. ターゲット作成
    y = make_classification_target(features_df, horizon=5)

    # データとターゲットの長さを合わせる
    min_len = min(len(features_df), len(y))
    X = features_df.iloc[:min_len]
    y = y.iloc[:min_len]

    logger.info(
        f"✅ Training preparation: {len(X)} samples × {len(X.columns)} features"
    )

    # 4. アンサンブルモデル学習
    logger.info("🤖 Training TradingEnsembleClassifier...")

    ensemble = TradingEnsembleClassifier(
        ensemble_method="trading_stacking", confidence_threshold=0.35  # 取引機会確保
    )

    # 学習実行
    ensemble.fit(X, y)

    # 5. モデル保存
    logger.info("💾 Saving model...")

    # 既存モデルをバックアップ
    model_path = Path("models/production/model.pkl")
    if model_path.exists():
        backup_path = f"models/production/model_backup_realistic_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.pkl"
        import shutil

        shutil.copy(model_path, backup_path)
        logger.info(f"✅ Existing model backed up: {backup_path}")

    # 新しいモデルを保存
    import joblib

    joblib.dump(ensemble, str(model_path))

    # メタデータ保存
    metadata = {
        "phase": "Realistic_Features_Model",
        "features": len(X.columns),
        "samples": len(X),
        "feature_names": list(X.columns),
        "timestamp": pd.Timestamp.now().isoformat(),
        "approach": "implemented_features_only",
        "implementation_rate": "100%",
    }

    import json

    with open("models/production/model_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"✅ Model saved: {model_path}")
    logger.info(f"📊 Training completed: {len(X)} samples, {len(X.columns)} features")

    print("🎊 Realistic Features Model Creation Completed!")
    print(f"✅ Model features: {len(X.columns)} features")
    print(f"✅ Training samples: {len(X)} samples")
    print(f"✅ Features: {list(X.columns)}")
    print("🚀 Ready for realistic backtest!")


if __name__ == "__main__":
    create_realistic_features_model()

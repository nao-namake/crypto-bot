#!/usr/bin/env python3
"""
Phase H.24.6: 155特徴量完全対応モデル再学習スクリプト

目的:
- 既存の154特徴量（enhanced_default含む）モデルを置き換え
- 正しい155特徴量でアンサンブルモデルを再学習
- 各タイムフレーム（15m, 1h, 4h）のモデルを保存

実行方法:
python retrain_models.py --config config/production/production.yml
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yaml
from sklearn.model_selection import train_test_split

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent))

import ccxt  # noqa: E402
from crypto_bot.ml.ensemble import (  # noqa: E402
    TradingEnsembleClassifier,
    create_trading_ensemble,
)
from crypto_bot.ml.preprocessor import FeatureEngineer  # noqa: E402

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_config(config_path: str) -> dict:
    """設定ファイル読み込み"""
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # 環境変数を適用
    if "BITBANK_API_KEY" in os.environ:
        config["data"]["api_key"] = os.environ["BITBANK_API_KEY"]
    if "BITBANK_API_SECRET" in os.environ:
        config["data"]["api_secret"] = os.environ["BITBANK_API_SECRET"]

    return config


def prepare_training_data(config: dict, timeframe: str) -> tuple:
    """
    指定タイムフレームの学習データを準備

    Returns:
        X, y: 特徴量とターゲット
    """
    logger.info(f"🔄 Preparing training data for {timeframe}...")

    # データ取得
    exchange_config = config.get("data", {})
    exchange_id = exchange_config.get("exchange", "bitbank")
    symbol = exchange_config.get("symbol", "BTC/JPY")

    # ccxtで直接データ取得
    try:
        exchange = getattr(ccxt, exchange_id)({
            "apiKey": exchange_config.get("api_key"),
            "secret": exchange_config.get("api_secret"),
            "enableRateLimit": True
        })

        # 30日分のデータを取得
        since_ms = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=since_ms, limit=1000)

        # DataFrameに変換
        df = pd.DataFrame(
            ohlcv,
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)

        if df is None or df.empty:
            logger.error(f"No data fetched for {timeframe}")
            return None, None

        logger.info(f"✅ Fetched {len(df)} records for {timeframe}")

        # 特徴量生成
        feature_engineer = FeatureEngineer(config)
        features_df = feature_engineer.create_features(df)

        if features_df is None or features_df.empty:
            logger.error(f"No features generated for {timeframe}")
            return None, None

        # ターゲット生成（5期間先の価格変化）
        df["target"] = (df["close"].shift(-5) > df["close"]).astype(int)

        # 有効なデータのみ抽出
        valid_idx = ~(features_df.isna().any(axis=1) | df["target"].isna())
        X = features_df[valid_idx]
        y = df["target"][valid_idx]

        logger.info(
            f"✅ Prepared {len(X)} samples with {X.shape[1]} features for {timeframe}"
        )

        # 155特徴量であることを確認
        if X.shape[1] != 155:
            logger.warning(f"⚠️ Expected 155 features, got {X.shape[1]}")

        return X, y

    except Exception as e:
        logger.error(f"❌ Error preparing data for {timeframe}: {e}")
        return None, None


def train_timeframe_model(
    config: dict, timeframe: str, X: pd.DataFrame, y: pd.Series
) -> TradingEnsembleClassifier:
    """
    単一タイムフレームのアンサンブルモデルを学習
    """
    logger.info(f"🎯 Training ensemble model for {timeframe}...")

    # 学習・検証データ分割
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # アンサンブルモデル作成
    ensemble_model = create_trading_ensemble(config)

    # 学習
    ensemble_model.fit(X_train, y_train)

    # 検証スコア
    val_score = ensemble_model.score(X_val, y_val)
    logger.info(f"✅ {timeframe} model trained - Validation accuracy: {val_score:.4f}")

    return ensemble_model


def save_models(models: dict, config: dict):
    """
    学習済みモデルを保存
    """
    model_dir = Path("models/production/timeframe_models")
    model_dir.mkdir(parents=True, exist_ok=True)

    for timeframe, model in models.items():
        model_path = model_dir / f"{timeframe}_ensemble_model.pkl"

        import joblib

        joblib.dump(model, model_path)
        logger.info(f"💾 Saved {timeframe} model to {model_path}")

    # モデルメタデータ保存
    metadata = {
        "trained_at": datetime.now().isoformat(),
        "num_features": 155,
        "timeframes": list(models.keys()),
        "feature_order_file": "feature_order.json",
        "config_used": config.get("strategy", {}).get("params", {}),
    }

    metadata_path = model_dir / "model_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"📝 Saved model metadata to {metadata_path}")


def update_feature_order():
    """
    feature_order.jsonが正しく設定されていることを確認
    """
    feature_order_path = Path("feature_order.json")

    if feature_order_path.exists():
        with open(feature_order_path, "r") as f:
            data = json.load(f)

        if data.get("num_features") == 155:
            logger.info(
                "✅ feature_order.json is correctly configured with 155 features"
            )
        else:
            logger.warning("⚠️ feature_order.json has incorrect feature count")
    else:
        logger.warning("⚠️ feature_order.json not found")


def main():
    parser = argparse.ArgumentParser(description="Retrain models with 155 features")
    parser.add_argument("--config", required=True, help="Path to configuration file")
    parser.add_argument(
        "--timeframes",
        nargs="+",
        default=["15m", "1h", "4h"],
        help="Timeframes to train models for",
    )
    args = parser.parse_args()

    # 設定読み込み
    config = load_config(args.config)

    logger.info("🚀 Starting model retraining with 155 features...")
    logger.info(f"   Config: {args.config}")
    logger.info(f"   Timeframes: {args.timeframes}")

    # feature_order.json確認
    update_feature_order()

    # 各タイムフレームでモデル学習
    trained_models = {}

    for timeframe in args.timeframes:
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing {timeframe}")
        logger.info(f"{'='*60}")

        # データ準備
        X, y = prepare_training_data(config, timeframe)

        if X is None or y is None:
            logger.error(f"❌ Skipping {timeframe} due to data preparation failure")
            continue

        # モデル学習
        try:
            model = train_timeframe_model(config, timeframe, X, y)
            trained_models[timeframe] = model
        except Exception as e:
            logger.error(f"❌ Failed to train {timeframe} model: {e}")
            continue

    # モデル保存
    if trained_models:
        logger.info(f"\n🎉 Successfully trained {len(trained_models)} models")
        save_models(trained_models, config)
        logger.info("\n✅ Model retraining completed successfully!")
    else:
        logger.error("\n❌ No models were successfully trained")
        sys.exit(1)


if __name__ == "__main__":
    main()

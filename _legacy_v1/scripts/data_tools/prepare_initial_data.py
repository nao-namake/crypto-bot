#!/usr/bin/env python3
"""
初期データ事前取得スクリプト（168時間版）
本番デプロイ前に168時間分のOHLCVデータと97特徴量を事前計算してキャッシュ保存
API制限回避・データ取得安定化のため、ローカル環境で事前取得

使用方法:
    export BITBANK_API_KEY="your-api-key"
    export BITBANK_API_SECRET="your-api-secret"
    python scripts/data_tools/prepare_initial_data.py

出力:
    cache/initial_data_168h.pkl - 168時間初期データキャッシュ
    cache/initial_features_168h.pkl - 97特徴量キャッシュ
    
本番環境での利用:
    - Docker imageに含めて配置
    - 起動時の高速データロード
    - API制限回避効果
"""

import json
import logging
import os
import pickle
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yaml

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from crypto_bot.data.fetcher import MarketDataFetcher
from crypto_bot.indicator.calculator import IndicatorCalculator

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def load_config():
    """本番設定を読み込み"""
    config_path = Path("config/production/production.yml")
    logger.info(f"📋 Loading configuration from {config_path}")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def fetch_initial_data(config):
    """168時間分のOHLCVデータを取得"""
    logger.info("🔄 Fetching 168-hour OHLCV data for production cache...")

    dd = config.get("data", {})

    # MarketDataFetcherを初期化
    fetcher = MarketDataFetcher(
        exchange_id=dd.get("exchange", "bitbank"),
        symbol=dd.get("symbol", "BTC/JPY"),
        api_key=os.getenv("BITBANK_API_KEY"),
        api_secret=os.getenv("BITBANK_API_SECRET"),
        ccxt_options=dd.get("ccxt_options", {}),
    )

    # 現在時刻から168時間前をsince_timeとして設定（1週間分データ）
    current_time = pd.Timestamp.now(tz="UTC")
    since_time = current_time - pd.Timedelta(hours=168)  # 168時間（1週間）

    logger.info(f"📊 Fetching 168-hour data from {since_time} to {current_time}")

    try:
        # 168レコードを目標に取得（168時間分）
        price_df = fetcher.get_price_df(
            timeframe="1h",
            since=since_time,
            limit=200,  # 余裕を持って200に設定
            paginate=True,
            per_page=200,
            max_consecutive_empty=12,
            max_consecutive_no_new=20,
            max_attempts=25,
        )

        if price_df.empty:
            logger.error("❌ Failed to fetch any data")
            return None

        logger.info(f"✅ Successfully fetched {len(price_df)} records")
        logger.info(f"📈 Data range: {price_df.index.min()} to {price_df.index.max()}")

        # データ品質チェック
        if len(price_df) < 200:
            logger.warning(f"⚠️ Only {len(price_df)} records fetched (target was 400)")

        return price_df

    except Exception as e:
        logger.error(f"❌ Error fetching data: {e}")
        import traceback

        traceback.print_exc()
        return None


def compute_97_features(data, config):
    """97特徴量を事前計算"""
    logger.info("🔧 Computing 97 features...")

    try:
        # FeatureMasterImplementationを試みる
        from crypto_bot.ml.feature_master_implementation import (
            FeatureMasterImplementation,
        )

        feature_impl = FeatureMasterImplementation()

        # DataFrameの準備
        if not isinstance(data, pd.DataFrame):
            data = pd.DataFrame(data)

        # 特徴量計算
        features = feature_impl.generate_all_features(data)

        logger.info(
            f"✅ Computed {features.shape[1]} features for {features.shape[0]} records"
        )
        logger.info(
            f"📊 Feature columns: {list(features.columns)[:10]}... (showing first 10)"
        )

        return features

    except ImportError:
        logger.warning(
            "⚠️ FeatureMasterImplementation not available, using basic features"
        )
        # フォールバック: 基本的な特徴量のみ計算
        calculator = IndicatorCalculator()

        # 基本的なテクニカル指標を計算
        features = data.copy()

        # RSI
        features["rsi_14"] = calculator.rsi(data["close"], period=14)

        # MACD
        macd_result = calculator.macd(data["close"])
        features["macd"] = macd_result["macd"]
        features["macd_signal"] = macd_result["signal"]
        features["macd_hist"] = macd_result["histogram"]

        # ボリンジャーバンド
        bb_result = calculator.bollinger_bands(data["close"])
        features["bb_upper"] = bb_result["upper"]
        features["bb_middle"] = bb_result["middle"]
        features["bb_lower"] = bb_result["lower"]

        # ATR
        features["atr_14"] = calculator.atr(
            data["high"], data["low"], data["close"], period=14
        )

        # ボリューム関連
        features["volume_sma_20"] = data["volume"].rolling(window=20).mean()

        logger.info(f"✅ Computed basic features: {features.shape}")
        return features

    except Exception as e:
        logger.error(f"❌ Feature computation failed: {e}")
        return data


def save_cache(data, features, config):
    """データと特徴量をキャッシュファイルに保存"""
    cache_dir = Path("cache")
    cache_dir.mkdir(exist_ok=True)

    # メタデータ
    metadata = {
        "created_at": datetime.now().isoformat(),
        "data_shape": data.shape if data is not None else None,
        "features_shape": features.shape if features is not None else None,
        "symbol": config.get("data", {}).get("symbol", "BTC/JPY"),
        "timeframe": "1h",
        "records": len(data) if data is not None else 0,
    }

    # OHLCVデータの保存
    if data is not None:
        data_cache_path = cache_dir / "initial_data_168h.pkl"
        with open(data_cache_path, "wb") as f:
            pickle.dump({"data": data, "metadata": metadata}, f)
        logger.info(f"💾 Saved OHLCV data to {data_cache_path}")

    # 特徴量データの保存
    if features is not None:
        features_cache_path = cache_dir / "initial_features_168h.pkl"
        with open(features_cache_path, "wb") as f:
            pickle.dump({"features": features, "metadata": metadata}, f)
        logger.info(f"💾 Saved features to {features_cache_path}")

    # メタデータを別途JSON形式でも保存（人間が読める形式）
    metadata_path = cache_dir / "initial_data_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2, default=str)
    logger.info(f"📝 Saved metadata to {metadata_path}")

    return metadata


def verify_cache():
    """保存されたキャッシュを検証"""
    cache_dir = Path("cache")

    # OHLCVデータの検証
    data_cache_path = cache_dir / "initial_data_168h.pkl"
    if data_cache_path.exists():
        with open(data_cache_path, "rb") as f:
            cache_data = pickle.load(f)
            data = cache_data["data"]
            logger.info(f"✅ OHLCV cache verified: {len(data)} records")
    else:
        logger.warning("⚠️ OHLCV cache not found")

    # 特徴量データの検証
    features_cache_path = cache_dir / "initial_features_168h.pkl"
    if features_cache_path.exists():
        with open(features_cache_path, "rb") as f:
            cache_data = pickle.load(f)
            features = cache_data["features"]
            logger.info(f"✅ Features cache verified: shape={features.shape}")
    else:
        logger.warning("⚠️ Features cache not found")

    # メタデータの表示
    metadata_path = cache_dir / "initial_data_metadata.json"
    if metadata_path.exists():
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
            logger.info(f"📊 Cache metadata:")
            for key, value in metadata.items():
                logger.info(f"  - {key}: {value}")


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("🚀 Initial Data Preparation Script")
    logger.info("=" * 60)

    # 設定読み込み
    config = load_config()

    # 初期データ取得
    data = fetch_initial_data(config)
    if data is None:
        logger.error("❌ Failed to fetch initial data. Exiting.")
        sys.exit(1)

    # 97特徴量計算
    features = compute_97_features(data, config)

    # キャッシュ保存
    metadata = save_cache(data, features, config)

    # 検証
    logger.info("\n" + "=" * 60)
    logger.info("🔍 Verifying saved cache...")
    verify_cache()

    logger.info("\n" + "=" * 60)
    logger.info("✅ Initial data preparation completed successfully!")
    logger.info("📦 Cache files are ready for deployment")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()

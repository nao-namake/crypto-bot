#!/usr/bin/env python3
"""
Phase 12.3: ローカル事前計算スクリプト
本番デプロイ前に重い計算を実行し、キャッシュに保存

使用方法:
    python scripts/pre_compute_data.py
"""

import logging
import sys
from pathlib import Path

import pandas as pd
import yaml

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from crypto_bot.data.fetcher import MarketDataFetcher
from crypto_bot.indicator.calculator import IndicatorCalculator

try:
    from crypto_bot.ml.feature_master_implementation import FeatureMasterImplementation

    FEATURE_MASTER_AVAILABLE = True
except ImportError:
    FEATURE_MASTER_AVAILABLE = False
    # logger will be initialized after logging setup
from crypto_bot.utils.pre_computed_cache import PreComputedCache

# ロギング設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_config():
    """本番設定を読み込み"""
    config_path = Path("config/production/production.yml")
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def fetch_market_data(config):
    """最新の市場データを取得"""
    logger.info("📊 Fetching market data...")

    dd = config.get("data", {})
    fetcher = MarketDataFetcher(
        exchange_id=dd.get("exchange", "bitbank"),
        symbol=dd.get("symbol", "BTC/JPY"),
        ccxt_options=dd.get("ccxt_options", {}),
    )

    # 200レコード取得（INIT-5と同等）
    # Phase 12.3: 直接データ取得
    data = fetcher.get_price_df(timeframe=dd.get("timeframe", "1h"), limit=200)

    logger.info(f"✅ Fetched {len(data)} records")
    return data


def compute_features(data, config):
    """97特徴量を計算"""
    logger.info("🔧 Computing 97 features...")

    if not FEATURE_MASTER_AVAILABLE:
        logger.warning(
            "⚠️ FeatureMasterImplementation not available, returning raw data"
        )
        return data

    try:
        # FeatureMasterImplementation使用
        feature_impl = FeatureMasterImplementation()

        # データフレームの準備
        if not isinstance(data, pd.DataFrame):
            data = pd.DataFrame(data)

        # 特徴量計算
        features = feature_impl.generate_all_features(data)

        logger.info(f"✅ Computed features: shape={features.shape}")
        return features

    except Exception as e:
        logger.error(f"❌ Feature computation failed: {e}")
        # フォールバック: 基本的な特徴量のみ
        return data


def compute_technical_indicators(data):
    """テクニカル指標を計算"""
    logger.info("📈 Computing technical indicators...")

    calculator = IndicatorCalculator()

    technical = {}

    # ATR計算
    try:
        atr = calculator.calculate_atr(data, period=14)
        if atr is not None and not atr.empty:
            latest_atr = float(atr.iloc[-1])
            technical["atr_14"] = latest_atr
            technical["atr_14_mean"] = float(atr.mean())
            logger.info(f"✅ ATR calculated: {latest_atr:.6f}")
    except Exception as e:
        logger.error(f"❌ ATR calculation failed: {e}")

    # ボラティリティ計算
    try:
        returns = data["close"].pct_change()
        volatility = returns.rolling(window=20).std()
        if not volatility.empty:
            technical["volatility_20"] = float(volatility.iloc[-1])
            logger.info(f"✅ Volatility calculated: {technical['volatility_20']:.6f}")
    except Exception as e:
        logger.error(f"❌ Volatility calculation failed: {e}")

    # その他の重要指標
    try:
        # RSI
        if hasattr(calculator, "calculate_rsi"):
            rsi = calculator.calculate_rsi(data, period=14)
            if rsi is not None and not rsi.empty:
                technical["rsi_14"] = float(rsi.iloc[-1])

        # MACD
        if hasattr(calculator, "calculate_macd"):
            macd_result = calculator.calculate_macd(data)
            if macd_result is not None:
                technical["macd"] = float(
                    macd_result.get("macd", pd.Series()).iloc[-1]
                    if "macd" in macd_result
                    else 0
                )

    except Exception as e:
        logger.warning(f"⚠️ Additional indicators failed: {e}")

    logger.info(f"✅ Computed {len(technical)} technical indicators")
    return technical


def main():
    """メイン処理"""
    logger.info("🚀 Starting pre-computation for Phase 12.3...")

    try:
        # 設定読み込み
        config = load_config()

        # キャッシュ初期化
        cache = PreComputedCache()

        # 1. 市場データ取得
        market_data = fetch_market_data(config)
        cache.save_market_data(market_data)

        # 2. 97特徴量計算
        features = compute_features(market_data, config)
        cache.save_features(features)

        # 3. テクニカル指標計算
        technical = compute_technical_indicators(market_data)
        cache.save_technical(technical)

        # 4. メタデータ保存
        cache.save_metadata()

        logger.info("✅ Pre-computation completed successfully!")
        logger.info("📦 Cache files created in ./cache/ directory")

        # 検証
        if cache.has_valid_cache():
            logger.info("✅ Cache validation passed")
            cache_data = cache.load_all()
            logger.info(f"📊 Cache contents: {list(cache_data.keys())}")
        else:
            logger.error("❌ Cache validation failed")
            return 1

    except Exception as e:
        logger.error(f"❌ Pre-computation failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

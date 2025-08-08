#!/usr/bin/env python3
"""
特徴量生成の詳細デバッグスクリプト
RSIとrolling統計が生成されない原因を特定
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yaml

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crypto_bot.data.fetcher import MarketDataFetcher
from crypto_bot.ml.feature_engines.batch_calculator import BatchFeatureCalculator
from crypto_bot.ml.feature_engines.technical_engine import TechnicalFeatureEngine

# ログ設定（DEBUG）
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def debug_feature_generation():
    """特徴量生成の詳細デバッグ"""
    # 設定ファイル読み込み
    config_path = str(project_root / "config/production/production.yml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # データ取得
    fetcher = MarketDataFetcher(
        exchange_id="bitbank",
        symbol="BTC/JPY",
        api_key=config.get("data", {}).get("api_key"),
        api_secret=config.get("data", {}).get("api_secret"),
        testnet=False,
    )

    # より多くのデータを取得（RSI計算に必要）
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=96)  # 4日分のデータ
    df = fetcher.get_price_df(
        timeframe="1h", since=int(start_time.timestamp() * 1000), limit=96  # 96時間分
    )
    logger.info(f"📊 テストデータ: {len(df)}レコード")

    # BatchCalculatorとTechnicalFeatureEngine作成
    batch_calc = BatchFeatureCalculator(config)
    tech_engine = TechnicalFeatureEngine(config, batch_calc)

    print("\n" + "=" * 60)
    print("🔍 特徴量生成詳細デバッグ")
    print("=" * 60)

    # 1. RSIバッチ生成テスト
    print("\n1️⃣ RSIバッチ生成テスト:")
    rsi_batch = tech_engine.calculate_rsi_batch(df)
    print(f"   - RSIバッチサイズ: {len(rsi_batch)}")
    if len(rsi_batch) > 0:
        print(f"   - RSI特徴量: {list(rsi_batch.features.keys())}")
    else:
        print("   ❌ RSIバッチが空です！")

    # 2. Lag/Rollingバッチ生成テスト
    print("\n2️⃣ Lag/Rollingバッチ生成テスト:")
    lag_roll_batch = tech_engine.calculate_lag_rolling_batch(df)
    print(f"   - Lag/Rollingバッチサイズ: {len(lag_roll_batch)}")
    if len(lag_roll_batch) > 0:
        lag_roll_features = list(lag_roll_batch.features.keys())
        print(f"   - Lag/Rolling特徴量: {lag_roll_features}")

        # close_mean_10とclose_std_10を探す
        mean_features = [f for f in lag_roll_features if "mean" in f]
        std_features = [f for f in lag_roll_features if "std" in f]
        print(f"   - Mean特徴量: {mean_features}")
        print(f"   - Std特徴量: {std_features}")

    # 3. 全バッチ生成テスト
    print("\n3️⃣ 全バッチ生成:")
    all_batches = tech_engine.calculate_all_technical_batches(df)
    for i, batch in enumerate(all_batches):
        print(f"   - バッチ{i+1} ({batch.name}): {len(batch)}特徴量")
        if batch.name == "rsi_batch" and len(batch) == 0:
            print("     ⚠️ RSIバッチが空！")
        if batch.name == "lag_roll_batch":
            features = list(batch.features.keys())
            if "close_mean_10" not in features:
                print("     ⚠️ close_mean_10が含まれていない！")
            if "close_std_10" not in features:
                print("     ⚠️ close_std_10が含まれていない！")

    # 4. rolling_window設定確認
    rolling_window = config["ml"].get("rolling_window", 14)
    print(f"\n4️⃣ rolling_window設定: {rolling_window}")
    print(
        f"   → 期待される特徴量: close_mean_{rolling_window}, close_std_{rolling_window}"
    )

    # 5. calculate_lag_rolling_batchメソッドの詳細確認
    print("\n5️⃣ calculate_lag_rolling_batch内部動作:")
    try:
        # メソッドを直接呼び出してデバッグ
        lag_roll_features = {}

        # Lag特徴量
        lags = config["ml"].get("lags", [1, 2, 3])
        close_series = df["close"]

        for lag in lags:
            lag_roll_features[f"close_lag_{lag}"] = close_series.shift(lag)
        print(f"   - Lag特徴量生成: {list(lag_roll_features.keys())}")

        # Rolling統計
        rolling_window = config["ml"].get("rolling_window", 14)
        lag_roll_features[f"close_mean_{rolling_window}"] = close_series.rolling(
            rolling_window
        ).mean()
        lag_roll_features[f"close_std_{rolling_window}"] = close_series.rolling(
            rolling_window
        ).std()
        print(
            f"   - Rolling統計生成: close_mean_{rolling_window}, close_std_{rolling_window}"
        )

    except Exception as e:
        print(f"   ❌ エラー: {e}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    try:
        debug_feature_generation()
    except Exception as e:
        logger.error(f"❌ デバッグ失敗: {e}")
        import traceback

        traceback.print_exc()

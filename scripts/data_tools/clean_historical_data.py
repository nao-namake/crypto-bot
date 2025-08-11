#!/usr/bin/env python3
"""
データクリーニングスクリプト - btc_usd_2024_hourly.csvの異常値修正

Phase 14.6: データ品質修正・異常値クリーニング実施
- 1e+88等の異常値を検出・修正
- BTC価格範囲を適切な値（10,000-150,000 USD）に制限
- タイムスタンプ整合性確認
- バックアップ作成後に修正実施
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def clean_btc_historical_data():
    """BTC歴史データクリーニング実施"""

    data_path = Path("data/btc_usd_2024_hourly.csv")
    backup_path = Path(
        f"data/btc_usd_2024_hourly_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )

    logger.info("🧹 BTC歴史データクリーニング開始")

    # バックアップ作成
    logger.info(f"📦 バックアップ作成: {backup_path}")
    shutil.copy2(data_path, backup_path)

    # データ読み込み
    logger.info("📊 データ読み込み中...")
    df = pd.read_csv(data_path)
    original_rows = len(df)
    logger.info(f"📊 元データ行数: {original_rows:,}")

    # 異常値検出
    price_columns = ["open", "high", "low", "close"]

    # BTC価格の適切な範囲設定 (2023-2024年考慮)
    btc_min_price = 10000  # $10,000
    btc_max_price = 150000  # $150,000
    volume_max = 100000  # 出来高上限

    # 異常値検出
    for col in price_columns:
        anomaly_mask = (df[col] > btc_max_price) | (df[col] < btc_min_price)
        anomaly_count = anomaly_mask.sum()
        if anomaly_count > 0:
            logger.warning(f"⚠️ {col}列で異常値検出: {anomaly_count:,}行")

    # 出来高異常値検出
    volume_anomaly = (df["volume"] > volume_max) | (df["volume"] < 0)
    volume_anomaly_count = volume_anomaly.sum()
    if volume_anomaly_count > 0:
        logger.warning(f"⚠️ volume列で異常値検出: {volume_anomaly_count:,}行")

    # 異常値修正戦略
    logger.info("🔧 異常値修正実施中...")

    # 1. 極端な異常値（1e+80以上）を含む行を削除
    extreme_anomaly_mask = (
        (df["open"] > 1e80)
        | (df["high"] > 1e80)
        | (df["low"] > 1e80)
        | (df["close"] > 1e80)
    )
    extreme_anomaly_count = extreme_anomaly_mask.sum()

    if extreme_anomaly_count > 0:
        logger.warning(f"🗑️ 極端異常値行削除: {extreme_anomaly_count:,}行")
        df = df[~extreme_anomaly_mask].copy()

    # 2. 適度な異常値は前後の値で補間
    for col in price_columns:
        anomaly_mask = (df[col] > btc_max_price) | (df[col] < btc_min_price)
        if anomaly_mask.sum() > 0:
            logger.info(f"🔄 {col}列補間修正: {anomaly_mask.sum():,}行")
            # 線形補間で修正
            df.loc[anomaly_mask, col] = np.nan
            df[col] = df[col].interpolate(method="linear")

    # 3. 出来高異常値修正
    volume_anomaly = (df["volume"] > volume_max) | (df["volume"] < 0)
    if volume_anomaly.sum() > 0:
        logger.info(f"🔄 volume補間修正: {volume_anomaly.sum():,}行")
        df.loc[volume_anomaly, "volume"] = np.nan
        df["volume"] = df["volume"].interpolate(method="linear")
        df["volume"] = df["volume"].fillna(
            df["volume"].median()
        )  # 残りは中央値で埋める

    # 4. タイムスタンプ重複・欠損チェック
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    duplicates = df["timestamp"].duplicated().sum()
    if duplicates > 0:
        logger.warning(f"⚠️ タイムスタンプ重複検出: {duplicates}行")
        df = df.drop_duplicates(subset=["timestamp"]).copy()

    # 5. OHLC整合性チェック・修正
    ohlc_errors = 0
    for idx in df.index:
        o, h, l, c = df.loc[idx, ["open", "high", "low", "close"]]

        # high >= max(open, close, low) かつ low <= min(open, close, high)
        if h < max(o, l, c):
            df.loc[idx, "high"] = max(o, l, c)
            ohlc_errors += 1
        if l > min(o, h, c):
            df.loc[idx, "low"] = min(o, h, c)
            ohlc_errors += 1

    if ohlc_errors > 0:
        logger.info(f"🔧 OHLC整合性修正: {ohlc_errors}箇所")

    # 最終データ品質確認
    final_rows = len(df)
    removed_rows = original_rows - final_rows

    logger.info("✅ データクリーニング完了")
    logger.info(f"📊 最終行数: {final_rows:,} (削除: {removed_rows:,}行)")

    # 価格範囲確認
    for col in price_columns:
        min_val = df[col].min()
        max_val = df[col].max()
        logger.info(f"📈 {col}: ${min_val:,.2f} - ${max_val:,.2f}")

    # 出来高範囲確認
    vol_min = df["volume"].min()
    vol_max = df["volume"].max()
    logger.info(f"📊 volume: {vol_min:,.2f} - {vol_max:,.2f}")

    # クリーニング済みデータ保存
    logger.info("💾 クリーニング済みデータ保存中...")
    df.to_csv(data_path, index=False)

    logger.info("🎉 データクリーニング完了・品質向上実現!")

    # 統計サマリー出力
    return {
        "original_rows": original_rows,
        "final_rows": final_rows,
        "removed_rows": removed_rows,
        "backup_path": str(backup_path),
        "price_range": {
            col: {"min": float(df[col].min()), "max": float(df[col].max())}
            for col in price_columns
        },
        "volume_range": {
            "min": float(df["volume"].min()),
            "max": float(df["volume"].max()),
        },
    }


if __name__ == "__main__":
    try:
        result = clean_btc_historical_data()
        print(f"\n🎊 データクリーニング成功!")
        print(f"📊 処理結果: {result['original_rows']:,} → {result['final_rows']:,}行")
        print(f"📦 バックアップ: {result['backup_path']}")
    except Exception as e:
        logger.error(f"❌ データクリーニング失敗: {e}")
        raise

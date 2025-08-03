#!/usr/bin/env python3
"""
バックテスト用CSVデータ作成スクリプト
127特徴量計算に十分なデータ量確保
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_realistic_crypto_data():
    """現実的な仮想通貨データ生成"""
    logger.info("現実的な仮想通貨バックテストデータ生成開始")

    # データ期間（十分な期間確保）
    start_date = "2023-01-01"
    end_date = "2024-12-31"
    freq = "1H"

    # 時間インデックス作成
    timestamps = pd.date_range(start=start_date, end=end_date, freq=freq)
    n_periods = len(timestamps)

    logger.info(f"データ期間: {start_date} - {end_date}")
    logger.info(f"データポイント数: {n_periods}")

    # シード設定
    np.random.seed(42)

    # より現実的な価格生成アルゴリズム
    base_price = 30000  # BTC初期価格

    # 複数の市場要因を組み込んだ価格生成

    # 1. 長期トレンド（年間成長）
    long_trend = np.linspace(0, 0.8, n_periods)  # 年間80%成長トレンド

    # 2. 季節性（四半期サイクル）
    seasonal = 0.1 * np.sin(
        2 * np.pi * np.arange(n_periods) / (24 * 30 * 3)
    )  # 3ヶ月サイクル

    # 3. 週次パターン
    weekly = 0.05 * np.sin(2 * np.pi * np.arange(n_periods) / (24 * 7))  # 週次サイクル

    # 4. 日次パターン
    daily = 0.02 * np.sin(2 * np.pi * np.arange(n_periods) / 24)  # 日次サイクル

    # 5. ランダムウォーク
    random_walk = np.cumsum(np.random.normal(0, 0.01, n_periods))

    # 6. ボラティリティクラスタリング
    vol_base = 0.02
    vol_persistence = 0.95
    volatility = [vol_base]

    for i in range(1, n_periods):
        new_vol = (
            vol_base * (1 - vol_persistence)
            + vol_persistence * volatility[-1]
            + 0.001 * np.random.normal()
        )
        new_vol = max(0.005, min(0.08, new_vol))  # ボラティリティ制限
        volatility.append(new_vol)

    volatility = np.array(volatility)

    # 7. ジャンプ（急激な価格変動）
    jump_probability = 0.001  # 0.1%の確率
    jump_magnitudes = np.random.choice(
        [0, 1], size=n_periods, p=[1 - jump_probability, jump_probability]
    )
    jump_directions = np.random.choice([-1, 1], size=n_periods)
    jump_sizes = (
        np.random.exponential(0.05, n_periods) * jump_magnitudes * jump_directions
    )

    # 8. 市場レジーム（強気・弱気）
    regime_changes = np.random.poisson(0.00002, n_periods)  # 稀なレジーム変更
    current_regime = 1  # 1: 強気, -1: 弱気
    regime_impact = []

    for change in regime_changes:
        if change > 0:
            current_regime *= -1
        regime_impact.append(current_regime * 0.01)

    regime_impact = np.array(regime_impact)

    # 全要因を統合してリターン生成
    returns = (
        long_trend / n_periods  # 長期トレンド
        + seasonal  # 季節性
        + weekly  # 週次パターン
        + daily  # 日次パターン
        + random_walk / 100  # ランダムウォーク
        + volatility * np.random.normal(0, 1, n_periods)  # ボラティリティクラスタリング
        + jump_sizes  # ジャンプ
        + regime_impact  # レジーム
    )

    # 累積価格計算
    log_prices = np.log(base_price) + np.cumsum(returns)
    prices = np.exp(log_prices)

    # OHLC生成
    # より現実的なOHLC計算
    opens = np.roll(prices, 1)
    opens[0] = base_price
    closes = prices

    # 高値・安値の生成（現実的な値幅）
    intraday_ranges = volatility * prices * np.random.exponential(0.5, n_periods)
    highs = np.maximum(opens, closes) + intraday_ranges * np.random.uniform(
        0.3, 1.0, n_periods
    )
    lows = np.minimum(opens, closes) - intraday_ranges * np.random.uniform(
        0.3, 1.0, n_periods
    )

    # 出来高生成（価格変動と相関）
    price_changes = np.abs(np.diff(np.log(prices), prepend=np.log(base_price)))
    base_volume = 1000
    volume_multiplier = 1 + 5 * price_changes + 2 * volatility
    volumes = base_volume * volume_multiplier * np.random.lognormal(0, 0.3, n_periods)

    # データフレーム作成
    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
        }
    )

    # データ検証
    df["price_change"] = df["close"].pct_change()
    df["volume_change"] = df["volume"].pct_change()

    logger.info(f"価格統計:")
    logger.info(f"  開始価格: ${df['close'].iloc[0]:,.0f}")
    logger.info(f"  終了価格: ${df['close'].iloc[-1]:,.0f}")
    logger.info(
        f"  総リターン: {(df['close'].iloc[-1]/df['close'].iloc[0] - 1)*100:.1f}%"
    )
    logger.info(
        f"  年間ボラティリティ: {df['price_change'].std() * np.sqrt(24*365) * 100:.1f}%"
    )
    logger.info(f"  平均日次出来高: {df['volume'].mean():,.0f}")

    # 異常値チェック
    high_low_valid = (df["high"] >= df[["open", "close"]].max(axis=1)).all()
    low_high_valid = (df["low"] <= df[["open", "close"]].min(axis=1)).all()

    logger.info(f"データ整合性チェック:")
    logger.info(f"  高値 >= max(始値, 終値): {high_low_valid}")
    logger.info(f"  安値 <= min(始値, 終値): {low_high_valid}")

    if not (high_low_valid and low_high_valid):
        logger.warning("OHLC整合性を修正中...")
        # 整合性修正
        df["high"] = np.maximum(df["high"], df[["open", "close"]].max(axis=1))
        df["low"] = np.minimum(df["low"], df[["open", "close"]].min(axis=1))

    # 不要な列削除
    df = df[["timestamp", "open", "high", "low", "close", "volume"]]

    return df


def save_backtest_data(df):
    """バックテストデータ保存"""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    csv_path = data_dir / "btc_usd_2024_hourly.csv"

    # CSV保存（タイムスタンプをISO形式で）
    df_save = df.copy()
    df_save["timestamp"] = df_save["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    df_save.to_csv(csv_path, index=False)
    logger.info(f"バックテストデータ保存完了: {csv_path}")
    logger.info(f"ファイルサイズ: {csv_path.stat().st_size / 1024 / 1024:.1f} MB")

    return csv_path


def main():
    """メイン実行"""
    logger.info("=" * 80)
    logger.info("127特徴量対応バックテストデータ作成")
    logger.info("=" * 80)

    # データ生成
    df = create_realistic_crypto_data()

    # データ保存
    csv_path = save_backtest_data(df)

    logger.info("=" * 80)
    logger.info("バックテストデータ作成完了")
    logger.info("=" * 80)
    logger.info(f"データファイル: {csv_path}")
    logger.info(f"データ期間: {df['timestamp'].min()} - {df['timestamp'].max()}")
    logger.info(f"データポイント数: {len(df)}")
    logger.info("127特徴量計算に十分なデータが準備できました！")


if __name__ == "__main__":
    main()

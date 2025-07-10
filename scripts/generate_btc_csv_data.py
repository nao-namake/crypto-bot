#!/usr/bin/env python3
"""
BTC 1年分のCSVデータ生成スクリプト
実際のデータ取得は時間がかかるため、リアルなサンプルデータを生成します。
"""

import os

import numpy as np
import pandas as pd


def generate_realistic_btc_data(
    start_date: str = "2024-01-01", end_date: str = "2024-12-31"
) -> pd.DataFrame:
    """
    リアルなBTCデータを生成

    Parameters
    ----------
    start_date : str
        開始日 (YYYY-MM-DD)
    end_date : str
        終了日 (YYYY-MM-DD)

    Returns
    -------
    pd.DataFrame
        BTC OHLCV データ
    """
    # 日付範囲生成（1時間足）
    date_range = pd.date_range(start=start_date, end=end_date, freq="1H", tz="UTC")

    # 基本パラメータ
    n_periods = len(date_range)
    base_price = 45000.0  # 2024年BTC平均価格

    # 価格トレンド生成（年間で30%上昇）
    trend = np.linspace(0, 0.3, n_periods)

    # ランダムウォーク生成
    np.random.seed(42)  # 再現性のため
    returns = np.random.normal(0, 0.02, n_periods)  # 平均0、標準偏差2%

    # 季節性効果（年末年始に下落、夏に上昇）
    seasonal = 0.1 * np.sin(2 * np.pi * np.arange(n_periods) / (365 * 24))

    # ボラティリティクラスタリング
    volatility = np.abs(returns)
    for i in range(1, n_periods):
        volatility[i] = 0.1 * volatility[i - 1] + 0.9 * volatility[i]

    # 調整済みリターン
    adjusted_returns = returns * (1 + volatility) + seasonal * 0.001

    # 価格生成
    log_prices = np.log(base_price) + np.cumsum(adjusted_returns) + trend
    close_prices = np.exp(log_prices)

    # OHLCV生成
    data = []
    for i in range(n_periods):
        close = close_prices[i]

        # 日中変動（±2%）
        intraday_range = close * 0.02
        high = close + np.random.uniform(0, intraday_range)
        low = close - np.random.uniform(0, intraday_range)

        # Open価格（前のCloseに近い）
        if i == 0:
            open_price = close * (1 + np.random.normal(0, 0.001))
        else:
            open_price = close_prices[i - 1] * (1 + np.random.normal(0, 0.005))

        # 価格整合性確保
        prices = [open_price, high, low, close]
        high = max(prices)
        low = min(prices)

        # 出来高生成（価格変動に連動）
        volume_base = 1000.0
        volume_multiplier = 1 + abs(adjusted_returns[i]) * 10
        volume = volume_base * volume_multiplier * np.random.uniform(0.5, 2.0)

        data.append(
            {
                "datetime": date_range[i],
                "open": round(open_price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(close, 2),
                "volume": round(volume, 6),
            }
        )

    df = pd.DataFrame(data)
    df.set_index("datetime", inplace=True)

    # データ品質チェック
    print(f"生成されたデータ期間: {df.index[0]} - {df.index[-1]}")
    print(f"データ件数: {len(df):,} 件")
    print(f"価格範囲: ${df['close'].min():,.2f} - ${df['close'].max():,.2f}")
    print(
        f"年間リターン: {(df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100:.1f}%"
    )

    return df


def main():
    """メイン実行"""
    print("🚀 BTC 1年分CSVデータ生成開始...")

    # データ生成
    df = generate_realistic_btc_data("2024-01-01", "2024-12-31")

    # データディレクトリ作成
    data_dir = "/Users/nao/Desktop/bot/data"
    os.makedirs(data_dir, exist_ok=True)

    # CSV保存
    csv_path = os.path.join(data_dir, "btc_usd_2024_hourly.csv")
    df.to_csv(csv_path)

    print(f"✅ CSVファイル生成完了: {csv_path}")
    print(f"📊 ファイルサイズ: {os.path.getsize(csv_path) / 1024 / 1024:.1f} MB")

    # サンプルデータ表示
    print("\n📋 サンプルデータ（最初の5行）:")
    print(df.head())

    print("\n📋 サンプルデータ（最後の5行）:")
    print(df.tail())

    print("\n🎯 統計情報:")
    print(df.describe())


if __name__ == "__main__":
    main()

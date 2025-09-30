#!/usr/bin/env python3
"""
過去データCSV収集スクリプト

本番環境と同じBitbank APIから過去データを取得してCSV形式で保存。
バックテストの高速化とAPI依存削減を実現。

使用方法:
    python src/backtest/scripts/collect_historical_csv.py --days 180
    python src/backtest/scripts/collect_historical_csv.py --days 90 --symbol BTC/JPY
"""

import argparse
import asyncio
import csv
import ssl

# プロジェクトルートからの相対パス設定
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

import aiohttp
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.core.logger import get_logger
from src.data.bitbank_client import BitbankClient


class HistoricalDataCollector:
    """過去データCSV収集システム"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.output_dir = Path(__file__).parent.parent / "data" / "historical"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # SSL証明書設定（セキュア設定）
        self.ssl_context = ssl.create_default_context()

    async def collect_data(
        self,
        symbol: str = "BTC/JPY",
        days: int = 180,
        timeframes: List[str] = None,
        start_timestamp: int = None,
        end_timestamp: int = None,
    ) -> None:
        """
        過去データ収集・CSV保存

        Args:
            symbol: 通貨ペア
            days: 収集日数
            timeframes: タイムフレームリスト（デフォルト: ['15m', '4h']）
            start_timestamp: 開始タイムスタンプ（ミリ秒）
            end_timestamp: 終了タイムスタンプ（ミリ秒）
        """
        if timeframes is None:
            # 設定からタイムフレームを取得
            try:
                from ...core.config import get_data_config

                timeframes = get_data_config("timeframes", ["4h", "15m"])
            except Exception:
                timeframes = ["4h", "15m"]  # フォールバック

        self.logger.info(f"過去データ収集開始: {symbol}, {days}日間, {timeframes}")

        # 各タイムフレームでデータ収集
        for timeframe in timeframes:
            try:
                await self._collect_timeframe_data(
                    symbol, timeframe, days, start_timestamp, end_timestamp
                )
                self.logger.info(f"✅ {timeframe}データ収集完了")
            except Exception as e:
                self.logger.error(f"❌ {timeframe}データ収集失敗: {e}")

    async def _collect_timeframe_data(
        self,
        symbol: str,
        timeframe: str,
        days: int,
        start_timestamp: int = None,
        end_timestamp: int = None,
    ) -> None:
        """タイムフレーム別データ収集"""

        # 4時間足の場合は直接API、それ以外はBitbankClient使用
        if timeframe == "4h":
            data = await self._collect_4h_direct(symbol, days, start_timestamp, end_timestamp)
        else:
            data = await self._collect_via_client(
                symbol, timeframe, days, start_timestamp, end_timestamp
            )

        if data:
            await self._save_to_csv(data, symbol, timeframe)
            self.logger.info(f"CSV保存完了: {symbol}_{timeframe} ({len(data)}件)")
        else:
            self.logger.warning(f"データ取得できませんでした: {symbol}_{timeframe}")

    async def _collect_4h_direct(
        self, symbol: str, days: int, start_timestamp: int = None, end_timestamp: int = None
    ) -> List[List]:
        """4時間足データ直接取得"""
        try:
            # 複数年のデータを取得
            current_year = datetime.now().year
            start_year = (datetime.now() - timedelta(days=days)).year

            all_data = []

            for year in range(start_year, current_year + 1):
                year_data = await self._fetch_4h_year_data(symbol, year)
                if year_data:
                    all_data.extend(year_data)

            # 日付フィルタリング
            if start_timestamp and end_timestamp:
                # 指定期間でフィルタ
                filtered_data = [
                    row for row in all_data if start_timestamp <= row[0] <= end_timestamp
                ]
            else:
                # 日数指定でフィルタ
                cutoff_date = datetime.now() - timedelta(days=days)
                cutoff_timestamp = int(cutoff_date.timestamp() * 1000)
                filtered_data = [
                    row for row in all_data if row[0] >= cutoff_timestamp
                ]  # timestampでフィルタ

            return sorted(filtered_data, key=lambda x: x[0])  # 時系列順にソート

        except Exception as e:
            self.logger.error(f"4時間足直接取得エラー: {e}")
            return []

    async def _fetch_4h_year_data(self, symbol: str, year: int) -> List[List]:
        """年別4時間足データ取得"""
        try:
            pair = symbol.lower().replace("/", "_")  # BTC/JPY -> btc_jpy
            url = f"https://public.bitbank.cc/{pair}/candlestick/4hour/{year}"

            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                timeout = aiohttp.ClientTimeout(total=30.0)
                async with session.get(url, timeout=timeout) as response:
                    data = await response.json()

                    if data.get("success") == 1:
                        candlestick_data = data["data"]["candlestick"][0]["ohlcv"]

                        # ccxt形式に変換: [timestamp_ms, open, high, low, close, volume]
                        ohlcv_data = []
                        for item in candlestick_data:
                            if len(item) >= 6:
                                ohlcv_data.append(
                                    [
                                        item[5],  # timestamp_ms
                                        float(item[0]),  # open
                                        float(item[1]),  # high
                                        float(item[2]),  # low
                                        float(item[3]),  # close
                                        float(item[4]),  # volume
                                    ]
                                )

                        return ohlcv_data

        except Exception as e:
            self.logger.warning(f"年別データ取得失敗 {year}: {e}")

        return []

    async def _collect_via_client(
        self,
        symbol: str,
        timeframe: str,
        days: int,
        start_timestamp: int = None,
        end_timestamp: int = None,
    ) -> List[List]:
        """BitbankClient経由でデータ取得"""
        try:
            client = BitbankClient()

            # 期間指定がある場合は直接指定、なければ日数から計算
            if start_timestamp and end_timestamp:
                since_timestamp = start_timestamp
                end_ts = end_timestamp
            else:
                current_date = datetime.now()
                since_date = current_date - timedelta(days=days)
                since_timestamp = int(since_date.timestamp() * 1000)
                end_ts = int(current_date.timestamp() * 1000)

            # 大量データ取得のための分割処理
            all_data = []

            # 15分足の場合、大量データが必要なので分割取得
            period_days = (end_ts - since_timestamp) / (1000 * 60 * 60 * 24)  # ミリ秒を日数に変換

            # 10日分ずつ取得（APIレート制限対応）
            for i in range(0, int(period_days), 10):
                batch_start = since_timestamp + (i * 24 * 60 * 60 * 1000)  # i日後の開始時刻
                batch_end = min(
                    batch_start + (10 * 24 * 60 * 60 * 1000), end_ts
                )  # 10日後または終了時刻

                data = await client.fetch_ohlcv(
                    symbol=symbol, timeframe=timeframe, since=batch_start, limit=2000
                )

                if data:
                    # 期間内のデータのみ追加
                    filtered_batch = [row for row in data if batch_start <= row[0] <= batch_end]
                    all_data.extend(filtered_batch)

                # API制限対応
                await asyncio.sleep(1)

            # 重複除去とソート
            unique_data = {}
            for row in all_data:
                unique_data[row[0]] = row  # timestampをキーに重複除去

            return sorted(unique_data.values(), key=lambda x: x[0])

        except Exception as e:
            self.logger.error(f"Client経由取得エラー: {e}")
            return []

    async def _save_to_csv(self, data: List[List], symbol: str, timeframe: str) -> None:
        """データをCSV形式で保存"""
        # ファイル名固定化（日付なし）
        filename = f"{symbol.replace('/', '_')}_{timeframe}.csv"
        filepath = self.output_dir / filename

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # ヘッダー行
            writer.writerow(["timestamp", "open", "high", "low", "close", "volume", "datetime"])

            # データ行
            for row in data:
                timestamp = row[0]
                dt = datetime.fromtimestamp(timestamp / 1000)
                writer.writerow(
                    [
                        timestamp,
                        row[1],  # open
                        row[2],  # high
                        row[3],  # low
                        row[4],  # close
                        row[5],  # volume
                        dt.strftime("%Y-%m-%d %H:%M:%S"),  # 可読性のため
                    ]
                )

        self.logger.info(f"CSV保存: {filepath} ({len(data)}件)")


async def main():
    """メイン実行"""
    # 設定からデフォルト値を取得
    try:
        from ...core.config import get_config, get_data_config

        config = get_config()
        default_symbol = config.exchange.symbol
        default_timeframes = get_data_config("timeframes", ["4h", "15m"])
    except Exception:
        default_symbol = "BTC/JPY"
        default_timeframes = ["4h", "15m"]

    parser = argparse.ArgumentParser(description="過去データCSV収集")
    parser.add_argument("--days", type=int, default=180, help="収集日数（デフォルト: 180日）")
    parser.add_argument(
        "--symbol", default=default_symbol, help=f"通貨ペア（デフォルト: {default_symbol}）"
    )
    parser.add_argument(
        "--timeframes",
        nargs="+",
        default=default_timeframes,
        help=f"タイムフレーム（デフォルト: {default_timeframes}）",
    )
    parser.add_argument("--start-timestamp", type=int, help="開始タイムスタンプ（ミリ秒）")
    parser.add_argument("--end-timestamp", type=int, help="終了タイムスタンプ（ミリ秒）")
    parser.add_argument("--match-4h", action="store_true", help="既存の4時間足データと期間を揃える")

    args = parser.parse_args()

    # 既存4時間足データと期間を揃える場合
    if args.match_4h:
        # 既存4時間足データの期間を取得
        csv_path = Path(__file__).parent.parent / "data" / "historical" / "BTC_JPY_4h.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            if not df.empty:
                args.start_timestamp = int(df["timestamp"].iloc[0])
                args.end_timestamp = int(df["timestamp"].iloc[-1])
                print(
                    f"既存4時間足データ期間に合わせます: {args.start_timestamp} - {args.end_timestamp}"
                )
        else:
            print("既存4時間足データが見つかりません")
            return

    collector = HistoricalDataCollector()
    await collector.collect_data(
        symbol=args.symbol,
        days=args.days,
        timeframes=args.timeframes,
        start_timestamp=args.start_timestamp,
        end_timestamp=args.end_timestamp,
    )

    print("✅ 過去データCSV収集完了")


if __name__ == "__main__":
    asyncio.run(main())

# =============================================================================
# ファイル名: crypto_bot/data/fetcher.py
# 説明:
# ・MarketDataFetcher：取引所（Bybit等）からOHLCVデータをDataFrame形式で取得するユーティリティ
# ・DataPreprocessor：取得した価格データ（OHLCV）の重複除去、欠損補完、外れ値除去などの前処理を一括で行う
# ・.envファイルやAPIキー自動読込、Bybit専用の細かい工夫もあり
# ・バックテストや学習データ用のデータ取得・整形の中心的な役割
# =============================================================================

import logging
import numbers
import os
from datetime import datetime
from typing import List, Optional, Union

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from pandas.tseries.frequencies import to_offset

from crypto_bot.execution.factory import create_exchange_client

load_dotenv()

logger = logging.getLogger(__name__)


class MarketDataFetcher:
    def __init__(
        self,
        exchange_id: str = "bitbank",
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        symbol: str = "BTC/JPY",
        testnet: bool = False,
        ccxt_options: Optional[dict] = None,
        csv_path: Optional[str] = None,
    ):
        self.exchange_id = exchange_id
        self.symbol = symbol
        self.csv_path = csv_path
        self.testnet = testnet

        # CSV モードの場合はAPI接続をスキップ
        if csv_path:
            self.client = None
            self.exchange = None
        else:
            api_key = api_key or os.getenv(f"{exchange_id.upper()}_API_KEY")
            api_secret = api_secret or os.getenv(f"{exchange_id.upper()}_API_SECRET")
            env_test_key = os.getenv(f"{exchange_id.upper()}_TESTNET_API_KEY")
            testnet = testnet or bool(env_test_key)
            self.client = create_exchange_client(
                exchange_id=exchange_id,
                api_key=api_key,
                api_secret=api_secret,
                testnet=testnet,
                ccxt_options=ccxt_options or {},
            )
            # Bitbank固有の設定があれば追加
            if exchange_id == "bitbank":
                # Bitbank特有の設定を追加する場合はここで実装
                pass
            self.exchange = getattr(self.client, "_exchange", self.client)

    def get_price_df(
        self,
        timeframe: str = "1m",
        since: Optional[Union[int, float, str, datetime]] = None,
        limit: Optional[int] = None,
        paginate: bool = False,
        sleep: bool = True,
        per_page: int = 500,
    ) -> pd.DataFrame:
        # CSV モードの場合は CSV から読み込み
        if self.csv_path:
            return self._get_price_from_csv(since, limit)

        import time

        since_ms: Optional[int] = None
        if since is not None:
            if isinstance(since, str):
                dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
                since_ms = int(dt.timestamp() * 1000)
            elif isinstance(since, datetime):
                since_ms = int(since.timestamp() * 1000)
            elif isinstance(since, numbers.Real):
                ts = int(since)
                since_ms = ts if ts > 1e12 else int(ts * 1000)
            else:
                raise TypeError(f"Unsupported type for since: {type(since)}")

        max_records = limit if limit is not None else float("inf")

        if paginate and limit:
            logger.info(f"🔄 Paginated fetch: limit={limit}, per_page={per_page}")
            records: List = []
            seen_ts = set()
            last_since = since_ms
            retries = 0
            MAX_RETRIES = 20  # 5→20に増加

            while len(records) < max_records and retries < MAX_RETRIES:
                logger.info(
                    f"🔄 Batch {retries+1}: fetching from {last_since}, "
                    f"target={len(records)}/{max_records}"
                )

                batch = self.client.fetch_ohlcv(
                    self.symbol, timeframe, last_since, per_page
                )

                if isinstance(batch, pd.DataFrame):
                    logger.info(f"✅ Received DataFrame directly: {len(batch)} records")
                    return batch

                if not batch:
                    logger.warning(f"⚠️ Empty batch received at retry {retries}")
                    retries += 1
                    continue

                logger.info(f"📊 Batch received: {len(batch)} records")
                added = False
                for row in batch:
                    ts = row[0]
                    if ts not in seen_ts:
                        seen_ts.add(ts)
                        records.append(row)
                        last_since = ts + 1
                        added = True

                if not added:
                    logger.warning(f"⚠️ No new records added in batch {retries}")
                    retries += 1
                else:
                    logger.info(f"✅ Added records: total={len(records)}")

                if (
                    sleep
                    and hasattr(self.exchange, "rateLimit")
                    and self.exchange.rateLimit
                ):
                    time.sleep(self.exchange.rateLimit / 1000.0)

            logger.info(
                f"✅ Pagination complete: {len(records)} total records collected"
            )
            data = records if limit is None else records[:limit]

        else:
            raw = self.client.fetch_ohlcv(self.symbol, timeframe, since_ms, limit)
            if (
                sleep
                and hasattr(self.exchange, "rateLimit")
                and self.exchange.rateLimit
            ):
                time.sleep(self.exchange.rateLimit / 1000.0)
            if isinstance(raw, pd.DataFrame):
                return raw
            data = raw or []

            # Bitbank固有の再試行ロジック（必要に応じて実装）
            if not data and self.exchange_id == "bitbank":
                # Bitbank特有の処理が必要な場合はここで実装
                pass

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(
            data, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df.set_index("datetime")

        if isinstance(since, datetime) or (isinstance(since, str) and since):
            df = df.iloc[1:]

        if limit is not None:
            df = df.head(limit)

        return df[["open", "high", "low", "close", "volume"]]

    def _get_price_from_csv(
        self,
        since: Optional[Union[int, float, str, datetime]] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        CSVファイルから価格データを読み込み

        Parameters
        ----------
        since : Optional[Union[int, float, str, datetime]]
            開始時刻
        limit : Optional[int]
            取得件数制限

        Returns
        -------
        pd.DataFrame
            価格データ
        """
        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(f"CSV file not found: {self.csv_path}")

        # CSVファイル読み込み
        df = pd.read_csv(self.csv_path, parse_dates=True, index_col=0)

        # インデックスがdatetimeでない場合は変換
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)

        # タイムゾーンを UTC に設定
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")

        # since パラメータでフィルタリング
        if since is not None:
            if isinstance(since, str):
                since_dt = pd.to_datetime(since, utc=True)
            elif isinstance(since, datetime):
                since_dt = since
                if since_dt.tzinfo is None:
                    since_dt = since_dt.replace(tzinfo=pd.Timestamp.now().tz)
            else:
                # タイムスタンプの場合
                since_dt = pd.to_datetime(since, unit="ms", utc=True)

            df = df[df.index >= since_dt]

        # limit パラメータで件数制限
        if limit is not None:
            df = df.head(limit)

        # 必要な列のみ返す
        required_columns = ["open", "high", "low", "close", "volume"]
        available_columns = [col for col in required_columns if col in df.columns]

        if not available_columns:
            raise ValueError(
                f"Required columns {required_columns} not found in CSV file"
            )

        return df[available_columns]


class DataPreprocessor:
    @staticmethod
    def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
        return df[~df.index.duplicated(keep="first")]

    @staticmethod
    def fill_missing_bars(df: pd.DataFrame, timeframe: str = "1h") -> pd.DataFrame:
        freq_offset = to_offset(timeframe)
        idx = pd.date_range(
            start=df.index[0],
            end=df.index[-1],
            freq=freq_offset,
            tz=df.index.tz,
        )
        df2 = df.reindex(idx)
        for col in ["open", "high", "low", "close", "volume"]:
            df2[col] = df2[col].ffill()
        return df2

    @staticmethod
    def remove_outliers(
        df: pd.DataFrame, thresh: float = 3.5, window: int = 20
    ) -> pd.DataFrame:
        df = df.copy()
        price_cols = ["open", "high", "low", "close"]
        for col in [c for c in price_cols if c in df.columns]:
            median = (
                df[col]
                .rolling(
                    window=window,
                    center=True,
                    min_periods=1,
                )
                .median()
            )
            deviation = (df[col] - median).abs()
            mad = deviation.rolling(
                window=window,
                center=True,
                min_periods=1,
            ).median()
            mad = mad + 1e-8
            modified_zscore = 0.6745 * deviation / mad
            is_outlier = modified_zscore > thresh
            temp = df[col].copy()
            temp[is_outlier] = np.nan
            filled = temp.rolling(
                window=window,
                center=True,
                min_periods=1,
            ).mean()
            filled = filled.fillna(method="ffill").fillna(method="bfill")
            df[col] = np.where(is_outlier, filled, df[col])
        return df

    @staticmethod
    def clean(
        df: pd.DataFrame,
        timeframe: str = "1h",
        thresh: float = 3.5,
        window: int = 20,
    ) -> pd.DataFrame:
        df = DataPreprocessor.remove_duplicates(df)
        df = DataPreprocessor.fill_missing_bars(df, timeframe)
        df = DataPreprocessor.remove_outliers(df, thresh, window)
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].ffill().bfill()
        return df


class OIDataFetcher:
    """OI（未決済建玉）データ取得クラス"""

    def __init__(self, market_fetcher: MarketDataFetcher):
        self.market_fetcher = market_fetcher
        self.exchange = market_fetcher.exchange
        self.symbol = market_fetcher.symbol

    def get_oi_data(
        self,
        timeframe: str = "1h",
        since: Optional[Union[str, datetime]] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        OI（未決済建玉）データを取得

        Returns
        -------
        pd.DataFrame
            OIデータ（index: datetime, columns: oi_amount, oi_value）
        """
        try:
            # Bitbankの場合のOI取得（現物・信用取引対応）
            if self.market_fetcher.exchange_id == "bitbank":
                # Bitbank現物取引にはOIがないため、代替指標を使用
                # 取引量×価格でポジション規模を推定
                logger.info("Generating OI approximation for Bitbank")

                # 最新の価格・出来高データを取得
                price_data = self.market_fetcher.get_price_df(
                    timeframe="1h", limit=168  # 1週間分
                )

                if not price_data.empty:
                    # ポジション規模の推定（出来高×価格）
                    position_size = price_data["volume"] * price_data["close"]

                    result = pd.DataFrame(
                        {
                            "oi_amount": position_size,
                            "oi_value": position_size * price_data["close"],
                        }
                    )

                    return result

                # データがない場合は空のDataFrame
                return pd.DataFrame(columns=["oi_amount", "oi_value"])

        except Exception as e:
            logger.warning(f"Could not fetch OI approximation: {e}")

        # デフォルト: 空のDataFrameを返す
        return pd.DataFrame(columns=["oi_amount", "oi_value"])

    def calculate_oi_features(self, df: pd.DataFrame, window: int = 24) -> pd.DataFrame:
        """
        OI関連の特徴量を計算

        Parameters
        ----------
        df : pd.DataFrame
            OIデータ
        window : int
            移動平均の期間

        Returns
        -------
        pd.DataFrame
            OI特徴量付きDataFrame
        """
        if df.empty or "oi_amount" not in df.columns:
            return df

        # OI変化率
        df["oi_pct_change"] = df["oi_amount"].pct_change()

        # OI移動平均
        df[f"oi_ma_{window}"] = df["oi_amount"].rolling(window=window).mean()

        # OI標準化（Z-score）
        df["oi_zscore"] = (
            df["oi_amount"] - df["oi_amount"].rolling(window=window).mean()
        ) / df["oi_amount"].rolling(window=window).std()

        # OI勢い（momentum）
        df["oi_momentum"] = df["oi_amount"] / df["oi_amount"].shift(window) - 1

        # OI急激な変化検知
        df["oi_spike"] = (
            df["oi_pct_change"].abs()
            > df["oi_pct_change"].rolling(window=window).std() * 2
        ).astype(int)

        return df

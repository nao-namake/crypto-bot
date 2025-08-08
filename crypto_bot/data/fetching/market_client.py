"""
Market Client - Phase 16.3-C Split

統合前: crypto_bot/data/fetcher.py（1,456行）
分割後: crypto_bot/data/fetching/market_client.py

機能:
- MarketDataFetcher基本クラス（API接続・認証・設定）
- 並列データ取得・CSV読み込み機能
- 残高取得・エラーハンドリング・resilience統合
- 基本的なクライアント機能（複雑なデータ処理は除く）

Phase 16.3-C実装日: 2025年8月8日
"""

import concurrent.futures
import logging
import os
from datetime import datetime
from typing import Optional, Union

import pandas as pd
from dotenv import load_dotenv

from crypto_bot.execution.factory import create_exchange_client
from crypto_bot.utils.error_resilience import get_resilience_manager, with_resilience

load_dotenv()

logger = logging.getLogger(__name__)


class MarketDataFetcher:
    """
    市場データ取得クライアント

    - 取引所API接続・認証
    - 基本データ取得・残高取得
    - 並列データ取得・CSV読み込み
    - エラーハンドリング・resilience統合
    """

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

        # Phase H.8.3: エラー耐性管理システム統合
        self.resilience = get_resilience_manager()

        # CSV モードの場合はAPI接続をスキップ
        if csv_path:
            self.client = None
            self.exchange = None
            logger.info(f"🗂️ [RESILIENCE] CSV mode initialized: {csv_path}")
        else:
            try:
                api_key = api_key or os.getenv(f"{exchange_id.upper()}_API_KEY")
                api_secret = api_secret or os.getenv(
                    f"{exchange_id.upper()}_API_SECRET"
                )
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

                # Phase H.8.3: 初期化成功を記録
                self.resilience.record_success("market_data_fetcher")
                logger.info(
                    f"✅ [RESILIENCE] Market data fetcher initialized: {exchange_id}"
                )

            except Exception as e:
                # Phase H.8.3: 初期化失敗を記録
                self.resilience.record_error(
                    component="market_data_fetcher",
                    error_type="InitializationError",
                    error_message=f"Failed to initialize {exchange_id}: {str(e)}",
                    severity="CRITICAL",
                )
                logger.error(
                    f"❌ [RESILIENCE] Market data fetcher initialization failed: {e}"
                )
                raise

        # Phase 12.2: 部分データ保存用（タイムアウト時の救済用）
        self._last_partial_records = []

    @with_resilience("market_data_fetcher", "fetch_balance")
    def fetch_balance(self) -> dict:
        """
        残高情報を取得

        Returns:
            dict: 残高情報
        """
        if not self.client:
            raise RuntimeError("Client not initialized (CSV mode)")

        logger.info("💰 [RESILIENCE] Fetching balance with error resilience")
        return self.client.fetch_balance()

    def get_last_partial_data(self) -> Optional[pd.DataFrame]:
        """
        Phase 12.2: 最後に取得した部分データを返す（タイムアウト時の救済用）

        Returns:
            Optional[pd.DataFrame]: 部分データ、またはNone
        """
        if not self._last_partial_records:
            logger.debug("🔍 [PARTIAL-DATA] No partial data available")
            return None

        logger.info(
            f"✅ [PARTIAL-DATA] Rescued {len(self._last_partial_records)} records from partial data"
        )

        df = self._convert_to_dataframe(self._last_partial_records)
        return df

    def _convert_to_dataframe(self, data) -> pd.DataFrame:
        """
        データをDataFrameに変換

        Parameters
        ----------
        data : list or pd.DataFrame
            変換対象データ

        Returns
        -------
        pd.DataFrame
            変換済みDataFrame
        """
        if isinstance(data, pd.DataFrame):
            return data

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(
            data, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df.set_index("datetime")
        return df

    def _is_data_too_old(self, data: pd.DataFrame, max_age_hours: float = 2.0) -> bool:
        """
        データが古すぎるかどうかをチェック（新鮮さ判定）

        Parameters
        ----------
        data : pd.DataFrame
            判定対象データ
        max_age_hours : float
            最大許容時間（デフォルト2時間）

        Returns
        -------
        bool
            True: データが古すぎる, False: 許容範囲内
        """
        if data.empty:
            return True

        # 最新のタイムスタンプを取得
        latest_timestamp = data.index.max()
        current_time = pd.Timestamp.now(tz="UTC")
        age_hours = (current_time - latest_timestamp).total_seconds() / 3600

        is_too_old = age_hours > max_age_hours

        if is_too_old:
            logger.warning(
                f"⚠️ [FRESHNESS] Data is too old: {age_hours:.1f}h > {max_age_hours}h limit"
            )
            logger.warning(
                f"   Latest data: {latest_timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )
            logger.warning(
                f"   Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )

        return is_too_old

    def _select_freshest_data(
        self, data1: pd.DataFrame, data2: pd.DataFrame
    ) -> pd.DataFrame:
        """
        2つのデータセットのうち、より新しいものを選択

        Parameters
        ----------
        data1 : pd.DataFrame
            データセット1
        data2 : pd.DataFrame
            データセット2

        Returns
        -------
        pd.DataFrame
            より新しい（または有効な）データセット
        """
        # 空のデータ処理
        if data1.empty and data2.empty:
            logger.warning("⚠️ [FRESHNESS] Both datasets are empty")
            return pd.DataFrame()
        elif data1.empty:
            logger.info("📊 [FRESHNESS] Data1 is empty, selecting data2")
            return data2
        elif data2.empty:
            logger.info("📊 [FRESHNESS] Data2 is empty, selecting data1")
            return data1

        # 最新タイムスタンプで比較
        latest1 = data1.index.max()
        latest2 = data2.index.max()

        if latest1 >= latest2:
            logger.info(
                f"📊 [FRESHNESS] Selected data1: {latest1.strftime('%Y-%m-%d %H:%M:%S UTC')} >= {latest2.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )
            return data1
        else:
            logger.info(
                f"📊 [FRESHNESS] Selected data2: {latest2.strftime('%Y-%m-%d %H:%M:%S UTC')} > {latest1.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )
            return data2

    def parallel_data_fetch(
        self,
        timeframe: str = "1h",
        since: Optional[Union[int, float, str, datetime]] = None,
        limit: Optional[int] = None,
        **kwargs,
    ) -> pd.DataFrame:
        """
        並行データ取得（since指定 vs since=None）（Phase H.8.1）

        Args:
            timeframe: タイムフレーム
            since: 開始時刻
            limit: 取得件数上限
            **kwargs: get_price_dfへの追加パラメータ

        Returns:
            pd.DataFrame: より新しいデータ
        """
        logger.info("🚀 [PHASE-H8.1] Starting parallel data fetch")

        def fetch_since_data():
            try:
                logger.info("📡 [PARALLEL-SINCE] Fetching since-based data...")
                # ここでdata_processorのget_price_dfを呼び出すことになる
                # 循環importを避けるため、実際の実装では遅延importまたは依存注入を使用
                from .data_processor import DataProcessor

                processor = DataProcessor(self)
                return processor.get_price_df(
                    timeframe=timeframe, since=since, limit=limit, **kwargs
                )
            except Exception as e:
                logger.warning(f"⚠️ [PARALLEL-SINCE] Failed: {e}")
                return pd.DataFrame()

        def fetch_latest_data():
            try:
                logger.info("📡 [PARALLEL-LATEST] Fetching latest data...")
                # 最新データは高速設定で取得
                from .data_processor import DataProcessor

                processor = DataProcessor(self)
                return processor.get_price_df(
                    timeframe=timeframe,
                    since=None,
                    limit=min(limit or 50, 50),
                    paginate=False,
                    **{
                        k: v
                        for k, v in kwargs.items()
                        if k not in ["paginate", "per_page"]
                    },
                )
            except Exception as e:
                logger.warning(f"⚠️ [PARALLEL-LATEST] Failed: {e}")
                return pd.DataFrame()

        try:
            # 並行実行（最大60秒でタイムアウト）
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                future_since = executor.submit(fetch_since_data)
                future_latest = executor.submit(fetch_latest_data)

                # 結果取得（タイムアウト付き・Phase 12.2: 90秒統一）
                try:
                    data_since = future_since.result(timeout=90)
                    data_latest = future_latest.result(timeout=90)
                except concurrent.futures.TimeoutError:
                    logger.warning(
                        "⚠️ [PHASE-H8.1] Parallel fetch timeout, canceling futures"
                    )
                    future_since.cancel()
                    future_latest.cancel()
                    # タイムアウト時は通常の取得にフォールバック
                    from .data_processor import DataProcessor

                    processor = DataProcessor(self)
                    return processor.get_price_df(
                        timeframe=timeframe, since=since, limit=limit, **kwargs
                    )

            # より新しいデータを選択
            best_data = self._select_freshest_data(data_since, data_latest)

            if not best_data.empty:
                logger.info(
                    f"✅ [PHASE-H8.1] Parallel fetch successful: {len(best_data)} records"
                )
            else:
                logger.warning(
                    "⚠️ [PHASE-H8.1] Both parallel fetches returned empty data"
                )

            return best_data

        except Exception as e:
            logger.error(f"❌ [PHASE-H8.1] Parallel fetch failed: {e}")
            # エラー時は通常の取得にフォールバック
            from .data_processor import DataProcessor

            processor = DataProcessor(self)
            return processor.get_price_df(
                timeframe=timeframe, since=since, limit=limit, **kwargs
            )

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

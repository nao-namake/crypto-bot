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
from crypto_bot.utils.error_resilience import get_resilience_manager, with_resilience

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

    @with_resilience("market_data_fetcher", "get_price_df")
    def get_price_df(
        self,
        timeframe: str = "1m",
        since: Optional[Union[int, float, str, datetime]] = None,
        limit: Optional[int] = None,
        paginate: bool = False,
        sleep: bool = True,
        per_page: int = 500,
        max_consecutive_empty: Optional[int] = None,
        max_consecutive_no_new: Optional[int] = None,
        max_attempts: Optional[int] = None,
    ) -> pd.DataFrame:
        # CSV モードの場合は CSV から読み込み
        if self.csv_path:
            return self._get_price_from_csv(since, limit)

        import time

        since_ms: Optional[int] = None
        if since is not None:
            # Phase H.22 fix: pd.Timestamp型の処理を追加
            if hasattr(since, "value"):  # pd.Timestampかどうかチェック
                # pd.Timestamp.valueはナノ秒なので、ミリ秒に変換
                since_ms = int(since.value // 1_000_000)
            elif isinstance(since, str):
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
            # Phase H.23.6: データ取得アルゴリズム最適化（400レコード確実達成）
            MAX_ATTEMPTS = (
                max_attempts if max_attempts is not None else 25
            )  # 20→25に増加（per_page=200対応）
            MAX_CONSECUTIVE_EMPTY = (
                max_consecutive_empty
                if max_consecutive_empty is not None
                else 8  # 5→8に増加（安定取得強化）
            )
            MAX_CONSECUTIVE_NO_NEW = (
                max_consecutive_no_new
                if max_consecutive_no_new is not None
                else 15  # 8→15に増加（per_page大幅増加対応）
            )
            logger.info(f"🔄 Paginated fetch: limit={limit}, per_page={per_page}")
            logger.info(
                f"🔧 [PHASE-H4] Pagination config: MAX_ATTEMPTS={MAX_ATTEMPTS}, MAX_CONSECUTIVE_EMPTY={MAX_CONSECUTIVE_EMPTY}, MAX_CONSECUTIVE_NO_NEW={MAX_CONSECUTIVE_NO_NEW}"
            )
            records: List = []
            seen_ts = set()
            last_since = since_ms
            attempt = 0
            consecutive_empty = 0
            consecutive_no_new = 0

            while len(records) < max_records and attempt < MAX_ATTEMPTS:
                logger.info(
                    f"🔄 Attempt {attempt + 1}/{MAX_ATTEMPTS}: fetching from {last_since}, "
                    f"current={len(records)}/{max_records}"
                )

                try:
                    # Phase H.6.3: APIレスポンスの詳細ログ
                    logger.info(
                        f"🔍 [PHASE-H6] Calling API: symbol={self.symbol}, timeframe={timeframe}, "
                        f"since={last_since}, limit={per_page}"
                    )

                    batch = self.client.fetch_ohlcv(
                        self.symbol, timeframe, last_since, per_page
                    )

                    # Phase H.6.3: レスポンスタイプと内容の詳細ログ
                    logger.info(
                        f"🔍 [PHASE-H6] API response type: {type(batch).__name__}"
                    )

                    if batch and isinstance(batch, list) and len(batch) > 0:
                        logger.info(f"🔍 [PHASE-H6] First record sample: {batch[0]}")

                    if isinstance(batch, pd.DataFrame):
                        logger.info(
                            f"✅ Received DataFrame directly: {len(batch)} records"
                        )
                        return batch

                    if not batch:
                        consecutive_empty += 1
                        logger.warning(
                            f"⚠️ Empty batch {consecutive_empty}/{MAX_CONSECUTIVE_EMPTY}"
                        )

                        # Phase H.4: 空バッチの詳細情報
                        logger.warning(
                            f"🔍 [PHASE-H4] Empty batch at timestamp: {last_since}, attempt {attempt + 1}"
                        )

                        if consecutive_empty >= MAX_CONSECUTIVE_EMPTY:
                            logger.warning(
                                f"❌ [PHASE-H4] EARLY TERMINATION: Too many consecutive empty batches ({consecutive_empty}/{MAX_CONSECUTIVE_EMPTY}), stopping pagination"
                            )
                            logger.warning(
                                f"📊 [PHASE-H4] Final stats: {len(records)} records collected in {attempt + 1} attempts"
                            )
                            break

                        # Phase H.20.1.3: 最適化されたバックオフ戦略
                        # より効率的な取得のため待機時間短縮（10秒→6秒上限）
                        backoff_delay = min(
                            consecutive_empty * 1.5, 6
                        )  # 2→1.5, 10→6に短縮
                        logger.debug(
                            f"🔄 [PHASE-H20.1.3] Backoff delay: {backoff_delay}秒"
                        )
                        time.sleep(backoff_delay)
                        attempt += 1
                        continue

                    # 空バッチカウンタリセット
                    consecutive_empty = 0

                    logger.info(f"📊 Batch received: {len(batch)} records")

                    # Phase H.4: バッチ内容の詳細分析ログ
                    if batch:
                        first_ts = batch[0][0]
                        last_ts = batch[-1][0]
                        first_time = pd.Timestamp(first_ts, unit="ms")
                        last_time = pd.Timestamp(last_ts, unit="ms")
                        logger.info(
                            f"🔍 [PHASE-H4] Batch time range: {first_time} to {last_time}"
                        )
                        logger.info(
                            f"🔍 [PHASE-H4] Batch time span: {(last_ts - first_ts) / (1000 * 3600):.2f} hours"
                        )

                    added = False
                    new_records_count = 0
                    duplicate_count = 0
                    for row in batch:
                        ts = row[0]
                        if ts not in seen_ts:
                            seen_ts.add(ts)
                            records.append(row)
                            new_records_count += 1
                            # タイムフレームに応じた適切な時刻進行
                            # 1h = 3600秒, 4h = 14400秒, 15m = 900秒
                            timeframe_ms = {
                                "1m": 60 * 1000,
                                "5m": 5 * 60 * 1000,
                                "15m": 15 * 60 * 1000,
                                "1h": 60 * 60 * 1000,
                                "4h": 4 * 60 * 60 * 1000,
                                "1d": 24 * 60 * 60 * 1000,
                            }.get(
                                timeframe, 60 * 60 * 1000
                            )  # デフォルト1時間
                            last_since = ts + timeframe_ms
                            added = True
                        else:
                            duplicate_count += 1

                    logger.info(
                        f"✅ [PHASE-H4] Added {new_records_count} new records, {duplicate_count} duplicates, total={len(records)}"
                    )
                    logger.info(
                        f"📈 [PHASE-H4] Progress: {len(records)}/{max_records} ({len(records)/max_records*100:.1f}%)"
                    )

                    if not added:
                        consecutive_no_new += 1
                        logger.warning(
                            f"⚠️ No new records {consecutive_no_new}/{MAX_CONSECUTIVE_NO_NEW}"
                        )

                        # Phase H.4: 早期終了の詳細理由ログ
                        logger.warning(
                            f"🔍 [PHASE-H4] No new records reason: {len(batch)} total received, {duplicate_count} were duplicates"
                        )

                        if consecutive_no_new >= MAX_CONSECUTIVE_NO_NEW:
                            logger.warning(
                                f"❌ [PHASE-H4] EARLY TERMINATION: Too many attempts with no new records ({consecutive_no_new}/{MAX_CONSECUTIVE_NO_NEW}), stopping pagination"
                            )
                            logger.warning(
                                f"📊 [PHASE-H4] Final stats: {len(records)} records collected in {attempt + 1} attempts"
                            )
                            break

                        # Phase H.20.1.3: 改善されたタイムスタンプ進行戦略
                        if batch:
                            # より小さな単位でタイムスタンプを進めて見逃しを減少
                            timeframe_ms = {
                                "1m": 60 * 1000,
                                "5m": 5 * 60 * 1000,
                                "15m": 15 * 60 * 1000,
                                "1h": 60 * 60 * 1000,
                                "4h": 4 * 60 * 60 * 1000,
                                "1d": 24 * 60 * 60 * 1000,
                            }.get(timeframe, 60 * 60 * 1000)

                            # 小刻みに進行（従来の半分の幅で進む）
                            step_ms = timeframe_ms // 2  # 半分の時間間隔で進行
                            last_since = batch[-1][0] + step_ms

                            logger.debug(
                                f"🔄 [PHASE-H20.1.3] Timestamp advance: +{step_ms}ms "
                                f"(half of {timeframe} interval)"
                            )
                    else:
                        # 新レコードがあった場合はカウンタリセット
                        consecutive_no_new = 0
                        logger.info(
                            f"✅ Added {sum(1 for row in batch if row[0] in seen_ts and row[0] >= last_since - len(batch))} records, total={len(records)}"
                        )

                    # Phase H.20.1.3: 最適化されたレート制限
                    if (
                        sleep
                        and hasattr(self.exchange, "rateLimit")
                        and self.exchange.rateLimit
                    ):
                        base_delay = self.exchange.rateLimit / 1000.0

                        # より効率的な取得のため基本待機時間を短縮
                        base_delay *= 0.8  # 20%短縮でより積極的取得

                        # 連続問題発生時の延長も抑制（1.5→1.3）
                        if consecutive_empty > 0 or consecutive_no_new > 0:
                            base_delay *= 1.3

                        logger.debug(
                            f"🔄 [PHASE-H20.1.3] Rate limit delay: {base_delay:.3f}秒"
                        )
                        time.sleep(base_delay)

                except Exception as e:
                    logger.error(f"❌ Batch fetch error on attempt {attempt + 1}: {e}")
                    # エラー時は少し待機してリトライ
                    error_delay = min((attempt + 1) * 1.5, 8)
                    time.sleep(error_delay)

                attempt += 1

            # Phase H.4: ページネーション完了の詳細サマリー
            logger.info(
                f"✅ [PHASE-H4] Pagination complete: {len(records)} total records collected in {attempt} attempts"
            )
            if records:
                first_record_time = pd.Timestamp(records[0][0], unit="ms")
                last_record_time = pd.Timestamp(records[-1][0], unit="ms")
                time_span = (records[-1][0] - records[0][0]) / (1000 * 3600)  # hours
                logger.info(
                    f"📊 [PHASE-H4] Data time range: {first_record_time} to {last_record_time} ({time_span:.2f} hours)"
                )
            logger.info(
                f"🔧 [PHASE-H4] Termination reason: MAX_RECORDS_REACHED={len(records) >= max_records}, MAX_ATTEMPTS_REACHED={attempt >= MAX_ATTEMPTS}"
            )
            data = records if limit is None else records[:limit]

        else:
            # Phase H.6.3: 非ページネーションモードでもデバッグログ追加
            logger.info(
                f"🔍 [PHASE-H6] Non-paginated fetch: timeframe={timeframe}, "
                f"since_ms={since_ms}, limit={limit}"
            )

            raw = self.client.fetch_ohlcv(self.symbol, timeframe, since_ms, limit)

            # Phase H.6.3: レスポンス詳細ログ
            logger.info(
                f"🔍 [PHASE-H6] Response type: {type(raw).__name__}, "
                f"content: {len(raw) if raw else 0} records"
            )
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
                logger.warning(
                    f"⚠️ [PHASE-H6] Bitbank returned no data for since_ms={since_ms}"
                )
                # Phase H.6.3: 最新データ取得を試みる
                logger.info(
                    "🔄 [PHASE-H6] Trying to fetch latest data without since parameter"
                )
                raw_latest = self.client.fetch_ohlcv(self.symbol, timeframe, None, 10)
                if raw_latest:
                    logger.info(f"✅ [PHASE-H6] Got {len(raw_latest)} latest records")
                    data = raw_latest

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

    def _is_data_too_old(self, data: pd.DataFrame, max_age_hours: float = 2.0) -> bool:
        """
        データが古すぎるかどうかをチェック

        Args:
            data: チェック対象のDataFrame
            max_age_hours: 許容される最大時間（時間）

        Returns:
            bool: データが古すぎる場合True
        """
        if data is None or data.empty:
            return True

        # 最新データのタイムスタンプを取得
        latest_timestamp = data.index.max()
        current_time = pd.Timestamp.now(tz="UTC")

        # タイムゾーン情報を統一
        if latest_timestamp.tz is None:
            latest_timestamp = latest_timestamp.tz_localize("UTC")

        # データの年齢を計算
        data_age = current_time - latest_timestamp
        data_age_hours = data_age.total_seconds() / 3600

        logger.info(
            f"🔍 [DATA-FRESHNESS] Latest data: {latest_timestamp}, Age: {data_age_hours:.1f}h"
        )

        if data_age_hours > max_age_hours:
            logger.warning(
                f"⚠️ [DATA-FRESHNESS] Data too old: {data_age_hours:.1f}h > {max_age_hours}h"
            )
            return True

        logger.info(
            f"✅ [DATA-FRESHNESS] Data is fresh: {data_age_hours:.1f}h <= {max_age_hours}h"
        )
        return False

    def _select_freshest_data(
        self, data1: pd.DataFrame, data2: pd.DataFrame
    ) -> pd.DataFrame:
        """
        2つのDataFrameから新しいデータを選択

        Args:
            data1: 比較対象データ1
            data2: 比較対象データ2

        Returns:
            pd.DataFrame: より新しいデータ
        """
        if data1 is None or data1.empty:
            return data2 if data2 is not None else pd.DataFrame()

        if data2 is None or data2.empty:
            return data1

        # 最新タイムスタンプを比較
        latest1 = data1.index.max()
        latest2 = data2.index.max()

        if latest1.tz is None:
            latest1 = latest1.tz_localize("UTC")
        if latest2.tz is None:
            latest2 = latest2.tz_localize("UTC")

        if latest2 > latest1:
            logger.info(
                f"✅ [DATA-SELECT] Selected data2 (newer): {latest2} vs {latest1}"
            )
            return data2
        else:
            logger.info(
                f"✅ [DATA-SELECT] Selected data1 (newer/equal): {latest1} vs {latest2}"
            )
            return data1

    def fetch_with_freshness_fallback(
        self,
        timeframe: str = "1h",
        since: Optional[Union[int, float, str, datetime]] = None,
        limit: Optional[int] = None,
        max_age_hours: float = 2.0,
        **kwargs,
    ) -> pd.DataFrame:
        """
        データ新鮮度チェック付きデータ取得（Phase H.8.1 + H.9.4土日対応強化）

        Args:
            timeframe: タイムフレーム
            since: 開始時刻
            limit: 取得件数上限
            max_age_hours: 許容される最大データ年齢（時間）
            **kwargs: get_price_dfへの追加パラメータ

        Returns:
            pd.DataFrame: 新鮮なデータ
        """
        logger.info(
            "🚀 [PHASE-H9.4] Starting enhanced freshness data fetch with fallback optimization"
        )

        # Phase H.9.4: since計算問題解決・強制最新データ取得戦略
        current_time = pd.Timestamp.now(tz="UTC")

        # since が古すぎる場合の自動調整（Phase H.9.4根本解決）
        if since is not None:
            if isinstance(since, str):
                since_dt = pd.to_datetime(since, utc=True)
            elif isinstance(since, datetime):
                since_dt = (
                    since
                    if since.tzinfo
                    else since.replace(tzinfo=pd.Timestamp.now().tz)
                )
            else:
                since_dt = pd.to_datetime(
                    since, unit="ms" if since > 1e12 else "s", utc=True
                )

            age_hours = (current_time - since_dt).total_seconds() / 3600
            if age_hours > 24:  # 24時間以上古い場合は強制調整
                new_since = current_time - pd.Timedelta(hours=6)  # 6時間前に調整
                logger.warning(
                    f"🔧 [PHASE-H9.4] since too old ({age_hours:.1f}h), adjusting: {since_dt} → {new_since}"
                )
                since = new_since

        logger.info(
            f"🔧 [PHASE-H9.4] Config: timeframe={timeframe}, since={since}, limit={limit}, max_age_hours={max_age_hours}"
        )

        try:
            # 通常のsince指定取得
            logger.info("📡 [PHASE-H8.1] Attempting since-based fetch...")
            data = self.get_price_df(
                timeframe=timeframe, since=since, limit=limit, **kwargs
            )

            # データ新鮮度チェック（Phase H.9.4: 調整されたmax_age_hours使用）
            if not self._is_data_too_old(data, max_age_hours):
                logger.info("✅ [PHASE-H9.4] Since-based data is fresh, using it")
                return data

            # データが古い場合：since=Noneで最新データ取得
            logger.warning(
                "🔄 [PHASE-H8.1] Data too old, falling back to latest data fetch"
            )
            latest_data = self.get_price_df(
                timeframe=timeframe,
                since=None,
                limit=min(limit or 100, 100),  # 最新データは100件以下に制限
                paginate=False,  # 最新データは高速取得
                **{k: v for k, v in kwargs.items() if k != "paginate"},
            )

            if not latest_data.empty:
                logger.info(
                    f"✅ [PHASE-H8.1] Latest data fallback successful: {len(latest_data)} records"
                )
                return latest_data
            else:
                logger.warning(
                    "⚠️ [PHASE-H8.1] Latest data fallback also empty, returning original"
                )
                return data

        except Exception as e:
            logger.error(f"❌ [PHASE-H8.1] Freshness fallback failed: {e}")
            # エラー時は通常の取得を試行
            try:
                return self.get_price_df(
                    timeframe=timeframe, since=since, limit=limit, **kwargs
                )
            except Exception as e2:
                logger.error(
                    f"❌ [PHASE-H8.1] Fallback to normal fetch also failed: {e2}"
                )
                return pd.DataFrame()

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

        import concurrent.futures

        def fetch_since_data():
            try:
                logger.info("📡 [PARALLEL-SINCE] Fetching since-based data...")
                return self.get_price_df(
                    timeframe=timeframe, since=since, limit=limit, **kwargs
                )
            except Exception as e:
                logger.warning(f"⚠️ [PARALLEL-SINCE] Failed: {e}")
                return pd.DataFrame()

        def fetch_latest_data():
            try:
                logger.info("📡 [PARALLEL-LATEST] Fetching latest data...")
                # 最新データは高速設定で取得
                return self.get_price_df(
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

                # 結果取得（タイムアウト付き）
                try:
                    data_since = future_since.result(timeout=60)
                    data_latest = future_latest.result(timeout=60)
                except concurrent.futures.TimeoutError:
                    logger.warning(
                        "⚠️ [PHASE-H8.1] Parallel fetch timeout, canceling futures"
                    )
                    future_since.cancel()
                    future_latest.cancel()
                    # タイムアウト時は通常の取得にフォールバック
                    return self.get_price_df(
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
            return self.get_price_df(
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

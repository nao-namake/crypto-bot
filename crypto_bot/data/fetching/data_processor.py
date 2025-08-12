"""
Data Processor - Phase 16.3-C Split

統合前: crypto_bot/data/fetcher.py（1,456行）
分割後: crypto_bot/data/fetching/data_processor.py

機能:
- 複雑なget_price_df核心処理（ページネーション・リトライ・検証）
- タイムスタンプ検証・データ品質保証システム
- DataPreprocessor統合（重複除去・欠損補完・外れ値除去）
- フォールバック処理・エラーハンドリング最適化
- 性能最適化によるデータ取得効率向上

Phase 16.3-C実装日: 2025年8月8日
"""

import logging
import numbers
import time
from datetime import datetime
from typing import List, Optional, Union

import numpy as np
import pandas as pd
from pandas.tseries.frequencies import to_offset

logger = logging.getLogger(__name__)


class DataProcessor:
    """
    データ処理・品質保証統合クラス

    - 複雑なデータ取得処理（get_price_df）
    - タイムスタンプ検証・データ品質保証
    - フォールバック処理・エラーハンドリング
    - データ前処理統合（DataPreprocessor機能統合）
    """

    def __init__(self, market_client):
        """
        データプロセッサ初期化

        Parameters
        ----------
        market_client : MarketDataFetcher
            市場データクライアント
        """
        self.client_obj = market_client
        self.client = market_client.client
        self.exchange = market_client.exchange
        self.symbol = market_client.symbol
        self.exchange_id = market_client.exchange_id
        self.csv_path = market_client.csv_path
        self.resilience = market_client.resilience

    def _validate_timestamp_h28(
        self, timestamp: Optional[int], context: str = "unknown"
    ) -> Optional[int]:
        """
        Phase H.28.1: タイムスタンプ堅牢性システム - 5段階検証

        Args:
            timestamp: 検証対象のタイムスタンプ（ミリ秒）
            context: 呼び出し元の文脈情報

        Returns:
            Optional[int]: 検証済み・修正済みタイムスタンプ、または None（異常値の場合）
        """
        if timestamp is None:
            return None

        try:
            # H.28.1-Stage1: 型安全性保証
            if (
                not isinstance(timestamp, (int, float))
                or np.isnan(timestamp)
                or np.isinf(timestamp)
            ):
                logger.error(
                    f"🚨 [H.28.1-Stage1] Invalid timestamp type/value: {timestamp} (context: {context})"
                )
                return None

            ts = int(timestamp)

            # H.28.1-Stage2: ミリ秒桁数検証（10桁=秒、13桁=ミリ秒）
            if ts < 1e12:  # 10桁以下（秒単位の可能性）
                ts = ts * 1000  # ミリ秒に変換
                logger.info(
                    f"🔄 [H.28.1-Stage2] Converted seconds to milliseconds: {timestamp} -> {ts}"
                )

            # H.28.1-Stage3: 現実的な時間範囲検証
            current_time_ms = int(time.time() * 1000)
            # 2020年1月1日から未来100年までを有効範囲とする
            min_timestamp = int(datetime(2020, 1, 1).timestamp() * 1000)
            max_timestamp = current_time_ms + (
                100 * 365 * 24 * 60 * 60 * 1000
            )  # 100年後

            if ts < min_timestamp or ts > max_timestamp:
                logger.error(
                    f"🚨 [H.28.1-Stage3] Timestamp out of realistic range: {ts} (context: {context})"
                )
                logger.error(f"   Valid range: {min_timestamp} - {max_timestamp}")
                return None

            # H.28.1-Stage4: 取引所API制限考慮（Bitbank: 168時間制限）
            if self.exchange_id == "bitbank":
                max_lookback_ms = 168 * 60 * 60 * 1000  # 168時間（1週間）
                oldest_allowed = current_time_ms - max_lookback_ms

                if ts < oldest_allowed:
                    logger.warning(
                        f"⚠️ [H.28.1-Stage4] Timestamp beyond Bitbank limit, adjusting: {ts} -> {oldest_allowed}"
                    )
                    ts = oldest_allowed

            # H.28.1-Stage5: 未来データ検証（24時間の余裕を持たせる）
            future_threshold = current_time_ms + (24 * 60 * 60 * 1000)
            if ts > future_threshold:
                logger.warning(
                    f"⚠️ [H.28.1-Stage5] Future timestamp detected, adjusting: {ts} -> {current_time_ms}"
                )
                ts = current_time_ms

            # 最終検証: 正常範囲内であることを確認
            if oldest_allowed <= ts <= future_threshold:
                logger.debug(f"✅ [H.28.1] Timestamp validated successfully: {ts}")
                return ts
            else:
                logger.error(
                    f"🚨 [H.28.1] Final validation failed: {ts} (context: {context})"
                )
                return None

        except Exception as e:
            logger.error(
                f"❌ [H.28.1] Timestamp validation error: {e} (context: {context})"
            )
            return None

    def _calculate_safe_since_h28(self, base_timestamp: int, timeframe: str) -> int:
        """
        Phase H.28.1: 安全なsince値計算（取引所制限・データ要求最適化）

        Args:
            base_timestamp: 基準タイムスタンプ（ミリ秒）
            timeframe: 時間枠（"1m", "1h"等）

        Returns:
            int: 最適化されたsince値（ミリ秒）
        """
        current_time_ms = int(time.time() * 1000)

        # Phase 16.1-C: Bitbank 168時間制限への対応
        if self.exchange_id == "bitbank":
            # 167時間前を上限とする（1時間の安全マージン）
            max_lookback_hours = 167
            max_lookback_ms = max_lookback_hours * 60 * 60 * 1000
            earliest_allowed = current_time_ms - max_lookback_ms

            if base_timestamp < earliest_allowed:
                logger.info(
                    f"🔧 [Phase 16.1-C] Adjusting since for Bitbank 168h limit: "
                    f"{base_timestamp} -> {earliest_allowed} ({max_lookback_hours}h ago)"
                )
                return earliest_allowed

        # 時間枠に応じた最小必要期間を確保
        timeframe_multipliers = {
            "1m": 1,
            "5m": 5,
            "15m": 15,
            "1h": 60,
            "4h": 240,
            "1d": 1440,
        }
        multiplier = timeframe_multipliers.get(timeframe, 60)

        # 最低限必要なデータ期間（400バー × timeframe）を確保
        required_bars = 400
        required_duration_ms = required_bars * multiplier * 60 * 1000

        # 必要期間を確保できる範囲で最適なsince値を計算
        optimal_since = max(base_timestamp, current_time_ms - required_duration_ms)

        logger.debug(
            f"🔧 [H.28.1] Calculated safe since: {optimal_since} "
            f"(timeframe: {timeframe}, required_bars: {required_bars})"
        )

        return optimal_since

    def _should_abort_retry_h28(
        self, error_context: dict, current_attempt: int, max_attempts: int
    ) -> tuple[bool, str]:
        """
        Phase H.28.2: インテリジェント停止判定システム

        Args:
            error_context: エラー文脈情報
            current_attempt: 現在の試行回数
            max_attempts: 最大試行回数

        Returns:
            tuple[bool, str]: (停止すべきか, 停止理由)
        """
        # 最大試行回数に達した場合
        if current_attempt >= max_attempts:
            return True, f"Max attempts reached ({max_attempts})"

        # 連続して長時間空データが続く場合
        consecutive_empty = error_context.get("consecutive_empty", 0)
        if consecutive_empty >= 15:  # 15回連続空データ
            return True, f"Too many consecutive empty responses ({consecutive_empty})"

        # タイムスタンプに明らかな異常がある場合
        if error_context.get("timestamp_anomaly", False):
            return True, "Timestamp anomaly detected"

        # 要求期間が現実的でない場合（30日以上）
        time_span_hours = error_context.get("time_span_hours", 0)
        if time_span_hours > 30 * 24:  # 30日以上
            return True, f"Time span too large ({time_span_hours:.1f}h > 720h limit)"

        return False, ""

    def _calculate_smart_backoff_h28(
        self, attempt_num: int, consecutive_failures: int, error_type: str
    ) -> float:
        """
        Phase H.28.2: スマートバックオフ戦略

        Args:
            attempt_num: 試行回数
            consecutive_failures: 連続失敗回数
            error_type: エラータイプ

        Returns:
            float: バックオフ遅延時間（秒）
        """
        base_delay = 1.0  # 基本遅延1秒

        # エラータイプ別調整
        error_multipliers = {
            "empty_response": 2.0,  # 空レスポンス
            "rate_limit": 5.0,  # レート制限
            "timeout": 3.0,  # タイムアウト
            "api_error": 2.5,  # API エラー
        }

        multiplier = error_multipliers.get(error_type, 2.0)

        # 指数バックオフ（上限10秒）
        exponential_delay = min(base_delay * (2 ** (attempt_num - 1)), 10.0)

        # 連続失敗による追加遅延
        failure_penalty = consecutive_failures * 0.5

        total_delay = (exponential_delay * multiplier) + failure_penalty

        # 最小0.5秒、最大15秒に制限
        final_delay = max(0.5, min(total_delay, 15.0))

        logger.debug(
            f"🔧 [H.28.2] Smart backoff: attempt={attempt_num}, "
            f"consecutive_failures={consecutive_failures}, type={error_type}, "
            f"delay={final_delay:.2f}s"
        )

        return final_delay

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
        """
        価格データ取得（最適化版・Phase 16.3-C性能向上）

        Parameters
        ----------
        timeframe : str
            時間枠（"1m", "1h"等）
        since : Optional[Union[int, float, str, datetime]]
            開始時刻
        limit : Optional[int]
            取得件数制限
        paginate : bool
            ページネーション使用
        sleep : bool
            レート制限待機
        per_page : int
            1ページあたりの取得件数
        max_consecutive_empty : Optional[int]
            最大連続空レスポンス回数
        max_consecutive_no_new : Optional[int]
            最大連続新規データなし回数
        max_attempts : Optional[int]
            最大試行回数

        Returns
        -------
        pd.DataFrame
            価格データ
        """
        # CSV モードの場合は CSV から読み込み
        if self.csv_path:
            return self.client_obj._get_price_from_csv(since, limit)

        since_ms: Optional[int] = None
        if since is not None:
            # Phase H.28.1: タイムスタンプ堅牢性システム統合
            raw_since_ms: Optional[int] = None

            try:
                if hasattr(since, "value"):  # pd.Timestampかどうかチェック
                    # pd.Timestamp.valueはナノ秒なので、ミリ秒に変換
                    raw_since_ms = int(since.value // 1_000_000)
                elif isinstance(since, str):
                    dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
                    raw_since_ms = int(dt.timestamp() * 1000)
                elif isinstance(since, datetime):
                    raw_since_ms = int(since.timestamp() * 1000)
                elif isinstance(since, numbers.Real):
                    ts = int(since)
                    raw_since_ms = ts if ts > 1e12 else int(ts * 1000)
                else:
                    raise TypeError(f"Unsupported type for since: {type(since)}")

                # H.28.1: 5段階検証システムで検証
                since_ms = self._validate_timestamp_h28(
                    raw_since_ms, f"since_calculation_{type(since).__name__}"
                )

                if since_ms is None:
                    # 検証失敗時は安全な開始点を使用
                    since_ms = self._calculate_safe_since_h28(
                        raw_since_ms or (int(time.time() * 1000) - 167 * 60 * 60 * 1000),
                        timeframe,
                    )
                    logger.warning(
                        f"🔧 [Phase 16.1-C] Invalid since value, using safe fallback: {since_ms}"
                    )

            except Exception as e:
                logger.error(f"🚨 [H.28.1] Since calculation error: {e}")
                # エラー時は安全な開始点を使用
                since_ms = self._calculate_safe_since_h28(
                    int(time.time() * 1000) - 167 * 60 * 60 * 1000, timeframe
                )
                logger.warning(
                    f"🔧 [H.28.1] Error fallback, using safe since: {since_ms}"
                )
        if paginate and limit:
            return self._paginated_fetch(
                timeframe,
                since_ms,
                limit,
                per_page,
                sleep,
                max_consecutive_empty,
                max_consecutive_no_new,
                max_attempts,
            )
        else:
            return self._simple_fetch(timeframe, since_ms, limit, sleep)

    def _paginated_fetch(
        self,
        timeframe: str,
        since_ms: Optional[int],
        limit: int,
        per_page: int,
        sleep: bool,
        max_consecutive_empty: Optional[int],
        max_consecutive_no_new: Optional[int],
        max_attempts: Optional[int],
    ) -> pd.DataFrame:
        """
        ページネーション取得（最適化版）
        """
        # Phase H.23.6: データ取得アルゴリズム最適化（400レコード確実達成）
        MAX_ATTEMPTS = max_attempts if max_attempts is not None else 25
        MAX_CONSECUTIVE_EMPTY = (
            max_consecutive_empty if max_consecutive_empty is not None else 12
        )
        MAX_CONSECUTIVE_NO_NEW = (
            max_consecutive_no_new if max_consecutive_no_new is not None else 20
        )

        logger.info(f"🔄 Paginated fetch: limit={limit}, per_page={per_page}")
        logger.info(
            f"🔧 [PHASE-H4] Pagination config: MAX_ATTEMPTS={MAX_ATTEMPTS}, "
            f"MAX_CONSECUTIVE_EMPTY={MAX_CONSECUTIVE_EMPTY}, MAX_CONSECUTIVE_NO_NEW={MAX_CONSECUTIVE_NO_NEW}"
        )

        records: List = []
        seen_ts = set()
        last_since = since_ms
        attempt = 0
        consecutive_empty = 0
        consecutive_no_new = 0

        while len(records) < limit and attempt < MAX_ATTEMPTS:
            logger.info(
                f"🔄 Attempt {attempt + 1}/{MAX_ATTEMPTS}: fetching from {last_since}, "
                f"current={len(records)}/{limit}"
            )

            try:
                # タイムスタンプ検証と調整（修正版）
                current_ms = int(time.time() * 1000)

                # 初回の場合、安全なデフォルト値を設定
                if last_since is None:
                    # 24時間前から開始（安全な範囲）
                    last_since = current_ms - (24 * 60 * 60 * 1000)
                    logger.info(
                        f"🔧 [TIMESTAMP] Initial timestamp set to 24h ago: {last_since}"
                    )

                # 未来のタイムスタンプチェック
                elif last_since > current_ms:
                    logger.warning(
                        f"⚠️ [TIMESTAMP] Future timestamp detected: {last_since} > {current_ms}"
                    )
                    # 24時間前に安全にリセット
                    last_since = current_ms - (24 * 60 * 60 * 1000)
                    logger.info(f"🔧 [TIMESTAMP] Reset to 24h ago: {last_since}")

                # Bitbank API制限チェック（168時間以内に短縮）
                else:
                    max_age_ms = 168 * 60 * 60 * 1000  # 168時間（1週間、設定値と一致）
                    min_since = current_ms - max_age_ms
                    if last_since < min_since:
                        logger.warning(
                            f"⚠️ [TIMESTAMP] Too old timestamp: {last_since} < {min_since}"
                        )
                        last_since = min_since
                        logger.info(f"🔧 [TIMESTAMP] Adjusted to 168h ago: {last_since}")

                batch = self.client.fetch_ohlcv(
                    self.symbol, timeframe, last_since, per_page
                )

                if isinstance(batch, pd.DataFrame):
                    logger.info(f"✅ Received DataFrame directly: {len(batch)} records")
                    return batch

                if not batch:
                    consecutive_empty += 1
                    logger.warning(
                        f"⚠️ Empty batch {consecutive_empty}/{MAX_CONSECUTIVE_EMPTY}"
                    )

                    # Phase H.28.2: インテリジェントリトライシステム適用
                    error_context = {
                        "consecutive_empty": consecutive_empty,
                        "timestamp_anomaly": (
                            last_since
                            and last_since
                            > int(time.time() * 1000) + 24 * 60 * 60 * 1000
                        ),
                        "error_message": "Empty batch response",
                        "time_span_hours": (
                            (int(time.time() * 1000) - (since_ms or 0)) / (1000 * 3600)
                            if since_ms
                            else 0
                        ),
                    }

                    should_abort, abort_reason = self._should_abort_retry_h28(
                        error_context, attempt + 1, MAX_ATTEMPTS
                    )

                    if should_abort:
                        logger.warning(
                            f"🚨 [H.28.2] INTELLIGENT TERMINATION: {abort_reason}"
                        )
                        logger.warning(
                            f"📊 [H.28.2] Final stats: {len(records)} records collected in {attempt + 1} attempts"
                        )
                        break

                    backoff_delay = self._calculate_smart_backoff_h28(
                        attempt + 1, consecutive_empty, "empty_response"
                    )
                    logger.info(f"⏳ [H.28.2] Smart backoff: {backoff_delay:.2f}s")
                    time.sleep(backoff_delay)

                    attempt += 1
                    continue

                # データ処理・フィルタリング・品質検証
                batch = self._process_batch_data(batch, seen_ts, timeframe)

                if not batch:
                    consecutive_no_new += 1
                    if consecutive_no_new >= MAX_CONSECUTIVE_NO_NEW:
                        logger.info(
                            f"🔚 [PAGINATION] No new data for {consecutive_no_new} attempts, stopping"
                        )
                        break
                else:
                    consecutive_empty = 0
                    consecutive_no_new = 0
                    records.extend(batch)

                    # 次の取得開始点を更新（timeframeに応じて調整）
                    if batch:
                        # timeframeに応じた間隔を設定
                        if timeframe == "15m":
                            interval_ms = 15 * 60 * 1000  # 15分
                        elif timeframe == "1h":
                            interval_ms = 60 * 60 * 1000  # 1時間
                        elif timeframe == "4h":
                            interval_ms = 4 * 60 * 60 * 1000  # 4時間
                        else:
                            interval_ms = 60 * 60 * 1000  # デフォルト1時間

                        # 次のタイムスタンプを計算（安全性チェック付き）
                        next_ts = int(batch[-1][0] + interval_ms)

                        # 未来のタイムスタンプを防ぐ
                        current_ms = int(time.time() * 1000)
                        if next_ts > current_ms:
                            logger.warning(
                                "⚠️ [TIMESTAMP] Next timestamp would be in future, using current time"
                            )
                            last_since = current_ms
                        else:
                            last_since = next_ts

                # Phase 12.2: 部分データ保存（タイムアウト時の救済用）
                self.client_obj._last_partial_records = records.copy()

                # レート制限対応
                if (
                    sleep
                    and hasattr(self.exchange, "rateLimit")
                    and self.exchange.rateLimit
                ):
                    time.sleep(self.exchange.rateLimit / 1000.0)

            except Exception as e:
                logger.error(f"❌ [PAGINATION] API call failed: {e}")
                backoff_delay = self._calculate_smart_backoff_h28(
                    attempt + 1, consecutive_empty, "api_error"
                )
                time.sleep(backoff_delay)

            attempt += 1

        # 結果をDataFrameに変換
        if records:
            df = self._convert_records_to_dataframe(records)
            logger.info(f"✅ [PAGINATION] Completed: {len(df)} records collected")
            return df
        else:
            logger.warning("⚠️ [PAGINATION] No data collected")
            return pd.DataFrame()

    def _simple_fetch(
        self, timeframe: str, since_ms: Optional[int], limit: Optional[int], sleep: bool
    ) -> pd.DataFrame:
        """
        シンプルな一括取得
        """
        try:
            raw = self.client.fetch_ohlcv(self.symbol, timeframe, since_ms, limit)

            if isinstance(raw, pd.DataFrame):
                return raw

            if not raw:
                return pd.DataFrame()

            # データ品質検証・フィルタリング
            raw = self._validate_and_filter_data(raw, timeframe)

            # レート制限対応
            if (
                sleep
                and hasattr(self.exchange, "rateLimit")
                and self.exchange.rateLimit
            ):
                time.sleep(self.exchange.rateLimit / 1000.0)

            return self._convert_records_to_dataframe(raw)

        except Exception as e:
            logger.error(f"❌ [SIMPLE_FETCH] Failed: {e}")
            return pd.DataFrame()

    def _process_batch_data(self, batch: List, seen_ts: set, timeframe: str) -> List:
        """
        バッチデータの処理・フィルタリング（最適化版）
        """
        if not batch:
            return []

        # データ品質検証
        batch = self._validate_and_filter_data(batch, timeframe)

        # 重複削除（性能最適化：set操作を使用）
        new_records = []
        for record in batch:
            if record[0] not in seen_ts:
                seen_ts.add(record[0])
                new_records.append(record)

        return new_records

    def _validate_and_filter_data(self, data: List, timeframe: str) -> List:
        """
        データ品質検証・フィルタリング（最適化版）
        """
        if not data:
            return []

        valid_records = []
        anomalous_timestamps = []

        current_time_ms = int(time.time() * 1000)
        future_threshold = current_time_ms + (24 * 60 * 60 * 1000)  # 24時間後

        for record in data:
            try:
                timestamp_ms = int(record[0])

                # タイムスタンプ検証（最適化：範囲チェックのみ）
                if timestamp_ms <= future_threshold and timestamp_ms > 0:
                    valid_records.append(record)
                else:
                    anomalous_timestamps.append(
                        {
                            "timestamp_ms": timestamp_ms,
                            "timestamp_dt": pd.to_datetime(
                                timestamp_ms, unit="ms", utc=True
                            ),
                        }
                    )
            except (ValueError, IndexError, TypeError):
                continue

        # 異常タイムスタンプの警告（最初の3件のみ）
        if anomalous_timestamps:
            logger.warning(
                f"⚠️ [DATA_VALIDATION] Found {len(anomalous_timestamps)} anomalous timestamps"
            )
            for i, anomaly in enumerate(anomalous_timestamps[:3]):
                logger.warning(
                    f"   Anomaly {i+1}: {anomaly['timestamp_ms']} -> {anomaly['timestamp_dt']}"
                )

        return valid_records

    def _convert_records_to_dataframe(self, records: List) -> pd.DataFrame:
        """
        レコードをDataFrameに変換（最適化版）
        """
        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(
            records, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df.set_index("datetime")

        # 未来データフィルタリング（24時間の余裕）
        current_time = pd.Timestamp.now(tz="UTC")
        future_threshold = current_time + pd.Timedelta(hours=24)
        future_data_mask = df.index > future_threshold

        if future_data_mask.any():
            future_count = future_data_mask.sum()
            logger.warning(
                f"🚫 [DATA_FILTER] Future data filtered: {future_count} records"
            )
            df = df[~future_data_mask]

        return df[["open", "high", "low", "close", "volume"]]

    def fetch_with_freshness_fallback(
        self,
        timeframe: str = "1h",
        since: Optional[Union[int, float, str, datetime]] = None,
        limit: Optional[int] = None,
        max_age_hours: float = 2.0,
        **kwargs,
    ) -> pd.DataFrame:
        """
        データ新鮮度チェック付きデータ取得（最適化版）

        Args:
            timeframe: タイムフレーム
            since: 開始時刻
            limit: 取得件数上限
            max_age_hours: 許容される最大データ年齢（時間）
            **kwargs: get_price_dfへの追加パラメータ

        Returns:
            pd.DataFrame: 新鮮なデータ
        """
        logger.info("🔍 [FRESHNESS] Starting freshness-aware data fetch")
        logger.info(f"🔍 [FRESHNESS] Max age: {max_age_hours}h, timeframe: {timeframe}")

        try:
            # 通常のデータ取得を試行
            primary_data = self.get_price_df(
                timeframe=timeframe, since=since, limit=limit, **kwargs
            )

            # データの新鮮度チェック
            if not primary_data.empty and not self.client_obj._is_data_too_old(
                primary_data, max_age_hours
            ):
                logger.info(
                    f"✅ [FRESHNESS] Primary data is fresh: {len(primary_data)} records"
                )
                return primary_data

            logger.warning(
                "⚠️ [FRESHNESS] Primary data is stale, trying fallback strategies"
            )

            # フォールバック戦略1: 最新データ取得
            fallback_data = self.get_price_df(
                timeframe=timeframe,
                since=None,
                limit=min(limit or 100, 100),
                paginate=False,
                **kwargs,
            )

            if not fallback_data.empty and not self.client_obj._is_data_too_old(
                fallback_data, max_age_hours
            ):
                logger.info(
                    f"✅ [FRESHNESS] Fallback data is fresh: {len(fallback_data)} records"
                )
                return fallback_data

            # フォールバック戦略2: 部分データ救済
            partial_data = self.client_obj.get_last_partial_data()
            if partial_data is not None and not partial_data.empty:
                logger.info(
                    f"✅ [FRESHNESS] Using partial data rescue: {len(partial_data)} records"
                )
                return partial_data

            logger.warning("⚠️ [FRESHNESS] All fallback strategies failed")
            return primary_data  # 古くても何かしらのデータを返す

        except Exception as e:
            logger.error(f"❌ [FRESHNESS] Freshness fallback failed: {e}")
            return pd.DataFrame()


class DataPreprocessor:
    """
    データ前処理クラス（Phase 16.3-C統合版）

    - 重複除去・欠損補完・外れ値除去
    - 静的メソッドによる独立性保証
    - 性能最適化による処理時間短縮
    """

    @staticmethod
    def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
        """重複インデックスを除去"""
        return df[~df.index.duplicated(keep="first")]

    @staticmethod
    def fill_missing_bars(df: pd.DataFrame, timeframe: str = "1h") -> pd.DataFrame:
        """欠損バーを補完"""
        if df.empty:
            return df

        freq_offset = to_offset(timeframe)
        idx = pd.date_range(
            start=df.index[0],
            end=df.index[-1],
            freq=freq_offset,
            tz=df.index.tz,
        )
        df2 = df.reindex(idx)

        # 高速前方補完
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df2.columns:
                df2[col] = df2[col].ffill()

        return df2

    @staticmethod
    def remove_outliers(
        df: pd.DataFrame, thresh: float = 3.5, window: int = 20
    ) -> pd.DataFrame:
        """外れ値除去（最適化版）"""
        if df.empty:
            return df

        df = df.copy()
        price_cols = ["open", "high", "low", "close"]

        for col in [c for c in price_cols if c in df.columns]:
            # 中央値ベースの外れ値検出（MAD法）
            rolling_median = (
                df[col].rolling(window=window, center=True, min_periods=1).median()
            )
            deviation = (df[col] - rolling_median).abs()
            mad = deviation.rolling(window=window, center=True, min_periods=1).median()
            mad = mad + 1e-8  # ゼロ除算防止

            modified_zscore = 0.6745 * deviation / mad
            is_outlier = modified_zscore > thresh

            # 外れ値を移動平均で置換
            temp = df[col].copy()
            temp[is_outlier] = np.nan
            filled = temp.rolling(window=window, center=True, min_periods=1).mean()
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
        """
        統合クリーニング処理（最適化版）
        """
        if df.empty:
            return df

        # 重複除去 → 欠損補完 → 外れ値除去の順序で処理
        df = DataPreprocessor.remove_duplicates(df)
        df = DataPreprocessor.fill_missing_bars(df, timeframe)
        df = DataPreprocessor.remove_outliers(df, thresh, window)

        # 最終的な前方・後方補完
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = df[col].ffill().bfill()

        return df

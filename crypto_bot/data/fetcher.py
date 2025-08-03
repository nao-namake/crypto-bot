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
import time
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
            elif ts > 1e16:  # 16桁以上（異常値）
                logger.error(
                    f"🚨 [H.28.1-Stage2] Timestamp too large: {ts} (context: {context})"
                )
                return None

            # H.28.1-Stage3: 現在時刻比較・合理的範囲チェック
            current_time_ms = int(time.time() * 1000)
            one_year_ago_ms = current_time_ms - (365 * 24 * 60 * 60 * 1000)
            # Phase H.29: 未来時刻許容を24時間から1時間に厳格化
            one_hour_future_ms = current_time_ms + (60 * 60 * 1000)  # 1時間後まで

            if ts < one_year_ago_ms:
                logger.error(
                    f"🚨 [H.28.1-Stage3] Timestamp too old: {ts} < {one_year_ago_ms} (context: {context})"
                )
                return None
            elif ts > one_hour_future_ms:
                # Phase H.29: 未来時刻検出時の詳細ログ
                time_diff_hours = (ts - current_time_ms) / (60 * 60 * 1000)
                logger.error(
                    f"🚨 [H.29-Stage3] Future timestamp detected: {ts} is {time_diff_hours:.2f} hours ahead (context: {context})"
                )
                # 未来時刻の場合は現在時刻に修正
                corrected_ts = current_time_ms
                logger.warning(
                    f"🔧 [H.29-Stage3] Corrected future timestamp: {ts} -> {corrected_ts} (context: {context})"
                )
                return corrected_ts

            # H.28.1-Stage4: API仕様準拠確認（Bitbank用）
            # Bitbank APIは通常、現在時刻から過去72時間のデータを提供
            bitbank_limit_ms = current_time_ms - (72 * 60 * 60 * 1000)
            if ts < bitbank_limit_ms:
                logger.warning(
                    f"⚠️ [H.28.1-Stage4] Timestamp beyond Bitbank limit: {ts} < {bitbank_limit_ms} (context: {context})"
                )
                # API制限を超えているが、エラーではなく警告として処理

            # H.28.1-Stage5: 最終検証・ログ出力
            ts_datetime = datetime.fromtimestamp(ts / 1000)
            logger.debug(
                f"✅ [H.28.1-Stage5] Timestamp validated: {ts} ({ts_datetime}) (context: {context})"
            )

            return ts

        except Exception as e:
            logger.error(
                f"🚨 [H.28.1] Timestamp validation error: {e} (timestamp: {timestamp}, context: {context})"
            )
            return None

    def _calculate_safe_since_h28(self, base_timestamp: int, timeframe: str) -> int:
        """
        Phase H.28.1: 安全なsince値計算

        Args:
            base_timestamp: ベースとなるタイムスタンプ（ミリ秒）
            timeframe: タイムフレーム（"1h", "4h", "15m"等）

        Returns:
            int: 検証済みの次回取得用タイムスタンプ
        """
        try:
            # タイムフレーム→ミリ秒変換
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

            # 安全な次回タイムスタンプ計算
            next_timestamp = base_timestamp + timeframe_ms

            # H.28.1 検証システムで検証
            validated_timestamp = self._validate_timestamp_h28(
                next_timestamp, f"calculate_since_{timeframe}"
            )

            if validated_timestamp is None:
                # 異常値の場合は現在時刻を使用
                current_time_ms = int(time.time() * 1000)
                logger.error(
                    f"🚨 [H.28.1] Safe since calculation failed, using current time: {current_time_ms}"
                )
                return current_time_ms

            return validated_timestamp

        except Exception as e:
            # 計算失敗時は現在時刻を安全な値として返す
            current_time_ms = int(time.time() * 1000)
            logger.error(
                f"🚨 [H.28.1] Since calculation error: {e}, using current time: {current_time_ms}"
            )
            return current_time_ms

    def _should_abort_retry_h28(
        self, error_context: dict, attempt: int, max_attempts: int
    ) -> tuple[bool, str]:
        """
        Phase H.28.2: インテリジェントリトライ判定システム

        Args:
            error_context: エラー文脈情報
            attempt: 現在の試行回数
            max_attempts: 最大試行回数

        Returns:
            tuple[bool, str]: (停止すべきか, 理由)
        """
        # H.28.2-Rule1: 異常タイムスタンプ検出時は即座停止
        if error_context.get("timestamp_anomaly", False):
            return True, "Timestamp anomaly detected - no point in retrying"

        # H.28.2-Rule2: 構造的問題検出時は即座停止
        structural_issues = [
            "Invalid API credentials",
            "Symbol not found",
            "Timeframe not supported",
            "Permission denied",
        ]
        error_msg = error_context.get("error_message", "")
        for issue in structural_issues:
            if issue.lower() in error_msg.lower():
                return True, f"Structural issue detected: {issue}"

        # H.28.2-Rule3: 連続空レスポンス数に基づく判定
        consecutive_empty = error_context.get("consecutive_empty", 0)
        if consecutive_empty >= 8:  # 12→8に厳格化
            return True, f"Too many consecutive empty responses: {consecutive_empty}"

        # H.28.2-Rule4: タイムウィンドウ制御
        time_span_hours = error_context.get("time_span_hours", 0)
        if time_span_hours > 96:  # 96時間（4日）を超える場合は停止
            return True, f"Time window exceeded: {time_span_hours}h > 96h limit"

        # H.28.2-Rule5: 通常の試行回数制限
        if attempt >= max_attempts:
            return True, f"Max attempts reached: {attempt}/{max_attempts}"

        return False, "Continue retrying"

    def _calculate_smart_backoff_h28(
        self, attempt: int, consecutive_empty: int, error_type: str
    ) -> float:
        """
        Phase H.28.2: スマートバックオフ戦略

        Args:
            attempt: 試行回数
            consecutive_empty: 連続空レスポンス数
            error_type: エラータイプ

        Returns:
            float: 待機時間（秒）
        """
        # エラータイプ別の基本待機時間
        base_delays = {
            "rate_limit": 30,  # レート制限
            "server_error": 10,  # サーバーエラー
            "network_error": 5,  # ネットワークエラー
            "empty_response": 2,  # 空レスポンス
            "default": 3,  # デフォルト
        }

        base_delay = base_delays.get(error_type, base_delays["default"])

        # 指数バックオフ（上限付き）
        exponential_factor = min(2 ** (attempt - 1), 8)  # 最大8倍

        # 連続空レスポンスペナルティ
        empty_penalty = consecutive_empty * 0.5

        # 最終計算（上限15秒）
        total_delay = min(base_delay * exponential_factor + empty_penalty, 15)

        logger.debug(
            f"🔄 [H.28.2] Smart backoff: attempt={attempt}, empty={consecutive_empty}, type={error_type} -> {total_delay}s"
        )

        return total_delay

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
                    # 検証失敗時は現在時刻から72時間前を安全な開始点として使用
                    current_time_ms = int(time.time() * 1000)
                    since_ms = current_time_ms - (72 * 60 * 60 * 1000)  # 72時間前
                    logger.warning(
                        f"🔧 [H.28.1] Invalid since value, using 72h ago: {since_ms}"
                    )

            except Exception as e:
                logger.error(f"🚨 [H.28.1] Since calculation error: {e}")
                # エラー時は現在時刻から72時間前を使用
                current_time_ms = int(time.time() * 1000)
                since_ms = current_time_ms - (72 * 60 * 60 * 1000)
                logger.warning(f"🔧 [H.28.1] Error fallback, using 72h ago: {since_ms}")

        max_records = limit if limit is not None else float("inf")

        if paginate and limit:
            # Phase H.23.6: データ取得アルゴリズム最適化（400レコード確実達成）
            MAX_ATTEMPTS = (
                max_attempts if max_attempts is not None else 25
            )  # 20→25に増加（per_page=200対応）
            MAX_CONSECUTIVE_EMPTY = (
                max_consecutive_empty
                if max_consecutive_empty is not None
                else 12  # Phase H.26: 200レコード確実取得のため増加
            )
            MAX_CONSECUTIVE_NO_NEW = (
                max_consecutive_no_new
                if max_consecutive_no_new is not None
                else 20  # Phase H.26: 小バッチ対応・継続取得強化
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

                        # Phase H.28.2: インテリジェントリトライシステム適用
                        # エラー文脈構築
                        error_context = {
                            "consecutive_empty": consecutive_empty,
                            "timestamp_anomaly": last_since
                            and (
                                last_since
                                > int(time.time() * 1000) + 24 * 60 * 60 * 1000
                            ),
                            "error_message": "Empty batch response",
                            "time_span_hours": (
                                (int(time.time() * 1000) - (since_ms or 0))
                                / (1000 * 3600)
                                if since_ms
                                else 0
                            ),
                        }

                        # インテリジェント停止判定
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

                        # Phase H.28.2: スマートバックオフ戦略
                        backoff_delay = self._calculate_smart_backoff_h28(
                            attempt + 1, consecutive_empty, "empty_response"
                        )

                        logger.info(
                            f"🔄 [H.28.2] Smart backoff: {backoff_delay}s (attempt={attempt + 1}, empty={consecutive_empty})"
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
                            # Phase H.28.1: 安全なタイムスタンプ計算
                            # まず、現在のtsを検証
                            validated_ts = self._validate_timestamp_h28(
                                ts, f"batch_record_{new_records_count}"
                            )
                            if validated_ts is not None:
                                # 検証済みtsから安全な次回タイムスタンプを計算
                                last_since = self._calculate_safe_since_h28(
                                    validated_ts, timeframe
                                )
                                logger.debug(
                                    f"🔧 [H.28.1] Safe since calculated: {validated_ts} + {timeframe} -> {last_since}"
                                )
                            else:
                                # tsが異常値の場合は現在時刻を使用
                                current_time_ms = int(time.time() * 1000)
                                last_since = current_time_ms
                                logger.warning(
                                    f"🚨 [H.28.1] Invalid batch timestamp {ts}, using current time: {last_since}"
                                )
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
                    error_str = str(e).lower()
                    logger.error(
                        f"❌ [H.28.2] Batch fetch error on attempt {attempt + 1}: {e}"
                    )

                    # Phase H.28.2: エラー分類とインテリジェント対応
                    error_type = "default"
                    if "rate limit" in error_str or "too many requests" in error_str:
                        error_type = "rate_limit"
                    elif "timeout" in error_str or "connection" in error_str:
                        error_type = "network_error"
                    elif (
                        "server error" in error_str
                        or "500" in error_str
                        or "502" in error_str
                    ):
                        error_type = "server_error"
                    elif "permission" in error_str or "unauthorized" in error_str:
                        error_type = "structural"
                    elif "symbol" in error_str or "market" in error_str:
                        error_type = "structural"

                    # エラー文脈構築
                    error_context = {
                        "consecutive_empty": consecutive_empty,
                        "timestamp_anomaly": last_since
                        and (
                            last_since > int(time.time() * 1000) + 24 * 60 * 60 * 1000
                        ),
                        "error_message": str(e),
                        "time_span_hours": (
                            (int(time.time() * 1000) - (since_ms or 0)) / (1000 * 3600)
                            if since_ms
                            else 0
                        ),
                    }

                    # インテリジェント停止判定
                    should_abort, abort_reason = self._should_abort_retry_h28(
                        error_context, attempt + 1, MAX_ATTEMPTS
                    )

                    if should_abort:
                        logger.warning(
                            f"🚨 [H.28.2] INTELLIGENT TERMINATION after error: {abort_reason}"
                        )
                        break

                    # Phase H.28.2: スマートバックオフ戦略
                    error_delay = self._calculate_smart_backoff_h28(
                        attempt + 1, consecutive_empty, error_type
                    )
                    logger.info(
                        f"🔄 [H.28.2] Error recovery backoff: {error_delay}s (type={error_type})"
                    )
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

            # Phase 6.3: API応答タイムスタンプ検証機能追加
            if raw and isinstance(raw, list) and len(raw) > 0:
                current_time = pd.Timestamp.now(tz="UTC")
                current_ts_ms = int(current_time.timestamp() * 1000)

                # タイムスタンプ異常検出
                anomalous_timestamps = []
                valid_records = []

                for i, record in enumerate(raw):
                    if len(record) >= 6:  # OHLCV + timestamp
                        timestamp_ms = record[0]
                        timestamp_dt = pd.to_datetime(timestamp_ms, unit="ms", utc=True)

                        # 異常チェック: 未来データ
                        if timestamp_ms > current_ts_ms:
                            anomalous_timestamps.append(
                                {
                                    "index": i,
                                    "timestamp_ms": timestamp_ms,
                                    "timestamp_dt": timestamp_dt,
                                    "issue": "future_data",
                                }
                            )

                        # 異常チェック: 極端に古いデータ（2年以上前）
                        elif timestamp_ms < current_ts_ms - (
                            2 * 365 * 24 * 60 * 60 * 1000
                        ):
                            anomalous_timestamps.append(
                                {
                                    "index": i,
                                    "timestamp_ms": timestamp_ms,
                                    "timestamp_dt": timestamp_dt,
                                    "issue": "too_old",
                                }
                            )

                        # 異常チェック: 無効なタイムスタンプ（負の値など）
                        elif timestamp_ms <= 0:
                            anomalous_timestamps.append(
                                {
                                    "index": i,
                                    "timestamp_ms": timestamp_ms,
                                    "timestamp_dt": "invalid",
                                    "issue": "invalid_timestamp",
                                }
                            )
                        else:
                            valid_records.append(record)

                # 異常タイムスタンプのログ出力
                if anomalous_timestamps:
                    logger.warning(
                        "🚨 [PHASE-6.3] Anomalous timestamps detected in API response:"
                    )
                    logger.warning(
                        f"   Total records: {len(raw)}, Anomalous: {len(anomalous_timestamps)}, Valid: {len(valid_records)}"
                    )

                    for anomaly in anomalous_timestamps[:3]:  # 最大3件まで詳細表示
                        logger.warning(
                            f"   [{anomaly['index']}] {anomaly['issue']}: "
                            f"{anomaly['timestamp_ms']} -> {anomaly['timestamp_dt']}"
                        )

                    if len(anomalous_timestamps) > 3:
                        logger.warning(
                            f"   ... and {len(anomalous_timestamps) - 3} more anomalous records"
                        )

                    # 有効なレコードのみを使用
                    raw = valid_records
                    logger.info(
                        f"✅ [PHASE-6.3] Using {len(valid_records)} valid records after timestamp filtering"
                    )
                else:
                    logger.debug(
                        f"✅ [PHASE-6.3] All {len(raw)} API response timestamps are valid"
                    )

                # タイムスタンプ順序性検証
                if len(raw) > 1:
                    timestamps = [record[0] for record in raw]
                    is_sorted = all(
                        timestamps[i] <= timestamps[i + 1]
                        for i in range(len(timestamps) - 1)
                    )
                    if not is_sorted:
                        logger.warning(
                            "⚠️ [PHASE-6.3] API response timestamps are not in chronological order"
                        )
                        # タイムスタンプでソート
                        raw.sort(key=lambda x: x[0])
                        logger.info("✅ [PHASE-6.3] Records sorted by timestamp")
                    else:
                        logger.debug(
                            "✅ [PHASE-6.3] API response timestamps are properly ordered"
                        )
            else:
                logger.debug(
                    "🔍 [PHASE-6.3] No data to validate or invalid response format"
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

        # Phase 6.1: 未来データフィルタリング機能追加（緩和版）
        # 24時間の余裕を持たせて異常な未来データのみフィルタリング
        current_time = pd.Timestamp.now(tz="UTC")
        tolerance_hours = 24  # 24時間の余裕
        future_threshold = current_time + pd.Timedelta(hours=tolerance_hours)
        future_data_mask = df.index > future_threshold
        if future_data_mask.any():
            future_count = future_data_mask.sum()
            logger.warning(
                f"🚫 [PHASE-6.1] Future data detected and filtered: {future_count} records"
            )
            logger.warning(
                f"   Current time: {current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )
            if future_count > 0:
                future_samples = df[future_data_mask].head(3)
                for idx, row in future_samples.iterrows():
                    logger.warning(
                        f"   Future timestamp: {idx.strftime('%Y-%m-%d %H:%M:%S UTC')}"
                    )
            # 未来データを除去
            df = df[~future_data_mask]
            logger.info(
                f"✅ [PHASE-6.1] Remaining records after future data removal: {len(df)}"
            )
        else:
            logger.debug(f"✅ [PHASE-6.1] No future data detected in {len(df)} records")

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

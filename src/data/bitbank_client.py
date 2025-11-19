"""
Bitbank 信用取引専用APIクライアント

最終更新: 2025/11/16 (Phase 52.4-B)

信用取引（ロング・ショート）に特化したBitbank APIクライアント。
ccxtライブラリを使用したシンプル実装・証拠金維持率監視・SSL証明書対応。

主要機能:
- 信用取引注文（成行・指値・stop_limit）
- 証拠金維持率監視（80%遵守）
- OHLCVデータ取得（マルチタイムフレーム対応）
- GET/POST API対応・エラーハンドリング

開発履歴:
- Phase 52.4-B: コード整理・ドキュメント統一
- Phase 49: バックテストモード・維持率80%遵守
- Phase 35: stop_limit注文・GET/POST API対応
"""

import asyncio
import os
import time
from typing import Any, Dict, List, Optional, Union

import aiohttp
import ccxt.async_support as ccxt

from ..core.config import get_config, get_threshold
from ..core.exceptions import DataFetchError, ExchangeAPIError
from ..core.logger import get_logger


class BitbankClient:
    """Bitbank信用取引専用APIクライアント."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        leverage: float = 1.0,
    ):
        """
        初期化

        Args:
            api_key: BitbankのAPIキー
            api_secret: BitbankのAPIシークレット
            leverage: レバレッジ倍率（1.0-2.0）.
        """
        self.logger = get_logger()

        # API認証情報（Cloud Run環境デバッグ強化）
        self.api_key = api_key or os.getenv("BITBANK_API_KEY")
        self.api_secret = api_secret or os.getenv("BITBANK_API_SECRET")

        # CRIT-2 Fix: API Secret露出防止（MD5ハッシュ削除・安全な情報のみログ出力）
        if self.api_key:
            self.logger.info(f"🔑 BITBANK_API_KEY読み込み確認: 存在=True, 長さ={len(self.api_key)}")
        else:
            self.logger.error("❌ BITBANK_API_KEY読み込み失敗: 環境変数が空またはNone")

        if self.api_secret:
            self.logger.info(
                f"🔐 BITBANK_API_SECRET読み込み確認: 存在=True, 長さ={len(self.api_secret)}"
            )
        else:
            self.logger.error("❌ BITBANK_API_SECRET読み込み失敗: 環境変数が空またはNone")

        # レバレッジ検証（bitbank信用取引仕様: 1.0-2.0）
        if not (1.0 <= leverage <= 2.0):
            raise ValueError(f"レバレッジは1.0-2.0の範囲で設定してください: {leverage}")

        self.leverage = leverage

        # Phase 35: バックテストモードフラグ（API呼び出しモック化用）
        # グローバルフラグから自動検出
        try:
            from ..core.config import is_backtest_mode

            self._backtest_mode = is_backtest_mode()
            if self._backtest_mode:
                self.logger.info("🎯 バックテストモード検出: API呼び出しをモック化します")
        except Exception:
            # インポートエラー時はデフォルトFalse
            self._backtest_mode = False

        # ccxt Bitbank エクスチェンジ初期化
        try:
            self.exchange = ccxt.bitbank(
                {
                    "apiKey": self.api_key,
                    "secret": self.api_secret,
                    "sandbox": False,  # 本番環境
                    "rateLimit": get_config().exchange.rate_limit_ms,  # HIGH-3 Fix: Config統合
                    "enableRateLimit": True,
                    "timeout": get_config().exchange.timeout_ms,  # HIGH-3 Fix: Config統合
                }
            )

            self.logger.info(f"Bitbank信用取引クライアント初期化完了（レバレッジ: {leverage}x）")

        except Exception as e:
            raise ExchangeAPIError(
                f"Bitbank API初期化に失敗しました: {e}",
                context={
                    "leverage": leverage,
                    "has_credentials": bool(self.api_key and self.api_secret),
                },
            )

    async def test_connection(self) -> bool:
        """
        API接続テスト

        CRIT-1 Fix: async/await対応（ccxt.async_support使用）
        """
        try:
            # 公開API（認証不要）でテスト（設定から取得）
            try:
                config = get_config()
                symbol = config.exchange.symbol
            except Exception:
                symbol = "BTC/JPY"  # フォールバック

            ticker = await self.exchange.fetch_ticker(symbol)
            self.logger.info(
                f"Bitbank API接続テスト成功 - {symbol}価格: ¥{ticker['last']:,.0f}",
                extra_data={"price": ticker["last"]},
            )
            return True

        except Exception as e:
            self.logger.error("Bitbank API接続テスト失敗", error=e)
            return False

    def set_backtest_mode(self, enabled: bool) -> None:
        """
        バックテストモード設定（Phase 35: API呼び出しモック化）

        Args:
            enabled: バックテストモード有効化フラグ
        """
        self._backtest_mode = enabled
        if enabled:
            self.logger.info("🎯 BitbankClient: バックテストモード有効化（API呼び出しモック化）")
        else:
            self.logger.debug("BitbankClient: バックテストモード無効化")

    async def fetch_ohlcv(
        self,
        symbol: str = None,
        timeframe: str = "1h",
        since: Optional[int] = None,
        limit: int = 200,  # Phase 51.5-A Fix: デフォルト100→200件
    ) -> List[List[Union[int, float]]]:
        """
        OHLCV データ取得（4時間足は直接API実装を使用）

        Args:
            symbol: 通貨ペア（Noneの場合は設定から取得）
            timeframe: タイムフレーム（1m, 5m, 15m, 30m, 1h, 4h, 8h, 12h, 1d, 1w）
            since: 開始時刻（ミリ秒）
            limit: 取得件数（Phase 51.5-A Fix: デフォルト200件）

        Returns:
            OHLCV データリスト [[timestamp, open, high, low, close, volume], ...]

        Raises:
            DataFetchError: データ取得失敗時.
        """
        # symbolが未指定の場合は設定から取得
        if symbol is None:
            try:
                config = get_config()
                symbol = config.exchange.symbol
            except Exception:
                symbol = "BTC/JPY"  # フォールバック

        # 4時間足の場合は直接API実装を使用（ccxt制約回避）
        if timeframe == "4h":
            self.logger.debug("4時間足検出: 直接API実装を使用")
            # Phase 52.5: 重複import asyncio削除（モジュール先頭でimport済み）
            from datetime import datetime

            # 現在年を取得
            current_year = datetime.now().year

            try:
                # 既存のイベントループ内で直接awaitを使用
                ohlcv = await self.fetch_ohlcv_4h_direct(symbol=symbol, year=current_year)

                # Phase 51.5 Fix: limit適用前の件数ログ
                original_count = len(ohlcv)

                # limitが指定されている場合は最新データに制限
                if limit and len(ohlcv) > limit:
                    ohlcv = ohlcv[-limit:]
                    self.logger.info(
                        "📊 4時間足limit適用 - "
                        f"取得件数={original_count}件, "
                        f"limit={limit}件, "
                        f"適用後={len(ohlcv)}件"
                    )
                else:
                    self.logger.info(
                        "📊 4時間足limit適用なし - "
                        f"取得件数={original_count}件 (limit={limit}件)"
                    )

                # Phase 51.5 Fix: 最小行数チェック（戦略要求20行未満ならエラー）
                min_required_rows = 20
                if len(ohlcv) < min_required_rows:
                    self.logger.warning(
                        f"⚠️ 4時間足直接API取得件数不足: {len(ohlcv)}件 < {min_required_rows}件必要 "
                        "- ccxtリトライ"
                    )
                    raise ValueError(
                        f"データ不足: {len(ohlcv)}件 < {min_required_rows}件（戦略要求最小行数）"
                    )

                return ohlcv

            except Exception as e:
                self.logger.warning(f"直接API取得失敗（{type(e).__name__}: {e}）、ccxtでリトライ")
                # フォールバックとしてccxtを試行（エラーになる可能性が高いが）
                # ここはそのままccxt呼び出しを継続

        # Phase 51.5-C Fix: 15分足の場合は直接API実装を使用（YYYYMMDD形式・since=None問題回避）
        if timeframe == "15m":
            self.logger.debug("15分足検出: 直接API実装を使用（Phase 51.5-C）")
            # 削除: 重複import asyncio (line 222)
            from datetime import datetime, timedelta

            try:
                # 15分足は1日96本 → limitから必要日数を計算
                # limit=50なら約0.5日分 → 1日分取得
                # limit=200なら約2.08日分 → 3日分取得
                candles_per_day = 96
                days_needed = max(1, (limit // candles_per_day) + 1)

                self.logger.debug(
                    f"📊 15分足データ取得計画: limit={limit}本 → {days_needed}日分取得"
                )

                # 複数日のデータを結合
                all_ohlcv = []
                # Phase 53.8.2: Bitbank API仕様により当日の15m足URLは存在しない（エラーコード10000）
                # 前日以降の完全データのみ取得（days_ago=1から開始）
                for days_ago in range(1, days_needed + 1):
                    date_obj = datetime.now() - timedelta(days=days_ago)
                    date_str = date_obj.strftime("%Y%m%d")

                    try:
                        daily_data = await self.fetch_ohlcv_15m_direct(symbol=symbol, date=date_str)
                        if daily_data:
                            all_ohlcv.extend(daily_data)
                            self.logger.debug(
                                f"📊 15分足日次データ取得成功: {date_str} → {len(daily_data)}件"
                            )
                    except DataFetchError as e:
                        self.logger.warning(f"⚠️ 15分足日次データ取得失敗（{date_str}）: {e}")
                        # 1日分の失敗は許容（他の日でカバー）
                        continue

                if not all_ohlcv:
                    raise DataFetchError(
                        f"15分足データ取得失敗: {days_needed}日間すべて取得失敗",
                        context={"symbol": symbol, "timeframe": timeframe, "days": days_needed},
                    )

                # タイムスタンプでソート（古い順）
                all_ohlcv.sort(key=lambda x: x[0])

                # Phase 51.5-C: limit適用前の件数ログ
                original_count = len(all_ohlcv)

                # limitが指定されている場合は最新データに制限
                if limit and len(all_ohlcv) > limit:
                    all_ohlcv = all_ohlcv[-limit:]
                    self.logger.info(
                        "📊 15分足limit適用 - "
                        f"取得件数={original_count}件, "
                        f"limit={limit}件, "
                        f"適用後={len(all_ohlcv)}件"
                    )
                else:
                    self.logger.info(
                        "📊 15分足limit適用なし - " f"取得件数={original_count}件 (limit={limit}件)"
                    )

                # Phase 51.5-C: 最小行数チェック（戦略要求20行未満ならエラー）
                min_required_rows = 20
                if len(all_ohlcv) < min_required_rows:
                    self.logger.warning(
                        f"⚠️ 15分足直接API取得件数不足: {len(all_ohlcv)}件 < {min_required_rows}件必要 "
                        "- ccxtリトライ"
                    )
                    raise ValueError(
                        f"データ不足: {len(all_ohlcv)}件 < {min_required_rows}件（戦略要求最小行数）"
                    )

                self.logger.info(
                    "✅ Phase 51.5-C: 15分足直接API実装成功 - "
                    f"{days_needed}日分 → {len(all_ohlcv)}件取得完了"
                )

                return all_ohlcv

            except Exception as e:
                self.logger.warning(
                    f"15分足直接API取得失敗（{type(e).__name__}: {e}）、ccxtでリトライ"
                )
                # フォールバックとしてccxtを試行
                # ここはそのままccxt呼び出しを継続

        # Phase 51.5-C Fix: 15m足等でもリトライロジック適用
        max_retries = 3
        last_exception = None
        min_required_rows = 20  # Phase 52.5: 戦略要求最小行数（ハードコード統一）

        for attempt in range(max_retries):
            try:
                self.logger.debug(
                    f"OHLCV データ取得開始（試行{attempt + 1}/{max_retries}）: "
                    f"{symbol} {timeframe} limit={limit}"
                )

                # CRIT-1 Fix: async/await対応（イベントループブロッキング解消）
                # Phase 51.5-C Fix: タイムアウト設定（既存のexchange設定を利用）
                # ccxtのexchangeインスタンスは既にtimeout設定済み（30秒）
                ohlcv = await self.exchange.fetch_ohlcv(
                    symbol=symbol, timeframe=timeframe, since=since, limit=limit
                )

                if not ohlcv:
                    raise DataFetchError(
                        f"OHLCV データが空です: {symbol} {timeframe}",
                        context={"symbol": symbol, "timeframe": timeframe},
                    )

                # Phase 51.5-C Fix: 最小行数チェック
                if len(ohlcv) < min_required_rows:
                    error_msg = (
                        f"データ不足: {len(ohlcv)}件 < {min_required_rows}件（戦略要求最小行数）"
                    )
                    if attempt < max_retries - 1:
                        wait_time = 2**attempt  # Exponential backoff
                        self.logger.warning(
                            f"⚠️ {error_msg} - {wait_time}秒後にリトライ（試行{attempt + 1}/{max_retries}）"
                        )
                        # 削除: 重複import asyncio（line 340）

                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise DataFetchError(
                            error_msg, context={"symbol": symbol, "timeframe": timeframe}
                        )

                self.logger.info(
                    f"✅ {timeframe}足データ取得成功: {len(ohlcv)}件",
                    extra_data={
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "count": len(ohlcv),
                    },
                )

                return ohlcv

            except (ccxt.NetworkError, ccxt.ExchangeError) as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff: 1秒, 2秒, 4秒
                    self.logger.warning(
                        f"⚠️ {timeframe}足取得失敗（試行{attempt + 1}/{max_retries}）: "
                        f"{type(e).__name__}: {e} - {wait_time}秒後にリトライ"
                    )
                    # Phase 52.5: 重複import asyncio削除（モジュール先頭でimport済み）
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(
                        f"❌ {timeframe}足取得失敗（全{max_retries}回試行）: {type(e).__name__}: {e}"
                    )
                    raise DataFetchError(
                        f"{type(e).__name__}: {e}",
                        context={"symbol": symbol, "timeframe": timeframe},
                    ) from e
            except Exception as e:
                self.logger.error(f"❌ 予期しないエラー: {type(e).__name__}: {e}")
                raise DataFetchError(
                    f"OHLCV データ取得に失敗しました: {e}",
                    context={"symbol": symbol, "timeframe": timeframe},
                ) from e

        # 全リトライ失敗時（ここには到達しないはずだが念のため）
        if last_exception:
            raise DataFetchError(
                f"全{max_retries}回のリトライ失敗: {last_exception}",
                context={"symbol": symbol, "timeframe": timeframe},
            ) from last_exception

    async def fetch_ohlcv_4h_direct(
        self,
        symbol: str = "BTC/JPY",
        year: int = 2025,
    ) -> List[List[Union[int, float]]]:
        """
        4時間足データを直接API実装で取得（ccxt制約回避）

        Args:
            symbol: 通貨ペア
            year: 取得年（YYYY形式）

        Returns:
            OHLCV データリスト [[timestamp, open, high, low, close, volume], ...]

        Raises:
            DataFetchError: データ取得失敗時
        """
        # Phase 51.5 Fix: リトライロジック追加（タイムアウト・ネットワークエラー対策）
        max_retries = 3
        last_exception = None

        for attempt in range(max_retries):
            try:
                self.logger.debug(
                    f"4時間足直接API取得開始: {symbol} {year} (試行 {attempt + 1}/{max_retries})"
                )

                # Bitbank Public APIの正しい形式
                pair = symbol.lower().replace("/", "_")  # BTC/JPY -> btc_jpy
                url = f"https://public.bitbank.cc/{pair}/candlestick/4hour/{year}"

                # SSL証明書設定（セキュア設定）
                import ssl

                ssl_context = ssl.create_default_context()

                connector = aiohttp.TCPConnector(ssl=ssl_context)
                async with aiohttp.ClientSession(connector=connector) as session:
                    # Phase 51.5 Fix: タイムアウト延長（10秒→30秒・大量データ対応）
                    # データ量経時的増加対策: 2025年11月時点で約1,830件（約515KB）
                    timeout = aiohttp.ClientTimeout(
                        total=30.0,  # 全体タイムアウト: 10秒→30秒
                        connect=5.0,  # 接続タイムアウト: 5秒
                        sock_read=25.0,  # 読み取りタイムアウト: 25秒
                    )

                    async with session.get(url, timeout=timeout) as response:
                        # Phase 51.5 Fix: レスポンスサイズログ追加（デバッグ用）
                        content_length = response.headers.get("Content-Length")
                        if content_length:
                            self.logger.debug(
                                f"📊 レスポンスサイズ: {int(content_length) / 1024:.1f}KB"
                            )

                        # JSONパース前にテキストサイズ確認（メモリ使用量診断）
                        text = await response.text()
                        self.logger.debug(f"📊 テキストサイズ: {len(text) / 1024:.1f}KB")

                        import json

                        data = json.loads(text)

                        # Phase 51.5 Fix: Raw Responseログ追加（デバッグ強化）
                        self.logger.debug(
                            "📊 API Response確認 - "
                            f"success={data.get('success')}, "
                            f"has_data={bool(data.get('data'))}, "
                            f"has_candlestick={bool(data.get('data', {}).get('candlestick'))}"
                        )

                        if data.get("success") == 1:
                            candlestick_data = data["data"]["candlestick"][0]["ohlcv"]

                            if not candlestick_data:
                                raise DataFetchError(
                                    f"4時間足データが空です: {symbol} {year}",
                                    context={"symbol": symbol, "year": year},
                                )

                            # Phase 51.5 Fix: データ変換前の件数ログ
                            self.logger.debug(f"📊 Raw Candlestick件数: {len(candlestick_data)}件")

                            # データ形式をccxtと統一（timestampをミリ秒に変換）
                            ohlcv_data = []
                            for item in candlestick_data:
                                # Bitbank形式: [open, high, low, close, volume, timestamp_ms]
                                # ccxt形式: [timestamp_ms, open, high, low, close, volume]
                                if len(item) >= 6:
                                    timestamp_ms = item[5]
                                    ohlcv_data.append(
                                        [
                                            timestamp_ms,
                                            float(item[0]),  # open
                                            float(item[1]),  # high
                                            float(item[2]),  # low
                                            float(item[3]),  # close
                                            float(item[4]),  # volume
                                        ]
                                    )

                            # Phase 51.5 Fix: 変換後のデータ件数ログ強化
                            self.logger.info(
                                f"✅ 4時間足直接API取得成功: {len(ohlcv_data)}件 "
                                f"(raw={len(candlestick_data)}件, "
                                f"first_ts={ohlcv_data[0][0] if ohlcv_data else None}, "
                                f"last_ts={ohlcv_data[-1][0] if ohlcv_data else None})",
                                extra_data={
                                    "symbol": symbol,
                                    "year": year,
                                    "count": len(ohlcv_data),
                                    "method": "direct_api",
                                    "attempt": attempt + 1,
                                },
                            )

                            return ohlcv_data

                        else:
                            error_code = data.get("data", {}).get("code", "unknown")
                            raise DataFetchError(
                                f"Bitbank API エラー: {error_code}",
                                context={
                                    "symbol": symbol,
                                    "year": year,
                                    "error_code": error_code,
                                },
                            )

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff: 1秒, 2秒, 4秒
                    self.logger.warning(
                        f"⚠️ 4時間足取得失敗（試行{attempt + 1}/{max_retries}）: {type(e).__name__}: {e} "
                        f"- {wait_time}秒後にリトライ"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(
                        f"❌ 4時間足取得失敗（全{max_retries}回試行失敗）: {type(e).__name__}: {e}"
                    )
                    raise DataFetchError(
                        f"ネットワークエラー（4時間足・{max_retries}回リトライ失敗）: {e}",
                        context={"symbol": symbol, "year": year, "attempts": max_retries},
                    )
            except Exception as e:
                last_exception = e
                self.logger.error(f"❌ 4時間足取得予期しないエラー: {type(e).__name__}: {e}")
                raise DataFetchError(
                    f"4時間足データ取得失敗: {e}",
                    context={"symbol": symbol, "year": year, "attempt": attempt + 1},
                )

        # ここには到達しないはずだが、念のため
        raise DataFetchError(
            f"4時間足データ取得失敗（全{max_retries}回試行完了・原因不明）",
            context={"symbol": symbol, "year": year, "last_exception": str(last_exception)},
        )

    async def fetch_ohlcv_15m_direct(
        self,
        symbol: str = "BTC/JPY",
        date: str = "20251104",
    ) -> List[List[Union[int, float]]]:
        """
        15分足データを直接API実装で取得（ccxt制約回避）

        Phase 51.5-C: since=None問題解決のため、4h足と同様の直接API実装を追加
        bitbank APIは15m足に対してYYYYMMDD形式パラメータを要求（短期足仕様）

        Args:
            symbol: 通貨ペア
            date: 取得日（YYYYMMDD形式、例: 20251104）

        Returns:
            OHLCV データリスト [[timestamp, open, high, low, close, volume], ...]

        Raises:
            DataFetchError: データ取得失敗時
        """
        # Phase 51.5-C: リトライロジック追加（4h足パターン準拠）
        max_retries = 3
        last_exception = None

        for attempt in range(max_retries):
            try:
                self.logger.debug(
                    f"15分足直接API取得開始: {symbol} {date} (試行 {attempt + 1}/{max_retries})"
                )

                # Bitbank Public APIの正しい形式（YYYYMMDD形式）
                pair = symbol.lower().replace("/", "_")  # BTC/JPY -> btc_jpy
                url = f"https://public.bitbank.cc/{pair}/candlestick/15min/{date}"

                # SSL証明書設定（セキュア設定）
                import ssl

                ssl_context = ssl.create_default_context()

                connector = aiohttp.TCPConnector(ssl=ssl_context)
                async with aiohttp.ClientSession(connector=connector) as session:
                    # Phase 51.5-C: タイムアウト設定（4h足と同様）
                    timeout = aiohttp.ClientTimeout(
                        total=30.0,  # 全体タイムアウト: 30秒
                        connect=5.0,  # 接続タイムアウト: 5秒
                        sock_read=25.0,  # 読み取りタイムアウト: 25秒
                    )

                    async with session.get(url, timeout=timeout) as response:
                        # レスポンスサイズログ
                        content_length = response.headers.get("Content-Length")
                        if content_length:
                            self.logger.debug(
                                f"📊 15m足レスポンスサイズ: {int(content_length) / 1024:.1f}KB"
                            )

                        # JSONパース
                        text = await response.text()
                        self.logger.debug(f"📊 15m足テキストサイズ: {len(text) / 1024:.1f}KB")

                        import json

                        data = json.loads(text)

                        # API Response確認
                        self.logger.debug(
                            "📊 15m足API Response確認 - "
                            f"success={data.get('success')}, "
                            f"has_data={bool(data.get('data'))}, "
                            f"has_candlestick={bool(data.get('data', {}).get('candlestick'))}"
                        )

                        if data.get("success") == 1:
                            candlestick_data = data["data"]["candlestick"][0]["ohlcv"]

                            if not candlestick_data:
                                raise DataFetchError(
                                    f"15分足データが空です: {symbol} {date}",
                                    context={"symbol": symbol, "date": date},
                                )

                            # Raw Candlestick件数ログ
                            self.logger.debug(
                                f"📊 15m足Raw Candlestick件数: {len(candlestick_data)}件"
                            )

                            # データ形式をccxtと統一（timestampをミリ秒に変換）
                            ohlcv_data = []
                            for item in candlestick_data:
                                # Bitbank形式: [open, high, low, close, volume, timestamp_ms]
                                # ccxt形式: [timestamp_ms, open, high, low, close, volume]
                                if len(item) >= 6:
                                    timestamp_ms = item[5]
                                    ohlcv_data.append(
                                        [
                                            timestamp_ms,
                                            float(item[0]),  # open
                                            float(item[1]),  # high
                                            float(item[2]),  # low
                                            float(item[3]),  # close
                                            float(item[4]),  # volume
                                        ]
                                    )

                            # 変換後のデータ件数ログ
                            self.logger.info(
                                f"✅ 15分足直接API取得成功: {len(ohlcv_data)}件 (date={date})",
                                extra_data={
                                    "symbol": symbol,
                                    "date": date,
                                    "count": len(ohlcv_data),
                                    "method": "direct_api_15m",
                                    "attempt": attempt + 1,
                                },
                            )

                            return ohlcv_data

                        else:
                            error_code = data.get("data", {}).get("code", "unknown")
                            raise DataFetchError(
                                f"Bitbank API エラー（15m足）: {error_code}",
                                context={
                                    "symbol": symbol,
                                    "date": date,
                                    "error_code": error_code,
                                },
                            )

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff: 1秒, 2秒, 4秒
                    self.logger.warning(
                        f"⚠️ 15分足取得失敗（試行{attempt + 1}/{max_retries}）: {type(e).__name__}: {e} "
                        f"- {wait_time}秒後にリトライ"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(
                        f"❌ 15分足取得失敗（全{max_retries}回試行失敗）: {type(e).__name__}: {e}"
                    )
                    raise DataFetchError(
                        f"ネットワークエラー（15分足・{max_retries}回リトライ失敗）: {e}",
                        context={"symbol": symbol, "date": date, "attempts": max_retries},
                    )
            except Exception as e:
                last_exception = e
                self.logger.error(f"❌ 15分足取得予期しないエラー: {type(e).__name__}: {e}")
                raise DataFetchError(
                    f"15分足データ取得失敗: {e}",
                    context={"symbol": symbol, "date": date, "attempt": attempt + 1},
                )

        # ここには到達しないはずだが、念のため
        raise DataFetchError(
            f"15分足データ取得失敗（全{max_retries}回試行完了・原因不明）",
            context={"symbol": symbol, "date": date, "last_exception": str(last_exception)},
        )

    async def fetch_ticker(self, symbol: str = "BTC/JPY") -> Dict[str, Any]:
        """
        ティッカー情報取得

        CRIT-1 Fix: async/await対応

        Args:
            symbol: 通貨ペア

        Returns:
            ティッカー情報.
        """
        try:
            ticker = await self.exchange.fetch_ticker(symbol)

            self.logger.debug(
                f"ティッカー取得成功: {symbol} = ¥{ticker['last']:,.0f}",
                extra_data={
                    "symbol": symbol,
                    "price": ticker["last"],
                    "bid": ticker["bid"],
                    "ask": ticker["ask"],
                },
            )

            return ticker

        except Exception as e:
            raise DataFetchError(
                f"ティッカー取得に失敗しました: {symbol} - {e}",
                context={"symbol": symbol},
            )

    async def fetch_order_book(self, symbol: str = "BTC/JPY", limit: int = 20) -> Dict[str, Any]:
        """
        板情報取得（Phase 33: スマート注文機能用）

        CRIT-1 Fix: async/await対応

        Args:
            symbol: 通貨ペア
            limit: 取得する板の深さ

        Returns:
            板情報（bids: 買い板, asks: 売り板）
        """
        try:
            orderbook = await self.exchange.fetch_order_book(symbol, limit)

            self.logger.debug(
                f"板情報取得成功: {symbol} (depth={limit})",
                extra_data={
                    "symbol": symbol,
                    "best_bid": orderbook["bids"][0][0] if orderbook.get("bids") else None,
                    "best_ask": orderbook["asks"][0][0] if orderbook.get("asks") else None,
                },
            )

            return orderbook

        except Exception as e:
            raise DataFetchError(
                f"板情報取得に失敗しました: {symbol} - {e}",
                context={"symbol": symbol},
            )

    async def fetch_balance(self) -> Dict[str, Any]:
        """
        残高情報取得（Phase 35: バックテストモックデータ対応）

        Returns:
            信用取引残高情報.
        """
        # Phase 35: バックテストモード時はモックデータ返却（API呼び出しスキップ）
        if self._backtest_mode:
            # 削除: 重複import get_threshold (line 785)

            mock_enabled = get_threshold("backtest.mock_api_calls", True)
            if mock_enabled:
                self.logger.debug("🎯 バックテストモック: fetch_balance スキップ")
                return {
                    "JPY": {"total": 10000.0, "free": 10000.0, "used": 0.0},
                    "BTC": {"total": 0.0, "free": 0.0, "used": 0.0},
                    "info": {"mock": True},
                }

        try:
            if not self.api_key or not self.api_secret:
                raise ExchangeAPIError(
                    "残高取得には認証が必要です",
                    context={"operation": "fetch_balance"},
                )

            balance = await self.exchange.fetch_balance()

            self.logger.debug(
                "信用取引残高取得成功",
                extra_data={
                    "total_jpy": balance.get("JPY", {}).get("total", 0),
                    "free_jpy": balance.get("JPY", {}).get("free", 0),
                },
            )

            return balance

        except ccxt.AuthenticationError as e:
            raise ExchangeAPIError(f"認証エラー: {e}", context={"operation": "fetch_balance"})
        except Exception as e:
            raise ExchangeAPIError(
                f"残高取得に失敗しました: {e}",
                context={"operation": "fetch_balance"},
            )

    async def create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        amount: float,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        is_closing_order: bool = False,
        entry_position_side: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        注文作成（信用取引対応・Phase 37.5: stop_limit対応）

        Args:
            symbol: 通貨ペア（例：BTC/JPY）
            side: 売買方向（buy/sell）
            order_type: 注文タイプ（market/limit/stop/stop_limit）
            amount: 注文量（BTC）
            price: 指値価格（limit/stop_limitの場合・JPY）
            trigger_price: トリガー価格（stop/stop_limitの場合・JPY）
            is_closing_order: 決済注文フラグ（True=既存ポジション決済のみ）
            entry_position_side: エントリー時のposition_side（"long"/"short"・決済時のみ必須）

        Returns:
            注文情報（order_id含む）

        Raises:
            ExchangeAPIError: 注文作成失敗時.
        """
        try:
            if not self.api_key or not self.api_secret:
                raise ExchangeAPIError(
                    "注文作成には認証が必要です",
                    context={"operation": "create_order"},
                )

            # パラメータ検証
            if side not in ["buy", "sell"]:
                raise ExchangeAPIError(f"無効な売買方向: {side}", context={"side": side})

            if order_type not in ["market", "limit", "stop", "stop_limit"]:
                raise ExchangeAPIError(
                    f"無効な注文タイプ: {order_type}",
                    context={"order_type": order_type},
                )

            if amount <= 0:
                raise ExchangeAPIError(f"無効な注文量: {amount}", context={"amount": amount})

            # Phase 37.5: limit/stop_limit注文の価格検証
            if order_type in ["limit", "stop_limit"] and (price is None or price <= 0):
                raise ExchangeAPIError(
                    f"{order_type}注文には有効な価格が必要です: {price}",
                    context={"price": price, "order_type": order_type},
                )

            # Phase 37.5: stop/stop_limit注文のトリガー価格検証
            if order_type in ["stop", "stop_limit"] and (
                trigger_price is None or trigger_price <= 0
            ):
                raise ExchangeAPIError(
                    f"逆指値注文には有効なトリガー価格が必要です: {trigger_price}",
                    context={"trigger_price": trigger_price, "order_type": order_type},
                )

            # Phase 33.1: 信用取引用パラメータ（TP/SL決済注文対応・両建て防止修正）
            params = {
                "margin": True,  # 信用取引有効
                "marginType": "isolated",  # 分離マージン
                "leverage": self.leverage,  # レバレッジ倍率
            }

            # Phase 37.5: stop/stop_limit注文のトリガー価格・執行価格設定
            if trigger_price is not None:
                # HIGH-5 Fix: str(int()) → str(round()) - 価格精度保持
                # bitbank API仕様: 整数文字列を期待
                params["trigger_price"] = str(round(trigger_price))
                self.logger.info(
                    f"🎯 逆指値注文トリガー設定: {trigger_price:.0f}円",
                    extra_data={"trigger_price": trigger_price, "order_type": order_type},
                )

            # Phase 37.5.2: stop_limit注文の場合、執行価格もparams内に明示的に設定
            if order_type == "stop_limit" and price is not None:
                # HIGH-5 Fix: str(int()) → str(round()) - 価格精度保持
                params["price"] = str(round(price))  # bitbank APIは整数文字列を期待
                self.logger.info(
                    f"💰 逆指値指値注文執行価格設定: {price:.0f}円",
                    extra_data={"price": price, "order_type": order_type},
                )

            # Phase 37.5.2: amount文字列化（bitbank API仕様完全準拠）
            params["amount"] = str(amount)
            self.logger.debug(
                f"📦 注文数量設定: {amount} BTC (文字列形式)",
                extra_data={"amount": amount, "order_type": order_type},
            )

            if is_closing_order:
                # ✅ 決済注文：既存ポジションと同じposition_sideでreduceOnly指定
                if not entry_position_side:
                    raise ExchangeAPIError(
                        "決済注文にはentry_position_sideが必須です",
                        context={"is_closing_order": True, "entry_position_side": None},
                    )
                params["reduceOnly"] = True  # 既存ポジション決済のみ（新規ポジション開かない）
                params["position_side"] = entry_position_side  # エントリーと同じposition_side
                self.logger.info(
                    f"🔄 決済注文作成: {side} {amount:.4f} BTC @ {price or 'MARKET'} (position_side={entry_position_side}, reduceOnly=True)"
                )
            else:
                # 新規注文：sideに基づいてposition_sideを設定
                params["position_side"] = "long" if side.lower() == "buy" else "short"

            # ショート注文の場合の特別な処理（レガシーから継承）
            if side.lower() == "sell":
                self.logger.info(
                    f"信用取引ショート注文作成: {symbol} {amount:.4f} BTC @ {price or 'MARKET'}",
                    extra_data={
                        "side": side,
                        "amount": amount,
                        "price": price,
                        "leverage": self.leverage,
                    },
                )
                params["side"] = "sell"  # 明示的にショート指定
            else:
                self.logger.info(
                    f"信用取引ロング注文作成: {symbol} {amount:.4f} BTC @ {price or 'MARKET'}",
                    extra_data={
                        "side": side,
                        "amount": amount,
                        "price": price,
                        "leverage": self.leverage,
                    },
                )
                params["side"] = "buy"

            # Phase 37.5: デバッグログ（stop_limit注文パラメータ確認）
            if order_type == "stop_limit":
                self.logger.info(
                    "📋 stop_limit注文パラメータ確認",
                    extra_data={
                        "symbol": symbol,
                        "type": order_type,
                        "side": side,
                        "amount": amount,
                        "price": price,
                        "params": params,
                    },
                )

            # Phase 37.5.2: stop_limit注文の場合、ccxtのprice引数をNone化（params["price"]のみ使用）
            order_price_arg = None if order_type == "stop_limit" else price

            # 注文実行
            start_time = time.time()
            order = await self.exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                price=order_price_arg,  # stop_limitの場合はNone、params["price"]のみ使用
                params=params,
            )
            execution_time = time.time() - start_time

            self.logger.info(
                f"注文作成成功: {order['id']} ({execution_time:.3f}秒)",
                extra_data={
                    "order_id": order["id"],
                    "symbol": symbol,
                    "side": side,
                    "amount": amount,
                    "price": price,
                    "execution_time": execution_time,
                },
                discord_notify=True,
            )

            return order

        except ccxt.AuthenticationError as e:
            raise ExchangeAPIError(
                f"認証エラー: {e}",
                context={
                    "operation": "create_order",
                    "symbol": symbol,
                    "side": side,
                },
            )
        except ccxt.InsufficientFunds as e:
            raise ExchangeAPIError(
                f"残高不足: {e}",
                context={
                    "operation": "create_order",
                    "symbol": symbol,
                    "side": side,
                },
            )
        except ccxt.NetworkError as e:
            raise ExchangeAPIError(
                f"ネットワークエラー: {e}",
                context={
                    "operation": "create_order",
                    "symbol": symbol,
                    "side": side,
                },
            )
        except ccxt.ExchangeError as e:
            raise ExchangeAPIError(
                f"取引所エラー: {e}",
                context={
                    "operation": "create_order",
                    "symbol": symbol,
                    "side": side,
                },
            )
        except Exception as e:
            raise ExchangeAPIError(
                f"注文作成に失敗しました: {e}",
                context={
                    "operation": "create_order",
                    "symbol": symbol,
                    "side": side,
                },
            )

    def create_take_profit_order(
        self,
        entry_side: str,
        amount: float,
        take_profit_price: float,
        symbol: str = "BTC/JPY",
    ) -> Dict[str, Any]:
        """
        テイクプロフィット指値注文作成（Phase 33.1: 決済注文対応・両建て防止修正）

        Args:
            entry_side: エントリー方向（buy/sell）
            amount: 注文量（BTC）
            take_profit_price: 利確価格（JPY）
            symbol: 通貨ペア

        Returns:
            注文情報（order_id含む）

        Raises:
            ExchangeAPIError: 注文作成失敗時
        """
        # TP注文の方向：エントリーと逆方向（決済するため）
        tp_side = "sell" if entry_side.lower() == "buy" else "buy"

        # ✅ Phase 33.1修正：元のポジションと同じposition_sideで決済注文として作成
        entry_position_side = "long" if entry_side.lower() == "buy" else "short"

        self.logger.info(
            f"📈 テイクプロフィット決済注文作成: {tp_side} {amount:.4f} BTC @ {take_profit_price:.0f}円 (position_side={entry_position_side})",
            extra_data={
                "entry_side": entry_side,
                "tp_side": tp_side,
                "entry_position_side": entry_position_side,
                "amount": amount,
                "price": take_profit_price,
            },
        )

        return self.create_order(
            symbol=symbol,
            side=tp_side,
            order_type="limit",
            amount=amount,
            price=take_profit_price,
            is_closing_order=True,  # ✅ 決済注文フラグ
            entry_position_side=entry_position_side,  # ✅ エントリー時のposition_side
        )

    def create_stop_loss_order(
        self,
        entry_side: str,
        amount: float,
        stop_loss_price: float,
        symbol: str = "BTC/JPY",
    ) -> Dict[str, Any]:
        """
        ストップロス逆指値成行注文作成（Phase 38.7.1: stop対応・確実な損切り実行）

        Args:
            entry_side: エントリー方向（buy/sell）
            amount: 注文量（BTC）
            stop_loss_price: 損切りトリガー価格（JPY）
            symbol: 通貨ペア

        Returns:
            注文情報（order_id含む）

        Raises:
            ExchangeAPIError: 注文作成失敗時
        """
        # SL注文の方向：エントリーと逆方向（決済するため）
        sl_side = "sell" if entry_side.lower() == "buy" else "buy"

        # ✅ Phase 33.1修正：元のポジションと同じposition_sideで決済注文として作成
        entry_position_side = "long" if entry_side.lower() == "buy" else "short"

        # ✅ Phase 38.7.1: stop注文（逆指値成行）で確実な損切り実行
        # トリガー到達後は即座に成行注文として執行される（執行価格指定不要）
        self.logger.info(
            f"🛡️ ストップロス逆指値成行注文作成: {sl_side} {amount:.4f} BTC @ trigger={stop_loss_price:.0f}円 (position_side={entry_position_side})",
            extra_data={
                "entry_side": entry_side,
                "sl_side": sl_side,
                "entry_position_side": entry_position_side,
                "amount": amount,
                "trigger_price": stop_loss_price,
                "order_type": "stop",
            },
        )

        return self.create_order(
            symbol=symbol,
            side=sl_side,
            order_type="stop",  # ✅ Phase 38.7.1: 逆指値成行注文（stop）に変更
            amount=amount,
            price=None,  # ✅ stop注文には執行価格不要（成行執行）
            trigger_price=stop_loss_price,  # ✅ トリガー価格
            is_closing_order=True,  # ✅ 決済注文フラグ
            entry_position_side=entry_position_side,  # ✅ エントリー時のposition_side
        )

    async def cancel_order(self, order_id: str, symbol: str = "BTC/JPY") -> Dict[str, Any]:
        """
        注文キャンセル

        Args:
            order_id: 注文ID
            symbol: 通貨ペア

        Returns:
            キャンセル結果

        Raises:
            ExchangeAPIError: キャンセル失敗時.
        """
        try:
            if not self.api_key or not self.api_secret:
                raise ExchangeAPIError(
                    "注文キャンセルには認証が必要です",
                    context={"operation": "cancel_order"},
                )

            cancel_result = await self.exchange.cancel_order(order_id, symbol)

            self.logger.info(
                f"注文キャンセル成功: {order_id}",
                extra_data={"order_id": order_id, "symbol": symbol},
            )

            return cancel_result

        except ccxt.OrderNotFound:
            raise ExchangeAPIError(
                f"注文が見つかりません: {order_id}",
                context={"operation": "cancel_order", "order_id": order_id},
            )
        except ccxt.AuthenticationError as e:
            raise ExchangeAPIError(
                f"認証エラー: {e}",
                context={"operation": "cancel_order", "order_id": order_id},
            )
        except Exception as e:
            raise ExchangeAPIError(
                f"注文キャンセルに失敗しました: {e}",
                context={"operation": "cancel_order", "order_id": order_id},
            )

    async def fetch_order(self, order_id: str, symbol: str = "BTC/JPY") -> Dict[str, Any]:
        """
        注文状況確認

        Args:
            order_id: 注文ID
            symbol: 通貨ペア

        Returns:
            注文情報

        Raises:
            ExchangeAPIError: 取得失敗時.
        """
        try:
            if not self.api_key or not self.api_secret:
                raise ExchangeAPIError(
                    "注文確認には認証が必要です",
                    context={"operation": "fetch_order"},
                )

            order = await self.exchange.fetch_order(order_id, symbol)

            self.logger.debug(
                f"注文情報取得成功: {order_id} - {order['status']}",
                extra_data={
                    "order_id": order_id,
                    "status": order["status"],
                    "filled": order.get("filled", 0),
                    "remaining": order.get("remaining", 0),
                },
            )

            return order

        except ccxt.OrderNotFound:
            raise ExchangeAPIError(
                f"注文が見つかりません: {order_id}",
                context={"operation": "fetch_order", "order_id": order_id},
            )
        except ccxt.AuthenticationError as e:
            raise ExchangeAPIError(
                f"認証エラー: {e}",
                context={"operation": "fetch_order", "order_id": order_id},
            )
        except Exception as e:
            raise ExchangeAPIError(
                f"注文情報取得に失敗しました: {e}",
                context={"operation": "fetch_order", "order_id": order_id},
            )

    async def fetch_active_orders(
        self, symbol: str = "BTC/JPY", limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        アクティブな注文一覧取得（Phase 33.2: TP/SL配置確認用）

        CRIT-1 Fix: async/await対応

        Args:
            symbol: 通貨ペア
            limit: 取得する注文数（デフォルト100）

        Returns:
            アクティブな注文のリスト

        Raises:
            ExchangeAPIError: 取得失敗時
        """
        try:
            if not self.api_key or not self.api_secret:
                raise ExchangeAPIError(
                    "アクティブ注文取得には認証が必要です",
                    context={"operation": "fetch_active_orders"},
                )

            # ccxtのfetch_open_ordersを使用
            active_orders = await self.exchange.fetch_open_orders(symbol, limit=limit)

            self.logger.info(
                f"アクティブ注文取得成功: {len(active_orders)}件",
                extra_data={
                    "symbol": symbol,
                    "order_count": len(active_orders),
                },
            )

            # TP/SL注文の統計情報をログ出力
            tp_orders = [o for o in active_orders if o.get("type") == "take_profit"]
            sl_orders = [o for o in active_orders if o.get("type") == "stop_loss"]
            limit_orders = [o for o in active_orders if o.get("type") == "limit"]

            self.logger.info(
                f"📊 注文タイプ内訳: limit={len(limit_orders)}, TP={len(tp_orders)}, SL={len(sl_orders)}"
            )

            return active_orders

        except ccxt.AuthenticationError as e:
            raise ExchangeAPIError(
                f"認証エラー: {e}",
                context={"operation": "fetch_active_orders"},
            )
        except Exception as e:
            raise ExchangeAPIError(
                f"アクティブ注文取得に失敗しました: {e}",
                context={"operation": "fetch_active_orders", "symbol": symbol},
            )

    async def fetch_positions(self, symbol: str = "BTC/JPY") -> List[Dict[str, Any]]:
        """
        ポジション情報取得（信用取引）

        Args:
            symbol: 通貨ペア

        Returns:
            ポジション情報リスト

        Raises:
            ExchangeAPIError: 取得失敗時.
        """
        try:
            if not self.api_key or not self.api_secret:
                raise ExchangeAPIError(
                    "ポジション確認には認証が必要です",
                    context={"operation": "fetch_positions"},
                )

            positions = await self.exchange.fetch_positions([symbol])

            # 有効なポジションのみフィルタ
            active_positions = [pos for pos in positions if pos["contracts"] > 0]

            self.logger.debug(
                f"ポジション情報取得成功: {len(active_positions)}件",
                extra_data={
                    "symbol": symbol,
                    "active_positions": len(active_positions),
                },
            )

            return active_positions

        except ccxt.AuthenticationError as e:
            raise ExchangeAPIError(
                f"認証エラー: {e}",
                context={"operation": "fetch_positions", "symbol": symbol},
            )
        except Exception as e:
            raise ExchangeAPIError(
                f"ポジション情報取得に失敗しました: {e}",
                context={"operation": "fetch_positions", "symbol": symbol},
            )

    async def set_leverage(self, symbol: str, leverage: float) -> Dict[str, Any]:
        """
        レバレッジ設定（信用取引）

        Args:
            symbol: 通貨ペア
            leverage: レバレッジ倍率（1.0-2.0）

        Returns:
            設定結果

        Raises:
            ExchangeAPIError: 設定失敗時.
        """
        try:
            cfg = get_config()
            # HIGH-3 Fix: Config統合
            if not (cfg.exchange.leverage_min <= leverage <= cfg.exchange.leverage_max):
                raise ExchangeAPIError(
                    f"Bitbankでは1.0-2.0倍のレバレッジのみサポートされています: {leverage}",
                    context={"leverage": leverage},
                )

            if not self.api_key or not self.api_secret:
                raise ExchangeAPIError(
                    "レバレッジ設定には認証が必要です",
                    context={"operation": "set_leverage"},
                )

            result = await self.exchange.set_leverage(leverage, symbol)
            self.leverage = leverage  # 内部状態更新

            self.logger.info(
                f"レバレッジ設定成功: {symbol} {leverage}x",
                extra_data={"symbol": symbol, "leverage": leverage},
            )

            return result

        except ccxt.AuthenticationError as e:
            raise ExchangeAPIError(
                f"認証エラー: {e}",
                context={"operation": "set_leverage", "symbol": symbol},
            )
        except Exception as e:
            raise ExchangeAPIError(
                f"レバレッジ設定に失敗しました: {e}",
                context={
                    "operation": "set_leverage",
                    "symbol": symbol,
                    "leverage": leverage,
                },
            )

    async def get_market_info(self, symbol: str = "BTC/JPY") -> Dict[str, Any]:
        """
        市場情報取得

        CRIT-1 Fix: async/await対応

        Args:
            symbol: 通貨ペア

        Returns:
            市場情報（最小注文単位、手数料等）.
        """
        try:
            markets = await self.exchange.load_markets()
            market = markets.get(symbol)

            if not market:
                raise DataFetchError(
                    f"市場情報が見つかりません: {symbol}",
                    context={"symbol": symbol},
                )

            return {
                "id": market["id"],
                "symbol": market["symbol"],
                "base": market["base"],
                "quote": market["quote"],
                "precision": market["precision"],
                "limits": market["limits"],
                "fees": market.get("fees", {}),
                "active": market["active"],
            }

        except Exception as e:
            raise DataFetchError(
                f"市場情報取得に失敗しました: {symbol} - {e}",
                context={"symbol": symbol},
            )

    async def fetch_margin_status(self) -> Dict[str, Any]:
        """
        信用取引口座状況取得（Phase 35: バックテストモックデータ対応）

        Returns:
            信用取引口座の状況情報（保証金維持率含む）

        Raises:
            ExchangeAPIError: 取得失敗時
        """
        # Phase 35: バックテストモード時はモックデータ返却（API呼び出しスキップ）
        if self._backtest_mode:
            # 削除: 重複import get_threshold (line 1452)

            mock_enabled = get_threshold("backtest.mock_api_calls", True)
            if mock_enabled:
                self.logger.debug("🎯 バックテストモック: fetch_margin_status スキップ")
                return {
                    "margin_ratio": 500.0,  # 維持率500%（安全な値）
                    "available_balance": 10000.0,  # 利用可能残高10,000円
                    "used_margin": 0.0,  # 使用保証金0円
                    "unrealized_pnl": 0.0,  # 未実現損益0円
                    "margin_call_status": "safe",  # マージンコールなし
                    "raw_response": {"success": 1, "data": {"mock": True}},
                }

        try:
            if not self.api_key or not self.api_secret:
                raise ExchangeAPIError(
                    "信用取引口座状況取得には認証が必要です",
                    context={"operation": "fetch_margin_status"},
                )

            # ccxtの標準APIでは信用取引状況を取得できない場合があるため、
            # bitbank独自のprivate APIを直接呼び出す
            # Phase 37.2: GETメソッドで呼び出し（エラー20003修正）
            response = await self._call_private_api("/user/margin/status", method="GET")

            # 保証金維持率とリスク情報を含む完全な状況を返す
            margin_data = {
                "margin_ratio": response.get("data", {}).get("maintenance_margin_ratio"),
                "available_balance": response.get("data", {}).get("available_margin"),
                "used_margin": response.get("data", {}).get("used_margin"),
                "unrealized_pnl": response.get("data", {}).get("unrealized_pnl"),
                "margin_call_status": response.get("data", {}).get("margin_call_status"),
                "raw_response": response,
            }

            self.logger.info(
                f"📊 信用取引口座状況取得成功 - 維持率: {margin_data['margin_ratio']:.1f}%",
                extra_data={
                    "margin_ratio": margin_data["margin_ratio"],
                    "available_balance": margin_data["available_balance"],
                    "margin_call_status": margin_data["margin_call_status"],
                },
            )

            return margin_data

        except Exception as e:
            self.logger.error(f"信用取引口座状況取得失敗: {e}")
            raise ExchangeAPIError(
                f"信用取引口座状況取得に失敗しました: {e}",
                context={"operation": "fetch_margin_status"},
            )

    async def fetch_margin_positions(self, symbol: str = "BTC/JPY") -> List[Dict[str, Any]]:
        """
        信用建玉情報取得（Phase 27新機能・詳細ポジション情報）

        Args:
            symbol: 通貨ペア

        Returns:
            建玉情報リスト（ロング・ショート別）

        Raises:
            ExchangeAPIError: 取得失敗時
        """
        try:
            if not self.api_key or not self.api_secret:
                raise ExchangeAPIError(
                    "信用建玉情報取得には認証が必要です",
                    context={"operation": "fetch_margin_positions"},
                )

            # bitbank独自のprivate APIを直接呼び出し
            response = await self._call_private_api("/user/margin/positions")

            positions = []
            for position_data in response.get("data", {}).get("positions", []):
                position = {
                    "symbol": position_data.get("pair", symbol),
                    "side": position_data.get("position_side"),  # long/short
                    "amount": float(position_data.get("open_amount", 0)),
                    "average_price": float(position_data.get("average_price", 0)),
                    "unrealized_pnl": float(position_data.get("unrealized_pnl", 0)),
                    "margin_used": float(position_data.get("margin_used", 0)),
                    "losscut_price": float(position_data.get("losscut_price", 0)),
                    "raw_data": position_data,
                }
                positions.append(position)

            self.logger.debug(
                f"信用建玉情報取得成功: {len(positions)}件",
                extra_data={"symbol": symbol, "active_positions": len(positions)},
            )

            return positions

        except Exception as e:
            self.logger.error(f"信用建玉情報取得失敗: {e}")
            raise ExchangeAPIError(
                f"信用建玉情報取得に失敗しました: {e}",
                context={"operation": "fetch_margin_positions", "symbol": symbol},
            )

    async def _call_private_api(
        self, endpoint: str, params: Optional[Dict] = None, method: str = "POST"
    ) -> Dict[str, Any]:
        """
        bitbank private API直接呼び出し（Phase 37.2: GET/POST両対応）

        Args:
            endpoint: APIエンドポイント（例: '/user/margin/status'）
            params: リクエストパラメータ
            method: HTTPメソッド（"GET" or "POST"）

        Returns:
            API応答データ

        Raises:
            ExchangeAPIError: API呼び出し失敗時
        """
        import hashlib
        import hmac
        import json
        from urllib.parse import urlencode

        try:
            # bitbank API仕様に基づく認証署名生成
            base_url = "https://api.bitbank.cc/v1"
            url = f"{base_url}{endpoint}"

            # タイムスタンプとnonce
            timestamp = str(int(time.time() * 1000))
            nonce = timestamp

            # Phase 37.2: GET/POSTで署名ロジック分岐
            if method.upper() == "GET":
                # GETリクエスト署名: nonce + endpoint (+ query parameters)
                # 現時点でquery parametersは使用しないため、endpointのみ
                message = f"{nonce}{endpoint}"
                body = None
            else:
                # POSTリクエスト署名: nonce + request body
                if params:
                    body = json.dumps(params, separators=(",", ":"))
                else:
                    body = ""
                message = f"{nonce}{body}"

            # 署名生成
            signature = hmac.new(
                self.api_secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
            ).hexdigest()

            # ヘッダー作成
            headers = {
                "ACCESS-KEY": self.api_key,
                "ACCESS-NONCE": nonce,
                "ACCESS-SIGNATURE": signature,
            }

            # GETリクエストにはContent-Type不要
            if method.upper() == "POST":
                headers["Content-Type"] = "application/json"

            # SSL設定（セキュア設定）
            import ssl

            ssl_context = ssl.create_default_context()

            # API呼び出し実行
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                timeout = aiohttp.ClientTimeout(total=30.0)

                # Phase 37.2: GET/POSTメソッド分岐
                if method.upper() == "GET":
                    async with session.get(url, headers=headers, timeout=timeout) as response:
                        result = await response.json()
                else:
                    async with session.post(
                        url, headers=headers, data=body, timeout=timeout
                    ) as response:
                        result = await response.json()

                if result.get("success") == 1:
                    return result
                else:
                    error_code = result.get("data", {}).get("code", "unknown")
                    raise ExchangeAPIError(
                        f"bitbank API エラー: {error_code}",
                        context={"endpoint": endpoint, "method": method, "error_code": error_code},
                    )

        except aiohttp.ClientError as e:
            raise ExchangeAPIError(
                f"ネットワークエラー: {e}", context={"endpoint": endpoint, "method": method}
            )
        except Exception as e:
            raise ExchangeAPIError(
                f"private API呼び出し失敗: {e}", context={"endpoint": endpoint, "method": method}
            )

    def get_stats(self) -> Dict[str, Any]:
        """統計情報取得."""
        return {
            "authenticated": bool(self.api_key and self.api_secret),
            "margin_mode": True,
            "leverage": self.leverage,
            "exchange_id": (self.exchange.id if hasattr(self, "exchange") else None),
            "rate_limit": (
                getattr(self.exchange, "rateLimit", None) if hasattr(self, "exchange") else None
            ),
        }


# グローバルクライアント
_bitbank_client: Optional[BitbankClient] = None


def get_bitbank_client(force_recreate: bool = False, leverage: float = 1.0) -> BitbankClient:
    """グローバルクライアント取得."""
    global _bitbank_client

    if _bitbank_client is None or force_recreate:
        _bitbank_client = BitbankClient(leverage=leverage)

    return _bitbank_client


def create_margin_client(
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    leverage: float = 1.0,
) -> BitbankClient:
    """新しい信用取引クライアント作成."""
    return BitbankClient(api_key=api_key, api_secret=api_secret, leverage=leverage)

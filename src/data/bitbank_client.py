"""
Bitbank 信用取引専用APIクライアント

ccxtライブラリ + 直接API実装によるBitbank信用取引クライアント。
"""

import asyncio
import os
import time
from typing import Any, Dict, List, Optional, Union

import aiohttp
import ccxt

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

        # Cloud Run環境変数読み込み状況をデバッグ
        import hashlib

        if self.api_key:
            key_hash = hashlib.md5(self.api_key.encode()).hexdigest()[:8]
            self.logger.info(
                f"🔑 BITBANK_API_KEY読み込み確認: 存在={bool(self.api_key)}, 長さ={len(self.api_key)}, ハッシュ={key_hash}"
            )
        else:
            self.logger.error("❌ BITBANK_API_KEY読み込み失敗: 環境変数が空またはNone")

        if self.api_secret:
            secret_hash = hashlib.md5(self.api_secret.encode()).hexdigest()[:8]
            self.logger.info(
                f"🔐 BITBANK_API_SECRET読み込み確認: 存在={bool(self.api_secret)}, 長さ={len(self.api_secret)}, ハッシュ={secret_hash}"
            )
        else:
            self.logger.error("❌ BITBANK_API_SECRET読み込み失敗: 環境変数が空またはNone")

        # レバレッジ検証
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
        # Phase 88 M2: rateLimit を thresholds.yaml 参照に統一（ハードコード 200 解消）
        ccxt_rate_limit_ms = int(get_threshold("exchange.ccxt_rate_limit_ms", 200))
        try:
            self.exchange = ccxt.bitbank(
                {
                    "apiKey": self.api_key,
                    "secret": self.api_secret,
                    "sandbox": False,  # 本番環境
                    "rateLimit": ccxt_rate_limit_ms,  # Phase 88 M2: 設定参照（bitbank APIは秒間制限ベース・5回/秒に収まる）
                    "enableRateLimit": True,
                    "timeout": 30000,  # 30秒タイムアウト
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

        # Phase 89-δ: WebSocket クライアント（遅延初期化・実機接続は connect_websocket() 呼び出し時）
        self._ws_task = None
        self._ws_client = None

    # ========================================
    # Phase 89-δ: WebSocket ライフサイクル（最小実装）
    # ========================================

    def get_primary_symbol(self) -> str:
        """Phase 89-δ: thresholds.yaml の `exchange.primary_symbol` を返す（後方互換: 既存 `symbol` も参照）."""
        return get_threshold(
            "exchange.primary_symbol",
            get_threshold("exchange.symbol", "BTC/JPY"),
        )

    def get_websocket_client(self):
        """Phase 89-δ: WebSocket クライアントを取得（シングルトン）.

        Returns:
            BitbankWebSocketClient or None（websockets 未インストール時）
        """
        if self._ws_client is None:
            try:
                from .bitbank_websocket_client import get_bitbank_websocket_client

                self._ws_client = get_bitbank_websocket_client()
            except ImportError:
                self.logger.warning("Phase 89-δ websockets 未インストール → WebSocket 無効")
                return None
        return self._ws_client

    async def connect_websocket(self) -> bool:
        """Phase 89-δ: WebSocket 接続を非同期で開始（既存 task があれば何もしない）.

        Returns:
            True: 接続タスク起動成功 / False: ライブラリ未インストール or 既起動
        """
        ws = self.get_websocket_client()
        if ws is None:
            return False
        if self._ws_task is not None and not self._ws_task.done():
            return False  # 既に起動中

        self._ws_task = asyncio.create_task(ws.connect())
        self.logger.info("Phase 89-δ WebSocket 接続タスク起動")
        return True

    async def disconnect_websocket(self) -> None:
        """Phase 89-δ: WebSocket 接続停止."""
        if self._ws_client is not None:
            await self._ws_client.disconnect()
        if self._ws_task is not None and not self._ws_task.done():
            self._ws_task.cancel()
            try:
                await self._ws_task
            except Exception:
                pass
        self._ws_task = None

    def test_connection(self) -> bool:
        """API接続テスト."""
        try:
            # 公開API（認証不要）でテスト（設定から取得）
            try:
                config = get_config()
                symbol = config.exchange.symbol
            except Exception:
                symbol = "BTC/JPY"  # フォールバック

            ticker = self.exchange.fetch_ticker(symbol)
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
            import asyncio
            from datetime import datetime

            # 現在年を取得
            current_year = datetime.now().year

            try:
                # Phase 59.5 Fix: 年跨ぎ対応 - 現在年 + 前年を取得してマージ
                ohlcv_current = await self.fetch_ohlcv_4h_direct(symbol=symbol, year=current_year)

                # Phase 59.5: データが不足している場合、前年も取得
                if len(ohlcv_current) < limit:
                    self.logger.debug(
                        f"📊 4時間足年跨ぎ取得: 現在年{len(ohlcv_current)}件 < limit{limit}件 → 前年も取得"
                    )
                    try:
                        ohlcv_prev = await self.fetch_ohlcv_4h_direct(
                            symbol=symbol, year=current_year - 1
                        )
                        # 時系列順にマージ（前年 + 現在年）
                        ohlcv = ohlcv_prev + ohlcv_current
                        self.logger.info(
                            f"📊 4時間足年跨ぎ取得成功: {current_year - 1}年={len(ohlcv_prev)}件 + "
                            f"{current_year}年={len(ohlcv_current)}件 = 合計{len(ohlcv)}件"
                        )
                    except Exception as e:
                        self.logger.warning(f"前年データ取得失敗: {e} - 現在年のみ使用")
                        ohlcv = ohlcv_current
                else:
                    ohlcv = ohlcv_current

                # Phase 51.5 Fix: limit適用前の件数ログ
                original_count = len(ohlcv)

                # limitが指定されている場合は最新データに制限
                if limit and len(ohlcv) > limit:
                    ohlcv = ohlcv[-limit:]
                    self.logger.info(
                        f"📊 4時間足limit適用 - "
                        f"取得件数={original_count}件, "
                        f"limit={limit}件, "
                        f"適用後={len(ohlcv)}件"
                    )
                else:
                    self.logger.info(
                        f"📊 4時間足limit適用なし - "
                        f"取得件数={original_count}件 (limit={limit}件)"
                    )

                # Phase 51.5 Fix: 最小行数チェック（戦略要求20行未満ならエラー）
                min_required_rows = 20
                if len(ohlcv) < min_required_rows:
                    self.logger.warning(
                        f"⚠️ 4時間足直接API取得件数不足: {len(ohlcv)}件 < {min_required_rows}件必要 "
                        f"- ccxtリトライ"
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
            import asyncio
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
                for days_ago in range(days_needed):
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
                        f"📊 15分足limit適用 - "
                        f"取得件数={original_count}件, "
                        f"limit={limit}件, "
                        f"適用後={len(all_ohlcv)}件"
                    )
                else:
                    self.logger.info(
                        f"📊 15分足limit適用なし - "
                        f"取得件数={original_count}件 (limit={limit}件)"
                    )

                # Phase 51.5-C: 最小行数チェック（戦略要求20行未満ならエラー）
                min_required_rows = 20
                if len(all_ohlcv) < min_required_rows:
                    self.logger.warning(
                        f"⚠️ 15分足直接API取得件数不足: {len(all_ohlcv)}件 < {min_required_rows}件必要 "
                        f"- ccxtリトライ"
                    )
                    raise ValueError(
                        f"データ不足: {len(all_ohlcv)}件 < {min_required_rows}件（戦略要求最小行数）"
                    )

                self.logger.info(
                    f"✅ Phase 51.5-C: 15分足直接API実装成功 - "
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
        min_required_rows = 20  # 戦略要求最小行数

        for attempt in range(max_retries):
            try:
                self.logger.debug(
                    f"OHLCV データ取得開始（試行{attempt + 1}/{max_retries}）: "
                    f"{symbol} {timeframe} limit={limit}"
                )

                # Phase 51.5-C Fix: タイムアウト設定（既存のexchange設定を利用）
                # ccxtのexchangeインスタンスは既にtimeout設定済み（30秒）
                ohlcv = self.exchange.fetch_ohlcv(
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
                        import asyncio

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
                    import asyncio

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

    async def _fetch_candlestick_direct(
        self,
        symbol: str,
        period: str,
        param: str,
        label: str,
    ) -> List[List[Union[int, float]]]:
        """
        Bitbank candlestick API共通実装（リトライ・OHLCV変換）

        Args:
            symbol: 通貨ペア（例: "BTC/JPY"）
            period: ローソク足種別（"4hour" or "15min"）
            param: APIパスパラメータ（年 "2025" or 日付 "20251104"）
            label: ログ用ラベル（"4時間足" or "15分足"）

        Returns:
            OHLCV データリスト [[timestamp, open, high, low, close, volume], ...]

        Raises:
            DataFetchError: データ取得失敗時
        """
        import json
        import ssl

        max_retries = 3
        last_exception = None
        pair = symbol.lower().replace("/", "_")  # BTC/JPY -> btc_jpy
        url = f"https://public.bitbank.cc/{pair}/candlestick/{period}/{param}"

        for attempt in range(max_retries):
            try:
                self.logger.debug(
                    f"{label}直接API取得開始: {symbol} {param} (試行 {attempt + 1}/{max_retries})"
                )

                ssl_context = ssl.create_default_context()
                connector = aiohttp.TCPConnector(ssl=ssl_context)
                async with aiohttp.ClientSession(connector=connector) as session:
                    timeout = aiohttp.ClientTimeout(
                        total=30.0,
                        connect=5.0,
                        sock_read=25.0,
                    )

                    async with session.get(url, timeout=timeout) as response:
                        content_length = response.headers.get("Content-Length")
                        if content_length:
                            self.logger.debug(
                                f"📊 {label}レスポンスサイズ: {int(content_length) / 1024:.1f}KB"
                            )

                        text = await response.text()
                        self.logger.debug(f"📊 {label}テキストサイズ: {len(text) / 1024:.1f}KB")

                        data = json.loads(text)

                        self.logger.debug(
                            f"📊 {label}API Response確認 - "
                            f"success={data.get('success')}, "
                            f"has_data={bool(data.get('data'))}, "
                            f"has_candlestick={bool(data.get('data', {}).get('candlestick'))}"
                        )

                        if data.get("success") == 1:
                            candlestick_data = data["data"]["candlestick"][0]["ohlcv"]

                            if not candlestick_data:
                                raise DataFetchError(
                                    f"{label}データが空です: {symbol} {param}",
                                    context={"symbol": symbol, "param": param},
                                )

                            self.logger.debug(
                                f"📊 {label}Raw Candlestick件数: {len(candlestick_data)}件"
                            )

                            # Bitbank形式→ccxt形式変換
                            # Bitbank: [open, high, low, close, volume, timestamp_ms]
                            # ccxt:    [timestamp_ms, open, high, low, close, volume]
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

                            self.logger.info(
                                f"✅ {label}直接API取得成功: {len(ohlcv_data)}件 "
                                f"(raw={len(candlestick_data)}件)",
                                extra_data={
                                    "symbol": symbol,
                                    "param": param,
                                    "count": len(ohlcv_data),
                                    "method": f"direct_api_{period}",
                                    "attempt": attempt + 1,
                                },
                            )

                            return ohlcv_data

                        else:
                            error_code = data.get("data", {}).get("code", "unknown")
                            raise DataFetchError(
                                f"Bitbank API エラー（{label}）: {error_code}",
                                context={
                                    "symbol": symbol,
                                    "param": param,
                                    "error_code": error_code,
                                },
                            )

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff: 1秒, 2秒, 4秒
                    self.logger.warning(
                        f"⚠️ {label}取得失敗（試行{attempt + 1}/{max_retries}）: "
                        f"{type(e).__name__}: {e} - {wait_time}秒後にリトライ"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(
                        f"❌ {label}取得失敗（全{max_retries}回試行失敗）: "
                        f"{type(e).__name__}: {e}"
                    )
                    raise DataFetchError(
                        f"ネットワークエラー（{label}・{max_retries}回リトライ失敗）: {e}",
                        context={
                            "symbol": symbol,
                            "param": param,
                            "attempts": max_retries,
                        },
                    )
            except Exception as e:
                last_exception = e
                self.logger.error(f"❌ {label}取得予期しないエラー: {type(e).__name__}: {e}")
                raise DataFetchError(
                    f"{label}データ取得失敗: {e}",
                    context={
                        "symbol": symbol,
                        "param": param,
                        "attempt": attempt + 1,
                    },
                )

        raise DataFetchError(
            f"{label}データ取得失敗（全{max_retries}回試行完了・原因不明）",
            context={
                "symbol": symbol,
                "param": param,
                "last_exception": str(last_exception),
            },
        )

    async def fetch_ohlcv_4h_direct(
        self,
        symbol: str = "BTC/JPY",
        year: int = 2025,
    ) -> List[List[Union[int, float]]]:
        """4時間足データを直接API実装で取得（ccxt制約回避）"""
        return await self._fetch_candlestick_direct(symbol, "4hour", str(year), "4時間足")

    async def fetch_ohlcv_15m_direct(
        self,
        symbol: str = "BTC/JPY",
        date: str = "20251104",
    ) -> List[List[Union[int, float]]]:
        """15分足データを直接API実装で取得（ccxt制約回避）"""
        return await self._fetch_candlestick_direct(symbol, "15min", date, "15分足")

    def fetch_ticker(self, symbol: str = "BTC/JPY") -> Dict[str, Any]:
        """
        ティッカー情報取得

        Phase 88 I5 候補: 同一 symbol への高頻度呼び出しを 60-120 秒メモリキャッシュ化
        することで Egress を月 ¥20-50 削減可能。ただし新規キャッシュ層構築が必要なため
        Phase 89 のキャッシュ機構整備（OFI 特徴量導入時の WebSocket 化）と同時実施予定。

        Args:
            symbol: 通貨ペア

        Returns:
            ティッカー情報.
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)

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

    def fetch_order_book(self, symbol: str = "BTC/JPY", limit: int = 20) -> Dict[str, Any]:
        """
        板情報取得（Phase 33: スマート注文機能用）

        Args:
            symbol: 通貨ペア
            limit: 取得する板の深さ

        Returns:
            板情報（bids: 買い板, asks: 売り板）
        """
        try:
            orderbook = self.exchange.fetch_order_book(symbol, limit)

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

    def fetch_balance(self) -> Dict[str, Any]:
        """
        残高情報取得（Phase 35: バックテストモックデータ対応）

        Returns:
            信用取引残高情報.
        """
        # Phase 35: バックテストモード時はモックデータ返却（API呼び出しスキップ）
        if self._backtest_mode:
            from ..core.config import get_threshold

            mock_enabled = get_threshold("backtest.mock_api_calls", True)
            if mock_enabled:
                # Phase 55.10: バックテスト残高をmode_balancesから取得
                backtest_balance = get_threshold("mode_balances.backtest.initial_balance", 100000.0)
                self.logger.debug(
                    f"🎯 バックテストモック: fetch_balance スキップ（残高: ¥{backtest_balance:,.0f}）"
                )
                return {
                    "JPY": {"total": backtest_balance, "free": backtest_balance, "used": 0.0},
                    "BTC": {"total": 0.0, "free": 0.0, "used": 0.0},
                    "info": {"mock": True},
                }

        try:
            if not self.api_key or not self.api_secret:
                raise ExchangeAPIError(
                    "残高取得には認証が必要です",
                    context={"operation": "fetch_balance"},
                )

            balance = self.exchange.fetch_balance()

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

    def create_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        amount: float,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        is_closing_order: bool = False,
        entry_position_side: Optional[str] = None,
        post_only: bool = False,  # Phase 62.9: Maker戦略用
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
                # bitbank API仕様: 整数文字列を期待
                params["trigger_price"] = str(int(trigger_price))
                self.logger.info(
                    f"🎯 逆指値注文トリガー設定: {trigger_price:.0f}円",
                    extra_data={"trigger_price": trigger_price, "order_type": order_type},
                )

            # Phase 37.5.2: stop_limit注文の場合、執行価格もparams内に明示的に設定
            if order_type == "stop_limit" and price is not None:
                params["price"] = str(int(price))  # bitbank APIは整数文字列を期待
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

            # Phase 62.9: post_onlyパラメータ追加（Maker戦略）
            if post_only and order_type == "limit":
                params["postOnly"] = True
                self.logger.info(
                    f"📡 Phase 62.9: post_only注文 - {side} {amount:.4f} BTC @ {price:.0f}円"
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
                    f"📋 stop_limit注文パラメータ確認",
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
            order = self.exchange.create_order(
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
        except ccxt.InvalidOrder as e:
            # Phase 62.9: post_onlyキャンセル検知
            error_str = str(e).lower()
            if post_only and (
                "post_only" in error_str
                or "would immediately" in error_str
                or "postonly" in error_str
            ):
                from src.core.exceptions import PostOnlyCancelledException

                raise PostOnlyCancelledException(
                    f"post_only注文キャンセル: {e}",
                    symbol=symbol,
                    price=price,
                )
            raise ExchangeAPIError(
                f"無効な注文: {e}",
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
        post_only: bool = False,  # Phase 62.10: Maker戦略用
    ) -> Dict[str, Any]:
        """
        テイクプロフィット指値注文作成（Phase 61.3: take_profitタイプ対応）

        Phase 61.3:
        - use_native_tp_sl=true: bitbank API直接呼び出し（type="take_profit"）
        - use_native_tp_sl=false: 従来のlimit注文

        Phase 62.10:
        - post_only=true: limit + post_only注文（Maker約定のみ）
        - post_only=false: 従来のtake_profit/limit注文

        bitbank UI表示:
        - type="take_profit": 「利確」と表示
        - type="limit": 「指値」と表示

        Args:
            entry_side: エントリー方向（buy/sell）
            amount: 注文量（BTC）
            take_profit_price: 利確価格（JPY）
            symbol: 通貨ペア
            post_only: Maker約定のみを許可（Phase 62.10追加）

        Returns:
            注文情報（order_id含む）

        Raises:
            ExchangeAPIError: 注文作成失敗時
            PostOnlyCancelledException: post_only注文がキャンセルされた場合
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
                "post_only": post_only,
            },
        )

        # Phase 62.10: Maker戦略（post_only）優先
        if post_only:
            self.logger.info(
                f"📡 Phase 62.10: TP Maker戦略 - limit + post_only注文 "
                f"@ {take_profit_price:.0f}円"
            )
            return self.create_order(
                symbol=symbol,
                side=tp_side,
                order_type="limit",
                amount=amount,
                price=take_profit_price,
                is_closing_order=True,
                entry_position_side=entry_position_side,
                post_only=True,
            )

        # Phase 61.3: take_profitタイプ使用設定を確認
        use_native_tp_sl = get_threshold("position_management.take_profit.use_native_type", False)

        if use_native_tp_sl:
            # Phase 61.3: bitbank API直接呼び出し（take_profitタイプ）
            try:
                import asyncio

                self.logger.info(
                    f"📡 Phase 61.3: take_profitタイプで注文作成（UI「利確」表示期待）"
                )
                # 同期コンテキストから非同期メソッドを呼び出し
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 既に実行中のイベントループ内の場合
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run,
                            self._create_order_direct(
                                symbol=symbol,
                                side=tp_side,
                                order_type="take_profit",
                                amount=amount,
                                price=take_profit_price,
                                trigger_price=take_profit_price,  # Phase 61.6: TPにはtrigger_price必須
                                is_closing_order=True,
                                entry_position_side=entry_position_side,
                            ),
                        )
                        return future.result()
                else:
                    return asyncio.run(
                        self._create_order_direct(
                            symbol=symbol,
                            side=tp_side,
                            order_type="take_profit",
                            amount=amount,
                            price=take_profit_price,
                            trigger_price=take_profit_price,  # Phase 61.6: TPにはtrigger_price必須
                            is_closing_order=True,
                            entry_position_side=entry_position_side,
                        )
                    )
            except Exception as e:
                self.logger.warning(f"⚠️ Phase 61.3: take_profitタイプ失敗 - フォールバック: {e}")
                # フォールバック: 従来のlimit注文

        # 従来方式: limit注文（type="limit"）
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
        order_type: str = "stop",
        limit_price: float = None,
    ) -> Dict[str, Any]:
        """
        ストップロス注文作成（Phase 61.3: stop_lossタイプ対応）

        Phase 61.3:
        - use_native_tp_sl=true: bitbank API直接呼び出し（type="stop_loss"）
        - use_native_tp_sl=false: 従来のstop/stop_limit注文

        bitbank UI表示:
        - type="stop_loss": 「損切り」と表示
        - type="stop"/"stop_limit": 「逆指値」と表示

        Args:
            entry_side: エントリー方向（buy/sell）
            amount: 注文量（BTC）
            stop_loss_price: 損切りトリガー価格（JPY）
            symbol: 通貨ペア
            order_type: "stop"（成行）or "stop_limit"（指値）※use_native_tp_sl=false時のみ
            limit_price: 指値価格（stop_limit時のみ必須）

        Returns:
            注文情報（order_id含む）

        Raises:
            ExchangeAPIError: 注文作成失敗時
        """
        # SL注文の方向：エントリーと逆方向（決済するため）
        sl_side = "sell" if entry_side.lower() == "buy" else "buy"

        # ✅ Phase 33.1修正：元のポジションと同じposition_sideで決済注文として作成
        entry_position_side = "long" if entry_side.lower() == "buy" else "short"

        self.logger.info(
            f"🛡️ ストップロス注文作成: {sl_side} {amount:.4f} BTC @ trigger={stop_loss_price:.0f}円 (position_side={entry_position_side})",
            extra_data={
                "entry_side": entry_side,
                "sl_side": sl_side,
                "entry_position_side": entry_position_side,
                "amount": amount,
                "trigger_price": stop_loss_price,
            },
        )

        # Phase 61.3: stop_lossタイプ使用設定を確認
        use_native_tp_sl = get_threshold("position_management.stop_loss.use_native_type", False)

        if use_native_tp_sl:
            # Phase 61.3: bitbank API直接呼び出し（stop_lossタイプ）
            try:
                import asyncio

                # stop_lossタイプでは、priceは指値約定価格（トリガー価格ではない）
                # トリガー価格はtrigger_priceパラメータで指定
                sl_limit_price = limit_price if limit_price else stop_loss_price

                self.logger.info(
                    f"📡 Phase 61.3: stop_lossタイプで注文作成（UI「損切り」表示期待）"
                )

                # 同期コンテキストから非同期メソッドを呼び出し
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run,
                            self._create_order_direct(
                                symbol=symbol,
                                side=sl_side,
                                order_type="stop_loss",
                                amount=amount,
                                price=sl_limit_price,
                                trigger_price=stop_loss_price,
                                is_closing_order=True,
                                entry_position_side=entry_position_side,
                            ),
                        )
                        return future.result()
                else:
                    return asyncio.run(
                        self._create_order_direct(
                            symbol=symbol,
                            side=sl_side,
                            order_type="stop_loss",
                            amount=amount,
                            price=sl_limit_price,
                            trigger_price=stop_loss_price,
                            is_closing_order=True,
                            entry_position_side=entry_position_side,
                        )
                    )
            except Exception as e:
                self.logger.warning(f"⚠️ Phase 61.3: stop_lossタイプ失敗 - フォールバック: {e}")
                # フォールバック: 従来のstop/stop_limit注文

        # 従来方式: stop/stop_limit注文
        if order_type == "stop_limit":
            if limit_price is None:
                raise ValueError("stop_limit注文にはlimit_priceが必須です")

            self.logger.info(
                f"🛡️ ストップロス逆指値指値注文作成: {sl_side} {amount:.4f} BTC @ trigger={stop_loss_price:.0f}円, limit={limit_price:.0f}円",
                extra_data={
                    "order_type": "stop_limit",
                    "trigger_price": stop_loss_price,
                    "limit_price": limit_price,
                },
            )

            return self.create_order(
                symbol=symbol,
                side=sl_side,
                order_type="stop_limit",
                amount=amount,
                price=limit_price,
                trigger_price=stop_loss_price,
                is_closing_order=True,
                entry_position_side=entry_position_side,
            )
        else:
            # 従来のstop（成行）注文
            self.logger.info(
                f"🛡️ ストップロス逆指値成行注文作成: {sl_side} {amount:.4f} BTC @ trigger={stop_loss_price:.0f}円",
                extra_data={
                    "order_type": "stop",
                    "trigger_price": stop_loss_price,
                },
            )

            return self.create_order(
                symbol=symbol,
                side=sl_side,
                order_type="stop",
                amount=amount,
                price=None,
                trigger_price=stop_loss_price,
                is_closing_order=True,
                entry_position_side=entry_position_side,
            )

    def cancel_order(self, order_id: str, symbol: str = "BTC/JPY") -> Dict[str, Any]:
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

            cancel_result = self.exchange.cancel_order(order_id, symbol)

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

    def fetch_order(self, order_id: str, symbol: str = "BTC/JPY") -> Dict[str, Any]:
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

            order = self.exchange.fetch_order(order_id, symbol)

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

    def fetch_active_orders(
        self, symbol: str = "BTC/JPY", limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        アクティブな注文一覧取得（Phase 33.2: TP/SL配置確認用）

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
            active_orders = self.exchange.fetch_open_orders(symbol, limit=limit)

            self.logger.info(
                f"アクティブ注文取得成功: {len(active_orders)}件",
                extra_data={
                    "symbol": symbol,
                    "order_count": len(active_orders),
                },
            )

            # TP/SL注文の統計情報をログ出力
            # Phase 59.5 Fix: CCXTはstop_loss/take_profitではなくstop/limitを返す
            # - limit: エントリー指値注文 または TP注文（区別不可）
            # - stop/stop_limit: SL注文
            limit_orders = [o for o in active_orders if o.get("type") == "limit"]
            sl_orders = [o for o in active_orders if o.get("type") in ["stop", "stop_limit"]]

            self.logger.info(f"📊 注文タイプ内訳: limit={len(limit_orders)}, stop={len(sl_orders)}")

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

    def get_market_info(self, symbol: str = "BTC/JPY") -> Dict[str, Any]:
        """
        市場情報取得

        Args:
            symbol: 通貨ペア

        Returns:
            市場情報（最小注文単位、手数料等）.
        """
        try:
            markets = self.exchange.load_markets()
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
            from ..core.config import get_threshold

            mock_enabled = get_threshold("backtest.mock_api_calls", True)
            if mock_enabled:
                # Phase 55.10: バックテスト残高をmode_balancesから取得
                backtest_balance = get_threshold("mode_balances.backtest.initial_balance", 100000.0)
                self.logger.debug(
                    f"🎯 バックテストモック: fetch_margin_status スキップ（残高: ¥{backtest_balance:,.0f}）"
                )
                return {
                    "margin_ratio": 500.0,  # 維持率500%（安全な値）
                    "available_balance": backtest_balance,  # Phase 55.10: mode_balancesから取得
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
            # Phase 53.14: APIフィールド名修正・計算方式追加
            data = response.get("data", {})

            # Phase 53.14: 維持率計算（ポジションがある場合のみ計算可能）
            # API仕様: total_margin_balance_percentage はポジションなし時にnull
            raw_margin_ratio = data.get("total_margin_balance_percentage")
            total_margin_balance = float(data.get("total_margin_balance") or 0)
            maintenance_margin = float(data.get("total_position_maintenance_margin") or 0)

            if raw_margin_ratio is not None:
                # APIが値を返した場合はそれを使用
                try:
                    margin_ratio = float(raw_margin_ratio)
                except (ValueError, TypeError):
                    self.logger.warning(
                        f"⚠️ margin_ratio型変換失敗: {raw_margin_ratio}, 計算方式使用"
                    )
                    margin_ratio = 500.0
            elif maintenance_margin > 0:
                # ポジションがあるが維持率がnullの場合は計算
                margin_ratio = (total_margin_balance / maintenance_margin) * 100
                self.logger.info(
                    f"📊 Phase 53.14: 維持率計算 - "
                    f"残高={total_margin_balance:.0f}円 / 必要証拠金={maintenance_margin:.0f}円 "
                    f"= {margin_ratio:.1f}%"
                )
            else:
                # Phase 58.3: ポジションがない場合（正常）
                # 500%は安全なデフォルト値だが、ポジションなしを明示的にログ出力
                margin_ratio = 500.0
                self.logger.info(
                    "📊 Phase 58.3: ポジションなし（維持率=500%デフォルト） "
                    "- 実際のポジション確認にはfetch_margin_positions()を使用"
                )

            margin_data = {
                "margin_ratio": margin_ratio,
                "available_balance": total_margin_balance,
                "used_margin": maintenance_margin,
                "unrealized_pnl": float(data.get("margin_position_profit_loss") or 0),
                "margin_call_status": data.get("status"),
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
            # Phase 58.4: GETメソッドで呼び出し（エラー20003修正）
            response = await self._call_private_api("/user/margin/positions", method="GET")

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

    async def has_open_positions(self, symbol: str = "BTC/JPY") -> bool:
        """
        Phase 58.3: 実ポジションがあるかどうかを確認

        Args:
            symbol: 通貨ペア

        Returns:
            True: ポジションあり, False: ポジションなし
        """
        try:
            positions = await self.fetch_margin_positions(symbol)
            has_positions = len(positions) > 0 and any(p.get("amount", 0) > 0 for p in positions)
            self.logger.debug(
                f"📊 Phase 58.3: ポジション確認 - {symbol}: {'あり' if has_positions else 'なし'}"
            )
            return has_positions
        except Exception as e:
            self.logger.warning(f"⚠️ Phase 58.3: ポジション確認失敗: {e}")
            return False  # エラー時は安全側（ポジションなしと仮定）

    async def _create_order_direct(
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
        Phase 61.3: bitbank APIを直接呼び出す注文作成（ccxt非対応タイプ用）

        take_profit / stop_loss タイプはccxtがサポートしていないため、
        _call_private_api()を使用して直接注文する。

        bitbank API仕様参照:
        - エンドポイント: POST /user/spot/order
        - typeパラメータ: "limit", "market", "stop", "stop_limit", "take_profit", "stop_loss"
        - take_profit/stop_lossではamountがオプション（ポジション全量決済）
        - パラメータは全て文字列型

        Args:
            symbol: 通貨ペア（例: "BTC/JPY"）
            side: 売買方向（"buy" / "sell"）
            order_type: 注文タイプ（"take_profit" / "stop_loss"）
            amount: 注文量（BTC）
            price: 指値価格（JPY・take_profitとstop_lossで必須）
            trigger_price: トリガー価格（JPY・stop_lossで必須）
            is_closing_order: 決済注文フラグ
            entry_position_side: エントリー時のposition_side（"long" / "short"）

        Returns:
            注文情報（id, status等を含む）

        Raises:
            ExchangeAPIError: 注文作成失敗時
        """
        try:
            pair = symbol.lower().replace("/", "_")

            # Phase 86: stop型注文の trigger_price 必須検証
            stop_types = ("stop", "stop_limit", "stop_loss", "take_profit", "take_profit_limit")
            if order_type in stop_types and order_type not in ("take_profit",):
                # take_profit は trigger_price 任意（priceのみで動く場合あり）
                # stop / stop_loss は必須
                if order_type in ("stop", "stop_limit", "stop_loss"):
                    if trigger_price is None or trigger_price <= 0:
                        raise ExchangeAPIError(
                            f"Phase 86: stop型注文には trigger_price 必須 "
                            f"(type={order_type}, trigger_price={trigger_price})",
                            context={
                                "symbol": symbol,
                                "side": side,
                                "order_type": order_type,
                                "amount": amount,
                            },
                        )

            # bitbank API仕様: パラメータは全て文字列型
            params = {
                "pair": pair,
                "side": side,
                "type": order_type,
            }

            # amount: take_profit/stop_lossではオプション（明示的に指定する方が安全）
            if amount is not None and amount > 0:
                params["amount"] = str(amount)

            # 価格設定（整数文字列）
            if price is not None:
                params["price"] = str(int(price))

            # トリガー価格設定（stop_loss用・整数文字列）
            if trigger_price is not None:
                params["trigger_price"] = str(int(trigger_price))

            # 信用取引パラメータ: position_side（"long" / "short"）
            # bitbank API仕様: 信用取引時のみ有効
            if entry_position_side:
                params["position_side"] = entry_position_side

            self.logger.info(
                f"📡 Phase 61.3: 直接API注文作成 - type={order_type}, side={side}, "
                f"amount={amount:.6f} BTC, price={price}, trigger={trigger_price}",
                extra_data={
                    "order_type": order_type,
                    "side": side,
                    "amount": amount,
                    "price": price,
                    "trigger_price": trigger_price,
                    "params": params,
                },
            )

            # 直接API呼び出し
            response = await self._call_private_api(
                "/user/spot/order", params=params, method="POST"
            )

            order_data = response.get("data", {})
            order_id = str(order_data.get("order_id", ""))

            # Phase 86: API応答にorder_idがあるか確認
            if not order_id:
                raise ExchangeAPIError(
                    f"Phase 86: API応答にorder_idなし - response={response}",
                    context={
                        "symbol": symbol,
                        "side": side,
                        "order_type": order_type,
                    },
                )

            # ccxt形式に変換して返す
            result = {
                "id": order_id,
                "symbol": symbol,
                "type": order_type,
                "side": side,
                "amount": amount,
                "price": price,
                "trigger_price": trigger_price,
                "status": order_data.get("status", "open"),
                "raw_response": response,
            }

            # Phase 86: stop型注文の配置後実存在確認（最大3秒・3回ポーリング）
            # API成功でも実際は注文されていない silent fail を検出
            if order_type in ("stop", "stop_limit", "stop_loss"):
                import asyncio as _asyncio

                verified = False
                for attempt in range(3):
                    await _asyncio.sleep(1)
                    try:
                        verify_order = await _asyncio.to_thread(
                            self.exchange.fetch_order, order_id, symbol
                        )
                        if verify_order and verify_order.get("status") in (
                            "open",
                            "closed",
                            "active",
                        ):
                            verified = True
                            break
                        # INACTIVE 状態（stop_limit でトリガー未達）も「配置済み」扱い
                        info_status = (verify_order or {}).get("info", {}).get("status", "")
                        if info_status in ("INACTIVE", "UNFILLED", "PARTIALLY_FILLED"):
                            verified = True
                            break
                    except Exception as verify_err:
                        self.logger.warning(
                            f"⚠️ Phase 86: 配置後確認 試行{attempt + 1}/3 失敗: {verify_err}"
                        )
                if not verified:
                    raise ExchangeAPIError(
                        f"Phase 86: stop注文配置後の実存在確認失敗 - order_id={order_id} "
                        f"がAPIで取得できない（silent fail疑い）",
                        context={
                            "symbol": symbol,
                            "side": side,
                            "order_type": order_type,
                            "order_id": order_id,
                        },
                    )
                result["verified"] = True

            self.logger.info(
                f"✅ Phase 61.3: 直接API注文成功 - ID: {result['id']}, type={order_type}",
                extra_data={"order_id": result["id"], "order_type": order_type},
            )

            return result

        except ExchangeAPIError:
            raise  # Phase 86: 構造化エラーは再raise（上位で分類対応）
        except Exception as e:
            # Phase 86: bitbank エラーコード分類対応
            err_msg = str(e)
            err_code = None
            for code in ("30101", "50061", "50062", "50063", "70015"):
                if code in err_msg:
                    err_code = code
                    break
            err_categories = {
                "30101": "trigger_price未指定 or 不正",
                "50061": "必要証拠金不足",
                "50062": "保有建玉数量超過",
                "50063": "建玉ロット数上限",
                "70015": "新規発注停止中",
            }
            err_category = err_categories.get(err_code, "未分類")
            self.logger.error(
                f"❌ Phase 61.3/86: 直接API注文失敗: {e} "
                f"[error_code={err_code}, category={err_category}]"
            )
            raise ExchangeAPIError(
                f"直接API注文作成に失敗しました: {e} [code={err_code}, {err_category}]",
                context={
                    "symbol": symbol,
                    "side": side,
                    "order_type": order_type,
                    "amount": amount,
                    "trigger_price": trigger_price,
                    "error_code": err_code,
                    "error_category": err_category,
                },
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

            # Phase 53.2: GET/POSTで署名ロジック分岐
            # 重要: GETリクエストの署名には /v1 プレフィックスが必要
            if method.upper() == "GET":
                # GETリクエスト署名: nonce + /v1 + endpoint
                # Phase 53.2修正: bitbank APIはGET署名に /v1 プレフィックスを要求
                message = f"{nonce}/v1{endpoint}"
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

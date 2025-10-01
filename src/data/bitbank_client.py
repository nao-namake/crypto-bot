"""
Bitbank 信用取引専用APIクライアント - シンプル版

信用取引（ロング・ショート）に特化したBitbank APIクライアント
ccxtライブラリを使用してシンプルな実装に特化。.
"""

import os
import time
from typing import Any, Dict, List, Optional, Union

import aiohttp
import ccxt

from ..core.config import get_config
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

        # ccxt Bitbank エクスチェンジ初期化
        try:
            self.exchange = ccxt.bitbank(
                {
                    "apiKey": self.api_key,
                    "secret": self.api_secret,
                    "sandbox": False,  # 本番環境
                    "rateLimit": 1000,  # API制限対応
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

    async def fetch_ohlcv(
        self,
        symbol: str = None,
        timeframe: str = "1h",
        since: Optional[int] = None,
        limit: int = 100,
    ) -> List[List[Union[int, float]]]:
        """
        OHLCV データ取得（4時間足は直接API実装を使用）

        Args:
            symbol: 通貨ペア（Noneの場合は設定から取得）
            timeframe: タイムフレーム（1m, 5m, 15m, 30m, 1h, 4h, 8h, 12h, 1d, 1w）
            since: 開始時刻（ミリ秒）
            limit: 取得件数

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
                # 既存のイベントループ内で直接awaitを使用
                ohlcv = await self.fetch_ohlcv_4h_direct(symbol=symbol, year=current_year)

                # limitが指定されている場合は最新データに制限
                if limit and len(ohlcv) > limit:
                    ohlcv = ohlcv[-limit:]

                return ohlcv

            except Exception as e:
                self.logger.warning(f"直接API取得失敗、ccxtでリトライ: {e}")
                # フォールバックとしてccxtを試行（エラーになる可能性が高いが）
                # ここはそのままccxt呼び出しを継続

        try:
            self.logger.debug(f"OHLCV データ取得開始: {symbol} {timeframe} limit={limit}")

            ohlcv = self.exchange.fetch_ohlcv(
                symbol=symbol, timeframe=timeframe, since=since, limit=limit
            )

            if not ohlcv:
                raise DataFetchError(
                    f"OHLCV データが空です: {symbol} {timeframe}",
                    context={"symbol": symbol, "timeframe": timeframe},
                )

            self.logger.debug(
                f"OHLCV データ取得成功: {len(ohlcv)}件",
                extra_data={
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "count": len(ohlcv),
                },
            )

            return ohlcv

        except ccxt.NetworkError as e:
            raise DataFetchError(
                f"ネットワークエラー: {e}",
                context={"symbol": symbol, "timeframe": timeframe},
            )
        except ccxt.ExchangeError as e:
            raise DataFetchError(
                f"取引所エラー: {e}",
                context={"symbol": symbol, "timeframe": timeframe},
            )
        except Exception as e:
            raise DataFetchError(
                f"OHLCV データ取得に失敗しました: {e}",
                context={"symbol": symbol, "timeframe": timeframe},
            )

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
        try:
            self.logger.debug(f"4時間足直接API取得開始: {symbol} {year}")

            # Bitbank Public APIの正しい形式
            pair = symbol.lower().replace("/", "_")  # BTC/JPY -> btc_jpy
            url = f"https://public.bitbank.cc/{pair}/candlestick/4hour/{year}"

            # SSL証明書設定（セキュア設定）
            import ssl

            ssl_context = ssl.create_default_context()

            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                timeout = aiohttp.ClientTimeout(total=10.0)
                async with session.get(url, timeout=timeout) as response:
                    data = await response.json()

                    if data.get("success") == 1:
                        candlestick_data = data["data"]["candlestick"][0]["ohlcv"]

                        if not candlestick_data:
                            raise DataFetchError(
                                f"4時間足データが空です: {symbol} {year}",
                                context={"symbol": symbol, "year": year},
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

                        self.logger.info(
                            f"4時間足直接API取得成功: {len(ohlcv_data)}件",
                            extra_data={
                                "symbol": symbol,
                                "year": year,
                                "count": len(ohlcv_data),
                                "method": "direct_api",
                            },
                        )

                        return ohlcv_data

                    else:
                        error_code = data.get("data", {}).get("code", "unknown")
                        raise DataFetchError(
                            f"Bitbank API エラー: {error_code}",
                            context={"symbol": symbol, "year": year, "error_code": error_code},
                        )

        except aiohttp.ClientError as e:
            raise DataFetchError(
                f"ネットワークエラー（4時間足）: {e}", context={"symbol": symbol, "year": year}
            )
        except Exception as e:
            raise DataFetchError(
                f"4時間足データ取得失敗: {e}", context={"symbol": symbol, "year": year}
            )

    def fetch_ticker(self, symbol: str = "BTC/JPY") -> Dict[str, Any]:
        """
        ティッカー情報取得

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

    def fetch_balance(self) -> Dict[str, Any]:
        """
        残高情報取得（信用取引）

        Returns:
            信用取引残高情報.
        """
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
    ) -> Dict[str, Any]:
        """
        注文作成（信用取引対応・レガシー実証済み設定使用）

        Args:
            symbol: 通貨ペア（例：BTC/JPY）
            side: 売買方向（buy/sell）
            order_type: 注文タイプ（market/limit）
            amount: 注文量（BTC）
            price: 指値価格（limitの場合・JPY）

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

            if order_type not in ["market", "limit"]:
                raise ExchangeAPIError(
                    f"無効な注文タイプ: {order_type}",
                    context={"order_type": order_type},
                )

            if amount <= 0:
                raise ExchangeAPIError(f"無効な注文量: {amount}", context={"amount": amount})

            if order_type == "limit" and (price is None or price <= 0):
                raise ExchangeAPIError(
                    f"指値注文には有効な価格が必要です: {price}",
                    context={"price": price},
                )

            # 信用取引用パラメータ（bitbank API仕様対応・2025/09/23更新）
            params = {
                "margin": True,  # 信用取引有効
                "marginType": "isolated",  # 分離マージン
                "leverage": self.leverage,  # レバレッジ倍率
                "position_side": (
                    "long" if side.lower() == "buy" else "short"
                ),  # bitbank信用取引必須パラメータ
            }

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

            # 注文実行
            start_time = time.time()
            order = self.exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                price=price,
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
        テイクプロフィット指値注文作成（Phase 29.6）

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
        # TP注文の方向：エントリーと逆方向
        tp_side = "sell" if entry_side.lower() == "buy" else "buy"

        self.logger.info(
            f"📈 テイクプロフィット注文作成: {tp_side} {amount:.4f} BTC @ {take_profit_price:.0f}円",
            extra_data={
                "entry_side": entry_side,
                "tp_side": tp_side,
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
        )

    def create_stop_loss_order(
        self,
        entry_side: str,
        amount: float,
        stop_loss_price: float,
        symbol: str = "BTC/JPY",
    ) -> Dict[str, Any]:
        """
        ストップロス指値注文作成（Phase 29.6）

        Args:
            entry_side: エントリー方向（buy/sell）
            amount: 注文量（BTC）
            stop_loss_price: 損切り価格（JPY）
            symbol: 通貨ペア

        Returns:
            注文情報（order_id含む）

        Raises:
            ExchangeAPIError: 注文作成失敗時
        """
        # SL注文の方向：エントリーと逆方向
        sl_side = "sell" if entry_side.lower() == "buy" else "buy"

        self.logger.info(
            f"🛡️ ストップロス注文作成: {sl_side} {amount:.4f} BTC @ {stop_loss_price:.0f}円",
            extra_data={
                "entry_side": entry_side,
                "sl_side": sl_side,
                "amount": amount,
                "price": stop_loss_price,
            },
        )

        return self.create_order(
            symbol=symbol,
            side=sl_side,
            order_type="limit",
            amount=amount,
            price=stop_loss_price,
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

    def fetch_positions(self, symbol: str = "BTC/JPY") -> List[Dict[str, Any]]:
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

            positions = self.exchange.fetch_positions([symbol])

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

    def set_leverage(self, symbol: str, leverage: float) -> Dict[str, Any]:
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
            if not (1.0 <= leverage <= 2.0):
                raise ExchangeAPIError(
                    f"Bitbankでは1.0-2.0倍のレバレッジのみサポートされています: {leverage}",
                    context={"leverage": leverage},
                )

            if not self.api_key or not self.api_secret:
                raise ExchangeAPIError(
                    "レバレッジ設定には認証が必要です",
                    context={"operation": "set_leverage"},
                )

            result = self.exchange.set_leverage(leverage, symbol)
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
        信用取引口座状況取得（Phase 27新機能・保証金維持率直接取得）

        Returns:
            信用取引口座の状況情報（保証金維持率含む）

        Raises:
            ExchangeAPIError: 取得失敗時
        """
        try:
            if not self.api_key or not self.api_secret:
                raise ExchangeAPIError(
                    "信用取引口座状況取得には認証が必要です",
                    context={"operation": "fetch_margin_status"},
                )

            # ccxtの標準APIでは信用取引状況を取得できない場合があるため、
            # bitbank独自のprivate APIを直接呼び出す
            response = await self._call_private_api("/user/margin/status")

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
        self, endpoint: str, params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        bitbank private API直接呼び出し（内部用）

        Args:
            endpoint: APIエンドポイント（例: '/user/margin/status'）
            params: リクエストパラメータ

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

            # リクエストボディ作成
            if params:
                body = json.dumps(params, separators=(",", ":"))
            else:
                body = ""

            # 署名文字列作成
            message = f"{timestamp}{body}"
            signature = hmac.new(
                self.api_secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
            ).hexdigest()

            # ヘッダー作成
            headers = {
                "ACCESS-KEY": self.api_key,
                "ACCESS-NONCE": nonce,
                "ACCESS-SIGNATURE": signature,
                "Content-Type": "application/json",
            }

            # SSL設定（セキュア設定）
            import ssl

            ssl_context = ssl.create_default_context()

            # API呼び出し実行
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                timeout = aiohttp.ClientTimeout(total=30.0)
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
                            context={"endpoint": endpoint, "error_code": error_code},
                        )

        except aiohttp.ClientError as e:
            raise ExchangeAPIError(f"ネットワークエラー: {e}", context={"endpoint": endpoint})
        except Exception as e:
            raise ExchangeAPIError(f"private API呼び出し失敗: {e}", context={"endpoint": endpoint})

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

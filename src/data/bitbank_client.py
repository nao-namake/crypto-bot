"""
Bitbank 信用取引専用APIクライアント - シンプル版

信用取引（ロング・ショート）に特化したBitbank APIクライアント
ccxtライブラリを使用してシンプルな実装に特化。.
"""

import os
import time
from typing import Any, Dict, List, Optional, Union

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

        # API認証情報
        self.api_key = api_key or os.getenv("BITBANK_API_KEY")
        self.api_secret = api_secret or os.getenv("BITBANK_API_SECRET")

        # レバレッジ検証
        if not (1.0 <= leverage <= 2.0):
            raise ValueError(
                f"レバレッジは1.0-2.0の範囲で設定してください: {leverage}"
            )

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

            self.logger.info(
                f"Bitbank信用取引クライアント初期化完了（レバレッジ: {leverage}x）"
            )

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
            # 公開API（認証不要）でテスト
            ticker = self.exchange.fetch_ticker("BTC/JPY")
            self.logger.info(
                f"Bitbank API接続テスト成功 - BTC/JPY価格: ¥{ticker['last']:,.0f}",
                extra_data={"price": ticker["last"]},
            )
            return True

        except Exception as e:
            self.logger.error("Bitbank API接続テスト失敗", error=e)
            return False

    def fetch_ohlcv(
        self,
        symbol: str = "BTC/JPY",
        timeframe: str = "1h",
        since: Optional[int] = None,
        limit: int = 100,
    ) -> List[List[Union[int, float]]]:
        """
        OHLCV データ取得

        Args:
            symbol: 通貨ペア
            timeframe: タイムフレーム（1m, 5m, 15m, 30m, 1h, 4h, 8h, 12h, 1d, 1w）
            since: 開始時刻（ミリ秒）
            limit: 取得件数

        Returns:
            OHLCV データリスト [[timestamp, open, high, low, close, volume], ...]

        Raises:
            DataFetchError: データ取得失敗時.
        """
        try:
            self.logger.debug(
                f"OHLCV データ取得開始: {symbol} {timeframe} limit={limit}"
            )

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
            raise ExchangeAPIError(
                f"認証エラー: {e}", context={"operation": "fetch_balance"}
            )
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
                raise ExchangeAPIError(
                    f"無効な売買方向: {side}", context={"side": side}
                )

            if order_type not in ["market", "limit"]:
                raise ExchangeAPIError(
                    f"無効な注文タイプ: {order_type}",
                    context={"order_type": order_type},
                )

            if amount <= 0:
                raise ExchangeAPIError(
                    f"無効な注文量: {amount}", context={"amount": amount}
                )

            if order_type == "limit" and (price is None or price <= 0):
                raise ExchangeAPIError(
                    f"指値注文には有効な価格が必要です: {price}",
                    context={"price": price},
                )

            # 信用取引用パラメータ（レガシーから継承・実証済み設定）
            params = {
                "margin": True,  # 信用取引有効
                "marginType": "isolated",  # 分離マージン
                "leverage": self.leverage,  # レバレッジ倍率
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

    def cancel_order(
        self, order_id: str, symbol: str = "BTC/JPY"
    ) -> Dict[str, Any]:
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

        except ccxt.OrderNotFound as e:
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

    def fetch_order(
        self, order_id: str, symbol: str = "BTC/JPY"
    ) -> Dict[str, Any]:
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

        except ccxt.OrderNotFound as e:
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
            active_positions = [
                pos for pos in positions if pos["contracts"] > 0
            ]

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

    def get_stats(self) -> Dict[str, Any]:
        """統計情報取得."""
        return {
            "authenticated": bool(self.api_key and self.api_secret),
            "margin_mode": True,
            "leverage": self.leverage,
            "exchange_id": (
                self.exchange.id if hasattr(self, "exchange") else None
            ),
            "rate_limit": (
                getattr(self.exchange, "rateLimit", None)
                if hasattr(self, "exchange")
                else None
            ),
        }


# グローバルクライアント
_bitbank_client: Optional[BitbankClient] = None


def get_bitbank_client(
    force_recreate: bool = False, leverage: float = 1.0
) -> BitbankClient:
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
    return BitbankClient(
        api_key=api_key, api_secret=api_secret, leverage=leverage
    )

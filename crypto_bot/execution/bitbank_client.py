# crypto_bot/execution/bitbank_client.py
# 説明:
# bitbank 向け取引所クライアントラッパー（ccxt利用）。
# ・現物取引と信用取引の両方に対応
# ・テストネットは未対応（testnet引数は無視される）
# ・OHLCV取得、注文発注、キャンセルなどの基本機能を実装
# ・信用取引：レバレッジ1倍でロング・ショート両対応

import logging

import ccxt
import pandas as pd

from .base import ExchangeClient

logger = logging.getLogger(__name__)


class BitbankClient(ExchangeClient):
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        testnet: bool = False,
        margin_mode: bool = False,
    ):
        """
        Bitbank取引所クライアント

        Args:
            api_key: APIキー
            api_secret: APIシークレット
            testnet: テストネットフラグ（Bitbankでは無視）
            margin_mode: 信用取引モード（True=信用取引、False=現物取引）
        """
        # bitbank にはテストネットは公式にはないので testnet フラグは無視してよい
        self._exchange = ccxt.bitbank(
            {
                "apiKey": api_key,
                "secret": api_secret,
            }
        )
        self.margin_mode = margin_mode
        logger.info(f"BitbankClient initialized: margin_mode={margin_mode}")

    def fetch_balance(self) -> dict:
        return self._exchange.fetch_balance()

    def fetch_ohlcv(self, symbol, timeframe, since=None, limit=None) -> pd.DataFrame:
        data = self._exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
        df = pd.DataFrame(
            data, columns=["ts", "open", "high", "low", "close", "volume"]
        )
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")
        return df.set_index("ts")

    def create_order(self, symbol, side, type, amount, price=None, params=None):
        """
        注文作成（現物・信用取引対応）

        Args:
            symbol: 通貨ペア（例：BTC/JPY）
            side: 売買方向（buy/sell）
            type: 注文タイプ（market/limit）
            amount: 注文量
            price: 指値価格（limitの場合）
            params: 追加パラメータ
        """
        # mutable default を避ける
        params = params or {}

        # 信用取引モードの場合、信用取引用パラメータを追加
        if self.margin_mode:
            # Bitbank信用取引用パラメータ
            params["margin"] = True

            # ショート（売り建て）の場合は売り建て注文として実行
            if side.lower() == "sell":
                logger.info(f"Creating margin SHORT order: {symbol} {amount} @ {price}")
                params["marginType"] = "isolated"  # 分離マージン
                params["side"] = "sell"  # 明示的にショート指定
            else:
                logger.info(f"Creating margin LONG order: {symbol} {amount} @ {price}")
                params["marginType"] = "isolated"  # 分離マージン
                params["side"] = "buy"
        else:
            # 現物取引の場合はショート不可
            if side.lower() == "sell":
                logger.warning("SHORT order not supported in spot trading mode")

        logger.debug(f"Order params: {params}")
        return self._exchange.create_order(symbol, side, type, amount, price, params)

    def cancel_order(self, symbol, order_id):
        return self._exchange.cancel_order(order_id, {"symbol": symbol})

    def cancel_all_orders(self, symbol):
        orders = self._exchange.fetch_open_orders(symbol)
        results = []
        for o in orders:
            results.append(self._exchange.cancel_order(o["id"], {"symbol": symbol}))
        return results

    def set_leverage(self, symbol, leverage):
        """
        レバレッジ設定（信用取引対応）

        Args:
            symbol: 通貨ペア
            leverage: レバレッジ倍率（1-2倍）

        Returns:
            dict: レバレッジ設定結果
        """
        if not self.margin_mode:
            logger.error("Leverage setting is only available in margin trading mode")
            raise NotImplementedError("Leverage setting requires margin_mode=True")

        if leverage < 1 or leverage > 2:
            logger.error(
                f"Invalid leverage: {leverage}. " f"Bitbank supports 1-2x leverage only"
            )
            raise ValueError("Bitbank supports leverage between 1-2x only")

        logger.info(f"Setting leverage to {leverage}x for {symbol} in margin mode")

        try:
            # Bitbank信用取引のレバレッジ設定
            # 実際のAPIコールはBitbankの仕様に依存
            result = self._exchange.set_leverage(leverage, symbol)
            logger.info(f"Leverage set successfully: {leverage}x")
            return result
        except Exception as e:
            logger.error(f"Failed to set leverage: {e}")
            # レバレッジ設定に失敗してもフォールバック
            logger.warning("Continuing with default leverage settings")
            return {"leverage": leverage, "status": "fallback"}

    def get_margin_balance(self) -> dict:
        """
        信用取引残高取得

        Returns:
            dict: 信用取引残高情報
        """
        if not self.margin_mode:
            logger.warning("Margin balance check in spot trading mode")
            return self.fetch_balance()

        try:
            # 信用取引残高を取得
            balance = self._exchange.fetch_balance({"type": "margin"})
            logger.debug(f"Margin balance: {balance}")
            return balance
        except Exception as e:
            logger.warning(f"Failed to get margin balance, falling back to spot: {e}")
            return self.fetch_balance()

    def get_margin_positions(self, symbol=None) -> list:
        """
        信用取引ポジション取得

        Args:
            symbol: 通貨ペア（指定なしで全ポジション）

        Returns:
            list: ポジション情報のリスト
        """
        if not self.margin_mode:
            logger.warning("Position check requested in spot trading mode")
            return []

        try:
            # 信用取引ポジションを取得
            positions = self._exchange.fetch_positions(symbol)
            logger.debug(f"Margin positions: {len(positions)} positions")
            return positions
        except Exception as e:
            logger.error(f"Failed to get margin positions: {e}")
            return []

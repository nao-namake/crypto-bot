"""
注文戦略決定サービス - Phase 38リファクタリング
Phase 26: 指値注文オプション機能

ML信頼度・市場条件・設定に基づいて成行/指値注文を選択し、
指値注文の場合は最適価格を計算する。
"""

import asyncio
from typing import Any, Dict, Optional

from ...core.config import get_threshold
from ...core.logger import get_logger
from ...data.bitbank_client import BitbankClient
from ..core import TradeEvaluation


class OrderStrategy:
    """
    注文戦略決定サービス

    市場条件とML信頼度に基づいて最適な注文戦略を決定する。
    """

    def __init__(self):
        """OrderStrategy初期化"""
        self.logger = get_logger()

    async def get_optimal_execution_config(
        self, evaluation: TradeEvaluation, bitbank_client: Optional[BitbankClient] = None
    ) -> Dict[str, Any]:
        """
        最適注文実行戦略決定（Phase 26: 指値注文オプション）

        ML信頼度・市場条件・設定に基づいて成行/指値注文を選択し、
        指値注文の場合は最適価格を計算する。

        Args:
            evaluation: 取引評価結果
            bitbank_client: BitbankClientインスタンス

        Returns:
            Dict: 注文実行設定 {"order_type": str, "price": Optional[float], "strategy": str}
        """
        try:
            # 1. 基本設定取得
            smart_order_enabled = get_threshold("order_execution.smart_order_enabled", False)

            # スマート注文機能が無効な場合はデフォルト注文タイプを使用
            if not smart_order_enabled:
                default_order_type = get_threshold(
                    "trading_constraints.default_order_type", "market"
                )

                # Phase 29.6: 指値注文の場合は簡易価格計算
                if default_order_type == "limit" and bitbank_client:
                    try:
                        # 板情報取得
                        orderbook = await asyncio.to_thread(
                            bitbank_client.fetch_order_book, "BTC/JPY", 5
                        )

                        if orderbook and "bids" in orderbook and "asks" in orderbook:
                            best_bid = float(orderbook["bids"][0][0]) if orderbook["bids"] else 0
                            best_ask = float(orderbook["asks"][0][0]) if orderbook["asks"] else 0

                            # 約定確率を高めるため、わずかに有利な価格を設定
                            side = evaluation.side
                            if side.lower() == "buy":
                                # 買い注文: ベストアスクより少し高め（0.05%）
                                limit_price = best_ask * 1.0005
                            else:
                                # 売り注文: ベストビッドより少し低め（0.05%）
                                limit_price = best_bid * 0.9995

                            self.logger.info(
                                f"📊 簡易指値価格計算: {side} @ {limit_price:.0f}円 "
                                f"(bid:{best_bid:.0f}, ask:{best_ask:.0f})"
                            )

                            return {
                                "order_type": "limit",
                                "price": limit_price,
                                "strategy": "simple_limit",
                            }
                    except Exception as e:
                        self.logger.warning(f"⚠️ 指値価格計算失敗、成行注文にフォールバック: {e}")
                        return {
                            "order_type": "market",
                            "price": None,
                            "strategy": "fallback_market",
                        }

                return {"order_type": default_order_type, "price": None, "strategy": "default"}

            # 2. ML信頼度による判定
            ml_confidence = float(getattr(evaluation, "confidence_level", 0.5))
            high_confidence_threshold = get_threshold(
                "order_execution.high_confidence_threshold", 0.75
            )

            # 3. 市場条件確認
            market_conditions = await self._assess_market_conditions(bitbank_client)

            # 4. 注文戦略決定
            order_config = await self._determine_order_strategy(
                ml_confidence,
                high_confidence_threshold,
                market_conditions,
                evaluation,
                bitbank_client,
            )

            self.logger.info(
                f"📋 注文実行戦略: {order_config['strategy']} -> {order_config['order_type']}注文"
                + (f" @ {order_config.get('price', 0):.0f}円" if order_config.get("price") else "")
            )

            return order_config

        except Exception as e:
            self.logger.error(f"❌ 注文実行戦略決定エラー: {e}")
            # エラー時は安全な成行注文を使用
            return {"order_type": "market", "price": None, "strategy": "fallback_market"}

    async def _assess_market_conditions(
        self, bitbank_client: Optional[BitbankClient] = None
    ) -> Dict[str, Any]:
        """
        市場条件評価（指値注文判定用）

        Returns:
            Dict: 市場状況情報
        """
        try:
            conditions = {
                "spread_ratio": 0.0,
                "volume_adequate": True,
                "volatility_level": "normal",
                "liquidity_sufficient": True,
            }

            if not bitbank_client:
                conditions["assessment"] = "unable_to_assess"
                return conditions

            # 板情報取得（スプレッド・流動性確認）
            try:
                orderbook = await asyncio.to_thread(bitbank_client.fetch_order_book, "BTC/JPY", 10)

                if orderbook and "bids" in orderbook and "asks" in orderbook:
                    best_bid = float(orderbook["bids"][0][0]) if orderbook["bids"] else 0
                    best_ask = float(orderbook["asks"][0][0]) if orderbook["asks"] else 0

                    if best_bid > 0 and best_ask > 0:
                        spread_ratio = (best_ask - best_bid) / best_bid
                        conditions["spread_ratio"] = spread_ratio
                        conditions["best_bid"] = best_bid
                        conditions["best_ask"] = best_ask

                        # スプレッド判定（設定値と比較）
                        max_spread_for_limit = get_threshold(
                            "order_execution.max_spread_ratio_for_limit", 0.005
                        )  # 0.5%

                        if spread_ratio > max_spread_for_limit:
                            conditions["spread_too_wide"] = True
                            self.logger.warning(
                                f"⚠️ スプレッド拡大: {spread_ratio * 100:.2f}% > {max_spread_for_limit * 100:.1f}%"
                            )

            except Exception as e:
                self.logger.warning(f"⚠️ 板情報取得エラー: {e}")
                conditions["orderbook_error"] = str(e)

            return conditions

        except Exception as e:
            self.logger.error(f"❌ 市場条件評価エラー: {e}")
            return {"assessment": "error", "error": str(e)}

    async def _determine_order_strategy(
        self,
        ml_confidence: float,
        high_confidence_threshold: float,
        market_conditions: Dict[str, Any],
        evaluation: TradeEvaluation,
        bitbank_client: Optional[BitbankClient] = None,
    ) -> Dict[str, Any]:
        """
        注文戦略決定ロジック

        Args:
            ml_confidence: ML信頼度
            high_confidence_threshold: 高信頼度閾値
            market_conditions: 市場条件
            evaluation: 取引評価
            bitbank_client: BitbankClientインスタンス

        Returns:
            Dict: 注文実行設定
        """
        try:
            # 1. 緊急時は成行注文
            if hasattr(evaluation, "emergency_exit") and evaluation.emergency_exit:
                return {"order_type": "market", "price": None, "strategy": "emergency_market"}

            # 2. 低信頼度の場合は成行注文（確実な約定優先）
            low_confidence_threshold = get_threshold(
                "order_execution.low_confidence_threshold", 0.4
            )
            if ml_confidence < low_confidence_threshold:
                return {"order_type": "market", "price": None, "strategy": "low_confidence_market"}

            # 3. スプレッドが広すぎる場合は成行注文
            if market_conditions.get("spread_too_wide", False):
                return {"order_type": "market", "price": None, "strategy": "wide_spread_market"}

            # 4. 高信頼度 + 良好な市場条件 = 指値注文（手数料削減）
            if (
                ml_confidence >= high_confidence_threshold
                and market_conditions.get("liquidity_sufficient", False)
                and not market_conditions.get("orderbook_error")
            ):

                # 指値価格計算
                limit_price = await self._calculate_limit_price(evaluation, market_conditions)

                if limit_price > 0:
                    return {
                        "order_type": "limit",
                        "price": limit_price,
                        "strategy": "high_confidence_limit",
                        "expected_fee": "maker_rebate",  # -0.02%
                    }

            # 5. デフォルト: 中信頼度は成行注文（安全重視）
            return {"order_type": "market", "price": None, "strategy": "medium_confidence_market"}

        except Exception as e:
            self.logger.error(f"❌ 注文戦略決定エラー: {e}")
            return {"order_type": "market", "price": None, "strategy": "error_fallback_market"}

    async def _calculate_limit_price(
        self, evaluation: TradeEvaluation, market_conditions: Dict[str, Any]
    ) -> float:
        """
        指値注文価格計算

        約定確率を考慮しつつ、手数料削減効果を最大化する指値価格を計算。

        Args:
            evaluation: 取引評価
            market_conditions: 市場条件

        Returns:
            float: 指値価格（0の場合は計算失敗）
        """
        try:
            side = evaluation.side
            best_bid = market_conditions.get("best_bid", 0)
            best_ask = market_conditions.get("best_ask", 0)

            if not best_bid or not best_ask:
                self.logger.warning("⚠️ 最良気配なし、指値価格計算不可")
                return 0

            # 指値注文の価格戦略設定
            price_improvement_ratio = get_threshold(
                "order_execution.price_improvement_ratio", 0.001
            )  # 0.1% 価格改善

            if side.lower() == "buy":
                # 買い注文：現在のbid価格より少し上（約定確率向上）
                limit_price = best_bid * (1 + price_improvement_ratio)

                # ask価格を超えないように制限
                max_buy_price = best_ask * 0.999  # askより0.1%下
                limit_price = min(limit_price, max_buy_price)

                self.logger.debug(
                    f"💰 買い指値価格計算: bid={best_bid:.0f}円 -> 指値={limit_price:.0f}円 "
                    f"(改善={price_improvement_ratio * 100:.1f}%)"
                )

            elif side.lower() == "sell":
                # 売り注文：現在のask価格より少し下（約定確率向上）
                limit_price = best_ask * (1 - price_improvement_ratio)

                # bid価格を下回らないように制限
                min_sell_price = best_bid * 1.001  # bidより0.1%上
                limit_price = max(limit_price, min_sell_price)

                self.logger.debug(
                    f"💰 売り指値価格計算: ask={best_ask:.0f}円 -> 指値={limit_price:.0f}円 "
                    f"(改善={price_improvement_ratio * 100:.1f}%)"
                )

            else:
                self.logger.error(f"❌ 不正な注文サイド: {side}")
                return 0

            # 価格の妥当性チェック
            if limit_price <= 0:
                self.logger.error(f"❌ 不正な指値価格: {limit_price}")
                return 0

            return round(limit_price)  # 円単位に丸める

        except Exception as e:
            self.logger.error(f"❌ 指値価格計算エラー: {e}")
            return 0

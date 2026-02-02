"""
注文戦略決定サービス - Phase 49完了
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
        指値注文価格計算（Phase 38.7.1: 確実約定戦略対応）

        約定確率を最優先しつつ、メイカー手数料リベート獲得を目指す指値価格を計算。

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

            # Phase 38.7.1: 確実約定戦略設定
            entry_price_strategy = get_threshold(
                "order_execution.entry_price_strategy", "unfavorable"
            )  # "favorable" or "unfavorable"

            guaranteed_execution_premium = get_threshold(
                "order_execution.guaranteed_execution_premium", 0.0005
            )  # 0.05% プレミアム（確実約定用）

            if entry_price_strategy == "unfavorable":
                # ✅ 確実約定戦略：板の前に並ぶ不利な価格で注文（約定確率100%）
                if side.lower() == "buy":
                    # 買い注文：ask価格より少し上（板の最前列・確実に約定）
                    limit_price = best_ask * (1 + guaranteed_execution_premium)

                    self.logger.debug(
                        f"💰 買い指値価格計算（確実約定戦略）: ask={best_ask:.0f}円 -> 指値={limit_price:.0f}円 "
                        f"(プレミアム={guaranteed_execution_premium * 100:.2f}%)"
                    )

                elif side.lower() == "sell":
                    # 売り注文：bid価格より少し下（板の最前列・確実に約定）
                    limit_price = best_bid * (1 - guaranteed_execution_premium)

                    self.logger.debug(
                        f"💰 売り指値価格計算（確実約定戦略）: bid={best_bid:.0f}円 -> 指値={limit_price:.0f}円 "
                        f"(プレミアム={guaranteed_execution_premium * 100:.2f}%)"
                    )

                else:
                    self.logger.error(f"❌ 不正な注文サイド: {side}")
                    return 0

            else:
                # 従来の価格改善戦略（有利な価格だが約定確率は低い）
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
                        f"💰 買い指値価格計算（価格改善戦略）: bid={best_bid:.0f}円 -> 指値={limit_price:.0f}円 "
                        f"(改善={price_improvement_ratio * 100:.1f}%)"
                    )

                elif side.lower() == "sell":
                    # 売り注文：現在のask価格より少し下（約定確率向上）
                    limit_price = best_ask * (1 - price_improvement_ratio)

                    # bid価格を下回らないように制限
                    min_sell_price = best_bid * 1.001  # bidより0.1%上
                    limit_price = max(limit_price, min_sell_price)

                    self.logger.debug(
                        f"💰 売り指値価格計算（価格改善戦略）: ask={best_ask:.0f}円 -> 指値={limit_price:.0f}円 "
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

    # ========================================
    # Phase 46: 統合TP/SL価格計算メソッド削除（デイトレード特化）
    # ========================================
    # Phase 42-43で実装された統合TP/SL価格計算機能を削除:
    # - calculate_consolidated_tp_sl_prices() - 統合TP/SL価格計算（~148行）
    #
    # デイトレード特化設計では個別TP/SL配置に回帰・シンプル性重視
    # 個別TP/SL計算は calculate_take_profit_price() / calculate_stop_loss_price() を使用

    # ========================================
    # Phase 62.9: Maker戦略メソッド
    # ========================================

    async def get_maker_execution_config(
        self,
        evaluation: TradeEvaluation,
        bitbank_client: Optional[BitbankClient] = None,
    ) -> Dict[str, Any]:
        """
        Phase 62.9: Maker注文設定取得

        Args:
            evaluation: 取引評価結果
            bitbank_client: BitbankClientインスタンス

        Returns:
            Dict: Maker注文設定 {"use_maker": bool, "price": float, ...}
        """
        config = get_threshold("order_execution.maker_strategy", {})

        # Maker戦略無効時
        if not config.get("enabled", False):
            return {"use_maker": False, "disable_reason": "disabled"}

        # クライアントなし
        if not bitbank_client:
            return {"use_maker": False, "disable_reason": "no_client"}

        # 市場条件評価
        conditions = await self._assess_maker_conditions(bitbank_client, config)
        if not conditions.get("maker_viable", False):
            return {
                "use_maker": False,
                "disable_reason": conditions.get("disable_reason", "unknown"),
            }

        # Maker価格計算
        price = self._calculate_maker_price(
            evaluation.side, conditions["best_bid"], conditions["best_ask"]
        )

        if price <= 0:
            return {"use_maker": False, "disable_reason": "price_calculation_failed"}

        self.logger.info(
            f"📡 Phase 62.9: Maker戦略有効 - {evaluation.side} @ {price:.0f}円 "
            f"(スプレッド: {conditions['spread_ratio'] * 100:.3f}%)"
        )

        return {
            "use_maker": True,
            "price": price,
            "best_bid": conditions["best_bid"],
            "best_ask": conditions["best_ask"],
            "spread_ratio": conditions["spread_ratio"],
        }

    async def _assess_maker_conditions(
        self, client: BitbankClient, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Phase 62.9: Maker市場条件評価

        Args:
            client: BitbankClientインスタンス
            config: Maker戦略設定

        Returns:
            Dict: 市場条件評価結果
        """
        try:
            # 板情報取得
            orderbook = await asyncio.to_thread(client.fetch_order_book, "BTC/JPY", 5)

            if not orderbook or "bids" not in orderbook or "asks" not in orderbook:
                return {"maker_viable": False, "disable_reason": "orderbook_unavailable"}

            if not orderbook["bids"] or not orderbook["asks"]:
                return {"maker_viable": False, "disable_reason": "empty_orderbook"}

            best_bid = float(orderbook["bids"][0][0])
            best_ask = float(orderbook["asks"][0][0])

            if best_bid <= 0 or best_ask <= 0:
                return {"maker_viable": False, "disable_reason": "invalid_prices"}

            spread_ratio = (best_ask - best_bid) / best_bid

            # スプレッド狭すぎ確認（Maker不利）
            min_spread = config.get("min_spread_for_maker", 0.001)
            if spread_ratio < min_spread:
                self.logger.debug(
                    f"📡 Phase 62.9: スプレッド狭すぎ {spread_ratio * 100:.3f}% < {min_spread * 100:.1f}%"
                )
                return {"maker_viable": False, "disable_reason": "spread_too_narrow"}

            # 高ボラティリティ確認（Maker危険）
            volatility_threshold = config.get("volatility_threshold", 0.02)
            if spread_ratio > volatility_threshold:
                self.logger.debug(
                    f"📡 Phase 62.9: 高ボラティリティ {spread_ratio * 100:.3f}% > {volatility_threshold * 100:.1f}%"
                )
                return {"maker_viable": False, "disable_reason": "high_volatility"}

            return {
                "maker_viable": True,
                "best_bid": best_bid,
                "best_ask": best_ask,
                "spread_ratio": spread_ratio,
            }

        except Exception as e:
            self.logger.warning(f"⚠️ Phase 62.9: 市場条件評価エラー: {e}")
            return {"maker_viable": False, "disable_reason": f"error: {e}"}

    def _calculate_maker_price(self, side: str, best_bid: float, best_ask: float) -> float:
        """
        Phase 62.9: Maker価格計算（板の内側に配置）

        Args:
            side: 売買方向（buy/sell）
            best_bid: 最良買い気配
            best_ask: 最良売り気配

        Returns:
            float: Maker価格（0の場合は計算失敗）
        """
        tick = get_threshold("order_execution.maker_strategy.price_adjustment_tick", 1)

        if side.lower() == "buy":
            # 買い注文: bid直上（最良買い気配+1tick）
            price = best_bid + tick
            # ask以上になってはいけない（即時約定=Taker化）
            if price >= best_ask:
                self.logger.debug(
                    f"📡 Phase 62.9: 買いMaker価格がask以上 {price:.0f} >= {best_ask:.0f}"
                )
                return 0
            return round(price)

        elif side.lower() == "sell":
            # 売り注文: ask直下（最良売り気配-1tick）
            price = best_ask - tick
            # bid以下になってはいけない（即時約定=Taker化）
            if price <= best_bid:
                self.logger.debug(
                    f"📡 Phase 62.9: 売りMaker価格がbid以下 {price:.0f} <= {best_bid:.0f}"
                )
                return 0
            return round(price)

        else:
            self.logger.error(f"❌ Phase 62.9: 不正なside: {side}")
            return 0

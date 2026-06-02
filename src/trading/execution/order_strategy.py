"""
注文戦略決定サービス - Phase 64
Phase 26: 指値注文オプション機能

ML信頼度・市場条件・設定に基づいて成行/指値注文を選択し、
指値注文の場合は最適価格を計算する。
"""

import asyncio
from dataclasses import replace
from typing import Any, Dict, Optional

from ...core.config import get_threshold
from ...core.logger import get_logger
from ...data.bitbank_client import BitbankClient
from ..core import ExecutionMode, ExecutionResult, OrderStatus, TradeEvaluation
from .tp_sl_config import TPSLConfig


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

        # Phase 90γ-③.4: 本番 LOG_LEVEL=WARNING (Phase 88 I1) で観察可能にするため warning 格上げ
        self.logger.warning(
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
                # Phase 90γ-⑥: Maker 経路スキップ理由を WARNING で観察可能化
                self.logger.warning(
                    "📊 Phase 90γ-⑥: Maker 経路スキップ - reason=orderbook_unavailable"
                )
                return {"maker_viable": False, "disable_reason": "orderbook_unavailable"}

            if not orderbook["bids"] or not orderbook["asks"]:
                self.logger.warning("📊 Phase 90γ-⑥: Maker 経路スキップ - reason=empty_orderbook")
                return {"maker_viable": False, "disable_reason": "empty_orderbook"}

            best_bid = float(orderbook["bids"][0][0])
            best_ask = float(orderbook["asks"][0][0])

            if best_bid <= 0 or best_ask <= 0:
                self.logger.warning(
                    f"📊 Phase 90γ-⑥: Maker 経路スキップ - reason=invalid_prices "
                    f"(best_bid={best_bid}, best_ask={best_ask})"
                )
                return {"maker_viable": False, "disable_reason": "invalid_prices"}

            spread_ratio = (best_ask - best_bid) / best_bid

            # スプレッド狭すぎ確認（Maker不利）
            # Phase 65.4: min_spread=0でチェック無効化（post_onlyで保護）
            min_spread = config.get("min_spread_for_maker", 0)
            if min_spread > 0 and spread_ratio < min_spread:
                # Phase 90γ-⑥: info→warning（spread_too_narrow 経路の観察可能化）
                self.logger.warning(
                    f"📊 Phase 90γ-⑥: Maker 経路スキップ - reason=spread_too_narrow "
                    f"({spread_ratio * 100:.4f}% < {min_spread * 100:.3f}%)"
                )
                return {"maker_viable": False, "disable_reason": "spread_too_narrow"}

            # 高ボラティリティ確認（Maker危険）
            volatility_threshold = config.get("volatility_threshold", 0.02)
            if spread_ratio > volatility_threshold:
                # Phase 90γ-⑥: debug→warning（高ボラ判定経路の観察可能化）
                # Taker 87.5% の主因仮説 - threshold=0.02 (2%) が厳しすぎる可能性
                self.logger.warning(
                    f"📊 Phase 90γ-⑥: Maker 経路スキップ - reason=high_volatility "
                    f"({spread_ratio * 100:.3f}% > {volatility_threshold * 100:.1f}%)"
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
        """Maker 価格計算（Phase 90γ-③.5 で仕様誤読を訂正）.

        bitbank 公式仕様（Support サイト）:
            post_only=true の指値は「**反対側板**と即時マッチして部分約定し得る場合のみ cancel」。
            **自側板**（buy なら best_bid、sell なら best_ask）と同価格の場合は cancel されず、
            queue 末尾に並んで Maker 約定可能。

        旧 Phase 68/79 のコメント「best_bid/ask に直接配置すると必ず reject される」は
        この仕様の誤読であり、Phase 90γ-③.5 で訂正した（広 spread では improvement を
        加えて queue 先頭側に並ぶ既存戦略を維持しつつ、狭 spread<2 円では best_bid 直接
        配置で Maker 約定を実現する）。

        spread >= 2 円: best_bid + improvement または best_ask - improvement（既存戦略）。
        spread < 2 円 (= BTC/JPY 1 tick 最小 spread): best_bid または best_ask 直接配置
            （queue 末尾待機戦略・Phase 90γ-③.5）。

        Args:
            side: 売買方向（buy/sell）
            best_bid: 最良買い気配
            best_ask: 最良売り気配

        Returns:
            float: Maker価格（0の場合は計算失敗）
        """
        spread = best_ask - best_bid

        # spread<=0 の異常ケース（best_bid >= best_ask = クロス板）は安全側で発注中止
        if spread <= 0:
            self.logger.warning(
                f"⚠️ Phase 90γ-③.5: 異常 spread {spread:.0f}円 (best_bid={best_bid:.0f} >= "
                f"best_ask={best_ask:.0f}) - Maker配置中止"
            )
            return 0

        # Phase 90γ-③.5: 狭 spread（< 2 円・BTC/JPY 1 tick 最小 spread）での best_bid 直接配置戦略
        # 旧 Phase 79 では return 0 で即 Taker fallback → 24h で Taker fallback 4 件発生
        # bitbank 公式仕様により自側板への post_only=true は cancel されず Maker 約定可能
        narrow_strategy_enabled = bool(
            get_threshold(
                "order_execution.maker_strategy.narrow_spread_strategy.enabled",
                True,
            )
        )
        if spread < 2:
            if not narrow_strategy_enabled:
                # feature flag false: 旧挙動（即 Taker fallback）
                self.logger.warning(f"⚠️ Phase 79: スプレッド狭小({spread:.0f}円) - Maker配置不可")
                return 0

            if side.lower() == "buy":
                price = best_bid  # 自側板（既存買い板の最高値）に並ぶ
                self.logger.warning(
                    f"📡 Phase 90γ-③.5: 狭spread Maker買い価格 {price:.0f}円 "
                    f"(spread={spread:.0f}円, best_bid直接配置・queue末尾待機)"
                )
                return round(price)
            elif side.lower() == "sell":
                price = best_ask  # 自側板（既存売り板の最安値）に並ぶ
                self.logger.warning(
                    f"📡 Phase 90γ-③.5: 狭spread Maker売り価格 {price:.0f}円 "
                    f"(spread={spread:.0f}円, best_ask直接配置・queue末尾待機)"
                )
                return round(price)
            else:
                self.logger.error(f"❌ Phase 62.9: 不正なside: {side}")
                return 0

        # 広 spread (>= 2 円): improvement で queue 先頭側に並ぶ既存戦略
        # Phase 90γ-③.2: 旧 spread*0.1 ではほぼ常に 1 円に張り付き約定確率が低かったため 0.3 に拡大
        improvement = max(1, min(int(spread * 0.3), int(spread - 1)))

        if side.lower() == "buy":
            # best_bidより improvement円上（既存買い板より優先される位置・post_only は best_ask 未到達なので安全）
            price = best_bid + improvement
            # Phase 90γ-③.4: warning 格上げ（観察可能化）
            self.logger.warning(
                f"📡 Phase 79: Maker買い価格 {price:.0f}円 "
                f"(best_bid={best_bid:.0f} +{improvement}, スプレッド={spread:.0f}円)"
            )
            return round(price)

        elif side.lower() == "sell":
            # best_askより improvement円下（既存売り板より優先される位置）
            price = best_ask - improvement
            # Phase 90γ-③.4: warning 格上げ（観察可能化）
            self.logger.warning(
                f"📡 Phase 79: Maker売り価格 {price:.0f}円 "
                f"(best_ask={best_ask:.0f} -{improvement}, スプレッド={spread:.0f}円)"
            )
            return round(price)

        else:
            self.logger.error(f"❌ Phase 62.9: 不正なside: {side}")
            return 0

    # ========================================
    # Phase 62.9: Maker注文実行（リトライ機構付き）
    # ========================================

    async def execute_maker_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        maker_config: Dict[str, Any],
        bitbank_client: BitbankClient,
    ) -> Optional[ExecutionResult]:
        """
        Phase 62.9: Maker注文実行（リトライ機構付き）

        Args:
            symbol: 通貨ペア
            side: 売買方向
            amount: 注文数量
            maker_config: Maker戦略設定（price, best_bid, best_ask等）
            bitbank_client: BitbankClientインスタンス

        Returns:
            ExecutionResult: 成功時は約定結果、失敗時はNone
        """
        from datetime import datetime

        from src.core.exceptions import PostOnlyCancelledException

        config = get_threshold(TPSLConfig.MAKER_STRATEGY, {})
        max_retries = config.get("max_retries", 3)
        retry_interval = config.get("retry_interval_ms", 500) / 1000
        timeout = config.get("timeout_seconds", 30)
        max_adj = config.get("max_price_adjustment_ratio", 0.001)
        # Phase 90κ: 1試行あたりの待機を timeout/max_retries に分割し、リトライを実際に複数回回す。
        # 旧実装は初回試行に残り総時間(~120秒)をフルで渡し、試行1回で全体timeoutを消費して
        # リトライに進まなかった（30日データで試行2が2件のみ＝max_retries=5が機能していなかった）。
        # 下限5秒で _wait_for_maker_fill の 0.5秒間隔×10回チェックを保証。
        per_attempt_timeout = max(5, int(timeout // max(1, max_retries)))

        initial_price = maker_config.get("price", 0)
        if initial_price <= 0:
            self.logger.warning("⚠️ Phase 62.9: Maker価格が無効")
            return None

        current_price = initial_price
        start = datetime.now()

        for attempt in range(max_retries):
            elapsed = (datetime.now() - start).total_seconds()
            if elapsed >= timeout:
                self.logger.warning(
                    f"⚠️ Phase 62.9: Makerタイムアウト ({elapsed:.1f}秒 >= {timeout}秒)"
                )
                return None

            try:
                # Phase 90γ-③.4: warning 格上げ（観察可能化）
                self.logger.warning(
                    f"📡 Phase 62.9: Maker注文試行 {attempt + 1}/{max_retries} - "
                    f"{side} {amount:.4f} BTC @ {current_price:.0f}円 (post_only)"
                )

                # post_only指値注文
                order = bitbank_client.create_order(
                    symbol=symbol,
                    side=side,
                    order_type="limit",
                    amount=amount,
                    price=current_price,
                    post_only=True,
                )

                order_id = order.get("id")
                if not order_id:
                    self.logger.warning("⚠️ Phase 62.9: 注文IDなし")
                    continue

                # 約定待機（Phase 90κ: per-attempt 枠と残り総時間の小さい方で待つ。
                # これによりリトライが実際に複数回回り、各回で最新 best 気配へ追従できる）
                remaining_total = timeout - (datetime.now() - start).total_seconds()
                wait_timeout = max(5, min(per_attempt_timeout, remaining_total))
                filled = await self._wait_for_maker_fill(
                    order_id, symbol, wait_timeout, bitbank_client
                )

                if filled:
                    filled_price = filled.get("price", current_price)
                    filled_amount = filled.get("amount", amount)

                    # Phase 90δ: 約定種別(maker/taker)と実手数料を bitbank 約定履歴から取得し
                    # 「Maker(0%)」の決め打ちログ・fee=0.0 ハードコードを実態ベースに是正
                    taker_or_maker, fee_cost = await self._resolve_fill_type(
                        order_id, symbol, bitbank_client
                    )
                    self._log_maker_fill_result(
                        order_id, filled_price, current_price, taker_or_maker, fee_cost
                    )

                    return ExecutionResult(
                        success=True,
                        mode=ExecutionMode.LIVE,
                        order_id=order_id,
                        price=filled_price,
                        amount=filled_amount,
                        filled_price=filled_price,
                        filled_amount=filled_amount,
                        error_message=None,
                        side=side,
                        fee=fee_cost if fee_cost is not None else 0.0,
                        status=OrderStatus.FILLED,
                        notes=f"Phase 62.9: Maker約定 (約定種別={taker_or_maker or '不明'})",
                    )

                # 未約定 → キャンセル
                self.logger.info(f"📡 Phase 62.9: 未約定 - 注文キャンセル試行 (ID: {order_id})")
                try:
                    await asyncio.to_thread(bitbank_client.cancel_order, order_id, symbol)
                except Exception as cancel_e:
                    self.logger.warning(
                        f"⚠️ Phase 62.9: キャンセル失敗（約定済みの可能性）: {cancel_e}"
                    )
                    # キャンセル失敗=約定済みの可能性があるので再確認
                    filled = await self._wait_for_maker_fill(order_id, symbol, 2, bitbank_client)
                    if filled:
                        filled_price = filled.get("price", current_price)
                        # Phase 90δ: キャンセル後確認の約定も種別・実手数料を取得
                        taker_or_maker, fee_cost = await self._resolve_fill_type(
                            order_id, symbol, bitbank_client
                        )
                        self._log_maker_fill_result(
                            order_id, filled_price, current_price, taker_or_maker, fee_cost
                        )
                        return ExecutionResult(
                            success=True,
                            mode=ExecutionMode.LIVE,
                            order_id=order_id,
                            price=filled_price,
                            amount=filled.get("amount", amount),
                            filled_price=filled_price,
                            filled_amount=filled.get("amount", amount),
                            error_message=None,
                            side=side,
                            fee=fee_cost if fee_cost is not None else 0.0,
                            status=OrderStatus.FILLED,
                            notes=f"Phase 62.9: Maker約定（キャンセル後確認・種別={taker_or_maker or '不明'}）",
                        )

            except PostOnlyCancelledException as e:
                self.logger.info(f"📡 Phase 62.9: post_onlyキャンセル（価格調整） - {e}")

            except Exception as e:
                self.logger.warning(f"⚠️ Phase 62.9: Maker注文エラー: {e}")

            # Phase 90κ: リトライ時は最新の best 気配を再取得して価格追従する。
            # 旧実装（Phase 68）は「板の奥へ tick ずらす」設計で、約定から遠ざかり、かつ価格が
            # 動いても追従しなかった。post_only キャンセルは 30日で 0件＝自側 best への再配置は
            # リジェクトされないため、best へ追従する方が queue末尾で価格到達時に約定できる。
            conditions = await self._assess_maker_conditions(bitbank_client, config)
            if not conditions.get("maker_viable"):
                self.logger.info(
                    "📡 Phase 90κ: リトライ時の板再取得で Maker 不可 → 中止 "
                    f"(reason={conditions.get('disable_reason')})"
                )
                return None
            new_price = self._calculate_maker_price(
                side, conditions["best_bid"], conditions["best_ask"]
            )
            if new_price <= 0:
                return None  # クロス板等 → fallback へ
            # 初期価格からの乖離上限ガード（暴走防止・Phase 68 の max_adj を踏襲）
            if abs(new_price - initial_price) > initial_price * max_adj:
                self.logger.warning(
                    f"⚠️ Phase 90κ: best 追従が乖離上限超過 "
                    f"({new_price:.0f} vs 初期 {initial_price:.0f}, 上限 {max_adj * 100:.2f}%) → 中止"
                )
                return None
            current_price = new_price

            await asyncio.sleep(retry_interval)

        self.logger.warning(f"⚠️ Phase 62.9: 最大リトライ回数到達 ({max_retries}回)")
        return None

    async def _wait_for_maker_fill(
        self,
        order_id: str,
        symbol: str,
        timeout: float,
        bitbank_client: BitbankClient,
    ) -> Optional[Dict[str, Any]]:
        """
        Phase 62.9: Maker注文の約定待機

        Args:
            order_id: 注文ID
            symbol: 通貨ペア
            timeout: タイムアウト秒数
            bitbank_client: BitbankClientインスタンス

        Returns:
            Dict: 約定情報（約定時）、None（未約定時）
        """
        from datetime import datetime

        check_interval = 0.5  # 500ms間隔でチェック
        start = datetime.now()

        while (datetime.now() - start).total_seconds() < timeout:
            try:
                order = await asyncio.to_thread(bitbank_client.fetch_order, order_id, symbol)

                if order:
                    status = order.get("status", "").lower()
                    filled_amount = float(order.get("filled") or 0)
                    order_amount = float(order.get("amount") or 0)

                    # 完全約定
                    if status == "closed" or (
                        filled_amount > 0 and filled_amount >= order_amount * 0.99
                    ):
                        return {
                            "price": float(order.get("average") or order.get("price") or 0),
                            "amount": filled_amount,
                        }

                    # キャンセル済み
                    if status == "canceled":
                        return None

            except Exception as e:
                self.logger.debug(f"📡 Phase 62.9: 注文状態確認エラー: {e}")

            await asyncio.sleep(check_interval)

        return None

    async def _resolve_fill_type(
        self,
        order_id: str,
        symbol: str,
        bitbank_client: BitbankClient,
    ) -> tuple:
        """Phase 90δ: 約定種別(maker/taker)と実手数料を bitbank 約定履歴から取得。

        ccxt の parse_order は fee/種別を埋めないため、fetch_my_trades から
        order_id に紐づく約定を集約する。取得失敗・該当なしの場合は (None, None)
        を返し、呼び出し側は「種別不明」として扱う。

        Returns:
            tuple: (taker_or_maker: Optional[str], fee_cost: Optional[float])
        """
        try:
            trades = await asyncio.to_thread(
                bitbank_client.exchange.fetch_my_trades, symbol, None, 20
            )
            matched = [t for t in (trades or []) if str(t.get("order")) == str(order_id)]
            if not matched:
                return None, None

            taker_or_maker = None
            fee_cost = 0.0
            has_fee = False
            for t in matched:
                # 最後に取れた種別を採用（同一注文の約定は通常同種別）
                taker_or_maker = t.get("takerOrMaker") or taker_or_maker
                fee = t.get("fee") or {}
                cost = fee.get("cost")
                if cost is not None:
                    fee_cost += float(cost)
                    has_fee = True

            return taker_or_maker, (fee_cost if has_fee else None)
        except Exception as e:
            self.logger.debug(f"📡 Phase 90δ: 約定種別取得失敗（種別不明として続行）: {e}")
            return None, None

    def _log_maker_fill_result(
        self,
        order_id: str,
        filled_price: float,
        limit_price: float,
        taker_or_maker: Optional[str],
        fee_cost: Optional[float],
    ) -> None:
        """Phase 90δ: 約定種別に応じた約定ログを出力（虚偽 Maker 記録の是正）。"""
        fee_str = f"{fee_cost:.1f}円" if fee_cost is not None else "不明"
        if taker_or_maker == "taker":
            # post_only 指定にもかかわらず Taker 約定＝価格が即時約定側に食い込んだ
            self.logger.warning(
                f"⚠️ Phase 90δ: post_only指定だがTaker約定 - "
                f"ID: {order_id}, 約定価格: {filled_price:.0f}円 "
                f"(指値: {limit_price:.0f}円), 実手数料: {fee_str}"
            )
        else:
            label = "Maker" if taker_or_maker == "maker" else "約定種別不明"
            self.logger.warning(
                f"✅ Phase 62.9: Maker約定成功 - "
                f"ID: {order_id}, 価格: {filled_price:.0f}円, "
                f"手数料: {label}({fee_str})"
            )

    def ensure_minimum_trade_size(self, evaluation: TradeEvaluation) -> TradeEvaluation:
        """
        最小ロットサイズを保証する（動的ポジションサイジング対応）

        Args:
            evaluation: 元の取引評価結果

        Returns:
            調整されたTradeEvaluation
        """
        try:
            # 動的ポジションサイジングが有効かチェック
            dynamic_enabled = get_threshold(
                "position_management.dynamic_position_sizing.enabled", False
            )

            if not dynamic_enabled:
                return evaluation  # 従来通り変更なし

            # 最小取引サイズ取得
            min_trade_size = get_threshold(TPSLConfig.MIN_TRADE_SIZE, 0.0001)

            # 現在のポジションサイズと比較
            current_position_size = float(getattr(evaluation, "position_size", 0))

            if current_position_size < min_trade_size:
                # 最小ロット保証適用
                self.logger.info(
                    f"📏 最小ロット保証適用: {current_position_size:.6f} -> {min_trade_size:.6f} BTC"
                )

                # evaluationのposition_sizeを更新（immutableなdataclassの場合を考慮）
                if hasattr(evaluation, "__dict__"):
                    evaluation.position_size = min_trade_size
                else:
                    # dataclassの場合は新しいインスタンスを作成
                    evaluation = replace(evaluation, position_size=min_trade_size)

            return evaluation

        except Exception as e:
            self.logger.error(f"最小ロット保証処理エラー: {e}")
            return evaluation  # エラー時は元のevaluationを返す

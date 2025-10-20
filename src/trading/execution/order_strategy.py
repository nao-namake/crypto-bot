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
    # Phase 42: 統合TP/SL用メソッド
    # ========================================

    def calculate_consolidated_tp_sl_prices(
        self,
        average_entry_price: float,
        side: str,
        market_conditions: Optional[Dict[str, Any]] = None,
        existing_sl_price: Optional[float] = None,
    ) -> Dict[str, float]:
        """
        統合TP/SL価格計算（Phase 43・SL最悪位置維持対応）

        平均エントリー価格から±TP/SL率で統合TP/SL価格を計算する。
        適応型ATR倍率・リスクリワード比管理に対応。

        Phase 43: ナンピン時は既存SLと比較し、より保護的なSL位置を維持する。
        - 買いポジション: max(新規SL, 既存SL) - 高い方が保護的
        - 売りポジション: min(新規SL, 既存SL) - 低い方が保護的

        Args:
            average_entry_price: 平均エントリー価格
            side: 注文サイド (buy/sell)
            market_conditions: 市場条件（ATR値等）
            existing_sl_price: 既存SL価格（ナンピン時、Phase 43追加）

        Returns:
            Dict: {
                "take_profit_price": float,
                "stop_loss_price": float,
                "tp_rate": float,
                "sl_rate": float
            }
        """
        try:
            # Phase 42.4: TP/SL設定をthresholds.yamlトップレベルから取得（ハードコード削除）
            # 固定パラメータ（Phase 42で最適化対象外として設定済み）
            default_tp_ratio = get_threshold("tp_default_ratio", 1.5)
            min_profit_ratio = get_threshold("tp_min_profit_ratio", 0.019)
            default_atr_multiplier = get_threshold("sl_atr_normal_vol", 2.0)
            sl_min_distance_ratio = get_threshold("sl_min_distance_ratio", 0.01)
            max_loss_ratio = get_threshold("position_management.stop_loss.max_loss_ratio", 0.03)

            # SL率計算（適応型ATR倍率対応）
            if market_conditions and "atr_ratio" in market_conditions:
                # ATR比率がある場合は適応型計算
                atr_ratio = market_conditions["atr_ratio"]
                sl_rate = min(atr_ratio * default_atr_multiplier, max_loss_ratio)
                self.logger.debug(
                    f"📊 適応型SL率計算: ATR比率={atr_ratio:.4f} × 倍率={default_atr_multiplier} = {sl_rate * 100:.2f}%"
                )
            else:
                # Phase 42.4: デフォルトSL率をthresholds.yamlから取得（ハードコード0.02削除）
                sl_rate = sl_min_distance_ratio
                self.logger.debug(f"📊 デフォルトSL率使用: {sl_rate * 100:.2f}%")

            # TP率計算（リスクリワード比管理）
            tp_rate = max(sl_rate * default_tp_ratio, min_profit_ratio)
            self.logger.debug(
                f"📊 TP率計算: SL率={sl_rate * 100:.2f}% × RR比={default_tp_ratio} = {tp_rate * 100:.2f}%"
            )

            # 価格計算
            if side.lower() == "buy":
                # 買いポジション: TP = 平均価格 × (1 + tp_rate), SL = 平均価格 × (1 - sl_rate)
                take_profit_price = round(average_entry_price * (1 + tp_rate))
                new_sl_price = round(average_entry_price * (1 - sl_rate))

                # Phase 43: 既存SLと比較し、より保護的な位置を維持
                if existing_sl_price is not None and existing_sl_price > 0:
                    # 買いポジション: SL価格が高い方が保護的（損失が小さい）
                    stop_loss_price = max(new_sl_price, existing_sl_price)
                    if stop_loss_price != new_sl_price:
                        self.logger.info(
                            f"🛡️ Phase 43: 既存SL維持 - 新規={new_sl_price:.0f}円 < 既存={existing_sl_price:.0f}円 "
                            f"→ 保護的な既存SL採用"
                        )
                else:
                    stop_loss_price = new_sl_price

                self.logger.info(
                    f"💰 買いポジション統合TP/SL計算: "
                    f"平均={average_entry_price:.0f}円, "
                    f"TP={take_profit_price:.0f}円(+{tp_rate * 100:.2f}%), "
                    f"SL={stop_loss_price:.0f}円(-{(average_entry_price - stop_loss_price) / average_entry_price * 100:.2f}%)"
                )

            elif side.lower() == "sell":
                # 売りポジション: TP = 平均価格 × (1 - tp_rate), SL = 平均価格 × (1 + sl_rate)
                take_profit_price = round(average_entry_price * (1 - tp_rate))
                new_sl_price = round(average_entry_price * (1 + sl_rate))

                # Phase 43: 既存SLと比較し、より保護的な位置を維持
                if existing_sl_price is not None and existing_sl_price > 0:
                    # 売りポジション: SL価格が低い方が保護的（損失が小さい）
                    stop_loss_price = min(new_sl_price, existing_sl_price)
                    if stop_loss_price != new_sl_price:
                        self.logger.info(
                            f"🛡️ Phase 43: 既存SL維持 - 新規={new_sl_price:.0f}円 > 既存={existing_sl_price:.0f}円 "
                            f"→ 保護的な既存SL採用"
                        )
                else:
                    stop_loss_price = new_sl_price

                self.logger.info(
                    f"💰 売りポジション統合TP/SL計算: "
                    f"平均={average_entry_price:.0f}円, "
                    f"TP={take_profit_price:.0f}円(-{tp_rate * 100:.2f}%), "
                    f"SL={stop_loss_price:.0f}円(+{(stop_loss_price - average_entry_price) / average_entry_price * 100:.2f}%)"
                )

            else:
                self.logger.error(f"❌ 不正な注文サイド: {side}")
                return {
                    "take_profit_price": 0.0,
                    "stop_loss_price": 0.0,
                    "tp_rate": 0.0,
                    "sl_rate": 0.0,
                }

            # 価格の妥当性チェック
            if take_profit_price <= 0 or stop_loss_price <= 0:
                self.logger.error(
                    f"❌ 不正なTP/SL価格: TP={take_profit_price}, SL={stop_loss_price}"
                )
                return {
                    "take_profit_price": 0.0,
                    "stop_loss_price": 0.0,
                    "tp_rate": tp_rate,
                    "sl_rate": sl_rate,
                }

            return {
                "take_profit_price": take_profit_price,
                "stop_loss_price": stop_loss_price,
                "tp_rate": tp_rate,
                "sl_rate": sl_rate,
            }

        except Exception as e:
            self.logger.error(f"❌ 統合TP/SL価格計算エラー: {e}")
            return {
                "take_profit_price": 0.0,
                "stop_loss_price": 0.0,
                "tp_rate": 0.0,
                "sl_rate": 0.0,
            }

"""
TP/SL設置・検証・復旧・クリーンアップの統合管理 - Phase 64.2

executor.pyから10メソッドを抽出し、TP/SLライフサイクル管理を集約。

責務:
- TP/SL欠損検出・自動再構築
- エントリー前の古いTP/SL注文クリーンアップ
- TP/SL検証スケジューリング・実行
- TP/SL定期ヘルスチェック

executor.pyに残る薄いラッパーメソッドから委譲される形で呼び出される。
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from ...core.config import get_threshold
from ...core.exceptions import CryptoBotError, TradingError
from ...core.logger import get_logger
from ...data.bitbank_client import BitbankClient
from ..core import ExecutionResult, TradeEvaluation
from .tp_sl_config import TPSLConfig


class TPSLManager:
    """TP/SL設置・検証・復旧・クリーンアップの統合管理"""

    def __init__(self):
        self.logger = get_logger()
        self._pending_verifications: List[Dict[str, Any]] = []
        self._last_tp_sl_check_time: Optional[datetime] = None

    # ========================================
    # Phase 64: 個別TP/SL配置メソッド（stop_manager.pyから移動）
    # ========================================

    async def place_take_profit(
        self,
        side: str,
        amount: float,
        entry_price: float,
        take_profit_price: float,
        symbol: str,
        bitbank_client: BitbankClient,
    ) -> Optional[Dict[str, Any]]:
        """
        個別TP注文配置（Phase 46・Phase 62.10: Maker戦略対応）

        Phase 62.10:
        - Maker戦略有効時: limit + post_only注文を試行
        - 失敗時: take_profitタイプにフォールバック

        Args:
            side: エントリーサイド (buy/sell)
            amount: 数量
            entry_price: エントリー価格
            take_profit_price: TP価格
            symbol: 通貨ペア
            bitbank_client: BitbankClientインスタンス

        Returns:
            Dict: TP注文情報 {"order_id": str, "price": float} or None
        """
        tp_config = get_threshold(TPSLConfig.TP_CONFIG, {})

        if not tp_config.get("enabled", True):
            self.logger.debug("TP配置無効（設定オフ）")
            return None

        if take_profit_price <= 0:
            raise TradingError("TP価格が不正（0以下）")

        # Phase 62.10: Maker戦略設定取得
        maker_config = tp_config.get("maker_strategy", {})
        use_maker = maker_config.get("enabled", False)

        if use_maker:
            # Maker戦略: limit + post_only
            result = await self._place_tp_maker(
                side, amount, take_profit_price, symbol, bitbank_client, maker_config
            )
            if result:
                return result

            # Maker失敗時フォールバック
            if maker_config.get("fallback_to_native", True):
                self.logger.info("📡 Phase 62.10: TP Maker失敗 → take_profitフォールバック")
            else:
                raise TradingError("TP Maker失敗・フォールバック無効")

        # 従来方式: take_profitタイプ
        return await self._place_tp_native(side, amount, take_profit_price, symbol, bitbank_client)

    async def _place_tp_maker(
        self,
        side: str,
        amount: float,
        take_profit_price: float,
        symbol: str,
        bitbank_client: BitbankClient,
        config: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Phase 62.10: TP Maker注文（limit + post_only）

        Maker約定のみを許可する注文を発行し、リトライを行う。

        Args:
            side: エントリーサイド (buy/sell)
            amount: 数量
            take_profit_price: TP価格
            symbol: 通貨ペア
            bitbank_client: BitbankClientインスタンス
            config: Maker戦略設定

        Returns:
            Dict: TP注文情報 {"order_id": str, "price": float} or None
        """
        from datetime import datetime as dt_cls

        from src.core.exceptions import PostOnlyCancelledException

        max_retries = config.get("max_retries", 2)
        retry_interval = config.get("retry_interval_ms", 300) / 1000
        timeout = config.get("timeout_seconds", 10)

        start = dt_cls.now()

        for attempt in range(max_retries):
            if (dt_cls.now() - start).total_seconds() >= timeout:
                self.logger.warning(f"⏰ Phase 62.10: TP Makerタイムアウト - {timeout}秒経過")
                return None

            try:
                tp_order = await asyncio.to_thread(
                    bitbank_client.create_take_profit_order,
                    entry_side=side,
                    amount=amount,
                    take_profit_price=take_profit_price,
                    symbol=symbol,
                    post_only=True,
                )

                order_id = tp_order.get("id")

                if not order_id:
                    raise Exception(f"TP Maker注文配置失敗（order_idが空）: API応答={tp_order}")

                self.logger.info(
                    f"✅ Phase 62.10: TP Maker配置成功 - "
                    f"ID: {order_id}, 価格: {take_profit_price:.0f}円, "
                    f"試行: {attempt + 1}/{max_retries}"
                )
                return {"order_id": order_id, "price": take_profit_price}

            except PostOnlyCancelledException:
                self.logger.info(
                    f"📡 Phase 62.10: TP post_onlyキャンセル "
                    f"（試行{attempt + 1}/{max_retries}）"
                )
            except Exception as e:
                self.logger.warning(
                    f"⚠️ Phase 62.10: TP Makerエラー " f"（試行{attempt + 1}/{max_retries}）: {e}"
                )

            if attempt < max_retries - 1:
                await asyncio.sleep(retry_interval)

        self.logger.warning(f"⚠️ Phase 62.10: TP Maker全{max_retries}回失敗")
        return None

    async def _place_tp_native(
        self,
        side: str,
        amount: float,
        take_profit_price: float,
        symbol: str,
        bitbank_client: BitbankClient,
    ) -> Optional[Dict[str, Any]]:
        """
        Phase 62.10: TP従来注文（take_profitタイプ）

        Args:
            side: エントリーサイド (buy/sell)
            amount: 数量
            take_profit_price: TP価格
            symbol: 通貨ペア
            bitbank_client: BitbankClientインスタンス

        Returns:
            Dict: TP注文情報 {"order_id": str, "price": float} or None
        """
        tp_order = await asyncio.to_thread(
            bitbank_client.create_take_profit_order,
            entry_side=side,
            amount=amount,
            take_profit_price=take_profit_price,
            symbol=symbol,
            post_only=False,
        )

        order_id = tp_order.get("id")

        # Phase 57.11: 注文ID null check強化
        if not order_id:
            raise Exception(
                f"TP注文配置失敗（order_idが空）: API応答={tp_order}, "
                f"サイド={side}, 数量={amount:.6f} BTC, TP価格={take_profit_price:.0f}円"
            )

        self.logger.info(
            f"✅ Phase 46: 個別TP配置成功 - ID: {order_id}, "
            f"サイド: {side}, 数量: {amount:.6f} BTC, TP価格: {take_profit_price:.0f}円"
        )

        return {"order_id": order_id, "price": take_profit_price}

    async def place_stop_loss(
        self,
        side: str,
        amount: float,
        entry_price: float,
        stop_loss_price: float,
        symbol: str,
        bitbank_client: BitbankClient,
    ) -> Optional[Dict[str, Any]]:
        """
        個別SL注文配置（Phase 51.6強化: SL価格検証・エラー30101対策）
        Phase 62.17: sl_placed_at追加（タイムアウトチェック用）

        Args:
            side: エントリーサイド (buy/sell)
            amount: 数量
            entry_price: エントリー価格
            stop_loss_price: SL価格
            symbol: 通貨ペア
            bitbank_client: BitbankClientインスタンス

        Returns:
            Dict: SL注文情報 {"order_id": str, "price": float, "sl_placed_at": str} or None
        """
        sl_config = get_threshold(TPSLConfig.SL_CONFIG, {})

        if not sl_config.get("enabled", True):
            self.logger.debug("SL配置無効（設定オフ）")
            return None

        # Phase 51.6: SL価格検証強化（None/0/負の値チェック）
        if stop_loss_price is None:
            raise TradingError("SL価格がNone（エラー30101対策）")

        if stop_loss_price <= 0:
            raise TradingError(
                f"SL価格が不正（0以下）: {stop_loss_price}円 - エントリー: {entry_price:.0f}円"
            )

        # Phase 51.6: エントリー価格との妥当性チェック
        if side.lower() == "buy" and stop_loss_price >= entry_price:
            raise TradingError(
                f"SL価格が不正（BUY時はエントリー価格より低い必要）: "
                f"SL={stop_loss_price:.0f}円 >= Entry={entry_price:.0f}円"
            )
        elif side.lower() == "sell" and stop_loss_price <= entry_price:
            raise TradingError(
                f"SL価格が不正（SELL時はエントリー価格より高い必要）: "
                f"SL={stop_loss_price:.0f}円 <= Entry={entry_price:.0f}円"
            )

        # Phase 51.6: SL距離の合理性チェック（極端な値の検出）
        sl_distance_ratio = abs(stop_loss_price - entry_price) / entry_price
        max_sl_ratio = get_threshold(TPSLConfig.SL_MAX_LOSS_RATIO, 0.007)

        if sl_distance_ratio < TPSLConfig.SL_MIN_DISTANCE_WARNING:
            self.logger.warning(
                f"⚠️ SL価格が極端に近い: {sl_distance_ratio * 100:.3f}% "
                f"(SL: {stop_loss_price:.0f}円, Entry: {entry_price:.0f}円)"
            )
        elif sl_distance_ratio > max_sl_ratio * 3:  # 設定値の3倍以上（極端に遠い）
            self.logger.warning(
                f"⚠️ SL価格が極端に遠い: {sl_distance_ratio * 100:.2f}% > {max_sl_ratio * 3 * 100:.1f}% "
                f"(SL: {stop_loss_price:.0f}円, Entry: {entry_price:.0f}円)"
            )

        # Phase 59.6: SL指値化設定取得
        sl_order_type = sl_config.get("order_type", "stop")
        slippage_buffer = sl_config.get("slippage_buffer", 0.001)

        # stop_limit時の指値価格計算
        limit_price = None
        if sl_order_type == "stop_limit":
            if side.lower() == "buy":
                # ロングポジションのSL（売り決済）：トリガー価格より低い指値
                limit_price = stop_loss_price * (1 - slippage_buffer)
            else:
                # ショートポジションのSL（買い決済）：トリガー価格より高い指値
                limit_price = stop_loss_price * (1 + slippage_buffer)

            self.logger.info(
                f"📊 Phase 59.6: SL指値化 - order_type={sl_order_type}, "
                f"trigger={stop_loss_price:.0f}円, limit={limit_price:.0f}円"
            )

        # SL注文配置
        sl_order = bitbank_client.create_stop_loss_order(
            entry_side=side,
            amount=amount,
            stop_loss_price=stop_loss_price,
            symbol=symbol,
            order_type=sl_order_type,
            limit_price=limit_price,
        )

        order_id = sl_order.get("id")

        # Phase 57.11: 注文ID null check強化（SL未設置問題対策）
        if not order_id:
            raise TradingError(
                f"SL注文配置失敗（order_idが空）: API応答={sl_order}, "
                f"サイド={side}, 数量={amount:.6f} BTC, SL価格={stop_loss_price:.0f}円"
            )

        # Phase 62.17: SL配置時刻を記録（タイムアウトチェック用）
        sl_placed_at = datetime.now(timezone.utc).isoformat()

        self.logger.info(
            f"✅ Phase 46: 個別SL配置成功 - ID: {order_id}, "
            f"サイド: {side}, 数量: {amount:.6f} BTC, SL価格: {stop_loss_price:.0f}円",
            extra_data={
                "sl_order_id": order_id,
                "trigger_price": stop_loss_price,
                "entry_side": side,
                "amount": amount,
            },
        )

        return {
            "order_id": order_id,
            "price": stop_loss_price,
            "sl_placed_at": sl_placed_at,  # Phase 62.17: タイムアウトチェック用
        }

    # ========================================
    # TP/SL配置（リトライ付き）
    # ========================================

    async def place_tp_with_retry(
        self,
        side: str,
        amount: float,
        entry_price: float,
        take_profit_price: float,
        symbol: str,
        bitbank_client: BitbankClient,
        max_retries: int = 3,
    ) -> Optional[Dict[str, Any]]:
        """
        TP注文配置（Exponential Backoff リトライ）

        Args:
            side: エントリーサイド (buy/sell)
            amount: 数量
            entry_price: エントリー価格
            take_profit_price: TP価格
            symbol: 通貨ペア
            bitbank_client: BitbankClientインスタンス
            max_retries: 最大リトライ回数（デフォルト3回）

        Returns:
            Dict: TP注文情報 {"order_id": str, "price": float} or None
        """
        for attempt in range(max_retries):
            try:
                tp_order = await self.place_take_profit(
                    side=side,
                    amount=amount,
                    entry_price=entry_price,
                    take_profit_price=take_profit_price,
                    symbol=symbol,
                    bitbank_client=bitbank_client,
                )
                if tp_order is None:
                    return None  # 設定無効 → 即時リターン（リトライ不要）
                if attempt > 0:
                    self.logger.info(
                        f"✅ Phase 51.6: TP配置成功（試行{attempt + 1}回目） - ID: {tp_order.get('order_id')}"
                    )
                return tp_order
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # 1秒, 2秒, 4秒
                    self.logger.warning(
                        f"⚠️ Phase 51.6: TP配置失敗（試行{attempt + 1}/{max_retries}）: {e} "
                        f"- {wait_time}秒後にリトライ"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"❌ Phase 51.6: TP配置失敗（全{max_retries}回試行）: {e}")
                    raise

        return None  # 到達不能（安全のため残す）

    async def place_sl_with_retry(
        self,
        side: str,
        amount: float,
        entry_price: float,
        stop_loss_price: float,
        symbol: str,
        bitbank_client: BitbankClient,
        max_retries: int = 3,
    ) -> Optional[Dict[str, Any]]:
        """
        SL注文配置（Exponential Backoff リトライ）

        Args:
            side: エントリーサイド (buy/sell)
            amount: 数量
            entry_price: エントリー価格
            stop_loss_price: SL価格
            symbol: 通貨ペア
            bitbank_client: BitbankClientインスタンス
            max_retries: 最大リトライ回数（デフォルト3回）

        Returns:
            Dict: SL注文情報 {"order_id": str, "price": float} or None
        """
        for attempt in range(max_retries):
            try:
                sl_order = await self.place_stop_loss(
                    side=side,
                    amount=amount,
                    entry_price=entry_price,
                    stop_loss_price=stop_loss_price,
                    symbol=symbol,
                    bitbank_client=bitbank_client,
                )
                if sl_order is None:
                    return None  # 設定無効 → 即時リターン（リトライ不要）
                if attempt > 0:
                    self.logger.info(
                        f"✅ Phase 51.6: SL配置成功（試行{attempt + 1}回目） - ID: {sl_order.get('order_id')}"
                    )
                return sl_order
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # 1秒, 2秒, 4秒
                    self.logger.warning(
                        f"⚠️ Phase 51.6: SL配置失敗（試行{attempt + 1}/{max_retries}）: {e} "
                        f"- {wait_time}秒後にリトライ"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"❌ Phase 51.6: SL配置失敗（全{max_retries}回試行）: {e}")
                    raise

        return None  # 到達不能（安全のため残す）

    # ========================================
    # 既存ポジションTP/SL確保
    # ========================================

    async def ensure_tp_sl_for_existing_positions(
        self,
        virtual_positions: List[Dict[str, Any]],
        bitbank_client: BitbankClient,
        position_tracker: Any,
        mode: str,
    ) -> None:
        """
        Phase 56.5: 既存ポジションのTP/SL確保

        起動時にTP/SL注文がないポジションを検出し、自動配置する。

        Args:
            virtual_positions: 仮想ポジションリスト（直接更新される）
            bitbank_client: BitbankClientインスタンス
            position_tracker: PositionTrackerインスタンス
            mode: 実行モード
        """
        if mode != "live":
            return

        try:
            # Step 1: 信用建玉情報取得
            margin_positions = await bitbank_client.fetch_margin_positions("BTC/JPY")

            if not margin_positions:
                self.logger.info("📊 Phase 56.5: 既存ポジションなし")
                return

            # Step 2: アクティブ注文取得（TP/SL存在確認用）
            active_orders = await asyncio.to_thread(
                bitbank_client.fetch_active_orders,
                "BTC/JPY",
                TPSLConfig.API_ORDER_LIMIT,
            )

            # Phase 64.3: サイド別合計でTP/SLカバレッジ判定（数量ベース）
            long_total = sum(
                float(p.get("amount", 0)) for p in margin_positions if p.get("side") == "long"
            )
            short_total = sum(
                float(p.get("amount", 0)) for p in margin_positions if p.get("side") == "short"
            )

            # exit側の注文合計
            tp_sell_total = sum(
                float(o.get("amount", 0))
                for o in active_orders
                if o.get("side") == "sell" and o.get("type") == "limit"
            )
            sl_sell_total = sum(
                float(o.get("amount", 0))
                for o in active_orders
                if o.get("side") == "sell" and o.get("type") in ("stop", "stop_limit")
            )
            tp_buy_total = sum(
                float(o.get("amount", 0))
                for o in active_orders
                if o.get("side") == "buy" and o.get("type") == "limit"
            )
            sl_buy_total = sum(
                float(o.get("amount", 0))
                for o in active_orders
                if o.get("side") == "buy" and o.get("type") in ("stop", "stop_limit")
            )

            # 95%カバレッジで判定（端数誤差許容）
            long_tp_ok = long_total <= 0 or tp_sell_total >= long_total * 0.95
            long_sl_ok = long_total <= 0 or sl_sell_total >= long_total * 0.95
            short_tp_ok = short_total <= 0 or tp_buy_total >= short_total * 0.95
            short_sl_ok = short_total <= 0 or sl_buy_total >= short_total * 0.95

            if long_tp_ok and long_sl_ok and short_tp_ok and short_sl_ok:
                self.logger.debug("✅ Phase 64.3: 全ポジションTP/SLカバレッジ確認済み")
                return

            # Step 3: 不足がある場合、サイド毎に1回だけ処理（重複配置防止）
            processed_sides = set()
            for position in margin_positions:
                position_side = position.get("side")  # "long" or "short"
                if position_side in processed_sides:
                    continue

                amount = float(position.get("amount", 0))
                avg_price = float(position.get("average_price", 0))
                if amount <= 0:
                    continue

                entry_side = "buy" if position_side == "long" else "sell"

                # Phase 63.5: restore済み＋TP/SL設置済みの場合のみスキップ
                already_restored = any(
                    vp.get("side") == entry_side
                    and vp.get("restored")
                    and vp.get("tp_order_id")
                    and vp.get("sl_order_id")
                    for vp in virtual_positions
                )
                if already_restored:
                    self.logger.debug(
                        f"✅ Phase 63.5: 復元済み＋TP/SL設置済み - "
                        f"{position_side} {amount:.4f} BTC"
                    )
                    continue

                if position_side == "long":
                    has_tp = long_tp_ok
                    has_sl = long_sl_ok
                    side_total = long_total
                else:
                    has_tp = short_tp_ok
                    has_sl = short_sl_ok
                    side_total = short_total

                if has_tp and has_sl:
                    continue

                # Step 4: 不足しているTP/SL注文を配置
                self.logger.info(
                    f"⚠️ Phase 64.3: TP/SLカバレッジ不足検出 - "
                    f"{position_side} 合計={side_total:.4f} BTC, "
                    f"TP={'OK' if has_tp else '不足'}, SL={'OK' if has_sl else '不足'}"
                )

                # Phase 63.5/63.6: 復元済みだがTP/SLいずれか欠損のvirtual_positionを削除
                virtual_positions[:] = [
                    vp
                    for vp in virtual_positions
                    if not (
                        vp.get("side") == entry_side
                        and (not vp.get("tp_order_id") or not vp.get("sl_order_id"))
                    )
                ]

                await self._place_missing_tp_sl(
                    position_side=position_side,
                    amount=side_total,
                    avg_price=avg_price,
                    has_tp=has_tp,
                    has_sl=has_sl,
                    virtual_positions=virtual_positions,
                    bitbank_client=bitbank_client,
                )
                processed_sides.add(position_side)

        except Exception as e:
            self.logger.warning(f"⚠️ Phase 56.5: 既存ポジションTP/SL確保失敗: {e}")

    def calculate_recovery_tp_sl_prices(
        self,
        position_side: str,
        avg_price: float,
        regime: str = "normal_range",
    ) -> Tuple[float, float]:
        """
        Phase 64.9: 復旧用TP/SL価格計算（デフォルト: normal_range = 安全側）

        Args:
            position_side: "long" or "short"
            avg_price: 平均取得価格
            regime: レジーム（デフォルト: normal_range）

        Returns:
            Tuple[float, float]: (tp_price, sl_price)
        """
        tp_ratio = get_threshold(
            TPSLConfig.tp_regime_path(regime, "min_profit_ratio"),
            TPSLConfig.DEFAULT_TP_RATIO,
        )
        sl_ratio = get_threshold(
            TPSLConfig.sl_regime_path(regime, "max_loss_ratio"),
            TPSLConfig.DEFAULT_SL_RATIO,
        )
        if position_side == "long":
            return avg_price * (1 + tp_ratio), avg_price * (1 - sl_ratio)
        else:
            return avg_price * (1 - tp_ratio), avg_price * (1 + sl_ratio)

    async def place_sl_or_market_close(
        self,
        entry_side: str,
        position_side: str,
        amount: float,
        avg_price: float,
        sl_price: float,
        symbol: str,
        bitbank_client: BitbankClient,
    ) -> Optional[Dict[str, Any]]:
        """
        Phase 64.4: SL配置（トリガー超過時は成行決済にフォールバック）

        Args:
            entry_side: エントリーサイド (buy/sell)
            position_side: ポジションサイド (long/short)
            amount: ポジション数量
            avg_price: 平均取得価格
            sl_price: SL価格
            symbol: 通貨ペア
            bitbank_client: BitbankClientインスタンス

        Returns:
            Dict: SL注文情報 or None
        """
        # ticker取得 → SL超過判定
        try:
            ticker = await asyncio.to_thread(bitbank_client.fetch_ticker, symbol)
            current_price = float(ticker.get("last", 0))
        except Exception:
            current_price = 0

        sl_breached = False
        if current_price > 0:
            if position_side == "long" and current_price <= sl_price:
                sl_breached = True
            elif position_side == "short" and current_price >= sl_price:
                sl_breached = True

        if sl_breached:
            # SL超過 → 成行決済
            self.logger.critical(
                f"🚨 Phase 64.4: SLトリガー超過 - 成行決済実行 "
                f"({position_side} {amount:.4f} BTC, "
                f"SL={sl_price:.0f}円, 現在={current_price:.0f}円)"
            )
            try:
                exit_side = "sell" if entry_side == "buy" else "buy"
                close_order = await asyncio.to_thread(
                    bitbank_client.create_order,
                    symbol=symbol,
                    order_type="market",
                    side=exit_side,
                    amount=amount,
                    is_closing_order=True,
                    entry_position_side=position_side,
                )
                return {"order_id": f"market_close_{close_order.get('id', 'unknown')}"}
            except Exception as e:
                self.logger.critical(f"🚨 Phase 64.4: 成行決済失敗 - 手動介入必要: {e}")
                return None
        else:
            # 通常SL配置
            try:
                sl_order = await self.place_stop_loss(
                    side=entry_side,
                    amount=amount,
                    entry_price=avg_price,
                    stop_loss_price=sl_price,
                    symbol=symbol,
                    bitbank_client=bitbank_client,
                )
                if sl_order:
                    self.logger.info(
                        f"✅ Phase 64.4: SL注文配置成功 - "
                        f"{position_side} {amount:.4f} BTC @ {sl_price:.0f}円"
                    )
                return sl_order
            except Exception as e:
                self.logger.error(f"❌ Phase 64.4: SL配置失敗: {e}")
                return None

    async def _place_missing_tp_sl(
        self,
        position_side: str,
        amount: float,
        avg_price: float,
        has_tp: bool,
        has_sl: bool,
        virtual_positions: List[Dict[str, Any]],
        bitbank_client: BitbankClient,
    ):
        """
        Phase 56.5: 不足しているTP/SL注文を配置

        Args:
            position_side: "long" or "short"
            amount: ポジション数量
            avg_price: 平均取得価格
            has_tp: TP注文が存在するか
            has_sl: SL注文が存在するか
            virtual_positions: 仮想ポジションリスト（直接更新）
            bitbank_client: BitbankClientインスタンス
        """
        symbol = get_threshold(TPSLConfig.CURRENCY_PAIR, "BTC/JPY")

        # Phase 64.9: 共通ヘルパーで計算（デフォルト: normal_range = 安全側）
        tp_price, sl_price = self.calculate_recovery_tp_sl_prices(
            position_side=position_side,
            avg_price=avg_price,
        )
        entry_side = "buy" if position_side == "long" else "sell"

        tp_order = None
        sl_order = None

        # TP配置
        if not has_tp:
            try:
                tp_order = await self.place_take_profit(
                    side=entry_side,
                    amount=amount,
                    entry_price=avg_price,
                    take_profit_price=tp_price,
                    symbol=symbol,
                    bitbank_client=bitbank_client,
                )
                if tp_order:
                    self.logger.info(
                        f"✅ Phase 56.5: TP注文配置成功 - "
                        f"{position_side} {amount:.4f} BTC @ {tp_price:.0f}円"
                    )
            except Exception as e:
                self.logger.error(f"❌ Phase 56.5: TP配置失敗: {e}")

        # SL配置（Phase 64.4: 共通ヘルパーに委譲）
        if not has_sl:
            sl_order = await self.place_sl_or_market_close(
                entry_side=entry_side,
                position_side=position_side,
                amount=amount,
                avg_price=avg_price,
                sl_price=sl_price,
                symbol=symbol,
                bitbank_client=bitbank_client,
            )

        # Phase 64.2: TP/SL両方成功した場合のみvirtual_positionsに追加
        tp_ok = has_tp or (tp_order and tp_order.get("order_id"))
        sl_ok = has_sl or (sl_order and sl_order.get("order_id"))

        if tp_ok and sl_ok:
            recovered_position = {
                "order_id": f"recovered_{position_side}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "side": entry_side,
                "amount": amount,
                "price": avg_price,
                "timestamp": datetime.now(),
                "take_profit": tp_price if not has_tp else None,
                "stop_loss": sl_price if not has_sl else None,
                "recovered": True,
                "tp_order_id": tp_order.get("order_id") if tp_order else None,
                "sl_order_id": sl_order.get("order_id") if sl_order else None,
                "sl_placed_at": sl_order.get("sl_placed_at") if sl_order else None,
            }
            virtual_positions.append(recovered_position)
            self.logger.info(
                f"✅ Phase 64.2: TP/SL復旧完了 - virtual_positions追加 "
                f"({position_side} {amount:.4f} BTC)"
            )
        else:
            self.logger.critical(
                f"🚨 Phase 64.2: TP/SL配置不完全（virtual_positions未追加・次回チェックで再試行）"
                f" - TP: {'OK' if tp_ok else 'NG'}, SL: {'OK' if sl_ok else 'NG'}"
                f" ({position_side} {amount:.4f} BTC)"
            )

    # ========================================
    # エントリー前TP/SLクリーンアップ
    # ========================================

    async def cleanup_old_tp_sl_before_entry(
        self,
        side: str,
        symbol: str,
        entry_order_id: str,
        virtual_positions: List[Dict[str, Any]],
        bitbank_client: BitbankClient,
    ) -> None:
        """
        Phase 51.10-A: エントリー前の古いTP/SL注文クリーンアップ

        同一ポジション側（BUY or SELL）の古い未約定TP/SL注文を削除する。

        Args:
            side: エントリーサイド (buy/sell)
            symbol: 通貨ペア
            entry_order_id: 今回のエントリー注文ID（ログ用）
            virtual_positions: 仮想ポジションリスト
            bitbank_client: BitbankClientインスタンス
        """
        try:
            active_orders = await asyncio.to_thread(
                bitbank_client.fetch_active_orders,
                symbol,
                TPSLConfig.API_ORDER_LIMIT,
            )

            if not active_orders:
                self.logger.debug("📋 Phase 51.10-A: アクティブ注文なし - クリーンアップ不要")
                return

            target_tp_side = "sell" if side == "buy" else "buy"
            target_sl_side = "sell" if side == "buy" else "buy"

            # 保護対象の注文IDを収集
            protected_order_ids = set()
            if virtual_positions:
                for pos in virtual_positions:
                    tp_id = pos.get("tp_order_id")
                    sl_id = pos.get("sl_order_id")
                    if tp_id:
                        protected_order_ids.add(str(tp_id))
                    if sl_id:
                        protected_order_ids.add(str(sl_id))

                    if pos.get("restored"):
                        order_id = pos.get("order_id")
                        if order_id:
                            protected_order_ids.add(str(order_id))
                            self.logger.debug(
                                f"🛡️ Phase 58.1: 復元ポジション保護 - order_id={order_id}"
                            )

            if protected_order_ids:
                self.logger.info(
                    f"🛡️ Phase 53.12: {len(protected_order_ids)}件の注文を保護対象に設定"
                )

            # 削除対象の注文を収集
            orders_to_cancel = []
            for order in active_orders:
                order_id = str(order.get("id", order.get("order_id", "")))
                order_side = order.get("side", "")
                order_type = order.get("type", "")

                if order_id in protected_order_ids:
                    continue

                is_tp = order_type == "limit" and order_side == target_tp_side
                is_sl = order_type == "stop" and order_side == target_sl_side

                if is_tp or is_sl:
                    orders_to_cancel.append(
                        {
                            "order_id": order_id,
                            "side": order_side,
                            "type": order_type,
                            "price": order.get("price"),
                        }
                    )

            if not orders_to_cancel:
                self.logger.info(
                    f"✅ Phase 51.10-A: クリーンアップ不要 - "
                    f"{side}側の古いTP/SL注文なし（Entry: {entry_order_id}）"
                )
                return

            cancel_success = 0
            cancel_fail = 0

            for order in orders_to_cancel:
                try:
                    await asyncio.to_thread(bitbank_client.cancel_order, order["order_id"], symbol)
                    cancel_success += 1
                    self.logger.info(
                        f"🗑️ Phase 51.10-A: 古いTP/SL削除成功 - "
                        f"ID: {order['order_id']}, "
                        f"Type: {order['type']}, "
                        f"Price: {order.get('price', 'N/A')}"
                    )
                except Exception as e:
                    cancel_fail += 1
                    self.logger.warning(
                        f"⚠️ Phase 51.10-A: TP/SL削除失敗（継続） - "
                        f"ID: {order['order_id']}, エラー: {e}"
                    )

            self.logger.info(
                f"✅ Phase 51.10-A: クリーンアップ完了 - "
                f"{side}側 {cancel_success}件削除成功・{cancel_fail}件失敗 "
                f"（Entry: {entry_order_id}）"
            )

        except Exception as e:
            self.logger.warning(
                f"⚠️ Phase 51.10-A: エントリー前クリーンアップ失敗（処理継続） - "
                f"Entry: {entry_order_id}, エラー: {e}"
            )

    # ========================================
    # TP/SL検証スケジューリング
    # ========================================

    def schedule_tp_sl_verification(
        self,
        entry_order_id: str,
        side: str,
        amount: float,
        entry_price: float,
        tp_order_id: Optional[str],
        sl_order_id: Optional[str],
        symbol: str,
    ) -> None:
        """
        Phase 62.20: TP/SL欠損検証をスケジュール

        Atomic Entry完了後、10分後にTP/SL設置状態を再確認し、
        欠損があれば自動的に再構築する。

        Args:
            entry_order_id: エントリー注文ID
            side: 売買方向（buy/sell）
            amount: ポジション数量
            entry_price: エントリー価格
            tp_order_id: TP注文ID
            sl_order_id: SL注文ID
            symbol: 通貨ペア
        """
        delay_seconds = get_threshold(TPSLConfig.VERIFICATION_DELAY, 600)

        self._pending_verifications.append(
            {
                "scheduled_at": datetime.now(timezone.utc),
                "verify_after": datetime.now(timezone.utc) + timedelta(seconds=delay_seconds),
                "entry_order_id": entry_order_id,
                "side": side,
                "amount": amount,
                "entry_price": entry_price,
                "expected_tp_order_id": tp_order_id,
                "expected_sl_order_id": sl_order_id,
                "symbol": symbol,
            }
        )

        self.logger.info(
            f"📋 Phase 63: TP/SL検証スケジュール - {delay_seconds}秒後 "
            f"(Entry: {entry_order_id}, pending: {len(self._pending_verifications)}件)"
        )

    async def process_pending_verifications(
        self,
        bitbank_client: BitbankClient,
        virtual_positions: Optional[List[Dict[str, Any]]] = None,
        position_tracker: Any = None,
    ):
        """
        Phase 63: メインサイクルで期限到来の検証を処理

        Args:
            bitbank_client: BitbankClientインスタンス
            virtual_positions: 仮想ポジションリスト（Phase 64.4追加）
            position_tracker: PositionTrackerインスタンス（Phase 64.4追加）
        """
        if not self._pending_verifications:
            return

        now = datetime.now(timezone.utc)
        due = [v for v in self._pending_verifications if now >= v["verify_after"]]
        self._pending_verifications = [
            v for v in self._pending_verifications if now < v["verify_after"]
        ]

        if due:
            self.logger.info(f"🔍 Phase 63: TP/SL検証実行 - {len(due)}件期限到来")

        for v in due:
            try:
                await self._verify_and_rebuild_tp_sl(
                    entry_order_id=v["entry_order_id"],
                    side=v["side"],
                    symbol=v["symbol"],
                    bitbank_client=bitbank_client,
                    virtual_positions=virtual_positions,
                    position_tracker=position_tracker,
                )
            except Exception as e:
                self.logger.error(
                    f"❌ Phase 63: TP/SL検証エラー - Entry: {v['entry_order_id']}, {e}"
                )

    async def _verify_and_rebuild_tp_sl(
        self,
        entry_order_id: str,
        side: str,
        symbol: str,
        bitbank_client: BitbankClient,
        virtual_positions: Optional[List[Dict[str, Any]]] = None,
        position_tracker: Any = None,
    ) -> None:
        """
        Phase 64.4: TP/SL欠損検証（ensure_tp_sl_for_existing_positionsに委譲）

        ポジション存在確認後、統合チェック（数量ベース・SL超過対応・VP更新込み）に委譲。

        Args:
            entry_order_id: エントリー注文ID
            side: 売買方向（buy/sell）
            symbol: 通貨ペア
            bitbank_client: BitbankClientインスタンス
            virtual_positions: 仮想ポジションリスト
            position_tracker: PositionTrackerインスタンス
        """
        try:
            self.logger.info(f"🔍 Phase 63: TP/SL検証開始 - Entry: {entry_order_id}")

            # ポジション存在確認（決済済みなら検証不要）
            positions = await bitbank_client.fetch_margin_positions(symbol)
            expected_pos_side = "long" if side == "buy" else "short"
            if not any(
                p.get("side") == expected_pos_side and float(p.get("amount", 0)) > 0
                for p in (positions or [])
            ):
                self.logger.info(f"✅ Phase 62.20: ポジションなし - Entry: {entry_order_id}")
                return

            # 統合チェックに委譲（数量ベース・SL超過対応・VP更新込み）
            await self.ensure_tp_sl_for_existing_positions(
                virtual_positions=virtual_positions or [],
                bitbank_client=bitbank_client,
                position_tracker=position_tracker,
                mode="live",
            )

        except Exception as e:
            self.logger.error(f"❌ Phase 62.20: TP/SL検証エラー - Entry: {entry_order_id}, {e}")

    # ========================================
    # TP/SL定期ヘルスチェック
    # ========================================

    async def periodic_tp_sl_check(
        self,
        virtual_positions: List[Dict[str, Any]],
        bitbank_client: BitbankClient,
        position_tracker: Any,
        mode: str,
    ) -> None:
        """
        Phase 63.6: TP/SL健全性定期チェック（10分間隔）

        virtual_positionsに存在するポジションのTP/SL注文がbitbank上に存在するか確認。

        Args:
            virtual_positions: 仮想ポジションリスト
            bitbank_client: BitbankClientインスタンス
            position_tracker: PositionTrackerインスタンス
            mode: 実行モード
        """
        now = datetime.now()
        check_interval = get_threshold(TPSLConfig.CHECK_INTERVAL, 600)

        if (
            self._last_tp_sl_check_time
            and (now - self._last_tp_sl_check_time).total_seconds() < check_interval
        ):
            return

        self._last_tp_sl_check_time = now

        self.logger.debug("🔍 Phase 63.6: TP/SL健全性定期チェック開始")
        await self.ensure_tp_sl_for_existing_positions(
            virtual_positions=virtual_positions,
            bitbank_client=bitbank_client,
            position_tracker=position_tracker,
            mode=mode,
        )

    # ========================================
    # Phase 51.6: TP/SL再計算（3段階ATRフォールバック）
    # ========================================

    async def calculate_tp_sl_for_live_trade(
        self,
        evaluation: TradeEvaluation,
        result: ExecutionResult,
        side: str,
        amount: float,
        bitbank_client: BitbankClient,
        current_time: Any = None,
    ) -> Tuple[float, float]:
        """
        Phase 51.6: ライブトレードTP/SL再計算（3段階ATRフォールバック）

        Args:
            evaluation: 取引評価
            result: 注文実行結果
            side: 取引方向（buy/sell）
            amount: 取引数量
            bitbank_client: BitbankClientインスタンス
            current_time: 現在時刻（バックテスト用）

        Returns:
            Tuple[float, float]: (final_tp, final_sl)

        Raises:
            CryptoBotError: ATR取得失敗・TP/SL再計算失敗時
        """
        # Phase 38.7: 実約定価格ベースでTP/SL再計算（SL距離5x誤差修正）
        # Phase 51.5-C: TP/SL再計算強化（3段階ATRフォールバック + 再計算必須化）
        actual_filled_price = result.filled_price or result.price

        # 実約定価格でTP/SL価格を再計算
        recalculated_tp = None
        recalculated_sl = None

        if actual_filled_price > 0 and evaluation.take_profit and evaluation.stop_loss:
            from ...strategies.utils.strategy_utils import RiskManager
            from ..core.types import PositionFeeData

            # ATR値とATR履歴を取得（3段階フォールバック）
            market_conditions = getattr(evaluation, "market_conditions", {})
            market_data = market_conditions.get("market_data", {})

            # Phase 61.7: 固定金額TPモード用の手数料データ取得
            fee_data = None
            fixed_amount_enabled = get_threshold(
                "position_management.take_profit.fixed_amount.enabled", False
            )

            if fixed_amount_enabled and bitbank_client:
                try:
                    positions = await bitbank_client.fetch_margin_positions("BTC/JPY")
                    for pos in positions:
                        raw_data = pos.get("raw_data", {})
                        pos_side = raw_data.get("position_side", "")
                        # ポジション方向でマッチング（buy→long, sell→short）
                        if (side == "buy" and pos_side == "long") or (
                            side == "sell" and pos_side == "short"
                        ):
                            fee_data = PositionFeeData.from_api_response(raw_data)
                            self.logger.info(
                                f"📊 Phase 63.2: 手数料データ取得（参考値・TP計算には未使用） - "
                                f"累積手数料={fee_data.unrealized_fee_amount:.0f}円, "
                                f"累積利息={fee_data.unrealized_interest_amount:.0f}円"
                            )
                            break
                except Exception as e:
                    self.logger.warning(
                        f"⚠️ Phase 61.7: 手数料データ取得失敗 - フォールバック使用: {e}"
                    )

            current_atr = None
            atr_history = None
            atr_source = None  # デバッグ用：ATR取得元

            # Phase 62.13: Level 0（最優先）- market_conditions["atr_current"]から直接取得
            # RiskManager.evaluate_trade_opportunity()で既に計算・格納済みの値を使用
            atr_current_value = market_conditions.get("atr_current")
            if atr_current_value and atr_current_value > 0:
                current_atr = float(atr_current_value)
                atr_source = "market_conditions[atr_current]"
                self.logger.info(f"📊 Phase 62.13: ATR取得成功 - atr_current={current_atr:.0f}円")

            # Phase 51.5-C → Phase 61.6: 2段階ATRフォールバック（Level 2削除）
            # Level 1: evaluation.market_conditions から取得（後方互換）
            if not current_atr and "15m" in market_data:
                df_15m = market_data["15m"]
                if "atr_14" in df_15m.columns and len(df_15m) > 0:
                    current_atr = float(df_15m["atr_14"].iloc[-1])
                    atr_history = df_15m["atr_14"].dropna().tail(20).tolist()
                    atr_source = "evaluation.market_conditions[15m]"

            if not current_atr and "4h" in market_data:
                df_4h = market_data["4h"]
                if "atr_14" in df_4h.columns and len(df_4h) > 0:
                    current_atr = float(df_4h["atr_14"].iloc[-1])
                    atr_source = "evaluation.market_conditions[4h]"

            # Level 2: thresholds.yaml fallback_atr使用（Phase 61.6: Level 2→削除、Level 3→Level 2に繰り上げ）
            if not current_atr:
                try:
                    fallback_atr = float(get_threshold(TPSLConfig.FALLBACK_ATR, 500000))
                except (ValueError, TypeError):
                    # 型変換失敗時はデフォルト値使用
                    fallback_atr = 500000.0
                    self.logger.warning(
                        "⚠️ Phase 51.5-C: fallback_atr型変換失敗 - デフォルト値500,000円使用"
                    )
                current_atr = fallback_atr
                atr_source = "thresholds.yaml[fallback_atr]"
                self.logger.warning(
                    f"⚠️ Phase 51.5-C: フォールバックATR使用 - fallback_atr={fallback_atr:.0f}円"
                )

            # ATR取得完了（2段階いずれかで取得）
            if current_atr and current_atr > 0:
                # Phase 51.6: TP/SL設定完全渡し（ハードコード削除・設定ファイル一元管理）
                # Phase 52.0: レジーム情報取得追加
                config = {
                    # TP設定（Phase 51.6: TP 0.9%・RR比1.29:1）
                    "take_profit_ratio": get_threshold(
                        "position_management.take_profit.default_ratio"
                    ),
                    "min_profit_ratio": get_threshold(TPSLConfig.TP_MIN_PROFIT_RATIO),
                    # SL設定（Phase 51.6: SL 0.7%）
                    "max_loss_ratio": get_threshold(TPSLConfig.SL_MAX_LOSS_RATIO),
                    "min_distance_ratio": get_threshold(TPSLConfig.SL_MIN_DISTANCE_RATIO),
                    "default_atr_multiplier": get_threshold(TPSLConfig.SL_DEFAULT_ATR_MULTIPLIER),
                }

                # Phase 52.0: レジーム情報取得
                regime = market_conditions.get("regime", None)
                regime_str = None
                if regime:
                    # RegimeType enumの場合は文字列に変換
                    regime_str = regime.value if hasattr(regime, "value") else str(regime)
                    self.logger.info(f"🎯 Phase 52.0: レジーム情報取得 - {regime_str}")

                # Phase 52.0: レジーム情報を含めてTP/SL計算
                # Phase 58.6: 土日判定用にcurrent_time追加
                # Phase 61.7: 固定金額TP用にfee_data, position_amount追加
                recalculated_sl, recalculated_tp = RiskManager.calculate_stop_loss_take_profit(
                    side,
                    actual_filled_price,
                    current_atr,
                    config,
                    atr_history,
                    regime=regime_str,
                    current_time=current_time,
                    fee_data=fee_data,
                    position_amount=amount,
                )

                # 再計算成功時、ログ出力
                if recalculated_sl and recalculated_tp:
                    original_sl = evaluation.stop_loss
                    original_tp = evaluation.take_profit
                    sl_diff = abs(recalculated_sl - original_sl)
                    tp_diff = abs(recalculated_tp - original_tp)

                    # 価格差異計算（entry_priceがある場合）
                    if evaluation.entry_price is not None:
                        entry_price_val = float(evaluation.entry_price)
                        actual_price_val = float(actual_filled_price)
                        price_diff = abs(actual_price_val - entry_price_val)
                        price_info = (
                            f"価格: シグナル時={entry_price_val:.0f}円"
                            f"→実約定={actual_price_val:.0f}円 (差{price_diff:.0f}円) | "
                        )
                    else:
                        actual_price_val = float(actual_filled_price)
                        price_info = f"実約定価格={actual_price_val:.0f}円 | "

                    self.logger.info(
                        f"🔄 Phase 51.5-C: 実約定価格ベースTP/SL再計算完了 - "
                        f"ATR取得元={atr_source}, ATR={current_atr:.0f}円 | "
                        f"{price_info}"
                        f"SL: {original_sl:.0f}円→{recalculated_sl:.0f}円 (差{sl_diff:.0f}円) | "
                        f"TP: {original_tp:.0f}円→{recalculated_tp:.0f}円 (差{tp_diff:.0f}円)"
                    )
                else:
                    # Phase 51.5-C: 再計算失敗時のハンドリング
                    require_recalc = get_threshold(TPSLConfig.REQUIRE_TPSL_RECALCULATION, True)
                    if require_recalc:
                        # 再計算必須モード：エントリー中止
                        self.logger.error(
                            f"❌ Phase 51.5-C: TP/SL再計算失敗（require_tpsl_recalculation=True） - "
                            f"ATR={current_atr:.0f}円・エントリー中止"
                        )
                        raise CryptoBotError("TP/SL再計算失敗によりエントリー中止")
                    else:
                        # 再計算任意モード：元のTP/SL使用
                        self.logger.warning(
                            f"⚠️ Phase 51.5-C: TP/SL再計算失敗（RiskManager戻り値None） - "
                            f"ATR={current_atr:.0f}円・元のTP/SL使用継続"
                        )
            else:
                # Phase 51.5-C: ATR取得失敗時のハンドリング
                require_recalc = get_threshold(TPSLConfig.REQUIRE_TPSL_RECALCULATION, True)
                if require_recalc:
                    # 再計算必須モード：エントリー中止
                    self.logger.error(
                        f"❌ Phase 51.5-C: ATR取得失敗（require_tpsl_recalculation=True） - "
                        f"current_atr={current_atr}・エントリー中止"
                    )
                    raise CryptoBotError("ATR取得失敗によりエントリー中止")
                else:
                    # 再計算任意モード：元のTP/SL使用
                    self.logger.warning(
                        f"⚠️ Phase 51.5-C: ATR取得失敗（current_atr={current_atr}） - "
                        f"実約定価格ベースTP/SL再計算スキップ・元のTP/SL使用継続"
                    )

        # 再計算された値を使用（失敗時は元の値）
        final_tp = recalculated_tp if recalculated_tp else evaluation.take_profit
        final_sl = recalculated_sl if recalculated_sl else evaluation.stop_loss

        return final_tp, final_sl

    async def rollback_entry(
        self,
        entry_order_id: Optional[str],
        tp_order_id: Optional[str],
        sl_order_id: Optional[str],
        symbol: str,
        error: Exception,
        bitbank_client: BitbankClient,
    ) -> None:
        """
        Phase 51.6: Atomic Entry ロールバック

        エントリー・TP・SLのいずれかが失敗した場合、全ての注文をキャンセルする。

        Args:
            entry_order_id: エントリー注文ID
            tp_order_id: TP注文ID（配置済みの場合）
            sl_order_id: SL注文ID（配置済みの場合）
            symbol: 通貨ペア
            error: 発生したエラー
            bitbank_client: BitbankClientインスタンス
        """
        self.logger.error(
            f"🔄 Phase 51.6: Atomic Entry ロールバック開始 - "
            f"Entry: {entry_order_id}, TP: {tp_order_id}, SL: {sl_order_id}"
        )

        # TP注文キャンセル（配置済みの場合）
        if tp_order_id:
            try:
                await asyncio.to_thread(bitbank_client.cancel_order, tp_order_id, symbol)
                self.logger.info(f"✅ Phase 51.6: TP注文キャンセル成功 - ID: {tp_order_id}")
            except Exception as e:
                self.logger.warning(f"⚠️ Phase 51.6: TP注文キャンセル失敗: {e}")

        # SL注文キャンセル（配置済みの場合）
        if sl_order_id:
            try:
                await asyncio.to_thread(bitbank_client.cancel_order, sl_order_id, symbol)
                self.logger.info(f"✅ Phase 51.6: SL注文キャンセル成功 - ID: {sl_order_id}")
            except Exception as e:
                self.logger.warning(f"⚠️ Phase 51.6: SL注文キャンセル失敗: {e}")

        # エントリー注文キャンセル（最重要・Phase 57.11: リトライ追加）
        if entry_order_id:
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await asyncio.to_thread(bitbank_client.cancel_order, entry_order_id, symbol)
                    self.logger.error(
                        f"🚨 Phase 51.6: エントリー注文ロールバック成功 - "
                        f"ID: {entry_order_id}, 理由: {error}"
                        + (f" (試行{attempt + 1}回目)" if attempt > 0 else "")
                    )
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        wait_time = 2**attempt  # 1秒, 2秒
                        self.logger.warning(
                            f"⚠️ Phase 57.11: エントリーロールバック失敗（リトライ{attempt + 1}/{max_retries}）: {e}"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        # 全リトライ失敗は致命的エラー
                        self.logger.critical(
                            f"❌ CRITICAL: エントリー注文キャンセル失敗（手動介入必要） - "
                            f"ID: {entry_order_id}, 全{max_retries}回試行失敗, エラー: {e}"
                        )

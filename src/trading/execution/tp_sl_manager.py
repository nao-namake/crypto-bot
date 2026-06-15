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
from .sl_monitor import SLMonitor
from .sl_state_persistence import SLStatePersistence
from .tp_sl_config import TPSLConfig


class TPSLManager:
    """TP/SL設置・検証・復旧・クリーンアップの統合管理"""

    def __init__(self):
        self.logger = get_logger()
        self._pending_verifications: List[Dict[str, Any]] = []
        self._last_tp_sl_check_time: Optional[datetime] = None
        self.sl_persistence = SLStatePersistence()

        # Phase 87 C5: SL CANCELED_UNFILLED 検出 + 緊急成行決済（5分ループ統合）
        self.sl_monitor = SLMonitor(
            logger=self.logger,
            sl_persistence=self.sl_persistence,
            dry_run=bool(get_threshold("position_management.stop_loss.sl_monitor.dry_run", True)),
            timeout_hours=int(get_threshold("position_management.stop_loss.timeout_hours", 24)),
        )

    # ========================================
    # Phase 64: 個別TP/SL配置メソッド（stop_manager.pyから移動）
    # ========================================

    async def _check_position_exists(
        self,
        expected_amount: float,
        bitbank_client: BitbankClient,
    ) -> Tuple[bool, float]:
        """Phase 90γ-⑤: TP/SL 配置直前のポジション存在確認（50062 対策）。

        SL トリガー成行決済 → ポジ消滅後の同サイクル内で、別経路の TP/SL 配置試行が
        並行実行されると bitbank 50062「保有建玉数量超過」エラーが発生する。本関数は
        TP/SL 配置直前に実ポジション量を確認し、消滅検出時は配置を中止する。

        `_wait_position_reflected` は「ポジ増加方向の反映待ち」だが、本関数は
        「ポジ消滅方向の確定検出」を担う相補的な役割。

        Args:
            expected_amount: 期待されるポジション数量 (BTC)
            bitbank_client: BitbankClient インスタンス

        Returns:
            (exists, actual_amount): ポジ存在判定（閾値以上なら True）と実数量
        """
        try:
            positions = await bitbank_client.fetch_margin_positions()
            actual = sum(abs(float(p.get("amount", 0))) for p in positions or [])
        except Exception as e:
            self.logger.warning(
                f"⚠️ Phase 90γ-⑤: ポジション確認 API 失敗 - 配置続行（API再試行に委譲）: {e}"
            )
            return True, expected_amount

        threshold_ratio = float(
            get_threshold(
                "position_management.tp_sl_placement_guard.position_exists_threshold_ratio",
                0.5,
            )
        )
        exists = actual >= expected_amount * threshold_ratio
        return exists, actual

    async def _wait_position_reflected(
        self,
        expected_amount: float,
        bitbank_client: BitbankClient,
        max_wait_sec: int = 5,
    ) -> bool:
        """Phase 90γ-②: bitbank API へのポジション反映を待つ（50062 対策）。

        エントリー約定直後に TP/SL を配置すると、bitbank API のポジションが
        まだ反映されていない場合に 50062 (保有建玉数量超過) エラーが発生する。
        本関数は数秒間ポジション反映を待ち、TP/SL 配置失敗を防止する。

        Args:
            expected_amount: 期待されるポジション数量 (BTC)
            bitbank_client: BitbankClient インスタンス
            max_wait_sec: 最大待機秒数 (default: 5)

        Returns:
            True: ポジション反映確認 / False: タイムアウト（呼び出し側は処理続行）
        """
        for attempt in range(max_wait_sec):
            try:
                positions = await bitbank_client.fetch_margin_positions()
                actual = sum(abs(float(p.get("amount", 0))) for p in positions or [])
                if actual >= expected_amount * 0.95:
                    if attempt > 0:
                        self.logger.info(
                            f"✅ Phase 90γ-②: ポジション反映確認 "
                            f"({attempt + 1}s 後・actual={actual:.4f}/"
                            f"expected={expected_amount:.4f})"
                        )
                    return True
            except Exception as e:
                self.logger.debug(f"Phase 90γ-②: ポジション取得失敗 (attempt={attempt + 1}): {e}")
            # 最終 attempt 後の sleep は無駄なのでスキップ（タイムアウト時の 1 秒短縮）
            if attempt < max_wait_sec - 1:
                await asyncio.sleep(1.0)
        self.logger.warning(
            f"⚠️ Phase 90γ-②: ポジション反映待ちタイムアウト "
            f"({max_wait_sec}s 経過・expected={expected_amount:.4f}) → 配置試行続行"
        )
        return False

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

        # Phase 90γ-⑤: TP 配置前ポジション存在確認（SL 成行決済直後の 50062 対策）
        if get_threshold("position_management.tp_sl_placement_guard.enabled", True):
            exists, actual = await self._check_position_exists(amount, bitbank_client)
            if not exists:
                self.logger.warning(
                    f"⚠️ Phase 90γ-⑤: TP配置スキップ - ポジション消滅検出 "
                    f"(期待 {amount:.4f} > 実 {actual:.4f} BTC) - "
                    f"SL 成行決済等で消滅した可能性"
                )
                return None

        # Phase 90γ-②: bitbank API ポジション反映待ち（50062 対策）
        await self._wait_position_reflected(amount, bitbank_client)

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
        # Phase 87 C3: タイムアウト/リトライ時の確実キャンセル用に最後の order_id を保持
        last_order_id: Optional[str] = None

        async def _safe_cancel(order_id: Optional[str], context: str) -> None:
            """残存 TP Maker 注文を確実にキャンセル（重複TP配置防止）"""
            if not order_id:
                return
            try:
                await asyncio.to_thread(bitbank_client.cancel_order, str(order_id), symbol)
                self.logger.info(
                    f"✅ Phase 87 C3: TP Maker残注文キャンセル成功 "
                    f"(context={context}, ID={order_id})"
                )
            except Exception as cancel_err:
                # 既に約定済み・キャンセル済みの可能性 → warning にとどめる
                self.logger.warning(
                    f"⚠️ Phase 87 C3: TP Maker残注文キャンセル失敗 "
                    f"(context={context}, ID={order_id}): {cancel_err}"
                )

        for attempt in range(max_retries):
            if (dt_cls.now() - start).total_seconds() >= timeout:
                self.logger.warning(f"⏰ Phase 62.10: TP Makerタイムアウト - {timeout}秒経過")
                # Phase 87 C3: timeout 時も最後の order_id を確実キャンセル
                await _safe_cancel(last_order_id, "timeout")
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

                # 配置成功 → 旧 order_id を更新（成功時はそのまま返却するので保持不要）
                last_order_id = str(order_id)

                # Phase 90γ-⑥: info→warning（本番 LOG_LEVEL=WARNING で TP 約定価格を観察可能化）
                self.logger.warning(
                    f"✅ Phase 62.10: TP Maker配置成功 - "
                    f"ID: {order_id}, 価格: {take_profit_price:.0f}円, "
                    f"試行: {attempt + 1}/{max_retries}"
                )
                return {"order_id": order_id, "price": take_profit_price}

            except PostOnlyCancelledException:
                # post_only キャンセルは bitbank 側で完結しているため last_order_id はクリア
                last_order_id = None
                self.logger.info(
                    f"📡 Phase 62.10: TP post_onlyキャンセル "
                    f"（試行{attempt + 1}/{max_retries}）"
                )
            except Exception as e:
                # 配置途中の失敗 → 残存注文が存在する可能性 → 念のためキャンセル試行
                self.logger.warning(
                    f"⚠️ Phase 62.10: TP Makerエラー " f"（試行{attempt + 1}/{max_retries}）: {e}"
                )
                await _safe_cancel(last_order_id, f"retry_{attempt + 1}")
                last_order_id = None

            if attempt < max_retries - 1:
                await asyncio.sleep(retry_interval)

        self.logger.warning(f"⚠️ Phase 62.10: TP Maker全{max_retries}回失敗")
        # Phase 87 C3: 全試行失敗時も最終キャンセル
        await _safe_cancel(last_order_id, "final_failure")
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
            # Phase 82: 配置中止（旧: WARNINGログのみ → ダスト残渣で-88%SLを配置する事故が発生）
            raise TradingError(
                f"⛔ SL価格が極端に遠い（配置中止）: "
                f"{sl_distance_ratio * 100:.2f}% > {max_sl_ratio * 3 * 100:.1f}% "
                f"(SL: {stop_loss_price:.0f}円, Entry: {entry_price:.0f}円). "
                f"ダスト/微小ポジションまたは計算バグの可能性。"
            )

        # Phase 90γ-⑤: SL 配置前ポジション存在確認（並行成行決済との競合対策）
        if get_threshold("position_management.tp_sl_placement_guard.enabled", True):
            exists, actual = await self._check_position_exists(amount, bitbank_client)
            if not exists:
                self.logger.warning(
                    f"⚠️ Phase 90γ-⑤: SL配置スキップ - ポジション消滅検出 "
                    f"(期待 {amount:.4f} > 実 {actual:.4f} BTC) - "
                    f"並行成行決済等で消滅した可能性"
                )
                return None

        # Phase 90γ-②: bitbank API ポジション反映待ち（50062 対策）
        # 全バリデーション通過後に実行（不正データで無駄に 5 秒待たない）
        await self._wait_position_reflected(amount, bitbank_client)

        # Phase 87 H3: stop_limit 時の slippage_buffer 二重防衛
        # Phase 81: stop（成行）専用設計から拡張。order_type=stop_limit 時のみ limit_price 計算
        # Phase 78/80 ジレンマ完全解決: 通常時 stop_limit で確実約定 + 価格急変時の
        # CANCELED_UNFILLED は SLMonitor (C1/C5) で検出して緊急成行決済
        sl_order_type = sl_config.get("order_type", "stop")
        limit_price = None
        if sl_order_type == "stop_limit":
            slippage = float(sl_config.get("slippage_buffer", 0.008))
            if side.lower() == "buy":
                # BUY ポジション → sell SL → limit_price は stop_loss_price より低く
                limit_price = stop_loss_price * (1 - slippage)
            else:
                # SELL ポジション → buy SL → limit_price は stop_loss_price より高く
                limit_price = stop_loss_price * (1 + slippage)
            self.logger.info(
                f"📐 Phase 87 H3: stop_limit + slippage_buffer={slippage * 100:.1f}% "
                f"(stop={stop_loss_price:.0f}円, limit={limit_price:.0f}円)"
            )
        elif sl_order_type != "stop":
            # Phase 87 Stage 2-R3: 想定外の order_type を silent fall-through させない
            self.logger.warning(
                f"⚠️ Phase 87 Stage 2-R3: 想定外の sl_order_type='{sl_order_type}' "
                f"(期待: 'stop' or 'stop_limit')。limit_price=None で続行します。"
                f" thresholds.yaml の position_management.stop_loss.order_type を確認してください。"
            )

        # SL注文配置（Phase 65.5: asyncio.to_threadでラップ）
        sl_order = await asyncio.to_thread(
            bitbank_client.create_stop_loss_order,
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

        # Phase 68.4: SL永続化保存（INACTIVE SL対策）
        # Phase 69.6: sl_placed_atも永続化（Cloud Run再起動後のタイムアウト計算用）
        self.sl_persistence.save(
            side, str(order_id), stop_loss_price, amount, sl_placed_at=sl_placed_at
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
    # Phase 88 H11: 孤児SL注文の検出・キャンセル
    # ========================================

    # Phase R-C1: リトライ可能エラーのデフォルト patterns（小文字部分一致判定）
    # 70004=bitbank「取引一時停止」、suspended=同上、timeout/connection/rate=一時的ネットワーク系
    _DEFAULT_RETRYABLE_PATTERNS: tuple = (
        "70004",
        "suspended",
        "timeout",
        "connection",
        "rate limit",
    )

    # Phase 90λ: 「注文が既に存在しない」系エラー。孤児SLキャンセルの目的（注文消滅）が
    # 既に達成された状態のため失敗ではなく成功扱いとする（小文字部分一致）。
    _DEFAULT_ALREADY_RESOLVED_PATTERNS: tuple = (
        "50026",
        "order not found",
        "ordernotfound",
    )

    async def _detect_and_cancel_orphan_sl(
        self,
        margin_positions: List[Dict[str, Any]],
        active_orders: List[Dict[str, Any]],
        bitbank_client: BitbankClient,
        closed_order_ids: Optional[set] = None,
    ) -> None:
        """
        Phase 88 H11: 孤児SL注文（ポジション無しで残存）を検出してキャンセル。

        2026-05-14 09:05 BUYポジ TP約定後の SL cancel が bitbank 70004
        (transaction currently suspended) で失敗し12時間孤児SL放置事案の再発防止。

        Phase R-Hb: 部分ポジション close 時の誤判定を回避するため、
        「ポジション完全消失（合計=0）」のみを孤児扱いし、「ポジ>0 だが SL 過剰」は
        警告ログのみで cancel しない。
        Phase R-He: 同サイクル内で C5 が cancel/close した order id (closed_order_ids) を除外。
        Phase R-C1: リトライは retryable_patterns whitelist に該当する場合のみ。

        Args:
            margin_positions: 現在の信用建玉一覧
            active_orders: アクティブ注文一覧
            bitbank_client: BitbankClient
            closed_order_ids: 同サイクル内で既に cancel/close 済の order id セット（C5 干渉対策）
        """
        config = get_threshold("position_management.stop_loss.orphan_sl_order_scan", {})
        if not config.get("enabled", True):
            return

        closed_ids: set = closed_order_ids or set()

        # Phase R-Hb: ポジション合計量で判定（複数 VP / 部分 close 対応）
        long_total = sum(
            float(p.get("amount") or 0) for p in margin_positions if p.get("side") == "long"
        )
        short_total = sum(
            float(p.get("amount") or 0) for p in margin_positions if p.get("side") == "short"
        )

        sell_sl_orders = [
            o
            for o in active_orders
            if o.get("type") in ("stop", "stop_limit") and o.get("side") == "sell"
        ]
        buy_sl_orders = [
            o
            for o in active_orders
            if o.get("type") in ("stop", "stop_limit") and o.get("side") == "buy"
        ]
        sell_sl_total = sum(float(o.get("amount") or 0) for o in sell_sl_orders)
        buy_sl_total = sum(float(o.get("amount") or 0) for o in buy_sl_orders)

        orphan_orders: List[Dict[str, Any]] = []

        # 完全孤児: ポジション側が 0 で SL のみ残存 → 全件キャンセル対象
        if long_total <= 0 and sell_sl_orders:
            orphan_orders.extend(sell_sl_orders)
        elif long_total > 0 and sell_sl_total > long_total * 1.05:
            # 過剰 SL: cancel ではなく warning のみ（部分 close の正常範疇かもしれない）
            self.logger.warning(
                f"⚠️ Phase 88 H11: long ポジ用 sell SL 過剰検出（キャンセルせず観察） - "
                f"long_total={long_total:.4f} BTC, sell_sl_total={sell_sl_total:.4f} BTC"
            )

        if short_total <= 0 and buy_sl_orders:
            orphan_orders.extend(buy_sl_orders)
        elif short_total > 0 and buy_sl_total > short_total * 1.05:
            self.logger.warning(
                f"⚠️ Phase 88 H11: short ポジ用 buy SL 過剰検出（キャンセルせず観察） - "
                f"short_total={short_total:.4f} BTC, buy_sl_total={buy_sl_total:.4f} BTC"
            )

        # Phase R-He: C5 で既に cancel/close した order を除外
        if closed_ids:
            before = len(orphan_orders)
            orphan_orders = [o for o in orphan_orders if str(o.get("id", "")) not in closed_ids]
            skipped = before - len(orphan_orders)
            if skipped > 0:
                self.logger.info(
                    f"📌 Phase 88 H_e: C5 で処理済 order を孤児候補から除外 ({skipped} 件)"
                )

        if not orphan_orders:
            return

        self.logger.critical(
            f"🚨 Phase 88 H11: 孤児SL注文検出 - {len(orphan_orders)}件: "
            f"{[o.get('id') for o in orphan_orders]}"
        )

        max_retries = int(config.get("cancel_max_retries", 3))
        base_delay = float(config.get("cancel_base_delay_seconds", 1.0))
        retryable_patterns = tuple(
            config.get("retryable_patterns", self._DEFAULT_RETRYABLE_PATTERNS)
        )
        already_resolved_patterns = tuple(
            config.get("already_resolved_patterns", self._DEFAULT_ALREADY_RESOLVED_PATTERNS)
        )

        for order in orphan_orders:
            order_id = str(order.get("id", ""))
            if not order_id:
                continue
            await self._cancel_with_exponential_backoff(
                order_id,
                bitbank_client,
                max_retries,
                base_delay,
                retryable_patterns,
                already_resolved_patterns,
            )

    async def _cancel_with_exponential_backoff(
        self,
        order_id: str,
        bitbank_client: BitbankClient,
        max_retries: int,
        base_delay: float,
        retryable_patterns: tuple = _DEFAULT_RETRYABLE_PATTERNS,
        already_resolved_patterns: tuple = _DEFAULT_ALREADY_RESOLVED_PATTERNS,
    ) -> bool:
        """
        Phase 88 H11: 指数バックオフでキャンセル試行。

        Phase R-C1: retryable_patterns に該当するエラーのみリトライし、
        それ以外（permission 不足・order id 不正など恒久的エラー）は即時中断。
        無駄な 7 秒遅延・API quota 消費・他取引への影響を防ぐ。

        Phase 90λ: already_resolved_patterns（bitbank 50026=注文が既に存在しない等）は
        孤児SLキャンセルの目的（注文消滅）が既に達成された状態のため成功扱い（True）とし、
        CRITICAL ノイズと次サイクルの再検出を解消する。

        bitbank エラー 70004 (transaction currently suspended) 等の一時的エラー対応。
        3回失敗時は critical ログのみ・次の 5分サイクルで再試行（呼び元委譲）。
        """
        for attempt in range(max_retries):
            try:
                await asyncio.to_thread(bitbank_client.cancel_order, order_id, "BTC/JPY")
                self.logger.info(
                    f"✅ Phase 88 H11: 孤児SLキャンセル成功 "
                    f"(ID={order_id}, 試行{attempt + 1}/{max_retries})"
                )
                return True
            except Exception as e:
                err_msg = str(e).lower()
                # Phase 90λ: 「注文が既に存在しない」は孤児解消済み＝成功扱い（CRITICAL 化しない）
                if any(p in err_msg for p in already_resolved_patterns):
                    self.logger.info(
                        f"✅ Phase 90λ: 孤児SL は既に消滅済み＝解消済みとして確定 "
                        f"(ID={order_id}, 試行{attempt + 1}/{max_retries}): {e}"
                    )
                    return True
                is_retryable = any(p in err_msg for p in retryable_patterns)
                if not is_retryable:
                    # Phase R-C1: リトライ不可エラー → 即時中断
                    self.logger.critical(
                        f"🚨 Phase 88 H11: リトライ不可エラー、即時中断 "
                        f"(ID={order_id}, 試行{attempt + 1}/{max_retries}): {e}"
                    )
                    return False
                self.logger.warning(
                    f"⚠️ Phase 88 H11: 孤児SLキャンセル失敗（リトライ可能） "
                    f"(ID={order_id}, 試行{attempt + 1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    # 指数バックオフ: 1s, 2s, 4s
                    await asyncio.sleep(base_delay * (2**attempt))

        self.logger.critical(
            f"🚨 Phase 88 H11: 孤児SL全{max_retries}回キャンセル失敗 "
            f"(ID={order_id}) - 次の5分サイクルで再試行"
        )
        return False

    # ========================================
    # 既存ポジションTP/SL確保
    # ========================================

    def _check_position_invariants(
        self,
        virtual_positions: List[Dict[str, Any]],
        margin_positions: List[Dict[str, Any]],
    ) -> None:
        """Phase 90ο Stage 3: VP↔実ポジの不変条件を毎サイクル検査（検知・ログのみ）。

        状態のズレ（二重管理の乖離・サイズ膨張・両建て）を損失が出る前に可視化する。
        実害（重複エントリー）の防止は Stage 0/1（実ポジ基準の上限チェック）が担い、
        本メソッドは決済も復元もせず WARNING/CRITICAL ログを出すだけ（誤動作リスクなし）。
        ライブ分析(standard_analysis.py)がこのログを集計し、再発を監視する。
        """
        try:
            long_total = sum(
                float(p.get("amount") or 0) for p in margin_positions if p.get("side") == "long"
            )
            short_total = sum(
                float(p.get("amount") or 0) for p in margin_positions if p.get("side") == "short"
            )
            real_total = long_total + short_total
            max_total = get_threshold("position_management.max_total_position_btc", 0.02)

            # 1. 合計サイズ上限超過（サイズ膨張の事後検知＝6/15事故の再発シグナル）
            if real_total > max_total:
                self.logger.critical(
                    f"🚨 Phase 90ο invariant違反: 建玉合計 {real_total:.4f} BTC > 上限 "
                    f"{max_total} BTC（サイズ膨張・Stage 0/1 をすり抜けた可能性）"
                )

            # 2. 両建て（long+short 同時保有）
            if long_total > 0 and short_total > 0:
                self.logger.warning(
                    f"⚠️ Phase 90ο invariant: long+short 両建て検出 "
                    f"(long={long_total:.4f}, short={short_total:.4f} BTC)"
                )

            # 3. VP↔実ポジ乖離（合計サイズ）— API反映遅延を考慮し3連続で CRITICAL 昇格
            vp_total = sum(float(vp.get("amount") or 0) for vp in virtual_positions)
            divergence = abs(vp_total - real_total)
            if divergence > 0.0001:
                self._invariant_divergence_count = (
                    getattr(self, "_invariant_divergence_count", 0) + 1
                )
                if self._invariant_divergence_count >= 3:
                    self.logger.critical(
                        f"🚨 Phase 90ο invariant違反: VP↔実ポジ乖離 "
                        f"{self._invariant_divergence_count}連続 "
                        f"(VP合計={vp_total:.4f} vs 実ポジ={real_total:.4f} BTC)"
                    )
                else:
                    self.logger.warning(
                        f"⚠️ Phase 90ο invariant: VP↔実ポジ乖離 "
                        f"{self._invariant_divergence_count}/3 "
                        f"(VP={vp_total:.4f} vs 実={real_total:.4f} BTC・API反映待ちの可能性)"
                    )
            else:
                self._invariant_divergence_count = 0
        except Exception as e:
            self.logger.warning(f"⚠️ Phase 90ο invariant 検査エラー（無害・継続）: {e}")

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

        # Phase R-He: C5 で処理済の SL order id を H11 側に共有して重複 cancel を防ぐ
        c5_processed_sl_ids: set = set()

        try:
            # Phase 87 C5: 各VPのSL health check（CANCELED_UNFILLED/EXPIRED/REJECTED 検出）
            # 5分間隔で呼ばれる ensure_tp_sl_for_existing_positions に統合し、
            # API消費を抑えつつ全VPを個別検証する。
            if virtual_positions:
                positions_to_close: List[Dict[str, Any]] = []
                for vp in list(virtual_positions):
                    sl_order_id = vp.get("sl_order_id")
                    if not sl_order_id:
                        continue  # SL未配置VPは後続のカバレッジ検証で再配置
                    try:
                        health = await self.sl_monitor.check_sl_health(
                            sl_order_id=str(sl_order_id),
                            sl_placed_at_iso=vp.get("sl_placed_at"),
                            bitbank_client=bitbank_client,
                            amount=float(vp.get("amount") or 0.0),
                        )
                    except Exception as health_err:
                        self.logger.warning(
                            f"⚠️ Phase 87 C5: SL health check 失敗 "
                            f"(ID={sl_order_id}): {health_err}"
                        )
                        continue

                    if not health.requires_emergency_close:
                        continue

                    self.logger.critical(
                        f"🚨 Phase 87 C5: SL異常検出 - reason={health.failure_reason}, "
                        f"side={vp.get('side')}, "
                        f"amount={float(vp.get('amount') or 0):.6f} BTC, "
                        f"sl_order_id={sl_order_id}"
                    )
                    try:
                        await self.sl_monitor.emergency_market_close(
                            entry_side=vp.get("side", ""),
                            amount=float(vp.get("amount") or 0.0),
                            reason=f"c5_{health.failure_reason}",
                            bitbank_client=bitbank_client,
                        )
                        positions_to_close.append(vp)
                        # Phase R-He: H11 で重複処理しないように記録
                        c5_processed_sl_ids.add(str(sl_order_id))
                    except Exception as close_err:
                        self.logger.critical(
                            f"🚨🚨 Phase 87 C5: 緊急成行決済失敗 - 手動介入必要: {close_err}"
                        )
                for vp in positions_to_close:
                    if vp in virtual_positions:
                        virtual_positions.remove(vp)

            # Step 1: 信用建玉情報取得
            margin_positions = await bitbank_client.fetch_margin_positions("BTC/JPY")

            # Phase 90ο Stage 3: VP↔実ポジ invariant 検査（毎サイクル・検知/ログのみ）
            # run_trading_cycle(C5経由) と run_monitor_only の両経路が必ず通る合流点。
            # 決済も復元もせず、状態のズレ（サイズ膨張・両建て・乖離）を損失前に可視化する。
            self._check_position_invariants(virtual_positions, margin_positions or [])

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
                float(p.get("amount") or 0) for p in margin_positions if p.get("side") == "long"
            )
            short_total = sum(
                float(p.get("amount") or 0) for p in margin_positions if p.get("side") == "short"
            )

            # Phase 64.12: SL価格妥当性検証用の平均取得価格
            long_avg_price = 0.0
            short_avg_price = 0.0
            for p in margin_positions:
                if p.get("side") == "long" and float(p.get("amount") or 0) > 0:
                    long_avg_price = float(p.get("average_price") or 0)
                elif p.get("side") == "short" and float(p.get("amount") or 0) > 0:
                    short_avg_price = float(p.get("average_price") or 0)

            def _is_sl_price_valid(order: dict, ref_price: float) -> bool:
                """Phase 64.12: SL注文の価格がポジション取得価格から3%以内か"""
                if ref_price <= 0:
                    return True  # 参照価格なしは許容
                # Phase 65.14: None安全パターン（キーが存在しても値がNoneの場合に対応）
                trigger = float(
                    order.get("stopPrice") or order.get("triggerPrice") or order.get("price") or 0
                )
                if trigger <= 0:
                    return True
                return abs(trigger - ref_price) / ref_price <= 0.03

            # exit側の注文合計
            # Phase 65.14: None安全パターン（amount=Noneでfloat(None)→TypeError回避）
            tp_sell_total = sum(
                float(o.get("amount") or 0)
                for o in active_orders
                if o.get("side") == "sell" and o.get("type") in ("limit", "take_profit")
            )
            sl_sell_total = sum(
                float(o.get("amount") or 0)
                for o in active_orders
                if o.get("side") == "sell"
                and o.get("type") in ("stop", "stop_limit")
                and _is_sl_price_valid(o, long_avg_price)
            )
            tp_buy_total = sum(
                float(o.get("amount") or 0)
                for o in active_orders
                if o.get("side") == "buy" and o.get("type") in ("limit", "take_profit")
            )
            sl_buy_total = sum(
                float(o.get("amount") or 0)
                for o in active_orders
                if o.get("side") == "buy"
                and o.get("type") in ("stop", "stop_limit")
                and _is_sl_price_valid(o, short_avg_price)
            )

            # Phase 88 H11: 孤児SL検出（ポジション無し + stop/stop_limit 注文残存）
            # margin_positions と active_orders 取得直後に実行することで、
            # TP/SL カバレッジ計算より先に孤児SLをキャンセルし、二重カウントを防ぐ
            # Phase R-He: C5 で処理済の SL order id を渡して重複 cancel を防止
            await self._detect_and_cancel_orphan_sl(
                margin_positions,
                active_orders,
                bitbank_client,
                closed_order_ids=c5_processed_sl_ids,
            )

            # Phase 65.15: active_ordersのorder IDセットを収集（二重カウント防止）
            active_order_ids = {str(o.get("id", "")) for o in active_orders}

            # Phase 65.4: VPのTP追跡で補完
            # take_profit型注文もstop_limitと同様にINACTIVE状態では
            # fetch_active_ordersに含まれないため、VP側のtp_order_idで補完する
            # Phase 65.15: active_ordersに既にある注文はスキップ（二重カウント防止）
            for vp in virtual_positions:
                tp_id = vp.get("tp_order_id")
                if not tp_id or str(tp_id) in active_order_ids:
                    continue  # active_ordersで既にカウント済み
                vp_side = vp.get("side", "")
                vp_amount = float(vp.get("amount") or 0)
                if vp_side == "buy":  # long position → sell TP
                    tp_sell_total += vp_amount
                elif vp_side == "sell":  # short position → buy TP
                    tp_buy_total += vp_amount

            # Phase 65.4: VPのSL追跡で補完
            # bitbankのINACTIVE注文（stop_limitのトリガー待ち）は
            # fetch_active_orders（= ccxt fetch_open_orders）に含まれないため、
            # VP側のsl_order_idで補完する
            # Phase 65.15: active_ordersに既にある注文はスキップ（二重カウント防止）
            for vp in virtual_positions:
                sl_id = vp.get("sl_order_id")
                if not sl_id or str(sl_id) in active_order_ids:
                    continue  # active_ordersで既にカウント済み
                vp_side = vp.get("side", "")
                vp_amount = float(vp.get("amount") or 0)
                if vp_side == "buy":  # long position → sell SL
                    sl_sell_total += vp_amount
                elif vp_side == "sell":  # short position → buy SL
                    sl_buy_total += vp_amount

            # Phase 68.4: 永続化ファイルからINACTIVE SL検証
            # VPにもactive_ordersにもSLがない場合、永続化ファイルから検証
            if long_total > 0 and sl_sell_total < long_total * 0.95:
                try:
                    verified_sl_id = self.sl_persistence.verify_with_api(
                        "buy", bitbank_client, "BTC/JPY"
                    )
                    if verified_sl_id:
                        sl_sell_total += long_total  # INACTIVE SL存在確認
                        self.logger.info(
                            f"Phase 68.4: INACTIVE SL検出（永続化） - "
                            f"long {long_total:.4f} BTC, ID={verified_sl_id}"
                        )
                        # VPにもsl_order_idを復元
                        for vp in virtual_positions:
                            if vp.get("side") == "buy" and not vp.get("sl_order_id"):
                                vp["sl_order_id"] = verified_sl_id
                                break
                except Exception as e:
                    self.logger.debug(f"Phase 68.4: 永続化SL検証エラー（long）: {e}")

            if short_total > 0 and sl_buy_total < short_total * 0.95:
                try:
                    verified_sl_id = self.sl_persistence.verify_with_api(
                        "sell", bitbank_client, "BTC/JPY"
                    )
                    if verified_sl_id:
                        sl_buy_total += short_total  # INACTIVE SL存在確認
                        self.logger.info(
                            f"Phase 68.4: INACTIVE SL検出（永続化） - "
                            f"short {short_total:.4f} BTC, ID={verified_sl_id}"
                        )
                        for vp in virtual_positions:
                            if vp.get("side") == "sell" and not vp.get("sl_order_id"):
                                vp["sl_order_id"] = verified_sl_id
                                break
                except Exception as e:
                    self.logger.debug(f"Phase 68.4: 永続化SL検証エラー（short）: {e}")

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

                amount = float(position.get("amount") or 0)
                avg_price = float(position.get("average_price") or 0)
                if amount <= 0:
                    continue

                entry_side = "buy" if position_side == "long" else "sell"

                if position_side == "long":
                    has_tp = long_tp_ok
                    has_sl = long_sl_ok
                    side_total = long_total
                else:
                    has_tp = short_tp_ok
                    has_sl = short_sl_ok
                    side_total = short_total

                # Phase 65.2: カバレッジ十分であればスキップ（restored状態に関わらず）
                # 旧Phase 63.5: already_restoredでスキップしていたが、
                # カバレッジ不足時にもスキップされる問題があったため廃止
                if has_tp and has_sl:
                    continue

                # Step 4: 不足しているTP/SL注文を配置
                self.logger.info(
                    f"⚠️ Phase 65.2: TP/SLカバレッジ不足検出 - "
                    f"{position_side} 合計={side_total:.4f} BTC, "
                    f"TP={'OK' if has_tp else '不足'}, SL={'OK' if has_sl else '不足'}"
                )

                # Phase 68.3: VP削除前に既存SL order IDを保存
                existing_sl_info = {}
                if has_sl:
                    for vp in virtual_positions:
                        if vp.get("side") == entry_side and vp.get("sl_order_id"):
                            existing_sl_info = {
                                "sl_order_id": vp.get("sl_order_id"),
                                "sl_placed_at": vp.get("sl_placed_at"),
                            }
                            break

                # Phase 65.2: 統合再配置のため、このサイドの全VPを削除
                # （_place_missing_tp_slで既存注文キャンセル→新規配置→新VP追加される）
                virtual_positions[:] = [
                    vp for vp in virtual_positions if vp.get("side") != entry_side
                ]

                result = await self._place_missing_tp_sl(
                    position_side=position_side,
                    amount=side_total,
                    avg_price=avg_price,
                    has_tp=has_tp,
                    has_sl=has_sl,
                    virtual_positions=virtual_positions,
                    bitbank_client=bitbank_client,
                    existing_sl_info=existing_sl_info,
                )
                # Phase 82: ダスト検出時は成行決済で自動クリーンアップ
                if isinstance(result, dict) and result.get("action") == "dust_cleanup_required":
                    await self._cleanup_dust_position(
                        position_side=position_side,
                        amount=side_total,
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
            current_price = float(ticker.get("last") or 0)
        except Exception as e:
            # Phase 83C: 旧実装は無音 pass → API障害検知漏れ
            self.logger.warning(f"⚠️ Phase 83C: ticker取得失敗 - SL超過判定スキップ: {e}")
            current_price = 0

        sl_breached = False
        if current_price > 0:
            if position_side == "long" and current_price <= sl_price:
                sl_breached = True
            elif position_side == "short" and current_price >= sl_price:
                sl_breached = True

        if sl_breached:
            # SL超過 → 既存注文キャンセル → 成行決済
            self.logger.critical(
                f"🚨 Phase 64.12: SLトリガー超過 - 既存注文キャンセル→成行決済 "
                f"({position_side} {amount:.4f} BTC, "
                f"SL={sl_price:.0f}円, 現在={current_price:.0f}円)"
            )

            # Phase 64.12: 既存注文を全キャンセル（50062対策）
            try:
                active_orders = await asyncio.to_thread(
                    bitbank_client.fetch_active_orders, symbol, 100
                )
                for order in active_orders or []:
                    try:
                        await asyncio.to_thread(
                            bitbank_client.cancel_order,
                            str(order.get("id", "")),
                            symbol,
                        )
                        self.logger.info(f"✅ Phase 64.12: 注文キャンセル - ID: {order.get('id')}")
                    except Exception as e:
                        # Phase 83C: 旧実装は無音 pass → 孤児注文検知漏れ
                        self.logger.warning(
                            f"⚠️ Phase 83C: 注文キャンセル失敗 - " f"ID={order.get('id')}: {e}"
                        )
            except Exception as e:
                self.logger.warning(f"⚠️ Phase 64.12: 注文一括キャンセルエラー: {e}")

            # Phase 68.7: SL永続化クリア（SL超過成行決済時）
            try:
                self.sl_persistence.clear(entry_side)
            except Exception as e:
                # Phase 83C: 旧実装は無音 pass → SL永続化ファイル不整合検知漏れ
                self.logger.warning(f"⚠️ Phase 83C: SL永続化クリア失敗 ({entry_side}): {e}")

            # キャンセル後に成行決済
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
                self.logger.critical(
                    f"🚨 Phase 64.12: 成行決済失敗（注文キャンセル後）- 手動介入必要: {e}"
                )
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
                # Phase 68.4: 50062フォールバック（place_sl_or_market_close経由）
                if "50062" in str(e):
                    self.logger.info(
                        f"Phase 68.4: 50062検出（place_sl_or_market_close）→ "
                        f"既存INACTIVE SL存在 ({position_side})"
                    )
                    return {"order_id": "inactive_sl_preserved", "price": sl_price}
                self.logger.error(f"❌ Phase 64.4: SL配置失敗: {e}")
                return None

    async def _cleanup_dust_position(
        self,
        position_side: str,
        amount: float,
        bitbank_client: BitbankClient,
    ) -> None:
        """
        Phase 82: ダスト残りポジションを成行決済でクリーンアップ

        TP決済後の残渣等でbitbankが極小ポジション（< min_valid_position_btc）を
        返した場合、そのまま放置すると新規エントリーがブロックされるため成行で
        自動決済する。
        """
        symbol = get_threshold(TPSLConfig.CURRENCY_PAIR, "BTC/JPY")
        exit_side = "sell" if position_side == "long" else "buy"
        try:
            close_order = await asyncio.to_thread(
                bitbank_client.create_order,
                symbol=symbol,
                order_type="market",
                side=exit_side,
                amount=amount,
                is_closing_order=True,
                entry_position_side=position_side,
            )
            self.logger.info(
                f"✅ Phase 82: ダストポジション自動クリーンアップ完了 - "
                f"{position_side} {amount:.6f} BTC 成行決済 "
                f"(order_id={close_order.get('id', 'unknown') if close_order else 'none'})"
            )
        except Exception as e:
            self.logger.critical(
                f"🚨 Phase 82: ダストクリーンアップ失敗（手動介入必要） - "
                f"{position_side} {amount:.6f} BTC: {e}"
            )

    async def _place_missing_tp_sl(
        self,
        position_side: str,
        amount: float,
        avg_price: float,
        has_tp: bool,
        has_sl: bool,
        virtual_positions: List[Dict[str, Any]],
        bitbank_client: BitbankClient,
        existing_sl_info: Optional[Dict[str, Any]] = None,
    ):
        """
        Phase 65.2: 不足しているTP/SL注文を統合配置

        既存の部分TP/SL注文を全キャンセルし、ポジション全量をカバーする
        TP/SLを1組配置する。固定500円TPにも対応。

        Phase 68.3: SL保護 - SL存在時はキャンセルせず、既存SL情報をVPに引き継ぐ

        背景: bitbankはポジションを加重平均で統合管理するため、
        個別エントリーごとのTP/SLでは部分カバーになる問題を解消。

        Args:
            position_side: "long" or "short"
            amount: ポジション数量（サイド合計）
            avg_price: 平均取得価格（bitbank加重平均）
            has_tp: TP注文が十分か（95%カバレッジ）
            has_sl: SL注文が十分か（95%カバレッジ）
            virtual_positions: 仮想ポジションリスト（直接更新）
            bitbank_client: BitbankClientインスタンス
            existing_sl_info: Phase 68.3 既存SL注文情報（SL保護時に引き継ぎ）
        """
        if existing_sl_info is None:
            existing_sl_info = {}
        symbol = get_threshold(TPSLConfig.CURRENCY_PAIR, "BTC/JPY")
        entry_side = "buy" if position_side == "long" else "sell"

        # Phase 82: ダスト/微小ポジション検出（TP決済後の残渣対策）
        # amountが極小（通常0.01-0.02 BTC、ダストは0.0001 BTC）の場合、
        # 固定金額TP/SL計算で分母が小さくなり価格が極端値になる（例: TP+66%, SL-88%）。
        # ここで配置をスキップして呼び出し側にクリーンアップを促す。
        min_valid_btc = get_threshold("position_management.min_valid_position_btc", 0.001)
        if amount < min_valid_btc:
            self.logger.warning(
                f"🧹 Phase 82: ダストポジション検出（TP/SL配置スキップ） - "
                f"{position_side} {amount:.6f} BTC @ {avg_price:.0f}円 "
                f"(下限 {min_valid_btc} BTC未満・要クリーンアップ)"
            )
            return {
                "action": "dust_cleanup_required",
                "amount": amount,
                "side": position_side,
                "avg_price": avg_price,
            }

        # ── Phase 67.5: TP/SL価格計算を先行実行 ──
        # キャンセル前にSL超過チェックを行うため、価格計算を最初に実行
        if self._is_fixed_amount_tp_enabled() and avg_price > 0 and amount > 0:
            tp_price = self._calculate_fixed_amount_tp_for_position(
                position_side, amount, avg_price
            )
            _, sl_price = self.calculate_recovery_tp_sl_prices(
                position_side=position_side,
                avg_price=avg_price,
            )
            # Phase 66.6: 固定金額SLも適用
            fixed_sl_enabled = get_threshold(
                "position_management.stop_loss.fixed_amount.enabled", False
            )
            if fixed_sl_enabled:
                sl_price = self._calculate_fixed_amount_sl_for_position(
                    position_side, amount, avg_price
                )
            # Phase 90γ-⑥: info→warning（統合ポジ用 TP/SL 復旧経路の確定値を観察可能化）
            self.logger.warning(
                f"📊 Phase 65.2/66.6: 固定金額TP/SL使用 - "
                f"TP={tp_price:.0f}円, SL={sl_price:.0f}円 "
                f"(avg={avg_price:.0f}円, amount={amount:.4f} BTC)"
            )
        else:
            # Phase 64.9: %ベース計算（デフォルト: normal_range = 安全側）
            tp_price, sl_price = self.calculate_recovery_tp_sl_prices(
                position_side=position_side,
                avg_price=avg_price,
            )

        # ── Step 0: 既存部分注文キャンセル ──
        # Phase 68.4: SLは常にキャンセルしない（INACTIVE SL保護）
        # has_sl=Falseでも、INACTIVE SLが存在する可能性がある
        # SL配置を先に試行し、50062で既存SL検出を行う（Layer 2）
        try:
            cancelled = await self._cancel_partial_exit_orders(
                position_side,
                symbol,
                bitbank_client,
                cancel_sl=False,  # Phase 68.4: SLは常にキャンセルしない
            )
            if cancelled > 0:
                self.logger.info(
                    f"🔄 Phase 68.4: TP注文 {cancelled}件キャンセル → 再配置（SL保護維持）"
                )
                # TPはキャンセルしたので再配置が必要
                has_tp = False
        except Exception as e:
            self.logger.warning(f"⚠️ Phase 65.2: 部分TPキャンセル失敗（継続）: {e}")

        tp_order = None
        sl_order = None

        # Phase 68.4: SL不在時、先にSL配置を試行（キャンセルなし）
        # 50062エラー → 既存INACTIVE SLが存在する証拠 → has_sl=Trueに修正
        if not has_sl:
            try:
                sl_order = await self.place_sl_or_market_close(
                    entry_side=entry_side,
                    position_side=position_side,
                    amount=amount,
                    avg_price=avg_price,
                    sl_price=sl_price,
                    symbol=symbol,
                    bitbank_client=bitbank_client,
                )
            except Exception as e:
                # Phase 68.4: 50062フォールバック（Layer 2）
                # 50062（保有建玉数量超過）= 既存INACTIVE SLが存在する証拠
                if "50062" in str(e):
                    has_sl = True
                    sl_order = None
                    self.logger.info(
                        f"Phase 68.4: 50062検出 → 既存INACTIVE SL保護 "
                        f"({position_side} {amount:.4f} BTC)"
                    )
                    # 永続化ファイルからSL IDを復元試行
                    try:
                        verified_id = self.sl_persistence.verify_with_api(
                            entry_side, bitbank_client, symbol
                        )
                        if verified_id:
                            existing_sl_info = existing_sl_info or {}
                            existing_sl_info["sl_order_id"] = verified_id
                    except Exception as e:
                        self.logger.debug(f"Phase 68.4: SL永続化ファイル復元失敗（無視）: {e}")
                else:
                    self.logger.error(f"❌ Phase 68.4: SL配置失敗: {e}")

        # ── Phase 67.5: SL超過再チェック（SL不在のまま配置失敗時） ──
        # Phase 68.4: SL配置もINACTIVE SL検出も失敗した場合のみ
        if not has_sl and not sl_order:
            try:
                ticker = await asyncio.to_thread(bitbank_client.fetch_ticker, symbol)
                current_price = float(ticker.get("last", 0)) if ticker else 0
                if current_price > 0:
                    sl_breached = False
                    if position_side == "long" and current_price <= sl_price:
                        sl_breached = True
                    elif position_side == "short" and current_price >= sl_price:
                        sl_breached = True

                    if sl_breached:
                        self.logger.warning(
                            f"🚨 Phase 67.5: SL超過検出 - "
                            f"現在={current_price:.0f}円, SL={sl_price:.0f}円 "
                            f"→ 成行決済"
                        )
                        try:
                            close_side = "sell" if position_side == "long" else "buy"
                            await asyncio.to_thread(
                                bitbank_client.create_order,
                                symbol=symbol,
                                order_type="market",
                                side=close_side,
                                amount=amount,
                                is_closing_order=True,
                                entry_position_side=position_side,
                            )
                            self.logger.info(
                                f"✅ Phase 67.5: SL超過による成行決済完了 - "
                                f"{position_side} {amount:.4f} BTC"
                            )
                        except Exception as e:
                            self.logger.error(f"❌ Phase 67.5: SL超過成行決済失敗: {e}")
                        return
            except Exception as e:
                self.logger.warning(f"⚠️ Phase 67.5: SL超過再チェック失敗（継続）: {e}")

        # TP配置（全量カバー）
        if not has_tp:
            try:
                # Phase 68.6: TP配置前に既存TP limit注文を明示キャンセル（50062防止）
                try:
                    exit_side = "sell" if position_side == "long" else "buy"
                    active_orders = await asyncio.to_thread(
                        bitbank_client.fetch_active_orders, symbol, TPSLConfig.API_ORDER_LIMIT
                    )
                    tp_cancelled = 0
                    for order in active_orders or []:
                        if order.get("side") == exit_side and order.get("type") in (
                            "limit",
                            "take_profit",
                        ):
                            oid = str(order.get("id", ""))
                            if oid:
                                await asyncio.to_thread(bitbank_client.cancel_order, oid, symbol)
                                tp_cancelled += 1
                    if tp_cancelled > 0:
                        self.logger.info(
                            f"🗑️ Phase 68.6: TP配置前に既存TP {tp_cancelled}件キャンセル"
                        )
                except Exception as e:
                    self.logger.warning(f"⚠️ Phase 68.6: TP事前キャンセル失敗（継続）: {e}")

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
                        f"✅ Phase 65.2: 統合TP配置成功 - "
                        f"{position_side} {amount:.4f} BTC @ {tp_price:.0f}円"
                    )
            except Exception as e:
                self.logger.error(f"❌ Phase 65.2: TP配置失敗: {e}")

        # Phase 64.12: SLが設置されていればVP追加（TPは次回再試行）
        tp_ok = has_tp or (tp_order and tp_order.get("order_id"))
        sl_ok = has_sl or (sl_order and sl_order.get("order_id"))

        if sl_ok:
            recovered_position = {
                "order_id": f"recovered_{position_side}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "side": entry_side,
                "amount": amount,
                "price": avg_price,
                "timestamp": datetime.now(),
                "take_profit": tp_price,
                "stop_loss": sl_price,
                "restored": True,
                "tp_order_id": tp_order.get("order_id") if tp_order else None,
                "sl_order_id": (sl_order.get("order_id") if sl_order else None)
                or existing_sl_info.get("sl_order_id"),
                "sl_placed_at": (sl_order.get("sl_placed_at") if sl_order else None)
                or existing_sl_info.get("sl_placed_at"),
            }
            virtual_positions.append(recovered_position)
            if tp_ok:
                self.logger.info(
                    f"✅ Phase 65.2: 統合TP/SL復旧完了 - VP追加 "
                    f"({position_side} {amount:.4f} BTC)"
                )
            else:
                self.logger.warning(
                    f"⚠️ Phase 65.2: TP未設置だがSL設置済み - VP追加（TPは次回再試行）"
                    f" ({position_side} {amount:.4f} BTC)"
                )
        else:
            self.logger.critical(
                f"🚨 Phase 65.2: SL未設置 - VP未追加・次回再試行"
                f" - TP: {'OK' if tp_ok else 'NG'}, SL: NG"
                f" ({position_side} {amount:.4f} BTC)"
            )

    # ========================================
    # Phase 65.2: 統合TP/SL配置ヘルパー
    # ========================================

    async def _cancel_partial_exit_orders(
        self,
        position_side: str,
        symbol: str,
        bitbank_client: BitbankClient,
        cancel_sl: bool = True,
    ) -> int:
        """
        Phase 65.2: 統合TP/SL配置前に既存の部分決済注文をキャンセル

        bitbankはTP+SLの合計数量がポジション数量を超えると50062エラーになるため、
        既存の部分注文をキャンセルしてから全量注文を配置する。

        Phase 68.3: cancel_sl=Falseの場合、SL注文はキャンセルしない（SL保護）

        Args:
            position_side: "long" or "short"
            symbol: 通貨ペア
            bitbank_client: BitbankClientインスタンス
            cancel_sl: SL注文もキャンセルするか（デフォルト: True）

        Returns:
            int: キャンセルした注文数
        """
        active_orders = await asyncio.to_thread(
            bitbank_client.fetch_active_orders, symbol, TPSLConfig.API_ORDER_LIMIT
        )

        if not active_orders:
            return 0

        # 決済方向の注文を特定（long→sell決済、short→buy決済）
        exit_side = "sell" if position_side == "long" else "buy"
        cancelled = 0

        for order in active_orders:
            if order.get("side") != exit_side:
                continue

            order_type = order.get("type", "")
            # Phase 68.3: TP/SL種別を分離してcancel_slフラグで制御
            tp_types = ("limit", "take_profit")
            sl_types = ("stop", "stop_limit", "stop_loss")
            if order_type in tp_types or (cancel_sl and order_type in sl_types):
                order_id = str(order.get("id", ""))
                if not order_id:
                    continue

                try:
                    await asyncio.to_thread(bitbank_client.cancel_order, order_id, symbol)
                    cancelled += 1
                    self.logger.info(
                        f"🗑️ Phase 65.2: 部分注文キャンセル - "
                        f"ID: {order_id}, type: {order_type}, "
                        f"amount: {order.get('amount', '?')}"
                    )
                except Exception as e:
                    self.logger.warning(
                        f"⚠️ Phase 65.2: 注文キャンセル失敗（継続） - " f"ID: {order_id}, error: {e}"
                    )

        return cancelled

    def _is_fixed_amount_tp_enabled(self) -> bool:
        """Phase 65.2: 固定金額TPモードが有効か"""
        return get_threshold("position_management.take_profit.fixed_amount.enabled", False)

    def _calculate_fixed_amount_tp_for_position(
        self,
        position_side: str,
        amount: float,
        avg_price: float,
    ) -> float:
        """
        Phase 65.2: 統合ポジション向け固定金額TP価格計算

        エントリー時のRiskManager.calculate_stop_loss_take_profitと同じ
        固定500円TP計算ロジックを、リカバリパス用に簡易実装。

        Args:
            position_side: "long" or "short"
            amount: ポジション数量（BTC）
            avg_price: 平均取得価格

        Returns:
            float: TP価格
        """
        # Phase 82: amount下限ガード（ダスト残り対策）
        min_valid_btc = get_threshold("position_management.min_valid_position_btc", 0.001)
        if amount < min_valid_btc:
            raise ValueError(
                f"固定金額TP計算のamount下限未満: {amount:.6f} BTC < "
                f"{min_valid_btc} BTC. ダスト/微小ポジションの可能性。"
            )

        # Phase 86: TPSLCalculator に統一（entry_fee 加算漏れバグ修正）
        from .tpsl_calculator import TPSLCalculator

        target = get_threshold(
            "position_management.take_profit.fixed_amount.target_net_profit",
            1500,  # Phase 85: 500→1500
        )
        entry_fee_rate = get_threshold(
            "position_management.take_profit.fixed_amount.fallback_entry_fee_rate", 0.001
        )
        exit_fee_rate = get_threshold(
            "position_management.take_profit.fixed_amount.fallback_exit_fee_rate", 0.0
        )
        action = "buy" if position_side == "long" else "sell"
        return TPSLCalculator.calculate_tp(
            action=action,
            entry_price=avg_price,
            amount=amount,
            target_net_profit=target,
            entry_fee_rate=entry_fee_rate,
            exit_fee_rate=exit_fee_rate,
        )

    def _calculate_fixed_amount_sl_for_position(
        self,
        position_side: str,
        amount: float,
        avg_price: float,
    ) -> float:
        """
        Phase 66.6: 統合ポジション向け固定金額SL価格計算

        Args:
            position_side: "long" or "short"
            amount: ポジション数量（BTC）
            avg_price: 平均取得価格

        Returns:
            float: SL価格
        """
        # Phase 82: amount下限ガード（ダスト残り対策）
        min_valid_btc = get_threshold("position_management.min_valid_position_btc", 0.001)
        if amount < min_valid_btc:
            raise ValueError(
                f"固定金額SL計算のamount下限未満: {amount:.6f} BTC < "
                f"{min_valid_btc} BTC. ダスト/微小ポジションの可能性。"
            )

        # Phase 86: TPSLCalculator に統一（floor強制を計算層に集約）
        from .tpsl_calculator import TPSLCalculator

        target = get_threshold(TPSLConfig.SL_FIXED_AMOUNT_TARGET, 2000)  # Phase 85: 500→2000
        entry_fee_rate = get_threshold(TPSLConfig.SL_FIXED_AMOUNT_ENTRY_FEE, 0.001)
        exit_fee_rate = get_threshold(TPSLConfig.SL_FIXED_AMOUNT_EXIT_FEE, 0.001)
        min_distance_enabled = get_threshold(
            "position_management.stop_loss.min_distance.enabled", False
        )
        min_ratio = get_threshold("position_management.stop_loss.min_distance.ratio", 0.007)

        action = "buy" if position_side == "long" else "sell"
        return TPSLCalculator.calculate_sl(
            action=action,
            entry_price=avg_price,
            amount=amount,
            target_max_loss=target,
            entry_fee_rate=entry_fee_rate,
            exit_fee_rate=exit_fee_rate,
            min_distance_ratio=min_ratio,
            enable_floor=min_distance_enabled,
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

            target_tp_side = "sell" if side == "buy" else "buy"

            # Phase 65.5: 共通ヘルパーで保護対象ID収集
            from .position_restorer import PositionRestorer

            protected_order_ids = PositionRestorer.collect_protected_order_ids(virtual_positions)

            if protected_order_ids:
                self.logger.info(
                    f"🛡️ Phase 53.12: {len(protected_order_ids)}件の注文を保護対象に設定"
                )

            # Phase 65.14: VP追跡のTP/SL注文をID指定でキャンセル（INACTIVE対策）
            # bitbankのINACTIVE状態のstop_limit注文はfetch_active_ordersに返されないが、
            # order ID指定でキャンセル可能。VP側で追跡している古い注文を確実にキャンセルする。
            # 注: このメソッドはTP/SL配置前に呼ばれるため、同一side VPの注文は全て古い注文。
            # protected_order_idsチェックは不要（fetch_active_orders由来の注文保護用に維持）。
            vp_cancelled = 0
            for vp in virtual_positions:
                if vp.get("side") != side:
                    continue
                # Phase 68.6: SLは保護、TPのみキャンセル（SL巻き添えキャンセル防止）
                for id_key in ("tp_order_id",):
                    order_id = vp.get(id_key)
                    if not order_id:
                        continue
                    try:
                        await asyncio.to_thread(bitbank_client.cancel_order, str(order_id), symbol)
                        vp[id_key] = None
                        vp_cancelled += 1
                        self.logger.info(
                            f"🗑️ Phase 65.14: VP追跡注文キャンセル - "
                            f"ID: {order_id}, key: {id_key}"
                        )
                    except Exception:
                        pass  # 既にキャンセル済みや約定済みの場合は無視

            if vp_cancelled > 0:
                self.logger.info(
                    f"✅ Phase 65.14: VP追跡TP/SL {vp_cancelled}件キャンセル（INACTIVE含む）"
                )

            if not active_orders:
                if vp_cancelled == 0:
                    self.logger.debug("📋 Phase 51.10-A: アクティブ注文なし - クリーンアップ不要")
                return

            # 削除対象の注文を収集
            orders_to_cancel = []
            for order in active_orders:
                order_id = str(order.get("id", order.get("order_id", "")))
                order_side = order.get("side", "")
                order_type = order.get("type", "")

                if order_id in protected_order_ids:
                    continue

                # Phase 65.15: take_profit型TP注文も判定対象に追加
                is_tp = order_type in ("limit", "take_profit") and order_side == target_tp_side
                # Phase 68.6: SL保護 - エントリー前クリーンアップでSLをキャンセルしない
                is_sl = False

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

        # Phase 86: 即時SL存在確認（10秒後）も並行スケジュール
        # 既存の10分後検証では孤児ポジ放置のリスクが大きいため、即時検証を追加
        self._pending_verifications.append(
            {
                "scheduled_at": datetime.now(timezone.utc),
                "verify_after": datetime.now(timezone.utc) + timedelta(seconds=10),
                "entry_order_id": entry_order_id,
                "side": side,
                "amount": amount,
                "entry_price": entry_price,
                "expected_tp_order_id": tp_order_id,
                "expected_sl_order_id": sl_order_id,
                "symbol": symbol,
                "immediate_check": True,  # Phase 86: 即時検証フラグ
            }
        )
        self.logger.info(f"⚡ Phase 86: 即時SL検証スケジュール - 10秒後 (Entry: {entry_order_id})")

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
                # Phase 68.8: 信頼度別TP/SL用にconfidence追加
                # Phase 90γ-⑥: TradeEvaluation には `confidence` フィールド無し（types.py L23-46）。
                # Phase 68 以降 getattr が常に None を返し confidence_based 上書きが全エントリーで
                # スキップされる致命的バグ → regime_based のみで TP/SL 決定 → normal_range で
                # TP=500 円が採用される事象が約 2.5 ヶ月継続。
                # 修正: adjusted_confidence (penalty/bonus 適用後・Phase 59.3) → confidence_level
                # (必須・常に有効) の優先順位で取得。
                eval_confidence = (
                    evaluation.adjusted_confidence
                    if evaluation.adjusted_confidence is not None
                    else evaluation.confidence_level
                )
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
                    confidence=eval_confidence,
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

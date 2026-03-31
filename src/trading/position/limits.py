"""
ポジション制限管理サービス - Phase 64

ポジション数、資金利用率、日次取引回数などの制限をチェック。
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ...core.config import get_threshold
from ...core.logger import get_logger
from ...core.services.regime_types import RegimeType
from ..core import TradeEvaluation


class PositionLimits:
    """
    ポジション制限管理サービス

    各種取引制限のチェックを行い、口座残高使い切り問題を防ぐ。
    """

    def __init__(self):
        """PositionLimits初期化"""
        self.logger = get_logger()
        self.cooldown_manager = None  # 後で注入

    def inject_cooldown_manager(self, cooldown_manager: Any) -> None:
        """
        CooldownManagerを注入

        Args:
            cooldown_manager: CooldownManagerインスタンス
        """
        self.cooldown_manager = cooldown_manager

    async def check_limits(
        self,
        evaluation: TradeEvaluation,
        virtual_positions: List[Dict[str, Any]],
        last_order_time: Optional[datetime],
        current_balance: float,
        regime: Optional[RegimeType] = None,
        current_time: Optional[datetime] = None,
        mode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        ポジション管理制限チェック（口座残高使い切り問題対策）

        Args:
            evaluation: 取引評価結果
            virtual_positions: 現在のポジションリスト
            last_order_time: 最後の注文時刻
            current_balance: 現在の残高
            regime: 市場レジーム（Phase 51.8: レジーム別ポジション制限）
            current_time: 判定基準時刻（Phase 56.3: バックテスト時刻対応）
            mode: 実行モード（Phase 65.6: 残高ベース推定を排除）

        Returns:
            Dict: {"allowed": bool, "reason": str}
        """
        try:
            # 0. 最小資金要件チェック（動的ポジションサイジング対応）
            min_balance_check = self._check_minimum_balance(current_balance)
            if not min_balance_check["allowed"]:
                return min_balance_check

            # Phase 29.6 + Phase 31.1: クールダウンチェック（柔軟な判定）
            # Phase 56.3: current_time対応（バックテスト時刻）
            cooldown_check = await self._check_cooldown(evaluation, last_order_time, current_time)
            if not cooldown_check["allowed"]:
                return cooldown_check

            # 1. 最大ポジション数チェック（Phase 51.8: レジーム対応）
            position_count_check = self._check_max_positions(virtual_positions, regime)
            if not position_count_check["allowed"]:
                return position_count_check

            # 1.5. Phase 69.8: 同方向ポジション制限チェック
            same_dir_check = self._check_same_direction_positions(evaluation, virtual_positions)
            if not same_dir_check["allowed"]:
                return same_dir_check

            # 2. 残高利用率チェック（Phase 65.6: mode伝搬）
            capital_usage_check = self._check_capital_usage(current_balance, mode)
            if not capital_usage_check["allowed"]:
                return capital_usage_check

            # 3. 日次取引回数チェック（簡易実装）
            daily_trades_check = self._check_daily_trades(virtual_positions)
            if not daily_trades_check["allowed"]:
                return daily_trades_check

            # 4. 取引サイズチェック（ML信頼度連動・最小ロット優先）
            trade_size_check = self._check_trade_size(evaluation, current_balance)
            if not trade_size_check["allowed"]:
                return trade_size_check

            return {"allowed": True, "reason": "制限チェック通過"}

        except Exception as e:
            self.logger.error(f"❌ ポジション制限チェックエラー: {e}")
            # エラー時は安全のため取引拒否
            return {"allowed": False, "reason": f"制限チェック処理エラー: {e}"}

    def _check_minimum_balance(self, current_balance: float) -> Dict[str, Any]:
        """
        最小資金要件チェック

        Args:
            current_balance: 現在の残高

        Returns:
            Dict: {"allowed": bool, "reason": str}
        """
        min_account_balance = get_threshold("position_management.min_account_balance", 10000.0)

        # 動的ポジションサイジングが有効な場合は最小要件を緩和
        dynamic_enabled = get_threshold(
            "position_management.dynamic_position_sizing.enabled", False
        )

        if not dynamic_enabled and current_balance < min_account_balance:
            return {
                "allowed": False,
                "reason": f"最小運用資金要件({min_account_balance:.0f}円)を下回っています。現在: {current_balance:.0f}円",
            }

        # 動的サイジング有効時は最小ロット取引可能性をチェック
        if dynamic_enabled:
            min_trade_size = get_threshold("position_management.min_trade_size", 0.0001)
            # 概算BTC価格（最新価格が不明な場合の推定値）
            estimated_btc_price = get_threshold("trading.fallback_btc_jpy", 10000000.0)
            min_required_balance = min_trade_size * estimated_btc_price * 1.1  # 10%マージン

            if current_balance < min_required_balance:
                return {
                    "allowed": False,
                    "reason": f"最小ロット取引に必要な資金({min_required_balance:.0f}円)を下回っています。現在: {current_balance:.0f}円",
                }

        return {"allowed": True, "reason": "資金要件OK"}

    async def _check_cooldown(
        self,
        evaluation: TradeEvaluation,
        last_order_time: Optional[datetime],
        current_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        クールダウンチェック（Phase 31.1: 柔軟な判定）
        Phase 56.3: バックテスト時刻対応

        Args:
            evaluation: 取引評価結果
            last_order_time: 最後の注文時刻
            current_time: 判定基準時刻（Noneの場合はdatetime.now()使用）

        Returns:
            Dict: {"allowed": bool, "reason": str}
        """
        cooldown_minutes = get_threshold("position_management.cooldown_minutes", 30)

        if not last_order_time or cooldown_minutes <= 0:
            return {"allowed": True, "reason": "クールダウンなし"}

        # Phase 56.3: バックテスト時はcurrent_time使用、本番時はdatetime.now()
        now = current_time if current_time is not None else datetime.now()
        time_since_last_order = now - last_order_time
        required_cooldown = timedelta(minutes=cooldown_minutes)

        if time_since_last_order < required_cooldown:
            # Phase 31.1: 柔軟なクールダウン判定（トレンド強度考慮）
            if self.cooldown_manager:
                should_apply = await self.cooldown_manager.should_apply_cooldown(evaluation)
            else:
                should_apply = True

            if should_apply:
                remaining_minutes = (required_cooldown - time_since_last_order).total_seconds() / 60
                return {
                    "allowed": False,
                    "reason": f"クールダウン期間中です。残り {remaining_minutes:.1f}分後に取引可能（設定: {cooldown_minutes}分間隔）",
                }
            else:
                self.logger.info(
                    f"🔥 強トレンド検出 - クールダウンスキップ（残り{(required_cooldown - time_since_last_order).total_seconds() / 60:.1f}分）"
                )

        return {"allowed": True, "reason": "クールダウンOK"}

    def _check_max_positions(
        self, virtual_positions: List[Dict[str, Any]], regime: Optional[RegimeType] = None
    ) -> Dict[str, Any]:
        """
        最大ポジション数チェック（Phase 51.8: レジーム対応）

        Args:
            virtual_positions: 現在のポジションリスト
            regime: 市場レジーム（Phase 51.8: レジーム別制限適用）

        Returns:
            Dict: {"allowed": bool, "reason": str}
        """
        current_positions = len(virtual_positions)

        # Phase 51.8: レジーム別ポジション制限
        if regime is not None:
            from ...core.services.dynamic_strategy_selector import DynamicStrategySelector

            selector = DynamicStrategySelector()
            max_positions = selector.get_regime_position_limit(regime)

            if current_positions >= max_positions:
                return {
                    "allowed": False,
                    "reason": f"Phase 51.8: レジーム別ポジション制限({regime.value}: {max_positions}個)に達しています。現在: {current_positions}個",
                }

            self.logger.info(
                f"📊 Phase 51.8: レジーム別ポジション数チェック通過 - "
                f"regime={regime.value}, 現在={current_positions}件, 上限={max_positions}件"
            )
            return {"allowed": True, "reason": f"レジーム別ポジション数OK({regime.value})"}

        # 従来のグローバル制限（レジーム情報なし時のフォールバック）
        max_positions = get_threshold("position_management.max_open_positions", 3)

        if current_positions >= max_positions:
            return {
                "allowed": False,
                "reason": f"最大ポジション数制限({max_positions}個)に達しています。現在: {current_positions}個",
            }

        return {"allowed": True, "reason": "ポジション数OK"}

    def _check_same_direction_positions(
        self,
        evaluation: TradeEvaluation,
        virtual_positions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Phase 69.8: 同方向ポジション制限チェック

        同方向に複数エントリーすると合算SLが倍増するリスクを抑制。

        Args:
            evaluation: 取引評価結果（sideを参照）
            virtual_positions: 現在のポジションリスト

        Returns:
            Dict: {"allowed": bool, "reason": str}
        """
        max_same_dir = get_threshold("position_management.max_same_direction_positions", 0)

        # 設定が0以下の場合は制限無効
        if max_same_dir <= 0:
            return {"allowed": True, "reason": "同方向制限無効"}

        side = getattr(evaluation, "side", None)
        if not side:
            return {"allowed": True, "reason": "side情報なし（スキップ）"}

        same_dir_count = sum(
            1 for pos in virtual_positions if pos.get("side", "").lower() == side.lower()
        )

        if same_dir_count >= max_same_dir:
            self.logger.info(
                f"🚫 同方向ポジション制限: {side}方向={same_dir_count}件 >= 上限{max_same_dir}件"
            )
            return {
                "allowed": False,
                "reason": f"同方向ポジション制限({side}: {max_same_dir}個)に達しています。現在: {same_dir_count}個",
            }

        return {"allowed": True, "reason": f"同方向ポジション数OK({side})"}

    def _check_capital_usage(
        self, current_balance: float, mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        残高利用率チェック

        Phase 75: DrawdownManagerが既にmax_drawdown_ratio(20%)でチェックしているため、
        ここでは固定initial_balanceとの比較を行わない（残高が流動的なため）。
        常に許可を返す。

        Args:
            current_balance: 現在の残高
            mode: 実行モード

        Returns:
            Dict: {"allowed": bool, "reason": str}
        """
        # Phase 75: ドローダウンチェック（DrawdownManager）と重複するため無効化
        # 固定initial_balanceとの比較は残高が減るほど厳しくなり、
        # ポジションゼロでも「資金利用率超過」と判定される問題があった
        return {"allowed": True, "reason": "資金利用率OK（DrawdownManagerで管理）"}

    def _check_daily_trades(self, virtual_positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        日次取引回数チェック

        Args:
            virtual_positions: ポジションリスト

        Returns:
            Dict: {"allowed": bool, "reason": str}
        """
        max_daily_trades = get_threshold("position_management.max_daily_trades", 20)

        # 今日の取引回数をカウント
        today = datetime.now().date()
        today_trades = 0

        for trade in virtual_positions:
            # timestamp処理（datetimeオブジェクトまたは文字列）
            timestamp = trade.get("timestamp")
            if isinstance(timestamp, datetime):
                trade_date = timestamp.date()
            elif isinstance(timestamp, str):
                try:
                    trade_date = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).date()
                except Exception as e:
                    self.logger.debug(f"⏭️ タイムスタンプパース失敗: {timestamp} - {e}")
                    continue
            else:
                continue

            if trade_date == today:
                today_trades += 1

        if today_trades >= max_daily_trades:
            return {
                "allowed": False,
                "reason": f"日次取引回数制限({max_daily_trades}回)に達しています。今日: {today_trades}回",
            }

        return {"allowed": True, "reason": "日次取引回数OK"}

    def _check_trade_size(
        self, evaluation: TradeEvaluation, current_balance: float
    ) -> Dict[str, Any]:
        """
        取引サイズチェック（ML信頼度連動・最小ロット優先）

        Args:
            evaluation: 取引評価結果
            current_balance: 現在の残高

        Returns:
            Dict: {"allowed": bool, "reason": str}
        """
        ml_confidence = getattr(evaluation, "confidence_level", 0.5)
        min_trade_size = get_threshold("position_management.min_trade_size", 0.0001)

        # Phase 55.11: 実BTC価格を取得（フォールバックは緊急時のみ）
        btc_price = None
        if hasattr(evaluation, "market_conditions") and evaluation.market_conditions:
            btc_price = evaluation.market_conditions.get("last_price")
        if not btc_price or btc_price <= 0:
            btc_price = get_threshold("trading.fallback_btc_jpy", 10000000.0)
            self.logger.debug(f"BTC価格フォールバック使用: ¥{btc_price:,.0f}")

        trade_amount = float(evaluation.position_size) * btc_price
        min_trade_amount = min_trade_size * btc_price

        # ML信頼度に基づく制限比率を決定
        # Phase 57.2: 閾値60%→50%に変更（ML信頼度平均51.8%に対応）
        if ml_confidence < 0.50:
            # 低信頼度
            max_position_ratio = get_threshold(
                "position_management.max_position_ratio_per_trade.low_confidence", 0.03
            )
            confidence_category = "low"
        elif ml_confidence < 0.65:
            # 中信頼度（Phase 57.2: 50-65%）
            max_position_ratio = get_threshold(
                "position_management.max_position_ratio_per_trade.medium_confidence", 0.05
            )
            confidence_category = "medium"
        else:
            # 高信頼度（Phase 57.2: 65%以上）
            max_position_ratio = get_threshold(
                "position_management.max_position_ratio_per_trade.high_confidence", 0.10
            )
            confidence_category = "high"

        max_allowed_amount = current_balance * max_position_ratio
        enforce_minimum = get_threshold(
            "position_management.max_position_ratio_per_trade.enforce_minimum", True
        )

        # 最小ロット優先チェック
        if enforce_minimum and trade_amount <= min_trade_amount:
            # 最小ロット以下の場合は制限を無視して許可
            self.logger.info(
                f"💡 最小ロット優先適用: 制限¥{max_allowed_amount:,.0f} < 最小ロット¥{min_trade_amount:,.0f} → 最小ロット許可"
            )
            return {"allowed": True, "reason": "最小ロット優先による許可"}

        if trade_amount > max_allowed_amount:
            return {
                "allowed": False,
                "reason": f"1取引あたりの最大金額制限({confidence_category}信頼度)を超過。制限: ¥{max_allowed_amount:,.0f}, 要求: ¥{trade_amount:,.0f}",
            }

        return {"allowed": True, "reason": "取引サイズOK"}

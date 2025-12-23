"""
ポジション制限管理サービス - Phase 49完了

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
    ) -> Dict[str, Any]:
        """
        ポジション管理制限チェック（口座残高使い切り問題対策）

        Args:
            evaluation: 取引評価結果
            virtual_positions: 現在のポジションリスト
            last_order_time: 最後の注文時刻
            current_balance: 現在の残高
            regime: 市場レジーム（Phase 51.8: レジーム別ポジション制限）

        Returns:
            Dict: {"allowed": bool, "reason": str}
        """
        try:
            # 0. 最小資金要件チェック（動的ポジションサイジング対応）
            min_balance_check = self._check_minimum_balance(current_balance)
            if not min_balance_check["allowed"]:
                return min_balance_check

            # Phase 29.6 + Phase 31.1: クールダウンチェック（柔軟な判定）
            cooldown_check = await self._check_cooldown(evaluation, last_order_time)
            if not cooldown_check["allowed"]:
                return cooldown_check

            # 1. 最大ポジション数チェック（Phase 51.8: レジーム対応）
            position_count_check = self._check_max_positions(virtual_positions, regime)
            if not position_count_check["allowed"]:
                return position_count_check

            # 2. 残高利用率チェック
            capital_usage_check = self._check_capital_usage(current_balance)
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
        self, evaluation: TradeEvaluation, last_order_time: Optional[datetime]
    ) -> Dict[str, Any]:
        """
        クールダウンチェック（Phase 31.1: 柔軟な判定）

        Args:
            evaluation: 取引評価結果
            last_order_time: 最後の注文時刻

        Returns:
            Dict: {"allowed": bool, "reason": str}
        """
        cooldown_minutes = get_threshold("position_management.cooldown_minutes", 30)

        if not last_order_time or cooldown_minutes <= 0:
            return {"allowed": True, "reason": "クールダウンなし"}

        time_since_last_order = datetime.now() - last_order_time
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

    def _check_capital_usage(self, current_balance: float) -> Dict[str, Any]:
        """
        残高利用率チェック

        Args:
            current_balance: 現在の残高

        Returns:
            Dict: {"allowed": bool, "reason": str}
        """
        max_capital_usage = get_threshold("risk.max_capital_usage", 0.3)

        # 初期残高の取得（Phase 55.9: get_threshold()使用に変更）
        # 簡易的なモード判定
        if current_balance >= 90000:
            mode = "live"
        elif current_balance >= 8000:
            mode = "paper"
        else:
            mode = "backtest"

        if mode == "backtest":
            initial_balance = get_threshold("mode_balances.backtest.initial_balance", 100000.0)
        elif mode == "paper":
            initial_balance = get_threshold("mode_balances.paper.initial_balance", 100000.0)
        else:
            initial_balance = get_threshold("mode_balances.live.initial_balance", 100000.0)

        # 現在の使用率計算
        if initial_balance > 0:
            current_usage_ratio = (initial_balance - current_balance) / initial_balance
        else:
            current_usage_ratio = 1.0

        if current_usage_ratio >= max_capital_usage:
            return {
                "allowed": False,
                "reason": f"資金利用率制限({max_capital_usage * 100:.0f}%)に達しています。現在: {current_usage_ratio * 100:.1f}%",
            }

        return {"allowed": True, "reason": "資金利用率OK"}

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
                except Exception:
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
        if ml_confidence < 0.60:
            # 低信頼度
            max_position_ratio = get_threshold(
                "position_management.max_position_ratio_per_trade.low_confidence", 0.03
            )
            confidence_category = "low"
        elif ml_confidence < 0.75:
            # 中信頼度
            max_position_ratio = get_threshold(
                "position_management.max_position_ratio_per_trade.medium_confidence", 0.05
            )
            confidence_category = "medium"
        else:
            # 高信頼度
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

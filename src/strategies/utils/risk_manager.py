"""
リスク管理計算統合モジュール

4つの戦略で重複していたストップロス・テイクプロフィット・
ポジションサイズ計算を統合。戦略固有のパラメータは各戦略で設定。.
"""

from typing import Any, Dict, Optional, Tuple

from ...core.logger import get_logger
from .constants import DEFAULT_RISK_PARAMS, EntryAction


class RiskManager:
    """
    リスク管理計算統合クラス

    全戦略で共通するリスク管理計算を一元化。
    戦略固有のパラメータは各戦略の設定で上書き可能。.
    """

    @staticmethod
    def calculate_stop_loss_take_profit(
        action: str,
        current_price: float,
        current_atr: float,
        config: Dict[str, Any],
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        ストップロス・テイクプロフィット計算

        Args:
            action: エントリーアクション（buy/sell）
            current_price: 現在価格
            current_atr: 現在のATR値
            config: 戦略設定（stop_loss_atr_multiplier, take_profit_ratio含む）

        Returns:
            (stop_loss, take_profit)のタプル.
        """
        logger = get_logger()

        try:
            if action not in [EntryAction.BUY, EntryAction.SELL]:
                return None, None

            # パラメータ取得（戦略固有 or デフォルト）
            stop_loss_multiplier = config.get(
                "stop_loss_atr_multiplier",
                DEFAULT_RISK_PARAMS["stop_loss_atr_multiplier"],
            )
            take_profit_ratio = config.get(
                "take_profit_ratio", DEFAULT_RISK_PARAMS["take_profit_ratio"]
            )
            min_atr = config.get("min_atr_threshold", DEFAULT_RISK_PARAMS["min_atr_threshold"])

            # ATR最小値チェック（ゼロ除算回避）
            if current_atr < min_atr:
                logger.warning(f"ATR値が小さすぎます: {current_atr:.6f} < {min_atr}")
                current_atr = min_atr

            # ストップロス距離計算
            stop_loss_distance = current_atr * stop_loss_multiplier

            # BUY/SELL別の計算
            if action == EntryAction.BUY:
                stop_loss = current_price - stop_loss_distance
                take_profit = current_price + (stop_loss_distance * take_profit_ratio)
            else:  # SELL
                stop_loss = current_price + stop_loss_distance
                take_profit = current_price - (stop_loss_distance * take_profit_ratio)

            # 値の妥当性確認
            if stop_loss <= 0 or take_profit <= 0:
                logger.error(
                    f"無効なストップロス/テイクプロフィット: SL={stop_loss:.2f}, TP={take_profit:.2f}"
                )
                return None, None

            return stop_loss, take_profit

        except Exception as e:
            logger.error(f"ストップロス・テイクプロフィット計算エラー: {e}")
            return None, None

    @staticmethod
    def calculate_position_size(confidence: float, config: Dict[str, Any]) -> float:
        """
        ポジションサイズ計算

        Args:
            confidence: シグナル信頼度（0.0-1.0）
            config: 戦略設定（position_size_base含む）

        Returns:
            計算されたポジションサイズ.
        """
        logger = get_logger()

        try:
            # パラメータ取得
            base_size = config.get("position_size_base", DEFAULT_RISK_PARAMS["position_size_base"])
            max_size = config.get("max_position_size", DEFAULT_RISK_PARAMS["max_position_size"])

            # 信頼度による調整
            position_size = base_size * max(0.0, min(1.0, confidence))

            # 最大サイズ制限
            position_size = min(position_size, max_size)

            return position_size

        except Exception as e:
            logger.error(f"ポジションサイズ計算エラー: {e}")
            return 0.0

    @staticmethod
    def calculate_risk_ratio(current_price: float, stop_loss: Optional[float]) -> Optional[float]:
        """
        リスク比率計算

        Args:
            current_price: 現在価格
            stop_loss: ストップロス価格

        Returns:
            リスク比率（None if 計算不可）.
        """
        try:
            if stop_loss is None or current_price <= 0:
                return None

            risk_ratio = abs(stop_loss - current_price) / current_price
            return risk_ratio

        except Exception:
            return None

    @staticmethod
    def validate_risk_parameters(config: Dict[str, Any]) -> bool:
        """
        リスクパラメータの妥当性確認

        Args:
            config: 戦略設定

        Returns:
            パラメータが妥当かどうか.
        """
        logger = get_logger()

        try:
            # 必須パラメータ確認
            stop_loss_multiplier = config.get("stop_loss_atr_multiplier", 0)
            take_profit_ratio = config.get("take_profit_ratio", 0)
            position_size_base = config.get("position_size_base", 0)

            # 範囲チェック
            if not (0.5 <= stop_loss_multiplier <= 5.0):
                logger.warning(f"stop_loss_atr_multiplier範囲外: {stop_loss_multiplier}")
                return False

            if not (1.0 <= take_profit_ratio <= 10.0):
                logger.warning(f"take_profit_ratio範囲外: {take_profit_ratio}")
                return False

            if not (0.001 <= position_size_base <= 0.1):
                logger.warning(f"position_size_base範囲外: {position_size_base}")
                return False

            return True

        except Exception as e:
            logger.error(f"リスクパラメータ検証エラー: {e}")
            return False

"""
戦略共通ユーティリティ統合モジュール - Phase 28完了・Phase 29最適化版

戦略関連のユーティリティ機能を統合管理：
- 戦略定数：EntryAction、StrategyType統一
- リスク管理：戦略レベルリスク評価
- シグナル生成：統一的なシグナル構築

統合により関連機能を一元化し、管理しやすい構造を提供。

Phase 28完了・Phase 29最適化: 2025年9月27日.
"""

from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import pandas as pd

from ...core.logger import get_logger
from ..base.strategy_base import StrategySignal

# === 戦略共通定数定義 ===


class EntryAction:
    """エントリーアクション定数."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"


class StrategyType:
    """戦略タイプ定数."""

    MOCHIPOY_ALERT = "mochipoy_alert"
    ATR_BASED = "atr_based"
    BOLLINGER_BANDS = "bollinger_bands"
    DONCHIAN_CHANNEL = "donchian_channel"
    ADX_TREND = "adx_trend"
    MULTI_TIMEFRAME = "multi_timeframe"


# 基本リスク管理パラメータ（戦略で上書き可能）
DEFAULT_RISK_PARAMS: Dict[str, Any] = {
    # ストップロス・テイクプロフィット
    "stop_loss_atr_multiplier": 2.0,  # 一般的な設定
    "take_profit_ratio": 2.5,  # リワード・リスク比
    # ポジションサイズ
    "position_size_base": 0.02,  # 2%の基本設定
    # 計算設定
    "min_atr_threshold": 0.001,  # ATRの最小値（ゼロ除算回避）
    "max_position_size": 0.05,  # 最大ポジションサイズ（5%）
}


# === リスク管理計算クラス ===


class RiskManager:
    """
    リスク管理計算統合クラス

    全戦略で共通するリスク管理計算を一元化。
    戦略固有のパラメータは各戦略の設定で上書き可能。
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
            (stop_loss, take_profit)のタプル
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
            計算されたポジションサイズ
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
            リスク比率（None if 計算不可）
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
            パラメータが妥当かどうか
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


# === シグナル生成クラス ===


class SignalBuilder:
    """
    StrategySignal生成統合クラス

    全戦略で共通するシグナル生成処理を一元化。
    リスク管理計算も統合して処理。
    """

    @staticmethod
    def create_signal_with_risk_management(
        strategy_name: str,
        decision: Dict[str, Any],
        current_price: float,
        df: pd.DataFrame,
        config: Dict[str, Any],
        strategy_type: Optional[str] = None,
    ) -> StrategySignal:
        """
        リスク管理付きシグナル生成

        Args:
            strategy_name: 戦略名
            decision: 戦略の判定結果（action, confidence, strength等）
            current_price: 現在価格
            df: 市場データ（ATR計算用）
            config: 戦略設定
            strategy_type: 戦略タイプ（メタデータ用）

        Returns:
            完全なStrategySignal
        """
        logger = get_logger()

        try:
            action = decision.get("action", EntryAction.HOLD)
            confidence = decision.get("confidence", 0.0)
            strength = decision.get("strength", 0.0)
            reason = decision.get("analysis", decision.get("reason", ""))

            # リスク管理計算（エントリーシグナルのみ）
            stop_loss = None
            take_profit = None
            position_size = None
            risk_ratio = None

            if action in [EntryAction.BUY, EntryAction.SELL]:
                # ATR取得
                current_atr = SignalBuilder._get_current_atr(df)
                if current_atr is None:
                    logger.warning(f"ATR取得失敗: {strategy_name}")
                    return SignalBuilder._create_error_signal(
                        strategy_name, current_price, "ATR取得失敗"
                    )

                # ストップロス・テイクプロフィット計算
                stop_loss, take_profit = RiskManager.calculate_stop_loss_take_profit(
                    action, current_price, current_atr, config
                )

                # ポジションサイズ計算
                position_size = RiskManager.calculate_position_size(confidence, config)

                # リスク比率計算
                risk_ratio = RiskManager.calculate_risk_ratio(current_price, stop_loss)

            # メタデータ作成
            metadata = {
                "strategy_type": strategy_type,
                "risk_calculated": action in [EntryAction.BUY, EntryAction.SELL],
                "decision_metadata": decision.get("metadata", {}),
            }

            # StrategySignal生成
            return StrategySignal(
                strategy_name=strategy_name,
                timestamp=datetime.now(),
                action=action,
                confidence=confidence,
                strength=strength,
                current_price=current_price,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                position_size=position_size,
                risk_ratio=risk_ratio,
                reason=reason,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"シグナル生成エラー ({strategy_name}): {e}")
            return SignalBuilder._create_error_signal(
                strategy_name, current_price, f"シグナル生成エラー: {e}"
            )

    @staticmethod
    def create_hold_signal(
        strategy_name: str,
        current_price: float,
        reason: str = "条件不適合",
        strategy_type: Optional[str] = None,
    ) -> StrategySignal:
        """
        ホールドシグナル生成

        Args:
            strategy_name: 戦略名
            current_price: 現在価格
            reason: ホールド理由
            strategy_type: 戦略タイプ

        Returns:
            ホールドStrategySignal
        """
        return StrategySignal(
            strategy_name=strategy_name,
            timestamp=datetime.now(),
            action=EntryAction.HOLD,
            confidence=0.5,  # ニュートラル
            strength=0.0,
            current_price=current_price,
            reason=reason,
            metadata={"strategy_type": strategy_type},
        )

    @staticmethod
    def _get_current_atr(df: pd.DataFrame) -> Optional[float]:
        """
        現在のATR値取得

        Args:
            df: 市場データ

        Returns:
            ATR値（None if 取得失敗）
        """
        try:
            if "atr_14" not in df.columns or len(df) == 0:
                return None

            atr_value = float(df["atr_14"].iloc[-1])
            return atr_value if atr_value > 0 else None

        except Exception:
            return None

    @staticmethod
    def _create_error_signal(
        strategy_name: str, current_price: float, error_message: str
    ) -> StrategySignal:
        """
        エラー時のフォールバックシグナル生成

        Args:
            strategy_name: 戦略名
            current_price: 現在価格
            error_message: エラーメッセージ

        Returns:
            エラー用ホールドシグナル
        """
        return StrategySignal(
            strategy_name=strategy_name,
            timestamp=datetime.now(),
            action=EntryAction.HOLD,
            confidence=0.0,
            strength=0.0,
            current_price=current_price,
            reason=error_message,
            metadata={"error": True},
        )

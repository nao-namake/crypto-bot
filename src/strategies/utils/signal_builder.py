"""
シグナル生成統合モジュール

4つの戦略で重複していたStrategySignal生成処理を統合。
リスク管理計算も含めて一元化。.
"""

from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd

from ...core.logger import get_logger
from ..base.strategy_base import StrategySignal
from .constants import EntryAction, StrategyType
from .risk_manager import RiskManager


class SignalBuilder:
    """
    StrategySignal生成統合クラス

    全戦略で共通するシグナル生成処理を一元化。
    リスク管理計算も統合して処理。.
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
            完全なStrategySignal.
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
            ホールドStrategySignal.
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
            ATR値（None if 取得失敗）.
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
            エラー用ホールドシグナル.
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

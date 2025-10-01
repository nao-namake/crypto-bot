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
from typing import Any, Dict, List, Optional, Tuple

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
    def _extract_15m_atr(
        df: pd.DataFrame, multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> Optional[float]:
        """
        Phase 31: 15m足ATR優先取得・4h足ATRフォールバック

        Args:
            df: メインタイムフレームデータ（4h足）
            multi_timeframe_data: マルチタイムフレームデータ

        Returns:
            ATR値（15m優先、なければ4h、取得失敗ならNone）
        """
        logger = get_logger()

        # Phase 31: 15m足ATR優先取得
        if multi_timeframe_data and "15m" in multi_timeframe_data:
            try:
                df_15m = multi_timeframe_data["15m"]
                if "atr_14" in df_15m.columns and len(df_15m) > 0:
                    atr_15m = float(df_15m["atr_14"].iloc[-1])
                    if atr_15m > 0:
                        logger.info(f"✅ Phase 31: 15m足ATR使用 = {atr_15m:.0f}円")
                        return atr_15m
            except Exception as e:
                logger.warning(f"15m足ATR取得失敗: {e}")

        # フォールバック: 4h足ATR取得
        try:
            if "atr_14" in df.columns and len(df) > 0:
                atr_4h = float(df["atr_14"].iloc[-1])
                if atr_4h > 0:
                    logger.info(f"⚠️ Phase 31フォールバック: 4h足ATR使用 = {atr_4h:.0f}円")
                    return atr_4h
        except Exception as e:
            logger.error(f"4h足ATR取得失敗: {e}")

        return None

    @staticmethod
    def _calculate_adaptive_atr_multiplier(
        current_atr: float, atr_history: Optional[List[float]] = None
    ) -> float:
        """
        Phase 30: 適応型ATR倍率計算

        Args:
            current_atr: 現在のATR値
            atr_history: ATR履歴（ボラティリティ判定用、Noneの場合はデフォルト倍率）

        Returns:
            適応型ATR倍率
        """
        from ...core.config import get_threshold

        # 適応型ATR機能が無効な場合
        if not get_threshold("position_management.stop_loss.adaptive_atr.enabled", True):
            return get_threshold("position_management.stop_loss.default_atr_multiplier", 2.0)

        # ATR履歴がない場合はデフォルト
        if not atr_history or len(atr_history) < 10:
            return get_threshold(
                "position_management.stop_loss.adaptive_atr.normal_volatility.multiplier", 2.0
            )

        # ATR平均計算
        import numpy as np

        avg_atr = np.mean(atr_history)

        # ボラティリティ状態判定
        low_threshold = get_threshold(
            "position_management.stop_loss.adaptive_atr.low_volatility.threshold_ratio", 0.7
        )
        high_threshold = get_threshold(
            "position_management.stop_loss.adaptive_atr.high_volatility.threshold_ratio", 1.3
        )

        volatility_ratio = current_atr / avg_atr if avg_atr > 0 else 1.0

        # ボラティリティに応じた倍率選択
        if volatility_ratio < low_threshold:
            # 低ボラティリティ → 広めのSL
            return get_threshold(
                "position_management.stop_loss.adaptive_atr.low_volatility.multiplier", 2.5
            )
        elif volatility_ratio > high_threshold:
            # 高ボラティリティ → 狭めのSL（急変時対策）
            return get_threshold(
                "position_management.stop_loss.adaptive_atr.high_volatility.multiplier", 1.5
            )
        else:
            # 通常ボラティリティ → 標準SL
            return get_threshold(
                "position_management.stop_loss.adaptive_atr.normal_volatility.multiplier", 2.0
            )

    @staticmethod
    def calculate_stop_loss_take_profit(
        action: str,
        current_price: float,
        current_atr: float,
        config: Dict[str, Any],
        atr_history: Optional[List[float]] = None,
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        ストップロス・テイクプロフィット計算

        Args:
            action: エントリーアクション（buy/sell）
            current_price: 現在価格
            current_atr: 現在のATR値（Phase 30: 15分足ATR推奨）
            config: 戦略設定（stop_loss_atr_multiplier, take_profit_ratio含む）
            atr_history: ATR履歴（Phase 30: 適応型ATR用）

        Returns:
            (stop_loss, take_profit)のタプル
        """
        logger = get_logger()
        from ...core.config import get_threshold

        try:
            if action not in [EntryAction.BUY, EntryAction.SELL]:
                return None, None

            # Phase 30: 適応型ATR倍率計算
            stop_loss_multiplier = RiskManager._calculate_adaptive_atr_multiplier(
                current_atr, atr_history
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

            # Phase 30: 最小SL距離保証
            # Phase 32.1修正: ATR優先・動的保証実現
            min_distance_enabled = get_threshold(
                "position_management.stop_loss.min_distance.enabled", True
            )
            if min_distance_enabled:
                override_atr = get_threshold(
                    "position_management.stop_loss.min_distance.override_atr", False
                )

                if override_atr:
                    # 旧動作: 固定1%保証がATRを上書き
                    min_distance_ratio = get_threshold(
                        "position_management.stop_loss.min_distance.ratio", 0.01
                    )
                    min_sl_distance = current_price * min_distance_ratio

                    if stop_loss_distance < min_sl_distance:
                        logger.info(
                            f"📏 固定1%SL距離保証適用: {stop_loss_distance:.0f}円 → {min_sl_distance:.0f}円"
                        )
                        stop_loss_distance = min_sl_distance
                else:
                    # Phase 32.1新動作: ATR×倍率を最小値として保証（動的保証）
                    min_atr_multiplier = get_threshold(
                        "position_management.stop_loss.min_distance.min_atr_multiplier", 1.5
                    )
                    min_atr_based = current_atr * min_atr_multiplier

                    # ATRベース最小値と計算値を比較
                    if stop_loss_distance < min_atr_based:
                        logger.info(
                            f"📏 ATRベース動的SL保証適用: {stop_loss_distance:.0f}円 → {min_atr_based:.0f}円 "
                            f"(ATR {current_atr:.0f}円 × {min_atr_multiplier:.1f}倍)"
                        )
                        stop_loss_distance = min_atr_based

                    # Phase 32.1修正: ATR極小時のみ固定1%フォールバック適用
                    # ATRベース最小保証より小さい場合のみ固定1%を適用
                    min_distance_ratio = get_threshold(
                        "position_management.stop_loss.min_distance.ratio", 0.01
                    )
                    absolute_min = current_price * min_distance_ratio

                    # ATRベース最小保証（min_atr_based）と固定1%を比較し、
                    # ATRベース最小保証より計算値が小さい場合のみ固定1%適用
                    if stop_loss_distance < min_atr_based and stop_loss_distance < absolute_min:
                        logger.warning(
                            f"⚠️ ATR極小・固定1%フォールバック適用: {stop_loss_distance:.0f}円 → {absolute_min:.0f}円 "
                            f"(ATR {current_atr:.0f}円が極小のため)"
                        )
                        stop_loss_distance = absolute_min

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

            logger.info(
                f"🎯 Phase 30 SL/TP計算: ATR={current_atr:.0f}円, 倍率={stop_loss_multiplier:.2f}, "
                f"SL距離={stop_loss_distance:.0f}円（{stop_loss_distance / current_price * 100:.2f}%）"
            )

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
        multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None,
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
            multi_timeframe_data: マルチタイムフレームデータ（Phase 31対応）

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
                # Phase 31: 15m足ATR優先取得
                current_atr = RiskManager._extract_15m_atr(df, multi_timeframe_data)
                if current_atr is None:
                    logger.warning(f"ATR取得失敗: {strategy_name}")
                    return SignalBuilder._create_error_signal(
                        strategy_name, current_price, "ATR取得失敗"
                    )

                # Phase 30: ATR履歴取得（適応型ATR用）
                atr_history = None
                if multi_timeframe_data and "15m" in multi_timeframe_data:
                    try:
                        df_15m = multi_timeframe_data["15m"]
                        if "atr_14" in df_15m.columns:
                            atr_history = df_15m["atr_14"].dropna().tail(20).tolist()
                    except Exception:
                        pass

                # ストップロス・テイクプロフィット計算
                stop_loss, take_profit = RiskManager.calculate_stop_loss_take_profit(
                    action, current_price, current_atr, config, atr_history
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

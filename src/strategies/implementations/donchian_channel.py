"""
Donchian Channel戦略実装 - Phase 56.8 平均回帰戦略リファクタリング

タイトレンジ向け平均回帰戦略。
直列評価方式でシンプルかつ高品質なシグナル生成。

設計思想:
- ADXフィルタ: トレンド相場を除外（ADX < 25）
- 極端位置: チャネル端部（< 0.10 or > 0.90）でのみシグナル
- RSIフィルタ: 方向確認で偽シグナル削減

Phase 56.8:
- 5段階判定 → 直列評価方式にシンプル化
- ブレイクアウトロジック削除（タイトレンジ不要）
- 中央域・弱シグナル複雑計算削除
- コード550行 → 約280行に圧縮
"""

from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd

from ...core.config import get_threshold
from ...core.logger import get_logger
from ..base.strategy_base import StrategyBase, StrategySignal
from ..strategy_registry import StrategyRegistry
from ..utils.strategy_utils import SignalBuilder, StrategyType


@StrategyRegistry.register(name="DonchianChannel", strategy_type=StrategyType.DONCHIAN_CHANNEL)
class DonchianChannelStrategy(StrategyBase):
    """
    Donchian Channel平均回帰戦略

    Phase 56.8: 直列評価方式
    1. ADXフィルタ（レンジ相場確認）
    2. 極端位置確認（チャネル端部）
    3. RSIフィルタ（方向確認）
    4. シグナル発生（信頼度計算）
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """戦略初期化"""
        super().__init__("DonchianChannel")
        self.config = config or {}
        self.logger = get_logger()

        # 直列評価パラメータ
        self.adx_max_threshold = get_threshold("strategies.donchian_channel.adx_max_threshold", 25)
        self.extreme_zone_threshold = get_threshold(
            "strategies.donchian_channel.extreme_zone_threshold", 0.10
        )
        self.rsi_oversold = get_threshold("strategies.donchian_channel.rsi_oversold", 40)
        self.rsi_overbought = get_threshold("strategies.donchian_channel.rsi_overbought", 60)

        # 信頼度設定
        self.base_confidence = get_threshold("strategies.donchian_channel.base_confidence", 0.40)
        self.max_confidence = get_threshold("strategies.donchian_channel.max_confidence", 0.60)
        self.min_confidence = get_threshold("strategies.donchian_channel.min_confidence", 0.30)
        self.hold_confidence = get_threshold("strategies.donchian_channel.hold_confidence", 0.25)

        # 信頼度ボーナス
        self.extreme_position_bonus = get_threshold(
            "strategies.donchian_channel.extreme_position_bonus", 0.10
        )
        self.rsi_confirmation_bonus = get_threshold(
            "strategies.donchian_channel.rsi_confirmation_bonus", 0.05
        )

        self.logger.info(
            f"Donchian Channel戦略初期化完了 - "
            f"ADX閾値: {self.adx_max_threshold}, "
            f"極端位置: {self.extreme_zone_threshold}"
        )

    def get_required_features(self) -> list[str]:
        """必要特徴量リスト"""
        return [
            "close",
            "high",
            "low",
            "donchian_high_20",
            "donchian_low_20",
            "channel_position",
            "atr_14",
            "adx_14",
            "rsi_14",
        ]

    def analyze(
        self, df: pd.DataFrame, multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> StrategySignal:
        """
        シグナル生成（直列評価方式）

        Args:
            df: 市場データ
            multi_timeframe_data: マルチタイムフレームデータ

        Returns:
            StrategySignal
        """
        try:
            # データ検証
            if not self._validate_data(df):
                return self._create_hold_signal(df, "データ不足")

            latest = df.iloc[-1]
            current_price = float(latest["close"])

            # チャネル情報取得
            channel_position = float(latest["channel_position"])
            adx = float(latest["adx_14"]) if pd.notna(latest["adx_14"]) else 0
            rsi = float(latest["rsi_14"]) if pd.notna(latest["rsi_14"]) else 50

            # ========================================
            # 直列評価: Step 1 - レンジ相場確認
            # ========================================
            if adx > self.adx_max_threshold:
                return self._create_hold_signal(
                    df, f"トレンド相場除外（ADX={adx:.1f} > {self.adx_max_threshold}）"
                )

            # ========================================
            # 直列評価: Step 2 - 極端位置確認
            # ========================================
            if channel_position < self.extreme_zone_threshold:
                direction = "buy"
            elif channel_position > (1 - self.extreme_zone_threshold):
                direction = "sell"
            else:
                return self._create_hold_signal(df, f"中央域HOLD（位置={channel_position:.3f}）")

            # ========================================
            # 直列評価: Step 3 - RSIフィルタ
            # ========================================
            if direction == "buy" and rsi > self.rsi_oversold:
                return self._create_hold_signal(
                    df, f"RSI高すぎ（RSI={rsi:.1f} > {self.rsi_oversold}）"
                )
            if direction == "sell" and rsi < self.rsi_overbought:
                return self._create_hold_signal(
                    df, f"RSI低すぎ（RSI={rsi:.1f} < {self.rsi_overbought}）"
                )

            # ========================================
            # 直列評価: Step 4 - シグナル発生
            # ========================================
            confidence = self._calculate_confidence(channel_position, rsi, direction)

            if confidence < self.min_confidence:
                return self._create_hold_signal(
                    df, f"信頼度不足（{confidence:.3f} < {self.min_confidence}）"
                )

            # シグナル生成
            reason = self._create_reason(direction, channel_position, rsi, adx)
            return self._create_signal(
                action=direction,
                confidence=confidence,
                reason=reason,
                current_price=current_price,
                df=df,
                channel_position=channel_position,
                multi_timeframe_data=multi_timeframe_data,
            )

        except Exception as e:
            self.logger.conditional_log(
                f"[DonchianChannel] シグナル生成エラー: {e}",
                level="error",
                backtest_level="debug",
            )
            return self._create_hold_signal(df, f"エラー: {str(e)}")

    def _validate_data(self, df: pd.DataFrame) -> bool:
        """データ検証"""
        required = self.get_required_features()
        missing = [col for col in required if col not in df.columns]
        if missing:
            self.logger.warning(f"[DonchianChannel] 不足特徴量: {missing}")
            return False

        if len(df) < 20:
            self.logger.warning(f"[DonchianChannel] データ不足: {len(df)} < 20")
            return False

        latest = df.iloc[-1]
        critical = ["close", "donchian_high_20", "donchian_low_20", "channel_position"]
        if latest[critical].isna().any():
            self.logger.warning("[DonchianChannel] 最新データにNaN")
            return False

        return True

    def _calculate_confidence(self, channel_position: float, rsi: float, direction: str) -> float:
        """
        信頼度計算（シンプル化）

        Args:
            channel_position: チャネル位置（0-1）
            rsi: RSI値
            direction: "buy" or "sell"

        Returns:
            信頼度（0.0-1.0）
        """
        confidence = self.base_confidence

        # 極端位置ボーナス（< 0.05 or > 0.95）
        if direction == "buy" and channel_position < 0.05:
            confidence += self.extreme_position_bonus
        elif direction == "sell" and channel_position > 0.95:
            confidence += self.extreme_position_bonus

        # RSI確認ボーナス（< 30 or > 70）
        if direction == "buy" and rsi < 30:
            confidence += self.rsi_confirmation_bonus
        elif direction == "sell" and rsi > 70:
            confidence += self.rsi_confirmation_bonus

        # 位置に応じた追加ボーナス
        if direction == "buy":
            position_bonus = (self.extreme_zone_threshold - channel_position) * 0.5
        else:
            position_bonus = (channel_position - (1 - self.extreme_zone_threshold)) * 0.5
        confidence += max(0, position_bonus)

        return min(self.max_confidence, max(self.min_confidence, confidence))

    def _create_reason(
        self, direction: str, channel_position: float, rsi: float, adx: float
    ) -> str:
        """シグナル理由生成"""
        if direction == "buy":
            return f"下限平均回帰（位置={channel_position:.3f}, " f"RSI={rsi:.1f}, ADX={adx:.1f}）"
        else:
            return f"上限平均回帰（位置={channel_position:.3f}, " f"RSI={rsi:.1f}, ADX={adx:.1f}）"

    def _create_hold_signal(self, df: pd.DataFrame, reason: str) -> StrategySignal:
        """HOLDシグナル生成"""
        current_price = float(df["close"].iloc[-1]) if "close" in df.columns else 0.0
        return StrategySignal(
            strategy_name=self.name,
            timestamp=datetime.now(),
            action="hold",
            confidence=self.hold_confidence,
            strength=self.hold_confidence * 0.5,
            current_price=current_price,
            reason=f"Donchian: {reason}",
            metadata={"signal_type": "donchian_hold"},
        )

    def _create_signal(
        self,
        action: str,
        confidence: float,
        reason: str,
        current_price: float,
        df: pd.DataFrame,
        channel_position: float,
        multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> StrategySignal:
        """シグナル生成（SignalBuilder使用）"""
        decision = {
            "action": action,
            "confidence": confidence,
            "strength": confidence,
            "reason": reason,
            "metadata": {
                "channel_position": channel_position,
                "signal_type": "donchian_mean_reversion",
            },
        }

        return SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.name,
            decision=decision,
            current_price=current_price,
            df=df,
            config=self.config,
            strategy_type=StrategyType.DONCHIAN_CHANNEL,
            multi_timeframe_data=multi_timeframe_data,
        )

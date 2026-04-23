"""
CMF Reversal戦略実装 - Phase 74

Chaikin Money Flow（出来高フロー）の反転を検出するレンジ型戦略。
DonchianChannel（勝率14%）の置換として導入。

設計思想:
- CMFが負（売り圧力）から反転 → BUYシグナル
- CMFが正（買い圧力）から反転 → SELLシグナル
- ADXフィルタ: トレンド相場を除外
- RSI確認: ボーナス/ペナルティとして使用（HOLDではなく）
- メタラベリング（Phase 73-D）と連携: MLが品質フィルタとして機能するため
  戦略は広くシグナルを出し、低品質はMLが除外する
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from ...core.config import get_threshold
from ...core.logger import get_logger
from ..base.strategy_base import StrategyBase, StrategySignal
from ..strategy_registry import StrategyRegistry
from ..utils import EntryAction, SignalBuilder, StrategyType


@StrategyRegistry.register(name="CMFReversal", strategy_type=StrategyType.CMF_REVERSAL)
class CMFReversalStrategy(StrategyBase):
    """
    CMF Reversal平均回帰戦略

    1. ADXフィルタ（レンジ相場確認）
    2. CMF方向判定（売り圧力/買い圧力の検出）
    3. RSIボーナス（方向確認→信頼度調整）
    4. シグナル発生（信頼度計算）
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """戦略初期化"""
        super().__init__("CMFReversal")
        self.config = config or {}
        self.logger = get_logger()

        # 設定読み込み
        self.cmf_buy_threshold = self.config.get(
            "cmf_buy_threshold",
            get_threshold("strategies.cmf_reversal.cmf_buy_threshold", -0.10),
        )
        self.cmf_sell_threshold = self.config.get(
            "cmf_sell_threshold",
            get_threshold("strategies.cmf_reversal.cmf_sell_threshold", 0.10),
        )
        self.cmf_extreme_threshold = self.config.get(
            "cmf_extreme_threshold",
            get_threshold("strategies.cmf_reversal.cmf_extreme_threshold", 0.15),
        )
        self.adx_max_threshold = self.config.get(
            "adx_max_threshold",
            get_threshold("strategies.cmf_reversal.adx_max_threshold", 28),
        )
        self.base_confidence = self.config.get(
            "base_confidence",
            get_threshold("strategies.cmf_reversal.base_confidence", 0.40),
        )
        self.max_confidence = self.config.get(
            "max_confidence",
            get_threshold("strategies.cmf_reversal.max_confidence", 0.60),
        )
        self.min_confidence = self.config.get(
            "min_confidence",
            get_threshold("strategies.cmf_reversal.min_confidence", 0.30),
        )
        self.hold_confidence = self.config.get(
            "hold_confidence",
            get_threshold("strategies.cmf_reversal.hold_confidence", 0.25),
        )
        self.extreme_bonus = self.config.get(
            "extreme_position_bonus",
            get_threshold("strategies.cmf_reversal.extreme_position_bonus", 0.10),
        )
        self.rsi_confirmation_bonus = self.config.get(
            "rsi_confirmation_bonus",
            get_threshold("strategies.cmf_reversal.rsi_confirmation_bonus", 0.05),
        )
        self.rsi_mismatch_penalty = self.config.get(
            "rsi_mismatch_penalty",
            get_threshold("strategies.cmf_reversal.rsi_mismatch_penalty", 0.08),
        )
        self.rsi_overbought = self.config.get(
            "rsi_overbought",
            get_threshold("strategies.cmf_reversal.rsi_overbought", 52),
        )
        self.rsi_oversold = self.config.get(
            "rsi_oversold",
            get_threshold("strategies.cmf_reversal.rsi_oversold", 48),
        )

        self.logger.info(
            f"CMFReversal戦略初期化完了 - "
            f"CMF閾値: buy<{self.cmf_buy_threshold}, sell>{self.cmf_sell_threshold}, "
            f"ADX閾値: {self.adx_max_threshold}"
        )

    def analyze(
        self,
        df: pd.DataFrame,
        multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> StrategySignal:
        """
        市場分析とシグナル生成

        CMFの値から出来高フローの方向を判定し、反転シグナルを生成。
        """
        try:
            current_price = float(df["close"].iloc[-1])

            # Step 1: データ検証
            required = self.get_required_features()
            missing = [f for f in required if f not in df.columns]
            if missing:
                return SignalBuilder.create_hold_signal(
                    strategy_name=self.name,
                    current_price=current_price,
                    reason=f"必要特徴量不足: {missing}",
                    strategy_type=StrategyType.CMF_REVERSAL,
                    confidence=self.hold_confidence,
                )

            # Step 2: ADXフィルタ（トレンド相場除外）
            adx = float(df["adx_14"].iloc[-1])
            if adx > self.adx_max_threshold:
                return SignalBuilder.create_hold_signal(
                    strategy_name=self.name,
                    current_price=current_price,
                    reason=f"トレンド相場除外 (ADX={adx:.1f} > {self.adx_max_threshold})",
                    strategy_type=StrategyType.CMF_REVERSAL,
                    confidence=self.hold_confidence,
                )

            # Step 3: CMF方向判定
            cmf = float(df["cmf_20"].iloc[-1])

            if cmf < self.cmf_buy_threshold:
                # 売り圧力が強い → 反転期待でBUY
                direction = "buy"
            elif cmf > self.cmf_sell_threshold:
                # 買い圧力が強い → 反転期待でSELL
                direction = "sell"
            else:
                return SignalBuilder.create_hold_signal(
                    strategy_name=self.name,
                    current_price=current_price,
                    reason=f"CMF中間帯 ({cmf:.3f})",
                    strategy_type=StrategyType.CMF_REVERSAL,
                    confidence=self.hold_confidence,
                )

            # Step 4: 信頼度計算
            confidence = self._calculate_confidence(df, cmf, direction)

            if confidence < self.min_confidence:
                return SignalBuilder.create_hold_signal(
                    strategy_name=self.name,
                    current_price=current_price,
                    reason=f"信頼度不足 ({confidence:.3f} < {self.min_confidence})",
                    strategy_type=StrategyType.CMF_REVERSAL,
                    confidence=self.hold_confidence,
                )

            # Step 5: シグナル生成
            # Phase 83A-1: utils 配下の EntryAction を使用（他5戦略と統一）
            action = EntryAction.BUY if direction == "buy" else EntryAction.SELL

            decision = {
                "action": action,
                "confidence": confidence,
                "strength": abs(cmf) / 0.3,  # CMF値を0-1に正規化（0.3を最大として）
                "analysis": (
                    f"CMFReversal: {direction.upper()} "
                    f"(CMF={cmf:.3f}, ADX={adx:.1f}, conf={confidence:.3f})"
                ),
            }

            signal = SignalBuilder.create_signal_with_risk_management(
                strategy_name=self.name,
                decision=decision,
                current_price=current_price,
                df=df,
                config=self.config,
                strategy_type=StrategyType.CMF_REVERSAL,
                multi_timeframe_data=multi_timeframe_data,
            )

            self.logger.info(
                f"[CMFReversal] シグナル生成: {signal.action} "
                f"(信頼度: {signal.confidence:.3f}, CMF: {cmf:.3f})"
            )
            return signal

        except Exception as e:
            self.logger.error(f"[CMFReversal] 分析エラー: {e}")
            return SignalBuilder.create_hold_signal(
                strategy_name=self.name,
                current_price=float(df["close"].iloc[-1]) if len(df) > 0 else 0,
                reason=f"分析エラー: {e}",
                strategy_type=StrategyType.CMF_REVERSAL,
                confidence=self.hold_confidence,
            )

    def _calculate_confidence(self, df: pd.DataFrame, cmf: float, direction: str) -> float:
        """信頼度計算"""
        confidence = self.base_confidence

        # CMF極端値ボーナス
        if abs(cmf) > self.cmf_extreme_threshold:
            confidence += self.extreme_bonus

        # RSI確認ボーナス/ペナルティ
        try:
            rsi = float(df["rsi_14"].iloc[-1])
            if direction == "buy" and rsi < self.rsi_oversold:
                confidence += self.rsi_confirmation_bonus
            elif direction == "sell" and rsi > self.rsi_overbought:
                confidence += self.rsi_confirmation_bonus
            elif direction == "buy" and rsi > self.rsi_overbought:
                confidence -= self.rsi_mismatch_penalty
            elif direction == "sell" and rsi < self.rsi_oversold:
                confidence -= self.rsi_mismatch_penalty
        except (KeyError, IndexError):
            pass  # RSIがなくても続行

        return min(self.max_confidence, max(self.min_confidence, confidence))

    def get_required_features(self) -> List[str]:
        """必要特徴量リスト"""
        return ["close", "high", "low", "cmf_20", "adx_14", "rsi_14", "atr_14"]

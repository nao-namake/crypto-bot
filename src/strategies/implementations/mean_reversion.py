"""
MeanReversion戦略実装 - Phase 60.15

移動平均乖離反転戦略（BBReversalパターン統一）:
- BB位置・RSI・SMA乖離の中央からの偏り度に基づく動的信頼度
- 0.5/50/0を中央として、乖離が大きいほど信頼度が高い
- レンジ相場特化（ADX < 45）

特徴:
- Phase 60.15: BBReversalパターン統一（動的信頼度計算）
- 3指標（BB/RSI/SMA乖離）の重み付け偏り計算
- HOLDでも動的信頼度使用（0.15~0.55範囲）
- 4戦略統一アーキテクチャ

Phase 60.15: BBReversal/StochasticReversal/ATRBasedと同一パターン
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from ...core.config.threshold_manager import get_threshold
from ...core.logger import get_logger
from ..base.strategy_base import StrategyBase, StrategySignal
from ..strategy_registry import StrategyRegistry
from ..utils.strategy_utils import EntryAction, SignalBuilder, StrategyType


@StrategyRegistry.register(name="MeanReversion", strategy_type=StrategyType.MEAN_REVERSION)
class MeanReversionStrategy(StrategyBase):
    """
    MeanReversion戦略 - 移動平均乖離反転戦略

    シグナル生成ロジック（OR条件）:
    1. BUY: RSI < 30 OR bb_position < 0.1 OR price < SMA20 * 0.98
    2. SELL: RSI > 70 OR bb_position > 0.9 OR price > SMA20 * 1.02
    3. ADX < 25 でのみ有効（レンジ相場特化）

    リスク管理:
    - SL距離: ATR × 1.5（レンジ相場に適した設定）
    - TP距離: thresholds.yaml設定優先
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        MeanReversion戦略初期化

        Args:
            config: 戦略固有設定（Noneの場合はthresholds.yamlから取得）
        """
        # thresholds.yamlから設定読み込み
        # Phase 60.15: BBReversalパターン統一（動的信頼度計算）
        default_config = {
            # Phase 60.15: 動的信頼度計算パラメータ
            "min_confidence": get_threshold("strategies.mean_reversion.min_confidence", 0.15),
            "max_confidence": get_threshold("strategies.mean_reversion.max_confidence", 0.55),
            "signal_threshold": get_threshold("strategies.mean_reversion.signal_threshold", 0.4),
            "bb_weight": get_threshold("strategies.mean_reversion.bb_weight", 0.3),
            "rsi_weight": get_threshold("strategies.mean_reversion.rsi_weight", 0.3),
            "sma_weight": get_threshold("strategies.mean_reversion.sma_weight", 0.4),
            # SMA乖離閾値
            "sma_deviation_threshold": get_threshold(
                "strategies.mean_reversion.sma_deviation_threshold", 0.008
            ),
            # レンジ相場判定
            "adx_range_threshold": get_threshold(
                "strategies.mean_reversion.adx_range_threshold", 45
            ),
            # SL設定
            "sl_multiplier": get_threshold("strategies.mean_reversion.sl_multiplier", 1.5),
            # TP/SL設定（thresholds.yaml優先）
            "max_loss_ratio": get_threshold("position_management.stop_loss.max_loss_ratio", 0.015),
            "min_profit_ratio": get_threshold(
                "position_management.take_profit.min_profit_ratio", 0.010
            ),
            "take_profit_ratio": get_threshold(
                "position_management.take_profit.default_ratio", 1.29
            ),
        }

        # 設定マージ
        merged_config = {**default_config, **(config or {})}
        super().__init__(name="MeanReversion", config=merged_config)

        self.logger = get_logger()
        self.logger.info(
            f"MeanReversion戦略初期化: SMA乖離閾値={self.config['sma_deviation_threshold']}, "
            f"ADX閾値={self.config['adx_range_threshold']}, "
            f"信頼度範囲=({self.config['min_confidence']}-{self.config['max_confidence']})"
        )

    def analyze(
        self, df: pd.DataFrame, multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> StrategySignal:
        """
        MeanReversion戦略分析

        Args:
            df: 4時間足データ（特徴量含む）
            multi_timeframe_data: マルチタイムフレームデータ（15m足ATR使用）

        Returns:
            StrategySignal（BUY/SELL/HOLD）
        """
        try:
            # 1. データ検証
            required_features = self.get_required_features()
            if df is None or df.empty:
                self.logger.warning("MeanReversion: データが空です")
                return self._create_hold_signal("no_data", df)

            missing_features = [f for f in required_features if f not in df.columns]
            if missing_features:
                self.logger.warning(f"MeanReversion: 必須特徴量不足: {missing_features}")
                return self._create_hold_signal("missing_features", df)

            # 2. 最新データ取得
            latest = df.iloc[-1]
            current_price = float(latest["close"])

            self.logger.debug(
                f"MeanReversion分析開始: 価格={current_price:.0f}円, "
                f"BB位置={latest['bb_position']:.2f}, "
                f"RSI={latest['rsi_14']:.1f}, "
                f"ADX={latest['adx_14']:.1f}"
            )

            # 3. レンジ相場判定（ADX < 25）
            adx = float(latest["adx_14"])
            if adx >= self.config["adx_range_threshold"]:
                reason = f"トレンド相場（ADX={adx:.1f} >= {self.config['adx_range_threshold']}）"
                self.logger.debug(f"MeanReversion: {reason}")
                return self._create_hold_signal(reason, df)

            # 4. MeanReversionシグナル分析（OR条件）
            decision = self._analyze_mean_reversion_signal(df)

            self.logger.info(
                f"MeanReversion判定: {decision['action']} "
                f"(信頼度={decision['confidence']:.2f}, 強度={decision['strength']:.2f})"
            )

            # 5. SignalBuilder使用（リスク管理統合）
            return SignalBuilder.create_signal_with_risk_management(
                strategy_name=self.name,
                decision=decision,
                current_price=current_price,
                df=df,
                config=self.config,
                strategy_type=StrategyType.MEAN_REVERSION,
                multi_timeframe_data=multi_timeframe_data,
            )

        except Exception as e:
            self.logger.error(f"MeanReversion分析エラー: {e}", exc_info=True)
            return self._create_hold_signal(f"分析エラー: {e}", df)

    def get_required_features(self) -> List[str]:
        """
        必須特徴量リスト

        Returns:
            必須特徴量名リスト
        """
        return [
            "close",
            "close_ma_20",  # Phase 61.1: sma_20 → close_ma_20（feature_order.json準拠）
            "bb_position",
            "rsi_14",
            "adx_14",
            "atr_14",
        ]

    def _calculate_sma_deviation(self, df: pd.DataFrame) -> float:
        """
        SMA乖離率計算

        乖離率 = (price - close_ma_20) / close_ma_20

        Args:
            df: 市場データ

        Returns:
            SMA乖離率（正: 上方乖離、負: 下方乖離）
        """
        try:
            latest = df.iloc[-1]
            price = float(latest["close"])
            # Phase 61.1: sma_20 → close_ma_20（feature_order.json準拠）
            close_ma_20 = float(latest["close_ma_20"])
            deviation = (price - close_ma_20) / close_ma_20
            return deviation
        except Exception as e:
            self.logger.error(f"SMA乖離率計算エラー: {e}")
            return 0.0

    def _analyze_mean_reversion_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        MeanReversionシグナル分析（Phase 60.15: BBReversalパターン統一）

        全ての状況で統一された動的信頼度計算を実行:
        - BB位置・RSI・SMA乖離の中央からの偏り度に基づく
        - 0.5/50/0を中央として、乖離が大きいほど信頼度が高い

        Args:
            df: 市場データ

        Returns:
            判定結果辞書（action, confidence, strength, reason）
        """
        try:
            latest = df.iloc[-1]
            bb_position = float(latest["bb_position"])
            rsi = float(latest["rsi_14"])
            sma_deviation = self._calculate_sma_deviation(df)
            threshold = self.config["sma_deviation_threshold"]

            # === Phase 60.15: 統一動的信頼度計算 ===

            # 設定から重みを取得
            bb_weight = self.config.get("bb_weight", 0.3)
            rsi_weight = self.config.get("rsi_weight", 0.3)
            sma_weight = self.config.get("sma_weight", 0.4)
            min_confidence = self.config.get("min_confidence", 0.15)
            max_confidence = self.config.get("max_confidence", 0.55)
            signal_threshold = self.config.get("signal_threshold", 0.4)

            # BB位置の偏り度合い（0-1スケールに正規化）
            bb_deviation = abs(bb_position - 0.5) * 2  # 0 ~ 1

            # RSIの偏り度合い（0-1スケールに正規化）
            rsi_deviation = abs(rsi - 50) / 50  # 0 ~ 1

            # SMA乖離の偏り度合い（閾値に対する比率、上限1.0）
            sma_dev_normalized = min(abs(sma_deviation) / threshold, 1.0)  # 0 ~ 1

            # 総合偏り度合い（重み付け平均）
            total_deviation = (
                bb_deviation * bb_weight
                + rsi_deviation * rsi_weight
                + sma_dev_normalized * sma_weight
            )

            # 動的信頼度計算（偏りが大きいほど高い）
            confidence_range = max_confidence - min_confidence
            dynamic_confidence = min_confidence + total_deviation * confidence_range

            # === 方向判定 ===

            # SELL方向の強さ（正の値）
            sell_strength = 0.0
            if bb_position > 0.5:
                sell_strength += (bb_position - 0.5) * 2  # 0 ~ 1
            if rsi > 50:
                sell_strength += (rsi - 50) / 50  # 0 ~ 1
            if sma_deviation > 0:
                sell_strength += min(sma_deviation / threshold, 1.0)  # 0 ~ 1

            # BUY方向の強さ（正の値）
            buy_strength = 0.0
            if bb_position < 0.5:
                buy_strength += (0.5 - bb_position) * 2  # 0 ~ 1
            if rsi < 50:
                buy_strength += (50 - rsi) / 50  # 0 ~ 1
            if sma_deviation < 0:
                buy_strength += min(abs(sma_deviation) / threshold, 1.0)  # 0 ~ 1

            # === シグナル決定 ===

            if sell_strength > buy_strength and sell_strength >= signal_threshold:
                return {
                    "action": EntryAction.SELL,
                    "confidence": dynamic_confidence,
                    "strength": sell_strength,
                    "reason": f"MeanReversion SELL (BB={bb_position:.2f}, RSI={rsi:.1f}, "
                    f"SMA乖離={sma_deviation*100:.2f}%, 強度={sell_strength:.2f})",
                    "analysis": f"過買い圏→平均回帰期待 (信頼度={dynamic_confidence:.3f})",
                }
            elif buy_strength > sell_strength and buy_strength >= signal_threshold:
                return {
                    "action": EntryAction.BUY,
                    "confidence": dynamic_confidence,
                    "strength": buy_strength,
                    "reason": f"MeanReversion BUY (BB={bb_position:.2f}, RSI={rsi:.1f}, "
                    f"SMA乖離={sma_deviation*100:.2f}%, 強度={buy_strength:.2f})",
                    "analysis": f"過売り圏→平均回帰期待 (信頼度={dynamic_confidence:.3f})",
                }
            else:
                # HOLDでも動的信頼度を使用（フォールバック値不使用）
                return {
                    "action": EntryAction.HOLD,
                    "confidence": dynamic_confidence,
                    "strength": max(sell_strength, buy_strength),
                    "reason": f"MeanReversion中立 (BB={bb_position:.2f}, RSI={rsi:.1f}, "
                    f"SMA乖離={sma_deviation*100:.2f}%, 強度={max(sell_strength, buy_strength):.2f})",
                    "analysis": f"方向性不明確 (信頼度={dynamic_confidence:.3f})",
                }

        except Exception as e:
            self.logger.error(f"MeanReversionシグナル分析エラー: {e}")
            return {
                "action": EntryAction.HOLD,
                "confidence": 0.0,
                "strength": 0.0,
                "reason": f"分析エラー: {e}",
            }

    def _create_hold_signal(self, reason: str, df: pd.DataFrame) -> StrategySignal:
        """
        ホールドシグナル生成

        Args:
            reason: ホールド理由
            df: 市場データ

        Returns:
            ホールドStrategySignal
        """
        try:
            current_price = float(df.iloc[-1]["close"]) if not df.empty else 0.0
        except Exception:
            current_price = 0.0

        return SignalBuilder.create_hold_signal(
            strategy_name=self.name,
            current_price=current_price,
            reason=reason,
            strategy_type=StrategyType.MEAN_REVERSION,
        )

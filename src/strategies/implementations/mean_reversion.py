"""
MeanReversion戦略実装 - Phase 61

移動平均乖離反転戦略:
- 価格がSMA20から±2%以上乖離 → 反転エントリー
- BB位置の極端値（<0.1または>0.9）でも発火
- RSI過買い/過売りでも発火

特徴:
- OR条件で発火率向上（良好戦略パターン踏襲）
- 極端値のみ判定（ノイズ回避）
- レンジ相場特化（ADX < 25）
- シンプルな信頼度計算

Phase 61: 新規戦略として追加（ADX/MACD/Donchianの代替）
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
        # Phase 60.5: 閾値緩和で発火率向上（HOLD率93.6%→目標60%）
        default_config = {
            "min_confidence": get_threshold("strategies.mean_reversion.min_confidence", 0.30),
            "hold_confidence": get_threshold("strategies.mean_reversion.hold_confidence", 0.15),
            # Phase 60.5: SMA乖離閾値緩和（0.02→0.015）
            "sma_deviation_threshold": get_threshold(
                "strategies.mean_reversion.sma_deviation_threshold", 0.015
            ),
            # Phase 60.5: RSI閾値緩和（70/30→65/35）
            "rsi_overbought": get_threshold("strategies.mean_reversion.rsi_overbought", 65),
            "rsi_oversold": get_threshold("strategies.mean_reversion.rsi_oversold", 35),
            # Phase 60.5: BB閾値緩和（0.9/0.1→0.85/0.15）
            "bb_upper_threshold": get_threshold("strategies.mean_reversion.bb_upper_threshold", 0.85),
            "bb_lower_threshold": get_threshold("strategies.mean_reversion.bb_lower_threshold", 0.15),
            # Phase 60.5: レンジ相場判定拡大（25→30）
            "adx_range_threshold": get_threshold(
                "strategies.mean_reversion.adx_range_threshold", 30
            ),
            # SL設定
            "sl_multiplier": get_threshold("strategies.mean_reversion.sl_multiplier", 1.5),
            # Phase 52.4-B: TP/SL設定（thresholds.yaml優先）
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
            f"RSI閾値=({self.config['rsi_oversold']}, {self.config['rsi_overbought']})"
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
        MeanReversionシグナル分析（OR条件）

        シグナル生成ロジック:
        BUY（OR条件）:
          - RSI < 30
          - bb_position < 0.1
          - price < SMA20 * 0.98（乖離-2%以下）

        SELL（OR条件）:
          - RSI > 70
          - bb_position > 0.9
          - price > SMA20 * 1.02（乖離+2%以上）

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

            # BUY条件（OR条件）
            rsi_buy = rsi < self.config["rsi_oversold"]
            bb_buy = bb_position < self.config["bb_lower_threshold"]
            sma_buy = sma_deviation < -threshold  # 下方乖離

            buy_conditions = [rsi_buy, bb_buy, sma_buy]
            buy_count = sum(buy_conditions)

            if buy_count > 0:
                # 信頼度: 条件数に応じて増加
                base_confidence = 0.30
                confidence = min(base_confidence + (buy_count - 1) * 0.10, 0.55)

                # 強度: 乖離度合いに基づく
                strength = min(abs(sma_deviation) / threshold, 1.0) * 0.8

                # 発火条件の記録
                conditions_met = []
                if rsi_buy:
                    conditions_met.append(f"RSI={rsi:.1f}")
                if bb_buy:
                    conditions_met.append(f"BB={bb_position:.2f}")
                if sma_buy:
                    conditions_met.append(f"SMA乖離={sma_deviation*100:.2f}%")

                return {
                    "action": EntryAction.BUY,
                    "confidence": confidence,
                    "strength": strength,
                    "reason": f"MeanReversion BUY ({', '.join(conditions_met)})",
                    "analysis": f"平均回帰シグナル: {buy_count}条件成立→反転上昇期待",
                }

            # SELL条件（OR条件）
            rsi_sell = rsi > self.config["rsi_overbought"]
            bb_sell = bb_position > self.config["bb_upper_threshold"]
            sma_sell = sma_deviation > threshold  # 上方乖離

            sell_conditions = [rsi_sell, bb_sell, sma_sell]
            sell_count = sum(sell_conditions)

            if sell_count > 0:
                # 信頼度: 条件数に応じて増加
                base_confidence = 0.30
                confidence = min(base_confidence + (sell_count - 1) * 0.10, 0.55)

                # 強度: 乖離度合いに基づく
                strength = min(abs(sma_deviation) / threshold, 1.0) * 0.8

                # 発火条件の記録
                conditions_met = []
                if rsi_sell:
                    conditions_met.append(f"RSI={rsi:.1f}")
                if bb_sell:
                    conditions_met.append(f"BB={bb_position:.2f}")
                if sma_sell:
                    conditions_met.append(f"SMA乖離=+{sma_deviation*100:.2f}%")

                return {
                    "action": EntryAction.SELL,
                    "confidence": confidence,
                    "strength": strength,
                    "reason": f"MeanReversion SELL ({', '.join(conditions_met)})",
                    "analysis": f"平均回帰シグナル: {sell_count}条件成立→反転下落期待",
                }

            # HOLD信号
            return {
                "action": EntryAction.HOLD,
                "confidence": self.config["hold_confidence"],
                "strength": 0.0,
                "reason": f"MeanReversion条件未達成 (RSI={rsi:.1f}, BB={bb_position:.2f}, SMA乖離={sma_deviation*100:.2f}%)",
                "analysis": "極端値未到達→エントリー見送り",
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

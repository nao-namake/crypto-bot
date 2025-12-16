"""
Donchian Channel戦略実装 - ブレイクアウト検出

レンジ相場対応ブレイクアウト戦略。
20期間チャネルを用いた反転・ブレイクアウト判定を行う。

主要機能:
- 20期間高値・安値チャネル計算
- ブレイクアウト・リバーサル検出
- レンジ相場適応（70-80%市場対応）
- チャネル位置による強度判定

Phase 49完了: 市場不確実性計算統合・バックテストログ統合
"""

from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

from ...core.config import get_threshold
from ...core.logger import get_logger
from ..base.strategy_base import StrategyBase, StrategySignal
from ..strategy_registry import StrategyRegistry
from ..utils import MarketUncertaintyCalculator
from ..utils.strategy_utils import SignalBuilder, StrategyType


@StrategyRegistry.register(name="DonchianChannel", strategy_type=StrategyType.DONCHIAN_CHANNEL)
class DonchianChannelStrategy(StrategyBase):
    """
    Donchian Channel戦略クラス
    20期間の高値・安値チャネルを用いてブレイクアウトと
    リバーサルシグナルを検出する。
    レンジ相場に最適化された設計。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Donchian Channel戦略の初期化
        Args:
            config: 戦略設定辞書
        """
        super().__init__("DonchianChannel")
        self.config = config or {}
        self.logger = get_logger()
        # 戦略パラメータ（動的信頼度計算対応）
        self.channel_period = self.config.get("channel_period", 20)
        self.breakout_threshold = get_threshold(
            "strategies.donchian_channel.breakout_threshold", 0.002
        )  # 0.2%
        self.reversal_threshold = get_threshold(
            "strategies.donchian_channel.reversal_threshold", 0.05
        )  # 5%位置
        self.min_confidence = get_threshold(
            "strategies.donchian_channel.min_confidence", 0.3
        )  # 緩和設定
        # 中央域・弱シグナル設定（動的計算用）
        self.middle_zone_min = get_threshold("strategies.donchian_channel.middle_zone_min", 0.4)
        self.middle_zone_max = get_threshold("strategies.donchian_channel.middle_zone_max", 0.6)
        self.weak_signal_confidence = get_threshold(
            "strategies.donchian_channel.weak_signal_confidence", 0.35
        )
        self.logger.info(f"Donchian Channel戦略初期化完了 - 期間: {self.channel_period}")

    def get_required_features(self) -> list[str]:
        """必要特徴量リスト取得"""
        return [
            "close",
            "high",
            "low",
            "volume",
            "donchian_high_20",
            "donchian_low_20",
            "channel_position",
            "atr_14",
            "volume_ratio",
        ]

    def analyze(
        self, df: pd.DataFrame, multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> StrategySignal:
        """
        Donchian Channelシグナル生成（抽象メソッド実装）
        Args:
            df: 市場データ（特徴量含む）
        Returns:
            戦略シグナル
        """
        try:
            self.logger.debug(f"[DonchianChannel] シグナル生成開始 - データ: {len(df)}行")
            # データ検証
            if not self._validate_data(df):
                return self._create_hold_signal(df, "データ不足")
            # チャネル分析
            channel_analysis = self._analyze_donchian_channel(df)
            if not channel_analysis:
                return self._create_hold_signal(df, "チャネル分析失敗")
            # シグナル判定（Phase 32: multi_timeframe_data渡す）
            signal = self._determine_signal(df, channel_analysis, multi_timeframe_data)
            self.logger.debug(
                f"[DonchianChannel] シグナル生成完了: {signal.action} "
                f"(信頼度: {signal.confidence:.3f})"
            )
            return signal
        except Exception as e:
            # Phase 38.4: バックテストログ統合
            self.logger.conditional_log(
                f"[DonchianChannel] シグナル生成エラー: {e}",
                level="error",
                backtest_level="debug",
            )
            return self._create_hold_signal(df, f"エラー: {str(e)}")

    def _validate_data(self, df: pd.DataFrame) -> bool:
        """データ検証"""
        required_features = self.get_required_features()
        # 必要列の存在確認
        missing_cols = [col for col in required_features if col not in df.columns]
        if missing_cols:
            self.logger.warning(f"[DonchianChannel] 不足特徴量: {missing_cols}")
            return False
        # データ長確認
        if len(df) < self.channel_period:
            self.logger.warning(f"[DonchianChannel] データ不足: {len(df)} < {self.channel_period}")
            return False
        # NaN確認（最新データ）
        latest = df.iloc[-1]
        required_non_nan = ["close", "donchian_high_20", "donchian_low_20", "channel_position"]
        if latest[required_non_nan].isna().any():
            self.logger.warning("[DonchianChannel] 最新データにNaN値")
            return False
        return True

    def _analyze_donchian_channel(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Donchian Channelチャネル分析
        Returns:
            チャネル分析結果辞書
        """
        try:
            latest = df.iloc[-1]
            current_price = float(latest["close"])
            # チャネル値取得
            donchian_high = float(latest["donchian_high_20"])
            donchian_low = float(latest["donchian_low_20"])
            channel_position = float(latest["channel_position"])
            # チャネル幅計算
            channel_width = donchian_high - donchian_low
            channel_mid = (donchian_high + donchian_low) / 2
            # 価格位置分析
            price_to_high = (
                (donchian_high - current_price) / channel_width if channel_width > 0 else 0
            )
            price_to_low = (
                (current_price - donchian_low) / channel_width if channel_width > 0 else 0
            )
            # ブレイクアウト検出
            is_upper_breakout = current_price > donchian_high * (1 + self.breakout_threshold)
            is_lower_breakout = current_price < donchian_low * (1 - self.breakout_threshold)
            # チャネル位置による判定（動的範囲対応）
            in_upper_zone = channel_position > (1 - self.reversal_threshold)  # 上部5%
            in_lower_zone = channel_position < self.reversal_threshold  # 下部5%
            in_middle_zone = self.middle_zone_min <= channel_position <= self.middle_zone_max
            # 弱シグナル範囲（中央域外の準備信号）
            in_weak_buy_zone = 0.25 <= channel_position < self.middle_zone_min
            in_weak_sell_zone = self.middle_zone_max < channel_position <= 0.75
            # analysis辞書の初期化と追加
            analysis = {}
            analysis["in_weak_buy_zone"] = in_weak_buy_zone
            analysis["in_weak_sell_zone"] = in_weak_sell_zone
            # ボラティリティ分析（ATR使用）
            atr = (
                float(latest["atr_14"])
                if "atr_14" in latest and not pd.isna(latest["atr_14"])
                else 0
            )
            volatility_ratio = atr / current_price if current_price > 0 else 0
            # 出来高分析
            volume_ratio = float(latest["volume_ratio"]) if "volume_ratio" in latest else 1.0
            analysis = {
                "current_price": current_price,
                "donchian_high": donchian_high,
                "donchian_low": donchian_low,
                "channel_position": channel_position,
                "channel_width": channel_width,
                "channel_mid": channel_mid,
                "price_to_high": price_to_high,
                "price_to_low": price_to_low,
                "is_upper_breakout": is_upper_breakout,
                "is_lower_breakout": is_lower_breakout,
                "in_upper_zone": in_upper_zone,
                "in_lower_zone": in_lower_zone,
                "in_middle_zone": in_middle_zone,
                "in_weak_buy_zone": in_weak_buy_zone,
                "in_weak_sell_zone": in_weak_sell_zone,
                "volatility_ratio": volatility_ratio,
                "volume_ratio": volume_ratio,
            }
            self.logger.debug(
                f"[DonchianChannel] チャネル分析: 位置={channel_position:.3f}, "
                f"幅={channel_width:.0f}, 上部BRK={is_upper_breakout}, 下部BRK={is_lower_breakout}"
            )
            return analysis
        except Exception as e:
            self.logger.error(f"[DonchianChannel] チャネル分析エラー: {e}")
            return None

    def _determine_signal(
        self,
        df: pd.DataFrame,
        analysis: Dict[str, Any],
        multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> StrategySignal:
        """
        シグナル判定ロジック（動的信頼度計算・中央域対応）

        Phase 32: multi_timeframe_data対応

        Args:
            df: 市場データ
            analysis: チャネル分析結果
            multi_timeframe_data: マルチタイムフレームデータ（Phase 32）

        Returns:
            最終シグナル
        """
        channel_pos = analysis["channel_position"]
        volume_ratio = analysis["volume_ratio"]
        current_price = analysis["current_price"]

        # 1. ブレイクアウトシグナル（強いトレンド）
        if analysis["is_upper_breakout"] and volume_ratio > 1.2:
            return self._create_signal(
                action="buy",
                confidence=0.75,
                reason="上方ブレイクアウト（出来高増加）",
                current_price=current_price,
                df=df,
                analysis=analysis,
                multi_timeframe_data=multi_timeframe_data,
            )
        if analysis["is_lower_breakout"] and volume_ratio > 1.2:
            return self._create_signal(
                action="sell",
                confidence=0.75,
                reason="下方ブレイクアウト（出来高増加）",
                current_price=current_price,
                df=df,
                analysis=analysis,
                multi_timeframe_data=multi_timeframe_data,
            )
        # 2. リバーサルシグナル（レンジ相場対応）
        if analysis["in_lower_zone"] and not analysis["is_lower_breakout"]:
            confidence = self._calculate_reversal_confidence(analysis, "buy")
            if confidence >= self.min_confidence:
                return self._create_signal(
                    action="buy",
                    confidence=confidence,
                    reason=f"下限リバーサル（位置: {channel_pos:.3f}）",
                    current_price=current_price,
                    df=df,
                    analysis=analysis,
                    multi_timeframe_data=multi_timeframe_data,
                )
        if analysis["in_upper_zone"] and not analysis["is_upper_breakout"]:
            confidence = self._calculate_reversal_confidence(analysis, "sell")
            if confidence >= self.min_confidence:
                return self._create_signal(
                    action="sell",
                    confidence=confidence,
                    reason=f"上限リバーサル（位置: {channel_pos:.3f}）",
                    current_price=current_price,
                    df=df,
                    analysis=analysis,
                    multi_timeframe_data=multi_timeframe_data,
                )
        # 3. 弱シグナル（中央域手前）- 動的信頼度計算
        # Phase 54.2: 弱シグナル無効化設定の確認
        weak_signal_enabled = get_threshold("strategies.donchian_channel.weak_signal_enabled", True)
        if weak_signal_enabled:
            if analysis["in_weak_buy_zone"]:
                # 下方向への動きを示唆する弱いbuyシグナル
                confidence = self._calculate_weak_signal_confidence(analysis, "buy")
                if confidence >= self.min_confidence:
                    return self._create_signal(
                        action="buy",
                        confidence=confidence,
                        reason=f"弱買いシグナル（位置: {channel_pos:.3f}）",
                        current_price=current_price,
                        df=df,
                        analysis=analysis,
                        multi_timeframe_data=multi_timeframe_data,
                    )
            if analysis["in_weak_sell_zone"]:
                # 上方向への動きを示唆する弱いsellシグナル
                confidence = self._calculate_weak_signal_confidence(analysis, "sell")
                if confidence >= self.min_confidence:
                    return self._create_signal(
                        action="sell",
                        confidence=confidence,
                        reason=f"弱売りシグナル（位置: {channel_pos:.3f}）",
                        current_price=current_price,
                        df=df,
                        analysis=analysis,
                        multi_timeframe_data=multi_timeframe_data,
                    )
        # 4. 中央域 - 動的HOLD信頼度計算（フォールバック回避・市場データ統合）
        if analysis["in_middle_zone"]:
            # 完全な中央域でもモメンタムに基づく微弱な方向性を計算
            dynamic_confidence = self._calculate_middle_zone_confidence(analysis, df)
            return self._create_hold_signal(
                df,
                f"中央域動的判定（位置: {channel_pos:.3f}, 信頼度: {dynamic_confidence:.3f}）",
                dynamic_confidence,
            )
        # 5. その他のケース - 動的HOLD（市場データ統合）
        dynamic_confidence = self._calculate_default_confidence(analysis, df)
        return self._create_hold_signal(
            df,
            f"動的HOLD（位置: {channel_pos:.3f}, 信頼度: {dynamic_confidence:.3f}）",
            dynamic_confidence,
        )

    def _calculate_reversal_confidence(self, analysis: Dict[str, Any], direction: str) -> float:
        """
        リバーサル信頼度計算
        Args:
            analysis: チャネル分析結果
            direction: "buy" または "sell"
        Returns:
            信頼度 (0.0-1.0)
        """
        base_confidence = self.min_confidence
        # チャネル位置による調整
        if direction == "buy":
            # 下限に近いほど信頼度上昇
            position_bonus = (1 - analysis["channel_position"]) * 0.3
        else:
            # 上限に近いほど信頼度上昇
            position_bonus = analysis["channel_position"] * 0.3
        # ボラティリティによる調整
        volatility_bonus = 0.0
        if 0.01 <= analysis["volatility_ratio"] <= 0.03:  # 適度なボラティリティ
            volatility_bonus = 0.1
        # 出来高による調整
        volume_bonus = 0.0
        if analysis["volume_ratio"] > 1.0:  # 平均以上の出来高
            volume_bonus = min(0.1, (analysis["volume_ratio"] - 1.0) * 0.2)
        confidence = base_confidence + position_bonus + volatility_bonus + volume_bonus
        # 0.2-0.9の範囲にクランプ
        return max(0.2, min(0.9, confidence))

    def _calculate_weak_signal_confidence(self, analysis: Dict[str, Any], direction: str) -> float:
        """
        弱シグナル信頼度計算（中央域手前）
        Args:
            analysis: チャネル分析結果
            direction: "buy" または "sell"
        Returns:
            信頼度 (0.0-1.0)
        """
        base_confidence = self.weak_signal_confidence
        # チャネル位置による調整
        channel_pos = analysis["channel_position"]
        if direction == "buy":
            # 下方向に近いほど信頼度上昇（0.25-0.4の範囲）
            position_factor = (self.middle_zone_min - channel_pos) / (self.middle_zone_min - 0.25)
        else:
            # 上方向に近いほど信頼度上昇（0.6-0.75の範囲）
            position_factor = (channel_pos - self.middle_zone_max) / (0.75 - self.middle_zone_max)
        position_bonus = position_factor * 0.2
        # ボラティリティ・出来高による調整
        volatility_bonus = 0.0
        if 0.01 <= analysis["volatility_ratio"] <= 0.03:
            volatility_bonus = 0.1
        volume_bonus = 0.0
        if analysis["volume_ratio"] > 1.0:
            volume_bonus = min(0.1, (analysis["volume_ratio"] - 1.0) * 0.2)
        confidence = base_confidence + position_bonus + volatility_bonus + volume_bonus
        return max(0.25, min(0.6, confidence))

    def _calculate_middle_zone_confidence(
        self, analysis: Dict[str, Any], df: pd.DataFrame = None
    ) -> float:
        """
        中央域動的信頼度計算（市場データ統合版）
        Args:
            analysis: チャネル分析結果
            df: 市場データ（市場不確実性計算用）
        Returns:
            動的信頼度 (0.2-0.4)
        """
        # 循環インポート回避のため遅延インポート
        from ...core.config.threshold_manager import get_threshold

        # 基本信頼度
        base_confidence = get_threshold("strategies.donchian_channel.hold_confidence", 0.25)
        # 市場データ基づく動的信頼度調整システム
        market_uncertainty = self._calculate_market_uncertainty(df) if df is not None else 0.02

        # チャネル位置による微調整（完全中央=0.5から離れるほど信頼度上昇）
        channel_pos = analysis["channel_position"]
        center_deviation = abs(channel_pos - 0.5)
        deviation_bonus = center_deviation * 0.2

        # 基本信頼度と位置補正を市場不確実性で動的調整（固定値回避）
        raw_confidence = (base_confidence + deviation_bonus) * (1 + market_uncertainty)

        # 循環インポート回避のため遅延インポート
        from ...core.config.threshold_manager import get_threshold

        hold_min = get_threshold("dynamic_confidence.strategies.donchian_channel.hold_min", 0.20)
        hold_max = get_threshold("dynamic_confidence.strategies.donchian_channel.hold_max", 0.45)
        confidence = max(hold_min, min(hold_max, raw_confidence))

        return confidence

    def _calculate_market_uncertainty(self, df: pd.DataFrame) -> float:
        """
        市場データ基づく不確実性計算（Phase 38.4: 統合ユーティリティ使用）

        Args:
            df: 市場データ

        Returns:
            float: 市場不確実性係数（0-0.1の範囲）
        """
        return MarketUncertaintyCalculator.calculate(df)

    def _calculate_default_confidence(
        self, analysis: Dict[str, Any], df: pd.DataFrame = None
    ) -> float:
        """
        デフォルト動的信頼度計算（その他のケース・市場データ統合版）
        Args:
            analysis: チャネル分析結果
            df: 市場データ（市場不確実性計算用）
        Returns:
            動的信頼度 (0.15-0.35)
        """
        # 循環インポート回避のため遅延インポート
        from ...core.config.threshold_manager import get_threshold

        # 基本信頼度
        base_confidence = get_threshold("strategies.donchian_channel.hold_confidence", 0.25)
        # 市場データ基づく動的信頼度調整システム（強化版）
        market_uncertainty = self._calculate_market_uncertainty(df) if df is not None else 0.02

        # チャネル幅による調整（幅が大きいほど不確実性増加）
        width_adjustment = 0.0
        if analysis["channel_width"] > 0:
            width_factor = min(1.0, analysis["channel_width"] / (analysis["current_price"] * 0.1))
            width_adjustment = width_factor * 0.05

        # ボラティリティと出来高による追加動的調整
        volatility_adjustment = analysis.get("volatility_ratio", 0.02) * 2.0
        volume_adjustment = abs(analysis.get("volume_ratio", 1.0) - 1.0) * 0.1

        # 総合動的調整（固定値回避・確実な変動確保）
        total_adjustment = market_uncertainty + volatility_adjustment + volume_adjustment
        raw_confidence = base_confidence * (1 + total_adjustment) - width_adjustment

        # 循環インポート回避のため遅延インポート
        from ...core.config.threshold_manager import get_threshold

        hold_min = get_threshold("dynamic_confidence.strategies.donchian_channel.hold_min", 0.20)
        hold_max = get_threshold("dynamic_confidence.strategies.donchian_channel.hold_max", 0.45)
        confidence = max(hold_min, min(hold_max, raw_confidence))

        return confidence

    def _create_hold_signal(
        self, df: pd.DataFrame, reason: str, dynamic_confidence: float = None
    ) -> StrategySignal:
        """HOLDシグナル生成（動的信頼度対応）"""
        current_price = float(df["close"].iloc[-1]) if "close" in df.columns else 0.0
        # 動的信頼度優先、なければ設定値使用
        if dynamic_confidence is not None:
            confidence = dynamic_confidence
        else:
            confidence = get_threshold("strategies.donchian_channel.hold_confidence", 0.25)
        return StrategySignal(
            strategy_name=self.name,
            timestamp=datetime.now(),
            action="hold",
            confidence=confidence,
            strength=confidence * 0.5,  # 強度は信頼度の50%
            current_price=current_price,
            reason=f"Donchian動的: {reason}",
            metadata={
                "signal_type": "donchian_dynamic_hold",
                "is_dynamic": dynamic_confidence is not None,
                "confidence_source": "dynamic" if dynamic_confidence is not None else "config",
            },
        )

    def _create_signal(
        self,
        action: str,
        confidence: float,
        reason: str,
        current_price: float,
        df: pd.DataFrame,
        analysis: Dict[str, Any],
        multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> StrategySignal:
        """
        Phase 32: SignalBuilder統合 - 15m足ATR使用

        Args:
            action: シグナルアクション（buy/sell）
            confidence: 信頼度
            reason: シグナル理由
            current_price: 現在価格
            df: 市場データ（4h足）
            analysis: チャネル分析結果
            multi_timeframe_data: マルチタイムフレームデータ

        Returns:
            StrategySignal
        """
        # 決定辞書作成
        decision = {
            "action": action,
            "confidence": confidence,
            "strength": confidence,  # DonchianChannelでは信頼度=強度
            "reason": reason,
            "metadata": {
                "channel_position": analysis["channel_position"],
                "channel_width": analysis["channel_width"],
                "volume_ratio": analysis["volume_ratio"],
                "signal_type": (
                    "donchian_breakout" if "ブレイクアウト" in reason else "donchian_reversal"
                ),
            },
        }

        # Phase 32: SignalBuilder使用（15m足ATR優先取得）
        return SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.name,
            decision=decision,
            current_price=current_price,
            df=df,
            config=self.config,
            strategy_type=StrategyType.DONCHIAN_CHANNEL,
            multi_timeframe_data=multi_timeframe_data,
        )

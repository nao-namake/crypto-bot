"""
Donchian Channel戦略実装 - ブレイクアウト検出
レンジ相場対応ブレイクアウト戦略。
20期間チャネルを用いた反転・ブレイクアウト判定を行う。
主要機能:
- 20期間高値・安値チャネル計算
- ブレイクアウト・リバーサル検出
- レンジ相場適応（70-80%市場対応）
- チャネル位置による強度判定
実装日: 2025年9月9日 - フィボナッチ戦略置換
"""

from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

from ...core.config import get_threshold
from ...core.logger import get_logger
from ..base.strategy_base import StrategyBase, StrategySignal


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

    def analyze(self, df: pd.DataFrame) -> StrategySignal:
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
            # シグナル判定
            signal = self._determine_signal(df, channel_analysis)
            self.logger.debug(
                f"[DonchianChannel] シグナル生成完了: {signal.action} "
                f"(信頼度: {signal.confidence:.3f})"
            )
            return signal
        except Exception as e:
            self.logger.error(f"[DonchianChannel] シグナル生成エラー: {e}")
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

    def _determine_signal(self, df: pd.DataFrame, analysis: Dict[str, Any]) -> StrategySignal:
        """
        シグナル判定ロジック（動的信頼度計算・中央域対応）
        Args:
            df: 市場データ
            analysis: チャネル分析結果
        Returns:
            最終シグナル
        """
        channel_pos = analysis["channel_position"]
        volume_ratio = analysis["volume_ratio"]
        # 1. ブレイクアウトシグナル（強いトレンド）
        if analysis["is_upper_breakout"] and volume_ratio > 1.2:
            return self._create_buy_signal(
                df, analysis, confidence=0.75, reason="上方ブレイクアウト（出来高増加）"
            )
        if analysis["is_lower_breakout"] and volume_ratio > 1.2:
            return self._create_sell_signal(
                df, analysis, confidence=0.75, reason="下方ブレイクアウト（出来高増加）"
            )
        # 2. リバーサルシグナル（レンジ相場対応）
        if analysis["in_lower_zone"] and not analysis["is_lower_breakout"]:
            confidence = self._calculate_reversal_confidence(analysis, "buy")
            if confidence >= self.min_confidence:
                return self._create_buy_signal(
                    df,
                    analysis,
                    confidence=confidence,
                    reason=f"下限リバーサル（位置: {channel_pos:.3f}）",
                )
        if analysis["in_upper_zone"] and not analysis["is_upper_breakout"]:
            confidence = self._calculate_reversal_confidence(analysis, "sell")
            if confidence >= self.min_confidence:
                return self._create_sell_signal(
                    df,
                    analysis,
                    confidence=confidence,
                    reason=f"上限リバーサル（位置: {channel_pos:.3f}）",
                )
        # 3. 弱シグナル（中央域手前）- 動的信頼度計算
        if analysis["in_weak_buy_zone"]:
            # 下方向への動きを示唆する弱いbuyシグナル
            confidence = self._calculate_weak_signal_confidence(analysis, "buy")
            if confidence >= self.min_confidence:
                return self._create_buy_signal(
                    df,
                    analysis,
                    confidence=confidence,
                    reason=f"弱買いシグナル（位置: {channel_pos:.3f}）",
                )
        if analysis["in_weak_sell_zone"]:
            # 上方向への動きを示唆する弱いsellシグナル
            confidence = self._calculate_weak_signal_confidence(analysis, "sell")
            if confidence >= self.min_confidence:
                return self._create_sell_signal(
                    df,
                    analysis,
                    confidence=confidence,
                    reason=f"弱売りシグナル（位置: {channel_pos:.3f}）",
                )
        # 4. 中央域 - 動的HOLD信頼度計算（フォールバック回避）
        if analysis["in_middle_zone"]:
            # 完全な中央域でもモメンタムに基づく微弱な方向性を計算
            dynamic_confidence = self._calculate_middle_zone_confidence(analysis)
            return self._create_hold_signal(
                df,
                f"中央域動的判定（位置: {channel_pos:.3f}, 信頼度: {dynamic_confidence:.3f}）",
                dynamic_confidence,
            )
        # 5. その他のケース - 動的HOLD
        dynamic_confidence = self._calculate_default_confidence(analysis)
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

    def _calculate_middle_zone_confidence(self, analysis: Dict[str, Any]) -> float:
        """
        中央域動的信頼度計算
        Args:
            analysis: チャネル分析結果
        Returns:
            動的信頼度 (0.2-0.4)
        """
        # 基本信頼度
        base_confidence = get_threshold("strategies.donchian_channel.hold_confidence", 0.25)
        # チャネル位置による微調整（完全中央=0.5から離れるほど信頼度上昇）
        channel_pos = analysis["channel_position"]
        center_deviation = abs(channel_pos - 0.5)
        deviation_bonus = center_deviation * 0.2
        # ボラティリティによる調整
        volatility_bonus = 0.0
        if analysis["volatility_ratio"] > 0.015:  # 1.5%以上のボラティリティ
            volatility_bonus = min(0.05, (analysis["volatility_ratio"] - 0.015) * 10)
        # 出来高による微調整
        volume_bonus = 0.0
        if analysis["volume_ratio"] != 1.0:  # 平均と異なる出来高
            volume_bonus = min(0.03, abs(analysis["volume_ratio"] - 1.0) * 0.05)
        confidence = base_confidence + deviation_bonus + volatility_bonus + volume_bonus
        return max(0.2, min(0.4, confidence))

    def _calculate_default_confidence(self, analysis: Dict[str, Any]) -> float:
        """
        デフォルト動的信頼度計算（その他のケース）
        Args:
            analysis: チャネル分析結果
        Returns:
            動的信頼度 (0.2-0.35)
        """
        # 基本信頼度
        base_confidence = get_threshold("strategies.donchian_channel.hold_confidence", 0.25)
        # チャネル幅による調整（幅が大きいほど不確実性増加）
        if analysis["channel_width"] > 0:
            width_factor = min(1.0, analysis["channel_width"] / (analysis["current_price"] * 0.1))
            width_penalty = width_factor * 0.05
            base_confidence -= width_penalty
        # 市場状況による微調整
        volatility_adjustment = analysis["volatility_ratio"] * 0.5
        volume_adjustment = abs(analysis["volume_ratio"] - 1.0) * 0.02
        confidence = base_confidence + volatility_adjustment + volume_adjustment
        return max(0.2, min(0.35, confidence))

    def _create_buy_signal(
        self, df: pd.DataFrame, analysis: Dict[str, Any], confidence: float, reason: str
    ) -> StrategySignal:
        """BUYシグナル生成"""
        current_price = analysis["current_price"]
        # リスク管理計算
        atr = analysis.get("volatility_ratio", 0.02) * current_price
        stop_loss = current_price - (atr * 2.0)  # 2ATR
        take_profit = current_price + (atr * 3.0)  # 3ATR (1:1.5リスクリワード)
        return StrategySignal(
            strategy_name=self.name,
            timestamp=datetime.now(),
            action="buy",
            confidence=confidence,
            strength=confidence,
            current_price=current_price,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_ratio=0.02,  # 2%リスク
            reason=reason,
            metadata={
                "channel_position": analysis["channel_position"],
                "channel_width": analysis["channel_width"],
                "volume_ratio": analysis["volume_ratio"],
                "signal_type": (
                    "donchian_breakout" if "ブレイクアウト" in reason else "donchian_reversal"
                ),
            },
        )

    def _create_sell_signal(
        self, df: pd.DataFrame, analysis: Dict[str, Any], confidence: float, reason: str
    ) -> StrategySignal:
        """SELLシグナル生成"""
        current_price = analysis["current_price"]
        # リスク管理計算
        atr = analysis.get("volatility_ratio", 0.02) * current_price
        stop_loss = current_price + (atr * 2.0)  # 2ATR
        take_profit = current_price - (atr * 3.0)  # 3ATR
        return StrategySignal(
            strategy_name=self.name,
            timestamp=datetime.now(),
            action="sell",
            confidence=confidence,
            strength=confidence,
            current_price=current_price,
            entry_price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_ratio=0.02,
            reason=reason,
            metadata={
                "channel_position": analysis["channel_position"],
                "channel_width": analysis["channel_width"],
                "volume_ratio": analysis["volume_ratio"],
                "signal_type": (
                    "donchian_breakout" if "ブレイクアウト" in reason else "donchian_reversal"
                ),
            },
        )

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

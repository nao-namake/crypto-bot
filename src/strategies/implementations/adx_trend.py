"""
ADX Trend Strength戦略実装 - 市場レジーム適応型取引

Average Directional Index (ADX) を用いたトレンド強度判定と
+DI/-DIクロスオーバーによる方向性検出を組み合わせた戦略。

主要機能:
- ADX値による市場レジーム判定（トレンド vs レンジ）
- +DI/-DIクロスオーバー検出
- トレンド強度適応型信頼度調整
- レンジ相場での取引抑制

Phase 49完了: 市場不確実性計算統合・バックテストログ統合

Phase 55.6: タイトレンジ逆張りモード追加
- tight_range（90%の市場）でDI急変を逆張りシグナルとして使用
- ADX低下＋DI急変 → 反転予測
- 他戦略（ATR, BB, Stochastic）と異なるDI強度指標を使用
"""

from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

from ...core.logger import get_logger
from ..base.strategy_base import StrategyBase, StrategySignal
from ..strategy_registry import StrategyRegistry
from ..utils import MarketUncertaintyCalculator
from ..utils.strategy_utils import SignalBuilder, StrategyType


@StrategyRegistry.register(name="ADXTrendStrength", strategy_type=StrategyType.ADX_TREND)
class ADXTrendStrengthStrategy(StrategyBase):
    """
    ADX Trend Strength戦略クラス
    ADX指標によるトレンド強度判定と+DI/-DIによる方向性検出を
    組み合わせた市場レジーム適応型戦略。
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        ADX戦略の初期化
        Args:
            config: 戦略設定辞書
        """
        super().__init__("ADXTrendStrength")
        self.config = config or {}
        self.logger = get_logger()

        # 循環インポート回避のため遅延インポート
        from ...core.config.threshold_manager import get_threshold

        # 戦略パラメータ（動的信頼度計算対応）
        self.adx_period = self.config.get("adx_period", 14)
        self.strong_trend_threshold = get_threshold(
            "strategies.adx_trend.strong_trend_threshold", 25
        )
        self.weak_trend_threshold = get_threshold("strategies.adx_trend.weak_trend_threshold", 15)
        self.di_crossover_threshold = get_threshold(
            "strategies.adx_trend.di_crossover_threshold", 0.5
        )
        self.min_confidence = get_threshold("strategies.adx_trend.min_confidence", 0.3)
        # 弱シグナル用設定
        self.weak_di_threshold = get_threshold("strategies.adx_trend.weak_di_threshold", 1.0)
        self.di_weak_signal_confidence = get_threshold(
            "strategies.adx_trend.di_weak_signal_confidence", 0.35
        )

        # Phase 55.6: レンジ逆張りモード設定
        self.range_mode_enabled = get_threshold("strategies.adx_trend.range_mode_enabled", True)
        self.range_adx_threshold = get_threshold("strategies.adx_trend.range_adx_threshold", 20)
        self.di_reversal_threshold = get_threshold(
            "strategies.adx_trend.di_reversal_threshold", 5.0
        )
        self.di_diff_threshold = get_threshold("strategies.adx_trend.di_diff_threshold", 8.0)
        self.range_signal_confidence = get_threshold(
            "strategies.adx_trend.range_signal_confidence", 0.45
        )
        # Phase 55.6: DI乖離逆張りモード
        self.use_di_divergence = get_threshold("strategies.adx_trend.use_di_divergence", True)
        self.di_divergence_threshold = get_threshold(
            "strategies.adx_trend.di_divergence_threshold", 12.0
        )
        # Phase 55.6 パターンB: BB位置フィルタ
        self.use_bb_position_filter = get_threshold(
            "strategies.adx_trend.use_bb_position_filter", False
        )
        self.bb_position_upper = get_threshold("strategies.adx_trend.bb_position_upper", 0.80)
        self.bb_position_lower = get_threshold("strategies.adx_trend.bb_position_lower", 0.20)
        self.bb_filter_confidence_bonus = get_threshold(
            "strategies.adx_trend.bb_filter_confidence_bonus", 0.10
        )
        # Phase 55.6 パターンC: RSI反転検証
        self.use_rsi_filter = get_threshold("strategies.adx_trend.use_rsi_filter", False)
        self.rsi_sell_threshold = get_threshold("strategies.adx_trend.rsi_sell_threshold", 60)
        self.rsi_buy_threshold = get_threshold("strategies.adx_trend.rsi_buy_threshold", 40)
        self.rsi_filter_confidence_bonus = get_threshold(
            "strategies.adx_trend.rsi_filter_confidence_bonus", 0.08
        )
        # Phase 55.6 パターンD: ADX動的閾値
        self.use_dynamic_thresholds = get_threshold(
            "strategies.adx_trend.use_dynamic_thresholds", False
        )
        self.dynamic_adx_ultra_low = get_threshold("strategies.adx_trend.dynamic_adx_ultra_low", 10)
        self.dynamic_adx_low = get_threshold("strategies.adx_trend.dynamic_adx_low", 15)
        self.dynamic_di_strict = get_threshold("strategies.adx_trend.dynamic_di_strict", 6.0)
        self.dynamic_di_normal = get_threshold("strategies.adx_trend.dynamic_di_normal", 5.0)
        self.dynamic_di_loose = get_threshold("strategies.adx_trend.dynamic_di_loose", 4.0)
        self.dynamic_conf_high = get_threshold("strategies.adx_trend.dynamic_conf_high", 0.55)
        self.dynamic_conf_mid = get_threshold("strategies.adx_trend.dynamic_conf_mid", 0.48)
        self.dynamic_conf_low = get_threshold("strategies.adx_trend.dynamic_conf_low", 0.42)

        # Phase 56.9: RSI主導型レンジ逆張りモード
        self.use_rsi_driven_mode = get_threshold("strategies.adx_trend.use_rsi_driven_mode", True)
        self.rsi_oversold_trigger = get_threshold("strategies.adx_trend.rsi_oversold_trigger", 35)
        self.rsi_overbought_trigger = get_threshold(
            "strategies.adx_trend.rsi_overbought_trigger", 65
        )
        self.bb_lower_trigger = get_threshold("strategies.adx_trend.bb_lower_trigger", 0.25)
        self.bb_upper_trigger = get_threshold("strategies.adx_trend.bb_upper_trigger", 0.75)
        self.rsi_extreme_bonus = get_threshold("strategies.adx_trend.rsi_extreme_bonus", 0.10)
        self.bb_extreme_bonus = get_threshold("strategies.adx_trend.bb_extreme_bonus", 0.05)
        self.adx_falling_bonus = get_threshold("strategies.adx_trend.adx_falling_bonus", 0.05)

        self.logger.info(
            f"ADX Trend戦略初期化完了 - 期間: {self.adx_period}, "
            f"強いトレンド閾値: {self.strong_trend_threshold}, "
            f"レンジモード: {self.range_mode_enabled}, "
            f"RSI主導モード: {self.use_rsi_driven_mode}"
        )

    def get_required_features(self) -> list[str]:
        """必要特徴量リスト取得"""
        return [
            "close",
            "high",
            "low",
            "volume",
            "adx_14",
            "plus_di_14",
            "minus_di_14",
            "atr_14",
            "volume_ratio",
            "rsi_14",  # Phase 55.6 パターンC: RSI反転検証用
            "bb_position",  # Phase 55.6 パターンB: BB位置フィルタ用
        ]

    def analyze(
        self, df: pd.DataFrame, multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> StrategySignal:
        """
        ADXシグナル生成（抽象メソッド実装）
        Args:
            df: 市場データ（特徴量含む）
        Returns:
            戦略シグナル
        """
        try:
            self.logger.debug(f"[ADXTrend] シグナル生成開始 - データ: {len(df)}行")
            # データ検証
            if not self._validate_data(df):
                return self._create_hold_signal(df, "データ不足")
            # ADX分析
            adx_analysis = self._analyze_adx_trend(df)
            if not adx_analysis:
                return self._create_hold_signal(df, "ADX分析失敗")
            # シグナル判定（Phase 32: multi_timeframe_data渡す）
            signal = self._determine_signal(df, adx_analysis, multi_timeframe_data)
            self.logger.debug(
                f"[ADXTrend] シグナル生成完了: {signal.action} "
                f"(信頼度: {signal.confidence:.3f})"
            )
            return signal
        except Exception as e:
            # Phase 38.4: バックテストログ統合
            self.logger.conditional_log(
                f"[ADXTrend] シグナル生成エラー: {e}", level="error", backtest_level="debug"
            )
            return self._create_hold_signal(df, f"エラー: {str(e)}")

    def _validate_data(self, df: pd.DataFrame) -> bool:
        """データ検証"""
        required_features = self.get_required_features()
        # 必要列の存在確認
        missing_cols = [col for col in required_features if col not in df.columns]
        if missing_cols:
            self.logger.warning(f"[ADXTrend] 不足特徴量: {missing_cols}")
            return False
        # データ長確認
        if len(df) < self.adx_period + 5:  # ADX + 余裕
            self.logger.warning(f"[ADXTrend] データ不足: {len(df)} < {self.adx_period + 5}")
            return False
        # NaN確認（最新データ）
        latest = df.iloc[-1]
        required_non_nan = ["close", "adx_14", "plus_di_14", "minus_di_14"]
        if latest[required_non_nan].isna().any():
            self.logger.warning("[ADXTrend] 最新データにNaN値")
            return False
        return True

    def _analyze_adx_trend(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        ADXトレンド分析
        Returns:
            ADX分析結果辞書
        """
        try:
            # 最新値取得
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else latest
            current_price = float(latest["close"])
            adx = float(latest["adx_14"])
            plus_di = float(latest["plus_di_14"])
            minus_di = float(latest["minus_di_14"])
            # 前期間値
            prev_adx = (
                float(prev["adx_14"]) if "adx_14" in prev and not pd.isna(prev["adx_14"]) else adx
            )
            prev_plus_di = (
                float(prev["plus_di_14"])
                if "plus_di_14" in prev and not pd.isna(prev["plus_di_14"])
                else plus_di
            )
            prev_minus_di = (
                float(prev["minus_di_14"])
                if "minus_di_14" in prev and not pd.isna(prev["minus_di_14"])
                else minus_di
            )
            # トレンド強度判定
            is_strong_trend = adx >= self.strong_trend_threshold
            is_weak_trend = adx < self.weak_trend_threshold
            is_moderate_trend = self.weak_trend_threshold <= adx < self.strong_trend_threshold
            # ADX方向性（上昇/下降）
            adx_rising = adx > prev_adx
            adx_falling = adx < prev_adx
            # DI分析
            di_difference = plus_di - minus_di
            prev_di_difference = prev_plus_di - prev_minus_di
            # DIクロスオーバー検出
            bullish_crossover = (
                di_difference > 0
                and prev_di_difference <= 0
                and abs(di_difference) >= self.di_crossover_threshold
            )
            bearish_crossover = (
                di_difference < 0
                and prev_di_difference >= 0
                and abs(di_difference) >= self.di_crossover_threshold
            )
            # DI強度
            di_strength = abs(di_difference)
            dominant_direction = "bullish" if plus_di > minus_di else "bearish"
            # ボラティリティ・出来高分析
            atr = (
                float(latest["atr_14"])
                if "atr_14" in latest and not pd.isna(latest["atr_14"])
                else 0
            )
            volatility_ratio = atr / current_price if current_price > 0 else 0
            volume_ratio = float(latest["volume_ratio"]) if "volume_ratio" in latest else 1.0
            analysis = {
                "current_price": current_price,
                "adx": adx,
                "plus_di": plus_di,
                "minus_di": minus_di,
                "prev_adx": prev_adx,
                "di_difference": di_difference,
                "prev_di_difference": prev_di_difference,
                "is_strong_trend": is_strong_trend,
                "is_weak_trend": is_weak_trend,
                "is_moderate_trend": is_moderate_trend,
                "adx_rising": adx_rising,
                "adx_falling": adx_falling,
                "bullish_crossover": bullish_crossover,
                "bearish_crossover": bearish_crossover,
                "di_strength": di_strength,
                "dominant_direction": dominant_direction,
                "volatility_ratio": volatility_ratio,
                "volume_ratio": volume_ratio,
            }
            self.logger.debug(
                f"[ADXTrend] ADX分析: ADX={adx:.1f}, +DI={plus_di:.1f}, -DI={minus_di:.1f}, "
                f"強度={['弱', '中', '強'][int(is_moderate_trend) + int(is_strong_trend)]}, "
                f"方向={dominant_direction}"
            )
            return analysis
        except Exception as e:
            self.logger.error(f"[ADXTrend] ADX分析エラー: {e}")
            return None

    def _determine_signal(
        self,
        df: pd.DataFrame,
        analysis: Dict[str, Any],
        multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> StrategySignal:
        """
        シグナル判定ロジック

        Phase 32: multi_timeframe_data対応
        Phase 55.6: レンジ逆張りモード追加

        Args:
            df: 市場データ
            analysis: ADX分析結果
            multi_timeframe_data: マルチタイムフレームデータ（Phase 32）

        Returns:
            最終シグナル
        """
        current_price = analysis["current_price"]

        # Phase 55.6: レンジ逆張りモード（最優先）
        # tight_rangeで90%の市場環境に適応
        if self.range_mode_enabled and analysis["adx"] < self.range_adx_threshold:
            range_signal = self._analyze_range_reversal(df, analysis, multi_timeframe_data)
            if range_signal is not None:
                return range_signal

        # 1. 強いトレンド + DIクロスオーバー（最優先）
        if analysis["is_strong_trend"] and analysis["adx_rising"]:
            if analysis["bullish_crossover"]:
                confidence = self._calculate_trend_confidence(analysis, "buy")
                return self._create_signal(
                    action="buy",
                    confidence=confidence,
                    reason=f"強トレンド上昇DIクロス（ADX: {analysis['adx']:.1f}）",
                    current_price=current_price,
                    df=df,
                    analysis=analysis,
                    multi_timeframe_data=multi_timeframe_data,
                )
            elif analysis["bearish_crossover"]:
                confidence = self._calculate_trend_confidence(analysis, "sell")
                return self._create_signal(
                    action="sell",
                    confidence=confidence,
                    reason=f"強トレンド下降DIクロス（ADX: {analysis['adx']:.1f}）",
                    current_price=current_price,
                    df=df,
                    analysis=analysis,
                    multi_timeframe_data=multi_timeframe_data,
                )
        # 2. 中程度トレンド + 明確なDI優勢
        if analysis["is_moderate_trend"] and analysis["di_strength"] >= 2.0:
            if analysis["dominant_direction"] == "bullish" and analysis["volume_ratio"] > 1.1:
                confidence = self._calculate_trend_confidence(analysis, "buy")
                if confidence >= self.min_confidence:
                    return self._create_signal(
                        action="buy",
                        confidence=confidence,
                        reason=f"中トレンド上昇（ADX: {analysis['adx']:.1f}, +DI優勢）",
                        current_price=current_price,
                        df=df,
                        analysis=analysis,
                        multi_timeframe_data=multi_timeframe_data,
                    )
            elif analysis["dominant_direction"] == "bearish" and analysis["volume_ratio"] > 1.1:
                confidence = self._calculate_trend_confidence(analysis, "sell")
                if confidence >= self.min_confidence:
                    return self._create_signal(
                        action="sell",
                        confidence=confidence,
                        reason=f"中トレンド下降（ADX: {analysis['adx']:.1f}, -DI優勢）",
                        current_price=current_price,
                        df=df,
                        analysis=analysis,
                        multi_timeframe_data=multi_timeframe_data,
                    )
        # 3. 弱いトレンド（レンジ相場）- DI差分ベースの動的判定
        if analysis["is_weak_trend"]:
            return self._handle_weak_trend_signal(df, analysis, multi_timeframe_data)
        # 4. その他の場合 - 動的HOLD信頼度（市場データ統合）
        dynamic_confidence = self._calculate_default_confidence(analysis, df)
        return self._create_hold_signal(
            df,
            f"条件不適合動的（ADX: {analysis['adx']:.1f}, DI差: {analysis['di_difference']:.1f}）",
            dynamic_confidence,
        )

    def _calculate_trend_confidence(self, analysis: Dict[str, Any], direction: str) -> float:
        """
        トレンド信頼度計算
        Args:
            analysis: ADX分析結果
            direction: "buy" または "sell"
        Returns:
            信頼度 (0.0-1.0)
        """
        base_confidence = self.min_confidence
        # ADX強度による調整
        adx_bonus = 0.0
        if analysis["adx"] >= self.strong_trend_threshold:
            adx_bonus = min(0.3, (analysis["adx"] - self.strong_trend_threshold) / 20 * 0.3)
        elif analysis["is_moderate_trend"]:
            adx_bonus = 0.1
        # ADX上昇による追加ボーナス
        adx_direction_bonus = 0.1 if analysis["adx_rising"] else 0.0
        # DI強度による調整
        di_bonus = min(0.2, analysis["di_strength"] / 10 * 0.2)
        # クロスオーバーボーナス
        crossover_bonus = 0.0
        if direction == "buy" and analysis["bullish_crossover"]:
            crossover_bonus = 0.15
        elif direction == "sell" and analysis["bearish_crossover"]:
            crossover_bonus = 0.15
        # 出来高による調整
        volume_bonus = 0.0
        if analysis["volume_ratio"] > 1.2:
            volume_bonus = min(0.1, (analysis["volume_ratio"] - 1.0) * 0.2)
        confidence = (
            base_confidence
            + adx_bonus
            + adx_direction_bonus
            + di_bonus
            + crossover_bonus
            + volume_bonus
        )
        # 循環インポート回避のため遅延インポート
        from ...core.config.threshold_manager import get_threshold

        # 設定値による範囲制限
        min_confidence = get_threshold("dynamic_confidence.strategies.adx_trend.strong_min", 0.40)
        max_confidence = get_threshold("dynamic_confidence.strategies.adx_trend.strong_max", 0.85)
        return max(min_confidence, min(max_confidence, confidence))

    def _handle_weak_trend_signal(
        self,
        df: pd.DataFrame,
        analysis: Dict[str, Any],
        multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> StrategySignal:
        """
        弱トレンド時の動的シグナル処理

        Phase 32: multi_timeframe_data対応

        Args:
            df: 市場データ
            analysis: ADX分析結果
            multi_timeframe_data: マルチタイムフレームデータ（Phase 32）

        Returns:
            動的シグナル
        """
        current_price = analysis["current_price"]

        # DI差分による弱いシグナル判定
        di_diff = abs(analysis["di_difference"])
        # 十分なDI差分がある場合は弱いシグナルを生成
        if di_diff >= self.weak_di_threshold:
            direction = "bullish" if analysis["di_difference"] > 0 else "bearish"
            confidence = self._calculate_weak_trend_confidence(analysis, direction)
            if confidence >= self.min_confidence:
                if direction == "bullish":
                    return self._create_signal(
                        action="buy",
                        confidence=confidence,
                        reason=f"弱トレンド上昇DI（ADX: {analysis['adx']:.1f}, DI差: {di_diff:.1f}）",
                        current_price=current_price,
                        df=df,
                        analysis=analysis,
                        multi_timeframe_data=multi_timeframe_data,
                    )
                else:
                    return self._create_signal(
                        action="sell",
                        confidence=confidence,
                        reason=f"弱トレンド下降DI（ADX: {analysis['adx']:.1f}, DI差: {di_diff:.1f}）",
                        current_price=current_price,
                        df=df,
                        analysis=analysis,
                        multi_timeframe_data=multi_timeframe_data,
                    )
        # DI差分が小さい場合は動的HOLD（市場データ統合）
        dynamic_confidence = self._calculate_weak_trend_hold_confidence(analysis, df)
        return self._create_hold_signal(
            df,
            f"レンジ相場動的（ADX: {analysis['adx']:.1f}, DI差: {di_diff:.1f}）",
            dynamic_confidence,
        )

    def _get_dynamic_thresholds(self, adx_value: float) -> Dict[str, float]:
        """
        Phase 55.6 パターンD: ADX値に基づく動的閾値取得

        Args:
            adx_value: 現在のADX値

        Returns:
            動的閾値辞書 {di_threshold, confidence_base}
        """
        if adx_value < self.dynamic_adx_ultra_low:
            # 超安定レンジ（ADX<10）: 厳格な閾値、高信頼度
            return {
                "di_threshold": self.dynamic_di_strict,
                "confidence_base": self.dynamic_conf_high,
            }
        elif adx_value < self.dynamic_adx_low:
            # 標準レンジ（ADX 10-15）: 通常閾値
            return {
                "di_threshold": self.dynamic_di_normal,
                "confidence_base": self.dynamic_conf_mid,
            }
        else:
            # 境界レンジ（ADX 15-20）: 緩い閾値、控えめ信頼度
            return {
                "di_threshold": self.dynamic_di_loose,
                "confidence_base": self.dynamic_conf_low,
            }

    def _analyze_range_reversal(
        self,
        df: pd.DataFrame,
        analysis: Dict[str, Any],
        multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> Optional[StrategySignal]:
        """
        Phase 56.9: RSI主導型レンジ逆張り分析

        Web調査に基づき、DI分析からRSI+BB主導に変更。
        レンジ相場ではRSI極端値が最も信頼できるシグナル。

        Args:
            df: 市場データ
            analysis: ADX分析結果
            multi_timeframe_data: マルチタイムフレームデータ

        Returns:
            逆張りシグナル、またはNone（条件不適合時）
        """
        try:
            current_price = analysis["current_price"]
            adx_value = analysis["adx"]
            adx_falling = analysis["adx_falling"]

            # Phase 56.9: RSI主導モード（優先）
            if self.use_rsi_driven_mode:
                # RSI取得
                if "rsi_14" not in df.columns:
                    return None
                rsi = float(df["rsi_14"].iloc[-1])
                if pd.isna(rsi):
                    return None

                # BB位置取得
                if "bb_position" not in df.columns:
                    return None
                bb_position = float(df["bb_position"].iloc[-1])
                if pd.isna(bb_position):
                    return None

                self.logger.debug(
                    f"[ADXTrend RSI主導] RSI={rsi:.1f}, BB={bb_position:.2f}, "
                    f"ADX={adx_value:.1f}, falling={adx_falling}"
                )

                # === 買いシグナル（RSI AND BB条件）===
                if rsi < self.rsi_oversold_trigger and bb_position < self.bb_lower_trigger:
                    confidence = self._calculate_rsi_reversal_confidence(
                        rsi, bb_position, adx_falling, "buy"
                    )
                    self.logger.info(
                        f"[ADXTrend RSI主導] BUY検出: RSI={rsi:.1f}, "
                        f"BB={bb_position:.2f}, ADX={adx_value:.1f}, 信頼度={confidence:.2f}"
                    )
                    return self._create_signal(
                        action="buy",
                        confidence=confidence,
                        reason=f"RSI売られすぎ逆張り（RSI={rsi:.1f}, BB={bb_position:.2f}）",
                        current_price=current_price,
                        df=df,
                        analysis=analysis,
                        multi_timeframe_data=multi_timeframe_data,
                    )

                # === 売りシグナル（RSI AND BB条件）===
                if rsi > self.rsi_overbought_trigger and bb_position > self.bb_upper_trigger:
                    confidence = self._calculate_rsi_reversal_confidence(
                        rsi, bb_position, adx_falling, "sell"
                    )
                    self.logger.info(
                        f"[ADXTrend RSI主導] SELL検出: RSI={rsi:.1f}, "
                        f"BB={bb_position:.2f}, ADX={adx_value:.1f}, 信頼度={confidence:.2f}"
                    )
                    return self._create_signal(
                        action="sell",
                        confidence=confidence,
                        reason=f"RSI買われすぎ逆張り（RSI={rsi:.1f}, BB={bb_position:.2f}）",
                        current_price=current_price,
                        df=df,
                        analysis=analysis,
                        multi_timeframe_data=multi_timeframe_data,
                    )

                # RSI主導モードで条件不適合
                return None

            # フォールバック: 従来DI分析ロジック（use_rsi_driven_mode=Falseの場合）
            di_diff = analysis["di_difference"]
            prev_di_diff = analysis["prev_di_difference"]
            di_change = abs(di_diff - prev_di_diff)
            di_diff_abs = abs(di_diff)

            if di_change >= self.di_reversal_threshold and di_diff_abs >= self.di_diff_threshold:
                confidence = self._calculate_range_reversal_confidence(
                    analysis, di_change, di_diff_abs, self.range_signal_confidence
                )
                if di_diff > 0:
                    return self._create_signal(
                        action="sell",
                        confidence=confidence,
                        reason=f"レンジDI逆張り売り（DI変化: {di_change:.1f}）",
                        current_price=current_price,
                        df=df,
                        analysis=analysis,
                        multi_timeframe_data=multi_timeframe_data,
                    )
                else:
                    return self._create_signal(
                        action="buy",
                        confidence=confidence,
                        reason=f"レンジDI逆張り買い（DI変化: {di_change:.1f}）",
                        current_price=current_price,
                        df=df,
                        analysis=analysis,
                        multi_timeframe_data=multi_timeframe_data,
                    )

            # 条件不適合 → None（従来ロジックへフォールスルー）
            return None

        except Exception as e:
            self.logger.error(f"[ADXTrend Range] 逆張り分析エラー: {e}")
            return None

    def _calculate_di_divergence_confidence(
        self, analysis: Dict[str, Any], di_diff_abs: float
    ) -> float:
        """
        Phase 55.6: DI乖離逆張り信頼度計算

        Args:
            analysis: ADX分析結果
            di_diff_abs: DI差分の絶対値

        Returns:
            信頼度 (0.40-0.60)
        """
        base_confidence = self.range_signal_confidence

        # DI乖離ボーナス（乖離が大きいほど信頼度UP）
        divergence_bonus = min(0.15, (di_diff_abs - self.di_divergence_threshold) / 20 * 0.15)

        # ADX低さボーナス（ADXが低いほどレンジ確定）
        adx_bonus = 0.0
        if analysis["adx"] < 12:
            adx_bonus = 0.05
        elif analysis["adx"] < 15:
            adx_bonus = 0.03
        elif analysis["adx"] < 18:
            adx_bonus = 0.01

        # 出来高ボーナス
        volume_bonus = 0.0
        if analysis["volume_ratio"] > 1.2:
            volume_bonus = min(0.05, (analysis["volume_ratio"] - 1.0) * 0.1)

        confidence = base_confidence + divergence_bonus + adx_bonus + volume_bonus

        # 範囲制限
        return max(0.40, min(0.60, confidence))

    def _calculate_range_reversal_confidence(
        self,
        analysis: Dict[str, Any],
        di_change: float,
        di_diff_abs: float,
        confidence_base: float = None,
    ) -> float:
        """
        Phase 55.6: レンジ逆張り信頼度計算

        Args:
            analysis: ADX分析結果
            di_change: DI変化量
            di_diff_abs: DI差分の絶対値
            confidence_base: 基本信頼度（パターンD動的閾値用）

        Returns:
            信頼度 (0.35-0.55)
        """
        base_confidence = confidence_base if confidence_base else self.range_signal_confidence

        # DI変化量ボーナス（変化が大きいほど信頼度UP）
        change_bonus = min(0.10, (di_change - self.di_reversal_threshold) / 10 * 0.10)

        # DI差分ボーナス（差分が大きいほど方向性明確）
        diff_bonus = min(0.05, (di_diff_abs - self.di_diff_threshold) / 10 * 0.05)

        # ADX低さボーナス（ADXが低いほどレンジ確定）
        adx_bonus = 0.0
        if analysis["adx"] < 15:
            adx_bonus = 0.03
        elif analysis["adx"] < 18:
            adx_bonus = 0.01

        # 出来高ボーナス
        volume_bonus = 0.0
        if analysis["volume_ratio"] > 1.2:
            volume_bonus = min(0.05, (analysis["volume_ratio"] - 1.0) * 0.1)

        confidence = base_confidence + change_bonus + diff_bonus + adx_bonus + volume_bonus

        # 範囲制限
        return max(0.35, min(0.55, confidence))

    def _calculate_rsi_reversal_confidence(
        self,
        rsi: float,
        bb_position: float,
        adx_falling: bool,
        direction: str,
    ) -> float:
        """
        Phase 56.9: RSI主導型レンジ逆張り信頼度計算

        Web調査に基づき、RSI極端値とBB位置で信頼度を計算。
        ADX下降中はレンジ強化を示すためボーナス付与。

        Args:
            rsi: RSI値
            bb_position: BB位置（0-1）
            adx_falling: ADX下降中フラグ
            direction: "buy" or "sell"

        Returns:
            信頼度 (0.40-0.70)
        """
        confidence = self.range_signal_confidence  # 0.40 base

        # RSI極端ボーナス（< 30 or > 70）
        if direction == "buy" and rsi < 30:
            confidence += self.rsi_extreme_bonus
        elif direction == "sell" and rsi > 70:
            confidence += self.rsi_extreme_bonus

        # BB極端ボーナス（< 0.15 or > 0.85）
        if direction == "buy" and bb_position < 0.15:
            confidence += self.bb_extreme_bonus
        elif direction == "sell" and bb_position > 0.85:
            confidence += self.bb_extreme_bonus

        # ADX下降ボーナス（レンジ強化）
        if adx_falling:
            confidence += self.adx_falling_bonus

        # RSI/BB位置に応じた追加ボーナス
        if direction == "buy":
            # RSIが低いほどボーナス
            rsi_bonus = max(0, (self.rsi_oversold_trigger - rsi) / 100 * 0.10)
            # BB位置が低いほどボーナス
            bb_bonus = max(0, (self.bb_lower_trigger - bb_position) * 0.10)
        else:
            # RSIが高いほどボーナス
            rsi_bonus = max(0, (rsi - self.rsi_overbought_trigger) / 100 * 0.10)
            # BB位置が高いほどボーナス
            bb_bonus = max(0, (bb_position - self.bb_upper_trigger) * 0.10)

        confidence += rsi_bonus + bb_bonus

        # 範囲制限（0.40-0.70）
        return max(0.40, min(0.70, confidence))

    def _calculate_weak_trend_confidence(self, analysis: Dict[str, Any], direction: str) -> float:
        """
        弱トレンド信頼度計算
        Args:
            analysis: ADX分析結果
            direction: "bullish" または "bearish"
        Returns:
            信頼度 (0.0-1.0)
        """
        base_confidence = self.di_weak_signal_confidence
        # DI差分による調整（差分が大きいほど信頼度上昇）
        di_strength_bonus = min(0.2, analysis["di_strength"] / 5.0 * 0.2)
        # ADX上昇による調整（弱くても上昇中なら少しボーナス）
        adx_direction_bonus = 0.05 if analysis["adx_rising"] else 0.0
        # 出来高による調整
        volume_bonus = 0.0
        if analysis["volume_ratio"] > 1.1:
            volume_bonus = min(0.1, (analysis["volume_ratio"] - 1.0) * 0.2)
        confidence = base_confidence + di_strength_bonus + adx_direction_bonus + volume_bonus
        # 循環インポート回避のため遅延インポート
        from ...core.config.threshold_manager import get_threshold

        # 設定値による範囲制限
        min_confidence = get_threshold("dynamic_confidence.strategies.adx_trend.weak_min", 0.25)
        max_confidence = get_threshold("dynamic_confidence.strategies.adx_trend.weak_max", 0.50)
        return max(min_confidence, min(max_confidence, confidence))

    def _calculate_weak_trend_hold_confidence(
        self, analysis: Dict[str, Any], df: pd.DataFrame = None
    ) -> float:
        """
        弱トレンドHOLD信頼度計算（市場データ統合版）
        Args:
            analysis: ADX分析結果
            df: 市場データ（市場不確実性計算用）
        Returns:
            動的信頼度 (0.2-0.35)
        """
        # 循環インポート回避のため遅延インポート
        from ...core.config.threshold_manager import get_threshold

        base_confidence = get_threshold("strategies.adx_trend.hold_confidence", 0.30)

        # 市場データ基づく動的信頼度調整システム
        market_uncertainty = self._calculate_market_uncertainty(df) if df is not None else 0.02

        # ADX値による調整（低いほど不確実性増加）
        adx_penalty = (
            (self.weak_trend_threshold - analysis["adx"]) / self.weak_trend_threshold * 0.05
        )
        # DI差分による微調整
        di_strength_bonus = min(0.03, analysis["di_strength"] / 10.0 * 0.03)

        # 基本信頼度と補正を市場不確実性で動的調整（固定値回避）
        confidence = (base_confidence - adx_penalty + di_strength_bonus) * (1 + market_uncertainty)

        # 循環インポート回避のため遅延インポート
        from ...core.config.threshold_manager import get_threshold

        hold_min = get_threshold("dynamic_confidence.strategies.adx_trend.hold_min", 0.20)
        hold_max = get_threshold("dynamic_confidence.strategies.adx_trend.hold_max", 0.35)
        return max(hold_min, min(hold_max, confidence))

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
        デフォルト動的信頼度計算（市場データ統合版）
        Args:
            analysis: ADX分析結果
            df: 市場データ（市場不確実性計算用）
        Returns:
            動的信頼度 (0.25-0.45)
        """
        # 循環インポート回避のため遅延インポート
        from ...core.config.threshold_manager import get_threshold

        base_confidence = get_threshold("strategies.adx_trend.hold_confidence", 0.30)

        # 市場データ基づく動的信頼度調整システム
        market_uncertainty = self._calculate_market_uncertainty(df) if df is not None else 0.02

        # ADX状態による調整
        if analysis["is_moderate_trend"]:
            trend_bonus = 0.02
        elif analysis["is_weak_trend"]:
            trend_bonus = -0.02
        else:
            trend_bonus = 0.0

        # 基本信頼度と傾向補正を市場不確実性で動的調整（固定値回避）
        confidence = (base_confidence + trend_bonus) * (1 + market_uncertainty)

        # 循環インポート回避のため遅延インポート
        from ...core.config.threshold_manager import get_threshold

        default_min = get_threshold("dynamic_confidence.strategies.adx_trend.default_min", 0.25)
        default_max = get_threshold(
            "dynamic_confidence.strategies.adx_trend.default_max", 0.60
        )  # Phase 38.5.1: 0.45→0.60（thresholds.yaml統一）
        return max(default_min, min(default_max, confidence))

    def _create_hold_signal(
        self, df: pd.DataFrame, reason: str, dynamic_confidence: float = None
    ) -> StrategySignal:
        """HOLDシグナル生成（動的信頼度対応）"""
        current_price = float(df["close"].iloc[-1]) if "close" in df.columns else 0.0
        # 動的信頼度優先、なければ設定値使用
        if dynamic_confidence is not None:
            confidence = dynamic_confidence
        else:
            # 循環インポート回避のため遅延インポート
            from ...core.config.threshold_manager import get_threshold

            confidence = get_threshold("strategies.adx_trend.hold_confidence", 0.25)
        return StrategySignal(
            strategy_name=self.name,
            timestamp=datetime.now(),
            action="hold",
            confidence=confidence,
            strength=confidence * 0.4,  # 強度は信頼度の40%
            current_price=current_price,
            reason=f"ADX動的: {reason}",
            metadata={
                "signal_type": "adx_dynamic_hold",
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
            analysis: ADX分析結果
            multi_timeframe_data: マルチタイムフレームデータ

        Returns:
            StrategySignal
        """
        # 決定辞書作成
        decision = {
            "action": action,
            "confidence": confidence,
            "strength": confidence,  # ADXTrendでは信頼度=強度
            "reason": reason,
            "metadata": {
                "adx": analysis["adx"],
                "plus_di": analysis["plus_di"],
                "minus_di": analysis["minus_di"],
                "di_difference": analysis["di_difference"],
                "trend_strength": "strong" if analysis["is_strong_trend"] else "moderate",
                "signal_type": f"adx_trend_{action}",
            },
        }

        # Phase 32: SignalBuilder使用（15m足ATR優先取得）
        return SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.name,
            decision=decision,
            current_price=current_price,
            df=df,
            config=self.config,
            strategy_type=StrategyType.ADX_TREND,
            multi_timeframe_data=multi_timeframe_data,
        )

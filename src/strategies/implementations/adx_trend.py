"""
ADX Trend Strength戦略実装 - 市場レジーム適応型取引
Average Directional Index (ADX) を用いたトレンド強度判定と
+DI/-DIクロスオーバーによる方向性検出を組み合わせた戦略。
主要機能:
- ADX値による市場レジーム判定（トレンド vs レンジ）
- +DI/-DIクロスオーバー検出
- トレンド強度適応型信頼度調整
- レンジ相場での取引抑制
実装日: 2025年9月9日 - フィボナッチ戦略置換
"""

from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd

from ...core.logger import get_logger
from ..base.strategy_base import StrategyBase, StrategySignal
from ..utils.strategy_utils import SignalBuilder, StrategyType


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
        self.logger.info(
            f"ADX Trend戦略初期化完了 - 期間: {self.adx_period}, 強いトレンド閾値: {self.strong_trend_threshold}"
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
            # Phase 35: バックテストモード時はDEBUGレベル（環境変数直接チェック）
            import os
            if os.environ.get('BACKTEST_MODE') == 'true':
                self.logger.debug(f"[ADXTrend] シグナル生成エラー: {e}")
            else:
                self.logger.error(f"[ADXTrend] シグナル生成エラー: {e}")
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

        Args:
            df: 市場データ
            analysis: ADX分析結果
            multi_timeframe_data: マルチタイムフレームデータ（Phase 32）

        Returns:
            最終シグナル
        """
        current_price = analysis["current_price"]

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
        市場データ基づく不確実性計算（設定ベース統一ロジック）

        Args:
            df: 市場データ

        Returns:
            float: 市場不確実性係数（設定値の範囲）
        """
        try:
            # 循環インポート回避のため遅延インポート
            from ...core.config.threshold_manager import get_threshold

            # 設定値取得
            volatility_max = get_threshold(
                "dynamic_confidence.market_uncertainty.volatility_factor_max", 0.05
            )
            volume_max = get_threshold(
                "dynamic_confidence.market_uncertainty.volume_factor_max", 0.03
            )
            volume_multiplier = get_threshold(
                "dynamic_confidence.market_uncertainty.volume_multiplier", 0.1
            )
            price_max = get_threshold(
                "dynamic_confidence.market_uncertainty.price_factor_max", 0.02
            )
            uncertainty_max = get_threshold(
                "dynamic_confidence.market_uncertainty.uncertainty_max", 0.10
            )

            # ATRベースのボラティリティ要因
            current_price = float(df["close"].iloc[-1])
            atr_value = float(df["atr_14"].iloc[-1])
            volatility_factor = min(volatility_max, atr_value / current_price)

            # ボリューム異常度（平均からの乖離）
            current_volume = float(df["volume"].iloc[-1])
            avg_volume = float(df["volume"].rolling(20).mean().iloc[-1])
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            volume_factor = min(volume_max, abs(volume_ratio - 1.0) * volume_multiplier)

            # 価格変動率（短期動向）
            price_change = abs(float(df["close"].pct_change().iloc[-1]))
            price_factor = min(price_max, price_change)

            # 統合不確実性（設定値の範囲で市場状況を反映）
            market_uncertainty = volatility_factor + volume_factor + price_factor

            # 設定値で調整範囲を制限
            return min(uncertainty_max, market_uncertainty)

        except Exception as e:
            self.logger.warning(f"市場不確実性計算エラー: {e}")
            return 0.02  # デフォルト値（2%の軽微な調整）

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
        default_max = get_threshold("dynamic_confidence.strategies.adx_trend.default_max", 0.45)
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

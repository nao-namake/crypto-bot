# =============================================================================
# ファイル名: crypto_bot/analysis/market_environment_analyzer.py
# 説明:
# Phase C2: 高度な市場環境解析システム
# ボラティリティレジーム判定・流動性スコア・市場状況適応・多次元市場分析
# CrossTimeframeIntegratorの動的重み調整システム用基盤モジュール
# =============================================================================

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class MarketEnvironmentAnalyzer:
    """
    Phase C2: 高度な市場環境解析システム

    機能:
    - 多次元市場レジーム判定（crisis/volatile/normal/calm/bullish/bearish）
    - ボラティリティレジーム検出・分類・予測
    - 流動性スコア計算・市場深度分析
    - トレンド強度・持続性評価
    - 市場ストレス指標統合解析
    - リアルタイム市場状況監視・異常検知
    """

    def __init__(self, config: Dict[str, Any]):
        """
        市場環境解析システム初期化

        Parameters:
        -----------
        config : Dict[str, Any]
            解析設定辞書
        """
        self.config = config

        # 基本解析設定
        analysis_config = config.get("market_analysis", {})
        self.volatility_lookback = analysis_config.get("volatility_lookback", 20)
        self.trend_lookback = analysis_config.get("trend_lookback", 50)
        self.liquidity_lookback = analysis_config.get("liquidity_lookback", 10)
        self.regime_sensitivity = analysis_config.get("regime_sensitivity", 1.0)

        # ボラティリティレジーム閾値設定
        self.volatility_thresholds = analysis_config.get(
            "volatility_thresholds",
            {
                "extreme_low": 0.005,  # 0.5%未満: 超低ボラティリティ
                "low": 0.01,  # 1%未満: 低ボラティリティ
                "normal_low": 0.02,  # 2%未満: 正常低域
                "normal_high": 0.04,  # 4%未満: 正常高域
                "high": 0.06,  # 6%未満: 高ボラティリティ
                "extreme_high": 0.10,  # 10%以上: 極高ボラティリティ
            },
        )

        # VIXレジーム閾値設定
        self.vix_thresholds = analysis_config.get(
            "vix_thresholds",
            {
                "extreme_complacency": 12,  # 12未満: 極度の楽観
                "complacency": 16,  # 16未満: 楽観
                "normal_low": 20,  # 20未満: 正常低域
                "normal_high": 25,  # 25未満: 正常高域
                "fear": 30,  # 30未満: 恐怖
                "panic": 40,  # 40未満: パニック
                "extreme_panic": 50,  # 50以上: 極度のパニック
            },
        )

        # 流動性評価設定
        self.liquidity_config = analysis_config.get(
            "liquidity",
            {
                "volume_ma_period": 20,
                "spread_threshold": 0.001,
                "depth_levels": [0.1, 0.5, 1.0, 2.0],  # パーセント深度レベル
                "time_decay_factor": 0.9,
            },
        )

        # 統計・履歴管理
        self.analysis_history: List[Dict[str, Any]] = []
        self.regime_history: List[Dict[str, Any]] = []
        self.max_history_size = 200

        # 統計追跡
        self.analysis_stats = {
            "total_analyses": 0,
            "regime_changes": 0,
            "volatility_regime_changes": 0,
            "liquidity_assessments": 0,
            "trend_analyses": 0,
            "stress_detections": 0,
        }

        # 現在の市場状態キャッシュ
        self.current_regime = "unknown"
        self.current_volatility_regime = "unknown"
        self.current_liquidity_score = 0.5
        self.last_analysis_time = None

        logger.info("🔍 MarketEnvironmentAnalyzer initialized")
        logger.info(f"   Volatility lookback: {self.volatility_lookback} periods")
        logger.info(f"   Trend lookback: {self.trend_lookback} periods")
        logger.info(f"   Regime sensitivity: {self.regime_sensitivity}")

    def analyze_comprehensive_market_environment(
        self,
        price_data: pd.DataFrame,
        external_data: Optional[Dict[str, Any]] = None,
        volume_data: Optional[pd.Series] = None,
    ) -> Dict[str, Any]:
        """
        包括的市場環境分析（Phase C2コア機能）

        Parameters:
        -----------
        price_data : pd.DataFrame
            OHLCV価格データ
        external_data : Dict[str, Any], optional
            外部データ（VIX・Fear&Greed・DXY等）
        volume_data : pd.Series, optional
            出来高データ

        Returns:
        --------
        Dict[str, Any]
            包括的市場環境分析結果
        """
        self.analysis_stats["total_analyses"] += 1

        try:
            analysis_result = {
                "timestamp": datetime.now(),
                "analysis_version": "phase_c2_comprehensive",
            }

            # 1. ボラティリティレジーム分析
            volatility_analysis = self._analyze_volatility_regime(price_data)
            analysis_result.update(volatility_analysis)

            # 2. 市場レジーム判定
            market_regime = self._determine_market_regime(price_data, external_data)
            analysis_result["market_regime"] = market_regime

            # 3. トレンド分析
            trend_analysis = self._analyze_trend_characteristics(price_data)
            analysis_result.update(trend_analysis)

            # 4. 流動性分析
            if volume_data is not None or "volume" in price_data.columns:
                liquidity_analysis = self._analyze_liquidity_conditions(
                    price_data, volume_data
                )
                analysis_result.update(liquidity_analysis)
            else:
                analysis_result["liquidity_score"] = 0.5
                analysis_result["liquidity_regime"] = "unknown"

            # 5. 市場ストレス指標
            stress_analysis = self._calculate_market_stress_indicators(
                price_data, external_data
            )
            analysis_result.update(stress_analysis)

            # 6. 予測適応性スコア
            adaptability_score = self._calculate_prediction_adaptability(
                analysis_result
            )
            analysis_result["prediction_adaptability"] = adaptability_score

            # 7. 取引環境品質評価
            trading_environment = self._assess_trading_environment_quality(
                analysis_result
            )
            analysis_result.update(trading_environment)

            # 履歴記録・状態更新
            self._update_analysis_state(analysis_result)
            self._record_analysis(analysis_result)

            logger.debug(
                f"🔍 Market Analysis: regime={market_regime}, "
                f"vol_regime={analysis_result.get('volatility_regime', 'unknown')}, "
                f"stress={analysis_result.get('stress_level', 'unknown')}"
            )

            return analysis_result

        except Exception as e:
            logger.error(f"❌ Comprehensive market analysis failed: {e}")
            return self._create_fallback_analysis()

    def _analyze_volatility_regime(self, price_data: pd.DataFrame) -> Dict[str, Any]:
        """ボラティリティレジーム分析"""
        try:
            if len(price_data) < self.volatility_lookback:
                return {
                    "volatility_regime": "insufficient_data",
                    "volatility_score": 0.5,
                }

            # リターン計算
            returns = price_data["close"].pct_change().dropna()

            if len(returns) < self.volatility_lookback:
                return {
                    "volatility_regime": "insufficient_data",
                    "volatility_score": 0.5,
                }

            # 短期・中期・長期ボラティリティ
            short_vol = returns.rolling(5).std().iloc[-1] * np.sqrt(365)
            medium_vol = returns.rolling(self.volatility_lookback).std().iloc[
                -1
            ] * np.sqrt(365)

            if len(returns) >= 60:
                long_vol = returns.rolling(60).std().iloc[-1] * np.sqrt(365)
            else:
                long_vol = medium_vol

            # 実現ボラティリティ（主指標）
            realized_vol = medium_vol

            # ボラティリティレジーム判定
            if realized_vol < self.volatility_thresholds["extreme_low"]:
                vol_regime = "extreme_calm"
            elif realized_vol < self.volatility_thresholds["low"]:
                vol_regime = "calm"
            elif realized_vol < self.volatility_thresholds["normal_low"]:
                vol_regime = "normal_low"
            elif realized_vol < self.volatility_thresholds["normal_high"]:
                vol_regime = "normal"
            elif realized_vol < self.volatility_thresholds["high"]:
                vol_regime = "volatile"
            elif realized_vol < self.volatility_thresholds["extreme_high"]:
                vol_regime = "high_volatile"
            else:
                vol_regime = "extreme_volatile"

            # ボラティリティ変動傾向
            vol_trend = "stable"
            if short_vol > medium_vol * 1.2:
                vol_trend = "increasing"
            elif short_vol < medium_vol * 0.8:
                vol_trend = "decreasing"

            # ボラティリティスコア正規化
            vol_score = min(realized_vol / 0.05, 1.0)  # 5%で正規化

            return {
                "volatility_regime": vol_regime,
                "volatility_score": vol_score,
                "realized_volatility": realized_vol,
                "short_volatility": short_vol,
                "medium_volatility": medium_vol,
                "long_volatility": long_vol,
                "volatility_trend": vol_trend,
                "volatility_percentile": self._calculate_volatility_percentile(
                    returns, realized_vol
                ),
            }

        except Exception as e:
            logger.error(f"Volatility regime analysis failed: {e}")
            return {"volatility_regime": "error", "volatility_score": 0.5}

    def _determine_market_regime(
        self, price_data: pd.DataFrame, external_data: Optional[Dict[str, Any]]
    ) -> str:
        """市場レジーム判定（多次元分析）"""
        try:
            regime_scores = {
                "crisis": 0.0,
                "volatile": 0.0,
                "normal": 0.0,
                "calm": 0.0,
                "bullish": 0.0,
                "bearish": 0.0,
            }

            # 1. ボラティリティベーススコア
            returns = price_data["close"].pct_change().dropna()
            if len(returns) >= self.volatility_lookback:
                recent_vol = returns.rolling(self.volatility_lookback).std().iloc[
                    -1
                ] * np.sqrt(365)

                if recent_vol > 0.08:  # 8%超
                    regime_scores["crisis"] += 0.4
                    regime_scores["volatile"] += 0.3
                elif recent_vol > 0.04:  # 4-8%
                    regime_scores["volatile"] += 0.4
                    regime_scores["normal"] += 0.2
                elif recent_vol > 0.015:  # 1.5-4%
                    regime_scores["normal"] += 0.5
                else:  # 1.5%未満
                    regime_scores["calm"] += 0.4

            # 2. VIXベーススコア
            if external_data and "vix_level" in external_data:
                vix = external_data["vix_level"]

                if vix > 40:
                    regime_scores["crisis"] += 0.4
                elif vix > 30:
                    regime_scores["volatile"] += 0.3
                    regime_scores["crisis"] += 0.1
                elif vix > 20:
                    regime_scores["normal"] += 0.3
                elif vix < 15:
                    regime_scores["calm"] += 0.2
                    regime_scores["bullish"] += 0.2

            # 3. 価格トレンドベーススコア
            if len(price_data) >= self.trend_lookback:
                recent_price = price_data["close"].iloc[-1]
                ma_short = price_data["close"].rolling(10).mean().iloc[-1]
                ma_long = (
                    price_data["close"].rolling(self.trend_lookback).mean().iloc[-1]
                )

                if recent_price > ma_short > ma_long:
                    regime_scores["bullish"] += 0.3
                elif recent_price < ma_short < ma_long:
                    regime_scores["bearish"] += 0.3

                # トレンド強度
                price_change = (recent_price - ma_long) / ma_long
                if abs(price_change) > 0.2:  # 20%超の変動
                    if price_change > 0:
                        regime_scores["bullish"] += 0.2
                    else:
                        regime_scores["bearish"] += 0.2
                        regime_scores["volatile"] += 0.1

            # 4. Fear&Greedベーススコア
            if external_data and "fear_greed" in external_data:
                fg = external_data["fear_greed"]

                if fg > 80:  # Extreme Greed
                    regime_scores["bullish"] += 0.2
                    regime_scores["volatile"] += 0.1  # バブル警戒
                elif fg < 20:  # Extreme Fear
                    regime_scores["bearish"] += 0.2
                    regime_scores["crisis"] += 0.1
                elif 40 <= fg <= 60:  # Neutral
                    regime_scores["normal"] += 0.2

            # 最高スコアのレジーム選択
            max_regime = max(regime_scores, key=regime_scores.get)
            max_score = regime_scores[max_regime]

            # 信頼度チェック
            if max_score < 0.3:  # 低信頼度
                return "uncertain"

            # 複合レジーム判定
            sorted_regimes = sorted(
                regime_scores.items(), key=lambda x: x[1], reverse=True
            )
            if sorted_regimes[1][1] > max_score * 0.7:  # 2位が1位の70%以上
                return f"{max_regime}_{sorted_regimes[1][0]}"

            return max_regime

        except Exception as e:
            logger.error(f"Market regime determination failed: {e}")
            return "unknown"

    def _analyze_trend_characteristics(
        self, price_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """トレンド特性分析"""
        try:
            if len(price_data) < self.trend_lookback:
                return {"trend_strength": 0.5, "trend_direction": "sideways"}

            self.analysis_stats["trend_analyses"] += 1

            # 複数期間移動平均
            ma_10 = price_data["close"].rolling(10).mean()
            ma_20 = price_data["close"].rolling(20).mean()
            ma_50 = price_data["close"].rolling(50).mean()

            current_price = price_data["close"].iloc[-1]

            # トレンド方向判定
            if current_price > ma_10.iloc[-1] > ma_20.iloc[-1] > ma_50.iloc[-1]:
                trend_direction = "strong_uptrend"
                trend_strength = 0.9
            elif current_price > ma_10.iloc[-1] > ma_20.iloc[-1]:
                trend_direction = "uptrend"
                trend_strength = 0.7
            elif current_price > ma_20.iloc[-1]:
                trend_direction = "weak_uptrend"
                trend_strength = 0.6
            elif current_price < ma_10.iloc[-1] < ma_20.iloc[-1] < ma_50.iloc[-1]:
                trend_direction = "strong_downtrend"
                trend_strength = 0.9
            elif current_price < ma_10.iloc[-1] < ma_20.iloc[-1]:
                trend_direction = "downtrend"
                trend_strength = 0.7
            elif current_price < ma_20.iloc[-1]:
                trend_direction = "weak_downtrend"
                trend_strength = 0.6
            else:
                trend_direction = "sideways"
                trend_strength = 0.3

            # トレンド持続性（ADX風）
            price_changes = price_data["close"].pct_change().dropna()
            if len(price_changes) >= 14:
                directional_movement = abs(price_changes.rolling(14).mean().iloc[-1])
                trend_persistence = min(directional_movement * 50, 1.0)  # 正規化
            else:
                trend_persistence = 0.5

            # トレンド安定性
            if len(ma_20) >= 10:
                ma_stability = 1.0 - (ma_20.rolling(10).std().iloc[-1] / ma_20.iloc[-1])
                trend_stability = max(0.0, min(1.0, ma_stability))
            else:
                trend_stability = 0.5

            return {
                "trend_direction": trend_direction,
                "trend_strength": trend_strength,
                "trend_persistence": trend_persistence,
                "trend_stability": trend_stability,
                "price_vs_ma20": (current_price - ma_20.iloc[-1]) / ma_20.iloc[-1],
                "ma_alignment_score": self._calculate_ma_alignment_score(
                    current_price, ma_10.iloc[-1], ma_20.iloc[-1], ma_50.iloc[-1]
                ),
            }

        except Exception as e:
            logger.error(f"Trend characteristics analysis failed: {e}")
            return {"trend_strength": 0.5, "trend_direction": "unknown"}

    def _analyze_liquidity_conditions(
        self, price_data: pd.DataFrame, volume_data: Optional[pd.Series] = None
    ) -> Dict[str, Any]:
        """流動性状況分析"""
        try:
            self.analysis_stats["liquidity_assessments"] += 1

            # 出来高データ取得
            if volume_data is not None:
                volume = volume_data
            elif "volume" in price_data.columns:
                volume = price_data["volume"]
            else:
                return {"liquidity_score": 0.5, "liquidity_regime": "unknown"}

            if len(volume) < self.liquidity_config["volume_ma_period"]:
                return {"liquidity_score": 0.5, "liquidity_regime": "insufficient_data"}

            # 出来高分析
            volume_ma = volume.rolling(self.liquidity_config["volume_ma_period"]).mean()
            current_volume = volume.iloc[-1]
            avg_volume = volume_ma.iloc[-1]

            # 相対出来高スコア
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            volume_score = min(volume_ratio / 2.0, 1.0)  # 2倍で満点

            # 価格レンジ分析（流動性の代理指標）
            if len(price_data) >= 10:
                high_low_range = (price_data["high"] - price_data["low"]) / price_data[
                    "close"
                ]
                avg_range = high_low_range.rolling(10).mean().iloc[-1]
                range_score = 1.0 - min(avg_range * 20, 1.0)  # 狭いレンジほど高流動性
            else:
                range_score = 0.5

            # 総合流動性スコア
            liquidity_score = volume_score * 0.6 + range_score * 0.4

            # 流動性レジーム
            if liquidity_score > 0.8:
                liquidity_regime = "high_liquidity"
            elif liquidity_score > 0.6:
                liquidity_regime = "normal_liquidity"
            elif liquidity_score > 0.4:
                liquidity_regime = "low_liquidity"
            else:
                liquidity_regime = "illiquid"

            return {
                "liquidity_score": liquidity_score,
                "liquidity_regime": liquidity_regime,
                "volume_ratio": volume_ratio,
                "average_range": avg_range if "avg_range" in locals() else 0.0,
                "liquidity_trend": self._assess_liquidity_trend(volume, volume_ma),
            }

        except Exception as e:
            logger.error(f"Liquidity conditions analysis failed: {e}")
            return {"liquidity_score": 0.5, "liquidity_regime": "error"}

    def _calculate_market_stress_indicators(
        self, price_data: pd.DataFrame, external_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """市場ストレス指標計算"""
        try:
            stress_indicators = {}
            total_stress = 0.0
            stress_components = 0

            # 1. 価格ボラティリティストレス
            if len(price_data) >= 20:
                returns = price_data["close"].pct_change().dropna()
                vol_stress = min(
                    returns.rolling(20).std().iloc[-1] * np.sqrt(365) / 0.05, 1.0
                )
                stress_indicators["volatility_stress"] = vol_stress
                total_stress += vol_stress
                stress_components += 1

            # 2. VIXストレス
            if external_data and "vix_level" in external_data:
                vix = external_data["vix_level"]
                vix_stress = min(max(vix - 15, 0) / 25, 1.0)  # 15-40の範囲で正規化
                stress_indicators["vix_stress"] = vix_stress
                total_stress += vix_stress
                stress_components += 1

            # 3. Fear&Greedストレス
            if external_data and "fear_greed" in external_data:
                fg = external_data["fear_greed"]
                # 極端な値（0-20, 80-100）でストレス高
                if fg <= 20:
                    fg_stress = (20 - fg) / 20
                elif fg >= 80:
                    fg_stress = (fg - 80) / 20
                else:
                    fg_stress = 0.0
                stress_indicators["sentiment_stress"] = fg_stress
                total_stress += fg_stress
                stress_components += 1

            # 4. 価格急変ストレス
            if len(price_data) >= 5:
                price_changes = price_data["close"].pct_change().abs()
                max_recent_change = price_changes.tail(5).max()
                change_stress = min(max_recent_change / 0.05, 1.0)  # 5%で満点
                stress_indicators["price_shock_stress"] = change_stress
                total_stress += change_stress
                stress_components += 1

            # 総合ストレスレベル
            if stress_components > 0:
                overall_stress = total_stress / stress_components
            else:
                overall_stress = 0.0

            # ストレスレベル分類
            if overall_stress > 0.8:
                stress_level = "extreme"
            elif overall_stress > 0.6:
                stress_level = "high"
            elif overall_stress > 0.4:
                stress_level = "medium"
            elif overall_stress > 0.2:
                stress_level = "low"
            else:
                stress_level = "minimal"

            if overall_stress > 0.6:
                self.analysis_stats["stress_detections"] += 1

            stress_indicators.update(
                {
                    "overall_stress": overall_stress,
                    "stress_level": stress_level,
                    "stress_components_count": stress_components,
                }
            )

            return stress_indicators

        except Exception as e:
            logger.error(f"Market stress calculation failed: {e}")
            return {"overall_stress": 0.5, "stress_level": "unknown"}

    def _calculate_prediction_adaptability(
        self, analysis_result: Dict[str, Any]
    ) -> float:
        """予測モデル適応性スコア計算"""
        try:
            adaptability_score = 0.0

            # 1. ボラティリティ適応性
            vol_regime = analysis_result.get("volatility_regime", "unknown")
            if vol_regime in ["normal", "normal_low"]:
                adaptability_score += 0.3  # 通常ボラティリティで高適応性
            elif vol_regime in ["calm", "extreme_calm"]:
                adaptability_score += 0.2  # 低ボラティリティでやや高適応性
            elif vol_regime in ["volatile"]:
                adaptability_score += 0.1  # 高ボラティリティで低適応性
            else:
                adaptability_score += 0.0  # 極端な状況で低適応性

            # 2. トレンド適応性
            trend_strength = analysis_result.get("trend_strength", 0.5)
            trend_stability = analysis_result.get("trend_stability", 0.5)
            trend_adaptability = (trend_strength + trend_stability) / 2 * 0.25
            adaptability_score += trend_adaptability

            # 3. 流動性適応性
            liquidity_score = analysis_result.get("liquidity_score", 0.5)
            liquidity_adaptability = liquidity_score * 0.2
            adaptability_score += liquidity_adaptability

            # 4. ストレス逆適応性
            stress_level = analysis_result.get("overall_stress", 0.5)
            stress_adaptability = (1.0 - stress_level) * 0.25
            adaptability_score += stress_adaptability

            return max(0.0, min(1.0, adaptability_score))

        except Exception as e:
            logger.error(f"Prediction adaptability calculation failed: {e}")
            return 0.5

    def _assess_trading_environment_quality(
        self, analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """取引環境品質評価"""
        try:
            # 各要素スコア収集
            vol_score = 1.0 - analysis_result.get(
                "volatility_score", 0.5
            )  # 低ボラほど高品質
            trend_score = analysis_result.get("trend_strength", 0.5)
            liquidity_score = analysis_result.get("liquidity_score", 0.5)
            stress_score = 1.0 - analysis_result.get(
                "overall_stress", 0.5
            )  # 低ストレスほど高品質

            # 重み付き総合評価
            trading_quality = (
                vol_score * 0.25
                + trend_score * 0.25
                + liquidity_score * 0.25
                + stress_score * 0.25
            )

            # 品質レベル分類
            if trading_quality > 0.8:
                quality_level = "excellent"
                recommended_risk = 1.0
            elif trading_quality > 0.6:
                quality_level = "good"
                recommended_risk = 0.8
            elif trading_quality > 0.4:
                quality_level = "fair"
                recommended_risk = 0.6
            elif trading_quality > 0.2:
                quality_level = "poor"
                recommended_risk = 0.4
            else:
                quality_level = "very_poor"
                recommended_risk = 0.2

            return {
                "trading_environment_quality": trading_quality,
                "quality_level": quality_level,
                "recommended_risk_level": recommended_risk,
                "quality_components": {
                    "volatility": vol_score,
                    "trend": trend_score,
                    "liquidity": liquidity_score,
                    "stress": stress_score,
                },
            }

        except Exception as e:
            logger.error(f"Trading environment assessment failed: {e}")
            return {
                "trading_environment_quality": 0.5,
                "quality_level": "unknown",
                "recommended_risk_level": 0.5,
            }

    def _calculate_volatility_percentile(
        self, returns: pd.Series, current_vol: float
    ) -> float:
        """ボラティリティ百分位数計算"""
        try:
            if len(returns) < 60:  # 最低60日
                return 0.5

            # 過去の実現ボラティリティ計算
            rolling_vols = returns.rolling(20).std() * np.sqrt(365)
            rolling_vols = rolling_vols.dropna()

            if len(rolling_vols) == 0:
                return 0.5

            # 百分位数計算
            percentile = (rolling_vols < current_vol).mean()
            return percentile

        except Exception as e:
            logger.error(f"Volatility percentile calculation failed: {e}")
            return 0.5

    def _calculate_ma_alignment_score(
        self, price: float, ma_10: float, ma_20: float, ma_50: float
    ) -> float:
        """移動平均整列スコア計算"""
        try:
            # 理想的な上昇トレンド: price > ma_10 > ma_20 > ma_50
            # 理想的な下降トレンド: price < ma_10 < ma_20 < ma_50

            if price > ma_10 > ma_20 > ma_50:  # 完璧な上昇整列
                return 1.0
            elif price < ma_10 < ma_20 < ma_50:  # 完璧な下降整列
                return 1.0
            elif price > ma_10 > ma_20:  # 短期上昇整列
                return 0.7
            elif price < ma_10 < ma_20:  # 短期下降整列
                return 0.7
            elif price > ma_20:  # 中期上昇
                return 0.5
            elif price < ma_20:  # 中期下降
                return 0.5
            else:  # 混乱状態
                return 0.2

        except Exception as e:
            logger.error(f"MA alignment score calculation failed: {e}")
            return 0.5

    def _assess_liquidity_trend(self, volume: pd.Series, volume_ma: pd.Series) -> str:
        """流動性トレンド評価"""
        try:
            if len(volume_ma) < 5:
                return "unknown"

            recent_ma = volume_ma.tail(5)
            if recent_ma.iloc[-1] > recent_ma.iloc[0] * 1.1:
                return "improving"
            elif recent_ma.iloc[-1] < recent_ma.iloc[0] * 0.9:
                return "deteriorating"
            else:
                return "stable"

        except Exception as e:
            logger.error(f"Liquidity trend assessment failed: {e}")
            return "unknown"

    def _update_analysis_state(self, analysis_result: Dict[str, Any]):
        """分析状態更新"""
        try:
            new_regime = analysis_result.get("market_regime", "unknown")
            new_vol_regime = analysis_result.get("volatility_regime", "unknown")

            # レジーム変化検出
            if new_regime != self.current_regime:
                self.analysis_stats["regime_changes"] += 1
                logger.info(
                    f"🔄 Market regime change: {self.current_regime} → {new_regime}"
                )

            if new_vol_regime != self.current_volatility_regime:
                self.analysis_stats["volatility_regime_changes"] += 1
                logger.info(
                    f"🔄 Volatility regime change: {self.current_volatility_regime} → {new_vol_regime}"
                )

            # 状態更新
            self.current_regime = new_regime
            self.current_volatility_regime = new_vol_regime
            self.current_liquidity_score = analysis_result.get("liquidity_score", 0.5)
            self.last_analysis_time = datetime.now()

        except Exception as e:
            logger.error(f"Analysis state update failed: {e}")

    def _record_analysis(self, analysis_result: Dict[str, Any]):
        """分析履歴記録"""
        try:
            # 履歴記録
            self.analysis_history.append(analysis_result.copy())

            # レジーム履歴記録
            regime_record = {
                "timestamp": analysis_result["timestamp"],
                "market_regime": analysis_result.get("market_regime", "unknown"),
                "volatility_regime": analysis_result.get(
                    "volatility_regime", "unknown"
                ),
                "stress_level": analysis_result.get("stress_level", "unknown"),
            }
            self.regime_history.append(regime_record)

            # 履歴サイズ制限
            if len(self.analysis_history) > self.max_history_size:
                self.analysis_history.pop(0)
            if len(self.regime_history) > self.max_history_size:
                self.regime_history.pop(0)

        except Exception as e:
            logger.error(f"Analysis recording failed: {e}")

    def _create_fallback_analysis(self) -> Dict[str, Any]:
        """フォールバック分析結果作成"""
        return {
            "timestamp": datetime.now(),
            "analysis_version": "phase_c2_fallback",
            "market_regime": "unknown",
            "volatility_regime": "unknown",
            "volatility_score": 0.5,
            "trend_strength": 0.5,
            "trend_direction": "unknown",
            "liquidity_score": 0.5,
            "liquidity_regime": "unknown",
            "overall_stress": 0.5,
            "stress_level": "unknown",
            "prediction_adaptability": 0.5,
            "trading_environment_quality": 0.5,
            "quality_level": "unknown",
            "recommended_risk_level": 0.5,
            "error": True,
        }

    def get_current_market_state(self) -> Dict[str, Any]:
        """現在の市場状態取得"""
        return {
            "current_regime": self.current_regime,
            "current_volatility_regime": self.current_volatility_regime,
            "current_liquidity_score": self.current_liquidity_score,
            "last_analysis_time": self.last_analysis_time,
            "analysis_stats": self.analysis_stats.copy(),
        }

    def get_regime_history(self, lookback_periods: int = 50) -> List[Dict[str, Any]]:
        """レジーム履歴取得"""
        return self.regime_history[-lookback_periods:] if self.regime_history else []

    def calculate_market_adaptation_weights(
        self, analysis_result: Dict[str, Any]
    ) -> Dict[str, float]:
        """市場適応重み計算（Phase C2統合用）"""
        try:
            # 基本重み調整係数
            regime = analysis_result.get("market_regime", "normal")
            stress_level = analysis_result.get("overall_stress", 0.5)
            adaptability = analysis_result.get("prediction_adaptability", 0.5)

            # レジーム別重み調整
            if regime in ["crisis", "extreme_volatile"]:
                # 危機時：長期重視・短期抑制
                weight_adjustments = {
                    "15m": 0.7,  # 短期抑制
                    "1h": 1.0,  # 維持
                    "4h": 1.3,  # 長期重視
                }
            elif regime in ["volatile", "high_volatile"]:
                # 高ボラ時：中期重視
                weight_adjustments = {
                    "15m": 0.8,
                    "1h": 1.2,
                    "4h": 1.0,
                }
            elif regime in ["calm", "extreme_calm"]:
                # 安定時：短期重視
                weight_adjustments = {
                    "15m": 1.2,
                    "1h": 1.0,
                    "4h": 0.8,
                }
            elif regime in ["bullish", "bearish"]:
                # トレンド時：中長期重視
                weight_adjustments = {
                    "15m": 0.9,
                    "1h": 1.1,
                    "4h": 1.1,
                }
            else:
                # 通常時：バランス維持
                weight_adjustments = {
                    "15m": 1.0,
                    "1h": 1.0,
                    "4h": 1.0,
                }

            # ストレス・適応性調整
            stress_factor = 1.0 - (stress_level * 0.2)  # 高ストレス時は全体的に保守的
            adaptability_factor = 0.8 + (adaptability * 0.4)  # 適応性による微調整

            final_weights = {}
            for timeframe, adjustment in weight_adjustments.items():
                final_weights[timeframe] = (
                    adjustment * stress_factor * adaptability_factor
                )

            return final_weights

        except Exception as e:
            logger.error(f"Market adaptation weights calculation failed: {e}")
            return {"15m": 1.0, "1h": 1.0, "4h": 1.0}

    def reset_statistics(self):
        """統計リセット"""
        for key in self.analysis_stats:
            self.analysis_stats[key] = 0
        self.analysis_history.clear()
        self.regime_history.clear()
        self.current_regime = "unknown"
        self.current_volatility_regime = "unknown"
        self.current_liquidity_score = 0.5
        logger.info("📊 Market environment analyzer statistics reset")


# ファクトリー関数


def create_market_environment_analyzer(
    config: Dict[str, Any],
) -> MarketEnvironmentAnalyzer:
    """
    市場環境解析システム作成

    Parameters:
    -----------
    config : Dict[str, Any]
        設定辞書

    Returns:
    --------
    MarketEnvironmentAnalyzer
        初期化済み市場環境解析システム
    """
    return MarketEnvironmentAnalyzer(config)

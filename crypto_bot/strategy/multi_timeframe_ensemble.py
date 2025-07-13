# =============================================================================
# ファイル名: crypto_bot/strategy/multi_timeframe_ensemble.py
# 説明:
# マルチタイムフレーム × アンサンブル学習統合戦略
# 15分足・1時間足・4時間足のアンサンブル統合で勝率向上を実現
# =============================================================================

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from crypto_bot.execution.engine import Position, Signal
from crypto_bot.strategy.base import StrategyBase
from crypto_bot.strategy.ensemble_ml_strategy import EnsembleMLStrategy

logger = logging.getLogger(__name__)


class MultiTimeframeEnsembleStrategy(StrategyBase):
    """
    マルチタイムフレーム × アンサンブル学習統合戦略

    各タイムフレームでアンサンブル学習を適用し、
    さらにタイムフレーム間でもアンサンブル統合を行う2段階アンサンブル
    """

    def __init__(self, config: dict):
        super().__init__()
        self.config = config

        # タイムフレーム設定
        multi_config = config.get("multi_timeframe", {})
        self.timeframes = multi_config.get("timeframes", ["15m", "1h", "4h"])
        self.weights = multi_config.get("weights", [0.3, 0.5, 0.2])

        # アンサンブル統合設定
        ensemble_config = config.get("ml", {}).get("ensemble", {})
        self.ensemble_enabled = ensemble_config.get("enabled", True)
        self.ensemble_method = ensemble_config.get("method", "trading_stacking")
        self.confidence_threshold = ensemble_config.get("confidence_threshold", 0.65)

        # 各タイムフレーム用のアンサンブル戦略
        self.ensemble_strategies = {}
        self._initialize_ensemble_strategies()

        # キャッシュとパフォーマンス追跡
        self.data_cache = {}
        self.cache_timeout = timedelta(minutes=3)
        self.last_cache_time = {}
        self.prediction_history = []
        self.timeframe_performance = {}

        logger.info(
            f"Initialized Multi-Timeframe Ensemble Strategy: {self.timeframes} "
            f"with weights {self.weights}"
        )

    def _initialize_ensemble_strategies(self):
        """各タイムフレーム用のアンサンブル戦略初期化"""

        for timeframe in self.timeframes:
            # タイムフレーム別設定作成
            tf_config = self._create_timeframe_config(timeframe)

            try:
                # アンサンブルML戦略作成
                strategy = EnsembleMLStrategy(
                    model_path=None,  # アンサンブルモードでは不要
                    threshold=None,
                    config=tf_config,
                )

                self.ensemble_strategies[timeframe] = strategy
                logger.info(f"Created ensemble strategy for {timeframe}")

            except Exception as e:
                logger.error(f"Failed to create ensemble strategy for {timeframe}: {e}")
                # フォールバック: 基本設定
                self.ensemble_strategies[timeframe] = None

    def _create_timeframe_config(self, timeframe: str) -> Dict:
        """タイムフレーム別設定作成"""
        tf_config = self.config.copy()

        # データ設定更新
        if "data" not in tf_config:
            tf_config["data"] = {
                "exchange": "csv",
                "csv_path": ("/Users/nao/Desktop/bot/data/btc_usd_2024_hourly.csv"),
                "symbol": "BTC/USDT",
            }

        tf_config["data"]["timeframe"] = timeframe

        # タイムフレーム別特徴量調整
        if "ml" not in tf_config:
            tf_config["ml"] = {}

        # アンサンブル設定（全タイムフレームで有効）
        if "ensemble" not in tf_config["ml"]:
            tf_config["ml"]["ensemble"] = {
                "enabled": True,
                "method": "trading_stacking",
                "confidence_threshold": 0.65,
                "risk_adjustment": True,
            }

        # タイムフレーム別特徴量最適化
        if timeframe == "15m":
            # 15分足: 高頻度・軽量特徴量
            tf_config["ml"]["extra_features"] = [
                "rsi_14",
                "rsi_7",
                "macd",
                "bb_percent",
                "volume_zscore",
                "vix",
                "momentum_14",
                "day_of_week",
                "hour_of_day",
                "price_change_1h",
                "volatility_1h",
                "breakout_signal",
            ]
            tf_config["ml"]["feat_period"] = 7
            # 15分足用アンサンブル設定
            tf_config["ml"]["ensemble"]["confidence_threshold"] = 0.6  # より積極的

        elif timeframe == "4h":
            # 4時間足: トレンド確認・長期特徴量
            tf_config["ml"]["extra_features"] = [
                "sma_200",
                "sma_50",
                "ema_50",
                "adx",
                "dxy",
                "fear_greed",
                "trend_strength",
                "bb_width",
                "cmf",
                "support_resistance",
                "fibonacci_level",
                "central_bank_policy",
                "macro_regime",
            ]
            tf_config["ml"]["feat_period"] = 21
            # 4時間足用アンサンブル設定
            tf_config["ml"]["ensemble"]["confidence_threshold"] = 0.7  # より保守的

        else:  # 1h (デフォルト)
            # 1時間足: 101特徴量フルセット
            tf_config["ml"]["extra_features"] = self._get_full_feature_set()
            tf_config["ml"]["feat_period"] = 14
            # 1時間足用アンサンブル設定（バランス型）
            tf_config["ml"]["ensemble"]["confidence_threshold"] = 0.65

        return tf_config

    def _get_full_feature_set(self) -> List[str]:
        """101特徴量フルセット取得"""
        return [
            # VIX恐怖指数（6特徴量）
            "vix",
            "vix_change",
            "vix_zscore",
            "vix_spike",
            "fear_level",
            "volatility_regime",
            # DXY・金利（10特徴量）
            "dxy",
            "dxy_change",
            "us_10y",
            "yield_curve",
            "real_rates",
            "dollar_strength",
            "fed_funds_rate",
            "treasury_volatility",
            "currency_momentum",
            "rate_expectations",
            # Fear&Greed（13特徴量）
            "fear_greed",
            "fear_greed_ma",
            "fear_greed_change",
            "extreme_fear",
            "extreme_greed",
            "sentiment_regime",
            "sentiment_divergence",
            "social_sentiment",
            "options_sentiment",
            "momentum_sentiment",
            "volume_sentiment",
            "breadth_sentiment",
            "volatility_sentiment",
            # Funding Rate・OI（17特徴量）
            "funding",
            "funding_ma",
            "funding_change",
            "funding_extreme",
            "oi_change",
            "oi_volume_ratio",
            "leverage_ratio",
            "long_short_ratio",
            "liquidation_risk",
            "perpetual_basis",
            "futures_basis",
            "options_flow",
            "institutional_flow",
            "retail_sentiment",
            "whale_activity",
            "exchange_flows",
            "stablecoin_flows",
            # 基本テクニカル（20特徴量）
            "rsi_14",
            "rsi_7",
            "rsi_21",
            "macd",
            "macd_signal",
            "macd_histogram",
            "bb_percent",
            "bb_width",
            "sma_20",
            "sma_50",
            "sma_200",
            "ema_12",
            "ema_26",
            "ema_50",
            "adx",
            "cci",
            "williams_r",
            "stoch_k",
            "stoch_d",
            "momentum_14",
            # その他重要特徴量（35特徴量）
            "day_of_week",
            "hour_of_day",
            "mochipoyo_long_signal",
            "mochipoyo_short_signal",
            "price_change_1h",
            "price_change_4h",
            "price_change_24h",
            "volume_change_1h",
            "volume_change_24h",
            "volume_zscore",
            "volatility_1h",
            "volatility_24h",
            "support_resistance",
            "trend_strength",
            "breakout_signal",
            "reversal_signal",
            "fibonacci_level",
            "pivot_points",
            "bollinger_squeeze",
            "volume_profile",
            "order_flow",
            "market_microstructure",
            "cross_asset_correlation",
            "sector_rotation",
            "macro_regime",
            "central_bank_policy",
            "economic_surprises",
            "earnings_season",
            "options_expiry",
            "futures_rollover",
            "seasonal_patterns",
            "anomaly_detection",
            "regime_change",
            "tail_risk",
            "skewness",
        ]

    def logic_signal(self, price_df: pd.DataFrame, position: Position) -> Signal:
        """
        マルチタイムフレーム × アンサンブル統合シグナル生成

        2段階アンサンブル:
        1. 各タイムフレームでアンサンブル学習
        2. タイムフレーム間でアンサンブル統合
        """
        try:
            logger.debug("Multi-Timeframe Ensemble: Generating integrated signal")

            # 各タイムフレームのアンサンブル予測取得
            timeframe_predictions = self._get_timeframe_ensemble_predictions(price_df)

            if not timeframe_predictions:
                logger.warning("No timeframe predictions available")
                return Signal()

            # 統合シグナル計算
            integrated_signal, signal_info = self._integrate_ensemble_signals(
                timeframe_predictions, position
            )

            # シグナル判定
            final_signal = self._make_final_signal_decision(
                integrated_signal, signal_info, price_df, position
            )

            # パフォーマンス追跡
            self._track_prediction_performance(
                timeframe_predictions, integrated_signal, signal_info
            )

            return final_signal

        except Exception as e:
            logger.error(f"Multi-timeframe ensemble signal generation failed: {e}")
            return Signal()

    def _get_timeframe_ensemble_predictions(
        self, price_df: pd.DataFrame
    ) -> Dict[str, Dict]:
        """各タイムフレームのアンサンブル予測取得"""
        predictions = {}

        for timeframe in self.timeframes:
            try:
                # タイムフレーム別データ取得
                tf_data = self._get_timeframe_data(price_df, timeframe)

                if tf_data.empty:
                    logger.warning(f"No data available for {timeframe}")
                    continue

                strategy = self.ensemble_strategies.get(timeframe)
                if strategy is None:
                    logger.warning(f"No strategy available for {timeframe}")
                    continue

                # ダミーポジションでアンサンブル予測取得
                dummy_position = Position()
                dummy_position.exist = False

                # アンサンブル戦略でシグナル生成
                signal = strategy.logic_signal(tf_data, dummy_position)

                # アンサンブル詳細情報取得
                ensemble_info = strategy.get_ensemble_performance_info()

                predictions[timeframe] = {
                    "signal": signal,
                    "ensemble_info": ensemble_info,
                    "data_quality": self._assess_data_quality(tf_data),
                }

                logger.debug(f"Got ensemble prediction for {timeframe}: {signal.side}")

            except Exception as e:
                logger.error(f"Failed to get ensemble prediction for {timeframe}: {e}")
                continue

        return predictions

    def _get_timeframe_data(
        self, price_df: pd.DataFrame, timeframe: str
    ) -> pd.DataFrame:
        """タイムフレーム別データ生成（キャッシュ活用）"""
        cache_key = f"{timeframe}_data"
        current_time = datetime.now()

        # キャッシュチェック
        if (
            cache_key in self.data_cache
            and cache_key in self.last_cache_time
            and current_time - self.last_cache_time[cache_key] < self.cache_timeout
        ):
            return self.data_cache[cache_key]

        try:
            # タイムフレーム変換
            if timeframe == "15m":
                # 1時間足から15分足に補間
                tf_data = price_df.resample("15T").interpolate(method="linear")
            elif timeframe == "4h":
                # 1時間足から4時間足に集約
                tf_data = price_df.resample("4h").agg(
                    {
                        "open": "first",
                        "high": "max",
                        "low": "min",
                        "close": "last",
                        "volume": "sum",
                    }
                )
            else:  # 1h
                tf_data = price_df.copy()

            # データ品質チェック
            if len(tf_data) < 50:  # 最小データ要件
                logger.warning(
                    f"Insufficient data for {timeframe}: {len(tf_data)} rows"
                )
                return pd.DataFrame()

            # キャッシュ更新
            self.data_cache[cache_key] = tf_data
            self.last_cache_time[cache_key] = current_time

            return tf_data

        except Exception as e:
            logger.error(f"Failed to generate {timeframe} data: {e}")
            return pd.DataFrame()

    def _assess_data_quality(self, data: pd.DataFrame) -> Dict[str, float]:
        """データ品質評価"""
        if data.empty:
            return {"quality_score": 0.0}

        try:
            # 基本品質指標
            total_cells = len(data) * len(data.columns)
            null_cells = data.isnull().sum().sum()
            completeness = 1.0 - (null_cells / total_cells)
            data_length_score = min(len(data) / 100.0, 1.0)  # 100行以上で満点

            # 価格データの妥当性
            price_validity = 1.0
            if "close" in data.columns:
                price_changes = data["close"].pct_change().abs()
                extreme_changes = (price_changes > 0.1).sum()  # 10%以上の変化
                if len(data) > 0:
                    price_validity = 1.0 - (extreme_changes / len(data))

            quality_score = (
                completeness * 0.4 + data_length_score * 0.3 + price_validity * 0.3
            )

            return {
                "quality_score": quality_score,
                "completeness": completeness,
                "data_length_score": data_length_score,
                "price_validity": price_validity,
            }

        except Exception as e:
            logger.error(f"Data quality assessment failed: {e}")
            return {"quality_score": 0.5}

    def _integrate_ensemble_signals(
        self, timeframe_predictions: Dict, position: Position
    ) -> Tuple[float, Dict]:
        """アンサンブルシグナル統合"""
        signal_values = []
        weights = []
        integration_info = {
            "timeframe_signals": {},
            "quality_weights": {},
            "ensemble_confidence": {},
            "method": "quality_weighted_ensemble",
        }

        for i, timeframe in enumerate(self.timeframes):
            if timeframe not in timeframe_predictions:
                continue

            prediction = timeframe_predictions[timeframe]
            signal = prediction["signal"]
            data_quality = prediction["data_quality"]
            ensemble_info = prediction["ensemble_info"]

            # シグナル値変換
            if signal.side == "BUY":
                signal_value = 0.75
            elif signal.side == "SELL":
                signal_value = 0.25
            else:
                signal_value = 0.5

            # 品質調整重み計算
            base_weight = self.weights[i] if i < len(self.weights) else 0.1
            quality_score = data_quality.get("quality_score", 0.5)
            ensemble_confidence = ensemble_info.get("average_confidence", 0.5)

            # 統合重み（基本重み × データ品質 × アンサンブル信頼度）
            adjusted_weight = base_weight * quality_score * ensemble_confidence

            signal_values.append(signal_value)
            weights.append(adjusted_weight)

            # 詳細情報記録
            integration_info["timeframe_signals"][timeframe] = signal_value
            integration_info["quality_weights"][timeframe] = adjusted_weight
            integration_info["ensemble_confidence"][timeframe] = ensemble_confidence

        # 重み付き統合計算
        if signal_values and sum(weights) > 0:
            weighted_sum = sum(s * w for s, w in zip(signal_values, weights))
            integrated_signal = weighted_sum / sum(weights)
        else:
            integrated_signal = 0.5  # ニュートラル

        integration_info["integrated_signal"] = integrated_signal
        integration_info["total_weight"] = sum(weights)
        integration_info["signal_consensus"] = self._calculate_consensus(signal_values)

        return integrated_signal, integration_info

    def _calculate_consensus(self, signal_values: List[float]) -> float:
        """シグナル合意度計算"""
        if len(signal_values) < 2:
            return 1.0

        # 標準偏差ベースの合意度（低分散 = 高合意度）
        std_dev = np.std(signal_values)
        max_std = 0.25  # 最大想定標準偏差
        consensus = 1.0 - min(std_dev / max_std, 1.0)

        return consensus

    def _make_final_signal_decision(
        self,
        integrated_signal: float,
        signal_info: Dict,
        price_df: pd.DataFrame,
        position: Position,
    ) -> Signal:
        """最終シグナル判定"""
        if not price_df.empty:
            current_price = float(price_df["close"].iloc[-1])
        else:
            current_price = None

        if current_price is None:
            return Signal()

        # 動的閾値計算
        dynamic_threshold = self._calculate_multi_timeframe_threshold(signal_info)

        # 合意度チェック
        consensus = signal_info.get("signal_consensus", 0.0)
        min_consensus = 0.6  # 最低合意度要件

        position_exists = position is not None and position.exist

        if position_exists:
            # エグジット判定
            exit_threshold = (
                0.4 + (1.0 - consensus) * 0.1
            )  # 低合意度では早めにエグジット

            if integrated_signal < exit_threshold:
                logger.info(
                    f"Multi-timeframe ensemble EXIT: "
                    f"signal={integrated_signal:.3f} < {exit_threshold:.3f}"
                )
                return Signal(side="SELL", price=current_price)

            return Signal()  # ホールド

        else:
            # エントリー判定
            if (
                integrated_signal > (0.5 + dynamic_threshold)
                and consensus >= min_consensus
            ):
                logger.info(
                    f"Multi-timeframe ensemble LONG: signal={integrated_signal:.3f}, "
                    f"consensus={consensus:.3f}"
                )
                return Signal(side="BUY", price=current_price)

            elif (
                integrated_signal < (0.5 - dynamic_threshold)
                and consensus >= min_consensus
            ):
                logger.info(
                    f"Multi-timeframe ensemble SHORT: signal={integrated_signal:.3f}, "
                    f"consensus={consensus:.3f}"
                )
                return Signal(side="SELL", price=current_price)

            return Signal()  # ホールド

    def _calculate_multi_timeframe_threshold(self, signal_info: Dict) -> float:
        """マルチタイムフレーム動的閾値計算"""
        base_threshold = self.confidence_threshold - 0.5  # 基本閾値調整

        # 総合品質スコア
        total_weight = signal_info.get("total_weight", 1.0)
        quality_adjustment = min(total_weight, 1.0) * 0.05  # 高品質ほど積極的

        # 合意度調整
        consensus = signal_info.get("signal_consensus", 0.5)
        consensus_adjustment = (consensus - 0.5) * 0.1  # 高合意度ほど積極的

        dynamic_threshold = base_threshold - quality_adjustment - consensus_adjustment

        return max(0.05, min(0.2, dynamic_threshold))  # 範囲制限

    def _track_prediction_performance(
        self, timeframe_predictions: Dict, integrated_signal: float, signal_info: Dict
    ):
        """予測パフォーマンス追跡"""
        prediction_record = {
            "timestamp": datetime.now(),
            "timeframe_predictions": timeframe_predictions,
            "integrated_signal": integrated_signal,
            "signal_info": signal_info,
        }

        self.prediction_history.append(prediction_record)

        # 履歴サイズ制限
        if len(self.prediction_history) > 100:
            self.prediction_history.pop(0)

    def get_multi_ensemble_info(self) -> Dict:
        """マルチタイムフレーム×アンサンブル統合情報取得"""
        try:
            info = {
                "strategy_type": "multi_timeframe_ensemble",
                "timeframes": self.timeframes,
                "weights": self.weights,
                "ensemble_enabled": self.ensemble_enabled,
                "confidence_threshold": self.confidence_threshold,
                "prediction_history_size": len(self.prediction_history),
                "timeframe_strategies": {},
            }

            # 各タイムフレームのアンサンブル情報
            for timeframe, strategy in self.ensemble_strategies.items():
                if strategy:
                    try:
                        tf_info = strategy.get_ensemble_performance_info()
                        info["timeframe_strategies"][timeframe] = tf_info
                    except Exception as e:
                        info["timeframe_strategies"][timeframe] = {"error": str(e)}
                else:
                    info["timeframe_strategies"][timeframe] = {
                        "status": "not_available"
                    }

            # 最近のパフォーマンス統計
            if self.prediction_history:
                recent_predictions = self.prediction_history[-10:]
                info["recent_performance"] = self._analyze_recent_performance(
                    recent_predictions
                )

            return info

        except Exception as e:
            logger.error(f"Failed to get multi-ensemble info: {e}")
            return {"error": str(e)}

    def _analyze_recent_performance(self, recent_predictions: List[Dict]) -> Dict:
        """最近のパフォーマンス分析"""
        try:
            integrated_signals = [p["integrated_signal"] for p in recent_predictions]
            consensus_scores = [
                p["signal_info"].get("signal_consensus", 0.5)
                for p in recent_predictions
            ]

            return {
                "avg_integrated_signal": np.mean(integrated_signals),
                "signal_volatility": np.std(integrated_signals),
                "avg_consensus": np.mean(consensus_scores),
                "consensus_stability": np.std(consensus_scores),
                "prediction_count": len(recent_predictions),
            }

        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")
            return {}

# =============================================================================
# ファイル名: crypto_bot/strategy/multi_timeframe_ensemble_strategy.py
# 説明:
# Phase C1: 2段階アンサンブル統合戦略（完全版）
# 既存multi_timeframe_ensemble.py改良・Phase B基盤統合・Phase C1モジュール統合
# タイムフレーム内×タイムフレーム間の2段階アンサンブル学習完全実装
# =============================================================================

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from crypto_bot.data.multi_timeframe_fetcher import MultiTimeframeDataFetcher
from crypto_bot.execution.engine import Position, Signal
from crypto_bot.ml.cross_timeframe_ensemble import create_cross_timeframe_integrator
from crypto_bot.ml.preprocessor import FeatureEngineer
from crypto_bot.ml.timeframe_ensemble import (
    TimeframeEnsembleProcessor,
    create_timeframe_ensemble_processor,
)
from crypto_bot.strategy.base import StrategyBase
from crypto_bot.utils.ensemble_confidence import EnsembleConfidenceCalculator

# Phase B基盤統合
try:
    from crypto_bot.feature_engineering.batch_feature_calculator import (
        BatchFeatureCalculator,
    )
    from crypto_bot.feature_engineering.external_data_integrator import (
        ExternalDataIntegrator,
    )
    from crypto_bot.feature_engineering.technical_feature_engine import (
        TechnicalFeatureEngine,
    )

    PHASE_B_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("🚀 Phase B基盤モジュール統合成功")
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠️ Phase B基盤モジュール未利用: {e}")
    PHASE_B_AVAILABLE = False

logger = logging.getLogger(__name__)


class MultiTimeframeEnsembleStrategy(StrategyBase):
    """
    Phase C1: 2段階アンサンブル統合戦略

    統合機能:
    - Stage 1: タイムフレーム内アンサンブル（15m/1h/4h各々で複数モデル統合）
    - Stage 2: タイムフレーム間アンサンブル（3タイムフレーム予測の重み付き統合）
    - Phase B基盤統合: BatchFeatureCalculator・TechnicalFeatureEngine・ExternalDataIntegrator
    - Phase C1統合: 統一信頼度計算・動的重み調整・市場環境適応
    - 151特徴量システム完全対応・パフォーマンス最適化
    """

    def __init__(self, config: dict):
        """
        2段階アンサンブル戦略初期化

        Parameters:
        -----------
        config : dict
            戦略設定辞書（マルチタイムフレーム・アンサンブル・Phase B設定含む）
        """
        super().__init__()
        self.config = config

        # マルチタイムフレーム設定
        multi_config = config.get("multi_timeframe", {})
        self.timeframes = multi_config.get("timeframes", ["15m", "1h", "4h"])
        self.base_weights = multi_config.get("weights", [0.3, 0.5, 0.2])
        self.base_timeframe = multi_config.get("base_timeframe", "1h")
        self.data_quality_threshold = multi_config.get("data_quality_threshold", 0.9)

        logger.info(
            f"🔧 Strategy data quality threshold set to: {self.data_quality_threshold}"
        )

        # アンサンブル設定
        ensemble_config = config.get("ml", {}).get("ensemble", {})
        self.ensemble_enabled = ensemble_config.get("enabled", True)
        self.ensemble_method = ensemble_config.get("method", "trading_stacking")
        self.confidence_threshold = ensemble_config.get("confidence_threshold", 0.65)

        # Phase C1統合: 新モジュール初期化
        self.confidence_calculator = EnsembleConfidenceCalculator(config)
        self.cross_timeframe_integrator = create_cross_timeframe_integrator(config)

        # タイムフレーム内アンサンブルプロセッサー辞書
        self.timeframe_processors: Dict[str, TimeframeEnsembleProcessor] = {}

        # Phase B基盤統合初期化
        if PHASE_B_AVAILABLE:
            self._initialize_phase_b_components()
        else:
            # フォールバック: 従来方式
            self.feature_engineer = FeatureEngineer(config)
            self.batch_processor = None

        # マルチタイムフレームデータフェッチャー
        self.multi_timeframe_fetcher: Optional[MultiTimeframeDataFetcher] = None
        self._base_fetcher = None

        # 統合キャッシュ・パフォーマンス管理
        self.data_cache = {}
        self.prediction_cache = {}
        self.cache_timeout = timedelta(minutes=3)
        self.last_cache_time = {}

        # 統計・パフォーマンス追跡
        self.strategy_stats = {
            "total_predictions": 0,
            "stage1_ensemble_predictions": 0,
            "stage2_integration_predictions": 0,
            "phase_b_batch_processing": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "high_confidence_signals": 0,
            "low_confidence_rejections": 0,
        }

        # 履歴管理
        self.prediction_history: List[Dict] = []
        self.performance_history: List[Dict] = []
        self.max_history_size = 100

        logger.info("🚀 MultiTimeframeEnsembleStrategy (Phase C1) initialized")
        logger.info(f"   Timeframes: {self.timeframes}")
        logger.info(f"   Base weights: {self.base_weights}")
        logger.info(f"   Ensemble method: {self.ensemble_method}")
        logger.info(f"   Phase B integration: {PHASE_B_AVAILABLE}")

    def _initialize_phase_b_components(self):
        """Phase B基盤コンポーネント初期化"""
        try:
            # BatchFeatureCalculator初期化
            self.batch_calculator = BatchFeatureCalculator(self.config)

            # TechnicalFeatureEngine初期化
            self.technical_engine = TechnicalFeatureEngine(self.config)

            # ExternalDataIntegrator初期化
            self.external_integrator = ExternalDataIntegrator(self.config)

            # 統合特徴量エンジニアリング（Phase B統合版）
            self.feature_engineer = FeatureEngineer(self.config)

            logger.info("✅ Phase B基盤統合完了")
            self.phase_b_integrated = True

        except Exception as e:
            logger.error(f"❌ Phase B基盤統合失敗: {e}")
            logger.info("🔄 フォールバック: 従来方式使用")
            self.feature_engineer = FeatureEngineer(self.config)
            self.phase_b_integrated = False

    def _initialize_timeframe_processors(self):
        """タイムフレーム内アンサンブルプロセッサー初期化"""
        for timeframe in self.timeframes:
            try:
                # タイムフレーム特化設定作成
                tf_config = self._create_timeframe_specific_config(timeframe)

                # プロセッサー作成（Phase C1モジュール使用）
                processor = create_timeframe_ensemble_processor(
                    timeframe=timeframe,
                    config=tf_config,
                    feature_engineer=self.feature_engineer,  # Phase B統合特徴量エンジニアリング
                )

                self.timeframe_processors[timeframe] = processor
                logger.info(f"✅ {timeframe} ensemble processor created")

            except Exception as e:
                logger.error(f"❌ Failed to create {timeframe} processor: {e}")
                self.timeframe_processors[timeframe] = None

    def _create_timeframe_specific_config(self, timeframe: str) -> Dict:
        """タイムフレーム特化設定作成"""
        tf_config = self.config.copy()

        # データ設定更新
        if "data" not in tf_config:
            tf_config["data"] = {}
        tf_config["data"]["timeframe"] = timeframe

        # タイムフレーム別特徴量最適化
        if timeframe == "15m":
            # 15分足: 高頻度・軽量特徴量
            tf_config["ml"]["extra_features"] = self._get_short_term_features()
            tf_config["ml"]["feat_period"] = 7
            tf_config["ml"]["ensemble"]["confidence_threshold"] = 0.6  # より積極的

        elif timeframe == "4h":
            # 4時間足: トレンド確認・長期特徴量
            tf_config["ml"]["extra_features"] = self._get_long_term_features()
            tf_config["ml"]["feat_period"] = 21
            tf_config["ml"]["ensemble"]["confidence_threshold"] = 0.7  # より保守的

        else:  # 1h (デフォルト)
            # 1時間足: 151特徴量フルセット
            tf_config["ml"]["extra_features"] = self._get_full_feature_set()
            tf_config["ml"]["feat_period"] = 14
            tf_config["ml"]["ensemble"]["confidence_threshold"] = 0.65  # バランス型

        return tf_config

    def _get_short_term_features(self) -> List[str]:
        """短期取引用特徴量セット（15分足特化）"""
        return [
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
            "stoch",
            "willr",
            "adx",
            "cmf",
            "atr_7",
        ]

    def _get_long_term_features(self) -> List[str]:
        """長期トレンド用特徴量セット（4時間足特化）"""
        return [
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
            "vix",
            "funding",
            "cross_correlation",
            "regime_detection",
        ]

    def _get_full_feature_set(self) -> List[str]:
        """151特徴量フルセット（1時間足・メイン）"""
        # 既存multi_timeframe_ensemble.pyから抽出・Phase C1対応改良
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
            # Phase 3.2A-D高度特徴量（65特徴量）
            "price_position",
            "candle_patterns",
            "support_resistance",
            "breakout_signals",
            "autocorrelation",
            "seasonal_patterns",
            "regime_detection",
            "cycle_analysis",
            "cross_correlation",
            "relative_strength",
            "spread_analysis",
            "volatility_regime",
            "momentum_signals",
            "liquidity_indicators",
            # 時間・シグナル特徴量（20特徴量）
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
            "trend_strength",
            "breakout_signal",
            "reversal_signal",
            "fibonacci_level",
            "pivot_points",
            "bollinger_squeeze",
            "volume_profile",
            "order_flow",
        ]

    def set_data_fetcher(self, base_fetcher):
        """データフェッチャー設定・初期化"""
        try:
            self._base_fetcher = base_fetcher

            # MultiTimeframeDataFetcher初期化
            self.multi_timeframe_fetcher = MultiTimeframeDataFetcher(
                base_fetcher=base_fetcher,
                config=self.config,
                timeframes=self.timeframes,
                base_timeframe=self.base_timeframe,
                cache_enabled=True,
                data_quality_threshold=self.data_quality_threshold,
            )

            # タイムフレーム内プロセッサー初期化
            self._initialize_timeframe_processors()

            logger.info("✅ Multi-timeframe data fetcher & processors initialized")

        except Exception as e:
            logger.error(f"❌ Failed to initialize data fetcher: {e}")
            self.multi_timeframe_fetcher = None

    def fit_ensemble_models(self, price_df: pd.DataFrame, y: pd.Series):
        """全タイムフレームアンサンブルモデル学習"""
        if not self.timeframe_processors:
            logger.error("Timeframe processors not initialized")
            return

        logger.info("🎯 Training multi-timeframe ensemble models")
        logger.info(
            f"📊 Original data shape: {tuple(price_df.shape)}, label shape: {tuple(y.shape)}"
        )

        for timeframe, processor in self.timeframe_processors.items():
            if processor is None:
                continue

            try:
                # タイムフレーム別データ準備
                tf_data = self._get_timeframe_data(price_df, timeframe)
                if tf_data.empty:
                    logger.warning(f"No data for {timeframe} training")
                    continue

                logger.info(f"📊 {timeframe} data shape: {tuple(tf_data.shape)}")

                # タイムフレームに対応するラベルを生成
                tf_labels = self._generate_timeframe_labels(
                    tf_data, price_df, y, timeframe
                )

                if tf_labels is None or len(tf_labels) == 0:
                    logger.warning(f"⚠️ Failed to generate labels for {timeframe}")
                    continue

                logger.info(f"📊 {timeframe} labels shape: {tuple(tf_labels.shape)}")

                # データとラベルの長さを確認
                if len(tf_data) != len(tf_labels):
                    logger.error(
                        f"❌ {timeframe} data/label mismatch: data={len(tf_data)}, labels={len(tf_labels)}"
                    )
                    continue

                # アンサンブルモデル学習
                processor.fit(tf_data, tf_labels)
                logger.info(f"✅ {timeframe} ensemble model trained successfully")
                logger.info(f"   - Processor fitted: {processor.is_fitted}")

            except Exception as e:
                logger.error(f"❌ {timeframe} ensemble training failed: {e}")
                logger.error(f"   - Error type: {type(e).__name__}")
                logger.error(f"   - Error details: {str(e)}")

    def logic_signal(self, price_df: pd.DataFrame, position: Position) -> Signal:
        """
        Phase C1: 2段階アンサンブル統合シグナル生成

        Stage 1: タイムフレーム内アンサンブル（各15m/1h/4hで複数モデル統合）
        Stage 2: タイムフレーム間アンサンブル（3タイムフレーム予測重み付き統合）
        """
        self.strategy_stats["total_predictions"] += 1
        start_time = datetime.now()

        try:
            logger.info(
                "🚀 [LOGIC-SIGNAL] Phase C1: 2段階アンサンブル統合シグナル生成開始"
            )
            logger.info(
                f"📊 [LOGIC-SIGNAL] Input price_df shape: {tuple(price_df.shape)}"
            )
            logger.info(f"📊 [LOGIC-SIGNAL] Position exists: {position.exist}")

            # モデル状態の確認ログ
            logger.info("🔍 [LOGIC-SIGNAL] Checking ensemble model states...")
            if hasattr(self, "timeframe_processors"):
                for tf, processor in self.timeframe_processors.items():
                    if processor:
                        logger.info(
                            f"  - {tf} processor: fitted={processor.is_fitted}, enabled={processor.ensemble_enabled}"
                        )
                    else:
                        logger.warning(f"  - {tf} processor: NOT INITIALIZED")
            else:
                logger.error("❌ [LOGIC-SIGNAL] No timeframe processors found!")

            # 市場コンテキスト生成
            logger.info("🔄 [LOGIC-SIGNAL] Step 1: 市場コンテキスト生成開始")
            context_start = datetime.now()
            market_context = self._generate_market_context(price_df)
            context_elapsed = (datetime.now() - context_start).total_seconds()
            logger.info(
                f"✅ [LOGIC-SIGNAL] Step 1完了: 市場コンテキスト生成 ({context_elapsed:.2f}秒)"
            )
            logger.debug(f"📊 [LOGIC-SIGNAL] Market context: {market_context}")

            # Stage 1: タイムフレーム内アンサンブル予測実行
            logger.info(
                "🔄 [LOGIC-SIGNAL] Step 2: Stage 1 タイムフレーム内アンサンブル予測開始"
            )
            stage1_start = datetime.now()
            timeframe_predictions = self._execute_stage1_ensemble_predictions(
                price_df, market_context
            )
            stage1_elapsed = (datetime.now() - stage1_start).total_seconds()
            logger.info(
                f"✅ [LOGIC-SIGNAL] Step 2完了: Stage 1予測 ({stage1_elapsed:.2f}秒)"
            )
            logger.info(
                f"📊 [LOGIC-SIGNAL] Timeframe predictions count: {len(timeframe_predictions)}"
            )

            if not timeframe_predictions:
                logger.warning(
                    "⚠️ [LOGIC-SIGNAL] No Stage 1 predictions available - returning empty signal"
                )
                total_elapsed = (datetime.now() - start_time).total_seconds()
                logger.info(
                    f"🏁 [LOGIC-SIGNAL] 処理終了（空シグナル） - 総処理時間: {total_elapsed:.2f}秒"
                )
                return Signal()

            # Stage 2: タイムフレーム間アンサンブル統合
            logger.info(
                "🔄 [LOGIC-SIGNAL] Step 3: Stage 2 タイムフレーム間アンサンブル統合開始"
            )
            stage2_start = datetime.now()
            integrated_signal, integration_info = self._execute_stage2_integration(
                timeframe_predictions, market_context
            )
            stage2_elapsed = (datetime.now() - stage2_start).total_seconds()
            logger.info(
                f"✅ [LOGIC-SIGNAL] Step 3完了: Stage 2統合 ({stage2_elapsed:.2f}秒)"
            )
            # Phase H.20.1.1: numpy配列安全処理
            safe_signal = (
                float(integrated_signal)
                if hasattr(integrated_signal, "__len__")
                else float(integrated_signal)
            )
            logger.info(f"📊 [LOGIC-SIGNAL] Integrated signal: {safe_signal:.3f}")

            # 最終シグナル判定
            logger.info("🔄 [LOGIC-SIGNAL] Step 4: 最終シグナル判定開始")
            decision_start = datetime.now()
            final_signal = self._make_final_ensemble_decision(
                integrated_signal, integration_info, price_df, position
            )
            decision_elapsed = (datetime.now() - decision_start).total_seconds()
            logger.info(
                f"✅ [LOGIC-SIGNAL] Step 4完了: 最終判定 ({decision_elapsed:.2f}秒)"
            )
            logger.info(
                f"📊 [LOGIC-SIGNAL] Final signal: side={final_signal.side}, price={final_signal.price}"
            )

            # パフォーマンス追跡
            logger.info("🔄 [LOGIC-SIGNAL] Step 5: パフォーマンス追跡開始")
            track_start = datetime.now()
            self._track_ensemble_performance(
                timeframe_predictions, integrated_signal, integration_info, final_signal
            )
            track_elapsed = (datetime.now() - track_start).total_seconds()
            logger.info(
                f"✅ [LOGIC-SIGNAL] Step 5完了: パフォーマンス追跡 ({track_elapsed:.2f}秒)"
            )

            total_elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"🏁 [LOGIC-SIGNAL] 処理完了 - 総処理時間: {total_elapsed:.2f}秒"
            )
            return final_signal

        except Exception as e:
            total_elapsed = (datetime.now() - start_time).total_seconds()
            logger.error(f"❌ [LOGIC-SIGNAL] Phase C1 2段階アンサンブル失敗: {e}")
            logger.error(
                f"🏁 [LOGIC-SIGNAL] エラー終了 - 処理時間: {total_elapsed:.2f}秒"
            )
            import traceback

            logger.error(f"📋 [LOGIC-SIGNAL] Stack trace: {traceback.format_exc()}")
            return Signal()

    def _execute_stage1_ensemble_predictions(
        self, price_df: pd.DataFrame, market_context: Dict
    ) -> Dict[str, Dict]:
        """Stage 1: タイムフレーム内アンサンブル予測実行"""
        predictions = {}
        self.strategy_stats["stage1_ensemble_predictions"] += 1

        for timeframe in self.timeframes:
            try:
                processor = self.timeframe_processors.get(timeframe)
                if processor is None:
                    logger.warning(f"No processor for {timeframe}")
                    continue

                # タイムフレームデータ取得
                tf_data = self._get_timeframe_data(price_df, timeframe)
                if tf_data.empty:
                    logger.warning(f"No data for {timeframe}")
                    continue

                # Phase B基盤統合: バッチ処理実行
                if PHASE_B_AVAILABLE and hasattr(self, "batch_calculator"):
                    tf_data = self._apply_phase_b_processing(tf_data, timeframe)
                    self.strategy_stats["phase_b_batch_processing"] += 1

                # タイムフレーム内アンサンブル予測（Phase C1コア機能）
                pred_result, prob_result, conf_result, pred_info = (
                    processor.predict_with_confidence(tf_data, market_context)
                )

                predictions[timeframe] = {
                    "prediction": pred_result,
                    "probability": prob_result,
                    "confidence": conf_result,
                    "info": pred_info,
                }

                # Phase H.21.1: numpy配列format string修正（エントリーシグナル復活）
                safe_conf = (
                    float(conf_result[0])
                    if hasattr(conf_result[0], "__len__")
                    else float(conf_result[0])
                )
                logger.debug(f"✅ Stage 1 {timeframe}: conf={safe_conf:.3f}")

            except Exception as e:
                logger.error(f"❌ Stage 1 {timeframe} failed: {e}")
                continue

        return predictions

    def _apply_phase_b_processing(
        self, data: pd.DataFrame, timeframe: str
    ) -> pd.DataFrame:
        """Phase B基盤バッチ処理適用"""
        try:
            # TechnicalFeatureEngine適用
            technical_features = self.technical_engine.calculate_features(data)

            # ExternalDataIntegrator適用
            external_features = self.external_integrator.integrate_external_data(data)

            # BatchFeatureCalculator適用
            batch_result = self.batch_calculator.calculate_batch_features(
                {
                    "price_data": data,
                    "technical_features": technical_features,
                    "external_features": external_features,
                    "timeframe": timeframe,
                }
            )

            return batch_result.get("processed_data", data)

        except Exception as e:
            logger.error(f"Phase B processing failed for {timeframe}: {e}")
            return data

    def _execute_stage2_integration(
        self, timeframe_predictions: Dict, market_context: Dict
    ) -> Tuple[float, Dict]:
        """Stage 2: タイムフレーム間アンサンブル統合"""
        self.strategy_stats["stage2_integration_predictions"] += 1

        # Phase C1統合: CrossTimeframeIntegrator使用
        integrated_signal, integration_info = (
            self.cross_timeframe_integrator.integrate_timeframe_predictions(
                timeframe_predictions, market_context
            )
        )

        # Phase H.26: numpy配列のフォーマットエラー完全修正
        safe_signal = (
            float(integrated_signal.flat[0])
            if isinstance(integrated_signal, np.ndarray)
            else float(integrated_signal)
        )

        # consensus_scoreも安全に処理
        consensus_raw = integration_info.get("consensus_score", 0)
        safe_consensus = (
            float(consensus_raw.flat[0])
            if isinstance(consensus_raw, np.ndarray)
            else float(consensus_raw)
        )

        logger.debug(
            f"✅ Stage 2 integration: signal={safe_signal:.3f}, "
            f"consensus={safe_consensus:.3f}"
        )

        return integrated_signal, integration_info

    def _generate_market_context(self, price_df: pd.DataFrame) -> Dict:
        """市場コンテキスト生成（Phase C1統合版）"""
        context = {}

        try:
            # 基本ボラティリティ
            if len(price_df) >= 20:
                returns = price_df["close"].pct_change().dropna()
                context["volatility"] = (
                    returns.rolling(20).std().iloc[-1] if len(returns) >= 20 else 0.02
                )
            else:
                context["volatility"] = 0.02

            # トレンド強度
            if len(price_df) >= 50:
                sma_50 = price_df["close"].rolling(50).mean().iloc[-1]
                current_price = price_df["close"].iloc[-1]
                context["trend_strength"] = min(
                    abs(current_price - sma_50) / sma_50, 1.0
                )
            else:
                context["trend_strength"] = 0.5

            # VIX情報（外部データ統合対応）
            if PHASE_B_AVAILABLE and hasattr(self, "external_integrator"):
                external_data = self.external_integrator.get_latest_external_data()
                context["vix_level"] = external_data.get("vix", 20.0)
                context["dxy_level"] = external_data.get("dxy", 103.0)
                context["fear_greed"] = external_data.get("fear_greed", 50)
            else:
                context["vix_level"] = 20.0
                context["dxy_level"] = 103.0
                context["fear_greed"] = 50

            # 市場レジーム判定（Phase C1統合）
            context["market_regime"] = self.confidence_calculator.assess_market_regime(
                context
            )

        except Exception as e:
            logger.error(f"Market context generation failed: {e}")

        return context

    def _get_timeframe_data(
        self, price_df: pd.DataFrame, timeframe: str
    ) -> pd.DataFrame:
        """タイムフレーム別データ取得（キャッシュ機能付き）"""
        cache_key = f"{timeframe}_data"
        current_time = datetime.now()

        # キャッシュチェック
        if (
            cache_key in self.data_cache
            and cache_key in self.last_cache_time
            and current_time - self.last_cache_time[cache_key] < self.cache_timeout
        ):
            self.strategy_stats["cache_hits"] += 1
            return self.data_cache[cache_key]

        self.strategy_stats["cache_misses"] += 1

        try:
            # MultiTimeframeDataFetcher使用（優先）
            if self.multi_timeframe_fetcher is not None:
                multi_data = self.multi_timeframe_fetcher.get_multi_timeframe_data()
                if timeframe in multi_data:
                    tf_data = multi_data[timeframe]
                    logger.debug(
                        f"✅ {timeframe} data from fetcher: {len(tf_data)} records"
                    )
                else:
                    tf_data = pd.DataFrame()
            else:
                # フォールバック: 従来方式
                tf_data = self._convert_timeframe_data(price_df, timeframe)

            # データ品質チェック（Phase H.9.3: 即座取引開始対応・18行実稼働許可）
            if (
                len(tf_data) < 18
            ):  # 最小データ要件（50→18に緩和・実データに基づく現実的設定）
                logger.warning(
                    f"Insufficient {timeframe} data: {len(tf_data)} rows (minimum: 18)"
                )
            elif len(tf_data) < 20:  # 軽度警告レベル（rolling_window=10対応）
                logger.info(
                    f"⚠️ Limited {timeframe} data: {len(tf_data)} rows (recommended: 20+)"
                )

            # キャッシュ更新
            self.data_cache[cache_key] = tf_data
            self.last_cache_time[cache_key] = current_time

            return tf_data

        except Exception as e:
            logger.error(f"❌ Failed to get {timeframe} data: {e}")
            return pd.DataFrame()

    def _convert_timeframe_data(
        self, price_df: pd.DataFrame, timeframe: str
    ) -> pd.DataFrame:
        """従来方式タイムフレーム変換"""
        try:
            if timeframe == "15m":
                return price_df.resample("15T").interpolate(method="linear")
            elif timeframe == "4h":
                return price_df.resample("4h").agg(
                    {
                        "open": "first",
                        "high": "max",
                        "low": "min",
                        "close": "last",
                        "volume": "sum",
                    }
                )
            else:  # 1h
                return price_df.copy()
        except Exception as e:
            logger.error(f"Timeframe conversion failed for {timeframe}: {e}")
            return pd.DataFrame()

    def _generate_timeframe_labels(
        self,
        tf_data: pd.DataFrame,
        original_df: pd.DataFrame,
        original_y: pd.Series,
        timeframe: str,
    ) -> pd.Series:
        """タイムフレーム変換後のデータに対応するラベルを生成

        Args:
            tf_data: タイムフレーム変換後のデータ
            original_df: 元の価格データ（1時間足）
            original_y: 元のラベル
            timeframe: タイムフレーム

        Returns:
            pd.Series: タイムフレームに対応するラベル
        """
        try:
            if tf_data.empty:
                logger.warning(f"Empty data for {timeframe} label generation")
                return pd.Series()

            # タイムフレームごとの価格変化からラベルを生成
            if timeframe == "15m":
                # 15分足: 次の15分の価格変化を予測
                price_change = tf_data["close"].pct_change().shift(-1)
                tf_labels = (price_change > 0).astype(int)

            elif timeframe == "4h":
                # 4時間足: 次の4時間の価格変化を予測
                price_change = tf_data["close"].pct_change().shift(-1)
                tf_labels = (price_change > 0).astype(int)

            else:  # 1h
                # 1時間足: 元のラベルをそのまま使用（インデックスで整合性確保）
                # tf_dataのインデックスに合わせてラベルを抽出
                common_index = tf_data.index.intersection(original_y.index)
                if len(common_index) == 0:
                    # インデックスが一致しない場合は、元のラベルを使用
                    tf_labels = original_y.iloc[: len(tf_data)]
                else:
                    tf_labels = original_y.loc[common_index]

            # NaNを除去（最後の行にはラベルがない）
            tf_labels = tf_labels.dropna()

            # データとラベルの長さを調整（最後の行を除外）
            if len(tf_data) > len(tf_labels):
                # tf_dataの長さに合わせるため、最後にNaNを追加
                nan_count = len(tf_data) - len(tf_labels)
                nan_series = pd.Series(
                    [np.nan] * nan_count, index=tf_data.index[-nan_count:]
                )
                tf_labels = pd.concat([tf_labels, nan_series])
                logger.debug(
                    f"📊 {timeframe} labels padded with {nan_count} NaN values"
                )

            # インデックスを揃える
            tf_labels.index = tf_data.index

            logger.info(
                f"✅ {timeframe} labels generated: {len(tf_labels)} labels, "
                f"non-NaN labels: {tf_labels.notna().sum()}, "
                f"positive rate: {tf_labels.dropna().mean():.2%}"
            )

            return tf_labels

        except Exception as e:
            logger.error(f"❌ Failed to generate {timeframe} labels: {e}")
            logger.error(f"   - tf_data shape: {tuple(tf_data.shape)}")
            logger.error(f"   - original_y shape: {tuple(original_y.shape)}")
            return pd.Series()

    def _make_final_ensemble_decision(
        self,
        integrated_signal: float,
        integration_info: Dict,
        price_df: pd.DataFrame,
        position: Position,
    ) -> Signal:
        """最終アンサンブル判定（Phase C1統合版）"""
        if price_df.empty:
            return Signal()

        current_price = float(price_df["close"].iloc[-1])
        consensus_score = integration_info.get("consensus_score", 0.0)
        integration_quality = integration_info.get("integration_quality", "poor")

        # Phase H.26: consensus_scoreの安全処理
        safe_consensus_score = (
            float(consensus_score.flat[0])
            if isinstance(consensus_score, np.ndarray)
            else float(consensus_score)
        )

        # 信頼度フィルタリング
        if safe_consensus_score < self.cross_timeframe_integrator.consensus_threshold:
            logger.debug(f"🚫 Low consensus rejection: {safe_consensus_score:.3f}")
            self.strategy_stats["low_confidence_rejections"] += 1
            return Signal()

        # Phase C1統合: CrossTimeframeIntegrator最終シグナル生成
        final_signal = self.cross_timeframe_integrator.create_final_signal(
            integrated_signal, integration_info, current_price, position.exist
        )

        if final_signal.side != "":  # 有効シグナル
            self.strategy_stats["high_confidence_signals"] += 1
            logger.info(
                f"🎯 Phase C1 Final Signal: {final_signal.side}, "
                f"consensus={consensus_score:.3f}, quality={integration_quality}"
            )

        return final_signal

    def _track_ensemble_performance(
        self,
        timeframe_predictions: Dict,
        integrated_signal: float,
        integration_info: Dict,
        final_signal: Signal,
    ):
        """アンサンブルパフォーマンス追跡"""
        record = {
            "timestamp": datetime.now(),
            "timeframe_count": len(timeframe_predictions),
            "integrated_signal": integrated_signal,
            "consensus_score": integration_info.get("consensus_score", 0.0),
            "integration_quality": integration_info.get(
                "integration_quality", "unknown"
            ),
            "final_signal": final_signal.side,
            "timeframe_confidences": {},
        }

        # 各タイムフレーム信頼度記録
        for tf, pred_data in timeframe_predictions.items():
            confidence = pred_data.get("confidence", [0.5])
            record["timeframe_confidences"][tf] = (
                confidence[0] if hasattr(confidence, "__len__") else confidence
            )

        self.prediction_history.append(record)

        # 履歴サイズ制限
        if len(self.prediction_history) > self.max_history_size:
            self.prediction_history.pop(0)

    def get_ensemble_strategy_info(self) -> Dict:
        """Phase C1統合戦略情報取得"""
        info = {
            "strategy_type": "multi_timeframe_ensemble_phase_c1",
            "phase_b_integrated": PHASE_B_AVAILABLE
            and hasattr(self, "phase_b_integrated"),
            "timeframes": self.timeframes,
            "base_weights": self.base_weights,
            "ensemble_method": self.ensemble_method,
            "confidence_threshold": self.confidence_threshold,
            "strategy_stats": self.strategy_stats.copy(),
            "prediction_history_size": len(self.prediction_history),
        }

        # タイムフレームプロセッサー情報
        info["timeframe_processors"] = {}
        for tf, processor in self.timeframe_processors.items():
            if processor:
                try:
                    info["timeframe_processors"][tf] = processor.get_processor_info()
                except Exception as e:
                    info["timeframe_processors"][tf] = {"error": str(e)}

        # CrossTimeframeIntegrator情報
        try:
            info["cross_timeframe_integrator"] = (
                self.cross_timeframe_integrator.get_integrator_info()
            )
        except Exception as e:
            info["cross_timeframe_integrator"] = {"error": str(e)}

        # 最近のパフォーマンス
        if self.prediction_history:
            recent_predictions = self.prediction_history[-10:]
            info["recent_performance"] = self._analyze_recent_ensemble_performance(
                recent_predictions
            )

        return info

    def _analyze_recent_ensemble_performance(
        self, recent_predictions: List[Dict]
    ) -> Dict:
        """最近のアンサンブルパフォーマンス分析"""
        try:
            consensus_scores = [p["consensus_score"] for p in recent_predictions]
            integrated_signals = [p["integrated_signal"] for p in recent_predictions]

            quality_counts = {}
            signal_counts = {}
            for p in recent_predictions:
                quality = p["integration_quality"]
                signal = p["final_signal"]
                quality_counts[quality] = quality_counts.get(quality, 0) + 1
                signal_counts[signal] = signal_counts.get(signal, 0) + 1

            return {
                "avg_consensus": np.mean(consensus_scores) if consensus_scores else 0.0,
                "consensus_stability": (
                    np.std(consensus_scores) if consensus_scores else 0.0
                ),
                "avg_integrated_signal": (
                    np.mean(integrated_signals) if integrated_signals else 0.5
                ),
                "signal_diversity": (
                    np.std(integrated_signals) if integrated_signals else 0.0
                ),
                "prediction_count": len(recent_predictions),
                "quality_distribution": quality_counts,
                "signal_distribution": signal_counts,
            }

        except Exception as e:
            logger.error(f"Ensemble performance analysis failed: {e}")
            return {}

    def reset_statistics(self):
        """統計リセット"""
        for key in self.strategy_stats:
            self.strategy_stats[key] = 0
        self.prediction_history.clear()
        self.performance_history.clear()
        self.data_cache.clear()
        self.prediction_cache.clear()

        # サブコンポーネント統計リセット
        for processor in self.timeframe_processors.values():
            if processor:
                processor.reset_statistics()
        self.cross_timeframe_integrator.reset_statistics()
        self.confidence_calculator.reset_statistics()

        logger.info("📊 Multi-timeframe ensemble strategy statistics reset")

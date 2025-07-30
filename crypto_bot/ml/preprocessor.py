# =============================================================================
# ファイル名: crypto_bot/ml/preprocessor.py
# 説明:
# 機械学習用の特徴量生成・前処理パイプラインを提供。
# - OHLCV DataFrame から機械学習用特徴量を生成
# - sklearn Pipeline互換の FeatureEngineer を提供
# - build_ml_pipeline() で特徴量＋標準化パイプライン生成
# - prepare_ml_dataset() で特徴量・ターゲット列を一括生成
#
# ※ バックテスト用ではなく、MLStrategyや学習/推論系で使用
# =============================================================================

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# Phase B2.4: バッチ処理エンジン統合
try:
    from crypto_bot.ml.feature_engines import (
        BatchFeatureCalculator,
        ExternalDataIntegrator,
        TechnicalFeatureEngine,
    )

    BATCH_ENGINES_AVAILABLE = True
except ImportError as e:
    # logger is not yet defined, use print temporarily
    print(f"⚠️ Batch engines not available: {e}")
    BATCH_ENGINES_AVAILABLE = False

# Phase H.11: 特徴量エンジニアリング強化システム統合
try:
    from crypto_bot.ml.feature_engineering_enhanced import (
        FeatureEngineeringEnhanced,
        enhance_feature_engineering,
    )

    ENHANCED_FEATURES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Enhanced feature engineering not available: {e}")
    ENHANCED_FEATURES_AVAILABLE = False

try:
    from crypto_bot.data.vix_fetcher import VIXDataFetcher

    VIX_AVAILABLE = True
except ImportError:
    VIXDataFetcher = None
    VIX_AVAILABLE = False

try:
    from crypto_bot.data.macro_fetcher import MacroDataFetcher

    MACRO_AVAILABLE = True
except ImportError:
    MacroDataFetcher = None
    MACRO_AVAILABLE = False

try:
    from crypto_bot.data.funding_fetcher import FundingDataFetcher

    FUNDING_AVAILABLE = True
except ImportError:
    FundingDataFetcher = None
    FUNDING_AVAILABLE = False

try:
    from crypto_bot.data.fear_greed_fetcher import FearGreedDataFetcher

    FEAR_GREED_AVAILABLE = True
except ImportError:
    FearGreedDataFetcher = None
    FEAR_GREED_AVAILABLE = False

from crypto_bot.indicator.calculator import IndicatorCalculator
from crypto_bot.ml.target import make_classification_target, make_regression_target

logger = logging.getLogger(__name__)


def calc_rci(series: pd.Series, period: int) -> pd.Series:
    """
    Rank Correlation Index（RCI）を計算する。
    :param series: 終値などの価格データ（pd.Series）
    :param period: 期間
    :return: RCIのpd.Series
    """
    n = period

    def _rci(x):
        price_ranks = pd.Series(x).rank(ascending=False)
        date_ranks = np.arange(1, n + 1)
        d = price_ranks.values - date_ranks
        return (1 - 6 * (d**2).sum() / (n * (n**2 - 1))) * 100

    return series.rolling(window=n).apply(_rci, raw=False)


class FeatureEngineer(BaseEstimator, TransformerMixin):
    """
    OHLCVから各種特徴量を生成する sklearn互換クラス。

    入力: OHLCV DataFrame（indexはtz-aware DatetimeIndex）
    出力: 特徴量DataFrame

    - 欠損補完
    - ATR, lag, rolling統計, extra_features対応
    - ffill/0埋め等も実施
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ind_calc = IndicatorCalculator()
        self.extra_features = self.config["ml"].get("extra_features", [])

        # MLパラメータ設定
        ml_config = self.config["ml"]
        self.feat_period = ml_config.get("feat_period", 14)
        self.lags = ml_config.get("lags", [1, 2, 3])
        self.rolling_window = ml_config.get("rolling_window", 14)

        # VIX統合設定（強制初期化版）
        logger.info(f"🔍 VIX Debug: extra_features={self.extra_features}")
        logger.info(f"🔍 VIX Debug: VIX_AVAILABLE={VIX_AVAILABLE}")
        vix_in_features = "vix" in self.extra_features
        logger.info(f"🔍 VIX Debug: vix_in_features={vix_in_features}")

        # VIX復活実装：設定対応・複数データソース・キャッシュ機能
        if vix_in_features:
            try:
                if VIX_AVAILABLE and VIXDataFetcher:
                    self.vix_fetcher = VIXDataFetcher(self.config)
                    self.vix_enabled = True
                    logger.info(
                        "✅ VIX fetcher initialized successfully (config-aware)"
                    )
                else:
                    # VIXDataFetcherを直接インポートして初期化を強制
                    from crypto_bot.data.vix_fetcher import (
                        VIXDataFetcher as DirectVIXFetcher,
                    )

                    self.vix_fetcher = DirectVIXFetcher(self.config)
                    self.vix_enabled = True
                    logger.info(
                        "✅ VIX fetcher initialized with direct import (config-aware)"
                    )
            except Exception as e:
                logger.error(f"❌ VIX fetcher initialization failed: {e}")
                self.vix_fetcher = None
                self.vix_enabled = False
        else:
            self.vix_enabled = False
            self.vix_fetcher = None
            logger.info(f"⚠️ VIX not in extra_features: {self.extra_features}")

        # マクロデータ統合設定（強制初期化版）
        macro_in_features = any(
            feat in self.extra_features for feat in ["dxy", "macro", "treasury"]
        )
        logger.info(f"🔍 Macro Debug: macro_in_features={macro_in_features}")

        if macro_in_features:
            try:
                if MACRO_AVAILABLE and MacroDataFetcher:
                    self.macro_fetcher = MacroDataFetcher()
                    self.macro_enabled = True
                    logger.info("✅ Macro fetcher initialized successfully (forced)")
                else:
                    # MacroDataFetcherを直接インポートして初期化を強制
                    from crypto_bot.data.macro_fetcher import (
                        MacroDataFetcher as DirectMacroFetcher,
                    )

                    self.macro_fetcher = DirectMacroFetcher()
                    self.macro_enabled = True
                    logger.info("✅ Macro fetcher initialized with direct import")
            except Exception as e:
                logger.error(f"❌ Macro fetcher initialization failed: {e}")
                self.macro_fetcher = None
                self.macro_enabled = False
        else:
            self.macro_enabled = False
            self.macro_fetcher = None
            logger.info(
                f"⚠️ Macro features not in extra_features: {self.extra_features}"
            )

        # Funding Rate統合設定（Bitbank専用：現物取引のため無効化）
        self.funding_enabled = False
        self.funding_fetcher = None

        # Bitbank現物取引では代替特徴量を使用
        self.funding_alternative_enabled = any(
            feat in self.extra_features for feat in ["funding", "oi"]
        )

        # Fear & Greed復活実装：設定対応・複数データソース・フォールバック機能
        fear_greed_in_features = any(
            feat in self.extra_features for feat in ["fear_greed", "fg"]
        )
        logger.info(
            f"🔍 Fear&Greed Debug: fear_greed_in_features={fear_greed_in_features}"
        )

        if fear_greed_in_features:
            try:
                if FEAR_GREED_AVAILABLE and FearGreedDataFetcher:
                    self.fear_greed_fetcher = FearGreedDataFetcher(self.config)
                    self.fear_greed_enabled = True
                    logger.info(
                        "✅ Fear&Greed fetcher initialized successfully (config-aware)"
                    )
                else:
                    # FearGreedDataFetcherを直接インポートして初期化を強制
                    from crypto_bot.data.fear_greed_fetcher import (
                        FearGreedDataFetcher as DirectFGFetcher,
                    )

                    self.fear_greed_fetcher = DirectFGFetcher(self.config)
                    self.fear_greed_enabled = True
                    logger.info(
                        "✅ Fear&Greed fetcher initialized with direct import "
                        "(config-aware)"
                    )
            except Exception as e:
                logger.error(f"❌ Fear&Greed fetcher initialization failed: {e}")
                self.fear_greed_fetcher = None
                self.fear_greed_enabled = False
        else:
            self.fear_greed_enabled = False
            self.fear_greed_fetcher = None
            logger.info(f"⚠️ Fear&Greed not in extra_features: {self.extra_features}")

        # USD/JPY為替データ統合設定（強制初期化版）
        forex_in_features = any(
            feat in self.extra_features for feat in ["forex", "usdjpy", "jpy"]
        )
        logger.info(f"🔍 Forex Debug: forex_in_features={forex_in_features}")

        if forex_in_features:
            try:
                # MacroDataFetcherを為替データ取得に再利用
                if MACRO_AVAILABLE and MacroDataFetcher:
                    self.forex_fetcher = MacroDataFetcher()
                    self.forex_enabled = True
                    logger.info("✅ Forex fetcher initialized successfully (forced)")
                else:
                    # MacroDataFetcherを直接インポートして初期化を強制
                    from crypto_bot.data.macro_fetcher import (
                        MacroDataFetcher as DirectForexFetcher,
                    )

                    self.forex_fetcher = DirectForexFetcher()
                    self.forex_enabled = True
                    logger.info("✅ Forex fetcher initialized with direct import")
            except Exception as e:
                logger.error(f"❌ Forex fetcher initialization failed: {e}")
                self.forex_fetcher = None
                self.forex_enabled = False
        else:
            self.forex_enabled = False
            self.forex_fetcher = None
            logger.info(f"⚠️ Forex not in extra_features: {self.extra_features}")

        # Phase B2.4: バッチ処理エンジン初期化
        self._initialize_batch_engines()

    def _initialize_batch_engines(self):
        """
        Phase B2.4: バッチ処理エンジン初期化
        DataFrame断片化解消のための新エンジンシステム
        """
        if not BATCH_ENGINES_AVAILABLE:
            logger.warning(
                "⚠️ Batch engines not available, falling back to legacy processing"
            )
            self.batch_engines_enabled = False
            return

        try:
            # BatchFeatureCalculator（コア）
            self.batch_calculator = BatchFeatureCalculator(self.config)

            # TechnicalFeatureEngine（テクニカル指標）
            self.technical_engine = TechnicalFeatureEngine(
                self.config, self.batch_calculator
            )

            # Phase H.25: 外部データ無効化時はExternalDataIntegratorをスキップ
            external_data_enabled = (
                self.config.get("ml", {}).get("external_data", {}).get("enabled", True)
            )
            if external_data_enabled:
                # ExternalDataIntegrator（外部データ統合）
                self.external_integrator = ExternalDataIntegrator(
                    self.config, self.batch_calculator
                )
            else:
                self.external_integrator = None
                logger.info("⚠️ ExternalDataIntegrator skipped - external data disabled")

            self.batch_engines_enabled = True

            logger.info(
                "🚀 Phase B2.4: Batch processing engines initialized successfully - "
                "DataFrame fragmentation optimization enabled"
            )

        except Exception as e:
            logger.error(f"❌ Failed to initialize batch engines: {e}")
            self.batch_engines_enabled = False

    def _transform_with_batch_engines(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Phase B2.4: バッチ処理エンジンによる高速特徴量生成
        DataFrame断片化を解消する根本的改善
        """
        start_time = time.time()
        logger.info("🚀 Starting batch processing feature generation")

        feature_batches = []

        try:
            # 1. テクニカル指標バッチ処理
            technical_batches = self.technical_engine.calculate_all_technical_batches(
                df
            )
            feature_batches.extend(technical_batches)
            logger.debug(f"📊 Technical batches: {len(technical_batches)}")

            # 2. 外部データ統合バッチ処理
            if self.external_integrator:
                external_batches = (
                    self.external_integrator.create_external_data_batches(df.index)
                )
                feature_batches.extend(external_batches)
                logger.debug(f"📊 External data batches: {len(external_batches)}")

            # 3. 一括統合（断片化解消の中核）
            result_df = self.batch_calculator.merge_batches_efficient(
                df, feature_batches
            )

            processing_time = time.time() - start_time
            total_features = sum(len(batch) for batch in feature_batches)

            logger.info(
                f"✅ Batch processing completed: {total_features} features "
                f"in {processing_time:.3f}s ({total_features/processing_time:.1f} features/sec)"
            )

            # パフォーマンス統計出力
            batch_stats = self.batch_calculator.get_performance_summary()
            logger.debug(f"📊 Batch Performance:\n{batch_stats}")

            return result_df

        except Exception as e:
            import traceback

            logger.error(f"❌ Batch processing failed: {e}")
            logger.error(
                f"❌ Batch processing error details:\n{traceback.format_exc()}"
            )
            logger.warning("⚠️ Falling back to legacy processing")
            return self._transform_legacy(df)

    def _transform_legacy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        レガシー特徴量処理（フォールバック用）
        個別DataFrame操作による従来方式
        """
        logger.warning("⚠️ Using legacy feature processing - performance may be slower")

        # 2. ATR
        feat_period = self.config["ml"]["feat_period"]
        atr = self.ind_calc.atr(df, window=feat_period)
        if isinstance(atr, pd.Series):
            df[f"ATR_{feat_period}"] = atr
        else:
            df[f"ATR_{feat_period}"] = atr.iloc[:, 0]
        logger.debug("After ATR: %s", df.shape)

        # 3. lag特徴量
        for lag in self.config["ml"]["lags"]:
            df[f"close_lag_{lag}"] = df["close"].shift(lag)
        logger.debug("After lag feats: %s", df.shape)

        # 4. rolling統計
        win = self.config["ml"]["rolling_window"]
        df[f"close_mean_{win}"] = df["close"].rolling(win).mean()
        df[f"close_std_{win}"] = df["close"].rolling(win).std()
        logger.debug("After rolling stats: %s", df.shape)

        # 5. extra_features処理（レガシー方式）
        return self._process_extra_features_legacy(df)

    def _process_extra_features_legacy(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        レガシー方式による extra_features 処理
        フォールバック時に使用（個別DataFrame操作）
        """
        if not self.extra_features:
            return df

        logger.warning(
            "⚠️ Using legacy feature processing - individual DataFrame operations"
        )
        logger.debug(f"Legacy processing for: {self.extra_features}")

        # レガシー処理では既存のextra_features処理ループを使用
        # （メインのtransform内の処理と重複を避けるため、ここでは基本処理のみ）

        return df

    def _get_cached_external_data(
        self, data_type: str, time_index: pd.DatetimeIndex
    ) -> pd.DataFrame:
        """
        キャッシュから外部データを取得

        Parameters
        ----------
        data_type : str
            データタイプ ('vix', 'macro', 'forex', 'fear_greed', 'funding')
        time_index : pd.DatetimeIndex
            対象期間のタイムインデックス

        Returns
        -------
        pd.DataFrame
            キャッシュされた外部データ（該当期間）
        """
        try:
            from crypto_bot.ml.external_data_cache import get_global_cache

            cache = get_global_cache()
            if not cache.is_initialized:
                return pd.DataFrame()

            start_time = time_index.min()
            end_time = time_index.max()

            cached_data = cache.get_period_data(data_type, start_time, end_time)
            return cached_data

        except Exception as e:
            logger.debug(f"Failed to get cached {data_type} data: {e}")
            return pd.DataFrame()

    def _validate_external_data_fetchers(self) -> dict:
        """
        外部データフェッチャーの状態を検証し、データ品質改善のための情報を返す

        Returns
        -------
        dict
            フェッチャーの状態レポート
        """
        validation_report = {
            "vix": {"available": False, "initialized": False, "working": False},
            "macro": {"available": False, "initialized": False, "working": False},
            "forex": {"available": False, "initialized": False, "working": False},
            "fear_greed": {"available": False, "initialized": False, "working": False},
            "total_working": 0,
            "external_data_success_rate": 0.0,
        }

        # VIX検証
        if "vix" in self.extra_features:
            validation_report["vix"]["available"] = True
            if self.vix_fetcher is not None:
                validation_report["vix"]["initialized"] = True
                try:
                    # 簡単なテスト取得
                    test_data = self.vix_fetcher.get_vix_data(timeframe="1d", limit=1)
                    if test_data is not None and not test_data.empty:
                        validation_report["vix"]["working"] = True
                        validation_report["total_working"] += 1
                        logger.info("✅ VIX fetcher validation: WORKING")
                    else:
                        logger.warning(
                            "⚠️ VIX fetcher validation: NOT WORKING (empty data)"
                        )
                except Exception as e:
                    logger.error(f"❌ VIX fetcher validation failed: {e}")

        # Macro検証
        if any(feat in self.extra_features for feat in ["dxy", "macro", "treasury"]):
            validation_report["macro"]["available"] = True
            if self.macro_fetcher is not None:
                validation_report["macro"]["initialized"] = True
                try:
                    # 簡単なテスト取得
                    test_data = self.macro_fetcher.get_macro_data()
                    if test_data and not all(df.empty for df in test_data.values()):
                        validation_report["macro"]["working"] = True
                        validation_report["total_working"] += 1
                        logger.info("✅ Macro fetcher validation: WORKING")
                    else:
                        logger.warning(
                            "⚠️ Macro fetcher validation: NOT WORKING (empty data)"
                        )
                except Exception as e:
                    logger.error(f"❌ Macro fetcher validation failed: {e}")

        # Fear&Greed検証
        if any(feat in self.extra_features for feat in ["fear_greed", "fg"]):
            validation_report["fear_greed"]["available"] = True
            if self.fear_greed_fetcher is not None:
                validation_report["fear_greed"]["initialized"] = True
                try:
                    # 簡単なテスト取得
                    test_data = self.fear_greed_fetcher.get_fear_greed_data(days_back=1)
                    if test_data is not None and not test_data.empty:
                        validation_report["fear_greed"]["working"] = True
                        validation_report["total_working"] += 1
                        logger.info("✅ Fear&Greed fetcher validation: WORKING")
                    else:
                        logger.warning(
                            "⚠️ Fear&Greed fetcher validation: NOT WORKING (empty data)"
                        )
                except Exception as e:
                    logger.error(f"❌ Fear&Greed fetcher validation failed: {e}")

        # Forex検証
        if any(feat in self.extra_features for feat in ["forex", "usdjpy", "jpy"]):
            validation_report["forex"]["available"] = True
            if self.forex_fetcher is not None:
                validation_report["forex"]["initialized"] = True
                try:
                    # 簡単なテスト取得
                    test_data = self.forex_fetcher.get_macro_data()
                    if (
                        test_data
                        and "usdjpy" in test_data
                        and not test_data["usdjpy"].empty
                    ):
                        validation_report["forex"]["working"] = True
                        validation_report["total_working"] += 1
                        logger.info("✅ Forex fetcher validation: WORKING")
                    else:
                        logger.warning(
                            "⚠️ Forex fetcher validation: NOT WORKING (empty data)"
                        )
                except Exception as e:
                    logger.error(f"❌ Forex fetcher validation failed: {e}")

        # 成功率計算
        total_available = sum(
            1
            for fetcher in validation_report.values()
            if isinstance(fetcher, dict) and fetcher.get("available", False)
        )
        if total_available > 0:
            validation_report["external_data_success_rate"] = (
                validation_report["total_working"] / total_available
            )

        logger.info(
            f"🔍 External data validation: "
            f"{validation_report['total_working']}/{total_available} fetchers working "
            f"({validation_report['external_data_success_rate']*100:.1f}% success rate)"
        )
        return validation_report

    def fit(self, X: pd.DataFrame, y=None):
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        logger.debug("Input DataFrame shape: %s", X.shape)

        # 外部データフェッチャーの状態検証（データ品質改善）
        validation_report = self._validate_external_data_fetchers()
        logger.info(
            f"🔍 External data fetcher status: "
            f"{validation_report['total_working']} working, "
            f"{validation_report['external_data_success_rate']*100:.1f}% success rate"
        )

        if X.empty:
            feat_period = self.config["ml"]["feat_period"]
            win = self.config["ml"]["rolling_window"]
            lags = self.config["ml"]["lags"]
            columns = ["ATR_" + str(feat_period)]
            columns.extend([f"close_lag_{lag}" for lag in lags])
            columns.extend([f"close_mean_{win}", f"close_std_{win}"])
            for feat in self.extra_features:
                feat_lc = feat.lower()
                base, _, param = feat_lc.partition("_")
                period = int(param) if param.isdigit() else None
                if base == "rsi" and period:
                    columns.append(f"rsi_{period}")
                elif base == "ema" and period:
                    columns.append(f"ema_{period}")
                elif base == "sma" and period:
                    columns.append(f"sma_{period}")
                elif base == "macd":
                    columns.extend(["macd", "macd_signal", "macd_hist"])
                elif base == "rci" and period:
                    columns.append(f"rci_{period}")
                elif base == "volume" and "zscore" in feat_lc:
                    period_str = feat_lc.split("_")[-1]
                    win_z = int(period_str) if period_str.isdigit() else win
                    columns.append(f"volume_zscore_{win_z}")
                elif feat_lc == "day_of_week":
                    columns.append("day_of_week")
                elif feat_lc == "hour_of_day":
                    columns.append("hour_of_day")
                # Phase F.3: 新規特徴量の列名定義
                elif feat_lc in [
                    "volatility_24h",
                    "volatility_1h",
                    "volume_change_24h",
                    "volume_change_1h",
                    "price_change_24h",
                    "price_change_4h",
                    "price_change_1h",
                    "cmf_20",
                    "willr_14",
                ]:
                    columns.append(feat_lc)
                elif feat_lc in ["mochipoyo_long_signal", "mochipoyo_short_signal"]:
                    columns.extend(["mochipoyo_long_signal", "mochipoyo_short_signal"])
            return pd.DataFrame(columns=columns)
        df = X.copy()

        # 1. 欠損補完
        df = df.ffill()
        logger.debug("After ffill: %s", df.shape)

        # Phase B2.4: バッチ処理による高速特徴量生成
        logger.info(f"🔍 Batch engines enabled: {self.batch_engines_enabled}")
        if self.batch_engines_enabled:
            df = self._transform_with_batch_engines(df)
        else:
            # レガシー処理（フォールバック）
            df = self._transform_legacy(df)

        # 6. 最終特徴量検証・欠損値処理
        # Phase B2.5: バッチ処理有効時は追加処理をスキップ（バッチ処理で完了済み）
        if self.extra_features and not self.batch_engines_enabled:
            logger.debug("Adding extra features: %s", self.extra_features)
            # 追加でmochipoyoのシグナルが含まれている場合は一度まとめて取得しておく
            mochipoyo_needed = any(
                feat.lower() in ["mochipoyo_long_signal", "mochipoyo_short_signal"]
                for feat in self.extra_features
            )
            mochipoyo_signals = None
            if mochipoyo_needed:
                mochipoyo_signals = self.ind_calc.mochipoyo_signals(df)

            for feat in self.extra_features:
                feat_lc = feat.lower()
                try:
                    # fear_greedは特別処理（アンダースコアを含む複合語）
                    if feat_lc == "fear_greed":
                        base = "fear_greed"
                        param = ""
                        period = None
                    else:
                        base, _, param = feat_lc.partition("_")
                        period = int(param) if param.isdigit() else None

                    # Phase B2.5: バッチ処理済み特徴量のスキップロジック
                    if self.batch_engines_enabled:
                        # バッチ処理済み特徴量はスキップ
                        skip_features = [
                            "rsi",
                            "ema",
                            "sma",
                            "macd",
                            "atr",
                            "volume",
                            "stoch",
                            "bb",
                            "bollinger",
                            "willr",
                            "williams",
                            "adx",
                            "cmf",
                            "fisher",
                            "vix",
                            "dxy",
                            "macro",
                            "treasury",
                            "fear_greed",
                            "fg",
                        ]
                        if any(
                            base == skip_feat or base.startswith(skip_feat)
                            for skip_feat in skip_features
                        ):
                            logger.debug(f"Skipping batch-processed feature: {feat}")
                            continue

                    # 時間特徴量（バッチ処理対象外のため継続処理）
                    if feat_lc == "day_of_week":
                        if isinstance(df.index, pd.DatetimeIndex):
                            df["day_of_week"] = df.index.dayofweek.astype("int8")
                        else:
                            df["day_of_week"] = 0
                    elif feat_lc == "hour_of_day":
                        if isinstance(df.index, pd.DatetimeIndex):
                            df["hour_of_day"] = df.index.hour.astype("int8")
                        else:
                            df["hour_of_day"] = 0

                    # Phase F.3: 151特徴量WARNING解消 - 不足特徴量処理
                    elif feat_lc == "volatility_24h":
                        df["volatility_24h"] = self.ind_calc.volatility_24h(df["close"])
                    elif feat_lc == "volatility_1h":
                        df["volatility_1h"] = self.ind_calc.volatility_1h(df["close"])
                    elif feat_lc == "volume_change_24h":
                        df["volume_change_24h"] = self.ind_calc.volume_change_24h(
                            df["volume"]
                        )
                    elif feat_lc == "volume_change_1h":
                        df["volume_change_1h"] = self.ind_calc.volume_change_1h(
                            df["volume"]
                        )
                    elif feat_lc == "price_change_24h":
                        df["price_change_24h"] = self.ind_calc.price_change_24h(
                            df["close"]
                        )
                    elif feat_lc == "price_change_4h":
                        df["price_change_4h"] = self.ind_calc.price_change_4h(
                            df["close"]
                        )
                    elif feat_lc == "price_change_1h":
                        df["price_change_1h"] = self.ind_calc.price_change_1h(
                            df["close"]
                        )
                    elif feat_lc == "cmf_20":
                        df["cmf_20"] = self.ind_calc.cmf_20(df)
                    elif feat_lc == "willr_14":
                        df["willr_14"] = self.ind_calc.willr_14(df)

                    # Phase B2.5: VIX特徴量は既にExternalDataIntegratorで処理済み
                    elif base == "vix":
                        try:
                            logger.info(
                                f"🔍 Processing VIX features: "
                                f"vix_enabled={self.vix_enabled}, "
                                f"vix_fetcher={self.vix_fetcher is not None}"
                            )

                            vix_features = None

                            # キャッシュからVIXデータを取得（優先）
                            cached_vix = self._get_cached_external_data("vix", df.index)
                            if not cached_vix.empty:
                                logger.info(
                                    f"✅ Using cached VIX: {len(cached_vix)} records"
                                )
                                vix_features = cached_vix

                            # キャッシュが空の場合、VIXフェッチャーで直接取得
                            if vix_features is None or vix_features.empty:
                                if self.vix_fetcher:
                                    logger.info("🔍 Fetching fresh VIX data...")
                                    try:
                                        vix_data = self.vix_fetcher.get_vix_data(
                                            timeframe="1d", limit=100
                                        )
                                        if not vix_data.empty:
                                            logger.info(
                                                f"✅ VIX: {len(vix_data)} records"
                                            )
                                            vix_features = (
                                                self.vix_fetcher.calculate_vix_features(
                                                    vix_data
                                                )
                                            )
                                        else:
                                            logger.warning(
                                                "❌ VIX data empty from fetcher"
                                            )
                                    except Exception as e:
                                        logger.error(f"❌ VIX fetching failed: {e}")
                                else:
                                    logger.warning("❌ VIX fetcher not available")

                            # VIXデータが取得できた場合の処理
                            if vix_features is not None and not vix_features.empty:
                                # タイムゾーン統一・データアライメント改良
                                if isinstance(
                                    df.index, pd.DatetimeIndex
                                ) and isinstance(vix_features.index, pd.DatetimeIndex):
                                    # タイムゾーン統一（重要な修正）
                                    if df.index.tz is None:
                                        df.index = df.index.tz_localize("UTC")
                                    if vix_features.index.tz is None:
                                        vix_features.index = (
                                            vix_features.index.tz_localize("UTC")
                                        )
                                    elif vix_features.index.tz != df.index.tz:
                                        vix_features.index = (
                                            vix_features.index.tz_convert("UTC")
                                        )

                                    # 改良されたリサンプリング：日次→時間足への変換
                                    # 前方補完（ffill）で日次データを時間足に展開
                                    vix_hourly = vix_features.resample("H").ffill()

                                    # 暗号資産データの時間範囲に合わせて制限
                                    start_time = df.index.min()
                                    end_time = df.index.max()
                                    vix_hourly = vix_hourly.loc[start_time:end_time]

                                    # より柔軟なマッチング：最も近い時刻のデータを使用
                                    vix_cols = [
                                        "vix_level",
                                        "vix_change",
                                        "vix_zscore",
                                        "fear_level",
                                        "vix_spike",
                                        "vix_regime",
                                    ]
                                    added_features = 0

                                    for i, timestamp in enumerate(df.index):
                                        # 最も近いVIXデータポイントを検索
                                        if len(vix_hourly) > 0:
                                            closest_idx = vix_hourly.index.get_indexer(
                                                [timestamp], method="ffill"
                                            )[0]
                                            if closest_idx >= 0:
                                                vix_row = vix_hourly.iloc[closest_idx]
                                                for col in vix_cols:
                                                    if col in vix_row.index:
                                                        if col == "vix_regime":
                                                            # カテゴリを数値に変換
                                                            regime_map = {
                                                                "low": 0,
                                                                "normal": 1,
                                                                "high": 2,
                                                                "extreme": 3,
                                                            }
                                                            k = "vix_regime_numeric"
                                                            v = regime_map.get(
                                                                vix_row[col], 1
                                                            )
                                                            df.loc[timestamp, k] = v
                                                        else:
                                                            df.loc[timestamp, col] = (
                                                                vix_row[col]
                                                            )
                                        added_features = i + 1

                                    logger.info(
                                        f"VIX: {added_features}/{len(df)} points"
                                    )
                                else:
                                    logger.warning(
                                        "Could not align VIX data - index type mismatch"
                                    )
                            else:
                                logger.warning("No VIX data available - using defaults")
                        except Exception as e:
                            logger.warning("Failed to add VIX features: %s", e)

                    # OI（未決済建玉）関連特徴量
                    elif base == "oi":
                        try:
                            # from crypto_bot.data.fetcher import (
                            #     MarketDataFetcher,
                            #     OIDataFetcher,
                            # )

                            # OIデータ取得のためのプレースホルダー（実際にはより詳細な実装が必要）
                            # 現時点では基本的なOI特徴量をシミュレート
                            # OI変化率（価格とOIの相関）
                            df["oi_price_divergence"] = (
                                df["close"].pct_change()
                                - df["volume"].pct_change().fillna(0)
                            ).fillna(0)

                            # ボリューム強度（OIの代替）
                            df["volume_intensity"] = (
                                df["volume"] / df["volume"].rolling(20).mean()
                            )

                            # OI勢い（ボリュームベース）
                            df["oi_momentum_proxy"] = (
                                df["volume"].rolling(10).sum()
                                / df["volume"].rolling(50).sum()
                            )

                        except Exception as e:
                            logger.warning("Failed to add OI features: %s", e)

                    # Phase B2.5: Macro経済データ特徴量は既にExternalDataIntegratorで処理済み
                    elif base in ["dxy", "macro", "treasury"]:
                        try:
                            logger.info(
                                f"🔍 Processing Macro features: "
                                f"macro_enabled={self.macro_enabled}, "
                                f"macro_fetcher={self.macro_fetcher is not None}"
                            )

                            macro_features = None

                            # キャッシュからマクロデータを取得（優先）
                            cached_macro = self._get_cached_external_data(
                                "macro", df.index
                            )
                            if not cached_macro.empty:
                                logger.info(
                                    f"✅ Using cached macro: {len(cached_macro)} records"
                                )
                                macro_features = cached_macro

                            # キャッシュが空の場合、マクロフェッチャーで直接取得
                            if macro_features is None or macro_features.empty:
                                if self.macro_fetcher:
                                    logger.info("🔍 Fetching fresh Macro data...")
                                    try:
                                        macro_data = self.macro_fetcher.get_macro_data()
                                        if macro_data and not all(
                                            df.empty for df in macro_data.values()
                                        ):
                                            logger.info(
                                                f"✅ Macro: {len(macro_data)} datasets"
                                            )
                                            calc_func = (
                                                self.macro_fetcher.calculate_macro_features  # noqa: E501
                                            )
                                            macro_features = calc_func(macro_data)
                                        else:
                                            logger.warning(
                                                "❌ Macro data empty from fetcher"
                                            )
                                    except Exception as e:
                                        logger.error(f"❌ Macro fetching failed: {e}")
                                else:
                                    logger.warning("❌ Macro fetcher not available")

                            # マクロデータが取得できた場合の処理
                            if macro_features is not None and not macro_features.empty:
                                # キャッシュがない場合は従来の方法
                                if hasattr(df, "index") and len(df) > 0:
                                    backtest_year = df.index.min().year
                                    self.macro_fetcher._backtest_start_year = (
                                        backtest_year
                                    )
                                macro_data = self.macro_fetcher.get_macro_data(limit=50)
                                if macro_data and not all(
                                    df.empty for df in macro_data.values()
                                ):
                                    macro_features = (
                                        self.macro_fetcher.calculate_macro_features(
                                            macro_data
                                        )
                                    )

                                    # 暗号資産データとマクロデータの時間軸を合わせる
                                    if isinstance(
                                        df.index, pd.DatetimeIndex
                                    ) and isinstance(
                                        macro_features.index, pd.DatetimeIndex
                                    ):
                                        # タイムゾーンを統一
                                        if df.index.tz is None:
                                            df.index = df.index.tz_localize("UTC")
                                        if macro_features.index.tz is None:
                                            macro_features.index = (
                                                macro_features.index.tz_localize("UTC")
                                            )
                                        elif macro_features.index.tz != df.index.tz:
                                            macro_features.index = (
                                                macro_features.index.tz_convert("UTC")
                                            )

                                        # 改良されたリサンプリング：日次→時間足への変換
                                        macro_hourly = macro_features.resample(
                                            "H"
                                        ).ffill()

                                        # 暗号資産データの時間範囲に合わせて制限
                                        start_time = df.index.min()
                                        end_time = df.index.max()
                                        macro_hourly = macro_hourly.loc[
                                            start_time:end_time
                                        ]

                                        # より柔軟なマッチング：最も近い時刻のデータを使用
                                        macro_cols = [
                                            "dxy_level",
                                            "dxy_change",
                                            "dxy_zscore",
                                            "dxy_strength",
                                            "treasury_10y_level",
                                            "treasury_10y_change",
                                            "treasury_10y_zscore",
                                            "treasury_regime",
                                            "yield_curve_spread",
                                            "risk_sentiment",
                                            # USD/JPY為替特徴量追加
                                            "usdjpy_level",
                                            "usdjpy_change",
                                            "usdjpy_volatility",
                                            "usdjpy_zscore",
                                            "usdjpy_trend",
                                            "usdjpy_strength",
                                        ]
                                        added_features = 0

                                        for i, timestamp in enumerate(df.index):
                                            # 最も近いマクロデータポイントを検索
                                            if len(macro_hourly) > 0:
                                                closest_idx = (
                                                    macro_hourly.index.get_indexer(
                                                        [timestamp], method="ffill"
                                                    )[0]
                                                )
                                                if closest_idx >= 0:
                                                    macro_row = macro_hourly.iloc[
                                                        closest_idx
                                                    ]
                                                    for col in macro_cols:
                                                        if col in macro_row.index:
                                                            df.loc[timestamp, col] = (
                                                                macro_row[col]
                                                            )
                                                    added_features = i + 1

                                        logger.info(
                                            f"Added DXY/macro features to "
                                            f"{added_features}/{len(df)} data points"
                                        )
                                    else:
                                        logger.warning(
                                            "Index type mismatch for "
                                            "macro data alignment"
                                        )
                                else:
                                    logger.warning("No macro data available")
                            else:
                                logger.warning("Macro fetcher not initialized")
                        except Exception as e:
                            logger.warning("Failed to add macro features: %s", e)

                    # Funding Rate & Open Interest 特徴量（Bitbank信用取引専用代替実装）
                    elif base in ["funding", "oi"]:
                        try:
                            # Bitbank信用取引（1倍レバレッジ）に適した代替特徴量（17特徴量）
                            logger.info(
                                "Adding Bitbank margin trading alternative features"
                            )

                            # 1. 金利コスト推定特徴量（Funding Rate代替）
                            # 価格変動率から金利コストを推定（信用取引の借入コスト）
                            returns = df["close"].pct_change()
                            df["fr_rate"] = (
                                returns.rolling(20).std() * 100
                            )  # 変動率をコスト代替
                            df["fr_change_1d"] = (
                                df["fr_rate"].pct_change(24) * 100
                            )  # 1日変化率
                            df["fr_change_3d"] = (
                                df["fr_rate"].pct_change(72) * 100
                            )  # 3日変化率

                            # 2. 信用取引リスク指標（Funding Z-Score代替）
                            # 価格変動率のZ-Score（信用取引リスク）
                            vol_ma_7 = returns.rolling(7 * 24).std()
                            vol_std_7 = (
                                returns.rolling(7 * 24).std().rolling(7 * 24).std()
                            )
                            df["fr_zscore_7d"] = (
                                returns.rolling(24).std() - vol_ma_7
                            ) / vol_std_7.replace(0, 1)

                            vol_ma_30 = returns.rolling(30 * 24).std()
                            vol_std_30 = (
                                returns.rolling(30 * 24).std().rolling(30 * 24).std()
                            )
                            df["fr_zscore_30d"] = (
                                returns.rolling(24).std() - vol_ma_30
                            ) / vol_std_30.replace(0, 1)

                            # 3. 市場レジーム判定（信用取引リスクベース）
                            current_vol = returns.rolling(24).std()
                            df["fr_regime"] = 0  # デフォルト：中立
                            df.loc[
                                current_vol > vol_ma_30 + vol_std_30, "fr_regime"
                            ] = 1  # 高リスク
                            df.loc[
                                current_vol < vol_ma_30 - vol_std_30, "fr_regime"
                            ] = -1  # 低リスク

                            # 4. 極端値検知（信用取引リスク転換シグナル）
                            vol_q95 = current_vol.rolling(60 * 24).quantile(0.95)
                            vol_q05 = current_vol.rolling(60 * 24).quantile(0.05)
                            df["fr_extreme_long"] = (current_vol > vol_q95).astype(int)
                            df["fr_extreme_short"] = (current_vol < vol_q05).astype(int)

                            # 5. 信用取引コスト波動率（リスク指標）
                            df["fr_volatility"] = (
                                current_vol.rolling(7 * 24).std() * 100
                            )

                            # 6. トレンド強度（信用取引方向性）
                            price_sma_3 = df["close"].rolling(3 * 24).mean()
                            price_sma_10 = df["close"].rolling(10 * 24).mean()
                            df["fr_trend_strength"] = (
                                (price_sma_3 - price_sma_10)
                                / price_sma_10.replace(0, 1)
                                * 100
                            )

                            # 7. ポジション規模推定（Open Interest代替）
                            # 出来高×価格で信用取引規模を推定
                            position_size = df["volume"] * df["close"]
                            oi_ma_30 = position_size.rolling(30 * 24).mean()
                            df["oi_normalized"] = (
                                position_size / oi_ma_30.replace(0, 1)
                            ) - 1

                            # 8. ポジション変化率（OI変化率代替）
                            df["oi_change_1d"] = position_size.pct_change(24) * 100
                            df["oi_momentum_3d"] = position_size.pct_change(72) * 100

                            # 9. ポジション規模Z-Score（OI Z-Score代替）
                            pos_ma_7 = position_size.rolling(7 * 24).mean()
                            pos_std_7 = position_size.rolling(7 * 24).std()
                            df["oi_zscore_7d"] = (
                                position_size - pos_ma_7
                            ) / pos_std_7.replace(0, 1)

                            # 10. ポジション新高値・新安値（OI新高値・新安値代替）
                            pos_max_30 = position_size.rolling(30 * 24).max()
                            pos_min_30 = position_size.rolling(30 * 24).min()
                            df["oi_new_high"] = (
                                position_size >= pos_max_30 * 0.98
                            ).astype(int)
                            df["oi_new_low"] = (
                                position_size <= pos_min_30 * 1.02
                            ).astype(int)

                            # 11. 信用取引偏向指標（ポジション偏向指標代替）
                            # 金利コストとポジション規模の複合指標
                            fr_abs = df["fr_rate"].abs()
                            oi_abs = df["oi_normalized"].abs()
                            df["position_bias"] = fr_abs * oi_abs

                            # 欠損値処理
                            funding_cols = [
                                "fr_rate",
                                "fr_change_1d",
                                "fr_change_3d",
                                "fr_zscore_7d",
                                "fr_zscore_30d",
                                "fr_regime",
                                "fr_extreme_long",
                                "fr_extreme_short",
                                "fr_volatility",
                                "fr_trend_strength",
                                "oi_normalized",
                                "oi_change_1d",
                                "oi_momentum_3d",
                                "oi_zscore_7d",
                                "oi_new_high",
                                "oi_new_low",
                                "position_bias",
                            ]

                            for col in funding_cols:
                                if col in df.columns:
                                    df[col] = df[col].bfill().ffill().fillna(0)
                                    df[col] = df[col].replace(
                                        [float("inf"), float("-inf")], 0
                                    )

                                    # 異常値クリッピング
                                    q975 = df[col].quantile(0.975)
                                    q025 = df[col].quantile(0.025)
                                    if (
                                        pd.notna(q975)
                                        and pd.notna(q025)
                                        and q975 != q025
                                    ):
                                        df[col] = df[col].clip(lower=q025, upper=q975)

                            logger.info(
                                f"Added {len(funding_cols)} Bitbank margin features"
                            )

                        except Exception as e:
                            logger.error(
                                "Failed to add Bitbank margin alternative features: %s",
                                e,
                            )
                            # エラー時はデフォルト値で17特徴量を追加
                            default_cols = [
                                "fr_rate",
                                "fr_change_1d",
                                "fr_change_3d",
                                "fr_zscore_7d",
                                "fr_zscore_30d",
                                "fr_regime",
                                "fr_extreme_long",
                                "fr_extreme_short",
                                "fr_volatility",
                                "fr_trend_strength",
                                "oi_normalized",
                                "oi_change_1d",
                                "oi_momentum_3d",
                                "oi_zscore_7d",
                                "oi_new_high",
                                "oi_new_low",
                                "position_bias",
                            ]
                            for col in default_cols:
                                if col not in df.columns:
                                    df[col] = 0
                            logger.warning(
                                "Used default values for Bitbank margin features"
                            )

                    # Phase B2.5: Fear&Greed特徴量は既にExternalDataIntegratorで処理済み
                    elif base in ["fear_greed", "fg"]:
                        try:
                            logger.info(
                                f"🔍 Processing Fear&Greed features: "
                                f"fear_greed_enabled={self.fear_greed_enabled}, "
                                f"fetcher={self.fear_greed_fetcher is not None}"
                            )

                            fg_features = None

                            # キャッシュからFear&Greedデータを取得（優先）
                            cached_fg = self._get_cached_external_data(
                                "fear_greed", df.index
                            )
                            if not cached_fg.empty:
                                logger.info(
                                    f"✅ Cached Fear&Greed: {len(cached_fg)} records"
                                )
                                fg_features = cached_fg

                            # キャッシュが空の場合、Fear&Greedフェッチャーで直接取得
                            if fg_features is None or fg_features.empty:
                                if self.fear_greed_fetcher:
                                    logger.info("🔍 Fetching fresh Fear&Greed data...")
                                    try:
                                        fg_data = (
                                            self.fear_greed_fetcher.get_fear_greed_data(
                                                days_back=30
                                            )
                                        )
                                        if not fg_data.empty:
                                            logger.info(
                                                f"✅ Fear&Greed: {len(fg_data)} records"
                                            )
                                            calc_func = (
                                                self.fear_greed_fetcher.calculate_fear_greed_features  # noqa: E501
                                            )
                                            fg_features = calc_func(fg_data)
                                        else:
                                            logger.warning(
                                                "❌ Fear&Greed data empty from fetcher"
                                            )
                                    except Exception as e:
                                        logger.error(
                                            f"❌ Fear&Greed fetching failed: {e}"
                                        )
                                else:
                                    logger.warning(
                                        "❌ Fear&Greed fetcher not available"
                                    )

                            # Fear&Greedデータが取得できた場合の処理
                            if fg_features is not None and not fg_features.empty:
                                # キャッシュがない場合は従来の方法
                                fg_data = self.fear_greed_fetcher.get_fear_greed_data(
                                    days_back=30
                                )
                                if not fg_data.empty:
                                    fg_features = self.fear_greed_fetcher.calculate_fear_greed_features(  # noqa: E501
                                        fg_data
                                    )

                                    # VIXとの相関特徴量も追加
                                    if self.vix_fetcher:
                                        try:
                                            vix_data = self.vix_fetcher.get_vix_data(
                                                timeframe="1d"
                                            )
                                            if not vix_data.empty:
                                                vix_fg_correlation = self.fear_greed_fetcher.get_vix_correlation_features(  # noqa: E501
                                                    fg_data, vix_data
                                                )
                                                if not vix_fg_correlation.empty:
                                                    fg_features = pd.concat(
                                                        [
                                                            fg_features,
                                                            vix_fg_correlation,
                                                        ],
                                                        axis=1,
                                                    )
                                                    logger.debug(
                                                        "Added VIX-FG correlation features"  # noqa: E501
                                                    )
                                        except Exception as e:
                                            logger.warning(
                                                f"Failed to add VIX-FG correlation: {e}"
                                            )

                                    # 暗号資産データとFear & Greedデータの時間軸を合わせる
                                    if isinstance(
                                        df.index, pd.DatetimeIndex
                                    ) and isinstance(
                                        fg_features.index, pd.DatetimeIndex
                                    ):
                                        # 日次データなので、暗号資産の時間軸に合わせてリサンプリング
                                        fg_resampled = fg_features.resample(
                                            "1h"
                                        ).ffill()

                                        # インデックスを合わせて結合
                                        common_index = df.index.intersection(
                                            fg_resampled.index
                                        )
                                        logger.debug(
                                            f"Fear & Greed alignment: crypto {len(df)}, fg {len(fg_resampled)}, common {len(common_index)}"  # noqa: E501
                                        )

                                        # 小さなデータチャンクの場合は最新のFear & Greedデータを使用
                                        if len(common_index) == 0 and len(df) > 0:
                                            # Fear & Greedデータが期間外の場合、最新データで全行を埋める
                                            logger.warning(
                                                "Fear & Greed data period mismatch - using latest available data"  # noqa: E501
                                            )

                                            # 最新のFear & Greedデータを取得
                                            if not fg_resampled.empty:
                                                latest_fg_data = fg_resampled.iloc[
                                                    -1
                                                ]  # 最新行
                                                for col in fg_features.columns:
                                                    if col in latest_fg_data.index:
                                                        df[col] = latest_fg_data[col]
                                                logger.debug(
                                                    f"Filled all {len(df)} rows with latest Fear & Greed data"  # noqa: E501
                                                )
                                            else:
                                                # Fear & Greedデータが全くない場合、デフォルト値で埋める
                                                logger.warning(
                                                    "No Fear & Greed data available - using default values"  # noqa: E501
                                                )
                                                for col in fg_features.columns:
                                                    if col == "fg_level":
                                                        df[col] = 50  # 中立値
                                                    elif col == "fg_regime":
                                                        df[col] = 3  # 中立レジーム
                                                    else:
                                                        df[col] = 0  # その他は0
                                        elif len(common_index) > 0:
                                            # Fear & Greed特徴量を追加
                                            for col in fg_features.columns:
                                                if col in fg_resampled.columns:
                                                    df.loc[common_index, col] = (
                                                        fg_resampled.loc[
                                                            common_index, col
                                                        ]
                                                    )

                                            logger.debug(
                                                f"Added Fear & Greed features: {len(common_index)} data points aligned"  # noqa: E501
                                            )
                                        else:
                                            logger.warning(
                                                "Could not align Fear & Greed data with crypto data"  # noqa: E501
                                            )
                                    else:
                                        logger.warning(
                                            "Index type mismatch for Fear & Greed data alignment"  # noqa: E501
                                        )
                                else:
                                    logger.warning(
                                        "No Fear & Greed data available - adding default Fear & Greed features"  # noqa: E501
                                    )
                                    # Fear & Greedデータが取得できない場合、デフォルト特徴量を追加
                                    from crypto_bot.data.fear_greed_fetcher import (
                                        get_available_fear_greed_features,
                                    )

                                    fg_feature_names = (
                                        get_available_fear_greed_features()
                                    )

                                    for col in fg_feature_names:
                                        if col not in df.columns:
                                            if col == "fg_level":
                                                df[col] = 50  # 中立値
                                            elif col == "fg_regime":
                                                df[col] = 3  # 中立レジーム
                                            else:
                                                df[col] = 0  # その他は0
                                    logger.debug(
                                        f"Added {len(fg_feature_names)} default Fear & Greed features"  # noqa: E501
                                    )
                            else:
                                logger.warning(
                                    "Fear & Greed fetcher not initialized - adding default Fear & Greed features"  # noqa: E501
                                )
                                # Fetcherが初期化されていない場合もデフォルト特徴量を追加
                                from crypto_bot.data.fear_greed_fetcher import (
                                    get_available_fear_greed_features,
                                )

                                fg_feature_names = get_available_fear_greed_features()

                                for col in fg_feature_names:
                                    if col not in df.columns:
                                        if col == "fg_level":
                                            df[col] = 50  # 中立値
                                        elif col == "fg_regime":
                                            df[col] = 3  # 中立レジーム
                                        else:
                                            df[col] = 0  # その他は0
                                logger.debug(
                                    f"Added {len(fg_feature_names)} default Fear & Greed features"  # noqa: E501
                                )
                        except Exception as e:
                            logger.warning("Failed to add Fear & Greed features: %s", e)
                            logger.warning(
                                "Adding default Fear & Greed features due to error"
                            )
                            # エラー時もデフォルト特徴量を追加して特徴量数を一致させる
                            try:
                                from crypto_bot.data.fear_greed_fetcher import (
                                    get_available_fear_greed_features,
                                )

                                fg_feature_names = get_available_fear_greed_features()

                                for col in fg_feature_names:
                                    if col not in df.columns:
                                        if col == "fg_level":
                                            df[col] = 50  # 中立値
                                        elif col == "fg_regime":
                                            df[col] = 3  # 中立レジーム
                                        else:
                                            df[col] = 0  # その他は0
                                logger.debug(
                                    f"Added {len(fg_feature_names)} default Fear & Greed features after error"  # noqa: E501
                                )
                            except Exception as inner_e:
                                logger.error(
                                    f"Failed to add default Fear & Greed features: {inner_e}"  # noqa: E501
                                )

                    # mochipoyo_long_signal or mochipoyo_short_signal
                    elif (
                        feat_lc == "mochipoyo_long_signal"
                        or feat_lc == "mochipoyo_short_signal"
                    ):
                        if mochipoyo_signals is not None:
                            for signal_col in mochipoyo_signals.columns:
                                if signal_col not in df:
                                    df[signal_col] = mochipoyo_signals[signal_col]

                    # momentum_14 特徴量
                    elif feat_lc == "momentum_14":
                        df["momentum_14"] = df["close"].pct_change(14).fillna(0)

                    # trend_strength 特徴量
                    elif feat_lc == "trend_strength":
                        # トレンド強度を計算（ADXベース）
                        try:
                            import pandas_ta as ta

                            adx_result = ta.adx(
                                high=df["high"],
                                low=df["low"],
                                close=df["close"],
                                length=14,
                            )

                            if adx_result is not None and not adx_result.empty:
                                # ADXの結果はDataFrameなので、ADX列を取得
                                if (
                                    isinstance(adx_result, pd.DataFrame)
                                    and "ADX_14" in adx_result.columns
                                ):
                                    df["trend_strength"] = adx_result["ADX_14"].fillna(
                                        25
                                    )
                                elif isinstance(adx_result, pd.Series):
                                    df["trend_strength"] = adx_result.fillna(25)
                                else:
                                    df["trend_strength"] = 25
                            else:
                                df["trend_strength"] = 25  # デフォルト値
                        except Exception as e:
                            logger.warning(f"Failed to calculate trend_strength: {e}")
                            df["trend_strength"] = 25  # デフォルト値

                    # volatility_regime 特徴量 (5特徴量)
                    elif feat_lc == "volatility_regime":
                        try:
                            # 複数期間でのボラティリティレジーム分析
                            volatility_windows = [10, 20, 50]

                            for window in volatility_windows:
                                # rolling標準偏差を計算
                                vol = df["close"].rolling(window=window).std()

                                # ボラティリティレジームを3段階に分類 (0:低, 1:中, 2:高)
                                vol_regime = pd.cut(vol, bins=3, labels=[0, 1, 2])
                                df[f"vol_regime_{window}"] = pd.to_numeric(
                                    vol_regime, errors="coerce"
                                ).fillna(1)

                                # ボラティリティ百分位数
                                df[f"vol_percentile_{window}"] = (
                                    vol.rolling(window=100, min_periods=window)
                                    .rank(pct=True)
                                    .fillna(0.5)
                                )

                            # 短期vs長期ボラティリティ比率
                            short_vol = df["close"].rolling(window=10).std()
                            long_vol = df["close"].rolling(window=50).std()
                            df["vol_ratio_short_long"] = (short_vol / long_vol).fillna(
                                1.0
                            )

                        except Exception as e:
                            logger.warning(
                                f"Failed to calculate volatility_regime: {e}"
                            )
                            # デフォルト値設定
                            for window in [10, 20, 50]:
                                df[f"vol_regime_{window}"] = 1
                                df[f"vol_percentile_{window}"] = 0.5
                            df["vol_ratio_short_long"] = 1.0

                    # momentum_signals 特徴量 (7特徴量)
                    elif feat_lc == "momentum_signals":
                        try:
                            # 複数期間のモメンタム信号
                            momentum_periods = [1, 3, 7, 14, 21, 30]

                            for period in momentum_periods:
                                df[f"momentum_{period}"] = (
                                    df["close"].pct_change(period).fillna(0)
                                )

                            # モメンタム収束・発散指標
                            mom_short = df["close"].pct_change(3)
                            mom_long = df["close"].pct_change(21)
                            df["momentum_convergence"] = (mom_short - mom_long).fillna(
                                0
                            )

                        except Exception as e:
                            logger.warning(f"Failed to calculate momentum_signals: {e}")
                            # デフォルト値設定
                            for period in [1, 3, 7, 14, 21, 30]:
                                df[f"momentum_{period}"] = 0
                            df["momentum_convergence"] = 0

                    # liquidity_indicators 特徴量 (8特徴量)
                    elif feat_lc == "liquidity_indicators":
                        try:
                            # Amihud流動性指標（非流動性度）
                            price_change = abs(df["close"].pct_change())
                            volume_scaled = (
                                df["volume"] / df["volume"].rolling(window=20).mean()
                            )
                            df["amihud_illiquidity"] = (
                                price_change / (volume_scaled + 1e-8)
                            ).fillna(0)

                            # 価格インパクト指標
                            df["price_impact"] = (
                                (df["high"] - df["low"]) / (df["volume"] + 1e-8)
                            ).fillna(0)

                            # ボリューム・プライス・トレンド（VPT）
                            df["vpt"] = (
                                (df["volume"] * df["close"].pct_change())
                                .cumsum()
                                .fillna(0)
                            )

                            # 出来高相対強度
                            df["volume_strength"] = (
                                df["volume"] / df["volume"].rolling(window=20).mean()
                            ).fillna(1.0)

                            # 流動性枯渇指標
                            volume_ma = df["volume"].rolling(window=10).mean()
                            volume_std = df["volume"].rolling(window=10).std()
                            df["liquidity_drought"] = (
                                (volume_ma - df["volume"]) / (volume_std + 1e-8)
                            ).fillna(0)

                            # ビッド・アスク代理指標（高値-安値スプレッド）
                            typical_price = (df["high"] + df["low"] + df["close"]) / 3
                            df["spread_proxy"] = (
                                (df["high"] - df["low"]) / typical_price
                            ).fillna(0)

                            # 出来高加重平均価格からの乖離
                            vwap = (typical_price * df["volume"]).rolling(
                                window=20
                            ).sum() / df["volume"].rolling(window=20).sum()
                            df["vwap_deviation"] = ((df["close"] - vwap) / vwap).fillna(
                                0
                            )

                            # 注文不均衡代理指標
                            df["order_imbalance_proxy"] = (
                                (df["close"] - df["open"])
                                / (df["high"] - df["low"] + 1e-8)
                            ).fillna(0)

                        except Exception as e:
                            logger.warning(
                                f"Failed to calculate liquidity_indicators: {e}"
                            )
                            # デフォルト値設定
                            liquidity_features = [
                                "amihud_illiquidity",
                                "price_impact",
                                "vpt",
                                "volume_strength",
                                "liquidity_drought",
                                "spread_proxy",
                                "vwap_deviation",
                                "order_imbalance_proxy",
                            ]
                            for feat in liquidity_features:
                                df[feat] = 0

                    # Phase 3.2A: 追加ATR期間（atr_7, atr_21）
                    elif base == "atr" and period and period != self.feat_period:
                        atr_calc = self.ind_calc.atr(df, window=period)
                        if isinstance(atr_calc, pd.Series):
                            df[f"atr_{period}"] = atr_calc
                        else:
                            df[f"atr_{period}"] = atr_calc.iloc[:, 0]

                    # Phase 3.2B: 価格ポジション指標（5特徴量）
                    elif feat_lc == "price_position":
                        try:
                            # 価格レンジ内の位置（%Kスタイル）
                            high_20 = df["high"].rolling(20).max()
                            low_20 = df["low"].rolling(20).min()
                            df["price_position_20"] = (
                                (df["close"] - low_20) / (high_20 - low_20 + 1e-8)
                            ).fillna(0.5)

                            # 異なる期間での価格位置
                            high_50 = df["high"].rolling(50).max()
                            low_50 = df["low"].rolling(50).min()
                            df["price_position_50"] = (
                                (df["close"] - low_50) / (high_50 - low_50 + 1e-8)
                            ).fillna(0.5)

                            # 移動平均からの位置
                            sma_20 = df["close"].rolling(20).mean()
                            df["price_vs_sma20"] = (
                                (df["close"] - sma_20) / sma_20
                            ).fillna(0)

                            # ボリンジャーバンド内位置（%B）
                            bb_middle = df["close"].rolling(20).mean()
                            bb_std = df["close"].rolling(20).std()
                            bb_upper = bb_middle + (bb_std * 2)
                            bb_lower = bb_middle - (bb_std * 2)
                            df["bb_position"] = (
                                (df["close"] - bb_lower) / (bb_upper - bb_lower + 1e-8)
                            ).fillna(0.5)

                            # 日中レンジ内位置
                            df["intraday_position"] = (
                                (df["close"] - df["low"])
                                / (df["high"] - df["low"] + 1e-8)
                            ).fillna(0.5)

                        except Exception as e:
                            logger.warning(f"Failed to calculate price_position: {e}")
                            for i in range(5):
                                df[f"price_pos_{i}"] = 0.5

                    # Phase 3.2B: ローソク足パターン（4特徴量）
                    elif feat_lc == "candle_patterns":
                        try:
                            # ドジ（十字線）
                            body_size = abs(df["close"] - df["open"])
                            candle_range = df["high"] - df["low"]
                            df["doji"] = (
                                body_size / (candle_range + 1e-8) < 0.1
                            ).astype(int)

                            # ハンマー/ハンギングマン
                            upper_shadow = df["high"] - np.maximum(
                                df["open"], df["close"]
                            )
                            lower_shadow = (
                                np.minimum(df["open"], df["close"]) - df["low"]
                            )
                            df["hammer"] = (
                                (lower_shadow > body_size * 2)
                                & (upper_shadow < body_size * 0.5)
                            ).astype(int)

                            # エンゴルフィングパターン
                            prev_body = abs(df["close"].shift(1) - df["open"].shift(1))
                            curr_body = abs(df["close"] - df["open"])
                            df["engulfing"] = (
                                (curr_body > prev_body * 1.5)
                                & (df["close"] > df["open"])  # 現在のローソクが陽線
                                & (
                                    df["close"].shift(1) < df["open"].shift(1)
                                )  # 前のローソクが陰線
                            ).astype(int)

                            # ピンバー（上ヒゲ・下ヒゲ）
                            df["pinbar"] = (
                                (upper_shadow > body_size * 3)
                                | (lower_shadow > body_size * 3)
                            ).astype(int)

                        except Exception as e:
                            logger.warning(f"Failed to calculate candle_patterns: {e}")
                            for pattern in ["doji", "hammer", "engulfing", "pinbar"]:
                                df[pattern] = 0

                    # Phase 3.2B: サポート・レジスタンス（3特徴量）
                    elif feat_lc == "support_resistance":
                        try:
                            # サポートレベルからの距離
                            support_level = df["low"].rolling(50).min()
                            df["support_distance"] = (
                                (df["close"] - support_level) / support_level
                            ).fillna(0)

                            # レジスタンスレベルからの距離
                            resistance_level = df["high"].rolling(50).max()
                            df["resistance_distance"] = (
                                (resistance_level - df["close"]) / resistance_level
                            ).fillna(0)

                            # サポート・レジスタンスレベルの強度
                            support_tests = (
                                df["low"]
                                .rolling(10)
                                .apply(lambda x: (x <= x.min() * 1.02).sum())
                            )
                            df["support_strength"] = support_tests.fillna(0)

                        except Exception as e:
                            logger.warning(
                                f"Failed to calculate support_resistance: {e}"
                            )
                            for sr in [
                                "support_distance",
                                "resistance_distance",
                                "support_strength",
                            ]:
                                df[sr] = 0

                    # Phase 3.2B: ブレイクアウトシグナル（3特徴量）
                    elif feat_lc == "breakout_signals":
                        try:
                            # ボリュームブレイクアウト
                            volume_ma = df["volume"].rolling(20).mean()
                            price_change = abs(df["close"].pct_change())
                            df["volume_breakout"] = (
                                (df["volume"] > volume_ma * 2)
                                & (
                                    price_change
                                    > price_change.rolling(20).quantile(0.8)
                                )
                            ).astype(int)

                            # 価格ブレイクアウト（レンジ上放れ）
                            high_20 = df["high"].rolling(20).max()
                            df["price_breakout_up"] = (
                                df["close"] > high_20.shift(1)
                            ).astype(int)

                            # 価格ブレイクダウン（レンジ下放れ）
                            low_20 = df["low"].rolling(20).min()
                            df["price_breakout_down"] = (
                                df["close"] < low_20.shift(1)
                            ).astype(int)

                        except Exception as e:
                            logger.warning(f"Failed to calculate breakout_signals: {e}")
                            for bo in [
                                "volume_breakout",
                                "price_breakout_up",
                                "price_breakout_down",
                            ]:
                                df[bo] = 0

                    # Phase 3.2C: 自己相関（5特徴量）
                    elif feat_lc == "autocorrelation":
                        try:
                            returns = df["close"].pct_change()
                            for lag in [1, 5, 10, 20, 50]:
                                df[f"autocorr_lag_{lag}"] = (
                                    returns.rolling(100).apply(
                                        lambda x: (
                                            x.autocorr(lag=lag) if len(x) > lag else 0
                                        )
                                    )
                                ).fillna(0)
                        except Exception as e:
                            logger.warning(f"Failed to calculate autocorrelation: {e}")
                            for lag in [1, 5, 10, 20, 50]:
                                df[f"autocorr_lag_{lag}"] = 0

                    # Phase 3.2C: 季節性パターン（4特徴量）
                    elif feat_lc == "seasonal_patterns":
                        try:
                            if isinstance(df.index, pd.DatetimeIndex):
                                # 曜日効果
                                df["weekday_effect"] = df.index.dayofweek.astype(float)
                                # 時間帯効果
                                df["hour_effect"] = df.index.hour.astype(float)
                                # 月初月末効果
                                df["month_day_effect"] = df.index.day.astype(float)
                                # アジア時間・欧米時間区分
                                asia_hours = (
                                    (df.index.hour >= 0) & (df.index.hour < 8)
                                ).astype(int)
                                df["asia_session"] = asia_hours
                            else:
                                for feat in [
                                    "weekday_effect",
                                    "hour_effect",
                                    "month_day_effect",
                                    "asia_session",
                                ]:
                                    df[feat] = 0
                        except Exception as e:
                            logger.warning(
                                f"Failed to calculate seasonal_patterns: {e}"
                            )
                            for feat in [
                                "weekday_effect",
                                "hour_effect",
                                "month_day_effect",
                                "asia_session",
                            ]:
                                df[feat] = 0

                    # Phase 3.2C: レジーム検出（3特徴量）
                    elif feat_lc == "regime_detection":
                        try:
                            returns = df["close"].pct_change()
                            vol = returns.rolling(20).std()

                            # 高ボラティリティレジーム
                            vol_threshold = vol.rolling(100).quantile(0.8)
                            df["high_vol_regime"] = (vol > vol_threshold).astype(int)

                            # トレンドレジーム（上昇・下降・横ばい）
                            price_ma_short = df["close"].rolling(10).mean()
                            price_ma_long = df["close"].rolling(50).mean()
                            trend_strength = (
                                price_ma_short - price_ma_long
                            ) / price_ma_long
                            df["trend_regime"] = np.where(
                                trend_strength > 0.02,
                                1,  # 上昇トレンド
                                np.where(
                                    trend_strength < -0.02, -1, 0
                                ),  # 下降トレンド vs 横ばい
                            )

                            # モメンタムレジーム
                            momentum = returns.rolling(14).mean()
                            df["momentum_regime"] = np.where(
                                momentum > momentum.rolling(100).quantile(0.8),
                                1,
                                np.where(
                                    momentum < momentum.rolling(100).quantile(0.2),
                                    -1,
                                    0,
                                ),
                            )

                        except Exception as e:
                            logger.warning(f"Failed to calculate regime_detection: {e}")
                            for regime in [
                                "high_vol_regime",
                                "trend_regime",
                                "momentum_regime",
                            ]:
                                df[regime] = 0

                    # Phase 3.2C: サイクル分析（3特徴量）
                    elif feat_lc == "cycle_analysis":
                        try:
                            # 価格サイクル（デトレンド価格）
                            price_ma = df["close"].rolling(50).mean()
                            df["price_cycle"] = (
                                (df["close"] - price_ma) / price_ma
                            ).fillna(0)

                            # ボリュームサイクル
                            volume_ma = df["volume"].rolling(50).mean()
                            df["volume_cycle"] = (
                                (df["volume"] - volume_ma) / volume_ma
                            ).fillna(0)

                            # RSIサイクル（過買い過売りサイクル）
                            rsi = self.ind_calc.rsi(df["close"], window=14)
                            df["rsi_cycle"] = ((rsi - 50) / 50).fillna(0)

                        except Exception as e:
                            logger.warning(f"Failed to calculate cycle_analysis: {e}")
                            for cycle in ["price_cycle", "volume_cycle", "rsi_cycle"]:
                                df[cycle] = 0

                    # Phase 3.2D: クロス相関（5特徴量）
                    elif feat_lc == "cross_correlation":
                        try:
                            returns = df["close"].pct_change()
                            volume_returns = df["volume"].pct_change()

                            # 価格-ボリューム相関
                            for window in [10, 20, 50]:
                                df[f"price_volume_corr_{window}"] = (
                                    returns.rolling(window).corr(volume_returns)
                                ).fillna(0)

                            # 高値-低値相関（ボラティリティ構造）
                            high_returns = df["high"].pct_change()
                            low_returns = df["low"].pct_change()
                            df["high_low_corr_20"] = (
                                high_returns.rolling(20).corr(low_returns)
                            ).fillna(0)

                            # 価格ラグ相関（自己相関簡易版）
                            df["price_lag_corr"] = (
                                returns.rolling(30).corr(returns.shift(1))
                            ).fillna(0)

                        except Exception as e:
                            logger.warning(
                                f"Failed to calculate cross_correlation: {e}"
                            )
                            corr_features = [
                                "price_volume_corr_10",
                                "price_volume_corr_20",
                                "price_volume_corr_50",
                                "high_low_corr_20",
                                "price_lag_corr",
                            ]
                            for feat in corr_features:
                                df[feat] = 0

                    # Phase 3.2D: 相対強度（5特徴量）
                    elif feat_lc == "relative_strength":
                        try:
                            # 短期 vs 長期相対強度
                            short_ma = df["close"].rolling(10).mean()
                            long_ma = df["close"].rolling(50).mean()
                            df["short_long_strength"] = (
                                (short_ma - long_ma) / long_ma
                            ).fillna(0)

                            # ボリューム相対強度
                            volume_short = df["volume"].rolling(10).mean()
                            volume_long = df["volume"].rolling(50).mean()
                            df["volume_relative_strength"] = (
                                (volume_short - volume_long) / volume_long
                            ).fillna(0)

                            # ボラティリティ相対強度
                            vol_short = df["close"].pct_change().rolling(10).std()
                            vol_long = df["close"].pct_change().rolling(50).std()
                            df["volatility_relative_strength"] = (
                                (vol_short - vol_long) / vol_long
                            ).fillna(0)

                            # 価格動勉相対強度
                            momentum_short = df["close"].pct_change(5)
                            momentum_long = df["close"].pct_change(20)
                            df["momentum_relative_strength"] = (
                                momentum_short - momentum_long
                            ).fillna(0)

                            # RSI相対強度
                            rsi_14 = self.ind_calc.rsi(df["close"], window=14)
                            rsi_7 = self.ind_calc.rsi(df["close"], window=7)
                            df["rsi_relative_strength"] = (rsi_7 - rsi_14).fillna(0)

                        except Exception as e:
                            logger.warning(
                                f"Failed to calculate relative_strength: {e}"
                            )
                            rs_features = [
                                "short_long_strength",
                                "volume_relative_strength",
                                "volatility_relative_strength",
                                "momentum_relative_strength",
                                "rsi_relative_strength",
                            ]
                            for feat in rs_features:
                                df[feat] = 0

                    # Phase 3.2D: スプレッド分析（5特徴量）
                    elif feat_lc == "spread_analysis":
                        try:
                            # 高値-低値スプレッド
                            hl_spread = (df["high"] - df["low"]) / df["close"]
                            df["hl_spread"] = hl_spread.fillna(0)
                            df["hl_spread_ma"] = hl_spread.rolling(20).mean().fillna(0)

                            # 始値-終値スプレッド
                            oc_spread = abs(df["open"] - df["close"]) / df["close"]
                            df["oc_spread"] = oc_spread.fillna(0)

                            # ボラティリティスプレッド（短期 vs 長期）
                            vol_short = df["close"].pct_change().rolling(5).std()
                            vol_long = df["close"].pct_change().rolling(20).std()
                            df["volatility_spread"] = (vol_short - vol_long).fillna(0)

                            # タイムスプレッド（連続期間の価格差）
                            df["time_spread"] = (
                                df["close"] - df["close"].shift(24)
                            ).fillna(
                                0
                            )  # 24時間前との差

                        except Exception as e:
                            logger.warning(f"Failed to calculate spread_analysis: {e}")
                            spread_features = [
                                "hl_spread",
                                "hl_spread_ma",
                                "oc_spread",
                                "volatility_spread",
                                "time_spread",
                            ]
                            for feat in spread_features:
                                df[feat] = 0

                    else:
                        logger.warning(f"Unknown extra feature spec: {feat} - skipping")

                except Exception as e:
                    logger.error("Failed to add extra feature %s: %s", feat, e)
                    raise  # 失敗したら握りつぶさず停止する
            logger.debug("After extra feats: %s", df.shape)

        # 6. 欠損再補完＋0埋め
        df = df.ffill().fillna(0)

        # 7. 無限大値・異常値のクリーニング
        # 無限大値を前の有効値で置換、それも無い場合は0
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.ffill().fillna(0)

        # 異常に大きな値をクリップ（オーバーフロー防止）
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            # 99.9%ile以上の値をクリップ
            upper_bound = df[col].quantile(0.999)
            lower_bound = df[col].quantile(0.001)

            if np.isfinite(upper_bound) and np.isfinite(lower_bound):
                df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)

        logger.debug("Final features shape after cleaning: %s", df.shape)

        # データ品質管理システム（勝率改善のための重要なステップ）
        try:
            from crypto_bot.ml.data_quality_manager import DataQualityManager

            quality_manager = DataQualityManager(self.config)

            # メタデータ作成（外部データソース情報）
            metadata = {
                "feature_sources": {},
                "external_data_enabled": {
                    "vix": self.vix_enabled,
                    "macro": self.macro_enabled,
                    "fear_greed": self.fear_greed_enabled,
                    "funding": self.funding_enabled,
                },
            }

            # 各特徴量のソース情報を記録
            for column in df.columns:
                vix_prefixes = ["vix_", "dxy_", "treasury_"]
                if any(column.startswith(prefix) for prefix in vix_prefixes):
                    source_type = "api" if self.macro_enabled else "default"
                    metadata["feature_sources"][column] = {"source_type": source_type}
                elif any(column.startswith(prefix) for prefix in ["fear_greed", "fg_"]):
                    source_type = "api" if self.fear_greed_enabled else "default"
                    metadata["feature_sources"][column] = {"source_type": source_type}
                elif any(column.startswith(prefix) for prefix in ["fr_", "oi_"]):
                    # Bitbank代替特徴量
                    metadata["feature_sources"][column] = {"source_type": "calculated"}
                else:
                    metadata["feature_sources"][column] = {"source_type": "calculated"}

            # データ品質検証
            quality_passed, quality_report = quality_manager.validate_data_quality(
                df, metadata
            )

            if not quality_passed:
                logger.warning(f"Data quality check failed: {quality_report}")

                # データ品質改善を試行
                df_improved, improvement_report = quality_manager.improve_data_quality(
                    df, metadata
                )
                df = df_improved

                logger.info(f"Data quality improvement applied: {improvement_report}")
            else:
                score = quality_report["quality_score"]
                logger.info(f"Data quality check passed: score={score:.1f}")

        except Exception as e:
            logger.warning(
                f"Data quality management failed: {e} - continuing with original data"
            )

        # Phase B2.4: バッチ処理完了後の最終処理
        if self.batch_engines_enabled:
            logger.info("🔄 Batch processing completed - performing final validation")

        # 125特徴量の確実な保証（最終チェック）Phase H.25
        from crypto_bot.ml.feature_defaults import ensure_feature_consistency

        df = ensure_feature_consistency(
            df, target_count=125
        )  # Phase H.25: 125特徴量に統一（外部API除外）
        logger.info(f"Final guaranteed feature count: {len(df.columns)}")

        return df


def build_ml_pipeline(config: Dict[str, Any]) -> Pipeline:
    """
    sklearnパイプライン化（特徴量生成→標準化）。
    空のDataFrameの場合は、特徴量生成のみを行い、標準化はスキップする。
    """

    class EmptyDataFrameScaler(BaseEstimator, TransformerMixin):
        """空のDataFrameの場合のダミースケーラー"""

        def fit(self, X, y=None):
            return self

        def transform(self, X):
            return X

    class EmptyDataFramePipeline(Pipeline):
        """空のDataFrameの場合のパイプライン"""

        def fit_transform(self, X, y=None, **fit_params):
            if X.empty:
                # 空のDataFrameの場合は、特徴量生成のみを行い、標準化はスキップ
                features = self.named_steps["features"].transform(X)
                # DataFrameをnumpy.ndarrayに変換
                return features.values
            return super().fit_transform(X, y, **fit_params)

        def transform(self, X):
            if X.empty:
                # 空のDataFrameの場合は、特徴量生成のみを行い、標準化はスキップ
                features = self.named_steps["features"].transform(X)
                # DataFrameをnumpy.ndarrayに変換
                return features.values
            return super().transform(X)

    return EmptyDataFramePipeline(
        [
            ("features", FeatureEngineer(config)),
            (
                "scaler",
                (
                    EmptyDataFrameScaler()
                    if config.get("skip_scaling", False)
                    else StandardScaler()
                ),
            ),
        ]
    )


def prepare_ml_dataset(
    df: pd.DataFrame, config: Dict[str, Any]
) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    機械学習用データセットを作成。
    戻り値: X（特徴量）, y_reg（回帰ターゲット）, y_clf（分類ターゲット）

    - 必要なぶんだけ最初の行をドロップ（rolling/lags）
    - horizon, thresholdはconfig["ml"]から取得
    """
    logger.info(f"prepare_ml_dataset input df shape: {tuple(df.shape)}")
    pipeline = build_ml_pipeline(config)
    X_arr = pipeline.fit_transform(df)

    logger.info(f"Pipeline output type: {type(X_arr)}")
    if hasattr(X_arr, "shape"):
        shape_info = X_arr.shape
    elif hasattr(X_arr, "__len__"):
        shape_info = len(X_arr)
    else:
        shape_info = "no len"

    logger.info(f"Pipeline output shape/len: {shape_info}")

    # X_arrがlistの場合はnumpy arrayに変換
    if isinstance(X_arr, list):
        logger.warning(
            f"Pipeline returned list with {len(X_arr)} elements, converting to numpy array"  # noqa: E501
        )
        import numpy as np

        try:
            X_arr = np.array(X_arr)
        except Exception as e:
            logger.error(f"Failed to convert list to numpy array: {e}")
            # If conversion fails, return the list directly for debugging
            return X_arr

    # ----- 目的変数生成 -----
    horizon = config["ml"]["horizon"]
    thresh = config["ml"].get("threshold", 0.0)
    y_reg = make_regression_target(df, horizon).rename(f"return_{horizon}")
    y_clf = make_classification_target(df, horizon, thresh).rename(f"up_{horizon}")

    # ----- 行数を揃える -----
    win = config["ml"]["rolling_window"]
    lags = config["ml"]["lags"]
    drop_n = win + max(lags) if lags else win

    idx = df.index[drop_n:]
    X = pd.DataFrame(X_arr[drop_n:], index=idx)

    return X, y_reg.loc[idx], y_clf.loc[idx]


# Phase H.11: 特徴量完全性保証システム統合
def prepare_ml_dataset_enhanced(
    df: pd.DataFrame, config: Dict[str, Any]
) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    特徴量完全性保証付きML用データセット作成

    Args:
        df: OHLCVデータ
        config: 設定辞書

    Returns:
        (特徴量DataFrame, 回帰ターゲット, 分類ターゲット)
    """
    logger.info("🚀 [ENHANCED-ML] Starting enhanced ML dataset preparation...")
    logger.info(f"📊 [ENHANCED-ML] Input shape: {tuple(df.shape)}")

    # Phase H.11: 特徴量完全性保証実行
    if ENHANCED_FEATURES_AVAILABLE:
        logger.info("✅ [ENHANCED-ML] Using enhanced feature engineering system")
        enhanced_df, feature_report = enhance_feature_engineering(df, config)

        # 特徴量レポートの出力
        logger.info("📋 [ENHANCED-ML] Feature completeness report:")
        logger.info(
            f"   - Implementation rate: {feature_report['audit_result']['implementation_rate']:.1%}"
        )
        logger.info(
            f"   - Generated features: {len(feature_report['generated_features'])}"
        )
        logger.info(f"   - Final features: {feature_report['final_feature_count']}")
        logger.info(
            f"   - Completeness rate: {feature_report['completeness_rate']:.1%}"
        )

        # 品質の低い特徴量の警告
        low_quality_features = [
            f for f, score in feature_report["quality_scores"].items() if score < 0.5
        ]
        if low_quality_features:
            logger.warning(
                f"⚠️ [ENHANCED-ML] Low quality features ({len(low_quality_features)}): {low_quality_features[:5]}..."
            )

        # 強化されたDataFrameを使用してML処理継続
        logger.info(f"📊 [ENHANCED-ML] Enhanced shape: {tuple(enhanced_df.shape)}")
        result_df = enhanced_df
    else:
        logger.warning(
            "⚠️ [ENHANCED-ML] Enhanced features not available, falling back to standard processing"
        )
        result_df = df

    # 標準のML処理パイプライン実行
    pipeline = build_ml_pipeline(config)
    X_arr = pipeline.fit_transform(result_df)

    logger.info(
        f"🔧 [ENHANCED-ML] Pipeline output shape: {tuple(X_arr.shape) if hasattr(X_arr, 'shape') else len(X_arr)}"
    )

    # X_arrがlistの場合はnumpy arrayに変換
    if isinstance(X_arr, list):
        logger.warning("🔄 [ENHANCED-ML] Converting list to numpy array")
        import numpy as np

        try:
            X_arr = np.array(X_arr)
        except Exception as e:
            logger.error(f"❌ [ENHANCED-ML] Array conversion failed: {e}")
            return X_arr, None, None

    # 目的変数生成
    horizon = config["ml"]["horizon"]
    thresh = config["ml"].get("threshold", 0.0)
    y_reg = make_regression_target(result_df, horizon).rename(f"return_{horizon}")
    y_clf = make_classification_target(result_df, horizon, thresh).rename(
        f"up_{horizon}"
    )

    # 行数調整
    win = config["ml"]["rolling_window"]
    lags = config["ml"]["lags"]
    drop_n = win + max(lags) if lags else win

    idx = result_df.index[drop_n:]
    X = pd.DataFrame(X_arr[drop_n:], index=idx)

    logger.info(
        f"✅ [ENHANCED-ML] Enhanced ML dataset ready: X{tuple(X.shape)}, y_reg{tuple(y_reg.loc[idx].shape)}, y_clf{tuple(y_clf.loc[idx].shape)}"
    )

    return X, y_reg.loc[idx], y_clf.loc[idx]


def ensure_feature_coverage(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    設定ファイルの特徴量カバレッジ確保

    Args:
        config: 設定辞書

    Returns:
        特徴量カバレッジ保証済み設定辞書
    """
    if not ENHANCED_FEATURES_AVAILABLE:
        logger.warning("⚠️ Enhanced feature engineering not available")
        return config

    logger.info("🔍 [COVERAGE] Ensuring feature coverage in configuration...")

    enhanced_config = config.copy()

    # ML設定から要求特徴量を取得
    ml_features = config.get("ml", {}).get("extra_features", [])
    strategy_features = (
        config.get("strategy", {})
        .get("params", {})
        .get("ml", {})
        .get("extra_features", [])
    )

    all_features = list(set(ml_features + strategy_features))

    if not all_features:
        logger.warning("⚠️ [COVERAGE] No features specified in configuration")
        return enhanced_config

    # 特徴量実装監査
    enhancer = FeatureEngineeringEnhanced()
    audit_result = enhancer.audit_feature_implementation(all_features)

    # 未実装特徴量の警告とフォールバック設定
    if audit_result["missing"]:
        logger.warning(
            f"⚠️ [COVERAGE] Unimplemented features detected ({len(audit_result['missing'])})"
        )
        logger.info(
            f"   Missing: {audit_result['missing'][:10]}..."
        )  # 最初の10個を表示

        # フォールバック設定を追加
        enhanced_config.setdefault("feature_fallback", {})
        enhanced_config["feature_fallback"]["auto_generate_missing"] = True
        enhanced_config["feature_fallback"]["missing_features"] = audit_result[
            "missing"
        ]

    # 外部データ依存特徴量の設定確認
    if audit_result["external_dependent"]:
        logger.info(
            f"📡 [COVERAGE] External data features ({len(audit_result['external_dependent'])})"
        )

        # 外部データ設定の存在確認
        external_config = enhanced_config.get("ml", {}).get("external_data", {})
        if not external_config.get("enabled", False):
            logger.warning(
                "⚠️ [COVERAGE] External data features requested but external_data not enabled"
            )
            enhanced_config.setdefault("ml", {}).setdefault("external_data", {})[
                "enabled"
            ] = True

    logger.info("✅ [COVERAGE] Feature coverage ensured:")
    logger.info(f"   - Implementation rate: {audit_result['implementation_rate']:.1%}")
    logger.info(f"   - Total features: {audit_result['total_requested']}")
    logger.info(f"   - Implemented: {len(audit_result['implemented'])}")
    logger.info(f"   - Missing: {len(audit_result['missing'])}")

    return enhanced_config

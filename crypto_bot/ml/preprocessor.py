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
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

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

        # VIX統合設定
        logger.info(f"🔍 VIX Debug: extra_features={self.extra_features}")
        logger.info(f"🔍 VIX Debug: VIX_AVAILABLE={VIX_AVAILABLE}")
        vix_in_features = "vix" in self.extra_features
        logger.info(f"🔍 VIX Debug: vix_in_features={vix_in_features}")
        self.vix_enabled = vix_in_features and VIX_AVAILABLE
        logger.info(f"🔍 VIX Debug: vix_enabled={self.vix_enabled}")
        
        if self.vix_enabled and VIX_AVAILABLE:
            try:
                self.vix_fetcher = VIXDataFetcher()
                logger.info("✅ VIX fetcher initialized successfully")
            except Exception as e:
                logger.error(f"❌ VIX fetcher initialization failed: {e}")
                self.vix_fetcher = None
        else:
            self.vix_fetcher = None
            logger.warning(f"⚠️ VIX fetcher not initialized: vix_enabled={self.vix_enabled}, VIX_AVAILABLE={VIX_AVAILABLE}")

        # マクロデータ統合設定
        self.macro_enabled = (
            any(feat in self.extra_features for feat in ["dxy", "macro", "treasury"])
            and MACRO_AVAILABLE
        )
        if self.macro_enabled and MACRO_AVAILABLE:
            self.macro_fetcher = MacroDataFetcher()
        else:
            self.macro_fetcher = None

        # Funding Rate統合設定（Bitbank専用：現物取引のため無効化）
        self.funding_enabled = False
        self.funding_fetcher = None

        # Bitbank現物取引では代替特徴量を使用
        self.funding_alternative_enabled = any(
            feat in self.extra_features for feat in ["funding", "oi"]
        )

        # Fear & Greed統合設定
        self.fear_greed_enabled = (
            any(feat in self.extra_features for feat in ["fear_greed", "fg"])
            and FEAR_GREED_AVAILABLE
        )
        if self.fear_greed_enabled and FEAR_GREED_AVAILABLE:
            self.fear_greed_fetcher = FearGreedDataFetcher()
        else:
            self.fear_greed_fetcher = None

    def _get_cached_external_data(
        self, data_type: str, time_index: pd.DatetimeIndex
    ) -> pd.DataFrame:
        """
        キャッシュから外部データを取得

        Parameters
        ----------
        data_type : str
            データタイプ ('vix', 'macro', 'fear_greed', 'funding')
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

    def fit(self, X: pd.DataFrame, y=None):
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        logger.debug("Input DataFrame shape: %s", X.shape)
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
                elif feat_lc in ["mochipoyo_long_signal", "mochipoyo_short_signal"]:
                    columns.extend(["mochipoyo_long_signal", "mochipoyo_short_signal"])
            return pd.DataFrame(columns=columns)
        df = X.copy()

        # 1. 欠損補完
        df = df.ffill()
        logger.debug("After ffill: %s", df.shape)

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

        # 5. extra_features
        if self.extra_features:
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

                    # RSI
                    if base == "rsi" and period:
                        df[f"rsi_{period}"] = self.ind_calc.rsi(
                            df["close"], window=period
                        )
                    # EMA
                    elif base == "ema" and period:
                        df[f"ema_{period}"] = self.ind_calc.ema(
                            df["close"], window=period
                        )
                    # SMA
                    elif base == "sma" and period:
                        df[f"sma_{period}"] = self.ind_calc.sma(
                            df["close"], window=period
                        )
                    # MACD
                    elif base == "macd":
                        try:
                            macd_df = self.ind_calc.macd(df["close"])
                            # 列名をテストの期待値に合わせる
                            df["macd"] = macd_df["MACD_12_26_9"]
                            df["macd_signal"] = macd_df["MACDs_12_26_9"]
                            df["macd_hist"] = macd_df["MACDh_12_26_9"]
                        except Exception as e:
                            logger.error("Failed to add extra feature macd: %s", e)
                            raise
                    # RCI
                    elif base == "rci" and period:
                        try:
                            # まずはIndicatorCalculatorで提供されていればそちら優先
                            if hasattr(self.ind_calc, "rci"):
                                df[f"rci_{period}"] = self.ind_calc.rci(
                                    df["close"], window=period
                                )
                            else:
                                df[f"rci_{period}"] = calc_rci(df["close"], period)
                        except Exception as e:
                            logger.error(
                                "Failed to add extra feature rci_%s: %s", period, e
                            )
                            raise
                    # volume_zscore
                    elif base == "volume" and "zscore" in feat_lc:
                        # volume_zscore_20 のような形式から期間を抽出
                        period_str = feat_lc.split("_")[-1]
                        win_z = (
                            int(period_str)
                            if period_str.isdigit()
                            else self.config["ml"]["rolling_window"]
                        )
                        vol = df["volume"]
                        df[f"volume_zscore_{win_z}"] = (
                            vol - vol.rolling(win_z).mean()
                        ) / vol.rolling(win_z).std()
                    # 曜日・時間
                    elif feat_lc == "day_of_week":
                        if isinstance(df.index, pd.DatetimeIndex):
                            df["day_of_week"] = df.index.dayofweek.astype("int8")
                        else:
                            # 空のDataFrameやDatetimeIndexでない場合は0で埋める
                            df["day_of_week"] = 0
                    elif feat_lc == "hour_of_day":
                        if isinstance(df.index, pd.DatetimeIndex):
                            df["hour_of_day"] = df.index.hour.astype("int8")
                        else:
                            # 空のDataFrameやDatetimeIndexでない場合は0で埋める
                            df["hour_of_day"] = 0
                    # ストキャスティクス
                    elif base == "stoch":
                        try:
                            stoch_df = self.ind_calc.stochastic(df)
                            if not stoch_df.empty:
                                df["stoch_k"] = stoch_df.iloc[:, 0]
                                df["stoch_d"] = stoch_df.iloc[:, 1]
                        except Exception as e:
                            logger.warning("Failed to add stochastic: %s", e)

                    # ボリンジャーバンド
                    elif base == "bb" or base == "bollinger":
                        try:
                            bb_df = self.ind_calc.bollinger_bands(df["close"])
                            if not bb_df.empty:
                                df["bb_upper"] = bb_df.iloc[:, 2]  # BBU
                                df["bb_middle"] = bb_df.iloc[:, 1]  # BBM
                                df["bb_lower"] = bb_df.iloc[:, 0]  # BBL
                                df["bb_percent"] = bb_df.iloc[:, 3]  # %B
                                df["bb_width"] = bb_df.iloc[:, 4]  # Band Width
                        except Exception as e:
                            logger.warning("Failed to add Bollinger Bands: %s", e)

                    # Williams %R
                    elif base == "willr" or base == "williams":
                        try:
                            period_willr = period if period else 14
                            willr = self.ind_calc.williams_r(df, window=period_willr)
                            df[f"willr_{period_willr}"] = willr
                        except Exception as e:
                            logger.warning("Failed to add Williams %%R: %s", e)

                    # ADX
                    elif base == "adx":
                        try:
                            adx_df = self.ind_calc.adx(df)
                            if not adx_df.empty:
                                df["adx"] = adx_df.iloc[:, 0]
                                df["di_plus"] = adx_df.iloc[:, 1]
                                df["di_minus"] = adx_df.iloc[:, 2]
                        except Exception as e:
                            logger.warning("Failed to add ADX: %s", e)

                    # チャイキンマネーフロー
                    elif base == "cmf":
                        try:
                            period_cmf = period if period else 20
                            cmf = self.ind_calc.chaikin_money_flow(
                                df, window=period_cmf
                            )
                            df[f"cmf_{period_cmf}"] = cmf
                        except Exception as e:
                            logger.warning("Failed to add CMF: %s", e)

                    # フィッシャートランスフォーム
                    elif base == "fisher":
                        try:
                            fisher_df = self.ind_calc.fisher_transform(df)
                            if not fisher_df.empty:
                                df["fisher"] = fisher_df.iloc[:, 0]
                                df["fisher_signal"] = fisher_df.iloc[:, 1]
                        except Exception as e:
                            logger.warning("Failed to add Fisher Transform: %s", e)

                    # 高度な複合シグナル
                    elif base == "advanced" and "signals" in feat_lc:
                        try:
                            advanced_df = self.ind_calc.advanced_signals(df)
                            for col in advanced_df.columns:
                                df[col] = advanced_df[col]
                        except Exception as e:
                            logger.warning("Failed to add advanced signals: %s", e)

                    # VIX恐怖指数関連特徴量（キャッシュ優先版）
                    elif base == "vix":
                        try:
                            # キャッシュからVIXデータを取得（優先）
                            cached_vix = self._get_cached_external_data("vix", df.index)

                            if not cached_vix.empty:
                                logger.debug(
                                    f"Using cached VIX data: {len(cached_vix)} records"
                                )
                                vix_features = cached_vix
                            elif self.vix_fetcher:
                                # キャッシュがない場合は従来の方法
                                backtest_since = None
                                if hasattr(df, "index") and len(df) > 0:
                                    backtest_since = df.index.min()

                                vix_data = self.vix_fetcher.get_vix_data(
                                    timeframe="1d", limit=100, since=backtest_since
                                )
                                if not vix_data.empty:
                                    vix_features = (
                                        self.vix_fetcher.calculate_vix_features(
                                            vix_data
                                        )
                                    )

                                    # タイムゾーン統一・データアライメント改良
                                    if isinstance(
                                        df.index, pd.DatetimeIndex
                                    ) and isinstance(
                                        vix_features.index, pd.DatetimeIndex
                                    ):
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
                                                closest_idx = (
                                                    vix_hourly.index.get_indexer(
                                                        [timestamp], method="ffill"
                                                    )[0]
                                                )
                                                if closest_idx >= 0:
                                                    vix_row = vix_hourly.iloc[
                                                        closest_idx
                                                    ]
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
                                                                # vix_regime設定
                                                                k = "vix_regime_numeric"
                                                                v = regime_map.get(
                                                                    vix_row[col], 1
                                                                )
                                                                df.loc[timestamp, k] = v
                                                            else:
                                                                df.loc[
                                                                    timestamp, col
                                                                ] = vix_row[col]
                                                    added_features = i + 1

                                        logger.info(
                                            f"Added VIX features to "
                                            f"{added_features}/{len(df)} data points"
                                        )
                                    else:
                                        logger.warning(
                                            "Could not align VIX data - "
                                            "index type mismatch"
                                        )
                                else:
                                    logger.warning("No VIX data available")
                            else:
                                logger.warning("VIX fetcher not initialized")
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

                    # マクロ経済データ特徴量（DXY, 金利）（キャッシュ優先版）
                    elif base in ["dxy", "macro", "treasury"]:
                        try:
                            # キャッシュからマクロデータを取得（優先）
                            cached_macro = self._get_cached_external_data(
                                "macro", df.index
                            )

                            if not cached_macro.empty:
                                logger.debug(
                                    f"Using cached macro: {len(cached_macro)} items"
                                )
                                macro_features = cached_macro
                            elif self.macro_fetcher:
                                # キャッシュがない場合は従来の方法
                                if hasattr(df, "index") and len(df) > 0:
                                    backtest_year = df.index.min().year
                                    self.macro_fetcher._backtest_start_year = (
                                        backtest_year
                                    )
                                macro_data = self.macro_fetcher.get_macro_data(limit=50)
                                if not macro_data.empty:
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

                    # Fear & Greed Index特徴量（キャッシュ優先版）
                    elif base in ["fear_greed", "fg"]:
                        try:
                            # キャッシュからFear&Greedデータを取得（優先）
                            cached_fg = self._get_cached_external_data(
                                "fear_greed", df.index
                            )

                            if not cached_fg.empty:
                                logger.debug(
                                    f"Using cached Fear&Greed: {len(cached_fg)} items"
                                )
                                fg_features = cached_fg
                            elif self.fear_greed_fetcher:
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

        # 101特徴量の確実な保証（最終チェック）
        from crypto_bot.ml.feature_defaults import ensure_feature_consistency

        df = ensure_feature_consistency(df, target_count=101)
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
    logger.info(f"prepare_ml_dataset input df shape: {df.shape}")
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

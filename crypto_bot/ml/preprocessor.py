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
    from crypto_bot.data.fear_greed_fetcher import FearGreedFetcher

    FEAR_GREED_AVAILABLE = True
except ImportError:
    FearGreedFetcher = None
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
        self.vix_enabled = "vix" in self.extra_features and VIX_AVAILABLE
        if self.vix_enabled and VIX_AVAILABLE:
            self.vix_fetcher = VIXDataFetcher()
        else:
            self.vix_fetcher = None

        # マクロデータ統合設定
        self.macro_enabled = (
            any(feat in self.extra_features for feat in ["dxy", "macro", "treasury"])
            and MACRO_AVAILABLE
        )
        if self.macro_enabled and MACRO_AVAILABLE:
            self.macro_fetcher = MacroDataFetcher()
        else:
            self.macro_fetcher = None

        # Funding Rate統合設定
        self.funding_enabled = (
            any(feat in self.extra_features for feat in ["funding", "oi"])
            and FUNDING_AVAILABLE
        )
        if self.funding_enabled and FUNDING_AVAILABLE:
            self.funding_fetcher = FundingDataFetcher(testnet=True)
        else:
            self.funding_fetcher = None

        # Fear & Greed統合設定
        self.fear_greed_enabled = (
            any(feat in self.extra_features for feat in ["fear_greed", "fg"])
            and FEAR_GREED_AVAILABLE
        )
        if self.fear_greed_enabled and FEAR_GREED_AVAILABLE:
            self.fear_greed_fetcher = FearGreedFetcher()
        else:
            self.fear_greed_fetcher = None

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

                    # VIX恐怖指数関連特徴量（改良版）
                    elif base == "vix":
                        try:
                            if self.vix_fetcher:
                                # バックテスト期間を設定
                                backtest_since = None
                                if hasattr(df, "index") and len(df) > 0:
                                    backtest_since = df.index.min()

                                # VIXデータ取得（バックテスト期間対応）
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

                    # マクロ経済データ特徴量（DXY, 金利）
                    elif base in ["dxy", "macro", "treasury"]:
                        try:
                            if self.macro_fetcher:
                                # バックテスト年を設定
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

                    # Funding Rate & Open Interest 特徴量（最適化版）
                    elif base in ["funding", "oi"]:
                        try:
                            if self.funding_fetcher:
                                funding_data = (
                                    self.funding_fetcher.get_funding_rate_data(limit=60)
                                )  # より多くのデータ
                                oi_data = self.funding_fetcher.get_open_interest_data(
                                    limit=60
                                )

                                if not funding_data.empty or not oi_data.empty:
                                    funding_features = (
                                        self.funding_fetcher.calculate_funding_features(
                                            funding_data, oi_data
                                        )
                                    )

                                    # 暗号資産データとFundingデータの時間軸を合わせる
                                    if isinstance(
                                        df.index, pd.DatetimeIndex
                                    ) and isinstance(
                                        funding_features.index, pd.DatetimeIndex
                                    ):
                                        # タイムゾーン統一
                                        if df.index.tz is None:
                                            df.index = df.index.tz_localize("UTC")
                                        if funding_features.index.tz is None:
                                            funding_features.index = (
                                                funding_features.index.tz_localize(
                                                    "UTC"
                                                )
                                            )
                                        elif funding_features.index.tz != df.index.tz:
                                            funding_features.index = (
                                                funding_features.index.tz_convert("UTC")
                                            )

                                        # 日次データなので、暗号資産の時間軸に合わせてリサンプリング
                                        funding_resampled = funding_features.resample(
                                            "1H"
                                        ).ffill()

                                        # インデックスを合わせて結合
                                        common_index = df.index.intersection(
                                            funding_resampled.index
                                        )
                                        logger.debug(
                                            f"Funding alignment: crypto {len(df)}, "
                                            f"funding {len(funding_resampled)}, "
                                            f"common {len(common_index)}"
                                        )

                                        if len(common_index) == 0 and len(df) > 0:
                                            # 期間ミスマッチの場合、最新データで埋める
                                            closest_funding_date = (
                                                funding_resampled.index[
                                                    funding_resampled.index
                                                    <= df.index.max()
                                                ]
                                            )
                                            if len(closest_funding_date) > 0:
                                                closest_date = (
                                                    closest_funding_date.max()
                                                )
                                                funding_values = funding_resampled.loc[
                                                    closest_date
                                                ]

                                                from crypto_bot.data.funding_fetcher import (  # noqa: E501
                                                    get_available_funding_features,
                                                )

                                                funding_feature_names = (
                                                    get_available_funding_features()
                                                )

                                                for col in funding_feature_names:
                                                    if col in funding_values.index:
                                                        df[col] = funding_values[col]
                                                    else:
                                                        df[col] = 0  # デフォルト値
                                                logger.debug(
                                                    f"Used closest funding data from {closest_date}"  # noqa: E501
                                                )
                                            else:
                                                # データなしの場合はデフォルト値
                                                from crypto_bot.data.funding_fetcher import (  # noqa: E501
                                                    get_available_funding_features,
                                                )

                                                funding_feature_names = (
                                                    get_available_funding_features()
                                                )
                                                for col in funding_feature_names:
                                                    df[col] = 0
                                                logger.warning(
                                                    "No suitable funding data found - using default values"  # noqa: E501
                                                )
                                        elif len(common_index) > 0:
                                            # 通常のアライメント
                                            from crypto_bot.data.funding_fetcher import (  # noqa: E501
                                                get_available_funding_features,
                                            )

                                            funding_feature_names = (
                                                get_available_funding_features()
                                            )

                                            for col in funding_feature_names:
                                                if col in funding_resampled.columns:
                                                    df.loc[common_index, col] = (
                                                        funding_resampled.loc[
                                                            common_index, col
                                                        ]
                                                    )

                                            logger.info(
                                                f"Added {len(funding_feature_names)} funding features: {len(common_index)} data points aligned"  # noqa: E501
                                            )
                                        else:
                                            logger.warning(
                                                "Could not align funding data with crypto data"  # noqa: E501
                                            )
                                    else:
                                        logger.warning(
                                            "Index type mismatch for funding data alignment"  # noqa: E501
                                        )
                                else:
                                    # データなしの場合は必ずデフォルト特徴量を追加（特徴量数一致のため）
                                    logger.warning(
                                        "No funding data available - adding default features"  # noqa: E501
                                    )
                                    try:
                                        from crypto_bot.data.funding_fetcher import (
                                            get_available_funding_features,
                                        )

                                        funding_feature_names = (
                                            get_available_funding_features()
                                        )

                                        for col in funding_feature_names:
                                            if col not in df.columns:
                                                df[col] = 0  # デフォルト値
                                        logger.debug(
                                            f"Added {len(funding_feature_names)} default funding features"  # noqa: E501
                                        )
                                    except Exception as inner_e:
                                        logger.error(
                                            f"Failed to add default funding features: {inner_e}"  # noqa: E501
                                        )
                            else:
                                # Fetcherなしの場合も必ずデフォルト特徴量を追加
                                logger.warning(
                                    "Funding fetcher not initialized - adding default features"  # noqa: E501
                                )
                                try:
                                    from crypto_bot.data.funding_fetcher import (
                                        get_available_funding_features,
                                    )

                                    funding_feature_names = (
                                        get_available_funding_features()
                                    )

                                    for col in funding_feature_names:
                                        if col not in df.columns:
                                            df[col] = 0  # デフォルト値
                                    logger.debug(
                                        f"Added {len(funding_feature_names)} default funding features"  # noqa: E501
                                    )
                                except Exception as inner_e:
                                    logger.error(
                                        f"Failed to add default funding features: {inner_e}"  # noqa: E501
                                    )
                        except Exception as e:
                            logger.warning("Failed to add funding features: %s", e)
                            # エラー時もデフォルト特徴量を追加
                            try:
                                from crypto_bot.data.funding_fetcher import (
                                    get_available_funding_features,
                                )

                                funding_feature_names = get_available_funding_features()

                                for col in funding_feature_names:
                                    if col not in df.columns:
                                        df[col] = 0  # デフォルト値
                                logger.debug(
                                    f"Added {len(funding_feature_names)} default funding features after error"  # noqa: E501
                                )
                            except Exception as inner_e:
                                logger.error(
                                    f"Failed to add default funding features: {inner_e}"
                                )

                    # Fear & Greed Index特徴量
                    elif base in ["fear_greed", "fg"]:
                        try:
                            if self.fear_greed_fetcher:
                                # Fear & Greedデータを取得
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

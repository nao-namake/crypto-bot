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
                        raise ValueError(f"Unknown extra feature spec: {feat}")

                except Exception as e:
                    logger.error("Failed to add extra feature %s: %s", feat, e)
                    raise  # 失敗したら握りつぶさず停止する
            logger.debug("After extra feats: %s", df.shape)

        # 6. 欠損再補完＋0埋め
        df = df.ffill().fillna(0)
        logger.debug("Final features shape: %s", df.shape)
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
    pipeline = build_ml_pipeline(config)
    X_arr = pipeline.fit_transform(df)

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

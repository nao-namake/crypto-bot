from typing import Any, Dict, List

import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from crypto_bot.indicator.calculator import IndicatorCalculator
from crypto_bot.ml.target import make_classification_target, make_regression_target


class FeatureEngineer(BaseEstimator, TransformerMixin):
    """
    Pandas DataFrame を受け取り、
      1) ffill→初期 NA drop
      2) ATR_<feat_period>
      3) close_lag_<lag>（lag 特徴）
      4) close_mean_<rolling_window>, close_std_<rolling_window>
    を追加し、先頭 drop_n 行をスライスして返す。
    drop_n = rolling_window + max(lags)
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ind_calc = IndicatorCalculator()

    def fit(self, X: pd.DataFrame, y=None):
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        df = X.copy()

        # 1) 欠損処理: ffill→残り初期 NA drop
        df = df.ffill().dropna()

        # 2) ATR 指標
        feat_period = self.config["ml"]["feat_period"]
        atr_series = self.ind_calc.atr(df, window=feat_period)
        if isinstance(atr_series, pd.DataFrame):
            col0 = atr_series.columns[0]
            atr_series = atr_series[col0].rename(f"ATR_{feat_period}")
        else:
            atr_series = atr_series.rename(f"ATR_{feat_period}")
        df = pd.concat([df, atr_series], axis=1)

        # 3) ラグ特徴
        lags: List[int] = self.config["ml"]["lags"]
        for lag in lags:
            df[f"close_lag_{lag}"] = df["close"].shift(lag)

        # 4) クローズの移動統計量
        win: int = self.config["ml"]["rolling_window"]
        df[f"close_mean_{win}"] = df["close"].rolling(win).mean()
        df[f"close_std_{win}"] = df["close"].rolling(win).std()

        # 5) 先頭 drop_n 行をスライス
        drop_n = win + max(lags) if lags else win
        df = df.iloc[drop_n:].copy()

        return df


def build_ml_pipeline(config: Dict[str, Any]) -> Pipeline:
    return Pipeline(
        [
            ("features", FeatureEngineer(config)),
            ("scaler", StandardScaler()),
        ]
    )


def prepare_ml_dataset(
    df: pd.DataFrame, config: Dict[str, Any]
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    pipeline = build_ml_pipeline(config)
    X_arr = pipeline.fit_transform(df)

    horizon = config["ml"]["horizon"]
    threshold = config["ml"].get("threshold", 0.0)
    y_reg = make_regression_target(df, horizon).rename(f"return_{horizon}")
    y_clf = make_classification_target(df, horizon, threshold).rename(f"up_{horizon}")

    win = config["ml"]["rolling_window"]
    lags = config["ml"]["lags"]
    drop_n = win + max(lags) if lags else win
    idx = df.index[drop_n:]

    X = pd.DataFrame(X_arr, index=idx)
    return X, y_reg.loc[idx], y_clf.loc[idx]

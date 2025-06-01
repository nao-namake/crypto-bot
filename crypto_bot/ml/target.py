# =============================================================================
# ファイル名: crypto_bot/ml/target.py
# 説明:
# 機械学習モデル用のターゲット（目的変数）生成ユーティリティ
# - 回帰タスク用: N期間後リターン
# - 分類タスク用: リターン閾値超過かどうかの2値ラベル
# =============================================================================

import pandas as pd

def make_regression_target(df: pd.DataFrame, horizon: int) -> pd.Series:
    """
    N期間後のリターン (close_t+horizon / close_t) - 1 を返す。
    最後の horizon 件は NaN。

    Parameters
    ----------
    df : pd.DataFrame
        OHLCV等を含むデータ
    horizon : int
        先をどれだけ予測するか

    Returns
    -------
    pd.Series
        N期間後リターン
    """
    future = df["close"].shift(-horizon)
    ret = future / df["close"] - 1.0
    return ret.rename(f"return_{horizon}")

def make_classification_target(
    df: pd.DataFrame, horizon: int, threshold: float = 0.0
) -> pd.Series:
    """
    N期間後のリターン > threshold なら 1, それ以外は 0 のラベルを返す。

    Parameters
    ----------
    df : pd.DataFrame
        OHLCV等を含むデータ
    horizon : int
        先をどれだけ予測するか
    threshold : float, optional
        クラス分け閾値（デフォルト: 0）

    Returns
    -------
    pd.Series
        2値ラベル
    """
    future = df["close"].shift(-horizon)
    ret = future / df["close"] - 1.0
    label = (ret > threshold).astype(int)
    return label.rename(f"up_{horizon}")

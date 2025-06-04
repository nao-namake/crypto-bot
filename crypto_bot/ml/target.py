# =============================================================================
# ファイル名: crypto_bot/ml/target.py
# 説明:
# 機械学習用のターゲット（目的変数）生成関数を提供。
# - 回帰用: N期間後のリターン
# - 分類用: N期間後の上昇/下落（閾値で判定）
# =============================================================================

import pandas as pd


def make_regression_target(df: pd.DataFrame, horizon: int) -> pd.Series:
    """
    回帰用のターゲット（horizon期間後のリターン）を生成。
    :param df: OHLCV DataFrame
    :param horizon: 何期間後のリターンか
    :return: リターンのpd.Series
    """
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    ret = df["close"].pct_change(horizon).shift(-horizon)
    return ret.rename(f"return_{horizon}")


def make_classification_target(
    df: pd.DataFrame, horizon: int, threshold: float = 0.0
) -> pd.Series:
    """
    分類用のターゲット（horizon期間後の上昇/下落）を生成。
    :param df: OHLCV DataFrame
    :param horizon: 何期間後のリターンか
    :param threshold: 上昇と判定する閾値（デフォルト: 0.0）
    :return: 1（上昇）または0（下落）のpd.Series
    """
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    if len(df) <= 1:
        # 空のDataFrameまたは単一行の場合は空のSeriesを返す
        return pd.Series(dtype=float, index=df.index, name=f"up_{horizon}")
    ret = df["close"].pct_change(horizon).shift(-horizon)
    return (ret > threshold).astype(int).rename(f"up_{horizon}")

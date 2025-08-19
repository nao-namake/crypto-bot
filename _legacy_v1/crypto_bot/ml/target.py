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
    Phase H.26: NaN値除去処理追加
    :param df: OHLCV DataFrame
    :param horizon: 何期間後のリターンか
    :return: リターンのpd.Series
    """
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    if len(df) <= horizon * 2:
        # データが少なすぎる場合は空のSeriesを返す（Phase H.26）
        return pd.Series(dtype=float, index=df.index, name=f"return_{horizon}")

    # Phase H.26: NaN値を避けてリターン計算
    ret = df["close"].pct_change(horizon).shift(-horizon)

    # Phase H.26: NaN値を除去してクリーンなラベルを返す
    ret_clean = ret.dropna()

    if len(ret_clean) == 0:
        # 有効なラベルがない場合は空のSeriesを返す
        return pd.Series(dtype=float, index=df.index, name=f"return_{horizon}")

    return ret_clean.rename(f"return_{horizon}")


def make_classification_target(
    df: pd.DataFrame, horizon: int, threshold: float = 0.0
) -> pd.Series:
    """
    分類用のターゲット（horizon期間後の上昇/下落）を生成。
    Phase H.26: NaN値除去処理追加
    :param df: OHLCV DataFrame
    :param horizon: 何期間後のリターンか
    :param threshold: 上昇と判定する閾値（デフォルト: 0.0）
    :return: 1（上昇）または0（下落）のpd.Series
    """
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    if len(df) <= horizon * 2:
        # データが少なすぎる場合は空のSeriesを返す（Phase H.26）
        return pd.Series(dtype=float, index=df.index, name=f"up_{horizon}")

    # Phase H.26: NaN値を避けてリターン計算
    ret = df["close"].pct_change(horizon).shift(-horizon)

    # Phase H.26: NaN値を除去してクリーンなラベルを生成
    target = (ret > threshold).astype(int)

    # NaN値をdropして有効なラベルのみ返す
    target = target.dropna()

    if len(target) == 0:
        # 有効なラベルがない場合は空のSeriesを返す
        return pd.Series(dtype=float, index=df.index, name=f"up_{horizon}")

    return target.rename(f"up_{horizon}")

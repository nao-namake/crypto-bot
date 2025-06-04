# tests/unit/strategy/test_ml_strategy.py
# テスト対象: crypto_bot/strategy/ml_strategy.py
# 説明:
#   - MLStrategy: 機械学習ベースの戦略
#   - モデルによる予測→シグナル生成の流れ

import numpy as np
import pandas as pd
import pytest

from crypto_bot.execution.engine import Position
from crypto_bot.strategy.ml_strategy import MLStrategy


class DummyPipeline:
    """テスト用のダミーパイプライン"""

    def transform(self, X):
        return X.values


class DummyModel:
    """テスト用のダミーモデル"""

    def __init__(self, proba):
        self.proba = proba

    def predict_proba(self, X):
        return np.array([[1 - self.proba, self.proba]])


class DummyFeatureEngineer:
    """特徴量データフレームを返すだけのダミー"""

    def __init__(self, df):
        self.df = df

    def transform(self, price_df):
        return self.df


@pytest.fixture
def price_df():
    # 最低限のダミーデータ
    return pd.DataFrame(
        {
            "close": [100, 101, 102],
        },
        index=pd.date_range("2023-01-01", periods=3, freq="D"),
    )


@pytest.mark.parametrize(
    "mochi_long, mochi_short, proba, position_exist, expected_side",
    [
        # もちぽよロング優先
        (1, 0, 0.7, False, "BUY"),
        # もちぽよショート優先
        (0, 1, 0.7, False, "SELL"),
        # ML BUY
        (0, 0, 0.7, False, "BUY"),
        # ML SELL
        (0, 0, 0.2, False, "SELL"),
        # ポジション有&exit条件
        (0, 0, 0.3, True, "SELL"),
        # ポジション有&exit条件なし
        (0, 0, 0.6, True, None),
        # どちらでもないとき
        (0, 0, 0.5, False, None),
    ],
)
def test_logic_signal_branch(
    monkeypatch, price_df, mochi_long, mochi_short, proba, position_exist, expected_side
):
    # 特徴量データフレームに必要なカラムをセット
    feat_df = price_df.copy()
    # OHLCVカラムを追加
    feat_df["high"] = feat_df["close"] * 1.01  # 高値は終値の1%上
    feat_df["low"] = feat_df["close"] * 0.99  # 安値は終値の1%下
    feat_df["open"] = feat_df["close"] * 0.995  # 始値は終値の0.5%下
    feat_df["volume"] = 1000.0  # 取引量は固定値
    # もちぽよシグナルを追加
    feat_df["mochipoyo_long_signal"] = [0, 0, mochi_long]
    feat_df["mochipoyo_short_signal"] = [0, 0, mochi_short]

    # テスト用の設定
    test_config = {
        "ml": {
            "feat_period": 14,
            "rolling_window": 20,
            "lags": [1, 2, 3],
            "extra_features": ["mochipoyo_long_signal", "mochipoyo_short_signal"],
            "horizon": 3,
            "threshold": 0.0,
        }
    }

    # MLModel.loadをモック化
    dummy_model = DummyModel(proba)
    monkeypatch.setattr("crypto_bot.ml.model.MLModel.load", lambda _: dummy_model)

    # MLStrategyのインスタンスを作成
    strategy = MLStrategy(model_path="dummy.pkl", config=test_config)
    strategy.pipeline = DummyPipeline()

    # ポジション情報を設定
    position = Position(exist=position_exist) if position_exist else None
    if position_exist:
        position.side = "BUY"  # テスト用にBUYポジションを設定

    # シグナルを取得
    signal = strategy.logic_signal(feat_df, position)
    if expected_side is None:
        assert signal is None
    else:
        assert (
            signal.side == expected_side
        ), f"Expected side {expected_side}, got {signal.side}"

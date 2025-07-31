# tests/unit/ml/test_target.py
# テスト対象: crypto_bot/ml/target.py
# 説明:
#   - make_regression_target: N期間後リターンの連続値を返す
#   - make_classification_target: N期間後リターンの2値ラベルを返す

import numpy as np
import pandas as pd
import pytest

from crypto_bot.ml.target import make_classification_target, make_regression_target


def test_make_regression_target_basic():
    df = pd.DataFrame({"close": [100, 110, 105, 120, 130]})
    # horizon=1なら (110/100-1)=0.1, (105/110-1)=約-0.0454, ...
    result = make_regression_target(df, horizon=1)
    np.testing.assert_almost_equal(result.iloc[0], 0.1)
    np.testing.assert_almost_equal(result.iloc[1], (105 / 110) - 1)
    # Phase H.26: NaN値処理改善により、最後の値も計算される
    # result[3] = (130/120) - 1 ≈ 0.0833
    np.testing.assert_almost_equal(result.iloc[-1], (130 / 120) - 1)


def test_make_regression_target_horizon2():
    df = pd.DataFrame({"close": [100, 110, 105, 120, 130]})
    # horizon=2: (105/100-1)=0.05, (120/110-1)=約0.0909,
    # (130/105-1)=約0.238, 末尾2つはnan
    result = make_regression_target(df, horizon=2)
    np.testing.assert_almost_equal(result.iloc[0], 0.05)
    np.testing.assert_almost_equal(result.iloc[1], (120 / 110) - 1)
    # Phase H.26: NaN値処理改善により、すべての値が計算される
    # result[2] = (130/105) - 1 ≈ 0.238
    np.testing.assert_almost_equal(result.iloc[-1], (130 / 105) - 1)


def test_make_regression_target_empty_df():
    df = pd.DataFrame({"close": []})
    result = make_regression_target(df, horizon=1)
    assert len(result) == 0


def test_make_regression_target_single_row():
    df = pd.DataFrame({"close": [100]})
    result = make_regression_target(df, horizon=1)
    assert len(result) == 1
    assert np.isnan(result.iloc[0])


def test_make_regression_target_negative_horizon():
    df = pd.DataFrame({"close": [100, 110, 105]})
    with pytest.raises(ValueError):
        make_regression_target(df, horizon=-1)


def test_make_classification_target_default_thresh():
    df = pd.DataFrame({"close": [100, 110, 105, 120, 130]})
    # horizon=1, threshold=0 → [1, 0, 1, 1, nan]
    result = make_classification_target(df, horizon=1)
    assert result.iloc[0] == 1  # (110-100)/100 > 0 → 1
    assert result.iloc[1] == 0  # (105-110)/110 < 0 → 0
    assert result.iloc[2] == 1  # (120-105)/105 > 0 → 1
    assert result.iloc[3] == 1  # (130-120)/120 > 0 → 1
    assert np.isnan(result.iloc[4]) or result.iloc[4] == 0


def test_make_classification_target_custom_thresh():
    df = pd.DataFrame({"close": [100, 110, 105, 120, 130]})
    # horizon=1, threshold=0.05 →
    # 0.1>0.05=1, (-0.0454)<0.05=0,
    # (0.1429)>0.05=1, (0.0833)>0.05=1
    result = make_classification_target(df, horizon=1, threshold=0.05)
    assert result.iloc[0] == 1  # 0.1 > 0.05
    assert result.iloc[1] == 0  # -0.0454 < 0.05
    assert result.iloc[2] == 1  # 0.142857 > 0.05
    assert result.iloc[3] == 1  # 0.08333 > 0.05


def test_make_classification_target_empty_df():
    df = pd.DataFrame({"close": []})
    result = make_classification_target(df, horizon=1)
    assert len(result) == 0


def test_make_classification_target_single_row():
    df = pd.DataFrame({"close": [100]})
    result = make_classification_target(df, horizon=1)
    assert len(result) == 1
    assert np.isnan(result.iloc[0])


def test_make_classification_target_negative_horizon():
    df = pd.DataFrame({"close": [100, 110, 105]})
    with pytest.raises(ValueError):
        make_classification_target(df, horizon=-1)


def test_make_classification_target_negative_threshold():
    df = pd.DataFrame({"close": [100, 110, 105]})
    result = make_classification_target(df, horizon=1, threshold=-0.1)
    assert result.iloc[0] == 1  # 0.1 > -0.1
    assert result.iloc[1] == 1  # -0.0454 > -0.1


def test_column_names():
    df = pd.DataFrame({"close": [100, 110, 105, 120, 130]})
    reg = make_regression_target(df, horizon=3)
    clf = make_classification_target(df, horizon=2)
    assert reg.name == "return_3"
    assert clf.name == "up_2"

import numpy as np
import pandas as pd
import pytest

from crypto_bot.ml.target import make_classification_target, make_regression_target


def test_make_regression_target_basic():
    df = pd.DataFrame({"close": [100, 110, 121, 133.1, 146.41]})
    tgt = make_regression_target(df, horizon=1)
    expected = pd.Series([0.1, 0.1, 0.1, 0.1, np.nan])
    # index や name は無視して値だけ比較
    pd.testing.assert_series_equal(
        tgt.reset_index(drop=True),
        expected,
        check_names=False,
        rtol=1e-6,
    )


def test_make_regression_target_multi_horizon():
    df = pd.DataFrame({"close": [100, 200, 300, 400, 500]})
    tgt = make_regression_target(df, horizon=2)
    assert pytest.approx(tgt.iloc[0], rel=1e-6) == 2.0
    assert pytest.approx(tgt.iloc[1], rel=1e-6) == 1.0
    # 最後2行は NaN
    assert np.isnan(tgt.iloc[3]) and np.isnan(tgt.iloc[4])


def test_make_classification_target_default_threshold():
    df = pd.DataFrame({"close": [100, 90, 110, 100]})
    clf = make_classification_target(df, horizon=1, threshold=0.0)
    assert clf.tolist() == [0, 1, 0, 0]


def test_make_classification_target_custom_threshold():
    df = pd.DataFrame({"close": [100, 150, 80, 120]})
    clf = make_classification_target(df, horizon=1, threshold=0.4)
    assert clf.tolist() == [1, 0, 1, 0]

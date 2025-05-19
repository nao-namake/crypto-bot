from datetime import datetime, timedelta

import pandas as pd
import pytest


@pytest.fixture
def small_ohlcv():
    # 10 行だけのダミー OHLCV
    dates = [datetime(2022, 1, 1) + timedelta(hours=i) for i in range(10)]
    df = pd.DataFrame(
        {
            "timestamp": dates,
            "open": range(100, 110),
            "high": range(101, 111),
            "low": range(99, 109),
            "close": range(100, 110),
            "volume": [1] * 10,
        }
    ).set_index("timestamp")
    return df

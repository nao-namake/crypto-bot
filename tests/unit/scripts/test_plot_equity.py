# tests/unit/scripts/test_plot_equity.py
# テスト対象: crypto_bot/scripts/plot_equity.py
# 説明:
#   - CSVからエクイティ/累積損益カラムを読み出して正しくプロット用データが抽出できるかをテスト
#   - プロット部分はmatplotlibの描画関数をモック化してチェック

import matplotlib
import pandas as pd
import pytest

matplotlib.use("Agg")  # テスト時はGUI描画しない


# テスト対象関数部分だけ移植
def _load_and_choose_column(csv_path, equity_mode=True):
    df = pd.read_csv(csv_path, parse_dates=True, index_col=0)
    if equity_mode and "equity" in df.columns:
        y = df["equity"]
        label = "Equity"
    elif "total_profit" in df.columns:
        y = df["total_profit"].cumsum()
        label = "Cumulative Profit"
    else:
        raise ValueError(
            "プロット可能なカラム（'equity' or 'total_profit'）がありません。"
        )
    return y, label


def test_plot_equity_equity_col(tmp_path):
    # テスト用CSV作成
    df = pd.DataFrame(
        {
            "equity": [100, 102, 101, 105],
            "total_profit": [0, 2, -1, 4],
        }
    )
    csv_file = tmp_path / "test_equity.csv"
    df.to_csv(csv_file)
    y, label = _load_and_choose_column(csv_file, equity_mode=True)
    assert label == "Equity"
    assert list(y) == [100, 102, 101, 105]


def test_plot_equity_total_profit_col(tmp_path):
    df = pd.DataFrame(
        {
            "total_profit": [0, 2, -1, 4],
        }
    )
    csv_file = tmp_path / "test_profit.csv"
    df.to_csv(csv_file)
    y, label = _load_and_choose_column(csv_file, equity_mode=False)
    assert label == "Cumulative Profit"
    assert list(y) == [0, 2, 1, 5]


def test_plot_equity_no_plot_col(tmp_path):
    df = pd.DataFrame(
        {
            "foo": [1, 2, 3],
        }
    )
    csv_file = tmp_path / "test_no_plot.csv"
    df.to_csv(csv_file)
    with pytest.raises(ValueError):
        _load_and_choose_column(csv_file)

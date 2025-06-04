# tests/unit/backtest/test_analysis.py
# テスト対象: crypto_bot/backtest/analysis.py
# 説明:
#   - BacktestAnalyzer: バックテスト結果の分析・集計
#   - 各種メトリクス（リターン、シャープレシオ、ドローダウン等）の計算

import pandas as pd

from crypto_bot.backtest import analysis


def sample_trade_log():
    return pd.DataFrame(
        {
            "entry_time": [
                "2024-01-01 09:00",
                "2024-01-01 10:00",
                "2024-01-02 11:00",
                "2024-01-07 15:00",
                "2024-01-15 12:00",
            ],
            "duration_bars": [60, 30, 90, 45, 120],
            "profit": [100, -50, 200, 0, 150],
        }
    )


def test_preprocess_trade_log():
    df = sample_trade_log()
    out = analysis.preprocess_trade_log(df)
    # entry_time should be datetime
    assert pd.api.types.is_datetime64_any_dtype(out["entry_time"])
    # exit_time should be entry_time + duration_bars (in minutes)
    expected_exit = pd.to_datetime(df["entry_time"]) + pd.to_timedelta(
        df["duration_bars"], unit="min"
    )
    assert (out["exit_time"] == expected_exit).all()


def test_aggregate_by_period_daily():
    df = sample_trade_log()
    agg = analysis.aggregate_by_period(df, "D")
    # 日単位で3日分（1/1, 1/2, 1/7, 1/15の4日、ただし1/1に2件）
    assert isinstance(agg, pd.DataFrame)
    # 簡単な合計チェック（例：トータル損益合計が全体合計と一致）
    assert agg["total_pl"].sum() == df["profit"].sum()
    # トレード数合計が全体件数と一致
    assert agg["trades"].sum() == len(df)


def test_aggregate_by_period_weekly():
    df = sample_trade_log()
    agg = analysis.aggregate_by_period(df, "W")
    assert isinstance(agg, pd.DataFrame)
    # 週次合計損益チェック
    assert agg["total_pl"].sum() == df["profit"].sum()


def test_aggregate_by_period_monthly():
    df = sample_trade_log()
    agg = analysis.aggregate_by_period(df, "ME")
    assert isinstance(agg, pd.DataFrame)
    # 月次合計損益チェック
    assert agg["total_pl"].sum() == df["profit"].sum()


def test_export_aggregates_creates_csv_files(tmp_path):
    df = sample_trade_log()
    out_prefix = tmp_path / "agg"
    analysis.export_aggregates(df, str(out_prefix))
    # ファイルが出力されているか
    for suffix in ["daily", "weekly", "monthly"]:
        out_file = tmp_path / f"agg_{suffix}.csv"
        assert out_file.exists()
        out_df = pd.read_csv(out_file)
        assert len(out_df) > 0

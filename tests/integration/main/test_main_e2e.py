# tests/test_main_e2e.py

import pandas as pd
import pytest
import yaml
from click.testing import CliRunner

from crypto_bot.main import cli


@pytest.fixture
def tmp_config(tmp_path):
    """
    main.py が参照する全てのキーを含む最小構成の YAML。
    """
    cfg = {
        # ── ここを修正 ──
        "data": {
            "symbol": "BTCUSDT",
            "timeframe": "1d",
            "since": "2020-01-01",
            "limit": 100,
            "per_page": 10,
        },
        "strategy": {
            "params": {
                "period": 2,
                "nbdev": 1.0,
            }
        },
        # ── ここまで ──
        "backtest": {"starting_balance": 10000, "slippage_rate": 0.0},
        "walk_forward": {"train_window": 2, "test_window": 1, "step": 1},
        "optimizer": {
            "periods": [2],
            "nbdevs": [1.0],
            "parallel": False,
            "max_workers": 1,
        },
    }
    path = tmp_path / "config.yml"
    path.write_text(yaml.safe_dump(cfg))
    return str(path)


def test_backtest_e2e(monkeypatch, tmp_config):
    # 1) ダミーの価格データ
    dummy_df = pd.DataFrame(
        {
            "low": [10.0, 11.0, 12.0],
            "high": [15.0, 16.0, 17.0],
            "open": [12.0, 13.0, 14.0],
            "close": [13.0, 14.0, 15.0],
        },
        index=pd.date_range("2020-01-01", periods=3),
    )

    # --- main.py の名前空間をパッチ ---
    class DummyFetcher:
        def __init__(self, *args, **kwargs):
            pass

        def get_price_df(self, **kwargs):
            return dummy_df

    monkeypatch.setattr("crypto_bot.main.MarketDataFetcher", DummyFetcher)

    monkeypatch.setattr(
        "crypto_bot.main.DataPreprocessor.clean",
        lambda df, **kwargs: df,
    )

    monkeypatch.setattr(
        "crypto_bot.main.split_walk_forward",
        lambda df, train_window, test_window, step: [(df.iloc[:2], df.iloc[2:3])],
    )

    # （ParameterOptimizer は main.py では使われていませんが安全のためパッチ）
    import pandas as _pd  # noqa: E402

    dummy_scan = _pd.DataFrame([{"period": 2, "nbdev": 1.0, "total_profit": 5.0}])

    class DummyOptimizer:
        def __init__(self, price_df, starting_balance, slippage_rate):
            pass

        def scan(self, periods, nbdevs, parallel, max_workers):
            return dummy_scan

    monkeypatch.setattr("crypto_bot.main.ParameterOptimizer", DummyOptimizer)

    # BacktestEngine → DummyEngine
    dummy_stats = {
        "total_profit": 5.0,
        "cagr": 0.1,
        "sharpe": 0.5,
        "max_drawdown": 0.1,
    }

    class DummyEngine:
        def __init__(self, price_df, strategy, starting_balance, slippage_rate):
            pass

        def run(self):
            pass

        def statistics(self):
            return dummy_stats

    monkeypatch.setattr("crypto_bot.main.BacktestEngine", DummyEngine)
    # --- パッチここまで ---

    # 2) CLI 実行
    runner = CliRunner()
    result = runner.invoke(cli, ["backtest", "--config", tmp_config])

    # 終了コード 0
    assert result.exit_code == 0

    out = result.output.lower()
    # 出力に主要な統計指標名が含まれること
    assert "total_profit" in out or "total profit" in out
    assert "cagr" in out
    assert "sharpe" in out

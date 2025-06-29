# tests/integration/main/test_main_e2e.py
# main.py のCLIコマンド（backtest サブコマンド）を、モック依存でエンドツーエンド検証する統合テスト

import pandas as pd
import pytest
import yaml
from click.testing import CliRunner

from crypto_bot.main import cli


@pytest.fixture
def tmp_config(tmp_path):
    """
    main.py が参照する全てのキーを含む最小構成の YAML。
    出力ファイルはtmp_path配下にリダイレクトする
    """
    # 必要なディレクトリを作成
    results_dir = tmp_path / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    # ダミーモデルファイルを作成（空ファイルでOK）
    dummy_model = tmp_path / "dummy_model.pkl"
    dummy_model.touch()

    cfg = {
        "data": {
            "symbol": "BTCUSDT",
            "timeframe": "1d",
            "since": "2020-01-01",
            "limit": 100,
            "per_page": 10,
        },
        "strategy": {
            "name": "ml",
            "params": {
                "model_path": str(dummy_model),
                "threshold": 0.0,
            },
        },
        "backtest": {
            "starting_balance": 10000,
            "slippage_rate": 0.0,
            "trade_log_csv": str(results_dir / "trade_log.csv"),
            "aggregate_out_prefix": str(results_dir / "agg"),
        },
        "walk_forward": {"train_window": 2, "test_window": 1, "step": 1},
        "optimizer": {
            "param_space": {},
            "parallel": False,
            "max_workers": 1,
        },
    }
    path = tmp_path / "config.yml"
    path.write_text(yaml.safe_dump(cfg))
    return str(path)


def test_backtest_e2e(monkeypatch, tmp_config, tmp_path):
    # 1) ダミーの価格データ
    dummy_df = pd.DataFrame(
        {
            "low": [10.0, 11.0, 12.0],
            "high": [15.0, 16.0, 17.0],
            "open": [12.0, 13.0, 14.0],
            "close": [13.0, 14.0, 15.0],
            "volume": [100, 101, 102],
        },
        index=pd.date_range("2020-01-01", periods=3),
    )

    # --- 各依存先モック ---
    class DummyFetcher:
        def __init__(self, *args, **kwargs):
            pass

        def get_price_df(self, **kwargs):
            return dummy_df

    monkeypatch.setattr("crypto_bot.main.MarketDataFetcher", DummyFetcher)
    monkeypatch.setattr(
        "crypto_bot.main.DataPreprocessor.clean", lambda df, **kwargs: df
    )
    monkeypatch.setattr(
        "crypto_bot.main.split_walk_forward",
        lambda df, train_window, test_window, step: [(df.iloc[:2], df.iloc[2:3])],
    )

    # ParameterOptimizer（安全のためパッチ。現状main.pyでは未使用）
    import pandas as _pd

    dummy_scan = _pd.DataFrame([{"dummy": 0}])

    class DummyOptimizer:
        def __init__(self, price_df, starting_balance, slippage_rate):
            pass

        def scan(self, param_space, parallel, max_workers):
            return dummy_scan

    monkeypatch.setattr("crypto_bot.main.ParameterOptimizer", DummyOptimizer)

    # BacktestEngine
    dummy_metrics = pd.DataFrame(
        [
            {
                "total_profit": 5.0,
                "cagr": 0.1,
                "sharpe": 0.5,
                "max_drawdown": 0.1,
                "trades": 2,
            }
        ]
    )
    dummy_trades = pd.DataFrame(
        [
            {
                "time": "2020-01-03",
                "side": "BUY",
                "price": 14.0,
                "volume": 1.0,
                "profit": 1.0,
            }
        ]
    )

    # MLStrategyのモック
    class DummyMLStrategy:
        def __init__(self, model_path, threshold, config):
            pass

        def logic_signal(self, price_df, position):
            from crypto_bot.execution.engine import Signal

            return Signal(side="BUY", price=price_df["close"].iloc[-1])

    monkeypatch.setattr("crypto_bot.main.MLStrategy", DummyMLStrategy)

    class DummyEngine:
        def __init__(self, price_df, strategy, starting_balance, slippage_rate):
            pass

        def run(self):
            return dummy_metrics, dummy_trades

    monkeypatch.setattr("crypto_bot.main.BacktestEngine", DummyEngine)

    # StrategyFactory のモック
    class DummyStrategyFactory:
        @staticmethod
        def create_strategy(config, full_config=None):
            return DummyMLStrategy("", 0.0, {})

        @staticmethod
        def create_multi_strategy(strategies_config, combination_mode):
            return DummyMLStrategy("", 0.0, {})

    monkeypatch.setattr("crypto_bot.main.StrategyFactory", DummyStrategyFactory)

    # trade log/agg エクスポート（ファイル生成もモック化して安全に）
    monkeypatch.setattr(
        "crypto_bot.main.export_aggregates", lambda trades, prefix: None
    )

    # 2) CLI 実行
    # 結果ファイル出力先もtmp_path下にする
    stats_output = tmp_path / "results" / "backtest_results.csv"
    # 出力ディレクトリを作成
    stats_output.parent.mkdir(parents=True, exist_ok=True)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "backtest",
            "--config",
            tmp_config,
            "--stats-output",
            str(stats_output),
        ],
    )

    # エラー時は出力を表示
    if result.exit_code != 0:
        print("\nCLI Output:")
        print(result.output)
        print("\nException:")
        print(result.exception)

    # 終了コード 0
    assert result.exit_code == 0

    # 出力内容に主要指標名・trade log保存文言が含まれていること
    out = result.output.lower()
    assert "statistics saved" in out
    assert "trade log saved" in out
    assert "aggregates saved" in out
    assert "total_profit" in out or "total profit" in out
    assert "sharpe" in out
    assert "cagr" in out

    # ファイルの有無もチェックしたい場合はここで assert stats_output.exists()

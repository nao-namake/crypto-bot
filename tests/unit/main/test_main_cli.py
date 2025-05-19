# tests/unit/test_main_cli.py

from types import SimpleNamespace

import pytest
import yaml
from click.testing import CliRunner

from crypto_bot.main import cli


def test_cli_train_with_model_option(tmp_path, monkeypatch):
    runner = CliRunner()

    # ダミー prepare_data / save_model を差し替え
    def dummy_prepare_data(cfg):
        import numpy as np

        return np.zeros((10, 3)), np.zeros(10), np.zeros((5, 3)), np.zeros(5)

    monkeypatch.setattr("crypto_bot.main.prepare_data", dummy_prepare_data)
    monkeypatch.setattr("crypto_bot.main.train_best_model", lambda cfg, *_: "OK")
    monkeypatch.setattr("crypto_bot.main.save_model", lambda m, p: None)

    result = runner.invoke(
        cli, ["train", "-c", "config/default.yml", "--model-type", "xgb"]
    )
    assert result.exit_code == 0
    assert "Using model_type: xgb" in result.output


@pytest.fixture
def minimal_cfg(tmp_path):
    """
    train/optimize-ml/ train-best で必要最小限の設定ファイルを作る
    """
    cfg = {
        "data": {
            "symbol": "BTC/USDT",
            "timeframe": "1h",
            "since": None,
            "limit": 1,
        },
        "ml": {
            "feat_period": 1,
            "lags": [1],
            "rolling_window": 1,
            "horizon": 1,
            "threshold": 0.0,
        },
    }
    p = tmp_path / "cfg.yml"
    p.write_text(yaml.safe_dump(cfg))
    return str(p)


def test_optimize_ml_cli(monkeypatch, minimal_cfg):
    """
    optimize_ml コマンドをモックして走らせる
    """
    dummy_study = SimpleNamespace(best_value=0.42, best_params={"foo": 123})
    monkeypatch.setattr("crypto_bot.main.run_optuna", lambda cfg: dummy_study)

    runner = CliRunner()
    result = runner.invoke(cli, ["optimize-ml", "-c", minimal_cfg])
    assert result.exit_code == 0
    assert "Best trial value: 0.42" in result.output
    assert "Best params: {'foo': 123}" in result.output


def test_train_best_cli(monkeypatch, minimal_cfg, tmp_path):
    """
    train-best コマンドをモックして走らせる
    """
    called = {}

    def fake_train_best_model(cfg, out_path):
        called["cfg"] = cfg
        called["out"] = out_path

    monkeypatch.setattr("crypto_bot.main.train_best_model", fake_train_best_model)

    out = tmp_path / "best_model.pkl"
    runner = CliRunner()
    result = runner.invoke(cli, ["train-best", "-c", minimal_cfg, "-o", str(out)])
    assert result.exit_code == 0
    assert "Running optimization and training best model" in result.output
    # モック関数が正しい引数で呼ばれているか
    assert called["out"] == str(out)

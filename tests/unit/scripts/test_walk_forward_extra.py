from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

import crypto_bot.scripts.walk_forward as wf


# ---------- 1) split_walk_forward 追加パターン ----------
def test_split_walk_forward_edge_empty():
    df = pd.DataFrame({"x": np.arange(3)})
    # train+test がデータ長より大きい -> 空 list
    out = wf.split_walk_forward(df, train_window=5, test_window=2, step=1)
    assert out == []


def test_split_walk_forward_invalid_step():
    df = pd.DataFrame({"x": np.arange(10)})
    with pytest.raises(ValueError):
        wf.split_walk_forward(df, train_window=4, test_window=2, step=0)


# ---------- 2) make_strategy_factory ----------
def test_make_strategy_factory_returns_new_instance(monkeypatch):
    """
    MLStrategy はコンストラクタ内で `MLModel.load()` を呼びに行くため、
    ここでは Joblib I/O を伴わないダミー実装に置き換えておく。
    """
    from crypto_bot.strategy.ml_strategy import MLModel  # local import for patch

    class DummyModel:
        pass

    # --- モデルロードをスタブ化してファイルアクセスを回避 ---
    monkeypatch.setattr(MLModel, "load", lambda *_, **__: DummyModel())

    # MLStrategy 内部で config["ml"] 参照があるため最低限のキーを渡す
    factory = wf.make_strategy_factory("m.pkl", 0.1, {"ml": {}})
    s1, s2 = factory(), factory()
    assert type(s1) is type(s2)
    assert s1 is not s2  # 別インスタンスであること


# ---------- 3) main() の薄い E2E ----------
def test_main_smoke(monkeypatch, capsys):
    # --- (a) config YAML を置き換え ---
    dummy_cfg = {
        "data": {
            "exchange": "bitbank",
            "symbol": "BTC/JPY",
            "timeframe": "1h",
            "since": None,
            "limit": 10,
            "paginate": False,
            "per_page": 0,
        },
        "ml": {"feat_period": 2},
        "strategy": {"params": {"model_path": "m.pkl", "threshold": 0.0}},
        "walk_forward": {"train_window": 5, "test_window": 3, "step": 2},
        "backtest": {"starting_balance": 10_000, "slippage_rate": 0.0},
    }
    monkeypatch.setattr(yaml, "safe_load", lambda *_: dummy_cfg)

    # --- (b) MarketDataFetcher / Preprocessor をモック ---
    dummy_df = pd.DataFrame(
        {"close": np.arange(20)},
        index=pd.date_range("2024-01-01", periods=20, freq="H"),
    )
    monkeypatch.setattr(
        "crypto_bot.scripts.walk_forward.MarketDataFetcher.get_price_df",
        lambda *_, **__: dummy_df,
    )
    monkeypatch.setattr(
        "crypto_bot.scripts.walk_forward.DataPreprocessor.clean",
        lambda df, **_: df,
    )

    # --- (c) BacktestEngine ダミー ---
    class DummyEngine:
        def __init__(self, *a, **k):
            self._called = False

        def run(self):
            self._called = True

        def statistics(self):
            return {"total_profit": 1}

    monkeypatch.setattr("crypto_bot.scripts.walk_forward.BacktestEngine", DummyEngine)

    # --- (c.5) MLModel.load をスタブ化してファイルアクセスを回避 ---
    from crypto_bot.strategy.ml_strategy import MLModel  # late import for patch

    monkeypatch.setattr(MLModel, "load", lambda *_, **__: object())

    # --- (d) ファイル I/O を NO-OP に ---
    monkeypatch.setattr(Path, "mkdir", lambda *a, **k: None)
    monkeypatch.setattr(pd.DataFrame, "to_csv", lambda *a, **k: None)

    # --- (e) 実行 & 検証 ---
    wf.main()  # 引数無し → default.yml だが safe_load を置換してある
    captured = capsys.readouterr().out
    assert "total_profit" in captured

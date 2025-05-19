import joblib
import pandas as pd
import yaml
from click.testing import CliRunner
from sklearn.base import BaseEstimator

from crypto_bot.main import cli


class DummyEstimator(BaseEstimator):
    def fit(self, X, y):
        return self

    def predict(self, X):
        return [0] * len(X)


def test_train_command_monkeypatched(tmp_path, monkeypatch):
    # 1) モックデータを返す fetcher
    dummy_df = pd.DataFrame(
        {
            "open": [1, 2, 3, 4],
            "high": [1, 2, 3, 4],
            "low": [1, 2, 3, 4],
            "close": [1, 2, 3, 4],
        }
    )
    monkeypatch.setattr(
        "crypto_bot.main.MarketDataFetcher.get_price_df", lambda self, **kw: dummy_df
    )

    # 2) prepare_ml_dataset を簡易化
    X = pd.DataFrame({"f": [0, 1, 0, 1]})
    y = pd.Series([0, 1, 0, 1])
    monkeypatch.setattr("crypto_bot.main.prepare_ml_dataset", lambda df, cfg: (X, y, y))

    # 3) LogisticRegression を DummyEstimator に置換
    monkeypatch.setattr(
        "crypto_bot.main.LogisticRegression", lambda **kw: DummyEstimator()
    )

    # 4) テスト用の config.yml を作成
    cfg = {
        "data": {"symbol": "BTC/USDT", "timeframe": "1h", "since": None, "limit": 4},
        "ml": {
            "feat_period": 2,
            "lags": [1],
            "rolling_window": 2,
            "horizon": 1,
            "threshold": 0.0,
        },
    }
    cfg_path = tmp_path / "config.yml"
    cfg_path.write_text(yaml.safe_dump(cfg))
    model_path = tmp_path / "model.pkl"

    # CLI 実行
    runner = CliRunner()
    result = runner.invoke(cli, ["train", "-c", str(cfg_path), "-o", str(model_path)])
    assert result.exit_code == 0

    # サンプル数は X の行数 (4) になっていること
    assert "Training classification model on 4 samples" in result.output

    # モデルファイルが作成されている
    assert model_path.exists()

    # 保存されたオブジェクトが DummyEstimator であること
    loaded = joblib.load(model_path)
    assert isinstance(loaded, DummyEstimator)

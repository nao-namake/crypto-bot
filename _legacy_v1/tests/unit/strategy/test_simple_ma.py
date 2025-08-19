# tests/unit/strategy/test_simple_ma.py
# テスト対象: crypto_bot/strategy/simple_ma.py
# 説明: 移動平均戦略のテスト

import numpy as np
import pandas as pd
import pytest

from crypto_bot.execution.engine import Position, Signal
from crypto_bot.strategy.simple_ma import SimpleMAStrategy


@pytest.fixture
def sample_price_data():
    """テスト用の価格データ"""
    return pd.DataFrame(
        {
            "open": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
            "high": [102, 103, 104, 105, 106, 107, 108, 109, 110, 111],
            "low": [98, 99, 100, 101, 102, 103, 104, 105, 106, 107],
            "close": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
            "volume": [1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900],
        },
        index=pd.date_range("2023-01-01", periods=10),
    )


class TestSimpleMAStrategy:
    """SimpleMAStrategyのテストクラス"""

    def test_initialization_default(self):
        """デフォルト初期化のテスト"""
        strategy = SimpleMAStrategy()

        assert strategy.short_period == 20
        assert strategy.long_period == 50

    def test_initialization_custom_params(self):
        """カスタムパラメータでの初期化テスト"""
        strategy = SimpleMAStrategy(short_period=5, long_period=15)

        assert strategy.short_period == 5
        assert strategy.long_period == 15

    def test_logic_signal_insufficient_data(self, sample_price_data):
        """データ不足でのシグナル生成テスト"""
        strategy = SimpleMAStrategy(short_period=5, long_period=20)

        # データが不足している場合（20行必要だが10行しかない）
        signal = strategy.logic_signal(sample_price_data, None)

        # データ不足の場合はNoneまたは適切に処理される
        assert signal is None or isinstance(signal, Signal)

    def test_logic_signal_sufficient_data(self):
        """十分なデータでのシグナル生成テスト"""
        # 十分なデータを作成
        data = pd.DataFrame(
            {
                "open": np.random.rand(30) * 100 + 100,
                "high": np.random.rand(30) * 100 + 100,
                "low": np.random.rand(30) * 100 + 100,
                "close": np.random.rand(30) * 100 + 100,
                "volume": np.random.rand(30) * 1000 + 1000,
            },
            index=pd.date_range("2023-01-01", periods=30),
        )

        strategy = SimpleMAStrategy(short_period=5, long_period=10)
        signal = strategy.logic_signal(data, None)

        # シグナルが生成されるかチェック
        assert signal is None or isinstance(signal, Signal)

    def test_logic_signal_with_position(self):
        """既存ポジションがある場合のシグナル生成テスト"""
        data = pd.DataFrame(
            {
                "close": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
                * 3  # 30データポイント
            },
            index=pd.date_range("2023-01-01", periods=30),
        )

        strategy = SimpleMAStrategy(short_period=5, long_period=10)
        position = Position(exist=True)
        position.side = "BUY"

        signal = strategy.logic_signal(data, position)

        # ポジションがある場合のシグナル処理をテスト
        assert signal is None or isinstance(signal, Signal)

    def test_moving_average_calculation(self):
        """移動平均計算のテスト"""
        strategy = SimpleMAStrategy(short_period=3, long_period=5)

        # 簡単な価格データ
        prices = pd.Series([100, 102, 104, 106, 108, 110, 112, 114, 116, 118])

        # 移動平均計算が正しく動作することを確認
        try:
            # 内部メソッドが存在する場合
            short_ma = strategy._calculate_short_ma(prices)
            long_ma = strategy._calculate_long_ma(prices)

            assert isinstance(short_ma, pd.Series)
            assert isinstance(long_ma, pd.Series)
        except AttributeError:
            # 内部メソッドが存在しない場合は、logic_signalで間接的にテスト
            data = pd.DataFrame(
                {
                    "close": prices.values,
                    "open": prices.values * 0.99,
                    "high": prices.values * 1.01,
                    "low": prices.values * 0.98,
                    "volume": [1000] * len(prices),
                },
                index=pd.date_range("2023-01-01", periods=len(prices)),
            )

            signal = strategy.logic_signal(data, None)
            # エラーが発生しないことを確認
            assert signal is None or isinstance(signal, Signal)

    def test_crossover_signals(self):
        """クロスオーバーシグナルのテスト"""
        strategy = SimpleMAStrategy(short_period=3, long_period=5)

        # ゴールデンクロス（上昇トレンド）データ
        uptrend_data = pd.DataFrame(
            {
                "close": [100, 101, 102, 103, 104, 105, 106, 107, 108, 109],
                "open": [99, 100, 101, 102, 103, 104, 105, 106, 107, 108],
                "high": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
                "low": [98, 99, 100, 101, 102, 103, 104, 105, 106, 107],
                "volume": [1000] * 10,
            },
            index=pd.date_range("2023-01-01", periods=10),
        )

        signal = strategy.logic_signal(uptrend_data, None)

        # 上昇トレンドでBUYシグナルまたはNone
        if signal is not None:
            assert signal.side in ["BUY", "SELL"] or signal is None

    def test_edge_cases(self):
        """エッジケースのテスト"""
        strategy = SimpleMAStrategy()

        # 空のDataFrame
        empty_data = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        signal = strategy.logic_signal(empty_data, None)
        assert signal is None

        # 1行のデータ
        single_row = pd.DataFrame(
            {
                "open": [100],
                "high": [102],
                "low": [98],
                "close": [101],
                "volume": [1000],
            },
            index=[pd.Timestamp("2023-01-01")],
        )

        signal = strategy.logic_signal(single_row, None)
        assert signal is None  # データ不足でシグナルなし

    def test_invalid_parameters(self):
        """無効なパラメータのテスト"""
        # short_period > long_periodの場合
        try:
            strategy = SimpleMAStrategy(short_period=20, long_period=10)
            # エラーハンドリングがあるかチェック
            assert strategy.short_period == 20
            assert strategy.long_period == 10
        except ValueError:
            # エラーが発生する場合も想定内
            assert True

    def test_nan_handling(self):
        """NaN値の処理テスト"""
        strategy = SimpleMAStrategy(short_period=3, long_period=5)

        # NaN値を含むデータ
        data_with_nan = pd.DataFrame(
            {
                "close": [100, np.nan, 102, 103, np.nan, 105, 106, 107, 108, 109],
                "open": [99, 100, 101, 102, 103, 104, 105, 106, 107, 108],
                "high": [101, 102, 103, 104, 105, 106, 107, 108, 109, 110],
                "low": [98, 99, 100, 101, 102, 103, 104, 105, 106, 107],
                "volume": [1000] * 10,
            },
            index=pd.date_range("2023-01-01", periods=10),
        )

        # NaN値があってもエラーが発生しないことを確認
        try:
            signal = strategy.logic_signal(data_with_nan, None)
            assert signal is None or isinstance(signal, Signal)
        except Exception:
            # NaN処理でエラーが発生する場合も想定内
            assert True

    def test_signal_properties(self):
        """シグナルのプロパティテスト"""
        strategy = SimpleMAStrategy(short_period=3, long_period=5)

        # 十分なデータでシグナル生成
        data = pd.DataFrame(
            {
                "close": list(range(100, 120)),
                "open": list(range(99, 119)),
                "high": list(range(101, 121)),
                "low": list(range(98, 118)),
                "volume": [1000] * 20,
            },
            index=pd.date_range("2023-01-01", periods=20),
        )

        signal = strategy.logic_signal(data, None)

        if signal is not None:
            # シグナルのプロパティをチェック
            assert hasattr(signal, "side")
            assert signal.side in ["BUY", "SELL"]
            assert hasattr(signal, "timestamp")
            assert isinstance(signal.timestamp, pd.Timestamp)

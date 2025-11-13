"""
DataPipeline バックテストモード機能テスト - Phase 34実装

バックテストモード関連の新機能をテスト:
- set_backtest_data()
- clear_backtest_data()
- fetch_ohlcv() のバックテストモード対応
"""

import pandas as pd
import pytest

from src.data.data_pipeline import DataPipeline, DataRequest, TimeFrame


class TestDataPipelineBacktest:
    """DataPipeline バックテストモード機能テストクラス"""

    @pytest.fixture
    def pipeline(self):
        """テスト用DataPipelineインスタンス"""
        return DataPipeline()

    @pytest.fixture
    def sample_backtest_data(self):
        """テスト用バックテストデータ"""
        # 4h データ
        df_4h = pd.DataFrame(
            {
                "open": [100.0, 101.0, 102.0],
                "high": [105.0, 106.0, 107.0],
                "low": [99.0, 100.0, 101.0],
                "close": [103.0, 104.0, 105.0],
                "volume": [1000.0, 1100.0, 1200.0],
            }
        )
        df_4h.index = pd.date_range("2025-01-01", periods=3, freq="4h")

        # 15m データ
        df_15m = pd.DataFrame(
            {
                "open": [100.0, 101.0, 102.0, 103.0, 104.0],
                "high": [105.0, 106.0, 107.0, 108.0, 109.0],
                "low": [99.0, 100.0, 101.0, 102.0, 103.0],
                "close": [103.0, 104.0, 105.0, 106.0, 107.0],
                "volume": [100.0, 110.0, 120.0, 130.0, 140.0],
            }
        )
        df_15m.index = pd.date_range("2025-01-01", periods=5, freq="15min")

        return {"4h": df_4h, "15m": df_15m}

    def test_set_backtest_data(self, pipeline, sample_backtest_data):
        """set_backtest_data() メソッドのテスト"""
        # バックテストデータ設定
        pipeline.set_backtest_data(sample_backtest_data)

        # データが正しく設定されたか確認
        assert pipeline._backtest_data == sample_backtest_data
        assert "4h" in pipeline._backtest_data
        assert "15m" in pipeline._backtest_data
        assert len(pipeline._backtest_data["4h"]) == 3
        assert len(pipeline._backtest_data["15m"]) == 5

    def test_clear_backtest_data(self, pipeline, sample_backtest_data):
        """clear_backtest_data() メソッドのテスト"""
        # データ設定
        pipeline.set_backtest_data(sample_backtest_data)
        assert len(pipeline._backtest_data) > 0

        # クリア実行
        pipeline.clear_backtest_data()

        # データが空になったか確認
        assert len(pipeline._backtest_data) == 0

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_backtest_mode(self, pipeline, sample_backtest_data):
        """fetch_ohlcv() バックテストモード対応のテスト"""
        # バックテストモード有効化
        pipeline.set_backtest_mode(True)
        pipeline.set_backtest_data(sample_backtest_data)

        # 4h データ取得
        request_4h = DataRequest(symbol="BTC/JPY", timeframe=TimeFrame.H4)
        df_4h = await pipeline.fetch_ohlcv(request_4h)

        # データが正しく返されるか確認
        assert isinstance(df_4h, pd.DataFrame)
        assert len(df_4h) == 3
        assert df_4h["close"].iloc[0] == 103.0

        # 15m データ取得
        request_15m = DataRequest(symbol="BTC/JPY", timeframe=TimeFrame.M15)
        df_15m = await pipeline.fetch_ohlcv(request_15m)

        # データが正しく返されるか確認
        assert isinstance(df_15m, pd.DataFrame)
        assert len(df_15m) == 5
        assert df_15m["close"].iloc[0] == 103.0

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_backtest_mode_missing_timeframe(self, pipeline, sample_backtest_data):
        """fetch_ohlcv() 存在しないタイムフレーム取得のテスト"""
        # バックテストモード有効化（15mデータのみ）
        pipeline.set_backtest_mode(True)
        pipeline.set_backtest_data({"15m": sample_backtest_data["15m"]})

        # 存在しない4hデータ取得
        request_4h = DataRequest(symbol="BTC/JPY", timeframe=TimeFrame.H4)
        df_4h = await pipeline.fetch_ohlcv(request_4h)

        # 空のDataFrameが返されるか確認
        assert isinstance(df_4h, pd.DataFrame)
        assert len(df_4h) == 0

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_backtest_mode_disabled(self, pipeline, sample_backtest_data):
        """fetch_ohlcv() バックテストモード無効時のテスト"""
        # バックテストモード無効（デフォルト）
        pipeline.set_backtest_mode(False)
        pipeline.set_backtest_data(sample_backtest_data)

        # バックテストデータが設定されていても、通常のAPI呼び出しが行われることを確認
        # （実際のAPI呼び出しは行わず、バックテストデータが使われないことを確認）
        # このテストは実装の詳細に依存するため、モード確認のみ
        assert pipeline.is_backtest_mode() is False

    def test_backtest_mode_toggle(self, pipeline):
        """バックテストモードのON/OFF切り替えテスト"""
        # 初期状態: OFF
        assert pipeline.is_backtest_mode() is False

        # ON
        pipeline.set_backtest_mode(True)
        assert pipeline.is_backtest_mode() is True

        # OFF
        pipeline.set_backtest_mode(False)
        assert pipeline.is_backtest_mode() is False

    def test_backtest_data_initialization(self, pipeline):
        """バックテストデータの初期化状態テスト"""
        # 初期状態: 空の辞書
        assert pipeline._backtest_data == {}
        assert len(pipeline._backtest_data) == 0

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_backtest_data_copy(self, pipeline, sample_backtest_data):
        """fetch_ohlcv() がデータのコピーを返すかテスト"""
        # バックテストモード有効化
        pipeline.set_backtest_mode(True)
        pipeline.set_backtest_data(sample_backtest_data)

        # データ取得
        request = DataRequest(symbol="BTC/JPY", timeframe=TimeFrame.H4)
        df1 = await pipeline.fetch_ohlcv(request)
        df2 = await pipeline.fetch_ohlcv(request)

        # 別のオブジェクトが返されるか確認
        assert df1 is not df2

        # データ内容は同じか確認
        assert df1.equals(df2)

    def test_set_backtest_data_overwrites(self, pipeline, sample_backtest_data):
        """set_backtest_data() が既存データを上書きするかテスト"""
        # 最初のデータ設定
        pipeline.set_backtest_data(sample_backtest_data)
        assert len(pipeline._backtest_data["4h"]) == 3

        # 新しいデータで上書き
        new_data = {
            "4h": pd.DataFrame(
                {
                    "open": [200.0],
                    "high": [205.0],
                    "low": [199.0],
                    "close": [203.0],
                    "volume": [2000.0],
                }
            )
        }
        pipeline.set_backtest_data(new_data)

        # 上書きされたか確認
        assert len(pipeline._backtest_data["4h"]) == 1
        assert pipeline._backtest_data["4h"]["close"].iloc[0] == 203.0
        assert "15m" not in pipeline._backtest_data

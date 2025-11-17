"""
DataPipeline 主要機能テスト

主要機能のカバレッジ向上を目的としたテストスイート。
データ取得・キャッシング・品質チェック・マルチタイムフレーム対応をテスト。

カバー範囲:
- キャッシュ機能（生成・検証・クリア）
- データ品質チェック
- OHLCV変換
- fetch_ohlcv（リトライ機能含む）
- fetch_multi_timeframe
- get_latest_prices
- fetch_historical_data
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest

from src.core.exceptions import DataFetchError
from src.data.data_pipeline import DataPipeline, DataRequest, TimeFrame


@pytest.fixture
def mock_bitbank_client():
    """モックBitbankClient"""
    client = AsyncMock()
    client.fetch_ohlcv = AsyncMock()
    client.set_backtest_mode = Mock()
    return client


@pytest.fixture
def pipeline(mock_bitbank_client):
    """テスト用DataPipelineインスタンス"""
    return DataPipeline(client=mock_bitbank_client)


@pytest.fixture
def sample_ohlcv_data():
    """テスト用OHLCVデータ"""
    return [
        [1704067200000, 14000000.0, 14100000.0, 13900000.0, 14050000.0, 1000.0],
        [1704070800000, 14050000.0, 14150000.0, 14000000.0, 14100000.0, 1100.0],
        [1704074400000, 14100000.0, 14200000.0, 14050000.0, 14150000.0, 1200.0],
    ]


class TestCacheFunctionality:
    """キャッシュ機能テスト"""

    def test_generate_cache_key(self, pipeline):
        """キャッシュキー生成テスト"""
        request = DataRequest(symbol="BTC/JPY", timeframe=TimeFrame.H4, limit=1000)
        key = pipeline._generate_cache_key(request)

        assert key == "BTC/JPY_4h_1000"
        assert isinstance(key, str)

    def test_generate_cache_key_different_timeframes(self, pipeline):
        """異なるタイムフレームで異なるキーが生成される"""
        request_4h = DataRequest(symbol="BTC/JPY", timeframe=TimeFrame.H4, limit=100)
        request_15m = DataRequest(symbol="BTC/JPY", timeframe=TimeFrame.M15, limit=100)

        key_4h = pipeline._generate_cache_key(request_4h)
        key_15m = pipeline._generate_cache_key(request_15m)

        assert key_4h != key_15m
        assert "4h" in key_4h
        assert "15m" in key_15m

    def test_is_cache_valid_empty_cache(self, pipeline):
        """空キャッシュは無効"""
        assert pipeline._is_cache_valid("non_existent_key") is False

    def test_is_cache_valid_fresh_cache(self, pipeline):
        """新しいキャッシュは有効"""
        cache_key = "test_key"
        pipeline._cache_timestamps[cache_key] = datetime.now()

        assert pipeline._is_cache_valid(cache_key) is True

    def test_is_cache_valid_expired_cache(self, pipeline):
        """期限切れキャッシュは無効"""
        cache_key = "test_key"
        # 10分前のタイムスタンプ（cache_duration_minutes=5なので期限切れ）
        pipeline._cache_timestamps[cache_key] = datetime.now() - timedelta(minutes=10)

        assert pipeline._is_cache_valid(cache_key) is False

    def test_clear_cache(self, pipeline):
        """キャッシュクリア"""
        # キャッシュにデータ追加
        pipeline._cache["test_key"] = pd.DataFrame({"close": [1, 2, 3]})
        pipeline._cache_timestamps["test_key"] = datetime.now()

        assert len(pipeline._cache) > 0
        assert len(pipeline._cache_timestamps) > 0

        # クリア実行
        pipeline.clear_cache()

        assert len(pipeline._cache) == 0
        assert len(pipeline._cache_timestamps) == 0

    def test_get_cache_info(self, pipeline):
        """キャッシュ情報取得"""
        # テストデータ追加
        df = pd.DataFrame({"close": [14000000.0, 14100000.0, 14200000.0]})
        pipeline._cache["BTC/JPY_4h_100"] = df
        pipeline._cache_timestamps["BTC/JPY_4h_100"] = datetime.now()

        info = pipeline.get_cache_info()

        assert "total_cached_items" in info
        assert info["total_cached_items"] == 1
        assert "cache_size_mb" in info
        assert "items" in info
        assert len(info["items"]) == 1
        assert info["items"][0]["key"] == "BTC/JPY_4h_100"
        assert info["items"][0]["is_valid"] is True


class TestDataValidation:
    """データ品質チェックテスト"""

    def test_validate_ohlcv_data_valid(self, pipeline, sample_ohlcv_data):
        """正常なOHLCVデータは検証成功"""
        assert pipeline._validate_ohlcv_data(sample_ohlcv_data) is True

    def test_validate_ohlcv_data_empty(self, pipeline):
        """空データは検証失敗"""
        assert pipeline._validate_ohlcv_data([]) is False

    def test_validate_ohlcv_data_wrong_columns(self, pipeline):
        """カラム数不正は検証失敗"""
        invalid_data = [[1704067200000, 14000000.0, 14100000.0, 13900000.0]]  # 4列のみ（6列必要）
        assert pipeline._validate_ohlcv_data(invalid_data) is False

    def test_validate_ohlcv_data_high_lower_than_low(self, pipeline):
        """high < low は検証失敗"""
        invalid_data = [
            [1704067200000, 14000000.0, 13900000.0, 14100000.0, 14050000.0, 1000.0]
        ]  # high < low
        assert pipeline._validate_ohlcv_data(invalid_data) is False

    def test_validate_ohlcv_data_negative_volume(self, pipeline):
        """負のvolumeは検証失敗"""
        invalid_data = [
            [1704067200000, 14000000.0, 14100000.0, 13900000.0, 14050000.0, -1000.0]
        ]  # 負volume
        assert pipeline._validate_ohlcv_data(invalid_data) is False

    def test_validate_ohlcv_data_non_numeric(self, pipeline):
        """非数値データは検証失敗"""
        invalid_data = [[1704067200000, "invalid", 14100000.0, 13900000.0, 14050000.0, 1000.0]]
        assert pipeline._validate_ohlcv_data(invalid_data) is False


class TestDataConversion:
    """データ変換テスト"""

    def test_convert_to_dataframe(self, pipeline, sample_ohlcv_data):
        """OHLCV → DataFrame変換"""
        df = pipeline._convert_to_dataframe(sample_ohlcv_data)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert list(df.columns) == ["open", "high", "low", "close", "volume"]
        assert df.index.name == "timestamp"

    def test_convert_to_dataframe_types(self, pipeline, sample_ohlcv_data):
        """データ型が正しく変換される"""
        df = pipeline._convert_to_dataframe(sample_ohlcv_data)

        assert df["open"].dtype == float
        assert df["high"].dtype == float
        assert df["low"].dtype == float
        assert df["close"].dtype == float
        assert df["volume"].dtype == float

    def test_convert_to_dataframe_sorted(self, pipeline):
        """タイムスタンプ順にソートされる"""
        # 逆順のデータ
        unsorted_data = [
            [1704074400000, 14100000.0, 14200000.0, 14050000.0, 14150000.0, 1200.0],
            [1704067200000, 14000000.0, 14100000.0, 13900000.0, 14050000.0, 1000.0],
            [1704070800000, 14050000.0, 14150000.0, 14000000.0, 14100000.0, 1100.0],
        ]

        df = pipeline._convert_to_dataframe(unsorted_data)

        # ソートされていることを確認
        assert df.index[0] < df.index[1] < df.index[2]


class TestFetchOhlcv:
    """fetch_ohlcv() テスト"""

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_success(self, pipeline, mock_bitbank_client, sample_ohlcv_data):
        """正常なデータ取得"""
        mock_bitbank_client.fetch_ohlcv.return_value = sample_ohlcv_data

        request = DataRequest(symbol="BTC/JPY", timeframe=TimeFrame.H4, limit=100)
        df = await pipeline.fetch_ohlcv(request)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert "close" in df.columns
        mock_bitbank_client.fetch_ohlcv.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_with_cache(self, pipeline, mock_bitbank_client, sample_ohlcv_data):
        """キャッシュがある場合はAPIを呼ばない"""
        mock_bitbank_client.fetch_ohlcv.return_value = sample_ohlcv_data

        request = DataRequest(symbol="BTC/JPY", timeframe=TimeFrame.H4, limit=100)

        # 1回目: APIから取得
        df1 = await pipeline.fetch_ohlcv(request, use_cache=True)
        assert len(df1) == 3

        # 2回目: キャッシュから取得（API呼び出しなし）
        df2 = await pipeline.fetch_ohlcv(request, use_cache=True)
        assert len(df2) == 3

        # API呼び出しは1回のみ
        assert mock_bitbank_client.fetch_ohlcv.call_count == 1

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_cache_disabled(
        self, pipeline, mock_bitbank_client, sample_ohlcv_data
    ):
        """キャッシュ無効時は毎回APIを呼ぶ"""
        mock_bitbank_client.fetch_ohlcv.return_value = sample_ohlcv_data

        request = DataRequest(symbol="BTC/JPY", timeframe=TimeFrame.H4, limit=100)

        await pipeline.fetch_ohlcv(request, use_cache=False)
        await pipeline.fetch_ohlcv(request, use_cache=False)

        # API呼び出しは2回
        assert mock_bitbank_client.fetch_ohlcv.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_retry_on_failure(self, pipeline, mock_bitbank_client):
        """エラー時のリトライ機能"""
        # 最初の2回は失敗、3回目は成功
        mock_bitbank_client.fetch_ohlcv.side_effect = [
            Exception("API Error 1"),
            Exception("API Error 2"),
            [[1704067200000, 14000000.0, 14100000.0, 13900000.0, 14050000.0, 1000.0]],
        ]

        pipeline.retry_delay = 0.01  # テスト高速化

        request = DataRequest(symbol="BTC/JPY", timeframe=TimeFrame.H4, limit=100)
        df = await pipeline.fetch_ohlcv(request, use_cache=False)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        # 3回試行された
        assert mock_bitbank_client.fetch_ohlcv.call_count == 3

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_max_retries_exceeded(self, pipeline, mock_bitbank_client):
        """最大リトライ回数超過でエラー"""
        # 常に失敗
        mock_bitbank_client.fetch_ohlcv.side_effect = Exception("Persistent API Error")

        pipeline.retry_delay = 0.01  # テスト高速化

        request = DataRequest(symbol="BTC/JPY", timeframe=TimeFrame.H4, limit=100)

        with pytest.raises(DataFetchError, match="データ取得に失敗しました"):
            await pipeline.fetch_ohlcv(request, use_cache=False)

        # max_retries=3回試行された
        assert mock_bitbank_client.fetch_ohlcv.call_count == 3

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_validation_failure(self, pipeline, mock_bitbank_client):
        """データ品質チェック失敗時のリトライ"""
        # 不正なデータ（high < low）
        invalid_data = [[1704067200000, 14000000.0, 13900000.0, 14100000.0, 14050000.0, 1000.0]]
        mock_bitbank_client.fetch_ohlcv.return_value = invalid_data

        pipeline.retry_delay = 0.01

        request = DataRequest(symbol="BTC/JPY", timeframe=TimeFrame.H4, limit=100)

        with pytest.raises(DataFetchError, match="データ取得に失敗しました"):
            await pipeline.fetch_ohlcv(request, use_cache=False)


class TestMultiTimeframe:
    """fetch_multi_timeframe() テスト"""

    @pytest.mark.asyncio
    async def test_fetch_multi_timeframe_success(
        self, pipeline, mock_bitbank_client, sample_ohlcv_data
    ):
        """マルチタイムフレーム取得成功"""
        mock_bitbank_client.fetch_ohlcv.return_value = sample_ohlcv_data

        results = await pipeline.fetch_multi_timeframe(symbol="BTC/JPY", limit=100)

        assert isinstance(results, dict)
        assert "4h" in results
        assert "15m" in results
        assert isinstance(results["4h"], pd.DataFrame)
        assert isinstance(results["15m"], pd.DataFrame)

    @pytest.mark.asyncio
    async def test_fetch_multi_timeframe_partial_failure(
        self, pipeline, mock_bitbank_client, sample_ohlcv_data
    ):
        """一部のタイムフレーム取得失敗でも継続"""
        # 15m成功、4h失敗
        mock_bitbank_client.fetch_ohlcv.side_effect = [
            Exception("4h fetch failed"),
            sample_ohlcv_data,  # 15m成功
        ]

        results = await pipeline.fetch_multi_timeframe(symbol="BTC/JPY", limit=100)

        # 失敗したタイムフレームは空DataFrame
        assert isinstance(results["4h"], pd.DataFrame)
        assert len(results["4h"]) == 0
        # 成功したタイムフレームは正常なデータ
        assert len(results["15m"]) == 3

    @pytest.mark.asyncio
    @patch("src.core.config.get_config")
    async def test_fetch_multi_timeframe_symbol_from_config(
        self, mock_get_config, pipeline, mock_bitbank_client, sample_ohlcv_data
    ):
        """symbol未指定時は設定から取得"""
        mock_config = Mock()
        mock_config.exchange.symbol = "ETH/JPY"
        mock_get_config.return_value = mock_config

        mock_bitbank_client.fetch_ohlcv.return_value = sample_ohlcv_data

        results = await pipeline.fetch_multi_timeframe(symbol=None, limit=100)

        # ETH/JPYで呼ばれたか確認
        calls = mock_bitbank_client.fetch_ohlcv.call_args_list
        for call in calls:
            kwargs = call[1]
            assert kwargs["symbol"] == "ETH/JPY"


class TestLatestPrices:
    """get_latest_prices() テスト"""

    @pytest.mark.asyncio
    async def test_get_latest_prices(self, pipeline, mock_bitbank_client, sample_ohlcv_data):
        """最新価格取得"""
        mock_bitbank_client.fetch_ohlcv.return_value = sample_ohlcv_data

        prices = await pipeline.get_latest_prices(symbol="BTC/JPY")

        assert isinstance(prices, dict)
        assert "4h" in prices
        assert "15m" in prices
        # 最新価格はsample_ohlcv_dataの最後のclose
        assert prices["4h"] == 14150000.0
        assert prices["15m"] == 14150000.0

    @pytest.mark.asyncio
    async def test_get_latest_prices_with_failure(
        self, pipeline, mock_bitbank_client, sample_ohlcv_data
    ):
        """一部失敗しても継続"""
        # 4h失敗、15m成功
        mock_bitbank_client.fetch_ohlcv.side_effect = [
            Exception("Failed"),
            sample_ohlcv_data,
        ]

        prices = await pipeline.get_latest_prices(symbol="BTC/JPY")

        # 失敗したタイムフレームはキーが存在しない
        assert "4h" not in prices
        # 成功したタイムフレームは正常
        assert "15m" in prices


class TestHistoricalData:
    """fetch_historical_data() テスト"""

    @pytest.mark.asyncio
    async def test_fetch_historical_data(self, pipeline, mock_bitbank_client, sample_ohlcv_data):
        """過去データ取得"""
        mock_bitbank_client.fetch_ohlcv.return_value = sample_ohlcv_data

        since = datetime(2025, 1, 1)
        df = await pipeline.fetch_historical_data(
            symbol="BTC/JPY", timeframe="4h", since=since, limit=100
        )

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3

    @pytest.mark.asyncio
    async def test_fetch_historical_data_timeframe_mapping(
        self, pipeline, mock_bitbank_client, sample_ohlcv_data
    ):
        """タイムフレーム文字列のマッピング"""
        mock_bitbank_client.fetch_ohlcv.return_value = sample_ohlcv_data

        # "15m" → TimeFrame.M15
        df_15m = await pipeline.fetch_historical_data(symbol="BTC/JPY", timeframe="15m", limit=100)
        assert isinstance(df_15m, pd.DataFrame)

        # "4h" → TimeFrame.H4
        df_4h = await pipeline.fetch_historical_data(symbol="BTC/JPY", timeframe="4h", limit=100)
        assert isinstance(df_4h, pd.DataFrame)

    @pytest.mark.asyncio
    async def test_fetch_historical_data_error_handling(self, pipeline, mock_bitbank_client):
        """エラー時は空DataFrame"""
        mock_bitbank_client.fetch_ohlcv.side_effect = Exception("API Error")

        df = await pipeline.fetch_historical_data(symbol="BTC/JPY", timeframe="4h", limit=100)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0


class TestGlobalFunctions:
    """グローバル関数テスト"""

    @patch("src.data.data_pipeline._data_pipeline", None)
    def test_get_data_pipeline_singleton(self):
        """get_data_pipeline()はシングルトン"""
        from src.data.data_pipeline import get_data_pipeline

        pipeline1 = get_data_pipeline()
        pipeline2 = get_data_pipeline()

        # 同一インスタンス
        assert pipeline1 is pipeline2

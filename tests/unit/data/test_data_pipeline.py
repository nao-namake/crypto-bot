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
            [1704067200000, 14000000.0, 13900000.0, 14100000.0, 14050000.0, 1000.0]  # high < low
        ]
        assert pipeline._validate_ohlcv_data(invalid_data) is False

    def test_validate_ohlcv_data_negative_volume(self, pipeline):
        """負のvolumeは検証失敗"""
        invalid_data = [
            [1704067200000, 14000000.0, 14100000.0, 13900000.0, 14050000.0, -1000.0]  # 負volume
        ]
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


class TestBacktestMode:
    """バックテストモード関連テスト"""

    def test_set_backtest_mode_enable(self, pipeline, mock_bitbank_client):
        """バックテストモード有効化"""
        pipeline.set_backtest_mode(True)

        assert pipeline._backtest_mode is True
        mock_bitbank_client.set_backtest_mode.assert_called_once_with(True)

    def test_set_backtest_mode_disable(self, pipeline, mock_bitbank_client):
        """バックテストモード無効化"""
        pipeline._backtest_mode = True  # 先に有効化
        pipeline.set_backtest_mode(False)

        assert pipeline._backtest_mode is False
        mock_bitbank_client.set_backtest_mode.assert_called_with(False)

    def test_set_backtest_mode_client_without_method(self, pipeline):
        """set_backtest_modeメソッドがないクライアント"""
        # メソッドを削除
        del pipeline.client.set_backtest_mode

        # エラーが発生しないことを確認
        pipeline.set_backtest_mode(True)
        assert pipeline._backtest_mode is True

    def test_is_backtest_mode(self, pipeline):
        """バックテストモード状態取得"""
        assert pipeline.is_backtest_mode() is False

        pipeline._backtest_mode = True
        assert pipeline.is_backtest_mode() is True

    def test_set_backtest_data(self, pipeline):
        """バックテストデータ設定"""
        df_4h = pd.DataFrame({"close": [14000000.0, 14100000.0]})
        df_15m = pd.DataFrame({"close": [14000000.0, 14050000.0, 14100000.0]})

        data = {"4h": df_4h, "15m": df_15m}
        pipeline.set_backtest_data(data)

        assert "4h" in pipeline._backtest_data
        assert "15m" in pipeline._backtest_data
        assert len(pipeline._backtest_data["4h"]) == 2
        assert len(pipeline._backtest_data["15m"]) == 3

    def test_clear_backtest_data(self, pipeline):
        """バックテストデータクリア"""
        pipeline._backtest_data = {"4h": pd.DataFrame({"close": [1, 2, 3]})}

        pipeline.clear_backtest_data()

        assert len(pipeline._backtest_data) == 0

    def test_set_backtest_ml_prediction(self, pipeline):
        """ML予測設定"""
        prediction = {"predicted_action": "BUY", "confidence": 0.85}
        pipeline.set_backtest_ml_prediction(prediction)

        assert pipeline._backtest_ml_prediction == prediction

    def test_get_backtest_ml_prediction(self, pipeline):
        """ML予測取得"""
        # 初期状態はNone
        assert pipeline.get_backtest_ml_prediction() is None

        # 設定後は値が取得できる
        prediction = {"predicted_action": "SELL", "confidence": 0.70}
        pipeline._backtest_ml_prediction = prediction

        assert pipeline.get_backtest_ml_prediction() == prediction

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_backtest_mode_with_data(self, pipeline):
        """バックテストモードでデータが存在する場合"""
        # バックテストモード有効化
        pipeline._backtest_mode = True

        # バックテストデータ設定
        df = pd.DataFrame(
            {
                "open": [14000000.0],
                "high": [14100000.0],
                "low": [13900000.0],
                "close": [14050000.0],
                "volume": [1000.0],
            }
        )
        pipeline._backtest_data = {"4h": df}

        request = DataRequest(symbol="BTC/JPY", timeframe=TimeFrame.H4, limit=100)
        result = await pipeline.fetch_ohlcv(request)

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        # コピーが返されることを確認（元データが変更されない）
        assert result is not pipeline._backtest_data["4h"]

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_backtest_mode_missing_timeframe(self, pipeline):
        """バックテストモードで要求タイムフレームが存在しない場合"""
        pipeline._backtest_mode = True
        pipeline._backtest_data = {"4h": pd.DataFrame()}  # 15mは存在しない

        request = DataRequest(symbol="BTC/JPY", timeframe=TimeFrame.M15, limit=100)
        result = await pipeline.fetch_ohlcv(request)

        # 空のDataFrameが返される
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0


class TestDataValidationEdgeCases:
    """データ品質チェック追加テスト"""

    def test_validate_ohlcv_data_low_greater_than_open(self, pipeline):
        """low > open は検証失敗"""
        invalid_data = [
            [1704067200000, 14000000.0, 14200000.0, 14100000.0, 14050000.0, 1000.0]  # low > open
        ]
        assert pipeline._validate_ohlcv_data(invalid_data) is False

    def test_validate_ohlcv_data_low_greater_than_close(self, pipeline):
        """low > close は検証失敗"""
        invalid_data = [
            [1704067200000, 14100000.0, 14200000.0, 14050000.0, 14000000.0, 1000.0]  # low > close
        ]
        assert pipeline._validate_ohlcv_data(invalid_data) is False

    def test_validate_ohlcv_data_high_less_than_open(self, pipeline):
        """high < open は検証失敗"""
        invalid_data = [
            [1704067200000, 14100000.0, 14000000.0, 13900000.0, 14050000.0, 1000.0]  # high < open
        ]
        assert pipeline._validate_ohlcv_data(invalid_data) is False

    def test_validate_ohlcv_data_high_less_than_close(self, pipeline):
        """high < close は検証失敗"""
        invalid_data = [
            [1704067200000, 14000000.0, 14050000.0, 13900000.0, 14100000.0, 1000.0]  # high < close
        ]
        assert pipeline._validate_ohlcv_data(invalid_data) is False

    def test_validate_ohlcv_data_zero_volume(self, pipeline):
        """volume=0は検証成功（0は許容）"""
        valid_data = [[1704067200000, 14000000.0, 14100000.0, 13900000.0, 14050000.0, 0.0]]
        assert pipeline._validate_ohlcv_data(valid_data) is True


class TestMultiTimeframeEdgeCases:
    """fetch_multi_timeframe() 追加テスト"""

    @pytest.mark.asyncio
    async def test_fetch_multi_timeframe_none_return(self, pipeline, mock_bitbank_client):
        """fetch_ohlcvがNoneを返す場合、空DataFrameで代替"""
        # fetch_ohlcvを直接モック
        with patch.object(pipeline, "fetch_ohlcv", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = None

            # ValueErrorは内部でキャッチされ、空DataFrameで代替される
            results = await pipeline.fetch_multi_timeframe(symbol="BTC/JPY", limit=100)

            # 両方とも空DataFrame
            assert isinstance(results["4h"], pd.DataFrame)
            assert len(results["4h"]) == 0
            assert isinstance(results["15m"], pd.DataFrame)
            assert len(results["15m"]) == 0

    @pytest.mark.asyncio
    async def test_fetch_multi_timeframe_dict_return(
        self, pipeline, mock_bitbank_client, sample_ohlcv_data
    ):
        """fetch_ohlcvが辞書を返す場合（DataFrameに変換）"""
        # 1回目はdict、2回目は正常
        mock_bitbank_client.fetch_ohlcv.return_value = sample_ohlcv_data

        with patch.object(pipeline, "fetch_ohlcv", new_callable=AsyncMock) as mock_fetch:
            # 1回目は辞書を返す、2回目は正常なDataFrame
            mock_fetch.side_effect = [
                {"close": [14000000.0, 14100000.0]},  # 辞書として返す
                pd.DataFrame({"close": [14000000.0]}),  # 正常なDataFrame
            ]

            results = await pipeline.fetch_multi_timeframe(symbol="BTC/JPY", limit=100)

            # 両方DataFrameになっている
            assert isinstance(results["4h"], pd.DataFrame)
            assert isinstance(results["15m"], pd.DataFrame)

    @pytest.mark.asyncio
    async def test_fetch_multi_timeframe_dict_conversion_failure(self, pipeline):
        """辞書からDataFrame変換が失敗する場合"""
        with patch.object(pipeline, "fetch_ohlcv", new_callable=AsyncMock) as mock_fetch:
            # 変換不可能な辞書を返す（2回分）
            bad_dict = {"invalid": object()}  # DataFrameに変換できない
            mock_fetch.side_effect = [bad_dict, bad_dict]

            results = await pipeline.fetch_multi_timeframe(symbol="BTC/JPY", limit=100)

            # 空DataFrameで代替される
            assert isinstance(results["4h"], pd.DataFrame)
            assert len(results["4h"]) == 0

    @pytest.mark.asyncio
    async def test_fetch_multi_timeframe_timeout_error(self, pipeline):
        """asyncio.TimeoutErrorが発生した場合"""
        import asyncio

        with patch.object(pipeline, "fetch_ohlcv", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = asyncio.TimeoutError("Timeout")

            results = await pipeline.fetch_multi_timeframe(symbol="BTC/JPY", limit=100)

            # 空DataFrameで代替される
            assert isinstance(results["4h"], pd.DataFrame)
            assert len(results["4h"]) == 0
            assert isinstance(results["15m"], pd.DataFrame)
            assert len(results["15m"]) == 0

    @pytest.mark.asyncio
    async def test_fetch_multi_timeframe_cancelled_error(self, pipeline):
        """asyncio.CancelledErrorはre-raiseされる"""
        import asyncio

        with patch.object(pipeline, "fetch_ohlcv", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = asyncio.CancelledError()

            with pytest.raises(asyncio.CancelledError):
                await pipeline.fetch_multi_timeframe(symbol="BTC/JPY", limit=100)

    @pytest.mark.asyncio
    async def test_fetch_multi_timeframe_config_exception(
        self, pipeline, mock_bitbank_client, sample_ohlcv_data
    ):
        """設定取得失敗時はBTC/JPYフォールバック"""
        mock_bitbank_client.fetch_ohlcv.return_value = sample_ohlcv_data

        with patch("src.core.config.get_config") as mock_get_config:
            mock_get_config.side_effect = Exception("Config error")

            results = await pipeline.fetch_multi_timeframe(symbol=None, limit=100)

            # BTC/JPYで呼ばれたか確認
            calls = mock_bitbank_client.fetch_ohlcv.call_args_list
            for call in calls:
                kwargs = call[1]
                assert kwargs["symbol"] == "BTC/JPY"


class TestLatestPricesEdgeCases:
    """get_latest_prices() 追加テスト"""

    @pytest.mark.asyncio
    async def test_get_latest_prices_config_exception(
        self, pipeline, mock_bitbank_client, sample_ohlcv_data
    ):
        """設定取得失敗時はBTC/JPYフォールバック"""
        mock_bitbank_client.fetch_ohlcv.return_value = sample_ohlcv_data

        with patch("src.core.config.get_config") as mock_get_config:
            mock_get_config.side_effect = Exception("Config error")

            prices = await pipeline.get_latest_prices(symbol=None)

            # 正常に価格が取得できる
            assert "4h" in prices or "15m" in prices

    @pytest.mark.asyncio
    async def test_get_latest_prices_empty_dataframe(self, pipeline, mock_bitbank_client):
        """空DataFrameの場合はキーが追加されない"""
        # 空のDataFrameを返すようにモック
        with patch.object(pipeline, "fetch_ohlcv", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = pd.DataFrame()

            prices = await pipeline.get_latest_prices(symbol="BTC/JPY")

            # 空なのでキーは追加されない
            assert "4h" not in prices
            assert "15m" not in prices


class TestHistoricalDataEdgeCases:
    """fetch_historical_data() 追加テスト"""

    @pytest.mark.asyncio
    async def test_fetch_historical_data_without_since(
        self, pipeline, mock_bitbank_client, sample_ohlcv_data
    ):
        """since未指定の場合"""
        mock_bitbank_client.fetch_ohlcv.return_value = sample_ohlcv_data

        df = await pipeline.fetch_historical_data(symbol="BTC/JPY", timeframe="4h", limit=100)

        assert isinstance(df, pd.DataFrame)
        # sinceがNoneでも正常動作
        assert len(df) == 3

    @pytest.mark.asyncio
    async def test_fetch_historical_data_unknown_timeframe(
        self, pipeline, mock_bitbank_client, sample_ohlcv_data
    ):
        """未知のタイムフレームはH4にフォールバック"""
        mock_bitbank_client.fetch_ohlcv.return_value = sample_ohlcv_data

        # "1h"はマッピングに存在しない→H4にフォールバック
        df = await pipeline.fetch_historical_data(symbol="BTC/JPY", timeframe="1h", limit=100)

        assert isinstance(df, pd.DataFrame)
        # APIが呼ばれたことを確認
        assert mock_bitbank_client.fetch_ohlcv.called

    @pytest.mark.asyncio
    async def test_fetch_historical_data_config_exception(
        self, pipeline, mock_bitbank_client, sample_ohlcv_data
    ):
        """設定取得失敗時はBTC/JPYフォールバック"""
        mock_bitbank_client.fetch_ohlcv.return_value = sample_ohlcv_data

        with patch("src.core.config.get_config") as mock_get_config:
            mock_get_config.side_effect = Exception("Config error")

            df = await pipeline.fetch_historical_data(symbol=None, timeframe="4h", limit=100)

            assert isinstance(df, pd.DataFrame)
            assert len(df) == 3


class TestCacheInfoEdgeCases:
    """get_cache_info() 追加テスト"""

    def test_get_cache_info_expired_items(self, pipeline):
        """期限切れアイテムの情報"""
        df = pd.DataFrame({"close": [14000000.0]})
        pipeline._cache["expired_key"] = df
        # 10分前のタイムスタンプ（期限切れ）
        pipeline._cache_timestamps["expired_key"] = datetime.now() - timedelta(minutes=10)

        info = pipeline.get_cache_info()

        assert info["total_cached_items"] == 1
        assert len(info["items"]) == 1
        assert info["items"][0]["key"] == "expired_key"
        assert info["items"][0]["is_valid"] is False
        assert info["items"][0]["age_minutes"] >= 10

    def test_get_cache_info_multiple_items(self, pipeline):
        """複数アイテムの情報"""
        df1 = pd.DataFrame({"close": [14000000.0]})
        df2 = pd.DataFrame({"close": [14100000.0, 14200000.0]})

        pipeline._cache["key1"] = df1
        pipeline._cache["key2"] = df2
        pipeline._cache_timestamps["key1"] = datetime.now()
        pipeline._cache_timestamps["key2"] = datetime.now() - timedelta(minutes=3)

        info = pipeline.get_cache_info()

        assert info["total_cached_items"] == 2
        assert len(info["items"]) == 2


class TestFetchOhlcvEdgeCases:
    """fetch_ohlcv() 追加テスト"""

    @pytest.mark.asyncio
    async def test_fetch_ohlcv_low_data_count_warning(
        self, pipeline, mock_bitbank_client
    ):
        """取得件数が要求の半分以下の場合の警告"""
        # 要求100件に対して20件しか返さない
        small_data = [[1704067200000, 14000000.0, 14100000.0, 13900000.0, 14050000.0, 1000.0]]
        mock_bitbank_client.fetch_ohlcv.return_value = small_data

        request = DataRequest(symbol="BTC/JPY", timeframe=TimeFrame.H4, limit=100)
        df = await pipeline.fetch_ohlcv(request, use_cache=False)

        # 正常に返されるがログに警告が出る
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1


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

    def test_fetch_market_data_returns_coroutine(self, pipeline, mock_bitbank_client):
        """fetch_market_data() はCoroutineを返す"""
        from src.data.data_pipeline import fetch_market_data
        import src.data.data_pipeline as dp_module

        # グローバルパイプラインを設定
        original = dp_module._data_pipeline
        dp_module._data_pipeline = pipeline

        try:
            # fetch_market_dataはCoroutineを返す
            result = fetch_market_data(symbol="BTC/JPY", timeframe="4h", limit=100)

            import asyncio

            assert asyncio.iscoroutine(result)
            result.close()
        finally:
            dp_module._data_pipeline = original

    def test_fetch_market_data_symbol_from_config(self, pipeline, mock_bitbank_client):
        """fetch_market_data() symbol未指定時は設定から取得"""
        from src.data.data_pipeline import fetch_market_data
        import src.data.data_pipeline as dp_module

        original = dp_module._data_pipeline
        dp_module._data_pipeline = pipeline

        try:
            with patch("src.core.config.get_config") as mock_get_config:
                mock_config = Mock()
                mock_config.exchange.symbol = "ETH/JPY"
                mock_get_config.return_value = mock_config

                result = fetch_market_data(symbol=None, timeframe="15m", limit=50)

                import asyncio

                assert asyncio.iscoroutine(result)
                result.close()
        finally:
            dp_module._data_pipeline = original

    def test_fetch_market_data_config_exception(self, pipeline, mock_bitbank_client):
        """fetch_market_data() 設定取得失敗時はBTC/JPYフォールバック"""
        from src.data.data_pipeline import fetch_market_data
        import src.data.data_pipeline as dp_module

        original = dp_module._data_pipeline
        dp_module._data_pipeline = pipeline

        try:
            with patch("src.core.config.get_config") as mock_get_config:
                mock_get_config.side_effect = Exception("Config error")

                result = fetch_market_data(symbol=None, timeframe="4h", limit=100)

                import asyncio

                assert asyncio.iscoroutine(result)
                result.close()
        finally:
            dp_module._data_pipeline = original


class TestPipelineInitialization:
    """DataPipeline初期化テスト"""

    def test_init_without_client(self):
        """クライアント未指定時はグローバルクライアント使用"""
        with patch("src.data.bitbank_client.get_bitbank_client") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client

            pipeline = DataPipeline(client=None)

            assert pipeline.client is mock_client
            mock_get_client.assert_called_once()

    def test_init_with_client(self, mock_bitbank_client):
        """クライアント指定時はそれを使用"""
        pipeline = DataPipeline(client=mock_bitbank_client)

        assert pipeline.client is mock_bitbank_client

    def test_init_default_values(self, pipeline):
        """初期値の確認"""
        assert pipeline.cache_duration_minutes == 5
        assert pipeline.max_retries == 3
        assert pipeline.retry_delay == 1.0
        assert pipeline._backtest_mode is False
        assert len(pipeline._backtest_data) == 0
        assert pipeline._backtest_ml_prediction is None


class TestDataRequestDefaults:
    """DataRequestデフォルト値テスト"""

    def test_data_request_defaults(self):
        """DataRequestのデフォルト値"""
        request = DataRequest()

        assert request.symbol is None
        assert request.timeframe == TimeFrame.H4
        assert request.limit == 1000
        assert request.since is None

    def test_data_request_custom_values(self):
        """DataRequestのカスタム値"""
        request = DataRequest(
            symbol="ETH/JPY", timeframe=TimeFrame.M15, limit=500, since=1704067200000
        )

        assert request.symbol == "ETH/JPY"
        assert request.timeframe == TimeFrame.M15
        assert request.limit == 500
        assert request.since == 1704067200000


class TestTimeFrameEnum:
    """TimeFrame Enumテスト"""

    def test_timeframe_values(self):
        """TimeFrame値の確認"""
        assert TimeFrame.M15.value == "15m"
        assert TimeFrame.H4.value == "4h"

    def test_timeframe_iteration(self):
        """TimeFrame列挙"""
        timeframes = list(TimeFrame)
        assert len(timeframes) == 2
        assert TimeFrame.M15 in timeframes
        assert TimeFrame.H4 in timeframes

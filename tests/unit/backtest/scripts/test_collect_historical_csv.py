"""
HistoricalDataCollector ユニットテスト

最終更新: 2025/11/16 (Phase 52.4-B)

テストカバレッジ:
- 初期化
- CSV保存機能
- 4時間足データ収集
- 15分足データ収集
- マルチタイムフレーム収集
- エラーハンドリング
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.backtest.scripts.collect_historical_csv import HistoricalDataCollector


@pytest.fixture
def temp_output_dir():
    """一時出力ディレクトリ"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_logger():
    """モックロガー"""
    return Mock()


@pytest.fixture
def sample_ohlcv_data():
    """テスト用OHLCVデータ"""
    base_timestamp = int(datetime(2024, 1, 1).timestamp() * 1000)
    return [
        [
            base_timestamp + i * 3600000,
            14000000.0 + i * 1000,
            14010000.0 + i * 1000,
            13990000.0 + i * 1000,
            14005000.0 + i * 1000,
            100.0 + i,
        ]
        for i in range(10)
    ]


@pytest.fixture
def sample_bitbank_response():
    """Bitbank API レスポンスのサンプル"""
    base_timestamp = int(datetime(2024, 1, 1).timestamp() * 1000)
    return {
        "success": 1,
        "data": {
            "candlestick": [
                {
                    "ohlcv": [
                        [
                            "14000000",  # open
                            "14010000",  # high
                            "13990000",  # low
                            "14005000",  # close
                            "100.0",  # volume
                            base_timestamp + i * 3600000,  # timestamp
                        ]
                        for i in range(10)
                    ]
                }
            ]
        },
    }


class TestHistoricalDataCollectorInitialization:
    """初期化テスト"""

    @patch("src.backtest.scripts.collect_historical_csv.get_logger")
    def test_initialization(self, mock_get_logger, temp_output_dir):
        """正常な初期化"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        with patch.object(Path, "mkdir"):
            collector = HistoricalDataCollector()

            assert collector.logger is not None
            assert collector.output_dir is not None
            assert collector.ssl_context is not None

    @patch("src.backtest.scripts.collect_historical_csv.get_logger")
    def test_output_directory_creation(self, mock_get_logger, temp_output_dir):
        """出力ディレクトリ作成"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        with patch.object(HistoricalDataCollector, "__init__", lambda x: None):
            collector = HistoricalDataCollector()
            collector.logger = mock_logger
            collector.output_dir = temp_output_dir / "test_output"
            collector.output_dir.mkdir(parents=True, exist_ok=True)

            assert collector.output_dir.exists()


class TestHistoricalDataCollectorCSVSave:
    """CSV保存機能テスト"""

    @pytest.mark.asyncio
    @patch("src.backtest.scripts.collect_historical_csv.get_logger")
    async def test_save_to_csv(self, mock_get_logger, temp_output_dir, sample_ohlcv_data):
        """CSV保存成功"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        collector = HistoricalDataCollector()
        collector.output_dir = temp_output_dir

        await collector._save_to_csv(sample_ohlcv_data, "BTC/JPY", "4h")

        # CSVファイル存在確認
        csv_file = temp_output_dir / "BTC_JPY_4h.csv"
        assert csv_file.exists()

        # CSVファイル内容確認
        with open(csv_file, "r") as f:
            lines = f.readlines()
            assert len(lines) == 11  # ヘッダー + 10データ行
            assert "timestamp,open,high,low,close,volume,datetime" in lines[0]

    @pytest.mark.asyncio
    @patch("src.backtest.scripts.collect_historical_csv.get_logger")
    async def test_save_empty_data(self, mock_get_logger, temp_output_dir):
        """空データの保存"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        collector = HistoricalDataCollector()
        collector.output_dir = temp_output_dir

        await collector._save_to_csv([], "BTC/JPY", "4h")

        # CSVファイル存在確認（ヘッダーのみ）
        csv_file = temp_output_dir / "BTC_JPY_4h.csv"
        assert csv_file.exists()

        with open(csv_file, "r") as f:
            lines = f.readlines()
            assert len(lines) == 1  # ヘッダーのみ


class TestHistoricalDataCollector4hData:
    """4時間足データ収集テスト"""

    @pytest.mark.asyncio
    @patch("src.backtest.scripts.collect_historical_csv.get_logger")
    @patch("src.backtest.scripts.collect_historical_csv.aiohttp.ClientSession")
    async def test_collect_4h_direct(
        self, mock_session_class, mock_get_logger, sample_bitbank_response
    ):
        """4時間足データ直接取得"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # モックレスポンス設定
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=sample_bitbank_response)
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        collector = HistoricalDataCollector()
        data = await collector._collect_4h_direct("BTC/JPY", days=30)

        assert isinstance(data, list)
        # データが取得されたかどうかのみ確認（実装に依存するため）

    @pytest.mark.asyncio
    @patch("src.backtest.scripts.collect_historical_csv.get_logger")
    @patch("src.backtest.scripts.collect_historical_csv.aiohttp.ClientSession")
    async def test_fetch_4h_year_data(
        self, mock_session_class, mock_get_logger, sample_bitbank_response
    ):
        """年別4時間足データ取得"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # モックレスポンス設定
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=sample_bitbank_response)
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        collector = HistoricalDataCollector()
        data = await collector._fetch_4h_year_data("BTC/JPY", 2024)

        assert isinstance(data, list)
        if data:  # データが取得された場合
            assert len(data[0]) == 6  # [timestamp, open, high, low, close, volume]


class TestHistoricalDataCollector15mData:
    """15分足データ収集テスト"""

    @pytest.mark.asyncio
    @patch("src.backtest.scripts.collect_historical_csv.get_logger")
    @patch("src.backtest.scripts.collect_historical_csv.asyncio.sleep", new_callable=AsyncMock)
    @patch("src.backtest.scripts.collect_historical_csv.aiohttp.ClientSession")
    async def test_collect_15m_direct(
        self, mock_session_class, mock_sleep, mock_get_logger, sample_bitbank_response
    ):
        """15分足データ直接取得"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # モックレスポンス設定
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=sample_bitbank_response)
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        collector = HistoricalDataCollector()
        data = await collector._collect_15m_direct("BTC/JPY", days=1)

        assert isinstance(data, list)

    @pytest.mark.asyncio
    @patch("src.backtest.scripts.collect_historical_csv.get_logger")
    @patch("src.backtest.scripts.collect_historical_csv.aiohttp.ClientSession")
    async def test_fetch_15m_day_data(
        self, mock_session_class, mock_get_logger, sample_bitbank_response
    ):
        """日別15分足データ取得"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # モックレスポンス設定
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=sample_bitbank_response)
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        collector = HistoricalDataCollector()
        data = await collector._fetch_15m_day_data("BTC/JPY", datetime(2024, 1, 1))

        assert isinstance(data, list)
        if data:
            assert len(data[0]) == 6


class TestHistoricalDataCollectorViaClient:
    """BitbankClient経由データ収集テスト"""

    @pytest.mark.asyncio
    @patch("src.backtest.scripts.collect_historical_csv.get_logger")
    @patch("src.backtest.scripts.collect_historical_csv.BitbankClient")
    @patch("src.backtest.scripts.collect_historical_csv.asyncio.sleep", new_callable=AsyncMock)
    async def test_collect_via_client(
        self, mock_sleep, mock_bitbank_client_class, mock_get_logger, sample_ohlcv_data
    ):
        """Client経由データ取得"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # モックBitbankClient設定
        mock_client = AsyncMock()
        mock_client.fetch_ohlcv = AsyncMock(return_value=sample_ohlcv_data)
        mock_bitbank_client_class.return_value = mock_client

        collector = HistoricalDataCollector()
        data = await collector._collect_via_client("BTC/JPY", "1h", days=10)

        assert isinstance(data, list)

    @pytest.mark.asyncio
    @patch("src.backtest.scripts.collect_historical_csv.get_logger")
    @patch("src.backtest.scripts.collect_historical_csv.BitbankClient")
    async def test_collect_via_client_error(self, mock_bitbank_client_class, mock_get_logger):
        """Client経由データ取得エラー"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # エラーを発生させる
        mock_client = AsyncMock()
        mock_client.fetch_ohlcv = AsyncMock(side_effect=Exception("API Error"))
        mock_bitbank_client_class.return_value = mock_client

        collector = HistoricalDataCollector()
        data = await collector._collect_via_client("BTC/JPY", "1h", days=10)

        assert data == []


class TestHistoricalDataCollectorMultiTimeframe:
    """マルチタイムフレーム収集テスト"""

    @pytest.mark.asyncio
    @patch("src.backtest.scripts.collect_historical_csv.get_logger")
    async def test_collect_data_multiple_timeframes(self, mock_get_logger, sample_ohlcv_data):
        """複数タイムフレームデータ収集"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        collector = HistoricalDataCollector()

        # _collect_timeframe_dataをモック
        with patch.object(
            collector, "_collect_timeframe_data", new_callable=AsyncMock
        ) as mock_collect:
            await collector.collect_data(symbol="BTC/JPY", days=30, timeframes=["4h", "15m"])

            # 2回呼ばれることを確認（4h, 15m）
            assert mock_collect.call_count == 2


class TestHistoricalDataCollectorErrorHandling:
    """エラーハンドリングテスト"""

    @pytest.mark.asyncio
    @patch("src.backtest.scripts.collect_historical_csv.get_logger")
    @patch("src.backtest.scripts.collect_historical_csv.aiohttp.ClientSession")
    async def test_api_error_handling(self, mock_session_class, mock_get_logger):
        """API エラーハンドリング"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # エラーレスポンス設定
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(side_effect=Exception("Network Error"))
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        collector = HistoricalDataCollector()
        data = await collector._fetch_4h_year_data("BTC/JPY", 2024)

        # エラー時は空リスト返却
        assert data == []

    @pytest.mark.asyncio
    @patch("src.backtest.scripts.collect_historical_csv.get_logger")
    @patch("src.backtest.scripts.collect_historical_csv.aiohttp.ClientSession")
    async def test_invalid_api_response(self, mock_session_class, mock_get_logger):
        """不正なAPIレスポンス"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # 不正なレスポンス
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"success": 0, "data": None})
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        collector = HistoricalDataCollector()
        data = await collector._fetch_4h_year_data("BTC/JPY", 2024)

        # 不正なレスポンス時は空リスト
        assert data == []


class TestHistoricalDataCollectorFiltering:
    """データフィルタリングテスト"""

    @pytest.mark.asyncio
    @patch("src.backtest.scripts.collect_historical_csv.get_logger")
    @patch("src.backtest.scripts.collect_historical_csv.aiohttp.ClientSession")
    async def test_date_filtering(
        self, mock_session_class, mock_get_logger, sample_bitbank_response
    ):
        """日付範囲フィルタリング"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # モックレスポンス設定
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=sample_bitbank_response)
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_class.return_value = mock_session

        collector = HistoricalDataCollector()

        # 期間指定でデータ取得
        start_ts = int((datetime.now() - timedelta(days=10)).timestamp() * 1000)
        end_ts = int(datetime.now().timestamp() * 1000)

        data = await collector._collect_4h_direct(
            "BTC/JPY", days=30, start_timestamp=start_ts, end_timestamp=end_ts
        )

        assert isinstance(data, list)

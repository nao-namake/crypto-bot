"""
BacktestCSVLoader ユニットテスト

最終更新: 2025/11/16 (Phase 52.4-B)

テストカバレッジ:
- 初期化（デフォルト・カスタムディレクトリ・設定連携）
- CSV読み込み（正常・エラーケース）
- キャッシュ機能（有効・無効）
- データフィルタリング（日付・件数制限）
- マルチタイムフレーム読み込み
- データ整合性チェック
- ファイル情報取得
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from src.backtest.data.csv_data_loader import BacktestCSVLoader, get_csv_loader
from src.core.exceptions import DataFetchError


@pytest.fixture
def temp_data_dir():
    """一時データディレクトリ"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_csv_data():
    """テスト用CSVデータ（DataFrame形式）"""
    timestamps = pd.date_range(start="2024-01-01", periods=100, freq="4h")
    return pd.DataFrame(
        {
            "timestamp": (timestamps.astype(int) // 10**6).tolist(),  # ミリ秒
            "open": [14000000.0 + i * 1000 for i in range(100)],
            "high": [14010000.0 + i * 1000 for i in range(100)],
            "low": [13990000.0 + i * 1000 for i in range(100)],
            "close": [14005000.0 + i * 1000 for i in range(100)],
            "volume": [100.0 + i * 0.5 for i in range(100)],
        }
    )


@pytest.fixture
def mock_config_with_cache():
    """キャッシュ有効設定のモック"""
    config = Mock()
    config.backtest = {"data": {"data_directory": None, "cache_enabled": True}}
    return config


@pytest.fixture
def mock_config_without_cache():
    """キャッシュ無効設定のモック"""
    config = Mock()
    config.backtest = {"data": {"data_directory": None, "cache_enabled": False}}
    return config


class TestBacktestCSVLoaderInitialization:
    """初期化テスト"""

    @patch("src.backtest.data.csv_data_loader.get_config")
    def test_initialization_default_directory(self, mock_get_config):
        """デフォルトディレクトリでの初期化"""
        mock_get_config.return_value = Mock(
            backtest={"data": {"data_directory": None, "cache_enabled": True}}
        )

        loader = BacktestCSVLoader()

        assert loader.data_dir.exists()
        assert loader._cache_enabled is True
        assert loader._cache is not None

    @patch("src.backtest.data.csv_data_loader.get_config")
    def test_initialization_custom_directory(self, mock_get_config, temp_data_dir):
        """カスタムディレクトリでの初期化"""
        mock_get_config.return_value = Mock(
            backtest={"data": {"data_directory": None, "cache_enabled": True}}
        )

        loader = BacktestCSVLoader(data_dir=temp_data_dir)

        assert loader.data_dir == temp_data_dir
        assert loader.data_dir.exists()

    @patch("src.backtest.data.csv_data_loader.get_config")
    def test_initialization_from_config(self, mock_get_config, temp_data_dir):
        """設定ファイルからディレクトリ取得"""
        mock_get_config.return_value = Mock(
            backtest={"data": {"data_directory": str(temp_data_dir), "cache_enabled": True}}
        )

        loader = BacktestCSVLoader()

        assert loader.data_dir == temp_data_dir

    @patch("src.backtest.data.csv_data_loader.get_config")
    def test_initialization_cache_disabled(self, mock_get_config):
        """キャッシュ無効での初期化"""
        mock_get_config.return_value = Mock(
            backtest={"data": {"data_directory": None, "cache_enabled": False}}
        )

        loader = BacktestCSVLoader()

        assert loader._cache_enabled is False
        assert loader._cache is None


class TestBacktestCSVLoaderLoadData:
    """データ読み込みテスト"""

    @patch("src.backtest.data.csv_data_loader.get_config")
    def test_load_csv_success(self, mock_get_config, temp_data_dir, sample_csv_data):
        """正常なCSV読み込み"""
        mock_get_config.return_value = Mock(
            backtest={"data": {"data_directory": None, "cache_enabled": True}}
        )

        # テストCSVファイル作成
        csv_file = temp_data_dir / "BTC_JPY_4h.csv"
        sample_csv_data.to_csv(csv_file, index=False)

        loader = BacktestCSVLoader(data_dir=temp_data_dir)
        df = loader.load_historical_data(symbol="BTC/JPY", timeframe="4h")

        assert not df.empty
        assert len(df) == 100
        assert all(col in df.columns for col in ["open", "high", "low", "close", "volume"])
        assert isinstance(df.index, pd.DatetimeIndex)

    @patch("src.backtest.data.csv_data_loader.get_config")
    def test_load_csv_file_not_found(self, mock_get_config, temp_data_dir):
        """CSVファイル未発見エラー"""
        mock_get_config.return_value = Mock(
            backtest={"data": {"data_directory": None, "cache_enabled": True}}
        )

        loader = BacktestCSVLoader(data_dir=temp_data_dir)

        with pytest.raises(DataFetchError, match="CSVデータ読み込み失敗"):
            loader.load_historical_data(symbol="BTC/JPY", timeframe="4h")

    @patch("src.backtest.data.csv_data_loader.get_config")
    def test_load_csv_invalid_columns(self, mock_get_config, temp_data_dir):
        """不正な列構成のCSV"""
        mock_get_config.return_value = Mock(
            backtest={"data": {"data_directory": None, "cache_enabled": True}}
        )

        # 不正なCSVファイル作成（必須列不足）
        csv_file = temp_data_dir / "BTC_JPY_4h.csv"
        invalid_df = pd.DataFrame({"timestamp": [1704067200000], "open": [14000000.0]})
        invalid_df.to_csv(csv_file, index=False)

        loader = BacktestCSVLoader(data_dir=temp_data_dir)

        with pytest.raises(DataFetchError, match="CSVデータ読み込み失敗"):
            loader.load_historical_data(symbol="BTC/JPY", timeframe="4h")

    @patch("src.backtest.data.csv_data_loader.get_config")
    def test_load_csv_with_date_suffix_fallback(
        self, mock_get_config, temp_data_dir, sample_csv_data
    ):
        """日付付きファイル名フォールバック"""
        mock_get_config.return_value = Mock(
            backtest={"data": {"data_directory": None, "cache_enabled": True}}
        )

        # 日付付きファイル作成
        csv_file = temp_data_dir / "BTC_JPY_4h_20250116.csv"
        sample_csv_data.to_csv(csv_file, index=False)

        loader = BacktestCSVLoader(data_dir=temp_data_dir)
        df = loader.load_historical_data(symbol="BTC/JPY", timeframe="4h")

        assert not df.empty
        assert len(df) == 100


class TestBacktestCSVLoaderCache:
    """キャッシュ機能テスト"""

    @patch("src.backtest.data.csv_data_loader.get_config")
    def test_cache_enabled(self, mock_get_config, temp_data_dir, sample_csv_data):
        """キャッシュ有効時の動作"""
        mock_get_config.return_value = Mock(
            backtest={"data": {"data_directory": None, "cache_enabled": True}}
        )

        csv_file = temp_data_dir / "BTC_JPY_4h.csv"
        sample_csv_data.to_csv(csv_file, index=False)

        loader = BacktestCSVLoader(data_dir=temp_data_dir)

        # 1回目の読み込み
        df1 = loader.load_historical_data(symbol="BTC/JPY", timeframe="4h")
        assert "BTC/JPY_4h" in loader._cache

        # 2回目の読み込み（キャッシュから）
        df2 = loader.load_historical_data(symbol="BTC/JPY", timeframe="4h")
        assert df1.equals(df2)

    @patch("src.backtest.data.csv_data_loader.get_config")
    def test_cache_disabled(self, mock_get_config, temp_data_dir, sample_csv_data):
        """キャッシュ無効時の動作"""
        mock_get_config.return_value = Mock(
            backtest={"data": {"data_directory": None, "cache_enabled": False}}
        )

        csv_file = temp_data_dir / "BTC_JPY_4h.csv"
        sample_csv_data.to_csv(csv_file, index=False)

        loader = BacktestCSVLoader(data_dir=temp_data_dir)
        df = loader.load_historical_data(symbol="BTC/JPY", timeframe="4h")

        assert loader._cache is None
        assert not df.empty

    @patch("src.backtest.data.csv_data_loader.get_config")
    def test_clear_cache(self, mock_get_config, temp_data_dir, sample_csv_data):
        """キャッシュクリア"""
        mock_get_config.return_value = Mock(
            backtest={"data": {"data_directory": None, "cache_enabled": True}}
        )

        csv_file = temp_data_dir / "BTC_JPY_4h.csv"
        sample_csv_data.to_csv(csv_file, index=False)

        loader = BacktestCSVLoader(data_dir=temp_data_dir)
        loader.load_historical_data(symbol="BTC/JPY", timeframe="4h")

        assert "BTC/JPY_4h" in loader._cache

        loader.clear_cache()

        assert len(loader._cache) == 0

    @patch("src.backtest.data.csv_data_loader.get_config")
    def test_clear_cache_when_disabled(self, mock_get_config):
        """キャッシュ無効時のクリア呼び出し（エラーなし）"""
        mock_get_config.return_value = Mock(
            backtest={"data": {"data_directory": None, "cache_enabled": False}}
        )

        loader = BacktestCSVLoader()
        loader.clear_cache()  # エラーが発生しないことを確認


class TestBacktestCSVLoaderFiltering:
    """データフィルタリングテスト"""

    @patch("src.backtest.data.csv_data_loader.get_config")
    def test_filter_by_date(self, mock_get_config, temp_data_dir, sample_csv_data):
        """日付範囲フィルタ"""
        mock_get_config.return_value = Mock(
            backtest={"data": {"data_directory": None, "cache_enabled": True}}
        )

        csv_file = temp_data_dir / "BTC_JPY_4h.csv"
        sample_csv_data.to_csv(csv_file, index=False)

        loader = BacktestCSVLoader(data_dir=temp_data_dir)

        start_date = datetime(2024, 1, 5)
        end_date = datetime(2024, 1, 10)

        df = loader.load_historical_data(
            symbol="BTC/JPY", timeframe="4h", start_date=start_date, end_date=end_date
        )

        assert not df.empty
        assert (df.index >= start_date).all()
        assert (df.index <= end_date).all()

    @patch("src.backtest.data.csv_data_loader.get_config")
    def test_filter_by_limit(self, mock_get_config, temp_data_dir, sample_csv_data):
        """件数制限フィルタ"""
        mock_get_config.return_value = Mock(
            backtest={"data": {"data_directory": None, "cache_enabled": True}}
        )

        csv_file = temp_data_dir / "BTC_JPY_4h.csv"
        sample_csv_data.to_csv(csv_file, index=False)

        loader = BacktestCSVLoader(data_dir=temp_data_dir)
        df = loader.load_historical_data(symbol="BTC/JPY", timeframe="4h", limit=50)

        assert len(df) == 50

    @patch("src.backtest.data.csv_data_loader.get_config")
    def test_filter_empty_result(self, mock_get_config, temp_data_dir, sample_csv_data):
        """フィルタ結果が空"""
        mock_get_config.return_value = Mock(
            backtest={"data": {"data_directory": None, "cache_enabled": True}}
        )

        csv_file = temp_data_dir / "BTC_JPY_4h.csv"
        sample_csv_data.to_csv(csv_file, index=False)

        loader = BacktestCSVLoader(data_dir=temp_data_dir)

        # 未来の日付で検索
        future_date = datetime(2030, 1, 1)
        df = loader.load_historical_data(symbol="BTC/JPY", timeframe="4h", start_date=future_date)

        assert df.empty


class TestBacktestCSVLoaderMultiTimeframe:
    """マルチタイムフレームテスト"""

    @patch("src.backtest.data.csv_data_loader.get_config")
    def test_load_multi_timeframe_success(self, mock_get_config, temp_data_dir, sample_csv_data):
        """マルチタイムフレーム読み込み成功"""
        mock_get_config.return_value = Mock(
            backtest={"data": {"data_directory": None, "cache_enabled": True}}
        )

        # 複数のCSVファイル作成
        for timeframe in ["15m", "4h"]:
            csv_file = temp_data_dir / f"BTC_JPY_{timeframe}.csv"
            sample_csv_data.to_csv(csv_file, index=False)

        loader = BacktestCSVLoader(data_dir=temp_data_dir)
        results = loader.load_multi_timeframe(symbol="BTC/JPY", timeframes=["15m", "4h"])

        assert "15m" in results
        assert "4h" in results
        assert not results["15m"].empty
        assert not results["4h"].empty

    @patch("src.backtest.data.csv_data_loader.get_config")
    def test_load_multi_timeframe_partial_error(
        self, mock_get_config, temp_data_dir, sample_csv_data
    ):
        """マルチタイムフレーム読み込み（一部エラー）"""
        mock_get_config.return_value = Mock(
            backtest={"data": {"data_directory": None, "cache_enabled": True}}
        )

        # 1つだけCSVファイル作成
        csv_file = temp_data_dir / "BTC_JPY_4h.csv"
        sample_csv_data.to_csv(csv_file, index=False)

        loader = BacktestCSVLoader(data_dir=temp_data_dir)
        results = loader.load_multi_timeframe(symbol="BTC/JPY", timeframes=["15m", "4h"])

        assert "15m" in results
        assert "4h" in results
        assert results["15m"].empty  # エラーで空DataFrame
        assert not results["4h"].empty


class TestBacktestCSVLoaderDataIntegrity:
    """データ整合性チェックテスト"""

    @patch("src.backtest.data.csv_data_loader.get_config")
    def test_validate_data_integrity_success(self, mock_get_config, temp_data_dir, sample_csv_data):
        """データ整合性チェック成功"""
        mock_get_config.return_value = Mock(
            backtest={"data": {"data_directory": None, "cache_enabled": True}}
        )

        csv_file = temp_data_dir / "BTC_JPY_4h.csv"
        sample_csv_data.to_csv(csv_file, index=False)

        loader = BacktestCSVLoader(data_dir=temp_data_dir)
        checks = loader.validate_data_integrity(symbol="BTC/JPY", timeframe="4h")

        assert checks["has_data"] is True
        assert checks["valid_columns"] is True
        assert checks["no_duplicates"] is True
        assert checks["sorted_index"] is True
        assert checks["no_null_values"] is True
        assert bool(checks["positive_prices"]) is True
        assert bool(checks["positive_volume"]) is True
        assert bool(checks["valid_ohlc"]) is True

    @patch("src.backtest.data.csv_data_loader.get_config")
    def test_validate_data_integrity_error(self, mock_get_config, temp_data_dir):
        """データ整合性チェックエラー"""
        mock_get_config.return_value = Mock(
            backtest={"data": {"data_directory": None, "cache_enabled": True}}
        )

        loader = BacktestCSVLoader(data_dir=temp_data_dir)
        checks = loader.validate_data_integrity(symbol="BTC/JPY", timeframe="4h")

        assert "error" in checks
        assert checks["error"] is True


class TestBacktestCSVLoaderFileInfo:
    """ファイル情報取得テスト"""

    @patch("src.backtest.data.csv_data_loader.get_config")
    def test_get_latest_data_info(self, mock_get_config, temp_data_dir, sample_csv_data):
        """利用可能なデータ情報取得"""
        mock_get_config.return_value = Mock(
            backtest={"data": {"data_directory": None, "cache_enabled": True}}
        )

        # CSVファイル作成
        csv_file = temp_data_dir / "BTC_JPY_4h.csv"
        sample_csv_data.to_csv(csv_file, index=False)

        loader = BacktestCSVLoader(data_dir=temp_data_dir)
        info = loader.get_latest_data_info()

        assert "BTC/JPY_4h" in info
        assert "file_path" in info["BTC/JPY_4h"]
        assert "file_size_mb" in info["BTC/JPY_4h"]
        assert "modified_time" in info["BTC/JPY_4h"]


class TestBacktestCSVLoaderSingleton:
    """シングルトンパターンテスト"""

    @patch("src.backtest.data.csv_data_loader.get_config")
    def test_get_csv_loader_singleton(self, mock_get_config):
        """get_csv_loader()がシングルトンを返す"""
        mock_get_config.return_value = Mock(
            backtest={"data": {"data_directory": None, "cache_enabled": True}}
        )

        loader1 = get_csv_loader()
        loader2 = get_csv_loader()

        assert loader1 is loader2

"""
CSVデータローダー - バックテスト用高速データ読み込みシステム

最終更新: 2025/11/16 (Phase 52.4-B)

API依存を排除し、安定した過去データ取得を実現。

主要機能:
- 大量データの高速読み込み（数万件のOHLCV処理）
- キャッシュ機構による読み込み最適化
- 固定ファイル名対応・日付付きファイルへのフォールバック
- 期間フィルタリング・行数制限機能
- データ整合性チェック（8種類の検証）
"""

import csv
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from ...core.config import get_config
from ...core.exceptions import DataFetchError
from ...core.logger import get_logger


class BacktestCSVLoader:
    """
    バックテスト用CSVデータローダー

    高速化・固定ファイル名対応・キャッシュ機能実装済み。
    """

    def __init__(self, data_dir: Optional[Path] = None):
        self.logger = get_logger(__name__)

        # Config読み込み
        config = get_config()

        # デフォルトデータディレクトリ（優先順: 引数 > config > デフォルト）
        if data_dir is None:
            config_dir = getattr(config, "backtest", {}).get("data", {}).get("data_directory")
            if config_dir:
                data_dir = Path(config_dir)
            else:
                data_dir = Path(__file__).parent / "historical"

        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # キャッシュ設定
        cache_enabled = getattr(config, "backtest", {}).get("data", {}).get("cache_enabled", True)
        self._cache: Dict[str, pd.DataFrame] = {} if cache_enabled else None
        self._cache_enabled = cache_enabled

        self.logger.info(f"CSVローダー初期化: {self.data_dir} (cache={cache_enabled})")

    def load_historical_data(
        self,
        symbol: str = "BTC/JPY",
        timeframe: str = "4h",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = None,
    ) -> pd.DataFrame:
        """
        過去データCSV読み込み

        Args:
            symbol: 通貨ペア
            timeframe: タイムフレーム
            start_date: 開始日時
            end_date: 終了日時
            limit: 最大データ数

        Returns:
            OHLCV DataFrame
        """
        try:
            # キャッシュキー生成
            cache_key = f"{symbol}_{timeframe}"

            # キャッシュチェック（キャッシュ有効時のみ）
            if self._cache_enabled and cache_key in self._cache:
                df = self._cache[cache_key]
                self.logger.debug(f"キャッシュからデータ取得: {cache_key}")
            else:
                # CSV読み込み
                df = self._load_csv_data(symbol, timeframe)
                if self._cache_enabled:
                    self._cache[cache_key] = df

            # データフィルタリング
            filtered_df = self._filter_data(df, start_date, end_date, limit)

            if filtered_df.empty:
                self.logger.warning(f"データが見つかりません: {symbol} {timeframe}")
                return pd.DataFrame()

            self.logger.info(f"CSV読み込み成功: {symbol} {timeframe} ({len(filtered_df)}件)")
            return filtered_df

        except Exception as e:
            self.logger.error(f"CSV読み込みエラー: {e}")
            raise DataFetchError(f"CSVデータ読み込み失敗: {symbol} {timeframe}")

    def _load_csv_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        """CSV ファイル読み込み"""
        symbol_filename = symbol.replace("/", "_")

        # 固定ファイル名のCSVファイルを検索
        fixed_filename = f"{symbol_filename}_{timeframe}.csv"
        csv_file = self.data_dir / fixed_filename

        if not csv_file.exists():
            # フォールバック: 日付付きファイルを検索
            csv_files = list(self.data_dir.glob(f"{symbol_filename}_{timeframe}_*.csv"))
            if not csv_files:
                raise DataFetchError(f"CSVファイルが見つかりません: {symbol} {timeframe}")
            latest_file = max(csv_files, key=lambda x: x.stat().st_mtime)
        else:
            latest_file = csv_file

        self.logger.debug(f"CSV読み込み: {latest_file}")

        # CSV読み込み
        df = pd.read_csv(latest_file)

        # データ形式確認・変換
        required_columns = ["timestamp", "open", "high", "low", "close", "volume"]
        if not all(col in df.columns for col in required_columns):
            raise DataFetchError(f"CSVの列が不正: {list(df.columns)}")

        # タイムスタンプをインデックスに設定
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)

        # 数値型に変換
        numeric_columns = ["open", "high", "low", "close", "volume"]
        df[numeric_columns] = df[numeric_columns].astype(float)

        # ソート
        df.sort_index(inplace=True)

        return df

    def _filter_data(
        self,
        df: pd.DataFrame,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        limit: Optional[int],
    ) -> pd.DataFrame:
        """データフィルタリング"""
        filtered_df = df.copy()

        # 日付フィルタ
        if start_date:
            filtered_df = filtered_df[filtered_df.index >= start_date]
        if end_date:
            filtered_df = filtered_df[filtered_df.index <= end_date]

        # 件数制限（最新データから）
        if limit and len(filtered_df) > limit:
            filtered_df = filtered_df.tail(limit)

        return filtered_df

    def load_multi_timeframe(
        self,
        symbol: str = "BTC/JPY",
        timeframes: List[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000,
    ) -> Dict[str, pd.DataFrame]:
        """
        マルチタイムフレーム データ読み込み

        Returns:
            タイムフレーム別DataFrame辞書
        """
        if timeframes is None:
            timeframes = ["15m", "4h"]  # 本番と同じ2軸構成

        results = {}

        for timeframe in timeframes:
            try:
                df = self.load_historical_data(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit,
                )
                results[timeframe] = df

            except Exception as e:
                self.logger.error(f"マルチフレーム取得エラー: {timeframe} - {e}")
                results[timeframe] = pd.DataFrame()

        return results

    def get_latest_data_info(self) -> Dict[str, Dict]:
        """利用可能なデータ情報取得"""
        info = {}

        for csv_file in self.data_dir.glob("*.csv"):
            try:
                # ファイル名解析
                parts = csv_file.stem.split("_")
                if len(parts) >= 3:
                    symbol = f"{parts[0]}/{parts[1]}"
                    timeframe = parts[2]

                    # ファイル情報
                    stat = csv_file.stat()

                    # サンプルデータ読み込み（設定可能サイズ）
                    sample_df = pd.read_csv(csv_file, nrows=10)

                    info[f"{symbol}_{timeframe}"] = {
                        "file_path": str(csv_file),
                        "file_size_mb": stat.st_size / 1024 / 1024,
                        "modified_time": datetime.fromtimestamp(stat.st_mtime),
                        "sample_rows": len(sample_df),
                        "columns": list(sample_df.columns),
                    }

            except Exception as e:
                self.logger.warning(f"ファイル情報取得エラー {csv_file}: {e}")

        return info

    def clear_cache(self) -> None:
        """キャッシュクリア"""
        if self._cache_enabled and self._cache is not None:
            self._cache.clear()
            self.logger.info("CSVキャッシュをクリアしました")
        else:
            self.logger.debug("キャッシュ無効のためクリア不要")

    def validate_data_integrity(self, symbol: str, timeframe: str) -> Dict[str, bool]:
        """データ整合性チェック"""
        try:
            df = self.load_historical_data(symbol, timeframe)

            checks = {
                "has_data": not df.empty,
                "valid_columns": all(
                    col in df.columns for col in ["open", "high", "low", "close", "volume"]
                ),
                "no_duplicates": not df.index.duplicated().any(),
                "sorted_index": df.index.is_monotonic_increasing,
                "no_null_values": not df.isnull().any().any(),
                "positive_prices": (df[["open", "high", "low", "close"]] > 0).all().all(),
                "positive_volume": (df["volume"] >= 0).all(),
                "valid_ohlc": (df["high"] >= df[["open", "low", "close"]].max(axis=1)).all(),
            }

            self.logger.info(f"整合性チェック結果 {symbol} {timeframe}: {checks}")
            return checks

        except Exception as e:
            self.logger.error(f"整合性チェックエラー: {e}")
            return {"error": True, "message": str(e)}


# バックテスト用のグローバルインスタンス
_csv_loader = None


def get_csv_loader() -> BacktestCSVLoader:
    """CSVローダーのグローバルインスタンス取得"""
    global _csv_loader
    if _csv_loader is None:
        _csv_loader = BacktestCSVLoader()
    return _csv_loader

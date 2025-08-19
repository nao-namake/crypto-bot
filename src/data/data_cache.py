"""
データキャッシング機能 - メモリ効率・3ヶ月保存対応

高速アクセスとメモリ効率を両立した
データキャッシングシステムの実装。

主な特徴:
- インメモリキャッシュによる高速アクセス
- LRU（Least Recently Used）方式での自動削除
- 3ヶ月間の長期保存対応
- データ整合性チェック機能.
"""

import gzip
import pickle
import threading
from collections import OrderedDict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from ..core.exceptions import DataFetchError
from ..core.logger import get_logger


@dataclass
class CacheMetadata:
    """キャッシュメタデータ."""

    key: str
    created_at: datetime
    last_accessed: datetime
    size_bytes: int
    data_type: str
    timeframe: str
    symbol: str
    expires_at: Optional[datetime] = None


class LRUCache:
    """LRU（Least Recently Used）キャッシュ実装."""

    def __init__(self, max_size: int = 1000):
        """
        初期化

        Args:
            max_size: 最大キャッシュサイズ.
        """
        self.max_size = max_size
        self._cache: OrderedDict = OrderedDict()
        self._metadata: Dict[str, CacheMetadata] = {}
        self._lock = threading.RLock()
        self.logger = get_logger()

    def get(self, key: str) -> Optional[Any]:
        """データ取得."""
        with self._lock:
            if key in self._cache:
                # アクセス時刻更新（LRU）
                value = self._cache.pop(key)
                self._cache[key] = value

                # メタデータ更新
                if key in self._metadata:
                    self._metadata[key].last_accessed = datetime.now()

                return value
            return None

    def put(self, key: str, value: Any, metadata: Optional[CacheMetadata] = None):
        """データ保存."""
        with self._lock:
            # 既存エントリを削除
            if key in self._cache:
                del self._cache[key]

            # 容量チェック
            while len(self._cache) >= self.max_size:
                # 最古のエントリを削除
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                if oldest_key in self._metadata:
                    del self._metadata[oldest_key]

            # 新しいエントリを追加
            self._cache[key] = value

            if metadata:
                self._metadata[key] = metadata

    def remove(self, key: str) -> bool:
        """データ削除."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._metadata:
                    del self._metadata[key]
                return True
            return False

    def clear(self):
        """全データクリア."""
        with self._lock:
            self._cache.clear()
            self._metadata.clear()

    def keys(self) -> List[str]:
        """全キー取得."""
        with self._lock:
            return list(self._cache.keys())

    def size(self) -> int:
        """キャッシュサイズ取得."""
        return len(self._cache)

    def get_metadata(self, key: str) -> Optional[CacheMetadata]:
        """メタデータ取得."""
        return self._metadata.get(key)


class DataCache:
    """
    データキャッシング管理システム

    メモリキャッシュと永続化を組み合わせた
    高性能データキャッシングを提供.
    """

    def __init__(
        self,
        cache_dir: str = ".cache/data",
        memory_cache_size: int = 500,
        retention_days: int = 90,
    ):
        """
        初期化

        Args:
            cache_dir: キャッシュディレクトリ（統合キャッシュ配下）
            memory_cache_size: メモリキャッシュサイズ
            retention_days: 保持期間（日数）.
        """
        self.logger = get_logger()

        # ディレクトリ設定（統合キャッシュ配下）
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # メモリキャッシュ
        self.memory_cache = LRUCache(memory_cache_size)

        # 設定
        self.retention_days = retention_days
        self.cleanup_interval_hours = 24  # クリーンアップ間隔

        # 統計
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "disk_saves": 0,
            "disk_loads": 0,
        }

        # 最後のクリーンアップ時刻
        self._last_cleanup = datetime.now()

        self.logger.info(f"データキャッシュ初期化: {cache_dir} (保持期間: {retention_days}日)")

    def _generate_cache_key(
        self,
        symbol: str,
        timeframe: str,
        start_time: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> str:
        """キャッシュキー生成."""
        key_parts = [symbol, timeframe]

        if start_time:
            key_parts.append(start_time.strftime("%Y%m%d_%H%M"))
        if limit:
            key_parts.append(f"limit_{limit}")

        return "_".join(key_parts)

    def _get_file_path(self, key: str) -> Path:
        """ファイルパス取得."""
        # 安全なファイル名に変換
        safe_key = key.replace("/", "_").replace(":", "_")
        return self.cache_dir / f"{safe_key}.pkl.gz"

    def _save_to_disk(self, key: str, data: Any, metadata: CacheMetadata):
        """ディスクに保存."""
        try:
            file_path = self._get_file_path(key)

            # データを圧縮して保存
            with gzip.open(file_path, "wb") as f:
                pickle.dump({"data": data, "metadata": asdict(metadata)}, f)

            self.stats["disk_saves"] += 1
            self.logger.debug(f"ディスク保存完了: {key}")

        except Exception as e:
            self.logger.error(f"ディスク保存エラー: {key} - {e}")

    def _load_from_disk(self, key: str) -> Optional[Tuple[Any, CacheMetadata]]:
        """ディスクから読み込み."""
        try:
            file_path = self._get_file_path(key)

            if not file_path.exists():
                return None

            with gzip.open(file_path, "rb") as f:
                cached_data = pickle.load(f)

            # メタデータを復元
            metadata_dict = cached_data["metadata"]
            metadata = CacheMetadata(
                key=metadata_dict["key"],
                created_at=datetime.fromisoformat(metadata_dict["created_at"]),
                last_accessed=datetime.fromisoformat(metadata_dict["last_accessed"]),
                size_bytes=metadata_dict["size_bytes"],
                data_type=metadata_dict["data_type"],
                timeframe=metadata_dict["timeframe"],
                symbol=metadata_dict["symbol"],
                expires_at=(
                    datetime.fromisoformat(metadata_dict["expires_at"])
                    if metadata_dict["expires_at"]
                    else None
                ),
            )

            self.stats["disk_loads"] += 1
            self.logger.debug(f"ディスク読み込み完了: {key}")

            return cached_data["data"], metadata

        except Exception as e:
            self.logger.error(f"ディスク読み込みエラー: {key} - {e}")
            return None

    def _is_expired(self, metadata: CacheMetadata) -> bool:
        """期限切れチェック."""
        if metadata.expires_at:
            return datetime.now() > metadata.expires_at

        # デフォルト保持期間チェック
        age = datetime.now() - metadata.created_at
        return age.days > self.retention_days

    def get(
        self,
        symbol: str,
        timeframe: str,
        start_time: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> Optional[pd.DataFrame]:
        """
        キャッシュからデータ取得

        Args:
            symbol: 通貨ペア
            timeframe: タイムフレーム
            start_time: 開始時刻
            limit: 件数制限

        Returns:
            キャッシュされたデータ（なければNone）.
        """
        key = self._generate_cache_key(symbol, timeframe, start_time, limit)

        # メモリキャッシュから試行
        data = self.memory_cache.get(key)
        if data is not None:
            self.stats["cache_hits"] += 1
            self.logger.debug(f"メモリキャッシュヒット: {key}")
            return data

        # ディスクキャッシュから試行
        disk_result = self._load_from_disk(key)
        if disk_result:
            data, metadata = disk_result

            # 期限切れチェック
            if self._is_expired(metadata):
                self._remove_disk_cache(key)
                self.stats["cache_misses"] += 1
                return None

            # メモリキャッシュに復元
            self.memory_cache.put(key, data, metadata)
            self.stats["cache_hits"] += 1
            self.logger.debug(f"ディスクキャッシュヒット: {key}")
            return data

        self.stats["cache_misses"] += 1
        return None

    def put(
        self,
        symbol: str,
        timeframe: str,
        data: pd.DataFrame,
        start_time: Optional[datetime] = None,
        limit: Optional[int] = None,
        expires_in_hours: Optional[int] = None,
    ):
        """
        データをキャッシュに保存

        Args:
            symbol: 通貨ペア
            timeframe: タイムフレーム
            data: データ
            start_time: 開始時刻
            limit: 件数制限
            expires_in_hours: 有効期限（時間）.
        """
        key = self._generate_cache_key(symbol, timeframe, start_time, limit)

        # メタデータ作成
        now = datetime.now()
        expires_at = None
        if expires_in_hours:
            expires_at = now + timedelta(hours=expires_in_hours)

        # データサイズ計算
        size_bytes = data.memory_usage(deep=True).sum()

        metadata = CacheMetadata(
            key=key,
            created_at=now,
            last_accessed=now,
            size_bytes=size_bytes,
            data_type="DataFrame",
            timeframe=timeframe,
            symbol=symbol,
            expires_at=expires_at,
        )

        # メモリキャッシュに保存
        self.memory_cache.put(key, data, metadata)

        # ディスクにも保存（非同期で行うことも可能）
        self._save_to_disk(key, data, metadata)

        self.logger.debug(f"キャッシュ保存完了: {key} ({size_bytes} bytes)")

    def _remove_disk_cache(self, key: str):
        """ディスクキャッシュ削除."""
        try:
            file_path = self._get_file_path(key)
            if file_path.exists():
                file_path.unlink()
                self.logger.debug(f"ディスクキャッシュ削除: {key}")
        except Exception as e:
            self.logger.error(f"ディスクキャッシュ削除エラー: {key} - {e}")

    def remove(
        self,
        symbol: str,
        timeframe: str,
        start_time: Optional[datetime] = None,
        limit: Optional[int] = None,
    ):
        """キャッシュ削除."""
        key = self._generate_cache_key(symbol, timeframe, start_time, limit)

        # メモリから削除
        self.memory_cache.remove(key)

        # ディスクから削除
        self._remove_disk_cache(key)

    def cleanup_expired(self):
        """期限切れキャッシュのクリーンアップ."""
        now = datetime.now()

        # クリーンアップ間隔チェック
        if (now - self._last_cleanup).total_seconds() < (self.cleanup_interval_hours * 3600):
            return

        self.logger.info("期限切れキャッシュのクリーンアップ開始")

        cleaned_count = 0

        # メモリキャッシュのクリーンアップ
        keys_to_remove = []
        for key in self.memory_cache.keys():
            metadata = self.memory_cache.get_metadata(key)
            if metadata and self._is_expired(metadata):
                keys_to_remove.append(key)

        for key in keys_to_remove:
            self.memory_cache.remove(key)
            cleaned_count += 1

        # ディスクキャッシュのクリーンアップ
        for file_path in self.cache_dir.glob("*.pkl.gz"):
            try:
                # ファイルの更新時刻をチェック
                file_age = now - datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_age.days > self.retention_days:
                    file_path.unlink()
                    cleaned_count += 1
            except Exception as e:
                self.logger.error(f"ファイルクリーンアップエラー: {file_path} - {e}")

        self._last_cleanup = now
        self.logger.info(f"クリーンアップ完了: {cleaned_count}件削除")

    def clear_all(self):
        """全キャッシュクリア."""
        # メモリクリア
        self.memory_cache.clear()

        # ディスククリア
        for file_path in self.cache_dir.glob("*.pkl.gz"):
            try:
                file_path.unlink()
            except Exception as e:
                self.logger.error(f"ファイル削除エラー: {file_path} - {e}")

        self.logger.info("全キャッシュをクリアしました")

    def get_cache_stats(self) -> Dict[str, Any]:
        """キャッシュ統計取得."""
        # ディスク使用量計算
        disk_size = sum(file_path.stat().st_size for file_path in self.cache_dir.glob("*.pkl.gz"))

        # メモリ使用量計算
        memory_size = sum(metadata.size_bytes for metadata in self.memory_cache._metadata.values())

        hit_rate = 0
        total_requests = self.stats["cache_hits"] + self.stats["cache_misses"]
        if total_requests > 0:
            hit_rate = self.stats["cache_hits"] / total_requests * 100

        return {
            "memory_cache_size": self.memory_cache.size(),
            "memory_usage_bytes": memory_size,
            "disk_usage_bytes": disk_size,
            "hit_rate_percent": round(hit_rate, 2),
            "total_hits": self.stats["cache_hits"],
            "total_misses": self.stats["cache_misses"],
            "disk_saves": self.stats["disk_saves"],
            "disk_loads": self.stats["disk_loads"],
            "retention_days": self.retention_days,
        }


# グローバルキャッシュインスタンス
_data_cache: Optional[DataCache] = None


def get_data_cache() -> DataCache:
    """グローバルデータキャッシュ取得."""
    global _data_cache

    if _data_cache is None:
        _data_cache = DataCache()

    return _data_cache

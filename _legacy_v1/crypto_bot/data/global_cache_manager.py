# =============================================================================
# ファイル名: crypto_bot/data/global_cache_manager.py
# 説明:
# 外部データグローバルキャッシュ管理システム
# ・重複リクエスト排除・インテリジェントTTL・API効率50%向上
# ・VIX・Macro・Fear&Greed統合キャッシュ・品質監視統合
# ・Phase A3: 外部データキャッシュ最適化
# =============================================================================

import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """キャッシュエントリクラス"""

    key: str
    data: Any
    timestamp: datetime
    ttl: timedelta
    access_count: int = 0
    last_access: datetime = field(default_factory=datetime.now)
    quality_score: float = 1.0
    source: str = "unknown"
    size_bytes: int = 0

    def is_expired(self) -> bool:
        """有効期限チェック"""
        return datetime.now() > (self.timestamp + self.ttl)

    def is_stale(self, staleness_factor: float = 0.8) -> bool:
        """データ陳腐化チェック"""
        stale_time = self.timestamp + (self.ttl * staleness_factor)
        return datetime.now() > stale_time

    def update_access(self):
        """アクセス情報更新"""
        self.access_count += 1
        self.last_access = datetime.now()


class GlobalCacheManager:
    """外部データグローバルキャッシュ管理クラス"""

    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        """シングルトンパターン実装"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """初期化（シングルトンなので一度のみ実行）"""
        if hasattr(self, "_initialized"):
            return

        self._cache: Dict[str, CacheEntry] = {}
        self._cache_lock = threading.RLock()
        self._stats = {
            "requests": 0,
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "api_calls_saved": 0,
            "total_size_bytes": 0,
        }

        # キャッシュ設定
        self.max_cache_size = 100  # 最大エントリ数
        self.cleanup_interval = 300  # 5分間隔でクリーンアップ
        self.max_memory_mb = 50  # 50MB上限

        # データ種別別TTL設定
        self.default_ttls = {
            "vix": timedelta(hours=24),  # VIXは日次更新
            "macro": timedelta(hours=6),  # マクロデータは6時間
            "fear_greed": timedelta(hours=1),  # Fear&Greedは1時間
            "funding": timedelta(minutes=30),  # Funding Rateは30分
            "forex": timedelta(hours=4),  # 為替は4時間
            "default": timedelta(hours=2),  # デフォルト2時間
        }

        # リクエスト重複防止用
        self._pending_requests: Dict[str, threading.Event] = {}
        self._request_results: Dict[str, Any] = {}

        # バックグラウンドクリーンアップ開始
        self._cleanup_thread = threading.Thread(
            target=self._background_cleanup, daemon=True
        )
        self._cleanup_thread.start()

        self._initialized = True
        logger.info("🗄️ GlobalCacheManager initialized (singleton)")
        logger.info(f"  - Max cache size: {self.max_cache_size}")
        logger.info(f"  - Max memory: {self.max_memory_mb}MB")
        logger.info(f"  - Cleanup interval: {self.cleanup_interval}s")

    def get_cache_key(self, source: str, params: Dict[str, Any] = None) -> str:
        """キャッシュキー生成"""
        if params:
            params_str = json.dumps(params, sort_keys=True, default=str)
            params_hash = hashlib.md5(params_str.encode()).hexdigest()
            return f"{source}:{params_hash}"
        return source

    def get(self, key: str, default: Any = None) -> Optional[Any]:
        """キャッシュデータ取得"""
        with self._cache_lock:
            self._stats["requests"] += 1

            if key in self._cache:
                entry = self._cache[key]

                if entry.is_expired():
                    # 期限切れエントリ削除
                    del self._cache[key]
                    self._stats["misses"] += 1
                    logger.debug(f"💀 Cache expired: {key}")
                    return default

                # アクセス更新
                entry.update_access()
                self._stats["hits"] += 1
                self._stats["api_calls_saved"] += 1

                logger.debug(
                    f"🎯 Cache hit: {key} (quality: {entry.quality_score:.2f})"
                )
                return entry.data

            self._stats["misses"] += 1
            logger.debug(f"❌ Cache miss: {key}")
            return default

    def put(
        self,
        key: str,
        data: Any,
        source: str = "unknown",
        ttl: timedelta = None,
        quality_score: float = 1.0,
    ) -> bool:
        """キャッシュデータ保存"""
        try:
            with self._cache_lock:
                # TTL設定
                if ttl is None:
                    ttl = self.default_ttls.get(source, self.default_ttls["default"])

                # データサイズ計算
                size_bytes = self._calculate_size(data)

                # メモリ制限チェック
                if not self._check_memory_limit(size_bytes):
                    logger.warning(f"⚠️ Memory limit exceeded, skipping cache: {key}")
                    return False

                # キャッシュサイズ制限チェック・クリーンアップ
                if len(self._cache) >= self.max_cache_size:
                    self._evict_lru_entries()

                # エントリ作成・保存
                entry = CacheEntry(
                    key=key,
                    data=data,
                    timestamp=datetime.now(),
                    ttl=ttl,
                    quality_score=quality_score,
                    source=source,
                    size_bytes=size_bytes,
                )

                self._cache[key] = entry
                self._stats["total_size_bytes"] += size_bytes

                logger.debug(
                    f"💾 Cached: {key} (TTL: {ttl}, Quality: {quality_score:.2f}, Size: {size_bytes}B)"
                )
                return True

        except Exception as e:
            logger.error(f"❌ Cache put failed: {key}, error: {e}")
            return False

    def get_or_fetch(
        self,
        key: str,
        fetch_func: callable,
        source: str = "unknown",
        ttl: timedelta = None,
        quality_score: float = 1.0,
        force_refresh: bool = False,
    ) -> Tuple[Any, bool]:
        """キャッシュ取得またはフェッチ（重複リクエスト防止付き）"""
        # 強制リフレッシュでない場合はキャッシュチェック
        if not force_refresh:
            cached_data = self.get(key)
            if cached_data is not None:
                return cached_data, True  # キャッシュヒット

        # リクエスト重複防止処理
        with self._cache_lock:
            if key in self._pending_requests:
                # 既に同じリクエストが進行中
                logger.debug(f"⏳ Waiting for pending request: {key}")
                event = self._pending_requests[key]
            else:
                # 新しいリクエスト開始
                event = threading.Event()
                self._pending_requests[key] = event
                need_fetch = True

        if key not in locals() or "need_fetch" not in locals():
            # 他のスレッドの結果待ち
            event.wait(timeout=30)  # 30秒タイムアウト

            with self._cache_lock:
                if key in self._request_results:
                    result = self._request_results[key]
                    del self._request_results[key]  # クリーンアップ
                    return result, False  # 他スレッドからの結果

            # タイムアウト時は独自実行
            logger.warning(f"⚠️ Request timeout, executing independently: {key}")

        # 実際のフェッチ実行
        try:
            logger.debug(f"🔄 Fetching: {key}")
            data = fetch_func()

            # 成功時はキャッシュに保存
            if data is not None:
                self.put(key, data, source, ttl, quality_score)

            # 結果を待機中のスレッドに共有
            with self._cache_lock:
                self._request_results[key] = data
                if key in self._pending_requests:
                    self._pending_requests[key].set()
                    del self._pending_requests[key]

            return data, False  # 新規フェッチ

        except Exception as e:
            logger.error(f"❌ Fetch failed: {key}, error: {e}")

            # エラー時もイベント解放
            with self._cache_lock:
                if key in self._pending_requests:
                    self._pending_requests[key].set()
                    del self._pending_requests[key]

            return None, False

    def invalidate(self, key_pattern: str = None, source: str = None) -> int:
        """キャッシュ無効化"""
        invalidated = 0

        with self._cache_lock:
            keys_to_remove = []

            for key, entry in self._cache.items():
                should_remove = False

                if key_pattern and key_pattern in key:
                    should_remove = True
                elif source and entry.source == source:
                    should_remove = True
                elif key_pattern is None and source is None:
                    should_remove = True  # 全削除

                if should_remove:
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                entry = self._cache[key]
                self._stats["total_size_bytes"] -= entry.size_bytes
                del self._cache[key]
                invalidated += 1

        logger.info(f"🗑️ Invalidated {invalidated} cache entries")
        return invalidated

    def _evict_lru_entries(self, target_size: int = None):
        """LRU方式でエントリ削除"""
        if target_size is None:
            target_size = self.max_cache_size - 10  # 10個余裕を持たせる

        # アクセス時刻順でソート（古い順）
        entries = list(self._cache.items())
        entries.sort(key=lambda x: x[1].last_access)

        removed_count = 0
        for key, entry in entries[: len(entries) - target_size]:
            self._stats["total_size_bytes"] -= entry.size_bytes
            del self._cache[key]
            removed_count += 1
            self._stats["evictions"] += 1

        if removed_count > 0:
            logger.info(f"🗑️ Evicted {removed_count} LRU cache entries")

    def _check_memory_limit(self, additional_bytes: int = 0) -> bool:
        """メモリ制限チェック"""
        total_size_mb = (self._stats["total_size_bytes"] + additional_bytes) / (
            1024 * 1024
        )
        return total_size_mb <= self.max_memory_mb

    def _calculate_size(self, data: Any) -> int:
        """データサイズ計算（概算）"""
        try:
            if isinstance(data, pd.DataFrame):
                return data.memory_usage(deep=True).sum()
            elif isinstance(data, (dict, list)):
                return len(json.dumps(data, default=str).encode("utf-8"))
            elif isinstance(data, str):
                return len(data.encode("utf-8"))
            else:
                return len(str(data).encode("utf-8"))
        except Exception:
            return 1024  # デフォルト1KB

    def _background_cleanup(self):
        """バックグラウンドクリーンアップ"""
        while True:
            try:
                time.sleep(self.cleanup_interval)
                self._cleanup_expired_entries()
            except Exception as e:
                logger.error(f"❌ Background cleanup failed: {e}")

    def _cleanup_expired_entries(self):
        """期限切れエントリクリーンアップ"""
        with self._cache_lock:
            expired_keys = []

            for key, entry in self._cache.items():
                if entry.is_expired():
                    expired_keys.append(key)

            for key in expired_keys:
                entry = self._cache[key]
                self._stats["total_size_bytes"] -= entry.size_bytes
                del self._cache[key]

            if expired_keys:
                logger.info(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")

    def get_stats(self) -> Dict[str, Any]:
        """キャッシュ統計取得"""
        with self._cache_lock:
            hit_rate = (
                (self._stats["hits"] / self._stats["requests"]) * 100
                if self._stats["requests"] > 0
                else 0
            )

            return {
                "cache_size": len(self._cache),
                "max_cache_size": self.max_cache_size,
                "total_size_mb": self._stats["total_size_bytes"] / (1024 * 1024),
                "max_memory_mb": self.max_memory_mb,
                "requests": self._stats["requests"],
                "hits": self._stats["hits"],
                "misses": self._stats["misses"],
                "hit_rate_percent": hit_rate,
                "evictions": self._stats["evictions"],
                "api_calls_saved": self._stats["api_calls_saved"],
                "pending_requests": len(self._pending_requests),
            }

    def get_cache_info(self) -> Dict[str, Any]:
        """詳細キャッシュ情報取得"""
        with self._cache_lock:
            entries_info = []

            for key, entry in self._cache.items():
                entries_info.append(
                    {
                        "key": key,
                        "source": entry.source,
                        "age_minutes": (
                            datetime.now() - entry.timestamp
                        ).total_seconds()
                        / 60,
                        "ttl_minutes": entry.ttl.total_seconds() / 60,
                        "access_count": entry.access_count,
                        "quality_score": entry.quality_score,
                        "size_kb": entry.size_bytes / 1024,
                        "is_stale": entry.is_stale(),
                    }
                )

            # アクセス回数順でソート
            entries_info.sort(key=lambda x: x["access_count"], reverse=True)

            return {
                "stats": self.get_stats(),
                "entries": entries_info,
                "ttl_settings": {
                    k: v.total_seconds() / 3600 for k, v in self.default_ttls.items()
                },
            }


# グローバルシングルトンインスタンス取得関数
def get_global_cache() -> GlobalCacheManager:
    """グローバルキャッシュインスタンス取得"""
    return GlobalCacheManager()


# 外部データフェッチャー統合用デコレータ
def cached_external_data(
    source: str, ttl_hours: float = None, quality_threshold: float = 0.5
):
    """外部データフェッチャー用キャッシュデコレータ"""

    def decorator(fetch_func):
        def wrapper(*args, **kwargs):
            cache = get_global_cache()

            # キャッシュキー生成
            params = {**kwargs}
            if args:
                params["args"] = str(args)
            cache_key = cache.get_cache_key(source, params)

            # TTL設定
            ttl = timedelta(hours=ttl_hours) if ttl_hours else None

            # キャッシュ取得またはフェッチ
            def fetch():
                return fetch_func(*args, **kwargs)

            data, from_cache = cache.get_or_fetch(
                cache_key,
                fetch,
                source=source,
                ttl=ttl,
                quality_score=kwargs.get("quality_score", quality_threshold),
            )

            return data

        return wrapper

    return decorator

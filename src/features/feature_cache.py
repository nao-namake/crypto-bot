"""
特徴量生成キャッシュ - Phase 89-α Stage 2

同一サイクル内で同じ market_data から繰り返し特徴量計算する無駄を削減する
LRU + TTL キャッシュ。

設計:
- src/data/data_cache.py の LRUCache 設計を踏襲（OrderedDict + threading.RLock）
- ディスク永続化なし（特徴量はサイクル内のみ価値あり）
- TTL ベースの自動失効
- BACKTEST_MODE=true 環境変数または config disable で完全無効化可能

キャッシュキー設計:
- (symbol, timeframe, last_timestamp, len(df), last_close) を md5 でハッシュ化
- last_close を含めることで同タイムスタンプでも内容が変われば別キー
"""

import hashlib
import threading
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

import pandas as pd

from ..core.config.threshold_manager import get_threshold
from ..core.logger import get_logger


class FeatureCache:
    """特徴量 DataFrame の LRU + TTL キャッシュ."""

    def __init__(
        self,
        max_size: Optional[int] = None,
        ttl_seconds: Optional[int] = None,
        enabled: Optional[bool] = None,
    ):
        """
        初期化

        Args:
            max_size: 最大エントリ数（None で config から取得）
            ttl_seconds: TTL 秒数（None で config から取得）
            enabled: 有効化フラグ（None で config から取得）
        """
        self.logger = get_logger()
        self._lock = threading.RLock()
        self._cache: "OrderedDict[str, Tuple[pd.DataFrame, datetime]]" = OrderedDict()

        self.max_size = (
            max_size if max_size is not None else get_threshold("features.cache.max_size", 200)
        )
        self.ttl_seconds = (
            ttl_seconds
            if ttl_seconds is not None
            else get_threshold("features.cache.ttl_seconds", 600)
        )
        self.enabled = (
            enabled if enabled is not None else get_threshold("features.cache.enabled", True)
        )

        self._stats: Dict[str, int] = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
        }

    @staticmethod
    def compute_key(symbol: str, timeframe: str, df: pd.DataFrame) -> str:
        """
        市場データ DataFrame から決定論的なキャッシュキーを生成

        last_timestamp + len + last_close を含めることで、同タイムスタンプでも
        異なる内容なら別キー（衝突確率実質ゼロ）。

        Args:
            symbol: 通貨ペア（例: "BTC/JPY"）
            timeframe: タイムフレーム（例: "15m"）
            df: 市場データ DataFrame（OHLCV を含むこと）

        Returns:
            32 文字の md5 ハッシュキー（DataFrame が空の場合は固定値）
        """
        if df is None or len(df) == 0:
            return hashlib.md5(f"{symbol}|{timeframe}|empty".encode("utf-8")).hexdigest()

        if isinstance(df.index, pd.DatetimeIndex):
            last_ts = df.index[-1].isoformat()
        else:
            last_ts = str(df.index[-1])

        last_close = float(df["close"].iloc[-1]) if "close" in df.columns else 0.0
        signature = f"{symbol}|{timeframe}|{last_ts}|{len(df)}|{last_close:.6f}"
        return hashlib.md5(signature.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[pd.DataFrame]:
        """
        キャッシュから DataFrame を取得（コピーを返す）

        Returns:
            キャッシュ DataFrame のコピー（ミス・期限切れ・無効化時 None）
        """
        if not self.enabled:
            return None

        with self._lock:
            if key not in self._cache:
                self._stats["misses"] += 1
                return None

            df, expires_at = self._cache[key]

            if datetime.now() >= expires_at:
                del self._cache[key]
                self._stats["expirations"] += 1
                self._stats["misses"] += 1
                return None

            # LRU: 最新アクセスとして末尾へ
            self._cache.move_to_end(key)
            self._stats["hits"] += 1
            return df.copy()

    def put(self, key: str, df: pd.DataFrame) -> None:
        """
        DataFrame をキャッシュに保存（コピーを保持）

        max_size を超えた場合は古いエントリから順に LRU 削除。
        """
        if not self.enabled:
            return

        with self._lock:
            expires_at = datetime.now() + timedelta(seconds=self.ttl_seconds)

            if key in self._cache:
                del self._cache[key]

            self._cache[key] = (df.copy(), expires_at)

            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)
                self._stats["evictions"] += 1

    def clear(self) -> None:
        """全エントリと統計をクリア."""
        with self._lock:
            self._cache.clear()
            for key in self._stats:
                self._stats[key] = 0

    def stats(self) -> Dict[str, Any]:
        """統計取得."""
        with self._lock:
            total = self._stats["hits"] + self._stats["misses"]
            hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0.0
            return {
                **self._stats,
                "size": len(self._cache),
                "max_size": self.max_size,
                "hit_rate_percent": round(hit_rate, 2),
                "enabled": self.enabled,
            }

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)


_feature_cache: Optional[FeatureCache] = None
_singleton_lock = threading.Lock()


def get_feature_cache() -> FeatureCache:
    """グローバル FeatureCache シングルトン."""
    global _feature_cache
    if _feature_cache is None:
        with _singleton_lock:
            if _feature_cache is None:
                _feature_cache = FeatureCache()
    return _feature_cache


def reset_feature_cache() -> None:
    """テスト用: シングルトンを再生成."""
    global _feature_cache
    with _singleton_lock:
        _feature_cache = None

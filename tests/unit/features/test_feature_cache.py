"""
FeatureCache テスト - Phase 89-α Stage 2

特徴量生成キャッシュ（src/features/feature_cache.py）の包括テスト 12 件。
"""

import threading
from datetime import datetime, timedelta
from unittest.mock import patch

import pandas as pd
import pytest

from src.features.feature_cache import (
    FeatureCache,
    get_feature_cache,
    reset_feature_cache,
)


@pytest.fixture(autouse=True)
def _reset_singleton():
    """各テストでシングルトンを初期化."""
    reset_feature_cache()
    yield
    reset_feature_cache()


def _make_df(n: int = 10, last_close: float = 100.0) -> pd.DataFrame:
    """テスト用 OHLCV DataFrame を作成."""
    idx = pd.date_range("2026-01-01", periods=n, freq="15min")
    closes = [last_close - (n - 1 - i) * 0.5 for i in range(n)]
    return pd.DataFrame(
        {
            "open": closes,
            "high": [c + 1 for c in closes],
            "low": [c - 1 for c in closes],
            "close": closes,
            "volume": [1.0] * n,
        },
        index=idx,
    )


def test_get_returns_none_when_empty():
    """空キャッシュからの取得は None を返す."""
    cache = FeatureCache(max_size=10, ttl_seconds=60, enabled=True)
    assert cache.get("nonexistent_key") is None
    stats = cache.stats()
    assert stats["misses"] == 1
    assert stats["hits"] == 0


def test_put_then_get_roundtrip():
    """put → get で同じ内容の DataFrame が返る."""
    cache = FeatureCache(max_size=10, ttl_seconds=60, enabled=True)
    df = _make_df()
    key = FeatureCache.compute_key("BTC/JPY", "15m", df)

    cache.put(key, df)
    retrieved = cache.get(key)

    assert retrieved is not None
    pd.testing.assert_frame_equal(retrieved, df)


def test_lru_eviction_when_max_size_exceeded():
    """max_size を超えたら最古エントリから LRU 削除される."""
    cache = FeatureCache(max_size=3, ttl_seconds=60, enabled=True)

    keys = []
    for i in range(5):
        df = _make_df(n=10, last_close=100.0 + i)
        key = FeatureCache.compute_key("BTC/JPY", "15m", df)
        cache.put(key, df)
        keys.append(key)

    assert len(cache) == 3
    # 最初の 2 件は eviction されているはず
    assert cache.get(keys[0]) is None
    assert cache.get(keys[1]) is None
    # 直近 3 件は残っているはず
    assert cache.get(keys[2]) is not None
    assert cache.get(keys[3]) is not None
    assert cache.get(keys[4]) is not None

    stats = cache.stats()
    assert stats["evictions"] >= 2


def test_ttl_expiration():
    """TTL 経過後の get は None を返し expirations カウントが増える."""
    cache = FeatureCache(max_size=10, ttl_seconds=60, enabled=True)
    df = _make_df()
    key = FeatureCache.compute_key("BTC/JPY", "15m", df)
    cache.put(key, df)

    # 通常取得（TTL 内）
    assert cache.get(key) is not None

    # datetime.now を未来時刻にモックして TTL 切れをシミュレート
    future = datetime.now() + timedelta(seconds=120)
    with patch("src.features.feature_cache.datetime") as mock_dt:
        mock_dt.now.return_value = future
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)
        result = cache.get(key)

    assert result is None
    stats = cache.stats()
    assert stats["expirations"] == 1


def test_thread_safety_concurrent_access():
    """並行 put/get でも整合性が保たれる."""
    cache = FeatureCache(max_size=100, ttl_seconds=60, enabled=True)
    errors = []

    def worker(thread_id: int):
        try:
            for i in range(20):
                df = _make_df(n=5, last_close=100.0 + thread_id * 100 + i)
                key = FeatureCache.compute_key("BTC/JPY", f"t{thread_id}", df)
                cache.put(key, df)
                retrieved = cache.get(key)
                # キャッシュサイズ制限超過時は eviction されている可能性があるため None も許容
                if retrieved is not None:
                    assert "close" in retrieved.columns
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"並行アクセス中にエラー: {errors}"


def test_clear_removes_all_entries():
    """clear で全エントリと統計が消える."""
    cache = FeatureCache(max_size=10, ttl_seconds=60, enabled=True)
    for i in range(3):
        df = _make_df(last_close=100.0 + i)
        key = FeatureCache.compute_key("BTC/JPY", "15m", df)
        cache.put(key, df)

    assert len(cache) == 3
    cache.clear()
    assert len(cache) == 0
    stats = cache.stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["evictions"] == 0


def test_stats_counts_hits_and_misses():
    """hits/misses/hit_rate が正しくカウントされる."""
    cache = FeatureCache(max_size=10, ttl_seconds=60, enabled=True)
    df = _make_df()
    key = FeatureCache.compute_key("BTC/JPY", "15m", df)

    # ミス 2 回
    cache.get(key)
    cache.get(key)
    cache.put(key, df)
    # ヒット 3 回
    cache.get(key)
    cache.get(key)
    cache.get(key)

    stats = cache.stats()
    assert stats["hits"] == 3
    assert stats["misses"] == 2
    assert stats["hit_rate_percent"] == 60.0


def test_key_generation_deterministic():
    """同じ DataFrame に対するキー生成は決定論的."""
    df = _make_df()
    k1 = FeatureCache.compute_key("BTC/JPY", "15m", df)
    k2 = FeatureCache.compute_key("BTC/JPY", "15m", df.copy())
    assert k1 == k2
    assert len(k1) == 32  # md5 hex


def test_key_generation_differs_for_different_dataframes():
    """異なる内容の DataFrame は異なるキーを生成."""
    df1 = _make_df(last_close=100.0)
    df2 = _make_df(last_close=200.0)
    df3 = _make_df(n=20, last_close=100.0)  # len 違い

    k1 = FeatureCache.compute_key("BTC/JPY", "15m", df1)
    k2 = FeatureCache.compute_key("BTC/JPY", "15m", df2)
    k3 = FeatureCache.compute_key("BTC/JPY", "15m", df3)

    assert k1 != k2
    assert k1 != k3
    assert k2 != k3

    # シンボル違いも別キー
    k4 = FeatureCache.compute_key("ETH/JPY", "15m", df1)
    assert k1 != k4


def test_disabled_via_config():
    """enabled=False では put しても get で None が返る."""
    cache = FeatureCache(max_size=10, ttl_seconds=60, enabled=False)
    df = _make_df()
    key = FeatureCache.compute_key("BTC/JPY", "15m", df)

    cache.put(key, df)
    assert cache.get(key) is None
    # 無効化時は内部状態を触らない
    assert len(cache) == 0


def test_returned_df_is_copy_not_reference():
    """get で返る DataFrame はコピー（cache 内 DF への参照ではない）."""
    cache = FeatureCache(max_size=10, ttl_seconds=60, enabled=True)
    df = _make_df()
    key = FeatureCache.compute_key("BTC/JPY", "15m", df)

    cache.put(key, df)
    retrieved = cache.get(key)
    retrieved.loc[retrieved.index[0], "close"] = -999999.0  # 改変

    # 再取得しても改変が反映されていないこと
    retrieved2 = cache.get(key)
    assert retrieved2.iloc[0]["close"] != -999999.0


def test_singleton_returns_same_instance():
    """get_feature_cache() は同一インスタンスを返す."""
    c1 = get_feature_cache()
    c2 = get_feature_cache()
    assert c1 is c2

    # reset 後は新しいインスタンス
    reset_feature_cache()
    c3 = get_feature_cache()
    assert c3 is not c1

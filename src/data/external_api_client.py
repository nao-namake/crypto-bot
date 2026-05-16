"""
外部 API クライアント - Phase 89-β

無料外部 API から市場マクロ情報を取得する非同期クライアント:
- Binance Funding Rate（BTCUSDT 永続契約・8h 平均）
- Alternative.me Fear & Greed Index（0-100 整数）

設計方針:
- fail-open: API 失敗時は last-known-good または 0.0 を返し、bot を停止させない
- TTL キャッシュ: 5 分（300 秒）デフォルト・連続呼び出しの API 負荷削減
- 設定駆動: thresholds.yaml の features.external_api セクションから動的取得
"""

import asyncio
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

import aiohttp

from ..core.config.threshold_manager import get_threshold
from ..core.logger import get_logger


class ExternalAPIClient:
    """無料外部 API（Binance Funding / Alternative.me Fear&Greed）の非同期取得."""

    def __init__(
        self,
        timeout_seconds: Optional[float] = None,
        cache_ttl_seconds: Optional[int] = None,
        fallback_value: Optional[float] = None,
    ):
        """
        初期化（引数 None で thresholds.yaml から取得）.

        Args:
            timeout_seconds: HTTP リクエストタイムアウト
            cache_ttl_seconds: TTL キャッシュ秒数
            fallback_value: API 失敗時の fallback 値（last-known-good 優先・無ければこの値）
        """
        self.logger = get_logger()
        self.timeout = aiohttp.ClientTimeout(
            total=(
                timeout_seconds
                if timeout_seconds is not None
                else get_threshold("features.external_api.timeout_seconds", 5)
            )
        )
        self.cache_ttl = (
            cache_ttl_seconds
            if cache_ttl_seconds is not None
            else get_threshold("features.external_api.cache_ttl_seconds", 300)
        )
        self.fallback_value = (
            fallback_value
            if fallback_value is not None
            else get_threshold("features.external_api.fallback_on_error", 0.0)
        )
        self.binance_url = get_threshold(
            "features.external_api.binance_funding_url",
            "https://fapi.binance.com/fapi/v1/fundingRate",
        )
        self.fear_greed_url = get_threshold(
            "features.external_api.fear_greed_url", "https://api.alternative.me/fng/"
        )

        self._cache: Dict[str, Tuple[float, datetime]] = {}
        self._last_known_good: Dict[str, float] = {}
        # P1-2: dict 型キャッシュ専用ストレージ（ticker 等）。float cache との二重管理を解消。
        self._dict_cache: Dict[str, Tuple[Dict[str, Any], datetime]] = {}
        self._last_known_good_dict: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    async def fetch_funding_rate(self, symbol: str = "BTCUSDT", limit: int = 24) -> float:
        """
        Binance Funding Rate (8h 平均) を取得.

        Args:
            symbol: ペアシンボル（Binance 形式・例: "BTCUSDT"）
            limit: 取得件数（直近 N 回の funding rate を平均）

        Returns:
            funding rate（小数表現・例: 0.0001 = 0.01%/8h）。失敗時 fallback_value
        """
        cache_key = f"funding:{symbol}:{limit}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        params = {"symbol": symbol, "limit": limit}
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.binance_url, params=params) as resp:
                    if resp.status != 200:
                        self.logger.warning(f"Binance Funding Rate HTTP {resp.status} → fallback")
                        return self._fallback(cache_key)
                    data = await resp.json()

            if not isinstance(data, list) or len(data) == 0:
                self.logger.warning("Binance Funding Rate 空応答 → fallback")
                return self._fallback(cache_key)

            rates = [float(item["fundingRate"]) for item in data if "fundingRate" in item]
            if not rates:
                return self._fallback(cache_key)

            avg = sum(rates) / len(rates)
            self._put_cache(cache_key, avg)
            return avg

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            self.logger.warning(f"Binance Funding Rate 取得失敗: {e} → fallback")
            return self._fallback(cache_key)
        except (ValueError, KeyError, TypeError) as e:
            self.logger.warning(f"Binance Funding Rate 応答解析失敗: {e} → fallback")
            return self._fallback(cache_key)

    async def fetch_eth_jpy_ticker(self) -> Dict[str, float]:
        """
        Phase 89-δ: bitbank Public API から ETH/JPY ticker を取得.

        Returns:
            {"last": float, "bid": float, "ask": float, "volume": float}
            失敗時は全て 0.0 fill（fail-open）。last-known-good を優先。
        """
        # P1-2: dict 型専用キャッシュで二重管理を解消（_get_cached_dict のみで TTL + last-known-good 統一）
        cache_key = "eth_jpy_ticker"
        cached = self._get_cached_dict(cache_key)
        if cached is not None:
            return cached

        url = "https://public.bitbank.cc/eth_jpy/ticker"
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        self.logger.warning(f"bitbank ETH/JPY ticker HTTP {resp.status} → fallback")
                        return self._fallback_eth_ticker()
                    raw = await resp.json()

            if not isinstance(raw, dict) or raw.get("success") != 1:
                self.logger.warning("bitbank ETH/JPY ticker 異常応答 → fallback")
                return self._fallback_eth_ticker()

            data = raw.get("data", {})
            result = {
                "last": float(data.get("last", 0.0) or 0.0),
                "bid": float(data.get("buy", 0.0) or 0.0),
                "ask": float(data.get("sell", 0.0) or 0.0),
                "volume": float(data.get("vol", 0.0) or 0.0),
            }
            # P1-2: dict 専用キャッシュで一元化（旧二重管理を解消）
            self._put_cache_dict(cache_key, result)
            return result

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            self.logger.warning(f"bitbank ETH/JPY ticker 取得失敗: {e} → fallback")
            return self._fallback_eth_ticker()
        except (ValueError, KeyError, TypeError) as e:
            self.logger.warning(f"bitbank ETH/JPY ticker 応答解析失敗: {e} → fallback")
            return self._fallback_eth_ticker()

    def _fallback_eth_ticker(self) -> Dict[str, float]:
        """ETH ticker 取得失敗時の fallback（last-known-good 優先）.

        P1-2: _fallback_dict に統一して二重管理を解消。
        """
        return self._fallback_dict(
            "eth_jpy_ticker", {"last": 0.0, "bid": 0.0, "ask": 0.0, "volume": 0.0}
        )

    async def fetch_fear_greed_index(self) -> float:
        """
        Alternative.me Fear & Greed Index を取得.

        Returns:
            Fear & Greed Index (0-100 を 0.0-1.0 に正規化)。失敗時 fallback_value
        """
        cache_key = "fear_greed"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(self.fear_greed_url, params={"limit": 1}) as resp:
                    if resp.status != 200:
                        self.logger.warning(f"Fear & Greed HTTP {resp.status} → fallback")
                        return self._fallback(cache_key)
                    data = await resp.json()

            if not isinstance(data, dict) or "data" not in data or len(data["data"]) == 0:
                self.logger.warning("Fear & Greed 空応答 → fallback")
                return self._fallback(cache_key)

            value_str = data["data"][0].get("value", "50")
            value = float(value_str) / 100.0  # 0-100 → 0.0-1.0
            self._put_cache(cache_key, value)
            return value

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            self.logger.warning(f"Fear & Greed 取得失敗: {e} → fallback")
            return self._fallback(cache_key)
        except (ValueError, KeyError, TypeError) as e:
            self.logger.warning(f"Fear & Greed 応答解析失敗: {e} → fallback")
            return self._fallback(cache_key)

    def _get_cached(self, key: str) -> Optional[float]:
        """TTL 内のキャッシュ値を返す（無ければ None）."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if datetime.now() >= expires_at:
                del self._cache[key]
                return None
            return value

    def _put_cache(self, key: str, value: float) -> None:
        """キャッシュと last-known-good 両方に保存."""
        with self._lock:
            expires_at = datetime.now() + timedelta(seconds=self.cache_ttl)
            self._cache[key] = (value, expires_at)
            self._last_known_good[key] = value

    def _fallback(self, key: str) -> float:
        """last-known-good 優先、無ければ fallback_value."""
        with self._lock:
            return self._last_known_good.get(key, self.fallback_value)

    # P1-2: dict 型キャッシュ専用メソッド（ticker 等）
    def _get_cached_dict(self, key: str) -> Optional[Dict[str, Any]]:
        """TTL 内の dict キャッシュ値を返す（無ければ None・copy 返却）."""
        with self._lock:
            entry = self._dict_cache.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if datetime.now() >= expires_at:
                del self._dict_cache[key]
                return None
            return dict(value)

    def _put_cache_dict(self, key: str, value: Dict[str, Any]) -> None:
        """dict キャッシュと last-known-good 両方に保存."""
        with self._lock:
            expires_at = datetime.now() + timedelta(seconds=self.cache_ttl)
            self._dict_cache[key] = (dict(value), expires_at)
            self._last_known_good_dict[key] = dict(value)

    def _fallback_dict(self, key: str, default: Dict[str, Any]) -> Dict[str, Any]:
        """last-known-good dict 優先、無ければ default 返却."""
        with self._lock:
            return dict(self._last_known_good_dict.get(key, default))

    def clear_cache(self) -> None:
        """テスト用: キャッシュ・last-known-good を初期化."""
        with self._lock:
            self._cache.clear()
            self._last_known_good.clear()
            self._dict_cache.clear()
            self._last_known_good_dict.clear()


_external_api_client: Optional[ExternalAPIClient] = None
_singleton_lock = threading.Lock()


def get_external_api_client() -> ExternalAPIClient:
    """シングルトン取得."""
    global _external_api_client
    if _external_api_client is None:
        with _singleton_lock:
            if _external_api_client is None:
                _external_api_client = ExternalAPIClient()
    return _external_api_client


def reset_external_api_client() -> None:
    """テスト用: シングルトン再生成."""
    global _external_api_client
    with _singleton_lock:
        _external_api_client = None

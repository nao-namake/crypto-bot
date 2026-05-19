"""
ExternalAPIClient テスト - Phase 89-β

src/data/external_api_client.py の包括テスト 10 件。
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from src.data.external_api_client import (
    ExternalAPIClient,
    get_external_api_client,
    reset_external_api_client,
)


@pytest.fixture(autouse=True)
def _reset_singleton():
    reset_external_api_client()
    yield
    reset_external_api_client()


def _mock_response(status: int, json_data):
    """aiohttp.ClientSession.get の context manager をモック."""
    resp = AsyncMock()
    resp.status = status
    resp.json = AsyncMock(return_value=json_data)
    resp.__aenter__ = AsyncMock(return_value=resp)
    resp.__aexit__ = AsyncMock(return_value=None)
    return resp


@pytest.mark.asyncio
async def test_fetch_funding_rate_success():
    """Binance Funding Rate 正常取得（平均値計算）."""
    client = ExternalAPIClient(timeout_seconds=5, cache_ttl_seconds=300, fallback_value=0.0)
    sample = [
        {"fundingRate": "0.0001"},
        {"fundingRate": "0.0002"},
        {"fundingRate": "0.0003"},
    ]

    with patch("aiohttp.ClientSession") as mock_session_cls:
        session = AsyncMock()
        session.get = MagicMock(return_value=_mock_response(200, sample))
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = session

        rate = await client.fetch_funding_rate(symbol="BTCUSDT", limit=3)

    assert rate == pytest.approx(0.0002, abs=1e-6)


@pytest.mark.asyncio
async def test_fetch_funding_rate_http_error_returns_fallback():
    """HTTP 500 で fallback_value を返す."""
    client = ExternalAPIClient(timeout_seconds=5, cache_ttl_seconds=300, fallback_value=-99.0)
    with patch("aiohttp.ClientSession") as mock_session_cls:
        session = AsyncMock()
        session.get = MagicMock(return_value=_mock_response(500, None))
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = session

        rate = await client.fetch_funding_rate()

    assert rate == -99.0


@pytest.mark.asyncio
async def test_fetch_funding_rate_timeout_returns_fallback():
    """asyncio.TimeoutError で fallback_value を返す."""
    client = ExternalAPIClient(timeout_seconds=5, cache_ttl_seconds=300, fallback_value=0.0)

    async def _raise_timeout(*args, **kwargs):
        raise asyncio.TimeoutError()

    with patch("aiohttp.ClientSession") as mock_session_cls:
        session = AsyncMock()
        session.get = MagicMock(side_effect=asyncio.TimeoutError())
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = session

        rate = await client.fetch_funding_rate()

    assert rate == 0.0


@pytest.mark.asyncio
async def test_fetch_funding_rate_invalid_json_returns_fallback():
    """空応答で fallback_value を返す."""
    client = ExternalAPIClient(timeout_seconds=5, cache_ttl_seconds=300, fallback_value=0.0)
    with patch("aiohttp.ClientSession") as mock_session_cls:
        session = AsyncMock()
        session.get = MagicMock(return_value=_mock_response(200, []))
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = session

        rate = await client.fetch_funding_rate()

    assert rate == 0.0


@pytest.mark.asyncio
async def test_fetch_fear_greed_success():
    """Fear & Greed 正常取得（0-100 → 0.0-1.0 正規化）."""
    client = ExternalAPIClient(timeout_seconds=5, cache_ttl_seconds=300, fallback_value=0.0)
    sample = {"data": [{"value": "75"}]}

    with patch("aiohttp.ClientSession") as mock_session_cls:
        session = AsyncMock()
        session.get = MagicMock(return_value=_mock_response(200, sample))
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = session

        value = await client.fetch_fear_greed_index()

    assert value == pytest.approx(0.75, abs=1e-6)


@pytest.mark.asyncio
async def test_fetch_fear_greed_malformed_json():
    """不正 JSON 形式で fallback_value を返す."""
    client = ExternalAPIClient(timeout_seconds=5, cache_ttl_seconds=300, fallback_value=0.0)
    sample = {"unexpected": "format"}

    with patch("aiohttp.ClientSession") as mock_session_cls:
        session = AsyncMock()
        session.get = MagicMock(return_value=_mock_response(200, sample))
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = session

        value = await client.fetch_fear_greed_index()

    assert value == 0.0


@pytest.mark.asyncio
async def test_cache_hit_skips_http_call():
    """キャッシュヒット時は HTTP リクエストを発行しない."""
    client = ExternalAPIClient(timeout_seconds=5, cache_ttl_seconds=300, fallback_value=0.0)
    sample = [{"fundingRate": "0.0005"}]

    with patch("aiohttp.ClientSession") as mock_session_cls:
        session = AsyncMock()
        session.get = MagicMock(return_value=_mock_response(200, sample))
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = session

        r1 = await client.fetch_funding_rate(symbol="BTCUSDT", limit=1)
        r2 = await client.fetch_funding_rate(symbol="BTCUSDT", limit=1)

    assert r1 == r2 == pytest.approx(0.0005, abs=1e-6)
    # ClientSession は 1 度しか作られない（2 回目はキャッシュ）
    assert mock_session_cls.call_count == 1


@pytest.mark.asyncio
async def test_cache_ttl_expiration_refetches():
    """TTL 経過後は再取得される."""
    client = ExternalAPIClient(timeout_seconds=5, cache_ttl_seconds=300, fallback_value=0.0)
    # 直接 cache に古いエントリを入れる
    past = datetime.now() - timedelta(seconds=10)
    client._cache["funding:BTCUSDT:24"] = (0.999, past)

    sample = [{"fundingRate": "0.0007"}]
    with patch("aiohttp.ClientSession") as mock_session_cls:
        session = AsyncMock()
        session.get = MagicMock(return_value=_mock_response(200, sample))
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = session

        rate = await client.fetch_funding_rate()

    # 古いキャッシュは expired と判定され再取得
    assert rate == pytest.approx(0.0007, abs=1e-6)


@pytest.mark.asyncio
async def test_fallback_uses_last_known_good_when_available():
    """API 失敗時、過去成功値があれば last-known-good を返す."""
    client = ExternalAPIClient(timeout_seconds=5, cache_ttl_seconds=300, fallback_value=-1.0)
    # 過去成功値を仕込む
    client._last_known_good["fear_greed"] = 0.42

    with patch("aiohttp.ClientSession") as mock_session_cls:
        session = AsyncMock()
        session.get = MagicMock(return_value=_mock_response(503, None))
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = session

        value = await client.fetch_fear_greed_index()

    # fallback_value(-1.0) ではなく last-known-good (0.42) が返る
    assert value == pytest.approx(0.42, abs=1e-6)


def test_singleton_pattern():
    """get_external_api_client() は同一インスタンスを返す."""
    c1 = get_external_api_client()
    c2 = get_external_api_client()
    assert c1 is c2

    reset_external_api_client()
    c3 = get_external_api_client()
    assert c3 is not c1

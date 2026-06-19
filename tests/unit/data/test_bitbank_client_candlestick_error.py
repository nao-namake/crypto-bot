"""Phase 90σ: bitbank candlestick API のエラー応答ログレベル是正のテスト。

bitbank の candlestick API が success!=1（例: code 10000＝当日分の日次ファイル未生成）を
返すと _fetch_candlestick_direct は DataFetchError を送出する。これは「予期された API
エラー」であり、日次バルク取得の呼び出し元が WARNING + continue でカバーする。

旧実装では同一 try 内の `except Exception` がこの DataFetchError を再キャッチして
「❌ {label}取得予期しないエラー」を ERROR で出力していたため、毎日 00:00 UTC（当日分要求）に
実害のない ERROR が 1 件出続けていた。Phase 90σ で `except DataFetchError: raise` を
追加し、予期された API エラーは ERROR 化せず素通しする。

本テストは:
- API エラー応答（success!=1）は DataFetchError を送出しつつ "予期しないエラー" ERROR を
  出さないこと
- 真に予期しない例外（不正 JSON）は従来どおり "予期しないエラー" ERROR を出すこと
を担保する（リグレッション防止）。
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exceptions import DataFetchError
from src.data.bitbank_client import BitbankClient


def _make_client():
    """__init__ をバイパスし、_fetch_candlestick_direct に必要な属性のみ持つ client を生成。"""
    client = BitbankClient.__new__(BitbankClient)
    client.api_key = "test_key"
    client.api_secret = "test_secret"
    client.leverage = 1.0
    client.logger = MagicMock()
    return client


def _patch_session(response_text: str):
    """aiohttp.ClientSession を、固定テキストを返す response でモックするパッチを返す。"""
    mock_response = MagicMock()
    mock_response.headers = {}
    mock_response.text = AsyncMock(return_value=response_text)

    mock_get_ctx = MagicMock()
    mock_get_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_get_ctx.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_get_ctx)

    mock_session_ctx = MagicMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=False)

    return patch("aiohttp.ClientSession", return_value=mock_session_ctx)


def _error_logged_unexpected(logger: MagicMock) -> bool:
    """logger.error が「予期しないエラー」で呼ばれたか。"""
    return any(
        "予期しないエラー" in str(call.args[0]) for call in logger.error.call_args_list if call.args
    )


class TestPhase90SigmaCandlestickErrorLogging:
    """Phase 90σ: candlestick API エラー応答のログレベル是正。"""

    @pytest.mark.asyncio
    async def test_api_error_response_not_logged_as_unexpected(self):
        """success!=1（code 10000）は DataFetchError を送出するが ERROR『予期しないエラー』を出さない。"""
        client = _make_client()
        body = json.dumps({"success": 0, "data": {"code": 10000}})

        with _patch_session(body):
            with pytest.raises(DataFetchError):
                await client._fetch_candlestick_direct(
                    symbol="BTC/JPY",
                    period="15min",
                    param="20260620",
                    label="15分足",
                )

        # 予期された API エラーなので「予期しないエラー」ERROR は出さない（ノイズ抑止）
        assert not _error_logged_unexpected(client.logger)

    @pytest.mark.asyncio
    async def test_truly_unexpected_error_still_logged(self):
        """不正 JSON 等の真に予期しない例外は従来どおり ERROR『予期しないエラー』を出す。"""
        client = _make_client()

        with _patch_session("this is not json"):
            with pytest.raises(DataFetchError):
                await client._fetch_candlestick_direct(
                    symbol="BTC/JPY",
                    period="15min",
                    param="20260620",
                    label="15分足",
                )

        # 真の異常は握り潰さず ERROR で可視化する（既存挙動維持）
        assert _error_logged_unexpected(client.logger)

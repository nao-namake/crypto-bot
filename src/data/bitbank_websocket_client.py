"""
Phase 89-δ: bitbank Public WebSocket クライアント

bitbank の Public Stream API (Socket.IO over WebSocket) から ticker / orderbook diff を
リアルタイム受信し、in-memory キャッシュに保持する。

設計:
- ccxtpro は商用ライセンスのため不採用。`websockets>=12.0` で独自実装
- Socket.IO のバージョン: EIO=3 (bitbank 公式仕様準拠)
- subscribe channels: `ticker_btc_jpy` / `depth_diff_btc_jpy`
- reconnect on close: exponential backoff (1s, 2s, 4s, ..., 最大 30s)
- fail-open: 接続失敗時は REST に fallback（bitbank_client が判定）

URL:
- wss://stream.bitbank.cc/socket.io/?EIO=3&transport=websocket

メッセージプロトコル（Socket.IO EIO=3 簡略実装）:
- 接続後: `0{...}` (handshake) を受信
- subscribe: `42["join-room","ticker_btc_jpy"]` を送信
- 受信: `42["message",{...}]` 形式
"""

from __future__ import annotations

import asyncio
import json
import threading
from datetime import datetime
from typing import Any, Callable, Dict, Optional

try:
    import websockets
    from websockets.exceptions import ConnectionClosed, InvalidStatusCode

    _HAS_WEBSOCKETS = True
except ImportError:  # pragma: no cover
    websockets = None  # type: ignore
    ConnectionClosed = Exception  # type: ignore
    InvalidStatusCode = Exception  # type: ignore
    _HAS_WEBSOCKETS = False

from ..core.config.threshold_manager import get_threshold
from ..core.logger import get_logger


def has_websockets() -> bool:
    return _HAS_WEBSOCKETS


class BitbankWebSocketClient:
    """bitbank Public Stream への WebSocket 接続クライアント."""

    DEFAULT_URL = "wss://stream.bitbank.cc/socket.io/?EIO=3&transport=websocket"
    DEFAULT_CHANNELS = ["ticker_btc_jpy", "depth_diff_btc_jpy"]
    MAX_BACKOFF_SECONDS = 30
    INITIAL_BACKOFF_SECONDS = 1.0

    def __init__(
        self,
        url: Optional[str] = None,
        channels: Optional[list] = None,
    ) -> None:
        if not _HAS_WEBSOCKETS:
            raise ImportError("websockets is required. Install: pip install websockets>=12.0")
        self.logger = get_logger()
        self.url = url or get_threshold("data.websocket.bitbank_url", self.DEFAULT_URL)
        self.channels = list(channels or self.DEFAULT_CHANNELS)

        # in-memory cache（最新値のみ保持・スレッドセーフ）
        self._lock = threading.RLock()
        self._ticker_cache: Dict[str, Dict[str, Any]] = {}
        self._orderbook_cache: Dict[str, Dict[str, Any]] = {}
        self._last_message_at: Optional[datetime] = None
        self._is_connected: bool = False
        self._stop_requested: bool = False
        self._task: Optional[asyncio.Task] = None

    # ========================================
    # Public API
    # ========================================

    async def connect(self) -> None:
        """WebSocket 接続を開始（reconnect ループ付き）.

        非同期で常駐するコルーチン。`disconnect()` で停止可能。
        """
        self._stop_requested = False
        backoff = self.INITIAL_BACKOFF_SECONDS

        while not self._stop_requested:
            try:
                await self._run_session()
                # 正常切断（stop_requested = True 時）
                if self._stop_requested:
                    break
            except (ConnectionClosed, InvalidStatusCode, OSError) as e:
                self.logger.warning(f"Phase 89-δ WebSocket 切断 → reconnect in {backoff:.1f}s: {e}")
            except Exception as e:
                self.logger.warning(
                    f"Phase 89-δ WebSocket 予期せぬエラー → reconnect in {backoff:.1f}s: {e}"
                )
            finally:
                with self._lock:
                    self._is_connected = False

            if self._stop_requested:
                break

            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, self.MAX_BACKOFF_SECONDS)

    async def disconnect(self) -> None:
        """接続停止."""
        self._stop_requested = True
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass

    def is_connected(self) -> bool:
        with self._lock:
            return self._is_connected

    def get_ticker(self, symbol: str = "btc_jpy") -> Optional[Dict[str, Any]]:
        """最新 ticker をキャッシュから取得（無ければ None）."""
        with self._lock:
            data = self._ticker_cache.get(symbol)
            return dict(data) if data else None

    def get_orderbook_diff(self, symbol: str = "btc_jpy") -> Optional[Dict[str, Any]]:
        """最新 orderbook diff をキャッシュから取得（無ければ None）."""
        with self._lock:
            data = self._orderbook_cache.get(symbol)
            return dict(data) if data else None

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "is_connected": self._is_connected,
                "last_message_at": (
                    self._last_message_at.isoformat() if self._last_message_at else None
                ),
                "subscribed_channels": list(self.channels),
                "ticker_symbols": list(self._ticker_cache.keys()),
                "orderbook_symbols": list(self._orderbook_cache.keys()),
            }

    # ========================================
    # Internal
    # ========================================

    async def _run_session(self) -> None:
        """単一 WebSocket セッション（接続 → subscribe → メッセージループ）."""
        async with websockets.connect(
            self.url,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=5,
        ) as ws:
            with self._lock:
                self._is_connected = True
            self.logger.info(f"Phase 89-δ WebSocket 接続: {self.url}")

            # subscribe channels（Socket.IO EIO=3 形式）
            for channel in self.channels:
                msg = f'42["join-room","{channel}"]'
                await ws.send(msg)
                self.logger.debug(f"Phase 89-δ subscribe: {channel}")

            # メッセージ受信ループ
            async for raw_message in ws:
                if self._stop_requested:
                    break
                try:
                    self._process_message(raw_message)
                except Exception as e:
                    self.logger.warning(f"Phase 89-δ メッセージ処理失敗（スキップ）: {e}")

    def _process_message(self, raw: Any) -> None:
        """Socket.IO 形式のメッセージを解析しキャッシュ更新."""
        if isinstance(raw, bytes):
            try:
                raw = raw.decode("utf-8")
            except UnicodeDecodeError:
                return
        if not isinstance(raw, str):
            return

        with self._lock:
            self._last_message_at = datetime.now()

        # Socket.IO EIO=3 のメッセージは "42[...]" 形式
        if not raw.startswith("42"):
            return  # heartbeat (3) や handshake (0/40) は無視

        payload_str = raw[2:]
        try:
            payload = json.loads(payload_str)
        except json.JSONDecodeError:
            return

        if not isinstance(payload, list) or len(payload) < 2:
            return

        event_name = payload[0]
        event_data = payload[1]
        if event_name != "message" or not isinstance(event_data, dict):
            return

        room_name = event_data.get("room_name", "")
        message = event_data.get("message", {})
        data = message.get("data", {}) if isinstance(message, dict) else {}
        if not isinstance(data, dict):
            return

        # ticker 系
        if room_name.startswith("ticker_"):
            symbol = room_name.replace("ticker_", "")
            with self._lock:
                self._ticker_cache[symbol] = data
        # orderbook diff 系
        elif room_name.startswith("depth_diff_"):
            symbol = room_name.replace("depth_diff_", "")
            with self._lock:
                self._orderbook_cache[symbol] = data


_ws_client: Optional[BitbankWebSocketClient] = None
_singleton_lock = threading.Lock()


def get_bitbank_websocket_client() -> BitbankWebSocketClient:
    """シングルトン取得."""
    global _ws_client
    if _ws_client is None:
        with _singleton_lock:
            if _ws_client is None:
                _ws_client = BitbankWebSocketClient()
    return _ws_client


def reset_bitbank_websocket_client() -> None:
    """テスト用: シングルトン再生成."""
    global _ws_client
    with _singleton_lock:
        _ws_client = None

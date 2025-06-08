# crypto_bot/utils/status.py  ← 新規ファイル
import json
from datetime import datetime
from pathlib import Path
from threading import Lock

_STATUS_PATH = Path("status.json")
_LOCK = Lock()  # 同時書き込み防止（マルチスレッドでも安全）


def update_status(
    total_profit: float,
    trade_count: int,
    position: str | None,
    bot_state: str = "running",
) -> None:
    """Bot の現在状況を status.json に保存する。

    Parameters
    ----------
    total_profit : float
        累積損益（円など好きな単位）
    trade_count : int
        取引回数
    position : str | None
        現在保有しているポジション（例: 'LONG', 'SHORT', None）
    bot_state : str
        Bot の稼働ステート ('running' / 'stopped' / 'error' など)
    """
    payload = {
        "last_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "total_profit": total_profit,
        "trade_count": trade_count,
        "position": position or "",
        "state": bot_state,
    }
    with _LOCK:
        _STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2))

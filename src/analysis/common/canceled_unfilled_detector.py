"""Phase 87 Stage 3 + C1: GCPログから CANCELED_UNFILLED 検出

Phase 87 C1 (SLMonitor) は本番で CANCELED_UNFILLED を検出すると critical ログに
「Phase 87 C1: SL異常検出」「Phase 87 C1: 緊急成行決済発動」を出力する。
本モジュールは事後分析（standard_analysis.py）でこれらのログを集計する。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, List, Optional


@dataclass
class CanceledUnfilledEvent:
    """1件の CANCELED_UNFILLED 検出イベント"""

    timestamp: Optional[str]
    sl_order_id: Optional[str]
    failure_reason: (
        str  # "canceled_unfilled" / "expired" / "rejected" / "timeout_24h" / "not_found"
    )
    emergency_close_executed: bool  # 緊急成行決済が実行されたか（dry_run でなければ True）
    dry_run: bool  # dry_run モードでログだけだったか
    raw_log: Optional[str] = None  # 元ログテキスト（デバッグ用）


def detect_canceled_unfilled(
    gcp_logs: Iterable[Any],
) -> List[CanceledUnfilledEvent]:
    """GCP ログイテレータから Phase 87 C1 イベントを抽出する。

    対象パターン:
        - "Phase 87 C1: SL異常検出 - reason=..." (C5 経路)
        - "Phase 87 C1: 緊急成行決済発動 (reason=...)"
        - "Phase 87 C1 [DRY_RUN]: 緊急成行決済シミュレーション ..."
        - "Phase 87 H1: SL 24h超過検出 ..." (timeout_24h 系)

    Args:
        gcp_logs: 各要素が dict (gcloud logging read --format=json) or str (テキストログ)

    Returns:
        List[CanceledUnfilledEvent]: 検出されたイベント
    """
    events: List[CanceledUnfilledEvent] = []
    for entry in gcp_logs or []:
        text = _extract_text(entry)
        if not text:
            continue
        timestamp = _extract_timestamp(entry)

        # CANCELED_UNFILLED / EXPIRED / REJECTED 検出（C5 経路）
        if "Phase 87 C5: SL異常検出" in text or "Phase 87 C1: SL異常検出" in text:
            reason = _extract_field(text, "reason=", ",")
            sl_id = _extract_field(text, "sl_order_id=", "")
            events.append(
                CanceledUnfilledEvent(
                    timestamp=timestamp,
                    sl_order_id=sl_id,
                    failure_reason=reason or "unknown",
                    emergency_close_executed=False,  # ここでは検出だけ、決済は別ログ
                    dry_run=False,
                    raw_log=text,
                )
            )
            continue

        # 緊急成行決済発動（実行された）
        if "Phase 87 C1: 緊急成行決済発動" in text:
            reason = _extract_field(text, "reason=", ",")
            events.append(
                CanceledUnfilledEvent(
                    timestamp=timestamp,
                    sl_order_id=None,
                    failure_reason=reason or "emergency_close",
                    emergency_close_executed=True,
                    dry_run=False,
                    raw_log=text,
                )
            )
            continue

        # dry_run シミュレーション
        if "Phase 87 C1 [DRY_RUN]" in text:
            reason = _extract_field(text, "reason=", ",")
            events.append(
                CanceledUnfilledEvent(
                    timestamp=timestamp,
                    sl_order_id=None,
                    failure_reason=reason or "dry_run",
                    emergency_close_executed=False,
                    dry_run=True,
                    raw_log=text,
                )
            )
            continue

        # 24h タイムアウト (H1)
        if "Phase 87 H1: SL 24h超過検出" in text:
            events.append(
                CanceledUnfilledEvent(
                    timestamp=timestamp,
                    sl_order_id=None,
                    failure_reason="timeout_24h",
                    emergency_close_executed=False,
                    dry_run=False,
                    raw_log=text,
                )
            )

    return events


def _extract_text(entry: Any) -> str:
    """log entry (dict or str) からテキストを抽出"""
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        return (
            entry.get("textPayload")
            or entry.get("jsonPayload", {}).get("message")
            or entry.get("message")
            or ""
        )
    return ""


def _extract_timestamp(entry: Any) -> Optional[str]:
    if isinstance(entry, dict):
        return entry.get("timestamp")
    return None


def _extract_field(text: str, key: str, terminator: str) -> Optional[str]:
    """text 内の `key<value><terminator>` を抽出。`)` 終端も許容。"""
    idx = text.find(key)
    if idx == -1:
        return None
    start = idx + len(key)
    # terminator 候補で最も近いものまで
    candidates = [terminator, ")", " ", "\n"]
    end_positions = [text.find(c, start) for c in candidates if c]
    end_positions = [p for p in end_positions if p != -1]
    end = min(end_positions) if end_positions else len(text)
    return text[start:end].strip()

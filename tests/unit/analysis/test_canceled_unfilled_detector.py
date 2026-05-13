"""Phase 87 Stage 3: detect_canceled_unfilled テスト"""

from src.analysis.common.canceled_unfilled_detector import (
    CanceledUnfilledEvent,
    detect_canceled_unfilled,
)


class TestDetectCanceledUnfilled:
    def test_empty_logs_returns_empty(self):
        assert detect_canceled_unfilled([]) == []

    def test_c5_sl_anomaly_detected(self):
        logs = [
            "🚨 Phase 87 C5: SL異常検出 - reason=canceled_unfilled, "
            "side=buy, amount=0.015 BTC, sl_order_id=ABC123"
        ]
        events = detect_canceled_unfilled(logs)
        assert len(events) == 1
        assert events[0].failure_reason == "canceled_unfilled"
        assert events[0].sl_order_id == "ABC123"
        assert events[0].emergency_close_executed is False
        assert events[0].dry_run is False

    def test_c1_emergency_close_detected(self):
        logs = [
            "🚨 Phase 87 C1: 緊急成行決済発動 (reason=canceled_unfilled, "
            "exit_side=sell, amount=0.015 BTC)"
        ]
        events = detect_canceled_unfilled(logs)
        assert len(events) == 1
        assert events[0].emergency_close_executed is True
        assert events[0].dry_run is False
        assert "canceled_unfilled" in events[0].failure_reason

    def test_dry_run_detected(self):
        logs = [
            "🧪 Phase 87 C1 [DRY_RUN]: 緊急成行決済シミュレーション "
            "(reason=expired, exit_side=sell, amount=0.015 BTC) - 実発注なし"
        ]
        events = detect_canceled_unfilled(logs)
        assert len(events) == 1
        assert events[0].dry_run is True
        assert events[0].emergency_close_executed is False

    def test_h1_timeout_detected(self):
        logs = [
            "🚨 Phase 87 H1: SL 24h超過検出 - side=buy, amount=0.015 BTC, "
            "sl_placed_at=2026-05-13T05:00:00+00:00"
        ]
        events = detect_canceled_unfilled(logs)
        assert len(events) == 1
        assert events[0].failure_reason == "timeout_24h"

    def test_irrelevant_logs_ignored(self):
        logs = [
            "INFO: 通常ログ",
            "DEBUG: 別のデバッグログ",
            "WARN: 関係ない警告",
        ]
        assert detect_canceled_unfilled(logs) == []

    def test_dict_log_entry_with_textPayload(self):
        logs = [
            {
                "timestamp": "2026-05-14T05:00:00Z",
                "textPayload": "🚨 Phase 87 C5: SL異常検出 - reason=expired, sl_order_id=XYZ",
            }
        ]
        events = detect_canceled_unfilled(logs)
        assert len(events) == 1
        assert events[0].timestamp == "2026-05-14T05:00:00Z"
        assert events[0].failure_reason == "expired"

    def test_multiple_events(self):
        logs = [
            "🚨 Phase 87 C5: SL異常検出 - reason=canceled_unfilled, sl_order_id=A",
            "🚨 Phase 87 C1: 緊急成行決済発動 (reason=canceled_unfilled)",
            "🚨 Phase 87 H1: SL 24h超過検出 - side=buy",
        ]
        events = detect_canceled_unfilled(logs)
        assert len(events) == 3
        assert events[0].emergency_close_executed is False
        assert events[1].emergency_close_executed is True
        assert events[2].failure_reason == "timeout_24h"

    def test_none_logs_returns_empty(self):
        """None 入力でクラッシュしない"""
        assert detect_canceled_unfilled(None) == []

    def test_dict_without_text_ignored(self):
        """text payload がない dict ログは無視"""
        logs = [{"timestamp": "2026-05-14T05:00:00Z"}]
        assert detect_canceled_unfilled(logs) == []

    def test_malformed_log_with_no_reason_field(self):
        """reason= 等のフィールドが欠落していても crash しない"""
        logs = ["🚨 Phase 87 C5: SL異常検出"]
        events = detect_canceled_unfilled(logs)
        assert len(events) == 1
        # reason は extract できないため "unknown" fallback
        assert events[0].failure_reason == "unknown"

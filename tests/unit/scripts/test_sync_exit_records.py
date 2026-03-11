"""
Phase 68.6: sync_exit_records.py テスト

GCPログからexit記録をパースする機能のテスト。
"""

import importlib.util
from pathlib import Path

_module_path = (
    Path(__file__).parent.parent.parent.parent / "scripts" / "live" / "sync_exit_records.py"
)
_spec = importlib.util.spec_from_file_location("sync_exit_records", _module_path)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

EXIT_RECORD_PATTERN = _mod.EXIT_RECORD_PATTERN
SL_DETECT_PATTERN = _mod.SL_DETECT_PATTERN
TP_DETECT_PATTERN = _mod.TP_DETECT_PATTERN
parse_exit_records = _mod.parse_exit_records


class TestLogPatternMatching:
    """ログパターンマッチングテスト"""

    def test_tp_detect_pattern(self):
        text = "🎯 Phase 61.9: TP自動執行検知 - SELL 0.010000 BTC @ 11087842円 (利益: +500円) 戦略: unknown"
        match = TP_DETECT_PATTERN.search(text)
        assert match is not None
        assert match.group(1) == "SELL"
        assert match.group(2) == "0.010000"
        assert match.group(3) == "11087842"
        assert match.group(4) == "500"
        assert match.group(5) == "unknown"

    def test_sl_detect_pattern(self):
        text = "🛑 Phase 61.9: SL自動執行検知 - BUY 0.020000 BTC @ 10811214円 (損失: -1009円) 戦略: unknown"
        match = SL_DETECT_PATTERN.search(text)
        assert match is not None
        assert match.group(1) == "BUY"
        assert match.group(2) == "0.020000"
        assert match.group(3) == "10811214"
        assert match.group(4) == "-1009"
        assert match.group(5) == "unknown"

    def test_exit_record_pattern(self):
        text = "📝 Phase 62.18: exit記録追加 - type=tp, pnl=500円, strategy=unknown"
        match = EXIT_RECORD_PATTERN.search(text)
        assert match is not None
        assert match.group(1) == "tp"
        assert match.group(2) == "500"
        assert match.group(3) == "unknown"


class TestParseExitRecords:
    """parse_exit_records テスト"""

    def test_parse_tp_execution(self):
        logs = [
            {
                "textPayload": "🎯 Phase 61.9: TP自動執行検知 - SELL 0.010000 BTC @ 11087842円 (利益: +500円) 戦略: ATRBased",
                "timestamp": "2026-03-10T12:00:00Z",
            }
        ]
        records = parse_exit_records(logs)
        assert len(records) == 1
        assert records[0]["trade_type"] == "tp"
        assert records[0]["side"] == "sell"
        assert records[0]["amount"] == 0.01
        assert records[0]["price"] == 11087842.0
        assert records[0]["pnl"] == 500.0

    def test_parse_sl_execution(self):
        logs = [
            {
                "textPayload": "🛑 Phase 61.9: SL自動執行検知 - BUY 0.020000 BTC @ 10811214円 (損失: -1009円) 戦略: unknown",
                "timestamp": "2026-03-10T13:00:00Z",
            }
        ]
        records = parse_exit_records(logs)
        assert len(records) == 1
        assert records[0]["trade_type"] == "sl"
        assert records[0]["pnl"] == -1009.0

    def test_dedup_same_timestamp_and_type(self):
        logs = [
            {
                "textPayload": "🎯 Phase 61.9: TP自動執行検知 - SELL 0.010000 BTC @ 11087842円 (利益: +500円) 戦略: unknown",
                "timestamp": "2026-03-10T12:00:00.123Z",
            },
            {
                "textPayload": "🎯 Phase 61.9: TP自動執行検知 - SELL 0.010000 BTC @ 11087842円 (利益: +500円) 戦略: unknown",
                "timestamp": "2026-03-10T12:00:00.456Z",
            },
        ]
        records = parse_exit_records(logs)
        assert len(records) == 1

    def test_fallback_exit_record(self):
        logs = [
            {
                "textPayload": "📝 Phase 62.18: exit記録追加 - type=sl, pnl=-700円, strategy=BBReversal",
                "timestamp": "2026-03-10T14:00:00Z",
            }
        ]
        records = parse_exit_records(logs)
        assert len(records) == 1
        assert records[0]["trade_type"] == "sl"
        assert records[0]["pnl"] == -700.0
        assert records[0]["side"] == "unknown"

    def test_empty_logs(self):
        records = parse_exit_records([])
        assert len(records) == 0

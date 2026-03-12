"""
Phase 68.6→68.8: sync_exit_records.py テスト

GCPログからexit記録をパースする機能のテスト。
Phase 68.8: PnL二重計上修正（2パス方式・分単位重複チェック・DBクリーンアップ）
"""

import importlib.util
import sqlite3
import tempfile
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
cleanup_duplicates = _mod.cleanup_duplicates
sync_to_local_db = _mod.sync_to_local_db


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

    def test_phase688_duplicate_elimination(self):
        """Phase 68.8: 同一決済の2ログ（Phase 61.9 + Phase 62.18）で重複排除"""
        logs = [
            {
                "textPayload": "🎯 Phase 61.9: TP自動執行検知 - SELL 0.010000 BTC @ 11087842円 (利益: +500円) 戦略: unknown",
                "timestamp": "2026-03-10T12:00:05.123Z",
            },
            {
                "textPayload": "📝 Phase 62.18: exit記録追加 - type=tp, pnl=500円, strategy=unknown",
                "timestamp": "2026-03-10T12:00:08.456Z",
            },
        ]
        records = parse_exit_records(logs)
        assert len(records) == 1
        assert records[0]["side"] == "sell"  # Phase 61.9の詳細レコードが優先

    def test_phase688_fallback_only_when_no_detail(self):
        """Phase 68.8: Phase 61.9がない分のPhase 62.18はフォールバックとして残る"""
        logs = [
            {
                "textPayload": "🎯 Phase 61.9: TP自動執行検知 - SELL 0.010000 BTC @ 11087842円 (利益: +500円) 戦略: unknown",
                "timestamp": "2026-03-10T12:00:05Z",
            },
            {
                "textPayload": "📝 Phase 62.18: exit記録追加 - type=sl, pnl=-400円, strategy=ATRBased",
                "timestamp": "2026-03-10T13:00:08Z",
            },
        ]
        records = parse_exit_records(logs)
        assert len(records) == 2

    def test_phase688_minute_level_dedup(self):
        """Phase 68.8: 秒が異なっても同分なら重複排除"""
        logs = [
            {
                "textPayload": "🎯 Phase 61.9: TP自動執行検知 - SELL 0.010000 BTC @ 11087842円 (利益: +500円) 戦略: unknown",
                "timestamp": "2026-03-10T12:05:01Z",
            },
            {
                "textPayload": "📝 Phase 62.18: exit記録追加 - type=tp, pnl=500円, strategy=unknown",
                "timestamp": "2026-03-10T12:05:30Z",
            },
        ]
        records = parse_exit_records(logs)
        assert len(records) == 1
        assert records[0]["side"] == "sell"


class TestCleanupDuplicates:
    """Phase 68.8: DBクリーンアップテスト"""

    def _create_test_db(self, records):
        """テスト用DBを作成してパスを返す"""
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        conn = sqlite3.connect(tmp.name)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                trade_type TEXT NOT NULL,
                side TEXT NOT NULL,
                amount REAL NOT NULL,
                price REAL NOT NULL,
                fee REAL,
                pnl REAL,
                order_id TEXT,
                notes TEXT,
                slippage REAL,
                expected_price REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        for r in records:
            cursor.execute(
                "INSERT INTO trades (timestamp, trade_type, side, amount, price, pnl, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    r["timestamp"],
                    r["trade_type"],
                    r["side"],
                    r["amount"],
                    r["price"],
                    r["pnl"],
                    r.get("notes", ""),
                ),
            )
        conn.commit()
        conn.close()
        return tmp.name

    def test_cleanup_removes_unknown_duplicates(self):
        """side=unknownが同分のside!=unknownで削除されること"""
        db_path = self._create_test_db(
            [
                {
                    "timestamp": "2026-03-10T12:00:05Z",
                    "trade_type": "tp",
                    "side": "sell",
                    "amount": 0.01,
                    "price": 11087842,
                    "pnl": 500,
                },
                {
                    "timestamp": "2026-03-10T12:00:08Z",
                    "trade_type": "tp",
                    "side": "unknown",
                    "amount": 0,
                    "price": 0,
                    "pnl": 500,
                },
            ]
        )
        deleted = cleanup_duplicates(db_path)
        assert deleted == 1

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM trades")
        assert cursor.fetchone()[0] == 1
        cursor.execute("SELECT side FROM trades")
        assert cursor.fetchone()[0] == "sell"
        conn.close()
        Path(db_path).unlink()

    def test_cleanup_keeps_unique_unknown(self):
        """対応するside!=unknownがなければunknownは残す"""
        db_path = self._create_test_db(
            [
                {
                    "timestamp": "2026-03-10T12:00:05Z",
                    "trade_type": "tp",
                    "side": "sell",
                    "amount": 0.01,
                    "price": 11087842,
                    "pnl": 500,
                },
                {
                    "timestamp": "2026-03-10T13:00:08Z",
                    "trade_type": "sl",
                    "side": "unknown",
                    "amount": 0,
                    "price": 0,
                    "pnl": -400,
                },
            ]
        )
        deleted = cleanup_duplicates(db_path)
        assert deleted == 0

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM trades")
        assert cursor.fetchone()[0] == 2
        conn.close()
        Path(db_path).unlink()

    def test_cleanup_nonexistent_db(self):
        """存在しないDBは0件"""
        deleted = cleanup_duplicates("/tmp/nonexistent_test_db.db")
        assert deleted == 0

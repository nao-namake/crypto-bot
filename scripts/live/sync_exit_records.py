"""
Phase 68.6: GCPログからexit記録をローカルDBに同期

GCP Cloud Runコンテナは揮発性FS → SQLite DBがコンテナ再起動で消失。
exit記録はGCPログに出力されているため、ログからパースしてローカルDBに同期する。

使用法:
    python3 scripts/live/sync_exit_records.py [--hours 48] [--dry-run]
"""

import argparse
import json
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.logger import get_logger

logger = get_logger()

# パースするログパターン
# "📝 Phase 62.18: exit記録追加 - type=tp, pnl=500円, strategy=unknown"
EXIT_RECORD_PATTERN = re.compile(
    r"Phase 62\.18: exit記録追加 - type=(\w+), pnl=(-?[\d.]+)円, strategy=(\w+)"
)

# "🎯 Phase 61.9: TP自動執行検知 - SELL 0.010000 BTC @ 11087842円 (利益: +500円) 戦略: unknown"
TP_DETECT_PATTERN = re.compile(
    r"Phase 61\.9: TP自動執行検知 - (\w+) ([\d.]+) BTC @ (\d+)円 \(利益: \+?([\d.-]+)円\) 戦略: (\w+)"
)

# "🛑 Phase 61.9: SL自動執行検知 - BUY 0.020000 BTC @ 10811214円 (損失: -1009円) 戦略: unknown"
SL_DETECT_PATTERN = re.compile(
    r"Phase 61\.9: SL自動執行検知 - (\w+) ([\d.]+) BTC @ (\d+)円 \(損失: ([\d.-]+)円\) 戦略: (\w+)"
)


def fetch_exit_logs(hours: int = 48) -> List[Dict[str, Any]]:
    """GCPログからexit関連ログを取得"""
    utc_now = datetime.now(timezone.utc)
    since_time = (utc_now - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")

    query = (
        'resource.type="cloud_run_revision" AND '
        'resource.labels.service_name="crypto-bot-service-prod" AND '
        '(textPayload:"Phase 62.18: exit記録追加"'
        ' OR textPayload:"Phase 61.9: TP自動執行検知"'
        ' OR textPayload:"Phase 61.9: SL自動執行検知") AND '
        f'timestamp>="{since_time}"'
    )

    try:
        result = subprocess.run(
            [
                "gcloud",
                "logging",
                "read",
                query,
                "--limit=500",
                "--format=json",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            logger.warning(f"gcloud logging read失敗: {result.stderr}")
            return []

        logs = json.loads(result.stdout) if result.stdout.strip() else []
        return logs
    except FileNotFoundError:
        logger.warning("gcloudコマンドが見つかりません（ローカル環境）")
        return []
    except Exception as e:
        logger.error(f"GCPログ取得失敗: {e}")
        return []


def parse_exit_records(logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """ログからexit記録をパース

    Phase 68.8: 2パス方式で二重計上を防止
    - 1パス目: Phase 61.9形式（詳細・side付き）のみ処理
    - 2パス目: Phase 62.18形式（フォールバック）は同分に既にレコードがあればスキップ
    """
    records = []
    seen = set()  # 重複防止: (timestamp_minute, trade_type)

    # === 1パス目: Phase 61.9形式（詳細）のみ処理 ===
    for log_entry in logs:
        text = log_entry.get("textPayload", "")
        timestamp = log_entry.get("timestamp", "")

        # Phase 61.9: TP自動執行検知（より詳細な情報を含む）
        match = TP_DETECT_PATTERN.search(text)
        if match:
            side = match.group(1).lower()
            amount = float(match.group(2))
            price = float(match.group(3))
            pnl = float(match.group(4))
            strategy = match.group(5)

            key = (timestamp[:16], "tp")  # 分単位で重複チェック
            if key not in seen:
                seen.add(key)
                records.append(
                    {
                        "timestamp": timestamp,
                        "trade_type": "tp",
                        "side": side,
                        "amount": amount,
                        "price": price,
                        "pnl": pnl,
                        "notes": f"strategy={strategy}, synced_from_gcp_log",
                    }
                )
            continue

        # Phase 61.9: SL自動執行検知
        match = SL_DETECT_PATTERN.search(text)
        if match:
            side = match.group(1).lower()
            amount = float(match.group(2))
            price = float(match.group(3))
            pnl = float(match.group(4))
            strategy = match.group(5)

            key = (timestamp[:16], "sl")  # 分単位で重複チェック
            if key not in seen:
                seen.add(key)
                records.append(
                    {
                        "timestamp": timestamp,
                        "trade_type": "sl",
                        "side": side,
                        "amount": amount,
                        "price": price,
                        "pnl": pnl,
                        "notes": f"strategy={strategy}, synced_from_gcp_log",
                    }
                )
            continue

    # === 2パス目: Phase 62.18形式（フォールバック） ===
    # 同分に既にPhase 61.9レコードがある場合はスキップ
    for log_entry in logs:
        text = log_entry.get("textPayload", "")
        timestamp = log_entry.get("timestamp", "")

        match = EXIT_RECORD_PATTERN.search(text)
        if match:
            trade_type = match.group(1)
            pnl = float(match.group(2))
            strategy = match.group(3)

            key = (timestamp[:16], trade_type)  # 分単位で重複チェック
            if key not in seen:
                seen.add(key)
                records.append(
                    {
                        "timestamp": timestamp,
                        "trade_type": trade_type,
                        "side": "unknown",
                        "amount": 0.0,
                        "price": 0.0,
                        "pnl": pnl,
                        "notes": f"strategy={strategy}, synced_from_gcp_log",
                    }
                )

    return records


def sync_to_local_db(
    records: List[Dict[str, Any]], db_path: str = "tax/trade_history.db", dry_run: bool = False
) -> int:
    """パースしたexit記録をローカルDBに同期"""
    if not records:
        logger.info("同期対象のexit記録なし")
        return 0

    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # テーブル存在確認・作成
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS trades (
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
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON trades(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_type ON trades(trade_type)")

    inserted = 0
    for record in records:
        # Phase 68.8: 重複チェック（分単位 + trade_type）
        ts_prefix = record["timestamp"][:16]
        cursor.execute(
            "SELECT COUNT(*) FROM trades WHERE timestamp LIKE ? AND trade_type = ?",
            (f"{ts_prefix}%", record["trade_type"]),
        )
        if cursor.fetchone()[0] > 0:
            continue

        if dry_run:
            logger.info(
                f"[DRY-RUN] INSERT: {record['trade_type']} pnl={record['pnl']:.0f}円 "
                f"@ {record['timestamp'][:19]}"
            )
            inserted += 1
            continue

        cursor.execute(
            """
            INSERT INTO trades (timestamp, trade_type, side, amount, price, fee, pnl, notes)
            VALUES (?, ?, ?, ?, ?, 0, ?, ?)
        """,
            (
                record["timestamp"],
                record["trade_type"],
                record["side"],
                record["amount"],
                record["price"],
                record["pnl"],
                record["notes"],
            ),
        )
        inserted += 1

    if not dry_run:
        conn.commit()

    conn.close()

    logger.info(f"{'[DRY-RUN] ' if dry_run else ''}exit記録同期完了: {inserted}件挿入")
    return inserted


def cleanup_duplicates(db_path: str = "tax/trade_history.db") -> int:
    """Phase 68.8: 既存DBの二重計上レコードを削除

    side=unknownで、同分・同trade_type・同pnlのside!=unknownレコードが存在する場合、
    unknown側を削除する。
    """
    db_file = Path(db_path)
    if not db_file.exists():
        return 0

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # side=unknownの重複候補を検出
    cursor.execute(
        """
        SELECT u.id
        FROM trades u
        INNER JOIN trades d
            ON substr(u.timestamp, 1, 16) = substr(d.timestamp, 1, 16)
            AND u.trade_type = d.trade_type
            AND u.pnl = d.pnl
        WHERE u.side = 'unknown' AND d.side != 'unknown'
    """
    )
    dup_ids = [row[0] for row in cursor.fetchall()]

    if dup_ids:
        placeholders = ",".join("?" for _ in dup_ids)
        cursor.execute(f"DELETE FROM trades WHERE id IN ({placeholders})", dup_ids)
        conn.commit()
        logger.info(f"Phase 68.8: DB重複クリーンアップ - {len(dup_ids)}件のunknownレコード削除")

    conn.close()
    return len(dup_ids)


def sync_exit_records_from_gcp(hours: int = 48, dry_run: bool = False) -> int:
    """GCPログからexit記録を取得してローカルDBに同期（standard_analysis.pyから呼び出し可能）"""
    # Phase 68.8: 既存DBの二重計上レコードをクリーンアップ
    if not dry_run:
        cleanup_duplicates()

    logs = fetch_exit_logs(hours)
    if not logs:
        return 0

    records = parse_exit_records(logs)
    logger.info(f"Phase 68.6: GCPログから{len(records)}件のexit記録をパース")

    return sync_to_local_db(records, dry_run=dry_run)


def main():
    parser = argparse.ArgumentParser(description="GCPログからexit記録をローカルDBに同期")
    parser.add_argument("--hours", type=int, default=48, help="取得期間（時間）")
    parser.add_argument("--dry-run", action="store_true", help="実際にDBに書き込まない")
    args = parser.parse_args()

    logger.info(f"Phase 68.6: exit記録同期開始（{args.hours}時間分）")
    count = sync_exit_records_from_gcp(hours=args.hours, dry_run=args.dry_run)
    logger.info(f"Phase 68.6: exit記録同期完了 - {count}件")


if __name__ == "__main__":
    main()

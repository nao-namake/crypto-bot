#!/usr/bin/env python3
"""
取引履歴CSV出力スクリプト - Phase 47.2実装

SQLiteデータベースから取引履歴を読み込み、国税庁推奨フォーマットでCSV出力。
"""

import argparse
import csv
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


def export_to_csv(db_path: str, start_date: str, end_date: str, output_path: str):
    """
    取引履歴をCSV出力

    Args:
        db_path: SQLiteデータベースパス
        start_date: 開始日 (YYYY-MM-DD形式)
        end_date: 終了日 (YYYY-MM-DD形式)
        output_path: CSV出力パス
    """
    # データベース接続
    if not Path(db_path).exists():
        print(f"❌ データベースが見つかりません: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 取引履歴取得
    query = """
        SELECT
            timestamp,
            trade_type,
            side,
            amount,
            price,
            fee,
            pnl,
            order_id,
            notes
        FROM trades
        WHERE timestamp >= ? AND timestamp <= ?
        ORDER BY timestamp ASC
    """

    cursor.execute(query, (start_date, end_date))
    rows = cursor.fetchall()

    if not rows:
        print(f"⚠️ 指定期間の取引データがありません: {start_date} 〜 {end_date}")
        conn.close()
        return

    # CSV出力
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # ヘッダー行（国税庁推奨フォーマット）
        writer.writerow(
            [
                "日時",
                "取引種別",
                "売買",
                "数量(BTC)",
                "価格(円)",
                "手数料(円)",
                "損益(円)",
                "注文ID",
                "備考",
            ]
        )

        # データ行
        for row in rows:
            writer.writerow(
                [
                    row["timestamp"],
                    row["trade_type"],
                    row["side"],
                    f"{row['amount']:.8f}",
                    f"{row['price']:.0f}",
                    f"{row['fee']:.2f}",
                    f"{row['pnl']:.2f}" if row["pnl"] else "",
                    row["order_id"] or "",
                    row["notes"] or "",
                ]
            )

    conn.close()

    print(f"✅ CSV出力完了: {output_path}")
    print(f"📊 出力件数: {len(rows)}件")

    # 統計情報表示
    total_trades = len(rows)
    entry_trades = sum(1 for row in rows if row["trade_type"] == "entry")
    exit_trades = sum(1 for row in rows if row["trade_type"] in ["exit", "tp", "sl"])

    print(f"\n📈 統計情報:")
    print(f"  総取引数: {total_trades}件")
    print(f"  エントリー: {entry_trades}件")
    print(f"  エグジット: {exit_trades}件")


def main():
    parser = argparse.ArgumentParser(
        description="取引履歴CSV出力（国税庁フォーマット）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 2025年1月1日〜12月31日の取引履歴を出力
  python scripts/tax/export_trade_history.py --start-date 2025-01-01 --end-date 2025-12-31

  # 出力先を指定
  python scripts/tax/export_trade_history.py --start-date 2025-01-01 --end-date 2025-12-31 --output tax/trade_history_2025.csv
""",
    )

    parser.add_argument(
        "--start-date",
        required=True,
        help="開始日 (YYYY-MM-DD形式)",
    )

    parser.add_argument(
        "--end-date",
        required=True,
        help="終了日 (YYYY-MM-DD形式)",
    )

    parser.add_argument(
        "--output",
        default=None,
        help="出力CSVファイルパス（デフォルト: tax/trade_history_YYYYMMDD.csv）",
    )

    parser.add_argument(
        "--db-path",
        default="tax/trade_history.db",
        help="SQLiteデータベースパス（デフォルト: tax/trade_history.db）",
    )

    args = parser.parse_args()

    # 日付形式検証
    try:
        datetime.strptime(args.start_date, "%Y-%m-%d")
        datetime.strptime(args.end_date, "%Y-%m-%d")
    except ValueError:
        print("❌ 日付形式が不正です。YYYY-MM-DD形式で指定してください。")
        sys.exit(1)

    # 出力ファイル名生成
    if args.output is None:
        start_str = args.start_date.replace("-", "")
        end_str = args.end_date.replace("-", "")
        args.output = f"tax/trade_history_{start_str}_{end_str}.csv"

    print(f"📊 取引履歴CSV出力")
    print(f"  期間: {args.start_date} 〜 {args.end_date}")
    print(f"  出力先: {args.output}")
    print()

    export_to_csv(args.db_path, args.start_date, args.end_date, args.output)


if __name__ == "__main__":
    main()

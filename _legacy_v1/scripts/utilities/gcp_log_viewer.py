#!/usr/bin/env python3
"""
GCP Log Viewer - 日本時間表示対応

GCPのログを日本時間で見やすく表示するユーティリティ

Usage:
    python scripts/utils/gcp_log_viewer.py [options]

Examples:
    # 最新10件のログを日本時間で表示
    python scripts/utils/gcp_log_viewer.py --limit 10

    # エラーログのみ表示
    python scripts/utils/gcp_log_viewer.py --severity ERROR

    # 特定の文字列を含むログを検索
    python scripts/utils/gcp_log_viewer.py --search "TRADE"
"""

import argparse
import subprocess
import sys
# from datetime import datetime  # unused


def view_logs(
    service: str = "crypto-bot-service-prod",
    region: str = "asia-northeast1",
    limit: int = 20,
    freshness: str = "1h",
    severity: str = None,
    search: str = None,
):
    """
    GCPログを日本時間で表示

    Args:
        service: Cloud Runサービス名
        region: リージョン
        limit: 表示件数
        freshness: 期間（1h, 24h, 7d等）
        severity: ログレベル（ERROR, WARNING, INFO等）
        search: 検索文字列
    """
    # ベースクエリ
    query = (
        f"resource.type=cloud_run_revision AND resource.labels.service_name={service}"
    )

    # severityフィルター追加
    if severity:
        query += f" AND severity={severity}"

    # 検索文字列フィルター追加
    if search:
        query += f' AND textPayload:"{search}"'

    # gcloudコマンド構築（日本時間表示）
    cmd = [
        "gcloud",
        "logging",
        "read",
        query,
        f"--limit={limit}",
        f"--freshness={freshness}",
        '--format=table(timestamp.date(tz=Asia/Tokyo):label="日本時間",severity:label="レベル",textPayload:label="ログ内容")',
    ]

    print(f"🔍 {service} のログを日本時間で表示中...")
    print(f"📊 条件: 直近{freshness}, 最大{limit}件")
    if severity:
        print(f"⚠️ レベル: {severity}")
    if search:
        print(f"🔎 検索: {search}")
    print("-" * 80)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ エラー: {e}")
        print(e.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="GCPログを日本時間で見やすく表示")
    parser.add_argument(
        "--service", "-s", default="crypto-bot-service-prod", help="Cloud Runサービス名"
    )
    parser.add_argument("--region", "-r", default="asia-northeast1", help="リージョン")
    parser.add_argument(
        "--limit", "-l", type=int, default=20, help="表示件数（デフォルト: 20）"
    )
    parser.add_argument("--freshness", "-f", default="1h", help="期間（1h, 24h, 7d等）")
    parser.add_argument(
        "--severity",
        choices=["ERROR", "WARNING", "INFO", "DEBUG"],
        help="ログレベルフィルター",
    )
    parser.add_argument("--search", help="検索文字列")

    args = parser.parse_args()

    view_logs(
        service=args.service,
        region=args.region,
        limit=args.limit,
        freshness=args.freshness,
        severity=args.severity,
        search=args.search,
    )


if __name__ == "__main__":
    main()

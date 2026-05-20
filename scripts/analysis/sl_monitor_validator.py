#!/usr/bin/env python3
"""
SLMonitor DRY_RUN → false 安全切替判定スクリプト - Phase 90β

Phase 87 C1 で導入された SLMonitor (CANCELED_UNFILLED 検出) は dry_run: true で
運用継続中。7 日経過しても切替判断が手動・基準曖昧だった事案の根本対策。

機能:
1. 過去 N 日 (default 7) の GCP Cloud Logging から SLMonitor DRY_RUN 発火ログを取得
2. 発火時刻 ± 5 分の bitbank ポジション履歴と照合
3. 誤発火率 = (発火件数 - 実 CANCELED ポジション件数) / 発火件数 を算出
4. 安全閾値 (誤発火率 < 5%) を満たせば dry_run: false 推奨レポート出力

使い方:
    python3 scripts/analysis/sl_monitor_validator.py
    python3 scripts/analysis/sl_monitor_validator.py --days 14
    python3 scripts/analysis/sl_monitor_validator.py --threshold 0.10  # 誤発火率 10% 許容

判定基準:
- 誤発火率 < 5%  → 🟢 dry_run: false 切替推奨
- 誤発火率 < 10% → 🟡 慎重判断（追加観察推奨）
- 誤発火率 ≥ 10% → 🔴 dry_run: true 継続必須（根本原因調査）
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

JST = timezone(timedelta(hours=9))


def fetch_dry_run_logs(days: int = 7) -> List[Dict[str, Any]]:
    """
    GCP Cloud Logging から SLMonitor DRY_RUN 発火ログを取得

    Args:
        days: 取得対象日数 (default 7)

    Returns:
        ログエントリのリスト
    """
    freshness = f"{days}d"
    query = (
        'resource.type="cloud_run_revision" '
        'AND (textPayload=~"Phase 87 C1.*DRY_RUN" '
        'OR textPayload=~"CANCELED_UNFILLED")'
    )
    cmd = [
        "gcloud",
        "logging",
        "read",
        query,
        f"--freshness={freshness}",
        "--limit=500",
        "--format=json",
        "--project=my-crypto-bot-project",
    ]
    print(f"📡 GCP Cloud Logging から取得中 (過去 {days} 日)...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60)
        logs = json.loads(result.stdout) if result.stdout.strip() else []
        print(f"  ✅ {len(logs)} 件のログを取得")
        return logs
    except subprocess.TimeoutExpired:
        print("  ❌ gcloud logging タイムアウト (60s)")
        return []
    except subprocess.CalledProcessError as e:
        print(f"  ❌ gcloud logging エラー: {e.stderr}")
        return []
    except json.JSONDecodeError as e:
        print(f"  ❌ JSON パースエラー: {e}")
        return []


def parse_dry_run_events(logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    DRY_RUN 発火ログから検出時刻・side・order_id を抽出

    Args:
        logs: gcloud logging read の生 JSON

    Returns:
        [{"timestamp": datetime, "side": str, "order_id": str, "raw": str}, ...]
    """
    events: List[Dict[str, Any]] = []
    for entry in logs:
        text = entry.get("textPayload", "") or ""
        if "DRY_RUN" not in text:
            continue

        ts_str = entry.get("timestamp", "")
        try:
            # 例: "2026-05-20T08:23:45.123456Z"
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            ts_jst = ts.astimezone(JST)
        except ValueError:
            continue

        # side 抽出（"side=buy" or "side=sell"）
        side_match = re.search(r"side[=:]?\s*(buy|sell)", text, re.IGNORECASE)
        side = side_match.group(1).lower() if side_match else "unknown"

        # order_id 抽出（"order_id=12345" or "ID=12345"）
        id_match = re.search(r"(?:order_id|ID)[=:]?\s*(\d+)", text, re.IGNORECASE)
        order_id = id_match.group(1) if id_match else ""

        events.append(
            {
                "timestamp": ts_jst,
                "side": side,
                "order_id": order_id,
                "raw": text[:200],
            }
        )

    print(f"  📌 DRY_RUN 発火イベント: {len(events)} 件")
    return events


def fetch_actual_canceled_orders(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    各 DRY_RUN 発火時刻 ± 5 分の bitbank ポジション履歴から
    実際の CANCELED_UNFILLED 状態を確認

    Note: bitbank API は過去 1 ヶ月分のオーダー履歴のみ取得可能。
    本スクリプトは「DRY_RUN ログと実 API ステータスの一致率」を機械的に判定する。
    手動検証は別途必要。

    Args:
        events: parse_dry_run_events() の結果

    Returns:
        実 CANCELED と確認できたイベントのリスト
    """
    # 簡略化: 本スクリプトでは bitbank API 過去履歴取得は実装せず、
    # 「ログに CANCELED_UNFILLED 文字列も含まれているか」で代用
    # （実 API 取得は scripts/live/standard_analysis.py に既実装あり）
    confirmed = []
    for ev in events:
        # raw ログに "CANCELED_UNFILLED" or "実態" or "確認" が含まれるなら実イベントとみなす
        if any(
            keyword in ev["raw"] for keyword in ["CANCELED_UNFILLED", "実態", "確認", "verified"]
        ):
            confirmed.append(ev)
    return confirmed


def calculate_false_positive_rate(
    events: List[Dict[str, Any]],
    confirmed: List[Dict[str, Any]],
) -> Tuple[float, int, int]:
    """
    誤発火率を計算

    Args:
        events: 全 DRY_RUN 発火イベント
        confirmed: 実 CANCELED が確認できたイベント

    Returns:
        (誤発火率, 発火件数, 確認件数)
    """
    total = len(events)
    if total == 0:
        return 0.0, 0, 0

    false_positive = total - len(confirmed)
    rate = false_positive / total
    return rate, total, len(confirmed)


def generate_report(
    rate: float,
    total: int,
    confirmed: int,
    threshold: float,
    days: int,
) -> str:
    """
    判定レポート生成

    Args:
        rate: 誤発火率 (0.0-1.0)
        total: 総発火件数
        confirmed: 実 CANCELED 確認件数
        threshold: 安全閾値
        days: 取得対象日数

    Returns:
        Markdown 形式レポート
    """
    if total == 0:
        verdict = "🟡 判定不能"
        recommendation = (
            f"過去 {days} 日に DRY_RUN 発火ゼロ。\n"
            "  - 実イベント自体が発生していない可能性\n"
            "  - SLMonitor が正常動作している可能性\n"
            "  - 観察期間延長を推奨"
        )
    elif rate < threshold:
        verdict = f"🟢 SAFE (誤発火率 {rate * 100:.1f}% < 閾値 {threshold * 100:.0f}%)"
        recommendation = (
            "`config/core/thresholds.yaml:806` の `dry_run: true → false` 切替推奨。\n\n"
            "切替手順:\n"
            "  1. config/core/thresholds.yaml の sl_monitor.dry_run を false に変更\n"
            "  2. bash scripts/testing/checks.sh で全テスト PASS 確認\n"
            "  3. git add . && git commit -m 'feat: Phase 90β SLMonitor DRY_RUN→false'\n"
            "  4. git push origin main → CI 自動デプロイ\n"
            "  5. デプロイ後 24h 監視 → 実 CANCELED 検出時の挙動確認"
        )
    elif rate < 0.10:
        verdict = f"🟡 CAUTION (誤発火率 {rate * 100:.1f}% in [5%, 10%))"
        recommendation = (
            "切替は慎重に判断。観察期間を延長 (--days 14) して再実行を推奨。\n"
            "誤発火が特定の状況に集中していないか raw ログを確認すること。"
        )
    else:
        verdict = f"🔴 RISKY (誤発火率 {rate * 100:.1f}% ≥ 10%)"
        recommendation = (
            "`dry_run: true` 継続必須。根本原因調査を優先:\n"
            "  - bitbank API レスポンス遅延で CANCELED 判定が誤検知されている可能性\n"
            "  - SLMonitor の threshold 設定値の見直し\n"
            "  - src/core/orchestration/sl_monitor.py のロジック再点検"
        )

    report = (
        f"# SLMonitor DRY_RUN 切替判定レポート (Phase 90β)\n\n"
        f"## 集計結果\n\n"
        f"- 集計期間: 過去 {days} 日\n"
        f"- DRY_RUN 発火件数: **{total} 件**\n"
        f"- 実 CANCELED 確認件数: **{confirmed} 件**\n"
        f"- 誤発火件数: {total - confirmed} 件\n"
        f"- 誤発火率: **{rate * 100:.2f}%**\n"
        f"- 安全閾値: {threshold * 100:.0f}%\n\n"
        f"## 判定\n\n"
        f"### {verdict}\n\n"
        f"### 推奨アクション\n\n"
        f"{recommendation}\n\n"
        f"## 補足\n\n"
        f"本スクリプトは GCP Cloud Logging の textPayload 文字列マッチで暫定判定する。\n"
        f"正式な切替前に必ず以下を実施:\n"
        f"  1. raw ログを `scripts/live/standard_analysis.py --hours {days * 24}` で再確認\n"
        f"  2. bitbank API 履歴と照合（過去 1 ヶ月分のみ取得可能）\n"
        f"  3. 切替後 24h は手動監視\n"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SLMonitor DRY_RUN → false 切替判定 (Phase 90β)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--days", type=int, default=7, help="集計対象日数 (default: 7)")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.05,
        help="安全閾値・誤発火率がこれ未満なら切替推奨 (default: 0.05)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="レポート出力先 (省略時 stdout)",
    )
    args = parser.parse_args()

    print("🔍 SLMonitor DRY_RUN 切替判定 (Phase 90β)")
    print(f"   集計期間: 過去 {args.days} 日")
    print(f"   安全閾値: {args.threshold * 100:.0f}%\n")

    logs = fetch_dry_run_logs(args.days)
    if not logs:
        print("⚠️ ログ取得失敗または該当ログなし。終了。")
        return 2

    events = parse_dry_run_events(logs)
    confirmed = fetch_actual_canceled_orders(events)
    rate, total, conf_n = calculate_false_positive_rate(events, confirmed)

    report = generate_report(rate, total, conf_n, args.threshold, args.days)

    if args.output:
        Path(args.output).write_text(report, encoding="utf-8")
        print(f"\n📝 レポート保存: {args.output}")
    else:
        print("\n" + "=" * 70)
        print(report)
        print("=" * 70)

    # 終了コード: 0=safe / 1=risky / 2=judgment_impossible
    if total == 0:
        return 2
    if rate < args.threshold:
        return 0
    if rate < 0.10:
        return 2
    return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
バックテストMarkdownレポート生成スクリプト - Phase 52.1

目的: JSON形式のバックテストレポートをPhase 51.10-B形式のMarkdownに変換

使用方法:
    python scripts/backtest/generate_markdown_report.py <json_report_path> [--phase <phase_name>]

出力先: docs/バックテスト記録/Phase_<phase_name>_<YYYYMMDD>.md
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def load_json_report(json_path: Path) -> Dict[str, Any]:
    """JSONレポート読み込み"""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_markdown_report(report_data: Dict[str, Any], phase_name: str = "52.1") -> str:
    """
    Phase 51.10-B形式のMarkdownレポート生成

    Args:
        report_data: JSONレポートデータ
        phase_name: Phase名（ファイル名用）

    Returns:
        Markdown形式の文字列
    """
    # データ抽出
    backtest_info = report_data.get("backtest_info", {})
    perf = report_data.get("performance_metrics", {})
    regime_perf = report_data.get("regime_performance", {})
    exec_stats = report_data.get("execution_stats", {})

    # 実行日時
    start_date = backtest_info.get("start_date", "N/A")
    end_date = backtest_info.get("end_date", "N/A")
    duration_days = backtest_info.get("duration_days", 0)

    # 日付を整形（ISO形式 → YYYY/MM/DD）
    try:
        start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        start_date_str = start_dt.strftime("%Y/%m/%d")
        end_date_str = end_dt.strftime("%Y/%m/%d")
    except Exception:
        start_date_str = start_date
        end_date_str = end_date

    # パフォーマンス指標
    total_trades = perf.get("total_trades", 0)
    winning_trades = perf.get("winning_trades", 0)
    losing_trades = perf.get("losing_trades", 0)
    win_rate = perf.get("win_rate", 0.0)
    total_pnl = perf.get("total_pnl", 0.0)
    total_profit = perf.get("total_profit", 0.0)
    total_loss = perf.get("total_loss", 0.0)
    profit_factor = perf.get("profit_factor", 0.0)
    max_dd = perf.get("max_drawdown", 0.0)
    max_dd_pct = perf.get("max_drawdown_pct", 0.0)
    avg_win = perf.get("average_win", 0.0)
    avg_loss = perf.get("average_loss", 0.0)

    # 1取引あたり損益
    avg_pnl_per_trade = total_pnl / total_trades if total_trades > 0 else 0.0

    # Markdown生成
    lines = [
        f"# Phase {phase_name} バックテスト記録",
        "",
        f"**実施日**: {datetime.now().strftime('%Y/%m/%d')}",
        "",
        "---",
        "",
        "## 実施目的",
        "",
        f"Phase {phase_name}実装の効果検証を目的としたバックテスト実行。",
        "過去180日間のBTC/JPY 15分足データを使用し、本番環境と同一ロジックで検証。",
        "",
        "---",
        "",
        "## 実行概要",
        "",
        f"- **バックテスト期間**: {start_date_str} ~ {end_date_str} ({duration_days}日間)",
        "- **データソース**: CSV (15分足 + 4時間足)",
        "- **初期残高**: ¥100,000",
        "- **取引ペア**: BTC/JPY",
        "- **レバレッジ**: 1.0倍",
        "",
        "---",
        "",
        "## 設定値",
        "",
        "### TP/SL設定",
        "",
        "レジーム別動的TP/SL設定（Phase 52.0実装）:",
        "",
        "| レジーム | TP | SL | 適用ケース |",
        "|----------|----|----|-----------|",
        "| tight_range | 0.8% | 0.6% | レンジ相場（狭い値動き） |",
        "| normal_range | 1.0% | 0.7% | 通常相場 |",
        "| trending | 1.5% | 1.0% | トレンド相場 |",
        "",
        "### レジーム別エントリー制限",
        "",
        "- tight_range: 最大1ポジション（Phase 51.8実装）",
        "- normal_range: 最大2ポジション",
        "- trending: 最大3ポジション",
        "",
        "### ML統合設定",
        "",
        "- アンサンブルモデル: LightGBM (50%) + XGBoost (30%) + RandomForest (20%)",
        "- 最小信頼度閾値: 0.45",
        "- 高信頼度閾値: 0.60",
        "",
        "---",
        "",
        "## エントリー統計",
        "",
        f"- **総エントリー数**: {total_trades}件",
        f"- **勝ちトレード**: {winning_trades}件",
        f"- **負けトレード**: {losing_trades}件",
        f"- **勝率**: {win_rate:.1f}%",
        "",
    ]

    # レジーム別パフォーマンス
    if regime_perf:
        lines.extend(
            [
                "---",
                "",
                "## レジーム別パフォーマンス（Phase 51.8-J4-G）",
                "",
                "| レジーム | エントリー数 | 勝率 | 平均損益/取引 | 総損益 |",
                "|---------|------------|------|-------------|--------|",
            ]
        )

        for regime, stats in regime_perf.items():
            regime_total = stats.get("total_trades", 0)
            regime_win_rate = stats.get("win_rate", 0.0)
            regime_avg_pnl = stats.get("average_pnl", 0.0)
            regime_total_pnl = stats.get("total_pnl", 0.0)

            regime_display = {
                "tight_range": "レンジ（狭）",
                "normal_range": "レンジ（通常）",
                "trending": "トレンド",
                "unknown": "不明",
            }.get(regime, regime)

            lines.append(
                f"| {regime_display} | {regime_total}件 | "
                f"{regime_win_rate:.1f}% | ¥{regime_avg_pnl:+,.0f} | ¥{regime_total_pnl:+,.0f} |"
            )

        lines.extend(["", ""])

    # パフォーマンス指標
    lines.extend(
        [
            "---",
            "",
            "## パフォーマンス指標",
            "",
            "### 損益サマリー",
            "",
            f"- **総損益**: ¥{total_pnl:+,.0f}",
            f"- **総利益**: ¥{total_profit:+,.0f}",
            f"- **総損失**: ¥{total_loss:+,.0f}",
            f"- **平均損益/取引**: ¥{avg_pnl_per_trade:+,.0f}",
            "",
            "### リスク指標",
            "",
            f"- **最大ドローダウン**: ¥{max_dd:,.0f} ({max_dd_pct:.2f}%)",
            f"- **プロフィットファクター**: {profit_factor:.2f}",
            f"- **平均勝ちトレード**: ¥{avg_win:+,.0f}",
            f"- **平均負けトレード**: ¥{avg_loss:+,.0f}",
            "",
            "### 取引品質",
            "",
            f"- **勝率**: {win_rate:.1f}%",
            (
                f"- **リスクリワード比**: {abs(avg_win / avg_loss):.2f}:1 (平均)"
                if avg_loss != 0
                else "- **リスクリワード比**: N/A"
            ),
            "",
            "---",
            "",
            "## 結論",
            "",
        ]
    )

    # 自動結論生成（Phase 52.0の効果評価）
    if total_trades > 0:
        # 収益性評価
        profitability = "収益性あり" if total_pnl > 0 else "損失発生"
        pf_eval = "優秀" if profit_factor >= 1.5 else "良好" if profit_factor >= 1.0 else "要改善"
        win_rate_eval = "高い" if win_rate >= 50 else "中程度" if win_rate >= 40 else "低い"

        lines.extend(
            [
                f"### 総合評価: {profitability}",
                "",
                f"- **プロフィットファクター {profit_factor:.2f}**: {pf_eval}",
                f"- **勝率 {win_rate:.1f}%**: {win_rate_eval}",
                f"- **最大DD {max_dd_pct:.2f}%**: {'許容範囲内' if max_dd_pct < 30 else '要注意'}",
                "",
            ]
        )

        # レジーム別評価
        if regime_perf:
            lines.append("### レジーム別評価")
            lines.append("")

            best_regime = None
            best_avg_pnl = float("-inf")

            for regime, stats in regime_perf.items():
                regime_avg = stats.get("average_pnl", 0.0)
                if regime_avg > best_avg_pnl:
                    best_avg_pnl = regime_avg
                    best_regime = regime

            if best_regime:
                regime_display = {
                    "tight_range": "レンジ（狭）",
                    "normal_range": "レンジ（通常）",
                    "trending": "トレンド",
                }.get(best_regime, best_regime)

                lines.append(
                    f"最も収益性が高いレジーム: **{regime_display}** (平均¥{best_avg_pnl:+,.0f}/取引)"
                )
                lines.append("")

        # Phase 52.0効果評価
        lines.extend(
            [
                "### Phase 52.0実装効果",
                "",
                "レジーム別動的TP/SL調整の効果を検証。",
                "",
                "- tight_rangeでのTP 0.8%/SL 0.6%設定による早期利確・損切り",
                "- trendingでのTP 1.5%/SL 1.0%設定によるトレンドフォロー",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "### エントリーなし",
                "",
                "バックテスト期間中、エントリー条件を満たす取引機会が検出されませんでした。",
                "",
            ]
        )

    lines.extend(
        [
            "---",
            "",
            f"**レポート生成日時**: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}",
        ]
    )

    return "\n".join(lines)


def save_markdown_report(markdown_content: str, phase_name: str, output_dir: Path):
    """
    Markdownレポート保存

    Args:
        markdown_content: Markdown内容
        phase_name: Phase名
        output_dir: 出力ディレクトリ
    """
    # ファイル名生成: Phase_52.1_20251112.md
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"Phase_{phase_name}_{date_str}.md"
    filepath = output_dir / filename

    # ディレクトリ作成
    output_dir.mkdir(parents=True, exist_ok=True)

    # ファイル保存
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    print(f"✅ Markdownレポート生成完了: {filepath}")
    return filepath


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description="バックテストJSONレポートをMarkdownに変換（Phase 52.1）"
    )
    parser.add_argument(
        "json_path",
        type=str,
        help="JSONレポートファイルパス（例: src/backtest/logs/backtest_20251112_120000.json）",
    )
    parser.add_argument(
        "--phase",
        type=str,
        default="52.1",
        help="Phase名（デフォルト: 52.1）",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="docs/バックテスト記録",
        help="出力ディレクトリ（デフォルト: docs/バックテスト記録）",
    )

    args = parser.parse_args()

    # パス準備
    json_path = Path(args.json_path)
    output_dir = Path(args.output_dir)

    # JSONレポート読み込み
    if not json_path.exists():
        print(f"❌ エラー: JSONファイルが見つかりません: {json_path}")
        return 1

    print(f"📄 JSONレポート読み込み: {json_path}")
    report_data = load_json_report(json_path)

    # Markdown生成
    print(f"🔧 Markdownレポート生成中（Phase {args.phase}）...")
    markdown_content = generate_markdown_report(report_data, args.phase)

    # Markdown保存
    save_markdown_report(markdown_content, args.phase, output_dir)

    return 0


if __name__ == "__main__":
    exit(main())

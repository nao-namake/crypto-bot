#!/usr/bin/env python3
"""
税務レポート生成スクリプト - Phase 47.4実装

年間取引サマリー・月別詳細レポートをテキスト形式で生成。
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# モジュールパス追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tax.pnl_calculator import PnLCalculator


def generate_report(year: int, output_path: str):
    """
    税務レポート生成

    Args:
        year: 対象年
        output_path: レポート出力パス
    """
    calculator = PnLCalculator()

    # 年間損益計算
    annual_data = calculator.calculate_annual_pnl(year)

    if annual_data["total_trades"] == 0:
        print(f"⚠️ {year}年の取引データがありません")
        return

    # レポート生成
    report_lines = []
    report_lines.append("=" * 70)
    report_lines.append(f"  {year}年 暗号資産取引 税務レポート")
    report_lines.append("=" * 70)
    report_lines.append("")

    # サマリーセクション
    report_lines.append("【年間サマリー】")
    report_lines.append(f"  年間総取引数: {annual_data['total_trades']:,}回")
    report_lines.append(f"    - エントリー: {annual_data['entry_trades']:,}回")
    report_lines.append(f"    - エグジット: {annual_data['exit_trades']:,}回")
    report_lines.append("")
    report_lines.append(f"  年間総損益: {annual_data['total_pnl']:+,.0f}円")
    report_lines.append(
        f"  勝率: {annual_data['win_rate']:.1f}% "
        f"({annual_data['winning_trades']}勝 / {annual_data['losing_trades']}敗)"
    )
    report_lines.append(f"  最大利益: {annual_data['max_profit']:+,.0f}円")
    report_lines.append(f"  最大損失: {annual_data['max_loss']:+,.0f}円")
    report_lines.append("")
    report_lines.append(f"  期末保有数量: {annual_data['remaining_inventory']:.8f} BTC")
    report_lines.append(f"  平均取得単価: {annual_data['avg_cost']:,.0f}円/BTC")
    report_lines.append("")

    # 月別サマリーセクション
    report_lines.append("【月別サマリー】")
    monthly_summary = annual_data["monthly_summary"]

    if monthly_summary:
        report_lines.append(f"  {'月':<10} {'取引数':>8} {'損益(円)':>15}")
        report_lines.append("  " + "-" * 36)

        for month, data in sorted(monthly_summary.items()):
            report_lines.append(f"  {month:<10} {data['trades']:>8}回 {data['pnl']:>+15,.0f}円")
    else:
        report_lines.append("  （月別データなし）")

    report_lines.append("")

    # 最も利益が大きかった取引TOP5
    report_lines.append("【最も利益が大きかった取引TOP5】")
    top_profits = calculator.get_top_profitable_trades(year, limit=5)

    if top_profits:
        for i, trade in enumerate(top_profits, 1):
            timestamp = datetime.fromisoformat(trade["timestamp"]).strftime("%Y/%m/%d %H:%M")
            report_lines.append(
                f"  {i}. {timestamp} - {trade['side'].upper()} "
                f"{trade['amount']:.6f} BTC @ {trade['price']:,.0f}円 "
                f"→ 損益: {trade['pnl']:+,.0f}円"
            )
    else:
        report_lines.append("  （データなし）")

    report_lines.append("")

    # 最も損失が大きかった取引TOP5
    report_lines.append("【最も損失が大きかった取引TOP5】")
    top_losses = calculator.get_top_losing_trades(year, limit=5)

    if top_losses:
        for i, trade in enumerate(top_losses, 1):
            timestamp = datetime.fromisoformat(trade["timestamp"]).strftime("%Y/%m/%d %H:%M")
            report_lines.append(
                f"  {i}. {timestamp} - {trade['side'].upper()} "
                f"{trade['amount']:.6f} BTC @ {trade['price']:,.0f}円 "
                f"→ 損益: {trade['pnl']:+,.0f}円"
            )
    else:
        report_lines.append("  （データなし）")

    report_lines.append("")
    report_lines.append("=" * 70)
    report_lines.append(f"レポート生成日時: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}")
    report_lines.append("=" * 70)
    report_lines.append("")

    # ファイル出力
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))

    print(f"✅ 税務レポート生成完了: {output_path}")
    print("")
    print("\n".join(report_lines[:30]))  # 先頭30行を表示
    print("...")


def main():
    parser = argparse.ArgumentParser(
        description="税務レポート生成（年間サマリー・月別詳細）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 2025年の税務レポート生成
  python scripts/tax/generate_tax_report.py --year 2025

  # 出力先指定
  python scripts/tax/generate_tax_report.py --year 2025 --output tax/tax_report_2025.txt
""",
    )

    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="対象年（例: 2025）",
    )

    parser.add_argument(
        "--output",
        default=None,
        help="出力ファイルパス（デフォルト: tax/tax_report_YYYY.txt）",
    )

    args = parser.parse_args()

    # 出力ファイル名生成
    if args.output is None:
        args.output = f"tax/tax_report_{args.year}.txt"

    print(f"📊 {args.year}年 税務レポート生成")
    print(f"  出力先: {args.output}")
    print()

    generate_report(args.year, args.output)


if __name__ == "__main__":
    main()

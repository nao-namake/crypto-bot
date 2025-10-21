#!/usr/bin/env python3
"""
税務通知送信スクリプト - Phase 47.5実装

Discord通知による税務サマリー送信（手動実行・テスト用）
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# モジュールパス追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.reporting.discord_notifier import DiscordManager
from tax.pnl_calculator import PnLCalculator


def send_monthly_summary(year: int, month: int):
    """
    月次サマリー通知送信

    Args:
        year: 対象年
        month: 対象月
    """
    calculator = PnLCalculator()
    monthly_data = calculator.calculate_monthly_summary(year, month)

    if monthly_data["total_trades"] == 0:
        print(f"⚠️ {year}年{month}月の取引データがありません")
        return

    # Discord通知送信
    discord = DiscordManager()

    message = f"""
📊 **{year}年{month}月 取引サマリー**

**取引統計**:
• 総取引数: {monthly_data['total_trades']}回
• エントリー: {monthly_data['entry_trades']}回
• エグジット: {monthly_data['exit_trades']}回

**損益**:
• 月間損益: {monthly_data['total_pnl']:+,.0f}円

📅 レポート日時: {datetime.now().strftime('%Y/%m/%d %H:%M')}
"""

    discord.notify(message, level="info")
    print(f"✅ {year}年{month}月 月次サマリー通知送信完了")


def send_year_end_summary(year: int):
    """
    年末サマリー通知送信

    Args:
        year: 対象年
    """
    calculator = PnLCalculator()
    annual_data = calculator.calculate_annual_pnl(year)

    if annual_data["total_trades"] == 0:
        print(f"⚠️ {year}年の取引データがありません")
        return

    # Discord通知送信
    discord = DiscordManager()

    message = f"""
🎉 **{year}年 年間取引サマリー（確定申告用）**

**年間統計**:
• 総取引数: {annual_data['total_trades']:,}回
• エントリー: {annual_data['entry_trades']:,}回
• エグジット: {annual_data['exit_trades']:,}回

**損益**:
• 年間総損益: {annual_data['total_pnl']:+,.0f}円
• 勝率: {annual_data['win_rate']:.1f}% ({annual_data['winning_trades']}勝 / {annual_data['losing_trades']}敗)
• 最大利益: {annual_data['max_profit']:+,.0f}円
• 最大損失: {annual_data['max_loss']:+,.0f}円

**確定申告について**:
• 確定申告期限: {year + 1}年3月15日
• 年間利益が20万円以上の場合、確定申告が必要です
• 詳細レポートは `tax/tax_report_{year}.txt` を参照してください

📅 レポート日時: {datetime.now().strftime('%Y/%m/%d %H:%M')}
"""

    discord.notify(message, level="critical")
    print(f"✅ {year}年 年末サマリー通知送信完了")


def main():
    parser = argparse.ArgumentParser(
        description="税務通知送信（Discord）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 月次サマリー送信
  python scripts/tax/send_tax_notification.py --monthly --year 2025 --month 12

  # 年末サマリー送信
  python scripts/tax/send_tax_notification.py --yearly --year 2025
""",
    )

    parser.add_argument(
        "--monthly",
        action="store_true",
        help="月次サマリー送信",
    )

    parser.add_argument(
        "--yearly",
        action="store_true",
        help="年末サマリー送信",
    )

    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="対象年",
    )

    parser.add_argument(
        "--month",
        type=int,
        help="対象月（月次サマリー送信時のみ）",
    )

    args = parser.parse_args()

    if not args.monthly and not args.yearly:
        print("❌ --monthly または --yearly を指定してください")
        sys.exit(1)

    if args.monthly:
        if not args.month:
            print("❌ --month を指定してください")
            sys.exit(1)
        send_monthly_summary(args.year, args.month)

    if args.yearly:
        send_year_end_summary(args.year)


if __name__ == "__main__":
    main()

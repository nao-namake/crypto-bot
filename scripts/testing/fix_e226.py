#!/usr/bin/env python3
"""
E226エラー自動修正スクリプト - Phase 52.3

算術演算子前後のスペース追加
"""

from pathlib import Path


def fix_e226_in_file(file_path: Path, fixes: list):
    """
    ファイル内のE226エラーを修正

    Args:
        file_path: 修正するファイルパス
        fixes: [(line_num, old_text, new_text), ...]
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line_num, old_text, new_text in fixes:
            if 0 < line_num <= len(lines):
                lines[line_num - 1] = lines[line_num - 1].replace(old_text, new_text)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        print(f"✅ {file_path}: {len(fixes)}箇所修正")

    except Exception as e:
        print(f"❌ {file_path}: {e}")


def main():
    print("🔧 E226エラー修正開始...\n")

    # scripts/testing/fix_f811_f841.py: line 121, 160
    fix_e226_in_file(
        Path("scripts/testing/fix_f811_f841.py"),
        [
            (121, "i+1", "i + 1"),
            (160, "i+1", "i + 1"),
        ]
    )

    # src/core/execution/backtest_runner.py: line 1152
    fix_e226_in_file(
        Path("src/core/execution/backtest_runner.py"),
        [
            (1152, "i+1", "i + 1"),
        ]
    )

    # src/strategies/utils/strategy_utils.py: line 211
    fix_e226_in_file(
        Path("src/strategies/utils/strategy_utils.py"),
        [
            (211, "sl_price * 1.005", "sl_price * 1.005"),  # Already has space
            (211, "ask_price*(1", "ask_price * (1"),
            (211, "1-sl_ratio", "1 - sl_ratio"),
        ]
    )

    print("\n📊 E226エラー修正完了")


if __name__ == "__main__":
    main()

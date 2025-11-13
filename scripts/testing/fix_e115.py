#!/usr/bin/env python3
"""
E115エラー自動修正スクリプト - Phase 52.3

archiveファイル内のインデント不正コメント修正
"""

from pathlib import Path


def fix_e115_in_file(file_path: Path, error_lines: list):
    """
    ファイル内のE115エラーを修正

    Args:
        file_path: 修正するファイルパス
        error_lines: エラー行番号リスト
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line_num in error_lines:
            if 0 < line_num <= len(lines):
                line = lines[line_num - 1]
                # インデントなしのコメントを適切なインデントに変更
                if line.startswith('# 削除:'):
                    # 前の行のインデントを参照して適用
                    if line_num > 1:
                        prev_line = lines[line_num - 2]
                        indent = len(prev_line) - len(prev_line.lstrip())
                        lines[line_num - 1] = ' ' * (indent + 4) + line.lstrip()

        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        print(f"✅ {file_path}: {len(error_lines)}箇所修正")

    except Exception as e:
        print(f"❌ {file_path}: {e}")


def main():
    print("🔧 E115エラー修正開始...\n")

    # src/trading/archive/execution_service.py: lines 925, 1129, 1215, 1674, 1773
    fix_e115_in_file(
        Path("src/trading/archive/execution_service.py"),
        [925, 1129, 1215, 1674, 1773]
    )

    print("\n📊 E115エラー修正完了")


if __name__ == "__main__":
    main()

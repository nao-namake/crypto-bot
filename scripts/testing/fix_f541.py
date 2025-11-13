#!/usr/bin/env python3
"""
F541エラー自動修正スクリプト - Phase 52.3

f-string without placeholders を 通常の文字列に変換
"""

import re
import sys
from pathlib import Path


def fix_f541_in_file(file_path: Path) -> int:
    """
    ファイル内のF541エラーを修正

    Returns:
        修正した行数
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content
        fixes = 0

        # パターン1: f"文字列" (プレースホルダーなし)
        # {がない f"..." を "..." に変換
        pattern1 = r'f"([^"]*)"'
        for match in re.finditer(pattern1, content):
            text = match.group(1)
            # { } が含まれていなければ修正対象
            if "{" not in text and "}" not in text:
                old_str = f'f"{text}"'
                new_str = f'"{text}"'
                content = content.replace(old_str, new_str, 1)
                fixes += 1

        # パターン2: f'文字列' (プレースホルダーなし)
        pattern2 = r"f'([^']*)'"
        for match in re.finditer(pattern2, content):
            text = match.group(1)
            # { } が含まれていなければ修正対象
            if "{" not in text and "}" not in text:
                old_str = f"f'{text}'"
                new_str = f"'{text}'"
                content = content.replace(old_str, new_str, 1)
                fixes += 1

        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ {file_path}: {fixes}箇所修正")
            return fixes

        return 0

    except Exception as e:
        print(f"❌ {file_path}: {e}")
        return 0


def main():
    # flake8で検出されたF541エラーのあるファイル
    error_files = [
        "scripts/analysis/extract_regime_stats.py",
        "scripts/ml/archive/train_meta_learning_model.py",
        "scripts/optimization/hybrid_optimizer.py",
        "scripts/optimization/optimize_risk_management.py",
        "scripts/optimization/run_phase40_optimization.py",
        "scripts/testing/validate_model_consistency.py",
        "src/core/execution/backtest_runner.py",
        "src/core/reporting/discord_notifier.py",
        "src/core/services/dynamic_strategy_selector.py",
        "src/data/bitbank_client.py",
        "src/strategies/implementations/bb_reversal.py",
        "src/trading/execution/executor.py",
        "src/trading/position/cleanup.py",
    ]

    total_fixes = 0
    for file_path_str in error_files:
        file_path = Path(file_path_str)
        if file_path.exists():
            fixes = fix_f541_in_file(file_path)
            total_fixes += fixes

    print(f"\n📊 合計: {total_fixes}箇所修正完了")


if __name__ == "__main__":
    main()

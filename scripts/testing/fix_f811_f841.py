#!/usr/bin/env python3
"""
F811・F841エラー自動修正スクリプト - Phase 52.3

F811: 重複import削除
F841: 未使用変数削除（コメント化）
"""

from pathlib import Path


def fix_backtest_runner():
    """src/core/execution/backtest_runner.py修正"""
    file_path = Path("src/core/execution/backtest_runner.py")

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Line 257: tf_start未使用（コメント化）
    for i, line in enumerate(lines):
        if i + 1 == 257 and "tf_start =" in line:
            lines[i] = line.replace("tf_start = ", "# 未使用: tf_start = ")

        # Line 938: strategy_name未使用（コメント化）
        if i + 1 == 938 and "strategy_name =" in line:
            lines[i] = line.replace("strategy_name = ", "# 未使用: strategy_name = ")

        # Line 945: current_balance未使用（コメント化）
        if i + 1 == 945 and "current_balance =" in line:
            lines[i] = line.replace("current_balance = ", "# 未使用: current_balance = ")

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"✅ {file_path}: 3箇所修正（未使用変数コメント化）")


def fix_market_regime_classifier():
    """src/core/services/market_regime_classifier.py修正"""
    file_path = Path("src/core/services/market_regime_classifier.py")

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Line 97: donchian_width未使用（コメント化）
    for i, line in enumerate(lines):
        if i + 1 == 97 and "donchian_width =" in line:
            lines[i] = line.replace("donchian_width = ", "# 未使用: donchian_width = ")

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"✅ {file_path}: 1箇所修正（未使用変数コメント化）")


def fix_bitbank_client():
    """src/data/bitbank_client.py修正（重複asyncio import削除）"""
    file_path = Path("src/data/bitbank_client.py")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Line 17でget_thresholdをインポート済み、後続の重複importを削除
    lines = content.split("\n")
    modified_lines = []

    for i, line in enumerate(lines):
        line_num = i + 1

        # Line 222, 340: 重複asyncio import削除
        if line_num in [222, 340] and "import asyncio" in line and line.strip().startswith("import asyncio"):
            modified_lines.append(f"# 削除: 重複import asyncio（line {line_num}）")
            continue

        # Line 785, 1452: 重複get_threshold import削除
        if line_num in [785, 1452] and "from" in line and "get_threshold" in line:
            modified_lines.append(f"# 削除: 重複import get_threshold（line {line_num}）")
            continue

        # Line 963: f-string placeholder missing（既に修正済みの可能性）
        modified_lines.append(line)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(modified_lines))

    print(f"✅ {file_path}: 4箇所修正（重複import削除）")


def fix_stop_manager():
    """src/trading/execution/stop_manager.py修正"""
    file_path = Path("src/trading/execution/stop_manager.py")

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        # Line 693: price_change_threshold未使用（コメント化）
        if i + 1 == 693 and "price_change_threshold =" in line:
            lines[i] = line.replace("price_change_threshold = ", "# 未使用: price_change_threshold = ")

        # Line 938: 重複timedelta import削除
        if i + 1 == 938 and "from datetime import" in line and "timedelta" in line:
            lines[i] = "# 削除: 重複import timedelta（line 938）\n"

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"✅ {file_path}: 2箇所修正（未使用変数コメント化・重複import削除）")


def fix_risk_sizer():
    """src/trading/risk/sizer.py修正（重複get_threshold import削除）"""
    file_path = Path("src/trading/risk/sizer.py")

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        # Line 59, 134: 重複get_threshold import削除
        if (i + 1 == 59 or i + 1 == 134) and "from" in line and "get_threshold" in line:
            lines[i] = f"# 削除: 重複import get_threshold（line {i + 1}）\n"

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"✅ {file_path}: 2箇所修正（重複import削除）")


def fix_ml_meta_learning():
    """src/ml/meta_learning.py修正（未使用変数e削除）"""
    file_path = Path("src/ml/meta_learning.py")

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        # Line 110: except Exception as e → except Exception（未使用）
        if i + 1 == 110 and "except Exception as e:" in line:
            lines[i] = line.replace("except Exception as e:", "except Exception:  # 未使用変数e削除")

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"✅ {file_path}: 1箇所修正（未使用変数削除）")


def fix_archive_files():
    """archive内のファイル修正（重要度低）"""
    # trading/archive/execution_service.py
    file_path = Path("src/trading/archive/execution_service.py")
    if not file_path.exists():
        return

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        # Line 446, 925, 1129, 1215, 1674, 1773: 重複asyncio import削除
        if (i + 1 in [446, 925, 1129, 1215, 1674, 1773]) and "import asyncio" in line:
            lines[i] = f"# 削除: 重複import asyncio（line {i + 1}）\n"

        # Line 1015: price_change_threshold未使用
        if i + 1 == 1015 and "price_change_threshold =" in line:
            lines[i] = line.replace("price_change_threshold = ", "# 未使用: price_change_threshold = ")

    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"✅ {file_path}: 7箇所修正（archive）")

    # trading/archive/risk_manager.py
    file_path = Path("src/trading/archive/risk_manager.py")
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for i, line in enumerate(lines):
            if i + 1 == 1279 and "reserve_ratio =" in line:
                lines[i] = line.replace("reserve_ratio = ", "# 未使用: reserve_ratio = ")

        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        print(f"✅ {file_path}: 1箇所修正（archive）")

    # trading/archive/risk_monitor.py
    file_path = Path("src/trading/archive/risk_monitor.py")
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        for i, line in enumerate(lines):
            if (i + 1 in [1146, 1217]) and "current_loop =" in line:
                lines[i] = line.replace("current_loop = ", "# 未使用: current_loop = ")

        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

        print(f"✅ {file_path}: 2箇所修正（archive）")


def main():
    print("🔧 F811・F841エラー修正開始...\n")

    fix_backtest_runner()
    fix_market_regime_classifier()
    fix_bitbank_client()
    fix_stop_manager()
    fix_risk_sizer()
    fix_ml_meta_learning()
    fix_archive_files()

    print("\n📊 F811・F841エラー修正完了")


if __name__ == "__main__":
    main()

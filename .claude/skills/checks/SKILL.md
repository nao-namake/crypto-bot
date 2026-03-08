---
name: checks
description: コミット前の品質チェック。テスト・カバレッジ・flake8・black・isortを実行
allowed-tools: Bash
---

# Pre-commit Quality Check

`bash scripts/testing/checks.sh` を実行し、結果を報告する。

## 手順

1. `bash scripts/testing/checks.sh` を実行
2. 結果を以下の形式で報告:
   - テスト: 成功数 / 失敗数
   - カバレッジ: XX%（75%以上が基準）
   - flake8: PASS / FAIL
   - black: PASS / FAIL
   - isort: PASS / FAIL
3. 失敗がある場合は原因を特定し、修正案を提示

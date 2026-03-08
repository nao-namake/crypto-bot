---
name: backtest
description: GitHub Actionsでバックテストを実行し、完了を監視する
allowed-tools: Bash
argument-hint: [days]
---

# Backtest Execution (GitHub Actions)

## 手順

1. GitHub Actionsワークフローを手動実行:
   - 引数なし: `gh workflow run backtest.yml`（デフォルト180日）
   - 日数指定: `gh workflow run backtest.yml -f backtest_days=$0`
2. `gh run list --workflow=backtest.yml --limit 1` で実行IDを取得
3. `gh run watch <run-id>` で完了まで監視
4. 完了後、結果を報告:
   - ステータス: success / failure
   - Artifactの有無
5. 失敗時:
   - `gh run view <run-id> --log-failed` で失敗ログを取得
   - 原因を分析し修正案を提示

## 使用例

- `/backtest` - デフォルト180日
- `/backtest 30` - 直近30日
- `/backtest 365` - 直近365日

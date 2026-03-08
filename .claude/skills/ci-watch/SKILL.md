---
name: ci-watch
description: GitHub ActionsのCI実行を監視し、結果を報告する。プッシュ後のCI確認に使用
allowed-tools: Bash
---

# CI Monitor

## 手順

1. `gh run list --limit 3` で最新のCI実行を確認
2. 実行中のrunがあれば `gh run watch` で完了まで監視
3. 完了後、結果を報告:
   - 全体ステータス: success / failure
   - 各ジョブの結果
4. 失敗がある場合:
   - `gh run view --log-failed` で失敗ログを取得
   - 失敗原因を分析し、修正案を提示

#!/usr/bin/env bash
# =============================================================================
# ファイル名: scripts/git_push.sh
# 説明:
#   - 変更を一括でステージング → コミット → プッシュ する簡易ラッパー。
#   - 引数にコミットメッセージを渡すとそのまま commit -m へ使用。
#   - 省略時は "chore: update" でコミット。
#   - 現在のブランチを自動判定し、`origin/<branch>` へ push。
#   - 例: bash scripts/git_push.sh "feat: add new strategy"
# =============================================================================
set -euo pipefail

# コミットメッセージ（デフォルト）
msg=${1:-"chore: update"}

# 現在のブランチ名を取得
branch=$(git rev-parse --abbrev-ref HEAD)

# 変更をすべてステージング → コミット → プッシュ
git add -A
git commit -m "$msg"
git push -u origin "$branch"

echo "🎉  Pushed '$branch' with message: \"$msg\""
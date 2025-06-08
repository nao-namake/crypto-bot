#!/usr/bin/env bash
# =============================================================================
# ファイル名: scripts/auto_push.sh
# 説明:
#   - 依存のインストール → コード整形 → Lint／UnitTest → Git push を自動化
#   - 使い方:
#       bash scripts/auto_push.sh "feat: add new algo"
#       bash scripts/auto_push.sh --install "chore: clean & format"
#   - 引数:
#       --install   : requirements-dev.txt を再インストールしてから実行
#       --help      : このヘルプを表示
#       <commit msg>: コミットメッセージ（省略時は "chore: update"、複数単語可）
# =============================================================================
set -euo pipefail
IFS=$'\n\t'

# ------------------------------------------------------------
# 0. オプション解析
# ------------------------------------------------------------
install_deps=false
commit_msg_parts=()
for arg in "$@"; do
  case "$arg" in
    --install)
      install_deps=true
      ;;
    --help)
      echo "Usage: bash scripts/auto_push.sh [--install] [commit message]"
      exit 0
      ;;
    *)
      commit_msg_parts+=("$arg")
      ;;
  esac
done

# デフォルトのコミットメッセージ
if [ ${#commit_msg_parts[@]} -eq 0 ]; then
  commit_msg="chore: update"
else
  # 空白を含むコミットメッセージをサポート
  commit_msg="${commit_msg_parts[*]}"
fi

# ------------------------------------------------------------
# 1. 依存インストール（必要なら）
# ------------------------------------------------------------
if $install_deps; then
  echo "📦  Installing dev dependencies ..."
  python -m pip install --upgrade pip
  pip install -r requirements-dev.txt
  pip install -e .
fi

# ------------------------------------------------------------
# 2. 一括整形 (isort / black)
# ------------------------------------------------------------
echo "🧹  Running isort & black ..."
isort .
black .

# ------------------------------------------------------------
# 3. Lint / Test / Coverage
# ------------------------------------------------------------
echo "🧪  Running checks.sh ..."
./scripts/checks.sh

# ------------------------------------------------------------
# 4. Git add / commit / push
# ------------------------------------------------------------
branch=$(git rev-parse --abbrev-ref HEAD)
echo "🚀  Committing & pushing to origin/$branch ..."
git add -A

# ステージされた変更があるかチェック
if git diff --cached --quiet; then
  echo "✅  No changes to commit."
else
  git commit -m "$commit_msg"
  git push -u origin "$branch"
  echo "✅  Done! Pushed '$branch' with message: \"$commit_msg\""
fi
---
name: commit
description: git add . で全ファイルをステージし、コミットメッセージを作成してコミット・プッシュする
allowed-tools: Bash
---

# Git Commit & Push

## 手順

1. `git status` で変更内容を確認
2. `git diff` と `git diff --staged` で差分を確認
3. `git log --oneline -5` で直近のコミットスタイルを確認
4. 変更内容に基づき、適切なコミットメッセージを作成
   - prefix: fix / feat / docs / refactor / test / chore
   - 日本語で簡潔に内容を記述
5. ユーザーにコミットメッセージを提示し、承認を得る
6. 承認後、以下を実行:
   ```bash
   git add . && git commit -m "メッセージ" && git push origin main
   ```
7. `git status` でコミット成功を確認

## 注意

- `git add .` を必ず使用（個別add禁止）
- .envや機密ファイルが含まれていないか確認
- push先は `origin main`

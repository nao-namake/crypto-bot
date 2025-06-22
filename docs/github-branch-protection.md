# GitHubブランチ保護ルール設定手順書

このドキュメントでは、crypto-botリポジトリでのコードレビューとブランチ保護ルールの設定手順を説明します。

## 🎯 概要

ブランチ保護ルールを設定することで、以下の品質管理を自動化できます：
- mainブランチへの直接プッシュを禁止
- Pull Requestでのコードレビューを必須化
- 自動テストの合格を必須化
- コード品質チェックの強制

## 📋 前提条件

- GitHubリポジトリの管理者権限が必要
- 以下のワークフローが設定済みであること：
  - `.github/workflows/ci.yml` (メインCI)
  - `.github/workflows/code-review.yml` (コードレビュー支援)

## 🔧 設定手順

### 1. GitHubリポジトリ設定画面へアクセス

1. GitHubリポジトリページを開く
2. **Settings** タブをクリック
3. 左サイドバーから **Branches** を選択

### 2. ブランチ保護ルールの作成

1. **Add branch protection rule** ボタンをクリック
2. **Branch name pattern** に `main` を入力

### 3. 基本保護設定

以下の項目にチェックを入れます：

#### ✅ Restrict pushes that create files larger than 100 MB
大きなファイルの誤commitを防止

#### ✅ Require a pull request before merging
- **Require approvals**: `1` (最低1人の承認が必要)
- **Dismiss stale reviews when new commits are pushed**: ✅
- **Require review from code owners**: ✅ (CODEOWNERSファイルがある場合)
- **Restrict reviews to users with read access**: ✅

#### ✅ Require status checks to pass before merging
- **Require branches to be up to date before merging**: ✅

必須ステータスチェックを追加：
```
Unit Tests (3.11)
Unit Tests (3.12)
Bybit Testnet E2E
Build & Push Docker Image
Code Quality Check
Security Scan
```

#### ✅ Require conversation resolution before merging
未解決のコメントがある場合はマージを禁止

#### ✅ Require signed commits (推奨)
セキュリティ強化のため

#### ✅ Require linear history
マージコミットを禁止してクリーンな履歴を維持

#### ✅ Do not allow bypassing the above settings
管理者も保護ルールを遵守

### 4. 管理者設定 (オプション)

#### Include administrators
管理者にもルールを適用する場合はチェック

#### Allow force pushes
通常は無効にすることを推奨

#### Allow deletions
mainブランチの削除を禁止

### 5. 保存

**Create** または **Save changes** をクリックして設定を保存

## 🔍 追加設定: CODEOWNERSファイル

### CODEOWNERSファイルの作成

リポジトリルートに `.github/CODEOWNERS` ファイルを作成：

```
# Global owners
* @your-username

# Core components
crypto_bot/main.py @your-username @lead-developer
crypto_bot/strategy/ @strategy-team
crypto_bot/ml/ @ml-team
crypto_bot/execution/ @trading-team

# Infrastructure
infra/ @devops-team
.github/workflows/ @devops-team
Dockerfile @devops-team

# Configuration
config/ @config-team
*.yml @config-team

# Documentation
*.md @docs-team
docs/ @docs-team

# Security-critical files
.env.example @security-team
crypto_bot/execution/ @security-team @trading-team
```

### CODEOWNERSの効果

- 指定されたファイルの変更時、該当オーナーのレビューが必須
- 自動的にレビュアーとして指定されるユーザーを設定
- 責任範囲を明確化

## 🚨 緊急時のブランチ保護解除手順

### 緊急時の一時的な保護解除

1. **Settings** → **Branches** → 対象ルールの **Edit**
2. 一時的に必要な保護を無効化
3. 緊急対応完了後、**必ず保護を再有効化**

### 緊急対応の記録

緊急時には以下を記録：
- 対応者
- 解除理由
- 解除期間
- 再有効化確認

## 📊 保護ルール監査

### 定期確認項目

月次で以下を確認：
- [ ] 保護ルールが意図通り動作しているか
- [ ] 必須ステータスチェックが最新のワークフローと一致しているか
- [ ] CODEOWNERSが組織体制と一致しているか
- [ ] バイパス履歴の確認

### メトリクス監視

以下の情報を監視：
- Pull Request承認率
- レビュー所要時間
- ステータスチェック失敗率
- 緊急バイパス使用頻度

## 🔧 トラブルシューティング

### よくある問題と解決策

#### 1. ステータスチェックが表示されない
- ワークフローが最低1回実行されていることを確認
- ブランチ名やジョブ名が正確に入力されているか確認

#### 2. 承認者が足りない
- CODEOWNERSファイルの設定を確認
- 該当ユーザーがリポジトリへのアクセス権を持っているか確認

#### 3. レビューが自動で要求されない
- CODEOWNERSファイルの構文を確認
- ファイルパスのパターンマッチングを確認

#### 4. 管理者がルールをバイパスできない
- "Do not allow bypassing the above settings" の設定を確認
- 必要に応じて一時的に無効化

## 📚 参考資料

- [GitHub Branch Protection Rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-protected-branches)
- [CODEOWNERS Syntax](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
- [Status Checks](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/about-status-checks)

## ✅ 設定完了後の確認

以下の動作をテストして設定が正しく動作することを確認：

1. **新しいブランチでPRを作成**
   ```bash
   git checkout -b test-branch-protection
   echo "test" > test-file.txt
   git add test-file.txt
   git commit -m "test: branch protection test"
   git push origin test-branch-protection
   ```

2. **PRでの動作確認**
   - PRが作成できること
   - 必須ステータスチェックが実行されること
   - 承認なしではマージできないこと
   - 承認後にマージできること

3. **直接プッシュの禁止確認**
   ```bash
   git checkout main
   echo "test" >> README.md
   git add README.md
   git commit -m "test: direct push test"
   git push origin main  # これは失敗するはず
   ```

設定が完了すると、コードの品質と安全性が大幅に向上します。
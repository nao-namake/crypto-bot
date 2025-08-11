# scripts/ci_tools/ - CI/CD前ツール

## 📋 概要

CI/CDパイプライン実行前に使用する品質チェック・検証ツールを管理するディレクトリです。  
コミット前・デプロイ前の必須チェックツールを集約しています。

## 🎯 ツール一覧

### **checks.sh** ⭐ 必須
品質チェック統合実行スクリプト（flake8・isort・black・pytest）

```bash
# コミット前に必ず実行
bash scripts/ci_tools/checks.sh
```

**チェック内容:**
- flake8: Pythonコード品質
- isort: import文の整列
- black: コードフォーマット
- pytest: ユニットテスト実行

### **validate_all.sh** ⭐ 必須
3段階検証システム

```bash
# フル検証（〜10分）
bash scripts/ci_tools/validate_all.sh

# 高速検証（Level 1のみ、〜1分）
bash scripts/ci_tools/validate_all.sh --quick

# CI用（Level 1+2、〜3分）
bash scripts/ci_tools/validate_all.sh --ci
```

**検証レベル:**
- Level 1: 静的解析（checks.sh）
- Level 2: 未来データリーク検出
- Level 3: 動的検証（ペーパートレード・監視）

### **pre_deploy_validation.py**
デプロイ前の統合検証Python版

```bash
python scripts/ci_tools/pre_deploy_validation.py
```

**機能:**
- 未来データリーク検出
- ペーパートレード実行
- シグナルモニタリング
- ユニットテスト実行
- HTMLレポート生成

### **auto_push.sh**
自動Git push（整形・テスト・プッシュ）

```bash
bash scripts/ci_tools/auto_push.sh "feat: your commit message"
```

**実行内容:**
1. black/isort 自動整形
2. checks.sh 実行
3. git add -A
4. git commit
5. git push

### **deploy_with_initial_data.sh**
初期データ付きデプロイスクリプト

```bash
bash scripts/ci_tools/deploy_with_initial_data.sh
```

**実行内容:**
1. 初期データキャッシュ準備
2. Dockerビルド・テスト
3. Git commit/push
4. CI/CD自動トリガー

### **テスト実行スクリプト**
- `run_all_local_tests.sh` - ローカル環境での包括的テスト
- `run_e2e.sh` - エンドツーエンドテスト
- `run_pipeline.sh` - パイプライン実行
- `run_production_tests.sh` - 本番環境テスト

### **validate_97_features_optimization.py**
97特徴量システムの最適化検証

```bash
python scripts/ci_tools/validate_97_features_optimization.py
```

## 💡 推奨ワークフロー

### **デイリー開発フロー**

```bash
# 1. 開発前の状態確認
python scripts/bot_manager.py status

# 2. コード変更後の高速チェック
bash scripts/ci_tools/checks.sh

# 3. コミット前の検証
bash scripts/ci_tools/validate_all.sh --quick

# 4. コミット＆プッシュ
bash scripts/ci_tools/auto_push.sh "feat: 機能追加"
```

### **リリース前フロー**

```bash
# 1. フル検証実行
bash scripts/ci_tools/validate_all.sh

# 2. 問題があれば修正
python scripts/bot_manager.py fix-errors

# 3. 再検証
bash scripts/ci_tools/validate_all.sh

# 4. デプロイ
git push origin main
```

## ⚠️ 注意事項

- **checks.sh** は最低限のチェック。必ず実行すること
- **validate_all.sh** は時間がかかるが、本番デプロイ前は必須
- **auto_push.sh** は自動でpushするため、慎重に使用すること

---

*最終更新: 2025年8月11日 - フォルダ整理実施*
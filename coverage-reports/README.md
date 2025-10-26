# coverage-reports/ - カバレッジレポート管理

## 📂 役割

テストカバレッジ測定結果の格納・管理を行います。**Phase 49完了時点で68.32%カバレッジを達成**し、品質保証の重要指標として機能しています。

## 📋 ディレクトリ構成

```
coverage-reports/
├── .gitkeep           # ディレクトリ保持用
├── .coverage          # カバレッジデータファイル（自動生成・.gitignore除外）
└── htmlcov/          # HTMLレポート（自動生成・.gitignore除外）
    ├── index.html    # メインダッシュボード
    └── *.html        # 各モジュール詳細分析
```

**注意**: `.coverage`と`htmlcov/`はテスト実行時に自動生成されます。Gitリポジトリには含まれません。

## 🔧 使用方法

### カバレッジ測定実行

```bash
# 推奨：統合品質チェック（1,117テスト・68.32%カバレッジ）
bash scripts/testing/checks.sh

# HTMLレポート閲覧
open coverage-reports/htmlcov/index.html
```

### レポート確認内容

- **全体カバレッジ**: 68.32%（Phase 49完了）
- **テスト数**: 1,117テスト（100%成功）
- **対象**: `src/`配下全モジュール
- **詳細分析**: 各ファイル・関数レベルのカバレッジ

## ⚙️ 管理ルール

- **自動生成**: テスト実行時に`pytest-cov`が自動生成
- **品質目標**: 68.32%以上維持（Phase 49基準）
- **Git管理**: `.coverage`と`htmlcov/`は`.gitignore`で除外
- **CI/CD**: GitHub Actions品質ゲートとして活用
- **クリーンアップ**: 不要時は`rm -rf htmlcov/ .coverage`で削除可能

## 🔗 関連ファイル

- `scripts/testing/checks.sh`: カバレッジ生成スクリプト
- `pyproject.toml`: pytest・coverage設定
- `.github/workflows/ci.yml`: CI/CD統合・品質ゲート
- `.gitignore`: カバレッジファイル除外設定

---

**最終更新**: 2025/10/25 - Phase 49完了（1,117テスト・68.32%カバレッジ達成）
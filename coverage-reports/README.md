# coverage-reports/ - カバレッジレポート管理

## 📂 役割

テストカバレッジ測定結果の格納・管理を行います。現在64.74%カバレッジを達成し、品質保証の重要指標として機能しています。

## 📋 ファイル構成

```
coverage-reports/
├── .coverage           # カバレッジデータファイル（pytest-cov生成）
├── .gitkeep           # ディレクトリ保持用
└── htmlcov/          # HTMLレポート（116ファイル）
    ├── index.html    # メインダッシュボード
    └── *.html        # 各モジュール詳細分析
```

## 🔧 使用方法

### カバレッジ測定実行
```bash
# 推奨：統合品質チェック
bash scripts/testing/checks.sh

# HTMLレポート閲覧
open coverage-reports/htmlcov/index.html
```

## ⚙️ 管理ルール

- **更新**: テスト実行時に自動生成
- **対象**: `src/`配下全体
- **品質目標**: 64.74%以上維持
- **Git管理**: HTMLファイルは`.gitignore`で除外
- **CI/CD**: 品質ゲートとして活用

## 🔗 関連

- `scripts/testing/checks.sh`: カバレッジ生成スクリプト
- `pyproject.toml`: pytest・coverage設定
- `.github/workflows/ci.yml`: CI/CD統合
# coverage-reports/ - テストカバレッジレポート管理

## 🎯 役割・責任

テストカバレッジの測定・分析・継続的改善を担当します。src/全域の品質を可視化し、テスト漏れ防止・コード品質向上・安全なリファクタリングを支援します。

## 📂 ファイル構成

```
coverage-reports/
├── README.md           # このファイル
├── .coverage           # カバレッジデータファイル（バイナリ）
├── .gitkeep            # Gitディレクトリ保持用
└── htmlcov/           # HTMLカバレッジレポート
    ├── index.html     # メインダッシュボード
    ├── status.json    # カバレッジメタデータ
    ├── *.css, *.js    # レポート用UI/UXファイル
    └── *.html         # 各モジュール詳細レポート
```

## 📋 各ファイル・フォルダの役割

### **.coverage**
pytest-covによって生成されるバイナリカバレッジデータファイルです。
- テスト実行時の行単位カバレッジ情報を格納
- HTMLレポート生成の元データ
- CI/CDでの自動測定結果を保存

### **htmlcov/**
HTMLフォーマットのカバレッジレポートが格納されるディレクトリです。
- `index.html`: プロジェクト全体のカバレッジダッシュボード
- `status.json`: カバレッジ統計情報（JSON形式）
- 個別ファイル: 各ソースファイルの詳細カバレッジ分析
- CSS/JSファイル: インタラクティブなレポートUI

### **.gitkeep**
空のディレクトリをGitで管理するための保持ファイルです。

## 📝 使用方法・例

### **カバレッジ測定の実行**
```bash
# 推奨：統合品質チェック（テスト + カバレッジ）
bash scripts/testing/checks.sh

# 直接実行
python3 -m pytest tests/ --cov=src --cov-report=html:coverage-reports/htmlcov --cov-report=term

# 特定モジュールのカバレッジ測定
python3 -m pytest tests/unit/core/ --cov=src/core --cov-report=term -v
```

### **HTMLレポートの閲覧**
```bash
# メインダッシュボードを開く
open coverage-reports/htmlcov/index.html

# 統計データの確認
cat coverage-reports/htmlcov/status.json | python3 -m json.tool

# カバレッジ情報をターミナルで確認
python3 -m coverage report
```

### **CI/CDでの自動実行**
```bash
# コードをプッシュすると自動でカバレッジ測定実行
git add .
git commit -m "テスト改善"
git push origin main
# → GitHub Actionsが自動でテスト実行 + カバレッジ測定
```

## ⚠️ 注意事項・制約

### **測定対象・除外設定**
- **測定対象**: `src/` 配下の全Pythonファイル
- **除外対象**: `tests/`, `scripts/`, `config/` ディレクトリ
- **レポート生成**: HTMLフォーマットでの詳細分析対応

### **データ管理**
- **更新頻度**: テスト実行時に自動更新
- **ファイル保持**: `.coverage`と`htmlcov/`は最新のみ保持
- **Git管理**: HTMLレポートは`.gitignore`で除外済み

### **品質目標**
- **目標カバレッジ**: 50%以上を維持
- **継続改善**: 定期的なテスト追加によるカバレッジ向上
- **品質保証**: CI/CDでの自動品質ゲート

## 🔗 関連ファイル・依存関係

### **テスト実行システム**
- `scripts/testing/checks.sh`: 統合品質チェックスクリプト
- `scripts/testing/dev_check.py`: 開発用品質診断
- `tests/`: テストファイル群
- `pyproject.toml`: pytest・coverage設定

### **CI/CD連携**
- `.github/workflows/ci.yml`: CI/CDパイプライン
- `src/`: カバレッジ測定対象のソースコード
- `.gitignore`: HTMLレポートのGit除外設定

### **品質管理**
- 自動品質ゲート：テスト失敗時のデプロイ停止
- 継続監視：カバレッジ低下時のアラート
- レポート分析：コード品質の継続的改善
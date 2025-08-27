# scripts/testing/ - テスト・品質保証

**Phase 13対応**: 統合品質チェック・テスト・品質保証（2025年8月26日現在）

## 📂 ファイル構成

```
testing/
├── checks.sh               # 統合品質チェック
└── test_live_trading.py    # ライブトレード統合テスト
└── README.md               # このファイル
```

## 🎯 役割・責任

テスト・品質保証として以下を提供：
- **統合品質チェック**: pytest・flake8・black・isort統合実行
- **ライブテスト**: 本番環境動作検証・リスク管理・安全性確認
- **CI/CD統合**: GitHub Actions・自動化ワークフロー・品質ゲート
- **品質保証**: 継続的品質管理・回帰防止・メトリクス測定

## ✅ 主要機能・実装

### **checks.sh**: 統合品質チェック
- 306テスト実行・全ディレクトリ対象・カバレッジ測定
- flake8コードスタイル・black自動整形・isortインポート整理
- CI/CD統合・GitHub Actions対応・品質ゲート

### **test_live_trading.py**: ライブトレード統合テスト
- 実取引環境テスト・最小取引単位・安全性確認
- BitbankAPI接続・注文実行・リスク管理テスト
- 単発・連続・24時間監視テストモード

## 🔧 使用方法・例

### **統合品質チェック（checks.sh）**
```bash
# 基本的な品質チェック実行
bash scripts/testing/checks.sh

# 詳細出力
VERBOSE=1 bash scripts/testing/checks.sh

# 特定チェックスキップ
SKIP_TESTS=1 bash scripts/testing/checks.sh      # テストスキップ
SKIP_FORMAT=1 bash scripts/testing/checks.sh     # フォーマットスキップ
SKIP_LINT=1 bash scripts/testing/checks.sh       # lintスキップ
```

### **ライブトレードテスト（test_live_trading.py）**
```bash
# 単発注文テスト
python scripts/testing/test_live_trading.py --mode single

# 連続取引テスト
python scripts/testing/test_live_trading.py --mode continuous --duration 2

# 24時間監視テスト
python scripts/testing/test_live_trading.py --mode monitoring
```

### **期待結果**
```
✅ 306テスト全合格 (100%)
✅ flake8チェック合格 (0 issues)
✅ blackフォーマット合格 (formatted)
✅ isortインポート整理完了
✅ カバレッジ: 58.88% (target achieved)
```

## ⚠️ 注意事項・制約

### **実行環境制約**
1. **プロジェクトルート**: 必ず`/Users/nao/Desktop/bot`から実行
2. **Python環境**: pytest・flake8・black・isort・カバレッジライブラリ必須
3. **実行時間**: checks.sh約30-60秒・ライブテスト数分-数時間
4. **権限**: ライブテスト時BitbankAPI認証・実取引権限必要

### **品質基準**
- **テスト成功率**: 306テスト100%合格必須
- **コードスタイル**: flake8エラー0件
- **フォーマット**: black・isort準拠
- **カバレッジ**: 58%以上維持

### **ライブテスト制約**
- **最小取引**: 0.0001 BTC・安全性優先
- **残高要件**: 最低10,000円以上
- **API制限**: レート制限・日次制限考慮
- **リスク管理**: 損切り・利確設定必須

## 🔗 関連ファイル・依存関係

### **システム統合**
- **scripts/management/**: dev_check.py品質チェック統合・自動実行
- **src/**: 新システム実装・テスト対象・品質確認
- **.github/workflows/**: GitHub Actions・CI/CD・自動品質チェック

### **設定・ログ**
- **coverage-reports/**: テストカバレッジ・HTMLレポート・品質指標
- **logs/**: テスト実行ログ・品質チェック結果・エラーログ
- **config/**: テスト設定・品質基準・環境設定

### **外部依存**
- **pytest**: テストフレームワーク・テストランナー・アサーション
- **flake8**: コードスタイルチェック・構文解析・品質評価
- **black・isort**: コードフォーマット・インポート整理・一貫性
- **BitbankAPI**: ライブテスト・実取引検証・API接続テスト

---

**🎯 Phase 13対応完了**: 統合品質チェック・ライブテスト・継続的品質保証により高品質なシステム開発環境を実現。
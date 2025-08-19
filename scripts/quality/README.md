# Quality Assurance Scripts

品質保証・チェック系スクリプト集（Phase 11 CI/CD統合・軽量チェック統合管理CLI化）

## 📂 スクリプト一覧

### checks.sh
**完全品質チェックスクリプト（Phase 11対応・CI/CD統合）**

新システムの包括的品質チェックを実行。flake8・isort・black・pytest・カバレッジ・CI/CD統合を実行。

#### 機能詳細
- **flake8**: コードスタイルチェック（PEP8違反検出・100行制限・CI/CD統合）
- **isort**: import順序チェック（自動修正なし・--check-only・GitHub Actions対応）
- **black**: コード整形チェック（自動修正なし・--check・CI/CD品質ゲート）
- **pytest**: 399テスト実行・80%カバレッジ目標・CI/CD自動実行
- **手動テスト**: Phase 2データ層基盤確認・統合テスト・CI/CD事前チェック

#### 使用例
```bash
# 完全品質チェック実行
bash scripts/quality/checks.sh

# 期待結果:
# ✅ flake8: PASS
# ✅ isort: PASS  
# ✅ black: PASS
# ✅ pytest: PASS (399テスト・80%カバレッジ)
```

#### チェック対象
```bash
# テスト実行範囲
tests/unit/strategies/  # 戦略113テスト
tests/unit/ml/         # ML89テスト  
tests/unit/backtest/   # バックテスト84テスト
tests/unit/trading/    # リスク管理113テスト
```

### 軽量品質チェック（統合管理CLI経由・Phase 11統合）
**統合管理CLI経由軽量チェック（Phase 11統合・checks_light.sh削除対応）**

基本的な動作確認・テスト実行に特化した軽量版チェック。統合管理CLIに統合済み。

#### 機能詳細
- **ディレクトリ構造確認**: src/存在・基本構造検証・CI/CD対応
- **MLモデル確認**: production_ensemble.pkl存在確認・メタデータ検証
- **基本インポートテスト**: 主要コンポーネント動作確認・依存関係チェック
- **399テスト実行**: 軽量版（--maxfail=5・--disable-warnings・99.7%成功実績）
- **手動テスト確認**: Phase 2テスト結果確認・統合テスト・CI/CD事前チェック

#### 使用例（統合管理CLI経由・推奨）
```bash
# 軽量品質チェック実行（統合管理CLI経由・推奨）
python scripts/management/bot_manager.py validate --mode light

# 期待結果:
# ✅ 398/399テスト成功（99.7%）
# 🎉 軽量品質チェック完了！
# 🚀 Phase 11システム対応・CI/CD統合
```

#### 実行時間
- **軽量版**: 約30秒（統合管理CLI経由）
- **完全版**: 約2-5分（カバレッジ計測含む・CI/CD統合）

## 🎯 設計原則

### 品質保証哲学
- **段階的チェック**: 構造→インポート→スタイル→テスト
- **早期失敗**: エラー検出時点で即座に停止
- **包括的カバレッジ**: 399テスト全範囲対応
- **実行効率**: 軽量/完全モードの使い分け

### エラーハンドリング
- **詳細エラー表示**: 失敗箇所の明確な特定
- **修正方法提示**: 自動修正コマンドの提案
- **継続可能設計**: 一部失敗でも結果表示

## 🔧 使い分けガイド

### 軽量品質チェック（推奨：日常開発）
**統合管理CLI経由**: `python scripts/management/bot_manager.py validate --mode light`

**用途**: 
- 日常の開発作業での基本確認
- CI/CD パイプラインの前段チェック
- 迅速な動作確認が必要な場面
- Phase 11 統合システム対応

**メリット**:
- ⚡ 高速実行（30秒）
- 🎯 基本品質保証
- 💻 開発効率重視
- 🚀 CI/CD統合・統合管理CLI統合

### checks.sh（推奨：デプロイ前）
**用途**:
- デプロイ前の完全品質保証
- Phase完了時の品質確認
- 本番環境移行前の最終チェック
- GitHub Actions CI/CDパイプライン

**メリット**:
- 🔍 包括的チェック
- 📊 80%カバレッジ確認
- 📝 HTMLレポート生成
- 🚀 CI/CD統合・段階的デプロイ対応

## 📊 品質指標

### 成功基準
- **テスト成功率**: 398/399（99.7%）以上
- **カバレッジ**: 80%以上（完全版のみ）
- **スタイル**: flake8・isort・black全合格
- **実行時間**: 軽量30秒・完全5分以内

### エラー分類
1. **Critical**: テスト失敗・インポートエラー
2. **Warning**: スタイルガイド違反
3. **Info**: カバレッジ不足・推奨事項

## 🛠️ トラブルシューティング

### よくあるエラー

**1. flake8チェック失敗**
```bash
❌ flake8チェック失敗
```
**対処**: スタイル修正
```bash
# エラー箇所確認
python3 -m flake8 src/ tests/ scripts/ --max-line-length=100

# 自動修正（一部）
python3 -m black src/ tests/ scripts/
python3 -m isort src/ tests/ scripts/
```

**2. テスト失敗**
```bash
❌ テスト実行失敗
```
**対処**: 個別テスト確認
```bash
# 失敗テスト特定
python3 -m pytest --maxfail=1 -v

# 特定テストのみ実行
python3 -m pytest tests/unit/strategies/ -v
```

**3. インポートエラー**
```bash
❌ インポートエラー: No module named 'src'
```
**対処**: プロジェクトルートから実行
```bash
cd /Users/nao/Desktop/bot
python scripts/management/bot_manager.py validate --mode light
```

## 📈 Performance Optimization

### 実行時間最適化
- **軽量モード**: 基本チェックのみ・開発効率重視
- **並列実行**: 可能な範囲でテスト並列化
- **キャッシュ活用**: pytest cache・coverage結果保存

### リソース使用量
- **メモリ**: 最大500MB（カバレッジ計測時）
- **CPU**: マルチコア活用（pytest -n auto対応）
- **ディスク**: 一時ファイル最小限・自動クリーンアップ

## 🔮 Future Enhancements

Phase 12以降の拡張予定:
- **type-check**: mypy型チェック統合・CI/CD自動実行・型安全性向上
- **security**: bandit セキュリティスキャン・脆弱性検出・CI/CD統合
- **performance**: pytest-benchmark 性能測定・パフォーマンス回帰検出
- **integration**: 統合テスト自動実行・E2Eテスト・本番環境テスト
- **compliance**: PCI DSS・SOC 2対応・監査ログ・金融規制対応
- **coverage**: より詳細なカバレッジ分析・branch coverage・mutation testing
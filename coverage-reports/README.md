# coverage-reports/ - テストカバレッジレポートディレクトリ

**Phase 13対応**: テストカバレッジ分析・品質保証・CI/CD品質チェック統合・306テスト100%成功対応のカバレッジレポート管理

## 📁 ディレクトリ構造

```
coverage-reports/
├── README.md           # このファイル
├── .coverage          # カバレッジデータ（自動生成）
└── htmlcov/           # HTMLカバレッジレポート（自動生成）
    ├── index.html     # メインカバレッジレポート
    ├── *.html         # 各モジュール詳細レポート
    ├── *.css          # スタイルファイル
    └── *.js           # インタラクティブ機能
```

## 🎯 役割・目的

### **テストカバレッジ管理（Phase 13完了）**
- **目的**: src/配下のコード品質・テストカバレッジ可視化・品質保証統合
- **範囲**: 全Python テストファイル・ユニットテスト・統合テスト・回帰テスト
- **効果**: 品質保証・テスト漏れ防止・コード品質向上・CI/CD統合

### **Phase 13完了成果**
- **306テスト100%成功**: 品質保証完全統合・回帰防止体制確立
- **コードカバレッジ**: 58.88%（継続改善中）
- **品質保証統合**: CI/CD・GitHub Actions・自動品質チェック連携

## 🔧 使用方法

### **カバレッジレポート生成**
```bash
# 基本カバレッジ実行
COVERAGE_FILE=coverage-reports/.coverage python3 -m pytest tests/ --cov=src --cov-report=html:coverage-reports/htmlcov --cov-report=term

# 特定モジュールのカバレッジ
COVERAGE_FILE=coverage-reports/.coverage python3 -m pytest tests/unit/ml/ --cov=src/ml --cov-report=html:coverage-reports/htmlcov

# カバレッジレポート閲覧
open coverage-reports/htmlcov/index.html
```

### **CI/CD統合実行**
```bash
# GitHub Actions経由（自動実行）
git push origin main  # ci.ymlで自動カバレッジ実行

# 品質チェック統合（手動実行）
python scripts/management/dev_check.py validate --mode light
```

### **品質目標（Phase 13基準）**
```yaml
カバレッジ目標:
  現在: 58.88%
  短期目標: 70%（6ヶ月）
  長期目標: 85%（12ヶ月）
  最重要: 80%（本番稼働品質）

重点モジュール:
  - src/ml/: MLモデル品質管理・sklearn警告解消
  - src/strategies/: 取引戦略・リスク管理
  - src/trading/: 注文実行・リアルタイム処理
  - src/core/: システム基盤・設定管理
```

## 📊 カバレッジ分析

### **現在のカバレッジ状況（Phase 13）**

#### **高カバレッジモジュール（✅ 優秀）**
- `src/ml/production/ensemble.py`: 100% （sklearn警告解消完了）
- `src/strategies/base/strategy_manager.py`: 97%
- `src/ml/ensemble/voting.py`: 93%
- `src/strategies/utils/signal_builder.py`: 90%

#### **中カバレッジモジュール（📈 改善中）**
- `src/strategies/implementations/mochipoy_alert.py`: 85%
- `src/strategies/implementations/multi_timeframe.py`: 86%
- `src/trading/anomaly_detector.py`: 87%
- `src/ml/model_manager.py`: 87%

#### **低カバレッジモジュール（🔴 要改善）**
- `src/backtest/data_loader.py`: 14%
- `src/backtest/engine.py`: 26%
- `src/core/orchestrator.py`: 0%（除外設定あり）
- `src/data/bitbank_client.py`: 21%

### **改善優先度（Phase 13対応）**
1. **最優先**: backtest/（バックテスト品質向上）
2. **高優先**: data/（データ層品質向上）
3. **中優先**: features/（特徴量エンジニアリング）
4. **継続**: ml/・strategies/（高品質維持）

## 🚨 管理ルール

### **✅ 保持すべきファイル**
- `htmlcov/`: 最新のHTMLレポート（ブラウザ閲覧用）
- `.coverage`: 最新のカバレッジデータ（追加分析用）
- `status.json`: カバレッジメタデータ（CI/CD連携用）

### **🗑️ 削除対象ファイル**
- **7日以上前のレポート**: 古いhtmlcov/フォルダ
- **一時ファイル**: .coverage.tmp, .coverage.*（一時ファイル）
- **重複データ**: 同じ日付の複数レポート

### **🔄 自動管理（Phase 13統合）**
```bash
# 自動クリーンアップ（週1回実行推奨）
find coverage-reports/ -name "htmlcov_*" -mtime +7 -exec rm -rf {} \; 2>/dev/null
find coverage-reports/ -name ".coverage.*" -mtime +7 -delete 2>/dev/null

# 最新レポート保持確認
ls -la coverage-reports/htmlcov/index.html
```

## 📈 カバレッジ向上戦略

### **Phase 13品質保証統合アプローチ**

#### **1. 段階的改善**
```bash
# Step 1: 低カバレッジモジュール特定
grep -A5 "n_missing.*[5-9][0-9]" coverage-reports/htmlcov/status.json

# Step 2: 該当モジュールのテスト強化
python3 -m pytest tests/unit/backtest/ --cov=src/backtest --cov-report=term

# Step 3: 新テスト追加・品質向上
# tests/unit/backtest/test_*.py ファイル拡充
```

#### **2. CI/CD品質ゲート統合**
```yaml
# .github/workflows/ci.yml 品質基準
quality_gates:
  minimum_coverage: 60%    # 現在: 58.88%
  target_coverage: 70%     # 短期目標
  critical_modules: 80%    # ml/, strategies/, trading/
```

#### **3. 継続監視（Phase 13対応）**
```bash
# 定期実行（月1回）
python3 -c "
import json
with open('coverage-reports/htmlcov/status.json') as f:
    data = json.load(f)
print(f'Overall Coverage: {data.get(\"totals\", {}).get(\"percent_covered\", 0):.1f}%')
print('Phase 13 Quality Goal: 70%')
"
```

## 🔒 セキュリティ・プライバシー

### **機密情報管理**
- **✅ 安全**: ソースコード構造・テスト結果のみ
- **❌ 含まない**: API キー・認証情報・個人データ
- **🔒 注意**: 外部共有時はパス情報に注意

### **Gitignore 管理**
```gitignore
# coverage-reports/ 内容
coverage-reports/.coverage.*     # 一時ファイルは除外
coverage-reports/htmlcov/       # HTMLレポートは除外（サイズ大）
```

## 🚀 Phase 13統合効果

### **品質保証効果**
```
📊 テスト品質: 306テスト100%成功（Phase 13達成）
🎯 カバレッジ監視: 自動化・CI/CD統合・品質ゲート
🔄 継続改善: 月次レビュー・段階的向上・目標設定
🏥 品質保証: 回帰防止・エラー検知・安定性向上
```

### **開発効率向上**
```
⚡ テスト効率: 可視化・優先順位・効果測定
🔧 品質向上: 問題特定・改善計画・継続監視  
📈 生産性: テスト漏れ防止・品質保証・安心開発
💾 保守性: 構造理解・影響分析・安全なリファクタリング
```

---

**重要**: このディレクトリはテストカバレッジの品質保証に重要です。Phase 13の306テスト100%成功を基盤として、継続的な品質向上を目指してください。定期的なクリーンアップと分析により、コード品質の継続的改善を実現します。
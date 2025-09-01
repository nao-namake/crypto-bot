# coverage-reports/ - テストカバレッジレポート管理

**Phase 16-A完了**: テスト品質向上・54.92%カバレッジ達成・619テスト成功・68ファイル対象により、継続的品質改善システムが完成

## 🎯 役割・責任

テストカバレッジの測定・分析・継続的改善を担当します。src/全68ファイルの品質可視化により、テスト漏れ防止・コード品質向上・安全なリファクタリングを支援し、Phase 16-Aの619テスト成功・54.92%カバレッジ基盤を維持します。

## 📂 ファイル構成

```
coverage-reports/
├── README.md           # このファイル（Phase 13完了版）
└── htmlcov/           # HTMLカバレッジレポート（最新：Phase 16-A・8/29更新）
    ├── index.html     # メインカバレッジダッシュボード（54.92%）
    ├── status.json    # カバレッジメタデータ・統計（68ファイル）
    ├── class_index.html    # クラス別カバレッジ分析
    ├── function_index.html # 関数別カバレッジ分析
    ├── *.css, *.js    # UI/UX・インタラクティブ機能（6.3MB）
    └── z_*.html       # 各モジュール詳細レポート（68ファイル対応）
```

## 🔧 主要機能・実装

### **カバレッジ測定システム（Phase 16-A最新版）**

**現在の品質状況（Phase 16-A達成）**:
- **全体カバレッジ**: 54.92% (3,842/6,995行・目標50%を4.92%上回る)
- **テスト対象ファイル**: 68ファイル（src/全域・完全網羅）
- **テスト成功率**: 619/620成功（99.84%・1スキップ）  
- **高品質基盤**: monitoring・strategies・ml中心に品質保証完成

**モジュール別カバレッジ分析**:
```python
# 高カバレッジ（90%以上・品質優秀）
- src/ml/production/ensemble.py: 100%（sklearn警告解消完了）
- src/strategies/base/strategy_manager.py: 97.3%
- src/ml/ensemble/voting.py: 93.0%
- src/strategies/utils/signal_builder.py: 89.6%

# 中カバレッジ（70-89%・継続改善）
- src/trading/anomaly_detector.py: 87.2%
- src/ml/model_manager.py: 87.0%
- src/strategies/implementations/multi_timeframe.py: 85.7%

# 要改善（70%未満・優先対応）
- src/backtest/data_loader.py: 14.0%
- src/backtest/engine.py: 25.6%
- src/data/bitbank_client.py: 17.8%
```

### **CI/CD品質ゲート統合**

**GitHub Actions自動実行**:
- 全テスト実行時のカバレッジ自動測定
- HTML レポート自動生成・更新
- 品質低下時の自動アラート

## 📝 使用方法・例

### **基本的なカバレッジ測定**

**全体カバレッジ実行**:
```bash
# 推奨：統合管理CLI経由
python3 scripts/management/dev_check.py validate

# 直接実行
python3 -m pytest tests/ --cov=src --cov-report=html:coverage-reports/htmlcov --cov-report=term
```

**特定モジュールの詳細分析**:
```bash
# 低カバレッジモジュールの改善
python3 -m pytest tests/unit/backtest/ --cov=src/backtest --cov-report=term -v

# 高品質モジュールの維持確認  
python3 -m pytest tests/unit/ml/ --cov=src/ml --cov-report=term -v
```

### **レポート閲覧・分析**

**HTMLダッシュボード**:
```bash
# メインダッシュボード表示
open coverage-reports/htmlcov/index.html

# 統計データ確認
cat coverage-reports/htmlcov/status.json | python3 -m json.tool
```

**CI/CD自動実行確認**:
```bash
# GitHub Actions経由（自動）
git push origin main  # 自動カバレッジ測定・レポート更新

# 最新レポート確認
ls -la coverage-reports/htmlcov/index.html
```

## ⚠️ 注意事項・制約

### **カバレッジ測定の制約**

**測定対象**:
- **対象**: src/全モジュール（48ファイル）
- **除外**: tests/, scripts/, _legacy_v1/, config/
- **特別扱い**: src/core/orchestrator.py（32行除外設定）

**データ更新頻度**:
- **自動更新**: GitHub Actions実行時
- **手動更新**: pytest --cov実行時
- **レポート世代**: htmlcov/内は最新のみ保持

### **品質目標・運用制約**

**カバレッジ目標（Phase 16-A基準）**:
```yaml
現在状況: 54.92% (3,842/6,995行・目標50%クリア)
短期目標: 60% (3ヶ月以内・実現可能)
中期目標: 70% (6ヶ月以内・品質向上)
長期目標: 80% (12ヶ月以内・理想品質)

重点改善エリア（Phase 16-A特定）:
- core/modes/: 現在0% → 目標70% (runner系実装)
- core/services/: 現在0% → 目標60% (health_checker等)
- backtest/: 現在20-40% → 目標70% (engine・evaluator)
```

**運用上の制約**:
- **レポートサイズ**: htmlcov/は6.3MB・81ファイル（Git除外・ローカル管理）
- **測定時間**: 全619テスト実行で約23秒・高速化達成
- **並列実行制限**: 大規模テスト時のリソース消費・CI効率化考慮

## 🔗 関連ファイル・依存関係

### **重要な外部依存**

**テスト実行システム**:
- **`scripts/management/dev_check.py`**: 統合品質チェック・カバレッジ実行
- **`.github/workflows/ci.yml`**: CI/CD自動カバレッジ測定
- **`tests/`**: 全テストファイル（619テスト・99.84%成功対応）
- **`pytest.ini`** または **`pyproject.toml`**: pytest設定

**品質保証統合**:
- **`scripts/testing/checks.sh`**: 品質チェックスクリプト
- **`src/`**: カバレッジ測定対象（68ファイル・完全網羅）
- **GitHub Actions**: 自動品質ゲート・レポート更新

### **生成されるレポートファイル**

**HTMLレポート**:
- **`htmlcov/index.html`**: メインダッシュボード（ブラウザ表示）
- **`htmlcov/status.json`**: 統計メタデータ（自動化処理用）
- **`htmlcov/z_*.html`**: 各モジュール詳細レポート（68ファイル・完全対応）

**データファイル**:
- **`.coverage`**: バイナリカバレッジデータ（Python coverage内部）
- **`class_index.html`**, **`function_index.html`**: 詳細分析ページ

### **Phase 13統合システム**

**統合管理CLI連携**:
- dev_check.py経由での自動実行
- 品質チェック統合・レポート保存
- CI前後チェックシステム統合

**品質保証フロー**:
```
テスト実行 → カバレッジ測定 → HTMLレポート生成 → 
品質評価 → CI/CDゲート → 継続改善サイクル
```

---

**重要**: Phase 16-A完了により、54.92%カバレッジ達成・619テスト成功・68ファイル完全対応の品質保証システムが完成しました。目標50%を4.92%上回る安定したカバレッジにより、継続的品質向上と安全なリファクタリングを実現します。
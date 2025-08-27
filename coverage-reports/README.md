# coverage-reports/ - テストカバレッジレポート管理

**Phase 13完了**: フォルダ構造最適化・品質保証統合・CI/CD完全自動化により、継続的品質改善システムが確立

## 🎯 役割・責任

テストカバレッジの測定・分析・継続的改善を担当します。src/全モジュールの品質可視化により、テスト漏れ防止・コード品質向上・安全なリファクタリングを支援し、Phase 13の306テスト100%成功基盤を維持します。

## 📂 ファイル構成

```
coverage-reports/
├── README.md           # このファイル（Phase 13完了版）
└── htmlcov/           # HTMLカバレッジレポート（最新：8/25更新）
    ├── index.html     # メインカバレッジダッシュボード
    ├── status.json    # カバレッジメタデータ・統計
    ├── class_index.html    # クラス別カバレッジ
    ├── function_index.html # 関数別カバレッジ
    ├── *.css, *.js    # UI/UX・インタラクティブ機能
    └── z_*.html       # 各モジュール詳細レポート（48ファイル）
```

## 🔧 主要機能・実装

### **カバレッジ測定システム（Phase 13最新版）**

**現在の品質状況**:
- **全体カバレッジ**: 55.04% (3,110/5,650行)
- **テスト対象ファイル**: 48モジュール（src/全域）
- **高品質モジュール**: 15ファイル（90%以上）
- **改善対象モジュール**: 17ファイル（70%未満）

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

**カバレッジ目標（Phase 13基準）**:
```yaml
現在状況: 55.04% (3,110/5,650行)
短期目標: 65% (6ヶ月以内・実現可能)
中期目標: 75% (12ヶ月以内・品質向上)
長期目標: 85% (18ヶ月以内・理想品質)

重点改善エリア:
- backtest/: 現在25% → 目標70%
- data/: 現在35% → 目標80%
- features/: 現在50% → 目標75%
```

**運用上の制約**:
- **レポートサイズ**: htmlcov/は約10MB（Git除外推奨）
- **測定時間**: 全テスト実行で約30-60秒
- **並列実行制限**: 大規模テスト時のリソース消費

## 🔗 関連ファイル・依存関係

### **重要な外部依存**

**テスト実行システム**:
- **`scripts/management/dev_check.py`**: 統合品質チェック・カバレッジ実行
- **`.github/workflows/ci.yml`**: CI/CD自動カバレッジ測定
- **`tests/`**: 全テストファイル（306テスト対応）
- **`pytest.ini`** または **`pyproject.toml`**: pytest設定

**品質保証統合**:
- **`scripts/testing/checks.sh`**: 品質チェックスクリプト
- **`src/`**: カバレッジ測定対象（48モジュール）
- **GitHub Actions**: 自動品質ゲート・レポート更新

### **生成されるレポートファイル**

**HTMLレポート**:
- **`htmlcov/index.html`**: メインダッシュボード（ブラウザ表示）
- **`htmlcov/status.json`**: 統計メタデータ（自動化処理用）
- **`htmlcov/z_*.html`**: 各モジュール詳細レポート（48ファイル）

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

**重要**: Phase 13完了により、カバレッジ測定が品質保証システムに完全統合されました。現在の55.04%から段階的な向上により、安全で高品質なソフトウェア開発を支援します。定期的なレポート確認と改善により、継続的品質向上を実現してください。
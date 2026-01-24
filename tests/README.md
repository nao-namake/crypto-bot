# tests/ - テスト・品質保証システム（Phase 61更新）

## 役割・責任

システム全体のテスト・品質保証を統合管理し、コード品質の維持、回帰防止、継続的品質向上を支援します。単体テストと統合テストによる包括的なテストカバレッジでシステムの信頼性と安定性を確保します。

## テスト統計（Phase 61時点）

| 項目 | 値 |
|------|-----|
| **総テスト数** | 約1,200 |
| **カバレッジ** | 64%以上 |
| **成功率** | 100% |

## ディレクトリ構成

```
tests/
├── README.md                    # このファイル
├── conftest.py                  # 共通フィクスチャ・モック
├── unit/                        # 単体テストシステム
│   ├── core/                       # コアシステムテスト（167テスト）
│   ├── data/                       # データ層テスト（67テスト）
│   ├── features/                   # 特徴量テスト（21テスト）
│   ├── ml/                         # 機械学習テスト（168テスト）
│   ├── monitoring/                 # 監視システムテスト（28テスト）
│   ├── services/                   # サービステスト（57テスト）
│   ├── strategies/                 # 取引戦略テスト（261テスト）
│   ├── trading/                    # 取引システムテスト（437テスト）
│   └── README.md                   # 単体テスト詳細ガイド
└── integration/                 # 統合テスト
    └── test_phase_50_3_graceful_degradation.py
```

## 主要テストカテゴリ

### unit/ - 単体テストシステム
システム全体の自動テストによる品質保証を担当します。

| カテゴリ | テスト数 | 内容 |
|---------|---------|------|
| core/ | 167 | 設定・ML統合・ヘルスチェック |
| data/ | 67 | Bitbank API・キャッシュ |
| features/ | 21 | 55特徴量生成 |
| ml/ | 168 | ProductionEnsemble・3モデル |
| monitoring/ | 28 | Discord通知 |
| services/ | 57 | レジーム判定・戦略選択 |
| strategies/ | 261 | 6戦略実装 |
| trading/ | 437 | 取引実行・リスク管理 |

### integration/ - 統合テスト
複数システム間の連携動作を検証します。
- Graceful Degradation（モデルフォールバック）

## 使用方法

### 全テスト実行
```bash
# 全単体テスト実行（推奨）
python -m pytest tests/unit/ -v --tb=short

# カバレッジ付き実行
python -m pytest tests/unit/ --cov=src --cov-report=term-missing

# 品質チェック統合実行
bash scripts/testing/checks.sh
```

### カテゴリ別テスト実行
```bash
# 機械学習テスト
python -m pytest tests/unit/ml/ -v

# 取引戦略テスト
python -m pytest tests/unit/strategies/ -v

# 取引システムテスト
python -m pytest tests/unit/trading/ -v

# サービステスト
python -m pytest tests/unit/services/ -v
```

### 開発時品質チェック
```bash
# 統合品質チェック（開発時必須）
bash scripts/testing/checks.sh

# 期待結果:
# ✅ 全テスト100%成功
# ✅ 64%+カバレッジ達成
# ✅ flake8/black/isort PASS
```

## 注意事項

### 実行環境要件
- **Python環境**: Python 3.8以上・pytest・pytest-cov・pytest-mock
- **実行場所**: プロジェクトルートディレクトリから実行
- **依存関係**: scikit-learn・lightgbm・xgboost完全インストール

### テスト品質基準
- **成功率**: 全テスト100%成功維持
- **カバレッジ**: 64%以上維持
- **CI/CD**: GitHub Actions自動品質ゲート

### モック戦略
- **外部API**: Bitbank API・Discord Webhook 完全モック化
- **機械学習**: ProductionEnsemble軽量版使用
- **時間依存**: 固定datetime・タイムゾーン一貫性

### 特記事項
- `tests/unit/ml/`: 1件のスキップ（GPU非対応環境）
- `tests/unit/trading/`: 1件のxfail（期待値調整待ち）

## 関連ファイル

| ファイル | 役割 |
|---------|------|
| `pytest.ini` | pytest設定 |
| `conftest.py` | 共通フィクスチャ・モック |
| `scripts/testing/checks.sh` | 品質チェックスクリプト |
| `.github/workflows/` | CI/CDパイプライン |

## テスト対象システム

| モジュール | 内容 |
|-----------|------|
| `src/features/` | 55特徴量生成 |
| `src/ml/` | ProductionEnsemble・3モデル統合 |
| `src/strategies/` | 6戦略・戦略管理 |
| `src/trading/` | 取引実行・リスク管理 |
| `src/monitoring/` | Discord通知 |
| `src/core/services/` | レジーム判定・戦略選択 |

---

**最終更新**: 2026年1月24日（Phase 61: テスト整理完了）

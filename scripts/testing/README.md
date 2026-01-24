# scripts/testing/ - 品質保証・テストシステム（Phase 61版）

**最終更新**: 2026年1月25日 - Phase 61.2完了・validate_ml_models.py Phase 61更新

## 役割・責任

システム全体の品質保証、テスト実行、コード品質チェック、MLモデル検証を担当するテストシステムです。単体テストから統合テスト、カバレッジ測定、コードスタイルチェック、機械学習モデル検証まで、包括的な品質保証機能を提供します。

**Phase 61.2成果**:
- checks.sh と validate_system.sh を統合（12項目チェック）
- 不要チェック削除・Phase参照統一
- ファイル数削減: 3 → 2
- 総行数削減: ~1,536行 → ~1,280行

## ファイル構成

```
scripts/testing/
├── README.md              # このファイル（Phase 61版）
├── checks.sh              # 品質チェック統合スクリプト（12項目）
└── validate_ml_models.py  # ML検証スクリプト
```

## 主要ファイルの役割

### **checks.sh**

システム全体の品質チェックとテスト実行を管理する統合スクリプト。

**チェック項目（12項目）**:

| # | 項目 | 説明 |
|---|------|------|
| 1 | ディレクトリ構造確認 | src/ディレクトリ存在確認 |
| 2 | Dockerfile整合性 | src/config/models/tax COPY命令確認 |
| 3 | 特徴量数検証 | 55特徴量（full）/ 49特徴量（basic）一致確認 |
| 4 | 戦略整合性 | 6戦略リスト一致確認 |
| 5 | 設定ファイル整合性 | YAML構文・必須フィールド・値範囲確認 |
| 6 | モデルファイル・メタデータ | ファイル存在・サイズ・F1スコア確認 |
| 7 | ML検証 | validate_ml_models.py --quick 呼び出し |
| 8 | flake8 | コードスタイルチェック（PEP8） |
| 9 | isort | import順序チェック |
| 10 | black | コード整形チェック |
| 11 | pytest | 全テストスイート実行・カバレッジ測定 |
| 12 | 結果サマリー | 実行結果と所要時間の表示 |

**実行時間**: 約60秒

### **validate_ml_models.py**

MLモデルの整合性と品質を検証する統合ツール（Phase 61版）。

**検証項目（8項目）**:

| # | 項目 | 説明 |
|---|------|------|
| 1 | モデルファイル整合性 | ensemble_full.pkl / ensemble_basic.pkl 存在確認 |
| 2 | 特徴量数整合性 | feature_order.json vs metadata.json 一致確認（55特徴量） |
| 3 | full/basicモデル差異 | MD5比較（異なるモデルであることを確認） |
| 4 | 3クラス分類確認 | BUY/HOLD/SELLの3クラス出力確認（2クラスはNG） |
| 5 | 戦略信号整合性 | 有効戦略数(6)と戦略信号特徴量数の一致確認 |
| 6 | 予測分布検証 | 極端なクラス偏り（90%超）がないか確認 |
| 7 | 信頼度統計 | 高信頼度(>60%)予測が十分あるか確認 |
| 8 | Stackingモデル検証 | stacking_enabled=true時にモデル存在確認 |

**CLIオプション**:
```bash
# 軽量モード（CIで使用・整合性のみ・高速）
python scripts/testing/validate_ml_models.py --quick

# 全検証（実データ読み込み・フル検証）
python scripts/testing/validate_ml_models.py

# 特定検証のみ
python scripts/testing/validate_ml_models.py --check consistency
python scripts/testing/validate_ml_models.py --check distribution
python scripts/testing/validate_ml_models.py --check performance
```

**実行時間**:
- `--quick`: 約3秒
- フル検証: 約15秒

## 使用方法

### 日常開発での品質チェック（必須）

```bash
# 基本的な品質チェック（開発前後必須）
bash scripts/testing/checks.sh

# 期待結果:
# ✅ システム整合性（6項目）
# ✅ ML検証通過（55特徴量・3クラス分類）
# ✅ コードスタイル準拠（flake8・black・isort）
# ✅ pytest成功（62%+カバレッジ）
```

### ML検証（モデル更新時）

```bash
# フル検証（モデル再訓練後に実行推奨）
python scripts/testing/validate_ml_models.py

# 期待結果:
# ✅ full/basicモデル差異確認（異なるMD5）
# ✅ 3クラス分類確認（BUY/HOLD/SELL）
# ✅ HOLD率60%以下
# ✅ F1スコア妥当範囲（0.35-0.55）
```

### CI/CD統合

```bash
# CI前品質チェック
bash scripts/testing/checks.sh && echo "✅ CI実行可能"

# GitHub Actionsで自動実行:
# - ci.yml: checks.sh + validate_ml_models.py（フル検証）
# - backtest.yml: バックテスト検証
# - model-training.yml: 週次モデル再学習
```

### トラブルシューティング

```bash
# テスト失敗時の詳細確認
bash scripts/testing/checks.sh 2>&1 | tee test_output.log

# 個別テスト実行
python3 -m pytest tests/unit/ml/ -v
python3 -m pytest tests/test_backtest/ -v

# カバレッジ詳細確認
python3 -m pytest tests/ --cov=src --cov-report=html
open .cache/coverage/htmlcov/index.html

# コードスタイル自動修正
python3 -m black src/ tests/ scripts/ tax/
python3 -m isort src/ tests/ scripts/ tax/

# ML検証詳細
python scripts/testing/validate_ml_models.py --check distribution
```

## 品質基準（Phase 61）

| 指標 | 基準 | 説明 |
|------|------|------|
| テスト成功率 | 100% | 全テスト成功必須 |
| カバレッジ | 62%以上 | 最低ライン維持 |
| コードスタイル | PASS | flake8/black/isort通過 |
| HOLD率 | 60%以下 | ML予測バランス |
| F1スコア | 0.35-0.55 | 妥当な予測性能 |

## 関連ファイル

### テスト・カバレッジ
- `tests/`: 単体テスト・統合テスト
- `.cache/coverage/htmlcov/`: カバレッジレポート出力

### MLモデル
- `models/production/ensemble_full.pkl`: 55特徴量モデル
- `models/production/ensemble_basic.pkl`: 49特徴量モデル
- `models/production/production_model_metadata.json`: モデルメタデータ

### 設定ファイル
- `config/core/unified.yaml`: 統一設定
- `config/core/thresholds.yaml`: 動的閾値・TP/SL設定
- `config/core/features.yaml`: 機能トグル
- `config/core/feature_order.json`: 55特徴量順序定義
- `config/strategies.yaml`: 6戦略定義

### CI/CD
- `.github/workflows/ci.yml`: CI品質ゲート
- `.github/workflows/model-training.yml`: 週次モデル再学習
- `.github/workflows/backtest.yml`: バックテスト実行

---

**推奨運用**:
1. **開発前後**: `bash scripts/testing/checks.sh`（必須・約60秒）
2. **モデル更新後**: `python scripts/testing/validate_ml_models.py`（推奨・約15秒）

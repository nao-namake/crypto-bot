# scripts/testing/ - 品質保証・テストシステム（Phase 55.8完了版）

**最終更新**: 2025年12月23日 - Phase 55.8完了・1,256テスト100%成功・65.42%カバレッジ達成・ML検証スクリプト統合

## 役割・責任

システム全体の品質保証、テスト実行、コード品質チェック、MLモデル検証を担当するテストシステムです。単体テストから統合テスト、カバレッジ測定、コードスタイルチェック、機械学習モデル検証、システム整合性検証まで、包括的な品質保証機能を提供します。

**Phase 55.8成果**:
- 1,256テスト100%成功
- 65.42%カバレッジ達成（63%閾値）
- ML検証スクリプト3つを1つに統合
- CIにフル検証ステップ追加
- HOLD率97.7%→54.7%修正完了

## ファイル構成

```
scripts/testing/
├── README.md              # このファイル（Phase 55.8完了版）
├── checks.sh              # 品質チェック・テスト実行スクリプト
├── validate_ml_models.py  # ML検証統合スクリプト（Phase 55.8新設）
└── validate_system.sh     # システム整合性検証スクリプト（7項目チェック）
```

## 主要ファイルの役割

### **checks.sh**

システム全体の品質チェックとテスト実行を管理するメインスクリプト。

**主要機能**:
| 機能 | 説明 |
|------|------|
| テスト実行 | pytest による全テストスイート実行（1,256テスト） |
| カバレッジ測定 | 65%以上維持（HTML/JSON/Term出力） |
| コードスタイル | flake8・black・isort によるPEP8準拠チェック |
| ML検証 | validate_ml_models.py --quick 呼び出し |
| 必須ライブラリ確認 | imbalanced-learn・optuna・matplotlib・Pillow |
| システム検証 | validate_system.sh統合 |

**実行時間**: 約90秒

### **validate_ml_models.py**（Phase 55.8新設）

3つのML検証スクリプトを統合した検証ツール。

**統合元**:
- validate_model_performance.py（削除済み）
- validate_ml_prediction_distribution.py（削除済み）
- validate_model_consistency.py（削除済み）

**検証項目**:
| # | 項目 | 説明 |
|---|------|------|
| 1 | モデルファイル整合性 | ensemble_full.pkl / ensemble_basic.pkl 存在確認 |
| 2 | 特徴量数整合性 | feature_order.json vs metadata.json 一致確認 |
| 3 | full/basicモデル差異 | MD5比較（異なるモデルであることを確認） |
| 4 | 3クラス分類確認 | BUY/HOLD/SELLの3クラス出力確認 |
| 5 | 予測分布検証 | HOLD率60%以下確認（Phase 55.8修正） |
| 6 | 信頼度統計 | 予測確率の統計情報 |
| 7 | 個別モデル性能 | F1スコア妥当性（0.35-0.55範囲） |

**CLIオプション**:
```bash
# 全検証（実データ読み込み・フル検証）
python scripts/testing/validate_ml_models.py

# 軽量モード（CIで使用・整合性のみ・高速）
python scripts/testing/validate_ml_models.py --quick

# 特定検証のみ
python scripts/testing/validate_ml_models.py --check consistency
python scripts/testing/validate_ml_models.py --check distribution
python scripts/testing/validate_ml_models.py --check performance
```

**実行時間**:
- `--quick`: 約3秒
- フル検証: 約15秒（実データ読み込み含む）

### **validate_system.sh**

システム整合性を検証する7項目チェックスクリプト。

**検証項目**:
| # | 項目 | 説明 |
|---|------|------|
| 1 | Dockerfile整合性 | src/config/models/tax/tests COPY命令確認 |
| 2 | 特徴量数検証 | 55特徴量（full）/ 49特徴量（basic）一致確認 |
| 3 | 戦略整合性検証 | 6戦略リスト一致確認（unified.yaml等） |
| 4 | モジュールimport検証 | TradingOrchestrator等の主要モジュール確認 |
| 5 | 設定ファイル整合性 | YAML構文・必須フィールド確認 |
| 6 | 環境変数・Secret | DISCORD_WEBHOOK_URL・BITBANK_API確認 |
| 7 | モデルメタデータ | F1スコア・モデル年齢・ファイルサイズ確認 |

**使用箇所**:
- `scripts/management/run_safe.sh`: ペーパートレード起動時
- GitHub Actions CI: Quality Check job
- 手動実行: デプロイ前チェック

**実行時間**: 約3-5秒

## 使用方法

### 日常開発での品質チェック（必須）

```bash
# 基本的な品質チェック（開発前後必須）
bash scripts/testing/checks.sh

# 期待結果:
# ✅ 1,256テスト100%成功
# ✅ 65%+カバレッジ達成
# ✅ コードスタイル準拠（flake8・black・isort）
# ✅ ML検証通過（55特徴量・3クラス分類）
# ✅ システム整合性確認
```

### ML検証（モデル更新時）

```bash
# フル検証（モデル再訓練後に実行推奨）
python scripts/testing/validate_ml_models.py

# 期待結果:
# ✅ full/basicモデル差異確認（異なるMD5）
# ✅ 3クラス分類確認（BUY/HOLD/SELL）
# ✅ HOLD率60%以下（Phase 55.8: 54.7%達成）
# ✅ F1スコア妥当範囲（0.35-0.55）
```

### システム整合性検証（デプロイ前）

```bash
bash scripts/testing/validate_system.sh

# 期待結果:
# ✅ [1/7] Dockerfile整合性
# ✅ [2/7] 特徴量数一致（55/49特徴量）
# ✅ [3/7] 6戦略整合性
# ✅ [4/7] モジュールimport成功
# ✅ [5/7] 設定ファイル整合性
# ⚠️ [6/7] 環境変数（ローカルでは警告OK）
# ✅ [7/7] モデルメタデータ整合性
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
open coverage-reports/htmlcov/index.html

# コードスタイル自動修正
python3 -m black src/ tests/ scripts/ tax/
python3 -m isort src/ tests/ scripts/ tax/

# ML検証詳細
python scripts/testing/validate_ml_models.py --check distribution
```

## 品質基準（Phase 55.8）

| 指標 | 基準 | 現在値 |
|------|------|--------|
| テスト成功率 | 100% | 1,256/1,256 |
| カバレッジ | 63%以上 | 65.42% |
| コードスタイル | flake8/black/isort通過 | PASS |
| HOLD率 | 60%以下 | 54.7% |
| F1スコア | 0.35-0.55 | 0.40-0.42 |

## 関連ファイル

### テスト・カバレッジ
- `tests/`: 単体テスト・統合テスト
- `coverage-reports/`: カバレッジレポート出力

### MLモデル
- `models/production/ensemble_full.pkl`: 55特徴量モデル（6戦略信号含む）
- `models/production/ensemble_basic.pkl`: 49特徴量モデル（フォールバック）
- `models/production/production_model_metadata.json`: fullモデルメタデータ
- `models/production/production_model_metadata_basic.json`: basicモデルメタデータ

### 設定ファイル
- `config/core/unified.yaml`: 統一設定（6戦略）
- `config/core/thresholds.yaml`: 動的閾値・TP/SL設定
- `config/core/features.yaml`: 機能トグル
- `config/core/feature_order.json`: 55特徴量順序定義

### CI/CD
- `.github/workflows/ci.yml`: CI品質ゲート
- `.github/workflows/model-training.yml`: 週次モデル再学習
- `.github/workflows/backtest.yml`: バックテスト実行

---

**推奨運用**:
1. **開発前後**: `bash scripts/testing/checks.sh`（必須・約90秒）
2. **モデル更新後**: `python scripts/testing/validate_ml_models.py`（推奨・約15秒）
3. **デプロイ前**: `bash scripts/testing/validate_system.sh`（推奨・約5秒）

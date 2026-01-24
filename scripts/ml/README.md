# scripts/ml/ - MLモデル学習スクリプト（Phase 61）

**最終更新**: 2026年1月24日

## 役割

機械学習モデルの学習・管理を担当します。

## ファイル構成

```
scripts/ml/
├── README.md              # このファイル
└── create_ml_models.py    # MLモデル学習スクリプト
```

## create_ml_models.py

6戦略統合・55特徴量・3クラス分類のMLモデルを学習。

### 主要機能

| 機能 | 説明 |
|------|------|
| 2段階モデル生成 | full（55特徴量）・basic（49特徴量） |
| 6戦略統合 | ATRBased / BBReversal / StochasticReversal / DonchianChannel / ADXTrendStrength / MACDEMACrossover |
| 3クラス分類 | BUY / HOLD / SELL |
| Optuna最適化 | ハイパーパラメータ自動最適化 |
| SMOTE | クラス不均衡対策 |
| 実戦略信号学習 | 訓練時と推論時の一貫性確保 |

### アンサンブル構成

| モデル | 重み |
|--------|------|
| LightGBM | 50% |
| XGBoost | 30% |
| RandomForest | 20% |

---

## 使用方法

### 推奨コマンド

```bash
# 両モデル一括学習（推奨）
python3 scripts/ml/create_ml_models.py --optimize --n-trials 50 --verbose

# fullモデルのみ
python3 scripts/ml/create_ml_models.py --model full --optimize --n-trials 50
```

### オプション

| オプション | デフォルト | 説明 |
|-----------|-----------|------|
| `--model` | both | both / full / basic |
| `--threshold` | 0.0005 | ターゲット閾値（±0.05%） |
| `--n-classes` | 3 | クラス数（BUY/HOLD/SELL） |
| `--use-smote` | True | SMOTE有効 |
| `--no-smote` | - | SMOTE無効化 |
| `--optimize` | False | Optuna最適化有効化 |
| `--n-trials` | 20 | Optuna試行回数 |
| `--days` | 180 | 学習データ期間（日数） |
| `--dry-run` | False | ドライラン |
| `--verbose` | False | 詳細ログ |

---

## 出力ファイル

| ファイル | 場所 | 説明 |
|---------|------|------|
| `ensemble_full.pkl` | models/production/ | 55特徴量モデル |
| `ensemble_basic.pkl` | models/production/ | 49特徴量モデル（フォールバック用） |
| `production_model_metadata.json` | models/production/ | モデルメタデータ |
| `training_metadata.json` | models/training/ | 学習メタデータ |
| `ml_training_*.log` | logs/ml/ | 学習ログ |

---

## GitHub Actions自動学習

`.github/workflows/model-training.yml`で週次自動実行。

| 項目 | 値 |
|------|-----|
| スケジュール | 毎週日曜 18:00 JST |
| 手動実行 | workflow_dispatch対応 |
| 自動コミット | モデル更新の自動バージョン管理 |

---

## トラブルシューティング

```bash
# ドライラン（学習前検証）
python3 scripts/ml/create_ml_models.py --dry-run --verbose

# モデル検証
python3 scripts/testing/validate_ml_models.py
```

---

## 関連ファイル

| ファイル | 役割 |
|---------|------|
| `src/ml/ensemble.py` | ProductionEnsemble |
| `src/features/feature_generator.py` | 特徴量生成 |
| `src/strategies/strategy_loader.py` | 6戦略動的ロード |
| `config/core/feature_order.json` | 55特徴量定義 |

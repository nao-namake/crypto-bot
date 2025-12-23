# scripts/ml/ - MLモデル学習スクリプト（Phase 55.9更新）

**最終更新**: 2025年12月23日

## 役割

機械学習モデルの学習・管理を担当します。

## ファイル構成

```
scripts/ml/
├── README.md              # このファイル
└── create_ml_models.py    # MLモデル学習メインスクリプト
```

## create_ml_models.py

6戦略統合・55特徴量・3クラス分類のMLモデルを学習・構築。

**主要機能**:

| 機能 | 説明 |
|------|------|
| 2段階モデル生成 | full（55特徴量）・basic（49特徴量） |
| 6戦略統合 | ATRBased / BBReversal / StochasticReversal / DonchianChannel / ADXTrendStrength / MACDEMACrossover |
| 3クラス分類 | BUY / HOLD / SELL（閾値 ±0.05%推奨） |
| Optuna最適化 | ハイパーパラメータ自動最適化 |
| SMOTE | クラス不均衡対策（デフォルト有効） |
| 実戦略信号学習 | 訓練時と推論時の一貫性確保 |

**アルゴリズム**:
- LightGBM 50%
- XGBoost 30%
- RandomForest 20%

## 使用方法

### 推奨コマンド（Phase 55.8）

```bash
# 両モデル一括学習（推奨）
python3 scripts/ml/create_ml_models.py \
  --model both \
  --threshold 0.0005 \
  --n-classes 3 \
  --use-smote \
  --optimize \
  --n-trials 30

# 高精度学習（50試行）
python3 scripts/ml/create_ml_models.py \
  --model both \
  --threshold 0.0005 \
  --n-classes 3 \
  --use-smote \
  --optimize \
  --n-trials 50
```

### オプション

| オプション | デフォルト | 説明 |
|-----------|-----------|------|
| `--model` | both | both / full / basic |
| `--threshold` | 0.005 | ターゲット閾値（**0.0005推奨**） |
| `--n-classes` | 3 | クラス数（3推奨） |
| `--use-smote` | True | SMOTE有効（--no-smoteで無効化） |
| `--optimize` | False | Optuna最適化有効化 |
| `--n-trials` | 20 | Optuna試行回数 |
| `--days` | 180 | 学習データ期間（日数） |
| `--dry-run` | False | ドライラン |
| `--verbose` | False | 詳細ログ |

### 閾値設定の重要性

| 閾値 | 訓練データHOLD比率 | 予測HOLD率 | 推奨 |
|------|-------------------|-----------|------|
| 0.005（±0.5%） | 92-94% | 97.7% | ❌ 高すぎ |
| **0.0005（±0.05%）** | **25.9%** | **54.7%** | **✅ 推奨** |

## GitHub Actions自動学習

`.github/workflows/model-training.yml`で週次自動実行。

| 項目 | 値 |
|------|-----|
| スケジュール | 毎週日曜 18:00 JST |
| 手動実行 | workflow_dispatch対応 |
| 自動コミット | モデル更新の自動バージョン管理 |
| デプロイトリガー | 本番環境自動デプロイ |

## 出力ファイル

| ファイル | 場所 | 説明 |
|---------|------|------|
| ensemble_full.pkl | models/production/ | 55特徴量モデル |
| ensemble_basic.pkl | models/production/ | 49特徴量モデル（Graceful Degradation用） |
| production_model_metadata.json | models/production/ | モデルメタデータ |
| training_metadata.json | models/training/ | 学習メタデータ |
| ml_training_*.log | logs/ml/ | 学習ログ |

## 依存関係

### 必須モジュール
- `src/features/feature_generator.py`: 特徴量生成
- `src/ml/ensemble.py`: ProductionEnsemble
- `src/strategies/strategy_loader.py`: 6戦略動的ロード
- `src/core/config/feature_manager.py`: 55特徴量定義

### 必須ライブラリ
- LightGBM / XGBoost / scikit-learn
- Optuna（ハイパーパラメータ最適化）
- imbalanced-learn（SMOTE）

## トラブルシューティング

```bash
# import確認
python3 -c "from scripts.ml.create_ml_models import NewSystemMLModelCreator; print('OK')"

# ドライラン（学習前検証）
python3 scripts/ml/create_ml_models.py --dry-run --verbose

# モデル検証
python3 scripts/testing/validate_ml_models.py
```

## 変更履歴

| Phase | 変更内容 |
|-------|---------|
| 39.1-39.5 | 実データ学習・TimeSeriesSplit・SMOTE・Optuna |
| 41.8 | 実戦略信号学習（訓練/推論一貫性） |
| 51.5-B | 2段階モデル一括生成（full/basic） |
| 51.9 | 6戦略統合・55特徴量・3クラス分類 |
| 55.6 | デフォルト3クラス・SMOTE有効 |
| 55.7 | モデル初期化バグ修正・特徴量選択修正 |
| 55.8 | 閾値0.0005推奨・HOLD率54.7%達成 |

---

**推奨運用**:
1. **週次自動学習**: GitHub Actionsで自動実行（手動介入不要）
2. **手動実行**: モデル品質問題時・緊急再学習時のみ
3. **検証**: `python3 scripts/testing/validate_ml_models.py` で品質確認

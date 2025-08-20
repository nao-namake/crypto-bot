# ML Scripts

機械学習・モデル管理系スクリプト集

## 📂 スクリプト一覧

### create_ml_models.py
**新システム用MLモデル作成スクリプト（Phase 12対応・CI/CD統合・監視統合）**

12特徴量最適化システム用の機械学習モデル学習・作成・検証・CI/CD統合・手動実行監視を行う包括的なMLスクリプト。

#### 主要機能
- **3モデル学習**: LightGBM・XGBoost・RandomForest の個別学習・CI/CD自動実行
- **アンサンブル統合**: ProductionEnsemble クラスによる重み付け統合・GitHub Actions対応
- **本番用モデル生成**: models/production/ への統合モデル保存・段階的デプロイ対応
- **品質保証**: モデル検証・予測テスト・メタデータ生成・CI/CD品質ゲート
- **監視統合**: 手動実行監視・パフォーマンス追跡・自動アラート・Discord通知

#### 学習対象
```python
# 12特徴量（新システム最適化済み）
expected_features = [
    'close', 'volume', 'returns_1', 'rsi_14', 
    'macd', 'macd_signal', 'atr_14', 'bb_position',
    'ema_20', 'ema_50', 'zscore', 'volume_ratio'
]
```

#### 使用例
```bash
# 通常実行（MLモデル作成・監視統合）
python scripts/ml/create_ml_models.py

# ドライラン（シミュレーション・CI/CD事前チェック）
python scripts/ml/create_ml_models.py --dry-run

# 詳細ログ出力（監視・デバッグ用）
python scripts/ml/create_ml_models.py --verbose

# 学習期間指定（本番データ・CI/CD最適化）
python scripts/ml/create_ml_models.py --days 360

# 設定ファイル指定（環境別設定・段階的デプロイ）
python scripts/ml/create_ml_models.py --config config/ml/custom.yaml

# 統合管理CLI経由実行（推奨・Phase 12対応）
python scripts/management/dev_check.py ml-models
```

#### 期待結果
```
🤖 MLモデル作成成功！
- LightGBM: F1 score 0.952（高いCV F1スコア・CI/CD統合）
- XGBoost: F1 score 0.997（高い精度・段階的デプロイ対応）
- RandomForest: F1 score 0.821（安定性重視・監視統合）
- ProductionEnsemble: 重み付け統合（0.4/0.4/0.2）・本番運用対応
🏥 手動実行監視統合: パフォーマンス追跡・自動アラート・Discord通知
🚀 CI/CD統合: GitHub Actions・品質ゲート・段階的デプロイ
```

## 🎯 設計原則

### ML開発哲学
- **12特徴量最適化**: 97個→12個への極限削減・過学習防止・CI/CD最適化
- **TimeSeriesSplit**: 時系列データ対応クロスバリデーション・本番環境対応
- **アンサンブル統合**: 重み付け投票による予測統合・段階的デプロイ対応
- **本番対応**: pickle対応・ProductionEnsemble・メタデータ管理・GitHub Actions統合
- **監視統合**: 手動実行監視・パフォーマンス追跡・Model Drift Detection・自動アラート

### モデル構成
```python
models = {
    "lightgbm": LGBMClassifier(
        n_estimators=200, learning_rate=0.1, 
        max_depth=8, num_leaves=31, random_state=42
    ),
    "xgboost": XGBClassifier(
        n_estimators=200, learning_rate=0.1,
        max_depth=8, random_state=42
    ),
    "random_forest": RandomForestClassifier(
        n_estimators=200, max_depth=12, 
        random_state=42, n_jobs=-1
    )
}
```

### アンサンブル重み
```python
weights = {
    'lightgbm': 0.4,     # 高いCV F1スコア
    'xgboost': 0.4,      # 高い精度
    'random_forest': 0.2  # 安定性重視
}
```

## 📊 モデル管理

### ディレクトリ構成
```
models/
├── training/              # 個別モデル保存先
│   ├── lightgbm_model.pkl
│   ├── xgboost_model.pkl
│   ├── random_forest_model.pkl
│   └── training_metadata.json
└── production/            # 本番用統合モデル
    ├── production_ensemble.pkl
    └── production_model_metadata.json
```

### メタデータ管理
```json
{
  "created_at": "2025-08-17T10:30:00",
  "model_type": "ProductionEnsemble",
  "phase": "Phase 12",
  "status": "production_ready",
  "feature_names": ["close", "volume", ...],
  "individual_models": ["lightgbm", "xgboost", "random_forest"],
  "model_weights": {"lightgbm": 0.4, "xgboost": 0.4, "random_forest": 0.2},
  "ci_cd_integration": {
    "github_actions": true,
    "quality_gate": "passed",
    "deployment_stage": "production"
  },
  "monitoring": {
    "drift_detection": true,
    "performance_tracking": true,
    "alert_system": "discord"
  }
}
```

## 🔧 トラブルシューティング

### よくあるエラー

**1. インポートエラー**
```bash
❌ 新システムモジュールのインポートに失敗: No module named 'src'
```
**対処**: プロジェクトルートから実行
```bash
cd /Users/nao/Desktop/bot
python scripts/ml/create_ml_models.py
```

**2. 設定ファイルエラー**
```bash
❌ 設定読み込み失敗: 設定ファイルが見つかりません
```
**対処**: 設定ファイルパス確認
```bash
# デフォルト設定使用
python scripts/ml/create_ml_models.py --config config/core/base.yaml

# 設定ファイル存在確認
ls config/core/base.yaml
```

**3. 特徴量エラー**
```bash
❌ 特徴量数不一致: 10 != 12
```
**対処**: 特徴量生成確認
```bash
# 特徴量生成テスト
python -c "
from src.features.technical import TechnicalIndicators
import pandas as pd
import numpy as np

ti = TechnicalIndicators()
sample_data = pd.DataFrame({
    'open': np.random.uniform(5000000, 5100000, 100),
    'high': np.random.uniform(5100000, 5200000, 100),
    'low': np.random.uniform(4900000, 5000000, 100), 
    'close': np.random.uniform(5000000, 5100000, 100),
    'volume': np.random.uniform(1000, 10000, 100)
})
features = ti.generate_all_features(sample_data)
print(f'特徴量数: {len(features.columns)}')
print(f'特徴量: {list(features.columns)}')
"
```

**4. モデル保存エラー**
```bash
❌ モデル保存エラー: Permission denied
```
**対処**: ディレクトリ権限確認
```bash
# ディレクトリ作成・権限設定
mkdir -p models/production models/training
chmod 755 models/production models/training
```

## 📈 Performance Notes

### 実行時間
- **軽量実行**: 約2-5分（サンプルデータ使用）
- **完全実行**: 約10-30分（180日実データ）
- **ドライラン**: 約30秒（学習スキップ）

### メモリ使用量
- **学習時**: 500MB-2GB（データサイズ依存）
- **予測時**: 100MB以下
- **モデルサイズ**: 10-50MB（個別モデル）

### GPU対応
```bash
# XGBoost GPU使用（オプション）
pip install xgboost[gpu]

# LightGBM GPU使用（オプション）  
pip install lightgbm[gpu]
```

## 🔮 Future Enhancements

Phase 12以降の拡張予定:
- **AutoML**: Optuna統合ハイパーパラメータ自動調整・実験管理・パラメータ最適化
- **Model Drift**: リアルタイム性能劣化検知・自動再学習・統計的検定・drift score
- **A/B Testing**: 複数モデル性能比較システム・カナリアリリース・最適重み調整
- **Real-time**: オンライン学習・incremental update・ストリーミング学習・適応的学習率
- **Feature Engineering**: 自動特徴量生成・選択・genetic programming・深層学習特徴量
- **Advanced Models**: Neural Network・CatBoost・Transformer・深層学習・大規模モデル
- **MLOps**: MLflow統合・Model Registry・実験管理・バージョン管理・ライフサイクル自動化

## 💡 Best Practices

### 開発時の推奨フロー（Phase 12 CI/CD統合対応）
```bash
# 1. ドライランで確認（CI/CD事前チェック）
python scripts/ml/create_ml_models.py --dry-run

# 2. 小規模データで動作確認（本番環境シミュレーション）
python scripts/ml/create_ml_models.py --days 30

# 3. 本格学習実行（監視統合・Discord通知）
python scripts/ml/create_ml_models.py --verbose

# 4. 統合管理CLI経由検証（推奨・Phase 12対応）
python scripts/management/dev_check.py ml-models

# 5. CI/CDパイプライン統合（GitHub Actions）
git add models/ && git commit -m "update: ML models Phase 12"
git push origin main  # GitHub Actions自動実行
```

### 品質管理（Phase 12 CI/CD・監視統合）
- **定期再学習**: 月1回・新データでモデル更新・CI/CD自動実行・無人運用
- **性能監視**: F1スコア・精度・再現率の追跡・手動実行監視・drift detection
- **バックアップ**: 過去モデルのバージョン管理・Git LFS・安全な復旧
- **検証**: 本番投入前の十分なテスト実行・段階的デプロイ・品質ゲート
- **セキュリティ**: Workload Identity・Secret Manager・監査ログ・コンプライアンス
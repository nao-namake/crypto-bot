# models/optuna/ - Optunaハイパーパラメータ最適化結果管理

## 🎯 役割・責任

Optunaハイパーパラメータ最適化の実行履歴、最適パラメータ、可視化レポートを管理する将来拡張用ディレクトリです。現在はPhase 39.5でOptunaがメモリ内実行のみですが、最適化履歴の永続化により、過去の試行結果の分析や最適化プロセスの可視化が可能になります。

## 📂 現在の状態（Phase 39.5完了時点）

```
models/optuna/
├── README.md                    # このファイル
└── (空 - 将来的に以下のファイルが追加予定)
```

**現在の実装**:
- ✅ **Phase 39.5完了**: Optuna TPESamplerハイパーパラメータ最適化実装
- ✅ **メモリ内実行**: `optuna.create_study()`でstudyオブジェクトを作成・最適化実行
- ✅ **最適パラメータ取得**: `study.best_params`で最適値を取得・モデル学習に使用
- ⏳ **永続化未実装**: 最適化履歴はメモリ内のみ・ファイル保存なし

**何かすると勝手に追加されるか？**:
- **現在**: いいえ。Optunaは明示的に永続化を指定しない限り、ファイルは作成されません
- **将来**: Phase 39.6以降で永続化機能を実装すれば、自動的にファイルが生成されます

## 📋 将来的なファイル構成（Phase 39.6以降予定）

```
models/optuna/
├── README.md                           # このファイル
├── optuna_study.db                     # SQLite最適化履歴データベース
├── best_params/                        # 最適パラメータJSON保存
│   ├── lightgbm_best_params.json      # LightGBM最適パラメータ
│   ├── xgboost_best_params.json       # XGBoost最適パラメータ
│   └── random_forest_best_params.json # RandomForest最適パラメータ
├── optimization_history/               # 最適化履歴可視化
│   ├── optimization_history.html      # 最適化進捗グラフ
│   ├── param_importances.html         # パラメータ重要度
│   └── parallel_coordinate.html       # パラレル座標プロット
└── logs/                               # 最適化ログ
    └── optimization_YYYYMMDD_HHMMSS.log # 実行ログ
```

## 📝 Phase 39.5現在の使用方法

### **Optunaハイパーパラメータ最適化実行**
```bash
# Phase 39.5: Optuna最適化実行（メモリ内のみ）
python3 scripts/ml/create_ml_models.py --optimize --n-trials 50

# 通常学習（最適化なし）
python3 scripts/ml/create_ml_models.py
```

### **Phase 39.5実装詳細**
```python
# scripts/ml/create_ml_models.py より抜粋

def optimize_hyperparameters(self, model_name, X_train, y_train, X_val, y_val, n_trials=50):
    """Phase 39.5: Optunaハイパーパラメータ最適化"""

    # Optunaスタディ作成（メモリ内のみ・永続化なし）
    study = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=42)
    )

    # 最適化実行
    study.optimize(objective_func, n_trials=n_trials, show_progress_bar=False)

    # 最適パラメータ取得・返却
    return study.best_params
```

## 🔮 将来的な拡張機能（Phase 39.6以降）

### **Phase 39.6予定: 最適化履歴の永続化**

**SQLite永続化実装**:
```python
# 将来的な実装例
study = optuna.create_study(
    direction="maximize",
    sampler=optuna.samplers.TPESampler(seed=42),
    storage="sqlite:///models/optuna/optuna_study.db",  # SQLite保存
    study_name="ml_model_optimization",
    load_if_exists=True  # 既存の履歴を継続
)
```

**最適パラメータJSON保存**:
```python
import json
from pathlib import Path

# 最適パラメータをJSONで保存
best_params_dir = Path("models/optuna/best_params")
best_params_dir.mkdir(exist_ok=True)

with open(best_params_dir / f"{model_name}_best_params.json", "w") as f:
    json.dump({
        "best_params": study.best_params,
        "best_value": study.best_value,
        "n_trials": len(study.trials),
        "datetime": datetime.now().isoformat()
    }, f, indent=2)
```

**可視化レポート生成**:
```python
import optuna.visualization as vis

# 最適化履歴の可視化
fig1 = vis.plot_optimization_history(study)
fig1.write_html("models/optuna/optimization_history/optimization_history.html")

# パラメータ重要度
fig2 = vis.plot_param_importances(study)
fig2.write_html("models/optuna/optimization_history/param_importances.html")

# パラレル座標プロット
fig3 = vis.plot_parallel_coordinate(study)
fig3.write_html("models/optuna/optimization_history/parallel_coordinate.html")
```

### **Phase 39.7予定: 最適化履歴の分析機能**

**過去の試行結果の確認**:
```python
import optuna

# 既存のstudyを読み込み
study = optuna.load_study(
    study_name="ml_model_optimization",
    storage="sqlite:///models/optuna/optuna_study.db"
)

# 最適試行の確認
print(f"Best trial: {study.best_trial.number}")
print(f"Best value: {study.best_value}")
print(f"Best params: {study.best_params}")

# 全試行の統計
print(f"Total trials: {len(study.trials)}")
print(f"Complete trials: {len([t for t in study.trials if t.state == optuna.trial.TrialState.COMPLETE])}")
```

**パラメータ探索空間の分析**:
```python
# パラメータごとの性能分布確認
import pandas as pd

trials_df = study.trials_dataframe()
print(trials_df[['number', 'value', 'params_learning_rate', 'params_max_depth']].head())

# 最適パラメータ周辺の探索
best_trial = study.best_trial
print(f"Optimal learning_rate: {best_trial.params['learning_rate']:.4f}")
print(f"Optimal max_depth: {best_trial.params['max_depth']}")
```

## ⚠️ 注意事項・制約

### **現在の制約（Phase 39.5）**
- **永続化なし**: 最適化履歴はメモリ内のみ・プロセス終了後に消失
- **再利用不可**: 過去の試行結果を活用した追加最適化ができない
- **可視化なし**: 最適化プロセスの詳細分析が困難
- **手動記録**: 最適パラメータは`models/production/production_model_metadata.json`に手動記録

### **将来の実装要件（Phase 39.6以降）**
- **SQLite管理**: 軽量で依存関係最小のSQLite使用
- **Git管理**: `.gitignore`でoptuna_study.dbを除外（サイズ大・頻繁更新）
- **バックアップ**: 重要な最適化結果はJSONで別途保存
- **可視化**: Plotlyベースの対話的レポート生成

### **システムリソース制約**
- **データベースサイズ**: n_trials増加でSQLiteファイルが増大
- **可視化処理**: HTML生成に追加の計算時間
- **メモリ使用**: 大規模な最適化履歴の読み込み時に注意

## 🔗 関連ファイル・依存関係

### **機械学習システム**
- `scripts/ml/create_ml_models.py`: Optuna最適化実装（Phase 39.5）
- `models/production/`: 最適パラメータで学習したモデル保存
- `models/training/`: 最適化された個別モデル保存

### **設定ファイル**
- `config/core/unified.yaml`: デフォルトハイパーパラメータ設定
- `config/core/thresholds.yaml`: 最適化探索範囲の設定（将来的）

### **外部ライブラリ依存**
- **optuna>=3.3.0**: ハイパーパラメータ最適化フレームワーク
- **optuna.samplers.TPESampler**: Tree-structured Parzen Estimator（Phase 39.5使用）
- **plotly**（将来的）: 可視化レポート生成
- **sqlite3**（将来的）: 最適化履歴永続化

## 📚 Optunaリファレンス

### **公式ドキュメント**
- Optuna公式: https://optuna.org/
- チュートリアル: https://optuna.readthedocs.io/en/stable/tutorial/index.html
- API Reference: https://optuna.readthedocs.io/en/stable/reference/index.html

### **Phase 39.5実装参考資料**
- TPESampler: https://optuna.readthedocs.io/en/stable/reference/samplers/generated/optuna.samplers.TPESampler.html
- Study: https://optuna.readthedocs.io/en/stable/reference/generated/optuna.study.Study.html
- Visualization: https://optuna.readthedocs.io/en/stable/reference/visualization/index.html

---

**現在の状態**: Phase 39.5完了（メモリ内最適化のみ）
**次のステップ**: Phase 39.6以降で永続化機能実装予定
**最終更新**: 2025年10月14日 - Phase 39.5完了・README新設

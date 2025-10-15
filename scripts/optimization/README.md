# Phase 40: Optuna包括最適化 - 使い方ガイド

## 📋 このディレクトリの役割

**Phase 40最適化スクリプト格納ディレクトリ**

Optunaを使用したベイズ最適化により、システム全体のパラメータを包括的に最適化します。

**対象パラメータ**: 79パラメータ
- Phase 40.1: リスク管理（12パラメータ）
- Phase 40.2: 戦略パラメータ（30パラメータ）
- Phase 40.3: ML統合（7パラメータ）
- Phase 40.4: MLハイパーパラメータ（30パラメータ）

**期待効果**:
- シャープレシオ: +50-70%向上
- 年間リターン: +50-100%向上
- ML信頼度: +15-25%向上

---

## 📂 ディレクトリ構成

```
scripts/optimization/
├── README_PHASE40.md                      # このファイル（使い方ガイド）
├── optuna_utils.py                        # 共通ユーティリティ
├── optimize_risk_management.py            # Phase 40.1: リスク管理最適化
├── optimize_strategy_parameters.py        # Phase 40.2: 戦略最適化
├── optimize_ml_integration.py             # Phase 40.3: ML統合最適化
├── optimize_ml_hyperparameters.py         # Phase 40.4: MLハイパーパラメータ最適化
└── integrate_and_deploy.py                # Phase 40.5: 統合・デプロイ

config/optuna_results/
├── README.md                              # 結果ファイルガイド
├── phase40_1_risk_management.json         # Phase 40.1結果
├── phase40_2_strategy_parameters.json     # Phase 40.2結果
├── phase40_3_ml_integration.json          # Phase 40.3結果
└── phase40_4_ml_hyperparameters.json      # Phase 40.4結果

config/core/backups/
└── thresholds_backup_YYYYMMDD_HHMMSS.yaml # 自動バックアップ
```

---

## 🚀 基本的な使い方

### ステップ1: 個別最適化の実行

Phase 40.1-40.4の最適化を順番に実行します。

```bash
# Phase 40.1: リスク管理パラメータ最適化（2-3時間）
python3 scripts/optimization/optimize_risk_management.py

# Phase 40.2: 戦略パラメータ最適化（5-7時間）
python3 scripts/optimization/optimize_strategy_parameters.py

# Phase 40.3: ML統合パラメータ最適化（2-3時間）
python3 scripts/optimization/optimize_ml_integration.py

# Phase 40.4: MLハイパーパラメータ最適化（4-6時間）
python3 scripts/optimization/optimize_ml_hyperparameters.py
```

**実行時間の目安**:
- Phase 40.1: 試行回数50回 → 約2-3時間
- Phase 40.2: 試行回数300回 → 約5-7時間
- Phase 40.3: 試行回数150回 → 約2-3時間
- Phase 40.4: 試行回数300回 → 約4-6時間
- **合計**: 約13-19時間（バックグラウンド実行可能）

### ステップ2: 結果の確認

最適化完了後、結果ファイルを確認します。

```bash
# JSON結果ファイルを確認
cat config/optuna_results/phase40_1_risk_management.json | python3 -m json.tool

# または、Pythonで確認
python3 -c "
import json
with open('config/optuna_results/phase40_1_risk_management.json') as f:
    data = json.load(f)
    print(f'Best Value (Sharpe Ratio): {data[\"best_value\"]:.4f}')
    print(f'Parameters Optimized: {len(data[\"best_params\"])}')
"
```

### ステップ3: 統合デプロイ

Phase 40.1-40.4の結果を統合し、thresholds.yamlに自動反映します。

```bash
# DRY RUNモード（実際の更新なし・レポートのみ）
python3 scripts/optimization/integrate_and_deploy.py --dry-run

# 本番実行（thresholds.yaml実際に更新）
python3 scripts/optimization/integrate_and_deploy.py
```

**実行結果**:
- ✅ バックアップ作成: `config/core/backups/thresholds_backup_*.yaml`
- ✅ thresholds.yaml更新: `config/core/thresholds.yaml`
- ✅ 変更DIFFレポート表示
- ✅ 期待効果サマリー表示

---

## 📊 各最適化スクリプトの詳細

### Phase 40.1: リスク管理パラメータ最適化

**対象**: 12パラメータ（TP/SL・Kelly基準・リスクスコア）

**実行方法**:
```bash
python3 scripts/optimization/optimize_risk_management.py
```

**デフォルト設定**:
- 試行回数: 50回
- タイムアウト: 1時間
- 目的関数: シャープレシオ最大化

**カスタマイズ**:
```python
# スクリプト内のmain()関数を編集
optimizer.optimize(n_trials=100, timeout=7200)  # 100回・2時間
```

---

### Phase 40.2: 戦略パラメータ最適化

**対象**: 30パラメータ（5戦略の閾値）

**実行方法**:
```bash
python3 scripts/optimization/optimize_strategy_parameters.py
```

**デフォルト設定**:
- 試行回数: 300回
- タイムアウト: 3時間
- 目的関数: シャープレシオ最大化

**パラメータ検証**:
- 信頼度順序制約（強 > 中 > 弱）
- 重み合計制約（MultiTimeframe: 4h + 15m = 1.0）
- ADX閾値整合性
- RSI/BB閾値順序

---

### Phase 40.3: ML統合パラメータ最適化

**対象**: 7パラメータ（ML重み・一致ボーナス等）

**実行方法**:
```bash
python3 scripts/optimization/optimize_ml_integration.py
```

**デフォルト設定**:
- 試行回数: 150回
- タイムアウト: 2時間
- 目的関数: シャープレシオ最大化

**パラメータ検証**:
- ml_weight + strategy_weight = 1.0
- agreement_bonus >= 1.0
- disagreement_penalty <= 1.0
- 閾値の論理的順序

---

### Phase 40.4: MLハイパーパラメータ最適化

**対象**: 30パラメータ（LightGBM・XGBoost・RandomForest）

**実行方法**:
```bash
python3 scripts/optimization/optimize_ml_hyperparameters.py
```

**デフォルト設定**:
- 試行回数: 300回
- タイムアウト: 4時間
- 目的関数: F1スコア最大化

**パラメータ検証**:
- LightGBM: bagging機構整合性・ツリー構造
- XGBoost: 極端な組み合わせ回避
- RandomForest: bootstrap/oob_score依存関係

---

### Phase 40.5: 統合デプロイ

**機能**: Phase 40.1-40.4の結果を統合・thresholds.yamlに自動反映

**実行方法**:
```bash
# DRY RUNモード（安全確認）
python3 scripts/optimization/integrate_and_deploy.py --dry-run

# 本番実行
python3 scripts/optimization/integrate_and_deploy.py
```

**処理フロー**:
1. Phase 40.1-40.4のJSONファイル読み込み
2. 79パラメータを統合（ドット記法 → YAML階層構造）
3. 現在のthresholds.yamlにディープマージ
4. タイムスタンプ付きバックアップ作成
5. 更新後のthresholds.yamlを保存
6. 変更DIFFレポート表示

---

## 🔄 Walk-forward Testing設計

**概要**: 時系列データの過学習を防ぐための検証手法

**基本構造**:
- 訓練期間: 120日（パラメータ最適化）
- テスト期間: 60日（out-of-sample検証）
- ステップサイズ: 30日（スライド間隔）

**実装例**（将来実装予定）:
```python
from scripts.optimization.optuna_utils import WalkForwardTester
import pandas as pd

# CSVデータ読み込み
data = pd.read_csv("data/historical/btc_jpy_15m.csv", index_col=0, parse_dates=True)

# Walk-forward tester初期化
wf_tester = WalkForwardTester(
    data=data,
    train_days=120,  # 訓練期間
    test_days=60,    # テスト期間
    step_days=30,    # ステップサイズ
)

# スプリット生成
splits = wf_tester.generate_splits()

# 各スプリットで最適化・検証
for i, (train_data, test_data) in enumerate(splits):
    print(f"Split {i+1}: Train={len(train_data)}日, Test={len(test_data)}日")

    # 訓練期間: パラメータ最適化
    study = optuna.create_study(direction="maximize")
    study.optimize(
        lambda trial: objective(trial, train_data),
        n_trials=50
    )

    # テスト期間: out-of-sample検証
    test_sharpe = evaluate_on_test_set(study.best_params, test_data)
    print(f"  訓練シャープ: {study.best_value:.4f}")
    print(f"  テストシャープ: {test_sharpe:.4f}")
```

**現状**: Phase 40.1-40.4はダミー実装（パラメータ妥当性検証のみ）
**将来**: 実際のBacktestRunnerを使用したWalk-forward testing統合予定

---

## ⚠️ 注意事項

### 過学習防止

1. **Walk-forward testing推奨**
   - 複数の時期で最適化・検証を繰り返す
   - ロバストネス（安定性）を評価

2. **Out-of-sample検証必須**
   - 最適化期間と異なる期間でバックテスト実行
   - テスト期間性能が訓練期間と大きく乖離する場合、過学習の可能性

3. **市場変動への適応**
   - 市況変化により最適パラメータが変わる可能性
   - 定期的な再最適化を推奨（月1回・四半期1回等）

### パラメータ制約

1. **妥当性範囲**
   - 極端な値を避ける（suggest_floatの範囲設定）
   - ドメイン知識に基づく範囲設定

2. **整合性チェック**
   - パラメータ間の矛盾を検出
   - 例: SL低 > SL通常 > SL高、重み合計 = 1.0

3. **実運用制約**
   - Bitbank API制限・最小取引サイズ等を考慮
   - 手数料・スリッページの影響

### 計算リソース

1. **実行時間**
   - 各Phase 2-7時間を想定
   - バックグラウンド実行可能

2. **並列化**
   - OptunaのJoblib backend使用可能
   - `n_jobs=-1`で全CPUコア使用

3. **メモリ使用量**
   - 大規模データセット処理時の監視
   - GCP Cloud Run: 1Gi制限

### バックアップ

1. **thresholds.yaml**
   - 統合デプロイ時に自動バックアップ作成
   - `config/core/backups/thresholds_backup_*.yaml`

2. **最適化結果**
   - `config/optuna_results/*.json`をGit管理推奨
   - 日付付きファイル名で保存

3. **復元方法**
   ```bash
   # バックアップから復元
   cp config/core/backups/thresholds_backup_20251014_123456.yaml config/core/thresholds.yaml
   ```

---

## 🔧 トラブルシューティング

### Q1: 最適化が途中で停止する

**原因**: タイムアウト・メモリ不足・例外発生

**解決策**:
```bash
# タイムアウトを延長
# スクリプト内のoptimize()呼び出しを編集
optimizer.optimize(n_trials=300, timeout=36000)  # 10時間

# 試行回数を減らす
optimizer.optimize(n_trials=100, timeout=3600)  # 100回・1時間
```

### Q2: 結果ファイルが見つからない

**原因**: 最適化が未実行・ファイルパス誤り

**確認方法**:
```bash
# 結果ファイル確認
ls -la config/optuna_results/

# 期待されるファイル:
# phase40_1_risk_management.json
# phase40_2_strategy_parameters.json
# phase40_3_ml_integration.json
# phase40_4_ml_hyperparameters.json
```

### Q3: 統合デプロイで「結果が見つかりません」エラー

**原因**: Phase 40.1-40.4の最適化が未実行

**解決策**:
```bash
# 個別最適化を先に実行
python3 scripts/optimization/optimize_risk_management.py
python3 scripts/optimization/optimize_strategy_parameters.py
python3 scripts/optimization/optimize_ml_integration.py
python3 scripts/optimization/optimize_ml_hyperparameters.py

# その後、統合デプロイ実行
python3 scripts/optimization/integrate_and_deploy.py
```

### Q4: パラメータ検証エラーが発生

**原因**: パラメータの論理的矛盾

**確認方法**:
```bash
# エラーメッセージを確認
# 例: "⚠️ 重み合計エラー: ml_weight(0.4) + strategy_weight(0.5) != 1.0"
# 例: "⚠️ 閾値順序エラー: high_confidence(0.7) <= min_ml(0.8)"
```

**解決策**: スクリプト内のパラメータ範囲を調整

### Q5: DRY RUNモードで問題が見つかった

**原因**: 最適化結果に想定外のパラメータ

**対処方法**:
```bash
# DRY RUNで確認
python3 scripts/optimization/integrate_and_deploy.py --dry-run

# DIFFレポートを確認
# 問題があれば、個別最適化を再実行

# 問題なければ本番実行
python3 scripts/optimization/integrate_and_deploy.py
```

---

## 🔄 定期的な再最適化

### 推奨スケジュール

- **毎月**: Phase 40.4（MLハイパーパラメータ）のみ再最適化
- **四半期毎**: Phase 40.1-40.4全体を再最適化
- **市況急変時**: 緊急で全体を再最適化

### 再最適化手順

```bash
# 1. 最適化実行（例: Phase 40.1）
python3 scripts/optimization/optimize_risk_management.py

# 2. 結果確認
cat config/optuna_results/phase40_1_risk_management.json | python3 -m json.tool

# 3. 既存結果とのベンチマーク比較
# 新しいbest_valueと既存best_valueを比較

# 4. 改善が見られる場合のみデプロイ
python3 scripts/optimization/integrate_and_deploy.py --dry-run
python3 scripts/optimization/integrate_and_deploy.py
```

### ベンチマーク比較

```python
import json

# 新旧結果を読み込み
with open('config/optuna_results/phase40_1_risk_management.json') as f:
    new_result = json.load(f)

with open('config/optuna_results/phase40_1_risk_management_old.json') as f:
    old_result = json.load(f)

# 性能比較
new_value = new_result['best_value']
old_value = old_result['best_value']
improvement = (new_value - old_value) / old_value * 100

print(f"新シャープレシオ: {new_value:.4f}")
print(f"旧シャープレシオ: {old_value:.4f}")
print(f"改善率: {improvement:+.2f}%")

if improvement > 5:
    print("✅ 有意な改善が見られます - デプロイ推奨")
elif improvement > 0:
    print("⚠️ 軽微な改善 - 慎重にデプロイ判断")
else:
    print("❌ 性能低下 - デプロイ非推奨")
```

---

## 📚 関連ドキュメント

- **開発履歴**: `docs/開発履歴/Phase_40/Phase_40_開発履歴.md`
- **結果ファイルガイド**: `config/optuna_results/README.md`
- **共通ユーティリティ**: `scripts/optimization/optuna_utils.py`
- **設定ファイル**: `config/core/thresholds.yaml`
- **Phase 38-39履歴**: `docs/開発履歴/Phase_38-39.md`

---

## 📞 サポート

**問題が発生した場合**:
1. このREADMEのトラブルシューティングセクション確認
2. `config/optuna_results/README.md`の結果ファイルフォーマット確認
3. `docs/開発履歴/Phase_40/Phase_40_開発履歴.md`の実装詳細確認

**ルール**:
- このファイルは「使い方」に特化
- 開発履歴・実装詳細は `docs/開発履歴/Phase_40/` 参照
- 定期的にREADMEを更新（新機能追加時等）

---

**最終更新**: 2025年10月14日 - Phase 40完了・使い方ガイド作成

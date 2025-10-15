# Optuna最適化結果ファイル - 使用ガイド

このディレクトリには、Phase 40で実行されたOptuna最適化の結果が保存されます。

---

## 📂 ファイル一覧

### Phase 40.1: リスク管理パラメータ
- **ファイル**: `phase40_1_risk_management.json`
- **パラメータ数**: 12
- **目的関数**: シャープレシオ最大化
- **最適化対象**:
  - ストップロス: ATR倍率（低/通常/高ボラティリティ）
  - テイクプロフィット: リスクリワード比・最小利益率
  - Kelly基準: max_position_ratio・safety_factor
  - リスクスコア: conditional・deny閾値

### Phase 40.2: 戦略パラメータ
- **ファイル**: `phase40_2_strategy_parameters.json`
- **パラメータ数**: 30
- **目的関数**: シャープレシオ最大化
- **最適化対象**:
  - MochipoyAlert: 5パラメータ（買い/売り強弱信頼度）
  - MultiTimeframe: 5パラメータ（一致度信頼度・時間足重み）
  - DonchianChannel: 5パラメータ（ブレイクアウト/リバーサル信頼度・閾値）
  - ADXTrend: 8パラメータ（トレンド強度信頼度・ADX/DI閾値）
  - ATRBased: 7パラメータ（ボラティリティ信頼度・RSI/BB閾値）

### Phase 40.3: ML統合パラメータ
- **ファイル**: `phase40_3_ml_integration.json`
- **パラメータ数**: 7
- **目的関数**: シャープレシオ最大化
- **最適化対象**:
  - ml_weight/strategy_weight: 加重平均の比率
  - high_confidence_threshold: 高信頼度判定閾値
  - agreement_bonus/disagreement_penalty: 一致/不一致時の調整倍率
  - min_ml_confidence: ML予測考慮開始閾値
  - hold_conversion_threshold: hold変更閾値

### Phase 40.4: MLハイパーパラメータ
- **ファイル**: `phase40_4_ml_hyperparameters.json`
- **パラメータ数**: 30
- **目的関数**: 予測精度（F1スコア）最大化
- **最適化対象**:
  - LightGBM: 10パラメータ（ツリー構造・正則化）
  - XGBoost: 10パラメータ（ツリー構造・正則化・重み）
  - RandomForest: 10パラメータ（ツリー構造・サンプリング・クラス重み）

---

## 📋 JSONファイルフォーマット

各最適化結果ファイルは以下のフォーマットで保存されます：

```json
{
  "phase": "phase40_1_risk_management",
  "created_at": "2025-10-14T12:34:56.789012",
  "best_params": {
    "risk.stop_loss.atr_multiplier_low_volatility": 2.5,
    "risk.stop_loss.atr_multiplier_normal_volatility": 2.0,
    "risk.stop_loss.atr_multiplier_high_volatility": 1.5,
    "risk.take_profit.risk_reward_ratio": 2.0,
    "risk.take_profit.min_profit_rate": 0.01,
    "risk.kelly.max_position_ratio": 0.5,
    "risk.kelly.safety_factor": 0.5,
    "risk.risk_score.conditional_threshold": 0.7,
    "risk.risk_score.deny_threshold": 0.85,
    "risk.drawdown.max_drawdown_threshold": 0.2,
    "risk.drawdown.daily_loss_limit": 0.05,
    "risk.anomaly.score_threshold": 0.7
  },
  "best_value": 0.8543,
  "study_stats": {
    "n_trials": 50,
    "n_complete": 48,
    "n_failed": 2,
    "duration_seconds": 3600.5
  }
}
```

### フィールド説明

- **phase**: Phase名（最適化スクリプト識別子）
- **created_at**: 最適化実行日時（ISO 8601形式）
- **best_params**: 最適パラメータ（ドット記法）
  - キー: `カテゴリ.サブカテゴリ.パラメータ名`
  - 値: 最適化された値
- **best_value**: 最適値（シャープレシオまたはF1スコア）
- **study_stats**: Optunaスタディ統計情報
  - n_trials: 総試行回数
  - n_complete: 成功した試行回数
  - n_failed: 失敗した試行回数
  - duration_seconds: 実行時間（秒）

---

## 🔧 使用方法

### 1. 最適化結果の確認

```bash
# JSONファイルを直接確認
cat config/optuna_results/phase40_1_risk_management.json | python3 -m json.tool

# または
python3 -c "
import json
with open('config/optuna_results/phase40_1_risk_management.json') as f:
    data = json.load(f)
    print(f'Phase: {data[\"phase\"]}')
    print(f'Best Value: {data[\"best_value\"]:.4f}')
    print(f'Parameters: {len(data[\"best_params\"])}')
    print('\\nBest Parameters:')
    for key, value in data['best_params'].items():
        print(f'  {key}: {value}')
"
```

### 2. thresholds.yamlへの適用

Phase 40.5の統合デプロイスクリプトを使用します：

```bash
# DRY RUNモード（実際の更新なし・レポートのみ）
python3 scripts/optimization/integrate_and_deploy.py --dry-run

# 本番実行（thresholds.yaml実際に更新）
python3 scripts/optimization/integrate_and_deploy.py
```

統合デプロイスクリプトは以下を自動実行します：
1. Phase 40.1-40.4の結果ファイルを読み込み
2. 79パラメータを統合（ドット記法 → YAML階層構造）
3. 現在のthresholds.yamlにディープマージ
4. タイムスタンプ付きバックアップ作成
5. 更新後のthresholds.yamlを保存
6. 変更DIFFレポート表示

### 3. Pythonコードからの読み込み

```python
from scripts.optimization.optuna_utils import OptimizationResultManager

# 結果マネージャー初期化
manager = OptimizationResultManager(results_dir="config/optuna_results")

# Phase 40.1の結果読み込み
result = manager.load_results("phase40_1_risk_management")

if result:
    print(f"Phase: {result['phase']}")
    print(f"Created: {result['created_at']}")
    print(f"Best Value: {result['best_value']:.4f}")
    print(f"Parameters: {len(result['best_params'])}")

    # 最適パラメータ取得
    best_params = result['best_params']
    sl_low = best_params.get("risk.stop_loss.atr_multiplier_low_volatility", 2.5)
    print(f"SL Low Volatility: {sl_low}")
else:
    print("結果ファイルが見つかりません")
```

---

## 📊 最適化結果の解釈

### シャープレシオ（Phase 40.1-40.3）

- **< 0.0**: 負のリターン（戦略が損失を出している）
- **0.0 - 0.5**: 低リターン（リスクに見合わないリターン）
- **0.5 - 1.0**: 中程度のリターン（実用的な戦略）
- **1.0 - 2.0**: 高リターン（優れた戦略）
- **> 2.0**: 非常に高いリターン（過学習の可能性も考慮）

**年率換算**: シャープレシオは日次リターンの標準偏差で計算後、√365で年率化

### F1スコア（Phase 40.4）

- **< 0.5**: 低精度（ランダム予測レベル）
- **0.5 - 0.7**: 中程度の精度（改善の余地あり）
- **0.7 - 0.85**: 高精度（実用的な予測モデル）
- **> 0.85**: 非常に高精度（過学習の可能性も考慮）

**計算式**: F1 = 2 × (Precision × Recall) / (Precision + Recall)

---

## ⚠️ 注意事項

### 過学習リスク

最適化結果は訓練データに対して最適化されています。以下に注意してください：

1. **Out-of-sample検証必須**:
   - 最適化期間と異なる期間でバックテスト実行
   - テスト期間性能が訓練期間と大きく乖離する場合、過学習の可能性

2. **Walk-forward testing推奨**:
   - 複数の時期で最適化・検証を繰り返す
   - ロバストネス（安定性）を評価

3. **市場変動への適応**:
   - 市況変化により最適パラメータが変わる可能性
   - 定期的な再最適化を推奨（月1回・四半期1回等）

### バックアップ

最適化結果ファイルは貴重なデータです：

- **定期的にバックアップ**: `config/optuna_results/`をコピー
- **Git管理推奨**: 結果ファイルをGitコミット
- **バージョン管理**: 日付付きファイル名で保存（例: `phase40_1_risk_management_20251014.json`）

### 本番適用前の確認

1. **DRY RUNモードでテスト**: `integrate_and_deploy.py --dry-run`
2. **DIFFレポート確認**: 想定外の変更がないか確認
3. **バックアップ確認**: `config/core/backups/`にバックアップが作成されているか確認
4. **段階的適用**: 一部パラメータから適用して様子見

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
python3 scripts/optimization/integrate_and_deploy.py
```

---

## 📚 関連ドキュメント

- **Phase 40実装ガイド**: `scripts/optimization/README_PHASE40.md`
- **最適化スクリプト**: `scripts/optimization/optimize_*.py`
- **統合デプロイスクリプト**: `scripts/optimization/integrate_and_deploy.py`
- **共通ユーティリティ**: `scripts/optimization/optuna_utils.py`
- **設定ファイル**: `config/core/thresholds.yaml`

---

**Phase 40完了日**: 2025年10月14日
**最適化パラメータ数**: 79（合計）
**期待効果**: +50-70%の収益向上

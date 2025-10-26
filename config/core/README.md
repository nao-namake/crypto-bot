# config/core/ - システム基本設定 🚀

## 🎯 役割・責任

システム全体で使用する基本設定を管理する中核フォルダです。4つの主要設定ファイルにより、機能トグル・動的閾値・基本設定・特徴量定義を統一管理します。

**Phase 49完了時点（2025年10月22日）**:
- 55特徴量（50基本+5戦略信号）
- 1,117テスト・68.32%カバレッジ
- 5戦略統合・3モデルアンサンブル
- デイトレード特化設定完了

---

## 📂 ファイル構成

### 1. **features.yaml** - 機能トグル管理

**役割**: 全機能のON/OFF切り替え（~50機能・7カテゴリー）

**構造**:
```yaml
trading:          # 取引実行機能（TP/SL・クールダウン）
risk_management:  # リスク管理機能（Kelly・ドローダウン・適応型ATR）
ml_integration:   # ML統合機能（アンサンブル・フォールバック）
strategies:       # 戦略機能（5戦略・動的信頼度）
data:             # データ管理（キャッシュ・55特徴量）
monitoring:       # 監視・通知（Discord・ヘルスチェック）
infrastructure:   # インフラ（GCP・ログ管理）
```

**使い方**:
- 機能の有効/無効化: `enabled: true/false`
- デバッグ時の機能切り分け
- 新機能追加時: 対応するカテゴリーに追加

**拡張ガイドライン**:
- **戦略追加時**: `strategies.individual_strategies:`に追加 + `unified.yaml:strategies.weights`で重み設定
- **MLモデル追加時**: `ml_integration.ensemble.note`に記載 + `unified.yaml:ensemble.weights`で重み設定
- **特徴量追加時**: `feature_order.json`更新で自動反映（`features.yaml`の修正不要）

---

### 2. **thresholds.yaml** - 動的閾値管理

**役割**: 動的に変更される閾値・パラメータの一元管理

**主要セクション**:
```yaml
ml:                    # ML統合（信頼度閾値・重み・Meta-Learning）
dynamic_confidence:    # 動的信頼度計算（5戦略の信頼度範囲）
strategies:            # 戦略パラメータ（ADX・ATR・Donchian等）
trading:               # 取引設定（Kelly基準・信頼度レベル）
position_management:   # ポジション管理（TP/SL・クールダウン）
margin:                # 証拠金管理（維持率閾値80%）
order_execution:       # 注文実行（完全指値オンリー）
models:                # MLモデルハイパーパラメータ

# Optuna最適化値（lines 409+）
# - 戦略信頼度パラメータ（mochipoy_*, mtf_*, adx_*, atr_*）
# - ML統合パラメータ（ml_weight, agreement_bonus等）
# - MLハイパーパラメータ（lgbm_*, xgb_*, rf_*）
```

**重要設定**:
- **デイトレード特化** (`position_management:`):
  - SL: 1.5%、TP: 2%、RR比 1.33:1（細かく利確）
  - max_daily_trades: 50
  - cooldown_minutes: 15
- **証拠金管理** (`margin.thresholds:`):
  - critical: 80.0%（エントリー拒否閾値）
- **完全指値オンリー** (`order_execution:`):
  - high_confidence_threshold: 0.0
  - low_confidence_threshold: -1.0

**使い方**:
- コードから参照: `get_threshold("パラメータ名")`
- Phase 40 Optuna最適化結果を含む
- 変更時: `scripts/optimization/run_phase40_optimization.py`使用推奨

---

### 3. **unified.yaml** - 基本設定管理

**役割**: 環境設定・基本構造の統一管理

**主要セクション**:
```yaml
mode_balances:         # モード別初期残高（paper/live/backtest: 10,000円）
exchange:              # 取引所設定（bitbank信用取引専用）
ml:                    # ML基本設定（ensemble有効・モデルパス）
data:                  # データ取得（15m/4h・キャッシュ設定）
features:              # 特徴量カテゴリー定義
strategies:            # 戦略有効化・重み設定（5戦略統合）
risk:                  # リスク管理基本設定
production:            # 本番運用設定（5分間隔・月700-900円）
logging:               # ログ設定（JST・30日保持）
cloud_run:             # GCP Cloud Run最適化（1Gi・1CPU）
ensemble:              # アンサンブル重み（LightGBM 50%・XGBoost 30%・RandomForest 20%）
```

**重要設定**:
- **features_count: 55**（feature_order.json参照）
- **timeframes: [15m, 4h]**（メイン・補助タイムフレーム）
- **trade_interval: 300**（5分間隔・コスト最適化）

**使い方**:
- モード制御: CLI引数 > 環境変数MODE > YAML内mode
- 基本的な構造設定（動的閾値は`thresholds.yaml`を使用）

**拡張ガイドライン**:
- **戦略追加時**: `strategies.enabled`リストに追加 + `strategies.weights`で重み設定
- **モデル追加時**: `ml.models`リストに追加 + `ensemble.weights`で重み設定

---

### 4. **feature_order.json** - 特徴量定義（単一真実源）

**役割**: 全システムで使用する特徴量の順序・定義を一元管理

**Phase 49完了時点**:
- **total_features: 55**（50基本+5戦略信号）
- **test_coverage: 68.32%**
- **total_tests: 1117**

**構造**:
```json
{
  "feature_order_version": "v2.5.0",
  "phase": "Phase 49",
  "total_features": 55,

  "feature_categories": {
    "basic": ["close", "volume"],
    "momentum": ["rsi_14", "macd"],
    "volatility": ["atr_14", "bb_position"],
    "trend": ["ema_20", "ema_50"],
    "volume": ["volume_ratio"],
    "breakout": ["donchian_high_20", "donchian_low_20", "channel_position"],
    "regime": ["adx_14", "plus_di_14", "minus_di_14"],
    "lag": [...],
    "rolling": [...],
    "interaction": [...],
    "time": [...],
    "strategy_signals": [
      "strategy_signal_atr_based",
      "strategy_signal_mochipoy_alert",
      "strategy_signal_multi_timeframe",
      "strategy_signal_donchian_channel",
      "strategy_signal_adx_trend_strength"
    ]
  }
}
```

**使い方**:
- 参照元: `src/core/config/feature_manager.py`
- 特徴量追加時: このファイルを更新すれば全システムに自動反映
- 順序変更時: 既存モデル再訓練必須

**拡張ガイドライン**:
- **特徴量追加時**:
  1. `feature_categories`の適切なカテゴリーに追加
  2. `feature_order`配列に追加
  3. `total_features`を更新
  4. `last_updated`タイムスタンプ更新
  5. MLモデル再訓練実施（`scripts/ml/create_ml_models.py`）

---

## 🔧 設定変更ガイド

### 機能追加・拡張の手順

#### 1. **特徴量を追加したい**

```bash
# Step 1: feature_order.json更新
vim config/core/feature_order.json
# → feature_categoriesに追加
# → total_features更新

# Step 2: 特徴量生成実装
vim src/features/technical.py
# → 新特徴量の計算ロジック追加

# Step 3: MLモデル再訓練
python scripts/ml/create_ml_models.py

# Step 4: テスト追加
vim tests/unit/features/test_technical.py
```

**注意**: `features.yaml`や`unified.yaml`の`features_count`は自動的に`feature_order.json`を参照するため修正不要

---

#### 2. **戦略を追加したい**

```bash
# Step 1: features.yaml更新
vim config/core/features.yaml
# → strategies.individual_strategies:に追加
#   example:
#     bollinger_bands: true  # 新戦略
#     note: "現在6戦略（拡張時: ここに追加 + unified.yamlで重み設定）"

# Step 2: unified.yaml更新
vim config/core/unified.yaml
# → strategies.enabled:リストに追加
# → strategies.weights:で重み設定
#   example:
#     bollinger_bands: 0.10

# Step 3: thresholds.yaml更新
vim config/core/thresholds.yaml
# → strategies:セクションに戦略パラメータ追加
# → dynamic_confidence.strategies:に信頼度範囲追加

# Step 4: 戦略実装
vim src/strategies/implementations/bollinger_bands.py

# Step 5: feature_order.json更新（戦略シグナル特徴量追加）
vim config/core/feature_order.json
# → strategy_signals:に追加
#   "strategy_signal_bollinger_bands"
```

---

#### 3. **MLモデルを追加したい**

```bash
# Step 1: features.yaml更新
vim config/core/features.yaml
# → ml_integration.ensemble.note:に記載
#   example:
#     note: "現在4モデル（LightGBM 40%・XGBoost 30%・RandomForest 20%・CatBoost 10%）・拡張時: unified.yaml:ensemble.weightsで重み設定"

# Step 2: unified.yaml更新
vim config/core/unified.yaml
# → ml.models:リストに追加
# → ensemble.weights:で重み設定
#   example:
#     catboost: 0.10

# Step 3: thresholds.yaml更新
vim config/core/thresholds.yaml
# → models:セクションに新モデルのハイパーパラメータ追加
#   example:
#     catboost:
#       iterations: 100
#       learning_rate: 0.05

# Step 4: モデル実装
vim src/ml/models/catboost_model.py

# Step 5: ProductionEnsemble更新
vim src/ml/ensemble/production_ensemble.py
```

---

#### 4. **設定値を変更したい（TP/SL等）**

```bash
# 基本ルール:
# - 動的閾値 → thresholds.yaml
# - 機能ON/OFF → features.yaml
# - 基本構造 → unified.yaml

# 例: TP/SL距離変更
vim config/core/thresholds.yaml
# → position_management:セクション
#   take_profit:
#     min_profit_ratio: 0.02  # TP 2%
#   stop_loss:
#     max_loss_ratio: 0.015   # SL 1.5%

# 例: クールダウン時間変更
vim config/core/thresholds.yaml
# → position_management:
#   cooldown_minutes: 15

# 例: 取引頻度変更
vim config/core/unified.yaml
# → production:
#   trade_interval: 300  # 秒単位
```

---

## 📊 現在のシステム状態（Phase 49完了）

### 品質指標
- **テスト**: 1,117テスト・100%成功
- **カバレッジ**: 68.32%
- **特徴量**: 55個（50基本+5戦略信号）

### ML統合システム
- **3段階統合ロジック**:
  - < 0.45: 戦略のみ採用
  - 0.45-0.60: 戦略70% + ML30%加重平均
  - ≥ 0.60: ボーナス/ペナルティ適用
- **F1スコア**: 0.56-0.61（XGBoost 0.593・RandomForest 0.614）
- **ML統合率**: 100%達成

### デイトレード特化設定
- **TP/SL**: SL 1.5%・TP 2%・RR比 1.33:1（細かく利確）
- **取引頻度**: 月100-200回（5分間隔実行）
- **証拠金維持率**: 80%確実遵守
- **完全指値オンリー**: 年間¥150,000手数料削減

### コスト最適化
- **月額コスト**: 700-900円（Phase 48: 35%削減達成）
- **通知**: 99%削減（300-1,500回/月 → 4回/月）
- **Discord週間レポート**: 損益曲線グラフ自動生成

### 確定申告対応
- **SQLite取引記録**: 自動記録・移動平均法損益計算
- **作業時間**: 95%削減（10時間 → 30分）
- **CSV出力**: 国税庁フォーマット対応

---

## ⚠️ 重要な注意事項

### 1. **設定ファイル間の同期**

以下の設定は複数ファイルで同期が必要：

| 設定項目 | 主要ファイル | 参照ファイル |
|---------|------------|------------|
| 特徴量数 | `feature_order.json` (total_features) | `unified.yaml` (features_count) |
| 戦略重み | `unified.yaml` (strategies.weights) | `features.yaml` (note) |
| モデル重み | `unified.yaml` (ensemble.weights) | `features.yaml` (note) |

### 2. **Phase 40 Optuna最適化値**

`thresholds.yaml`の以下のパラメータはOptuna最適化結果：
- 戦略信頼度パラメータ（mochipoy_*, mtf_*, adx_*, atr_*）
- ML統合パラメータ（ml_weight, agreement_bonus等）
- MLハイパーパラメータ（lgbm_*, xgb_*, rf_*）

**変更時**: `scripts/optimization/run_phase40_optimization.py`使用推奨

### 3. **feature_order.json変更時の影響**

- 既存MLモデルは使用不可（再訓練必須）
- バックテストデータの互換性喪失
- 全テスト再実行必須

---

## 🚀 クイックリファレンス

### よくある操作

```bash
# 機能の有効/無効化
vim config/core/features.yaml

# 閾値調整（TP/SL・信頼度等）
vim config/core/thresholds.yaml

# 基本設定変更（取引間隔等）
vim config/core/unified.yaml

# 特徴量追加
vim config/core/feature_order.json

# 設定検証
bash scripts/testing/checks.sh

# 設定確認（Pythonから）
python3 -c "
from src.core.config.threshold_manager import get_threshold
print(get_threshold('tp_default_ratio'))
"
```

---

**最終更新**: Phase 49完了（2025年10月22日）

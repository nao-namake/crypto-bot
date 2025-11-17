# config/core/ - システム基本設定 🚀

## 🎯 役割・責任

システム全体で使用する基本設定を管理する中核フォルダです。**5つの主要設定ファイル**により、機能トグル・動的閾値・基本設定・特徴量定義・戦略定義を統一管理します。

**Phase 52.5完了時点（2025年11月18日）**:
- 55特徴量（49基本+6戦略シグナル）
- 1,250テスト・68.77%カバレッジ
- 6戦略統合（レンジ型4・トレンド型2）・3モデルアンサンブル
- レジーム別ML統合・TP/SL最適化完了
- 設定履歴ドキュメント整備完了（docs/設定履歴/*.md）

---

## 📂 ファイル構成

### 1. **features.yaml** - 機能トグル管理

**役割**: 全機能のON/OFF切り替え（~50機能・7カテゴリー）

**構造**:
```yaml
trading:          # 取引実行機能（TP/SL・クールダウン・トレーリングストップ）
risk_management:  # リスク管理機能（Kelly・ドローダウン・適応型ATR）
ml_integration:   # ML統合機能（アンサンブル・フォールバック・レジーム別）
strategies:       # 戦略機能（6戦略・動的信頼度・動的戦略選択）
data:             # データ管理（キャッシュ・55特徴量・マルチタイムフレーム）
monitoring:       # 監視・通知（Discord・ヘルスチェック・パフォーマンス追跡）
infrastructure:   # インフラ（GCP・ログ管理・Secret Manager）
```

**使い方**:
- 機能の有効/無効化: `enabled: true/false`
- デバッグ時の機能切り分け
- 新機能追加時: 対応するカテゴリーに追加

**拡張ガイドライン**:
- **戦略追加時**: `strategies.individual_strategies:`に追加 + `config/strategies.yaml`で戦略定義
- **MLモデル追加時**: `ml_integration.ensemble.note`に記載 + `unified.yaml:ml.ensemble_weights`で重み設定
- **特徴量追加時**: `feature_order.json`更新で自動反映（`features.yaml`の修正不要）

**変更履歴**: `docs/設定履歴/unified_yaml_history.md`（features.yaml関連）

---

### 2. **thresholds.yaml** - 動的閾値管理

**役割**: 動的に変更される閾値・パラメータの一元管理

**主要セクション**:
```yaml
ml:                    # ML統合（信頼度閾値・レジーム別ML統合・Meta-Learning）
dynamic_confidence:    # 動的信頼度計算（6戦略の信頼度範囲）
dynamic_strategy_selection:  # 動的戦略選択（レジーム別戦略重み）
position_limits:       # レジーム別ポジション制限
strategies:            # 戦略パラメータ（6戦略: ATR・Donchian・ADX・BB・Stochastic・MACD）
trading:               # 取引設定（Kelly基準・信頼度レベル）
position_management:   # ポジション管理（レジーム別TP/SL・クールダウン）
margin:                # 証拠金管理（維持率閾値80%）
order_execution:       # 注文実行（完全指値オンリー）
models:                # MLモデルハイパーパラメータ
optuna_optimized:      # Optuna最適化値（Phase 40）
```

**重要設定**:
- **レジーム別TP/SL** (`position_management.take_profit/stop_loss.regime_based:`):
  - tight_range: SL 0.6%・TP 0.8%・RR比1.33:1
  - normal_range: SL 0.7%・TP 1.0%・RR比1.43:1
  - trending: SL 1.0%・TP 1.5%・RR比1.50:1
- **証拠金管理** (`margin.thresholds:`):
  - critical: 80.0%（エントリー拒否閾値）
- **完全指値オンリー** (`order_execution:`):
  - high_confidence_threshold: 0.0
  - low_confidence_threshold: -1.0

**使い方**:
- コードから参照: `get_threshold("パラメータ名")`
- Phase 40 Optuna最適化結果を含む
- 変更時: `scripts/optimization/run_phase40_optimization.py`使用推奨

**変更履歴**: `docs/設定履歴/thresholds_yaml_history.md`

---

### 3. **unified.yaml** - 基本設定管理

**役割**: 環境設定・基本構造の統一管理

**主要セクション**:
```yaml
mode_balances:         # モード別初期残高（paper/live: 10,000円・backtest: 100,000円）
exchange:              # 取引所設定（bitbank信用取引専用）
ml:                    # ML基本設定（ensemble有効・2段階Graceful Degradation）
data:                  # データ取得（15m/4h・キャッシュ設定）
features:              # 特徴量カテゴリー定義
risk:                  # リスク管理基本設定
production:            # 本番運用設定（5分間隔・月700-900円）
logging:               # ログ設定（JST・30日保持）
cloud_run:             # GCP Cloud Run最適化（1Gi・1CPU）
discord:               # Discord通知設定（レート制限・バッチ処理）
```

**重要設定**:
- **features_count: 55**（feature_order.json参照）
- **timeframes: [15m, 4h]**（メイン・補助タイムフレーム）
- **trade_interval: 300**（5分間隔・コスト最適化）
- **ensemble_weights**: LightGBM 50%・XGBoost 30%・RandomForest 20%

**使い方**:
- モード制御: CLI引数 > 環境変数MODE > YAML内mode
- 基本的な構造設定（動的閾値は`thresholds.yaml`を使用）

**拡張ガイドライン**:
- **戦略追加時**: `config/strategies.yaml`で戦略定義（Phase 51.5-B動的戦略管理基盤）
- **モデル追加時**: `ml.models`リストに追加 + `ml.ensemble_weights`で重み設定

**変更履歴**: `docs/設定履歴/unified_yaml_history.md`

---

### 4. **feature_order.json** - 特徴量定義（単一真実源）

**役割**: 全システムで使用する特徴量の順序・定義を一元管理

**Phase 52.4完了時点**:
- **total_features**: 55（49基本+6戦略シグナル）
- **test_coverage**: 68.77%
- **total_tests**: 1,250
- **6戦略システム実装完了**（ATRBased・DonchianChannel・ADXTrendStrength・BBReversal・StochasticReversal・MACDEMACrossover）
- **2段階Graceful Degradation実装完了**

**構造**:
```json
{
  "feature_order_version": "v4.2.0",
  "phase": "Phase 52.4",

  "feature_levels": {
    "full": {
      "count": 55,
      "model_file": "ensemble_full.pkl",
      "description": "完全特徴量（49基本+6戦略シグナル）"
    },
    "basic": {
      "count": 49,
      "model_file": "ensemble_basic.pkl",
      "description": "基本特徴量のみ（戦略シグナルなし・フォールバック用）"
    }
  },

  "feature_categories": {
    "basic": ["close", "volume"],
    "momentum": ["rsi_14", "macd", "macd_signal", "macd_histogram", "stoch_k", "stoch_d"],
    "volatility": ["atr_14", "bb_upper", "bb_lower", "bb_position", "atr_ratio"],
    "trend": ["ema_20", "ema_50"],
    "volume": ["volume_ratio", "volume_ema"],
    "breakout": ["donchian_high_20", "donchian_low_20", "channel_position"],
    "regime": ["adx_14", "plus_di_14", "minus_di_14"],
    "lag": [...],
    "rolling": [...],
    "interaction": [...],
    "time": ["hour", "day_of_week", "is_asia_hours", ...],
    "strategy_signals": [
      "strategy_signal_ATRBased",
      "strategy_signal_DonchianChannel",
      "strategy_signal_ADXTrendStrength",
      "strategy_signal_BBReversal",
      "strategy_signal_StochasticReversal",
      "strategy_signal_MACDEMACrossover"
    ]
  }
}
```

**Phase 52.4機能: feature_levels**
- **model_file設定**: 各レベルに対応するモデルファイル名を固定
  - Full: `ensemble_full.pkl`（55特徴量）
  - Basic: `ensemble_basic.pkl`（49特徴量）
- **設定駆動型モデル選択**: 特徴量数に応じて自動的に最適なモデルを選択
- **Graceful Degradation**: Full → Basic → DummyModelの3段階フォールバック

**使い方**:
- 参照元: `src/core/config/feature_manager.py`、`src/core/orchestration/ml_loader.py`
- 特徴量追加時: このファイルを更新すれば全システムに自動反映
- 順序変更時: 既存モデル再訓練必須
- **モデル名変更時**: `feature_levels[].model_file`を更新（固定化推奨）

**拡張ガイドライン**:
- **特徴量追加時**:
  1. `feature_categories`の適切なカテゴリーに追加
  2. `feature_definitions`に詳細定義追加
  3. `feature_levels`の`count`を更新（レベル別）
  4. `last_updated`タイムスタンプ更新
  5. MLモデル再訓練実施（`scripts/ml/create_ml_models.py`）

- **戦略追加時**:
  1. `strategy_signals`カテゴリーに戦略シグナル特徴量追加
  2. `feature_definitions`に定義追加（note: エンコーディング方式）
  3. `feature_levels.full.count`を+1更新
  4. MLモデル再訓練実施

**変更履歴**: `docs/設定履歴/unified_yaml_history.md`（feature_order.json関連）

---

### 5. **strategies.yaml** - 戦略定義管理（Phase 51.5-B動的戦略管理基盤）

**役割**: 戦略の宣言的設定・動的ロード・Registry Pattern実装

**Phase 52.5追加**: 5番目の主要設定ファイルとして明記

**構造**:
```yaml
strategies:
  atr_based:              # 戦略1: ATRベース逆張り
    enabled: true
    class_name: "ATRBased"
    module_path: "src.strategies.implementations.atr_based"
    weight: 0.17
    regime_affinity: "range"

  # ... (全6戦略定義)

integration:
  consensus_required: 0.4   # 必要合意度（40%）
  confidence_threshold: 0.3  # 最小信頼度（30%）

ml_features:
  strategy_signals_enabled: true  # 戦略シグナル特徴量生成
```

**Phase 51.5-B効果**:
- **Registry Pattern実装**: 戦略追加が2ファイルのみ（影響範囲93%削減）
- **動的ロード**: StrategyLoaderが自動読み込み
- **拡張性**: orchestrator.py等の修正不要

**使い方**:
- **戦略追加**: strategies:セクションに定義追加のみ
- **戦略無効化**: `enabled: false`に変更
- **重み調整**: weightフィールド変更後システム再起動

**使用箇所**:
- src/strategies/strategy_loader.py (load_strategies_from_config)
- src/strategies/strategy_registry.py (StrategyRegistry)
- src/core/services/dynamic_strategy_selector.py

**変更履歴**: Phase 51.5-B完了時に追加・Phase 52.5使用箇所追加

---

## 🔧 設定変更ガイド

### 機能追加・拡張の手順

#### 1. **特徴量を追加したい**

```bash
# Step 1: feature_order.json更新
vim config/core/feature_order.json
# → feature_categoriesに追加
# → feature_definitions に詳細定義追加
# → total_features更新

# Step 2: 特徴量生成実装
vim src/features/technical.py
# → 新特徴量の計算ロジック追加

# Step 3: MLモデル再訓練
python scripts/ml/create_ml_models.py

# Step 4: テスト追加
vim tests/unit/features/test_technical.py
```

**Phase 52.5修正済み**:
- `unified.yaml:features_count`はコメント化済み（Line 236）
- `features.yaml:feature_count`はコメント化済み（Line 205）
- `feature_order.json:total_features`が**唯一の単一真実源**
- 今後の特徴量数変更時は `feature_order.json` のみ更新

---

#### 2. **戦略を追加したい**

```bash
# Step 1: features.yaml更新
vim config/core/features.yaml
# → strategies.individual_strategies:に追加
#   example:
#     bollinger_bands_v2: true  # 新戦略
#     note: "Phase 52.4: 6戦略（ATR・Donchian・ADX・BB・Stochastic・MACD）・拡張時: ここに追加"

# Step 2: config/strategies.yaml更新（Phase 51.5-B動的戦略管理基盤）
vim config/strategies.yaml
# → strategies:に戦略定義追加
# → weights:で重み設定

# Step 3: thresholds.yaml更新
vim config/core/thresholds.yaml
# → strategies:セクションに戦略パラメータ追加
# → dynamic_confidence.strategies:に信頼度範囲追加
# → dynamic_strategy_selection.regime_strategy_mapping:にレジーム別重み追加

# Step 4: 戦略実装
vim src/strategies/implementations/bollinger_bands_v2.py

# Step 5: feature_order.json更新（戦略シグナル特徴量追加）
vim config/core/feature_order.json
# → strategy_signals:に追加
#   "strategy_signal_bollinger_bands_v2"

# 詳細な設定変更履歴:
# - thresholds.yaml: docs/設定履歴/thresholds_yaml_history.md
# - strategies.yaml: docs/設定履歴/strategies_yaml_history.md
```

---

#### 3. **MLモデルを追加したい**

```bash
# Step 1: features.yaml更新
vim config/core/features.yaml
# → ml_integration.ensemble.note:に記載
#   example:
#     note: "現在4モデル（LightGBM 40%・XGBoost 30%・RandomForest 20%・CatBoost 10%）・拡張: unified.yaml:ml.ensemble_weights"

# Step 2: unified.yaml更新
vim config/core/unified.yaml
# → ml.models:リストに追加
# → ml.ensemble_weights:で重み設定
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

# 例: レジーム別TP/SL変更
vim config/core/thresholds.yaml
# → position_management.take_profit.regime_based:
#   tight_range:
#     min_profit_ratio: 0.008  # TP 0.8%

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

## 📊 現在のシステム状態（Phase 52.4完了）

### 品質指標
- **テスト**: 1,250テスト・100%成功
- **カバレッジ**: 68.77%
- **特徴量**: 55個（49基本+6戦略シグナル）

### ML統合システム
- **3段階統合ロジック**:
  - < 0.45: 戦略のみ採用
  - 0.45-0.60: 戦略70% + ML30%加重平均
  - ≥ 0.60: ボーナス/ペナルティ適用
- **レジーム別ML統合**（Phase 52.4）:
  - tight_range: 戦略重視（ML 25%）・利益寄与99.4%
  - normal_range: バランス型（ML 30%）・利益寄与0.6%
  - trending: ML補完重視（ML 35%）・未発生
  - high_volatility: 超保守型（ML 10%）・エントリー禁止
- **F1スコア**: 0.56-0.61（XGBoost 0.593・RandomForest 0.614）
- **ML統合率**: 100%達成

### デイトレード特化設定（Phase 52.4最適化）
- **レジーム別TP/SL**:
  - tight_range: SL 0.6%・TP 0.8%・RR比1.33:1（頻繁利確・93.9%発生率）
  - normal_range: SL 0.7%・TP 1.0%・RR比1.43:1（標準利確）
  - trending: SL 1.0%・TP 1.5%・RR比1.50:1（大きく伸ばす）
- **取引頻度**: 月100-200回（5分間隔実行）
- **証拠金維持率**: 80%確実遵守
- **完全指値オンリー**: 年間¥150,000手数料削減

### 6戦略統合（Phase 52.4完了）
- **レンジ型戦略（4戦略）**: ATRBased・BBReversal・DonchianChannel・StochasticReversal
- **トレンド型戦略（2戦略）**: ADXTrendStrength・MACDEMACrossover
- **レジーム別重み最適化**:
  - tight_range: レンジ型95%集中（ATRBased 45%・BBReversal 35%）
  - trending: トレンド型80%集中（ADXTrendStrength 50%・MACDEMACrossover 30%）
- **動的戦略管理基盤**（Phase 51.5-B）: 戦略追加時2ファイルのみ変更（93%影響削減）

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

| 設定項目 | 主要ファイル | 参照ファイル | 変更履歴ドキュメント |
|---------|------------|------------|------------------|
| 特徴量数 | `feature_order.json` (total_features) | `unified.yaml` (features_count) | `unified_yaml_history.md` |
| 戦略重み | `strategies.yaml` (weights) | `thresholds.yaml` (regime_strategy_mapping) | `strategies_yaml_history.md` |
| ML統合パラメータ | `thresholds.yaml` (ml.strategy_integration) | - | `thresholds_yaml_history.md` |

**設定変更時の確認ポイント**:
1. 上記テーブルの参照ファイルも同時更新すること
2. 変更履歴ドキュメント（docs/設定履歴/*.md）に記録すること
3. `scripts/testing/checks.sh`で整合性検証すること

### 2. **Phase 40 Optuna最適化値**

`thresholds.yaml`の`optuna_optimized`セクションはOptuna最適化結果（Phase 40）：
- リスク管理パラメータ（12個）
- 戦略パラメータ（30個）
- ML統合パラメータ（7個）
- MLハイパーパラメータ（30個）

**変更時**: `scripts/optimization/run_phase40_optimization.py`使用推奨

**重要**: システムは各セクションの値を優先使用（`optuna_optimized`は記録・参照用）

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

# 戦略追加
vim config/strategies.yaml

# 設定検証
bash scripts/testing/checks.sh

# 設定確認（Pythonから）
python3 -c "
from src.core.config.threshold_manager import get_threshold
print(get_threshold('position_management.take_profit.min_profit_ratio'))
"
```

### 設定履歴ドキュメント

詳細な変更履歴は以下を参照：
- **unified.yaml**: `docs/設定履歴/unified_yaml_history.md`
- **thresholds.yaml**: `docs/設定履歴/thresholds_yaml_history.md`
- **strategies.yaml**: `docs/設定履歴/strategies_yaml_history.md`

---

**最終更新**: Phase 52.4完了（2025年11月14日）
- 55特徴量システム確立（49基本+6戦略シグナル）
- 6戦略統合完了（レンジ型4・トレンド型2）
- レジーム別ML統合・TP/SL最適化完了
- 設定履歴ドキュメント整備完了（docs/設定履歴/*.md）
- 品質指標: 1,250テスト・68.77%カバレッジ

# strategies.yaml 設定状態記録

**最終更新**: 2025-11-18

---

## このファイルの目的

`config/core/strategies.yaml`の現在の設定状態を記録し、設定の意味・構造・使われ方を文書化する。

---

## 現在の設定状態

### 戦略定義 (strategies)

**定義済み戦略**: 6戦略

| ID | クラス名 | 有効 | 重み | 優先度 | レジーム適性 | 説明 |
|----|---------|------|------|--------|------------|------|
| `atr_based` | ATRBased | ✅ | 0.17 | 1 | range | ATRベース逆張り戦略 - ボラティリティベース平均回帰 |
| `donchian_channel` | DonchianChannel | ✅ | 0.17 | 2 | range | Donchianチャネルブレイクアウト戦略 - 高値/安値ブレイクアウト検知 |
| `adx_trend` | ADXTrendStrength | ✅ | 0.17 | 3 | trend | ADXトレンド強度戦略 - トレンド方向性とDI判定 |
| `bb_reversal` | BBReversal | ✅ | 0.17 | 4 | range | BB Reversal戦略 - レンジ相場での平均回帰 |
| `stochastic_reversal` | StochasticReversal | ✅ | 0.17 | 5 | range | Stochastic Reversal戦略 - レンジ相場でのモメンタム逆張り |
| `macd_ema_crossover` | MACDEMACrossover | ✅ | 0.15 | 6 | trend | MACD+EMA Crossover戦略 - トレンド転換期の押し目買い・戻り売り |

**構成**:
- レンジ型戦略: 4戦略（ATRBased・DonchianChannel・BBReversal・StochasticReversal）
- トレンド型戦略: 2戦略（ADXTrendStrength・MACDEMACrossover）

### 統合設定 (integration)

**コンセンサスアルゴリズム**:
- `consensus_required`: 0.4（必要合意度40%）
- `confidence_threshold`: 0.3（最小信頼度30%）
- `signal_conflict_resolution`: "weighted_vote"（加重投票）

**シグナル統合**:
- `signal_aggregation`: "weighted_average"（加重平均）
- `min_active_strategies`: 1（最小有効戦略数）

### ML特徴量生成設定 (ml_features)

**戦略シグナル特徴量**:
- `strategy_signals_enabled`: true（戦略シグナル特徴量を生成）
- `signal_encoding`: "action_times_confidence"（buy=+confidence, hold=0, sell=-confidence）
- `feature_order_auto_update`: false（自動更新無効・手動管理）

### 戦略管理機能 (management)

**動的ロード**:
- `dynamic_loading`: true（StrategyLoader使用）
- `registry_pattern`: true（Registry Pattern使用）
- `hot_reload_enabled`: false（ホットリロード無効）

**検証**:
- `validate_on_load`: true（ロード時検証）
- `fail_fast`: true（エラー時即座に失敗）

### ログ設定 (logging)

- `strategy_load`: true（戦略ロードログ有効）
- `strategy_decision`: true（戦略判断ログ有効）
- `verbose`: false（詳細ログ無効）

---

## 使用箇所

| 項目 | 使用箇所 |
|------|---------|
| 戦略定義読み込み | `src/strategies/strategy_loader.py` (load_strategies_from_config) |
| Registry管理 | `src/strategies/strategy_registry.py` (StrategyRegistry) |
| 戦略実行管理 | `src/strategies/base/strategy_manager.py` |
| 動的戦略選択 | `src/core/services/dynamic_strategy_selector.py` |

---

## 戦略追加手順

1. 戦略クラスに `@StrategyRegistry.register()` デコレータ追加
2. `config/core/strategies.yaml` に戦略定義追加
3. `config/core/thresholds.yaml` に設定追加

**完了** - orchestrator.py等の修正不要（影響範囲93%削減達成）

---

## 設定値の意味

### 戦略定義の各フィールド

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `enabled` | bool | 戦略の有効/無効 |
| `class_name` | string | 戦略クラス名 |
| `module_path` | string | モジュールパス |
| `strategy_type` | string | 戦略タイプID |
| `weight` | float | 戦略重み（0-1） |
| `priority` | int | 実行優先度（1-N） |
| `regime_affinity` | string | レジーム適性（range/trend） |
| `indicators` | list | 使用インジケーター |
| `description` | string | 戦略説明 |
| `config_section` | string | thresholds.yaml設定セクション |

### レジーム適性 (regime_affinity)

- `range`: レンジ相場（横ばい・ボラティリティ低）に適した戦略
- `trend`: トレンド相場（上昇/下降・方向性明確）に適した戦略

---

## 参照

- **設定ファイル**: `config/core/strategies.yaml`
- **動的戦略管理**: `src/strategies/strategy_loader.py`
- **Registry Pattern**: `src/strategies/strategy_registry.py`
- **パラメータ設定**: `config/core/thresholds.yaml`
- **開発履歴**: `docs/開発履歴/`

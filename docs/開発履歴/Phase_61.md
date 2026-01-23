# Phase 61: 戦略分析・改修

**期間**: 2026年1月24日〜
**目的**: レジーム判定の最適化とトレンド型戦略の活性化

---

## 背景

Phase 60.7完了時点で総損益¥86,639（PF 1.58）を達成したが、以下の課題が判明：

| 課題 | 詳細 | 影響 |
|------|------|------|
| **ADXTrendStrength赤字** | 7取引、勝率42.9%、¥-2,511損失 | 全体PFを低下 |
| **MACDEMACrossover発動0件** | 183日間で0取引 | トレンド型戦略が機能していない |
| **レジーム偏り** | tight_range 88.2%、trending 0% | 戦略多様性が活かされていない |

**根本原因**: `MarketRegimeClassifier`のハードコード閾値が不適切
- tight_range: BB幅 < 3% AND 価格変動 < 2% → 緩すぎて88%がここに吸収
- trending: ADX > 25 AND EMA傾き > 1% → 厳しすぎて0件

---

## Phase 61.1: レジーム判定閾値調整 ✅完了

### 実施日
2026年1月24日

### 目標
- trending発生率: 0% → 5-15%
- tight_range発生率: 88% → 60-70%

---

### 実施内容

#### 1. thresholds.yamlにmarket_regimeセクション追加

```yaml
market_regime:
  tight_range:
    bb_width_threshold: 0.025      # 0.03→0.025（厳格化）
    price_range_threshold: 0.015   # 0.02→0.015（厳格化）
  trending:
    adx_threshold: 20              # 25→20（緩和）
    ema_slope_threshold: 0.007     # 0.01→0.007（緩和）
  normal_range:
    bb_width_threshold: 0.05       # 維持
    adx_threshold: 20              # 維持
  high_volatility:
    atr_ratio_threshold: 0.018     # 維持
```

#### 2. MarketRegimeClassifier修正

`src/core/services/market_regime_classifier.py`を修正：

- ハードコード値を`get_threshold()`による設定ファイル読み込みに変更
- 4つの判定メソッドを修正:
  - `_is_tight_range()`
  - `_is_trending()`
  - `_is_normal_range()`
  - `_is_high_volatility()`
- ログメッセージに実際の閾値を表示

```python
# 変更前（ハードコード）
def _is_tight_range(self, bb_width: float, price_range: float) -> bool:
    return bb_width < 0.03 and price_range < 0.02

# 変更後（設定ファイル参照）
def _is_tight_range(self, bb_width: float, price_range: float) -> bool:
    bb_threshold = get_threshold("market_regime.tight_range.bb_width_threshold", 0.025)
    price_threshold = get_threshold("market_regime.tight_range.price_range_threshold", 0.015)
    return bb_width < bb_threshold and price_range < price_threshold
```

#### 3. テスト更新

`tests/unit/services/test_market_regime_classifier.py`を更新：

- モック関数`mock_get_threshold()`で設定値を注入するテスト構造に変更
- 新しい閾値に対応したテストケース
- 21件のテスト全て成功

#### 4. Walk-Forward Validationバグ修正

CI検証中に発見したバグを修正：

**問題**:
```
create_trading_orchestrator() got an unexpected keyword argument 'mode'
```

Walk-Forward Validationスクリプトが`create_trading_orchestrator()`に無効な`mode`引数を渡していた。

**修正** (`scripts/backtest/walk_forward_validation.py`):
```python
# 変更前（エラー）
orchestrator = await create_trading_orchestrator(
    config=config, logger=self.logger, mode="backtest"
)

# 変更後（main.pyと同じ方法）
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["BACKTEST_MODE"] = "true"
set_backtest_mode(True)
set_backtest_log_level("WARNING")
config = load_config("config/core/unified.yaml", cmdline_mode="backtest")
orchestrator = await create_trading_orchestrator(config=config, logger=self.logger)
```

---

### 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `config/core/thresholds.yaml` | market_regimeセクション追加（27行） |
| `src/core/services/market_regime_classifier.py` | get_threshold()対応（全4メソッド） |
| `tests/unit/services/test_market_regime_classifier.py` | モック関数対応テスト（21件） |
| `scripts/backtest/walk_forward_validation.py` | バックテストモード設定修正 |
| `docs/開発計画/ToDo.md` | Phase 61計画更新 |
| `docs/開発履歴/SUMMARY.md` | Phase 61追加 |
| `CLAUDE.md` | Phase 61進行中に更新 |

---

### 閾値変更サマリー

| レジーム | パラメータ | 変更前 | 変更後 | 効果 |
|---------|-----------|--------|--------|------|
| **tight_range** | BB幅閾値 | 0.030 | 0.025 | 発生率削減 |
| **tight_range** | 価格変動閾値 | 0.020 | 0.015 | 発生率削減 |
| **trending** | ADX閾値 | 25 | 20 | 発生率増加 |
| **trending** | EMA傾き閾値 | 0.010 | 0.007 | 発生率増加 |
| normal_range | BB幅閾値 | 0.05 | 0.05 | 維持 |
| normal_range | ADX閾値 | 20 | 20 | 維持 |
| high_volatility | ATR比閾値 | 0.018 | 0.018 | 維持 |

---

### Gitコミット履歴

| コミット | 内容 |
|---------|------|
| `3f6f8bb2` | feat: Phase 61.1 レジーム判定閾値を設定ファイル化 |
| `48ed2a13` | fix: Walk-Forward Validationのmode引数エラーを修正 |

---

### 検証状況

| 検証項目 | 結果 |
|---------|------|
| 単体テスト（MarketRegimeClassifier） | 21件成功 |
| 全体テスト | 1206件成功（回帰なし） |
| CI/CD Pipeline | 成功（Run ID: 21300967165） |
| バックテスト | CI実行中（Run ID: 21301254775） |

---

### 期待される効果

| 指標 | 変更前 | 期待値 |
|------|--------|--------|
| trending発生率 | 0% | 5-15% |
| tight_range発生率 | 88.2% | 60-70% |
| ADXTrendStrength発動 | trendingで有効化 | 発動増加 |
| MACDEMACrossover発動 | 0件 | 増加期待 |

---

## Phase 61.2: ADXTrendStrength評価・対応 📋予定

### 判断フロー
1. 61.1バックテスト結果を分析
2. ADXTrendStrength勝率を確認
   - 勝率 ≥ 50%: パラメータ微調整で継続
   - 勝率 < 50%: 全レジームで重み0.0に設定（無効化）

### 変更対象ファイル
- `config/core/thresholds.yaml`（regime_strategy_mapping調整）

---

## Phase 61.3: MACDEMACrossover発動改善 📋予定

### 判断フロー
1. 61.1でtrending発生後、自動的に発動機会増加を確認
2. まだ発動が少ない場合:
   - `adx_trend_threshold`: 18→15に緩和
   - または`_is_trend_market()`にEMA乖離条件を追加

### 変更対象ファイル
- `config/core/thresholds.yaml`（strategies.macd_ema_crossover調整）
- `src/strategies/implementations/macd_ema_crossover.py`（必要時）

---

## 成功基準

| Phase | 指標 | 目標値 | 状態 |
|-------|------|--------|------|
| 61.1 | trending発生率 | ≥ 5% | バックテスト検証中 |
| 61.1 | tight_range発生率 | ≤ 70% | バックテスト検証中 |
| 61.2 | ADXTrendStrength勝率 | ≥ 50% or 無効化 | 📋予定 |
| 61.3 | MACDEMACrossover取引数 | ≥ 10件 | 📋予定 |
| **全体** | **PF** | **≥ 1.50維持** | バックテスト検証中 |
| **全体** | **総損益** | **≥ ¥80,000維持** | バックテスト検証中 |

---

## 技術的詳細

### get_threshold()パターンの利点

Phase 61.1でMarketRegimeClassifierに`get_threshold()`パターンを導入：

1. **閾値変更時にコード修正不要**
   - thresholds.yamlを変更するだけで閾値調整可能
   - デプロイ不要でA/Bテスト可能

2. **設定の一元管理**
   - 全てのレジーム閾値が1箇所に集約
   - 設定の見通しが良くなる

3. **テスト容易性**
   - モック関数で任意の閾値をテスト可能
   - 境界値テストが容易

---

**最終更新**: 2026年1月24日 - Phase 61.1完了（バックテスト検証中）

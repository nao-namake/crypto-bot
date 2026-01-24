# 暗号資産取引Bot - 開発計画

## 現在の状態

**Phase 60完了・Phase 61進行中** - 戦略分析・改修

※ 完了済みタスクの詳細は `docs/開発履歴/` を参照

---

## Phase 61: 戦略分析・改修（進行中）

**目的**: レジーム判定の最適化とトレンド型戦略の活性化

### 背景

Phase 60.7完了時点で総損益¥86,639（PF 1.58）を達成。しかし以下の課題が判明：

| 課題 | 詳細 | 影響 |
|------|------|------|
| **ADXTrendStrength赤字** | 7取引、勝率42.9%、¥-2,511損失 | 全体PFを低下 |
| **MACDEMACrossover発動0件** | 183日間で0取引 | トレンド型戦略が機能していない |
| **レジーム偏り** | tight_range 88.2%、trending 0% | 戦略多様性が活かされていない |

**根本原因**: `MarketRegimeClassifier`のハードコード閾値
- tight_range: BB幅 < 3% AND 価格変動 < 2% → 緩すぎて88%がここに吸収
- trending: ADX > 25 AND EMA傾き > 1% → 厳しすぎて0件

### 実装計画

| Phase | 内容 | 状態 |
|-------|------|------|
| 61.1 | レジーム判定閾値調整（thresholds.yaml + MarketRegimeClassifier） | ✅完了 |
| 61.2 | コードベース整理 + ADXTrendStrength評価・対応 | 🔄進行中 |
| 61.3 | MACDEMACrossover発動改善 | 📋予定（バックテスト結果待ち） |

---

### Phase 61.1: レジーム判定閾値調整 ✅完了

**目標**: trending発生率 0% → 5-15%、tight_range 88% → 60-70%

**実施内容**:
- thresholds.yamlにmarket_regimeセクション追加（27行）
- MarketRegimeClassifier修正（`get_threshold()`対応）
- テスト更新（モック関数対応、21件全成功）
- Walk-Forward Validationバグ修正（mode引数エラー）

**検証結果**:
- 単体テスト: 21件成功
- 全体テスト: 1206件成功（回帰なし）
- CI/CD: 成功（Run ID: 21300967165）
- バックテスト: CI実行中（Run ID: 21301254775）

**変更ファイル**:

| ファイル | 変更内容 |
|---------|---------|
| `config/core/thresholds.yaml` | market_regimeセクション追加 |
| `src/core/services/market_regime_classifier.py` | get_threshold()読み込み対応 |
| `tests/unit/services/test_market_regime_classifier.py` | モック関数対応テスト |
| `scripts/backtest/walk_forward_validation.py` | バックテストモード設定修正 |

---

### Phase 61.2: コードベース整理 🔄進行中

**目的**: バックテスト結果を待つ間に不要ファイルを整理

**実施内容**:

| 項目 | 削減量 | 内容 |
|------|--------|------|
| ログ整理 | 約500MB | 古いログファイル削除 |
| モデル整理 | 約31MB | Stacking関連モデル削除 |
| テスト整理 | 26テスト | dead code削除、xfailテスト整理 |
| README更新 | 5ファイル | models/、tests/ 配下 |

**削除ファイル**:
- `logs/crypto_bot.log.2026-01-14` 〜 `2026-01-20`
- `logs/ml/ab_test_*.log`、`ml_training_*.log`
- `models/production/stacking_ensemble.pkl`、`meta_learner.pkl`
- `tests/manual/`（ディレクトリ）
- `tests/unit/analysis/`（ディレクトリ）
- `tests/integration/test_phase_51_3_regime_strategy_integration.py`

**テスト整理結果**:
- trading/ xfailed: 12 → 1（-11）
- features/ skipped: 14 → 0（-14）
- 全体テスト数: 約1,200維持

---

### Phase 61.2続き: ADXTrendStrength評価・対応 📋予定

**判断フロー**:
1. 61.1完了後にバックテスト実行
2. ADXTrendStrength勝率を確認
   - 勝率 ≥ 50%: パラメータ微調整で継続
   - 勝率 < 50%: 全レジームで重み0.0に設定（無効化）

---

### Phase 61.3: MACDEMACrossover発動改善

**判断フロー**:
1. 61.1でtrending発生後、自動的に発動機会増加を確認
2. まだ発動が少ない場合:
   - `adx_trend_threshold`: 18→15に緩和
   - または`_is_trend_market()`にEMA乖離条件を追加

---

### 検証方法

```bash
# バックテスト実行
python3 main.py --mode backtest

# 結果分析
python3 scripts/backtest/standard_analysis.py --from-ci
```

### 成功基準

| Phase | 指標 | 目標値 |
|-------|------|--------|
| 61.1 | trending発生率 | ≥ 5% |
| 61.1 | tight_range発生率 | ≤ 70% |
| 61.2 | ADXTrendStrength勝率 | ≥ 50% or 無効化 |
| 61.3 | MACDEMACrossover取引数 | ≥ 10件 |
| **全体** | **PF** | **≥ 1.50維持** |
| **全体** | **総損益** | **≥ ¥80,000維持** |

---

## 完了済み: Phase 60

**目的**: リスク・リターン最適化と稼働率改善

| Phase | 内容 | 成果 |
|-------|------|------|
| 60.1 | 実効レバレッジ0.5倍移行 | 14箇所設定変更・年利75%目標 |
| 60.2 | 稼働率計算修正 | 7分間隔対応・稼働率100%表示 |
| 60.3 | Walk-Forward検証実装 | 過学習排除・信頼性向上 |
| 60.4 | ML重み削減・戦略重視設定 | 一致率向上・不一致ペナルティ強化 |
| 60.5 | MLモデル差別化 | シード差別化・特徴量サンプリング・動的重み計算 |
| 60.6 | Walk-Forward問題修正 | レジーム分布バグ修正・稼働率改善 |
| **60.7** | **¥86,639・PF 1.58達成** | **Phase 60最終結果** |

---

## 保留タスク

| タスク | 優先度 | 備考 |
|--------|--------|------|
| CatBoost追加 | 低 | 4モデルアンサンブル化 |
| SL指値非約定時の成行フォールバック | 中 | 急落時リスク対策 |
| 実効レバレッジ1.0倍移行 | 中 | 61完了後・結果良好な場合 |

---

## 関連ファイル

| ファイル | 内容 |
|---------|------|
| `docs/開発履歴/Phase_60.md` | Phase 60開発記録 |
| `docs/開発履歴/Phase_61.md` | Phase 61開発記録 |
| `docs/開発履歴/SUMMARY.md` | 全Phase総括 |
| `config/core/thresholds.yaml` | 戦略重み・レジーム設定 |

---

**最終更新**: 2026年1月24日 - Phase 61.2コードベース整理（進行中）

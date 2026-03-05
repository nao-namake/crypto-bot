# Phase 68: TP/SL手数料バグ修正 + Maker改善 + SL検出修正

**期間**: 2026年3月6日
**状態**: 実装完了・デプロイ待ち

| 変更 | 内容 | 状態 |
|------|------|------|
| **修正1** | TP計算にエントリー手数料(Taker 0.1%)を追加 | ✅ 完了 |
| **修正2** | SL計算にエントリー手数料(Taker 0.1%)を追加 | ✅ 完了 |
| **修正3** | Entry Maker戦略改善（best_bid/ask直接配置 + 板の奥リトライ） | ✅ 完了 |
| **修正4** | SL検出パターン拡充（Phase 63/64.12/65.13対応） | ✅ 完了 |
| **修正5** | 分析ツール設定検証の更新 | ✅ 完了 |

---

## 背景

### 問題1: TP/SL計算がエントリー手数料を無視

`fallback_entry_fee_rate: 0.0` により、Taker入場時の手数料(~115円)がTP/SL計算に含まれていなかった。

| 指標 | 修正前 | 修正後 |
|------|--------|--------|
| TP entry_fee | 0円 | 115円 |
| TP距離 | 50,000円(0.43%) | 61,500円(0.53%) |
| **TP純利益** | **386円** | **500円** |
| SL entry_fee | 0円 | 115円 |
| SL距離 | 58,500円(0.51%) | 47,000円(0.41%) |
| **SL実損失** | **814円** | **700円** |
| **実効RR** | **0.47:1** | **0.71:1** |

### 問題2: Entry Maker成功率0%

`post_only`注文がBTC/JPYの狭いスプレッド(1円)で即キャンセル。根本原因:

1. **初期価格**: `best_bid + 1` → スプレッド1円だと`best_ask`と同額 → post_only拒否
2. **リトライ方向**: buy時に`+tick`（市場側へ移動）→ さらにpost_only拒否されやすい

### 問題3: SL検出漏れ

分析ツールが `Phase 61.9: SL自動執行検知` のみ検索。Phase 63/64.12/65.13/67.5の成行SLが全てカウント外。

---

## 修正内容

### 修正1: TP エントリー手数料修正

**ファイル**: `config/core/thresholds.yaml`

```yaml
# Before:
fallback_entry_fee_rate: 0.0
# After:
fallback_entry_fee_rate: 0.001
```

コード変更不要。`strategy_utils.py`が既に`fallback_entry_fee_rate`を読んで計算。

### 修正2: SL エントリー手数料追加

**ファイル**: `config/core/thresholds.yaml` + `src/strategies/utils/strategy_utils.py`

設定:
```yaml
fixed_amount:
  enabled: true
  target_max_loss: 700
  include_entry_fee: true        # 追加
  fallback_entry_fee_rate: 0.001 # 追加
  include_exit_fee: true
  fallback_exit_fee_rate: 0.001
```

コード:
```python
# Phase 68: エントリー手数料もSL予算から差し引く
entry_fee_rate = fixed_sl_config.get("fallback_entry_fee_rate", 0.001)
entry_fee = current_price * position_amount * entry_fee_rate
gross_loss = sl_target - exit_fee - entry_fee
```

### 修正3: Entry Maker改善

**ファイル**: `src/trading/execution/order_strategy.py` + `config/core/thresholds.yaml`

#### 価格計算の変更

| 項目 | Before | After |
|------|--------|-------|
| 初期価格(buy) | `best_bid + tick`（スプレッド内配置） | `best_bid`（直接配置） |
| 初期価格(sell) | `best_ask - tick`（スプレッド内配置） | `best_ask`（直接配置） |
| リトライ方向(buy) | `+tick`（市場側=post_only拒否） | `-tick`（板の奥=Maker維持） |
| リトライ方向(sell) | `-tick`（市場側=post_only拒否） | `+tick`（板の奥=Maker維持） |

#### 設定変更

| パラメータ | Before | After | 理由 |
|-----------|--------|-------|------|
| `timeout_seconds` | 30 | 60 | Maker約定待ち時間を確保 |
| `retry_interval_ms` | 200 | 5000 | 各リトライで十分な約定待ち |
| `max_retries` | 5 | 3 | 板の奥配置で少ないリトライで十分 |
| `price_adjustment_tick` | 1 | 100 | 板の奥へ100円ずつ移動 |

#### 動作フロー

```
BUY注文の場合:
  試行1: best_bid で配置 → 5秒待機
  試行2: best_bid - 100円 で配置 → 5秒待機
  試行3: best_bid - 200円 で配置 → 5秒待機
  全失敗 or 60秒タイムアウト → Takerフォールバック
```

### 修正4: SL検出パターン拡充

**ファイル**: `scripts/live/standard_analysis.py`

検出クエリに以下を追加:
- `Phase 63: stop_limitタイムアウト`
- `Phase 65.13: SLキャンセル且つSL超過検出`
- `Phase 64.12: SLトリガー超過`

PnL取得不可のSLイベントは`pnl=None`として件数のみカウント。

### 修正5: 設定検証更新

`_verify_config()`に追加:
- `Entry Maker有効`: enabled=true確認
- `Maker timeout_seconds`: 60秒確認
- `TP entry_fee_rate`: 0.001確認
- `SL entry_fee_rate`: 0.001確認

旧Maker検証（max_retries=5, retry_interval_ms=200）を削除。

---

## 変更ファイル一覧

| # | ファイル | 変更内容 |
|---|---------|---------|
| 1 | `config/core/thresholds.yaml` | TP fee率修正、SL fee追加、Maker設定改善 |
| 2 | `src/strategies/utils/strategy_utils.py` | SL計算にentry fee差し引き追加 |
| 3 | `src/trading/execution/order_strategy.py` | Maker価格計算 + リトライ方向修正 |
| 4 | `scripts/live/standard_analysis.py` | SL検出パターン拡充 + 設定検証更新 |
| 5 | `tests/unit/strategies/utils/test_fixed_amount_tp.py` | Phase 68テスト4件追加 |
| 6 | `tests/unit/trading/execution/test_order_strategy.py` | Maker価格テスト更新 |

---

## テスト結果

```
1945 passed, 1 skipped, 75.25% coverage
flake8/black/isort: all PASS
```

### 新規テスト

- `TestPhase68EntryFeeCorrection::test_tp_with_taker_entry_fee` — TP距離61,500円確認
- `TestPhase68EntryFeeCorrection::test_tp_without_entry_fee_for_comparison` — 比較用
- `TestPhase68EntryFeeCorrection::test_tp_entry_fee_increases_distance` — 差分11,500円確認
- `TestPhase68EntryFeeCorrection::test_sell_tp_with_taker_entry_fee` — SELL方向確認

---

## 設計判断

### エントリー手数料をTaker(0.1%)で計算する理由

TP/SL計算は**最悪ケース**を想定すべき。Makerで約定すれば手数料0%で追加利益となるが、Taker約定時にTP利益が目標を下回るリスクを排除するため、常にTaker(0.1%)で計算。

### Makerを無効化せずに改善した理由

Maker約定時は手数料0%。エントリー手数料115円が不要になるため、TP純利益が500→615円に改善する。成功率0%の根本原因（スプレッド内配置 + 市場側リトライ）を修正し、best_bid/ask直接配置 + 板の奥リトライで確実なMaker注文を実現。タイムアウト後はTakerフォールバックで約定保証。

# Phase 68: TP/SL手数料バグ修正 + Maker改善 + SL検出修正

**期間**: 2026年3月6日〜12日
**状態**: Phase 68.7まで完了・デプロイ待ち

| 変更 | 内容 | 状態 |
|------|------|------|
| **修正1** | TP計算にエントリー手数料(Taker 0.1%)を追加 | ✅ 完了 |
| **修正2** | SL計算にエントリー手数料(Taker 0.1%)を追加 | ✅ 完了 |
| **修正3** | Entry Maker戦略改善（best_bid/ask直接配置 + 板の奥リトライ） | ✅ 完了 |
| **修正4** | SL検出パターン拡充（Phase 63/64.12/65.13対応） | ✅ 完了 |
| **修正5** | 分析ツール設定検証の更新 | ✅ 完了 |
| **Phase 68.2** | SL超過成行決済50062修正 + PnL手数料TP/SL分離 | ✅ 完了 |
| **Phase 68.3** | SL永続保護（キャンセル禁止） | ✅ 完了 |
| **Phase 68.4** | INACTIVE SL検出問題の根本解決（2層防御） | ✅ 完了 |
| **Phase 68.5** | コードレビュー指摘3件修正（SLログ・Logger JST・未使用設定削除） | ✅ 完了 |
| **Phase 68.6** | SL消失問題の根本解決（3バグ修正） | ✅ 完了 |
| **Phase 68.7** | SL永続化クリア包括追加 + SL金額500円変更 | ✅ 完了 |

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

---

## Phase 68.2: SL超過成行決済50062修正 + PnL手数料修正

**日付**: 2026年3月7日

### 背景

ライブ分析で2つの問題を発見:

1. **SL超過成行決済が50062エラーで失敗**: `_place_missing_tp_sl()`のPre-Check #1が既存TP/SL注文キャンセル前に成行決済を試行 → bitbankが「保有建玉数量超過」で拒否 → `return`で全フロー中断 → SL未配置のまま放置 → 5,000円損失発生
2. **PnL検出がTP決済にTaker手数料を適用**: `_calc_pnl()`が常にTaker 0.1%で計算。TP決済はMaker 0%のため、表示PnLが実際より~115円少ない

### 修正内容

#### 修正1: Pre-Check #1削除（50062修正）

**ファイル**: `src/trading/execution/tp_sl_manager.py`

キャンセル前のSL超過チェック（Pre-Check #1、38行）を完全削除。キャンセル後のPre-Check #2が同じ保護を提供する。

| フロー | Before | After |
|--------|--------|-------|
| SL超過検出 | Pre-Check #1（キャンセル前）→ 50062エラー → return | キャンセル後のPre-Check #2 → 成行決済成功 |
| 安全性 | キャンセル前は既存SL注文が保護 | キャンセル後に即座にチェック |

#### 修正2: PnL手数料率をTP/SLで分離

**ファイル**: `src/trading/execution/stop_manager.py` + `tp_sl_config.py` + `thresholds.yaml`

`_calc_pnl()`に`execution_type`引数を追加し、TP決済とSL決済で異なる手数料率を適用:

```python
def _calc_pnl(self, entry_price, exit_price, amount, side, execution_type="stop_loss"):
    entry_fee_rate = get_threshold(TPSLConfig.ENTRY_TAKER_RATE, 0.001)  # 常にTaker 0.1%
    if execution_type == "take_profit":
        exit_fee_rate = get_threshold(TPSLConfig.EXIT_MAKER_RATE, 0.0)  # Maker 0%
    else:
        exit_fee_rate = get_threshold(TPSLConfig.EXIT_TAKER_RATE, 0.001)  # Taker 0.1%
```

| 決済タイプ | exit_fee_rate | PnL影響 |
|-----------|---------------|---------|
| take_profit | 0%（Maker） | +~115円（正確に） |
| stop_loss | 0.1%（Taker） | 変更なし |
| emergency | 0.1%（Taker） | 変更なし |

### 変更ファイル一覧

| # | ファイル | 変更内容 |
|---|---------|---------|
| 1 | `src/trading/execution/tp_sl_config.py` | `EXIT_MAKER_RATE`定数追加 |
| 2 | `config/core/thresholds.yaml` | `exit_maker_rate: 0.0`追加 |
| 3 | `src/trading/execution/tp_sl_manager.py` | Pre-Check #1（38行）削除 |
| 4 | `src/trading/execution/stop_manager.py` | `_calc_pnl()`にexecution_type追加 + コール元2箇所更新 |
| 5 | `tests/unit/trading/execution/test_stop_manager.py` | PnL手数料テスト4件追加 + 既存TP期待値4件更新 |
| 6 | `tests/unit/trading/execution/test_phase675.py` | Pre-Check #1削除に伴うテスト更新 |

### テスト結果

```
1949 passed, 1 skipped, 75%+ coverage
flake8/black/isort: all PASS
```

#### 新規テスト

- `TestPhase682PnlFeeCalculation::test_tp_exit_uses_maker_rate` — TP=Maker 0%確認
- `TestPhase682PnlFeeCalculation::test_sl_exit_uses_taker_rate` — SL=Taker 0.1%確認
- `TestPhase682PnlFeeCalculation::test_emergency_exit_uses_taker_rate` — 緊急=Taker確認
- `TestPhase682PnlFeeCalculation::test_default_execution_type_is_stop_loss` — 後方互換性確認

---

## Phase 68.3: SL永続保護（キャンセル禁止）

**日付**: 2026年3月9日

### 背景

SL注文が定期チェック(`_place_missing_tp_sl`)時にキャンセル→再配置される設計のため、キャンセル中のSL不在期間に価格が急変し、目標700円の損切りが2000円超の損失になる問題が繰り返し発生。

根本原因: `_cancel_partial_exit_orders()`がTP/SL両方を無差別にキャンセルしていた。

### 修正内容

#### 修正1: SL保護パラメータ追加

`_cancel_partial_exit_orders()`に`cancel_sl`パラメータ追加。SL存在時は`cancel_sl=False`で呼び出し、TP注文のみキャンセル。

#### 修正2: Phase 67.5 SL超過チェックをSL不在時のみ実行

SL存在時は取引所側SLが保護中のため、SL超過チェック（fetch_ticker + 成行決済）をスキップ。

#### 修正3: VP再構築時の既存SL情報引き継ぎ

VP削除前に既存SL order IDを保存し、VP再作成時に引き継ぎ。

### 変更ファイル一覧

| # | ファイル | 変更内容 |
|---|---------|---------|
| 1 | `src/trading/execution/tp_sl_manager.py` | cancel_sl保護 + Phase 67.5条件分岐 + existing_sl_info引き継ぎ |
| 2 | `tests/unit/trading/execution/test_phase675.py` | Phase 68.3テスト3件追加 |

### テスト結果

```
1952 passed, 1 skipped, 75.22% coverage
flake8/black/isort: all PASS
```

#### 新規テスト

- `test_sl_preserved_when_tp_only_update` — has_sl=True時にcancel_sl=Falseで呼ばれること
- `test_sl_placed_when_missing` — has_sl=False時にcancel_sl=Falseで呼ばれること（Phase 68.4で変更）
- `test_phase675_skipped_when_sl_exists` — SL存在時にPhase 67.5がスキップされること

---

## Phase 68.4: INACTIVE SL検出問題の根本解決（2層防御）

**日付**: 2026年3月10日

### 背景

Phase 63〜68.3で多数のSL保護修正を重ねてきたが、ライブ分析で依然「SL未設定」警告が出る。bitbank管理画面でも実際にSL注文が存在しないことを確認済み。

#### 根本原因

bitbankの`stop_limit`注文はトリガー価格到達前に**INACTIVE状態**となり、`fetch_active_orders`（ccxt `fetch_open_orders`）に返されない。BotがINACTIVE SLを「存在しない」と誤判定し、キャンセル→再配置を試みて失敗する連鎖障害。

```
Container再起動時の連鎖障害:
  1. VP（インメモリ）消失 → sl_order_id喪失
  2. position_restorer: fetch_active_ordersでSLマッチング → INACTIVE未検出
  3. ensure_tp_sl: has_sl=False → cancel_sl=True（Phase 68.3保護が無効化）
  4. 既存INACTIVE SLがキャンセルされる → 再配置失敗時SL永久消失
```

Phase 68.3の`cancel_sl=False`保護は`has_sl=True`時のみ有効だったため、has_sl判定自体が失敗するこのケースでは無効化されていた。

### 解決方針: 2層防御

| Layer | 対象シナリオ | メカニズム |
|-------|------------|-----------|
| **Layer 1** | 通常起動（コンテナ存続中） | `data/sl_state.json`にSL注文IDを永続化 → `fetch_order(id)`で個別検証 |
| **Layer 2** | コンテナ再構築（ファイル消失） | SLキャンセルせず配置試行 → 50062エラー = 既存INACTIVE SL存在の証拠 |

**核心の修正**: `cancel_sl=False`を**常に**適用（`has_sl`の値に関係なく）。これによりINACTIVE SLが絶対にキャンセルされなくなった。

### 修正内容

#### 新規: SL注文ID永続化クラス

**ファイル**: `src/trading/execution/sl_state_persistence.py`

```python
class SLStatePersistence:
    """SL注文IDのローカルファイル永続化（INACTIVE SL対策）"""

    def save(side, sl_order_id, sl_price, amount)   # SL配置成功時
    def load() -> Dict                                # 起動時読み込み
    def clear(side)                                   # ポジション決済時
    def verify_with_api(side, bitbank_client) -> str  # fetch_order検証
```

`drawdown.py`の`_save_state`/`_load_state`パターンを参考に、`data/sl_state.json`にJSON永続化。`verify_with_api`は`fetch_order(id)`でINACTIVE含むステータスを個別取得して検証。

#### 修正1: SLキャンセル常時禁止 + 50062フォールバック

**ファイル**: `src/trading/execution/tp_sl_manager.py`

`_place_missing_tp_sl()`のフロー変更:

| ステップ | Before (Phase 68.3) | After (Phase 68.4) |
|---------|---------------------|---------------------|
| Step 0 キャンセル | `cancel_sl=(not has_sl)` | `cancel_sl=False`（常時） |
| SL配置 | キャンセル後にSL配置 | **SLキャンセルせず先に配置試行** |
| 50062対応 | なし | **50062 = 既存INACTIVE SL → has_sl=True** |
| Phase 67.5 | キャンセル後のSL超過チェック | SL配置もINACTIVE検出も失敗した場合のみ |

`ensure_tp_sl_for_existing_positions()`のINACTIVE SL検出:
- VP + active_ordersでSL未検出 → 永続化ファイルから`verify_with_api()`で検証
- 検証成功 → SLカバレッジに加算 + VPにsl_order_id復元

SL配置成功時の永続化フック:
- `place_stop_loss()`成功後に`sl_persistence.save()`呼び出し

#### 修正2: ポジション復元時のINACTIVE SL復元

**ファイル**: `src/trading/execution/position_restorer.py`

`restore_positions_from_api()`で、active_ordersからSL未検出時に永続化ファイルから復元:

```python
if not sl_order_id:
    verified_id = sl_persistence.verify_with_api(entry_side, bitbank_client)
    if verified_id:
        sl_order_id = verified_id  # INACTIVE SL復元
```

#### 修正3: TP/SL約定時のクリア

**ファイル**: `src/trading/execution/stop_manager.py`

`detect_auto_executed_orders()`でTP/SL約定検知時に`sl_persistence.clear()`呼び出し。

#### 修正4: 分析スクリプトのINACTIVE SL表示

**ファイル**: `scripts/live/standard_analysis.py`

`_check_tp_sl_placement()`でSL未検出時に永続化ファイルからINACTIVE SLを検証・表示。

### 動作フロー

#### 通常起動（コンテナ存続中、Layer 1）

```
SL配置成功 → sl_state.json保存
    ↓
5分後 ensure_tp_sl → active_ordersにSLなし（INACTIVE）
    ↓
Layer 1: sl_state.json → verify_with_api → INACTIVE確認 → has_sl=True
    ↓
TP再配置のみ（SL保護維持）
```

#### コンテナ再構築（Layer 2）

```
コンテナ再構築 → sl_state.json消失 + VP消失
    ↓
position_restorer → active_ordersにSLなし + ファイルなし → SLなしVP
    ↓
ensure_tp_sl → has_sl=False
    ↓
_place_missing_tp_sl → cancel_sl=False（INACTIVE SL保護）
    ↓
SL配置試行 → 50062エラー（既存INACTIVE SLが存在）
    ↓
Layer 2: has_sl=True → INACTIVE SL保護
```

### 変更ファイル一覧

| # | ファイル | 変更内容 |
|---|---------|---------|
| 1 | `src/trading/execution/sl_state_persistence.py` | **新規** SL注文ID永続化クラス |
| 2 | `src/trading/execution/tp_sl_manager.py` | cancel_sl常時False + 50062フォールバック + 永続化フック + INACTIVE SL検出 |
| 3 | `src/trading/execution/position_restorer.py` | 永続化SL復元ロジック追加 |
| 4 | `src/trading/execution/stop_manager.py` | 約定時sl_persistence.clear()追加 |
| 5 | `scripts/live/standard_analysis.py` | INACTIVE SL検証・表示追加 |
| 6 | `tests/unit/trading/execution/test_sl_state_persistence.py` | **新規** 19テスト（save/load/clear/verify全パターン） |
| 7 | `tests/unit/trading/execution/test_phase675.py` | Phase 68.4に伴うテスト更新（cancel_sl=False等） |

### テスト結果

```
1971 passed, 1 skipped, 75%+ coverage
flake8/black/isort: all PASS
```

#### 新規テスト（19件）

- `TestSLStatePersistence::test_save_and_load` — save→loadで正しく復元
- `TestSLStatePersistence::test_save_both_sides` — buy/sell両方保存
- `TestSLStatePersistence::test_save_overwrites_same_side` — 同サイド上書き
- `TestSLStatePersistence::test_clear` — 指定サイドのみ削除
- `TestSLStatePersistence::test_clear_nonexistent` — 存在しないサイドのclear
- `TestSLStatePersistence::test_load_empty` — ファイル未存在時
- `TestSLStatePersistence::test_load_corrupted_file` — 壊れたJSON
- `TestSLStatePersistence::test_save_error_handling` — 保存エラー
- `TestSLStatePersistence::test_clear_error_handling` — クリアエラー
- `TestSLStatePersistence::test_verify_with_no_order_id_in_state` — order_idなし
- `TestSLStatePersistenceVerifyWithAPI::test_verify_valid_inactive_sl` — INACTIVE=valid
- `TestSLStatePersistenceVerifyWithAPI::test_verify_valid_open_sl` — open=valid
- `TestSLStatePersistenceVerifyWithAPI::test_verify_canceled_sl` — canceled=無効→クリア
- `TestSLStatePersistenceVerifyWithAPI::test_verify_closed_sl` — closed=無効→クリア
- `TestSLStatePersistenceVerifyWithAPI::test_verify_order_not_found` — 注文消失→クリア
- `TestSLStatePersistenceVerifyWithAPI::test_verify_no_saved_state` — 保存データなし
- `TestSLStatePersistenceVerifyWithAPI::test_verify_api_returns_none` — API Null
- `TestSLStatePersistenceVerifyWithAPI::test_verify_api_error_non_not_found` — 一時エラー（クリアしない）
- `TestSLStatePersistenceVerifyWithAPI::test_verify_unfilled_status` — unfilled=valid

---

## Phase 68.5: コードレビュー指摘3件修正

**日付**: 2026年3月11日

### 修正内容

| # | 指摘 | 修正内容 |
|---|------|---------|
| 1 | SLキャンセル時のログ不足 | SLキャンセル時に詳細ログ追加 |
| 2 | Logger JST時刻の不統一 | Logger全体でJST統一 |
| 3 | 未使用設定の残存 | 不要な設定項目を削除 |

### テスト結果

```
1990 passed, 1 skipped, 75%+ coverage
flake8/black/isort: all PASS
```

---

## Phase 68.6: SL消失問題の根本解決（3バグ修正）

**日付**: 2026年3月12日

### 背景

Phase 68〜68.5でSL永続保護を実装したが、ライブ運用でSLが依然として消失する問題が継続。徹底調査の結果、SLが消える**3つの根本原因バグ**を特定。

Phase 68.3-68.4の修正（cancel_sl=False、sl_state.json永続化、50062検出）は「SLを守る防御層」だったが、**SLを消す攻撃側のバグ**が残っていたため効果が不十分だった。

### 因果関係

```
新規エントリー → cleanup_old_tp_sl_before_entry → Bug 3: SLもキャンセル → SLなし

SLタイムアウト → cleanup_position_orders(reason="stop_loss_timeout")
  → Bug 1: TPキャンセルされない → 成行決済で50062
  → Bug 2: SL再配置なし → SLなし
```

### Bug 1: stop_loss_timeout時にTPがキャンセルされない → 50062 → SL消失

**ファイル**: `src/trading/execution/stop_manager.py`

**問題**: `cleanup_position_orders(reason="stop_loss_timeout")`が呼ばれた時、TP注文キャンセル条件が`reason in ["stop_loss", "manual", "position_exit"]`で、`"stop_loss_timeout"`は部分一致せず**TPがキャンセルされない**。

**結果の連鎖**:
1. SLタイムアウト → 成行決済試行（TPが残ったまま）
2. TP注文 + 成行決済 = 保有建玉数量超過 → **50062エラー**
3. 成行決済失敗 → SLも既にキャンセル済み → **SLなし状態が確定**

**修正**: `reason in [...]`を`reason.startswith("stop_loss")`に変更。同様にSL側も`reason.startswith("take_profit")`に変更。

### Bug 2: SLタイムアウト成行決済失敗後にSL再配置なし

**ファイル**: `src/trading/execution/stop_manager.py`

**問題**: stop_limitタイムアウト処理で、成行決済が50062で失敗した場合、警告ログのみで**SLの再配置を一切行わない**。

**修正**: `_replace_sl_order()`メソッドを新規追加。成行決済失敗時にbitbank APIでstop_limit SL注文を直接再配置し、`sl_state.json`にも永続化。

### Bug 3: 新規エントリー時にSL注文が巻き添えキャンセルされる

**ファイル**: `src/trading/execution/tp_sl_manager.py`

**問題**: `cleanup_old_tp_sl_before_entry()`が新規エントリー前に呼ばれ、**既存ポジションのSL注文まで含めてキャンセル**してしまう。

具体的な2箇所:
1. VP追跡ループで`("tp_order_id", "sl_order_id")`の両方をキャンセル → `("tp_order_id",)`のみに変更
2. active_ordersループで`stop`/`stop_limit`型もSLとして判定しキャンセル → `is_sl = False`に変更

### 変更ファイル一覧

| # | ファイル | Bug | 変更内容 |
|---|---------|-----|---------|
| 1 | `src/trading/execution/stop_manager.py` | Bug 1 | reason文字列マッチをstartswith()に変更 |
| 2 | `src/trading/execution/stop_manager.py` | Bug 2 | `_replace_sl_order()`新規追加 + 成行決済失敗時フォールバック |
| 3 | `src/trading/execution/tp_sl_manager.py` | Bug 3 | cleanup_old_tp_sl_before_entryからSLキャンセルを除外 |
| 4 | `tests/unit/trading/execution/test_stop_manager.py` | Bug 1,2 | reason文字列テスト3件 + SL再配置テスト5件追加 |
| 5 | `tests/unit/trading/execution/test_tp_sl_manager.py` | Bug 3 | SL保護テスト更新3件 |
| 6 | `tests/unit/trading/execution/test_executor.py` | Bug 3 | cleanup_old_tp_sl_before_entryテスト更新3件 |

### テスト結果

```
1995 passed, 1 skipped, 75.02% coverage
flake8/black/isort: all PASS
```

#### 新規テスト

- `TestPhase686ReasonStringMatch::test_stop_loss_timeout_cancels_tp` — stop_loss_timeoutでTPキャンセル
- `TestPhase686ReasonStringMatch::test_stop_loss_prefix_cancels_tp` — stop_loss_プレフィックスでTPキャンセル
- `TestPhase686ReasonStringMatch::test_unrelated_reason_skips_tp` — 無関係reasonではスキップ
- `TestPhase686ReplaceSLOrder::test_replace_sl_order_success` — SL再配置成功
- `TestPhase686ReplaceSLOrder::test_replace_sl_order_no_stop_loss` — SL価格なし
- `TestPhase686ReplaceSLOrder::test_replace_sl_order_no_client` — クライアントなし
- `TestPhase686ReplaceSLOrder::test_replace_sl_order_empty_order_id` — 注文ID空
- `TestPhase686ReplaceSLOrder::test_replace_sl_order_sell_side_stop_limit` — ショートSL再配置

---

## Phase 68.7: SL永続化クリア包括追加 + SL金額500円変更

**日付**: 2026年3月12日

### 背景

Phase 68.4で導入した`sl_persistence.clear()`が`detect_auto_executed_orders()`の1箇所のみで、他の決済経路で欠落していた。これにより、古いSL IDが`sl_state.json`に残存し、次回のSL配置時に不整合が発生するリスクがあった。

### 修正内容

| # | ファイル | 変更内容 |
|---|---------|---------|
| 1 | `config/core/thresholds.yaml` | `target_max_loss` 700→500 |
| 2 | `src/trading/execution/stop_manager.py` | `_execute_position_exit()`: clear()追加（全決済共通合流点） |
| 3 | `src/trading/execution/stop_manager.py` | 消失ポジション強制削除: clear()追加 |
| 4 | `src/trading/execution/tp_sl_manager.py` | `place_sl_or_market_close()`: SL超過成行決済時にclear()追加 |
| 5 | `src/trading/execution/stop_manager.py` | `_replace_sl_order()`: 重複コードコメント追加 |

### SL金額変更

| 設定 | Before | After |
|------|--------|-------|
| `target_max_loss` | 700円 | 500円 |

### sl_persistence.clear() 追加箇所

| # | 経路 | メソッド | 説明 |
|---|------|---------|------|
| 1 | 既存 | `detect_auto_executed_orders()` | Phase 68.4で追加済み |
| 2 | **新規** | `_execute_position_exit()` | 全決済の共通合流点（TP約定・SLタイムアウト・手動決済） |
| 3 | **新規** | 消失ポジション強制削除 | APIにポジションなし→VP削除時 |
| 4 | **新規** | `place_sl_or_market_close()` | SL超過成行決済成功時 |

### テスト結果

```
2000 passed, 1 skipped, 75%+ coverage
flake8/black/isort: all PASS
```

#### 新規テスト（5件）

- `test_vanished_position_clears_sl_persistence` — 消失ポジション削除時にclear()呼び出し
- `test_execute_position_exit_clears_sl_persistence_buy` — BUY決済時にclear("buy")
- `test_execute_position_exit_clears_sl_persistence_sell` — SELL決済時にclear("sell")
- `test_execute_position_exit_sl_persistence_clear_failure` — clear()失敗でも決済継続
- `test_sl_exceeded_market_close_clears_sl_persistence` — SL超過成行決済時にclear()呼び出し

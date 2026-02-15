# Phase 64: TP/SLシンプル化 + システム全体整理

**期間**: 2026年2月14日〜（進行中）
**状態**: 🔄 Phase 64.1-64.2, 64.4完了、64.3待機
**目的**: TP/SLロジックの過度な複雑性を整理し、設置不具合の根本原因を解消する

---

## サマリー

| Phase | 内容 | 状態 |
|-------|------|------|
| **64.1** | src/trading/ 完全整理（メソッド移動・責務分離） | ✅ 完了 |
| **64.2** | TP/SL配置信頼性の根本修正（例外スワロー排除・リトライ正常化） | ✅ 完了 |
| **64.3** | virtual_positions二重管理解消 | ⏳ 待機 |
| **64.4** | デッドコード削除・重複統合・整合性バグ修正・ドキュメント更新 | ✅ 完了 |

---

## 背景

Phase 58-63で繰り返しTP/SL関連のバグ修正を実施。改修コード同士が干渉し合い、以下の問題が発生していた：

| 問題 | 詳細 |
|------|------|
| **コードの肥大化** | executor.py（1,943行）・stop_manager.py（2,177行）にTP/SLロジックが分散 |
| **責務の混在** | executor.pyにTP/SL計算・Maker実行・クリーンアップが混在 |
| **委譲パターンの複雑化** | executor→stop_manager→tp_sl_managerの間接呼び出し |
| **設定パスtypo** | Phase 63.6でCRITICALバグ3件が設定パス文字列のtypoで発生 |
| **条件分岐の深度** | Phase 58-63のバグ修正で条件分岐が深度8以上に複雑化 |

---

## Phase 64.1: src/trading/ 完全整理（✅完了）

**実施日**: 2026年2月14日〜15日
**方針**: メソッドの「移動」のみ。ロジック変更なし。既存テスト全通過で安全性担保。

### 実施内容（10ステップ）

| Step | 内容 | 変更ファイル |
|------|------|------------|
| 1 | stop_manager.pyの重複クールダウン削除（-102行） | stop_manager.py, test_stop_manager.py |
| 2 | TP/SL配置メソッドをtp_sl_manager.pyに移動（-340行） | stop_manager.py, tp_sl_manager.py, test_tp_sl_manager.py |
| 3 | クリーンアップメソッドをposition_restorer.pyに移動（-239行） | stop_manager.py, position_restorer.py, tp_sl_manager.py, executor.py |
| 4 | `_calculate_tp_sl_for_live_trade`をtp_sl_manager.pyに移動（-213行） | executor.py, tp_sl_manager.py |
| 5 | Maker実行をorder_strategy.pyに移動（-196行） | executor.py, order_strategy.py |
| 6 | 薄いラッパーメソッド7個をインライン化（-106行） | executor.py |
| 7 | `_rollback_entry`/`_ensure_minimum_trade_size`を各移動先に移動（-111行） | executor.py, tp_sl_manager.py, order_strategy.py |
| 8 | `__init__.py`更新（Phase 64対応） | src/trading/__init__.py, src/trading/execution/__init__.py |
| 9 | README.md全面更新 | src/trading/execution/README.md |
| 10 | テスト更新・flake8/black/isort対応 | test_executor.py, test_stop_manager.py, test_position_restorer.py |

### ファイル行数変化

| ファイル | Before | After | 変化 | 責務 |
|---------|--------|-------|------|------|
| `executor.py` | 1,943 | 1,297 | **-646 (-33%)** | エントリー実行に集中 |
| `stop_manager.py` | 2,177 | 1,525 | **-652 (-30%)** | TP/SL到達判定・決済のみ |
| `order_strategy.py` | 511 | 767 | +256 | 注文タイプ決定・Maker実行・最小ロット保証 |
| `tp_sl_config.py` | 125 | 125 | 0 | 設定パス定数 |
| `tp_sl_manager.py` | 885 | 1,505 | +620 | TP/SL配置・検証・復旧・計算・ロールバック統合 |
| `position_restorer.py` | 345 | 554 | +209 | ポジション復元・孤児クリーンアップ統合 |
| **合計** | **5,986** | **5,773** | **-213** | |

### 削除したラッパーメソッド（Step 6）

executor.pyから削除し、呼び出し元で直接tp_sl_manager/position_restorerを呼ぶように変更：

| メソッド | 行数 | 委譲先 |
|---------|------|--------|
| `_place_tp_with_retry` | 22行 | `tp_sl_manager.place_tp_with_retry()` |
| `_place_sl_with_retry` | 22行 | `tp_sl_manager.place_sl_with_retry()` |
| `_cleanup_old_tp_sl_before_entry` | 15行 | `tp_sl_manager.cleanup_old_tp_sl_before_entry()` |
| `_schedule_tp_sl_verification` | 21行 | `tp_sl_manager.schedule_tp_sl_verification()` |
| `_process_pending_verifications` | 7行 | `tp_sl_manager.process_pending_verifications()` |
| `_periodic_tp_sl_check` | 10行 | `tp_sl_manager.periodic_tp_sl_check()` |
| `_scan_orphan_positions` | 9行 | `position_restorer.scan_orphan_positions()` |
| `_check_tp_sl_orders_exist` | 20行 | `tp_sl_manager._check_tp_sl_orders_exist()` |
| `_place_missing_tp_sl` | 13行 | `tp_sl_manager._place_missing_tp_sl()` |

### 追加変更

- **OrderStrategy自動生成**: executor.pyの`__init__`で常に`OrderStrategy()`を生成（以前はNone初期化・後から注入）
- **重複クールダウン削除**: stop_manager.pyの`should_apply_cooldown()`/`_calculate_trend_strength()`をcooldown.pyと完全重複確認の上削除

### 品質検証

```
全テスト: 2,065 passed, 1 skipped ✅
カバレッジ: 72.53% ✅（基準62%+）
flake8 / black / isort: 全PASS ✅
```

---

## Phase 64.1 で解決できたこと・できていないこと

### 解決できたこと

| 項目 | 詳細 |
|------|------|
| **責務の明確化** | TP/SL配置→tp_sl_manager、クリーンアップ→position_restorer、到達判定→stop_manager |
| **委譲パターン排除** | executor→stop_manager→tp_sl_managerの三段委譲を排除、直接呼び出しに変更 |
| **コードの見通し改善** | executor.py -33%、stop_manager.py -30%で修正箇所の特定が容易に |
| **重複コード削除** | cooldown重複削除、ラッパーメソッドインライン化 |

### 未解決の根本問題

| 問題 | 詳細 | 関連Phase | 状態 |
|------|------|-----------|------|
| **例外スワロー** | `place_take_profit()`が例外catchして`None`返却→リトライ失敗と区別不能 | 64.2 | ✅ 解決 |
| **リトライ無効** | `place_tp_with_retry()`がNoneをretryせず3回空回り | 64.2 | ✅ 解決 |
| **ゾンビエントリ** | TP/SL配置失敗でもvirtual_positionsにNoneエントリ追加 | 64.2 | ✅ 解決 |
| **virtual_positions二重管理** | executor.virtual_positionsとposition_trackerの乖離 | 64.3 | ⏳ 未着手 |

---

## Phase 64.2: TP/SL配置信頼性の根本修正（✅完了）

**実施日**: 2026年2月15日
**方針**: `None`返却は「設定で無効」の場合のみ。それ以外は全て例外を上げてリトライを機能させる。

### 根本原因

`place_take_profit()`/`place_stop_loss()`が全例外をcatchして`None`を返すため：
1. **リトライが機能しない**: `place_tp_with_retry()`がNoneを受け取り、3回とも同じ失敗を繰り返す
2. **ゾンビエントリ**: 復旧処理で`tp_order_id=None`のエントリがvirtual_positionsに追加される
3. **再試行されない**: ゾンビエントリが存在するため次回の定期チェックで再試行が行われない

### 実施内容（5ステップ）

| Step | 内容 | 変更ファイル |
|------|------|------------|
| 1 | `place_take_profit()` 例外スワロー排除 | tp_sl_manager.py |
| 2 | `place_stop_loss()` 例外スワロー排除 | tp_sl_manager.py |
| 3 | `place_tp/sl_with_retry()` None即時リターン・リトライ正常化 | tp_sl_manager.py |
| 4 | `_place_missing_tp_sl()` 条件付きvirtual_positions追加 | tp_sl_manager.py |
| 5 | `scan_orphan_positions()` 条件付きvirtual_positions追加 | position_restorer.py |

### Step 1-2: 例外スワロー排除

**変更パターン**:

| 条件 | Before | After |
|------|--------|-------|
| 設定無効 | `return None` | `return None`（維持） |
| TP価格0以下 | `return None` | `raise TradingError(...)` |
| SL価格None/0以下/方向不正 | `return None` | `raise TradingError(...)` |
| Maker失敗+FB無効 | `return None` | `raise TradingError(...)` |
| 外側try/except | `except: return None` | **削除**（API例外は伝播） |

### Step 3: リトライロジック修正

```python
# Before: Noneでもリトライ（空回り）
for attempt in range(max_retries):
    tp_order = await self.place_take_profit(...)
    if tp_order:
        return tp_order
    # Noneの場合: 次のループへ（無意味なリトライ）
return None

# After: Noneは即時リターン、例外でリトライ
for attempt in range(max_retries):
    try:
        tp_order = await self.place_take_profit(...)
        if tp_order is None:
            return None  # 設定無効 → リトライ不要
        return tp_order  # 成功
    except Exception as e:
        if attempt < max_retries - 1:
            await asyncio.sleep(2 ** attempt)  # 1s, 2s, 4s
        else:
            raise  # 最終試行 → 例外伝播
```

### Step 4-5: virtual_positions条件付き追加

```python
# Before: 無条件追加（tp_order_id=None のゾンビエントリ生成）
virtual_positions.append(recovered_position)

# After: TP/SL両方成功した場合のみ追加
tp_ok = has_tp or (tp_order and tp_order.get("order_id"))
sl_ok = has_sl or (sl_order and sl_order.get("order_id"))
if tp_ok and sl_ok:
    virtual_positions.append(recovered_position)
else:
    self.logger.critical("🚨 TP/SL配置不完全（次回チェックで再試行）")
```

### フロー改善効果

#### エントリー時（executor.py Atomic Entry）
```
Before: API失敗 → None × 3回空回り → if not tp_order: raise → rollback
After:  API失敗 → 例外 → 1s待機→リトライ → 2s待機→リトライ → 最終失敗→rollback
```

#### 復旧フロー（_place_missing_tp_sl）
```
Before: 配置失敗 → None → virtual_positionsにNone追加 → ゾンビ化（再試行されない）
After:  配置失敗 → 例外catch → 追加しない → 10分後の定期チェックで再試行
```

#### 孤児スキャン（scan_orphan_positions）
```
Before: 配置失敗 → None → virtual_positionsにNone追加 → ゾンビ化
After:  配置失敗 → 例外 → continue → 追加しない → 30分後の再スキャンで再試行
```

### テスト更新

11テストの期待値を更新：
- `assert result is None` → `pytest.raises(TradingError)` に変更（価格不正・API失敗テスト）
- 設定無効テスト（`enabled: False`）は `assert result is None` を維持
- テストモックの修正（`mock_threshold.return_value = True` → `{"enabled": True}`）

### 品質検証

```
全テスト: 2,065 passed, 1 skipped ✅
カバレッジ: 72.54% ✅（基準62%+）
flake8 / black / isort: 全PASS ✅
```

---

## Phase 64.4: デッドコード削除・重複統合・整合性バグ修正（✅完了）

**実施日**: 2026年2月16日
**方針**: デッドコード・重複ロジック・整合性バグを一掃。動作変更は最小限・安全方向のみ。

### 問題一覧と対応

| # | 種別 | 内容 | 対応 |
|---|------|------|------|
| 1 | デッドコード | tp_sl_config.py 未使用定数4件 | 削除 |
| 2 | デッドコード | `_check_tp_sl_orders_exist()` 43行（呼出元ゼロ） | 削除 |
| 3 | 整合性バグ | scan_orphan_positionsのTP/SL検出がboolean方式（数量無視） | 数量ベース95%カバレッジに修正 |
| 4 | 重複+バグ | TP/SL価格計算が3箇所に重複、regime選択が不統一 | ヘルパー抽出+regime修正 |
| 5 | 重複 | SL超過→成行決済ロジックが2箇所に重複 | ヘルパー抽出 |
| 6 | 冗長ラッパー | cleanup委譲メソッド2件（付加価値ゼロ） | 削除→直接呼出 |
| 7 | レイヤー重複 | `_verify_and_rebuild_tp_sl`(169行)がensure_tp_slと同機能 | 委譲で30行に簡素化 |

### Step 1: デッドコード削除 — tp_sl_config.py

未使用定数4件を削除（grep確認済み・参照ゼロ）：
- `CLEANUP_MAX_RETRIES`, `CLEANUP_RETRY_DELAY`, `MAKER_FILL_THRESHOLD`, `MAKER_POLL_INTERVAL`

### Step 2: デッドコード削除 — `_check_tp_sl_orders_exist()`

Phase 64.3で`ensure_tp_sl_for_existing_positions()`内にインライン化済み。本メソッドは本番コードから一切呼ばれていない（テストのみ）。

- tp_sl_manager.py: メソッド本体43行を削除
- test_tp_sl_manager.py: `TestPhase643QuantityBasedDetection`クラス（5テスト）を削除
- test_executor.py: `TestCheckTpSlOrdersExist`クラス（4テスト）を削除

### Step 3: 整合性バグ修正 — position_restorer.py TP/SL検出

scan_orphan_positionsのTP/SL検出がboolean方式（1件でもあればTrue）で、0.001 BTCの注文で0.02 BTCポジションが「カバー済み」と誤判定されるバグを修正。

```python
# Before（boolean — バグ）:
has_tp = False
for order in active_orders:
    if order_side == exit_side and order_type == "limit":
        has_tp = True

# After（数量ベース95%カバレッジ）:
tp_total = sum(
    float(o.get("amount", 0))
    for o in active_orders
    if o.get("side", "").lower() == exit_side
    and o.get("type", "").lower() == "limit"
)
has_tp = tp_total >= pos_amount * 0.95
```

### Step 4: 重複統合 — TP/SL価格計算ヘルパー

3箇所に重複するTP/SL価格計算を`calculate_recovery_tp_sl_prices()`に統合。

**重複箇所**:
1. `_place_missing_tp_sl()` — **normal_range使用（バグ：他2箇所はtight_range）**
2. `_verify_and_rebuild_tp_sl()` — tight_range使用
3. `position_restorer.py scan_orphan_positions()` — tight_range使用

```python
def calculate_recovery_tp_sl_prices(
    self,
    position_side: str,
    avg_price: float,
    regime: str = "tight_range",  # デフォルト: 最保守
) -> Tuple[float, float]:
```

regime不統一バグも修正（`_place_missing_tp_sl`のnormal_range→tight_range = SL幅が狭くなり安全方向）。

### Step 5: 重複統合 — SL超過→成行決済ヘルパー

2箇所に重複するSL超過チェック+成行決済ロジックを`place_sl_or_market_close()`に統合。

**重複箇所**:
1. `tp_sl_manager.py _place_missing_tp_sl()`
2. `position_restorer.py scan_orphan_positions()`

### Step 6: ラッパー削除 — cleanup委譲メソッド

tp_sl_manager.pyの純粋な委譲メソッド2件を削除し、executor.pyからposition_restorerを直接呼出に変更。

- `cleanup_old_unfilled_orders()` → position_restorerに転送するだけ → 削除
- `cleanup_orphan_sl_orders()` → position_restorerに転送するだけ（呼出元ゼロ）→ 削除

### Step 7: レイヤー簡素化 — `_verify_and_rebuild_tp_sl`

169行の`_verify_and_rebuild_tp_sl`を`ensure_tp_sl_for_existing_positions`に委譲して30行に簡素化。

旧メソッドの問題:
- boolean検出（数量ベースでない）
- SL超過チェックなし
- virtual_positions更新なし

`process_pending_verifications()`にvirtual_positions/position_tracker引数を追加し、委譲先の統合チェックを活用。

### ファイル行数変化

| ファイル | Before (64.2) | After (64.4) | 変化 |
|---------|---------------|--------------|------|
| `executor.py` | 1,297 | ~1,300 | 微増（引数追加） |
| `stop_manager.py` | 1,525 | 1,525 | 変更なし |
| `order_strategy.py` | 767 | 767 | 変更なし |
| `tp_sl_config.py` | 125 | ~120 | -5（定数削除） |
| `tp_sl_manager.py` | 1,489 | ~1,250 | **-240** |
| `position_restorer.py` | 555 | ~560 | +5（数量ベース検出） |
| **合計** | **5,758** | **~5,522** | **-236** |

### 削除・統合サマリー

| 区分 | 件数 |
|------|------|
| デッドコード削除 | 5件（定数4+メソッド1） |
| 重複コード統合 | 4箇所→ヘルパー2件 |
| 整合性バグ修正 | 2件（boolean検出・regime不統一） |
| ラッパー削除 | 2件 |
| レイヤー簡素化 | 1件（169行→30行） |

### 品質検証

```
全テスト: 2,068 passed, 1 skipped ✅
カバレッジ: 72.96% ✅（基準62%+）
flake8 / black / isort: 全PASS ✅
```

---

## 最終ファイル構成（Phase 64.4完了時点）

```
src/trading/execution/
├── executor.py          ~1,300行  エントリー実行に集中
├── stop_manager.py      ~1,525行  TP/SL到達判定・決済のみ
├── order_strategy.py      ~770行  注文タイプ決定・Maker実行・最小ロット保証
├── tp_sl_config.py        ~120行  設定パス定数
├── tp_sl_manager.py     ~1,250行  TP/SL配置・検証・復旧・計算・ロールバック統合
└── position_restorer.py   ~560行  ポジション復元・孤児クリーンアップ統合
```

---

## 次のステップ

1. **Phase 64.3**: virtual_positions二重管理解消
   - PositionTracker一元管理への移行
   - executor.virtual_positionsとの同期問題解消

---

**最終更新**: 2026年2月16日

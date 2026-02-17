# Phase 64: TP/SLシンプル化 + システム全体整理

**期間**: 2026年2月14日〜（進行中）
**状態**: 🔄 Phase 64.1-64.6完了
**目的**: TP/SLロジックの過度な複雑性を整理し、設置不具合の根本原因を解消する

---

## サマリー

| Phase | 内容 | 状態 |
|-------|------|------|
| **64.1** | src/trading/ 完全整理（メソッド移動・責務分離） | ✅ 完了 |
| **64.2** | TP/SL配置信頼性の根本修正（例外スワロー排除・リトライ正常化） | ✅ 完了 |
| **64.3** | virtual_positions二重管理解消（property化・単一ソース化） | ✅ 完了 |
| **64.4** | デッドコード削除・重複統合・整合性バグ修正・ドキュメント更新 | ✅ 完了 |
| **64.5** | `src/strategies/`フォルダ全体監査・クリーンアップ | ✅ 完了 |
| **64.6** | `src/ml/`フォルダ監査・クリーンアップ | ✅ 完了 |

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
| **virtual_positions二重管理** | executor.virtual_positionsとposition_trackerの乖離 | 64.3 | ✅ 解決 |

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

## Phase 64.3: virtual_positions二重管理解消（✅完了）

**実施日**: 2026年2月18日
**方針**: `ExecutionService.virtual_positions`をPython propertyに変換し、`PositionTracker.virtual_positions`を単一ソースにする。全コンポーネントが同一listオブジェクトを操作する状態にする。

### 背景

`ExecutionService.virtual_positions`（プレーンlist）と`PositionTracker.virtual_positions`（ラッパー付きlist）が別々のlistオブジェクトとして存在。手動同期が必要だが、以下6箇所で同期漏れが発生していた：

| 同期漏れ箇所 | ファイル | 操作 |
|-------------|---------|------|
| Container再起動復元 | position_restorer.py | `virtual_positions.append(...)` |
| 孤児復旧(TP/SL既存) | position_restorer.py | `virtual_positions.append(...)` |
| 孤児復旧(TP/SL配置) | position_restorer.py | `virtual_positions.append(...)` |
| TP/SL復旧 | tp_sl_manager.py | `virtual_positions.append(...)` |
| TP/SL注文ID更新 | executor.py | `live_position["tp_order_id"] = ...` |
| 部分約定量更新 | executor.py | `vp["amount"] = partial_filled` |

**影響**: PositionTrackerのクエリメソッド（`find_position`, `get_position_count`等）が実態と乖離。将来的なバグの温床。

### 実施内容（5ステップ）

| Step | 内容 | 変更ファイル |
|------|------|------------|
| 1 | `add_position()`パラメータ拡張（sl_placed_at, restored, adjusted_confidence, timestamp） | tracker.py |
| 2 | `virtual_positions`をproperty化（PositionTracker単一ソース + fallback） | executor.py |
| 3 | list再代入を`[:]=`に変更（3箇所） | executor.py |
| 4 | 二重追加パターン統一（live/paper/backtest + 部分約定 + ロールバック） | executor.py |
| 5 | テスト追加（tracker新パラメータ8件 + 単一ソース検証6件） | test_tracker.py, test_executor.py |

### Step 1: PositionTracker.add_position()パラメータ拡張

復元・復旧時に必要なフィールドを`add_position()`で受け付けるように拡張（全パラメータOptional、既存呼出に影響なし）：

| パラメータ | 型 | 用途 |
|-----------|-----|------|
| `sl_placed_at` | `Optional[str]` | SL配置時刻（タイムアウトチェック用） |
| `restored` | `bool` | 復元フラグ（Container再起動復元の識別） |
| `adjusted_confidence` | `Optional[float]` | 調整済み信頼度（Phase 59.3） |
| `timestamp` | `Optional[datetime]` | タイムスタンプ（バックテスト時刻対応） |

### Step 2: virtual_positions property化

```python
# Before:
self.virtual_positions = []  # executor独自のlist

# After:
self._virtual_positions_fallback = []  # tracker注入前の一時保管

@property
def virtual_positions(self):
    if self.position_tracker is not None:
        return self.position_tracker.virtual_positions  # 単一ソース
    return self._virtual_positions_fallback

@virtual_positions.setter
def virtual_positions(self, value):
    if self.position_tracker is not None:
        self.position_tracker.virtual_positions[:] = value  # in-place更新
    else:
        self._virtual_positions_fallback = value
```

`inject_services()`でtracker注入時にfallbackデータを自動移行：

```python
if position_tracker:
    if self._virtual_positions_fallback:
        position_tracker.virtual_positions.extend(self._virtual_positions_fallback)
        self._virtual_positions_fallback.clear()
    self.position_tracker = position_tracker
```

### Step 3: list再代入を`[:]=`に変更

意図を明確にするため、3箇所のlist再代入をin-place更新に変更：

| 箇所 | Before | After |
|------|--------|-------|
| ロールバック削除 | `self.virtual_positions = [p for p in ...]` | `self.virtual_positions[:] = [...]` |
| 整合性クリーンアップ | `self.virtual_positions = [v for v in ...]` | `self.virtual_positions[:] = [...]` |
| 自動執行削除 | `self.virtual_positions = [p for p in ...]` | `self.virtual_positions[:] = [...]` |

### Step 4: 二重追加パターン統一

propertyにより同一listのため、「direct append + position_tracker.add_position()」の二重追加を解消：

#### ライブエントリー

```python
# Before: 手動dict作成→append→後でtracker.add_position()（二重追加）
live_position = {...}
self.virtual_positions.append(live_position)
# ... 後で:
if self.position_tracker:
    self.position_tracker.add_position(...)

# After: tracker経由で一元追加
if self.position_tracker:
    live_position = self.position_tracker.add_position(
        order_id=..., side=..., amount=..., price=...,
        take_profit=..., stop_loss=...,
    )
else:
    live_position = {...}
    self.virtual_positions.append(live_position)
```

#### ペーパー・バックテストエントリー

同様パターン。`position_tracker.add_position()`に`strategy_name`, `adjusted_confidence`, `timestamp`を渡すよう統一。try/exceptでエラー時のfallbackも確保。

#### 部分約定更新

```python
# Before: 直接ループ更新 + tracker remove/add（二重操作）
for vp in self.virtual_positions:
    if vp.get("order_id") == result.order_id:
        vp["amount"] = partial_filled
if self.position_tracker:
    self.position_tracker.remove_position(result.order_id)
    self.position_tracker.add_position(...)

# After: find_position + 直接更新（同一dictオブジェクト）
if self.position_tracker:
    pos = self.position_tracker.find_position(result.order_id)
    if pos:
        pos["amount"] = partial_filled
```

#### ロールバック削除

```python
# Before: listフィルタ + tracker.remove_position()（二重削除）
self.virtual_positions[:] = [p for p in ... if ...]
if self.position_tracker:
    self.position_tracker.remove_position(...)

# After: tracker経由で一元削除
if self.position_tracker:
    self.position_tracker.remove_position(result.order_id)
else:
    self.virtual_positions[:] = [p for p in ... if ...]
```

### Step 5: テスト追加

#### tracker.py新パラメータテスト（8件）

| テスト | 検証内容 |
|--------|---------|
| `test_add_position_with_sl_placed_at` | sl_placed_atフィールド追加 |
| `test_add_position_with_restored_flag` | restored=True追加 |
| `test_add_position_restored_false_not_added` | restored=False時フィールド不在 |
| `test_add_position_with_adjusted_confidence` | adjusted_confidence追加 |
| `test_add_position_adjusted_confidence_zero` | 0.0も正常にセット |
| `test_add_position_with_custom_timestamp` | カスタムtimestamp使用 |
| `test_add_position_default_timestamp` | デフォルトdatetime.now() |
| `test_add_position_all_new_params` | 全新パラメータ同時指定 |

#### executor.py単一ソース検証テスト（6件）

| テスト | 検証内容 |
|--------|---------|
| `test_virtual_positions_property_returns_tracker_list` | `executor.virtual_positions is tracker.virtual_positions` |
| `test_virtual_positions_fallback_without_tracker` | tracker未注入時のfallback動作 |
| `test_change_propagation_tracker_to_executor` | tracker→executor方向の変更伝播 |
| `test_change_propagation_executor_to_tracker` | executor→tracker方向の変更伝播 |
| `test_fallback_migration_on_inject` | 注入前データの自動移行 |
| `test_in_place_update_via_setter` | setterのin-place更新動作 |

### 変更ファイル一覧

| ファイル | 変更内容 | 行数変化 |
|---------|---------|---------|
| `src/trading/position/tracker.py` | add_position()パラメータ拡張 | +12行 |
| `src/trading/execution/executor.py` | property化 + 二重パターン統一 | ±40行 |
| `tests/unit/trading/position/test_tracker.py` | 新パラメータテスト8件 | +95行 |
| `tests/unit/trading/execution/test_executor.py` | 単一ソース検証テスト6件 | +75行 |

**変更不要（listが共有されるため自動的に動作）**:
- `src/trading/execution/tp_sl_manager.py` — `virtual_positions.append()`は共有listに反映
- `src/trading/execution/position_restorer.py` — 同上
- `src/trading/execution/stop_manager.py` — 参照のみ
- `src/core/execution/backtest_runner.py` — 参照のみ

### 品質検証

```
全テスト: 1,966 passed, 1 skipped ✅
カバレッジ: 72.40% ✅（基準62%+）
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

## Phase 64.5: `src/strategies/`フォルダ全体監査・クリーンアップ（✅完了）

**実施日**: 2026年2月16日
**方針**: 3エージェント並行監査で全20ファイルを調査。ロジック変更不要。デッドimport・冗長コード・import統一・テストコメントの軽微クリーンアップのみ。

### 監査結果

**総合評価**: `src/strategies/`のアーキテクチャは良好。Registry Pattern・StrategyBase継承・utils分離の設計は適切。

#### 修正不要と判断した項目

| 項目 | 理由 |
|------|------|
| `_create_hold_signal`の引数順不統一 | 各戦略固有の動作（adx_trendはdynamic_confidence対応）。統一は過剰 |
| `get_signal_proximity`が3/6戦略のみ | `hasattr()`チェックによる意図的設計。未実装戦略は該当指標なし |
| Registry/Loaderのテスト専用メソッド群 | Registry Patternの標準公開API。テスト可能性に貢献 |
| `regime_affinity`（格納のみ未使用） | Phase 51.8で将来用に追加。削除リスク > 保持コスト |
| confidence計算メソッドの統合 | adx_trendの7メソッドは各々異なる条件分岐。抽象化は過剰 |
| `List[str]` vs `list[str]`型ヒント混在 | flake8/mypy未検出・動作影響なし。全ファイル統一は変更範囲過大 |

### 実施内容

#### Step 1: デッドimport削除（4件）

| ファイル | 削除対象 | 理由 |
|---------|---------|------|
| `adx_trend.py` | `import numpy as np` | `np.`の使用箇所ゼロ |
| `adx_trend.py` | `Tuple`（from typing） | 使用箇所ゼロ |
| `atr_based.py` | `from datetime import datetime` | SignalBuilder経由で使用、直接呼出なし |
| `atr_based.py` | `from ...core.logger import get_logger` | base classが設定済み、直接呼出なし |

#### Step 2: 冗長logger再代入の削除（3件）

`StrategyBase.__init__()`（strategy_base.py:104）で`self.logger = get_logger()`が既に設定済み。サブクラスでの再代入は冗長。

| ファイル | 削除対象 |
|---------|---------|
| `adx_trend.py` | `self.logger = get_logger()` + `from ...core.logger import get_logger` |
| `donchian_channel.py` | `self.logger = get_logger()` + `from ...core.logger import get_logger` |
| `bb_reversal.py` | `self.logger = get_logger()` + `from ...core.logger import get_logger` |

#### Step 3: importパス統一（3件）

`utils/__init__.py`で全て再エクスポート済みのため、`from ..utils.strategy_utils import` → `from ..utils import` に統一。

| ファイル | 変更前 | 変更後 |
|---------|--------|--------|
| `adx_trend.py` | `from ..utils.strategy_utils import SignalBuilder, StrategyType` | `from ..utils import ...SignalBuilder, StrategyType` |
| `donchian_channel.py` | `from ..utils.strategy_utils import SignalBuilder, StrategyType` | `from ..utils import SignalBuilder, StrategyType` |
| `bb_reversal.py` | `from ..utils.strategy_utils import EntryAction, SignalBuilder, StrategyType` | `from ..utils import EntryAction, SignalBuilder, StrategyType` |

#### Step 4: テストコメント更新（3件）

削除済み戦略名の参照を現行戦略名に更新。

| ファイル | 変更前 | 変更後 |
|---------|--------|--------|
| `test_strategy_manager.py` L436 | `# MochipoyAlert相当` | `# BBReversal相当` |
| `test_strategy_manager.py` L445 | `# MultiTimeframe相当` | `# StochasticReversal相当` |
| `test_signal_builder.py` L161 | `# Phase 51.7 Day 7: MULTI_TIMEFRAME削除のためATR_BASED使用` | `# ATR_BASED使用` |

### 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `src/strategies/implementations/adx_trend.py` | `numpy`・`Tuple`import削除、`get_logger`import+再代入削除、importパス統一 |
| `src/strategies/implementations/atr_based.py` | `datetime`・`get_logger`import削除 |
| `src/strategies/implementations/donchian_channel.py` | `get_logger`import+再代入削除、importパス統一 |
| `src/strategies/implementations/bb_reversal.py` | `get_logger`import+再代入削除、importパス統一 |
| `tests/unit/strategies/test_strategy_manager.py` | コメント更新（2箇所） |
| `tests/unit/strategies/utils/test_signal_builder.py` | コメント更新（1箇所） |

### 品質検証

```
全テスト: 2,045 passed, 1 skipped ✅
カバレッジ: 72.96% ✅（基準62%+）
flake8 / black / isort: 全PASS ✅
```

---

## Phase 64.6: `src/ml/`フォルダ監査・クリーンアップ（✅完了）

**実施日**: 2026年2月17日
**方針**: 本番未使用のクラス・ファイルを削除し、`src/ml/`を70%削減。ProductionEnsemble + 3モデルのみ残す。

### 背景

`src/ml/`（2,712行・5ファイル）に4つのアンサンブルクラスが存在するが、本番使用はProductionEnsembleのみ。

| クラス | 本番使用 | 判断 |
|--------|---------|------|
| **ProductionEnsemble** | ✅ ml_loader.pyから使用 | 維持 |
| **StackingEnsemble** | ❌ `stacking_enabled: false`・pklファイル不在（Phase 59.10で無効化） | 削除 |
| **EnsembleModel** | ❌ model_manager.pyの型ヒントのみ | 削除 |
| **VotingSystem** | ❌ インスタンス化ゼロ | 削除 |
| **ModelManager** | ❌ src/・scripts/からimportなし | 削除 |
| **MetaLearningWeightOptimizer** | ❌ `meta_learning.enabled: false`（常にスキップ） | 削除 |
| **MarketRegimeAnalyzer** | ❌ meta_learning.py内部のみ | 削除 |
| **PerformanceTracker** | ❌ meta_learning.py内部のみ | 削除 |

### 実施内容

#### Step 1: ensemble.py — 未使用クラス3つ + enum削除（1,070行→~200行）

| 削除対象 | 行数 | 理由 |
|---------|------|------|
| `VotingMethod` enum | 6行 | VotingSystemの引数型のみ |
| `VotingSystem` | 165行 | インスタンス化ゼロ |
| `EnsembleModel` | 380行 | 本番未使用 |
| `StackingEnsemble` | 287行 | Phase 59.10で無効化済み |

ProductionEnsembleの軽微修正:
- `print()` → `self.logger.info()` に置換
- 重複import削除・late-binding import整理
- 未使用sklearn import削除

#### Step 2: ファイル削除（2ファイル・1,006行）

| ファイル | 行数 | 理由 |
|---------|------|------|
| `model_manager.py` | 337行 | 本番未使用（src/・scripts/からimportなし） |
| `meta_learning.py` | 669行 | 全3クラス無効化済み |

#### Step 3: ml_loader.py — Stacking関連コード削除

| 削除対象 | 内容 |
|---------|------|
| `_is_stacking_enabled()` | 常にfalseを返すメソッド |
| `_load_stacking_ensemble()` | StackingEnsemble読み込み全体（~90行） |
| Level 0分岐 | `if stacking_enabled:` |

フォールバック階層を簡素化:
```
Before: Level 0 (Stacking) → Level 1 (Full 55) → Level 2 (Basic 49) → Level 3 (再構築)
After:  Level 1 (Full 55) → Level 2 (Basic 49) → Level 3 (再構築)
```

#### Step 4: trading_cycle_manager.py — Meta-Learning関連削除

| 変更 | 内容 |
|------|------|
| Meta-Learning初期化ブロック削除 | `if get_threshold("ml.meta_learning.enabled", False)` + import |
| `_get_dynamic_weights()` 簡素化 | Meta-Learning分岐削除→固定重み返却のみ |
| `market_data_cache` 初期化追加 | `__init__`で`None`初期化（安全性向上） |
| エラーチェック簡素化 | `"EnsembleModel is not fitted"` → `"not fitted"` |

#### Step 5: その他参照箇所の更新

| ファイル | 修正内容 |
|---------|---------|
| `src/ml/__init__.py` | エクスポート10→5に削減 |
| `src/core/orchestration/ml_adapter.py` | EnsembleModel→ProductionEnsembleコメント修正 |
| `scripts/live/standard_analysis.py` | Stacking参照削除・モデルレベル判定簡素化 |
| `scripts/testing/validate_ml_models.py` | Stacking検証メソッド削除 |
| `src/README.md` | model_manager.py参照削除 |

#### Step 6: テストファイル整理

**削除（4ファイル）**:

| テストファイル | 理由 |
|---------------|------|
| `tests/unit/ml/test_voting_system.py` | VotingSystem削除 |
| `tests/unit/ml/test_model_manager.py` | ModelManager削除 |
| `tests/unit/ml/test_ensemble_model.py` | EnsembleModel削除 |
| `tests/unit/ml/test_meta_learning.py` | meta_learning.py削除 |

**修正（4ファイル）**:

| テストファイル | 修正内容 |
|---------------|---------|
| `tests/unit/ml/production/test_ensemble.py` | StackingEnsembleテストクラス削除 |
| `tests/unit/ml/test_ml_integration.py` | EnsembleModel→ProductionEnsemble使用に書換え |
| `tests/unit/core/orchestration/test_ml_loader.py` | Stacking関連テスト3クラス削除 |
| `tests/unit/core/services/test_ml_strategy_integration.py` | Meta-Learningテスト→固定重みテストに簡素化 |
| `tests/integration/test_phase_50_3_graceful_degradation.py` | Stacking参照削除 |
| `tests/unit/README.md` | 削除テストファイル参照除去 |

### ファイル行数変化

| ファイル | Before | After | 変化 |
|---------|--------|-------|------|
| `src/ml/ensemble.py` | 1,070 | ~200 | **-870** |
| `src/ml/model_manager.py` | 337 | 削除 | **-337** |
| `src/ml/meta_learning.py` | 669 | 削除 | **-669** |
| `src/ml/models.py` | 586 | 586 | 変更なし |
| `src/ml/__init__.py` | 50 | ~27 | -23 |
| `src/core/orchestration/ml_loader.py` | ~457 | ~298 | **-159** |
| **src/ml/ 合計** | **2,712** | **~813** | **-1,899 (-70%)** |

### 品質検証

```
全テスト: 1,952 passed, 1 skipped ✅
カバレッジ: 72.32% ✅（基準62%+）
flake8 / black / isort: 全PASS ✅
```

---

## 最終ファイル構成（Phase 64.6完了時点）

```
src/trading/execution/
├── executor.py          ~1,300行  エントリー実行に集中
├── stop_manager.py      ~1,525行  TP/SL到達判定・決済のみ
├── order_strategy.py      ~770行  注文タイプ決定・Maker実行・最小ロット保証
├── tp_sl_config.py        ~120行  設定パス定数
├── tp_sl_manager.py     ~1,250行  TP/SL配置・検証・復旧・計算・ロールバック統合
└── position_restorer.py   ~560行  ポジション復元・孤児クリーンアップ統合

src/ml/
├── __init__.py            ~27行  エクスポート（5クラス）
├── models.py             ~586行  BaseMLModel + LGBMModel + XGBModel + RFModel
└── ensemble.py           ~200行  ProductionEnsemble（3モデル重み付け投票）
```

---

## Phase 64.5時点の検証結果

### バックテスト結果（2026年2月16日 CI実行）

**期間**: 2025-07-01 〜 2025-12-31（6ヶ月）

| 指標 | 値 | 備考 |
|------|-----|------|
| 総取引数 | 400件 | Phase 62: 303件 → 64.5: 400件（TP500円化で取引増） |
| 勝率 | 89.2% | Phase 62: 59.7% → 64.5: 89.2%（固定金額TP効果） |
| 総損益 | **¥+102,135** | Phase 62: ¥+119,815（手数料改定影響） |
| PF | **2.47** | Phase 62: 1.65 → 64.5: 2.47 |
| 最大DD | ¥5,669 (0.94%) | Phase 62: ¥13,352 (2.14%) → 大幅改善 |
| 期待値 | ¥+255/取引 | - |
| リカバリーファクター | 30.26 | - |
| 平均ポジションサイズ | 0.022 BTC | - |

#### 戦略別パフォーマンス

| 戦略 | 取引数 | 勝率 | 総損益 |
|------|--------|------|--------|
| ATRBased | 332件 | 89.5% | ¥+85,958 |
| BBReversal | 22件 | 90.9% | ¥+6,885 |
| DonchianChannel | 26件 | 88.5% | ¥+2,807 |
| StochasticReversal | 16件 | 81.2% | ¥+3,680 |
| ADXTrendStrength | 4件 | 100.0% | ¥+2,805 |
| MACDEMACrossover | 0件 | - | ¥0 |

#### レジーム別パフォーマンス

| レジーム | 取引数 | 勝率 | 総損益 |
|----------|--------|------|--------|
| tight_range | 342件 | 88.6% | ¥+87,683 |
| normal_range | 58件 | 93.1% | ¥+14,452 |

### ライブ運用状態（2026年2月17日）

**分析日時**: 2026-02-17T05:56:33（直近48時間）

| 指標 | 値 | 状態 |
|------|-----|------|
| 利用可能残高 | ¥336,277 | 正常 |
| 稼働率 | 98.1% | 達成（目標90%） |
| API応答時間 | 220ms | 正常 |
| サービス状態 | Ready | 正常 |
| MLモデル | ProductionEnsemble (Level 1, 55特徴量) | 正常 |
| 全6戦略 | アクティブ | 正常 |
| TP決済 | 2件（+¥498） | TP正常動作 |
| SL決済 | 0件 | - |

#### 孤児注文問題（既知・手動対応）

| 項目 | 詳細 |
|------|------|
| 検出数 | API上2件（stop_limit）、実際4件（limit 2件はAPI未検出） |
| 原因 | TP約定→ポジション決済→Container再起動の順序でvirtual_positionsが消失し、残SL注文がキャンセルされない |
| 発生頻度 | 数十日〜数ヶ月に1回（TP約定とContainer再起動のタイミングが重なった場合のみ） |
| 実害 | 金銭的損失なし（対応ポジション不在のため発動しない）。注文枠を消費するのみ |
| 対応 | 手動キャンセルで十分（発生頻度が低いため自動化は過剰） |
| API検出問題 | bitbank `/user/spot/active_orders`が信用取引のlimit注文を返さない可能性あり（stop_limitは返す） |

---

## 次のステップ

1. **Phase 64.7**: `src/core/`フォルダ監査・クリーンアップ（10,237行）
2. **Phase 64.8**: `src/data/` `src/features/` `src/backtest/`監査・クリーンアップ（6,728行）

---

**最終更新**: 2026年2月18日 — Phase 64.3完了・virtual_positions property化・単一ソース化

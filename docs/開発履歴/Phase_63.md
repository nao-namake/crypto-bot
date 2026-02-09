# Phase 63: TP/SL設置不具合修正・固定金額TP累積手数料バグ修正

**期間**: 2026年2月10日
**状態**: ✅ Phase 63.2完了
**成果**: TP/SL関連の6つのバグを修正、固定金額TP計算の累積手数料バグ修正

---

## サマリー

| Phase | 内容 | 影響 | 状態 |
|-------|------|------|------|
| 63 Bug 1 | stop_limit注文タイプ検出失敗 | SL配置済みなのに欠損と誤検知 | ✅完了 |
| 63 Bug 2 | ポジション集約時の数量マッチング失敗（3箇所） | TP/SL/ポジション検出失敗 | ✅完了 |
| 63 Bug 3 | asyncio.create_taskでTP/SL検証タスク消失 | Cloud Run再起動時にTP/SL検証が実行されない | ✅完了 |
| 63 Bug 4 | stop_limitタイムアウト常時発火 | 約定済みSLに対して成行フォールバック→二重決済リスク | ✅完了 |
| 63 Bug 5 | virtual_positions消失検知マッチング不一致 | 正常ポジションを孤児と誤判定 | ✅完了 |
| 63 Bug 6 | virtual_positionsデータ不整合 | 決済済みTP/SLエントリが残存→メモリリーク | ✅完了 |
| **63.2** | **固定金額TP計算の累積手数料バグ** | **TP目標500円→平均741円に膨張（+48%超過）** | **✅完了** |

---

## 背景

Phase 62.14でSL注文を`stop_loss`（成行）から`stop_limit`（指値）に変更し、Phase 62.20でTP/SL欠損自動復旧を実装した。
しかし、以下の問題が複合的に発生していた：

| 問題 | 詳細 |
|------|------|
| stop_limit未対応 | 既存のSL検出ロジックが`stop`タイプのみ対応 |
| ポジション集約 | bitbankが複数エントリーを集約し、数量が変わる |
| Cloud Run制約 | コンテナ再起動でasyncioタスクが消失 |
| タイムアウトロジック | SL注文の実際の状態を確認せずにフォールバック |

---

## 修正内容

### Bug 1: stop_limit注文タイプ検出失敗

**ファイル**: `src/trading/execution/executor.py`

**問題**: SL検出ロジックが`stop`タイプのみチェックしていたため、Phase 62.14で導入された`stop_limit`注文が検出されず、SLが配置されていないと誤認識される。

**修正前**:
```python
if order_type == "stop":
    has_sl = True
```

**修正後**:
```python
# SL: stop注文またはstop_limit注文（Phase 63: Bug 1修正）
if order_type in ("stop", "stop_limit"):
    has_sl = True
```

---

### Bug 2: ポジション集約時の数量マッチング失敗（3箇所）

**ファイル**: `src/trading/execution/executor.py`

**問題**: 複数のエントリーがbitbankで集約されると、個別エントリー時の数量と集約後のポジション数量が異なるため、厳密な数量マッチングが失敗する。

#### 修正箇所1: `_check_tp_sl_orders_exist()`

数量チェックを削除し、サイド一致のみでTP/SL注文を検出するように変更。

```python
# Phase 63: Bug 2修正 - 数量マッチング緩和
# ポジション集約時に個別エントリー量と集約量が異なるため、
# サイド一致のみでマッチング（量チェック削除）
if order_amount <= 0:
    continue

# TP: limit注文
if order_type == "limit":
    has_tp = True
```

#### 修正箇所2: `_verify_and_rebuild_tp_sl()` ポジションマッチング

```python
# Phase 63: Bug 2修正 - サイド一致のみでマッチング
# ポジション集約時に個別エントリー量と集約ポジション量が異なるため
if pos_side == expected_pos_side and pos_amount > 0:
    matching_position = pos
    break
```

---

### Bug 3: asyncio.create_task廃止

**ファイル**: `src/trading/execution/executor.py`

**問題**: Phase 62.20で実装されたTP/SL検証は`asyncio.create_task()`で10分後のタスクをスケジュールしていたが、Cloud Runのコンテナ再起動やイベントループ終了によりタスクが消失する。

**修正方針**: fire-and-forget → リスト保存+メインサイクル処理

#### 1. データ構造追加

```python
# Phase 63: TP/SL検証スケジュール管理（asyncio.create_task廃止）
self._pending_verifications: List[Dict[str, Any]] = []
```

#### 2. スケジュール登録（`_schedule_tp_sl_verification`改修）

```python
# Phase 63: Bug 3修正 - asyncio.create_task廃止
# fire-and-forgetではなく、pending_verificationsに保存し
# メインサイクルで期限到来分を処理する方式に変更
self._pending_verifications.append(
    {
        "scheduled_at": datetime.now(timezone.utc),
        "verify_after": datetime.now(timezone.utc) + timedelta(seconds=delay_seconds),
        "entry_order_id": entry_order_id,
        "side": side,
        "amount": amount,
        "entry_price": entry_price,
        "expected_tp_order_id": tp_order_id,
        "expected_sl_order_id": sl_order_id,
        "symbol": symbol,
    }
)
```

#### 3. メインサイクルで期限到来分を処理

```python
async def _process_pending_verifications(self):
    now = datetime.now(timezone.utc)
    due = [v for v in self._pending_verifications if now >= v["verify_after"]]
    self._pending_verifications = [
        v for v in self._pending_verifications if now < v["verify_after"]
    ]

    for v in due:
        await self._verify_and_rebuild_tp_sl(
            entry_order_id=v["entry_order_id"],
            side=v["side"],
            amount=v["amount"],
            entry_price=v["entry_price"],
            expected_tp_order_id=v["expected_tp_order_id"],
            expected_sl_order_id=v["expected_sl_order_id"],
            symbol=v["symbol"],
            delay_seconds=0,  # 既に待機済み
        )
```

**効果**: Cloud Run再起動後も、次のサイクルでpending_verificationsを処理できる（ただしメモリ内保持のため完全な永続化ではない）。

---

### Bug 4: stop_limitタイムアウト常時発火

**ファイル**: `src/trading/execution/stop_manager.py`

**問題**: タイムアウト秒数経過後、SL注文の実際の状態を確認せずに成行フォールバック決済を実行していた。SLが既に約定済みの場合、二重決済（APIエラー50062）が発生するリスクがあった。

さらに、API一時エラー時にexcept句でreturnしておらず、フォールスルーして成行フォールバックが実行される問題もあった。

**修正内容**:
1. タイムアウト到達時に`fetch_order()`でSL注文の実際の状態を確認
2. `closed`/`canceled` → フォールバック不要（return None）
3. `open` → bitbankトリガー待機継続（return None）
4. API一時エラー → 安全側でフォールバックしない（return None）
5. SL注文が確認できない場合のみフォールバック決済を実行

```python
except Exception as e:
    self.logger.warning(f"⚠️ Phase 63: SL注文確認エラー: {e} - フォールバックスキップ")
    return None  # API一時エラー時は安全側（フォールバックしない）
```

**安全性の根拠**:
- SLがまだアクティブ → bitbankトリガーが正しく動作する
- SLが消失 → 次サイクルのpending_verifications（Bug 3修正）で再構築される

---

### Bug 5: virtual_positions消失検知マッチング不一致

**ファイル**: `src/trading/execution/stop_manager.py`

**問題**: virtual_positionsとactual_positionsのマッチングで数量を厳密にチェックしていたため、ポジション集約時にマッチングが失敗し、正常なポジションが「消失」と誤判定される。

**修正前**:
```python
# 数量の厳密マッチング
if aside == vside and abs(aamt - vamt) < tolerance:
    matched = True
```

**修正後**:
```python
# Phase 63: Bug 5修正 - サイド一致かつ実ポジション存在でマッチ
# ポジション集約時に個別数量と集約量が異なるため、
# サイド一致のみでマッチング
if aside == vside and aamt > 0:
    matched = True
    break
```

---

### Bug 6: virtual_positionsデータ不整合

**ファイル**: `src/trading/execution/executor.py`

**問題**: 実ポジションが決済されたのにvirtual_positionsにTP/SLエントリが残存し、メモリリークやTP/SL検証時の干渉を引き起こす。

**修正内容**: `check_stop_conditions()`の先頭で実ポジション情報を取得し、実ポジション0件の場合に孤立したTP/SLエントリをクリーンアップ。

```python
# Phase 63: Bug 6修正 - virtual_positions整合性チェック
if not actual_positions and self.virtual_positions:
    tp_sl_entries = [
        v for v in self.virtual_positions
        if v.get("tp_order_id") or v.get("sl_order_id")
    ]
    if tp_sl_entries:
        self.logger.info(
            f"🧹 Phase 63: virtual_positions整合性クリーンアップ - "
            f"{len(tp_sl_entries)}件の孤立エントリ削除"
        )
        self.virtual_positions = [
            v for v in self.virtual_positions
            if not (v.get("tp_order_id") or v.get("sl_order_id"))
        ]
```

**追加効果**: 取得済みの`actual_positions`を後続の`detect_auto_executed_orders()`で再利用し、API呼び出し回数を削減。

---

## 修正ファイル一覧

| ファイル | Bug | 変更内容 |
|---------|-----|----------|
| `src/trading/execution/executor.py` | 1, 2, 3, 6 | stop_limit検出・マッチング緩和・asyncio廃止・整合性チェック |
| `src/trading/execution/stop_manager.py` | 4, 5 | SL注文状態確認・消失検知マッチング修正 |
| `tests/unit/trading/execution/test_executor.py` | 2 | 数量不一致マッチングテスト追加 |

---

## 呼び出しフロー（修正後）

### TP/SL検証フロー（Bug 3修正後）

```
エントリー成功
    ↓
_schedule_tp_sl_verification()
    ↓
pending_verificationsに登録（10分後）
    ↓
（5分サイクル×2回後）
    ↓
_process_pending_verifications() ← メインサイクルで実行
    ↓
期限到来分を処理
    ↓
_verify_and_rebuild_tp_sl()
    ↓
ポジション存在確認（Bug 2: サイド一致マッチング）
    ↓
TP/SL欠損確認（Bug 1: stop_limit対応）
    ↓
欠損あれば再構築
```

### stop_limitタイムアウトフロー（Bug 4修正後）

```
_check_stop_limit_timeout()
    ↓
elapsed >= timeout_seconds ?
    ↓ Yes
fetch_order(sl_order_id) でSL注文の実際の状態確認
    ↓
closed/canceled → return None（フォールバック不要）
open → return None（bitbankトリガー待機）
APIエラー → return None（安全側）
確認不可 → 成行フォールバック実行
```

### virtual_positions整合性フロー（Bug 5, 6修正後）

```
check_stop_conditions()
    ↓
Bug 6: 実ポジション取得 → 0件 & virtual有 → クリーンアップ
    ↓
detect_auto_executed_orders()（actual_positions再利用）
    ↓
Bug 5: 消失検知 → サイド一致のみでマッチング
```

---

## 検証結果（Phase 63: Bug 1-6）

### 品質チェック

```
$ bash scripts/testing/checks.sh

📊 チェック結果:
  - システム整合性: ✅ PASS (6項目)
  - ML検証: ✅ PASS (55特徴量・3クラス分類)
  - flake8: ✅ PASS
  - isort: ✅ PASS
  - black: ✅ PASS
  - pytest: ✅ PASS (2095 passed, 73.26%カバレッジ)
```

---

## Phase 63.2: 固定金額TP計算の累積手数料バグ修正

### 問題

bitbank APIの`unrealized_fee_amount`は**集約ポジション全体**の累積手数料を返す。新規エントリー時に既存ポジションがあると、その累積値がTP計算に使われ、TPが500円目標 → 平均741円（+48%超過）に膨張していた。

#### GCPログ証拠

| エントリー | fee_data.unrealized_fee_amount | 実際の手数料 | 乖離 |
|-----------|-------------------------------|------------|------|
| 1件目 | 113円 | 0円（Maker） | +113円 |
| 2件目 | 228円 | 0円（Maker） | +228円 |
| 3件目 | 243円 | 0円（Maker） | +243円 |

- Maker 0%のため新規エントリーの手数料は常に0円
- `unrealized_fee_amount`は集約ポジション全体の累積（過去の手数料が蓄積）
- `unrealized_interest_amount`も同様の累積問題（0円→6円→45円と増加）

#### 影響

| 影響 | 説明 |
|------|------|
| TP膨張 | 500円目標が平均741円に（+48%超過） |
| TP到達確率低下 | 高いTPほど到達しにくい |
| SL発動率上昇 | TP到達前にSLヒット |
| 損益悪化 | 勝率低下→全体損益悪化 |

### 修正内容

**方針**: `calculate_fixed_amount_tp`内でfee_dataを無視し、常にfallbackレート（0.0）で個別計算する。

#### 1. `src/strategies/utils/strategy_utils.py`

fee_data参照を削除し、常にfallbackレートで個別計算。

**エントリー手数料**（修正前→修正後）:
```python
# 修正前: fee_dataの累積値を使用
if fee_data:
    entry_fee = fee_data.unrealized_fee_amount  # ★累積値が混入

# 修正後: 常にfallbackレートで個別計算
fallback_rate = config.get("fallback_entry_fee_rate", 0.0)
entry_fee = entry_price * amount * fallback_rate  # Maker 0% → 0円
```

**利息**（修正前→修正後）:
```python
# 修正前: fee_dataの累積値を使用
if fee_data:
    interest = fee_data.unrealized_interest_amount  # ★累積値が混入

# 修正後: 新規エントリー時点では利息≈0円
interest = 0
```

#### 2. `src/trading/execution/executor.py`

ログを「参考値」表記に変更（fee_data取得処理自体はデバッグ用に残す）。

```python
# 修正前
f"📊 Phase 61.7: 手数料データ取得成功 - エントリー手数料={fee_data.unrealized_fee_amount:.0f}円"

# 修正後
f"📊 Phase 63.2: 手数料データ取得（参考値・TP計算には未使用） - 累積手数料={fee_data.unrealized_fee_amount:.0f}円"
```

#### 3. `tests/unit/strategies/utils/test_fixed_amount_tp.py`

| テスト | 変更内容 |
|--------|---------|
| `test_buy_position_basic` | expected_required_profit = 1000+0+0（fee_data=346は無視される検証） |
| `test_with_interest` | fee_data.interest=50が無視されTP=1000円分のみで計算される検証 |
| `test_backtest_vs_live_consistency` | 1%以内→完全一致に変更（fee_dataが無視されるため） |
| **`test_phase_63_2_fee_data_ignored`** | **新規: fee_data有無で結果が同一であることを検証（BUY）** |
| **`test_phase_63_2_sell_fee_data_ignored`** | **新規: fee_data有無で結果が同一であることを検証（SELL）** |

### 修正ファイル一覧

| ファイル | 変更内容 |
|---------|----------|
| `src/strategies/utils/strategy_utils.py` | fee_data参照を削除、常にfallbackレート使用 |
| `src/trading/execution/executor.py` | ログを「参考値」表記に変更 |
| `tests/unit/strategies/utils/test_fixed_amount_tp.py` | テスト更新・Phase 63.2テスト2件追加 |

### 検証結果

```
$ python3 -m pytest tests/unit/strategies/utils/test_fixed_amount_tp.py -v
24 passed in 0.79s

$ bash scripts/testing/checks.sh
📊 チェック結果:
  - システム整合性: ✅ PASS (6項目)
  - ML検証: ✅ PASS (55特徴量・3クラス分類)
  - flake8: ✅ PASS
  - isort: ✅ PASS
  - black: ✅ PASS
  - pytest: ✅ PASS (2097 passed, 73.25%カバレッジ)
```

### 期待効果

| 項目 | 修正前 | 修正後 |
|------|--------|--------|
| 必要含み益 | 500 + 累積手数料（113〜270円） + 累積利息 | 500円（固定） |
| TP距離 | 膨張（+48%超過） | 正確（500円/数量） |
| TP到達確率 | 低下 | 正常化 |
| バックテスト/ライブ一致性 | 乖離あり | 完全一致 |

---

**最終更新**: 2026年2月10日 - **Phase 63.2完了**（固定金額TP累積手数料バグ修正）

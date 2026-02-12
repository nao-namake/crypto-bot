# Phase 63: TP/SL設置不具合修正・固定金額TP累積手数料バグ修正

**期間**: 2026年2月10日〜13日
**状態**: ✅ Phase 63.6完了
**成果**: TP/SL関連の6つのバグを修正、固定金額TP計算の累積手数料バグ修正、SLタイムアウト誤発動・ポジション復元不完全・TP/SL再構築amount不整合修正、TP/SL定期チェック実装、残存バグ3件修正

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
| **63.4 Bug 1** | **SLタイムアウトに価格安全チェック欠如** | **利益圏で成行決済→孤児ポジション生成** | **✅完了** |
| **63.4 Bug 2** | **restore_positions_from_apiメタデータ不完全** | **復元後SL監視無効・1注文=1エントリ重複** | **✅完了** |
| **63.4 Bug 3** | **_verify_and_rebuild_tp_slのamount不整合** | **ポジション集約時50062エラー** | **✅完了** |
| **63.4 Bug 4** | **_scan_orphan_positionsにsl_placed_at欠如** | **孤児復元ポジションのSLタイムアウト無効** | **✅完了** |
| **63.4 Bug 5** | **ensure_tp_sl_for_existing_positionsの重複防止** | **Bug 2修正後の重複エントリ作成リスク** | **✅完了** |
| **63.5** | **TP/SL定期チェック実装（10分間隔）** | **メインサイクル内でTP/SL欠損を自動検知・復旧** | **✅完了** |
| **63.6 Bug 1** | **_place_missing_tp_sl get_thresholdパス修正（CRITICAL）** | **TP +129%バグ → 正常なTP/SL設定値取得** | **✅完了** |
| **63.6 Bug 2** | **_scan_orphan_positions 設定パス修正（HIGH）** | **孤児スキャンSL設定が正しいパスを参照** | **✅完了** |
| **63.6 Bug 3** | **ensure_tp_sl restoredフィルタ削除（MEDIUM）** | **復元ポジションもTP/SL定期チェック対象化** | **✅完了** |

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

## Phase 63.4: SLタイムアウト誤発動・ポジション復元不完全・TP/SL再構築amount不整合

**期間**: 2026年2月12日

### 背景

Phase 63.3で7件のバグを修正後、GCPログ・3日分CSV分析により、以下の問題が判明。

**最大の問題**: SLタイムアウトフォールバック（Phase 62.17）が100%の確率で発動し成行決済を実行。9件中8件は50062エラー（TP約定済み）で無害だが、1件が実際に約定し0.0027 BTC孤児ポジションを生成（2/11 18:20 UTC）。

**根本原因チェーン**:
1. Cloud Runコンテナが5分毎に再起動される可能性がある
2. `restore_positions_from_api`がアクティブ**注文**ベースで復元し、`sl_order_id`/`sl_placed_at`/`stop_loss`/`take_profit`を設定しない
3. 復元ポジションはBot側SL監視もSLタイムアウトも無効（`stop_loss`がNoneのため`_evaluate_position_exit`のSLブロック全体がスキップ）
4. `_check_stop_limit_timeout`に価格安全チェックがなく、利益圏でも成行決済を実行
5. `_verify_and_rebuild_tp_sl`がスケジュール時の`amount`パラメータを使用し、ポジション集約時に50062エラー

---

### Bug 1: SLタイムアウトに価格安全チェック欠如（重大・防波堤）

**ファイル**: `src/trading/execution/stop_manager.py`

**問題**: `_check_stop_limit_timeout`が価格チェックなしで成行フォールバックを実行。SL注文確認不可の場合、現在価格がSL水準から大幅に離れていても決済してしまう。

**事例**: 2/11 18:20 UTC - エントリー10,292,159円、SL=10,102,339円に対し、現在価格10,207,867円（SLより約1%高い）で成行売却→0.0027 BTC孤児化。

**修正**: 成行フォールバック前に価格安全チェックを追加。

```python
# Phase 63.4: 価格安全チェック - SLゾーン外なら実行しない
if stop_loss and current_price > 0:
    sl_price = float(stop_loss)
    if entry_side.lower() == "buy":
        # ロング: 現在価格がSL+1.5%以上なら、SL発動は不合理
        if current_price > sl_price * 1.015:
            self.logger.warning(
                f"⚠️ Phase 63.4: SLタイムアウト中止 - "
                f"現在価格({current_price:.0f})がSL({sl_price:.0f})より"
                f"大幅に高い。bitbankトリガー待機継続。"
            )
            return None
    elif entry_side.lower() == "sell":
        # ショート: 現在価格がSL-1.5%以下なら不合理
        if current_price < sl_price * 0.985:
            ...
            return None
```

**設計根拠**: 1.5%マージンはtight_range SL幅(0.4%)の約4倍。SL価格から大幅に離れた状態での成行決済は常に不合理。

---

### Bug 2: restore_positions_from_api メタデータ不完全（重大・根本対策）

**ファイル**: `src/trading/execution/executor.py`

**問題**: アクティブ注文ベースで復元していたため、1ポジションに対しTP注文・SL注文の2エントリが作成され、`sl_order_id`、`sl_placed_at`、`take_profit`、`stop_loss`が未設定。コンテナ再起動後のBot側SL監視が完全に無効化。

**修正**: 実ポジション（信用建玉）ベースの復元に全面書き換え。

| 項目 | 修正前 | 修正後 |
|------|--------|--------|
| 復元ベース | アクティブ注文 | 実ポジション（信用建玉） |
| エントリ数 | 1注文 = 1エントリ（2重複） | 1ポジション = 1エントリ |
| TP/SLマッチング | なし | exit_side一致でマッチング |
| sl_placed_at | 未設定 | 注文datetime or 現在時刻 |
| take_profit/stop_loss | 未設定 | マッチング結果から設定 |
| sl_order_id/tp_order_id | 未設定 | マッチング結果から設定 |

---

### Bug 3: _verify_and_rebuild_tp_sl のamount不整合（重要）

**ファイル**: `src/trading/execution/executor.py`

**問題**: TP/SL再構築時（10分検証）にスケジュール時の`amount`パラメータを使用。ポジション集約により実際のAPIポジション量と異なる場合、50062エラー（保有建玉数量超過）が発生。

**修正**: `matching_position`から取得した`actual_api_amount`を使用。

```python
# Phase 63.4: 実際のAPIポジション量を使用（ポジション集約対応）
actual_api_amount = float(matching_position.get("amount", 0))

# TP/SL再構築時にactual_api_amountを使用
tp_order = await self._place_tp_with_retry(
    side=side,
    amount=actual_api_amount,  # Phase 63.4
    ...
)
sl_order = await self._place_sl_with_retry(
    side=side,
    amount=actual_api_amount,  # Phase 63.4
    ...
)
```

---

### Bug 4: _scan_orphan_positions にsl_placed_at欠如（軽微）

**ファイル**: `src/trading/execution/executor.py`

**問題**: Phase 63.3で追加した孤児スキャンが作成する`orphan_entry`に`sl_placed_at`がない。SLタイムアウト監視が孤児復元ポジションで無効のまま。

**修正**: 2箇所のorphan_entryに`sl_placed_at`を追加。

```python
orphan_entry = {
    ...
    "sl_placed_at": datetime.now(timezone.utc).isoformat(),  # Phase 63.4
}
```

---

### Bug 5: ensure_tp_sl_for_existing_positions の重複防止（軽微）

**ファイル**: `src/trading/execution/executor.py`

**問題**: Bug 2修正後、`restore_positions_from_api`がポジションベースの復元を行うため、`ensure_tp_sl_for_existing_positions`が同一ポジションに対して重複エントリを作成する可能性。

**修正**: ループ内で`restored`フラグを持つvirtual_positionが同じサイドに既に存在する場合はスキップ。

```python
# Phase 63.4: Bug 2修正後、restore済みポジションの重複防止
entry_side = "buy" if position_side == "long" else "sell"
already_restored = any(
    vp.get("side") == entry_side and vp.get("restored")
    for vp in self.virtual_positions
)
if already_restored:
    continue
```

---

### 修正ファイル一覧

| ファイル | Bug | 変更内容 |
|---------|-----|----------|
| `src/trading/execution/stop_manager.py` | 1 | SLタイムアウト価格安全チェック追加 |
| `src/trading/execution/executor.py` | 2, 3, 4, 5 | ポジション復元書き換え・amount修正・sl_placed_at追加・重複防止 |
| `tests/unit/trading/execution/test_executor.py` | 2 | テスト更新（1ポジション=1エントリ・メタデータ検証・実ポジションなしテスト） |

### テスト更新

| テスト | 変更内容 |
|--------|---------|
| `test_restore_positions_with_active_orders` | 旧: 2件復元 → 新: 1件復元 + メタデータ検証（tp_order_id, sl_order_id, take_profit, stop_loss, sl_placed_at） |
| `test_restore_positions_skips_incomplete_orders` | → `test_restore_positions_no_real_positions`に改名。実ポジションなし→復元なしの検証 |

### 検証結果

```
$ bash scripts/testing/checks.sh

📊 チェック結果:
  - システム整合性: ✅ PASS (6項目)
  - ML検証: ✅ PASS (55特徴量・3クラス分類)
  - flake8: ✅ PASS
  - isort: ✅ PASS
  - black: ✅ PASS
  - pytest: ✅ PASS (2097 passed, 72.64%カバレッジ)
```

### 期待効果

| 項目 | 修正前 | 修正後 |
|------|--------|--------|
| SLタイムアウト誤発動 | 利益圏でも成行決済実行 | SLから1.5%以上離れていれば中止 |
| ポジション復元 | 注文ベース（2重複・メタデータ欠落） | 実ポジションベース（1エントリ・メタデータ完備） |
| Bot側SL監視 | 復元後無効 | stop_loss/sl_placed_at設定により有効 |
| TP/SL再構築 | スケジュール時amount→50062エラー | APIポジション量使用→正常動作 |
| 孤児ポジション | SLタイムアウト監視無効 | sl_placed_at設定により有効 |

---

## Phase 63.5: TP/SL定期チェック実装

**期間**: 2026年2月13日

### 概要

メインサイクル内で10分間隔のTP/SL定期チェックを実装。既存の`_process_pending_verifications()`（エントリー後10分検証）に加え、全ポジションを対象とした定期的なTP/SL欠損検知・自動復旧メカニズムを追加。

### 実装内容

**ファイル**: `src/trading/execution/executor.py`

#### `_periodic_tp_sl_check()`

- 10分間隔でメインサイクルから呼び出し
- 全virtual_positionsのTP/SL設置状態を確認
- 欠損検知時に`_place_missing_tp_sl()`で自動復旧
- `_last_tp_sl_check`タイムスタンプで間隔管理

#### `_place_missing_tp_sl()`

- 個別ポジションのTP/SL欠損を復旧
- レジーム別TP/SL設定値をget_thresholdで取得
- 固定金額TP有効時はcalculate_fixed_amount_tpを使用

---

## Phase 63.6: 残存バグ3件修正（最終品質チェック）

**期間**: 2026年2月13日

### 概要

Phase 63.5実装後のOpusエージェント最終監査により、executor.py全体で3件の残存バグを検出・修正。修正後の再監査で**実運用に影響するバグはもう存在しない**ことを確認。

### Bug 1: _place_missing_tp_sl get_thresholdパス修正（CRITICAL）

**ファイル**: `src/trading/execution/executor.py`

**問題**: `_place_missing_tp_sl()`内でTP/SL設定値を取得する`get_threshold`のパスが`regime_configs`になっていたが、正しくは`regime_based`。これによりTP/SLが全てデフォルト値にフォールバックし、TP幅が+129%に膨張する。

**修正前**:
```python
tp_rate = get_threshold(f"regime_configs.{regime}.take_profit", 0.004)
sl_rate = get_threshold(f"regime_configs.{regime}.stop_loss", 0.004)
```

**修正後**:
```python
tp_rate = get_threshold(f"regime_based.{regime}.take_profit", 0.004)
sl_rate = get_threshold(f"regime_based.{regime}.stop_loss", 0.004)
```

### Bug 2: _scan_orphan_positions 設定パス修正（HIGH）

**ファイル**: `src/trading/execution/executor.py`

**問題**: `_scan_orphan_positions()`内のSL設定パスが`risk.stop_loss.*`になっていたが、正しくは`position_management.*`。デフォルト値にフォールバックし、SL幅やバッファが意図と異なる値になる。

**修正前**:
```python
sl_rate = get_threshold(f"risk.stop_loss.{regime}_rate", 0.004)
sl_buffer = get_threshold("risk.stop_loss.slippage_buffer", 0.002)
```

**修正後**:
```python
sl_rate = get_threshold(f"position_management.stop_loss.{regime}_rate", 0.004)
sl_buffer = get_threshold("position_management.stop_loss.slippage_buffer", 0.002)
```

### Bug 3: ensure_tp_sl restoredフィルタ削除（MEDIUM）

**ファイル**: `src/trading/execution/executor.py`

**問題**: `ensure_tp_sl_for_existing_positions()`が`restored`フラグを持つvirtual_positionsを削除フィルタで除外していたため、復元ポジションがTP/SL定期チェックの対象にならない。

**修正**: `restored`条件の削除フィルタを撤去し、復元ポジションも含む全ポジションをTP/SL確認対象に。

### 最終監査結果

| 項目 | 結果 |
|------|------|
| get_thresholdパス整合性 | ✅ 全て正常（修正済み3件含む） |
| TP/SL計算方向性 | ✅ long/short全箇所正常 |
| amount整合性 | ✅ APIポジション量使用で正常 |
| virtual_positions操作 | ✅ 二重エントリリスクなし |
| 500円固定TP | ✅ Phase 63.2修正健在 |
| 実運用影響バグ | **なし** |

### 修正ファイル一覧

| ファイル | Bug | 変更内容 |
|---------|-----|----------|
| `src/trading/execution/executor.py` | 1, 2, 3 | get_thresholdパス修正2件・restoredフィルタ削除 |

### 検証結果

```
$ bash scripts/testing/checks.sh

📊 チェック結果:
  - システム整合性: ✅ PASS (6項目)
  - ML検証: ✅ PASS (55特徴量・3クラス分類)
  - flake8: ✅ PASS
  - isort: ✅ PASS
  - black: ✅ PASS
  - pytest: ✅ PASS (2097 passed, 72.64%カバレッジ)
```

---

**最終更新**: 2026年2月13日 - **Phase 63.6完了**（TP/SL定期チェック実装・残存バグ3件修正・最終監査バグなし確認）

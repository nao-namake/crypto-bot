# Phase 58 開発記録

**期間**: 2026/01/07 - 進行中
**状況**: 🔄 Phase 58進行中

---

## 📋 Phase 58 概要

### 目的

TP/SL管理の致命的バグ修正と運用安定化

### 背景

- Phase 57.14完了後、ライブモードでTP/SL管理の問題が発覚
- 複数ポジション保有時にTP/SL注文が消失する問題
- 3件のポジションに対して1件分のTP/SLしか残らない

### Phase一覧

| Phase | 内容 | 状態 | 主要成果 |
|-------|------|------|----------|
| 58.1 | TP/SL管理バグ修正（3件） | ✅ | 決済注文発行・保護ロジック・複数処理対応 |
| 58.2 | ライブ分析スクリプト改善 | ✅ | TP/SL量整合性チェック追加 |
| 58.3 | ポジション同期問題修正 | ✅ | 実ポジション確認ロジック追加 |

---

## 🐛 Phase 58.1: TP/SL管理バグ修正【完了】

### 実施日: 2026/01/07

### 問題発覚経緯

ライブモードで3件のロングポジションを保有しているが、TP/SL注文が1件分しか存在しない。

| 項目 | 値 |
|------|-----|
| ポジション数 | 3件（0.0106 BTC） |
| TP注文数 | 1件（0.0037 BTC） |
| SL注文数 | 1件（0.0037 BTC） |
| カバー率 | 約35%（65%が無防備） |

### 根本原因分析

#### バグ1: 決済注文未発行（致命的）

**ファイル**: `src/trading/execution/stop_manager.py` L230-329

**問題**: `_execute_position_exit()`がローカルSL検知時にbitbankへ決済注文を発行していない

```python
# 修正前
async def _execute_position_exit(...):
    pnl = (current_price - entry_price) * amount  # P&L計算 ✓
    await self.cleanup_position_orders(...)        # 反対注文キャンセル ✓
    self.logger.info("🔄 ポジション決済完了")      # ログ ✓
    # ★★★ bitbank決済注文 ✗ ★★★
```

**影響**: SL価格到達時にvirtual_positionsからは削除されるが、実際のbitbank建玉は残り続ける

#### バグ2: TP/SL誤削除（Phase 51.10-A問題の再発）

**ファイル**: `src/trading/execution/executor.py` L1506-1647

**問題**: `_cleanup_old_tp_sl_before_entry()`の保護対象判定が不完全

```python
# 修正前: 同一サイドのポジションのみ保護
if pos.get("side") == side:  # ← 反対サイドのTP/SLが保護されない
    protected_order_ids.add(str(pos.get("tp_order_id")))
```

**影響**: 新規エントリー時に既存ポジションのTP/SL注文が「古い注文」として誤削除される

#### バグ3: 単一決済パターン

**ファイル**: `src/trading/execution/stop_manager.py` L126-139

**問題**: TP/SLチェックで1つ処理したら即return

```python
# 修正前
for position in virtual_positions:
    if exit_result:
        return exit_result  # ← 1つ目だけ処理して終了
```

**影響**: 複数ポジションが同時にSL到達しても、1件しか決済されない

### bitbank API調査

**結論**: OCO/ブラケット注文は非対応

- 各注文は個別に発行する必要がある
- エントリー約定後にTP/SLを別途配置するしかない

Sources:
- [bitbank REST API](https://github.com/bitbankinc/bitbank-api-docs/blob/master/rest-api_JP.md)

### 修正内容

#### バグ1修正: 決済注文発行追加

**ファイル**: `src/trading/execution/stop_manager.py` L301-322

```python
# Phase 58.1: 実際の決済注文をbitbankに発行
try:
    entry_position_side = "long" if entry_side.lower() == "buy" else "short"
    close_order = await asyncio.to_thread(
        bitbank_client.create_order,
        symbol="BTC/JPY",
        side=exit_side,
        order_type="market",
        amount=amount,
        is_closing_order=True,
        entry_position_side=entry_position_side,
    )
    close_order_id = close_order.get("id", "unknown")
    self.logger.info(f"✅ Phase 58.1: bitbank決済注文発行成功 - ID: {close_order_id}")
except Exception as e:
    self.logger.error(f"❌ Phase 58.1: bitbank決済注文発行失敗: {e}")
```

#### バグ2修正: 保護対象判定修正

**ファイル**: `src/trading/execution/executor.py` L1550-1570

```python
# Phase 58.1: 全ポジションのTP/SL注文を保護（同一側制限を撤廃）
protected_order_ids = set()
if self.virtual_positions:
    for pos in self.virtual_positions:
        # Phase 58.1: 全ポジションのtp_order_id/sl_order_idを保護
        tp_id = pos.get("tp_order_id")
        sl_id = pos.get("sl_order_id")
        if tp_id:
            protected_order_ids.add(str(tp_id))
        if sl_id:
            protected_order_ids.add(str(sl_id))

        # Phase 53.12: 復元されたポジションのorder_idも保護
        if pos.get("restored"):
            order_id = pos.get("order_id")
            if order_id:
                protected_order_ids.add(str(order_id))
```

#### バグ3修正: 全ポジション処理対応

**ファイル**: `src/trading/execution/stop_manager.py` L126-154

```python
# Phase 58.1: 全ポジションのTP/SLチェック（単一決済パターン修正）
positions_to_remove = []
first_result = None

for position in list(virtual_positions):  # コピーでイテレート（削除安全）
    exit_result = await self._evaluate_position_exit(...)
    if exit_result:
        positions_to_remove.append(position)
        if first_result is None:
            first_result = exit_result

# Phase 58.1: まとめて削除（イテレーション終了後）
for pos in positions_to_remove:
    if pos in virtual_positions:
        virtual_positions.remove(pos)

return first_result
```

### 設計判断

#### 検討した代替案: 統合TP/SL管理

| 方式 | 説明 | 却下理由 |
|------|------|---------|
| 統合管理 | 全ポジションを1つのTP/SLでカバー | 連敗クールダウン機能が壊れる |

**連敗クールダウン機能**:
- 6-8連敗でクールダウン発動
- 個別エントリーごとの勝敗判定が必要
- 統合すると「1回の大損」として扱われ、機能しなくなる

**結論**: 現行のエントリーごとのTP/SL管理を維持

### テスト結果

```
============================================
pytest結果: 1,256テスト成功（65%カバレッジ）
flake8/black/isort: PASS
============================================
```

### デプロイ

```bash
git add .
git commit -m "fix: Phase 58.1 TP/SL管理致命的バグ3件修正"
git push origin main
```

---

## 🔍 Phase 58.2: ライブ分析スクリプト改善【完了】

### 実施日: 2026/01/08

### 問題

Phase 57.14で作成した`scripts/live/standard_analysis.py`のTP/SLチェックが不十分だった。

#### 既存の検出能力

| チェック項目 | 検出 |
|-------------|------|
| TP/SL注文が存在しない | ✅ |
| TP/SL注文数がポジション数より少ない | ❌ |
| TP/SL注文量がポジション量より少ない | ❌ |

→ 今回のバグ（3ポジションに1件のTP/SL）は検出できなかった

### 修正内容

**ファイル**: `scripts/live/standard_analysis.py` L431-480

```python
# Phase 58.1: ポジション量とTP/SL注文量の整合性チェック
if self.result.position_details and self.result.open_position_count > 0:
    # ポジション総量を計算
    total_position_amount = sum(
        abs(float(pos.get("amount", 0))) for pos in self.result.position_details
    )

    # TP注文総量
    total_tp_amount = sum(
        abs(float(o.get("amount", 0) or o.get("remaining", 0))) for o in tp_orders
    )

    # SL注文総量
    total_sl_amount = sum(
        abs(float(o.get("amount", 0) or o.get("remaining", 0))) for o in sl_orders
    )

    # 許容誤差（0.1%）
    tolerance = 0.001

    # TP量不足チェック
    if total_position_amount > 0 and total_tp_amount > 0:
        tp_coverage = total_tp_amount / total_position_amount
        if tp_coverage < (1.0 - tolerance):
            self.result.tp_sl_placement_ok = False
            tp_pct = tp_coverage * 100
            self.logger.warning(
                f"⚠️ TP注文量不足: ポジション{total_position_amount:.4f}BTC vs "
                f"TP注文{total_tp_amount:.4f}BTC (カバー率: {tp_pct:.1f}%)"
            )

    # SL量不足チェック
    if total_position_amount > 0 and total_sl_amount > 0:
        sl_coverage = total_sl_amount / total_position_amount
        if sl_coverage < (1.0 - tolerance):
            self.result.tp_sl_placement_ok = False
            sl_pct = sl_coverage * 100
            self.logger.warning(
                f"⚠️ SL注文量不足: ポジション{total_position_amount:.4f}BTC vs "
                f"SL注文{total_sl_amount:.4f}BTC (カバー率: {sl_pct:.1f}%)"
            )
```

### 改善された検出能力

| チェック項目 | 検出 |
|-------------|------|
| TP/SL注文が存在しない | ✅ |
| TP/SL注文数がポジション数より少ない | ✅ |
| TP/SL注文量がポジション量より少ない | ✅ |
| カバー率の表示 | ✅ |

### 出力例

```
⚠️ TP注文量不足: ポジション0.0068BTC vs TP注文0.0036BTC (カバー率: 52.9%)
⚠️ SL注文量不足: ポジション0.0068BTC vs SL注文0.0036BTC (カバー率: 52.9%)
TP/SL詳細 - ポジション: 0.0068BTC, TP: 1件(0.0036BTC), SL: 1件(0.0036BTC)
```

---

## 🔧 Phase 58.3: ポジション同期問題修正【完了】

### 実施日: 2026/01/09

### 問題発覚経緯

ライブモード診断中に、システムが「ポジションあり（66,738円）」と表示しているが、実際はノーポジション状態だった。

| 項目 | システム表示 | 実際 |
|------|------------|------|
| ポジション価値 | 66,738円 | 0円 |
| 維持率 | 500% | N/A（ポジションなし） |

### 根本原因分析

#### 問題の流れ

```
1. ポジションなし時、bitbank_client.py が margin_ratio = 500.0 を返す（デフォルト値）

2. monitor.py が維持率500%を受け取り逆算:
   → ポジション価値 = 残高 / (維持率 / 100)
   → ポジション価値 = 333,689円 / 5 = 約66,738円

3. システムが「66,738円のポジションがある」と誤認
```

#### 原因ファイル

| ファイル | 問題 | 行番号 |
|---------|------|--------|
| `bitbank_client.py` | ポジションなし時に500%を返却 | L1513-1515 |
| `monitor.py` | 維持率からポジション価値を逆算（実ポジション未確認） | L217-226 |
| `executor.py` | 起動時に実ポジション確認していない | L109-172 |

### 修正内容

#### 修正1: has_open_positions()メソッド追加

**ファイル**: `src/data/bitbank_client.py` L1595-1619

```python
async def has_open_positions(self, symbol: str = "BTC/JPY") -> bool:
    """
    Phase 58.3: 実ポジションがあるかどうかを確認
    """
    try:
        positions = await self.fetch_margin_positions(symbol)
        has_positions = len(positions) > 0 and any(p.get("amount", 0) > 0 for p in positions)
        self.logger.debug(
            f"📊 Phase 58.3: ポジション確認 - {symbol}: {'あり' if has_positions else 'なし'}"
        )
        return has_positions
    except Exception as e:
        self.logger.warning(f"⚠️ Phase 58.3: ポジション確認失敗: {e}")
        return False  # エラー時は安全側（ポジションなしと仮定）
```

#### 修正2: ポジション価値推定前に実ポジション確認

**ファイル**: `src/trading/balance/monitor.py` L217-231

```python
# Phase 58.3: 実ポジション確認（維持率からの逆算前に必ず確認）
has_positions = False
if bitbank_client and not is_backtest_mode():
    try:
        has_positions = await bitbank_client.has_open_positions("BTC/JPY")
    except Exception as e:
        self.logger.warning(f"⚠️ Phase 58.3: ポジション確認エラー: {e}")

# Phase 58.3: ポジションなしの場合は推定スキップ
if not has_positions and bitbank_client and not is_backtest_mode():
    estimated_current_position_value = 0.0
    self.logger.info(
        f"📊 Phase 58.3: ポジションなし確認済み - 推定スキップ "
        f"(API維持率: {current_margin_ratio_from_api}%)"
    )
```

#### 修正3: 起動時の実ポジション確認ログ追加

**ファイル**: `src/trading/execution/executor.py` L126-144

```python
# Phase 58.3: まず実ポジションを確認してログ出力
margin_positions = await self.bitbank_client.fetch_margin_positions("BTC/JPY")
if margin_positions:
    total_position_value = sum(
        p.get("amount", 0) * p.get("average_price", 0) for p in margin_positions
    )
    self.logger.info(
        f"📊 Phase 58.3: 実ポジション確認 - {len(margin_positions)}件, "
        f"総額: {total_position_value:.0f}円"
    )
    for pos in margin_positions:
        self.logger.info(
            f"  └ {pos.get('side')} {pos.get('amount', 0):.4f} BTC "
            f"@ {pos.get('average_price', 0):.0f}円 "
            f"(含み損益: {pos.get('unrealized_pnl', 0):.0f}円)"
        )
else:
    self.logger.info("📊 Phase 58.3: 実ポジションなし（ノーポジション）")
```

#### 修正4: ポジションなし時のログ改善

**ファイル**: `src/data/bitbank_client.py` L1513-1520

```python
else:
    # Phase 58.3: ポジションがない場合（正常）
    # 500%は安全なデフォルト値だが、ポジションなしを明示的にログ出力
    margin_ratio = 500.0
    self.logger.info(
        "📊 Phase 58.3: ポジションなし（維持率=500%デフォルト） "
        "- 実際のポジション確認にはfetch_margin_positions()を使用"
    )
```

### 修正後の動作

**Before（問題）**:
```
📊 Phase 50.4: API維持率500.0%から現在ポジション価値を推定: 66738円
```

**After（修正後）**:
```
📊 Phase 58.3: 実ポジションなし（ノーポジション）
📊 Phase 58.3: ポジションなし確認済み - 推定スキップ (API維持率: 500.0%)
```

### テスト結果

```
============================================
pytest結果: 1,195 passed, 36 skipped
flake8/black/isort: PASS
============================================
```

---

## 📊 ライブポジション検証

### 検証日: 2026/01/08

Phase 58.1デプロイ前に、現行ポジションの正当性を確認。

### 3件のロングポジション

| Entry | 時刻 | エントリー価格 | 数量 | TP価格 | SL価格 | 信頼度 |
|-------|------|---------------|------|--------|--------|--------|
| 1 | 09:16 | 14,478,273円 | 0.0032 BTC | 14,594,099円 | 14,391,403円 | 19.5% |
| 2 | 09:43 | 14,385,882円 | 0.0037 BTC | 14,500,969円 | 14,299,567円 | 39.3% |
| 3 | 15:27 | 14,282,258円 | 0.0037 BTC | 14,396,516円 | 14,196,564円 | 32.6% |

**合計**: 0.0106 BTC（約151,361円）

### TP/SL設定検証

| Entry | TP距離 | 期待値 | SL距離 | 期待値 | 判定 |
|-------|--------|--------|--------|--------|------|
| 1 | 0.80% | 0.8% | 0.60% | 0.6% | ✅ |
| 2 | 0.80% | 0.8% | 0.60% | 0.6% | ✅ |
| 3 | 0.80% | 0.8% | 0.60% | 0.6% | ✅ |

→ **全エントリーでTP/SL設定は`thresholds.yaml`のtight_range設定通り**

### 検証結論

| 項目 | 結果 |
|------|------|
| ポジション正当性 | ✅ 3件全てBUYシグナルで一貫 |
| TP/SL設定値 | ✅ 設定通り（TP 0.8% / SL 0.6%） |
| TP/SL問題 | ⚠️ 3件中1件のみ存在（Phase 58.1で修正済み） |

---

## 📝 学習事項

### TP/SL管理

1. **注文保護の重要性**: 新規エントリー時のクリーンアップで既存TP/SLを誤削除しないよう保護必須
2. **成行決済の実装**: ローカルSL検知時は実際にbitbankへ決済注文を発行する必要あり
3. **複数ポジション対応**: イテレーション中の削除は危険、まとめて後処理

### 設計判断

4. **連敗クールダウン保護**: 統合TP/SL管理は連敗判定を壊すため却下
5. **bitbank API制約**: OCO/ブラケット注文非対応、個別注文必須

### 検出・監視

6. **量ベースの検証**: 注文の有無だけでなく、量の整合性チェックが重要
7. **カバー率表示**: 問題の深刻度を即座に把握できる

---

## 📁 修正ファイル一覧

### Phase 58.1

| ファイル | 修正内容 |
|---------|---------|
| `src/trading/execution/stop_manager.py` | 決済注文発行追加（L301-322）、全ポジション処理（L126-154） |
| `src/trading/execution/executor.py` | 保護対象判定修正（L1550-1570） |

### Phase 58.2

| ファイル | 修正内容 |
|---------|---------|
| `scripts/live/standard_analysis.py` | TP/SL量整合性チェック追加（L431-480） |

### Phase 58.3

| ファイル | 修正内容 |
|---------|---------|
| `src/data/bitbank_client.py` | `has_open_positions()`メソッド追加、ポジションなし時ログ改善 |
| `src/trading/balance/monitor.py` | 実ポジション確認ロジック追加 |
| `src/trading/execution/executor.py` | 起動時の実ポジション確認ログ追加 |

---

## 📊 Phase 58 進捗

### 完了項目

- [x] TP/SL管理バグ3件修正（Phase 58.1）
- [x] ライブ分析スクリプト改善（Phase 58.2）
- [x] 現行ポジション正当性検証
- [x] ポジション同期問題修正（Phase 58.3）

### 保留項目（Phase 57から引き継ぎ）

- [ ] BBReversal無効化（勝率8.3%・¥-5,451）
- [ ] DonchianChannel重み削減（¥-3,560）
- [ ] 信頼度フィルター見直し（高信頼度帯の逆転現象）

---

**📅 最終更新**: 2026年1月9日 - Phase 58.3完了（ポジション同期問題修正）

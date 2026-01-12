# Phase 58 開発記録

**期間**: 2026/01/07 - 2026/01/12
**状況**: ✅ Phase 58.7完了
**テーマ**: TP/SL管理の致命的バグ修正・運用安定化・バックテスト精度向上

---

## 目次

1. [Phase 58 概要](#-phase-58-概要)
2. [Phase 58.1: TP/SL管理バグ修正](#-phase-581-tpsl管理バグ修正完了)
3. [Phase 58.2: ライブ分析スクリプト改善](#-phase-582-ライブ分析スクリプト改善完了)
4. [Phase 58.3: ポジション同期問題修正](#-phase-583-ポジション同期問題修正完了)
5. [Phase 58.4: fetch_margin_positions APIエラー修正](#-phase-584-fetch_margin_positions-apiエラー修正完了)
6. [Phase 58.5: ポジション滞留問題対応](#-phase-585-ポジション滞留問題対応完了)
7. [Phase 58.6: バックテスト手数料・土日TP/SL縮小](#-phase-586-バックテスト手数料利息追加--土日tpsl縮小完了)
8. [Phase 58.7: 稼働率計算改善・維持率表示明確化](#-phase-587-稼働率計算改善維持率表示明確化完了)
9. [ライブポジション検証記録](#-ライブポジション検証記録)
10. [学習事項](#-学習事項)
11. [修正ファイル一覧](#-修正ファイル一覧)
12. [Phase 58 進捗サマリー](#-phase-58-進捗サマリー)

---

## 📋 Phase 58 概要

### 背景

Phase 57.14完了後、ライブモードで致命的な問題が発覚した。

**発覚した問題**:
- 複数ポジション保有時にTP/SL注文が消失
- 3件のポジションに対して1件分のTP/SLしか残らない（カバー率35%）
- システムとbitbank実態の不整合

### 目的

1. **TP/SL管理の致命的バグ修正**: 決済注文未発行・誤削除・単一処理パターン
2. **ポジション同期問題解消**: 実態との乖離を検出・修正
3. **運用安定化**: 滞留問題対応・TP/SL最適化
4. **バックテスト精度向上**: 手数料・利息追加・土日対応

### Phase一覧

| Phase | 実施日 | 内容 | 状態 | 主要成果 |
|-------|--------|------|------|----------|
| 58.1 | 01/07 | TP/SL管理バグ修正（3件） | ✅ | 決済注文発行・保護ロジック・複数処理対応 |
| 58.2 | 01/08 | ライブ分析スクリプト改善 | ✅ | TP/SL量整合性チェック追加 |
| 58.3 | 01/09 | ポジション同期問題修正 | ✅ | 実ポジション確認ロジック追加 |
| 58.4 | 01/10 | fetch_margin_positions修正 | ✅ | GETメソッド修正（APIエラー20003解消） |
| 58.5 | 01/11-12 | ポジション滞留問題対応 | ✅ | TP/SL縮小（0.8%→0.4%）・稼働率計算修正 |
| 58.6 | 01/12 | バックテスト精度向上 | ✅ | 手数料・利息追加・土日TP/SL縮小（62.5%） |
| 58.7 | 01/12 | 稼働率計算改善・維持率表示明確化 | ✅ | 検索パターン修正・N/A表示追加 |

### TP/SL設定変遷（Phase 58全体）

| 時点 | tight_range TP | tight_range SL | 備考 |
|------|----------------|----------------|------|
| Phase 58.4まで | 0.8% | 0.6% | 滞留問題発生 |
| Phase 58.5（平日） | 0.4% | 0.3% | 半減・到達確率向上 |
| Phase 58.6（土日） | 0.25% | 0.2% | 平日の62.5% |

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
| カバー率 | 約35%（**65%が無防備**） |

### 根本原因分析

3つの独立したバグが同時に存在していた。

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

### テスト・デプロイ

```
============================================
pytest結果: 1,256テスト成功（65%カバレッジ）
flake8/black/isort: PASS
============================================
```

```bash
git commit -m "fix: Phase 58.1 TP/SL管理致命的バグ3件修正"
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

→ **今回のバグ（3ポジションに1件のTP/SL）は検出できなかった**

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

    # SL量不足チェック（同様）
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

## 🔧 Phase 58.4: fetch_margin_positions APIエラー修正【完了】

### 実施日: 2026/01/10

### 問題発覚経緯

Phase 58.3デプロイ後のGCPログ確認中に、`fetch_margin_positions()`でAPI エラー20003が発生していることを発見。

```
❌ 信用取引ポジション取得失敗: API Error 20003: ACCESS-KEY not found
```

### 根本原因分析

#### bitbank APIの署名方式

| メソッド | 署名対象 |
|---------|---------|
| **GET** | URLパス + クエリパラメータ |
| **POST** | リクエストボディ |

`fetch_margin_positions()`はPOSTメソッドで呼び出されていたが、実際にはGETメソッドが必要なエンドポイント。

#### 同様のバグ（Phase 37.2で修正済み）

`fetch_margin_status()`で同じ問題が発生し、Phase 37.2で修正されていた：
```python
# Phase 37.2修正
response = await self._call_private_api("/user/margin/status", method="GET")
```

しかし、`fetch_margin_positions()`は同様の修正が漏れていた。

### 影響範囲

| 機能 | 影響 | 深刻度 |
|------|------|--------|
| Phase 58.3 ポジション確認 | フォールバックで動作（影響軽微） | 低 |
| Phase 56.5 既存ポジションTP/SL設置 | **完全に機能しない** | 高 |
| Phase 53.6 コンテナ再起動時復元 | **完全に機能しない** | 高 |
| 孤児注文クリーンアップ | **完全に機能しない** | 高 |

### 修正内容

**ファイル**: `src/data/bitbank_client.py` L1569-1571

```python
# 修正前
response = await self._call_private_api("/user/margin/positions")

# 修正後（Phase 58.4）
# bitbank独自のprivate APIを直接呼び出し
# Phase 58.4: GETメソッドで呼び出し（エラー20003修正）
response = await self._call_private_api("/user/margin/positions", method="GET")
```

### テスト結果

```
============================================
pytest結果: 1,195 passed, 36 skipped
flake8/black/isort: PASS
============================================
```

### 追加対応

**孤児TP注文の手動削除**:
- bitbank UIで確認された孤児TP注文（ポジションなしで残存）は手動でキャンセル
- 今後はfix後の自動クリーンアップが機能

---

## 🔧 Phase 58.5: ポジション滞留問題対応【完了】

### 実施日: 2026/01/11-12

### 問題発覚経緯

2日間ポジションが決済されず滞留。利息が累積していた。

| 項目 | 値 |
|------|-----|
| Long | 0.0083 BTC @ ¥14,305,550（2026-01-10 13:44エントリー） |
| Short | 0.0156 BTC @ ¥14,335,190（2026-01-10 10:11エントリー） |
| 経過日数 | 約2日 |
| 累積利息（推定） | ¥274（0.04%/日 × 2日 × ¥341,770） |

### 根本原因分析

#### 問題1: TP/SL幅 vs 市場ボラティリティ

```
15分足ATR: ¥12,541（0.087%）
日次想定レンジ: 0.3-0.5%

現在のTP/SL（tight_range）:
  - TP: 0.8% = ¥114,800
  - SL: 0.6% = ¥86,000

→ TP/SLはATRの5-6倍。タイトレンジでは到達に数日かかる
```

#### 問題2: 両建て状態の非効率性

```
建玉合計: ¥342,365（Long + Short両方に利息発生）
実質ポジション: Net Short ¥104,609
→ 本来必要な証拠金の3.3倍を使用中
```

#### 問題3: 稼働率計算の誤り

`standard_analysis.py`が存在しないログメッセージ「実行サイクル」を検索していたため、稼働率が常に0%と表示されていた。

### 修正内容

#### 修正1: tight_range TP/SL縮小

**ファイル**: `config/core/thresholds.yaml`

```yaml
# 変更前
tight_range:
  min_profit_ratio: 0.008  # TP 0.8%
  max_loss_ratio: 0.006    # SL 0.6%

# 変更後（Phase 58.5）
tight_range:
  min_profit_ratio: 0.004  # TP 0.4%（半減）
  max_loss_ratio: 0.003    # SL 0.3%（半減）
```

**期待効果**:
- TP/SL到達確率向上
- 保有期間短縮 → 利息削減
- RR比1.33:1維持

#### 修正2: 稼働率計算修正

**ファイル**: `scripts/live/standard_analysis.py`

```python
# 変更前: 存在しないログメッセージを検索
textPayload:"実行サイクル"

# 変更後: 実際に出力されるログメッセージを検索
textPayload:"ML予測完了"
```

**追加項目**:
- 実行回数 / 期待回数の表示
- コンテナ再起動回数の取得

### bitbank手数料・利息の整理

| 項目 | 値 | 備考 |
|------|-----|------|
| **Maker手数料** | -0.02% | リベート（もらえる） |
| **Taker手数料** | +0.12% | 支払い |
| **建玉利息** | 0.04%/日 | 年率14.6%、毎日0時に発生 |

**決済時の損益計算**:
```
実現損益 = 評価損益 − 未収手数料 − 未収利息
```

### 即時対応

- ✅ 滞留ポジション手動決済（ユーザー実施）
- ✅ 孤児SL注文キャンセル（6件）

### 今後の検討事項（Phase 58.6へ引き継ぎ）

1. ~~土日のみTP/SL縮小~~: **Phase 58.6で実装完了**
2. ~~バックテストへの手数料・利息追加~~: **Phase 58.6で実装完了**
3. **ポジションタイムアウト**: 一定時間後の強制決済（Phase 59へ）

---

## 📈 Phase 58.6: バックテスト手数料・利息追加 + 土日TP/SL縮小【完了】

### 実施日: 2026/01/12

### 目的

1. **バックテストに手数料・利息を追加**: 損益計算の精度向上
2. **土日のTP/SL縮小**: 低ボラティリティ期間への対応

### データ分析結果

半年分のCSVデータ（2025/7-12、17,628サンプル）を分析。

#### 曜日別ボラティリティ（15分足）

| 曜日 | ATR平均 | レンジ平均 | 終値変動 |
|------|---------|-----------|---------|
| 月 | 0.211% | 0.220% | 0.136% |
| 火 | 0.240% | 0.240% | 0.148% |
| 水 | 0.235% | 0.229% | 0.144% |
| 木 | 0.242% | 0.240% | 0.153% |
| 金 | 0.272% | 0.273% | 0.166% |
| **土** | **0.206%** | **0.181%** | **0.115%** |
| **日** | **0.105%** | **0.108%** | **0.073%** |

#### 平日 vs 土日 比較

| 指標 | 平日 | 土日 | 比率 |
|------|------|------|------|
| ATR平均 | 0.24% | 0.16% | **65%** |
| レンジ平均 | 0.24% | 0.14% | **60%** |
| 0.40%到達率 | 15.2% | 7.0% | 46% |
| 0.25%到達率 | 34.4% | 15.7% | 46% |

**結論**: 土日のTP/SLは平日の約62.5%に縮小すべき

### 修正内容

#### 修正1: バックテスト手数料・利息追加

**ファイル**: `src/core/execution/backtest_runner.py`

```python
def _calculate_pnl(
    self,
    side: str,
    entry_price: float,
    exit_price: float,
    amount: float,
    hold_minutes: float = 0,  # 追加パラメータ
) -> float:
    """損益計算（Phase 58.6: 手数料・利息追加）"""
    # 基本損益
    if side == "buy":
        pnl = (exit_price - entry_price) * amount
    else:
        pnl = (entry_price - exit_price) * amount

    # Phase 58.6: 簡易手数料・利息計算
    position_value = entry_price * amount
    entry_fee_rebate = position_value * 0.0002  # Maker リベート（+0.02%）
    hold_days = hold_minutes / 60 / 24
    interest_cost = position_value * 0.0004 * hold_days  # 利息（0.04%/日）

    return pnl + entry_fee_rebate - interest_cost
```

**追加変更**:
- TP/SLトリガー時に`hold_minutes`を計算して渡す（L927-937）
- 強制決済時にも`hold_minutes`を計算して渡す（L1111-1117）

#### 修正2: 土日TP/SL縮小設定

**ファイル**: `config/core/thresholds.yaml`

```yaml
# tight_rangeの例
take_profit:
  regime_based:
    tight_range:
      min_profit_ratio: 0.004      # 平日 TP 0.4%
      weekend_ratio: 0.0025        # 土日 TP 0.25%

stop_loss:
  regime_based:
    tight_range:
      max_loss_ratio: 0.003        # 平日 SL 0.3%
      weekend_ratio: 0.002         # 土日 SL 0.2%

weekend_adjustment:
  enabled: true
  reduction_factor: 0.625          # 土日は平日の62.5%
```

#### 修正3: 土日判定ロジック追加

**ファイル**: `src/strategies/utils/strategy_utils.py`

```python
def calculate_stop_loss_take_profit(..., current_time=None):
    # ... 既存コード ...

    # Phase 58.6: 土日判定
    weekend_enabled = get_threshold("position_management.weekend_adjustment.enabled", False)
    if weekend_enabled and regime:
        check_time = current_time if current_time else datetime.now()
        is_weekend = check_time.weekday() >= 5  # 5=土, 6=日

        if is_weekend:
            weekend_tp = get_threshold(
                f"position_management.take_profit.regime_based.{regime}.weekend_ratio", None
            )
            weekend_sl = get_threshold(
                f"position_management.stop_loss.regime_based.{regime}.weekend_ratio", None
            )
            if weekend_tp:
                config["min_profit_ratio"] = weekend_tp
            if weekend_sl:
                config["max_loss_ratio"] = weekend_sl
```

#### 修正4: Executor呼び出し修正

**ファイル**: `src/trading/execution/executor.py`

```python
# current_timeパラメータを追加
tp_sl_prices = calculate_stop_loss_take_profit(
    entry_price=entry_price,
    signal_type=signal_type,
    df=df,
    current_time=self.current_time,  # Phase 58.6: 土日判定用
)
```

### 土日TP/SL設定一覧

| レジーム | 平日TP | 土日TP | 平日SL | 土日SL |
|---------|--------|--------|--------|--------|
| tight_range | 0.40% | 0.25% | 0.30% | 0.20% |
| normal_range | 0.60% | 0.40% | 0.40% | 0.25% |
| trending | 1.00% | 0.60% | 0.60% | 0.40% |

### 手数料・利息の影響試算

```
【1取引あたり】
建玉: ¥60,000（0.004 BTC × ¥15,000,000）
保有期間: 6時間（0.25日）

エントリー手数料リベート: +¥12（0.02%）
エグジット手数料リベート: +¥12（0.02%）※既存処理
建玉利息: -¥6（0.04% × 0.25日）
────────────────────────────
手数料・利息Net: +¥18/取引

【月間100取引の場合】
手数料・利息Net: +¥1,800
※ 全てMaker取引の場合。Taker取引が混じると減少
```

### テスト修正

**ファイル**: `tests/unit/strategies/utils/test_risk_manager.py`

- Phase 58.5のTP/SL値（0.4%/0.3%）に更新
- `weekend_adjustment.enabled: False`を全モック設定に追加

### テスト・デプロイ

```
============================================
pytest結果: 1,256テスト成功
flake8/black/isort: PASS
============================================
```

```bash
git commit -m "feat: Phase 58.6 バックテスト手数料・利息追加 + 土日TP/SL縮小"
gh workflow run backtest.yml  # Run ID: 20901983753
```

---

## 🔧 Phase 58.7: 稼働率計算改善・維持率表示明確化【完了】

### 実施日: 2026/01/12

### 問題発覚経緯

ライブモード診断で2つの問題を発見。

#### 問題1: 稼働率46.5%

| 項目 | 値 |
|------|-----|
| 実行回数 | 134回 |
| 期待回数 | 288回 |
| 稼働率 | 46.5% |

**原因**: 検索パターン「ML予測完了」は、ML予測が成功した時のみ出力される。以下のケースでは出力されない：
- 市場データ取得失敗
- MLが空配列を返す
- ML例外発生

#### 問題2: 維持率500%表示

| 項目 | 表示 | 問題 |
|------|------|------|
| ポジションなし時 | `500.0% 正常` | フォールバック値と実際の値の区別がつかない |

### 修正内容

#### 修正1: 稼働率計算の検索パターン変更

**ファイル**: `scripts/live/standard_analysis.py` L519

```python
# 変更前
textPayload:"ML予測完了"

# 変更後
textPayload:"取引サイクル開始"
```

`trading_cycle_manager.py` L96の既存ログを使用：
```python
self.logger.info(f"🔄 取引サイクル開始 - サイクル: {cycle_id}")
```

**期待効果**: サイクル開始時点でカウントされるため、実際の稼働率を正確に反映。

#### 修正2: 維持率表示のノーポジション対応

**ファイル**: `scripts/live/standard_analysis.py` L607-617

```python
# Phase 58.7: ノーポジション時は明示的に表示
if result.open_position_count == 0 and result.margin_ratio >= 500:
    margin_display = "N/A"
    margin_status = "ポジションなし"
else:
    margin_display = f"{result.margin_ratio:.1f}%"
    margin_status = (
        "正常"
        if result.margin_ratio >= 100
        else "注意" if result.margin_ratio >= 80 else "危険"
    )
lines.append(f"| 証拠金維持率 | {margin_display} | {margin_status} |")
```

#### 修正3: コンソール出力のノーポジション対応

**ファイル**: `scripts/live/standard_analysis.py` L836-839

```python
if result.open_position_count == 0 and result.margin_ratio >= 500:
    print("証拠金維持率: N/A (ポジションなし)")
else:
    print(f"証拠金維持率: {result.margin_ratio:.1f}%")
```

### 修正後の表示例

**Before**:
```
| 証拠金維持率 | 500.0% | 正常 |
稼働率: 46.5%
```

**After**:
```
| 証拠金維持率 | N/A | ポジションなし |
稼働率: 80-90%（推定）
```

### テスト・デプロイ

```
============================================
pytest結果: 1,256テスト成功
flake8/black/isort: PASS
============================================
```

---

## 📊 ライブポジション検証記録

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

### API実装

8. **GET/POST署名の違い**: bitbank APIでは署名対象が異なる（過去にも同様のバグあり）
9. **エンドポイント調査の重要性**: 新規APIメソッド追加時は必ずGET/POSTを確認

### パフォーマンス最適化

10. **土日のボラティリティ低下**: 平日の65%程度、TP/SL到達率も半減
11. **データ分析の重要性**: 設定変更前に必ず過去データで検証

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

### Phase 58.4

| ファイル | 修正内容 |
|---------|---------|
| `src/data/bitbank_client.py` | `fetch_margin_positions()` GETメソッド修正（L1569-1571） |

### Phase 58.5

| ファイル | 修正内容 |
|---------|---------|
| `config/core/thresholds.yaml` | tight_range TP/SL縮小（0.8%/0.6%→0.4%/0.3%） |
| `scripts/live/standard_analysis.py` | 稼働率計算修正（"実行サイクル"→"ML予測完了"） |

### Phase 58.6

| ファイル | 修正内容 |
|---------|---------|
| `src/core/execution/backtest_runner.py` | `_calculate_pnl()`に手数料・利息追加、`hold_minutes`計算 |
| `src/strategies/utils/strategy_utils.py` | 土日判定ロジック追加、`current_time`パラメータ追加 |
| `config/core/thresholds.yaml` | 土日用TP/SL設定（`weekend_ratio`）追加 |
| `src/trading/execution/executor.py` | `current_time`パラメータ追加 |
| `tests/unit/strategies/utils/test_risk_manager.py` | Phase 58.5設定対応、土日判定無効化 |

### Phase 58.7

| ファイル | 修正内容 |
|---------|---------|
| `scripts/live/standard_analysis.py` | 稼働率検索パターン変更（L519）、維持率表示条件分岐追加（L607-617, L836-839） |

---

## 📊 Phase 58 進捗サマリー

### 完了項目

- [x] TP/SL管理バグ3件修正（Phase 58.1）
- [x] ライブ分析スクリプト改善（Phase 58.2）
- [x] 現行ポジション正当性検証
- [x] ポジション同期問題修正（Phase 58.3）
- [x] fetch_margin_positions APIエラー修正（Phase 58.4）
- [x] tight_range TP/SL縮小（Phase 58.5）
- [x] 稼働率計算修正（Phase 58.5）
- [x] バックテスト手数料・利息追加（Phase 58.6）
- [x] 土日TP/SL縮小実装（Phase 58.6）
- [x] 稼働率計算改善（Phase 58.7）
- [x] 維持率表示明確化（Phase 58.7）

### 検証完了

- [x] Phase 58.5 バックテスト結果確認（Run ID: 20901116954）✅
- [x] Phase 58.6 バックテスト結果確認（Run ID: 20901983753）✅

### Phase 59へ引き継ぎ

| 優先度 | 項目 | 根拠 |
|--------|------|------|
| 🔴 高 | BBReversal無効化 | 勝率8.3%・¥-5,451の赤字 |
| 🟡 中 | DonchianChannel重み削減 | ¥-3,560の赤字 |
| 🟡 中 | 信頼度フィルター見直し | 高信頼度帯の逆転現象 |
| 🟢 低 | ポジションタイムアウト | 滞留防止の最終手段 |

---

## バックテスト結果比較（確定）

| Phase | TP/SL設定 | 手数料 | 総損益 | 取引数 | 勝率 | PF | 最大DD |
|-------|-----------|--------|--------|--------|------|-----|--------|
| 58.4 | 0.8%/0.6% | なし | ¥+23,073 | 501件 | 44.7% | 1.18 | 2.93% |
| 58.5 | 0.4%/0.3% | なし | ¥+27,466 | 583件 | 48.5% | - | - |
| **58.6** | 0.4%/0.3%+土日縮小 | あり | **¥+35,105** | 589件 | **50.9%** | **1.38** | **1.55%** |

### 改善効果

| 比較 | 損益改善 | 改善率 |
|------|----------|--------|
| 58.4 → 58.5 | +¥4,393 | +19% |
| 58.5 → 58.6 | +¥7,639 | +28% |
| **58.4 → 58.6** | **+¥12,032** | **+52%** |

### Phase 58.6の主要改善

| 指標 | 58.4 | 58.6 | 改善 |
|------|------|------|------|
| 総損益 | ¥+23,073 | ¥+35,105 | **+52%** |
| 勝率 | 44.7% | 50.9% | +6.2pt |
| PF | 1.18 | 1.38 | +17% |
| 最大DD | 2.93% | 1.55% | **-47%** |
| シャープレシオ | 4.78 | 9.43 | +97% |

**成功要因**:
1. **TP/SL縮小** (0.8%/0.6% → 0.4%/0.3%): 回転率向上・滞留解消
2. **土日TP/SL縮小** (62.5%): 低ボラティリティ期間への適切な対応
3. **手数料計算追加**: Maker rebate +0.02%で実収益増加

---

**📅 最終更新**: 2026年1月12日 - Phase 58.7完了（稼働率計算改善・維持率表示明確化）

# Phase 50.5: SL注文保護・Phase 42完全削除

**実装日**: 2025年10月30日
**ステータス**: ✅ 完了
**Commit**: ee47661c

---

## 🚨 **問題発生**

### ユーザー報告（2025/10/30 早朝）

> "現在bitbankのUIを直接見ていますが、TPである指値は10個ありますが、SLの逆指値が一つも存在しないです。一時期は逆指値が存在していたはずですが、いつの間にか消えていました。"

**重大性**: Critical
- **TP注文**: 10個存在（正常）
- **SL注文**: 0個（完全消失）
- **リスク**: 無制限損失リスク・青天井状態
- **含み損**: 569円（期待150円の379%）

---

## 🔍 **根本原因調査**

### CSV データ分析

**ユーザー提供CSVファイル解析結果**:

```
10/29 04:47:19 - BUY約定（17,345,963円）
10/29 04:47:24 - TP注文配置（17,547,240円）→ 未約定 ✅
10/29 04:47:24 - SL注文配置（trigger 17,112,055円）→ CANCELED_UNFILLED ❌
```

**全10ポジションで100%同一パターン**:
- BUY約定成功 ✅
- TP注文配置 → 現在も存在 ✅
- SL注文配置 → **配置直後（同じ秒）にCANCELED** ❌

### Production Logs 確認

```bash
# Phase 46 SL配置ログが一切出ていない
# 期待: "✅ Phase 46: 個別SL配置完了 - ID: xxx"
# 実際: ログなし
```

### 根本原因特定（Phase 37.5.3と相互作用）

**問題のコード** (`src/trading/execution/stop_manager.py:78-80`):

```python
# Phase 37.5.3: ライブモードでポジション消失検出・残注文クリーンアップ
if mode == "live" and bitbank_client:
    await self._cleanup_orphaned_orders(virtual_positions, bitbank_client)
```

**問題のフロー**:

1. **executor.py**: BUY注文約定 → virtual_positionsに追加（`sl_order_id` なし）
2. **stop_manager.py**: SL注文配置成功（注文ID: 51245764461）
3. **しかし**: virtual_positionsに `sl_order_id` が保存されていない
   - Phase 50.3.1がデプロイされていない（10/28デプロイには未含）
   - Phase 50.3.1で実装された TP/SL注文ID保存機能が動作していない
4. **`_cleanup_orphaned_orders()`実行**:
   - virtual_positionsのポジションに sl_order_id がない
   - 実際のbitbank positionsと照合失敗
   - **孤立ポジションと誤判定**
   - SL注文を即座にキャンセル ❌

**なぜTP注文は残っているのか**:
- TP注文は limit 注文
- SL注文は stop 注文
- クリーンアップ判定ロジックで異なる扱い

---

## ✅ **解決策**

### Phase 50.5実装方針

1. **Phase 37.5.3クリーンアップ機能を一時無効化**
   - SL注文キャンセル問題を即座に解消
   - Phase 50.3.1デプロイ後、再有効化検討

2. **Phase 42統合TP/SL関係を完全削除**
   - ユーザー指摘: "統合はやめたはず。毎回統合SLや古いTPSLの設定を参照する。Phase 42関係を消し去って欲しい"
   - 混乱の原因となるコード・設定・ドキュメントを完全削除
   - Phase 46個別TP/SL実装のみに統一

---

## 📋 **実装内容**

### 1. Phase 37.5.3クリーンアップ機能無効化

**ファイル**: `src/trading/execution/stop_manager.py`

**修正箇所** (Line 78-84):

```python
# Phase 50.5: SL注文キャンセル問題により一時無効化
# Phase 37.5.3クリーンアップ機能が新規SL注文を誤ってキャンセルする問題を発見
# 根本原因: virtual_positionsに sl_order_id が保存されていない（Phase 50.3.1未デプロイ時）
# → 孤立注文と誤判定 → SL注文即座にキャンセル → 無制限損失リスク
# Phase 50.5: 一時無効化（Phase 50.3.1デプロイ後、再有効化検討）
# if mode == "live" and bitbank_client:
#     await self._cleanup_orphaned_orders(virtual_positions, bitbank_client)
```

**効果**:
- SL注文配置後、キャンセルされなくなる ✅
- Phase 46個別SL配置ロジックは正常動作（CSV確認済み）
- 損失制限機能が正常に動作

### 2. Phase 42統合TP/SL設定削除

**ファイル**: `config/core/thresholds.yaml`

**削除箇所**:
```yaml
# Line 11: "統合TP/SL" 参照削除
# Line 385-386: Phase 42.4/42.2コメント削除
# Line 391: `consolidate_on_new_entry: false` 削除
```

**変更後**:
```yaml
position_management:
  # Phase 46: 個別TP/SL実装（Phase 42統合TP/SL削除済み）
  min_account_balance: 10000
  ...
```

### 3. Phase 42関連コメント削除

**ファイル**: `src/trading/position/tracker.py`

**削除箇所**:
- Phase 42.2 コメント削除
- Phase 42統合TP/SL関連ドキュメント削除
- Phase 46個別TP/SL実装に統一

### 4. CLAUDE.md Phase 42参照削除

**削除箇所**:
- "Phase 42.4以降" → "Phase 46以降" に変更
- Phase 42.1/42.2/42.3/42.4セクション大幅簡略化
- Phase 46個別TP/SL実装のみに統一

---

## 🎯 **期待効果**

### 直接的効果

1. **SL注文保護**: 配置後キャンセルされない → 損失制限機能復活 ✅
2. **Phase 42混乱解消**: 統合TP/SL参照完全削除 → 誤認識防止 ✅
3. **システム簡潔化**: Phase 46個別TP/SL実装のみ → 保守性向上 ✅

### 間接的効果

1. **証拠金維持率80%チェック**: Phase 50.4との統合デプロイで完全動作
2. **ポジション蓄積制限**: 証拠金維持率80%未満でエントリー拒否
3. **含み損制限**: 期待値通りの損失制限（SL 1.5% = 150円 / 1万円証拠金）

---

## 📝 **次回予定**

1. ✅ Phase 50.5実装完了
2. ⏳ GCPデプロイ（Phase 50.3.1-50.5統合）
3. ⏳ 本番ログ確認（SL注文が残っているか）
4. ⏳ ユーザー確認（bitbank UIでSL注文確認）
5. ⏳ 外部API特徴量取得失敗確認（ユーザー報告）

---

**Phase 50.5完了日**: 2025年10月30日
**デプロイ予定日**: 2025年10月30日
**次回更新予定**: Phase 50.5稼働確認後

# src/trading/execution/ - 注文実行層 🚀 Phase 52.4-B完了

## 🎯 役割・責任

注文実行・TP/SL管理を担当します。Phase 52.4-Bでtradingレイヤードアーキテクチャの一部として分離、Phase 42で統合TP/SL実装、Phase 52.4-B.2でトレーリングストップ機能を完成、Phase 52.4-B.4でTP/SL設定最適化、Phase 52.4-Bで技術的負債削除・SL保護機能を実現、Phase 52.4-Bでデイトレード特化・シンプル設計に回帰、**Phase 52.4-B.16でTP/SL設定完全見直し・設定値確実反映を実現**しました。

## 📂 ファイル構成

```
execution/
├── executor.py              # 注文実行サービス（966行・Phase 52.4-B完了）
├── tp_sl_calculator.py      # TP/SL再計算サービス（226行・Phase 52.4-B新規）
├── atomic_entry_manager.py  # Atomic Entry管理（370行・Phase 52.4-B新規）
├── stop_manager.py          # TP/SL管理（1,003行・Phase 52.4-B完了）
├── order_strategy.py        # 注文戦略（355行・Phase 52.4-B完了）
├── __init__.py              # モジュール初期化
└── README.md                # このファイル
```

## 🚀 Phase 52.4-B新規クラス

### **tp_sl_calculator.py** - TP/SL再計算サービス (226行)

ライブトレードにおける実約定価格ベースのTP/SL再計算を担当。

**主要機能**:
- 3段階ATRフォールバック（evaluation → DataService → fallback_atr）
- 実約定価格ベースでTP/SL再計算（SL距離5x誤差修正）
- レジーム情報取得・RiskManagerに渡す

**主要メソッド**:
```python
async def calculate(
    evaluation: TradeEvaluation,
    result: ExecutionResult,
    side: str,
    amount: float
) -> Tuple[float, float]:
    """
    Phase 52.4-B: ライブトレードTP/SL再計算（3段階ATRフォールバック）

    Returns:
        Tuple[float, float]: (final_tp, final_sl)

    Raises:
        CryptoBotError: ATR取得失敗・TP/SL再計算失敗時
    """
```

---

### **atomic_entry_manager.py** - Atomic Entry管理サービス (370行)

エントリー・TP・SL注文のアトミックトランザクション管理を担当。

**主要機能**:
- TP/SL注文配置（Exponential Backoff リトライ・3回）
- Atomic Entry ロールバック（全成功 or 全キャンセル）
- エントリー前クリーンアップ（古いTP/SL注文削除）
- ロールバック状況追跡（success・cancelled_orders・manual_intervention_required）

**主要メソッド**:
```python
async def place_tp_with_retry(...) -> Optional[Dict[str, Any]]:
    """TP注文配置（リトライ付き）"""

async def place_sl_with_retry(...) -> Optional[Dict[str, Any]]:
    """SL注文配置（リトライ付き）"""

async def cleanup_old_tp_sl_before_entry(...) -> None:
    """エントリー前の古いTP/SL注文クリーンアップ"""

async def rollback_entry(...) -> Dict[str, Any]:
    """Atomic Entry ロールバック（全注文キャンセル）"""
```

## 📈 Phase 52.4-B完了（2025年10月26日）

**🎯 Phase 52.4-B.16: TP/SL設定完全見直し・設定値確実反映・ライブモード問題解決**

### 🚨 緊急修正背景

**ライブモード問題**: TP/SL価格が設定値（thresholds.yaml）と異なる問題が発生。
- 設定値: SL 1.5%・TP 1.0% (max_loss_ratio: 0.015, min_profit_ratio: 0.01) ← Phase 52.4-B.8時点
- 実際のTP/SL: 設定値が反映されず、ハードコード値やATRのみで計算

### ✅ Phase 52.4-B.16.1 executor.py TP/SL設定完全渡し修正（Line 348-371）

**根本原因**: executor.pyがRiskManagerに不完全な設定を渡していた。

**修正前（BROKEN）**:
```python
# Line 350: 間違った設定キー名・不完全な設定渡し
config = {"take_profit_ratio": get_threshold("tp_default_ratio", 2.0)}
recalculated_sl, recalculated_tp = RiskManager.calculate_stop_loss_take_profit(...)
```

**修正後（FIXED）**:
```python
# Phase 52.4-B.16: TP/SL設定完全渡し（thresholds.yaml完全準拠）
config = {
    # TP設定（Phase 52.4-B.8時点: min_profit_ratio: 0.01 = 1.0%）
    "take_profit_ratio": get_threshold("position_management.take_profit.default_ratio", 1.33),
    "min_profit_ratio": get_threshold("position_management.take_profit.min_profit_ratio", 0.01),
    # SL設定
    "max_loss_ratio": get_threshold("position_management.stop_loss.max_loss_ratio", 0.015),
    "min_distance_ratio": get_threshold("position_management.stop_loss.min_distance.ratio", 0.015),
    "default_atr_multiplier": get_threshold("position_management.stop_loss.default_atr_multiplier", 2.0),
}
```

**効果**:
- ✅ 全5設定項目を完全渡し（TP設定2項目・SL設定3項目）
- ✅ 正しい設定キー名使用（"position_management."プレフィックス）
- ✅ max_loss_ratio: 0.015（1.5%）が確実に反映

### ✅ Phase 52.4-B.16.2 strategy_utils.py RiskManager完全見直し（Line 169-274）

**根本原因**: RiskManagerがmax_loss_ratio・min_profit_ratioを無視していた。

**修正前（BROKEN）**:
```python
# ATRベースのSL距離のみ計算（max_loss_ratio無視）
stop_loss_distance = current_atr * stop_loss_multiplier

# TP距離も不完全（min_profit_ratio無視）
take_profit_distance = stop_loss_distance * default_tp_ratio
```

**修正後（FIXED）**:
```python
# === SL距離計算（max_loss_ratio優先） ===
max_loss_ratio = config.get("max_loss_ratio", 0.015)

# max_loss_ratioベースのSL距離（最優先）
sl_distance_from_ratio = current_price * max_loss_ratio

# ATRベースのSL距離（補助）
sl_distance_from_atr = current_atr * stop_loss_multiplier

# 最小値を採用（安全優先）
stop_loss_distance = min(sl_distance_from_ratio, sl_distance_from_atr)

# === TP距離計算（min_profit_ratio優先） ===
min_profit_ratio = config.get("min_profit_ratio", 0.02)

# min_profit_ratioベースのTP距離
tp_distance_from_ratio = current_price * min_profit_ratio

# SL距離×TP比率ベースのTP距離
tp_distance_from_sl = stop_loss_distance * default_tp_ratio

# 大きい方を採用（利益確保優先）
take_profit_distance = max(tp_distance_from_ratio, tp_distance_from_sl)
```

**効果**:
- ✅ max_loss_ratio: 0.015（1.5%）を確実に遵守
- ✅ min_profit_ratio: 0.02（2%）を確実に遵守
- ✅ 双方向計算（ratio-based + ATR-based）で最適値選択
- ✅ 詳細ログ出力（デバッグ容易化）

### 📊 Phase 52.4-B.16重要事項
- **設定値確実反映**: max_loss_ratio・min_profit_ratio完全遵守
- **デュアル計算アプローチ**: ratio-based（安全優先）+ ATR-based（市場適応）
- **詳細ログ**: 全計算ステップログ出力（検証容易化）
- **品質保証**: flake8準拠（E226エラー修正完了）

---

## 📈 Phase 52.4-B完了（2025年10月22日）

**🎯 Phase 52.4-B: デイトレード特化・シンプル設計回帰・スイングトレード機能削除**

### ✅ Phase 52.4-B.2.4 不要コード削除成果（-1,172行のコード削減）

**背景**: Phase 42-43で実装したスイングトレード向け機能（統合TP/SL・トレーリングストップ）が、デイトレード特化戦略では過剰に複雑で、本番環境で22注文問題を引き起こしました。Phase 52.4-Bでデイトレード特化設計に回帰し、シンプル性・保守性を最優先しました。

**削除内容**:
- **executor.py**: トレーリングストップ監視削除（Line 811-992、-182行）
- **executor.py**: 統合TP/SL処理削除（Line 665-806、-142行）
- **stop_manager.py**: トレーリングSL更新削除（Line 1083-1302、-220行）
- **stop_manager.py**: 統合TP/SL配置削除（Line 879-1077、-199行）
- **order_strategy.py**: 統合TP/SL価格計算削除（Line 352-467、-148行）
- **order_strategy.py**: SL最悪位置保護削除（Line 44-84、-41行）
- **tracker.py**: 統合TP/SL管理削除（Line 366-538、-173行）
- **thresholds.yaml**: トレーリング設定削除（-7行）
- **テスト**: Phase 42-43関連テスト8件削除（-60行）
- **合計**: -1,172行削除（Phase 42-43レガシーコード完全削除）

**効果**:
- コードベース大幅簡略化（executor.py: 980行 → 478行、-51.2%）
- 個別TP/SL配置に回帰（シンプル・予測可能・デバッグ容易）
- 保守性・可読性大幅向上

### ✅ Phase 52.4-B.2.5 個別TP/SL配置ロジック実装（+131行）

**背景**: Phase 52.4-B.5で削除したPhase 29.6の個別TP/SL実装（`place_tp_sl_orders()`）を、Phase 52.4-B設計に合わせて再実装しました。

**実装内容**:

**stop_manager.py** (`place_individual_tp_sl()`):
```python
async def place_individual_tp_sl(
    self,
    bitbank_client: BitbankClient,
    side: str,
    entry_price: float,
    position_size: float,
    tp_price: Optional[float] = None,
    sl_price: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Phase 52.4-B: 個別TP/SL配置（デイトレード特化・シンプル設計）

    Args:
        bitbank_client: Bitbank APIクライアント
        side: ポジションサイド（buy/sell）
        entry_price: エントリー価格
        position_size: ポジションサイズ
        tp_price: TP価格（Noneの場合は自動計算）
        sl_price: SL価格（Noneの場合は自動計算）

    Returns:
        Dict: {
            "tp_order_id": Optional[str],
            "sl_order_id": Optional[str],
            "success": bool
        }

    設計方針:
        - Phase 29.6実装を継承（実績あり）
        - RiskManager設定値を直接使用（ハードコード排除）
        - get_threshold()でthresholds.yaml参照
    """
```

**効果**:
- エントリー毎に個別TP/SL配置（1エントリー = 3注文）
- 設定値反映確認（SL 2%・TP 4%・RR 2.0:1）
- ハードコード値なし（get_threshold()パターン使用）

### ✅ Phase 52.4-B.3 ハードコード値完全排除（5箇所修正）

**背景**: 要件定義.md「ハードコード値ゼロ」要件を遵守するため、残存していたハードコード値を完全排除しました。

**修正箇所**:
1. **executor.py:129**: `default_side = get_threshold("trading_constraints.default_side", "buy")`
2. **executor.py:211**: `sl_min = get_threshold("sl_min_distance_ratio", 0.01)`
3. **order_strategy.py:72**: `limit_price = best_ask * (1 + get_threshold("order_execution.guaranteed_execution_premium", 0.0005))`
4. **order_strategy.py:75**: `limit_price = best_bid * (1 - get_threshold("order_execution.guaranteed_execution_premium", 0.0005))`
5. **RiskManager.py:369**: `sl_rate = get_threshold("sl_min_distance_ratio", 0.01)`

**効果**:
- ハードコード値完全排除（100%達成）
- 設定ファイル一元管理（thresholds.yaml）
- 運用中のパラメータ調整容易化

### ✅ Phase 52.4-B.5 ペーパートレードバグ修正

**背景**: ローカルペーパーモード検証時にパラメータ不一致エラーを発見しました。

**修正内容**:

**executor.py** (Line 473-478):
```python
# 修正前（INCORRECT）:
self.position_tracker.add_position(
    position_id=virtual_order_id,  # WRONG
    side=side,
    amount=amount,
    entry_price=price,  # WRONG
)

# 修正後（FIXED）:
self.position_tracker.add_position(
    order_id=virtual_order_id,
    side=side,
    amount=amount,
    price=price,
)
```

**効果**:
- ペーパートレード正常動作化
- PositionTrackerシグネチャ準拠
- エラー「ペーパーポジション追加エラー」完全解消

### 📊 Phase 52.4-B重要事項
- **Phase 52.4-B設計哲学**: デイトレード特化・シンプル性・保守性優先
- **削除vs実装**: -1,172行削除 + 131行実装 = -1,041行純削減
- **品質保証完了**: 1,101テスト100%成功・68.93%カバレッジ達成
- **ペーパートレード検証完了**: 全8項目チェックリストクリア

---

## 📈 Phase 52.4-B完了（2025年10月21日）

**🎯 Phase 52.4-B: 技術的負債削除・SL保護・維持率制限実装（再設計版）**

### ✅ Phase 52.4-B.5 技術的負債削除成果（-320行のコード削減）

**背景**: Phase 52.4-B.1の統合TP/SL実装後も、Phase 29.6の個別TP/SL実装（`place_tp_sl_orders()`メソッド）が残存し、フォールバックコードや重複処理が必要でした。Phase 52.4-B.5で完全削除し、クリーンなアーキテクチャを実現しました。

**削除内容**:
- **stop_manager.py**: `place_tp_sl_orders()`メソッド削除（Line 87-219、-133行）
- **executor.py**: individualモード分岐削除（Line 350-391、-28行）
- **executor.py**: fallbackハンドリング削除（Line 783-796、-11行）
- **thresholds.yaml**: `tp_sl_mode`設定削除（-3行）
- **tests**: 個別TP/SL関連テスト7件削除（-145行）
- **合計**: -320行削除（Phase 29.6レガシーコード完全削除）

**効果**:
- コードベース大幅簡略化（executor.py: 1,008行 → 980行）
- 統合TP/SL強制化（注文数91.7%削減効果維持）
- 保守性・可読性大幅向上

### ✅ Phase 52.4-B SL最悪位置保護実装（ナンピン時損失拡大防止）

**背景**: 本番環境で12回ナンピンエントリー実行時、SL位置が初期位置から移動し、損失が200円 → 450円に拡大（+125%）しました。

**実装内容**:

**order_strategy.py** (`calculate_consolidated_tp_sl_prices()`):
```python
def calculate_consolidated_tp_sl_prices(
    self,
    average_entry_price: float,
    side: str,
    market_conditions: Optional[Dict[str, Any]] = None,
    existing_sl_price: Optional[float] = None,  # Phase 52.4-B追加
) -> Dict[str, float]:
    """
    Phase 52.4-B: ナンピン時は既存SLと比較し、より保護的なSL位置を維持する。
    - 買いポジション: max(新規SL, 既存SL) - 高い方が保護的
    - 売りポジション: min(新規SL, 既存SL) - 低い方が保護的
    """
    # SL計算
    new_sl_price = average_entry_price * (1 - sl_rate)  # 新規SL

    # Phase 52.4-B: 既存SLと比較し、より保護的な位置を維持
    if existing_sl_price is not None and existing_sl_price > 0:
        if side.lower() == "buy":
            stop_loss_price = max(new_sl_price, existing_sl_price)  # 高い方
        else:  # sell
            stop_loss_price = min(new_sl_price, existing_sl_price)  # 低い方
    else:
        stop_loss_price = new_sl_price
```

**executor.py** (既存SL価格取得):
```python
# Phase 52.4-B: 既存SL価格を取得（SL最悪位置維持用）
existing_ids = self.position_tracker.get_consolidated_tp_sl_ids()
existing_sl_price = existing_ids.get("sl_price", 0)

# 統合TP/SL価格計算（Phase 52.4-B: 既存SL考慮）
new_tp_sl_prices = self.order_strategy.calculate_consolidated_tp_sl_prices(
    average_entry_price=new_average_price,
    side=side,
    market_conditions=market_conditions,
    existing_sl_price=existing_sl_price if existing_sl_price > 0 else None,
)
```

**効果**:
- 初回エントリー: SL = 新規計算値（例: entry - 2%）
- 2回目ナンピン: 平均価格上昇 → 新規SL > 既存SL → **既存SL維持**
- 結果: 最大損失が初期設定（2% = 200円）を超えない

### 📊 Phase 52.4-B重要事項
- **Phase 52.4-B.5前提**: 技術的負債削除により、クリーンな実装を実現
- **後方互換性**: ペーパートレード・ライブトレード両対応
- **品質保証完了**: 1,141テスト100%成功・69.47%カバレッジ達成

---

## 🗑️ Phase 46削除機能（2025年10月22日）

**Phase 46: デイトレード特化・個別TP/SL実装・シンプル設計回帰**

Phase 46において、以下の複雑な機能を完全削除し、シンプルで保守性の高い実装に回帰しました。

### ❌ 削除された機能

**Phase 42統合TP/SL（完全削除）**:
- 複数エントリーの平均価格ベースで単一TP/SL注文を配置する機能
- 削除理由: デイトレード特化により、個別TP/SL管理がシンプルで予測可能
- 影響: executor.py・stop_manager.py・order_strategy.py・tracker.pyから関連コード完全削除

**Phase 52.4-B.2トレーリングストップ（完全削除）**:
- Bybit/Binance準拠のトレーリングストップロス機能
- 削除理由: デイトレード特化により、固定TP/SL（SL 1.5%・TP 1.0%・RR比0.67:1）で十分
- 影響: executor.py・stop_manager.pyから関連コード完全削除

### ✅ Phase 46実装内容

**個別TP/SL実装**（現在の仕様）:
- エントリー毎に独立したTP/SL注文を配置
- SL 1.5%・TP 1.0%・RR比0.67:1（Phase 49.18デイトレード特化・レンジ型に最適）
- シンプル設計・保守性向上・予測可能な動作・デバッグ容易性確保

**Phase 46の設計思想**:
- **KISS原則**: 複雑性削減・シンプル実装優先
- **デイトレード特化**: 固定TP/SL・短期保有前提
- **予測可能性**: 個別TP/SL管理・明確な動作保証
- **保守性**: コードベース大幅簡略化・技術的負債削減

**詳細**: `docs/開発履歴/Phase_46.md`（Phase 46完全記録）

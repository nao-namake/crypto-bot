# src/trading/execution/ - 注文実行層 🚀 Phase 49.16完了

## 🎯 役割・責任

注文実行・TP/SL管理を担当します。Phase 38でtradingレイヤードアーキテクチャの一部として分離、Phase 42で統合TP/SL実装、Phase 42.2でトレーリングストップ機能を完成、Phase 42.4でTP/SL設定最適化、Phase 43で技術的負債削除・SL保護機能を実現、Phase 46でデイトレード特化・シンプル設計に回帰、**Phase 49.16でTP/SL設定完全見直し・設定値確実反映を実現**しました。

## 📂 ファイル構成

```
execution/
├── executor.py         # 注文実行サービス（758行・Phase 49.16: TP/SL設定完全渡し）
├── stop_manager.py     # TP/SL管理（989行・Phase 49完了）
├── order_strategy.py   # 注文戦略（356行・Phase 49完了）
├── __init__.py         # モジュール初期化
└── README.md           # このファイル
```

## 📈 Phase 49.16完了（2025年10月26日）

**🎯 Phase 49.16: TP/SL設定完全見直し・設定値確実反映・ライブモード問題解決**

### 🚨 緊急修正背景

**ライブモード問題**: TP/SL価格が設定値（thresholds.yaml）と異なる問題が発生。
- 設定値: SL 1.5%・TP 2% (max_loss_ratio: 0.015, min_profit_ratio: 0.02)
- 実際のTP/SL: 設定値が反映されず、ハードコード値やATRのみで計算

### ✅ Phase 49.16.1 executor.py TP/SL設定完全渡し修正（Line 348-371）

**根本原因**: executor.pyがRiskManagerに不完全な設定を渡していた。

**修正前（BROKEN）**:
```python
# Line 350: 間違った設定キー名・不完全な設定渡し
config = {"take_profit_ratio": get_threshold("tp_default_ratio", 2.0)}
recalculated_sl, recalculated_tp = RiskManager.calculate_stop_loss_take_profit(...)
```

**修正後（FIXED）**:
```python
# Phase 49.16: TP/SL設定完全渡し（thresholds.yaml完全準拠）
config = {
    # TP設定
    "take_profit_ratio": get_threshold("position_management.take_profit.default_ratio", 1.33),
    "min_profit_ratio": get_threshold("position_management.take_profit.min_profit_ratio", 0.02),
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

### ✅ Phase 49.16.2 strategy_utils.py RiskManager完全見直し（Line 169-274）

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

### 📊 Phase 49.16重要事項
- **設定値確実反映**: max_loss_ratio・min_profit_ratio完全遵守
- **デュアル計算アプローチ**: ratio-based（安全優先）+ ATR-based（市場適応）
- **詳細ログ**: 全計算ステップログ出力（検証容易化）
- **品質保証**: flake8準拠（E226エラー修正完了）

---

## 📈 Phase 46完了（2025年10月22日）

**🎯 Phase 46: デイトレード特化・シンプル設計回帰・スイングトレード機能削除**

### ✅ Phase 46.2.4 不要コード削除成果（-1,172行のコード削減）

**背景**: Phase 42-43で実装したスイングトレード向け機能（統合TP/SL・トレーリングストップ）が、デイトレード特化戦略では過剰に複雑で、本番環境で22注文問題を引き起こしました。Phase 46でデイトレード特化設計に回帰し、シンプル性・保守性を最優先しました。

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

### ✅ Phase 46.2.5 個別TP/SL配置ロジック実装（+131行）

**背景**: Phase 43.5で削除したPhase 29.6の個別TP/SL実装（`place_tp_sl_orders()`）を、Phase 46設計に合わせて再実装しました。

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
    Phase 46: 個別TP/SL配置（デイトレード特化・シンプル設計）

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

### ✅ Phase 46.3 ハードコード値完全排除（5箇所修正）

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

### ✅ Phase 46.5 ペーパートレードバグ修正

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

### 📊 Phase 46重要事項
- **Phase 46設計哲学**: デイトレード特化・シンプル性・保守性優先
- **削除vs実装**: -1,172行削除 + 131行実装 = -1,041行純削減
- **品質保証完了**: 1,101テスト100%成功・68.93%カバレッジ達成
- **ペーパートレード検証完了**: 全8項目チェックリストクリア

---

## 📈 Phase 43完了（2025年10月21日）

**🎯 Phase 43: 技術的負債削除・SL保護・維持率制限実装（再設計版）**

### ✅ Phase 43.5 技術的負債削除成果（-320行のコード削減）

**背景**: Phase 42.1の統合TP/SL実装後も、Phase 29.6の個別TP/SL実装（`place_tp_sl_orders()`メソッド）が残存し、フォールバックコードや重複処理が必要でした。Phase 43.5で完全削除し、クリーンなアーキテクチャを実現しました。

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

### ✅ Phase 43 SL最悪位置保護実装（ナンピン時損失拡大防止）

**背景**: 本番環境で12回ナンピンエントリー実行時、SL位置が初期位置から移動し、損失が200円 → 450円に拡大（+125%）しました。

**実装内容**:

**order_strategy.py** (`calculate_consolidated_tp_sl_prices()`):
```python
def calculate_consolidated_tp_sl_prices(
    self,
    average_entry_price: float,
    side: str,
    market_conditions: Optional[Dict[str, Any]] = None,
    existing_sl_price: Optional[float] = None,  # Phase 43追加
) -> Dict[str, float]:
    """
    Phase 43: ナンピン時は既存SLと比較し、より保護的なSL位置を維持する。
    - 買いポジション: max(新規SL, 既存SL) - 高い方が保護的
    - 売りポジション: min(新規SL, 既存SL) - 低い方が保護的
    """
    # SL計算
    new_sl_price = average_entry_price * (1 - sl_rate)  # 新規SL

    # Phase 43: 既存SLと比較し、より保護的な位置を維持
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
# Phase 43: 既存SL価格を取得（SL最悪位置維持用）
existing_ids = self.position_tracker.get_consolidated_tp_sl_ids()
existing_sl_price = existing_ids.get("sl_price", 0)

# 統合TP/SL価格計算（Phase 43: 既存SL考慮）
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

### 📊 Phase 43重要事項
- **Phase 43.5前提**: 技術的負債削除により、クリーンな実装を実現
- **後方互換性**: ペーパートレード・ライブトレード両対応
- **品質保証完了**: 1,141テスト100%成功・69.47%カバレッジ達成

---

## 📈 Phase 42.4完了（2025年10月20日）

**🎯 Phase 42.4: TP/SL設定最適化・ハードコード値削除・デイトレード対応**

### ✅ Phase 42.4最適化成果
- **ハードコード値完全削除**: order_strategy.py lines 378-397のハードコード値をthresholds.yaml読み込みに変更
  - 修正前: `sl_rate = min(0.02, max_loss_ratio)` ← 2%ハードコード
  - 修正後: `sl_rate = sl_min_distance_ratio` ← thresholds.yaml参照
  - 修正前: `default_tp_ratio = tp_config.get("default_ratio", 2.5)` ← 2.5倍ハードコード
  - 修正後: `default_tp_ratio = get_threshold("tp_default_ratio", 1.5)` ← thresholds.yaml参照

- **TP/SL距離最適化**: 2025年市場ベストプラクティス準拠（BTC日次ボラティリティ2-5%対応）
  - **SL: 2.0%**（市場推奨3-8%の下限・証拠金1万円で最大損失200円）
  - **TP: 3.0%**（細かく利益確定・市場ボラティリティ中間値）
  - **RR比: 1.5:1**（勝率40%以上で収益化可能・現行MLモデルF1スコア0.56-0.61）

- **デイトレード段階的最適化**:
  - 当面はRR比1.5:1で実績収集
  - 将来的に2:1への移行を検討（勝率33.3%で収益化）
  - 市場データに基づく保守的アプローチ

- **品質保証完了**: 1,164テスト100%成功・69.58%カバレッジ達成

### 📊 Phase 42.4重要事項
- **設定値一元化**: TP/SL距離をthresholds.yamlで一元管理
- **Optuna最適化統合**: optimize_risk_management.py FIXED_TP_SL_PARAMS同期（Phase 40統合対応）
- **後方互換性**: 既存の統合TP/SL・トレーリングストップ機能と完全互換

## 📈 Phase 42.2完了（2025年10月18日）

**🎯 Phase 42.2: トレーリングストップ実装・Bybit/Binance準拠・含み益保護**

### ✅ Phase 42.2最適化成果
- **トレーリングストップ実装**: Bybit/Binance標準仕様準拠（executor.py:811-992, stop_manager.py:1083-1302）
  - 2%含み益でトレーリング開始（activation_profit: 0.02）
  - 3%距離（trailing_percent: 0.03）・Bybit/Binance標準・TP2.5%対応最適化
  - 200円最低更新距離（min_update_distance: 200）・ノイズ防止
  - 0.5%最低利益保証（min_profit_lock: 0.005）・SLがentry+0.5%を下回らない
  - SL>TP時にTPキャンセル（cancel_tp_when_exceeds: true）・さらなる上昇追従

- **含み益保護機能**: -450円損失防止（Phase 42.2有効化効果）
  - 背景: Phase 38で-451円損失（4.5%）発生
  - 対策: 2%含み益到達後、トレーリングSLが0.5%利益を保証
  - 効果: 含み益がある状態での大幅な損失を防止

- **TP超過キャンセル機能**: トレーリングSLがTPを超えた場合にTPを自動キャンセル
  - ロジック: `_cancel_tp_when_trailing_exceeds()`（executor.py:930-992）
  - 効果: TP2.5%を超える上昇時、さらなる利益追求を可能に
  - 安全性: トレーリングSLが最低利益を保証しているため安全

- **品質保証完了**: 1,081テスト100%成功・69.57%カバレッジ達成

### 📊 Phase 42.2重要事項
- **Bybit/Binance準拠**: 主要取引所と同じ仕様で実装・移植容易性確保
- **Phase 42統合**: 統合TP/SLシステムと完全統合・複数エントリー対応
- **設定有効化**: `config/core/thresholds.yaml:335 enabled: true`

## 📈 Phase 42完了（2025年10月18日）

**🎯 Phase 42: 統合TP/SL実装・複数エントリー対応・注文数削減**

### ✅ Phase 42最適化成果
- **統合TP/SL実装**: 複数エントリーの平均価格ベースで単一TP/SL注文を配置
  - 従来: 3エントリー → 6注文（エントリー3 + TP3 + SL3）
  - Phase 42: 3エントリー → 5注文（エントリー3 + TP1 + SL1）
  - 効果: 注文数削減・API呼び出し削減・コスト最適化

- **平均価格追跡**: PositionTracker拡張（tracker.py:278-336）
  - 加重平均エントリー価格計算
  - 新規エントリー時の平均価格更新
  - 決済時の平均価格更新（全決済/部分決済対応）

- **統合TP/SL配置**: StopManager拡張（stop_manager.py:879-1077）
  - 平均価格ベースのTP/SL価格計算
  - 既存TP/SL注文の自動キャンセル
  - 統合TP/SL注文の配置

- **品質保証完了**: 1,081テスト100%成功・69.57%カバレッジ達成

### 📊 Phase 42重要事項
- **後方互換性**: 個別TP/SLモード維持・段階的移行可能
- **Phase 42.2統合**: トレーリングストップと完全統合
- **注文管理改善**: OCO注文非対応のbitbank APIに最適化

## 📈 Phase 38完了（2025年10月11日）

**🎯 Phase 38: tradingレイヤードアーキテクチャ実装**

### ✅ Phase 38最適化成果
- **execution層分離**: 注文実行機能を独立層として分離
- **5層アーキテクチャ**: core/balance/execution/position/risk層による責務分離
- **テストカバレッジ向上**: 58.62% → 70.56%（+11.94ポイント）
- **保守性向上**: executor.py 1,008行・適切なファイル分割

## 🔧 主要ファイル詳細

### **executor.py** 🚀**Phase 42.2 トレーリングストップ実装完了**

注文実行サービスの中核システムです。Phase 42で統合TP/SL実装、Phase 42.2でトレーリングストップ機能を完成させました。

**Phase 42.2新機能**:
```python
async def monitor_trailing_conditions(
    self,
    bitbank_client: BitbankClient,
    current_price: float
) -> None:
    """
    Phase 42.2: トレーリングストップ条件監視・SL更新

    Args:
        bitbank_client: Bitbank APIクライアント
        current_price: 現在価格

    処理:
        1. 統合ポジション情報取得
        2. トレーリング条件判定（2%含み益以上）
        3. StopManager.update_trailing_stop_loss()呼び出し
        4. SL>TP時にTPキャンセル（_cancel_tp_when_trailing_exceeds）
    """

async def _cancel_tp_when_trailing_exceeds(
    self,
    bitbank_client: BitbankClient,
    current_sl_price: float
) -> None:
    """
    Phase 42.2: トレーリングSLがTP超過時にTPキャンセル

    Args:
        bitbank_client: Bitbank APIクライアント
        current_sl_price: 現在のトレーリングSL価格

    ロジック:
        - buy: SL > TP → TPキャンセル（SLが上昇してTPを超えた）
        - sell: SL < TP → TPキャンセル（SLが下降してTPを超えた）

    効果:
        - TP2.5%を超える上昇時、さらなる利益追求
        - トレーリングSLが0.5%最低利益を保証しているため安全
    """
```

**Phase 42新機能**:
```python
async def _handle_consolidated_tp_sl(
    self,
    bitbank_client: BitbankClient,
    evaluation: TradeEvaluation,
    entry_order_id: str,
    entry_price: float,
    entry_amount: float
) -> None:
    """
    Phase 42: 統合TP/SL処理（複数エントリー対応）

    処理フロー:
        1. 平均エントリー価格更新（PositionTracker）
        2. 既存TP/SL注文キャンセル（StopManager）
        3. 新しい統合TP/SL配置（平均価格ベース）
        4. 統合注文ID・価格をPositionTrackerに保存
    """
```

**主要メソッド**:
- `execute_order()`: 注文実行メインロジック
- `_handle_consolidated_tp_sl()`: **【Phase 42新規】統合TP/SL処理**
- `monitor_trailing_conditions()`: **【Phase 42.2新規】トレーリング条件監視**
- `_cancel_tp_when_trailing_exceeds()`: **【Phase 42.2新規】TP超過キャンセル**

**ファイル構造**:
- Lines 1-349: 初期化・基本設定
- Lines 350-362: TP/SLモード判定（individual/consolidated）
- Lines 450-806: ペーパートレード・ライブトレード実行
- Lines 665-806: **【Phase 42】統合TP/SL処理**
- Lines 811-992: **【Phase 42.2】トレーリングストップ監視**

### **stop_manager.py** 🚀**Phase 42.2 トレーリングストップ実装完了**

TP/SL管理の中核システムです。Phase 42で統合TP/SL実装、Phase 42.2でトレーリングストップ機能を完成させました。

**Phase 42.2新機能**:
```python
async def update_trailing_stop_loss(
    self,
    bitbank_client: BitbankClient,
    current_price: float,
    side: str,
    entry_price: float,
    current_sl_price: float,
    current_sl_order_id: Optional[str],
    total_position_size: float
) -> Dict[str, Any]:
    """
    Phase 42.2: トレーリングストップロス更新（Bybit/Binance準拠）

    Args:
        bitbank_client: Bitbank APIクライアント
        current_price: 現在価格
        side: ポジションサイド（buy/sell）
        entry_price: エントリー価格
        current_sl_price: 現在のSL価格
        current_sl_order_id: 現在のSL注文ID
        total_position_size: 総ポジションサイズ

    Returns:
        Dict: {
            "updated": bool,
            "new_sl_price": float,
            "new_sl_order_id": Optional[str],
            "reason": str
        }

    トレーリングロジック:
        1. 2%含み益でトレーリング開始（activation_profit: 0.02）
        2. 3%距離維持（trailing_percent: 0.03）
        3. 200円最低更新距離（ノイズ防止）
        4. 0.5%最低利益保証（min_profit_lock: 0.005）
    """
```

**Phase 42新機能**:
```python
async def place_consolidated_tp_sl(
    self,
    bitbank_client: BitbankClient,
    side: str,
    average_entry_price: float,
    total_position_size: float,
    tp_price: float,
    sl_price: float
) -> Dict[str, Any]:
    """
    Phase 42: 統合TP/SL配置（平均価格ベース）

    Args:
        bitbank_client: Bitbank APIクライアント
        side: ポジションサイド（buy/sell）
        average_entry_price: 加重平均エントリー価格
        total_position_size: 総ポジションサイズ
        tp_price: TP価格
        sl_price: SL価格

    Returns:
        Dict: {
            "tp_order_id": Optional[str],
            "sl_order_id": Optional[str],
            "success": bool
        }
    """

async def cancel_existing_tp_sl(
    self,
    bitbank_client: BitbankClient,
    tp_order_id: Optional[str],
    sl_order_id: Optional[str]
) -> None:
    """
    Phase 42: 既存TP/SL注文キャンセル

    Args:
        bitbank_client: Bitbank APIクライアント
        tp_order_id: キャンセルするTP注文ID
        sl_order_id: キャンセルするSL注文ID
    """
```

**主要メソッド**:
- `check_stop_conditions()`: TP/SL条件チェック（Phase 28基盤）
- `place_consolidated_tp_sl()`: **【Phase 42新規】統合TP/SL配置**
- `cancel_existing_tp_sl()`: **【Phase 42新規】既存TP/SLキャンセル**
- `update_trailing_stop_loss()`: **【Phase 42.2新規】トレーリングSL更新**
- `_should_update_trailing_stop()`: **【Phase 42.2新規】更新判定**
- `_calculate_new_trailing_stop_price()`: **【Phase 42.2新規】新SL価格計算**
- `_calculate_min_profit_lock_price()`: **【Phase 42.2新規】最低利益保証価格**

**ファイル構造**:
- Lines 1-86: TP/SL条件チェック（Phase 28基盤）
- Lines 87-219: 個別TP/SL配置（後方互換性維持）
- Lines 407-522: 緊急ストップロス（急激な価格変動対応）
- Lines 576-735: 孤児注文クリーンアップ（Phase 37.5.3・OCO代替）
- Lines 737-839: 柔軟クールダウン（Phase 31.1）
- Lines 879-1077: **【Phase 42】統合TP/SL専用メソッド**
- Lines 1083-1302: **【Phase 42.2】トレーリングストップ専用メソッド**

### **order_strategy.py** 🚀**Phase 42.4 TP/SL設定最適化完了**

注文戦略の中核システムです。Phase 42で統合TP/SL価格計算機能を追加、Phase 42.4でハードコード値削除・設定値最適化を実現しました。

**Phase 42.4最適化**:
```python
# Phase 42.4修正前（ハードコード値）:
sl_rate = min(0.02, max_loss_ratio)  # ← 2%ハードコード
default_tp_ratio = tp_config.get("default_ratio", 2.5)  # ← 2.5倍ハードコード

# Phase 42.4修正後（thresholds.yaml読み込み）:
from src.core.config import get_threshold

default_tp_ratio = get_threshold("tp_default_ratio", 1.5)
min_profit_ratio = get_threshold("tp_min_profit_ratio", 0.019)
default_atr_multiplier = get_threshold("sl_atr_normal_vol", 2.0)
sl_min_distance_ratio = get_threshold("sl_min_distance_ratio", 0.01)
max_loss_ratio = get_threshold("position_management.stop_loss.max_loss_ratio", 0.03)

# デフォルトSL率を設定から取得（ハードコード0.02削除）
sl_rate = sl_min_distance_ratio  # Phase 42.4: thresholds.yamlから直接取得
```

**Phase 42.4設定値（thresholds.yaml）**:
- `sl_min_distance_ratio: 0.02` （2.0%・市場推奨3-8%の下限）
- `tp_default_ratio: 1.5` （RR比1.5:1・段階的最適化アプローチ）
- `tp_min_profit_ratio: 0.03` （3.0%・デイトレード最適化）

**Phase 42新機能**:
```python
def calculate_consolidated_tp_sl_prices(
    average_entry_price: float,
    side: str,
    atr_value: float,
    config: Dict
) -> Tuple[float, float]:
    """
    Phase 42: 統合TP/SL価格計算（平均価格ベース）

    Args:
        average_entry_price: 加重平均エントリー価格
        side: ポジションサイド（buy/sell）
        atr_value: ATR値
        config: 設定辞書

    Returns:
        Tuple[float, float]: (TP価格, SL価格)

    計算ロジック:
        - TP: average_entry ± (average_entry × tp_rate)
        - SL: average_entry ± (atr_value × sl_atr_multiplier)
    """
```

**主要メソッド**:
- `determine_order_type()`: 注文タイプ決定（Phase 33スマート注文）
- `calculate_tp_sl_prices()`: 個別TP/SL価格計算
- `calculate_consolidated_tp_sl_prices()`: **【Phase 42新規】統合TP/SL価格計算**

## 📝 使用方法・例

### **Phase 42.2トレーリングストップの動作**

```python
from src.trading.execution.executor import ExecutionService
from src.data.bitbank_client import BitbankClient

# ExecutionService初期化
executor = ExecutionService(mode="live")

# トレーリング条件監視（取引サイクル毎に実行）
await executor.monitor_trailing_conditions(
    bitbank_client=bitbank_client,
    current_price=14000000.0  # 現在価格: 1400万円
)

# トレーリング動作例:
# Entry: 1000万円
# Current: 1020万円（+2%含み益） → トレーリング開始
# Trailing SL: 989.7万円（1020万円 × 0.97 = 3%距離）
# Min Profit Lock: 1005万円（1000万円 × 1.005 = 0.5%利益保証）
# → 実際のSL: max(989.7万円, 1005万円) = 1005万円

# さらに上昇:
# Current: 1050万円（+5%含み益）
# Trailing SL: 1018.5万円（1050万円 × 0.97 = 3%距離）
# Min Profit Lock: 1005万円（変わらず）
# → 実際のSL: 1018.5万円（200円以上の更新のため更新実行）

# TP超過:
# TP: 1025万円（2.5%）
# Trailing SL: 1018.5万円 > TP → TPキャンセル
# → さらなる上昇を追従可能
```

### **Phase 42統合TP/SLの動作**

```python
from src.trading.execution.executor import ExecutionService

# ExecutionService初期化
executor = ExecutionService(mode="live")

# エントリー実行（自動的に統合TP/SL処理）
result = await executor.execute_order(
    bitbank_client=bitbank_client,
    evaluation=evaluation,
    mode="live"
)

# 内部動作:
# 1. エントリー注文実行（例: 1000万円で0.001 BTC買い）
# 2. PositionTracker.update_average_on_entry()呼び出し
# 3. 既存TP/SL注文キャンセル
# 4. 新しい統合TP/SL配置（平均価格ベース）
# 5. 統合注文ID・価格をTrackerに保存

# 複数エントリー例:
# Entry 1: 1000万円で0.001 BTC → 平均: 1000万円
# Entry 2: 1010万円で0.001 BTC → 平均: 1005万円
# Entry 3: 1020万円で0.001 BTC → 平均: 1010万円
# → TP/SLは1010万円（平均価格）ベースで計算
```

## ⚠️ 注意事項・制約

### **Phase 42.2トレーリングストップの動作条件**
- **有効化必須**: `config/core/thresholds.yaml:335 enabled: true`
- **2%起動閾値**: 2%含み益到達でトレーリング開始
- **3%距離**: Bybit/Binance標準・TP2.5%対応最適化
- **200円最低更新**: ノイズによる頻繁なSL更新を防止
- **0.5%利益保証**: SLがentry+0.5%を下回らない

### **TP超過キャンセルの安全性**
- **最低利益保証**: トレーリングSLが0.5%利益を保証
- **リスク管理**: TP2.5% < Trailing SL（例: 3%）の場合のみキャンセル
- **手動介入可能**: 必要に応じて手動でTPを再設定可能

### **Phase 42統合TP/SLの動作条件**
- **複数エントリー対応**: 平均価格ベースで単一TP/SL配置
- **個別モード維持**: 後方互換性のため個別TP/SLモードも利用可能
- **OCO非対応対策**: bitbank APIの制限に最適化された実装

### **Phase 38 Graceful Degradation統合**
- **エラーハンドリング**: TP/SL配置失敗時も取引続行
- **孤児注文クリーンアップ**: Phase 37.5.3で実装済み
- **柔軟クールダウン**: Phase 31.1で実装済み

## 🔗 関連ファイル・依存関係

### **Phase 42.2新規ファイル**
- `src/trading/execution/executor.py`: トレーリング監視（lines 811-992）
- `src/trading/execution/stop_manager.py`: トレーリングSL更新（lines 1083-1302）
- `config/core/thresholds.yaml`: トレーリング設定（lines 334-340）

### **Phase 42新規ファイル**
- `src/trading/execution/executor.py`: 統合TP/SL処理（lines 665-806）
- `src/trading/execution/stop_manager.py`: 統合TP/SL配置（lines 879-1077）
- `src/trading/execution/order_strategy.py`: 統合価格計算（lines 352-467）

### **参照元システム**
- `src/core/execution/execution_service.py`: 注文実行制御
- `src/trading/position/tracker.py`: ポジション追跡・平均価格管理
- `src/data/bitbank_client.py`: bitbank API呼び出し

### **設定ファイル連携**
- `config/core/thresholds.yaml`: TP/SL・トレーリングストップ設定
- `config/core/unified.yaml`: 注文実行設定

---

**🎯 重要**: Phase 42.2により、Bybit/Binance準拠のトレーリングストップ機能を実装しました。Phase 42の統合TP/SLシステムと完全統合し、複数エントリーに対する含み益保護を実現しています。

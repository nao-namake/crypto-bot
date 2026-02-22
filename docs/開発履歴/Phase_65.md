# Phase 65: ライブ取引頻度回復 + TP/SLフルカバー統合

**期間**: 2026年2月21日-22日
**状態**: Phase 65.2完了

| Sub-Phase | 内容 | 状態 |
|-----------|------|------|
| **65** | ライブ取引頻度回復（三重壁対策） | ✅ 完了 |
| **65.2** | TP/SLフルカバー統合 + Maker戦略改善 | ✅ 完了 |

---

## 背景

GCPログ72時間分析で**三重の遮断壁**を特定:

| 壁 | 内容 | 遮断率 |
|----|------|--------|
| **壁1** | 3戦略HOLD支配（ATRBased/StochasticReversal/DonchianChannelが全てHOLD） | 98.3% |
| **壁2** | min_strategy_confidence 0.250（信頼度0.246-0.248が僅差で遮断） | 75% |
| **壁3** | API遅延5000-7800ms（ccxt rateLimit 1000ms + 接続オーバーヘッド） | 100% |

---

## 対策内容

### 壁3修正: API遅延閾値緩和 + ccxtレート制限最適化

| ファイル | 変更 | 根拠 |
|---------|------|------|
| `src/trading/__init__.py` | api_latency_warning_ms: 2000→5000 | Cloud Run + ccxt rate limitingで5-8秒は正常範囲 |
| `src/trading/__init__.py` | api_latency_critical_ms: 5000→15000 | 15秒は真の異常のみ検出 |
| `src/data/bitbank_client.py` | ccxt rateLimit: 1000→200ms | bitbank APIは秒間制限ベース。200msで5回/秒に収まる |

### 壁2修正: min_strategy_confidence緩和

| ファイル | 変更 | 根拠 |
|---------|------|------|
| `config/core/thresholds.yaml` | min_strategy_confidence: 0.25→0.22 | 0.246-0.248のシグナルが通過。0.176等は引き続きフィルタ |

### 壁1修正: BBReversal再有効化 + 重み再配分

| ファイル | 変更 | 根拠 |
|---------|------|------|
| `config/core/thresholds.yaml` | tight_range BBReversal: 0.0→0.15 | Phase 62.2でBB主導ロジック変更済み。GCPログでBUY(0.550)連発確認 |
| `config/core/thresholds.yaml` | StochasticReversal: 0.35→0.30 | 再配分 |
| `config/core/thresholds.yaml` | ATRBased: 0.35→0.30 | 再配分 |
| `config/core/thresholds.yaml` | DonchianChannel: 0.30→0.25 | 再配分 |

合計重み: 0.15+0.30+0.30+0.25=1.0

### 戦略帰属バグ修正

| ファイル | 変更 | 効果 |
|---------|------|------|
| `src/strategies/base/strategy_manager.py` L330 | max()キーに重み考慮追加 | 重み0.0の戦略が帰属先にならない |
| `src/strategies/base/strategy_manager.py` L374 | 同上（_create_quorum_signal内） | 同上 |
| `src/strategies/base/strategy_manager.py` L438 | 同上（_integrate_consistent_signals内） | 同上 |

---

## 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `src/trading/__init__.py` | API遅延閾値 5000→15000ms、警告閾値 2000→5000ms |
| `src/data/bitbank_client.py` | ccxt rateLimit 1000→200ms |
| `config/core/thresholds.yaml` | min_strategy_confidence 0.25→0.22、BBReversal重み0.0→0.15 + 再配分 |
| `src/strategies/base/strategy_manager.py` | 戦略帰属バグ修正（3箇所） |
| `tests/unit/services/test_dynamic_strategy_selector.py` | tight_range重みテスト更新 |
| `CLAUDE.md` | Phase 65追加・重み記載更新 |
| `docs/開発計画/ToDo.md` | Phase 65更新 |
| `docs/開発履歴/Phase_65.md` | 新規作成 |

---

## バックテスト結果

### Phase 64 → Phase 65 比較

| 指標 | Phase 64 | Phase 65 | 変化 |
|------|---------|---------|------|
| **総取引数** | 303件 | **533件** | **+76%** |
| **勝率** | 89.2% | 85.4% | -3.8pt |
| **総損益** | ¥+102,135 | **¥+103,843** | +1.7% |
| **PF** | 2.47 | 1.87 | -24% |
| **最大DD** | ¥4,700 (0.94%) | ¥5,480 (1.07%) | +0.13pt |
| **期待値/件** | ¥+337 | ¥+195 | -42% |
| **SR** | — | 17.99 | — |

### 戦略別パフォーマンス

| 戦略 | 取引数 | 勝率 | 損益 |
|------|--------|------|------|
| **ATRBased** | 362件 | 87.0% | ¥+81,946 |
| **DonchianChannel** | 127件 | 81.9% | ¥+13,117 |
| **StochasticReversal** | 44件 | 81.8% | ¥+8,780 |

### レジーム別パフォーマンス

| レジーム | 取引数 | 勝率 | 損益 |
|---------|--------|------|------|
| tight_range | 476件 | 84.7% | ¥+87,826 |
| normal_range | 57件 | 91.2% | ¥+16,017 |

### ML予測別パフォーマンス

| ML予測 | 取引数 | 勝率 | 損益 |
|--------|--------|------|------|
| BUY | 310件 | 88.4% | ¥+75,206 |
| SELL | 149件 | 84.6% | ¥+29,051 |
| HOLD | 74件 | 74.3% | ¥-413 |

### SL決済パターン分析

| パターン | 件数 | 比率 |
|---------|------|------|
| 一直線損切り（MFE≤0） | 2件 | 2.6% |
| 微益後損切り（MFE<200） | 15件 | 19.2% |
| プラス圏経由（MFE 200-500） | 43件 | 55.1% |
| 500円以上経由 | 18件 | 23.1% |

### 評価

- **取引数+76%増加**（303→533件）: BBReversal再有効化 + min_strategy_confidence緩和の効果
- **総損益維持**: ¥+103,843（Phase 64比+1.7%）
- **PF低下は許容範囲**: 2.47→1.87（取引数増加に伴う自然な低下、1.87は十分高水準）
- **勝率85.4%**: 3.8pt低下だが85%超を維持
- **最大DD 1.07%**: Phase 64の0.94%から微増だが許容範囲内

---

## Phase 65.2: TP/SLフルカバー統合 + Maker戦略改善

**日付**: 2026年2月22日
**目的**: Phase 65デプロイ後のライブ運用で発覚した3つの問題を修正

### 背景

Phase 65デプロイ後、取引は再開されたが以下の問題を確認:

| 問題 | 内容 | 影響 |
|------|------|------|
| **TP/SLカバー率32.5%** | ポジション0.0317BTCに対しTP/SLが0.0103BTCのみ | 残り0.0214BTCがTP/SLなし |
| **500円固定TPが機能しない** | リカバリパスが%ベースTP（0.4%=42,000円幅）を使用 | 含み益1000円でもTP決済されない |
| **エントリーがTaker** | Maker戦略が0成功/1フォールバック | 往復手数料0.2%で利益が消失 |

**ライブ実例**: 含み益800円のポジションを手動決済 → 手数料715円（エントリーTaker+決済Taker+利息）→ **純利益わずか85円**

### 根本原因分析

#### 問題1+2: TP/SLカバレッジ不足

bitbankのポジション管理はエントリーを**加重平均で統合**:
```
Entry1 (0.0103BTC) → TP/SL for 0.0103BTC
Entry2 (0.0107BTC) → TP/SL for 0.0107BTC
Entry3 (0.0107BTC) → TP/SL for 0.0107BTC
bitbank上: 1ポジション 0.0317BTC / TP/SL注文3組（各エントリー分）
```

Container再起動（Phase 65デプロイ）時:
1. virtual_positionsが消失
2. position_restorerが0.0317BTCを1件のVPとして復元
3. 発見できたTP/SL注文（0.0103BTC分）のみ紐付け
4. **残り0.0214BTCがTP/SLなし**

10分定期チェック（`_place_missing_tp_sl`）の問題:
- カバー不足検出 → 全量TP/SL追加を試みる
- **既存0.0103BTC分をキャンセルしない** → TP+SL合計がポジション超過 → 50062エラー
- さらにリカバリパスは**%ベースTP**を使用（`calculate_recovery_tp_sl_prices`）で固定500円TPと乖離

#### 問題3: Maker戦略無効化

`order_strategy.py` L449の`_assess_maker_conditions()`:
- `min_spread_for_maker`のコード内デフォルト値: **0.001（0.1%=10,600円）**
- YAML設定値: **0.00002（0.002%=212円）**
- 50倍の乖離 → 設定読み込み失敗時にMakerが完全無効化
- リトライ設定も保守的（3回/500ms間隔）

### 修正内容

#### TP/SL統合再配置（`tp_sl_manager.py`）

**設計方針**: Phase 42-43で「統合TP/SL」を実装→複雑化して失敗→Phase 46で全削除(-1,172行)した経緯あり。今回は既存の10分定期チェック機構内に最小限の修正を加え、新たな統合ポイント（executor.py等）は追加しない。

| 変更箇所 | 内容 |
|---------|------|
| `ensure_tp_sl_for_existing_positions` | `already_restored`早期リターン廃止 → カバレッジ不足時に必ず修復実行 |
| `ensure_tp_sl_for_existing_positions` | 統合再配置前にサイドの全VPを削除（新VP追加のため） |
| `_place_missing_tp_sl` Step 0追加 | 既存部分TP/SL注文を全キャンセル → 50062エラー回避 |
| `_place_missing_tp_sl` TP計算 | 固定500円TP設定時はリカバリでも固定額計算を使用 |
| `_cancel_partial_exit_orders()` 新規 | 決済方向の全注文をキャンセル（limit/take_profit/stop/stop_limit/stop_loss対象） |
| `_is_fixed_amount_tp_enabled()` 新規 | 固定金額TPモード判定 |
| `_calculate_fixed_amount_tp_for_position()` 新規 | 統合ポジション向け固定500円TP価格計算（手数料考慮） |

**フロー改善**:
```
Before: カバー不足検出 → 部分注文残存のまま全量追加 → 50062エラー or 過剰注文
After:  カバー不足検出 → 部分注文全キャンセル → 全量TP/SL統合配置 → 新VP作成
```

#### Maker戦略改善

| ファイル | 変更 | 効果 |
|---------|------|------|
| `src/trading/execution/order_strategy.py` L449 | `min_spread_for_maker`デフォルト値 0.001→0.00002 | YAML設定と一致、設定読み込み失敗時もMaker有効 |
| `config/core/thresholds.yaml` | `max_retries`: 3→5 | リトライ回数増加 |
| `config/core/thresholds.yaml` | `retry_interval_ms`: 500→200 | 高速リトライ |

### 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `src/trading/execution/tp_sl_manager.py` | `ensure_tp_sl_for_existing_positions`改修 + `_place_missing_tp_sl`改修 + 新メソッド3件追加 |
| `src/trading/execution/order_strategy.py` | `min_spread_for_maker`デフォルト値修正（0.001→0.00002） |
| `config/core/thresholds.yaml` | Maker retry設定改善（max_retries 3→5、interval 500→200ms） |
| `tests/unit/trading/execution/test_tp_sl_manager.py` | 3テストに`fetch_active_orders`モック追加 |

### 設計判断: executor.pyへの統合チェック追加を見送り

当初計画では`executor.py`の`_execute_live_trade()`末尾にTP/SL統合チェックを追加予定だった。しかし:

| 観点 | 判断 |
|------|------|
| **Phase 42-43の教訓** | 同様の統合ポイント追加が+324行→executor.py肥大化→Phase 46で全削除 |
| **状態管理の複雑化** | executor内で統合管理するとvirtual_positions整合性問題が再発 |
| **既存機構で十分** | 10分定期チェックで同じ修復が実行される（最大10分の遅延は許容） |
| **最小変更原則** | 既存フロー内の修正に留め、新たな呼び出し経路を追加しない |

### 期待される改善

| 指標 | 修正前 | 修正後（期待値） |
|------|--------|-----------------|
| TP/SLカバー率 | 32.5% | **>95%** |
| 固定500円TP | リカバリ時に%ベース | **リカバリ時も500円固定** |
| Maker成功率 | 0% | **>50%** |
| 往復手数料（TP決済時） | 0.2%（両方Taker） | **0%（両方Maker）** |

### 品質チェック結果

```
pytest: 1752 passed, 1 skipped
Coverage: 71.79%
flake8: PASS
black: PASS
isort: PASS
ML validation: PASS
System integrity: PASS (6 items)
```

### 検証手順

```bash
# デプロイ後
python3 scripts/live/standard_analysis.py

# 確認事項:
# - TP/SLカバー率 > 95%
# - Maker成功率 > 0%（エントリー・TP決済）
# - 固定500円TPが復旧パスでも正しく配置される
# - 50062エラーがログに出ない
```

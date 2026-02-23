# Phase 65: ライブ取引頻度回復 + TP/SLフルカバー統合

**期間**: 2026年2月21日-24日
**状態**: Phase 65.12完了

| Sub-Phase | 内容 | 状態 |
|-----------|------|------|
| **65** | ライブ取引頻度回復（三重壁対策） | ✅ 完了 |
| **65.2** | TP/SLフルカバー統合 + Maker戦略改善 | ✅ 完了 |
| **65.3** | config/core 設定ファイル整理（3→2ファイル体系） | ✅ 完了 |
| **65.4** | NoneType安全性修正 + INACTIVE対応 | ✅ 完了 |
| **65.5** | execution/ 包括的コードレビュー（バグ修正19箇所 + 重複統合3箇所） | ✅ 完了 |
| **65.6** | position/ 包括的コードレビュー（バグ修正3箇所 + 重複統合1箇所） | ✅ 完了 |
| **65.7** | risk/ 包括的コードレビュー（バグ修正2箇所） | ✅ 完了 |
| **65.8** | balance/ 包括的コードレビュー（変更不要） | ✅ 完了 |
| **65.9** | core/ 包括的コードレビュー（変更不要） | ✅ 完了 |
| **65.10** | strategies.yaml 整理 + config/core/ 移動 | ✅ 完了 |
| **65.11** | strategies.yaml → thresholds.yaml 統合（設定3→2ファイル完全移行） | ✅ 完了 |
| **65.12** | unified.yaml → thresholds.yaml 統合（設定2→1ファイル完全移行） | ✅ 完了 |

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

---

## Phase 65.3: config/core 設定ファイル整理

**日付**: 2026年2月22日
**目的**: 設定ファイルを3ファイル→2ファイル体系に統合し、保守性を向上

### 背景

config/core に設定ファイルが分散し、以下の問題があった:

| 問題 | 内容 |
|------|------|
| **features.yaml冗長** | 291行中、コード参照箇所はわずか3-4箇所。大半がドキュメント/note |
| **同名セクション分散** | unified.yaml と thresholds.yaml で ml/risk/execution 等が重複 |
| **古いコメント蓄積** | thresholds.yaml に Phase 40-61 のロールバック履歴が残存 |
| **未使用設定残存** | Optunaセクション（~80行）、Stacking定義等がコード未参照のまま存在 |

### 変更内容

#### features.yaml → thresholds.yaml 統合（features.yaml 削除）

| 変更 | 内容 |
|------|------|
| thresholds.yaml に `feature_flags:` セクション追加 | features.yaml のトグル設定を移植 |
| `get_features_config()` 変更 | `get_threshold("feature_flags", {})` ラッパーに変更 |
| `_features_config_cache` 削除 | threshold_manager のキャッシュ機構を使用 |
| features.yaml 削除 | 291行削除 |

呼び出し元（cooldown.py, strategy_manager.py, backtest_runner.py）は**変更不要**。

#### unified.yaml スリム化（266行→97行）

| 残した設定（環境・構造） | 移動した設定（パラメータ系） |
|------------------------|--------------------------|
| mode, mode_balances | ml（ensemble_weights等） |
| exchange, data | risk（position_limits等） |
| cloud_run, security | execution, production |
| trading_constraints | reporting, logging, monitoring |

#### thresholds.yaml 整理

| 変更 | 削減量 |
|------|--------|
| Optunaセクション削除（コード未参照） | ~80行 |
| Phase 40-61 ロールバック詳細コメント削除 | ~40行 |
| 未使用設定削除（position_sizing.stop_loss_rate等） | ~5行 |
| unified.yaml からの移動設定追加 | +120行 |

#### その他

| ファイル | 変更 |
|---------|------|
| feature_order.json | Stacking定義削除、メタ情報更新（640→578行） |
| README.md | Phase 65.3対応に全面書き換え（471→153行） |
| CLAUDE.md | 3層設定体系→2層設定体系に更新 |
| checks.sh | features.yaml参照削除、unified.yaml必須フィールド変更 |

### 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `config/core/thresholds.yaml` | feature_flags追加 + unified.yaml移動 + 古い設定/コメント削除 |
| `config/core/features.yaml` | **削除** |
| `config/core/unified.yaml` | 環境・構造設定のみに縮小（266→97行） |
| `config/core/feature_order.json` | Stacking定義削除 + メタ情報更新 |
| `config/core/README.md` | Phase 65.3対応に全面更新 |
| `src/core/config/__init__.py` | `get_features_config()` を `get_threshold()` ラッパーに変更 |
| `src/core/execution/backtest_runner.py` | コメント更新 |
| `src/trading/__init__.py` | コメント更新 |
| `src/trading/position/cooldown.py` | コメント更新 |
| `scripts/testing/checks.sh` | features.yaml参照削除 + 必須フィールド更新 |
| `CLAUDE.md` | 2層設定体系に更新 |

### 数値サマリー

| 指標 | Before | After | 削減 |
|------|--------|-------|------|
| 設定ファイル数 | 3 | **2** | -1 |
| features.yaml | 291行 | **0（削除）** | -291行 |
| unified.yaml | 266行 | **97行** | -169行 |
| thresholds.yaml | 1,101行 | **906行** | -195行 |
| 合計（3ファイル） | 1,658行 | **1,003行** | **-655行（-39%）** |

### 品質チェック結果

```
pytest: 1752 passed, 1 skipped
Coverage: 71.77%
flake8: PASS
black: PASS
isort: PASS
ML validation: PASS
System integrity: PASS (5 items)
```

---

## Phase 65.4: NoneType安全性修正 + INACTIVE対応

**日付**: 2026年2月22日
**目的**: ライブ運用中のNoneTypeクラッシュ修正 + bitbank INACTIVE状態対応

### 修正内容

| ファイル | 変更 |
|---------|------|
| `src/trading/execution/tp_sl_manager.py` | VP追跡でTP/SLカバレッジ補完（INACTIVE注文対応） |
| `src/trading/execution/stop_manager.py` | INACTIVE状態をstop_limit正常状態として認識 |
| `config/core/thresholds.yaml` | `min_spread_for_maker: 0`（post_only保護でチェック不要に） |

---

## Phase 65.5: execution/ 包括的コードレビュー

**日付**: 2026年2月23日
**目的**: Phase 65.4を機にexecution/フォルダ全5ファイルを包括レビュー。バグ修正19箇所 + 重複統合3箇所。

### バグ修正（A-I: 19箇所）

| ID | 重要度 | 内容 | ファイル |
|----|--------|------|---------|
| **A** | CRITICAL | `"recovered": True` → `"restored": True` に統一（保護対象チェック不一致） | tp_sl_manager.py |
| **B** | CRITICAL | 孤児スキャンの `avg_price` → `average_price` キー修正（bitbank API準拠） | position_restorer.py |
| **C** | HIGH | ExecutionResult 必須引数 `mode` 欠落追加 | executor.py |
| **D** | HIGH | TP/SL再計算失敗時に `order_id=None` → `result.order_id` + 約定情報保持 | executor.py |
| **E** | HIGH | `place_stop_loss` ブロッキング呼び出しを `await asyncio.to_thread()` でラップ | tp_sl_manager.py |
| **F** | HIGH | NoneType安全性パターン残存8箇所を `or 0` パターンに統一 | 全5ファイル |
| **G** | MEDIUM | `stop_loss=None` 時の f-string クラッシュ修正 | stop_manager.py |
| **H** | MEDIUM | `except Exception: pass` ログなし握りつぶし2箇所にログ追加 | executor.py, stop_manager.py |
| **I** | LOW | 未使用 import 4箇所削除 | executor.py, stop_manager.py |

### 重複統合（J-L: 3箇所）

| ID | 内容 | 統合先 |
|----|------|--------|
| **J** | 保護対象注文ID収集ロジック統合 | `PositionRestorer.collect_protected_order_ids()` |
| **K** | `_mark_orphan_sl` を PositionRestorer に移動 | `PositionRestorer.mark_orphan_sl()` |
| **L** | `_execute_position_exit` の PnL計算を `_calc_pnl` に統合 | `StopManager._calc_pnl()` |

### 修正ファイル一覧

| ファイル | 修正内容 |
|---------|---------|
| `src/trading/execution/executor.py` | C, D, F×1, H×1, I×2 |
| `src/trading/execution/order_strategy.py` | F×3 |
| `src/trading/execution/stop_manager.py` | F×1, G, H×1, I×2, K(呼び出し変更), L |
| `src/trading/execution/tp_sl_manager.py` | A, E, F×1, J(呼び出し変更) |
| `src/trading/execution/position_restorer.py` | B×3, F×1, J(ヘルパー追加), K(メソッド受入れ) |

---

## Phase 65.6: position/ 包括的コードレビュー

**日付**: 2026年2月23日
**目的**: execution/レビュー（Phase 65.5）に続き、position/フォルダ（5ファイル・1,365行）を包括レビュー。バグ修正3箇所 + 重複統合1箇所。

### レビュー結果サマリー

| ファイル | 行数 | 状態 |
|---------|------|------|
| `__init__.py` | 17 | OK — 変更不要 |
| `cleanup.py` | 321 | D: 重複ロジック1箇所 |
| `cooldown.py` | 178 | OK — 変更不要 |
| `limits.py` | 379 | A: 例外握りつぶし, B: 脆弱モード判定 |
| `tracker.py` | 470 | C: 末尾デッドコメント |

### バグ修正（A-C: 3箇所）

| ID | 重要度 | 内容 | ファイル |
|----|--------|------|---------|
| **A** | MEDIUM | `except Exception: continue` にログ追加（タイムスタンプパース失敗） | limits.py |
| **B** | HIGH | 残高ベース脆弱モード判定を `mode` パラメータ伝搬に変更 | limits.py, executor.py |
| **C** | LOW | 末尾デッドコメント4行削除 | tracker.py |

### 重複統合（D: 1箇所）

| ID | 内容 | 統合先 |
|----|------|--------|
| **D** | TP/SL注文キャンセルロジック（cleanup_orphaned + emergency_cleanup） | `PositionCleanup._cancel_position_orders()` |

### 修正ファイル一覧

| ファイル | 修正内容 |
|---------|---------|
| `src/trading/position/limits.py` | A（例外ログ追加）, B（mode パラメータ追加） |
| `src/trading/position/cleanup.py` | D（`_cancel_position_orders` ヘルパー抽出） |
| `src/trading/position/tracker.py` | C（デッドコメント削除） |
| `src/trading/execution/executor.py` | B（`mode=self.mode` 引数追加） |
| `tests/unit/trading/position/test_limits.py` | B（テスト更新: mode引数対応 + フォールバックテスト追加） |

---

## Phase 65.7: risk/ 包括的コードレビュー

**日付**: 2026年2月23日
**目的**: execution/（65.5）→ position/（65.6）に続き、risk/フォルダ（6ファイル・2,355行）を包括レビュー。バグ修正2箇所。

### レビュー結果サマリー

| ファイル | 行数 | 状態 |
|---------|------|------|
| `__init__.py` | 30 | OK — 変更不要 |
| `anomaly.py` | 267 | OK — 変更不要 |
| `drawdown.py` | 308 | OK — 変更不要 |
| `kelly.py` | 562 | A: max_order_size デフォルト値不整合2箇所 |
| `manager.py` | 882 | B: 残高ベース脆弱モード判定（limits.pyと同パターン） |
| `sizer.py` | 306 | OK — 変更不要 |

確認済み（問題なし）:
- 未使用import: なし
- NoneType安全性: 全パターン正しい（`or 0` / `.get()` 使用済み）
- ハードコード値: `get_threshold()` を28箇所以上で使用（適切）
- async/await: 正しく使用（manager.py全async処理にawait適切）
- bitbank APIキー名: risk/はAPI直接呼び出しなし（安全）
- 例外処理: bare except なし、全23箇所で `except Exception as e:` + ログ
- 重複ロジック: 許容範囲（max_order_size取得の重複はあるが、各メソッドの独立性を維持する方が保守的に安全）

### バグ修正（A-B: 2箇所）

| ID | 重要度 | 内容 | ファイル |
|----|--------|------|---------|
| **A** | MEDIUM | `max_order_size` デフォルト値 0.02 → 0.03 に統一（他3箇所と一致） | kelly.py |
| **B** | HIGH | 残高ベース脆弱モード判定を `self.mode` 直接使用に変更（Phase 65.6 limits.pyと同パターン） | manager.py |

### 修正ファイル一覧

| ファイル | 修正内容 |
|---------|---------|
| `src/trading/risk/kelly.py` | A: L316, L339 のデフォルト値 0.02 → 0.03 |
| `src/trading/risk/manager.py` | B: L460-465 を `mode = self.mode` に置換 |

---

## Phase 65.8: balance/ 包括的コードレビュー

**日付**: 2026年2月23日
**目的**: execution/（65.5）→ position/（65.6）→ risk/（65.7）に続き、balance/フォルダ（2ファイル・473行）を包括レビュー。変更不要。

### レビュー結果サマリー

| ファイル | 行数 | 状態 |
|---------|------|------|
| `__init__.py` | 11 | OK — 変更不要 |
| `monitor.py` | 462 | OK — 変更不要 |

### 確認済み項目（全て問題なし）

- 未使用import: なし
- NoneType安全性: 全パターン正しい（`.get()` / `is not None` / `or 0` 使用済み）
- ハードコード値: `get_threshold()` を12箇所で使用（適切）
- デフォルト値不整合: なし（`balance_alert.min_required_margin` 14000.0 が2箇所で一致）
- 残高ベース脆弱モード判定: なし（`mode` パラメータを直接受取り）
- async/await: 全5箇所で正しく `await` 使用
- bitbank APIキー名: `fetch_margin_status()` / `has_open_positions()` で適切
- 例外処理: bare except なし、全3箇所で `except Exception as e:` + ログ出力
- 重複ロジック: threshold取得が3メソッドで重複するが、各メソッドが異なる閾値を異なる目的で使用しており独立性維持が妥当
- デッドコード: なし
- 型安全性: f-string内で全てfloat保証済み

### 検討して問題なしと判断した点

**`get_margin_status()` に `critical_threshold` がない件**:
- `_get_recommendation()` と `should_warn_user()` は `critical_threshold=80.0` を取得
- `get_margin_status()` は取得していない（else節で < 100 は全てCRITICAL）
- MarginStatus enumに80%と100%の区別がない（CRITICAL一種のみ）ため、取得しても未使用コードになる
- 現在の実装が正しい

### 修正ファイル

ソースコード変更なし。ドキュメント更新のみ。

---

## Phase 65.9: core/ 包括的コードレビュー

**日付**: 2026年2月23日
**目的**: execution/（65.5）→ position/（65.6）→ risk/（65.7）→ balance/（65.8）に続き、core/フォルダ（3ファイル・265行）を包括レビュー。データクラスとenumのみの純粋な型定義フォルダであり、変更不要。

### レビュー結果サマリー

| ファイル | 行数 | 状態 |
|---------|------|------|
| `__init__.py` | 36 | OK — 変更不要（re-export のみ） |
| `enums.py` | 57 | OK — 変更不要（4 enum 定義） |
| `types.py` | 175 | OK — 変更不要（6 dataclass 定義） |

### 確認済み項目（全て問題なし）

- 未使用import: なし（全import使用済み）
- NoneType安全性: `PositionFeeData.from_api_response()` で `.get(key, 0) or 0` の二重ガード使用（適切）
- ハードコード値: データクラスのデフォルト値のみ（`get_threshold()` 対象外）
- デフォルト値不整合: なし
- async/await: なし（データクラスのみ、ロジックなし）
- bitbank APIキー名: 直接API呼び出しなし（安全）
- 例外処理: なし（データクラスに例外処理不要）
- デッドコード: なし（`TradeEvaluation.action` プロパティはテストで使用確認済み）
- 重複ロジック: なし
- 型安全性: f-string なし、算術演算なし

### 検討して問題なしと判断した点

**`ExecutionResult.timestamp: datetime = None`（L69）**:
- 型アノテーション上は `datetime` だがデフォルト値が `None`
- `__post_init__`（L82-84）で `None` の場合 `datetime.now()` を自動設定 → ランタイムで必ず datetime になる
- `Optional[datetime]` に変更すると「None かもしれない」と誤解を招く（実際は常に datetime）
- プロジェクトで mypy/pyright 未使用のため型チェッカー問題は発生しない
- 現在の実装が正しい

**`MarginData.timestamp: datetime = None`（L114）**:
- 同パターンだが `__post_init__` なし
- 唯一の生成箇所（`balance/monitor.py`）で常に `datetime.now()` を明示的に渡している
- ランタイムで None になるパスが存在しない
- 現在の実装で問題なし

**`TradeEvaluation.strategy_name` のフィールド順序（L43）**:
- `str = "unknown"` が Optional フィールド群の間に位置（慣例と異なる）
- Python dataclass として正常動作（全てデフォルト値あり）
- フィールド順変更は既存の全呼び出し箇所に影響する可能性あり
- スタイル問題のみ、変更不要

### 修正ファイル

ソースコード変更なし。ドキュメント更新のみ。

---

## Phase 65.10: strategies.yaml 整理 + config/core/ 移動

**日付**: 2026年2月23日
**目的**: Phase 65.3の設定ファイル整理に続き、`config/strategies.yaml`を整理して`config/core/`に移動。設定ファイルを`config/core/`に集約。

### 背景

`config/strategies.yaml`（161行）の調査で、**32フィールド中6フィールドのみ**がコードで使用されていることが判明。4つのセクション（計16フィールド）は完全に未参照。

### 変更内容

#### strategies.yaml 整理（161行→73行）

**削除対象:**
- トップレベル: `last_updated`, `phase`（コード未参照）
- 各戦略から: `indicators`, `description`, `config_section`（未使用）
- `integration` セクション全体（5フィールド）
- `ml_features` セクション全体（3フィールド）
- `management` セクション全体（5フィールド）
- `logging` セクション全体（3フィールド）
- 末尾コメントブロック

**保持対象（各戦略7フィールド）:**
- `enabled`, `class_name`, `module_path`, `strategy_type`, `weight`, `priority`, `regime_affinity`
- `strategy_system_version`（ログで使用）

#### ファイル移動

```
config/strategies.yaml → config/core/strategies.yaml
```

### 修正ファイル一覧

| ファイル | 修正内容 |
|---------|---------|
| `config/strategies.yaml` | 整理（161→73行）+ `config/core/` に移動 |
| `src/strategies/strategy_loader.py` | デフォルトパス + metadata 簡素化 + docstring |
| `src/core/orchestration/orchestrator.py` | パス文字列更新 |
| `scripts/ml/create_ml_models.py` | パス文字列更新 |
| `scripts/testing/checks.sh` | パス + メッセージ更新 |
| `scripts/testing/validate_ml_models.py` | パス + メッセージ更新 |
| `tests/unit/strategies/test_strategy_loader.py` | アサーション更新 |
| `src/core/services/dynamic_strategy_selector.py` | docstring更新 |
| `src/features/feature_generator.py` | docstring更新 |
| `src/features/__init__.py` | docstring更新 |
| `src/features/README.md` | パス更新 |
| `scripts/testing/README.md` | パス更新 |
| `docs/運用ガイド/システムリファレンス.md` | パス更新（4箇所） |
| `docs/運用ガイド/統合運用ガイド.md` | パス更新（2箇所） |
| `CLAUDE.md` | しおり更新 |

### 数値サマリー

| 指標 | Before | After |
|------|--------|-------|
| strategies.yaml 行数 | 161行 | 73行（**-55%**） |
| 使用フィールド数 | 6/32 | 6/6（未使用26削除） |
| 未使用セクション | 4 | 0 |
| ファイル場所 | `config/` | `config/core/`（統一） |

---

## Phase 65.11: strategies.yaml → thresholds.yaml 統合

**日付**: 2026年2月23日
**目的**: strategies.yaml を thresholds.yaml に統合し、設定ファイルを3→2体系に完全移行。戦略追加時の編集ファイルを2→1に削減。

### 背景

Phase 65.10 で strategies.yaml を整理・`config/core/` に移動したが、thresholds.yaml にも同じ6戦略の `strategies:` セクションがあり、**同一戦略の設定が2ファイルに分散**していた。

### 変更内容

#### thresholds.yaml: 戦略定義フィールドをマージ

各戦略エントリの先頭に定義フィールド7個（enabled, class_name, module_path, strategy_type, weight, priority, regime_affinity）を追加。`strategy_system_version` をトップレベルに追加。

#### strategy_loader.py: リファクタ

| 変更 | 内容 |
|------|------|
| `__init__` | `config_path` 引数削除。`Path` / `yaml` import 不要に |
| `_load_config()` | `yaml.safe_load()` → `get_all_thresholds()` 経由に変更 |
| `_load_strategy()` | `_get_strategy_thresholds()` 呼び出し削除。`strategy_config` をそのまま渡す |
| `_get_strategy_thresholds()` | メソッド削除 |

#### strategies.yaml 削除

`config/core/strategies.yaml` を削除。

### 修正ファイル一覧

| ファイル | 修正内容 |
|---------|---------|
| `config/core/thresholds.yaml` | `strategy_system_version` 追加 + 各戦略に定義フィールド追加 |
| `config/core/strategies.yaml` | **削除** |
| `src/strategies/strategy_loader.py` | リファクタ（config_path廃止・get_all_thresholds使用・_get_strategy_thresholds削除） |
| `src/core/orchestration/orchestrator.py` | `StrategyLoader()` 引数削除 |
| `scripts/ml/create_ml_models.py` | 同上 |
| `scripts/testing/checks.sh` | thresholds.yaml から戦略読み込みに変更 |
| `scripts/testing/validate_ml_models.py` | 同上 |
| `tests/unit/strategies/test_strategy_loader.py` | 全テスト書き換え（get_all_thresholds モック方式） |
| `src/features/feature_generator.py` | docstring更新 |
| `src/features/__init__.py` | docstring更新 |
| `src/features/README.md` | パス更新 |
| `src/core/services/dynamic_strategy_selector.py` | docstring更新 |
| `scripts/testing/README.md` | パス更新 |
| `docs/運用ガイド/システムリファレンス.md` | パス・記述更新 |
| `docs/運用ガイド/統合運用ガイド.md` | パス更新 |
| `CLAUDE.md` | しおり + 設定体系更新 |
| `docs/開発履歴/Phase_65.md` | Phase 65.11 追記 |

### 数値サマリー

| 指標 | Before | After |
|------|--------|-------|
| 設定ファイル数 | 3（unified + thresholds + strategies） | **2（unified + thresholds）** |
| 戦略追加時の編集ファイル | 2 | **1** |
| strategy_loader.py 行数 | ~299行 | ~252行 |

### 検証結果

#### 品質チェック（checks.sh 全12項目PASS）

| チェック項目 | 結果 |
|---|---|
| [4/12] 戦略整合性検証 | ✅ thresholds.yaml から6戦略読み込み成功 |
| [7/12] ML検証 | ✅ 55特徴量・3クラス分類 |
| [8-10/12] flake8/isort/black | ✅ PASS |
| [11/12] pytest | ✅ 1750件成功（test_strategy_loader.py 17件含む） |
| [12/12] カバレッジ | ✅ 71.59% |

#### 修正漏れチェック（全項目クリーン）

| 検索パターン | 結果 |
|---|---|
| `strategies.yaml` 参照（コード・スクリプト・設定） | ゼロ（歴史的記録のみ） |
| `StrategyLoader()` 引数付き呼び出し | ゼロ（全25箇所が引数なし） |
| `_get_strategy_thresholds()` 参照 | ゼロ |
| `config_path` 関連（strategy_loader） | ゼロ |
| CI/Dockerfile/ワークフロー内参照 | ゼロ |

---

## Phase 65.12: unified.yaml → thresholds.yaml 統合（設定2→1ファイル完全移行）

**日付**: 2026年2月24日
**目的**: unified.yaml（環境設定7セクション）をthresholds.yamlに統合し、設定管理を完全1ファイル体系に移行

### 背景

Phase 65.11で3→2ファイル体系を完了したが、unified.yaml（98行・7キー）とthresholds.yaml（967行・26キー）はトップレベルキーの重複がゼロで、実行時に`load_thresholds()`が両ファイルをdeep mergeして1つの辞書として使用しており、分離する実質的メリットがなかった。

### 変更内容

| ファイル | 変更 |
|---------|------|
| `config/core/thresholds.yaml` | unified.yamlの7セクション（mode/mode_balances/exchange/data/cloud_run/security/trading_constraints）を先頭に統合 |
| `config/core/unified.yaml` | **削除** |
| `src/core/config/threshold_manager.py` | unified.yaml読み込み・deep mergeロジック削除。thresholds.yaml単一読み込みに簡素化 |
| `src/core/config/__init__.py` | load_from_file()の二重読み込み解消。load_thresholds()結果をそのまま使用 |
| `main.py` | デフォルトconfigパス → thresholds.yaml |
| `scripts/deployment/docker-entrypoint.sh` | configパス → thresholds.yaml |
| `scripts/testing/checks.sh` | unified.yaml検証削除、thresholds.yaml必須フィールドにmode/exchange/data追加 |
| `scripts/ml/create_ml_models.py` | パス更新 |
| `scripts/analysis/unified_strategy_analyzer.py` | パス更新 |
| `scripts/backtest/walk_forward_validation.py` | パス更新 |
| `src/core/execution/live_trading_runner.py` | パス更新 |
| `.github/workflows/walk_forward.yml` | git checkoutパス簡素化 |
| テスト3ファイル | パス更新 |
| ドキュメント5ファイル | 設定体系の記述更新 |

### 数値サマリー

| 指標 | Before | After |
|------|--------|-------|
| 設定ファイル数 | 2 | **1** |
| unified.yaml | 98行 | **0（削除）** |
| thresholds.yaml | 967行 | **~1,060行** |
| load_thresholds() | 2ファイル読み込み+deep merge | **1ファイル直接読み込み** |

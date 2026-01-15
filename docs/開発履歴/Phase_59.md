# Phase 59: 戦略改善・信頼度修正期

**期間**: 2026年1月13日
**目的**: Phase 58.6バックテスト分析に基づく戦略最適化

---

## 概要

Phase 58.5/58.6のTP/SL変更後のバックテスト分析により、戦略とML信頼度設定を最適化。
BBReversal改修と信頼度逆転問題の修正を実施。

---

## 分析結果（Phase 58.6バックテスト）

### 全体パフォーマンス

| 指標 | Phase 58.4 | Phase 58.6 | 改善率 |
|------|-----------|-----------|--------|
| 総損益 | ¥+23,073 | ¥+35,105 | +52% |
| PF | 1.18 | 1.38 | +17% |
| 勝率 | 44.7% | 50.9% | +6.2pt |
| 取引数 | 501件 | 589件 | +18% |

### 戦略別パフォーマンス（Phase 58.6）

| 戦略 | 取引数 | 勝率 | 損益 | 状態 |
|------|--------|------|------|------|
| ATRBased | 320 | 54.1% | +¥29,192 | 最優秀 |
| DonchianChannel | 110 | 49.1% | +¥6,711 | 黒字化 |
| StochasticDivergence | 98 | 47.0% | +¥1,533 | 安定 |
| MACDEMACrossover | 47 | 46.8% | -¥1,000 | 微損 |
| BBReversal | 14 | 50.0% | -¥1,331 | 要改修 |

### TP/SL変更の効果

| 戦略 | 変更前勝率 | 変更後勝率 | 変更前損益 | 変更後損益 |
|------|-----------|-----------|-----------|-----------|
| BBReversal | 8.3% | 50.0% | ¥-5,451 | ¥-1,331 |
| DonchianChannel | 42.0% | 49.1% | ¥-3,560 | ¥+6,711 |
| ATRBased | 47.0% | 54.1% | ¥+13,000 | ¥+29,192 |

---

## Phase 59.1: BBReversal normal_range無効化

### 背景

BBReversalのレジーム別パフォーマンス分析：

| レジーム | 取引数 | 勝率 | 損益 | 判断 |
|---------|--------|------|------|------|
| tight_range | 12件 | 58.3% | +¥379 | 維持 |
| normal_range | 2件 | 0% | -¥1,710 | 無効化 |

**根本原因**: normal_rangeで2件中2件がSL発動（100%敗北）

### 実装内容

```yaml
# config/core/thresholds.yaml
dynamic_strategy_selection:
  regime_strategy_mapping:
    normal_range:
      ATRBased: 0.50            # 0.40→0.50（主力強化）
      BBReversal: 0.0           # 0.25→0.0（無効化）
      StochasticReversal: 0.30  # 0.25→0.30
      DonchianChannel: 0.20     # 0.10→0.20（黒字化）
```

### 期待効果

- BBReversal損益改善: +¥1,710
- BBReversal損益: ¥-1,331 → ¥+379

---

## Phase 59.2: 信頼度逆転問題修正

### 背景

| 信頼度帯 | 取引数 | 勝率 |
|---------|--------|------|
| 低（<50%） | 136件 | 51.5% |
| 高（≥65%） | 44件 | 45.5% |

**問題**: 高信頼度帯の勝率が低信頼度帯より低い逆転現象

### 原因分析

```yaml
# 変更前の設定
ml_integration:
  disagreement_penalty: 0.96   # 弱すぎる（4%減）
  agreement_bonus: 1.18        # 強すぎる（18%増）
```

高信頼度時にMLを過信してポジションサイズ増加 → 負け時の損失拡大

### 実装内容

```yaml
# config/core/thresholds.yaml
regime_ml_integration:
  tight_range:
    high_confidence_threshold: 0.70   # 0.60→0.70
    agreement_bonus: 1.10             # 1.18→1.10
    disagreement_penalty: 0.80        # 0.96→0.80

  normal_range:
    high_confidence_threshold: 0.65   # 0.55→0.65
    agreement_bonus: 1.10             # 1.22→1.10
    disagreement_penalty: 0.80        # 0.96→0.80
```

### 期待効果

- 高信頼度帯の勝率改善（45.5% → 50%+）
- PF改善: 1.38 → 1.42+

---

## DonchianChannel（対応不要・計画撤回）

### 旧計画との差異

| 項目 | 旧計画（Phase 58.4時点） | 新分析（Phase 58.6） |
|------|------------------------|---------------------|
| 勝率 | 42.0% | 49.1% |
| 損益 | ¥-3,560 | ¥+6,711 |
| 判断 | 無効化予定 | **維持** |

**結論**: TP/SL変更により黒字化。無効化計画を撤回。

---

## バックテスト結果（Phase 59.1-59.2）

**実行**: GitHub Actions（run ID: 20954469350）
**完了**: 2026年1月14日

### 全体パフォーマンス

| 指標 | Phase 58.6 | Phase 59 | 改善 |
|------|-----------|----------|------|
| 総損益 | ¥+35,105 | **¥+35,955** | **+¥850 (+2.4%)** |
| PF | 1.38 | **1.39** | **+0.01** |
| 勝率 | 50.9% | 50.9% | ±0% |
| 最大DD | - | 1.55% | - |

### 戦略別パフォーマンス

| 戦略 | 取引数 | 勝率 | 損益 |
|------|--------|------|------|
| ATRBased | 321件 | 54.2% | ¥+30,381 |
| DonchianChannel | 110件 | 49.1% | ¥+6,711 |
| StochasticReversal | 71件 | 42.3% | ¥+179 |
| ADXTrendStrength | 75件 | 48.0% | ¥+15 |
| BBReversal | 14件 | 50.0% | ¥-1,330 |

### 信頼度逆転問題（未解決）

| 指標 | Phase 58.6 | Phase 59 |
|------|-----------|----------|
| 高信頼度勝率（≥65%） | 45.5% | 45.5% |
| 低信頼度勝率（<50%） | 51.5% | 51.6% |

**結論**: Phase 59.2のpenalty/bonus調整では信頼度逆転問題は解消しなかった

---

## Phase 59.3: adjusted_confidence記録修正

### サマリー

| 項目 | 内容 |
|------|------|
| 目的 | バックテスト統計でadjusted_confidence（調整済み信頼度）を正しく記録 |
| 問題 | 統計記録が生のML確率を使用 → penalty/bonus効果が見えなかった |
| 解決 | 6ファイル修正でadjusted_confidenceを記録パスに追加 |
| 結果 | ✅ 信頼度逆転問題の解消を確認（高信頼度帯61-67% > 低信頼度帯48.5%） |

### 背景

Phase 59.2で信頼度逆転問題が解消しなかった原因を調査。

### 根本原因

| 層 | 処理内容 | 記録される値 |
|---|---|---|
| 取引判断 | adjusted_confidence使用 | 正常 |
| 統計記録 | 生のML確率（ml_confidence）を記録 | **問題** |

**実際の取引動作は正しいが、統計分析用の記録が誤っていた**

### 修正ファイル一覧

| ファイル | 修正内容 |
|---------|---------|
| `src/trading/core/types.py` | TradeEvaluationにadjusted_confidenceフィールド追加 |
| `src/trading/risk/manager.py` | strategy_confidenceをadjusted_confidenceとして保存 |
| `src/trading/execution/executor.py` | virtual_positionにadjusted_confidence追加（2箇所） |
| `src/core/execution/backtest_runner.py` | position["adjusted_confidence"]を記録 |
| `src/backtest/reporter.py` | adjusted_confidenceパラメータ追加 |
| `scripts/backtest/standard_analysis.py` | adjusted_confidenceで統計計算 |

### バックテスト結果

**実行**: GitHub Actions（run ID: 20989212052）
**完了**: 2026年1月15日

#### adjusted_confidence記録の検証

| 項目 | ml_confidence | adjusted_confidence |
|------|---------------|---------------------|
| 最小 | 0.336 | 0.091 |
| 最大 | 0.817 | 0.617 |
| 平均 | 0.443 | 0.302 |

**✅ adjusted_confidence記録が正常に動作**

#### penalty/bonus適用状況

| 適用 | 件数 | 割合 |
|------|------|------|
| penalty適用（減少） | 538件 | 91% |
| bonus適用（増加） | 53件 | 9% |

#### 信頼度逆転問題の検証

| adjusted_confidence帯 | 取引数 | 勝率 |
|----------------------|--------|------|
| 0%-40% | 511件 | 48.5% |
| 40%-50% | 64件 | **67.2%** |
| 50%-55% | 13件 | **61.5%** |
| 55%+ | 3件 | - |

**✅ 信頼度逆転問題は解消**
- 高adjusted_confidence帯（40%+）の勝率: 61-67%
- 低adjusted_confidence帯（<40%）の勝率: 48.5%

#### 全体パフォーマンス（変化なし）

| 指標 | 値 |
|------|-----|
| 総損益 | ¥+35,955 |
| PF | 1.39 |
| 勝率 | 50.9% |

**注**: Phase 59.3は記録修正のみ。取引判断ロジック変更なし。

### テスト結果

| 項目 | 結果 |
|------|------|
| pytest | 1,195件全て通過 |
| flake8 | PASS |
| black | PASS |
| isort | PASS |

---

## 撤回・変更した計画

| 旧計画 | 新方針 | 理由 |
|--------|--------|------|
| DonchianChannel無効化 | 維持 | TP/SL変更で黒字化（+¥6,711） |
| BBReversal完全無効化 | normal_range限定無効化 | tight_rangeで機能（58.3%勝率） |

---

## 教訓

### TP/SL設定の重要性

Phase 58.5/58.6のTP/SL変更（0.8%/0.6% → 0.4%/0.3%）により：
- BBReversal勝率: 8.3% → 50.0%
- DonchianChannel: 赤字 → 黒字（+¥10,271改善）
- 全体PF: 1.18 → 1.38

**結論**: 戦略無効化の前にTP/SL最適化を検討すべき

### レジーム別分析の価値

BBReversalの全体パフォーマンス（50%勝率、¥-1,331）だけでは判断を誤る。
レジーム別分析により：
- tight_range: 58.3%勝率、+¥379（有効）
- normal_range: 0%勝率、-¥1,710（無効化対象）

**結論**: 戦略はレジーム別に評価・最適化すべき

---

## Phase 59.4: 戦略判定・ML統合改善

### 背景（Phase 59.3バックテスト分析）

#### 発見された問題1: 2票ルールが重み設定を無視

| 問題 | 内容 |
|------|------|
| 設定 | ADXTrendStrength tight_range/normal_range重み = 0.0 |
| 期待 | 取引数 = 0件 |
| 実際 | **75件の取引が発生** |
| 原因 | 2票ルールは重みを無視して「票数」のみカウント |

#### 発見された問題2: Agreement/Disagreement逆転

| 指標 | 値 |
|------|-----|
| Agreement時勝率 | 46.4% |
| Disagreement時勝率 | **51.5%** |
| 結論 | bonus/penaltyが逆効果 |

#### 発見された問題3: 高信頼度で負ける

| 信頼度帯 | 勝率 |
|---------|------|
| 高（≥55%） | 25.0% |
| 中（45-55%） | **57.8%** |
| 低（<45%） | 48.9% |

### Phase 59.4-A: 2票ルール無効化

**目的**: 重み設定が正しく機能するベースライン確立

**変更内容**:
```yaml
# config/core/features.yaml
consensus:
  enabled: false  # true → false（2票ルール無効化）
```

**理由**:
- 2票ルールは戦略の「重み」を無視して「票数」のみカウント
- 重み0の戦略（ADXTrendStrength等）が取引に参加していた
- 従来の重み付け統合ルールに戻すことで設計意図通りに動作

**期待効果**:
- 重み設定が正しく機能
- レジーム別戦略選択が設計通りに動作

### 実装ステップ

- [x] Phase 59.4-A: 2票ルール無効化
- [ ] Phase 59.4-A: バックテスト実行・検証
- [ ] Phase 59.4-B: bonus/penalty無効化
- [ ] Phase 59.4-C: 重み調整
- [ ] Phase 59.4-D: 個別戦略調整（必要に応じて）

---

## Phase 59.5: ライブモード分析修正

### 背景

ライブモード分析（`scripts/live/standard_analysis.py`）で3つの問題が発見された。

| 問題 | 症状 | 重要度 |
|------|------|--------|
| 孤児SL検出不一致 | UIで3件、スクリプトで1件 | HIGH |
| データ取得不足 | 200件要求→84件取得 | HIGH |
| 稼働率計算誤り | 41.7%表示（実際は正常） | MEDIUM |

### 修正内容

#### 1. 注文タイプ判定修正（bitbank_client.py）

**根本原因**: CCXTは`stop_loss`/`take_profit`ではなく`stop`/`limit`を返す

```python
# 修正前（L1288-1293）
tp_orders = [o for o in active_orders if o.get("type") == "take_profit"]
sl_orders = [o for o in active_orders if o.get("type") == "stop_loss"]

# 修正後
limit_orders = [o for o in active_orders if o.get("type") == "limit"]
sl_orders = [o for o in active_orders if o.get("type") in ["stop", "stop_limit"]]
```

#### 2. 注文フェッチ一元化（standard_analysis.py）

**根本原因**: `_fetch_position_status()`と`_check_tp_sl_placement()`が別々にAPI呼び出し → タイミング差で不整合

```python
# 修正: キャッシュ変数追加
self._cached_active_orders: List[Dict[str, Any]] = []

# _fetch_position_status()でキャッシュに保存
self._cached_active_orders = active_orders

# _check_tp_sl_placement()でキャッシュを再利用
active_orders = self._cached_active_orders or []
```

#### 3. 稼働率タイムゾーン修正（standard_analysis.py）

**根本原因**: ローカルJST時刻を使用 → GCPログはUTC → 9時間ズレ

```python
# 修正前
since_time = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")

# 修正後
from datetime import timezone
utc_now = datetime.now(timezone.utc)
since_time = (utc_now - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
```

#### 4. 4時間足年跨ぎ対応（bitbank_client.py）

**根本原因**: 現在年のみ取得 → 2026年1月は84件のみ（2025年を取得していない）

```python
# 修正: 年跨ぎ対応追加（L179-204）
ohlcv_current = await self.fetch_ohlcv_4h_direct(symbol=symbol, year=current_year)

if len(ohlcv_current) < limit:
    # 前年も取得してマージ
    ohlcv_prev = await self.fetch_ohlcv_4h_direct(symbol=symbol, year=current_year - 1)
    ohlcv = ohlcv_prev + ohlcv_current
```

### 修正ファイル一覧

| ファイル | 修正内容 |
|---------|---------|
| `src/data/bitbank_client.py` | 注文タイプ判定修正（L1288-1298） |
| `src/data/bitbank_client.py` | 4時間足年跨ぎ対応（L179-204） |
| `scripts/live/standard_analysis.py` | キャッシュ変数追加（L133-134） |
| `scripts/live/standard_analysis.py` | 注文フェッチ一元化（L230-232, L450-451） |
| `scripts/live/standard_analysis.py` | タイムゾーン修正（L537-542） |

### テスト結果

| 項目 | 結果 |
|------|------|
| pytest | 1,195件全て通過 |

---

**最終更新**: 2026年1月15日
**ステータス**: Phase 59.5実装完了・Phase 59.4-Aバックテスト検証中

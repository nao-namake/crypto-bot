# Phase 67: SL 700円 + 勝率改善施策

**期間**: 2026年3月1日-
**状態**: バックテスト検証中

| 変更 | 内容 | 状態 |
|------|------|------|
| **変更1** | 固定金額SL 500円→700円（全レジーム） | ✅ 完了 |
| **変更2** | StochasticReversal重み削減 + ATRBased集中 | ✅ 完了 |
| **変更3 (67.2)** | Kelly=0時のDynamicフォールバック（ポジションサイズ復元） | ✅ 完了 |

---

## 背景

### Phase 66.8のバックテスト結果（2025/7-12月）

| 指標 | 値 |
|------|-----|
| 取引数 | 520件 |
| 勝率 | 49.0% |
| 総損益 | ¥-3,804 |
| PF | 0.97 |
| SL件数 | 265件 (51%) |
| TP件数 | 254件 (49%) |

### 根本原因分析

Phase 65（成功: +¥102,135、勝率85%）→ Phase 66.8（失敗: -¥3,804、勝率49%）の最大の差:

| 比較 | Phase 65 | Phase 66.8 | 差 |
|------|----------|-----------|-----|
| SL方式 | 0.4%（percentage-based） | 500円（fixed amount） | - |
| 実効SL金額 | ~660円 | 500円 | **160円狭い** |

SL 500円はBTC価格レベルに対して狭すぎ、正しい方向に動いた取引（95%がプラス圏経由）が
SLに引っかかっていた。

### 戦略別成績（Phase 66.8）

| 戦略 | 取引数 | 勝率 | 損益 | SL率 |
|------|--------|------|------|------|
| ATRBased | 332件 | 51.2% | **+¥3,992** | 49% |
| DonchianChannel | 148件 | 48.0% | -¥3,003 | 52% |
| **StochasticReversal** | **38件** | **34.2%** | **-¥6,006** | **66%** |

StochasticReversalは全赤字の主犯（38件で-¥6,006）。

---

## 変更1: 固定金額SL 500円→700円

### 数理的根拠

| 指標 | TP=500/SL=500 | TP=500/SL=700 |
|------|---------------|---------------|
| RR比 | 1.00 | 0.71 |
| 損益分岐勝率 | **50.0%** | **58.3%** |

勝率と期待値の関係（1取引あたり）:

| 勝率 | TP=500/SL=500 | TP=500/SL=700 |
|------|---------------|---------------|
| 55% | +¥25 | -¥40 |
| 60% | +¥50 | **+¥20** |
| 65% | +¥75 | **+¥80** |
| 70% | +¥100 | **+¥140** |
| 75% | +¥125 | **+¥200** |

勝率65%を超えるとSL=700円の方が期待値が高くなる。
Phase 65の実績（85%勝率、実効SL ~660円）から判断して十分達成可能。

### 変更箇所

**ファイル**: `config/core/thresholds.yaml`

| 設定パス | 変更前 | 変更後 |
|---------|--------|--------|
| `stop_loss.fixed_amount.target_max_loss` | 500 | **700** |
| `regime_based.tight_range.fixed_amount_target` | 500 | **700** |
| `regime_based.normal_range.fixed_amount_target` | 500 | **700** |
| `regime_based.trending.fixed_amount_target` | 500 | **700** |
| `regime_based.high_volatility.fixed_amount_target` | 500 | **700** |

---

## 変更2: StochasticReversal重み削減

### 変更箇所

**ファイル**: `config/core/thresholds.yaml`

| レジーム | 戦略 | 変更前 | 変更後 |
|---------|------|--------|--------|
| tight_range | StochasticReversal | 0.30 | **0.10** |
| tight_range | ATRBased | 0.30 | **0.45** |
| tight_range | DonchianChannel | 0.25 | **0.30** |
| tight_range | BBReversal | 0.15 | 0.15（維持） |
| normal_range | StochasticReversal | 0.30 | **0.10** |
| normal_range | ATRBased | 0.50 | **0.60** |
| normal_range | DonchianChannel | 0.20 | **0.30** |

### 根拠

- Phase 65ではATRBased（68%シェア）で85%勝率達成
- StochasticReversalを除外するだけで勝率49%→50%、損益-3,804→+2,201に改善
- 完全無効化しない理由: SL=700での改善度を確認したい

---

## 変更しないもの

| 項目 | 理由 |
|------|------|
| ML設定（信頼度閾値等） | SL変更後のML予測パフォーマンスを先に確認 |
| TP金額（500円） | Phase 61.12で最適と実証済み |
| Recovery設定 | Phase 66.8で調整済み、SL変更後に再評価 |
| DonchianChannel重み | Phase 65では70-82%勝率、SL変更で回復する可能性 |

---

## 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `config/core/thresholds.yaml` | SL 500→700円（5箇所）+ 戦略重み調整（6値） |
| `tests/unit/services/test_dynamic_strategy_selector.py` | tight_range重みテスト値更新 |
| `CLAUDE.md` | しおり更新（Phase 67）+ 固定金額SL/戦略重み記載更新 |

---

## 変更3 (Phase 67.2): Kelly=0時のDynamicフォールバック

### 根本原因

Phase 65 (+¥102,135) → Phase 67 (-¥13,319) の大幅悪化の調査で、
ポジションサイズが 0.022 BTC → 0.0066 BTC に 3.3倍縮小していることが判明。

**ポジションサイズ計算（加重平均）**:
```
integrated = kelly(0.0) × 0.5 + dynamic(0.0204) × 0.3 + risk_mgr(0.00016) × 0.2
           = 0 + 0.00612 + 0.000032
           = 0.00615 BTC  ← 実績 0.0066 と一致
```

**原因**: 固定TP/SL（500/700円）でpayoff ratio ≈ 0.71。Kelly正にはwin rate > 58.5%が必要。
現行56%ではKelly構造的に常に0 → 50%の重みが無駄に → ポジション1/3に崩壊。

### 修正内容

**ファイル**: `src/trading/risk/sizer.py`（2箇所）

Kelly ≤ min_trade_size 時にDynamic sizing単独で決定するフォールバック追加:

```python
# L109-120（動的サイジング有効時）
min_trade_size = get_threshold("production.min_order_size", 0.0001)
if kelly_size <= min_trade_size:
    integrated_size = dynamic_size  # Kelly無信号→Dynamic単独
else:
    integrated_size = (加重平均)

# L194-201（動的サイジング無効時）
if kelly_size <= min_trade_size:
    integrated_size = risk_manager_size
else:
    integrated_size = (加重平均)
```

### 修正後の期待値

| 指標 | 修正前(0.006BTC) | 修正後(0.02BTC) |
|------|------------------|----------------|
| TP距離 | 83,333円 (0.69%) | 25,000円 (0.21%) |
| SL距離 | 116,667円 (0.97%) | 35,000円 (0.29%) |
| 1トレードリスク | 700円（0.14%） | 700円（0.14%） |

---

## バックテスト結果

（GitHub Actions実行中 -- 完了後に記載）

### 目標指標

| 指標 | Phase 66.8 | 目標 | Phase 65参考値 |
|------|-----------|------|---------------|
| 勝率 | 49.0% | **65%+** | 85.4% |
| 総損益 | ¥-3,804 | **¥+100,000+** | ¥+102,135 |
| PF | 0.97 | **1.5+** | 2.47 |
| 最大DD | 3.72% | **2%以下** | 0.94% |

### 判断基準

| 勝率 | 判定 | 次のアクション |
|------|------|---------------|
| ≥ 65% | 成功 | ライブ投入検討 |
| 58-65% | 部分成功 | 追加施策（ML調整等）検討 |
| < 58% | 失敗 | SL金額再検討 or 百分率SLへの回帰 |

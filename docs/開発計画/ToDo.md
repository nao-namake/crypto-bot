# 暗号資産取引Bot - 開発計画

## 現在の状態

**Phase 55.5進行中** - ポジションサイズ・ML統合修正（2025/12/22）

---

## Phase 55: 戦略最適化

### Phase 55概要

| Phase | 内容 | 状態 | 主要成果 |
|-------|------|------|----------|
| 55.1 | ATRBased閾値調整 | ✅ | 取引数+30%、PF 1.16 |
| 55.2 | StochasticDivergence転換 | ✅ | PF 0.77→1.25（+62%） |
| 55.3 | 取引数回復（並列評価・閾値緩和） | ✅ | シグナル生成改善 |
| 55.4 | 戦略分析・重み最適化 | ✅ | **ATR: PF 0.99→1.11** |
| **55.5** | **ポジションサイズ・ML統合修正** | **🔄 進行中** | - |
| 55.6 | 最終検証・本番適用 | 予定 | - |

---

## Phase 55.4: 戦略分析・重み最適化【完了】

### 目的

180日分析結果に基づき、各戦略の重みと設定を最適化する。

### 実施済み

#### 1. ADXTrendStrength無効化

| 指標 | 値 |
|------|-----|
| PF | 0.85（赤字） |
| 損失 | -36,432円 |
| 理由 | トレンド型だがtight_range 90%に不向き |

**変更:** `strategies.yaml`で`enabled: false`、`weight: 0.00`

#### 2. レジーム適性ベースの重み再設計

| 戦略 | 旧重み | 新重み | 適性 | PF |
|------|--------|--------|------|-----|
| BBReversal | 0.17 | **0.30** | range | 1.12 |
| DonchianChannel | 0.17 | **0.25** | range | 1.00 |
| StochasticReversal | 0.17 | **0.25** | range | 1.06 |
| ATRBased | 0.17 | **0.15** | range | **1.11** |
| MACDEMACrossover | 0.15 | **0.05** | trend | 1.20 |
| ADXTrendStrength | 0.17 | **0.00** | trend | 0.79 |

**設計思想:** tight_range 90%の相場に合わせてレンジ戦略を重視

#### 3. ATR戦略の直列評価方式復帰

**問題:** 並列スコアリング（Phase 55.3）でPF悪化（0.99→0.91）

**解決:** 直列評価方式に戻してPF改善

| 変更内容 | 詳細 |
|---------|------|
| 評価方式 | 並列スコア → 直列評価（必須条件チェック） |
| 消尽率閾値 | 0.60（バランス設定） |
| RSI閾値 | 58/42（取引数増加） |
| BB位置確認 | 信頼度ボーナスとして追加 |

**結果（60日分析）:**

| 指標 | 改善前 | 改善後 | 変化 |
|------|--------|--------|------|
| PF | 0.99 | **1.11** | +12% |
| 取引数 | 621件/180日 | 378件/180日 | -39% |
| 勝率 | 43.6% | **46.0%** | +2.4% |
| 損益 | -7,221円 | **+10,129円** | 黒字化 |

### 180日バックテスト結果

**Run ID:** 20401710348（旧設定で実行）

| 指標 | 結果 |
|------|------|
| 取引数 | 11件 |
| 勝率 | 36.36% |
| 損益 | -18円 |

**注:** バックテストシステムでML予測・リスク管理フィルタが強くかかり、分析スクリプトとの乖離が大きい。新設定で再実行が必要。

### 次のステップ

1. 新設定で180日バックテスト再実行
2. Phase 55.5で本番適用判断

---

## Phase 55.5: ポジションサイズ・ML統合修正【進行中】

### 背景

180日バックテスト（Run ID: 20401710348）で3つの重大な問題を発見。

| 問題 | 現象 | 根本原因 |
|------|------|----------|
| **ポジションサイズ固定** | 常に0.0001 BTC | min()で最小値が採用される |
| **取引数激減** | 11件/180日 | 戦略HOLDが多すぎる（77.6%） |
| **ML統合でHOLD変換** | BUY/SELLがHOLDに | hold_conversion_threshold問題 |

### 問題1: ポジションサイズ計算

#### 現状の問題構造

```python
# sizer.py:94
integrated_size = min(dynamic_size, kelly_size, risk_manager_size)
```

| 計算元 | 計算結果 | 問題点 |
|--------|---------|--------|
| Dynamic | 0.0006 BTC | 比率3-10%で計算、BTC高価格で極小化 |
| Kelly | 0.01 BTC | 履歴不足時のフォールバック（正常） |
| RiskManager | 0.02 BTC | 正常 |
| **min()採用** | **0.0006 BTC** | **Kellyが活かされない** |

#### 修正方針: 統合ロジック変更（正統進化）

**変更前（sizer.py:94）:**
```python
integrated_size = min(dynamic_size, kelly_size, risk_manager_size)
```

**変更後:**
```python
# Phase 55.5: 加重平均方式（Kelly基準を活かす）
kelly_weight = get_threshold("position_integrator.kelly_weight", 0.5)
dynamic_weight = get_threshold("position_integrator.dynamic_weight", 0.3)
risk_weight = get_threshold("position_integrator.risk_manager_weight", 0.2)

integrated_size = (
    kelly_size * kelly_weight +
    dynamic_size * dynamic_weight +
    risk_manager_size * risk_weight
)

# 安全上限・最小取引単位チェック
max_order_size = get_threshold("production.max_order_size", 0.03)
min_trade_size = get_threshold("production.min_order_size", 0.0001)
integrated_size = max(min(integrated_size, max_order_size), min_trade_size)
```

**期待効果:**
- Kelly（0.01 BTC）が50%の重みで反映
- 0.01 × 0.5 + 0.0006 × 0.3 + 0.02 × 0.2 = 0.0092 BTC
- 現在の0.0001から約90倍改善

### 問題2: 戦略HOLD率77.6%

5760データポイント中:
- HOLD: 4473件（77.6%）
- BUY/SELL: 1287件（22.4%）

**対策:** Phase 55.4で個別戦略（ATR直列評価等）改善済み。

### 問題3: ML統合でのHOLD変換

```python
# trading_cycle_manager.py
if adjusted_confidence < hold_conversion_threshold:  # 0.20
    return hold_signal  # HOLD変換！
```

**修正:** `hold_conversion_threshold: 0.20→0.15`

### 実装手順

| Step | ファイル | 変更内容 | 状態 |
|------|---------|---------|------|
| 1 | `docs/開発履歴/Phase_55.md` | Phase 55.4完了記録 | ✅ |
| 2 | `docs/開発計画/ToDo.md` | Phase 55.5計画追加 | 🔄 |
| 3 | `src/trading/risk/sizer.py` | min()→加重平均方式 | ⏳ |
| 4 | `config/core/thresholds.yaml` | position_integrator設定追加 | ⏳ |
| 5 | `config/core/thresholds.yaml` | hold_conversion_threshold緩和 | ⏳ |
| 6 | 検証 | 単体テスト・60日分析・180日バックテスト | ⏳ |

### 成功基準

| 指標 | 現状 | 最低ライン | 目標 |
|------|------|-----------|------|
| ポジションサイズ | 0.0001 BTC | >0.005 BTC | 0.01 BTC |
| 取引数 | 11件/180日 | ≥200件 | ≥400件 |
| PF | 1.11 | ≥1.15 | ≥1.25 |
| 勝率 | 36% | ≥50% | ≥52% |

---

## Phase 55.6: 最終検証・本番適用

### 目的

Phase 55全体の変更を本番環境に適用する前の最終検証。

### 本番適用手順

1. ペーパートレード1週間実行
2. 本番デプロイ（Cloud Run更新）
3. 24時間監視
4. Discord通知確認

---

## リスク管理

### ロールバック基準

- PFが0.95未満に低下 → 即時ロールバック
- 勝率が45%未満に低下 → 即時ロールバック
- 最大DDが1.5%を超過 → 即時ロールバック

### フォールバック設定

```
config/core/atr_based_backup_pf146.yaml  # 高PF設定バックアップ
```

---

## 今後の開発計画

### Phase 56予定: トレンド戦略強化

現在はレンジ相場特化（tight_range 90%+）だが、トレンド相場での収益機会も検討。

- ADXTrendStrength改善
- MACDEMACrossover最適化
- トレンド相場用TP/SL設定

### Phase 57予定: MLモデル再学習

Phase 55の戦略変更を反映したMLモデルの再学習。

- 新しいシグナルパターンの学習
- 特徴量の見直し
- アンサンブル重みの最適化

### Phase 58予定: ML・戦略統合ロジック見直し

Phase 55.5レビューで判明した対症療法的修正の本質的解決。

| 項目 | 現状 | 将来対応 |
|------|------|----------|
| `hold_conversion_threshold` | 0.20→0.15（閾値緩和） | ML・戦略不一致パターン分析・統合ロジック再設計 |
| Optuna記録との整合性 | Line 814に旧値0.4残存 | 記録セクションの値を実際の設定に同期 |
| `disagreement_penalty` | 0.95固定 | 戦略別・レジーム別ペナルティ検討 |

**背景:**
- 現在のML統合は対症療法（閾値緩和）で改善
- 本質的にはML・戦略の不一致パターンが多い根本原因を解決すべき
- Phase 55.4で戦略品質向上済みのため、まずは効果を検証

---

## 関連ファイル

| ファイル | 内容 |
|---------|------|
| `docs/開発履歴/Phase_55.md` | Phase 55詳細記録 |
| `scripts/analysis/unified_strategy_analyzer.py` | 統合分析スクリプト |
| `config/core/thresholds.yaml` | 閾値設定 |
| `.github/workflows/backtest.yml` | バックテストワークフロー |

---

**最終更新**: 2025年12月22日 - Phase 55.5進行中（ポジションサイズ・ML統合修正）

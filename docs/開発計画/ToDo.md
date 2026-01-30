# 暗号資産取引Bot - 開発計画

## 現在の状態

**Phase 62進行中** - 戦略閾値緩和・バランス改善

---

## Phase 62: 戦略閾値緩和・バランス改善

### 背景

**問題点**:
- ATRBased一強問題（83%）
- BBReversal: 1件・0%勝率（機能していない）
- DonchianChannel: 13件・69.2%勝率（良好だが活用不足）
- StochasticReversal: 29件・51.7%勝率（普通）

**Phase 61.12 バックテスト結果**:

| 戦略 | 取引数 | 勝率 | 損益 | 評価 |
|------|--------|------|------|------|
| ATRBased | 218件(83%) | 61.0% | +¥118,767 | 主力 |
| **DonchianChannel** | 13件(5%) | **69.2%** | **+¥10,608** | **良好** |
| StochasticReversal | 29件(11%) | 51.7% | +¥3,383 | 普通 |
| BBReversal | 1件(0.4%) | 0.0% | -¥1,194 | 問題 |

---

### 実装計画

| Phase | 内容 | 状態 |
|-------|------|------|
| **62.1** | **3戦略閾値一括緩和** | 📋実装中 |
| 62.2 | HOLD動的信頼度 | 📋保留（62.1結果次第） |

---

### Phase 62.1: 3戦略閾値一括緩和

**対象ファイル**: `config/core/thresholds.yaml`

**変更内容**:

#### BBReversal（1件・0%勝率 → 最優先）
```yaml
bb_upper_threshold: 0.85 → 0.75
bb_lower_threshold: 0.15 → 0.25
rsi_overbought: 62 → 58
rsi_oversold: 38 → 42
```

#### StochasticReversal（29件・51.7%勝率）
```yaml
stoch_overbought: 72 → 65
stoch_oversold: 28 → 35
```

#### DonchianChannel（13件・69.2%勝率 → 活用強化）
```yaml
extreme_zone_threshold: 0.12 → 0.15
rsi_oversold: 42 → 45
rsi_overbought: 58 → 55
```

---

### 成功基準

| 指標 | 現在 | 目標 |
|------|------|------|
| ATRBased比率 | 83% | 50%以下 |
| BBReversal取引数 | 1件 | 30件以上 |
| StochasticReversal取引数 | 29件 | 50件以上 |
| DonchianChannel取引数 | 13件 | 30件以上 |
| PF | 2.68 | 2.0以上維持 |
| 勝率 | 75.8% | 70%以上維持 |

---

### 検証方法

```bash
python3 main.py --mode backtest
python3 scripts/backtest/standard_analysis.py --from-ci
```

---

## 保留タスク

| タスク | 優先度 | 備考 |
|--------|--------|------|
| トレーリングストップ | 中 | 閾値緩和で不要になる可能性 |
| CatBoost追加 | 低 | 4モデルアンサンブル化 |
| SL成行フォールバック | 中 | 急落時リスク対策 |
| レバレッジ1.0倍移行 | 中 | Phase 62完了後 |
| トレンド型戦略改修 | 低 | trending発生率改善後 |

---

## 関連ファイル

| ファイル | 内容 |
|---------|------|
| `docs/開発履歴/Phase_61.md` | Phase 61完了記録 |
| `docs/開発履歴/Phase_62.md` | Phase 62開発記録 |
| `docs/開発履歴/SUMMARY.md` | 全Phase総括 |
| `config/core/thresholds.yaml` | 戦略閾値設定 |

---

**最終更新**: 2026年1月31日 - Phase 62.1実装中

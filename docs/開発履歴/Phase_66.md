# Phase 66: ライブ取引再開 — 3つの根本原因修正

**期間**: 2026年2月26日-
**状態**: 進行中

| 修正 | 内容 | 状態 |
|------|------|------|
| **修正1** | HOLD信頼度ハードコード修正（ATRBased 5箇所 + BBReversal 1箇所） | ✅ 完了 |
| **修正2** | レジーム分類バグ修正（EMA slope閾値 0.01→0.003） | ✅ 完了 |
| **修正3** | ML再学習 + Recovery閾値調整 | ✅ 完了 |

---

## 背景

Phase 65.16デプロイ後、24時間（59サイクル）で**取引ゼロ**。GCPログ分析で3つの根本原因を特定。

---

## 修正1: HOLD信頼度ハードコード修正

### 問題

`SignalBuilder.create_hold_signal()` が `confidence=0.5` をハードコード。ATRBasedは最大重み(0.50)を持つ主力戦略のため、HOLD(0.5×0.50=0.250)が常にSELL(0.545×0.30=0.164)に勝ち、取引が発生しなかった。

BBReversalも同じ問題（`SignalBuilder.create_hold_signal()`をconfidenceなしで呼び出し→デフォルト0.5）。

### 対策

| ファイル | 変更 |
|---------|------|
| `src/strategies/utils/strategy_utils.py` | `create_hold_signal()`に`confidence`パラメータ追加（デフォルト0.5で後方互換） |
| `src/strategies/implementations/atr_based.py` | 5箇所の呼び出しに`confidence=self.config["hold_confidence"]`(0.20)追加 |
| `src/strategies/implementations/bb_reversal.py` | 1箇所の呼び出しに`confidence=self.config["hold_confidence"]`(0.20)追加 |

### 効果（normal_rangeでの投票計算）

| 戦略 | 重み | 信頼度(修正前) | 加重(修正前) | 信頼度(修正後) | 加重(修正後) |
|------|------|--------------|-----------|--------------|-----------|
| ATRBased | 0.50 | 0.500 | 0.250 | 0.200 | 0.100 |
| Stochastic | 0.30 | SELL 0.545 | 0.164 | SELL 0.545 | 0.164 |
| Donchian | 0.20 | 0.250 | 0.050 | 0.250 | 0.050 |

- 修正前: HOLD比率=0.300/0.464=**64.7%** → 常にHOLD
- 修正後: HOLD比率=0.150/0.314=**47.8%** → SELLが勝てる

---

## 修正2: レジーム分類バグ修正

### 問題

`_is_trending()` は `ADX > 25 AND |EMA_slope| > 0.01` の両方が必要。EMA slope = (現在EMA20 - 5本前EMA20) / 5本前EMA20 → 15分足5本=75分で1%の変動は相当大きい。結果: ADXが74でもEMA slopeが0.01未満ならtrendingにならず、デフォルトのnormal_rangeへフォールスルー。

### 対策

| ファイル | 変更 | 根拠 |
|---------|------|------|
| `config/core/thresholds.yaml` | `ema_slope_threshold: 0.01→0.003` | 75分で0.3%変動はトレンド判定として妥当。ADX>25とのAND条件でノイズ誤判定リスク低い |

### 効果

バックテストではtrending判定は1件のみ（2025年7-12月データ）。ライブ環境（2026年2月、高ボラ期）での効果を期待。

---

## バックテスト結果（修正1+2）

**期間**: 2025/07/01 - 2025/12/31（183日間）

### 前回比較

| 指標 | Phase 65.16 | Phase 66 (修正1+2) | 変化 |
|------|------------|-------------------|------|
| 総損益 | ¥+102,135 | ¥+97,236 | -4.8% |
| PF | 2.47 | 1.82 | -26% |
| 勝率 | 89.2% | 85.0% | -4.2pt |
| 最大DD | 0.94% | 0.97% | +0.03pt |
| 取引数 | — | 535件 | — |

### レジーム分布

| レジーム | 取引数 | 勝率 | 総損益 |
|---------|--------|------|--------|
| tight_range | 481件 (89.9%) | 84.4% | ¥+82,881 |
| normal_range | 53件 (9.9%) | 90.6% | ¥+13,896 |
| trending | 1件 (0.2%) | 100% | ¥+459 |

### 信頼度帯別（ML再学習の必要性を示唆）

| 信頼度帯 | 取引数 | 勝率 | 総損益 |
|---------|--------|------|--------|
| 低（<50%） | 508件 | 86.0% | ¥+100,700 |
| 中（50-65%） | 22件 | 68.2% | ¥-1,606 |
| 高（≥65%） | 5件 | 60.0% | ¥-1,858 |

→ 低信頼度が全利益、中〜高信頼度はマイナス。MLモデル19日前作成で劣化を示唆。

### 戦略別

| 戦略 | 取引数 | 勝率 | 総損益 |
|------|--------|------|--------|
| ATRBased | 363件 | 86.8% | ¥+80,493 |
| DonchianChannel | 131件 | 81.7% | ¥+9,731 |
| StochasticReversal | 40件 | 80.0% | ¥+6,554 |
| ADXTrendStrength | 1件 | 100% | ¥+459 |

---

## 修正3: ML再学習 + Recovery閾値調整

### 問題

- MLモデルは19日前（2/6）に作成。信頼度分布が劣化（高信頼度ほど負ける逆転現象）
- ML Signal Recoveryの`min_ml_confidence=0.55`だが、ライブML信頼度は最大0.450 → Recoveryが一度も発動しない

### 対策

1. 最新180日分データでモデル再学習（Optuna最適化 n-trials=50）
2. 再学習後の信頼度分布に基づきRecovery閾値を調整

| ファイル / 設定 | 変更前 | 変更後 | 根拠 |
|---------------|--------|--------|------|
| `models/production/ensemble_full.pkl` | 2/6作成（19日前） | 2/26再学習 | 最新180日分データ（11,793サンプル） |
| `models/production/ensemble_basic.pkl` | 2/6作成 | 2/26再学習 | 同上 |
| `min_ml_confidence` | 0.55 | 0.45 | 平均信頼度0.425+0.025。平均以上に自信がある時のみRecovery発動 |
| `recovery_confidence_cap` | 0.35 | 0.30 | 保守的サイズで過大エントリーを防止 |

### 再学習モデルの性能

| モデル | Accuracy | F1 Score | CV F1 Mean |
|--------|----------|----------|------------|
| LightGBM | 0.484 | 0.465 | 0.385 |
| XGBoost | 0.485 | 0.464 | 0.387 |
| RandomForest | 0.494 | 0.467 | 0.378 |

### 信頼度分布（検証時）

| 指標 | 値 |
|------|-----|
| 平均信頼度 | 0.425 |
| 最大信頼度 | 0.494 |
| 最小信頼度 | 0.384 |
| 標準偏差 | 0.017 |
| 高信頼度(>60%) | 0.0% |

→ 信頼度が0.40-0.50に集中する控えめなモデル。旧`min_ml_confidence=0.55`では最大でも届かず、Recovery発動不能だった。

---

## バックテスト結果（全修正込み）

（GitHub Actions実行中 — 完了後に記載）

---

## 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `src/strategies/utils/strategy_utils.py` | `create_hold_signal()`にconfidenceパラメータ追加 |
| `src/strategies/implementations/atr_based.py` | 5箇所のcreate_hold_signal()にconfidence=config値追加 |
| `src/strategies/implementations/bb_reversal.py` | 1箇所のcreate_hold_signal()にconfidence=config値追加 |
| `config/core/thresholds.yaml` | `ema_slope_threshold: 0.01→0.003` |
| `config/core/thresholds.yaml` | `ml_signal_recovery.min_ml_confidence: 0.55→0.45` |
| `config/core/thresholds.yaml` | `recovery_confidence_cap: 0.35→0.30` |
| `models/production/ensemble_full.pkl` | MLモデル再学習（Optuna n-trials=50） |
| `models/production/ensemble_basic.pkl` | MLモデル再学習（基本特徴量版） |

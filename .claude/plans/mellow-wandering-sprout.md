# Phase 59.9: Meta-Learner改善計画

## 背景

Phase 59.8のバックテストで、Stackingモデルに以下の問題が発覚：

| 指標 | Stacking | ProductionEnsemble | 問題 |
|------|----------|-------------------|------|
| SELL予測率 | 21.7% | 41.9% | **-20.2%** |
| ML×戦略一致率 | 32.6% | 49.6% | **-17.0%** |
| 一致時勝率 | 49.4% | 62.8% | **-13.4%** |
| 総損益 | ¥41,327 | ¥49,327 | **-¥8,000** |

---

## 原因分析

1. **クラス重み設定の問題** (`class_weight="balanced"`)
   - 自動バランス化がOOF予測の歪みを補正できていない

2. **メタ特徴量の不足** (9特徴量のみ)
   - 3モデル×3クラス確率のみ
   - モデル間一致度・信頼度情報なし

3. **OOF予測分布の歪み**
   - ベースモデルのSELL予測が少ない状態でMeta-Learner学習

---

## 実装計画

### Phase 59.9-A: クラス重み動的計算

**修正ファイル**: `scripts/ml/create_ml_models.py`

**変更内容** (L1270-1290):
```python
# 現在
meta_params = {
    ...
    "class_weight": "balanced",
}

# 改善後
class_counts = y_meta_train.value_counts().sort_index()
computed_weights = {}
for cls in range(self.n_classes):
    if cls in class_counts.index:
        ratio = class_counts[cls] / len(y_meta_train)
        # SELL(cls=0)の重みを強化
        base_weight = 1.0 / (self.n_classes * ratio)
        if cls == 0:  # SELL
            computed_weights[cls] = base_weight * 1.5  # 50%強化
        else:
            computed_weights[cls] = base_weight

meta_params = {
    ...
    "class_weight": computed_weights,
}
```

**期待効果**: SELL予測 21.7% → 30%+

---

### Phase 59.9-B: メタ特徴量拡張

**修正ファイル**: `scripts/ml/create_ml_models.py`

**追加メタ特徴量** (9 → 15特徴量):

| 特徴量 | 計算式 | 役割 |
|--------|--------|------|
| `{model}_max_conf` (×3) | max(p_class) | 各モデルの確信度 |
| `model_agreement` | 3モデル予測一致=1, 不一致=0 | モデル間合意 |
| `entropy` | -Σ p*log(p) | 予測不確実性 |
| `max_prob_gap` | max(p) - 2nd_max(p) | 確信度の差 |

**新規メソッド追加**:
```python
def _add_enhanced_meta_features(self, X_meta_base, oof_preds):
    """拡張メタ特徴量を追加"""
    # 実装詳細は上記Exploreエージェントの提案に基づく
```

**期待効果**: 一致率 32.6% → 38-40%

---

### Phase 59.9-C: Meta-Learnerパラメータ調整

**修正ファイル**: `scripts/ml/create_ml_models.py`

**パラメータ変更**:

| パラメータ | 現在 | 改善後 | 理由 |
|-----------|------|--------|------|
| n_estimators | 50 | 100 | 学習容量増加 |
| max_depth | 4 | 5 | 複雑な関係学習 |
| num_leaves | 15 | 20 | 分割能力向上 |
| feature_fraction | なし | 0.8 | 過学習防止 |
| bagging_fraction | なし | 0.8 | 汎化性能向上 |

---

### Phase 59.9-D: 検証

```bash
# 1. モデル再学習
python3 scripts/ml/create_ml_models.py

# 2. ローカルテスト
python3 scripts/testing/validate_ml_models.py

# 3. 品質チェック
bash scripts/testing/checks.sh

# 4. コミット＆180日バックテスト
git add . && git commit -m "feat: Phase 59.9 Meta-Learner改善"
git push origin main
gh workflow run backtest.yml -f backtest_days=180

# 5. 結果分析
python3 scripts/backtest/standard_analysis.py --from-ci --phase 59.9
```

---

## 成功基準

| 指標 | Phase 59.8 | 目標 |
|------|-----------|------|
| SELL予測率 | 21.7% | **30%+** |
| ML×戦略一致率 | 32.6% | **40%+** |
| 一致時勝率 | 49.4% | **55%+** |
| PF | 1.54 | **1.55+** |
| 総損益 | ¥41,327 | **¥45,000+** |

---

## 修正ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `scripts/ml/create_ml_models.py` | クラス重み・メタ特徴量・パラメータ改善 |

---

## リスク対策

改善が見られない場合:
```yaml
# config/core/thresholds.yaml
ensemble:
  stacking_enabled: false  # ProductionEnsembleにフォールバック
```

→ PF 1.59, ¥+49,327 の成績に即座に戻せる

---

**最終更新**: 2026年1月17日

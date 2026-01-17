# 暗号資産取引Bot - 開発計画

## 現在の状態

**Phase 59.9完了**（Meta-Learner改善）- F1: 0.36→0.43（+19%）

※ 完了済みタスクの詳細は `docs/開発履歴/` を参照

---

## Phase 59 ロードマップ（ML性能向上フェーズ）

| Phase | 内容 | 状態 | 検証 |
|-------|------|------|------|
| 59.1-59.3 | バックテストシステム改善・分析 | ✅完了 | - |
| 59.4-A | 2票ルール無効化 | ✅完了 | - |
| 59.4-B | 重み調整 | ❌失敗→リバート | - |
| 59.5 | ライブモード分析バグ修正 | ✅完了 | - |
| 59.6 | SL指値処理変更 + 孤児SL修正 | ✅完了 | - |
| 59.7 | Stacking Meta-Learner実装 | ✅完了 | - |
| 59.8 | Stacking本番環境統合 | ✅完了 | バックテスト済 |
| **59.9** | **Meta-Learner改善** | ✅完了 | バックテスト実行中 |
| 59.10 | 追加メタ特徴量（保留） | 📋予定 | - |

---

## Phase 59.7: Stacking Meta-Learner ✅完了

### 実装内容（2026-01-17）

| 項目 | 内容 |
|------|------|
| OOF予測生成 | TimeSeriesSplit 5分割でメタ特徴量生成 |
| Meta-Learner | LightGBM（9次元メタ特徴量→最終予測） |
| StackingEnsemble | 2段階アーキテクチャ（ベースモデル→Meta-Learner） |

### 結果

| 指標 | Phase 59.6 | Phase 59.7 | 改善 |
|------|-----------|------------|------|
| F1スコア | 0.41 | **0.46** | **+12%** |
| Meta-Learner F1 | - | 0.46 | - |

### 保存モデル

```
models/production/
├── ensemble_full.pkl       (31MB)
├── ensemble_basic.pkl      (32MB)
├── stacking_ensemble.pkl   (32MB) ← 新規
└── meta_learner.pkl        (250KB) ← 新規
```

### 問題点

**StackingEnsembleは本番環境で使用されていない**
- ml_loader.pyがStackingモデルを認識しない
- feature_order.jsonにStacking定義がない
→ Phase 59.8で統合

---

## Phase 59.8: Stacking本番環境統合 📋予定

### 背景

Phase 59.7でStackingEnsembleを実装したが、本番環境では使用されていない。
本番環境に統合し、バックテストで性能検証を行う。

### モデル読み込み優先順位（統合後）

```
Level 0: stacking_ensemble.pkl (stacking_enabled=true時)
    ↓ 失敗時 or 無効時
Level 1: ensemble_full.pkl (ProductionEnsemble)
    ↓ 失敗時
Level 2: ensemble_basic.pkl
    ↓ 失敗時
Level 2.5: 個別モデル再構築
    ↓ 失敗時
Level 3: DummyModel
```

### 修正ファイル

| ファイル | 変更内容 |
|---------|---------|
| `config/core/feature_order.json` | Stackingレベル定義追加 |
| `src/core/orchestration/ml_loader.py` | Stackingロード処理追加 |
| `scripts/testing/checks.sh` | Stacking検証追加 |
| `scripts/testing/validate_ml_models.py` | Stacking検証追加 |

### 検証

```bash
# バックテスト実行
python3 main.py --mode backtest
python3 scripts/backtest/standard_analysis.py --from-ci --phase 59.8
```

---

## Phase 59.9: Meta-Learner強化 + OOF拡張 📋予定

### 改善内容

#### 1. Meta-Learnerパラメータ強化

| パラメータ | 現在 | 推奨 | 理由 |
|-----------|------|------|------|
| `n_estimators` | 50 | 100-150 | 学習容量増加 |
| `max_depth` | 4 | 6-8 | 複雑な相互作用表現 |
| `num_leaves` | 15 | 31-63 | 分割能力向上 |
| `feature_fraction` | なし | 0.8 | 過学習防止 |
| `bagging_fraction` | なし | 0.8 | 汎化性能向上 |

#### 2. OOF分割数増加

```python
# 現在
TimeSeriesSplit(n_splits=5)  # メタデータ80%使用

# 推奨
TimeSeriesSplit(n_splits=10)  # メタデータ90%使用
```

### 期待効果

- **F1スコア**: 0.46 → **0.49-0.51**

### 検証

バックテスト実行・性能比較

---

## Phase 59.10: 追加メタ特徴量 📋予定

### 追加メタ特徴量（9次元→18次元）

| 特徴量 | 計算式 | 役割 |
|--------|--------|------|
| `prob_diff_max_min` | max(p) - min(p) | 予測確実性 |
| `entropy` | -Σ p_i * log(p_i) | 予測不確実性 |
| `model_agreement` | 投票一致率 | モデル間合意度 |
| `prob_std` | std(all_proba) | モデル間バラツキ |
| `max_prob_gap` | max - 2nd_max | 最大と2番目の差 |
| その他4特徴量 | 相関・信頼度変動 | 補助特徴 |

### 期待効果

- **F1スコア**: 0.50 → **0.51-0.53**

### 検証

バックテスト実行・性能比較

---

## Phase 59 ML改善サマリー

| Phase | 内容 | F1目標 | 検証 |
|-------|------|--------|------|
| 59.7 | Stacking実装 | 0.46 | ✅完了 |
| 59.8 | 本番環境統合 | 0.46 | バックテスト |
| 59.9 | Meta-Learner強化 | 0.50 | バックテスト |
| 59.10 | メタ特徴量追加 | 0.52 | バックテスト |

---

## Phase 60 ロードマップ（予定）

| Phase | 内容 | 状態 |
|-------|------|------|
| 60.1 | 戦略見直し（レジーム閾値調整） | 📋予定 |
| 60.2 | SL指値非約定時の成行フォールバック | 📋予定 |
| 60.3 | CatBoost追加 + Optuna最適化 | 📋予定 |

---

### Phase 60.1: 戦略見直し 📋予定

#### 発見された課題（Phase 59.4-B分析）

| 課題 | 詳細 |
|------|------|
| **trending 0件** | ADX>25条件が厳しすぎる？ |
| **high_volatility 0件** | ATR比1.8%条件が厳しすぎる？ |
| **レジーム偏り** | 取引の88%がtight_range |

#### 検討内容

1. レジーム判定閾値の見直し
2. 低パフォーマンス戦略の改善または除外
3. 新戦略の検討（トレンド対応強化）

---

### Phase 60.2: SL指値非約定時の成行フォールバック 📋予定

#### 背景

Phase 59.6でSLを指値化（stop_limit）したが、急落時に指値が約定しないリスクがある。

#### 実装内容

| 項目 | 内容 |
|------|------|
| **トリガー条件** | SL発動後、一定時間経過しても約定しない場合 |
| **フォールバック** | stop_limit → 成行に切り替えて強制決済 |

---

### Phase 60.3: CatBoost追加 + Optuna最適化 📋予定

#### 内容

1. **CatBoost追加**: 4モデルアンサンブル化
2. **Meta-Learner Optuna最適化**: 50-100試行で最適パラメータ探索

#### 期待効果

- **F1スコア**: 0.52 → **0.55+**

---

## 保留タスク

| タスク | 優先度 | 備考 |
|--------|--------|------|
| 戦略分析とバックテストの乖離調査 | 低 | 戦略帰属ルールの影響 |
| Walk-Forward実装 | 中 | ML重み増加時に検討 |

---

## 関連ファイル

| ファイル | 内容 |
|---------|------|
| `docs/開発履歴/Phase_59.md` | Phase 59開発記録 |
| `config/core/features.yaml` | 機能トグル設定 |
| `config/core/thresholds.yaml` | 戦略重み・ML統合設定 |

---

**最終更新**: 2026年1月17日 - Phase 59.8計画（Stacking本番環境統合）

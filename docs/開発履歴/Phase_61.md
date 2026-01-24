# Phase 61: 戦略分析・改修

**期間**: 2026年1月24日〜
**目的**: レジーム判定の最適化とトレンド型戦略の活性化

---

## 背景

Phase 60.7完了時点で総損益¥86,639（PF 1.58）を達成したが、以下の課題が判明：

| 課題 | 詳細 | 影響 |
|------|------|------|
| **ADXTrendStrength赤字** | 7取引、勝率42.9%、¥-2,511損失 | 全体PFを低下 |
| **MACDEMACrossover発動0件** | 183日間で0取引 | トレンド型戦略が機能していない |
| **レジーム偏り** | tight_range 88.2%、trending 0% | 戦略多様性が活かされていない |

**根本原因**: `MarketRegimeClassifier`のハードコード閾値が不適切
- tight_range: BB幅 < 3% AND 価格変動 < 2% → 緩すぎて88%がここに吸収
- trending: ADX > 25 AND EMA傾き > 1% → 厳しすぎて0件

---

## Phase 61.1: レジーム判定閾値調整 ✅完了（失敗→ロールバック）

### 実施日
2026年1月24日

### 目標
- trending発生率: 0% → 5-15%
- tight_range発生率: 88% → 60-70%

---

### 実施内容

#### 1. thresholds.yamlにmarket_regimeセクション追加

```yaml
market_regime:
  tight_range:
    bb_width_threshold: 0.025      # 0.03→0.025（厳格化）
    price_range_threshold: 0.015   # 0.02→0.015（厳格化）
  trending:
    adx_threshold: 20              # 25→20（緩和）
    ema_slope_threshold: 0.007     # 0.01→0.007（緩和）
```

#### 2. MarketRegimeClassifier修正

`src/core/services/market_regime_classifier.py`を修正：
- ハードコード値を`get_threshold()`による設定ファイル読み込みに変更
- 4つの判定メソッドを修正

#### 3. Walk-Forward Validationバグ修正

CI検証中に発見したバグを修正（mode引数エラー）。

---

### バックテスト結果（失敗）

| 指標 | Phase 60.7 | Phase 61.1 | 変化 |
|------|-----------|-----------|------|
| **総損益** | ¥86,639 | ¥21,781 | **-75%** ❌ |
| **PF** | 1.58 | 1.13 | **-28%** ❌ |
| 勝率 | 54.8% | 50.6% | -4.2% |
| 取引数 | 347件 | 350件 | +3件 |

### レジーム分布（目標未達）

| レジーム | Phase 60.7 | 目標 | Phase 61.1 | 判定 |
|---------|-----------|------|-----------|------|
| tight_range | 88.2% | 60-70% | 72.6% | ⚠️ やや高い |
| trending | 0% | 5-15% | **0.6%** | ❌ 未達 |
| normal_range | - | - | 26.9% | - |

### 戦略別パフォーマンス

| 戦略 | 取引数 | 勝率 | 損益 |
|------|--------|------|------|
| ATRBased | 248件 | 50.0% | ¥+14,863 |
| StochasticReversal | 52件 | 53.8% | ¥+6,532 |
| BBReversal | 4件 | 75.0% | ¥+2,536 |
| DonchianChannel | 40件 | 47.5% | ¥-161 |
| ADXTrendStrength | 6件 | 50.0% | ¥-1,990 |
| MACDEMACrossover | **0件** | - | - |

---

### 失敗原因分析

1. **閾値変更の効果が限定的**
   - tight_range: 88%→72%（目標60-70%に近いが改善不十分）
   - trending: 0%→0.6%（目標5-15%に大幅未達）

2. **市場データの特性**
   - 2025年7-12月のBTC/JPYは下落トレンド
   - そもそもtrending判定に該当する期間が極めて少ない

3. **取引パターンの変化による悪影響**
   - 閾値変更により取引判断が変化
   - 結果的にPFが大幅低下

---

### ロールバック実施

**コミット**: `6031eaf8`

| パラメータ | Phase 61.1 | 復元値（Phase 60） |
|-----------|-----------|-------------------|
| tight_range.bb_width | 0.025 | **0.03** |
| tight_range.price_range | 0.015 | **0.02** |
| trending.adx | 20 | **25** |
| trending.ema_slope | 0.007 | **0.01** |

---

### ロールバック検証結果 ✅

**CI Run ID**: 21306359263（2026年1月24日）

| 指標 | Phase 60.7 | ロールバック後 | 一致 |
|------|-----------|---------------|------|
| **総損益** | ¥86,639 | **¥86,639** | ✅ |
| **PF** | 1.58 | **1.58** | ✅ |
| **勝率** | 54.8% | **54.8%** | ✅ |
| **取引数** | 347件 | **347件** | ✅ |

**結論**: Phase 60.7相当の性能に完全復元。ロールバック成功。

---

### 教訓

1. **レジーム閾値変更は高リスク**
   - 取引パターン全体に影響するため、小さな変更でも大きな結果差

2. **事前検証の重要性**
   - 本番適用前にローカルバックテストで効果を確認すべき

3. **市場依存性**
   - 閾値調整だけでは市場データの特性は変えられない
   - 2025年下半期はそもそもtrending期間が少なかった

---

### Gitコミット履歴

| コミット | 内容 |
|---------|------|
| `3f6f8bb2` | feat: Phase 61.1 レジーム判定閾値を設定ファイル化 |
| `48ed2a13` | fix: Walk-Forward Validationのmode引数エラーを修正 |
| `6031eaf8` | **revert: Phase 61.1 レジーム閾値をPhase 60オリジナルに復元** |

---

## Phase 61.2: コードベース整理 ✅完了

### 実施日
2026年1月24日〜25日

### 目的
バックテスト結果を待つ間にコードベースを整理し、不要なファイルを削除。

---

### 実施内容

#### 1. ログ整理

**削除対象**:
- `logs/crypto_bot.log.2026-01-14` 〜 `2026-01-20`（約197MB）
- `logs/ml/ab_test_*.log`、`ml_training_*.log`（約310MB）
- `logs/test*.log.*`（古いテストログ）

**削減効果**: 約500MB

#### 2. 不要モデル削除

Phase 59でStacking無効化が確定したため、以下を削除：

| ファイル | サイズ | 理由 |
|---------|--------|------|
| `models/production/stacking_ensemble.pkl` | 31MB | Stacking無効化済み |
| `models/production/meta_learner.pkl` | 364KB | Stacking無効化済み |

**削減効果**: 約31MB

#### 3. テスト整理

**削除したディレクトリ/ファイル**:

| 対象 | 理由 |
|------|------|
| `tests/manual/` | 壊れたスクリプト、必要時に再作成 |
| `tests/unit/analysis/` | 全テストスキップ |
| `tests/integration/test_phase_51_3_regime_strategy_integration.py` | 全テストスキップ |

**整理したテストファイル**:

| ファイル | 変更内容 |
|---------|---------|
| `tests/unit/features/test_feature_generator.py` | 14件のスキップテスト（旧Day2）削除 |
| `tests/unit/trading/test_anomaly_detector.py` | Phase 38削除機能のxfailテスト9件削除 |
| `tests/unit/trading/test_drawdown_manager.py` | 未実装機能のxfailテスト3件削除 |

**移動したファイル**:
- `tests/test_execution_service_simple.py` → `tests/unit/services/test_execution_service.py`

**xfailマーカー削除**:
- `@pytest.mark.xfail(False, reason="Phase 38対応済み")` を全削除（不要なマーカー）

#### 4. README更新

| ファイル | 内容 |
|---------|------|
| `models/README.md` | Stacking削除反映、構成更新 |
| `models/production/README.md` | Stackingファイル削除反映 |
| `models/training/README.md` | Git管理方針明確化 |
| `tests/README.md` | Phase 61更新、manual/削除反映 |
| `tests/unit/README.md` | テスト統計・構成更新 |

---

### テスト結果（整理後）

| カテゴリ | Before | After | 変更 |
|---------|--------|-------|------|
| trading/ xfailed | 12 | 1 | -11 |
| trading/ xpassed | 1 | 0 | -1 |
| trading/ passed | 437 | 437 | 維持 |
| features/ skipped | 14 | 0 | -14 |
| 全体 | 約1,200 | 約1,200 | 維持 |

---

### 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `tests/unit/trading/test_anomaly_detector.py` | 9テスト削除、xfailマーカー削除 |
| `tests/unit/trading/test_drawdown_manager.py` | 3テスト削除、xfailマーカー削除 |
| `tests/unit/features/test_feature_generator.py` | TestPhase517Day2NewFeaturesクラス削除 |
| `models/README.md` | Phase 61更新 |
| `models/production/README.md` | Stacking削除反映 |
| `models/training/README.md` | Git管理方針更新 |
| `tests/README.md` | Phase 61更新 |
| `tests/unit/README.md` | テスト統計更新 |

---

#### 5. デプロイ関連ファイル更新（2026年1月24日追加）

Phase 49からPhase 61へのメタデータ更新。

| ファイル | 変更内容 |
|---------|---------|
| `Dockerfile` | ✅完了済み（Phase 61メタデータ、tests/manual COPY削除） |
| `main.py` | docstring/argparse/起動ログをPhase 61に更新 |
| `pyproject.toml` | version 49.15.0→61.0.0、description更新 |
| `requirements.txt` | ヘッダーをv61・2026年1月に更新 |
| `CLAUDE.md` | Phase 61成果表更新、最終更新日更新 |
| `README.md` | Phase 61バッジ、開発状況にPhase 60-61追加 |
| `scripts/testing/validate_system.sh` | tests/manualを必須ディレクトリから削除 |
| `tests/unit/features/test_feature_generator.py` | 末尾空行削除（flake8修正） |

**品質チェック結果**:
- flake8/isort/black: PASS
- pytest: 1,214 passed（62.28%カバレッジ）
- システム整合性: 7項目チェック完了

#### 6. 運用ガイド・スクリプトドキュメント更新（2026年1月25日）

Phase 61整合性確保のためのドキュメント全面更新。

| ファイル | 変更内容 |
|---------|---------|
| `scripts/testing/validate_ml_models.py` | Phase参照59.8→61、パス参照scripts/ml/→scripts/testing/ |
| `scripts/testing/README.md` | 検証項目7→8項目、Stacking検証追加 |
| `scripts/README.md` | Phase 61版に全面更新、ディレクトリ構成反映 |
| `docs/運用ガイド/システム機能一覧.md` | Section 12追加、戦略/ML仕様更新（720→809行） |
| `docs/運用ガイド/システム要件定義.md` | 戦略構成・品質基準・レバレッジ更新 |
| `docs/運用ガイド/bitbank_APIリファレンス.md` | 日付更新 |
| `docs/運用ガイド/GCP運用ガイド.md` | 日付更新 |
| `docs/運用ガイド/税務対応ガイド.md` | 日付更新 |
| `docs/運用ガイド/統合運用ガイド.md` | 日付・実行時間・カバレッジ更新 |

**更新ポイント**:
- 戦略構成: レンジ型4 + トレンド型2（6戦略）明確化
- ML: ProductionEnsemble（動的重み・シード差別化）Phase 60.5仕様反映
- 品質基準: カバレッジ62%以上・checks.sh 12項目・約60秒
- Stacking: 無効化（stacking_enabled: false）の反映

**未更新（Phase 61.3以降）**:
- `src/` - ライブモードに影響
- `.github/` - CI/CDに影響
- `config/` - 設定ファイル（ライブモードに影響）

---

## Phase 61.3: ADXTrendStrength評価・対応 ❌中止

Phase 61.1失敗によりtrendingレジームが増加しなかったため、評価対象外。
現状維持（Phase 60.7設定）で運用継続。

---

## Phase 61.4: MACDEMACrossover発動改善 ❌中止

Phase 61.1失敗によりtrendingレジームが増加しなかったため、改善機会なし。
現状維持（Phase 60.7設定）で運用継続。

---

## 成功基準

| Phase | 指標 | 目標値 | 結果 |
|-------|------|--------|------|
| 61.1 | trending発生率 | ≥ 5% | ❌ 0.6%（未達） |
| 61.1 | tight_range発生率 | ≤ 70% | ⚠️ 72.6%（やや高い） |
| 61.1 | PF維持 | ≥ 1.50 | ❌ 1.13（大幅低下） |
| **61.1** | **ロールバック** | **Phase 60.7復元** | **✅ 成功（PF 1.58復元）** |
| **61.2** | **コードベース整理** | **品質チェックPASS** | **✅ 完了（ドキュメント更新含む）** |
| 61.3 | ADXTrendStrength評価 | - | ❌ 中止 |
| 61.4 | MACDEMACrossover改善 | - | ❌ 中止 |

---

## 技術的成果（Phase 61.1から継続）

### get_threshold()パターン導入

Phase 61.1でMarketRegimeClassifierに`get_threshold()`パターンを導入（コード自体は維持）：

1. **閾値変更時にコード修正不要**
   - thresholds.yamlを変更するだけで閾値調整可能

2. **設定の一元管理**
   - 全てのレジーム閾値が1箇所に集約

3. **デフォルト値はPhase 60オリジナル値に設定**
   - 安定動作を保証

---

## 結論

Phase 61.1のレジーム閾値調整は**失敗**。
- 閾値変更だけでは市場特性を変えられない
- PFが1.58→1.13に大幅低下（-75%損益）

**対応**: Phase 60オリジナル値にロールバックし、Phase 60.7相当の性能を維持。

今後のレジーム改善は、より慎重なアプローチ（ローカル事前検証、段階的変更）が必要。

---

**最終更新**: 2026年1月25日 - Phase 61.2完了（コードベース整理・ドキュメント全面更新）

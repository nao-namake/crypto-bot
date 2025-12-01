# 開発タスク管理（未達成のみ）

**目的**: Claude Codeに読み込ませ、続きの開発を実行するための未達成タスク管理

---

## 優先度一覧

| タスク | 優先度 | 状態 |
|-------|--------|------|
| Phase 56.5: 10万円増額・1ヶ月稼働 | 🔴高 | 24時間監視中 |
| Phase 57.5.3: Phase 56設定ロールバック検証 | 🔴高 | 180日バックテスト実行中 |
| Phase 57.6: 手数料・スプレッドシミュレーション | 🟡中 | 未着手 |
| Phase 58: Phase 57成果の本番反映 | 🟢低 | Phase 57完了後 |
| 5分足導入 | 🟢低 | 3ヶ月後判断 |

---

## Phase 56: 本番稼働安定化（継続中）

**目標**: 本番環境で安定稼働＋エントリー発生を確認

### Phase 56.2: Container crashゼロ達成（✅完了）
- [x] 自動タイムアウト無効化
- [x] docker-entrypoint.sh自動再起動対応
- [x] 稼働率99%達成（crashゼロ）

### Phase 56.3: GCPクリーンアップ（✅完了）
- [x] リビジョン削除（17→3個）
- [x] Dockerイメージ削除（31→9個）
- [x] 緊急停止ワークフロー作成

### Phase 56.4: 本番エントリーゼロ問題対応（✅完了）

**2025/12/01 デプロイ完了**

**修正内容**:
- [x] **56.4.0**: Atomic Entry補償ロジック追加（`atomic_entry_manager.py`, `executor.py`, `thresholds.yaml`）
- [x] **56.4.1**: Secret Manager `:3` → `:latest` 変更（`ci.yml`）
- [x] **56.4.2**: 証拠金API fallback強化（`monitor.py`）
- [x] **56.4.3**: 戦略条件緩和（**根本修正**）
  - `bb_reversal.py`: AND条件 → OR条件
  - `stochastic_reversal.py`: クロスオーバー必須 → オプション化
  - `atr_based.py`: 乖離度閾値緩和（0.25 → 0.15）
- [x] **56.4.4**: テスト100%成功・デプロイ完了

**期待効果**:
- エントリー: 0回/24h → 5-20回/24h
- holdシグナル: 100% → 50-70%
- BUY/SELLシグナル: 0% → 30-50%

**成功条件（24時間監視中）**:
- ⏳ エントリー発生確認（デプロイ後24時間監視必要）
- ⏳ API認証エラー削減確認
- ⏳ 証拠金維持率正常取得確認

### Phase 56.5: 10万円増額・1ヶ月稼働（Phase 56.4完了後）

**目標**: Phase 56.4完了後、本番環境で1ヶ月間安定稼働

- [ ] 証拠金: 2万円 → 10万円に変更
- [ ] 1ヶ月監視（稼働率99%・エントリー5-15回/日）

---

## Phase 57: 戦略最適化・勝率向上（ローカル検証のみ）

**目標**: ローカル環境でバックテスト・最適化を実施し、性能向上策を検証
**本番反映**: Phase 58で実施（Phase 57では本番に反映しない）

### 現状指標（2025/11/27バックテスト）

| 指標 | 現在値 | 目標値 |
|------|--------|--------|
| PF | 1.83 | ≥1.5（安定化） |
| 勝率 | 53.49% | ≥55% |
| 最大DD | 0.044% | ≤20% |
| 取引数 | 43件/7日 | 5-15回/日 |

### Phase 57.1: 戦略別パフォーマンス分析（✅完了）
- [x] `src/backtest/reporter.py` に `get_strategy_performance()` 実装
- [x] `src/trading/core/types.py` に `strategy_name` フィールド追加
- [x] `src/trading/risk/manager.py` で戦略名設定
- [x] バックテストレポートに戦略別パフォーマンス出力追加

### Phase 57.2: パラメータ最適化基盤（✅完了）
- [x] `scripts/optimization/backtest_integration.py` の `_execute_backtest()` 完成
- [x] subprocess方式への変更（信頼性向上）
- [x] JSONレポートからメトリクス抽出機能

### Phase 57.3: 検証バックテスト実行・不具合修正（✅完了）
- [x] 7日間バックテスト実行
- [x] 戦略別パフォーマンス出力の動作確認
- [x] JSONレポートに`strategy_performance`が正しく記録されているか確認
- [x] Phase 57.1/57.2の実装が正しく動作することを検証
- [x] **不具合修正**: StrategyManager統合シグナルの戦略名がすべて"StrategyManager"になる問題を修正
  - `strategy_manager.py`: `_combine_signals()`, `_integrate_consistent_signals()`で最高信頼度戦略名を設定
  - テスト更新（21テスト全パス）

**Phase 57.3 バックテスト結果**:
```
総取引: 48件
勝率: 約18.75%（9TP/34SL）
戦略別: ATRBased 46件, ADXTrendStrength 1件, StochasticReversal 1件
```

### Phase 57.4: レジーム別戦略選定の分析・修正（✅完了）

**問題点（Phase 57.3で発覚）**:
- tight_rangeレジームで97.9%のエントリー
- ATRBased戦略が96%を占有（46/48件）
- 他戦略（DonchianChannel、BBReversal等）がほぼ機能していない
- 勝率30.4%、PF 0.53と低迷

**実施内容**:
- [x] 各戦略のシグナル発生条件を確認・閾値調整
- [x] レジーム判定ロジックの確認・修正
- [x] ATRBasedエントリー条件調整
- [x] 6戦略の重み付け・有効化条件の修正
- [x] 7日間バックテストで効果検証（勝率21%・PF 0.53 → 要改善）

### Phase 57.5: プリセットシステム導入（✅完了）

**実装内容**（2025/12/01）:
- [x] プリセットYAML構造作成: `config/core/strategies/presets/`
- [x] `active.yaml`: プリセット選択・エイリアス設定（A=phase56, B=phase57_4）
- [x] `phase56.yaml`: Phase 56設定保存（勝率42.1%）
- [x] `phase57_4.yaml`: Phase 57.4設定保存（勝率21%）
- [x] `threshold_manager.py`にプリセット読み込み機能追加
- [x] 優先順位チェーン: runtime_overrides > preset > thresholds.yaml > default
- [x] `tests/conftest.py`でテスト環境のプリセット無効化
- [x] テスト全パス（1259件）・black/isort/flake8通過
- [x] 7日間バックテスト検証（勝率36%・PF 1.18・+7円）
- [x] Phase 56設定にロールバック（active_preset: phase56）

**効果**:
- 設定変更が1ファイル（active.yaml）で完結
- A/B/Cエイリアスで直感的な設定切り替え
- 過去設定への即座ロールバック可能

### Phase 57.5.3: Phase 56設定ロールバック検証（⏳進行中）⬅️ 今ここ

**状態**: 180日バックテスト GitHub Actions実行中（Run ID: 19805548309）

- [x] Phase 56設定にロールバック
- [x] 7日間バックテスト成功（システム動作確認）
- [ ] 180日バックテスト結果確認（CI実行中）
- [ ] 結果に基づく次フェーズ判断

### Phase 57.6: Optuna最適化実行（優先度MEDIUM・未着手）
- [x] ATRBased戦略最適化スクリプト作成: `scripts/optimization/phase57_strategy_optimizer.py`
- [ ] Phase 57.5.3完了後にOptuna最適化実行（5-10試行・約30分）
- [ ] 最適化対象: ATRBasedパラメータ（RSI閾値・BB閾値・ボラティリティ信頼度）
- [ ] 最適パラメータの特定と記録

### Phase 57.7: 手数料・スプレッドシミュレーション（優先度MEDIUM）
- [ ] bitbank手数料正確反映（Maker 0.05%・リベート -0.02%）
- [ ] スプレッドシミュレーション（1000-5000円変動）
- [ ] `src/core/execution/backtest_runner.py` 修正（既存実装確認・必要に応じて改善）

### Phase 57.8: ABテスト基盤構築（優先度LOW）
- [ ] `src/ab_testing/ab_test_controller.py` 新規作成
- [ ] `src/ab_testing/variant_manager.py` 新規作成
- [ ] `src/ab_testing/statistical_analyzer.py` 新規作成（t検定・Mann-Whitney U）
- [ ] `scripts/ab_testing/run_ab_test.py` 実行スクリプト
- [ ] `scripts/ab_testing/analyze_ab_results.py` 結果分析

### Phase 57 成功基準（ローカル検証）
- [ ] PF ≥ 1.5（180日バックテストで安定）
- [ ] 勝率 ≥ 55%
- [ ] 最大DD ≤ 20%
- [x] 戦略別パフォーマンスレポート生成可能（Phase 57.1で実装済み）
- [ ] Optuna最適化で有意なパラメータ改善

---

## Phase 58: Phase 57成果の本番反映（Phase 57完了後）

**目標**: Phase 57で検証した最適化パラメータを本番環境に反映

### 実施内容
- [ ] Phase 57で特定した最適パラメータを`config/core/thresholds.yaml`に反映
- [ ] 最適化されたMLモデルを本番デプロイ
- [ ] GCP Cloud Run更新
- [ ] 1週間監視・効果検証

**成功条件**:
- 勝率向上（53.49% → 55%以上）
- PF維持（≥1.5）
- 稼働率維持（≥99%）

---

## 5分足導入（3ヶ月後判断）

**検討条件**:
- 3ヶ月評価成功（月平均利益 ≥ 2,000円）
- バックテストで優位性実証

---

**📅 最終更新**: 2025年12月1日（Phase 57.5完了: プリセットシステム導入・Phase 56設定ロールバック・180日バックテストCI実行中）

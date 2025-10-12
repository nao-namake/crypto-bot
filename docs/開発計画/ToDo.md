# 暗号資産取引Bot - 未達成タスク管理

## 📋 このファイルの目的

**使用場面**:
- 今後の開発タスクの確認
- Phase 39以降の優先度判断
- 中長期的な機能拡張計画の把握

**ルール**:
- 未完了タスクのみ記載
- 達成済み情報は記載しない（開発履歴ドキュメント参照）
- 優先度に応じてタスクを分類
- 定期的にタスク状況を更新

---

## 🚨 **緊急タスク**（即座対応必須・2025/10/13発見）

### **Phase 38.8: 戦略統合ロジック緊急修正**（🔥🔥🔥 最優先・今日中）

**発見日**: 2025年10月13日
**発見方法**: ペーパートレード実行分析（第1サイクル）

**問題1: 戦略統合ロジックの致命的欠陥**
- **現状**: `_integrate_consistent_signals()`が**票数**で判定（`strategy_manager.py:314-322`）
  ```python
  # 現在の問題コード（strategy_manager.py:314-322）
  def _integrate_consistent_signals(self, signal_groups, all_signals, df):
      # 最も多いアクションを選択
      action_counts = {action: len(signals) for action, signals in signal_groups.items()}
      dominant_action = max(action_counts, key=action_counts.get)  # 票数で判定
  ```
- **具体例**（2025/10/13 06:40:36 ペーパートレード第1サイクル）:
  ```
  5戦略判定:
  - sell 2票（信頼度: 0.760, 0.651）→ 重み付け合計 1.411
  - hold 3票（信頼度: 0.150, 0.453, 0.489）→ 重み付け合計 1.092
  → 結果: 票数でholdが勝利（3票 > 2票）
  → 統合信頼度: 0.350（低信頼度）
  ```
- **正しい方法**: 信頼度の重み付け合計で判定すべき
  ```python
  # sell: 1.411 > hold: 1.092 → sellを選択すべき
  ```
- **影響**: 取引機会を大幅に逃している（GCPログでも同様の問題発生中）

**問題2: コンフリクト定義の不適切性**
- **現状**: `_has_signal_conflict()`がbuy vs sellのみをコンフリクトと定義（`strategy_manager.py:202-208`）
  ```python
  def _has_signal_conflict(self, signal_groups: Dict[str, List]) -> bool:
      has_buy = "buy" in signal_groups and len(signal_groups["buy"]) > 0
      has_sell = "sell" in signal_groups and len(signal_groups["sell"]) > 0
      return has_buy and has_sell  # hold vs sell/buy は検出されない
  ```
- **影響**: hold vs sell/buyケースで`_resolve_signal_conflict()`が呼ばれず、不適切な判定が発生

**問題3: ML学習データ問題**（Phase 39.1で対応）
- **現状**: `create_ml_models.py`がサンプルデータ（ランダムウォーク）で学習
- **結果**: ML信頼度0.749と高いが、実際の市場パターンを認識できず、holdと誤判定
- **影響**: ML予測が役に立たない状態

**修正内容**:
- [ ] **Step 1: `_integrate_consistent_signals()`を信頼度ベース判定に変更**
  - 票数判定を廃止
  - 各グループの重み付け信頼度合計を計算
  - 最高信頼度グループを選択
  - テスト追加（`tests/unit/strategies/test_strategy_manager.py`）
- [ ] **Step 2: `_has_signal_conflict()`の定義拡張**
  - buy vs sellだけでなく、2種類以上のアクションが存在する場合をコンフリクトと定義
  - `_resolve_signal_conflict()`で全アクションを信頼度ベースで比較
  - テスト追加
- [ ] **Step 3: 品質チェック実行**
  - `bash scripts/testing/checks.sh`で1,078テスト確認
  - 70.56%カバレッジ維持確認
- [ ] **Step 4: ペーパートレード再検証**（5-10分）
  - `bash scripts/management/run_safe.sh local paper`で動作確認
  - 戦略統合ロジックが信頼度ベースで動作することを確認
  - 取引機会が適切に捕捉されることを確認
- [ ] **Step 5: 本番デプロイ**
  - git commit & push
  - CI/CD自動デプロイ確認

**期待効果**:
- **取引機会大幅増加**: 高信頼度シグナルが適切に選択される
- **戦略信頼度適切反映**: 信頼度の高い戦略が優先される
- **取引頻度正常化**: 月100-200回の取引頻度回復

**推定時間**: 2-3時間
**優先度**: 🔥🔥🔥 **最優先・即時修正**

---

## 📊 **Phase 39以降: 運用最適化・監視体系強化**

### **📊 運用監視・可観測性拡張**
- [ ] **リアルタイム監視ダッシュボード**: 取引状況・パフォーマンス・リスク指標のWeb可視化
- [ ] **統合ログ分析システム**: 取引履歴分析・パターン検出・異常検知・予測精度追跡
- [ ] **Discord監視機能拡張**: リアルタイム統計・成績レポート・アラート体系強化
- [ ] **パフォーマンス統合分析**: backtest vs paper vs live 比較分析・予測精度検証
- [ ] **自動レポーティング**: 日次・週次・月次成績レポート・収益性分析・リスク評価

### **🔍 SL/TP配置監視・取引統計強化**（Phase 39優先推奨）
- [ ] **SL/TP配置状況分析スクリプト**: GCPログからSL/TP配置成功率集計・配置失敗原因分析（残高不足・API エラー等）・日次自動実行・Discord通知統合
- [ ] **未約定注文監視・アラート機能**: 定期実行（5分毎）TP/SL注文存在確認・価格乖離検出・長時間未約定アラート・Discord Critical通知・エントリー後必須チェック
- [ ] **取引統計・収益分析レポート**: TP約定数 vs SL約定数集計・勝率・平均利益/損失計算・手数料影響分析（手数料負け率・改善提案）・資金規模別シミュレーション・日次/週次/月次レポート自動生成

### **⚡ システムパフォーマンス向上**
- [ ] **ヘルスチェック機能拡張**: CPU・メモリ・ディスク使用率・API応答時間監視
- [ ] **キャッシュシステム最適化**: データ取得効率化・応答時間短縮・メモリ効率向上
- [ ] **並列処理最適化**: 特徴量計算・戦略実行・ML予測の並列化・処理時間短縮

---

## 🛡️ **セキュリティ・システム安定性強化**

### **🔐 セキュリティ機能拡張**
- [ ] **API認証強化**: 多要素認証・アクセス制御・権限管理・監査ログ
- [ ] **通信暗号化**: エンドツーエンド暗号化・機密データ保護・セキュア通信
- [ ] **脆弱性監査**: 依存関係チェック・セキュリティスキャン・定期監査

### **📝 型システム・コード品質完成**
- [ ] **MyPy完全対応**: 残り型エラー解消・型注釈強化・型安全性向上
- [ ] **Protocol適用拡大**: インターフェース統一・型安全性・拡張性向上
- [ ] **型チェックCI統合**: CI/CDパイプライン型チェック・品質ゲート強化

---

## 🎯 **標準取引機能拡張**（Phase 39推奨）

### **🤖 Phase 39: ML信頼度向上・包括改善**（Phase 38.8完了後）

**背景・目的**:
- **現在の問題**: ML信頼度0.749と高いが、サンプルデータ（ランダムウォーク）で学習しているため実際の市場パターンを認識できない
- **根本原因**: `create_ml_models.py:157-191`の`_generate_sample_data()`使用・実データ未使用
- **期待効果**: ML信頼度+40-70%向上・実市場パターン認識・予測精度大幅改善

**Phase 39.1: ML実データ学習システム実装**（🔥🔥 短期対応・1-2日・3-5時間）
- [ ] **Bitbank Public API統合**:
  - 過去180日BTC/JPY OHLCV データ収集機能（4h足・15m足）
  - `src/backtest/scripts/collect_historical_csv.py`パターン活用
  - データ品質チェック・欠損値処理・異常値除去
- [ ] **`create_ml_models.py`修正**:
  - `_generate_sample_data()`使用停止
  - 実データ読み込みパイプライン実装
  - CSVデータ → 特徴量生成 → ターゲット生成 → 学習
  - データ分割: Train 70% / Val 15% / Test 15%
- [ ] **品質チェック・検証**:
  - `bash scripts/testing/checks.sh`で1,078テスト確認
  - ML予測精度評価（F1スコア・精度・再現率）
  - ペーパートレードで実市場パターン認識確認
- [ ] **本番デプロイ**:
  - 新MLモデル`models/production/`保存
  - git commit & push・CI/CD自動デプロイ

**期待効果**: ML信頼度+15-25%向上・実市場パターン認識開始
**推定時間**: 3-5時間

**Phase 39.2: ターゲット生成改善**（🔥 中期対応・1-2日）
- [ ] **閾値最適化**: 0.3% → 0.5-1.0%（ノイズ削減）
- [ ] **3クラス分類検討**: BUY / HOLD / SELL（現在2クラス）
- [ ] **リスク・リワード比ベース**: TP/SL到達確率でラベル生成
- [ ] **複数時間軸検討**: 1h / 4h / 24h予測精度比較

**期待効果**: ML信頼度+10-15%向上
**推定時間**: 2-3時間

**Phase 39.3: 学習プロセス強化**（中期対応・1-2日）
- [ ] **Early Stopping追加**: `stopping_rounds=20`で過学習防止
- [ ] **Cross Validation強化**: `n_splits=3` → `n_splits=5+`
- [ ] **Train/Val/Test分割**: 70/15/15比率で性能評価

**期待効果**: ML信頼度+5-10%向上
**推定時間**: 2-3時間

**Phase 39.4: クラス不均衡対応**（中期対応・1-2日）
- [ ] **`class_weight='balanced'`実装**: LightGBM・XGBoost・RandomForest
- [ ] **SMOTE oversampling実装**: マイノリティクラス増強
- [ ] **Focal Loss検討**: 難しいサンプル重視

**期待効果**: ML信頼度+8-12%向上
**推定時間**: 2-3時間

**Phase 39.5: Hyperparameter Optimization**（中期対応・2-3日）
- [ ] **Optuna統合**: Bayesian最適化実装
- [ ] **最適化パラメータ**:
  - LightGBM: `learning_rate, max_depth, n_estimators, num_leaves`
  - XGBoost: `learning_rate, max_depth, n_estimators, min_child_weight`
  - RandomForest: `n_estimators, max_depth, min_samples_split`
- [ ] **目的関数**: F1スコア・Precision-Recall AUC最大化
- [ ] **Walk-forward testing**: 訓練90日・検証90日

**期待効果**: ML信頼度+5-8%向上
**推定時間**: 3-4時間

**Phase 39.6: Feature Engineering**（中期対応・3-5日）
- [ ] **Lag Features追加**: 過去N期間の特徴量（N=1,2,3,5,10）
- [ ] **Rolling Statistics追加**: 過去N期間の平均・標準偏差・最大・最小
- [ ] **Interaction Features追加**: RSI×ATR、MACD×Volume等
- [ ] **Time-based Features追加**: 曜日・時間帯・月初/月末フラグ

**期待効果**: ML信頼度+8-15%向上
**推定時間**: 5-7時間

**Phase 39.7: Model Ensemble Enhancement**（中期対応・2-3日）
- [ ] **Dynamic Weight Adjustment**: 直近性能ベース重み調整
- [ ] **Stacking実装**: メタモデル（LogisticRegression）追加
- [ ] **新モデル検討**: GradientBoosting・CatBoost追加

**期待効果**: ML信頼度向上（変動あり）
**推定時間**: 3-5時間

**Phase 39 Total Expected Impact**: ML信頼度+40-70%向上（累計）
**Phase 39 Total Estimated Time**: 15-20時間

---

### **💰 Phase 41: トレーリングストップ実装**（Phase 40完了後・中長期対応）

**背景・目的**:
- 現在の問題: 固定TP/SLでは含み益が消失する可能性（裁量トレードの「建値撤退」問題をbotで解決）
- プロスペクト理論: 含み益の消失＝心理的損失（実損失の2.5倍の痛み）をトレーリングSLで回避
- 小利益積み重ね戦略: 月100-200回 × 平均利益+2-3% × Kelly基準複利効果 = 年間+200-300%目標
- 期待効果: 平均利益額+10-20%向上 → Kelly基準複利効果でさらに加速

**Phase 41.1: Optuna最適化・最適パラメータ探索**:
- [ ] **トレーリングSL監視機能実装**: BacktestEngine拡張・含み益監視・SL価格動的更新シミュレーション
- [ ] **Optuna最適化実装**（180日データ・150試行）:
  - 探索空間: `activation_profit: 0.01-0.05`（1-5%）、`trailing_percent: 0.01-0.04`（1-4%）
  - 目的関数: シャープレシオ最大化（リスク調整後リターン重視）
  - 検証手法: Walk-forward testing（訓練90日・検証90日・過学習防止）
  - 最適パラメータ自動発見・統計的信頼性確保
- [ ] **性能指標計算**:
  - 勝率・平均利益額・最大ドローダウン・シャープレシオ
  - 固定TP/SLとの比較（勝率変化・利益額増加率・リスクリワード比）
  - 月間取引回数への影響分析（早期利確による機会損失評価）
- [ ] **最適パラメータ決定**: Optuna best_params保存・thresholds.yaml反映準備

**Phase 41.2: ライブシステム実装**:
- [ ] **execution層拡張**:
  - `update_trailing_stop_loss()メソッド`: 既存SLキャンセル → 新SL価格計算 → 新SL配置
  - `monitor_trailing_conditions()メソッド`: ポジション監視・トレーリング発動条件判定
  - 定期実行統合（5分間隔判定サイクル内で実行）
- [ ] **bitbank API統合**:
  - `cancel_order()` + `create_stop_loss_order()`連携
  - エラーハンドリング強化（キャンセル失敗・再配置失敗対応）
  - トランザクション整合性確保（キャンセル成功後のみ新規配置）
- [ ] **Discord通知統合**:
  - トレーリング開始通知（「含み益X%到達・トレーリングSL開始」）
  - SL更新通知（「SL価格をY円に更新・利益Z%確保」）
  - トレーリングSL発動通知（「トレーリングSL発動・実現利益+X%」）
- [ ] **設定ファイル更新**:
  - features.yaml: `enabled: true`に変更
  - thresholds.yaml: `enable_trailing: true`に変更
  - バックテスト最適値を反映

**Phase 41.3: ペーパートレード検証**:
- [ ] **1-2週間実動作確認**: トレーリングSL動作・Discord通知・エラーハンドリング検証
- [ ] **効果測定**: 平均利益額・勝率・建値撤退回避効果の実測
- [ ] **問題検出・修正**: バグ修正・パラメータ微調整・運用安定化

**Phase 41.4: ライブトレード適用**:
- [ ] **段階的有効化**: 初回1-2取引で慎重確認 → 問題なければ全取引で有効化
- [ ] **継続監視**: 月次効果測定・パラメータ調整・改善継続

**技術仕様案**:
```python
# ExecutionService新メソッド
async def update_trailing_stop_loss(
    position: Dict,
    current_price: float,
    trailing_percent: float = 0.02  # thresholds.yamlから取得
) -> bool:
    """
    トレーリングSL更新

    ロジック:
    1. 既存SL注文キャンセル（bitbank API）
    2. 新SL価格計算（現在価格 × (1 - trailing_percent)）
    3. 新SL注文配置（stop_limit注文・Phase 37.5.2仕様準拠）
    4. Discord通知（SL更新・利益確保額）
    """
```

**期待される成果**:
- 「建値撤退問題」の完全解決
- 平均利益額+10-20%向上
- Kelly基準複利効果との相乗効果（年間収益+200-300%目標への貢献）
- プロスペクト理論の実装（含み益の心理的損失回避）

### **🔬 Phase 40: Optuna包括最適化**（Phase 39完了後）

**背景・目的**:
- 現在のシステム: 手動調整された50-80パラメータ（戦略閾値・リスク管理・ML統合・モデル設定）
- 問題点: 最適値が不明・相互作用未考慮・局所最適の可能性
- 解決策: Optunaベイズ最適化で統計的に最適なパラメータセット発見
- 期待効果: シャープレシオ+20-40%向上・年間収益+50-100%改善

**Phase 40.1: リスク管理パラメータ最適化**（10-15パラメータ）:
- [ ] **Optuna最適化実装**（180日データ・200試行）:
  - TP比率: `default_ratio: 1.5-3.5`（現在2.5）
  - 適応型ATR倍率: `low: 2.0-3.0, normal: 1.5-2.5, high: 1.0-2.0`（現在2.5/2.0/1.5）
  - 最小SL距離: `min_distance.ratio: 0.005-0.02`（現在0.01）
  - スリッページ: `execution_slippage: 0.001-0.005`（現在0.003）
  - 指値注文: `high_confidence_threshold: 0.6-0.85, price_improvement_ratio: 0.0001-0.0005`
  - タイムアウト: `timeout_minutes: 3-10`（現在5分）
- [ ] **目的関数**: シャープレシオ最大化（リスク調整後リターン重視）
- [ ] **検証手法**: Walk-forward testing（訓練120日・検証60日・過学習防止）
- [ ] **最適パラメータ保存**: `config/optuna_results/phase40_1_risk_management.json`

**Phase 40.2: 戦略パラメータ最適化**（25-35パラメータ）:
- [ ] **Optuna最適化実装**（180日データ・300試行）:
  - **ATRBased戦略**: RSI閾値 `oversold: 20-40, overbought: 60-80`（現在35/65）、BB閾値 `oversold: 0.1-0.5, overbought: 0.5-0.9`（現在0.3/0.7）
  - **MochipoyAlert戦略**: RSI閾値 `bullish: 50-70, bearish: 30-50`、BB幅閾値 `expansion: 0.01-0.05`、EMA乖離率 `buy_threshold: 0.01-0.05`
  - **DonchianChannel戦略**: ブレイクアウト閾値 `breakout_threshold: 0.001-0.005`（現在0.002）、リバーサル閾値 `reversal_threshold: 0.02-0.10`（現在0.05）
  - **ADXTrend戦略**: ADX閾値 `strong: 20-35, moderate: 12-20, weak: <12`（現在25/15）、DI交差閾値 `di_crossover_threshold: 0.3-1.0`（現在0.5）
  - **MultiTimeframe戦略**: 時間軸重み `tf_4h_weight: 0.5-0.8, tf_15m_weight: 0.2-0.5`（現在0.6/0.4）、トレンド強度閾値 `tf_4h_min_strength: 0.001-0.005`（現在0.002）
- [ ] **最適パラメータ保存**: `config/optuna_results/phase40_2_strategies.json`

**Phase 40.3: ML統合・戦略重み最適化**（12-18パラメータ）:
- [ ] **Optuna最適化実装**（180日データ・250試行）:
  - **ML統合重み**: `strategy_weight: 0.5-0.9, ml_weight: 0.1-0.5`（現在0.7/0.3）、`agreement_bonus: 1.0-1.5`（現在1.2）、`disagreement_penalty: 0.5-0.9`（現在0.7）、`high_confidence_threshold: 0.7-0.9`（現在0.8）、`min_ml_confidence: 0.4-0.8`（現在0.6）
  - **5戦略重み配分**（合計1.0に正規化）: `weight_atr_based: 0.1-0.4`、`weight_mochipoy: 0.1-0.4`、`weight_multi_timeframe: 0.1-0.4`、`weight_donchian: 0.05-0.3`、`weight_adx_trend: 0.05-0.3`
  - **信頼度閾値**: `high: 0.4-0.6, medium: 0.25-0.4, low: 0.15-0.3`
- [ ] **最適パラメータ保存**: `config/optuna_results/phase40_3_ml_integration.json`

**Phase 40.4: MLモデルハイパーパラメータ最適化**（15-25パラメータ）:
- [ ] **Optuna最適化実装**（180日データ・各モデル150試行）:
  - **LightGBM**: `num_leaves: 20-50, learning_rate: 0.01-0.1, n_estimators: 50-200`、`max_depth: 3-10, min_child_samples: 10-50`、`feature_fraction: 0.7-1.0, bagging_fraction: 0.7-1.0`
  - **XGBoost**: `max_depth: 3-10, learning_rate: 0.01-0.1, n_estimators: 50-200`、`min_child_weight: 1-10, subsample: 0.6-1.0, colsample_bytree: 0.6-1.0`
  - **RandomForest**: `n_estimators: 50-200, max_depth: 5-15`、`min_samples_split: 2-10, min_samples_leaf: 1-5`
  - **アンサンブル重み**: `lgbm: 0.3-0.7, xgb: 0.2-0.5, rf: 0.1-0.3`（現在0.5/0.3/0.2）
- [ ] **目的関数**: 検証データF1スコア最大化
- [ ] **週次ML学習統合**: 最適ハイパーパラメータ適用
- [ ] **最適パラメータ保存**: `config/optuna_results/phase40_4_ml_models.json`

**Phase 40.5: 統合検証・本番適用**:
- [ ] **バックテスト総合検証**: Phase 40.1-40.4の最適パラメータ統合・180日検証
- [ ] **性能指標計算**:
  - シャープレシオ・最大ドローダウン・勝率・平均利益額
  - 最適化前との比較（改善率算出）
  - 月間取引回数・リスクリワード比
- [ ] **ペーパートレード検証**: 2週間実動作確認・最適化効果実測
- [ ] **段階的ライブ適用**: 初回1週間慎重監視 → 問題なければ全面適用
- [ ] **thresholds.yaml更新**: 全最適パラメータ反映・バックアップ保存

**技術仕様案**:
```python
# Phase 39 Optuna最適化スクリプト
def objective_phase39_1(trial):
    """リスク管理パラメータ最適化"""
    params = {
        "tp_ratio": trial.suggest_float("tp_ratio", 1.5, 3.5),
        "atr_low": trial.suggest_float("atr_low", 2.0, 3.0),
        "atr_normal": trial.suggest_float("atr_normal", 1.5, 2.5),
        "atr_high": trial.suggest_float("atr_high", 1.0, 2.0),
        "min_sl_distance": trial.suggest_float("min_sl_distance", 0.005, 0.02),
        "execution_slippage": trial.suggest_float("execution_slippage", 0.001, 0.005),
    }
    # バックテスト実行
    result = run_backtest_with_params(params, start="2024-04-01", end="2024-10-01")
    return result["sharpe_ratio"]  # シャープレシオ最大化

# Walk-forward testing
study = optuna.create_study(direction="maximize")
study.optimize(objective_phase39_1, n_trials=200)
```

**期待される成果**:
- **シャープレシオ+20-40%向上**: リスク調整後リターン最大化
- **年間収益+50-100%改善**: 最適パラメータによる収益性向上
- **勝率+5-10%向上**: 戦略パラメータ最適化
- **最大ドローダウン-20-30%削減**: リスク管理最適化
- **統計的信頼性確保**: 感覚ではなくデータドリブンな設定

**Phase 40完了後の目標**:
- 年間収益率+300-500%達成（Kelly基準複利効果込み）
- シャープレシオ2.0以上（機関投資家レベル）
- 最大ドローダウン15%以下（リスク管理徹底）
- 月間取引回数100-200回維持（高頻度小利益戦略）

### **🕐 Phase 42: 5分足追加・3軸マルチタイムフレーム戦略**（Phase 38.3完了後）

**背景・目的**:
- 現在の問題: 5分間隔実行だが4時間足・15分足の2軸のみ → 5分間で新情報が少ない
- 5分足の必要性: 5分間隔判定なら5分足を活用して直近市場状況を反映
- 期待効果: エントリー精度向上・ブレイクアウト早期捕捉・偽シグナル削減
- リスク: ノイズ増加・オーバーフィッティング・複雑性増加

**Phase 42.1: 5分足補助指標実装（保守的アプローチ）**:
- [ ] **5分足データ取得機能追加**: DataPipeline拡張・5分足OHLCV取得・キャッシュ対応
- [ ] **5分足分析ロジック実装**:
  - EMA5/EMA10クロス検出（超短期トレンド）
  - RSI過買い・過売り判定
  - 価格変動率計算（急激な動き検出）
  - モメンタム判定（1: 買い、-1: 売り、0: ニュートラル）
- [ ] **MultiTimeframe戦略拡張（3軸構成）**:
  - 4時間足: トレンド方向（60%重み） ← 変更なし
  - 15分足: エントリータイミング（30%重み） ← 変更なし
  - **5分足: 最終確認フィルター（10%重み）** ← 新規追加
  - フィルターモード実装:
    - 5分足逆シグナル → 信頼度×0.8（20%ペナルティ）
    - 5分足同シグナル → 信頼度×1.1（10%ボーナス）
- [ ] **thresholds.yaml設定追加**:
  ```yaml
  dynamic_confidence:
    strategies:
      multi_timeframe_3axis:
        tf_4h_weight: 0.5
        tf_15m_weight: 0.3
        tf_5m_weight: 0.1          # 補助的役割
        tf_5m_filter_mode: true    # フィルターモード有効
        tf_5m_penalty: 0.8         # 逆シグナル時ペナルティ
        tf_5m_bonus: 1.1           # 同シグナル時ボーナス
  ```

**Phase 42.2: バックテスト検証**（180日データ）:
- [ ] **効果測定**:
  - 2軸構成 vs 3軸構成の比較
  - 勝率・平均利益額・シャープレシオの変化
  - エントリー精度・偽シグナル削減効果
  - ブレイクアウト捕捉率向上
- [ ] **ノイズ影響評価**:
  - 5分足ノイズによる誤判定率
  - オーバーフィッティング検出（訓練vs検証性能）
  - レンジ相場 vs トレンド相場での効果差
- [ ] **最適パラメータ探索**:
  - 5分足重み: 0.05-0.20の範囲で最適値探索
  - ペナルティ/ボーナス比率の調整
  - フィルター閾値の最適化

**Phase 42.3: ペーパートレード検証**:
- [ ] **1-2週間実動作確認**: 3軸統合動作・5分足データ取得・フィルター効果検証
- [ ] **効果測定**: エントリー精度・信頼度変動・取引回数への影響分析
- [ ] **問題検出・修正**: バグ修正・パラメータ微調整・ノイズ対策

**Phase 42.4: 段階的ライブ適用**:
- [ ] **効果確認時のみ有効化**: バックテスト・ペーパーで明確な改善確認後のみ
- [ ] **継続監視**: 月次効果測定・性能劣化検出・必要に応じてロールバック

**Phase 42.5（オプション）: 3軸対等統合**:
- [ ] **Phase 42.1-42.4で効果確認できた場合のみ実施**:
  - 5分足を対等な軸として扱う（20%重み）
  - フィルターモード解除
  - 3軸を統合した信頼度計算
  ```python
  weighted_score = (
      tf_4h_signal * 0.5 +    # 50%
      tf_15m_signal * 0.3 +   # 30%
      tf_5m_signal * 0.2      # 20%
  )
  ```

**技術仕様案**:
```python
# MultiTimeframe戦略拡張
def _analyze_5m_momentum(self, df: pd.DataFrame) -> int:
    """
    5分足モメンタム分析

    Returns:
        1: 買いモメンタム
       -1: 売りモメンタム
        0: ニュートラル
    """
    current_price = float(df["close"].iloc[-1])
    ema5 = float(df["ema_5"].iloc[-1])
    ema10 = float(df["ema_10"].iloc[-1])
    rsi = float(df["rsi_14"].iloc[-1])

    # EMAクロス判定
    if ema5 > ema10 and current_price > ema5:
        momentum = 1
    elif ema5 < ema10 and current_price < ema5:
        momentum = -1
    else:
        momentum = 0

    # RSIフィルター（極端な場合は逆張り警告）
    if rsi > 70:
        momentum = min(momentum, 0)  # 買いシグナル無効化
    elif rsi < 30:
        momentum = max(momentum, 0)  # 売りシグナル無効化

    return momentum

def _make_3tf_decision(
    self, tf_4h_signal: int, tf_15m_signal: int, tf_5m_signal: int, df: pd.DataFrame
) -> Dict[str, Any]:
    """3軸統合判定（Phase 42.1: フィルターモード）"""
    # 基本判定: 4H + 15M（従来通り）
    base_decision = self._make_2tf_decision(tf_4h_signal, tf_15m_signal, df)

    # 5分足フィルター適用（Phase 42.1）
    if base_decision['action'] != 'hold':
        tf_5m_penalty = get_threshold(
            "dynamic_confidence.strategies.multi_timeframe_3axis.tf_5m_penalty", 0.8
        )
        tf_5m_bonus = get_threshold(
            "dynamic_confidence.strategies.multi_timeframe_3axis.tf_5m_bonus", 1.1
        )

        # 5分足で逆シグナル → ペナルティ
        if tf_5m_signal == -base_decision['action']:
            base_decision['confidence'] *= tf_5m_penalty
        # 5分足で同シグナル → ボーナス
        elif tf_5m_signal == base_decision['action']:
            base_decision['confidence'] *= tf_5m_bonus

    return base_decision
```

**期待される成果**:
- エントリー精度+5-10%向上（5分足による直近市場反映）
- ブレイクアウト早期捕捉（15分足より5-10分早い検出）
- 偽シグナル削減（5分足フィルターによる誤判定防止）
- 月間取引回数への影響最小（フィルターモードのため）

**成功条件**:
- バックテストでシャープレシオ+5%以上向上
- ペーパートレードで勝率+3%以上向上
- オーバーフィッティングなし（訓練vs検証性能差<5%）

**失敗時の対応**:
- 効果なしまたは性能劣化 → Phase 42ロールバック・2軸構成維持
- ノイズ増加検出 → 5分足重みをさらに削減（0.05以下）またはフィルター閾値調整

### **💰 高度なポジション管理**（Phase 43以降）
- [ ] **部分利確システム**: position層拡張・ポジション分割決済・段階的利確・リスク調整・収益最適化
- [ ] **ポートフォリオ最適化**: 複数ポジション統合管理・相関分析・全体最適化

### **📈 注文システム高度化**
- [ ] **OCO注文実装**: One-Cancels-Other・利確/損切り同時設定・注文管理効率化
- [ ] **ブラケット注文**: エントリー時の自動TP/SL設定・リスク管理自動化
- [ ] **注文価格戦略**: 板情報活用・最適価格計算・約定率向上・スリッページ最小化

---

## 🧠 **ML・AI機能拡張**

### **🔄 Optuna包括最適化システム**（→ Phase 40参照）
**注**: Optuna最適化の詳細は上記「Phase 40: Optuna包括最適化」を参照してください。
- Phase 40.1: リスク管理パラメータ最適化（TP比率・ATR倍率・スリッページ等）
- Phase 40.2: 戦略パラメータ最適化（5戦略の閾値・判定基準等）
- Phase 40.3: ML統合・戦略重み最適化（ML/戦略重み・信頼度閾値等）
- Phase 40.4: MLモデルハイパーパラメータ最適化（LightGBM/XGBoost/RF）
- Phase 40.5: 統合検証・本番適用

### **🤖 機械学習高度化**
- [ ] **特徴量エンジニアリング**: 新特徴量開発・重要度分析・相関除去・精度向上
- [ ] **MLハイパーパラメータ最適化**: LightGBM/XGBoost/RF自動調整・グリッドサーチ・ベイズ最適化・性能向上
- [ ] **モデルアンサンブル拡張**: 新モデル追加・重み最適化・予測精度向上
- [ ] **深層学習モデル**: LSTM・Transformer・時系列予測・市場レジーム分析

### **📊 戦略システム拡張**
- [ ] **新戦略開発**: 市場中立戦略・ペア取引・統計的裁定・アルファ探索
- [ ] **A/Bテストフレームワーク**: 戦略比較・パフォーマンス評価・最適化
- [ ] **動的戦略重み調整**: 市場環境適応・成績連動・リアルタイム最適化

---

## 🌐 **システム拡張・スケーラビリティ**

### **💱 マルチアセット対応**
- [ ] **ETH/JPY対応**: イーサリアム取引・ポートフォリオ分散・リスク軽減
- [ ] **複数通貨ペア同時運用**: BTC・ETH・XRP同時取引・相関分析・機会拡大
- [ ] **通貨間アービトラージ**: 価格差利用・リスクフリー収益・効率向上

### **🔧 インフラ・運用拡張**
- [ ] **マルチリージョン対応**: 冗長化・災害対策・可用性向上・パフォーマンス分散
- [ ] **自動バックアップシステム**: データ保護・災害復旧・継続性確保
- [ ] **運用自動化**: 定期メンテナンス・データクリーンアップ・システム最適化

---

## 💡 **改善提案・中長期展望**（Phase 39以降）

### **📈 短期改善（3-6ヶ月）**
- [ ] **統合分析ダッシュボード**: backtest・paper・liveの統合監視・差異分析・精度検証
- [ ] **CSVデータ自動更新**: cron定期実行・API→CSV変換・データ鮮度維持・品質保証
- [ ] **リアルタイム通知拡張**: Slack・Email・SMS統合・緊急アラート・運用効率化

### **🚀 中長期拡張（6-12ヶ月）**
- [ ] **UI/UX開発**: Web管理画面・リアルタイムダッシュボード・モバイル監視アプリ・操作性向上
- [ ] **高度分析機能**: VaR計算・ストレステスト・シナリオ分析・リスク管理高度化
- [ ] **税務・レポート機能**: 詳細損益計算・確定申告支援・パフォーマンス分析・合規対応

---

## 🎯 **開発優先度指針**（2025/10/13更新）

### **🚨 緊急対応（今日中・2-3時間）**
1. **Phase 38.8: 戦略統合ロジック緊急修正** 🔥🔥🔥
   - 戦略統合を票数判定 → 信頼度ベース判定に変更
   - コンフリクト定義拡張（hold vs sell/buy含む）
   - 取引機会大幅増加・戦略信頼度適切反映

### **🔥 最優先（短期対応・1-2日・3-5時間）**
1. **Phase 39.1: ML実データ学習システム実装** 🔥🔥
   - Bitbank Public API統合・180日実データ収集
   - サンプルデータ廃止・実市場パターン学習
   - ML信頼度+15-25%向上・実市場認識開始

### **🔥 高優先度（中期対応・3-5日・15-20時間）**
1. **Phase 39.2-39.7: ML包括改善** 🔥
   - ターゲット生成改善・クラス不均衡対応・Optuna最適化・特徴量エンジニアリング
   - ML信頼度+40-70%向上（累計）・予測精度大幅改善

### **⚡ 中優先度（中長期対応・1-2週間・20-30時間）**
1. **Phase 40: Optuna包括最適化** ⚡
   - 50-80パラメータ最適化（リスク管理・戦略・ML統合・モデル）
   - シャープレシオ+20-40%・年間収益+50-100%改善
2. **Phase 41: トレーリングストップ実装** ⚡
   - バックテスト検証 → 実装 → ペーパー検証 → ライブ適用
   - 平均利益額+10-20%向上・建値撤退問題解決
3. **Phase 42: 5分足追加・3軸マルチタイムフレーム戦略** ⚡
   - エントリー精度+5-10%向上・ブレイクアウト早期捕捉

### **🔧 低優先度（Phase 43以降）**
1. **部分利確システム**: position層拡張・リスク管理・収益安定化
2. **OCO・ブラケット注文**: execution層拡張・高度な注文システム
3. **運用監視・ダッシュボード**: 現行システムの可視化・パフォーマンス追跡
4. **セキュリティ強化**: 企業級セキュリティ・監査対応
5. **マルチアセット対応**: ETH/JPY・複数通貨ペア・ポートフォリオ分散

### **🔮 将来拡張（Phase 43以降）**
1. **UI/UX開発**: Web管理画面・モバイルアプリ・操作性向上
2. **税務・レポート機能**: 確定申告支援・詳細分析・合規対応
3. **高度分析機能**: VaR計算・ストレステスト・リスク分析
4. **深層学習モデル**: LSTM・Transformer・時系列予測

---

**📊 実装順序のロジック**:
1. **Phase 38.8（緊急）**: 戦略統合ロジック修正で取引機会即座回復
2. **Phase 39.1（短期）**: ML実データ学習でML予測精度改善開始
3. **Phase 39.2-39.7（中期）**: ML包括改善で予測精度大幅向上
4. **Phase 40（中長期）**: 全パラメータ最適化で収益最大化
5. **Phase 41（中長期）**: トレーリングストップで利益額向上
6. **Phase 42+**: 継続的改善・機能拡張

**🎯 期待される段階的効果**:
- **即座（Phase 38.8完了後）**: 取引機会回復・取引頻度正常化
- **1週間後（Phase 39.1完了後）**: ML信頼度+15-25%・実市場認識
- **2-3週間後（Phase 39完了後）**: ML信頼度+40-70%・予測精度大幅改善
- **1-2ヶ月後（Phase 40完了後）**: シャープレシオ+20-40%・年間収益+50-100%
- **2-3ヶ月後（Phase 41・42完了後）**: 平均利益額+10-20%・エントリー精度+5-10%

---

**最終更新**: 2025年10月13日 - Phase 38.8緊急タスク追加・Phase 39 ML改善再構成・実装順序最適化

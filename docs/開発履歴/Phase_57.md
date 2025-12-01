# Phase 57 - 戦略最適化・PF1.5以上安定化

**期間**: 2025/11/30〜
**目標**: ローカル環境で戦略最適化・勝率向上を検証（本番反映はPhase 58）

---

## 現状指標（2025/11/27バックテスト）

| 指標 | 現在値 | 目標値 |
|------|--------|--------|
| PF | 1.83 | ≥1.5（安定化） |
| 勝率 | 53.49% | ≥55% |
| 最大DD | 0.044% | ≤20% |
| 取引数 | 43件/7日 | 5-15回/日 |

---

## Phase 57.1 - 戦略別パフォーマンス分析機能（完了）

**実施日**: 2025/11/30

### 問題

バックテスト結果で戦略名が`"unknown"`として記録され、6戦略それぞれの寄与度が可視化できない。

### 根本原因

1. `TradeEvaluation`データクラスに`strategy_name`フィールドがない
2. `IntegratedRiskManager.evaluate_trade_opportunity()`で戦略名が設定されていない
3. バックテストレポートに戦略別パフォーマンス出力がない

### 修正内容

#### 1. TradeEvaluationにstrategy_nameフィールド追加

**ファイル**: `src/trading/core/types.py`

```python
@dataclass
class TradeEvaluation:
    # 既存フィールド...
    strategy_name: Optional[str] = None  # Phase 57.1追加
```

#### 2. IntegratedRiskManagerで戦略名を設定

**ファイル**: `src/trading/risk/manager.py`

```python
# 戦略名取得
strategy_name_extracted = (
    strategy_signal.get("strategy_name", "unknown")
    if isinstance(strategy_signal, dict)
    else getattr(strategy_signal, "strategy_name", "unknown")
)

evaluation = TradeEvaluation(
    # 既存フィールド...
    strategy_name=strategy_name_extracted,  # Phase 57.1追加
)
```

#### 3. TradeTrackerにget_strategy_performance()追加

**ファイル**: `src/backtest/reporter.py`

```python
def get_strategy_performance(self) -> Dict[str, Dict[str, Any]]:
    """
    Phase 57.1: 戦略別パフォーマンス集計

    Returns:
        戦略別パフォーマンス辞書（勝率・PF・平均損益等）
    """
```

#### 4. バックテストレポートに戦略別パフォーマンス出力追加

**ファイル**: `src/backtest/reporter.py`

- バックテスト終了時に戦略別パフォーマンスをログ出力
- JSONレポートにも`strategy_performance`を追加

### 期待効果

| 指標 | 修正前 | 修正後 |
|------|--------|--------|
| 戦略名記録 | "unknown" | 実際の戦略名（atr_based等） |
| パフォーマンス可視化 | 不可 | 6戦略別に可視化 |
| 最適化判断 | 全体のみ | 戦略別に判断可能 |

### テスト結果

- 49件のテストPASS
- 動作確認OK（TradeEvaluation.strategy_name設定確認、get_strategy_performance()出力確認）

### 修正ファイル

1. `src/trading/core/types.py` - strategy_nameフィールド追加
2. `src/trading/risk/manager.py` - 戦略名設定追加
3. `src/backtest/reporter.py` - get_strategy_performance()追加、レポート出力追加

---

## Phase 57.2 - パラメータ最適化基盤完成（完了）

**実施日**: 2025/11/30

### 問題

`scripts/optimization/backtest_integration.py`の`_execute_backtest()`メソッドが未実装のため、Optunaハイブリッド最適化が機能しない。

### 根本原因

1. TradingOrchestratorの直接呼び出しは複雑な非同期処理・初期化が必要で信頼性が低い
2. バックテスト結果（JSON）からのパフォーマンス指標抽出が未実装

### 修正内容

#### 1. subprocess方式への変更

**ファイル**: `scripts/optimization/backtest_integration.py`

```python
async def _execute_backtest(self, config_path: Path) -> float:
    """
    Phase 57.2完成: subprocessでmain.py --mode backtest実行
    """
    # 1. 設定ファイルバックアップ・上書き
    # 2. subprocessでバックテスト実行（BACKTEST_DAYS環境変数）
    # 3. 設定ファイル復元
    # 4. JSONレポートからシャープレシオ抽出
```

#### 2. JSONからのメトリクス抽出

```python
def _extract_metrics_from_json(self, json_path: str) -> float:
    """
    Phase 57.2: JSONレポートからシャープレシオを計算
    - performance_metricsから取引統計取得
    - 疑似リターン配列構築
    - シャープレシオ計算
    """
```

#### 3. エラー時のクリーンアップ

```python
def _restore_config(self, backup_path, original_path, temp_path) -> None:
    """設定ファイル復元（エラー時のクリーンアップ）"""
```

### 技術的詳細

| 項目 | 実装 |
|------|------|
| バックテスト実行 | subprocess.run（子プロセス） |
| パラメータ注入 | thresholds.yaml一時上書き |
| 結果抽出 | JSONレポートから自動抽出 |
| タイムアウト | 期間に応じて動的調整（最低5分） |
| エラー復帰 | 設定ファイル自動復元 |

### 最適化対象パラメータ

**Phase 57.2以降で最適化可能**:
- ML統合（7パラメータ）
- 信頼度閾値（5パラメータ）
- TP/SL（レジーム別・6パラメータ）

### テスト結果

- flake8: PASS
- インポートテスト: PASS

### 修正ファイル

1. `scripts/optimization/backtest_integration.py` - _execute_backtest()完全実装

---

## Phase 57.3 - 検証バックテスト実行・不具合修正（完了）

**実施日**: 2025/12/01

### 問題

Phase 57.1/57.2の実装検証中に発見された不具合：
1. JSONレポートに`strategy_performance`が含まれていない
2. 全トレードが`strategy: "StrategyManager"`として記録され、個別戦略名が追跡されていない

### 根本原因

1. `reporter.py`でJSONレポート生成時に`strategy_performance`を呼び出していなかった
2. `StrategyManager`の`_combine_signals()`と`_integrate_consistent_signals()`が統合シグナルに固定の戦略名「StrategyManager」を設定していた

### 修正内容

#### 1. JSONレポートにstrategy_performance追加

**ファイル**: `src/backtest/reporter.py`

```python
# Phase 57.1: 戦略別パフォーマンス取得
strategy_performance = self.trade_tracker.get_strategy_performance()

report_data = {
    # 既存フィールド...
    "strategy_performance": strategy_performance,  # Phase 57.1追加
}
```

#### 2. StrategyManagerで最高信頼度戦略名を設定

**ファイル**: `src/strategies/base/strategy_manager.py`

**_combine_signals() (Line 305)**:
```python
# 勝利グループから最も信頼度の高いシグナルをベースに統合
best_signal = max(winning_group, key=lambda x: x[1].confidence)[1]
best_strategy_name = max(winning_group, key=lambda x: x[1].confidence)[0]  # Phase 57.3

return StrategySignal(
    strategy_name=best_strategy_name,  # Phase 57.3: 最高信頼度戦略名を設定
    # ...
    metadata={
        # ...
        "dominant_strategy": best_strategy_name,  # Phase 57.3追加
    },
)
```

**_integrate_consistent_signals() (Line 370)**:
```python
# Phase 57.3: 最も貢献した戦略名を特定（best_signalの戦略）
best_strategy_name = max(same_action_signals, key=lambda x: x[1].confidence)[0]

return StrategySignal(
    strategy_name=best_strategy_name,  # Phase 57.3: 最高信頼度戦略名を設定
    # ...
    reason=f"{len(same_action_signals)}戦略の統合結果（主: {best_strategy_name}）",
    metadata={
        # ...
        "dominant_strategy": best_strategy_name,  # Phase 57.3追加
    },
)
```

#### 3. テスト更新

**ファイル**: `tests/unit/strategies/test_strategy_manager.py`

```python
def test_analyze_market_single_strategy(self):
    # Phase 57.3: 最高信頼度戦略名を返すように変更
    self.assertEqual(result.strategy_name, "SingleStrategy")  # "StrategyManager"から変更
```

### バックテスト結果（7日間）

| 指標 | 値 |
|------|-----|
| 総取引 | 48件 |
| TP決済 | 9件 |
| SL決済 | 34件 |
| 最終残高 | ¥9,906 |

**戦略別パフォーマンス**:

| 戦略 | 取引数 | 勝率 | 総PnL | PF |
|------|--------|------|-------|-----|
| ATRBased | 46件 | 30.4% | -106.77円 | 0.53 |
| ADXTrendStrength | 1件 | 0% | -7.07円 | 0.00 |
| StochasticReversal | 1件 | 0% | -7.10円 | 0.00 |

### 期待効果

| 指標 | 修正前 | 修正後 |
|------|--------|--------|
| 戦略名記録 | "StrategyManager"固定 | 最高信頼度戦略名（ATRBased等） |
| strategy_performance JSON | なし | 含まれる |
| 戦略別分析 | 不可 | 完全に可能 |

### テスト結果

- **21テスト全パス**（StrategyManagerテスト）
- バックテスト正常完了
- JSONレポート出力確認

### 修正ファイル

1. `src/backtest/reporter.py` - strategy_performance JSON出力追加
2. `src/strategies/base/strategy_manager.py` - _combine_signals(), _integrate_consistent_signals()で戦略名設定
3. `tests/unit/strategies/test_strategy_manager.py` - テスト期待値更新

---

## Phase 57.4 - Optuna最適化実行（準備完了）

**状態**: スクリプト作成完了、実行待ち

### 準備完了内容

**新規作成**: `scripts/optimization/phase57_strategy_optimizer.py`

```python
class ATRBasedOptimizer:
    """ATRBased戦略のパラメータ最適化クラス"""

    def __init__(self, n_trials=10, period_days=7, verbose=True):
        # バックテスト統合（軽量モード）
        self.backtest = BacktestIntegration(period_days=period_days, ...)

    def create_objective(self):
        """Optuna目的関数（ATRBasedパラメータ最適化）"""
        # 最適化対象パラメータ:
        # - atr_high_vol_base, atr_normal_vol_base, atr_low_vol_base
        # - atr_rsi_overbought, atr_rsi_oversold
        # - atr_bb_overbought, atr_bb_oversold
```

### 実行コマンド

```bash
# 5試行テスト実行（約30分）
python3 scripts/optimization/phase57_strategy_optimizer.py --trials 5 --days 7 --verbose

# 本格実行（約1時間）
python3 scripts/optimization/phase57_strategy_optimizer.py --trials 10 --days 7 --verbose
```

### 次ステップ

- [ ] Optuna最適化実行（5-10試行）
- [ ] 最適パラメータの記録
- [ ] Phase 58への反映候補選定

---

## Phase 57.5 - 戦略設定プリセットシステム導入（完了）

**実施日**: 2025/12/01

### 背景・問題

Phase 57.4の閾値緩和による勝率21%（Phase 56: 42.1%）への低下を受け、設定ロールバックの容易化が必要になった。

### 解決策

**戦略設定の変数化システム（プリセット）を導入**:
- 各フェーズの設定をYAMLファイルとして保存
- `active.yaml`の1行変更でプリセット切り替え可能
- 将来的なレジーム別組み合わせテストに対応

### 修正内容

#### 1. ディレクトリ・ファイル構成

```
config/core/strategies/
├── active.yaml                    # プリセット選択ファイル
└── presets/
    ├── phase56.yaml               # 勝率42.1%設定（推奨）
    └── phase57_4.yaml             # 勝率21%設定（参照用）
```

#### 2. active.yaml（プリセット選択）

```yaml
# 現在アクティブなプリセット
active_preset: phase56  # phase56 | phase57_4 | custom

# プリセットエイリアス
aliases:
  A: phase56       # 勝率42.1%・推奨
  B: phase57_4     # 勝率21%・非推奨

# 将来拡張: レジーム別組み合わせ
combination_mode: false
```

#### 3. threshold_manager.py プリセット読み込み機構

**ファイル**: `src/core/config/threshold_manager.py`

```python
# Phase 57.5: プリセットキャッシュ
_preset_cache: Optional[Dict[str, Any]] = None
_active_preset_name: Optional[str] = None

def load_active_preset() -> Dict[str, Any]:
    """active.yamlからプリセットを読み込み"""
    # 1. active.yaml読み込み
    # 2. プリセットファイル読み込み
    # 3. キャッシュに保存

def get_threshold(key_path: str, default_value: Any = None) -> Any:
    """
    優先順位:
    1. runtime_overrides（Optuna最適化時）
    2. preset（Phase 57.5）
    3. thresholds.yaml
    4. default_value
    """
```

#### 4. tests/conftest.py（テスト環境用）

```python
@pytest.fixture(autouse=True)
def clear_preset_cache():
    """各テスト前にプリセットキャッシュをクリア"""
    # テスト環境ではthresholds.yamlの値を直接使用
```

### プリセットファイル内容

**phase56.yaml（勝率42.1%・推奨）**:
- regime_active_strategies: レジーム別有効戦略
- regime_strategy_mapping: 戦略重み
- take_profit/stop_loss: レジーム別TP/SL
- ml_integration: ML統合設定（hold_conversion_threshold: 0.20）
- confidence_levels: 信頼度レベル
- strategies: 戦略パラメータ

**phase57_4.yaml（勝率21%・非推奨）**:
- Phase 57.4の閾値緩和設定を記録
- 比較・分析用途

### バックテスト結果（7日間）

| 指標 | 値 |
|------|-----|
| 勝率 | 36.00% (18/50) |
| PF | 1.18 |
| 総損益 | +7円 |
| 取引回数 | 50回 |
| 最大DD | 0.13% |

### プリセットシステムの有用性

| 機能 | 効果 |
|------|------|
| **ロールバック** | active.yaml 1行変更で即座に切り替え |
| **検証履歴** | フェーズ別設定を永続保存 |
| **組み合わせ** | 将来的にレジーム別プリセット適用可能 |
| **実験安全性** | 元設定を失うリスクなし |
| **透明性** | ログに適用プリセット名を表示 |

### テスト結果

- **全テスト**: 1259 passed, 22 skipped（100%成功）
- **カバレッジ**: 65.81%（目標65%達成）
- **180日間バックテスト**: GitHub Actions実行中（Run ID: 19805548309）

### 修正ファイル一覧

| ファイル | 操作 | 内容 |
|---------|------|------|
| `config/core/strategies/active.yaml` | 新規作成 | プリセット選択 |
| `config/core/strategies/presets/phase56.yaml` | 新規作成 | Phase 56設定保存 |
| `config/core/strategies/presets/phase57_4.yaml` | 新規作成 | Phase 57.4設定保存 |
| `src/core/config/threshold_manager.py` | 修正 | プリセット読み込み機構 |
| `tests/conftest.py` | 新規作成 | テスト環境プリセット無効化 |
| `tests/unit/strategies/implementations/test_bb_reversal.py` | 修正 | テスト境界値調整 |
| `tests/unit/strategies/implementations/test_donchian_channel.py` | 修正 | テスト境界値調整 |

---

## Phase 57.6 - GitHub Actions Optuna最適化ワークフロー（完了）

**実施日**: 2025/12/01

### 背景・目的

ローカル環境に依存せず、GitHub Actions上でOptuna最適化を自動実行し、最適パラメータをプリセットとして保存する仕組みを構築。

### 解決策

**3段階ハイブリッド最適化ワークフローの構築**:

1. **Stage 1**: シミュレーション（高速スクリーニング・750試行）
2. **Stage 2**: 軽量バックテスト検証（7日間・30候補）
3. **Stage 3**: フルバックテスト検証（90日間・7候補）

### 新規作成ファイル

| ファイル | サイズ | 目的 |
|---------|-------|------|
| `.github/workflows/optuna-optimization.yml` | 6.1KB | GitHub Actionsワークフロー定義 |
| `scripts/optimization/optimize_strategy_parameters_v2.py` | 24.8KB | 6戦略対応パラメータ最適化 |
| `scripts/optimization/run_github_optimization.py` | 12.7KB | GitHub Actions統合スクリプト |
| `scripts/optimization/save_as_preset.py` | 13.3KB | 最適化結果→プリセット変換 |

### ワークフロー仕様

```yaml
# optuna-optimization.yml
on:
  workflow_dispatch:
    inputs:
      optimization_type:
        type: choice
        options: ['hybrid', 'risk', 'ml_integration', 'strategy']
        default: 'hybrid'
      n_trials:
        type: choice
        options: ['30', '50', '100']
        default: '50'
      backtest_days:
        type: choice
        options: ['30', '90', '180']
        default: '90'
```

### 最適化対象パラメータ（6戦略対応）

| 戦略 | パラメータ例 |
|------|-------------|
| ATRBased | rsi_oversold, rsi_overbought, bb_thresholds |
| BBReversal | bb_width_threshold, rsi_thresholds, adx_threshold |
| StochasticReversal | stoch_overbought/oversold, rsi_thresholds |
| DonchianChannel | middle_zone_min/max, reversal_threshold |
| ADXTrendStrength | strong_trend_threshold, di_crossover_threshold |
| MACDEMACrossover | adx_trend_threshold, volume_ratio_threshold |

### 実行ステップ（9ステップ）

1. Checkout repository
2. Set up Python
3. Install dependencies
4. Collect historical data
5. Run Optuna optimization
6. Save optimization results as preset
7. Show optimization results
8. Commit optimization results
9. Job summary

### プリセット連携（Phase 57.5連携）

```
Optuna最適化完了
    ↓
save_as_preset.py で変換
    ↓
config/core/strategies/presets/optuna_YYYYMMDD.yaml 保存
    ↓
active.yaml の aliases.C に設定
    ↓
手動で active_preset 切り替え
    ↓
本番適用
```

### 実行時間目安

| タイプ | 試行数 | バックテスト日数 | 想定時間 |
|--------|--------|------------------|----------|
| hybrid | 50 | 90 | 3-4時間 |
| strategy | 50 | 90 | 2-3時間 |
| risk/ml_integration | 50 | 90 | 1-2時間 |

### テスト結果

- **import確認**: 全スクリプト成功
- **YAML構文**: 正常
- **flake8**: PASS
- **black/isort**: 適用済み

### 使用方法

```bash
# GitHub Actionsから手動実行
# 1. GitHub > Actions > Optuna Parameter Optimization
# 2. Run workflow をクリック
# 3. パラメータ選択（optimization_type, n_trials, backtest_days）
# 4. 実行開始
```

---

## Phase 57.7 - 軽量バックテストモード・タイムアウト最適化（完了）

**実施日**: 2025/12/02

### 背景・問題

Phase 57.6のGitHub Actions Optuna最適化がタイムアウト（5時間33分）で失敗。
- **原因**: Stage 2の`_precompute_strategy_signals()`がO(n)で3.2時間かかっていた
- **目標**: トータル4時間以内に最適化完了

### 解決策

**環境変数優先の軽量モード実装**:
- 戦略シグナル事前計算スキップ
- データサンプリング比率の動的制御
- ハードコードなし・設定一元化

### 修正内容

#### 1. backtest_runner.py - 環境変数優先対応

**ファイル**: `src/core/execution/backtest_runner.py`

```python
# Phase 57.7拡張: 環境変数優先対応（subprocess経由でのパラメータ注入）
# 優先順位: 環境変数 > thresholds.yaml > デフォルト

# 戦略シグナル事前計算スキップ
env_skip = os.environ.get("BACKTEST_SKIP_STRATEGY_SIGNALS", "").lower()
if env_skip:
    skip_strategy_signals = env_skip == "true"
else:
    skip_strategy_signals = get_threshold("backtest.skip_strategy_signals", False)

if not skip_strategy_signals:
    await self._precompute_strategy_signals()
else:
    self.logger.warning("⚡ 軽量モード: 戦略シグナル事前計算スキップ")

# データサンプリング比率
env_sampling = os.environ.get("BACKTEST_DATA_SAMPLING_RATIO", "")
if env_sampling:
    sampling_ratio = float(env_sampling)
else:
    sampling_ratio = get_threshold("backtest.data_sampling_ratio", 1.0)
```

#### 2. backtest_integration.py - 環境変数注入

**ファイル**: `scripts/optimization/backtest_integration.py`

```python
# Phase 57.7: 軽量モード - 戦略シグナル事前計算スキップ
if self.use_lightweight:
    env["BACKTEST_SKIP_STRATEGY_SIGNALS"] = "true"

# Phase 57.7拡張: データサンプリング比率を環境変数経由で注入
if self.data_sampling_ratio < 1.0:
    env["BACKTEST_DATA_SAMPLING_RATIO"] = str(self.data_sampling_ratio)
```

#### 3. run_github_optimization.py - Stage 2設定最適化

**ファイル**: `scripts/optimization/run_github_optimization.py`

```python
def _run_lightweight_backtest(self, params: Dict[str, Any]) -> float:
    """
    軽量バックテスト実行（7日間×100%）

    Phase 57.7: サンプリングなしで十分な取引数を確保
    - 7日間 × 100%データ → 約4分/試行、約25-30取引
    """
    # Phase 57.7: 100%データで十分な取引数を確保（20%→100%）
    integration = BacktestIntegration(
        period_days=7, data_sampling_ratio=1.0, verbose=self.verbose
    )
```

#### 4. optuna-optimization.yml - タイムアウト調整

**ファイル**: `.github/workflows/optuna-optimization.yml`

```yaml
# 実行時間目安（Phase 57.7更新）:
#   - hybrid (50試行, 90日): 約3.5-4時間
#     Stage 1: シミュレーション ~10分
#     Stage 2: 軽量バックテスト (7日×100%) 1試行 ~4分
#     Stage 3: フルバックテスト (90日×100%) 1試行 ~52分

timeout-minutes: 300  # 5時間（4時間目標+バッファ）

# タイムアウト設定（4.5時間 = 16200秒）
timeout 16200 python3 scripts/optimization/run_github_optimization.py
env:
  OPTUNA_TIMEOUT_SECONDS: '16200'  # 4.5時間（4時間目標+バッファ30分）
```

### ローカル検証結果

| ステージ | 見積もり | ローカル実測 | 状況 |
|---------|---------|-------------|------|
| **Stage 1** | ~10分 | ~0.3秒 | ✅ シミュレーション高速完了 |
| **Stage 2** | ~4分 | ~93秒 (~1.5分) | ✅ 見積もり内 |
| **Stage 1+2合計** | ~14分 | ~1.8分 | ✅ 大幅クリア |

### Stage 2 バックテスト結果（7日間×100%）

| 項目 | 値 |
|------|-----|
| 取引数 | 47回 |
| 勝率 | 34.04% |
| 総損益 | -41.85 JPY |
| PF | 0.81 |
| 最大DD | 139.24 JPY (1.38%) |

### 設計原則

| 原則 | 実装 |
|------|------|
| **ハードコードなし** | 全て環境変数 or thresholds.yaml |
| **設定一元化** | `get_threshold()`パターン遵守 |
| **環境変数優先** | subprocess経由でパラメータ注入可能 |
| **後方互換性** | 環境変数なしでも既存動作維持 |

### 修正ファイル一覧

| ファイル | 修正内容 |
|---------|---------|
| `src/core/execution/backtest_runner.py` | 環境変数優先の軽量モード |
| `scripts/optimization/backtest_integration.py` | 環境変数注入 |
| `scripts/optimization/run_github_optimization.py` | Stage 2: 7日×100% |
| `.github/workflows/optuna-optimization.yml` | タイムアウト4.5時間 |

---

## Phase 57.8 - ABテスト基盤構築（予定）

### 実施内容
- ABテストコントローラー新規作成
- 統計検定実装（t検定・Mann-Whitney U）
- バリアント管理システム

---

## Phase 57.9 - 手数料・スプレッドシミュレーション（予定）

### 実施内容
- bitbank手数料正確反映（Maker 0.05%・リベート -0.02%）
- スプレッドシミュレーション（1000-5000円変動）

---

**最終更新**: 2025年12月2日（Phase 57.7完了 - 軽量バックテストモード・タイムアウト最適化）

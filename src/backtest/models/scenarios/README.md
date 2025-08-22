# src/backtest/models/scenarios/ - バックテストシナリオ定義

**Phase 13完了・本番運用移行・システム最適化・CI/CD準備完了**: バックテスト実行のためのシナリオ設定・パラメータ定義・テストケース管理ディレクトリです。様々な市場環境・戦略設定での包括的テスト・GitHub Actions統合を提供します。

## 📁 ディレクトリ構成

```
scenarios/
├── market_conditions/    # 市場環境別シナリオ ✅ Phase 13完了・CI/CDワークフロー最適化
│   ├── bull_market.json       # 強気相場シナリオ
│   ├── bear_market.json       # 弱気相場シナリオ
│   ├── sideways_market.json   # 横ばい相場シナリオ
│   └── high_volatility.json   # 高ボラティリティシナリオ
├── strategy_tests/       # 戦略別テストシナリオ ✅ Phase 13完了・GitHub Actions対応
│   ├── atr_based_scenarios.json         # ATRベース戦略
│   ├── fibonacci_scenarios.json         # フィボナッチ戦略
│   ├── mochipoy_alert_scenarios.json    # もちぽよアラート戦略
│   └── multi_timeframe_scenarios.json   # マルチタイムフレーム戦略
├── risk_management/      # リスク管理テストシナリオ ✅ Phase 13完了・手動実行監視対応
│   ├── kelly_criterion_tests.json       # Kelly基準テスト
│   ├── drawdown_scenarios.json          # ドローダウンシナリオ
│   └── position_sizing_tests.json       # ポジションサイジングテスト
├── performance_tests/    # パフォーマンステストシナリオ ✅ Phase 13完了・段階的デプロイ対応
│   ├── speed_benchmarks.json            # 処理速度ベンチマーク
│   ├── memory_usage_tests.json          # メモリ使用量テスト
│   └── stress_tests.json                # ストレステスト
└── README.md            # このファイル
```

## 🎯 シナリオ設計原則（Phase 13・本番運用移行・システム最適化・CI/CD準備完了）

### 包括的テストカバレッジ（GitHub Actions対応）

**市場環境網羅**:
- ✅ **強気相場**: 継続的上昇トレンド・高成長期間
- ✅ **弱気相場**: 継続的下降トレンド・調整期間
- ✅ **横ばい相場**: レンジ相場・方向感なし
- ✅ **高ボラティリティ**: 急激な価格変動・ショック期間

**戦略パフォーマンス検証**:
- ✅ **個別戦略**: 各戦略の単独性能評価
- ✅ **戦略組み合わせ**: 複数戦略の統合効果
- ✅ **パラメータ感度**: 設定値変更による影響
- ✅ **実用性評価**: 実際の取引条件での検証

## 📊 市場環境別シナリオ詳細（Phase 13・CI/CDワークフロー最適化・監視統合）

### bull_market.json - 強気相場シナリオ（GitHub Actions対応）

**期間・条件**:
```json
{
  "scenario_name": "bull_market_2024_q4",
  "description": "2024年Q4強気相場（BTC 450万→1125万円）",
  "test_period": {
    "start_date": "2024-10-01",
    "end_date": "2024-12-31",
    "duration_days": 92
  },
  "market_characteristics": {
    "trend_direction": "upward",
    "avg_daily_return": 1.2,
    "volatility": 3.8,
    "max_drawdown": 15.0,
    "win_rate_expectation": 65
  },
  "expected_performance": {
    "long_bias_strategies": "outperform",
    "momentum_strategies": "strong",
    "mean_reversion": "underperform"
  }
}
```

**テスト対象戦略**:
- **ATRベース**: トレンドフォロー効果
- **マルチタイムフレーム**: 上位時間軸との整合性
- **フィボナッチ**: 押し目買いの効果

### bear_market.json - 弱気相場シナリオ（手動実行監視対応）

**期間・条件**:
```json
{
  "scenario_name": "bear_market_2024_q1",
  "description": "2024年Q1調整相場（BTC 700万→420万円）",
  "test_period": {
    "start_date": "2024-01-01",
    "end_date": "2024-03-31",
    "duration_days": 91
  },
  "market_characteristics": {
    "trend_direction": "downward",
    "avg_daily_return": -0.8,
    "volatility": 4.2,
    "max_drawdown": 40.0,
    "win_rate_expectation": 45
  },
  "expected_performance": {
    "short_bias_strategies": "outperform",
    "defensive_strategies": "strong",
    "aggressive_long": "underperform"
  }
}
```

### sideways_market.json - 横ばい相場シナリオ（段階的デプロイ対応）

**期間・条件**:
```json
{
  "scenario_name": "sideways_market_2024_q2",
  "description": "2024年Q2レンジ相場（BTC 420万-550万円）",
  "test_period": {
    "start_date": "2024-04-01",
    "end_date": "2024-06-30",
    "duration_days": 91
  },
  "market_characteristics": {
    "trend_direction": "sideways",
    "avg_daily_return": 0.1,
    "volatility": 2.5,
    "range_bound": true,
    "false_breakout_frequency": "high"
  },
  "expected_performance": {
    "mean_reversion": "outperform",
    "range_trading": "strong",
    "trend_following": "underperform"
  }
}
```

## 🎯 戦略別テストシナリオ（Phase 13・本番運用移行・システム最適化・CI/CD準備完了）

### atr_based_scenarios.json - ATRベース戦略テスト（GitHub Actions対応）

**パラメータ感度テスト**:
```json
{
  "parameter_sensitivity_tests": [
    {
      "test_name": "atr_period_optimization",
      "parameters": {
        "atr_period": [14, 20, 26, 32],
        "volatility_threshold": [1.5, 2.0, 2.5],
        "stop_loss_multiplier": [1.0, 1.5, 2.0]
      },
      "optimization_target": "sharpe_ratio",
      "expected_optimal": {
        "atr_period": 20,
        "volatility_threshold": 2.0,
        "stop_loss_multiplier": 1.5
      }
    }
  ],
  "market_condition_tests": [
    {
      "test_name": "high_volatility_performance",
      "market_filter": "volatility > 4.0",
      "expected_metrics": {
        "win_rate": "> 55%",
        "profit_factor": "> 1.3",
        "max_drawdown": "< 25%"
      }
    }
  ]
}
```

### fibonacci_scenarios.json - フィボナッチ戦略テスト（CI/CD品質ゲート対応）

**レベル精度テスト**:
```json
{
  "fibonacci_level_tests": [
    {
      "test_name": "retracement_accuracy",
      "fibonacci_levels": [0.236, 0.382, 0.5, 0.618, 0.786],
      "swing_detection": {
        "min_swing_size": 50000,
        "lookback_periods": 20
      },
      "accuracy_metrics": {
        "level_hit_rate": "> 60%",
        "reversal_success": "> 45%",
        "false_signal_rate": "< 30%"
      }
    }
  ]
}
```

## 🛡️ リスク管理テストシナリオ（Phase 13・本番運用移行・システム最適化・CI/CD準備完了）

### kelly_criterion_tests.json - Kelly基準テスト（GitHub Actions統合）

**ポジションサイジング検証**:
```json
{
  "kelly_criterion_tests": [
    {
      "test_name": "optimal_position_sizing",
      "historical_data": {
        "win_rate_range": [0.5, 0.7],
        "avg_win_loss_ratio": [1.2, 2.5],
        "sample_size_min": 100
      },
      "kelly_parameters": {
        "safety_factor": 0.5,
        "max_position_size": 0.03,
        "min_position_size": 0.001
      },
      "expected_outcomes": {
        "position_size_stability": "low_variance",
        "drawdown_control": "< 20%",
        "growth_rate": "optimal"
      }
    }
  ]
}
```

### drawdown_scenarios.json - ドローダウンシナリオ（手動実行監視対応）

**連続損失制御テスト**:
```json
{
  "drawdown_control_tests": [
    {
      "test_name": "consecutive_loss_management",
      "simulation_parameters": {
        "max_consecutive_losses": 5,
        "loss_size_range": [0.02, 0.05],
        "recovery_scenarios": ["immediate", "gradual", "delayed"]
      },
      "control_mechanisms": {
        "position_size_reduction": "50%_after_3_losses",
        "trading_pause": "24h_after_5_losses",
        "risk_limit": "20%_max_drawdown"
      },
      "success_criteria": {
        "auto_pause_trigger": "functional",
        "recovery_time": "< 30_days",
        "capital_preservation": "> 80%"
      }
    }
  ]
}
```

## 🚀 パフォーマンステストシナリオ（Phase 13・CI/CDワークフロー最適化・段階的デプロイ対応）

### speed_benchmarks.json - 処理速度ベンチマーク（GitHub Actions対応）

**実行速度要件**:
```json
{
  "performance_benchmarks": [
    {
      "test_name": "backtest_execution_speed",
      "data_sizes": {
        "small": "1_month_15m_data",
        "medium": "6_months_15m_data", 
        "large": "2_years_15m_data"
      },
      "speed_requirements": {
        "small_dataset": "< 5_seconds",
        "medium_dataset": "< 30_seconds",
        "large_dataset": "< 300_seconds"
      },
      "optimization_targets": {
        "data_loading": "30-50%_improvement",
        "calculation_speed": "25%_improvement",
        "memory_usage": "20-30%_reduction"
      }
    }
  ]
}
```

### stress_tests.json - ストレステスト（CI/CD品質ゲート対応）

**極限条件テスト**:
```json
{
  "stress_test_scenarios": [
    {
      "test_name": "extreme_market_conditions",
      "stress_conditions": {
        "price_gaps": "> 10%_single_period",
        "volume_spikes": "> 1000%_normal",
        "data_anomalies": "missing_periods",
        "api_failures": "connection_timeout"
      },
      "resilience_requirements": {
        "error_handling": "graceful_degradation",
        "data_recovery": "automatic",
        "system_stability": "no_crashes",
        "result_accuracy": "maintained"
      }
    }
  ]
}
```

## 🔧 シナリオ実行・管理（Phase 13・本番運用移行・システム最適化・CI/CD準備完了）

### 実行コマンド（GitHub Actions対応）

```bash
# 市場環境別テスト実行
python -m src.backtest.engine run-scenario --config=market_conditions/bull_market.json

# 戦略パフォーマンステスト
python -m src.backtest.engine strategy-test --scenario=atr_based_scenarios.json

# リスク管理テスト
python -m src.backtest.engine risk-test --scenario=drawdown_scenarios.json

# 包括的テストスイート実行
python -m src.backtest.engine test-suite --all-scenarios --parallel=4
```

### 結果分析・レポート（CI/CD品質ゲート対応）

```bash
# シナリオ比較レポート
python -m src.backtest.reporter scenario-comparison --output=html

# パフォーマンスサマリー
python -m src.backtest.reporter performance-summary --format=json

# リスク分析レポート
python -m src.backtest.reporter risk-analysis --discord-notify
```

## 📈 品質保証・継続的改善（Phase 13・本番運用移行・システム最適化・CI/CD準備完了）

### シナリオ検証（GitHub Actions統合）

**定期実行**（週次）:
- 全シナリオの自動実行
- 結果品質チェック
- 期待値との乖離分析
- パフォーマンス回帰検出

**更新・保守**（月次）:
- 新しい市場データでの検証
- シナリオパラメータ最適化
- 失敗事例の分析・改善
- 新シナリオの追加

### CI/CDインテグレーション（GitHub Actions対応）

```yaml
# GitHub Actions例
name: Backtest Scenario Tests
on: [push, pull_request]
jobs:
  scenario_tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run Critical Scenarios
        run: |
          python -m src.backtest.engine test-suite \
            --scenarios=critical \
            --timeout=1800 \
            --fail-fast
```

---

**Phase 13完了**: 包括的なバックテストシナリオ管理システムを実現。市場環境・戦略・リスク管理・パフォーマンスの全方位テスト・本番運用移行・システム最適化・CI/CD準備完了・GitHub Actions統合により、堅牢で実用的なトレーディングシステムの品質保証を提供
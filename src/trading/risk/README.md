# src/trading/risk/ - 統合リスク管理層

## 役割

取引前のリスク評価・ポジションサイジング・ドローダウン管理・異常検知を担当する。
`evaluate_trade_opportunity()` で全コンポーネントを統合し、APPROVED / DENIED を返す。

## ファイル構成

| ファイル | 行数 | クラス | 責務 |
|---------|------|--------|------|
| `manager.py` | 909 | `IntegratedRiskManager` | 全リスクコンポーネント統合・取引承認/拒否 |
| `kelly.py` | 562 | `KellyCriterion` | Kelly基準による最適ポジションサイズ計算 |
| `drawdown.py` | 310 | `DrawdownManager` | ドローダウン監視・連続損失管理・クールダウン |
| `anomaly.py` | 267 | `TradingAnomalyDetector` | スプレッド・レイテンシ・価格スパイク検知 |
| `sizer.py` | 294 | `PositionSizeIntegrator` | Kelly + Dynamic + RiskManager統合サイジング |
| `__init__.py` | 31 | - | モジュールエクスポート |

## クラス詳細

### IntegratedRiskManager（manager.py / 909行）

取引評価の中核。Kelly・ドローダウン・異常検知・証拠金監視を統合する。

| メソッド | 概要 |
|---------|------|
| `evaluate_trade_opportunity()` | 取引評価メイン（全コンポーネント統合） |
| `record_trade_result()` | 取引結果の記録 |
| `get_risk_summary()` | リスク管理サマリー取得 |
| `check_stop_conditions()` | システム停止条件チェック |
| `_check_margin_ratio()` | 証拠金維持率チェック（80%未満で拒否） |
| `_calculate_risk_score()` | リスクスコア算出（0.0-1.0） |
| `_check_capital_usage_limits()` | 資本使用率チェック |
| `_make_final_decision()` | 最終承認/拒否判定 |
| `_estimate_market_volatility()` | ATRベース市場ボラティリティ推定 |

### KellyCriterion（kelly.py / 562行）

履歴ベースの最適ポジションサイズ計算。5取引未満は固定サイズ（0.0001 BTC）。

| メソッド | 概要 |
|---------|------|
| `calculate_kelly_fraction()` | Kelly公式: f = (bp - q) / b |
| `calculate_from_history()` | 履歴ベースKelly計算 |
| `calculate_optimal_size()` | ML信頼度調整済みサイズ |
| `calculate_dynamic_position_size()` | ボラティリティ連動サイジング |
| `add_trade_result()` | 取引履歴追加 |
| `get_kelly_statistics()` | Kelly統計取得 |
| `validate_kelly_parameters()` | パラメータ範囲検証 |

補助データクラス: `TradeResult`, `KellyCalculationResult`

### DrawdownManager（drawdown.py / 310行）

最大DD 20%制限・連続損失8回で一時停止・6時間クールダウン。

| メソッド | 概要 |
|---------|------|
| `initialize_balance()` | 初期残高設定 |
| `update_balance()` | 残高更新・ピーク追跡 |
| `record_trade_result()` | 取引記録・連続損失カウント |
| `calculate_current_drawdown()` | 現在DD率算出 |
| `check_trading_allowed()` | 取引許可判定（クールダウン考慮） |
| `get_drawdown_statistics()` | DD統計スナップショット |

補助型: `TradingStatus`（enum）, `TradeRecord`（dataclass）

### TradingAnomalyDetector（anomaly.py / 267行）

市場異常・API異常をリアルタイム検知。

| メソッド | 概要 |
|---------|------|
| `comprehensive_anomaly_check()` | 全異常チェック実行（スプレッド・レイテンシ・価格・出来高） |
| `get_anomaly_statistics()` | 24時間異常カウント取得 |

補助型: `AnomalyLevel`（enum: INFO/WARNING/CRITICAL）, `AnomalyAlert`（dataclass）

### PositionSizeIntegrator（sizer.py / 294行）

Kelly・Dynamic・RiskManagerの3方式を加重平均で統合。

| メソッド | 概要 |
|---------|------|
| `calculate_integrated_position_size()` | 統合ポジションサイズ算出（Kelly 50% / Dynamic 30% / RM 20%） |

## 依存関係

- `src/trading/balance/monitor.py` - 証拠金維持率監視（IntegratedRiskManagerが使用）
- `src/core/config/threshold_manager.py` - `get_threshold()` による設定取得
- `config/core/thresholds.yaml` - リスク閾値・ポジションサイジング・維持率設定

## 設定ファイル

| 設定パス | 用途 |
|---------|------|
| `margin.thresholds.critical` | 維持率拒否閾値（80%） |
| `risk.sl_min_distance_ratio` | SL最小距離 |
| `position_integrator.*` | Kelly/Dynamic/RM重み配分 |
| `production.max_order_size` | 最大注文サイズ（0.03 BTC） |
| `position_management.dynamic_position_sizing.*` | ML信頼度別サイジング比率 |

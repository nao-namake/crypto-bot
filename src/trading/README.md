# src/trading/ - 統合取引管理層

**Phase 64.4**: レイヤードアーキテクチャによる責務分離実装。
5層構造（core / balance / execution / position / risk）で統合取引管理を実現。

## ファイル構成

```
src/trading/
├── __init__.py              # 取引層エクスポート・リスクプロファイル
├── core/                    # 共通定義層
│   ├── __init__.py
│   ├── enums.py            # 列挙型（ExecutionMode, OrderStatus等）
│   └── types.py            # データクラス（TradeEvaluation, ExecutionResult等）
├── execution/              # 実行層（詳細: execution/README.md）
│   ├── __init__.py
│   ├── executor.py         # エントリー注文実行（~1,300行）
│   ├── stop_manager.py     # TP/SL到達判定・決済（~1,525行）
│   ├── order_strategy.py   # 注文タイプ決定・Maker実行（~770行）
│   ├── tp_sl_config.py     # TP/SL設定パス定数（~120行）
│   ├── tp_sl_manager.py    # TP/SL配置・検証・復旧統合管理（~1,250行）
│   └── position_restorer.py # ポジション復元・孤児クリーンアップ（~560行）
├── position/               # ポジション管理層
│   ├── __init__.py
│   ├── tracker.py          # ポジション追跡
│   ├── limits.py           # ポジション制限
│   ├── cleanup.py          # 孤児ポジションクリーンアップ
│   └── cooldown.py         # クールダウン管理
├── balance/                # 残高監視層
│   ├── __init__.py
│   └── monitor.py          # 残高・保証金監視
└── risk/                   # リスク管理層
    ├── __init__.py
    ├── manager.py          # IntegratedRiskManager（統合リスク評価）
    ├── kelly.py            # Kelly基準ポジションサイジング
    ├── sizer.py            # PositionSizeIntegrator
    ├── anomaly.py          # TradingAnomalyDetector
    └── drawdown.py         # DrawdownManager
```

## レイヤー概要

### Layer 1: core/ — 共通定義層

全層で使用する列挙型・データクラスを定義。

- `RiskDecision`: APPROVED / CONDITIONAL / DENIED
- `OrderStatus`: PENDING / FILLED / CANCELED / FAILED
- `ExecutionMode`: PAPER / LIVE / BACKTEST
- `TradeEvaluation`, `ExecutionResult`, `RiskMetrics` 等

### Layer 2: balance/ — 残高監視層

証拠金維持率の監視とアラート。

- 4段階状態判定: SAFE / CAUTION / WARNING / CRITICAL
- 新規ポジション影響予測
- Discord通知連携

### Layer 3: execution/ — 注文実行層

注文実行・TP/SL管理・ポジション復元を担当。6ファイル構成。
詳細は [execution/README.md](execution/README.md) を参照。

主要クラス:
- **ExecutionService**: エントリー注文実行（ライブ/ペーパー/バックテスト）
- **StopManager**: TP/SL到達判定・決済実行
- **OrderStrategy**: 注文タイプ決定・Maker注文・最小ロット保証
- **TPSLConfig**: TP/SL設定パス定数（typoバグ防止）
- **TPSLManager**: TP/SL設置・検証・復旧・計算・ロールバック統合管理
- **PositionRestorer**: Container再起動時ポジション復元・孤児クリーンアップ

### Layer 4: position/ — ポジション管理層

ポジション追跡・制限・クールダウン・クリーンアップを担当。

- **PositionTracker**: ポジション追跡・状態管理
- **PositionLimits**: 最大ポジション数・日次取引数制限
- **PositionCleanup**: 孤児ポジション検出・自動クリーンアップ
- **CooldownManager**: トレンド強度ベース柔軟クールダウン

### Layer 5: risk/ — リスク管理層

リスク評価・ポジションサイジング・異常検知・ドローダウン管理。

- **IntegratedRiskManager**: ML信頼度・ドローダウン・異常検知の統合判定
- **KellyCriterion**: Kelly基準ポジションサイジング（ML信頼度連動）
- **PositionSizeIntegrator**: 資金規模別ポジションサイズ調整
- **TradingAnomalyDetector**: スプレッド・API遅延・価格スパイク検知
- **DrawdownManager**: 最大20%ドローダウン・連続5損失制限

## 使用方法

### リスクプロファイル

```python
from src.trading import create_risk_manager, list_risk_profiles

# プロファイル一覧
profiles = list_risk_profiles()
# {"conservative": "保守的...", "balanced": "バランス型...", "aggressive": "積極的..."}

# リスク管理器作成
risk_manager = create_risk_manager(risk_profile="balanced", mode="live")
```

### 取引実行フロー

```python
from src.trading import IntegratedRiskManager, ExecutionService

# 1. リスク評価
evaluation = risk_manager.evaluate_trade_opportunity(
    ml_prediction={'confidence': 0.8, 'action': 'buy'},
    strategy_signal={'strategy_name': 'atr_based', 'action': 'buy'},
    market_data=market_data,
    current_balance=500000,
    bid=14000000, ask=14001000
)

# 2. 取引実行（TP/SL自動配置含む）
if evaluation.decision == RiskDecision.APPROVED:
    result = await execution_service.execute_trade(evaluation)
```

### 設定参照パターン

```python
from src.core.config.threshold_manager import get_threshold
from src.trading.execution.tp_sl_config import TPSLConfig

# TP/SL設定はTPSLConfig定数を使用（文字列リテラル禁止）
tp_ratio = get_threshold(TPSLConfig.TP_MIN_PROFIT_RATIO, 0.009)
sl_ratio = get_threshold(TPSLConfig.SL_MAX_LOSS_RATIO, 0.007)
```

## テスト

```bash
# trading層全体テスト
python -m pytest tests/unit/trading/ -v

# レイヤー別テスト
python -m pytest tests/unit/trading/balance/ -v
python -m pytest tests/unit/trading/execution/ -v
python -m pytest tests/unit/trading/position/ -v
python -m pytest tests/unit/trading/risk/ -v
```

## 設定ファイル

| ファイル | 関連設定 |
|---------|---------|
| `config/core/features.yaml` | 機能トグル |
| `config/core/unified.yaml` | 基本設定（残高・実行間隔・SL設定等） |
| `config/core/thresholds.yaml` | TP/SL比率・レジーム別設定・リスク閾値 |

## 依存関係

- `src/core/config/`: 設定管理（get_threshold）
- `src/core/logger/`: ロギング
- `src/data/bitbank_client`: bitbank API
- `src/core/orchestration/`: TradingOrchestrator（呼出元）

# src/trading/core/ - 取引層共通定義

trading レイヤード全体で共有する列挙型・データクラス定義。

## ファイル構成

| ファイル | 行数 | 役割 |
|---|---|---|
| `__init__.py` | 35 | エクスポート |
| `enums.py` | 56 | 列挙型（`ExecutionMode` / `OrderStatus` / `RiskDecision`）|
| `types.py` | 174 | データクラス（`TradeEvaluation` / `ExecutionResult` / `PositionFeeData` 等）|

## 主要型

### enums.py

```python
class ExecutionMode(Enum):
    PAPER = "paper"
    LIVE = "live"
    BACKTEST = "backtest"

class OrderStatus(Enum):
    PENDING / FILLED / CANCELED / FAILED / INACTIVE

class RiskDecision(Enum):
    APPROVED / CONDITIONAL / DENIED
```

### types.py

```python
@dataclass
class TradeEvaluation:
    decision: RiskDecision
    ml_prediction: dict
    strategy_signal: dict
    ...

@dataclass
class ExecutionResult:
    order_id: str
    status: OrderStatus
    ...

@dataclass
class PositionFeeData:
    entry_fee: float
    exit_fee_maker: float
    exit_fee_taker: float
```

## 設計原則

- 循環インポート回避のため、`trading/` 配下の全モジュールがこの共通定義を import
- 型定義のみで実装ロジックを持たない（純粋なデータ層）

## 関連リンク

- 親 README: [../README.md](../README.md)

---

**最終更新**: 2026年5月20日（Phase 90α: 新規作成）

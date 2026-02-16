# src/strategies/utils/ - 戦略共通処理モジュール

**Phase 64.5更新**: 6戦略共通処理の統一管理。デッドコード削除完了。

## ファイル構成

```
src/strategies/utils/
├── __init__.py          # エクスポート管理
├── strategy_utils.py    # 戦略定数・リスク管理・シグナル生成
└── market_utils.py      # 市場不確実性計算
```

## 主要機能

### strategy_utils.py

**戦略定数**:
- `EntryAction`: BUY / SELL / HOLD / CLOSE
- `StrategyType`: 6戦略（ATR_BASED, DONCHIAN_CHANNEL, ADX_TREND, BB_REVERSAL, STOCHASTIC_REVERSAL, MACD_EMA_CROSSOVER）

**RiskManager**:
- `_extract_15m_atr()`: 15m足ATR優先取得（4h足フォールバック）
- `_calculate_adaptive_atr_multiplier()`: ボラティリティ連動ATR倍率（低ボラ2.5x / 通常2.0x / 高ボラ1.5x）
- `calculate_fixed_amount_tp()`: 固定金額TP価格計算（手数料考慮）
- `calculate_stop_loss_take_profit()`: レジーム別TP/SL計算（土日縮小対応）
- `calculate_position_size()`: 信頼度ベースポジションサイズ計算
- `calculate_risk_ratio()`: リスク比率計算

**SignalBuilder**:
- `create_signal_with_risk_management()`: リスク管理付きシグナル生成（Dynamic Position Sizing対応）
- `create_hold_signal()`: ホールドシグナル生成
- `_calculate_dynamic_position_size()`: PositionSizeIntegrator委譲
- `_create_error_signal()`: エラー時フォールバックシグナル

### market_utils.py

**MarketUncertaintyCalculator**:
- `calculate()`: ATR・ボリューム・価格変動率の統合不確実性計算（0-0.1範囲）

## 使用例

```python
from src.strategies.utils import EntryAction, SignalBuilder, StrategyType, RiskManager

# シグナル生成
signal = SignalBuilder.create_signal_with_risk_management(
    strategy_name="ATRBased",
    decision={"action": EntryAction.BUY, "confidence": 0.8, "strength": 0.7},
    current_price=15000000,
    df=market_data,
    config=config,
    strategy_type=StrategyType.ATR_BASED,
)

# ホールドシグナル
hold = SignalBuilder.create_hold_signal("ATRBased", 15000000, "条件不適合")

# 市場不確実性
from src.strategies.utils.market_utils import MarketUncertaintyCalculator
uncertainty = MarketUncertaintyCalculator.calculate(df)
```

## テスト

```bash
python -m pytest tests/unit/strategies/utils/ -v
```

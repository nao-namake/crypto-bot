# src/strategies/ - 取引戦略システム

**Phase 64.5**: Registry Pattern + Decoratorによる6戦略自動登録・動的ロード機構。

## ファイル構成

```
src/strategies/
├── __init__.py              # エクスポート（28行）
├── strategy_registry.py     # Registry Pattern戦略自動登録（184行）
├── strategy_loader.py       # 戦略動的ロード・有効化管理（300行）
├── base/                    # 戦略基盤システム
│   ├── strategy_base.py        # 抽象基底クラス StrategyBase・StrategySignal（254行）
│   └── strategy_manager.py     # 戦略統合管理・競合解決・重み付け統合（657行）
├── implementations/         # 6戦略実装
│   ├── bb_reversal.py          # BBReversal: BB位置主導＋RSIボーナス→平均回帰（410行）
│   ├── stochastic_reversal.py  # StochasticDivergence: 価格乖離検出→反転（589行）
│   ├── atr_based.py            # ATRBased: ATR消尽率70%以上→反転期待（668行）
│   ├── donchian_channel.py     # DonchianChannel: チャネル端部反転＋RSIボーナス（426行）
│   ├── macd_ema_crossover.py   # MACDEMACrossover: MACDクロス＋EMAトレンド確認（350行）
│   └── adx_trend.py            # ADXTrendStrength: ADX≥25＋DIクロス→トレンドフォロー（911行）
└── utils/                   # 共通処理
    ├── strategy_utils.py       # SignalBuilder・RiskManager・共通計算（835行）
    └── market_utils.py         # 市場分析ユーティリティ（108行）
```

## 6戦略構成

| 区分 | 戦略名 | 核心ロジック |
|------|--------|-------------|
| レンジ型 | BBReversal | BB位置主導 + RSIボーナス → 平均回帰 |
| レンジ型 | StochasticDivergence | 価格とStochasticの乖離検出 → 反転 |
| レンジ型 | ATRBased | ATR消尽率70%以上 → 反転期待 |
| レンジ型 | DonchianChannel | チャネル端部反転 + RSIボーナス |
| トレンド型 | MACDEMACrossover | MACDクロス + EMAトレンド確認 |
| トレンド型 | ADXTrendStrength | ADX≥25 + DIクロス → トレンドフォロー |

## Registry Pattern

戦略の追加・削除は`@StrategyRegistry.register()`デコレータのみで完結:

```python
from src.strategies.strategy_registry import StrategyRegistry
from src.strategies.base.strategy_base import StrategyBase

@StrategyRegistry.register(name="ATRBased", strategy_type="atr_based")
class ATRBasedStrategy(StrategyBase):
    def analyze(self, df):
        ...
```

有効化はfeatures.yamlで制御。strategy_loader.pyが有効戦略のみを動的ロード。

## データフロー

```
15分足データ（15特徴量）
    ↓
6戦略並行実行 → 個別StrategySignal生成
    ↓
StrategyManager: 重み付け統合・競合解決
    ↓
統合StrategySignal → ML予測・リスク評価へ
```

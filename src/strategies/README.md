# src/strategies/ - 取引戦略システム

**Phase 90α**: Registry Pattern + Decorator による 6 戦略自動登録・動的ロード機構。`DonchianChannel` は Phase 74 で `CMFReversal` に置換済・実体削除済（Phase 90α）。

## ファイル構成

```
src/strategies/
├── __init__.py              # エクスポート（26 行）
├── strategy_registry.py     # Registry Pattern 戦略自動登録（184 行）
├── strategy_loader.py       # 戦略動的ロード・有効化管理（249 行）
├── base/                    # 戦略基盤システム
│   ├── strategy_base.py        # 抽象基底クラス StrategyBase・StrategySignal（254 行）
│   └── strategy_manager.py     # 戦略統合管理・重み付け平均統合（798 行）
├── implementations/         # 6 戦略実装（詳細: implementations/README.md）
│   ├── atr_based.py            # ATRBased: ATR 消尽率 → 反転（707 行・主力）
│   ├── bb_reversal.py          # BBReversal: BB 位置主導 + RSI（409 行）
│   ├── stochastic_reversal.py  # StochasticReversal: 価格乖離検出 → 反転（589 行）
│   ├── cmf_reversal.py         # CMFReversal: CMF 出来高フロー反転（237 行・Phase 74）
│   ├── macd_ema_crossover.py   # MACDEMACrossover: MACD + EMA（350 行）
│   └── adx_trend.py            # ADXTrendStrength: ADX≥22 + DI クロス（961 行）
└── utils/                   # 共通処理
    ├── strategy_utils.py       # SignalBuilder・RiskManager・共通計算（938 行）
    └── market_utils.py         # 市場分析ユーティリティ（108 行）
```

## 6 戦略構成

| 区分 | 戦略名 | 核心ロジック |
|------|--------|-------------|
| レンジ型 | **ATRBased** | ATR 消尽率 70% 以上 → 反転期待（主力）|
| レンジ型 | **BBReversal** | BB 位置主導 + RSI ボーナス → 平均回帰 |
| レンジ型 | **StochasticReversal** | 価格と Stochastic の乖離検出 → 反転 |
| レンジ型 | **CMFReversal** | CMF 売り圧力減少 → BUY / 買い圧力減少 → SELL（Phase 74 置換）|
| トレンド型 | **MACDEMACrossover** | MACD クロス + EMA トレンド確認 |
| トレンド型 | **ADXTrendStrength** | ADX≥22 + DI クロス → トレンドフォロー |

Phase 85 以降、trending レジーム時は全戦略重み 0（エントリー停止）。設計思想「レンジ専用 bot」と整合。

## Registry Pattern

戦略の追加・削除は `@StrategyRegistry.register()` デコレータのみで完結:

```python
from src.strategies.strategy_registry import StrategyRegistry
from src.strategies.base.strategy_base import StrategyBase

@StrategyRegistry.register(name="ATRBased", strategy_type="atr_based")
class ATRBasedStrategy(StrategyBase):
    def analyze(self, df):
        ...
```

有効化は `config/core/thresholds.yaml` の `dynamic_strategy_selection.regime_strategy_mapping` で制御。`strategy_loader.py` が有効戦略のみを動的ロード。

## データフロー

```
15 分足データ + 55 特徴量
    ↓
6 戦略並行実行 → 個別 StrategySignal 生成
    ↓
StrategyManager: 重み付け平均統合（Phase 59.4: 2 票ルール廃止・重み付け統合方式）
    ↓
統合 StrategySignal → ML 品質フィルタ（Phase 90α メタラベリング）→ リスク評価へ
```

## 関連リンク

- 親 README: [../README.md](../README.md)
- 戦略基盤: [base/README.md](base/README.md)
- 戦略実装: [implementations/README.md](implementations/README.md)
- 共通処理: [utils/README.md](utils/README.md)

---

**最終更新**: 2026年5月19日（Phase 90α: DonchianChannel 削除・CMFReversal 反映・55 特徴量・thresholds.yaml 1 ファイル化）

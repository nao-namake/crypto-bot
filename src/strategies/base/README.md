# src/strategies/base/ - 戦略基盤システム

Phase 64.5: 6戦略の統一インターフェース・競合解決・重み付け統合。

## ファイル構成

```
src/strategies/base/
├── __init__.py          # エクスポート
├── strategy_base.py     # 抽象基底クラス・StrategySignal（~260行）
└── strategy_manager.py  # 戦略統合管理（~655行）
```

## 主要コンポーネント

### strategy_base.py

全6戦略（BBReversal・StochasticDivergence・ATRBased・DonchianChannel・MACDEMACrossover・ADXTrendStrength）が継承する統一基底クラス。

```python
@dataclass
class StrategySignal:
    strategy_name: str      # 戦略名
    timestamp: datetime     # シグナル発生時刻
    action: str            # buy/sell/hold
    confidence: float      # 信頼度 (0.0-1.0)
    strength: float        # シグナル強度 (0.0-1.0)
    current_price: float   # 現在価格
    # + entry_price, stop_loss, take_profit, position_size, risk_ratio, indicators, reason, metadata

class StrategyBase(ABC):
    def analyze(self, df, multi_timeframe_data=None) -> StrategySignal  # 戦略固有分析（実装必須）
    def get_required_features(self) -> List[str]                        # 必要特徴量（実装必須）
    def generate_signal(self, df, multi_timeframe_data=None)            # 統一エントリーポイント
```

### strategy_manager.py

6戦略の統合管理・競合解決・重み付け統合による最終シグナル生成。

```python
class StrategyManager:
    def register_strategy(self, strategy, weight=1.0)           # 戦略登録
    def analyze_market(self, df, multi_timeframe_data=None)     # 統合分析
    def update_strategy_weights(self, new_weights)              # 重み調整
    def get_individual_strategy_signals(self, df, ...)          # ML特徴量用個別シグナル
```

## 競合解決フロー

```
各戦略並行実行 → 個別StrategySignal生成（6戦略）
    ↓
アクション別グループ化 → {"buy": [...], "sell": [...], "hold": [...]}
    ↓
競合検知 → 2つ以上の異なるアクション存在チェック
    ↓
競合なし → 重み付き信頼度ベース判定
競合あり → Phase 56.7 quorumルール or 従来ロジック
    ↓
最終統合シグナル
```

### Phase 56.7 quorumルール（consensus.enabled=true時）

- BUY 2票以上 かつ SELL 1票以下 → BUY選択（HOLD無視）
- SELL 2票以上 かつ BUY 1票以下 → SELL選択（HOLD無視）
- BUY/SELL両方2票以上 → HOLD（矛盾）
- それ以外 → 従来ロジック（重み付け信頼度比較）

### 重み付け信頼度計算

Phase 49.8: 合計値（平均ではなく）。1.0でクリップ。

## レジーム別戦略重み（thresholds.yaml: tight_range）

| 戦略 | 重み |
|------|------|
| BBReversal | 0.35 |
| StochasticDivergence | 0.35 |
| ATRBased | 0.20 |
| DonchianChannel | 0.10 |
| MACDEMACrossover | 0.0 |
| ADXTrendStrength | 0.0 |

normal_range・trendingの詳細は `config/core/thresholds.yaml` 参照。

## 設定

- **環境変数**: `BACKTEST_MODE=true` でログ抑制
- **features.yaml**: `strategies.consensus.enabled`（2票ルール有効/無効）
- **thresholds.yaml**: レジーム別重み・ML閾値
- **データ要件**: 55特徴量（49基本 + 6戦略信号）・最小データ数20

# src/strategies/utils/ - 戦略共通処理モジュール

**Phase 49完了**: 5戦略共通処理の統一管理・適応型ATR倍率実装・最小SL距離保証・リスク管理統合・シグナル生成標準化。

## 📂 ファイル構成

```
src/strategies/utils/
├── __init__.py          # エクスポート管理（32行）
├── strategy_utils.py    # 戦略共通処理（572行・Phase 30: 適応ATR倍率追加）
└── market_utils.py      # 市場分析ユーティリティ（180行・Phase 49完了）
```

## 🔧 主要機能

### **strategy_utils.py（572行・Phase 30更新）**

**目的**: 5戦略（ATRBased・MochipoyAlert・MultiTimeframe・DonchianChannel・ADXTrendStrength）の共通処理統一管理

**提供クラス・機能**:
```python
# 戦略定数
class EntryAction:
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"

class StrategyType:
    ATR_BASED = "atr_based"
    MOCHIPOY_ALERT = "mochipoy_alert"
    MULTI_TIMEFRAME = "multi_timeframe"
    DONCHIAN_CHANNEL = "donchian_channel"
    ADX_TREND_STRENGTH = "adx_trend_strength"

# リスク管理（Phase 30拡張）
class RiskManager:
    @staticmethod
    def _calculate_adaptive_atr_multiplier(current_atr, atr_history=None) -> float
        # Phase 30新機能: ボラティリティ連動ATR倍率
        # 低ボラ: 2.5倍（広め）、通常: 2.0倍、高ボラ: 1.5倍（狭め）

    @staticmethod
    def calculate_stop_loss_take_profit(
        action, current_price, current_atr, config, atr_history=None
    ) -> Tuple[Optional[float], Optional[float]]
        # Phase 30拡張: 適応型ATR倍率・最小SL距離保証（1%）

    @staticmethod
    def calculate_position_size(confidence, config)

# シグナル構築
class SignalBuilder:
    @staticmethod
    def create_signal_with_risk_management(strategy_name, decision, current_price, df, config, strategy_type)
    @staticmethod
    def create_hold_signal(strategy_name, current_price, reason)
```

### **__init__.py（32行）**

**目的**: 統一インポートポイント・依存関係の明確化

```python
from .strategy_utils import (
    DEFAULT_RISK_PARAMS,
    EntryAction,
    RiskManager,
    SignalBuilder,
    StrategyType,
)
```

### **Phase 30新機能: 適応型ATR倍率**

**目的**: ボラティリティに応じたストップロス距離の動的調整

**実装内容**:
- **低ボラティリティ時**: ATR倍率 2.5x（広めのSL・振動による誤停止防止）
- **通常ボラティリティ**: ATR倍率 2.0x（標準設定）
- **高ボラティリティ時**: ATR倍率 1.5x（狭めのSL・急変時の損失制限）

**最小SL距離保証**:
- 1%最小距離保証により、少額資金でも適切なSL設定
- ATR計算値が小さすぎる場合でも、現在価格の1%を最小保証

## 🚀 使用例

### **基本的な戦略実装**

```python
from ..utils import EntryAction, RiskManager, SignalBuilder, StrategyType

# 戦略定数使用
action = EntryAction.BUY
strategy_type = StrategyType.ATR_BASED

# リスク管理計算
stop_loss, take_profit = RiskManager.calculate_stop_loss_take_profit(
    current_price=45000,
    action=EntryAction.BUY,
    atr_value=300,
    config=config
)

position_size = RiskManager.calculate_position_size(
    confidence=0.7,
    config=config
)

# 統一シグナル生成
signal = SignalBuilder.create_signal_with_risk_management(
    strategy_name="ATRBased",
    decision=decision_dict,
    current_price=45000,
    df=market_data,
    config=config,
    strategy_type=StrategyType.ATR_BASED
)

# ホールドシグナル
hold_signal = SignalBuilder.create_hold_signal(
    strategy_name="Strategy",
    current_price=45000,
    reason="条件不適合"
)
```

### **新戦略での利用**

```python
from ..base.strategy_base import StrategyBase
from ..utils import EntryAction, RiskManager, SignalBuilder, StrategyType

class CustomStrategy(StrategyBase):
    def analyze(self, df):
        # 戦略固有の分析ロジック
        decision = self._analyze_market(df)

        # 共通処理でシグナル生成
        return SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.name,
            decision=decision,
            current_price=float(df['close'].iloc[-1]),
            df=df,
            config=self.config,
            strategy_type=StrategyType.CUSTOM
        )
```

## 🔄 リファクタリング効果

### **重複排除の実装例**

```python
# Before: 各戦略で個別実装（重複）
class ATRBasedStrategy:
    def _create_signal(self, decision, price, df):
        # 50行の重複したリスク管理コード
        atr_value = float(df['atr_14'].iloc[-1])
        if decision['action'] == 'buy':
            stop_loss = price - (atr_value * 2.0)
            take_profit = price + (atr_value * 2.5)
        # ... 各戦略で同じコードが重複

# After: 統一されたシンプルな実装
class ATRBasedStrategy:
    def _create_signal(self, decision, price, df):
        return SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.name,
            decision=decision,
            current_price=price,
            df=df,
            config=self.config,
            strategy_type=StrategyType.ATR_BASED
        )  # 1行で完了
```

**削減実績**:
- **重複コード**: 約300行削除（5戦略×60行）
- **保守対象**: 5箇所 → 1箇所に集約
- **一貫性**: 全戦略で統一されたリスク管理

## 🧪 テスト

```bash
# 共通モジュールのテスト実行
python -m pytest tests/unit/strategies/utils/ -v

# 統合基盤確認（Phase 49.14システム整合性検証）
bash scripts/testing/validate_system.sh
```

**テスト対象**:
- **EntryAction・StrategyType**: 定数の正確性
- **RiskManager**: ストップロス・利確・ポジションサイズ計算精度
- **SignalBuilder**: シグナル生成・エラーハンドリング

## ⚠️ 重要事項

### **特性・制約**
- **5戦略共通**: ATRBased・MochipoyAlert・MultiTimeframe・DonchianChannel・ADXTrendStrength対応
- **統一リスク管理**: 全戦略で一貫したストップロス・利確・ポジションサイズ計算
- **Phase 30新機能**: 適応型ATR倍率・最小SL距離保証による少額資金対応
- **後方互換性**: 既存インターフェース維持・段階的移行可能
- **設定統合**: config/core/thresholds.yaml連携・一元管理
- **Phase 49完了**: 実用的機能に集中・保守性重視
- **依存**: pandas・numpy・datetime・src.strategies.base・src.core.*

---

**戦略共通処理モジュール（Phase 49完了）**: 5戦略統一管理・適応型ATR倍率・最小SL距離保証・重複排除・リスク管理統合・シグナル生成標準化システム。
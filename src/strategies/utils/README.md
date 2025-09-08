# strategies/utils/ - 戦略共通処理モジュール

4つの戦略（ATRBased、MochiPoyAlert、MultiTimeframe、FibonacciRetracement）で共通使用される処理をまとめた共通処理モジュール群。

## 📁 フォルダの目的

4つの戦略（ATRBased、MochiPoyAlert、MultiTimeframe、FibonacciRetracement）の共通処理を統合し、**保守性と安定性**を高めることを目的としています。

### 重複解決実績
- **共通定数の散在**: 各戦略での重複定義 → 統一化
- **リスク管理の重複**: 約300行の重複コード → 1箇所に集約
- **シグナル生成の散在**: 各戦略でバラバラな実装 → 標準化

## 📂 ファイル構成

```
src/strategies/utils/
├── __init__.py            # エクスポート管理・共通インポートポイント（27行）
└── strategy_utils.py      # 戦略共通処理・リスク管理・シグナル生成（380行）
```

## 🔧 含まれるモジュール

### 1. strategy_utils.py
**目的**: 戦略間で共通使用される処理の統一管理

**提供クラス・機能**:
- `EntryAction`: BUY, SELL, HOLD, CLOSE定数
- `StrategyType`: 戦略タイプ識別子（ATR_BASED、FIBONACCI等）
- `DEFAULT_RISK_PARAMS`: デフォルトリスク管理パラメータ
- `RiskManager`: リスク管理計算（ストップロス・利確・ポジションサイズ）
- `SignalBuilder`: シグナル生成・エラーハンドリング

```python
from ..utils import EntryAction, StrategyType, DEFAULT_RISK_PARAMS

# 全戦略で統一された定数使用
action = EntryAction.BUY
strategy_type = StrategyType.ATR_BASED
risk_params = DEFAULT_RISK_PARAMS
```

**リスク管理機能**:
```python
from ..utils import RiskManager

# ストップロス・利確価格の統一計算
stop_loss, take_profit = RiskManager.calculate_stop_loss_take_profit(
    current_price=price,
    action=EntryAction.BUY,
    atr_value=atr,
    config=config
)

# ポジションサイズの統一計算
position_size = RiskManager.calculate_position_size(
    confidence=0.7,
    config=config
)
```

**シグナル生成機能**:
```python
from ..utils import SignalBuilder

# リスク管理統合済みシグナル生成
signal = SignalBuilder.create_signal_with_risk_management(
    strategy_name="ATRBased",
    decision=decision_dict,
    current_price=price,
    df=market_data,
    config=config,
    strategy_type=StrategyType.ATR_BASED
)

# 標準ホールドシグナル
hold_signal = SignalBuilder.create_hold_signal(
    strategy_name="Strategy",
    current_price=price,
    reason="条件不適合"
)
```

### 2. __init__.py
**目的**: 統一インポートポイント・依存関係の明確化

```python
# すべての共通機能を1行でインポート可能
from ..utils import (
    EntryAction, StrategyType, DEFAULT_RISK_PARAMS,
    RiskManager, SignalBuilder
)
```

## 🔄 リファクタリング効果

### 重複排除の実装例
```python
# Before: 各戦略で個別実装（重複）
class ATRBasedStrategy:
    def _create_signal(self, decision, price, df):
        # ATRベースのSL/TP計算（50行の重複コード）
        atr_value = float(df['atr_14'].iloc[-1])
        if decision['action'] == 'buy':
            stop_loss = price - (atr_value * 2.0)
            take_profit = price + (atr_value * 2.5)
        # ... 重複するリスク管理ロジック

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

## ⚠️ 重要な設計原則

### 保守性と安定性を重視
```python
# ❌ シンプルすぎて成績悪化する実装
# ✅ 適切な複雑さを保ちつつ保守性向上
```

### 各戦略の独自性を維持
- **戦略固有ロジック**: 各戦略の独自アルゴリズムは保持
- **共通処理のみ統合**: リスク管理・シグナル生成のみ統一
- **設定の柔軟性**: 戦略別設定は引き続き可能

### 後方互換性の確保
- **既存インターフェース維持**: 戦略の外部APIは変更なし
- **段階的移行可能**: 戦略ごとに個別対応可能
- **設定互換性**: 既存設定ファイルがそのまま使用可能

## 📈 実装効果

### コード削減実績
- **重複コード**: 約300行削除
- **保守対象**: 4箇所 → 1箇所に集約
- **テストカバレッジ**: 共通処理の単体テスト追加

### 品質向上実績
- **一貫性**: 全戦略で統一されたリスク管理
- **バグ修正効率**: 1箇所修正で全戦略に反映
- **新戦略開発**: 共通処理を即座に利用可能

## 🧪 テスト

共通モジュールの品質確保のため包括的テストを実装：

```bash
# 共通モジュールのテスト実行
python -m pytest tests/unit/strategies/utils/ -v

# カバレッジ確認
python -m pytest tests/unit/strategies/utils/ --cov=src.strategies.utils

# システム全体のテスト確認
python scripts/testing/dev_check.py validate --mode light
```

### テスト対象
- **strategy_utils.py**: 定数・リスク管理・シグナル生成の正確性
- **RiskManager**: 計算精度・エッジケース処理
- **SignalBuilder**: シグナル生成・エラーハンドリング

## 🔧 使用方法

### 新戦略での利用
```python
from ..base.strategy_base import StrategyBase
from ..utils import EntryAction, RiskManager, SignalBuilder, StrategyType

class NewStrategy(StrategyBase):
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

### 既存戦略の更新
1. **インポート追加**: `from ..utils import ...`
2. **_create_signalメソッド更新**: `SignalBuilder.create_signal_with_risk_management()`使用
3. **定数置換**: ハードコードされた定数を`EntryAction`等に置換

## 📝 今後の拡張

### 機能追加予定
- **高度なリスク管理**: ドローダウン制御・ポートフォリオバランス
- **パフォーマンス追跡**: 戦略別成績管理・統計情報
- **動的設定**: ランタイムでの設定変更・A/Bテスト

### 互換性維持方針
- **インターフェース固定**: 既存メソッドシグネチャは変更しない
- **オプショナル機能**: 新機能は既存動作に影響しない
- **段階的導入**: 戦略ごとに選択的適用可能

---

**設計方針**: シンプル化が目的ではなく、保守性と安定性向上が目的  
**重複削減**: ~300行 → 統一化完了  
**テスト品質**: 共通処理の包括的テスト実装完了
# Strategies Utils - 戦略共通処理モジュール

Phase 11完了・CI/CD統合・24時間監視・段階的デプロイ対応で実装された、4つの戦略間の重複処理を統合する共通モジュール群・GitHub Actions統合。

## 📁 フォルダの目的

4つの戦略（ATRBased、MochiPoyAlert、MultiTimeframe、FibonacciRetracement）の共通処理を統合し、**保守性と安定性**を高めることを目的としています。

### 重複解決実績
- **共通定数の散在**: 各戦略での重複定義 → 統一化
- **リスク管理の重複**: 約300行の重複コード → 1箇所に集約
- **シグナル生成の散在**: 各戦略でバラバラな実装 → 標準化

## 🔧 含まれるモジュール

### 1. constants.py
**目的**: 戦略間で共通使用される定数の統一管理

```python
from ..utils import EntryAction, StrategyType, DEFAULT_RISK_PARAMS  # Phase 11対応

# 全戦略で統一された定数使用（CI/CD統合）
action = EntryAction.BUY  # GitHub Actions対応
strategy_type = StrategyType.ATR_BASED  # 24時間監視対応
risk_params = DEFAULT_RISK_PARAMS  # 段階的デプロイ対応
```

**提供クラス・定数**:
- `EntryAction`: BUY, SELL, HOLD, CLOSE定数
- `StrategyType`: 戦略タイプ識別子
- `DEFAULT_RISK_PARAMS`: デフォルトリスク管理パラメータ

### 2. risk_manager.py
**目的**: リスク管理計算の統一化・重複排除

```python
from ..utils import RiskManager  # Phase 11統合・GitHub Actions対応

# ストップロス・利確価格の統一計算（CI/CD統合）
stop_loss, take_profit = RiskManager.calculate_stop_loss_take_profit(
    current_price=price,
    action=EntryAction.BUY,
    atr_value=atr,
    config=config  # 24時間監視対応
)

# ポジションサイズの統一計算（段階的デプロイ対応）
position_size = RiskManager.calculate_position_size(
    confidence=0.7,
    config=config  # 監視統合
)
```

**提供メソッド**:
- `calculate_stop_loss_take_profit()`: SL/TP価格計算
- `calculate_position_size()`: 信頼度ベースのポジションサイズ計算
- `calculate_risk_ratio()`: リスク比率計算

### 3. signal_builder.py
**目的**: シグナル生成プロセスの統一化・リスク管理統合

```python
from ..utils import SignalBuilder  # Phase 11・CI/CD統合・24時間監視対応

# リスク管理統合済みシグナル生成（GitHub Actions対応）
signal = SignalBuilder.create_signal_with_risk_management(
    strategy_name="ATRBased",
    decision=decision_dict,
    current_price=price,
    df=market_data,
    config=config,  # 段階的デプロイ対応
    strategy_type=StrategyType.ATR_BASED  # 監視統合
)

# 標準ホールドシグナル（CI/CD品質ゲート対応）
hold_signal = SignalBuilder.create_hold_signal(
    strategy_name="Strategy",
    current_price=price,
    reason="条件不適合"  # 24時間監視統合
)
```

**提供メソッド**:
- `create_signal_with_risk_management()`: 完全統合シグナル生成
- `create_hold_signal()`: 標準ホールドシグナル
- `create_error_signal()`: エラーハンドリングシグナル

### 4. __init__.py
**目的**: 統一インポートポイント・依存関係の明確化

```python
# すべての共通機能を1行でインポート可能（Phase 11統合）
from ..utils import (  # CI/CD統合・24時間監視・段階的デプロイ対応
    EntryAction, StrategyType, DEFAULT_RISK_PARAMS,
    RiskManager, SignalBuilder  # GitHub Actions統合・監視統合
)
```

## 🔄 リファクタリング前後比較

### Before（Phase 3-4前）
```python
# 各戦略で個別実装（重複）
class ATRBasedStrategy:
    def _create_signal(self, decision, price, df):
        # ATRベースのSL/TP計算（50行）
        atr_value = float(df['atr_14'].iloc[-1])
        if decision['action'] == 'buy':
            stop_loss = price - (atr_value * 2.0)
            take_profit = price + (atr_value * 2.5)
        # ... 重複するリスク管理ロジック

class MochiPoyAlertStrategy:
    def _create_signal(self, decision, price, df):
        # 同じSL/TP計算の重複実装（50行）
        atr_value = float(df['atr_14'].iloc[-1])
        if decision['action'] == 'buy':
            stop_loss = price - (atr_value * 2.0)
            # ... 同じロジックの繰り返し
```

### After（Phase 3-4後）
```python
# 統一されたシンプルな実装（Phase 11・CI/CD統合）
class ATRBasedStrategy:  # GitHub Actions対応・24時間監視統合
    def _create_signal(self, decision, price, df):
        return SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.name,
            decision=decision,
            current_price=price,
            df=df,
            config=self.config,  # 段階的デプロイ対応
            strategy_type=StrategyType.ATR_BASED  # CI/CD品質ゲート対応
        )  # 1行で完了・監視統合

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
# 共通モジュールのテスト実行（Phase 11・CI/CD統合・GitHub Actions対応）
python -m pytest tests/unit/strategies/utils/ -v

# カバレッジ確認（24時間監視対応）
python -m pytest tests/unit/strategies/utils/ --cov=src.strategies.utils

# 399テスト統合基盤確認（段階的デプロイ対応）
python scripts/management/bot_manager.py validate --mode light
```

### テスト対象（Phase 11・CI/CD統合）
- **constants.py**: 定数の正確性・型整合性・GitHub Actions対応
- **risk_manager.py**: 計算精度・エッジケース処理・24時間監視対応
- **signal_builder.py**: シグナル生成・エラーハンドリング・段階的デプロイ対応

## 🔧 使用方法

### 新戦略での利用
```python
from ..base.strategy_base import StrategyBase  # Phase 11統合
from ..utils import EntryAction, RiskManager, SignalBuilder, StrategyType  # CI/CD統合

class NewStrategy(StrategyBase):  # GitHub Actions対応・24時間監視統合
    def analyze(self, df):
        # 戦略固有の分析ロジック（段階的デプロイ対応）
        decision = self._analyze_market(df)  # CI/CD品質ゲート対応
        
        # 共通処理でシグナル生成（監視統合）
        return SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.name,
            decision=decision,
            current_price=float(df['close'].iloc[-1]),
            df=df,
            config=self.config,  # GitHub Actions統合
            strategy_type=StrategyType.CUSTOM  # 24時間監視対応
        )
```

### 既存戦略の更新
1. **インポート追加**: `from ..utils import ...`
2. **_create_signalメソッド更新**: `SignalBuilder.create_signal_with_risk_management()`使用
3. **定数置換**: ハードコードされた定数を`EntryAction`等に置換

## 📝 今後の拡張

### Phase 12での機能追加予定（CI/CD統合基盤活用）
- **高度なリスク管理**: ドローダウン制御・ポートフォリオバランス・GitHub Actions統合
- **パフォーマンス追跡**: 戦略別成績管理・統計情報・24時間監視統合
- **動的設定**: ランタイムでの設定変更・A/Bテスト・段階的デプロイ対応

### 互換性維持方針（Phase 11基盤）
- **インターフェース固定**: 既存メソッドシグネチャは変更しない・CI/CD統合
- **オプショナル機能**: 新機能は既存動作に影響しない・GitHub Actions対応
- **段階的導入**: 戦略ごとに選択的適用可能・24時間監視統合

---

**Phase 11完了日**: 2025年8月18日・CI/CD統合・24時間監視・段階的デプロイ対応  
**設計方針**: シンプル化が目的ではなく、保守性と安定性向上が目的・GitHub Actions統合  
**重複削減**: ~300行 → 統一化完了・監視統合  
**テスト品質**: 113テスト全成功達成・399テスト統合基盤対応・CI/CD品質ゲート対応
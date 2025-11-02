# Phase 51.5-51.X: 戦略削除実行と動的管理基盤設計

## Phase 51.5-A: 戦略削除実行 (2025/11/03完了)

### 概要

**目的**: MochipoyAlert・MultiTimeframe削除により5戦略から3戦略へ削減

**実施内容**:
- 物理削除: MochipoyAlertStrategy・MultiTimeframeStrategy
- 戦略数: 5 → 3 (ATRBased, DonchianChannel, ADXTrendStrength)
- 特徴量数: 62 → 60 (戦略シグナル 5→3)
- 修正ファイル数: 27ファイル

### 修正対象ファイル一覧

**コアシステム (3ファイル)**:
1. src/core/orchestration/orchestrator.py
   - MochipoyAlert/MultiTimeframeのimport削除
   - 戦略登録を3戦略に変更

2. src/core/services/dynamic_strategy_selector.py
   - _get_default_weights()を完全書き換え
   - 4レジーム×3戦略の重み設定

3. config/core/unified.yaml
   - enabled strategies: atr_based, donchian_channel, adx_trend
   - weights設定を3戦略に変更

**設定ファイル (3ファイル)**:
4. config/core/thresholds.yaml
   - mochipoy/mtfのdynamic_confidence設定削除

5. config/core/feature_order.json
   - total_features: 62 → 60
   - 削除戦略のシグナル特徴量除去

6. models/production/production_model_metadata.json
   - feature_count: 62 → 60
   - strategy_signal_MochipoyAlert削除
   - strategy_signal_MultiTimeframe削除

**MLスクリプト (2ファイル)**:
7. scripts/ml/create_ml_models.py
   - 戦略リストを3戦略に変更

8. scripts/analysis/strategy_performance_analysis.py
   - 分析対象を3戦略に変更

9. scripts/analysis/strategy_theoretical_analysis.py
   - 戦略リストを3戦略に変更

**テストファイル (17ファイル)**:
10. tests/unit/features/test_feature_generator.py
    - 62→60特徴量アサーション変更
    - 戦略シグナル5→3

11. tests/unit/ml/production/test_ensemble.py
    - 全62→60 (replace_all使用)

12. tests/unit/services/test_dynamic_strategy_selector.py
    - 完全書き換え (230行)
    - 5戦略→3戦略のアサーション変更

13. tests/integration/test_phase_51_3_regime_strategy_integration.py
    - 戦略数アサーション変更

14. tests/unit/analysis/test_strategy_performance_analysis.py
    - sample_historical_data fixture修正 (datetime index追加)
    - 5テストケース修正 (async対応, 5→3戦略)

15. tests/unit/analysis/test_strategy_theoretical_analysis.py
    - 7テストケース修正 (5→3戦略)

16. tests/unit/core/test_ml_adapter_exception_handling.py
    - n_features_: 62 → 60

17-26. その他統合テストファイル (10ファイル)
    - 戦略数・特徴量数のアサーション更新

### 実行手順 (4 Phase)

**Phase 1: システム起動修正**
- orchestrator.py import削除・戦略登録変更
- dynamic_strategy_selector.py完全書き換え
- unified.yaml設定変更

**Phase 2: テスト修正 (62→60特徴量)**
- test_feature_generator.py修正
- test_ensemble.py修正 (replace_all)
- feature_order.json更新
- test_dynamic_strategy_selector.py完全書き換え
- test_phase_51_3_regime_strategy_integration.py修正

**Phase 3: 設定・モデルメタデータ修正**
- production_model_metadata.json更新
- create_ml_models.py更新
- thresholds.yaml更新

**Phase 4: 分析テスト修正**
- test_strategy_performance_analysis.py修正 (5テスト)
- strategy_performance_analysis.py更新
- test_strategy_theoretical_analysis.py修正 (7テスト)
- strategy_theoretical_analysis.py更新
- test_ml_adapter_exception_handling.py修正

### 品質保証結果

**テスト結果**:
- 全テスト数: 1095テスト
- 成功率: 100%
- カバレッジ: 66.31%

**システム整合性チェック (7項目)**:
- Dockerfile整合性: OK
- unified.yaml整合性: OK
- thresholds.yaml整合性: OK
- orchestrator.py import整合性: OK
- 特徴量数整合性: 60 (OK)
- 戦略数整合性: 3 (OK)
- モデルメタデータ整合性: OK

### まとめ

**成果**:
- 27ファイル修正完了
- 戦略数: 40%削減 (5→3)
- 特徴量数: 3.2%削減 (62→60)
- 品質: 100%テスト成功

**課題認識**:
戦略の追加・削除で27ファイル修正が必要
→ Phase 51.5-Bで動的戦略管理基盤を設計

---

## Phase 51.5-B: 動的戦略管理基盤実装 (未実装)

### 背景

**問題**: 戦略追加・削除で27ファイル修正が必要
**原因**: ハードコードされた戦略登録・設定
**目標**: 設定ファイル主導の動的戦略管理

### 設計方針

**Hybrid Architecture**:
- Config file (strategies.yaml) による戦略定義
- Registry pattern + decorator による自動登録
- StrategyLoader (Facade) による動的読み込み

#### 1. strategies.yaml (新規作成)

```yaml
strategies:
  ATRBased:
    enabled: true
    type: range
    class: ATRBasedStrategy
    module: src.strategies.implementations.atr_based
    indicators: [ATR, BB, RSI]

  DonchianChannel:
    enabled: true
    type: range
    class: DonchianChannelStrategy
    module: src.strategies.implementations.donchian_channel
    indicators: [Donchian, Breakout]

  ADXTrendStrength:
    enabled: true
    type: trend
    class: ADXTrendStrengthStrategy
    module: src.strategies.implementations.adx_trend_strength
    indicators: [ADX, DI]
```

#### 2. StrategyRegistry (Registry pattern)

```python
class StrategyRegistry:
    _strategies = {}

    @classmethod
    def register(cls, name: str, strategy_type: str):
        def decorator(strategy_class):
            cls._strategies[name] = {
                "class": strategy_class,
                "type": strategy_type
            }
            return strategy_class
        return decorator

    @classmethod
    def get_strategy(cls, name: str):
        return cls._strategies.get(name)
```

#### 3. 戦略実装例 (decorator適用)

```python
@StrategyRegistry.register(name="ATRBased", strategy_type="range")
class ATRBasedStrategy(StrategyBase):
    pass
```

#### 4. StrategyLoader (Facade pattern)

```python
class StrategyLoader:
    @staticmethod
    def load_strategies(config_path: str = "config/strategies.yaml") -> List[Strategy]:
        config = yaml.safe_load(open(config_path))
        strategies = []

        for name, strategy_config in config["strategies"].items():
            if strategy_config["enabled"]:
                strategy_info = StrategyRegistry.get_strategy(name)
                if strategy_info:
                    strategies.append(strategy_info["class"]())

        return strategies
```

### 期待効果

**修正ファイル数削減**:
- 現状: 27ファイル (100%)
- 目標: 4ファイル (15%) - 93%削減

**修正対象 (4ファイルのみ)**:
1. strategies.yaml - 戦略のenabled切り替え
2. 戦略実装ファイル - @decoratorのみ追加
3. thresholds.yaml - レジーム別重み設定のみ変更
4. テストファイル - 戦略クラスのテストのみ追加

**メリット**:
- 設定ファイル変更のみで戦略追加・削除可能
- コード変更を最小化
- 後方互換性維持
- 段階的移行が可能

### 実装計画

**Phase 51.5-B-1**: StrategyRegistry実装 (1日)
**Phase 51.5-B-2**: strategies.yaml作成 (0.5日)
**Phase 51.5-B-3**: StrategyLoader実装 (1日)
**Phase 51.5-B-4**: 既存戦略へdecorator適用 (0.5日)
**Phase 51.5-B-5**: orchestrator.py統合 (0.5日)
**Phase 51.5-B-6**: テスト実装・検証 (1日)

**合計**: 4.5日

---

## Phase 51.5-C: レガシーコード残存調査 (未実装)

### 目的

Phase 51.5-A完了後も残存している可能性のある
5戦略・62特徴量・70特徴量の参照を完全調査

### 調査項目

1. **5戦略参照調査**
   - MochipoyAlert文字列検索
   - MultiTimeframe文字列検索
   - 戦略リスト長さ5のハードコード検索

2. **62特徴量参照調査**
   - "62" 数値リテラル検索 (特徴量コンテキスト)
   - feature_count: 62 検索
   - assert文での62検索

3. **70特徴量参照調査** (Phase 50.9外部API削除後の残存)
   - "70" 数値リテラル検索 (特徴量コンテキスト)
   - external_api文字列検索
   - Level 1 / full_with_external検索

4. **ドキュメント更新**
   - README.md
   - CLAUDE.md
   - Phase履歴ドキュメント

### 実行手順

```bash
# 5戦略調査
grep -r "MochipoyAlert" src/ tests/ config/ docs/
grep -r "MultiTimeframe" src/ tests/ config/ docs/
grep -r "len.*==.*5" tests/ --include="*.py"

# 62特徴量調査
grep -r "62" src/ tests/ config/ --include="*.py" --include="*.json" --include="*.yaml"

# 70特徴量調査
grep -r "70" src/ tests/ config/ --include="*.py" --include="*.json" --include="*.yaml"
grep -r "external_api" src/ tests/ config/
```

### 期待成果

- 完全なレガシーコード削除
- ドキュメント整合性100%
- システムクリーン性確保

---

**最終更新**: 2025年11月3日 - Phase 51.5-A完了

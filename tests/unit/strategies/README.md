# Strategy Tests - 戦略システム包括的テスト

**Phase 13完了**: sklearn警告解消・306テスト100%成功・品質保証完成。Phase 3-4リファクタリングで実装された、戦略システム全体の**品質保証を担う包括的テストスイート**（113テスト・100%合格・0.44秒高速実行・CI/CD本番稼働・sklearn警告解消対応・品質保証完成）。

## 📁 フォルダの目的

4つの戦略実装・共通処理統合・戦略マネージャーの品質確保を通じて、**安定性・信頼性・保守性**を保証します。

### テスト戦略
- **完全カバレッジ**: 新規作成・リファクタリング対象の全コンポーネント
- **回帰防止**: 既存機能の動作保証
- **統合検証**: コンポーネント間の相互作用確認

## 🧪 テスト構成

```
tests/unit/strategies/
├── utils/                              # 共通モジュールテスト（新規）
│   ├── test_constants.py              # 定数・型システム
│   ├── test_risk_manager.py           # リスク管理計算
│   └── test_signal_builder.py         # シグナル生成統合
├── implementations/                    # 戦略実装テスト（更新）
│   ├── test_atr_based.py              # ATRBased戦略
│   ├── test_mochipoy_alert.py         # MochiPoyAlert戦略
│   ├── test_multi_timeframe.py        # MultiTimeframe戦略
│   └── test_fibonacci_retracement.py  # FibonacciRetracement戦略
└── test_strategy_manager.py           # 戦略マネージャー（更新）
```

## 📊 テスト実績

### 実行サマリー
```bash
====================== 113 passed, 144 warnings in 0.44s =======================
```

**Phase 13完了時点**:
- **総テスト数**: 113テスト（全成功・100%合格・CI/CD本番稼働・sklearn警告解消対応）
- **実行時間**: 0.44秒（高速実行・品質保証完成・GitHub Actions本番稼働）
- **警告**: sklearn警告解消完了・pandas・numpy互換性確保・品質保証完成

### カテゴリ別テスト数

| カテゴリ | テスト数 | 内容 |
|----------|----------|------|
| **共通モジュール** | 33テスト | 新規utils/のテスト |
| - constants.py | 8テスト | 定数・列挙型・デフォルト値 |
| - risk_manager.py | 12テスト | SL/TP・ポジションサイズ計算 |
| - signal_builder.py | 13テスト | 統合シグナル生成・エラー処理 |
| **戦略実装** | 62テスト | リファクタリング後4戦略 |
| - ATRBased | 15テスト | ボラティリティ・エントリー判定 |
| - MochiPoyAlert | 15テスト | RCI・多数決システム |
| - MultiTimeframe | 15テスト | 時間軸統合・トレンド整合性 |
| - FibonacciRetracement | 17テスト | スイング検出・フィボレベル |
| **統合管理** | 18テスト | 戦略マネージャー |
| - 基本機能 | 8テスト | 登録・解除・重み管理 |
| - 統合判定 | 6テスト | シグナル統合・コンフリクト解決 |
| - パフォーマンス | 4テスト | 成績追跡・統計情報 |

## 🔧 テスト実行

### 全戦略テスト実行
```bash
# 戦略関連テスト全実行
python -m pytest tests/unit/strategies/ -v

# 詳細出力での実行
python -m pytest tests/unit/strategies/ -v -s

# カバレッジ付きで実行
python -m pytest tests/unit/strategies/ --cov=src.strategies --cov-report=html
```

### カテゴリ別実行
```bash
# 共通モジュールのみ
python -m pytest tests/unit/strategies/utils/ -v

# 戦略実装のみ
python -m pytest tests/unit/strategies/implementations/ -v

# 戦略マネージャーのみ
python -m pytest tests/unit/strategies/test_strategy_manager.py -v
```

### 特定戦略の実行
```bash
# ATRBased戦略
python -m pytest tests/unit/strategies/implementations/test_atr_based.py -v

# フィボナッチ戦略
python -m pytest tests/unit/strategies/implementations/test_fibonacci_retracement.py -v
```

## 🧩 テスト内容詳細

### 1. 共通モジュールテスト (`utils/`)

#### constants.py テスト
```python
# テスト内容
- EntryAction定数の正確性
- StrategyType列挙型の整合性
- DEFAULT_RISK_PARAMS値の妥当性
- 型安全性・不変性確認
```

#### risk_manager.py テスト
```python
# テスト内容
- ストップロス・利確価格の正確な計算
- ポジションサイズの信頼度ベース調整
- リスク比率計算の精度
- エッジケース・エラーハンドリング
```

#### signal_builder.py テスト
```python
# テスト内容
- 統合シグナル生成の正確性
- リスク管理の自動統合
- エラーシグナルの適切な生成
- 各戦略タイプでの動作確認
```

### 2. 戦略実装テスト (`implementations/`)

#### ATRBased戦略テスト (15テスト)
```python
# 主要テストケース
- ボラティリティ計算の正確性
- 動的閾値による判定ロジック
- 順張りエントリーのタイミング
- リスク管理統合の確認
- volatility_20エラー修正の検証
```

#### MochiPoyAlert戦略テスト (15テスト)
```python
# 主要テストケース
- RCI計算の正確性
- 多数決システムの動作
- 複数指標の統合判定
- シンプル化後の一貫性
- 指標組み合わせでの判定精度
```

#### MultiTimeframe戦略テスト (15テスト)
```python
# 主要テストケース
- 4時間足・15分足の統合
- 時間軸間のトレンド整合性
- エントリータイミングの精度
- 2軸構成での効率性
- データ不足時の処理
```

#### FibonacciRetracement戦略テスト (17テスト)
```python
# 主要テストケース
- スイング高値・安値の検出
- フィボナッチレベル計算の正確性
- レベル接近判定の精度
- RSI・ローソク足での反転確認
- 複合指標による信頼度計算
```

### 3. 戦略マネージャーテスト (18テスト)

```python
# 主要テストケース
class TestStrategyManager:
    def test_manager_initialization(self):       # 初期化
    def test_register_strategy_success(self):    # 戦略登録
    def test_unregister_strategy(self):          # 戦略解除
    def test_analyze_market_single_strategy(self): # 単一戦略分析
    def test_analyze_market_consistent_signals(self): # 一貫シグナル
    def test_analyze_market_signal_conflict(self):    # コンフリクト解決
    def test_calculate_weighted_confidence(self):     # 重み付け信頼度
    def test_get_strategy_performance(self):          # パフォーマンス取得
    # ... 他10テスト
```

## 📈 品質指標

### テストカバレッジ
- **戦略実装**: 95%以上
- **共通モジュール**: 100%
- **統合管理**: 90%以上
- **エラーハンドリング**: 85%以上

### パフォーマンス指標
- **実行時間**: 平均0.44秒（113テスト）
- **メモリ使用量**: 50MB以下
- **並列実行**: pytest-xdist対応

## 🔍 テストデータ設計

### 市場データ模擬
```python
# 各戦略に特化したテストデータ
def create_test_data():
    # ATRBased: 高ボラティリティデータ
    # MochiPoyAlert: 複数指標シグナルデータ
    # MultiTimeframe: 異なる時間軸データ
    # FibonacciRetracement: スイング相場データ
```

### エッジケーステスト
```python
# 境界値・異常系の包括的テスト
- データ不足（最小データ数未満）
- 極端な価格変動（異常値処理）
- 設定エラー（無効なパラメータ）
- API通信エラー（外部依存なし設計）
```

## 🛠️ テスト環境

### 前提条件
```bash
# 必要なPythonパッケージ
pytest>=7.0.0
pytest-cov>=4.0.0
pandas>=2.0.0
numpy>=1.24.0
```

### CI/CD本番稼働（Phase 13完了）
```yaml
# GitHub Actions本番稼働・sklearn警告解消対応
name: Strategy Tests Phase 13
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Strategy Tests with CI/CD Production
        run: |
          python -m pytest tests/unit/strategies/ -v --cov
          python scripts/testing/dev_check.py validate --mode light
          python scripts/testing/dev_check.py health-check
```

## 🐛 トラブルシューティング

### よくある問題

#### 1. pandas警告の対応
```bash
# 警告が多い場合（144 warnings）
python -m pytest tests/unit/strategies/ -v --disable-warnings

# 特定警告の無視
python -m pytest tests/unit/strategies/ -v -W ignore::UserWarning
```

#### 2. テスト実行時間の最適化
```bash
# 並列実行（テスト時間短縮）
pip install pytest-xdist
python -m pytest tests/unit/strategies/ -n auto

# 失敗時即座停止
python -m pytest tests/unit/strategies/ -x
```

#### 3. データ生成エラー
```python
# randomデータ生成時の再現性確保
import numpy as np
np.random.seed(42)  # テストで固定シード使用
```

## 🔮 今後の拡張

### Phase 12でのテスト強化予定（Phase 12完了後）
```python
# 追加予定テスト
class TestAdvancedStrategies:
    def test_adaptive_parameters(self):      # パラメータ自動最適化
    def test_market_regime_detection(self):  # 市場体制検出
    def test_performance_attribution(self):  # パフォーマンス要因分析
    def test_risk_adjusted_metrics(self):    # リスク調整後指標
```

### A/Bテストフレームワーク
```python
# 戦略改良効果の定量測定
class TestABTesting:
    def test_strategy_comparison(self):      # 戦略比較
    def test_parameter_optimization(self):   # パラメータ最適化効果
    def test_feature_importance(self):       # 特徴量重要度分析
```

### 統合テスト強化
```python
# より現実的なシナリオテスト
class TestRealWorldScenarios:
    def test_market_crash_scenario(self):    # 市場暴落時
    def test_low_liquidity_periods(self):    # 流動性低下時
    def test_high_frequency_signals(self):   # 高頻度シグナル時
```

## 📋 テスト実行チェックリスト

### リファクタリング後の確認事項
```bash
✅ 全113テスト成功
✅ 実行時間1分以内
✅ 新機能のテストカバレッジ100%
✅ 既存機能の回帰テスト通過
✅ エラーハンドリングテスト完了
✅ パフォーマンステスト通過
```

### デプロイ前チェック
```bash
# 必須実行コマンド
python -m pytest tests/unit/strategies/ -v --cov=src.strategies --cov-report=term-missing

# 確認事項
- カバレッジ90%以上
- 全テスト成功
- 警告数が許容範囲内
- 実行時間2分以内
```

---

**Phase 13完了日**: 2025年8月19日  
**テスト方針**: 包括的品質保証・回帰防止・統合検証・CI/D本番稼働・sklearn警告解消対応  
**実績**: 113テスト全成功・0.44秒高速実行・GitHub Actions本番稼働・品質保証完成  
**カバレッジ**: 新規モジュール100%・戦略実装95%・CI/CD品質ゲート・306テスト100%成功  
**保守性**: sklearn警告解消完了・監視統合・自動復旧対応・品質保証完成
# src/strategies/implementations/ - 取引戦略実装群

## 🎯 役割・責任

AI自動取引システムの戦略実装層。4つの独立した取引戦略（ATRベース・フィボナッチ・もちぽよアラート・マルチタイムフレーム）を実装。各戦略は異なる技術指標や市場観測手法を使用し、多様な市場状況に対応。

## 📂 ファイル構成

```
src/strategies/implementations/
├── __init__.py                  # 実装戦略エクスポート（9行）
├── atr_based.py               # ATRベース戦略・ボラティリティ分析（348行）
├── fibonacci_retracement.py   # フィボナッチ戦略・レベル分析（563行）
├── mochipoy_alert.py          # もちぽよアラート・複合指標（283行）
└── multi_timeframe.py         # マルチタイムフレーム・時間軸統合（313行）
```

## 🔧 主要コンポーネント

### **各戦略の特徴**
- **ATRベース**: ボラティリティを活用した動的エントリー・エグジット
- **フィボナッチ**: サポート/レジスタンスレベルでの反転狙い
- **もちぽよアラート**: 複数指標の多数決システム
- **マルチタイムフレーム**: 異なる時間軸でのトレンド連携分析

### **戦略統一管理システム**

**設定一元化**:
- **設定ファイル**: `config/core/thresholds.yaml`
- **4戦略統合**: ATRBased・FibonacciRetracement・MochipoyAlert・MultiTimeframe
- **統一調整可能**: 一括設定変更で全戦略に反映

**設定構造**:
```yaml
# 4戦略統一管理システム
strategies:
  atr_based:
    normal_volatility_strength: 0.3  # 通常ボラティリティ強度
    hold_confidence: 0.3             # HOLD決定時信頼度
  fibonacci_retracement:
    no_signal_confidence: 0.3        # 反転シグナルなし信頼度
    no_level_confidence: 0.3         # フィボレベル接近なし信頼度
  mochipoy_alert:
    hold_confidence: 0.3             # HOLD信頼度
  multi_timeframe:
    hold_confidence: 0.3             # HOLD信頼度
```

**使用方法**:
1. **thresholds.yamlの値変更** → 4戦略すべてに反映
2. **閾値調整**: 0.3→0.2（より積極的）・0.3→0.4（より保守的）
3. **即座反映**: 再起動で設定適用・デプロイ不要

## ⚙️ 統合判定システム

### **統合判定フロー**

```
【各戦略並行実行】→ 個別StrategySignal生成
        ↓
【アクション別グループ化】→ {"buy": [...], "sell": [...], "hold": [...]}
        ↓
【競合検知】→ BUY vs SELL同時存在チェック
        ↓
【競合なし】→ 多数決 + 重み付け統合
【競合あり】→ 重み付け信頼度比較
        ↓
【最終統合シグナル】→ StrategySignal(strategy_name="StrategyManager")
```

**例**: 個別戦略結果
```python
ATRBased → StrategySignal(action="buy", confidence=0.7)
FibonacciRetracement → StrategySignal(action="sell", confidence=0.6)  
MochipoyAlert → StrategySignal(action="hold", confidence=0.3)
MultiTimeframe → StrategySignal(action="buy", confidence=0.8)
```

### **競合解決メカニズム**

**競合なし（例: SELL 2 + HOLD 2）**:
- BUY vs SELL同時でないため競合なし
- 多数決で積極的アクション（SELL）を選択

**競合あり（例: SELL 2 + BUY 2）**:
- BUY vs SELL同時のため競合あり
- 重み付け信頼度比較で判定
- 信頼度差0.1未満なら安全なHOLD選択
- 信頼度差0.1以上なら高信頼度グループが勝利

### **3段階取引実行条件**

**段階的フィルタリング**:
1. **戦略レベル**: 各戦略の最低信頼度閾値（通常0.4-0.5）
2. **ML信頼度**: ML予測信頼度 ≥ 0.25 必須
3. **リスク管理**: リスクスコア < 0.6で承認、≥ 0.8で拒否

**最終実行判定**:
- すべての条件を満たしたAPPROVEDのみ実際取引実行
- 複数段階のフェイルセーフ機能で資金保全を最優先

### **完全な取引判定フロー**

```
【データ取得】→【特徴量生成】→【4戦略実行】
                    ↓
【StrategyManager統合】→ 競合時: 重み付け信頼度比較
                    ↓
【ML予測統合】→ ProductionEnsemble 3モデル予測
                    ↓
【IntegratedRiskManager】→ ML≥0.25 & リスク<0.6 で承認
                    ↓
【OrderExecutor】→ APPROVEDのみ実際取引実行
```

**重要ポイント**:
- StrategyManagerは統合シグナル生成のみ担当
- 実際の取引実行判定はIntegratedRiskManagerが実施
- 複数段階のフェイルセーフ機能で資金保全を最優先

### **設計原則**
- **保守性優先**: シンプル化よりも保守性と安定性を重視
- **成績維持**: 戦略の本質的なロジックは保持
- **重複排除**: 共通処理の統合による保守性向上
- **モジュール性**: 各戦略の独立性と統合性のバランス

## 🔧 実装された戦略

### **atr_based.py（348行）**
**戦略タイプ**: ボラティリティ追従型・動的エントリーエグジット

**主要クラス**:
```python
class ATRBasedStrategy(StrategyBase):
    def __init__(self, config=None)                               # ATR戦略初期化
    def analyze(self, df: pd.DataFrame) -> StrategySignal         # ATR分析実行
    def _make_decision(self, bb_analysis, rsi_analysis, atr_analysis)  # 判定ロジック
    def _analyze_bb_position(self, df)                            # ボリンジャーバンド分析
    def _analyze_rsi(self, df)                                    # RSI分析
    def _analyze_atr_volatility(self, df)                         # ATRボラティリティ分析
```

**特徴**:
- **不一致取引**: BB・RSI不一致時も強いシグナルで取引実行（信頼度×0.8ペナルティ）
- **動的閾値**: high 0.45・very_high 0.60の信頼度閾値
- **市場適応**: 市場ボラティリティ連動HOLD信頼度（0.1-0.8変動）

**適用市場**: 高ボラティリティ相場・トレンドフォロー・積極的取引機会

### **mochipoy_alert.py（283行）**
**戦略タイプ**: 複合指標・多数決システム

**主要クラス**:
```python
class MochiPoyAlertStrategy(StrategyBase):
    def __init__(self, config=None)                               # もちぽよ初期化
    def analyze(self, df: pd.DataFrame) -> StrategySignal         # 複合分析実行
    def _analyze_ema(self, df)                                    # EMA分析
    def _analyze_macd_and_rci(self, df)                          # MACD・RCI分析
    def _make_simple_decision(self, ema_signal, macd_signal, rci_signal)  # 多数決判定
```

```python
# 攻撃的主要ロジック（月100-200取引対応）
- RCI・RSI・BB 1票でも取引実行（3票→1票変更）
- 攻撃的多数決システム（buy_votes==1 and sell_votes==0 で実行）
- 低信頼度でも取引実行（confidence=0.4）
```

**攻撃的特徴**:
- **1票取引**: RSI・RCI・BB のうち1つでも合意すれば取引実行
- **攻撃的多数決**: 保守的な全票一致から積極的な1票取引に変更
- **低信頼度取引**: 信頼度0.4でも取引実行・機会損失防止

**適用市場**: 全市場状況・機会損失防止・積極的シグナル捕捉・月100-200取引対応

### 3. Multi Timeframe Strategy (`multi_timeframe.py`)
**戦略タイプ**: マルチタイムフレーム分析型・手動実行監視統合  
**コード削減**: 668行 → 313行（53%削減・監視統合）

```python
# 主要ロジック
- 4時間足: 中期トレンド分析
- 15分足: 短期エントリータイミング
- 2軸統合: 時間軸間の整合性確認
```

**特徴**:
- **2軸構成**: 4時間足＋15分足の効率的な組み合わせ
- **トレンド整合性**: 異なる時間軸での方向性一致確認
- **エントリー精度**: 短期軸でのタイミング最適化

**適用市場**: 中期トレンド継続時・明確な方向性のある相場・GitHub Actions統合

### 4. Fibonacci Retracement Strategy (`fibonacci_retracement.py`)
**戦略タイプ**: 反転狙い・レベル分析型・段階的デプロイ対応  
**コード削減**: 812行 → 563行（31%削減・CI/CD品質ゲート対応）

```python
# 主要ロジック
- スイング高値・安値の自動検出
- 基本フィボレベル（23.6%, 38.2%, 50%, 61.8%）
- RSI＋ローソク足での反転確認
```

**特徴**:
- **成績重視バランス**: 複雑さと効果のバランス調整
- **基本レベル重視**: 実績のある4つのフィボレベルに集中
- **反転確認**: 複数指標での反転サイン検証

**適用市場**: レンジ相場・調整局面・サポート/レジスタンス明確時・監視統合

## 🔄 Phase 13リファクタリング効果（本番運用移行・システム最適化・CI/CD準備完了）

### Before（リファクタリング前）
```python
# 各戦略で重複していたコード例
class ATRBasedStrategy:
    def _create_signal(self, decision, current_price, df):
        # 50行のリスク管理コード
        atr_value = float(df['atr_14'].iloc[-1])
        if decision['action'] == EntryAction.BUY:
            stop_loss = current_price - (atr_value * 2.0)
            take_profit = current_price + (atr_value * 2.5)
            position_size = 0.02 * decision['confidence']
        # ... 重複するロジック

class MochiPoyAlertStrategy:
    def _create_signal(self, decision, current_price, df):
        # 同じ50行のリスク管理コード（重複）
        atr_value = float(df['atr_14'].iloc[-1])
        # ... 同一ロジックの繰り返し
```

### After（リファクタリング後）
```python
# 統一された実装（Phase 13・CI/CDワークフロー最適化）
class ATRBasedStrategy:  # 本番運用対応
    def _create_signal(self, decision, current_price, df):
        return SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.name,
            decision=decision,
            current_price=current_price,
            df=df,
            config=self.config,
            strategy_type=StrategyType.ATR_BASED
        )  # 共通処理で1行実装・手動実行監視対応

class MochiPoyAlertStrategy:  # 段階的デプロイ対応
    def _create_signal(self, decision, current_price, df):
        return SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.name,
            decision=decision,
            current_price=current_price,
            df=df,
            config=self.config,
            strategy_type=StrategyType.MOCHIPOY_ALERT
        )  # 統一インターフェース・CI/CD品質ゲート対応
```

## 📊 削減実績サマリー

| 戦略名 | Before | After | 削減率 | 主要改善点 |
|--------|--------|-------|--------|------------|
| ATRBased | 566行 | 348行 | 38% | volatility_20エラー修正 |
| MochiPoyAlert | 559行 | 283行 | 49% | RCI保持+シンプル多数決 |
| MultiTimeframe | 668行 | 313行 | 53% | 2軸構成への集約 |
| FibonacciRetracement | 812行 | 563行 | 31% | 成績重視バランス調整 |
| **合計** | **2,605行** | **1,507行** | **42%** | **重複排除・安定性向上** |

## 🎯 戦略選択ガイド

### 市場状況別推奨戦略

**高ボラティリティ・トレンド相場**:
```python
# ATRBased + MultiTimeframe の組み合わせ
recommended = ["ATRBased", "MultiTimeframe"]
```

**横ばい・レンジ相場**:
```python
# MochiPoyAlert + FibonacciRetracement の組み合わせ
recommended = ["MochiPoyAlert", "FibonacciRetracement"]
```

**不明確な相場**:
```python
# 全戦略での分散判定
recommended = ["ATRBased", "MochiPoyAlert", "MultiTimeframe", "FibonacciRetracement"]
```

## 🔧 共通インターフェース

すべての戦略は統一されたインターフェースを提供：

### 基本メソッド
```python
from src.strategies.implementations.atr_based import ATRBasedStrategy

# 戦略初期化
strategy = ATRBasedStrategy(config=custom_config)

# 市場分析実行
signal = strategy.analyze(market_data_df)

# 必要特徴量取得
features = strategy.get_required_features()

# 戦略情報取得
info = strategy.get_info()
```

### StrategySignal出力
```python
@dataclass
class StrategySignal:
    strategy_name: str          # 戦略名
    action: str                 # BUY/SELL/HOLD/CLOSE
    confidence: float           # 信頼度 (0.0-1.0)
    current_price: float        # 現在価格
    stop_loss: Optional[float]  # ストップロス価格
    take_profit: Optional[float] # 利確価格
    position_size: Optional[float] # ポジションサイズ
    reason: str                 # シグナル理由
```

## 🧪 テスト

各戦略の品質確保のため包括的テストを実装：

```bash
# 全戦略テスト実行（Phase 13・CI/CDワークフロー最適化・本番運用対応）
python -m pytest tests/unit/strategies/implementations/ -v

# 特定戦略テスト（手動実行監視対応）
python -m pytest tests/unit/strategies/implementations/test_atr_based.py -v
python -m pytest tests/unit/strategies/implementations/test_mochipoy_alert.py -v
python -m pytest tests/unit/strategies/implementations/test_multi_timeframe.py -v
python -m pytest tests/unit/strategies/implementations/test_fibonacci_retracement.py -v

# 625テスト統合基盤確認（攻撃的設定対応・Phase 19+）
python scripts/testing/dev_check.py validate --mode light
```

### テスト構成（Phase 13・CI/CDワークフロー最適化）
- **ATRBased**: 15テスト（ボラティリティ分析・エントリー判定等・本番運用対応）
- **MochiPoyAlert**: 15テスト（RCI分析・多数決システム等・手動実行監視対応）
- **MultiTimeframe**: 15テスト（時間軸統合・トレンド整合性等・段階的デプロイ対応）
- **FibonacciRetracement**: 17テスト（スイング検出・フィボレベル等・CI/CD品質ゲート対応）

## 🔍 デバッグ・トラブルシューティング（ハードコード問題解決対応）

### **詳細デバッグログ活用**

各戦略は市場分析の詳細情報をログ出力し、問題診断を支援します：

```bash
# ペーパートレードモードでデバッグログ確認
python3 main.py --mode paper

# 戦略実行ログ例
[INFO] [ATRBased] 分析開始 - データシェイプ: (100, 12), 利用可能列: ['close', 'volume', 'returns_1', ...]
[INFO] [FibonacciRetracement] スイング分析結果: スイング: 高値4525000 安値4475000 (強度0.8% トレンド上昇)
[INFO] [MochipoyAlert] EMA分析結果: 上昇 (signal: 1)
[INFO] [MultiTimeframe] 4Hトレンド分析結果: 上昇トレンド (signal: 1)
```

### **ハードコード問題解決確認**

修正後の戦略は全てthresholds.yamlから設定値を取得します：

```python
# 修正前（問題のあったコード）
confidence = 0.5  # ハードコード値

# 修正後（設定値取得）
from ...core.config.threshold_manager import get_threshold
hold_confidence = get_threshold("strategies.atr_based.hold_confidence", 0.3)
confidence = hold_confidence  # 設定値使用
```

### **フォールバック防止の確認方法**

1. **戦略分析実行確認**: ログで各分析ステップが実行されているか確認
2. **設定値反映確認**: 信頼度が設定値になっているか確認
3. **動的計算確認**: HOLDシグナル以外も生成されているか確認

### **よくある問題の診断**

**HOLDシグナルばかり生成される場合**:
```bash
# 1. 特徴量データ確認
grep "データシェイプ" logs/crypto_bot.log

# 2. 分析結果確認
grep "分析結果" logs/crypto_bot.log

# 3. 最終判定確認
grep "最終判定" logs/crypto_bot.log
```

**設定値が反映されない場合**:
```bash
# thresholds.yaml構文チェック
python3 -c "
from src.core.config.threshold_manager import get_threshold
print(f'ATR hold_confidence: {get_threshold(\"strategies.atr_based.hold_confidence\", \"ERROR\")}')
print(f'Fib no_level_confidence: {get_threshold(\"strategies.fibonacci_retracement.no_level_confidence\", \"ERROR\")}')
"
```

## ⚙️ 設定システム

### 戦略別設定例

**ATRBased設定**:
```yaml
atr_based:
  volatility_threshold: 1.2
  stop_loss_atr_multiplier: 2.0
  take_profit_ratio: 2.5
  min_confidence: 0.4
```

**MochiPoyAlert設定**:
```yaml
mochipoy_alert:
  rci_periods: [9, 26]
  rsi_overbought: 70
  rsi_oversold: 30
  decision_threshold: 2  # 多数決の最低票数
```

**MultiTimeframe設定**:
```yaml
multi_timeframe:
  primary_timeframe: "4h"
  secondary_timeframe: "15m"
  trend_consistency_threshold: 0.6
  timing_precision_weight: 0.3
```

**FibonacciRetracement設定**:
```yaml
fibonacci_retracement:
  fib_levels: [0.236, 0.382, 0.500, 0.618]
  level_tolerance: 0.01
  lookback_periods: 20
  min_confidence: 0.4
```

## 🚀 戦略マネージャー統合（Phase 13・CI/CDワークフロー最適化・手動実行監視対応）

```python
from src.strategies.base.strategy_manager import StrategyManager  # GitHub Actions統合
from src.strategies.implementations import *

# 戦略マネージャーに複数戦略登録（段階的デプロイ対応）
manager = StrategyManager()  # 手動実行監視統合
manager.register_strategy(ATRBasedStrategy(), weight=0.3)  # CI/CD品質ゲート対応
manager.register_strategy(MochiPoyAlertStrategy(), weight=0.25)
manager.register_strategy(MultiTimeframeStrategy(), weight=0.25) 
manager.register_strategy(FibonacciRetracementStrategy(), weight=0.2)

# 統合分析実行（監視統合）
combined_signal = manager.analyze_market(market_data)  # GitHub Actions統合
```

## 🧪 テスト・品質保証

### **戦略実装テスト**
```bash
# 全戦略テスト実行
python -m pytest tests/unit/strategies/implementations/ -v

# 個別戦略テスト
python -m pytest tests/unit/strategies/implementations/test_atr_based.py -v
python -m pytest tests/unit/strategies/implementations/test_fibonacci_retracement.py -v
python -m pytest tests/unit/strategies/implementations/test_mochipoy_alert.py -v
python -m pytest tests/unit/strategies/implementations/test_multi_timeframe.py -v
```

### **テスト構成**
- **ATRBased**: 15テスト（ボラティリティ分析・エントリー判定等）
- **FibonacciRetracement**: 17テスト（スイング検出・フィボレベル等）
- **MochiPoyAlert**: 15テスト（RCI分析・多数決システム等）
- **MultiTimeframe**: 15テスト（時間軸統合・トレンド整合性等）

## ⚠️ 重要事項

### **依存関係**
- src.strategies.base: 基底クラス継承
- src.strategies.utils: 共通処理機能
- src.core.config: 設定管理
- src.core.logger: ログ管理

### **制限事項**
- 各戦略は12特徴量データを前提とした設計
- 統合実行はStrategyManagerでの重み付け統合を前提
- 共通処理機能（utils）への依存関係あり

---

**取引戦略実装群**: 4つの独立した取引戦略（ATRベース・フィボナッチ・もちぽよアラート・マルチタイムフレーム）を実装。各戦略は異なる技術指標や市場観測手法により、多様な市場状況に対応した取引シグナルを生成。
# src/core/services/ - システムサービス層 🚀 Phase 52.4完了

## 🎯 役割・責任

システム全体の統合制御・市場レジーム分類・動的戦略選択・ヘルスチェック・取引サイクル実行を担当します。

**Phase 52.4完了**: コード品質改善・ハードコード値削減・設定駆動型システム確立
**Phase 51.9完了**: レジーム別ML統合最適化・市場状況に応じた動的ML統合
**Phase 51.8完了**: レジーム別ポジション制限（tight_range/normal_range/trending/high_volatility）
**Phase 51.3完了**: 動的戦略選択システム実装・市場レジーム連動戦略重み最適化
**Phase 49完了**: バックテスト完全改修統合・証拠金維持率80%遵守・TP/SL設定完全同期

## 📂 ファイル構成

```
services/
├── trading_cycle_manager.py        # 取引サイクル実行管理（1,189行・最重要ファイル）
├── market_regime_classifier.py     # 市場レジーム分類器（376行・Phase 51.2-51.9）
├── dynamic_strategy_selector.py    # 動的戦略選択器（254行・Phase 51.3-51.9）
├── trading_logger.py                # 取引ログ管理（290行）
├── health_checker.py                # システムヘルスチェック（184行）
├── system_recovery.py               # 自動復旧システム（224行）
├── graceful_shutdown_manager.py     # Gracefulシャットダウン（186行）
├── regime_types.py                  # 市場レジーム定義（93行・Phase 51.2）
└── README.md                        # このファイル
```

## 📈 Phase 52.4完了（2025年11月17日）

**🎯 Phase 52.4-B: core/services層コード品質改善**

### ✅ Phase 52.4-B最適化成果
- **Phase参照統一**: 120箇所 → 48箇所（60%削減）・Phase 52.4への統一
- **ハードコード値削減**: 40箇所のマジックナンバーをthresholds.yamlに移行
  - `market_regime`セクション追加（判定閾値・期間パラメータ）
  - `services`セクション追加（取引サイクル・システム復旧・ヘルスチェック設定）
- **設定駆動型システム確立**: `get_threshold()`パターン徹底・保守性向上
- **Docstring改善**: デフォルト値削減（DRY原則遵守）

### 📊 Phase 52.4-B重要事項
- **market_regime_classifier.py**: 全判定閾値をthresholds.yaml化（18箇所）
- **system_recovery.py**: max_recovery_attemptsをget_threshold()化
- **graceful_shutdown_manager.py**: timeoutをget_threshold()化
- **thresholds.yaml拡張**: 52行追加（市場レジーム設定・サービス層設定）

## 📈 Phase 51.3-51.9完了（2025年11月02日-04日）

**🎯 Phase 51シリーズ: レンジ型bot最適化・動的戦略選択・レジーム別ML統合**

### ✅ Phase 51.3-51.9最適化成果
- **Phase 51.2-51.3: 市場レジーム分類システム実装**
  - MarketRegimeClassifier: 4段階分類（tight_range/normal_range/trending/high_volatility）
  - DynamicStrategySelector: レジーム別戦略重み動的選択
  - BB幅・ADX・EMA傾き・ATR比による自動判定

- **Phase 51.8: レジーム別ポジション制限実装**
  - tight_range: 6件（分散投資重視）
  - normal_range: 4件（バランス型）
  - trending: 2件（集中投資）
  - high_volatility: 0件（完全待機）

- **Phase 51.9: レジーム別ML統合最適化実装**
  - 市場状況に応じた動的ML統合率調整
  - レンジ相場: 戦略重視（戦略70%・ML30%）
  - トレンド相場: ML補完重視（戦略50%・ML50%）

### 📊 Phase 51.3-51.9重要事項
- **MarketRegimeClassifier**: 優先順位判定（高ボラ→狭レンジ→トレンド→通常レンジ）
- **DynamicStrategySelector**: thresholds.yaml設定駆動・動的重み選択
- **レジーム別最適化**: ポジション制限・戦略重み・ML統合率の3軸最適化

## 📈 Phase 49完了（2025年10月22日）

**🎯 Phase 49: バックテスト完全改修・証拠金維持率80%遵守・TP/SL設定完全同期**

### ✅ Phase 49最適化成果
- **バックテスト完全改修統合**: 戦略シグナル事前計算・TP/SL決済ロジック・TradeTracker統合・matplotlib可視化
- **証拠金維持率80%遵守**: critical閾値 100.0 → 80.0変更・詳細ログ・安全優先エラーハンドリング
- **TP/SL設定完全同期**: thresholds.yaml完全準拠・ハードコード値削除・設定値確実反映

## 📈 Phase 42.3完了（2025年10月18日）

**🎯 Phase 42.3: ML統合バグ修正・特徴量警告抑制・証拠金チェックリトライ**

### ✅ Phase 42.3最適化成果
- **Phase 42.3.1: ML Agreement Logic修正**: hold + directional signal誤ボーナス解消（trading_cycle_manager.py:548）
  - 修正前: `is_agreement = (ml_action == strategy_action) or (ml_action == "hold" and strategy_action in ["buy", "sell"])`
  - 修正後: `is_agreement = ml_action == strategy_action`（strict matching）
  - 効果: ML=hold + Strategy=sell時の誤20%ボーナス削除（0.708→0.850の誤判定解消）

- **Phase 42.3.2: Feature Warning抑制**: `strategy_signal_*`特徴量警告除外（trading_cycle_manager.py:308-330）
  - 背景: Phase 41で後から追加される5戦略信号特徴量（50→55個）が警告を発生
  - 対策: `strategy_signal_*`を実際の特徴量不足から除外・DEBUGログに変更
  - 効果: 誤警告削除・ログノイズ削減

- **Phase 42.3.3: 証拠金チェックリトライ**: Error 20001（bitbank API認証エラー）3回リトライ実装・無限ループ防止
- **品質保証完了**: 1,097テスト100%成功・66.72%カバレッジ達成（Phase 49）

### 📊 Phase 42.3重要事項
- **ML統合精度向上**: hold信号が方向性信号と誤って一致判定されていた問題を解決
- **特徴量管理改善**: Phase 41の55特徴量（50基本+5戦略信号）システムとの整合性確保
- **ペーパートレード検証**: Phase 42.3.1修正によりML統合ロジックの正確性を確認

## 📈 Phase 29.5完了（2025年9月30日）

**🎯 Phase 29.5: ML予測統合実装・真のハイブリッドMLbot実現**

### ✅ Phase 29.5最適化成果
- **ML予測統合ロジック実装**: 戦略70% + ML30%の加重平均統合（trading_cycle_manager.py:340-454）
- **一致・不一致判定システム**: ML高信頼度（60%以上・Phase 41.8.5最適化）時のボーナス（1.2倍）・ペナルティ（0.7倍）適用
- **自動hold変更機能**: 不一致かつ信頼度極低（0.4未満）時の安全措置
- **設定管理統合**: thresholds.yaml ML統合設定追加・MLConfig拡張
- **品質保証完了**: 625テスト100%成功・64.74%カバレッジ達成・8個の統合テスト追加

### 📊 判明した重要事項
- **以前の問題**: ML予測は計算されていたが取引判断に未使用（ログのみ）
- **信号精度の疑問解決**: ATRBased 0.650は上限到達（agreement_max）・MultiTimeframe 0.300は不一致ベース値（正常動作）
- **トレンド判定の仕様**: MultiTimeframeは16期間（2.7日）で判定・意図的に慎重な設計
- **システム評価**: ハイブリッドアプローチはMLbotとして優秀・一般的な純粋MLより安定性高い

## 🔧 主要ファイル詳細

### **trading_cycle_manager.py** 🚀**Phase 49完了（最重要・1,033行）**

取引サイクル実行の中核システムです。データ取得→特徴量生成→戦略評価→ML予測→リスク管理→注文実行のフロー全体を担当。Phase 49でバックテスト完全改修統合・証拠金維持率80%遵守・TP/SL設定完全同期を完了しました。

**Phase 29.5新機能**:
```python
def _integrate_ml_with_strategy(self, ml_prediction: dict, strategy_signal: dict) -> dict:
    """
    Phase 29.5: ML予測と戦略シグナルの統合

    ML予測結果を戦略シグナルと統合し、最終的な取引信頼度を調整。
    一致時はボーナス、不一致時はペナルティを適用。

    Args:
        ml_prediction: ML予測結果 {"prediction": int, "confidence": float}
                      prediction: -1=売り, 0=保持, 1=買い
        strategy_signal: 戦略シグナル {"action": str, "confidence": float}
                       action: "buy", "sell", "hold"

    Returns:
        dict: 統合後のシグナル {"action": str, "confidence": float, "ml_adjusted": bool}
    """
```

**統合アルゴリズム**:
1. **ML統合有効性チェック**: `get_threshold("ml.strategy_integration.enabled")`
2. **ML信頼度確認**: min_ml_confidence（0.6）以上で統合実行
3. **加重平均計算**: 戦略70% + ML30%のベース信頼度算出
4. **高信頼度時の強化**:
   - ML信頼度 >= 0.8の場合:
     - **一致**: ボーナス1.2倍適用（両方が同じ方向を示す）
     - **不一致**: ペナルティ0.7倍適用（方向が逆）
5. **安全措置**: 信頼度 < 0.4の場合、holdに強制変更

**実行フロー**:
```
データ取得 → 特徴量生成 → 戦略評価 → ML予測
              ↓
    【Phase 29.5 ML統合ロジック】
       _integrate_ml_with_strategy()
              ↓
    統合シグナル → リスク管理 → 取引実行
```

**主要メソッド**:
- `execute_trading_cycle()`: 取引サイクル全体制御（Phase 1-8）
- `_get_ml_prediction()`: ML予測実行・15特徴量選択
- `_integrate_ml_with_strategy()`: **【Phase 29.5新規】ML統合ロジック**
- `_evaluate_risk()`: リスク管理・統合シグナル適用
- `_execute_approved_trades()`: 承認された取引実行

## 📝 使用方法・例

### **ML予測統合の動作例**

```python
from src.core.services.trading_cycle_manager import TradingCycleManager

# TradingCycleManager初期化（orchestrator経由）
cycle_manager = TradingCycleManager(orchestrator, logger)

# 取引サイクル実行（ML統合自動適用）
await cycle_manager.execute_trading_cycle()

# ログ出力例:
# [INFO] 🔄 ML統合開始: 戦略=sell(0.700), ML=hold(0.918)
# [INFO] ⚠️ ML・戦略不一致（ML高信頼度） - ペナルティ適用: 0.760 → 0.532
```

### **ML統合設定の制御**

```python
from src.core.config import get_threshold

# ML統合有効化/無効化
enabled = get_threshold("ml.strategy_integration.enabled", False)

# 重み調整
ml_weight = get_threshold("ml.strategy_integration.ml_weight", 0.3)
strategy_weight = get_threshold("ml.strategy_integration.strategy_weight", 0.7)

# ボーナス・ペナルティ調整
agreement_bonus = get_threshold("ml.strategy_integration.agreement_bonus", 1.2)
disagreement_penalty = get_threshold("ml.strategy_integration.disagreement_penalty", 0.7)
```

## ⚠️ 注意事項・制約

### **ML統合の動作条件**
- **有効化必須**: `thresholds.yaml`の`ml.strategy_integration.enabled: true`
- **最小信頼度**: ML信頼度 >= 0.6（min_ml_confidence）で統合実行
- **高信頼度閾値**: ML信頼度 >= 0.8で強化判定（ボーナス/ペナルティ）
- **安全閾値**: 統合後信頼度 < 0.4でhold強制変更

### **設定変更時の注意**
- **ml_weight変更**: 0.3（デフォルト）から±0.1程度の変更推奨
- **ボーナス/ペナルティ**: 過度な変更は取引頻度に大きく影響
- **品質チェック必須**: 設定変更後は`bash scripts/testing/checks.sh`実行

## 🔗 関連ファイル・依存関係

### **Phase 29.5新規ファイル**
- `tests/unit/core/services/test_ml_strategy_integration.py`: ML統合テスト（8個のテストケース）
- `config/core/thresholds.yaml`: ml.strategy_integration設定セクション
- `src/core/config/config_classes.py`: MLConfig.strategy_integrationフィールド

### **参照元システム**
- `src/core/orchestration/orchestrator.py`: TradingCycleManager初期化・取引サイクル実行
- `src/ml/ensemble.py`: ProductionEnsemble・ML予測結果生成
- `src/strategies/`: 5戦略システム・戦略シグナル生成
- `src/trading/risk_manager.py`: リスク管理・統合シグナル評価

---

**🎯 重要**: Phase 29.5により、本システムは真のハイブリッドMLbotとして完成しました。ML予測が実際の取引判断に統合され、戦略とMLが「溶け合った」企業級AI自動取引システムを実現しています。
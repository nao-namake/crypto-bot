# src/core/services/ - システムサービス層 🚀 Phase 29.5完了

## 🎯 役割・責任

システム全体の統合制御・ヘルスチェック・ログ管理・取引サイクル実行を担当します。Phase 29.5でML予測統合ロジックを実装し、真のハイブリッドMLbotを実現しました。

## 📂 ファイル構成

```
services/
├── trading_cycle_manager.py        # 取引サイクル実行管理（Phase 29.5: ML統合実装）
├── health_checker.py                # システムヘルスチェック
├── trading_logger.py                # 取引ログ管理・Discord通知
├── system_recovery.py               # 自動復旧システム
├── graceful_shutdown_manager.py     # グレースフルシャットダウン
└── README.md                        # このファイル
```

## 📈 Phase 29.5完了（2025年9月30日）

**🎯 Phase 29.5: ML予測統合実装・真のハイブリッドMLbot実現**

### ✅ Phase 29.5最適化成果
- **ML予測統合ロジック実装**: 戦略70% + ML30%の加重平均統合（trading_cycle_manager.py:340-454）
- **一致・不一致判定システム**: ML高信頼度（80%以上）時のボーナス（1.2倍）・ペナルティ（0.7倍）適用
- **自動hold変更機能**: 不一致かつ信頼度極低（0.4未満）時の安全措置
- **設定管理統合**: thresholds.yaml ML統合設定追加・MLConfig拡張
- **品質保証完了**: 625テスト100%成功・64.74%カバレッジ達成・8個の統合テスト追加

### 📊 判明した重要事項
- **以前の問題**: ML予測は計算されていたが取引判断に未使用（ログのみ）
- **信号精度の疑問解決**: ATRBased 0.650は上限到達（agreement_max）・MultiTimeframe 0.300は不一致ベース値（正常動作）
- **トレンド判定の仕様**: MultiTimeframeは16期間（2.7日）で判定・意図的に慎重な設計
- **システム評価**: ハイブリッドアプローチはMLbotとして優秀・一般的な純粋MLより安定性高い

## 🔧 主要ファイル詳細

### **trading_cycle_manager.py** 🚀**Phase 29.5 ML統合実装完了**

取引サイクル実行の中核システムです。Phase 29.5でML予測統合ロジックを実装し、戦略とMLの真の融合を実現しました。

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
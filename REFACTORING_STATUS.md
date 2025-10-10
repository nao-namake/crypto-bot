# trading/risk層リファクタリング進捗状況

**Phase 38: risk_manager.py分割 - 企業級コード品質実現**

## 完了状況サマリー

✅ **完了**: 2/7ファイル (29%)
⏳ **残作業**: 5/7ファイル (71%)

## ファイル別進捗

### ✅ 完了済み

#### 1. risk/kelly.py
- **ステータス**: ✅ 完成（686行）
- **場所**: `/Users/nao/Desktop/bot/src/trading/risk/kelly.py`
- **実装内容**:
  - `KellyCriterion`クラス: Kelly基準計算
  - `TradeResult`データクラス: 取引結果記録
  - `KellyCalculationResult`データクラス: Kelly計算結果
  - 設定ファイル化100%完了（ハードコード値0）
- **主要機能**:
  - Kelly公式による最適ポジション比率計算
  - 取引履歴からの動的Kelly値計算
  - ML予測信頼度を考慮した最適サイズ計算
  - ボラティリティ連動ダイナミックポジションサイジング
  - 複数レベルフォールバック機能

#### 2. risk/sizer.py
- **ステータス**: ✅ 完成（223行）
- **場所**: `/Users/nao/Desktop/bot/src/trading/risk/sizer.py`
- **実装内容**:
  - `PositionSizeIntegrator`クラス: Kelly基準とRiskManager統合
  - 設定ファイル化100%完了
- **主要機能**:
  - 統合ポジションサイズ計算（Dynamic, Kelly, RiskManagerの最小値採用）
  - ML信頼度に基づく動的ポジションサイジング
  - 信頼度カテゴリー別比率調整（低/中/高）
  - 資金規模別調整

### ⏳ 残作業

#### 3. risk/anomaly.py
- **ステータス**: ⏳ 未作成（実装コードあり）
- **元ファイル**: `src/trading/risk_monitor.py`
- **移動対象クラス**:
  - `TradingAnomalyDetector`
  - `AnomalyAlert`
  - `AnomalyLevel`
- **参照ドキュメント**: `/Users/nao/Desktop/bot/docs/refactoring/risk_layer_refactoring.md` (行200-400)

#### 4. risk/drawdown.py
- **ステータス**: ⏳ 未作成（実装コードあり）
- **元ファイル**: `src/trading/risk_monitor.py`
- **移動対象クラス**:
  - `DrawdownManager`
  - `TradingStatus`
  - `TradeRecord`
- **参照ドキュメント**: `/Users/nao/Desktop/bot/docs/refactoring/risk_layer_refactoring.md` (行400-700)

#### 5. risk/manager.py
- **ステータス**: ⏳ 未作成
- **元ファイル**: `src/trading/risk_manager.py`
- **抽出対象**:
  - `IntegratedRiskManager`クラス（メインロジック）
  - データクラスは`core/types.py`に移動検討
- **依存関係**:
  - kelly.py ✅
  - sizer.py ✅
  - anomaly.py ⏳
  - drawdown.py ⏳

#### 6. risk/__init__.py
- **ステータス**: ⏳ 未作成（テンプレートあり）
- **実装内容**: 全クラス・関数のエクスポート
- **参照ドキュメント**: `/Users/nao/Desktop/bot/docs/refactoring/risk_layer_refactoring.md` (行708-743)

#### 7. インポート更新
- **ステータス**: ⏳ 未対応
- **対象ファイル**:
  - `src/core/orchestration/trading_orchestrator.py`
  - `src/trading/execution_service.py`
  - `tests/trading/test_risk_manager.py`
  - その他依存ファイル

## 実装優先順位

### Phase 1（高優先度）
1. **risk/anomaly.py作成** - 実装コードあり、コピーベース
2. **risk/drawdown.py作成** - 実装コードあり、コピーベース

### Phase 2（中優先度）
3. **risk/manager.py作成** - IntegratedRiskManager抽出
4. **risk/__init__.py作成** - エクスポート定義

### Phase 3（低優先度）
5. **インポート更新** - 依存ファイル修正
6. **テスト更新** - テストファイル修正
7. **品質チェック** - `bash scripts/testing/checks.sh`

## 設定ファイル対応状況

### ✅ 完全対応（ハードコード値0）
- **kelly.py**: 全設定値を`thresholds.yaml`/`unified.yaml`から動的取得
- **sizer.py**: 全設定値を`thresholds.yaml`から動的取得

### ⏳ 対応予定（実装コードあり）
- **anomaly.py**: 設定ファイル対応実装済み
- **drawdown.py**: 設定ファイル対応実装済み
- **manager.py**: 既存コード確認・設定ファイル化必要

## 次のステップ

### 即座に実行可能
```bash
# 1. anomaly.pyを作成（ドキュメントからコピー）
# ドキュメント: /Users/nao/Desktop/bot/docs/refactoring/risk_layer_refactoring.md
# 行200-400をコピー → /Users/nao/Desktop/bot/src/trading/risk/anomaly.py

# 2. drawdown.pyを作成（ドキュメントからコピー）
# ドキュメント: /Users/nao/Desktop/bot/docs/refactoring/risk_layer_refactoring.md
# 行400-700をコピー → /Users/nao/Desktop/bot/src/trading/risk/drawdown.py

# 3. manager.pyを作成（元ファイルから抽出）
# 元ファイル: /Users/nao/Desktop/bot/src/trading/risk_manager.py
# IntegratedRiskManagerクラスを抽出 → /Users/nao/Desktop/bot/src/trading/risk/manager.py

# 4. __init__.pyを作成（ドキュメントからコピー）
# ドキュメント: /Users/nao/Desktop/bot/docs/refactoring/risk_layer_refactoring.md
# 行708-743をコピー → /Users/nao/Desktop/bot/src/trading/risk/__init__.py

# 5. インポート更新
# 各依存ファイルを編集

# 6. 品質チェック実行
bash scripts/testing/checks.sh
```

## ドキュメント参照

- **完全実装ガイド**: `/Users/nao/Desktop/bot/docs/refactoring/risk_layer_refactoring.md`
- **プロジェクトガイド**: `/Users/nao/Desktop/bot/CLAUDE.md`

## 品質基準（Phase 37.4完了時点）

- ✅ **テスト**: 653テスト100%成功維持
- ✅ **カバレッジ**: 58.62%以上維持
- ✅ **コード品質**: flake8・black・isort通過
- ✅ **設定ファイル化**: ハードコード値0

## 期待効果

1. **保守性向上**: 1ファイル1815行 → 5ファイル平均350行
2. **テスタビリティ向上**: 各モジュール独立テスト可能
3. **可読性向上**: 責務明確化・ナビゲーション容易
4. **拡張性向上**: 新機能追加時の影響範囲明確化

---

**作成日**: 2025/10/11
**Phase**: 38 リファクタリング開始
**前提Phase**: Phase 37.4完了（SL配置問題完全解決・コスト最適化35-45%）

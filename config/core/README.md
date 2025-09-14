# config/core/ - システム基本設定 🚀 Phase 22最適化完了

## 🎯 役割・責任

システム全体で使用する基本設定を管理します。取引所接続、機械学習、戦略、リスク管理などの核となる設定ファイル群を提供し、全システムで一貫した動作を保証します。特に**feature_order.json**は全システムの特徴量定義における単一真実源として機能します。

## 📈 Phase 22 最適化成果（2025年9月14日完了）

**🎯 目標**: 設定ファイル最適化・重複解決・システム性能向上

**✅ 実現成果**:
- **26キー重複問題解決**: unified.yaml→thresholds.yaml移行で性能最適化実現
- **unified.yaml**: 14.3KB→3.9KB（**72.7%削減**）・構造整理完了
- **thresholds.yaml**: 376行→147行・未使用120キー削除
- **システム整合性**: **620テスト100%成功**・動作確認完了
- **性能向上**: デフォルト値強制 → 最適化設定値活用で真の性能発揮

## 📂 ファイル構成

```
core/
├── unified.yaml         # 統一設定ファイル（全環境対応）
├── feature_order.json   # 15特徴量統一定義（単一真実源）
├── thresholds.yaml      # 動的閾値設定（フォールバック回避・戦略最適化）
└── README.md            # このファイル
```

## 📋 各ファイルの役割

### **unified.yaml** 🚀**Phase 22最適化完了（2025年9月14日）**
システムの基本動作を定義する統一設定ファイルです。Phase 22で**26キー重複削除・構造整理**により大幅に最適化されました。

**📊 Phase 22最適化成果**:
- **ファイルサイズ**: 14.3KB→3.9KB（**72.7%削減**）
- **重複解決**: 26キーをthresholds.yamlに移行・設定一元化実現
- **構造改善**: 日本語セクションヘッダー追加・可読性大幅向上
- **動作確認**: **620テスト100%成功**で最適化品質保証

**主要設定項目**:
- `mode`: 動作モード（paper/live/backtest）
- `exchange`: 取引所設定（bitbank信用取引専用）
- `ml`: 機械学習設定（アンサンブルモデル、信頼度閾値35%・取引機会拡大）
- `data`: データ取得設定（マルチタイムフレーム統一）
- `features`: 15特徴量管理設定（7カテゴリ分類）
- `strategies`: 5戦略統合設定（ATRBased・MochipoyAlert・MultiTimeframe・DonchianChannel・ADXTrendStrength）
- `risk`: リスク管理設定（Kelly基準・個人開発最適化）
- `execution`: 注文実行設定
- `production`: 本番運用設定（MODE=live時有効）
- `logging`: ログ設定（環境別対応）
- `monitoring`: 監視・ヘルスチェック
- `cloud_run`: GCP Cloud Run最適化
- `security`: セキュリティ設定
- `trading_constraints`: 取引制約・制限事項（個人開発）
- `ensemble/reporting/discord`: **Phase 22で整理・最適化されたセクション**

### **feature_order.json**  
**機械学習システムの特徴量定義における単一真実源**です。全システム（Generator・Manager・ML・Backtest）がこのファイルを参照し、特徴量の統一性を保証します。

**主要内容**:
- `total_features`: 特徴量総数（**15個**）
- `feature_order_version`: v2.2.0（統合システム対応）
- `feature_categories`: 7カテゴリ分類システム
  - `basic`: 基本価格・出来高情報（**2個**）- close, volume
  - `momentum`: モメンタム指標（**2個**）- rsi_14, macd
  - `volatility`: ボラティリティ指標（**2個**）- atr_14, bb_position
  - `trend`: トレンド指標（**2個**）- ema_20, ema_50
  - `volume`: 出来高指標（**1個**）- volume_ratio
  - `breakout`: ブレイクアウト指標（**3個**）- donchian_high_20, donchian_low_20, channel_position
  - `regime`: 市場レジーム指標（**3個**）- adx_14, plus_di_14, minus_di_14
- `feature_definitions`: 各特徴量の詳細定義（型・範囲・重要度）
- `reduction_history`: 特徴量最適化履歴（97→12→15個）

### **thresholds.yaml** 🚀**Phase 22最適化完了（2025年9月14日）**
**戦略フォールバック問題を解決する動的閾値設定システム**です。Phase 22で**26キー重複問題を完全解決**し、システム性能を大幅向上させました。

**📊 Phase 22最適化成果**:
- **重複解決**: unified.yaml内26キーをthresholds.yamlに移行・デフォルト値強制問題を完全解決
- **ファイル最適化**: 376行→147行（**60.9%削減**）・未使用120キー削除
- **性能改善**: 設定値が常にデフォルト値だった問題を解決・真の性能最適化実現
- **構造整理**: セクション分類による可読性向上・管理効率化

**主要内容**:
- `strategies`: 戦略別最適化パラメータ
  - `atr_based`: BB閾値70%/30%・RSI閾値65/35・最小信頼度0.3（取引機会拡大）・**base_confidence/confidence_multiplier追加**
  - `donchian_channel`: 中央域40-60%・弱シグナル範囲・動的HOLD信頼度
  - `adx_trend`: 弱トレンド15・DI差分1.0・レンジ相場対応
- `ml`: 動的信頼度基準・フォールバック値・**model_paths設定統合**
- `trading`: 信頼度階層設定・リスク閾値・**stats_log_interval・initial_balance統合**
- `ensemble/models`: アンサンブル設定・個別モデルパラメータ（**26キー移行分含む**）
- `reporting/risk`: レポート設定・リスク管理パラメータ

**効果**: フォールバック値0.200 → 市場適応型0.25-0.6・**デフォルト値強制回避によるシステム真価発揮**

**主要設定項目**:
- `confidence_levels`: 信頼度レベル別閾値
- `ml.dynamic_confidence`: 動的信頼度設定（統合システム対応）
- `strategies`: 5戦略各種設定値・重み・閾値
- `features`: 15特徴量管理設定
- `trading`: 取引関連設定
- `execution`: 実行制御設定
- 8個のヘルパー関数用設定値

## 📝 使用方法・例

### **基本設定の読み込み**
```python
from src.core.config import load_config, get_threshold, get_ml_config, get_trading_config

# unified.yaml設定読み込み
config = load_config('config/core/unified.yaml')

# 基本設定値取得
mode = config.mode  # paper/live/backtest
confidence = config.ml.confidence_threshold  # 0.65
leverage = config.exchange.leverage  # 1.0
strategies = config.strategies.enabled  # 5戦略リスト
```

### **特徴量管理（15特徴量統一システム）**
```python
from src.core.config.feature_manager import FeatureManager

# 特徴量管理システム初期化
fm = FeatureManager()

# 特徴量情報取得
feature_names = fm.get_feature_names()          # 15特徴量名一覧
feature_count = fm.get_feature_count()          # 15
categories = fm.get_feature_categories()        # 7カテゴリ分類

# カテゴリ別取得
basic_features = fm.get_category_features('basic')      # ['close', 'volume']
breakout_features = fm.get_category_features('breakout') # ['donchian_high_20', 'donchian_low_20', 'channel_position']

# 整合性検証
features_valid = fm.validate_features(some_features)  # True/False
```

### **動的設定値取得**
```python
from src.core.config import (
    get_threshold, get_ml_config, get_trading_config, 
    get_monitoring_config, get_position_config, 
    get_backtest_config, get_data_config, get_execution_config
)

# 各種設定値取得
confidence_threshold = get_ml_config('confidence_threshold', 0.65)
initial_balance = get_trading_config('default_balance_jpy', 10000.0)
discord_timeout = get_monitoring_config('discord.timeout_seconds', 30)
hold_confidence = get_threshold("strategies.atr_based.hold_confidence", 0.3)
```

## ⚠️ 注意事項・制約

### **設定ファイル編集時の注意** 🚨**Phase 22最適化後**
- **unified.yaml**: **Phase 22で72.7%最適化完了**・デフォルト`mode: paper`（安全）・信頼度35%設定維持
- **feature_order.json**: **変更厳禁**。全システムの単一真実源のため、変更時は全システムへの影響を考慮
- **thresholds.yaml**: **Phase 22で重複26キー統合完了**・閾値変更は取引頻度・リスクに大きく影響・**デフォルト値強制問題解決済み**

### **特徴量管理の重要原則**
- **単一真実源**: `feature_order.json`が全システムの特徴量定義の唯一の基準
- **15特徴量統一**: 全システム（Generator・Manager・ML・Backtest・Production）で15特徴量統一
- **順序厳守**: 特徴量順序変更は予測性能に重大な影響・MLモデル再学習必要
- **カテゴリ整合性**: 7カテゴリ分類システムの構造維持

### **設定整合性の重要性**
- **環境間統一**: core/とbacktest/間での特徴量・戦略設定の完全統一・**信頼度35%統一設定**
- **バージョン同期**: feature_order_version統一による互換性保証
- **閾値統合**: thresholds.yaml一元管理による設定値の整合性確保・**月100-200回取引対応設定**

## 🔗 関連ファイル・依存関係

### **設定管理システム連携**
- `src/core/config.py`: 設定読み込みシステム
- `src/core/config/feature_manager.py`: 15特徴量統一管理システム
- `src/core/config/threshold_manager.py`: 閾値管理システム

### **参照元システム**
- `src/core/orchestration/orchestrator.py`: システム統合制御
- `src/features/feature_generator.py`: 15特徴量生成（単一真実源参照）
- `src/strategies/`: 5戦略システム（base/implementations/）
- `src/ml/ensemble.py`: ProductionEnsemble（15特徴量対応）
- `main.py`: エントリーポイント

### **環境別設定連携**
- `config/backtest/feature_order.json`: バックテスト用（**完全同期必須**）
- `config/backtest/base.yaml`: バックテスト設定（本番一致設定）
- `models/production/`: MLモデル（15特徴量対応）

---

**🎯 重要**: このフォルダの設定、特に`feature_order.json`は全システムの基盤となる単一真実源です。変更時は全システムへの影響を十分に検討し、特に本番環境との整合性を最優先に保ってください。
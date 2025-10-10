# config/core/ - システム基本設定 🚀 Phase 33完了（Phase 31.1-33統合）

## 🎯 役割・責任

システム全体で使用する基本設定を管理します。取引所接続、機械学習、戦略、リスク管理などの核となる設定ファイル群を提供し、全システムで一貫した動作を保証します。特に**feature_order.json**は全システムの特徴量定義における単一真実源、**features.yaml**は機能トグル管理の中心として機能します。

## 📈 Phase 33完了（2025年10月3日）

**🎯 Phase 33: 手数料最適化・TP/SL堅牢化・デイトレード対応**

**✅ Phase 33完了**:
- **スマート注文機能有効化**: smart_order_enabled: false → true・手数料削減14-28%（月100-200回対応）
- **約定確率向上**: price_improvement_ratio: 0.001 → 0.0002（0.1% → 0.02%）・現在値に近い指値で大幅改善
- **デイトレード最適化**: timeout_minutes: 30 → 5・5分後に未約定指値を成行変換・機会損失防止
- **手数料最適化効果**: 高信頼度時は指値（Maker -0.02%）・低信頼度時は成行（Taker 0.12%）自動切替
- **品質保証**: 647テスト100%成功・59.85%カバレッジ達成・CI/CD統合

## 📈 Phase 32完了（2025年10月2日）

**🎯 Phase 32: 5戦略SignalBuilder統一・15m ATR優先実装・SL/TP機能完全化**

**✅ Phase 32完了**:
- **5戦略SignalBuilder統一**: DonchianChannel・ADXTrend統合完了・全5戦略でSignalBuilder使用
- **15m ATR優先実装**: 全戦略で15m足ATR使用統一・SL距離2%改善実現
- **SL/TP機能完全化**: Phase 31で3戦略統合済み・Phase 32で残り2戦略統合・全戦略で一貫したリスク管理
- **品質保証**: 646テスト100%成功（1 skipped）・59.75%カバレッジ達成・CI/CD統合

## 📈 Phase 31.1完了（2025年10月2日）

**🎯 Phase 31.1: 機能トグル管理・柔軟クールダウン・設定管理3層化**

**✅ Phase 31.1完了**:
- **features.yaml作成**: 7カテゴリー・~50機能トグル・機能視認性向上・設定一元化実現
- **柔軟クールダウン実装**: トレンド強度ベース（ADX 50%・DI 30%・EMA 20%）・強度>=0.7でスキップ
- **機会損失削減**: 強トレンド時のクールダウンスキップにより取引機会確保・通常時は30分維持
- **設定管理3層化**: features.yaml（機能トグル）+ unified.yaml（基本設定）+ thresholds.yaml（動的値）

## 📈 Phase 30完了（2025年10月1日）

**🎯 Phase 29.6: 本番環境問題修正 + Phase 30: SL最適化・マルチタイムフレーム対応**

**✅ Phase 29.6完了**:
- **TP/SL注文配置機能**: エントリー後自動配置・指値注文使用
- **指値注文切替**: default_order_type: limit（手数料最適化）
- **クールダウン機能**: cooldown_minutes: 30（過剰取引防止）
- **ポジション追跡修正**: ライブモード最大3ポジション制限正常動作

**✅ Phase 30完了**:
- **適応型ATR倍率**: ボラティリティ連動ATR倍率（低2.5x・通常2.0x・高1.5x）
- **15m足ATR使用**: エントリー時間軸に適したSL距離計算
- **最小SL距離保証**: 1%最小距離・少額資金対応
- **指値タイムアウト枠組み**: pending_limit_orders追跡（将来実装準備）

## 📈 Phase 29.5完了（2025年9月30日）

**🎯 Phase 29.5: ML予測統合実装・真のハイブリッドMLbot実現**

**✅ Phase 29.5最適化成果**:
- **ML予測統合ロジック実装**: trading_cycle_manager.pyにML統合機能追加・戦略70% + ML30%加重平均
- **設定管理統合**: thresholds.yaml ml.strategy_integration設定追加・MLConfig拡張
- **品質保証完了**: 625テスト100%成功・64.74%カバレッジ達成・8個の統合テスト追加
- **MLbot完成**: ML予測が実際の取引判断に統合・戦略とMLの真の融合実現

## 📈 Phase 29最適化完了（2025年9月28日）

**🎯 Phase 29: 設定重複完全解消・視覚的改善・理解しやすい構造化**

**✅ Phase 29最適化成果**:
- **設定重複完全解消**: 初期残高・ML信頼度・Kelly基準・リスク闾値重複削除
- **統一設定管理体系完成**: unified.yaml（基本設定）・thresholds.yaml（動的闾値）の完全分離
- **視覚的改善**: 日本語セクションヘッダー・コメント充実・理解しやすい構造
- **アンサンブル重み統一**: model_weightsとensemble.weightsの一元化・混乱解消
- **feature_order.json v2.3.0**: Phase 29最適化対応・設定統一化履歴追加

**✅ 前回Phase 22成果維持**:
- **統一設定管理体系確立**: cloudbuild.yaml削除・gcp_config.yaml実環境同期・CI/CD統一
- **Secret Manager最適化**: :latest→具体的バージョン（:3,:5）・セキュリティ向上
- **Kelly基準最適化**: min_trades 20→5・初期position_size 0.0002 BTC・実用性大幅向上
- **システム整合性**: **625テスト100%成功**・CI/CD統一動作確認完了
- **性能向上**: デフォルト値強制 → 最適化設定値活用で真の性能発揮

## 📂 ファイル構成

```
core/
├── features.yaml        # 機能トグル設定（Phase 31.1新規追加・7カテゴリー~50機能）
├── unified.yaml         # 統一設定ファイル（全環境対応）
├── feature_order.json   # 15特徴量統一定義（単一真実源）
├── thresholds.yaml      # 動的閾値設定（フォールバック回避・戦略最適化）
└── README.md            # このファイル
```

## 📋 各ファイルの役割

### **features.yaml** 🆕**Phase 31.1新規追加（2025年10月2日）**
システムの機能トグル管理を提供する設定ファイルです。全機能の有効/無効を一元管理し、運用状況に応じた柔軟な機能制御を実現します。

**📊 Phase 31.1機能トグル管理**:
- **7カテゴリー構成**: trading・risk_management・ml_integration・strategies・data・monitoring・infrastructure
- **~50機能トグル**: 全システム機能の視認性向上・設定一元化実現
- **柔軟な運用制御**: 状況に応じた機能有効化/無効化・設定漏れ防止
- **機能分離**: unified.yaml（基本設定）とfeatures.yaml（機能トグル）の明確な分離

**主要設定カテゴリー**:
- `trading`: 取引実行機能（実取引・ペーパートレード・柔軟クールダウン・指値注文等）
- `risk_management`: リスク管理機能（ストップロス・テイクプロフィット・適応型ATR・Kelly基準等）
- `ml_integration`: ML統合機能（戦略ML統合・信頼度連動制御・オンライン学習等）
- `strategies`: 戦略機能（5戦略個別有効化・Multi-timeframe・MochiPoy・ATR・Donchian・ADX）
- `data`: データ取得機能（Bitbank API・キャッシュ・Multi-timeframe・ストリーミング等）
- `monitoring`: 監視機能（Discord通知・ヘルスチェック・データ品質監視等）
- `infrastructure`: インフラ機能（GracefulShutdown・システム復旧・ドローダウン永続化等）

**Phase 31.1新機能**:
- `trading.flexible_cooldown`: トレンド強度ベースの柔軟クールダウン（強度>=0.7でスキップ）
  - ADX 50%重み・DI差分 30%重み・EMA関係 20%重み
  - 強トレンド時の機会損失削減・通常時30分維持

### **unified.yaml** 🚀**Phase 29最適化完了（2025年9月28日）**
システムの基本動作を定義する統一設定ファイルです。Phase 29で**設定重複完全解消・アンサンブル重み統一**を実現しました。

**📊 Phase 23新機能: モード別初期残高一元管理**:
- **mode_balances設定追加**: paper/live/backtest各モードの初期残高を一箇所で管理
- **将来の残高変更対応**: 10万円・50万円への変更もunified.yaml 1箇所修正で完結
- **設定不整合解消**: 各ファイルのハードコード残高を完全排除
- **モード別分離**: 状態ファイルをsrc/core/state/{mode}/に分離・本番環境への影響防止

**📊 統一設定管理体系 + Phase 22最適化成果**:
- **CI/CD統合**: GitHub Actions統一・cloudbuild.yaml削除・設定不整合完全解消
- **ファイルサイズ**: 14.3KB→3.9KB（**72.7%削減**）
- **重複解決**: 26キーをthresholds.yamlに移行・設定一元化実現
- **構造改善**: 日本語セクションヘッダー追加・可読性大幅向上
- **動作確認**: **638テスト100%成功**で統一設定管理品質保証

**主要設定項目**:
- `mode`: 動作モード（paper/live/backtest）
- `mode_balances`: **【Phase 23新規】モード別初期残高設定（一元管理）**
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
- `trading_constraints`: 取引制約・制限事項（**Phase 29.6**: default_order_type: limit・cooldown_minutes: 30）
- `discord`: **Discord通知設定（最適化強化版・通知負荷軽減対応）** 🆕
- `ensemble/reporting`: **Phase 22で整理・最適化されたセクション**

**Phase 29.6変更点**:
- `trading_constraints.default_order_type`: market → limit（手数料削減: 0.12% → -0.02%）
- `position_management.cooldown_minutes`: 30分間隔強制（過剰取引防止）

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

### **thresholds.yaml** 🚀**Phase 33 手数料最適化完了（2025年10月3日）**
**戦略ハードコード値完全排除・ML予測統合設定・手数料最適化設定・設定一元化システム**です。Phase 33で**スマート注文機能有効化・約定確率最適化・デイトレード対応**を実現し、Phase 29.5のML予測統合設定と合わせて完全な設定管理体系を確立しました。

**📊 Phase 33 手数料最適化設定追加**:
- **スマート注文機能**: smart_order_enabled: false → true（line 417）・高信頼度（≥75%）時は指値、低信頼度（<40%）時は成行
- **価格改善比率**: price_improvement_ratio: 0.001 → 0.0002（line 421）・0.02%価格改善で約定確率大幅向上
- **タイムアウト時間**: timeout_minutes: 30 → 5（line 426）・5分後に未約定指値を成行変換
- **手数料削減効果**: 0.14% × 月100-200回 = **月14-28%のコスト削減**
- **bitbank手数料**: Maker -0.02%（受取）、Taker 0.12%（支払）

**📊 Phase 29.5 ML予測統合設定追加**:
- **ML統合設定セクション新設**: `ml.strategy_integration.*` (7項目) で加重平均・ボーナス・ペナルティ制御
- **動的制御設定**: enabled（有効化）・ml_weight（0.3）・strategy_weight（0.7）・運用中調整対応
- **強化判定設定**: high_confidence_threshold（0.8）・agreement_bonus（1.2倍）・disagreement_penalty（0.7倍）
- **安全措置設定**: min_ml_confidence（0.6）最小信頼度閾値・低品質ML予測排除

**📊 Phase 29戦略設定値一元化成果**:
- **戦略ハードコード完全排除**: Multi-timeframe・ATRBased戦略の数値リテラル（0.002, 0.005, 0.015, 0.7, 0.5, 30.0等）を全てthresholds.yaml参照に変更
- **循環インポート問題解決**: get_threshold遅延インポート実装による安全な設定参照システム確立
- **戦略固有設定追加**: `dynamic_confidence.strategies.multi_timeframe.*` (6項目) / `dynamic_confidence.strategies.atr_based.*` (5項目) セクション新設
- **品質保証完了**: **639テスト100%成功・59.71%カバレッジ維持**でハードコード排除品質確保
- **コード品質向上**: flake8・black・isort全チェック通過による企業級品質実現

**📊 Phase 25最適化成果**:
- **動的ポジションサイジング追加**: ML信頼度連動の3段階サイジング（低:1-3%・中:3-5%・高:5-10%）
- **ポジション制限追加**: 最大3ポジション・1日20取引・30%資本使用制限で無制限取引問題完全解決
- **緊急ストップロス追加**: 3%価格変動・5%含み損で30分クールダウン回避の強制決済機能
- **資金規模別調整**: 1-5万円（テスト）・5-10万円（準本番）・10万円以上（本番）対応

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
- **【Phase 29新規追加】`dynamic_confidence.strategies`**: 戦略固有ハードコード値完全排除
  - `multi_timeframe`: tf_4h_min_strength(0.002)・tf_4h_weight(0.6)・tf_15m_weight(0.4)・position_size_base(0.025)・atr_ratio_threshold(0.005)・price_breakout_ratio(0.995)
  - `atr_based`: position_size_base(0.015)・market_stress_threshold(0.7)・min_atr_ratio(0.5)・strength_normalize(30.0)・rsi_base(0.2)
- `ml`: 動的信頼度基準・フォールバック値・**model_paths設定統合**
- `trading`: 信頼度階層設定・リスク閾値・**Kelly基準Silent Failure修正完了（2025/09/19）**
  - `kelly_min_trades`: 5（20→5に緩和・取引開始促進・実用性大幅向上）
  - `initial_position_size`: 0.0001 BTC（**Silent Failure修正・確実実行保証**）
  - `min_trade_size`: 0.0001 BTC（**Bitbank最小取引単位・Silent Failure根本修正**）
  - `fallback_btc_jpy`: 16000000.0（価格フォールバック・1BTC=1700万円対応）
- **【Phase 25新規】`position_management`**: ポジション制限・動的サイジング設定
  - `min_account_balance`: 10000（最小運用資金要件・1万円テスト対応）
  - `max_open_positions`: 3（同時保有ポジション数上限）
  - `max_daily_trades`: 20（1日の最大取引回数）
  - `dynamic_position_sizing`: ML信頼度連動の3段階サイジング設定
  - `account_size_adjustments`: 資金規模別調整（小・中・大口座対応）
  - `emergency_stop_loss`: 緊急時ストップロス設定（価格変動・含み損監視）
- `ensemble/models`: アンサンブル設定・個別モデルパラメータ（**26キー移行分含む**）
- `reporting/risk`: レポート設定・リスク管理パラメータ

**効果**: フォールバック値0.200 → 市場適応型0.25-0.6・**デフォルト値強制回避によるシステム真価発揮** + **無制限取引問題完全解決**

**主要設定項目**:
- `confidence_levels`: 信頼度レベル別閾値
- `ml.dynamic_confidence`: 動的信頼度設定（統合システム対応）
- `strategies`: 5戦略各種設定値・重み・閾値
- `features`: 15特徴量管理設定
- `trading`: 取引関連設定
- `execution`: 実行制御設定
- 8個のヘルパー関数用設定値

## 🗺️ 設定値の参照先一覧

このセクションでは、主要な設定項目がどのファイルに存在するかを明示します。設定変更時の参照ガイドとして活用してください。

### **機能トグル系（features.yaml）**
| 設定項目 | 説明 | 参照パス |
|---------|------|---------|
| 取引機能全体 | 取引実行のマスタースイッチ | `trading.enabled` |
| TP/SL自動配置 | テイクプロフィット・ストップロス機能 | `trading.stop_loss.enabled`, `trading.take_profit.enabled` |
| クールダウン機能 | 取引後のクールダウン（機能トグルのみ） | `trading.cooldown.enabled`, `trading.cooldown.flexible_mode` |
| ML予測統合 | ML予測と戦略の統合機能 | `ml_integration.enabled` |
| アンサンブルモデル | 3モデルアンサンブル機能 | `ml_integration.ensemble.enabled` |
| ドローダウン管理 | ドローダウン状態追跡・緊急停止 | `risk_management.drawdown_management.enabled` |
| Discord通知 | 各レベルの通知有効化 | `monitoring.discord.enabled`, `critical`, `warning`, `info` |

**注意**: features.yamlは機能の有効/無効のみを管理します。具体的な数値設定（時間・閾値・重み等）は以下のファイルを参照してください。

### **数値設定系（thresholds.yaml）**
| 設定項目 | 説明 | 参照パス |
|---------|------|---------|
| クールダウン時間 | 取引後の待機時間（分） | `position_management.cooldown_minutes` |
| ML統合重み | ML予測と戦略の重み配分 | `ml.strategy_integration.ml_weight`, `strategy_weight` |
| ML統合ボーナス・ペナルティ | 一致/不一致時の信頼度調整 | `ml.strategy_integration.agreement_bonus`, `disagreement_penalty` |
| ML信頼度閾値 | ML予測の信頼度判定閾値 | `ml.strategy_integration.high_confidence_threshold`, `min_ml_confidence` |
| 戦略別信頼度閾値 | 各戦略の動的信頼度設定 | `strategies.{strategy_name}.*` |
| スマート注文設定 | 指値/成行自動切替設定 | `execution.smart_order_enabled`, `price_improvement_ratio`, `timeout_minutes` |
| Kelly基準設定 | ポジションサイジング設定 | `trading.kelly_min_trades`, `initial_position_size` |
| ポジション制限 | 同時保有・日次取引上限 | `position_management.max_open_positions`, `max_daily_trades` |
| 動的サイジング閾値 | ML信頼度別のサイジング比率 | `position_management.dynamic_position_sizing.*` |
| 緊急ストップロス | 急激な価格変動時の強制決済 | `position_management.emergency_stop_loss.*` |

### **基本構造設定系（unified.yaml）**
| 設定項目 | 説明 | 参照パス |
|---------|------|---------|
| 動作モード | paper/live/backtest | `mode` |
| モード別初期残高 | 各モードの初期資金 | `mode_balances.paper`, `live`, `backtest` |
| 取引所設定 | bitbank信用取引設定 | `exchange.name`, `market_type`, `leverage` |
| アンサンブルモデル重み | LightGBM・XGBoost・RandomForest配分 | `ensemble.weights.lightgbm`, `xgboost`, `random_forest` |
| 戦略重み | 5戦略の重み配分 | `strategies.weights.{strategy_name}` |
| データ取得設定 | タイムフレーム・取得期間 | `data.default_timeframe`, `since_hours` |
| Cloud Run設定 | メモリ・CPU・タイムアウト | `cloud_run.memory`, `cpu`, `timeout` |

### **特徴量定義（feature_order.json）**
| 設定項目 | 説明 | 参照パス |
|---------|------|---------|
| 特徴量総数 | システム全体の特徴量数 | `total_features` (15個) |
| 特徴量順序 | ML予測に使用する特徴量の順序 | `feature_names` (配列) |
| カテゴリ分類 | 7カテゴリ分類システム | `feature_categories.*` |
| 特徴量定義 | 各特徴量の詳細仕様 | `feature_definitions.{feature_name}` |

**⚠️ 重要**: このファイルは全システムの単一真実源です。変更時はMLモデル再学習が必要です。

### **設定ファイル選択ガイド**
新しい設定を追加する際の判断基準：

1. **features.yaml**: 機能のON/OFFを制御したい場合
   - 例: 新機能の有効化フラグ、機能切り替え

2. **thresholds.yaml**: 数値による挙動調整が必要な場合
   - 例: 信頼度閾値、時間設定、比率設定、制限値

3. **unified.yaml**: システムの基本構造に関わる場合
   - 例: モード設定、取引所設定、重み配分、インフラ設定

4. **feature_order.json**: 特徴量定義を変更する場合（原則変更禁止）
   - 例: 特徴量追加・削除（全システム影響大・ML再学習必須）

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

# 🆕 Discord通知最適化設定取得
batch_enabled = get_monitoring_config('discord.batch_notifications', False)
batch_interval = get_monitoring_config('discord.batch_interval_minutes', 60)
rate_limit_max = get_monitoring_config('discord.rate_limit.max_per_hour', 12)
notification_level = get_monitoring_config('discord.notification_levels.warning', 'batch')
```

### **🆕 Discord通知最適化設定の活用**
```python
from src.core.reporting.discord_notifier import EnhancedDiscordManager

# バッチ処理対応Discord管理システム（推奨）
manager = EnhancedDiscordManager()

# 設定に基づく自動通知制御
# - critical: 即時送信
# - warning: 1時間バッチ集約
# - info: 日次サマリー
manager.send_simple_message("重要な残高異常", "critical")  # → 即時送信
manager.send_simple_message("API制限警告", "warning")     # → バッチ集約
manager.send_simple_message("取引完了", "info")          # → 日次サマリー

# 定期的なバッチ処理実行
manager.process_pending_notifications()
```

## ⚠️ 注意事項・制約

### **設定ファイル編集時の注意** 🚨**Phase 22最適化後**
- **unified.yaml**: **Phase 22で72.7%最適化完了** + **Discord通知最適化強化版**・デフォルト`mode: paper`（安全）・信頼度35%設定維持・バッチ処理対応
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
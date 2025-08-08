# crypto_bot/ - 暗号通貨自動取引システム

## 📋 概要

**Cryptocurrency Automated Trading System**  
crypto_bot は、機械学習を活用した暗号通貨自動取引システムです。97特徴量完全実装システムによる高精度予測、マルチタイムフレーム分析、リスク管理を統合した包括的な取引ソリューションを提供します。

## 🎯 システムアーキテクチャ

```
crypto_bot/
├── api/                    # APIサーバー・ヘルスチェック
├── backtest/               # バックテストエンジン
├── cli/                    # CLIコマンド実装
├── data/                   # データ取得・前処理（Phase 16.3-C分割対応）
├── execution/              # 取引実行・取引所統合
├── ml/                     # 機械学習パイプライン
├── strategy/               # 取引戦略実装
├── risk/                   # リスク管理
├── monitoring/             # システム監視・品質管理
├── utils/                  # ユーティリティ関数（Phase 16.5拡張）
├── visualization/          # 可視化・ダッシュボード（Phase 16.5-E新規）
├── indicator/              # テクニカル指標計算
├── drift_detection/        # ドリフト検出
├── online_learning/        # オンライン学習
├── validation/             # A/Bテスト・検証
├── analysis/               # 市場分析
├── analytics/              # 分析レポート
├── feedback/               # フィードバックループ
├── ha/                     # 高可用性
├── scripts/                # 分析スクリプト
└── trading/                # 取引機能（未実装）
```

## 📁 詳細ディレクトリ構造

```
crypto_bot/
├── __init__.py             # パッケージ初期化
├── main.py                 # メインエントリーポイント（Phase 14: ~130行）
├── README.md               # 本ドキュメント（フォルダガイド）
│
│ 🚀 Phase 16.5完了: crypto_bot直下クリーンアップ達成
│ ├── config.py         → utils/config.py (7個CLI依存)
│ ├── api.py            → api/legacy.py (フォールバック用)
│ ├── monitor.py        → visualization/dashboard.py (631行)
│ ├── init_enhanced.py  → utils/init_enhanced.py (866行)
│ └── 削除候補: main_backup_20250806.py（開発アーカイブ）
│
├── api/                    # APIサーバー・ヘルスチェック
│   ├── __init__.py
│   ├── health.py           # ヘルスチェックエンドポイント
│   └── server.py           # APIサーバー管理
│
├── backtest/               # バックテストエンジン
│   ├── __init__.py
│   ├── engine.py           # バックテストエンジン本体
│   ├── jpy_enhanced_engine.py # JPY建て特化版
│   ├── metrics.py          # 評価指標計算
│   ├── analysis.py         # 結果分析
│   └── optimizer.py        # パラメータ最適化
│
├── cli/                    # CLIコマンド実装（Phase 14.2）
│   ├── __init__.py
│   ├── backtest.py         # バックテストコマンド
│   ├── live.py             # ライブ取引コマンド
│   ├── model.py            # モデル管理コマンド
│   ├── online.py           # オンライン学習コマンド
│   ├── optimize.py         # 最適化コマンド
│   ├── stats.py            # 統計コマンド
│   ├── strategy.py         # 戦略管理コマンド
│   ├── train.py            # 訓練コマンド
│   └── validate.py         # 検証コマンド
│
├── data/                   # データ取得・処理（Phase 16.3-C分割対応）
│   ├── __init__.py
│   ├── fetcher.py          # 統合エクスポート（互換性レイヤー）
│   ├── fetching/           # Phase 16.3-C: fetcher.py分割システム
│   │   ├── __init__.py     # 分割モジュール統合
│   │   ├── market_client.py    # MarketDataFetcher（588行）
│   │   ├── data_processor.py   # DataProcessor/DataPreprocessor（444行）
│   │   └── oi_fetcher.py       # OIDataFetcher（424行）
│   ├── multi_timeframe_fetcher.py # マルチタイムフレーム
│   ├── timeframe_synchronizer.py  # タイムフレーム同期
│   ├── global_cache_manager.py    # キャッシュ管理
│   ├── scheduled_data_fetcher.py  # スケジュール取得
│   └── streamer.py         # リアルタイムストリーミング
│
├── drift_detection/        # ドリフト検出
│   ├── __init__.py
│   ├── detectors.py        # 検出アルゴリズム
│   ├── ensemble.py         # アンサンブル検出
│   └── monitor.py          # ドリフト監視
│
├── execution/              # 取引実行
│   ├── __init__.py
│   ├── base.py             # 基底インターフェース
│   ├── engine.py           # 実行エンジン
│   ├── factory.py          # ファクトリー
│   ├── api_version_manager.py     # APIバージョン管理
│   ├── bitbank_client.py          # Bitbankクライアント
│   ├── bitbank_api_rate_limiter.py # レート制限
│   ├── bitbank_order_manager.py   # 注文管理
│   ├── bitbank_fee_optimizer.py   # 手数料最適化
│   ├── bitbank_fee_guard.py       # 手数料保護
│   ├── bitbank_execution_efficiency_optimizer.py # 効率化
│   ├── bitflyer_client.py         # Bitflyerクライアント
│   ├── bybit_client.py            # Bybitクライアント
│   └── okcoinjp_client.py         # OKCoinJPクライアント
│
├── ml/                     # 機械学習
│   ├── __init__.py
│   ├── preprocessor.py     # 前処理パイプライン
│   ├── model.py            # MLモデルラッパー
│   ├── ensemble.py         # アンサンブル学習
│   ├── optimizer.py        # ハイパーパラメータ最適化
│   ├── target.py           # ターゲット生成
│   ├── feature_master_implementation.py # 97特徴量実装
│   ├── feature_order_manager.py        # 特徴量順序管理
│   ├── feature_defaults.py             # デフォルト値
│   ├── feature_engineering_enhanced.py # 拡張特徴量
│   ├── data_quality_manager.py         # データ品質
│   ├── dynamic_weight_adjuster.py      # 動的重み調整
│   ├── bayesian_strategy.py            # ベイズ最適化
│   ├── cross_timeframe_ensemble.py     # クロスタイムフレーム
│   ├── timeframe_ensemble.py           # タイムフレームアンサンブル
│   ├── feature_order_97_unified.json   # 97特徴量定義
│   ├── feature_order_manager.py.backup # バックアップ
│   └── feature_engines/    # 特徴量エンジン
│       ├── __init__.py
│       ├── batch_calculator.py # バッチ計算
│       └── technical_engine.py # テクニカル指標
│
├── monitoring/             # 監視システム
│   ├── data_quality_monitor.py    # データ品質監視
│   └── performance_monitor.py     # パフォーマンス監視
│
├── online_learning/        # オンライン学習
│   ├── __init__.py
│   ├── base.py             # 基底クラス
│   ├── models.py           # オンライン学習モデル
│   ├── monitoring.py       # 学習監視
│   └── scheduler.py        # スケジューラー
│
├── risk/                   # リスク管理
│   ├── __init__.py
│   ├── manager.py          # 基本リスク管理
│   └── aggressive_manager.py # 積極的リスク管理
│
├── scripts/                # ユーティリティスクリプト
│   ├── __init__.py
│   ├── plot_equity.py      # エクイティカーブ描画
│   └── walk_forward.py     # ウォークフォワード分析
│
├── strategy/               # 取引戦略（多数のファイル）
│   ├── __init__.py
│   ├── base.py             # 抽象基底クラス
│   ├── factory.py          # 戦略ファクトリー
│   ├── registry.py         # 戦略レジストリ
│   ├── simple_ma.py        # 移動平均戦略
│   ├── ml_strategy.py      # ML戦略
│   ├── aggressive_ml_strategy.py       # 積極的ML戦略
│   ├── ensemble_ml_strategy.py         # アンサンブルML戦略
│   ├── multi_timeframe_ensemble.py     # マルチタイムフレーム基盤
│   ├── multi_timeframe_ensemble_strategy.py # マルチタイムフレーム戦略
│   ├── composite.py        # 複合戦略
│   ├── bitbank_btc_jpy_strategy.py     # Bitbank BTC/JPY
│   ├── bitbank_xrp_jpy_strategy.py     # Bitbank XRP/JPY
│   ├── bitbank_day_trading_strategy.py # Bitbank日中取引
│   ├── bitbank_integrated_strategy.py  # Bitbank統合戦略
│   ├── bitbank_integrated_day_trading_system.py # Bitbank統合システム
│   ├── bitbank_taker_avoidance_strategy.py      # テイカー回避
│   ├── bitbank_enhanced_position_manager.py     # ポジション管理
│   └── bitbank_execution_orchestrator.py        # 実行オーケストレータ
│
├── utils/                  # ユーティリティ（多数のファイル）
│   ├── __init__.py
│   ├── error_resilience.py # エラー耐性
│   ├── api_retry.py        # APIリトライ
│   ├── logger.py           # ログ管理
│   ├── logging.py          # ログ設定
│   ├── status.py           # ステータス管理
│   ├── enhanced_status_manager.py  # 拡張ステータス
│   ├── config_validator.py # 設定検証
│   ├── config_state.py     # 設定状態
│   ├── data.py             # データ処理
│   ├── file.py             # ファイル操作
│   ├── model.py            # モデルユーティリティ
│   ├── chart.py            # チャート生成
│   ├── pre_computed_cache.py       # 事前計算キャッシュ
│   ├── ensemble_confidence.py      # アンサンブル信頼度
│   ├── http_client_optimizer.py    # HTTPクライアント最適化
│   ├── japanese_market.py          # 日本市場特有処理
│   ├── cloud_run_api_diagnostics.py # Cloud Run診断
│   ├── trading_integration_service.py    # 取引統合サービス
│   └── trading_statistics_manager.py     # 取引統計管理
│
├── validation/             # 検証システム
│   └── ab_testing_system.py # A/Bテストシステム
│
├── ha/                     # 高可用性
│   ├── __init__.py
│   └── state_manager.py    # 状態管理
│
├── feedback/               # フィードバックループ
│   └── feedback_loop_manager.py # フィードバック管理
│
├── indicator/              # テクニカル指標
│   ├── __init__.py
│   └── calculator.py       # 指標計算
│
├── trading/                # 取引機能（未実装）
│   └── __init__.py
│
├── analytics/              # 分析機能
│   └── bitbank_interest_avoidance_analyzer.py # 金利分析
│
└── analysis/               # 市場分析
    └── market_environment_analyzer.py # 市場環境分析
```

## 🚀 Phase 14リファクタリング概要

### Phase 14.1: 緊急修正（完了）
- INIT-PREFETCHコードブロック削除（8時間取引停止問題解決）
- UnboundLocalError修正（Position変数スコープ問題）

### Phase 14.2: モジュール分離（進行中）
- **main.py**: 2,765行 → 90行に削減
- **cli/**: CLIコマンドを独立モジュールに分離
- **utils/**: ユーティリティ関数を整理
- **live-bitbank統合**: --simpleフラグで通常版/シンプル版切り替え

## 🎯 主要機能

### 1. ライブトレード
```bash
# 通常版（統計システム・詳細ログあり）
python -m crypto_bot.main live-bitbank --config config/production/production.yml

# シンプル版（軽量・最小限の初期化）
python -m crypto_bot.main live-bitbank --config config/production/production.yml --simple
```

### 2. バックテスト
```bash
python -m crypto_bot.main backtest --config config/validation/unified_97_features_backtest.yml
```

### 3. モデル学習
```bash
python -m crypto_bot.main train --config config/production/production.yml
```

## 📊 97特徴量システム

- **OHLCV**: 5特徴量（基本価格データ）
- **extra_features**: 92特徴量（テクニカル指標）
- **合計**: 97特徴量

## 🔧 設定

設定ファイルは`config/`ディレクトリで管理：
- `production/production.yml`: 本番用設定
- `validation/`: 検証用設定

## 📝 注意事項

- Phase 14.1でINIT-5以降のプリフェッチ処理を削除
- INIT-1〜4は基本的な初期化として維持
- 統計システムは通常版のみで動作（--simpleでは無効）

## 🔧 crypto_bot/直下ファイル整理案

### **現状のファイル構成**
```
crypto_bot/
├── __init__.py             # パッケージ初期化 → 維持
├── main.py                 # メインエントリーポイント → 維持
├── config.py               # 設定管理 → 維持
├── api.py                  # レガシーAPI → 削除候補（api/と重複）
├── monitor.py              # Streamlitダッシュボード → 別フォルダへ移動候補
├── init_enhanced.py        # 拡張初期化 → utils/へ移動候補
└── main_backup_20250806.py # バックアップ → 削除候補
```

### **整理案詳細**

#### 1. **削除推奨ファイル**
- **main_backup_20250806.py**
  - 2,765行の旧バージョンバックアップ
  - Phase 14でmain.pyが130行にリファクタリング済み
  - Gitで履歴管理されているため不要

- **api.py**
  - api/フォルダのhealth.pyと機能重複
  - api/の方がより詳細で本格的な実装
  - レガシーコードとして削除推奨

#### 2. **移動推奨ファイル**
- **monitor.py → visualization/dashboard.py**
  - Streamlitによるビジュアルダッシュボード
  - monitoring/フォルダとは別目的（可視化専用）
  - 新しくvisualization/フォルダを作成して移動

- **init_enhanced.py → utils/init_enhanced.py**
  - INIT段階のエラーハンドリング強化
  - ユーティリティ機能として整理
  - utils/に移動して管理

#### 3. **維持ファイル**
- **__init__.py** - パッケージ初期化に必要
- **main.py** - エントリーポイント
- **config.py** - 設定管理の中核

### **推奨アクション**
```bash
# 1. バックアップファイル削除
rm crypto_bot/main_backup_20250806.py

# 2. レガシーAPI削除
rm crypto_bot/api.py

# 3. 可視化フォルダ作成・ファイル移動
mkdir -p crypto_bot/visualization
mv crypto_bot/monitor.py crypto_bot/visualization/dashboard.py

# 4. 拡張初期化をutilsへ移動
mv crypto_bot/init_enhanced.py crypto_bot/utils/

# 5. importパスの更新が必要な箇所を確認
grep -r "from crypto_bot.monitor" .
grep -r "import crypto_bot.api" .
grep -r "from crypto_bot.init_enhanced" .
```

## 🚨 Phase 16: 重大課題解決・大規模リファクタリング計画 (2025年8月7日策定)

### **🚨 緊急課題: トレード実行不能問題**

#### **根本原因特定（Phase 16.1最優先対応）**
1. **アンサンブルモデル未準備**
   - 問題：`create_trading_ensemble`が空のモデルを作成
   - 影響：「No ensemble models are ready」エラー
   - 修正：事前学習済みモデル（lgbm/xgb/rf）の自動読み込み機能追加

2. **データ取得不足問題**
   - 問題：Bitbank API 72時間制限により256/400レコード（64%）のみ取得
   - 影響：97特徴量計算・ATR計算に必要なデータ不足
   - 修正：適切な期間計算・400レコード確実取得ロジック実装

3. **タイムスタンプ制限問題**
   - 問題：「Timestamp beyond Bitbank limit」大量発生
   - 影響：2025年7月頃の過去データ要求がAPI制限超過
   - 修正：72時間以内の適切なデータ要求期間調整

### **📊 各フォルダREADME調査結果・公式課題認識との完全一致**

#### **🎯 strategy/フォルダ課題（README公式認識）**
- **公式課題**：「Bitbank関連戦略が8ファイルに分散・機能重複・類似実装の統合必要」
- **統合計画**：8ファイル → 2ファイル統合（core_strategy.py + specialized_strategy.py）
- **対象ファイル**：bitbank_btc_jpy + xrp_jpy + integrated + day_trading + taker_avoidance + enhanced_position + execution_orchestrator + integrated_day_system

#### **🎯 execution/フォルダ課題（README公式認識）**
- **公式課題**：「Bitbank関連ファイルが6つに分散・機能別から取引所別への再編成検討」
- **統合計画**：6ファイル → 2ファイル統合（core_execution.py + optimization.py）
- **対象ファイル**：bitbank_client + order_manager + api_rate_limiter + fee_optimizer + fee_guard + execution_efficiency_optimizer

#### **🎯 utils/フォルダ課題（README公式認識）**
- **公式課題**：「類似機能の統合（logger.py/logging.py等）・status.py + enhanced_status_manager.py統合」
- **統合計画**：重複機能完全統合（logging_system.py + status_manager.py）
- **対象ファイル**：logger.py + logging.py → logging_system.py / status.py + enhanced_status_manager.py → status_manager.py

#### **🎯 ml/フォルダ課題（README公式認識）**
- **公式課題**：「feature_*関連ファイル多数・feature_order_manager.py.backup整理」
- **整理計画**：feature_*ファイル論理的サブフォルダ化・バックアップファイル削除
- **巨大ファイル分割**：preprocessor.py（3,314行）→4ファイル・feature_master_implementation.py（1,801行）→3ファイル

#### **🎯 data/フォルダ課題（README公式認識）**
- **公式課題**：「fetcher.py+multi_timeframe_fetcher.py機能重複・前処理ロジック統合検討」
- **統合計画**：機能重複解消・fetcher.py（1,451行）→3ファイル分割
- **対象**：API通信・データ検証・フェッチ統合に論理分離

#### **🎯 analysis/ + analytics/ 統合（README公式認識）**
- **公式課題**：「analytics/フォルダとの役割重複・monitoring/との連携強化必要」
- **統合計画**：analysis/（市場分析）+ analytics/（パフォーマンス分析）→ 統合analysis/
- **効果**：重複除去・責任明確化・保守性向上

#### **🎯 indicator/フォルダ課題（README公式認識）**
- **公式課題**：「指標機能に対して単一ファイルのみ・カテゴリ別分離の検討」
- **分割計画**：technical_engine.py（1,405行）→ トレンド系・オシレーター系・ボラティリティ系・出来高系に分割

#### **🎯 空フォルダ削除**
- **trading/フォルダ**：「現在は空のフォルダ・削除または実装の判断が必要・execution/との統合検討」→ 削除決定

#### **🎯 バックアップファイル削除**
- main_backup_20250806.py（2,765行）→ 削除（Phase 14で130行化完了・Git履歴保存済み）
- feature_order_manager.py.backup → 削除（正式バージョン管理移行）

---

## 🚀 Phase 16実装計画・スケジュール

### **Phase 16.1: 緊急トレード実行修復（最優先・1-2日）**

#### **A. アンサンブルモデル修復**
```python
# 修正対象: crypto_bot/ml/ensemble.py
def create_trading_ensemble(config: Dict[str, Any]) -> TradingEnsembleClassifier:
    # 追加機能: 事前学習済みモデル自動読み込み
    ensemble = TradingEnsembleClassifier(...)
    ensemble.load_production_models()  # 新機能
    return ensemble
```

#### **B. データ取得修復**
```python
# 修正対象: crypto_bot/data/fetcher.py
def _validate_timestamp_h28(self, ts: int, context: str):
    # 現状: 2025年7月要求 → API制限超過
    # 修正: 72時間制限考慮・400レコード確実取得ロジック
```

#### **C. 実行可能性確認**
- エントリーシグナル → 実取引実行フロー完全動作確認
- 400レコードデータ取得確認
- アンサンブル予測機能完全復旧確認

### **Phase 16.2: 大規模統合リファクタリング（3-5日）**

#### **A. Bitbank関連統合**
1. **strategy/統合**（8→2ファイル）
   ```bash
   mkdir -p crypto_bot/strategy/exchange/bitbank
   # core_strategy.py（4ファイル統合）
   # specialized_strategy.py（4ファイル統合）
   ```

2. **execution/統合**（6→2ファイル）
   ```bash
   mkdir -p crypto_bot/execution/exchange/bitbank  
   # core_execution.py（3ファイル統合）
   # optimization.py（3ファイル統合）
   ```

#### **B. utils/重複解消**
```bash
crypto_bot/utils/system/
├── logging_system.py      # logger.py + logging.py 統合
├── status_manager.py      # status.py + enhanced_status_manager.py 統合
└── cache_manager.py       # キャッシュ関連機能統合
```

#### **C. analysis+analytics統合**
```bash
crypto_bot/analysis/
├── market/                # 旧analysis/market_environment_analyzer.py
├── performance/           # 旧analytics/bitbank_interest_avoidance_analyzer.py  
└── reporting/            # 統合レポート生成
```

### **Phase 16.3: 巨大ファイル分割（2-3日）**

#### **A. preprocessor.py分割**（3,314行→4ファイル）
```bash
crypto_bot/ml/preprocessing/
├── feature_preprocessor.py    # 特徴量前処理（800行）
├── data_cleaner.py           # データクリーニング（800行）
├── scaler_manager.py         # スケーリング管理（800行）
└── preprocessing_pipeline.py # パイプライン統合（900行）
```

#### **B. feature_master_implementation.py分割**（1,801行→3ファイル）
```bash
crypto_bot/ml/features/master/
├── technical_indicators.py   # テクニカル指標（600行）
├── market_features.py        # 市場特徴量（600行）
└── feature_coordinator.py    # 特徴量統合（600行）
```

#### **C. fetcher.py分割**（1,451行→3ファイル）
```bash
crypto_bot/data/fetching/
├── api_client.py             # API通信（500行）
├── data_validator.py         # データ検証（500行）
└── fetch_coordinator.py      # フェッチ統合（450行）
```

### **Phase 16.4: 清理・テスト・検証（1-2日）**

#### **A. 不要要素削除**
```bash
# 空フォルダ削除
rm -rf crypto_bot/trading/

# バックアップファイル削除  
rm crypto_bot/main_backup_20250806.py
rm crypto_bot/ml/feature_order_manager.py.backup

# レガシーファイル整理
rm crypto_bot/api.py  # api/フォルダと重複
```

#### **B. import文更新・テスト実行**
```bash
# 全import文更新
find . -name "*.py" -exec sed -i 's/old_import_path/new_import_path/g' {} \;

# 品質チェック実行
bash scripts/checks.sh
# 期待: flake8・black・pytest全通過・600+テスト成功

# 統合テスト実行
python -m crypto_bot.main validate-config --config config/production/production.yml
```

#### **C. README文書更新**
- 各フォルダREADME.md更新（新構造反映）
- crypto_bot/README.md更新（Phase 16完了記録）
- 新しいファイル構成・使用方法文書化

---

## 📊 Phase 16実装効果予測

### **即座の効果（Phase 16.1完了時）**
- ✅ **エントリーシグナル→実取引実行**完全動作
- ✅ **アンサンブル予測機能**完全復旧  
- ✅ **400レコードデータ取得**保証
- ✅ **トレードできない問題**根本解決

### **大規模効果（Phase 16.2-16.4完了時）**
- 🚀 **ファイル数50%削減**：20+ファイル統合→10ファイル
- 🚀 **巨大ファイル解消**：main.py成功モデル全面適用（平均1,500行→500行）
- 🚀 **公式課題100%解決**：全フォルダREADME課題完全対応
- 🚀 **保守性劇的向上**：重複除去・責任明確化・開発効率2-3倍向上
- 🚀 **コード品質向上**：統合テスト600+成功・35%+カバレッジ達成

### **長期的価値**
- 📈 **開発効率化**：新機能追加時間50%短縮
- 📈 **バグ修正効率化**：問題箇所特定時間70%短縮  
- 📈 **チーム開発対応**：明確な責任分離・並行開発可能
- 📈 **スケーラビリティ**：新機能・新取引所追加容易化

---

## ⚠️ Phase 16実装時重要原則

### **1. 段階的実装**
- Phase 16.1（トレード修復）を最優先完了
- Phase 16.2以降は16.1動作確認後に実施
- 各段階でテスト実行・動作確認必須

### **2. ブレない実装**
- 本README.md記載計画に厳密準拠
- README課題認識と100%一致した統合実行
- 独自判断による計画変更厳禁

### **3. 品質保証**
- 各ファイル統合後にimport文・依存関係確認
- scripts/checks.sh実行・全品質チェック通過必須
- 統合テスト・バックテスト動作確認必須

### **4. 文書化徹底**  
- 統合・分割ファイルの新機能説明更新
- 各フォルダREADME.md新構造反映
- 変更理由・効果の記録保持

**Phase 16により、main.py Phase 14成功に匹敵する大規模リファクタリングを実現し、crypto-botの保守性・拡張性・開発効率を劇的に向上させます。** 🎯

---

### **フォルダ構造最適化案**
```
crypto_bot/
├── core/               # コア機能統合
│   ├── main.py
│   ├── config.py
│   └── __init__.py
├── trading/            # 取引関連統合
│   ├── strategy/       # 戦略
│   ├── execution/      # 実行
│   └── risk/           # リスク管理
├── intelligence/       # ML・分析統合
│   ├── ml/             # 機械学習
│   ├── analysis/       # 市場分析
│   └── indicator/      # 指標計算
├── infrastructure/     # インフラ統合
│   ├── api/            # API
│   ├── monitoring/     # 監視
│   ├── visualization/  # 可視化
│   └── ha/             # 高可用性
└── support/            # サポート機能
    ├── utils/          # ユーティリティ
    ├── data/           # データ管理
    └── validation/     # 検証
```
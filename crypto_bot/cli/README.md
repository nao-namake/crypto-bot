# cli/ - コマンドラインインターフェース実装

## 📋 概要

**Command Line Interface Implementation**  
本フォルダは crypto-bot のCLIコマンド実装を管理し、ユーザーが実行できる各種コマンドの処理ロジックを提供します。

**🔗 Phase 16.5-C依存**: 全7つのCLIモジュールが utils/config.py に依存（旧crypto_bot/config.py から移動）

**🆕 2025年8月12日更新**: 
- **live.py データ取得効率化**: ATR初期化時のデータをメインループで再利用（重複取得防止）
- **cached_initial_data実装**: 48件のデータキャッシュにより、API制限回避とループ開始高速化
- **is_first_iteration フラグ**: 初回ループでキャッシュデータを再利用する仕組み

**2025年8月10日更新**: 
- **live.py修正**: EntryExit初期化バグ修正（正しい引数: strategy, risk_manager, atr_series）
- **ATR計算追加**: リスク管理用のATRシリーズ計算処理を追加
- **エントリーシグナル生成問題の根本解決**: 初期化エラーによる取引停止問題を解消
- **📝 Phase 2-1 ペーパートレードモード追加**: --paper-tradeフラグで仮想取引実行・リスクフリー検証

## 🎯 主要機能

### **取引関連コマンド**
- `backtest` - 過去データでのバックテスト実行
- `live-bitbank` - Bitbankでのライブ取引実行
- `optimize-backtest` - バックテストパラメータ最適化

### **モデル・学習関連コマンド**
- `train` - モデル訓練実行
- `optimize-ml` - 機械学習パラメータ最適化
- `optimize-and-train` - 最適化と訓練の統合実行
- `train-best` - 最良パラメータでの訓練
- `retrain` - モデル再訓練
- `validate-model` - モデル検証

### **オンライン学習関連コマンド**
- `online-train` - オンライン学習実行
- `online-status` - オンライン学習状態確認
- `drift-monitor` - ドリフト監視
- `retrain-schedule` - 再訓練スケジュール管理

### **その他のコマンド**
- `list-strategies` - 利用可能な戦略一覧表示
- `strategy-info` - 戦略詳細情報表示
- `validate-config` - 設定ファイル検証
- `diagnose-apis` - API接続診断
- `stats` - 統計情報表示

## 📁 ファイル構成

```
cli/
├── __init__.py      # パッケージ初期化
├── backtest.py      # バックテストコマンド
├── live.py          # ライブ取引コマンド（2025/8/10修正: EntryExit初期化修正）
├── model.py         # モデル管理コマンド
├── online.py        # オンライン学習コマンド
├── optimize.py      # 最適化コマンド
├── stats.py         # 統計コマンド
├── strategy.py      # 戦略管理コマンド
├── train.py         # 訓練関連コマンド
└── validate.py      # 検証コマンド
```

## 🔍 各ファイルの役割

### **backtest.py**
- `backtest_command()` - バックテスト実行
- ウォークフォワード分析対応
- 結果のCSV出力・可視化
- 集計レポート生成

### **live.py** (2025年8月10日更新)
- `live_bitbank_command()` - Bitbankライブ取引
- 環境変数からのAPI認証情報取得
- **簡素化されたINIT処理**:
  - INIT-1〜4のみ実行（INIT-5以降は削除）
  - オプショナルなキャッシュロード
  - メインループへの直接移行
- **改善された初期化処理**:
  - 初期データキャッシュ優先ロード
  - Docker環境とローカル環境の両対応
  - キャッシュパス: `/app/cache/initial_data.pkl` または `cache/initial_data.pkl`
  - フォールバック: キャッシュ失敗時はメインループで取得
- リアルタイム取引ループ実装
- エラー処理・リトライ機能
- --simpleフラグ: 統計システムなしの軽量版実行
- **📝 --paper-tradeフラグ**: ペーパートレードモード（Phase 2-1）
  - 実取引を行わず仮想取引で検証
  - 実際の市場データを使用
  - 取引結果をCSV/JSONに記録
  - P&L・勝率・ドローダウン追跡

### **model.py**
- `retrain_command()` - モデル再訓練
- `validate_model_command()` - モデル性能検証
- 特徴量重要度分析
- モデルメタデータ管理

### **online.py**
- `online_train_command()` - オンライン学習開始
- `online_status_command()` - 学習状態監視
- `drift_monitor_command()` - ドリフト検出
- `retrain_schedule_command()` - スケジュール設定

### **optimize.py**
- `optimize_backtest_command()` - バックテスト最適化
- パラメータグリッドサーチ
- 並列処理対応
- 最適パラメータ保存

### **stats.py**
- `stats_command()` - 取引統計表示
- パフォーマンスメトリクス計算
- 期間別集計
- レポート生成

### **strategy.py**
- `list_strategies_command()` - 戦略一覧
- `strategy_info_command()` - 戦略詳細
- 戦略パラメータ表示
- 戦略登録状態確認

### **train.py**
- `train_command()` - 基本訓練実行
- `optimize_ml_command()` - ML最適化
- `optimize_and_train_command()` - 統合実行
- `train_best_command()` - 最良設定訓練

### **validate.py**
- `validate_config_command()` - 設定検証
- `diagnose_apis_command()` - API診断
- 接続テスト実行
- エラー詳細レポート

## 🚀 使用方法

### **CLIコマンド実行例**
```bash
# バックテスト実行（従来方式）
python -m crypto_bot.main backtest --config backtest/configs/base_backtest_config.yml

# 🆕 統合バックテストシステム（推奨 - 2025年8月13日完成）
python backtest/scripts/run_backtest.py test_rsi_macd_ema     # 指標組み合わせテスト
python backtest/scripts/run_backtest.py base_backtest_config  # 97特徴量フルテスト

# ライブ取引開始
python -m crypto_bot.main live-bitbank --config config/production/production.yml

# ペーパートレード実行（Phase 2-1: リスクフリー検証）
python -m crypto_bot.main live-bitbank --config config/production/production.yml --paper-trade

# シンプルモード＋ペーパートレード
python -m crypto_bot.main live-bitbank --config config/production/production.yml --simple --paper-trade

# モデル訓練
python -m crypto_bot.main train --config config/ml/train_config.yml

# 戦略一覧表示
python -m crypto_bot.main list-strategies

# API診断
python -m crypto_bot.main diagnose-apis
```

## ⚠️ 課題・改善点

### **Phase 16.5-C統合効果**
- **設定読み込み統一**: 全CLIモジュールが utils/config.py の load_config() を使用
- **7モジュール依存**: backtest/live/optimize/validate/train/model/online が統一設定管理
- **crypto_bot直下整理**: config.py適切配置により import 一貫性確保

### **既存の課題（継続改善対象）**
- 各コマンドファイルで共通の初期化処理が重複
- ログ設定の共通化が必要
- エラーハンドリングパターンの統一化

### **ファイル統合の可能性**
- `model.py`と`train.py`の機能が類似
- `stats.py`は他のコマンドに統合可能
- より論理的なグループ化を検討

### **テスト不足**
- CLIコマンドの統合テストが必要
- モックを使用した単体テスト追加
- エラーケースのテストカバレッジ向上

### **ドキュメント**
- 各コマンドの詳細な使用例が必要
- パラメータ説明の充実
- よくあるエラーと対処法

## 📝 今後の展開

### **Phase 16.5-C統合完了後の発展**
1. **utils/config.py依存最適化**
   - 設定ファイル検証機能の統合活用
   - 環境変数管理の一元化
   - 設定継承・上書き機能の拡充

2. **コマンド構造の再編成**
   - サブコマンドグループ化（trading, model, analysis等）
   - より直感的なコマンド名
   - エイリアスサポート

2. **インタラクティブモード**
   - 対話的な設定入力
   - コマンド補完機能
   - リアルタイムステータス表示

3. **出力形式の拡張**
   - JSON/YAML出力対応
   - カスタムフォーマット
   - ストリーミング出力

4. **並列実行対応**
   - 複数コマンドの同時実行
   - ジョブキュー管理
   - 進捗表示の改善
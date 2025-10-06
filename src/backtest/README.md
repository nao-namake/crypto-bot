# 📊 バックテストシステム (Phase 28完了・Phase 29最適化版)

## 🎯 概要

**本番と完全同一のロジック**で動作するバックテストシステムです。
独自エンジンを廃止し、`TradingCycleManager`を使用してCSVデータから時系列バックテストを実行します。

## ✨ 特徴

- ✅ **本番同一ロジック**: ペーパートレードと同じ`TradingCycleManager`使用
- ✅ **固定ファイル名**: CSVファイル差し替えで簡単期間変更
- ✅ **期間自動統一**: 4時間足と15分足の期間を自動マッチング
- ✅ **高速CSV処理**: API依存なし・キャッシュ機能付き
- ✅ **時系列処理**: ルックアヘッドバイアス完全防止
- ✅ **集約管理**: バックテスト関連ファイル一元管理

## 📁 ディレクトリ構造

```
src/backtest/
├── __init__.py                    # Phase 29最適化版
├── README.md                      # このファイル  
├── reporter.py                    # JSONレポート生成
├── data/
│   ├── csv_data_loader.py         # CSV読み込み・キャッシュ機能
│   └── historical/                # 📂 CSVデータ（固定ファイル名）
│       ├── BTC_JPY_4h.csv         # 4時間足データ（1080件）
│       └── BTC_JPY_15m.csv        # 15分足データ（864件）
├── scripts/
│   └── collect_historical_csv.py  # データ収集・期間統一機能
└── logs/                          # レポート出力先
    ├── backtest_YYYYMMDD_HHMMSS.json
    ├── progress_YYYYMMDD_HHMMSS.json
    └── error_YYYYMMDD_HHMMSS.json
```

## 🚀 使用方法

### 1. 基本的なバックテスト実行

```bash
# 既存CSVデータでバックテスト実行（すぐに実行可能）
python main.py --mode backtest

# レポート確認
ls -t src/backtest/logs/backtest_*.json | head -1 | xargs cat | jq
```

### 2. データ期間変更

```bash
# 新しい期間のデータを収集（固定ファイル名で上書き）
python src/backtest/scripts/collect_historical_csv.py --days 90

# 15分足のみ再収集（既存4時間足データに期間を合わせる）
python src/backtest/scripts/collect_historical_csv.py --match-4h --timeframes 15m

# バックテスト実行
python main.py --mode backtest
```

### 3. データ確認

```bash
# CSVファイル確認
ls -la src/backtest/data/historical/
# 期待される結果: BTC_JPY_4h.csv, BTC_JPY_15m.csv

# データ統計確認
python -c "
import pandas as pd
df_4h = pd.read_csv('src/backtest/data/historical/BTC_JPY_4h.csv')
df_15m = pd.read_csv('src/backtest/data/historical/BTC_JPY_15m.csv')
print(f'4時間足: {len(df_4h)}件 ({df_4h[\"datetime\"].iloc[0]} - {df_4h[\"datetime\"].iloc[-1]})')
print(f'15分足: {len(df_15m)}件 ({df_15m[\"datetime\"].iloc[0]} - {df_15m[\"datetime\"].iloc[-1]})')
"
```

## 🔧 システムアーキテクチャ

### データフロー

```
main.py --mode backtest
    ↓
TradingOrchestrator
    ↓
BacktestRunner (src/core/execution/)
    ↓ 固定CSVから時系列データ供給
DataPipeline (backtest_mode=True)
    ↓
TradingCycleManager ← 本番と完全同一
    ↓
15特徴量生成 → 5戦略統合 → ML予測 → リスク管理 → BUY/SELL判定
```

### 主要コンポーネント

#### 🏃 BacktestRunner
- **場所**: `src/core/execution/backtest_runner.py`
- **役割**: CSV時系列処理、本番サイクル呼び出し
- **特徴**: ペーパートレードと同じアプローチ、ルックアヘッド防止

#### 📊 CSVDataLoader
- **場所**: `src/backtest/data/csv_data_loader.py`
- **機能**: 固定ファイル名対応、マルチタイムフレーム、キャッシュ機能
- **データ**: `src/backtest/data/historical/` の固定ファイル

#### 📝 BacktestReporter  
- **場所**: `src/backtest/reporter.py`
- **出力**: JSON形式の実行統計・進捗・エラーレポート

## 📋 データ管理ルール

### ファイル命名規則

- **固定ファイル名**: `BTC_JPY_4h.csv`, `BTC_JPY_15m.csv`
- **期間変更**: CSVファイル上書きのみ（パス修正不要）
- **サポート時間軸**: 4h（トレンド）, 15m（エントリー）

### 期間統一ルール

1. **4時間足優先**: 4時間足データの期間をベースとする
2. **自動マッチング**: `--match-4h`で15分足を4時間足に合わせる
3. **データ整合性**: MultiTimeframe戦略のため両時間軸必須

### 開発ルール

- ✅ **本番同一**: `TradingCycleManager`完全共用
- ✅ **CSV優先**: API呼び出し完全排除
- ✅ **シンプル維持**: 複雑な独自ロジック禁止
- ✅ **集約管理**: `src/backtest/`配下に一元化

## ⚡ 高速化機能

### CSVキャッシュシステム

```python
# キャッシュ利用確認
from src.backtest.data.csv_data_loader import get_csv_loader
loader = get_csv_loader()
loader.get_latest_data_info()  # ファイル情報確認
loader.clear_cache()          # キャッシュクリア
```

### データ整合性チェック

```python
# データ品質確認
loader.validate_data_integrity('BTC/JPY', '4h')
loader.validate_data_integrity('BTC/JPY', '15m')
```

## 🔍 トラブルシューティング

### データが見つからない

```bash
# 基本データ収集
python src/backtest/scripts/collect_historical_csv.py --days 180

# 期間統一（推奨）
python src/backtest/scripts/collect_historical_csv.py --match-4h --timeframes 15m
```

### MultiTimeframe戦略エラー

```bash
# 両時間軸データ確認
ls src/backtest/data/historical/BTC_JPY_*.csv
# 期待結果: BTC_JPY_4h.csv, BTC_JPY_15m.csv

# データ期間確認
python -c "
from src.backtest.data.csv_data_loader import get_csv_loader
loader = get_csv_loader()
multi_data = loader.load_multi_timeframe('BTC/JPY', ['15m', '4h'], limit=5)
print('利用可能時間軸:', list(multi_data.keys()))
"
```

### バックテスト実行エラー

```bash
# システム整合性確認
python -c "
from src.core.execution.backtest_runner import BacktestRunner
from src.backtest.data.csv_data_loader import get_csv_loader
print('✅ BacktestRunner: OK')
print('✅ CSVLoader: OK')
"

# データパイプライン確認
python -c "
from src.data.data_pipeline import DataPipeline
pipeline = DataPipeline()
pipeline.set_backtest_mode(True)
print('✅ DataPipeline backtest mode: OK')
"
```

## 💡 実用的な使用例

### 期間比較分析

```bash
# 短期間（1ヶ月）
python src/backtest/scripts/collect_historical_csv.py --days 30
python main.py --mode backtest
mv src/backtest/logs/backtest_*.json results_1month.json

# 長期間（6ヶ月）
python src/backtest/scripts/collect_historical_csv.py --days 180  
python main.py --mode backtest
mv src/backtest/logs/backtest_*.json results_6months.json

# 結果比較
jq '.execution_stats' results_1month.json
jq '.execution_stats' results_6months.json
```

### 戦略別分析

```bash
# データ統一
python src/backtest/scripts/collect_historical_csv.py --match-4h

# バックテスト実行（全戦略対象）
python main.py --mode backtest

# レポート分析
latest=$(ls -t src/backtest/logs/backtest_*.json | head -1)
jq '.execution_stats.strategy_performance' "$latest"
```

## 🎯 期待される動作

### 正常動作パターン

1. **データ読み込み**: 固定CSVファイルから高速読み込み
2. **時系列処理**: 1件ずつ順次処理（ルックアヘッド防止）
3. **本番同一処理**: 15特徴量→5戦略→ML→リスク管理→取引判定
4. **JSONレポート**: 構造化された実行結果出力

### パフォーマンス基準

- **読み込み速度**: 1080件（4h）+ 864件（15m）を1秒以内
- **処理速度**: 1件あたり0.1秒以内（特徴量生成含む）
- **メモリ使用量**: 50MB以下（キャッシュ込み）

## ⚠️ 廃止された機能（Phase 21）

### 削除済みコンポーネント

- ❌ `BacktestEngine`（独自エンジン）
- ❌ `BacktestEvaluator`（複雑統計分析）
- ❌ `/scripts/management/run_backtest.py`（独立実行）
- ❌ `日付付きCSVファイル名`（YYYYMM形式）

### 簡略化機能

- **レポート**: 複雑統計 → シンプルJSON
- **設定**: 専用設定 → 本番設定共用  
- **データ**: API+CSV → CSV専用
- **ファイル名**: 日付変動 → 固定名

---

**Phase 28完了・Phase 29最適化版**: 本番同一ロジック・固定ファイル名・期間統一・集約管理の4原則による、信頼性と使いやすさを兼ね備えたバックテストシステム。デプロイ前最終最適化完了 🚀
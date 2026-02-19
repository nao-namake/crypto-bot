# src/backtest/ - バックテストシステム

本番同一ロジック（TradingCycleManager統合）でCSVデータから時系列バックテストを実行。

## ファイル構成

```
src/backtest/
├── __init__.py                    14行  エクスポート（BacktestReporter・TradeTracker・MLAnalyzer）
├── reporter.py                 1,470行  TradeTracker・MLAnalyzer・BacktestReporter
├── visualizer.py                 314行  matplotlib可視化（4種グラフ）
├── data/
│   ├── csv_data_loader.py        255行  CSV読み込み・キャッシュ
│   └── historical/                     CSVデータ（BTC_JPY_4h.csv, BTC_JPY_15m.csv）
├── scripts/
│   └── collect_historical_csv.py 435行  Bitbank APIデータ収集
└── (出力先: logs/backtest/)            レポート出力先（JSON・テキスト・グラフ）
```

## 主要コンポーネント

### TradeTracker
エントリー/エグジットをペアリングし取引毎の損益を計算。勝率・PF・最大DD・MFE/MAE等の指標を提供。

### MLAnalyzer
ML予測の分布分析・信頼度統計・ML vs 戦略一致率を算出。

### BacktestReporter
JSON/テキスト/グラフ（matplotlib）形式のレポートを生成。TradeTracker・MLAnalyzerを統合。

### BacktestCSVLoader
固定ファイル名CSV読み込み。キャッシュ・マルチタイムフレーム（15m+4h）・データ整合性チェック対応。

### HistoricalDataCollector
Bitbank Public APIから4h（年単位）・15m（日単位）データを直接取得しCSV保存。

## 使用方法

```bash
# データ収集（初回・更新時）
python src/backtest/scripts/collect_historical_csv.py --days 180

# 15分足のみ再収集（既存4時間足に期間合わせ）
python src/backtest/scripts/collect_historical_csv.py --match-4h --timeframes 15m

# バックテスト実行
python main.py --mode backtest

# レポート確認
ls -t logs/backtest/backtest_*.json | head -1
```

## 外部依存

| インポート元 | 使用内容 |
|-------------|---------|
| `src.core.config` | `get_threshold()`（手数料率・初期残高） |
| `src.core.logger` | `get_logger()`（構造化ログ） |
| `src.core.exceptions` | `DataFetchError`（CSV読み込みエラー） |
| `src.data.bitbank_client` | `BitbankClient`（データ収集フォールバック） |
| `matplotlib` | グラフ生成（Aggバックエンド） |
| `numpy` / `pandas` | 数値計算・DataFrame処理 |

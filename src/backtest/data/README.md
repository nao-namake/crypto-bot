# Backtest Data Module

## 概要

バックテスト用の高速CSVデータ読み込みシステム。
API依存を排除し、安定した過去データ取得を実現。

## ディレクトリ構成

```
src/backtest/data/
├── csv_data_loader.py      # CSVデータローダー（メインモジュール）
├── historical/             # 履歴データ保存ディレクトリ（gitignore）
│   ├── .gitkeep
│   ├── BTC_JPY_15m.csv    # 15分足データ（~30,000行・180日分）
│   └── BTC_JPY_4h.csv     # 4時間足データ（~2,000行・180日分）
└── README.md              # このファイル
```

## 使い方

### Pythonモジュールとしてimport

```python
from src.backtest.data.csv_data_loader import get_csv_loader

# シングルトンインスタンス取得
loader = get_csv_loader()

# データ読み込み（単一時間軸）
df_4h = loader.load_historical_data(symbol="BTC/JPY", timeframe="4h")
df_15m = loader.load_historical_data(symbol="BTC/JPY", timeframe="15m")

# データ読み込み（複数時間軸）
data = loader.load_historical_data(
    symbol="BTC/JPY",
    timeframes=["4h", "15m"]
)
df_4h = data["4h"]
df_15m = data["15m"]

# 期間フィルタリング
from datetime import datetime, timedelta

end_date = datetime.now()
start_date = end_date - timedelta(days=30)

df = loader.load_historical_data(
    symbol="BTC/JPY",
    timeframe="15m",
    start_date=start_date,
    end_date=end_date
)

# 行数制限
df = loader.load_historical_data(
    symbol="BTC/JPY",
    timeframe="4h",
    limit=100  # 最新100行のみ
)
```

## データ収集

CSVデータは `src/backtest/scripts/collect_historical_csv.py` で生成されます：

```bash
# 180日分のデータ収集（推奨）
python src/backtest/scripts/collect_historical_csv.py --days 180

# カスタム期間
python src/backtest/scripts/collect_historical_csv.py --days 90
```

詳細は `../scripts/collect_historical_csv.py` を参照。

## 主要機能

### 1. 高速読み込み
- 数万件のOHLCVデータを高速処理
- キャッシュ機構により2回目以降は即座に読み込み

### 2. 柔軟なファイル解決
- 固定ファイル名（`BTC_JPY_15m.csv`）を優先
- 存在しない場合、日付付きファイルへフォールバック

### 3. データ整合性チェック
8種類の検証機能：
- 必須カラム存在確認
- データ型検証
- タイムスタンプ順序確認
- 重複行検出
- OHLC妥当性チェック（High≥Open/Close, Low≤Open/Close）
- 欠損値検出
- ゼロボリューム検出

### 4. 期間フィルタリング
- 開始日・終了日による絞り込み
- 行数制限（limit）機能

## データフォーマット

### CSVファイル形式

```csv
timestamp,open,high,low,close,volume,datetime
1731458700000,13651565.0,13652988.0,13585063.0,13612048.0,2.9298,2024-11-13 09:45:00
```

| カラム | 型 | 説明 |
|--------|-----|------|
| timestamp | int | UNIXタイムスタンプ（ミリ秒） |
| open | float | 始値 |
| high | float | 高値 |
| low | float | 安値 |
| close | float | 終値 |
| volume | float | 出来高（BTC） |
| datetime | str | 人間可読な日時（JST） |

## Gitignore

CSV データファイルは `.gitignore` により git 管理対象外：

```gitignore
# .gitignore
src/backtest/data/*.csv
```

これにより：
- リポジトリサイズ削減
- データ更新時のコミット不要
- 各環境で独自にデータ収集可能

## 関連ファイル

- **実行ツール**: `scripts/backtest/run_backtest.sh`
- **レポート生成**: `scripts/backtest/generate_markdown_report.py`
- **データ収集**: `src/backtest/scripts/collect_historical_csv.py`
- **バックテスト実行**: `src/core/execution/backtest_runner.py`

## トラブルシューティング

### ファイルが見つからない

```python
# エラー: FileNotFoundError: BTC_JPY_15m.csv not found
```

**解決策**: データ収集を実行
```bash
python src/backtest/scripts/collect_historical_csv.py --days 180
```

### データ整合性エラー

```python
# エラー: DataFetchError: Integrity check failed: ...
```

**解決策**: データ再収集
```bash
# 既存ファイル削除
rm src/backtest/data/historical/BTC_JPY_*.csv

# 再収集
python src/backtest/scripts/collect_historical_csv.py --days 180
```

### キャッシュクリア

```python
loader = get_csv_loader()
loader.clear_cache()  # キャッシュをクリア
df = loader.load_historical_data(symbol="BTC/JPY", timeframe="4h")
```

---

**最終更新**: 2025/11/16 (Phase 52.4-B)

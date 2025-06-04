#!/usr/bin/env python3
# =============================================================================
# ファイル名: tools/fetch_ohlcv.py
# 説明:
#   config/default.yml の内容に従い、指定した取引所・シンボルのOHLCVデータ（ローソク足）を
#   API経由で一括取得し、data/ohlcv.csv として保存するユーティリティです。
#
# 【用途】
#   - 機械学習やバックテストの“元データ”として使うOHLCV（時系列データ）を最新化したいときに実行します。
#   - 取得範囲や通貨ペアなどは config/default.yml で設定できます。
#
# 【使い方例】
#   python tools/fetch_ohlcv.py
#
# 【注意点】
#   - 実行前に config/default.yml の data セクション（exchange/symbol/timeframe等）を確認
#   - APIの制限やレートリミット超過に注意（大量取得の場合は分割取得やSleep設定推奨）
#   - 保存先は data/ohlcv.csv 固定（必要なら出力先を編集）
# =============================================================================

import os

import yaml

from crypto_bot.data.fetcher import MarketDataFetcher

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "default.yml")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "ohlcv.csv")


def main():
    # 1) 設定ファイル読み込み
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)

    # 2) データ取得
    fetcher = MarketDataFetcher(
        exchange_id=cfg["data"]["exchange"],
        symbol=cfg["data"]["symbol"],
        ccxt_options=cfg["data"].get("ccxt_options", {}),
    )

    print(f"▶ {cfg['data']['symbol']} のデータを取得中...")
    df = fetcher.get_price_df(
        timeframe=cfg["data"]["timeframe"],
        since=cfg["data"]["since"],
        limit=cfg["data"]["limit"],
        paginate=cfg["data"]["paginate"],
        per_page=cfg["data"]["per_page"],
    )

    # 3) 出力ディレクトリ作成
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 4) CSV保存
    df.to_csv(OUTPUT_FILE)
    print(f"▶ データを {OUTPUT_FILE} に保存しました")
    print(f"▶ 取得期間: {df.index[0]} ～ {df.index[-1]}")
    print(f"▶ データ件数: {len(df):,} 件")


if __name__ == "__main__":
    main()

import logging
import pandas as pd

from tool import MarketDataFetcher, IndicatorCalculator, DataPreprocessor
from strategy import BollingerStrategy
from entry import EntryExit
from backtest import BacktestEngine
from optimizer import ParameterOptimizer

# ログレベルを WARNING にして、雑多な INFO ログを抑制
logging.basicConfig(
    level=logging.WARNING,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s"
)

def main():
    # 1) データ取得
    fetcher = MarketDataFetcher("BTC/USDT")
    ts = int(pd.Timestamp("2022-01-01T00:00:00Z").value // 10**6)
    df = fetcher.get_price_df(timeframe="1h", after=ts)

    # 2) データ前処理
    df = DataPreprocessor.clean(
        df,
        timeframe="1h",   # fetcher と同じ頻度
        z_thresh=5.0,     # 飛び値判定の Z スコア閾値
        window=20         # 移動平均・SD 計算窓
    )

    # 3) 指標計算
    bb = IndicatorCalculator.calculate_bbands(
        df,
        period=20,
        nbdevup=2.0,
        nbdevdn=2.0
    )
    df = df.join(bb)

    # 4) 通常バックテスト実行＆サマリー表示
    strategy = BollingerStrategy(period=20, nbdevup=2.0, nbdevdn=2.0)
    ee = EntryExit(strategy)
    engine = BacktestEngine(
        price_df=df,
        entry_exit=ee,
        starting_balance=10000.0,
        slippage_rate=0.0
    )
    engine.run()
    engine.summary()

    # 5) パラメータスキャン
    optimizer = ParameterOptimizer(
        price_df=df,
        starting_balance=10000.0,
        slippage_rate=0.0
    )
    # BB period と σ幅をそれぞれリストで指定
    df_scan = optimizer.scan(
        periods=[10, 20, 30],
        nbdevs=[1.5, 2.0, 2.5]
    )
    # 結果を CSV 出力
    df_scan.to_csv("scan_results.csv", index=False)
    # 総損益の多い上位 10 組み合わせを表示
    print("\n===== パラメータスキャン上位10件 =====")
    print(
        df_scan
        .sort_values("total_profit", ascending=False)
        .head(10)
        .to_string(index=False)
    )

if __name__ == "__main__":
    main()
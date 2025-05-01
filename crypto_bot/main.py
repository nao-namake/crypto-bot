import logging
import pandas as pd

from crypto_bot.data.fetcher         import MarketDataFetcher, DataPreprocessor, IndicatorCalculator
from crypto_bot.strategy.bollinger   import BollingerStrategy
from crypto_bot.backtest.engine      import BacktestEngine
from crypto_bot.backtest.optimizer   import ParameterOptimizer

def main():
    # ログ設定
    logging.basicConfig(
        level=logging.WARNING,
        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s"
    )

    # 1) ページングで過去3000本を取得
    fetcher = MarketDataFetcher("BTC/USDT")
    ts = int(pd.Timestamp("2022-01-01T00:00:00Z").value // 10**6)
    df = fetcher.get_price_df(
        timeframe="1h",
        after=ts,
        limit=3000,       # 合計で3000本分取得
        paginate=True,    # ページングモードON
        per_page=500      # 1回のfetchで500本ずつ
    )

    # 2) データ前処理（クリーン & 欠損埋め）
    df = DataPreprocessor.clean(df, timeframe="1h", z_thresh=5.0, window=20)

    # 3) ボリンジャーバンドを計算して結合
    bb = IndicatorCalculator.calculate_bbands(
        df,
        period=20,
        nbdevup=2.0,
        nbdevdn=2.0
    )
    df = df.join(bb)

    # 4) 戦略インスタンス生成
    strategy = BollingerStrategy(period=20, nbdevup=2.0, nbdevdn=2.0)

    # 5) バックテスト実行
    engine = BacktestEngine(
        price_df=df,
        strategy=strategy,
        starting_balance=10_000.0,
        slippage_rate=0.0
    )
    records = engine.run()
    engine.summary()

    # 6) パラメータスキャン
    optimizer = ParameterOptimizer(
        price_df=df,
        starting_balance=10_000.0,
        slippage_rate=0.0
    )
    df_scan = optimizer.scan(
        periods=[10, 20, 30],
        nbdevs=[1.5, 2.0, 2.5]
    )
    df_scan.to_csv("scan_results.csv", index=False)
    print("\n===== パラメータスキャン上位10件 =====")
    print(
        df_scan
        .sort_values("total_profit", ascending=False)
        .head(10)
        .to_string(index=False)
    )

if __name__ == "__main__":
    main()
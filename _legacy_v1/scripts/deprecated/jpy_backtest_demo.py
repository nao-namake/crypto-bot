#!/usr/bin/env python3
"""
JPY建てバックテストデモスクリプト
日本市場特性・税制考慮・JPY建て収益計算のデモンストレーション
"""

import logging
import os
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd

from crypto_bot.backtest.jpy_enhanced_engine import JPYEnhancedBacktestEngine
from crypto_bot.utils.japanese_market import JapaneseMarketCalendar, JPYCalculator

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_sample_data() -> pd.DataFrame:
    """サンプルデータ作成（BTC/JPY）"""
    logger.info("Creating sample BTC/JPY data...")

    # 2024年の1年間のサンプルデータ
    date_range = pd.date_range(start="2024-01-01", end="2024-12-31", freq="1h")

    # 現実的なBTC/JPY価格データ（500万円〜1000万円の範囲）
    np.random.seed(42)
    base_price = 7000000  # 700万円
    price_changes = np.random.normal(0, 0.02, len(date_range))  # 2%の標準偏差
    prices = [base_price]

    for change in price_changes[1:]:
        new_price = prices[-1] * (1 + change)
        # 価格レンジ制限
        new_price = max(5000000, min(12000000, new_price))
        prices.append(new_price)

    # OHLCV データ作成
    df = pd.DataFrame(
        {
            "timestamp": date_range,
            "open": prices,
            "high": [p * (1 + abs(np.random.normal(0, 0.005))) for p in prices],
            "low": [p * (1 - abs(np.random.normal(0, 0.005))) for p in prices],
            "close": prices,
            "volume": np.random.uniform(10, 100, len(date_range)),
        }
    )

    df.set_index("timestamp", inplace=True)
    logger.info(
        f"Sample data created: {len(df)} records, price range: {df['close'].min():,.0f} - {df['close'].max():,.0f} JPY"
    )
    return df


def demo_japanese_market_features():
    """日本市場特性のデモ"""
    logger.info("=== 日本市場特性デモ ===")

    market_calendar = JapaneseMarketCalendar()

    # テスト日付
    test_dates = [
        pd.Timestamp("2024-01-01"),  # 元日
        pd.Timestamp("2024-01-02"),  # 平日
        pd.Timestamp("2024-01-06"),  # 土曜日
        pd.Timestamp("2024-05-03"),  # 憲法記念日
        pd.Timestamp("2024-12-30"),  # 年末
        pd.Timestamp("2024-07-15"),  # 平日
    ]

    for date in test_dates:
        is_holiday = market_calendar.is_japanese_holiday(date)
        is_weekend = market_calendar.is_weekend(date)
        is_year_end = market_calendar.is_year_end_period(date)
        activity_score = market_calendar.get_market_activity_score(date)

        logger.info(f"Date: {date.strftime('%Y-%m-%d %A')}")
        logger.info(
            f"  Holiday: {is_holiday}, Weekend: {is_weekend}, Year-end: {is_year_end}"
        )
        logger.info(f"  Activity Score: {activity_score:.2f}")
        logger.info("")


def demo_jpy_calculator():
    """JPY建て計算機のデモ"""
    logger.info("=== JPY建て計算機デモ ===")

    jpy_calc = JPYCalculator()

    # サンプル取引
    entry_price = 7000000  # 700万円
    exit_price = 7500000  # 750万円
    amount = 0.1  # 0.1 BTC

    # 利益計算
    profit = jpy_calc.calculate_profit_jpy(entry_price, exit_price, amount, "BUY")
    logger.info(f"取引利益: {profit:,.0f} JPY")

    # 税制考慮
    tax_info = jpy_calc.calculate_tax_implications(profit, 30)
    logger.info(f"税引き前利益: {tax_info['gross_profit']:,.0f} JPY")
    logger.info(f"税金額: {tax_info['tax_amount']:,.0f} JPY")
    logger.info(f"税引き後利益: {tax_info['net_profit']:,.0f} JPY")
    logger.info(f"税率: {tax_info['tax_rate']:.1%}")

    # 取引コスト
    cost_info = jpy_calc.calculate_transaction_costs(entry_price, amount, "bitbank")
    logger.info(f"取引価値: {cost_info['trade_value']:,.0f} JPY")
    logger.info(f"メイカー手数料: {cost_info['maker_fee']:,.0f} JPY")
    logger.info(f"テイカー手数料: {cost_info['taker_fee']:,.0f} JPY")
    logger.info("")


def demo_jpy_backtest():
    """JPY建てバックテストデモ"""
    logger.info("=== JPY建てバックテストデモ ===")

    # サンプルデータ作成
    sample_data = create_sample_data()

    # 日本市場設定
    japanese_market_config = {
        "enabled": True,
        "exclude_holidays": False,
        "exclude_year_end": False,
        "apply_activity_score": True,
        "min_activity_score": 0.6,
    }

    # 税制設定
    tax_settings = {"enabled": True, "tax_rate": 0.20, "calculate_net_profit": True}

    # JPY建てバックテストエンジン作成
    engine = JPYEnhancedBacktestEngine(
        price_df=sample_data,
        strategy=None,  # 簡易テスト用
        starting_balance=1000000,  # 100万円
        slippage_rate=0.001,
        commission_rate=0.0012,
        base_currency="JPY",
        japanese_market_config=japanese_market_config,
        tax_settings=tax_settings,
        exchange="bitbank",
    )

    # 価格データ拡張
    enhanced_data = engine.enhance_price_data(sample_data)
    logger.info(f"Enhanced data columns: {list(enhanced_data.columns)}")

    # サンプル取引実行
    sample_trades = [
        {
            "timestamp": pd.Timestamp("2024-03-15 10:00:00"),
            "entry_price": 7000000,
            "exit_price": 7200000,
            "side": "BUY",
            "amount": 0.1,
            "duration_bars": 24,
        },
        {
            "timestamp": pd.Timestamp("2024-05-03 14:00:00"),  # 憲法記念日
            "entry_price": 6800000,
            "exit_price": 6500000,
            "side": "BUY",
            "amount": 0.05,
            "duration_bars": 12,
        },
        {
            "timestamp": pd.Timestamp("2024-08-15 09:00:00"),
            "entry_price": 8000000,
            "exit_price": 8500000,
            "side": "BUY",
            "amount": 0.08,
            "duration_bars": 48,
        },
    ]

    # 取引実行
    for trade in sample_trades:
        jpy_trade = engine.execute_trade(
            trade["timestamp"],
            trade["entry_price"],
            trade["exit_price"],
            trade["side"],
            trade["amount"],
            trade["duration_bars"],
        )

        if jpy_trade:
            logger.info(f"Trade executed: {jpy_trade.side} {jpy_trade.size} BTC")
            logger.info(f"  Gross profit: {jpy_trade.gross_profit_jpy:,.0f} JPY")
            logger.info(f"  Tax amount: {jpy_trade.tax_amount_jpy:,.0f} JPY")
            logger.info(f"  Net profit: {jpy_trade.net_profit_jpy:,.0f} JPY")
            logger.info(f"  Holiday: {jpy_trade.is_japanese_holiday}")
            logger.info(f"  Activity score: {jpy_trade.market_activity_score:.2f}")

    # 統計情報計算
    stats = engine.calculate_jpy_statistics()
    logger.info("\n=== JPY建てバックテスト統計 ===")
    for key, value in stats.items():
        if isinstance(value, float):
            if "rate" in key or "score" in key:
                logger.info(f"{key}: {value:.1%}")
            else:
                logger.info(f"{key}: {value:,.2f}")
        else:
            logger.info(f"{key}: {value}")

    # 結果保存
    results_dir = project_root / "results"
    results_dir.mkdir(exist_ok=True)

    # 取引ログ保存
    engine.save_jpy_trade_log(str(results_dir / "jpy_demo_trades.csv"))

    # レポート生成
    engine.generate_jpy_report(str(results_dir / "jpy_demo_report.txt"))

    logger.info("JPY backtest demo completed successfully!")


def main():
    """メイン実行"""
    logger.info("Starting JPY Backtest Demo")

    try:
        # 日本市場特性デモ
        demo_japanese_market_features()

        # JPY建て計算機デモ
        demo_jpy_calculator()

        # JPY建てバックテストデモ
        demo_jpy_backtest()

        logger.info("All demos completed successfully!")

    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise


if __name__ == "__main__":
    main()

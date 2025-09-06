#!/usr/bin/env python3
"""
バックテスト実行スクリプト - Phase 19対応

独立したバックテスト実行環境を提供し、
本番設定に影響を与えずにバックテストを実行。

使用例:
    python scripts/backtest/run_backtest.py
    python scripts/backtest/run_backtest.py --days 60 --symbol BTC/JPY
    python scripts/backtest/run_backtest.py --config config/backtest/base.yaml --verbose
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# プロジェクトルートをsys.pathに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 必要なモジュールのインポート
from src.backtest.engine import BacktestEngine
from src.core.config import load_config
from src.core.logger import setup_logging


def parse_arguments():
    """コマンドライン引数の解析."""
    parser = argparse.ArgumentParser(
        description="Crypto-Bot バックテスト実行スクリプト",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python scripts/backtest/run_backtest.py                           # デフォルト90日間・50万円
  python scripts/backtest/run_backtest.py --days 60                 # 60日間
  python scripts/backtest/run_backtest.py --symbol ETH/JPY          # ETH/JPY対象
  python scripts/backtest/run_backtest.py --config custom.yaml      # カスタム設定
  python scripts/backtest/run_backtest.py --verbose                 # 詳細ログ
        """,
    )

    parser.add_argument(
        "--config",
        default="config/backtest/base.yaml",
        help="バックテスト設定ファイルパス (default: config/backtest/base.yaml)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=90,
        help="バックテスト期間（日数）(default: 90)",
    )
    parser.add_argument(
        "--symbol",
        default="BTC/JPY",
        help="取引対象シンボル (default: BTC/JPY)",
    )
    parser.add_argument(
        "--initial-balance",
        type=float,
        default=500000.0,
        help="初期残高（円）(default: 500000.0)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="詳細ログを表示",
    )

    return parser.parse_args()


async def run_backtest(args):
    """バックテストメイン実行."""
    try:
        print(f"🚀 Crypto-Bot バックテスト実行開始")
        print(f"📁 設定ファイル: {args.config}")
        print(f"📅 バックテスト期間: {args.days}日間")
        print(f"💱 対象シンボル: {args.symbol}")
        print(f"💰 初期残高: ¥{args.initial_balance:,.0f}")

        # 1. 設定読み込み
        try:
            config = load_config(args.config, cmdline_mode="backtest")
            print(f"✅ 設定読み込み完了: モード={config.mode}")
        except Exception as e:
            print(f"❌ 設定読み込みエラー: {e}")
            return False

        # 2. ロガー初期化
        logger = setup_logging("backtest")
        if args.verbose:
            # 詳細ログモードの場合はDEBUGレベルに設定
            import logging

            logging.getLogger().setLevel(logging.DEBUG)

        logger.info(f"🔧 バックテストエンジン初期化開始")

        # 3. BacktestEngine初期化
        engine = BacktestEngine(
            initial_balance=args.initial_balance,
            slippage_rate=0.0005,  # 0.05%
            commission_rate=0.0012,  # 0.12% (Bitbank手数料)
            max_position_ratio=0.05,  # 5%
            risk_profile="balanced",
        )

        logger.info(f"✅ BacktestEngine初期化完了")

        # 4. バックテスト期間設定
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.days)

        print(f"\n📊 バックテスト実行中...")
        print(f"   期間: {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}")
        print(f"   対象: {args.symbol}")

        # 5. バックテスト実行
        results = await engine.run_backtest(
            start_date=start_date, end_date=end_date, symbol=args.symbol
        )

        # 6. 結果表示
        print_backtest_results(results, args)

        return True

    except Exception as e:
        print(f"❌ バックテスト実行エラー: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return False


def print_backtest_results(results, args):
    """バックテスト結果の詳細表示."""
    print(f"\n{'=' * 60}")
    print(f"🎯 バックテスト結果サマリー")
    print(f"{'=' * 60}")

    # 基本統計
    total_trades = results.get("total_trades", 0)
    total_profit = results.get("total_profit", 0.0)
    win_rate = results.get("win_rate", 0.0) * 100
    max_drawdown = results.get("max_drawdown", 0.0) * 100
    final_balance = results.get("final_balance", args.initial_balance)
    return_rate = results.get("return_rate", 0.0) * 100

    print(f"📈 トレード統計:")
    print(f"   総取引数: {total_trades}回")
    print(f"   勝率: {win_rate:.1f}%")
    print(f"   総損益: ¥{total_profit:+,.0f}")

    print(f"\n💰 資産統計:")
    print(f"   初期残高: ¥{args.initial_balance:,.0f}")
    print(f"   最終残高: ¥{final_balance:,.0f}")
    print(f"   リターン: {return_rate:+.2f}%")
    print(f"   最大ドローダウン: {max_drawdown:.2f}%")

    # パフォーマンス評価
    print(f"\n📊 パフォーマンス評価:")
    if total_trades == 0:
        print(f"   ⚠️  取引が実行されませんでした")
        print(f"   🔍 考えられる原因:")
        print(f"      - データ不足")
        print(f"      - 戦略条件が厳しすぎる")
        print(f"      - MLモデル信頼度が低い")
        print(f"      - リスク管理による制限")
    else:
        avg_profit_per_trade = total_profit / total_trades if total_trades > 0 else 0
        print(f"   平均利益/取引: ¥{avg_profit_per_trade:+,.0f}")

        # 評価ランク
        if return_rate > 10:
            rank = "🏆 優秀"
        elif return_rate > 5:
            rank = "🥈 良好"
        elif return_rate > 0:
            rank = "🥉 普通"
        else:
            rank = "❌ 要改善"
        print(f"   総合評価: {rank}")

    # 取引履歴表示（最初の5件）
    trade_records = results.get("trade_records", [])
    if trade_records and len(trade_records) > 0:
        print(f"\n📋 取引履歴（最初の5件）:")
        for i, trade in enumerate(trade_records[:5]):
            entry_time = trade.entry_time.strftime("%m/%d %H:%M")
            exit_time = trade.exit_time.strftime("%m/%d %H:%M") if trade.exit_time else "未決済"
            profit = f"¥{trade.profit_jpy:+,.0f}" if hasattr(trade, "profit_jpy") else "N/A"
            print(f"   {i + 1}. {entry_time} -> {exit_time} | {trade.side.upper()} | {profit}")

    print(f"{'=' * 60}")


def main():
    """メイン実行関数."""
    args = parse_arguments()

    try:
        # 非同期実行
        success = asyncio.run(run_backtest(args))

        if success:
            print(f"\n✅ バックテスト実行完了")
            exit_code = 0
        else:
            print(f"\n❌ バックテスト実行失敗")
            exit_code = 1

    except KeyboardInterrupt:
        print(f"\n⏹️  ユーザーによって中断されました")
        exit_code = 2
    except Exception as e:
        print(f"\n💥 予期せぬエラー: {e}")
        exit_code = 3

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

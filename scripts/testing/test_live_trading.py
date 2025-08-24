#!/usr/bin/env python3
"""
Phase 9-2: 実取引テストスクリプト.

最小取引単位での安全な実取引テスト。
レガシーシステムの実証済み機能を活用した段階的テスト。

使用方法:
    python scripts/test_live_trading.py --mode single    # 単発注文テスト
    python scripts/test_live_trading.py --mode continuous # 連続取引テスト
    python scripts/test_live_trading.py --mode full      # 24時間連続テスト

実行前チェック:
    1. 環境変数 BITBANK_API_KEY, BITBANK_API_SECRET が設定済み
    2. Bitbank信用取引口座が有効
    3. Discord通知設定が完了.
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.core.config import load_config
    from src.core.logger import setup_logging
    from src.data.bitbank_client import BitbankClient
    from src.trading.executor import ExecutionMode, OrderExecutor
    from src.trading.risk import (
        IntegratedRiskManager,
        RiskDecision,
        TradeEvaluation,
    )
except ImportError as e:
    print(f"❌ 必要なモジュールのインポートに失敗: {e}")
    print("プロジェクトルートから実行してください。")
    sys.exit(1)


class LiveTradingTester:
    """実取引テスト実行クラス."""

    def __init__(self, config_path: str = "config/environments/live/production.yaml"):
        """初期化."""
        self.config = load_config(config_path)
        self.logger = setup_logging("live_trading_test")

        # コンポーネント初期化
        self.bitbank_client = None
        self.order_executor = None
        self.risk_manager = None

        # テスト結果記録
        self.test_results = []
        self.start_time = datetime.now()

    async def initialize(self) -> bool:
        """システム初期化."""
        try:
            self.logger.info("🚀 実取引テスト環境初期化開始")

            # 環境変数チェック
            api_key = os.getenv("BITBANK_API_KEY")
            api_secret = os.getenv("BITBANK_API_SECRET")

            if not api_key or not api_secret:
                self.logger.error(
                    "Bitbank API認証情報が設定されていません",
                    discord_notify=True,
                )
                return False

            # BitbankClient初期化
            self.bitbank_client = BitbankClient(
                api_key=api_key,
                api_secret=api_secret,
                leverage=1.0,  # テストは最小レバレッジ
            )

            # 接続テスト
            if not self.bitbank_client.test_connection():
                self.logger.error("Bitbank API接続テスト失敗", discord_notify=True)
                return False

            # 残高確認
            balance = self.bitbank_client.fetch_balance()
            available_jpy = balance.get("JPY", {}).get("free", 0)

            if available_jpy < 10000:  # 最低1万円必要
                self.logger.error(
                    f"残高不足: ¥{available_jpy:,.0f} < ¥10,000（最低必要額）",
                    discord_notify=True,
                )
                return False

            # OrderExecutor初期化（実取引モード）
            self.order_executor = OrderExecutor(
                mode=ExecutionMode.LIVE,
                initial_balance=available_jpy,
                enable_latency_monitoring=True,
                log_dir=project_root / "logs" / "trading",
            )

            # RiskManager初期化（保守的設定）
            test_risk_config = {
                "kelly_criterion": {
                    "max_position_ratio": 0.005,  # 最大0.5%（テスト用）
                    "safety_factor": 0.5,
                    "min_trades_for_kelly": 10,
                },
                "risk_thresholds": {
                    "min_ml_confidence": 0.7,  # 高信頼度のみ
                    "risk_threshold_deny": 0.6,  # 厳格
                    "risk_threshold_conditional": 0.4,
                },
            }

            self.risk_manager = IntegratedRiskManager(
                config=test_risk_config,
                initial_balance=available_jpy,
                enable_discord_notifications=True,
            )

            self.logger.info(
                f"✅ 実取引テスト環境初期化完了 - 利用可能残高: ¥{available_jpy:,.0f}",
                discord_notify=True,
            )

            return True

        except Exception as e:
            self.logger.error(f"初期化エラー: {e}", discord_notify=True)
            return False

    async def run_single_order_test(self) -> bool:
        """単発注文テスト."""
        try:
            self.logger.info("📊 単発注文テスト開始", discord_notify=True)

            # 現在価格取得
            ticker = self.bitbank_client.fetch_ticker("BTC/JPY")
            current_price = ticker["last"]

            # 最小注文サイズ（0.0001 BTC）でテスト評価作成
            test_evaluation = TradeEvaluation(
                decision=RiskDecision.APPROVED,
                side="buy",
                position_size=0.0001,  # 最小単位
                entry_price=current_price,
                stop_loss=current_price * 0.98,  # 2%損切り
                take_profit=current_price * 1.02,  # 2%利確
                risk_score=0.3,  # 低リスク
                confidence=0.8,
                recommended_action="buy",
                denial_reasons=[],
            )

            # 買い注文実行
            self.logger.info(f"買い注文実行: 0.0001 BTC @ ¥{current_price:,.0f}")
            buy_result = await self.order_executor.execute_trade(test_evaluation)

            if not buy_result.success:
                self.logger.error(f"買い注文失敗: {buy_result.error_message}")
                return False

            # 5秒待機後、売り注文実行
            await asyncio.sleep(5)

            test_evaluation_sell = TradeEvaluation(
                decision=RiskDecision.APPROVED,
                side="sell",
                position_size=0.0001,
                entry_price=current_price,
                stop_loss=None,
                take_profit=None,
                risk_score=0.3,
                confidence=0.8,
                recommended_action="sell",
                denial_reasons=[],
            )

            self.logger.info("売り注文実行: 0.0001 BTC")
            sell_result = await self.order_executor.execute_trade(test_evaluation_sell)

            if not sell_result.success:
                self.logger.error(f"売り注文失敗: {sell_result.error_message}")
                return False

            # 結果記録
            test_result = {
                "test_type": "single_order",
                "timestamp": datetime.now().isoformat(),
                "buy_order": buy_result.__dict__,
                "sell_order": sell_result.__dict__,
                "success": True,
            }

            self.test_results.append(test_result)

            self.logger.info(
                f"✅ 単発注文テスト完了 - "
                f"買い: {buy_result.order_id}, 売り: {sell_result.order_id}",
                discord_notify=True,
            )

            return True

        except Exception as e:
            self.logger.error(f"単発注文テストエラー: {e}", discord_notify=True)
            return False

    async def run_continuous_test(self, duration_hours: int = 4) -> bool:
        """連続取引テスト."""
        try:
            self.logger.info(
                f"🔄 連続取引テスト開始（{duration_hours}時間）",
                discord_notify=True,
            )

            end_time = datetime.now() + timedelta(hours=duration_hours)
            cycle_count = 0
            success_count = 0

            while datetime.now() < end_time:
                cycle_count += 1
                self.logger.info(f"取引サイクル {cycle_count} 開始")

                try:
                    # 単発注文テスト実行
                    if await self.run_single_order_test():
                        success_count += 1

                    # 取引統計出力
                    self.order_executor.get_trading_statistics()
                    success_rate = success_count / cycle_count * 100
                    self.logger.info(
                        f"サイクル {cycle_count} 完了 - "
                        f"成功率: {success_count}/{cycle_count} "
                        f"({success_rate:.1f}%)"
                    )

                    # 20分間隔（1日最大72回）
                    await asyncio.sleep(20 * 60)

                except KeyboardInterrupt:
                    self.logger.info("ユーザーによる中断要求")
                    break
                except Exception as e:
                    self.logger.error(f"サイクル {cycle_count} エラー: {e}")
                    await asyncio.sleep(60)  # エラー時は1分待機

            # 最終結果
            self.order_executor.get_trading_statistics()
            final_success_rate = success_count / cycle_count * 100
            self.logger.info(
                f"✅ 連続取引テスト完了 - サイクル: {cycle_count}, "
                f"成功: {success_count}, 成功率: {final_success_rate:.1f}%",
                discord_notify=True,
            )

            return success_count > 0

        except Exception as e:
            self.logger.error(f"連続取引テストエラー: {e}", discord_notify=True)
            return False

    async def run_24h_monitoring_test(self) -> bool:
        """手動実行監視テスト."""
        try:
            self.logger.info("⏰ 手動実行監視テスト開始", discord_notify=True)

            # 1時間ごとに健康状態チェック
            for hour in range(24):
                self.logger.info(f"24時間テスト - {hour + 1}/24時間経過")

                try:
                    # API接続確認
                    if not self.bitbank_client.test_connection():
                        self.logger.warning("API接続不安定")

                    # 残高確認
                    balance = self.bitbank_client.fetch_balance()
                    available_jpy = balance.get("JPY", {}).get("free", 0)

                    # 統計出力
                    stats = self.order_executor.get_trading_statistics()

                    self.logger.info(
                        f"時間 {hour + 1}: 残高 ¥{available_jpy:,.0f}, "
                        f"総取引回数: {stats.get('total_trades', 0)}"
                    )

                    # 12時間と24時間にDiscord通知
                    if hour + 1 in [12, 24]:
                        self.logger.info(
                            f"📊 24時間テスト中間報告 ({hour + 1}時間経過)",
                            discord_notify=True,
                        )

                    await asyncio.sleep(3600)  # 1時間待機

                except KeyboardInterrupt:
                    self.logger.info("ユーザーによる中断要求")
                    break
                except Exception as e:
                    self.logger.error(f"監視テストエラー（{hour + 1}時間目）: {e}")
                    await asyncio.sleep(60)

            self.logger.info("✅ 手動実行監視テスト完了", discord_notify=True)
            return True

        except Exception as e:
            self.logger.error(f"手動実行監視テストエラー: {e}", discord_notify=True)
            return False

    def save_test_results(self):
        """テスト結果保存."""
        try:
            import json

            results_dir = project_root / "logs" / "test_results"
            results_dir.mkdir(parents=True, exist_ok=True)

            timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
            results_file = results_dir / f"live_trading_test_{timestamp}.json"

            duration_minutes = (datetime.now() - self.start_time).total_seconds() / 60
            test_summary = {
                "start_time": self.start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "duration_minutes": duration_minutes,
                "test_count": len(self.test_results),
                "results": self.test_results,
            }

            with open(results_file, "w", encoding="utf-8") as f:
                json.dump(test_summary, f, indent=2, ensure_ascii=False)

            self.logger.info(f"テスト結果保存: {results_file}")

        except Exception as e:
            self.logger.error(f"テスト結果保存エラー: {e}")


async def main():
    """メイン処理."""
    parser = argparse.ArgumentParser(
        description="Phase 9-2: 実取引テストスクリプト",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python scripts/test_live_trading.py --mode single
  python scripts/test_live_trading.py --mode continuous --duration 2
  python scripts/test_live_trading.py --mode monitoring.
        """,
    )

    parser.add_argument(
        "--mode",
        choices=["single", "continuous", "monitoring"],
        default="single",
        help="テストモード (default: single)",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=4,
        help="連続テスト時間（時間） (default: 4)",
    )
    parser.add_argument(
        "--config",
        default="config/environments/live/production.yaml",
        help="設定ファイル (default: config/environments/live/production.yaml)",
    )

    args = parser.parse_args()

    # テスター初期化
    tester = LiveTradingTester(args.config)

    try:
        # 初期化
        if not await tester.initialize():
            print("❌ 初期化失敗")
            sys.exit(1)

        # テスト実行
        success = False

        if args.mode == "single":
            success = await tester.run_single_order_test()
        elif args.mode == "continuous":
            success = await tester.run_continuous_test(args.duration)
        elif args.mode == "monitoring":
            success = await tester.run_24h_monitoring_test()

        # 結果保存
        tester.save_test_results()

        if success:
            print("✅ テスト完了")
            sys.exit(0)
        else:
            print("❌ テスト失敗")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n⚠️ テスト中断")
        tester.save_test_results()
        sys.exit(130)
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Phase 2.2: シンプル実行フロー構築
CSV読込→97特徴量生成→ML予測→取引実行

完全なパイプライン実装:
1. CSV読込（data/btc_usd_2024_hourly.csv）
2. 97特徴量生成（production.yml準拠）
3. ML予測（アンサンブル学習対応）
4. 取引シグナル生成
5. 取引実行シミュレーション

5-10分以内実行・軽量化・高速処理最適化
"""

import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import yaml

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# HybridBacktestEngineインポート
try:
    from scripts.hybrid_backtest_approach import FEATURE_97_LIST, HybridBacktest

    logger.info("✅ HybridBacktestEngine successfully imported")
except ImportError as e:
    logger.error(f"❌ HybridBacktestEngine import failed: {e}")
    sys.exit(1)


class Simple97FeatureFlow:
    """
    Phase 2.2: シンプル実行フロー
    CSV→97特徴量→ML→取引の完全パイプライン
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.config = None
        self.data = None
        self.features_df = None
        self.signals_df = None
        self.results = {}

        logger.info("🚀 Simple97FeatureFlow initialized")

        # 設定読み込み
        if config_path:
            self.load_config()

    def load_config(self) -> bool:
        """設定ファイル読み込み"""
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = yaml.safe_load(f)
            logger.info(f"✅ Config loaded: {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"❌ Config load failed: {e}")
            return False

    def step1_load_csv_data(
        self, csv_path: str = "data/btc_usd_2024_hourly.csv"
    ) -> bool:
        """Step 1: CSV読込"""
        logger.info("📊 Step 1: CSV読込開始...")
        start_time = time.time()

        csv_path = Path(csv_path)

        if csv_path.exists():
            try:
                self.data = pd.read_csv(csv_path)

                # タイムスタンプ処理
                if "timestamp" in self.data.columns:
                    self.data["timestamp"] = pd.to_datetime(self.data["timestamp"])
                    self.data = self.data.set_index("timestamp")
                elif "datetime" in self.data.columns:
                    self.data["datetime"] = pd.to_datetime(self.data["datetime"])
                    self.data = self.data.set_index("datetime")

                # 軽量化: 最新1000件
                self.data = self.data.tail(1000)

                # 必要列確認
                required_cols = ["open", "high", "low", "close", "volume"]
                missing_cols = [
                    col for col in required_cols if col not in self.data.columns
                ]

                if missing_cols:
                    logger.error(f"❌ Missing columns: {missing_cols}")
                    return False

                execution_time = time.time() - start_time
                logger.info(f"✅ Step 1 completed in {execution_time:.2f}s")
                logger.info(
                    f"📈 Data loaded: {len(self.data)} records ({self.data.index[0]} to {self.data.index[-1]})"
                )

                return True

            except Exception as e:
                logger.error(f"❌ CSV load failed: {e}")
                return False
        else:
            logger.warning("⚠️ CSV file not found - generating sample data")
            return self.generate_sample_data()

    def generate_sample_data(self) -> bool:
        """サンプルデータ生成（CSVファイルがない場合）"""
        logger.info("🔧 Generating sample BTC/JPY data...")

        try:
            dates = pd.date_range("2024-01-01", periods=1000, freq="H")
            np.random.seed(42)

            # リアルなBTC価格シミュレーション
            initial_price = 50000 * 150  # BTC/JPY (1BTC = 50,000 USD × 150 JPY/USD)
            price = initial_price
            data = []

            for i, date in enumerate(dates):
                # 価格変動（ランダムウォーク + トレンド）
                trend = 0.001 if i % 100 < 60 else -0.001  # 60%上昇、40%下降
                volatility = np.random.normal(0, 0.02)  # 2%のボラティリティ
                price_change = price * (trend + volatility)
                price += price_change

                # OHLC生成
                high_var = abs(np.random.normal(0, 0.01))
                low_var = abs(np.random.normal(0, 0.01))
                open_price = price + np.random.normal(0, price * 0.005)
                high_price = max(open_price, price) + (price * high_var)
                low_price = min(open_price, price) - (price * low_var)
                close_price = price

                # 出来高生成（価格変動と相関）
                volume_base = 100
                volume_volatility = abs(price_change / price) * 500
                volume = max(
                    10, volume_base + volume_volatility + np.random.uniform(0, 50)
                )

                data.append(
                    {
                        "open": round(open_price, 2),
                        "high": round(high_price, 2),
                        "low": round(low_price, 2),
                        "close": round(close_price, 2),
                        "volume": round(volume, 4),
                    }
                )

            self.data = pd.DataFrame(data, index=dates)
            logger.info("✅ Sample data generated: 1000 BTC/JPY records")
            return True

        except Exception as e:
            logger.error(f"❌ Sample data generation failed: {e}")
            return False

    def step2_generate_97_features(self) -> bool:
        """Step 2: 97特徴量生成"""
        logger.info("🔧 Step 2: 97特徴量生成開始...")
        start_time = time.time()

        try:
            # HybridBacktestEngineを使用して97特徴量生成
            backtest_engine = HybridBacktest(phase="B")
            self.features_df = backtest_engine.add_97_features(self.data.copy())

            # 特徴量数確認
            feature_cols = [
                col
                for col in self.features_df.columns
                if col not in ["open", "high", "low", "close", "volume"]
            ]

            execution_time = time.time() - start_time
            logger.info(f"✅ Step 2 completed in {execution_time:.2f}s")
            logger.info(f"📊 Generated {len(feature_cols)} features")

            # 97特徴量リストとの整合性確認
            missing_features = []
            for feature in FEATURE_97_LIST:
                if feature not in self.features_df.columns:
                    missing_features.append(feature)

            if missing_features:
                logger.warning(f"⚠️ Missing features: {len(missing_features)}")
                logger.debug(f"Missing: {missing_features}")
            else:
                logger.info("✅ All 97 features successfully generated")

            return True

        except Exception as e:
            logger.error(f"❌ Feature generation failed: {e}")
            return False

    def step3_ml_prediction(self) -> bool:
        """Step 3: ML予測"""
        logger.info("🤖 Step 3: ML予測開始...")
        start_time = time.time()

        try:
            # HybridBacktestEngineを使用してML予測実行
            backtest_engine = HybridBacktest(phase="B", config_path=self.config_path)

            # MLモデル読み込み試行
            ml_loaded = backtest_engine.load_ml_model()

            if ml_loaded:
                logger.info("✅ ML model loaded - generating ML predictions")
                self.signals_df = backtest_engine.generate_signals_ml_97(
                    self.features_df.copy()
                )
            else:
                logger.info(
                    "⚠️ ML model not available - using enhanced technical analysis"
                )
                self.signals_df = backtest_engine.generate_enhanced_technical_signals(
                    self.features_df.copy()
                )

            # シグナル統計
            signals = self.signals_df["signal"]
            buy_signals = len(signals[signals == 1])
            sell_signals = len(signals[signals == -1])
            no_signals = len(signals[signals == 0])

            execution_time = time.time() - start_time
            logger.info(f"✅ Step 3 completed in {execution_time:.2f}s")
            logger.info(
                f"📈 Signals generated - BUY: {buy_signals}, SELL: {sell_signals}, HOLD: {no_signals}"
            )

            return True

        except Exception as e:
            logger.error(f"❌ ML prediction failed: {e}")
            return False

    def step4_trade_execution_simulation(self) -> bool:
        """Step 4: 取引実行シミュレーション"""
        logger.info("💰 Step 4: 取引実行シミュレーション開始...")
        start_time = time.time()

        try:
            # 初期設定
            initial_balance = 10000.0  # 初期資金1万円
            balance = initial_balance
            position = 0  # 0: ニュートラル, 1: ロング, -1: ショート
            position_size = 0
            entry_price = 0
            trades = []

            # シミュレーション実行
            for index, row in self.signals_df.iterrows():
                signal = row["signal"]
                current_price = row["close"]

                if pd.isna(signal) or signal == 0:
                    continue

                # BUYシグナル
                if signal == 1 and position != 1:
                    # 既存ポジション決済
                    if position == -1:
                        pnl = (entry_price - current_price) * position_size
                        balance += pnl
                        trades.append(
                            {
                                "timestamp": index,
                                "action": "CLOSE_SHORT",
                                "price": current_price,
                                "pnl": pnl,
                                "balance": balance,
                            }
                        )

                    # 新ポジション
                    position_size = balance * 0.95 / current_price  # 95%の資金を投入
                    entry_price = current_price
                    position = 1

                    trades.append(
                        {
                            "timestamp": index,
                            "action": "BUY",
                            "price": current_price,
                            "size": position_size,
                            "balance": balance,
                        }
                    )

                # SELLシグナル
                elif signal == -1 and position != -1:
                    # 既存ポジション決済
                    if position == 1:
                        pnl = (current_price - entry_price) * position_size
                        balance += pnl
                        trades.append(
                            {
                                "timestamp": index,
                                "action": "CLOSE_LONG",
                                "price": current_price,
                                "pnl": pnl,
                                "balance": balance,
                            }
                        )

                    # 新ポジション（ショート）
                    position_size = balance * 0.95 / current_price
                    entry_price = current_price
                    position = -1

                    trades.append(
                        {
                            "timestamp": index,
                            "action": "SELL",
                            "price": current_price,
                            "size": position_size,
                            "balance": balance,
                        }
                    )

            # 最終決済
            if position != 0:
                final_price = self.signals_df.iloc[-1]["close"]
                if position == 1:
                    pnl = (final_price - entry_price) * position_size
                elif position == -1:
                    pnl = (entry_price - final_price) * position_size
                balance += pnl

                trades.append(
                    {
                        "timestamp": self.signals_df.index[-1],
                        "action": "FINAL_CLOSE",
                        "price": final_price,
                        "pnl": pnl,
                        "balance": balance,
                    }
                )

            # 結果統計
            total_return = (balance - initial_balance) / initial_balance * 100
            num_trades = len(trades)

            self.results = {
                "initial_balance": initial_balance,
                "final_balance": balance,
                "total_return_pct": total_return,
                "num_trades": num_trades,
                "trades": trades,
            }

            execution_time = time.time() - start_time
            logger.info(f"✅ Step 4 completed in {execution_time:.2f}s")
            logger.info(f"💰 Final balance: ¥{balance:,.2f}")
            logger.info(f"📊 Total return: {total_return:+.2f}%")
            logger.info(f"🔄 Total trades: {num_trades}")

            return True

        except Exception as e:
            logger.error(f"❌ Trade execution simulation failed: {e}")
            return False

    def execute_complete_flow(
        self, csv_path: str = "data/btc_usd_2024_hourly.csv"
    ) -> Dict[str, Any]:
        """完全フロー実行"""
        logger.info("🚀 Phase 2.2: Simple 97-Feature Flow - 完全実行開始")
        logger.info("=" * 80)

        total_start_time = time.time()

        # Step 1: CSV読込
        if not self.step1_load_csv_data(csv_path):
            logger.error("❌ Step 1 failed - aborting flow")
            return {}

        # Step 2: 97特徴量生成
        if not self.step2_generate_97_features():
            logger.error("❌ Step 2 failed - aborting flow")
            return {}

        # Step 3: ML予測
        if not self.step3_ml_prediction():
            logger.error("❌ Step 3 failed - aborting flow")
            return {}

        # Step 4: 取引実行シミュレーション
        if not self.step4_trade_execution_simulation():
            logger.error("❌ Step 4 failed - aborting flow")
            return {}

        total_execution_time = time.time() - total_start_time

        # 完了レポート
        logger.info("=" * 80)
        logger.info("🎊 Phase 2.2: Complete Flow 実行完了!")
        logger.info("=" * 80)
        logger.info(f"⏱️ Total execution time: {total_execution_time:.2f} seconds")
        logger.info(f"💰 Final balance: ¥{self.results['final_balance']:,.2f}")
        logger.info(f"📊 Total return: {self.results['total_return_pct']:+.2f}%")
        logger.info(f"🔄 Total trades: {self.results['num_trades']}")

        # 5-10分以内目標達成確認
        if total_execution_time <= 300:  # 5分
            logger.info("🎯 ✅ 5分以内実行達成!")
        elif total_execution_time <= 600:  # 10分
            logger.info("🎯 ✅ 10分以内実行達成!")
        else:
            logger.warning(
                f"⚠️ 実行時間超過: {total_execution_time:.2f}s (目標: 10分以内)"
            )

        # 次ステップ推奨
        logger.info("🔄 Next: Phase 3.1 - feature_names mismatch解決")

        return self.results


def main():
    """メイン実行関数"""
    print("🚀 Phase 2.2: Simple 97-Feature Flow")
    print("CSV→97特徴量→ML予測→取引実行の完全パイプライン")
    print("=" * 80)

    # 設定ファイルパス
    config_path = "config/validation/production_97_backtest.yml"

    # フロー実行
    flow = Simple97FeatureFlow(config_path=config_path)
    results = flow.execute_complete_flow()

    if results:
        print(f"\n🎊 Phase 2.2完了: シンプル実行フロー構築成功!")
        print(f"✅ CSV読込→97特徴量→ML予測→取引実行パイプライン完成")
        return True
    else:
        print(f"\n❌ Phase 2.2失敗: 問題が発生しました")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

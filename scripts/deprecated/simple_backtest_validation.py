#!/usr/bin/env python3
"""
シンプルバックテスト検証スクリプト
bitbank-botters-labo方式を参考にした軽量バックテスト実装

目的:
1. 現在の複雑なバックテストの代替案検証
2. 5分以内での実行完了
3. 基本的なML戦略での収益性確認
4. デバッグしやすい簡潔な実装
"""

import logging
import pickle
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SimpleBacktest:
    """
    bitbank-botters-labo方式を参考にしたシンプルバックテスト
    複雑な外部データ・ウォークフォワードなしの軽量版
    """

    def __init__(self, initial_balance=10000, commission=0.0012):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.commission = commission
        self.position = 0  # 0: 現金, 1: BUY, -1: SELL
        self.entry_price = 0
        self.trades = []
        self.equity_curve = []

    def add_indicators(self, df):
        """基本的なテクニカル指標追加（軽量版）"""
        logger.info("Adding basic technical indicators...")

        # 移動平均
        df["sma_20"] = df["close"].rolling(20).mean()
        df["sma_50"] = df["close"].rolling(50).mean()
        df["ema_12"] = df["close"].ewm(span=12).mean()
        df["ema_26"] = df["close"].ewm(span=26).mean()

        # RSI
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = -delta.where(delta < 0, 0).rolling(14).mean()
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))

        # MACD
        df["macd"] = df["ema_12"] - df["ema_26"]
        df["macd_signal"] = df["macd"].ewm(span=9).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]

        # ボリンジャーバンド
        df["bb_middle"] = df["close"].rolling(20).mean()
        df["bb_std"] = df["close"].rolling(20).std()
        df["bb_upper"] = df["bb_middle"] + (df["bb_std"] * 2)
        df["bb_lower"] = df["bb_middle"] - (df["bb_std"] * 2)

        # ATR
        df["tr"] = np.maximum(
            df["high"] - df["low"],
            np.maximum(
                abs(df["high"] - df["close"].shift(1)),
                abs(df["low"] - df["close"].shift(1)),
            ),
        )
        df["atr"] = df["tr"].rolling(14).mean()

        # 価格位置
        df["price_position"] = (df["close"] - df["bb_lower"]) / (
            df["bb_upper"] - df["bb_lower"]
        )

        # トレンド判定
        df["trend"] = np.where(df["sma_20"] > df["sma_50"], 1, -1)

        logger.info(f"Added indicators: {df.shape[1]} columns")
        return df

    def generate_signals(self, df):
        """シンプルなトレードシグナル生成"""
        logger.info("Generating trade signals...")

        # BUYシグナル: RSI < 30 & 価格がボリンジャー下限近く & 上昇トレンド
        buy_condition = (
            (df["rsi"] < 30)
            & (df["price_position"] < 0.2)
            & (df["trend"] == 1)
            & (df["macd"] > df["macd_signal"])
        )

        # SELLシグナル: RSI > 70 & 価格がボリンジャー上限近く & 下降トレンド
        sell_condition = (
            (df["rsi"] > 70)
            & (df["price_position"] > 0.8)
            & (df["trend"] == -1)
            & (df["macd"] < df["macd_signal"])
        )

        df["signal"] = 0
        df.loc[buy_condition, "signal"] = 1
        df.loc[sell_condition, "signal"] = -1

        signal_count = len(df[df["signal"] != 0])
        logger.info(
            f"Generated {signal_count} signals ({len(df[df['signal'] == 1])} BUY, {len(df[df['signal'] == -1])} SELL)"
        )

        return df

    def execute_trade(self, row, index):
        """トレード実行"""
        signal = row["signal"]
        price = row["close"]

        if signal == 1 and self.position <= 0:  # BUY
            if self.position == -1:  # SELLポジション決済
                pnl = (self.entry_price - price) * abs(self.balance / self.entry_price)
                commission_cost = abs(self.balance) * self.commission
                self.balance += pnl - commission_cost

            # BUYポジション
            commission_cost = self.balance * self.commission
            self.balance -= commission_cost
            self.position = 1
            self.entry_price = price

            self.trades.append(
                {
                    "timestamp": index,
                    "action": "BUY",
                    "price": price,
                    "balance": self.balance,
                    "position": self.position,
                }
            )

        elif signal == -1 and self.position >= 0:  # SELL
            if self.position == 1:  # BUYポジション決済
                pnl = (price - self.entry_price) * (self.balance / self.entry_price)
                commission_cost = abs(self.balance) * self.commission
                self.balance += pnl - commission_cost

            # SELLポジション
            commission_cost = self.balance * self.commission
            self.balance -= commission_cost
            self.position = -1
            self.entry_price = price

            self.trades.append(
                {
                    "timestamp": index,
                    "action": "SELL",
                    "price": price,
                    "balance": self.balance,
                    "position": self.position,
                }
            )

    def run_backtest(self, df):
        """バックテスト実行"""
        logger.info("Starting simple backtest...")
        start_time = time.time()

        # 指標追加
        df = self.add_indicators(df)

        # シグナル生成
        df = self.generate_signals(df)

        # トレード実行
        for index, row in df.iterrows():
            self.execute_trade(row, index)

            # 現在の評価額計算
            current_value = self.balance
            if self.position != 0:
                if self.position == 1:  # BUY
                    current_value = self.balance * (row["close"] / self.entry_price)
                else:  # SELL
                    current_value = self.balance + (
                        self.entry_price - row["close"]
                    ) * abs(self.balance / self.entry_price)

            self.equity_curve.append(
                {
                    "timestamp": index,
                    "balance": current_value,
                    "position": self.position,
                }
            )

        # 最終決済
        if self.position != 0:
            final_price = df.iloc[-1]["close"]
            if self.position == 1:
                pnl = (final_price - self.entry_price) * (
                    self.balance / self.entry_price
                )
            else:
                pnl = (self.entry_price - final_price) * abs(
                    self.balance / self.entry_price
                )

            commission_cost = abs(self.balance) * self.commission
            self.balance += pnl - commission_cost
            self.position = 0

        execution_time = time.time() - start_time
        logger.info(f"Backtest completed in {execution_time:.2f} seconds")

        return self.calculate_performance()

    def calculate_performance(self):
        """パフォーマンス計算"""
        total_return = (
            (self.balance - self.initial_balance) / self.initial_balance * 100
        )
        num_trades = len(self.trades)

        # 勝率計算
        winning_trades = 0
        if len(self.trades) >= 2:
            for i in range(1, len(self.trades)):
                if self.trades[i]["balance"] > self.trades[i - 1]["balance"]:
                    winning_trades += 1

        win_rate = (
            (winning_trades / max(num_trades - 1, 1)) * 100 if num_trades > 1 else 0
        )

        # Equity curve DataFrame
        equity_df = pd.DataFrame(self.equity_curve)
        if len(equity_df) > 0:
            max_balance = equity_df["balance"].max()
            min_balance = equity_df["balance"].min()
            max_drawdown = (max_balance - min_balance) / max_balance * 100
        else:
            max_drawdown = 0

        return {
            "initial_balance": self.initial_balance,
            "final_balance": self.balance,
            "total_return_pct": total_return,
            "num_trades": num_trades,
            "win_rate_pct": win_rate,
            "max_drawdown_pct": max_drawdown,
            "trades": self.trades,
            "equity_curve": equity_df,
        }


def load_sample_data():
    """サンプルデータ読み込み（CSV or 生成）"""
    csv_path = Path("data/btc_usd_2024_hourly.csv")

    if csv_path.exists():
        logger.info(f"Loading data from {csv_path}")
        df = pd.read_csv(csv_path)

        # 列名標準化
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.set_index("timestamp")

        # 必要な列を確認
        required_cols = ["open", "high", "low", "close", "volume"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            logger.warning(f"Missing columns: {missing_cols}")

        # データサイズ制限（高速化のため）
        if len(df) > 2000:
            df = df.tail(2000)  # 最新2000件のみ
            logger.info(f"Limited to {len(df)} records for performance")

        return df
    else:
        logger.warning("CSV file not found, generating sample data")
        # サンプルデータ生成
        dates = pd.date_range("2024-01-01", periods=1000, freq="1H")
        np.random.seed(42)

        # ランダムウォーク価格生成
        price_changes = np.random.normal(0, 0.02, 1000)
        prices = 50000 * np.cumprod(1 + price_changes)

        df = pd.DataFrame(
            {
                "open": prices * (1 + np.random.normal(0, 0.001, 1000)),
                "high": prices * (1 + abs(np.random.normal(0, 0.01, 1000))),
                "low": prices * (1 - abs(np.random.normal(0, 0.01, 1000))),
                "close": prices,
                "volume": np.random.lognormal(10, 1, 1000),
            },
            index=dates,
        )

        return df


def compare_with_ml_model():
    """MLモデルとの比較（可能な場合）"""
    logger.info("Attempting to compare with ML model predictions...")

    try:
        model_path = Path("models/production/xgb_97_features.pkl")
        if model_path.exists():
            with open(model_path, "rb") as f:
                model = pickle.load(f)
            logger.info("ML model loaded successfully")
            return True
        else:
            logger.info("ML model not found, skipping comparison")
            return False
    except Exception as e:
        logger.warning(f"Failed to load ML model: {e}")
        return False


def main():
    """メイン実行"""
    print("🚀 シンプルバックテスト検証スクリプト")
    print("=" * 60)

    try:
        # データ読み込み
        df = load_sample_data()
        logger.info(f"Data loaded: {len(df)} records, {df.shape[1]} columns")
        print(f"📊 データ期間: {df.index[0]} ~ {df.index[-1]}")
        print(f"📊 データ件数: {len(df)} 件")

        # バックテスト実行
        backtest = SimpleBacktest(initial_balance=10000, commission=0.0012)
        results = backtest.run_backtest(df.copy())

        # 結果表示
        print("\n" + "=" * 60)
        print("📈 バックテスト結果")
        print("=" * 60)
        print(f"💰 初期資金: ¥{results['initial_balance']:,.0f}")
        print(f"💰 最終資金: ¥{results['final_balance']:,.0f}")
        print(f"📊 総リターン: {results['total_return_pct']:+.2f}%")
        print(f"🔄 取引回数: {results['num_trades']} 回")
        print(f"🎯 勝率: {results['win_rate_pct']:.1f}%")
        print(f"📉 最大ドローダウン: {results['max_drawdown_pct']:.2f}%")

        # MLモデル比較
        ml_available = compare_with_ml_model()

        print("\n" + "=" * 60)
        print("🎯 検証結果・推奨方向")
        print("=" * 60)

        if results["total_return_pct"] > 0:
            print("✅ シンプル戦略でプラス収益達成")
        else:
            print("❌ シンプル戦略では損失")

        if results["num_trades"] > 10:
            print("✅ 適切な取引頻度")
        else:
            print("⚠️ 取引頻度が少ない")

        print(f"\n🚀 bitbank-botters-labo方式の利点:")
        print(f"   ⚡ 高速実行（数秒で完了）")
        print(f"   🐛 デバッグ容易")
        print(f"   🔧 シンプルな実装")
        print(f"   📊 基本的な収益性確認")

        if ml_available:
            print(f"\n🤖 現在のML方式の利点:")
            print(f"   🎯 高精度予測")
            print(f"   📈 97特徴量活用")
            print(f"   🔄 アンサンブル学習")

        print(f"\n💡 推奨方向:")
        print(f"   1. シンプル版で基本動作確認")
        print(f"   2. 段階的に特徴量・複雑性追加")
        print(f"   3. タイムアウト問題解決後にフル機能")

        return results

    except Exception as e:
        logger.error(f"バックテスト実行エラー: {e}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    results = main()

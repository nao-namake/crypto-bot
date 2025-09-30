"""
もちぽよアラート戦略のテスト

リファクタリング後の戦略が正しく動作することを確認。
共通モジュール統合の効果も検証。.
"""

import os
import sys
import unittest
from datetime import datetime

import numpy as np
import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../"))

from src.strategies.implementations.mochipoy_alert import MochipoyAlertStrategy
from src.strategies.utils import EntryAction


class TestMochipoyAlertStrategy(unittest.TestCase):
    """もちぽよアラート戦略テストクラス."""

    def setUp(self):
        """テスト前準備."""
        # テスト用データ作成（1時間足想定）
        dates = pd.date_range(start="2025-08-01", periods=100, freq="1h")

        # 上昇トレンドのテストデータ
        prices = np.linspace(10000000, 11000000, 100)  # 1000万円から1100万円へ

        self.test_df = pd.DataFrame(
            {
                "timestamp": dates,
                "close": prices,
                "volume": np.random.uniform(100, 200, 100),
                "ema_20": prices - 50000,  # 20EMAは価格の少し下
                "ema_50": prices - 100000,  # 50EMAはさらに下（上昇トレンド）
                "macd": np.linspace(-10000, 50000, 100),  # MACDは徐々にポジティブへ
                "atr_14": np.full(100, 500000),  # ATR 50万円
            }
        )

        # 戦略インスタンス
        self.strategy = MochipoyAlertStrategy()

    def test_strategy_initialization(self):
        """戦略初期化テスト."""
        # デフォルト設定確認
        self.assertEqual(self.strategy.name, "MochipoyAlert")
        self.assertEqual(self.strategy.config["rci_period"], 14)
        self.assertEqual(self.strategy.config["rci_overbought"], 80)
        self.assertEqual(self.strategy.config["rci_oversold"], -80)
        self.assertEqual(self.strategy.config["min_confidence"], 0.4)

        # カスタム設定での初期化
        custom_config = {"rci_period": 20, "min_confidence": 0.5}
        custom_strategy = MochipoyAlertStrategy(config=custom_config)
        self.assertEqual(custom_strategy.config["rci_period"], 20)
        self.assertEqual(custom_strategy.config["min_confidence"], 0.5)

    def test_analyze_ema_trend_up(self):
        """EMAトレンド分析テスト - 上昇トレンド."""
        # EMA20 > EMA50 のケース
        signal = self.strategy._analyze_ema_trend(self.test_df)
        self.assertEqual(signal, 1)  # 買いシグナル

    def test_analyze_ema_trend_down(self):
        """EMAトレンド分析テスト - 下降トレンド."""
        # EMA20 < EMA50 のケース（下降トレンド）
        down_df = self.test_df.copy()
        down_df["ema_20"] = down_df["close"] - 100000  # 価格より下
        down_df["ema_50"] = down_df["close"] - 50000  # 20EMAより上（下降トレンド）

        signal = self.strategy._analyze_ema_trend(down_df)
        self.assertEqual(signal, -1)  # 売りシグナル

    def test_analyze_macd_momentum_positive(self):
        """MACDモメンタム分析テスト - ポジティブ."""
        # 最後のMACDがポジティブ
        signal = self.strategy._analyze_macd_momentum(self.test_df)
        self.assertEqual(signal, 1)  # 買いシグナル

    def test_analyze_macd_momentum_negative(self):
        """MACDモメンタム分析テスト - ネガティブ."""
        neg_df = self.test_df.copy()
        neg_df["macd"] = -50000  # ネガティブ値

        signal = self.strategy._analyze_macd_momentum(neg_df)
        self.assertEqual(signal, -1)  # 売りシグナル

    def test_calculate_rci(self):
        """RCI計算テスト."""
        # シンプルな価格データでテスト
        prices = pd.Series(
            [100, 102, 101, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114]
        )
        rci_values = self.strategy._calculate_rci(prices, period=14)

        # 最後の値が計算されていることを確認
        self.assertIsNotNone(rci_values.iloc[-1])

        # 上昇トレンドなのでRCIは高めになるはず
        self.assertGreater(rci_values.iloc[-1], 0)

    def test_analyze_rci_reversal(self):
        """RCI反転分析テスト."""
        # RCIは内部で計算されるので、実際の動作をテスト
        signal = self.strategy._analyze_rci_reversal(self.test_df)

        # シグナルが -1, 0, 1 のいずれかであることを確認
        self.assertIn(signal, [-1, 0, 1])

    def test_make_simple_decision_buy(self):
        """多数決判定テスト - 買い判定."""
        # テスト用のダミーDataFrame作成
        test_df = pd.DataFrame(
            {"close": [100, 101, 102], "atr_14": [1.0, 1.1, 1.2], "volume": [1000, 1100, 1200]}
        )
        # 2つ以上が買いシグナル
        decision = self.strategy._make_simple_decision(
            ema_signal=1, macd_signal=1, rci_signal=0, df=test_df
        )

        self.assertEqual(decision["action"], EntryAction.BUY)
        self.assertGreaterEqual(decision["confidence"], 0.6)
        self.assertEqual(decision["votes"]["buy"], 2)
        self.assertEqual(decision["votes"]["sell"], 0)
        self.assertEqual(decision["votes"]["hold"], 1)

    def test_make_simple_decision_sell(self):
        """多数決判定テスト - 売り判定."""
        # テスト用のダミーDataFrame作成
        test_df = pd.DataFrame(
            {"close": [100, 101, 102], "atr_14": [1.0, 1.1, 1.2], "volume": [1000, 1100, 1200]}
        )
        # 2つ以上が売りシグナル
        decision = self.strategy._make_simple_decision(
            ema_signal=-1, macd_signal=-1, rci_signal=0, df=test_df
        )

        self.assertEqual(decision["action"], EntryAction.SELL)
        self.assertGreaterEqual(decision["confidence"], 0.6)
        self.assertEqual(decision["votes"]["sell"], 2)

    def test_make_simple_decision_hold(self):
        """多数決判定テスト - ホールド判定."""
        # テスト用のダミーDataFrame作成
        test_df = pd.DataFrame(
            {"close": [100, 101, 102], "atr_14": [1.0, 1.1, 1.2], "volume": [1000, 1100, 1200]}
        )
        # 意見が分かれる場合
        decision = self.strategy._make_simple_decision(
            ema_signal=1, macd_signal=-1, rci_signal=0, df=test_df
        )

        self.assertEqual(decision["action"], EntryAction.HOLD)
        self.assertEqual(decision["confidence"], 0.15)  # 月100-200回最適化に合わせて0.2→0.15に変更

    def test_analyze_full_integration(self):
        """統合分析テスト."""
        # 実際のanalyzeメソッドをテスト
        signal = self.strategy.analyze(self.test_df)

        # 基本的なプロパティ確認
        self.assertEqual(signal.strategy_name, "MochipoyAlert")
        self.assertIsInstance(signal.timestamp, datetime)
        self.assertIn(signal.action, [EntryAction.BUY, EntryAction.SELL, EntryAction.HOLD])
        self.assertGreaterEqual(signal.confidence, 0.0)
        self.assertLessEqual(signal.confidence, 1.0)

        # 現在価格の確認
        expected_price = self.test_df["close"].iloc[-1]
        self.assertEqual(signal.current_price, expected_price)

        # エントリーシグナルの場合はリスク管理が計算されているはず
        if signal.action in [EntryAction.BUY, EntryAction.SELL]:
            self.assertIsNotNone(signal.stop_loss)
            self.assertIsNotNone(signal.take_profit)
            self.assertIsNotNone(signal.position_size)
            self.assertIsNotNone(signal.risk_ratio)

    def test_get_required_features(self):
        """必要特徴量リスト取得テスト."""
        features = self.strategy.get_required_features()

        # 必須特徴量が含まれていることを確認
        required = ["close", "ema_20", "ema_50", "macd", "atr_14"]
        for feature in required:
            self.assertIn(feature, features)

        # 特徴量数が適切（最小限）
        self.assertLessEqual(len(features), 10)

    def test_error_handling_missing_columns(self):
        """カラム不足時のエラーハンドリングテスト."""
        # 必須カラムが不足したDataFrame
        bad_df = pd.DataFrame({"close": [10000000], "volume": [100]})

        # エラーが発生してもクラッシュしないことを確認
        try:
            signal = self.strategy.analyze(bad_df)
            # エラーシグナルまたは通常のシグナルが返される
            self.assertIsNotNone(signal)
        except Exception as e:
            # StrategyError が発生する可能性もある
            from src.core.exceptions import StrategyError

            self.assertIsInstance(e, StrategyError)

    def test_rci_edge_cases(self):
        """RCI計算のエッジケーステスト."""
        # データ不足ケース
        short_prices = pd.Series([100, 101, 102])  # 14期間未満
        rci_values = self.strategy._calculate_rci(short_prices, period=14)

        # 期間不足の部分はNaNまたは0になる（実装に依存）
        # NaNの場合は0として扱うことを確認
        for i in range(3):
            value = rci_values.iloc[i]
            self.assertTrue(
                pd.isna(value) or value == 0, f"Index {i}: expected NaN or 0, got {value}"
            )

    def test_confidence_threshold(self):
        """信頼度閾値テスト."""
        # 低信頼度の設定でテスト
        low_conf_config = {"min_confidence": 0.9}
        strategy = MochipoyAlertStrategy(config=low_conf_config)

        # テスト用のダミーDataFrame作成
        test_df = pd.DataFrame(
            {"close": [100, 101, 102], "atr_14": [1.0, 1.1, 1.2], "volume": [1000, 1100, 1200]}
        )
        # 多数決で買いシグナルが出ても、信頼度が低ければHOLD
        decision = strategy._make_simple_decision(
            ema_signal=1, macd_signal=1, rci_signal=0, df=test_df
        )

        # confidence 0.6 < min_confidence 0.9 なのでHOLDになるはず
        if decision["confidence"] < 0.9:
            self.assertEqual(decision["action"], EntryAction.HOLD)


def run_mochipoy_tests():
    """もちぽよアラート戦略テスト実行関数."""
    print("=" * 50)
    print("もちぽよアラート戦略 テスト開始")
    print("=" * 50)

    # テスト実行
    unittest.main(verbosity=2, exit=False)

    print("\n" + "=" * 50)
    print("もちぽよアラート戦略 テスト完了")
    print("=" * 50)


if __name__ == "__main__":
    run_mochipoy_tests()

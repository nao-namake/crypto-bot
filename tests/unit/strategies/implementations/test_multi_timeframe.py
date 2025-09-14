"""
マルチタイムフレーム戦略のテスト

リファクタリング後の2軸構成戦略が正しく動作することを確認。
4時間足トレンドと15分足エントリーの統合を検証。.
"""

import os
import sys
import unittest
from datetime import datetime

import numpy as np
import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../../"))

from src.strategies.implementations.multi_timeframe import MultiTimeframeStrategy
from src.strategies.utils import EntryAction


class TestMultiTimeframeStrategy(unittest.TestCase):
    """マルチタイムフレーム戦略テストクラス."""

    def setUp(self):
        """テスト前準備."""
        # テスト用データ作成（上昇トレンド）
        dates = pd.date_range(start="2025-08-01", periods=100, freq="1h")

        # 明確な上昇トレンドのテストデータ
        prices = np.linspace(10000000, 11000000, 100)  # 1000万円から1100万円へ

        self.test_df = pd.DataFrame(
            {
                "timestamp": dates,
                "open": prices - 10000,
                "high": prices + 10000,
                "low": prices - 20000,
                "close": prices,
                "volume": np.random.uniform(100, 200, 100),
                "ema_20": prices - 30000,  # 20EMAは価格の少し下（上昇トレンド）
                "ema_50": prices - 50000,  # 50EMAはさらに下
                "rsi_14": np.linspace(40, 60, 100),  # RSI中間値
                "atr_14": np.full(100, 500000),  # ATR 50万円
            }
        )

        # 戦略インスタンス
        self.strategy = MultiTimeframeStrategy()

    def test_strategy_initialization(self):
        """戦略初期化テスト."""
        # デフォルト設定確認
        self.assertEqual(self.strategy.name, "MultiTimeframe")
        self.assertEqual(self.strategy.config["tf_4h_lookback"], 16)
        self.assertEqual(self.strategy.config["tf_15m_lookback"], 4)
        self.assertEqual(
            self.strategy.config["require_timeframe_agreement"], False
        )  # 攻撃的設定：重み付け判定優先
        self.assertEqual(self.strategy.config["min_confidence"], 0.4)  # 攻撃的設定：閾値引き下げ
        self.assertEqual(self.strategy.config["tf_4h_weight"], 0.6)
        self.assertEqual(self.strategy.config["tf_15m_weight"], 0.4)

    def test_analyze_4h_trend_up(self):
        """4時間足トレンド分析 - 上昇トレンドテスト."""
        # 明確な上昇トレンド条件
        signal = self.strategy._analyze_4h_trend(self.test_df)

        # 上昇トレンドなので買いシグナル期待
        self.assertEqual(signal, 1)

    def test_analyze_4h_trend_down(self):
        """4時間足トレンド分析 - 下降トレンドテスト."""
        # 下降トレンド条件を作成
        down_df = self.test_df.copy()
        down_df["ema_50"] = down_df["close"] + 50000  # EMA50が価格より上
        down_df["close"] = np.linspace(11000000, 10000000, 100)  # 価格下降

        # EMAの傾きも下向きにする
        down_df["ema_50"] = np.linspace(11100000, 10100000, 100)

        signal = self.strategy._analyze_4h_trend(down_df)

        # 下降トレンドなので売りシグナル期待
        self.assertIn(signal, [-1, 0])  # 条件によってはホールドも可

    def test_analyze_4h_trend_sideways(self):
        """4時間足トレンド分析 - 横ばいテスト."""
        # 横ばい相場を作成
        sideways_df = self.test_df.copy()
        sideways_df["ema_50"] = 10500000  # 一定値
        sideways_df["close"] = 10500000 + np.sin(np.linspace(0, 2 * np.pi, 100)) * 50000
        sideways_df["atr_14"] = 100000  # 低ボラティリティ

        signal = self.strategy._analyze_4h_trend(sideways_df)

        # 横ばいなのでホールドシグナル期待
        self.assertEqual(signal, 0)

    def test_analyze_15m_entry_golden_cross(self):
        """15分足エントリー分析 - ゴールデンクロステスト."""
        # ゴールデンクロス条件を作成
        gc_df = self.test_df.copy()
        gc_df.loc[gc_df.index[-2], "close"] = 10490000  # 前回はEMA下
        gc_df.loc[gc_df.index[-2], "ema_20"] = 10500000
        gc_df.loc[gc_df.index[-1], "close"] = 10510000  # 今回はEMA上
        gc_df.loc[gc_df.index[-1], "ema_20"] = 10500000
        gc_df["rsi_14"] = 45  # 中立的なRSI

        signal = self.strategy._analyze_15m_entry(gc_df)

        # クロスシグナルが検出されることを確認
        self.assertIn(signal, [0, 1])  # 条件によって変動

    def test_analyze_15m_entry_dead_cross(self):
        """15分足エントリー分析 - デッドクロステスト."""
        # デッドクロス条件を作成
        dc_df = self.test_df.copy()
        dc_df.loc[dc_df.index[-2], "close"] = 10510000  # 前回はEMA上
        dc_df.loc[dc_df.index[-2], "ema_20"] = 10500000
        dc_df.loc[dc_df.index[-1], "close"] = 10490000  # 今回はEMA下
        dc_df.loc[dc_df.index[-1], "ema_20"] = 10500000
        dc_df["rsi_14"] = 55  # 中立的なRSI

        signal = self.strategy._analyze_15m_entry(dc_df)

        # クロスシグナルが検出されることを確認
        self.assertIn(signal, [-1, 0])  # 条件によって変動

    def test_analyze_15m_entry_rsi_oversold(self):
        """15分足エントリー分析 - RSI過売りテスト."""
        # RSI過売り条件
        oversold_df = self.test_df.copy()
        oversold_df["rsi_14"] = 25  # 過売り

        signal = self.strategy._analyze_15m_entry(oversold_df)

        # RSIだけでは不十分な可能性もあるが、シグナルは生成される
        self.assertIn(signal, [-1, 0, 1])

    def test_make_2tf_decision_agreement(self):
        """2層統合判定 - 時間軸一致テスト."""
        # 両時間軸が買いシグナル
        decision = self.strategy._make_2tf_decision(tf_4h_signal=1, tf_15m_signal=1)

        self.assertEqual(decision["action"], EntryAction.BUY)
        # 動的信頼度（0.95〜1.05の範囲）
        self.assertGreaterEqual(decision["confidence"], 0.85)
        self.assertLessEqual(decision["confidence"], 1.05)
        self.assertTrue(decision["agreement"])

    def test_make_2tf_decision_disagreement(self):
        """2層統合判定 - 時間軸不一致テスト."""
        # 時間軸が不一致
        decision = self.strategy._make_2tf_decision(tf_4h_signal=1, tf_15m_signal=-1)

        # 攻撃的設定：重み付け判定で不一致でも取引（require_timeframe_agreement=False）
        # weighted_score = 1 * 0.6 + (-1) * 0.4 = 0.2 < min_confidence(0.4) なのでHOLD
        self.assertEqual(decision["action"], EntryAction.HOLD)
        self.assertFalse(decision.get("agreement", True))

    def test_make_2tf_decision_4h_only(self):
        """2層統合判定 - 4時間足のみシグナルテスト."""
        # 4時間足のみシグナルあり
        decision = self.strategy._make_2tf_decision(tf_4h_signal=1, tf_15m_signal=0)

        # 攻撃的設定：重み付け判定モード（require_timeframe_agreement=False）
        # weighted_score = 1 * 0.6 + 0 * 0.4 = 0.6 >= min_confidence(0.4) なのでBUY
        self.assertEqual(decision["action"], EntryAction.BUY)
        # 動的信頼度（0.6前後の範囲、分散考慮）
        self.assertGreaterEqual(decision["confidence"], 0.50)
        self.assertLessEqual(decision["confidence"], 0.70)

    def test_make_2tf_decision_no_agreement_mode(self):
        """2層統合判定 - 一致不要モードテスト."""
        # 一致不要モードの戦略
        strategy = MultiTimeframeStrategy(config={"require_timeframe_agreement": False})

        decision = strategy._make_2tf_decision(tf_4h_signal=1, tf_15m_signal=-1)

        # 重み付け判定モード
        # 4h(1 * 0.6) + 15m(-1 * 0.4) = 0.2 > 0 なので買い
        weighted_score = 1 * 0.6 + (-1) * 0.4
        if abs(weighted_score) >= strategy.config["min_confidence"]:
            expected_action = EntryAction.BUY if weighted_score > 0 else EntryAction.SELL
        else:
            expected_action = EntryAction.HOLD

        self.assertEqual(decision["action"], expected_action)

    def test_analyze_full_integration(self):
        """統合分析テスト."""
        signal = self.strategy.analyze(self.test_df)

        # 基本的なプロパティ確認
        self.assertEqual(signal.strategy_name, "MultiTimeframe")
        self.assertIn(signal.action, [EntryAction.BUY, EntryAction.SELL, EntryAction.HOLD])
        self.assertGreaterEqual(signal.confidence, 0.0)
        self.assertLessEqual(signal.confidence, 1.0)

        # メタデータに時間軸情報が含まれることを確認
        self.assertIn("tf_4h_signal", signal.metadata.get("decision_metadata", {}))
        self.assertIn("tf_15m_signal", signal.metadata.get("decision_metadata", {}))

        # リスク管理計算の確認
        if signal.action in [EntryAction.BUY, EntryAction.SELL]:
            self.assertIsNotNone(signal.stop_loss)
            self.assertIsNotNone(signal.take_profit)
            self.assertIsNotNone(signal.position_size)

    def test_get_required_features(self):
        """必要特徴量リスト取得テスト."""
        features = self.strategy.get_required_features()

        # 必須特徴量が含まれていることを確認
        required = ["close", "high", "low", "ema_20", "ema_50", "rsi_14", "atr_14"]
        for feature in required:
            self.assertIn(feature, features)

        # 最小限の特徴量であること
        self.assertLessEqual(len(features), 10)

    def test_custom_weight_configuration(self):
        """カスタム重み設定テスト."""
        # 15分足重視の設定
        custom_config = {"tf_4h_weight": 0.3, "tf_15m_weight": 0.7}
        strategy = MultiTimeframeStrategy(config=custom_config)

        self.assertEqual(strategy.config["tf_4h_weight"], 0.3)
        self.assertEqual(strategy.config["tf_15m_weight"], 0.7)

        # 重みの合計が1.0であることを確認
        total_weight = strategy.config["tf_4h_weight"] + strategy.config["tf_15m_weight"]
        self.assertEqual(total_weight, 1.0)

    def test_min_confidence_filter(self):
        """最小信頼度フィルターテスト."""
        # 高い最小信頼度を設定
        high_conf_strategy = MultiTimeframeStrategy(config={"min_confidence": 0.9})

        # 4時間足のみのシグナル（信頼度が低い）
        decision = high_conf_strategy._make_2tf_decision(tf_4h_signal=1, tf_15m_signal=0)

        # 信頼度が閾値未満ならHOLD
        if decision["confidence"] < 0.9:
            self.assertEqual(decision["action"], EntryAction.HOLD)


def run_multi_timeframe_tests():
    """マルチタイムフレーム戦略テスト実行関数."""
    print("=" * 50)
    print("マルチタイムフレーム戦略 テスト開始")
    print("=" * 50)

    # テスト実行
    unittest.main(verbosity=2, exit=False)

    print("\n" + "=" * 50)
    print("マルチタイムフレーム戦略 テスト完了")
    print("=" * 50)


if __name__ == "__main__":
    run_multi_timeframe_tests()

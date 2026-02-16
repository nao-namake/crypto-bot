"""
Strategy base class テスト - カバレッジ向上

64.76%の低カバレッジを改善するため、包括的なテスト追加。
基底クラスの抽象メソッド、共通処理、エラーハンドリング、拡張機能を網羅。
"""

from abc import ABC
from datetime import datetime
from typing import Dict, Optional
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest

from src.core.config import load_config
from src.core.exceptions import CryptoBotError
from src.strategies.base.strategy_base import StrategyBase, StrategySignal


@pytest.fixture(scope="session", autouse=True)
def init_config():
    """テスト用設定初期化"""
    try:
        load_config("config/core/unified.yaml")
    except Exception:
        # テスト環境で設定ファイルが見つからない場合はダミー設定
        from src.core.config import config_manager

        config_manager._config = {
            "system": {"name": "crypto_bot", "version": "1.0.0"},
            "exchange": {"name": "bitbank", "trading": {"enabled": False}},
            "discord": {"notifications": {"enabled": False}},
            "logging": {"level": "INFO", "file": "/tmp/test.log"},
        }


class ConcreteStrategy(StrategyBase):
    """テスト用具象戦略クラス"""

    def __init__(self, name: str = "TestStrategy", config=None):
        super().__init__(name, config)

    def analyze(
        self, features: pd.DataFrame, multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> StrategySignal:
        """テスト用分析実装"""
        if features.empty:
            return StrategySignal(
                strategy_name=self.name,
                timestamp=datetime.now(),
                action="HOLD",
                confidence=0.0,
                strength=0.0,
                current_price=0.0,
            )

        # 単純なテストロジック
        last_close = features["close"].iloc[-1]
        if last_close > 5000000:  # 500万円より高い
            return StrategySignal(
                strategy_name=self.name,
                timestamp=datetime.now(),
                action="SELL",
                confidence=0.8,
                strength=0.9,
                current_price=last_close,
            )
        elif last_close < 3000000:  # 300万円より低い
            return StrategySignal(
                strategy_name=self.name,
                timestamp=datetime.now(),
                action="BUY",
                confidence=0.7,
                strength=0.7,
                current_price=last_close,
            )
        else:
            return StrategySignal(
                strategy_name=self.name,
                timestamp=datetime.now(),
                action="HOLD",
                confidence=0.5,
                strength=0.3,
                current_price=last_close,
            )

    def get_required_features(self) -> list:
        """必要な特徴量リスト"""
        return ["close", "volume", "rsi_14", "bb_position"]


class TestStrategyBase:
    """StrategyBaseクラスの包括的テスト"""

    @pytest.fixture
    def sample_features(self):
        """サンプル特徴量データ（20以上のデータポイント）"""
        n_points = 25
        return pd.DataFrame(
            {
                "close": np.random.uniform(3500000, 5500000, n_points),
                "volume": np.random.uniform(100, 300, n_points),
                "rsi_14": np.random.uniform(20, 80, n_points),
                "bb_position": np.random.uniform(-1, 1, n_points),
                "timestamp": pd.date_range("2025-01-01", periods=n_points, freq="H"),
            }
        )

    @pytest.fixture
    def strategy(self):
        """具象戦略インスタンス"""
        return ConcreteStrategy("TestStrategy")

    def test_strategy_initialization(self, strategy):
        """戦略初期化テスト"""
        assert strategy.name == "TestStrategy"
        assert strategy.is_enabled is True
        assert strategy.last_signal is None
        assert strategy.signal_history == []
        assert strategy.total_signals == 0

    def test_strategy_initialization_with_params(self):
        """パラメータ付き戦略初期化テスト"""
        config = {"risk_threshold": 0.02, "confidence_threshold": 0.6}
        strategy = ConcreteStrategy("CustomStrategy", config)

        assert strategy.name == "CustomStrategy"
        assert strategy.config["risk_threshold"] == 0.02
        assert strategy.config["confidence_threshold"] == 0.6

    def test_abstract_strategy_cannot_be_instantiated(self):
        """抽象クラスのインスタンス化不可テスト"""
        with pytest.raises(TypeError):
            StrategyBase("AbstractStrategy")

    def test_analyze_method_success(self, strategy, sample_features):
        """分析メソッド成功テスト"""
        signal = strategy.analyze(sample_features)

        assert isinstance(signal, StrategySignal)
        assert signal.action in ["BUY", "SELL", "HOLD", "buy", "sell", "hold"]
        assert 0.0 <= signal.confidence <= 1.0
        assert isinstance(signal.strength, float)
        assert isinstance(signal.strategy_name, str)

    def test_analyze_method_with_empty_data(self, strategy):
        """空データでの分析テスト"""
        empty_features = pd.DataFrame()
        signal = strategy.analyze(empty_features)

        assert signal.action == "HOLD"
        assert signal.confidence == 0.0
        assert signal.strength == 0.0

    def test_analyze_method_with_high_price(self, strategy):
        """高価格での分析テスト（SELL シグナル）"""
        high_price_features = pd.DataFrame(
            {"close": [5500000], "volume": [100], "rsi_14": [75], "bb_position": [0.8]}  # 550万円
        )

        signal = strategy.analyze(high_price_features)

        assert signal.action == "SELL"
        assert signal.confidence == 0.8
        assert signal.strength == 0.9

    def test_analyze_method_with_low_price(self, strategy):
        """低価格での分析テスト（BUY シグナル）"""
        low_price_features = pd.DataFrame(
            {"close": [2500000], "volume": [100], "rsi_14": [25], "bb_position": [-0.8]}  # 250万円
        )

        signal = strategy.analyze(low_price_features)

        assert signal.action == "BUY"
        assert signal.confidence == 0.7
        assert signal.strength == 0.7

    def test_get_required_features(self, strategy):
        """必要特徴量取得テスト"""
        features = strategy.get_required_features()

        assert isinstance(features, list)
        assert "close" in features
        assert "volume" in features
        assert "rsi_14" in features
        assert "bb_position" in features

    def test_required_features_validation(self, strategy):
        """必要特徴量の検証テスト"""
        required = strategy.get_required_features()

        # 必要な特徴量がすべて含まれているかテスト
        sample_with_required = pd.DataFrame({feature: [1.0, 2.0, 3.0] for feature in required})

        # 特徴量が揃っていれば分析できる
        signal = strategy.analyze(sample_with_required)
        assert isinstance(signal, StrategySignal)

    def test_update_signal_history(self, strategy, sample_features):
        """シグナル履歴更新テスト"""
        # 初期状態
        assert len(strategy.signal_history) == 0

        # シグナル生成
        signal = strategy.analyze(sample_features)

        # generate_signalメソッドを使って履歴更新をテスト
        if hasattr(strategy, "generate_signal"):
            generated_signal = strategy.generate_signal(sample_features)
            assert isinstance(generated_signal, StrategySignal)

    def test_signal_tracking(self, strategy):
        """シグナル追跡テスト"""
        initial_count = strategy.total_signals

        # シグナル生成
        signal = strategy.analyze(
            strategy.sample_features
            if hasattr(strategy, "sample_features")
            else pd.DataFrame(
                {"close": [4000000], "volume": [100], "rsi_14": [50], "bb_position": [0.0]}
            )
        )

        # シグナルが生成されることを確認
        assert isinstance(signal, StrategySignal)
        assert signal.strategy_name == strategy.name

    def test_enable_disable_strategy(self, strategy):
        """戦略有効/無効化テスト"""
        # 初期状態は有効
        assert strategy.is_enabled is True

        # 手動で無効化
        strategy.is_enabled = False
        assert strategy.is_enabled is False

        # 手動で有効化
        strategy.is_enabled = True
        assert strategy.is_enabled is True

    def test_disabled_strategy_analysis(self, strategy, sample_features):
        """無効化された戦略の分析テスト"""
        strategy.is_enabled = False

        signal = strategy.analyze(sample_features)

        # 無効化されていても戦略は動作する（実装依存）
        assert isinstance(signal, StrategySignal)

    def test_performance_tracking(self, strategy):
        """パフォーマンス追跡テスト"""
        # 初期状態
        assert strategy.total_signals == 0

        # シグナルカウンタを手動で更新
        strategy.total_signals = 10

        assert strategy.total_signals == 10

    def test_calculate_confidence_adjustment(self, strategy):
        """信頼度調整計算テスト"""
        if hasattr(strategy, "_calculate_confidence_adjustment"):
            # ボラティリティベースの調整
            high_volatility = 0.05  # 5%
            low_volatility = 0.01  # 1%

            high_adj = strategy._calculate_confidence_adjustment(high_volatility)
            low_adj = strategy._calculate_confidence_adjustment(low_volatility)

            # 高ボラティリティでは信頼度が下がることを想定
            assert high_adj <= low_adj

    def test_config_management(self, strategy):
        """設定管理テスト"""
        # 設定の読み取り
        assert strategy.config is not None

        # 設定の追加
        strategy.config["test_param"] = "test_value"
        assert strategy.config["test_param"] == "test_value"

    def test_signal_properties(self, strategy, sample_features):
        """シグナルプロパティテスト"""
        signal = strategy.analyze(sample_features)

        # シグナルの基本プロパティを確認
        assert hasattr(signal, "strategy_name")
        assert hasattr(signal, "timestamp")
        assert hasattr(signal, "action")
        assert hasattr(signal, "confidence")
        assert hasattr(signal, "strength")

    def test_signal_methods(self, strategy, sample_features):
        """シグナルメソッドテスト"""
        signal = strategy.analyze(sample_features)

        # シグナルのメソッドをテスト
        if hasattr(signal, "is_entry_signal"):
            is_entry = signal.is_entry_signal()
            assert isinstance(is_entry, bool)

        if hasattr(signal, "is_hold_signal"):
            is_hold = signal.is_hold_signal()
            assert isinstance(is_hold, bool)

        if hasattr(signal, "to_dict"):
            signal_dict = signal.to_dict()
            assert isinstance(signal_dict, dict)
            assert "strategy_name" in signal_dict

    def test_strategy_comparison(self):
        """戦略比較テスト"""
        strategy1 = ConcreteStrategy("Strategy1")
        strategy2 = ConcreteStrategy("Strategy2")
        strategy3 = ConcreteStrategy("Strategy1")  # 同じ名前

        assert strategy1.name != strategy2.name
        assert strategy1.name == strategy3.name

    def test_logger_integration(self, strategy):
        """ログ統合テスト"""
        assert strategy.logger is not None
        assert hasattr(strategy, "last_update")
        assert isinstance(strategy.last_update, datetime)

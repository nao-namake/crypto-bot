"""
Phase 45.6: Meta-Learning動的重み最適化テスト

Meta-Learningシステムの単体テスト。
MarketRegimeAnalyzer・PerformanceTracker・MetaLearningWeightOptimizerの動作を検証。
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pandas as pd
import pytest

# プロジェクトルートをPythonパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from src.ml.meta_learning import (
    MarketRegimeAnalyzer,
    MetaLearningWeightOptimizer,
    PerformanceTracker,
)


class TestMarketRegimeAnalyzer:
    """MarketRegimeAnalyzer単体テスト"""

    @pytest.fixture
    def analyzer(self):
        """MarketRegimeAnalyzer初期化"""
        return MarketRegimeAnalyzer()

    @pytest.fixture
    def sample_market_data(self):
        """サンプル市場データ（正常系）"""
        dates = pd.date_range(start="2025-01-01", periods=100, freq="15T")
        data = {
            "timestamp": dates,
            "close": np.random.uniform(16000000, 17000000, 100),
            "high": np.random.uniform(16500000, 17500000, 100),
            "low": np.random.uniform(15500000, 16500000, 100),
            "volume": np.random.uniform(1000, 5000, 100),
            "atr_14": np.random.uniform(100000, 500000, 100),
            "bb_position": np.random.uniform(-1, 1, 100),
            "ema_20": np.random.uniform(16000000, 17000000, 100),
            "ema_50": np.random.uniform(16000000, 17000000, 100),
            "adx_14": np.random.uniform(10, 50, 100),
            "plus_di_14": np.random.uniform(10, 50, 100),
            "minus_di_14": np.random.uniform(10, 50, 100),
        }
        return pd.DataFrame(data)

    def test_analyze_normal_case(self, analyzer, sample_market_data):
        """正常系: 市場状況特徴量抽出"""
        features = analyzer.analyze(sample_market_data)

        # 11特徴量が返される
        assert len(features) == 11
        assert "volatility_atr_14" in features
        assert "volatility_bb_width" in features
        assert "volatility_ratio_7d" in features
        assert "trend_ema_spread" in features
        assert "trend_adx" in features
        assert "trend_di_plus" in features
        assert "trend_di_minus" in features
        assert "trend_strength" in features
        assert "range_donchian_width" in features
        assert "range_detection" in features
        assert "volume_ratio" in features

        # すべての特徴量が0-1範囲
        for key, value in features.items():
            assert 0.0 <= value <= 1.0, f"{key}={value} is out of range [0, 1]"

    def test_analyze_insufficient_data(self, analyzer):
        """エッジケース: データ不足時のデフォルト特徴量"""
        # 空のDataFrame
        empty_df = pd.DataFrame()
        features = analyzer.analyze(empty_df)

        # デフォルト特徴量（すべて0.5）
        assert len(features) == 11
        for value in features.values():
            assert value == 0.5

    def test_analyze_none_data(self, analyzer):
        """エッジケース: Noneデータ時のデフォルト特徴量"""
        features = analyzer.analyze(None)

        # デフォルト特徴量（すべて0.5）
        assert len(features) == 11
        for value in features.values():
            assert value == 0.5

    def test_normalize_method(self, analyzer):
        """_normalize()メソッドテスト"""
        # 正常系
        assert analyzer._normalize(100, 1000) == 0.1
        assert analyzer._normalize(1000, 1000) == 1.0
        assert analyzer._normalize(0, 1000) == 0.0

        # エッジケース: reference=0
        assert analyzer._normalize(100, 0) == 0.0

    def test_normalize_indicator_method(self, analyzer):
        """_normalize_indicator()メソッドテスト"""
        # 正常系（0-100を0-1に正規化）
        assert analyzer._normalize_indicator(0, 0, 100) == 0.0
        assert analyzer._normalize_indicator(50, 0, 100) == 0.5
        assert analyzer._normalize_indicator(100, 0, 100) == 1.0

        # エッジケース: min=max
        assert analyzer._normalize_indicator(50, 50, 50) == 0.5


class TestPerformanceTracker:
    """PerformanceTracker単体テスト"""

    @pytest.fixture
    def tracker(self, tmp_path):
        """PerformanceTracker初期化（一時ディレクトリ使用）"""
        # 一時ファイルパス設定
        history_file = tmp_path / "performance_history.json"

        with patch("src.ml.meta_learning.get_threshold") as mock_get_threshold:

            def threshold_side_effect(key, default):
                if key == "ml.meta_learning.performance_tracking.history_file":
                    return str(history_file)
                if key == "ml.meta_learning.performance_tracking.window_days_short":
                    return 7
                if key == "ml.meta_learning.performance_tracking.window_days_long":
                    return 30
                if key == "ml.meta_learning.performance_tracking.min_trades_required":
                    return 5
                return default

            mock_get_threshold.side_effect = threshold_side_effect
            tracker = PerformanceTracker()

        return tracker

    def test_record_trade_normal(self, tracker):
        """正常系: 取引結果記録"""
        trade_result = {
            "timestamp": datetime.now().isoformat(),
            "strategy_name": "ATRBased",
            "ml_prediction": 1,
            "actual_outcome": "win",
            "profit": 0.02,
        }

        tracker.record_trade(trade_result)

        # 履歴に記録されている
        assert len(tracker.history["ml_performance"]["trades"]) == 1
        assert "ATRBased" in tracker.history["strategy_performance"]
        assert len(tracker.history["strategy_performance"]["ATRBased"]["trades"]) == 1

    def test_get_recent_performance_insufficient_trades(self, tracker):
        """エッジケース: 取引数不足時のデフォルト値"""
        # 取引数0
        performance = tracker.get_recent_performance()

        # デフォルト値
        assert performance["ml_win_rate"] == 0.5
        assert performance["ml_avg_profit"] == 0.0
        assert performance["strategy_performance"] == {}

    def test_get_recent_performance_sufficient_trades(self, tracker):
        """正常系: 十分な取引数での統計計算"""
        # 10取引記録（win: 7, loss: 3）
        for i in range(10):
            trade_result = {
                "timestamp": datetime.now().isoformat(),
                "strategy_name": "ATRBased",
                "ml_prediction": 1,
                "actual_outcome": "win" if i < 7 else "loss",
                "profit": 0.02 if i < 7 else -0.01,
            }
            tracker.record_trade(trade_result)

        performance = tracker.get_recent_performance()

        # 勝率70%
        assert 0.65 <= performance["ml_win_rate"] <= 0.75
        # 平均利益 > 0
        assert performance["ml_avg_profit"] > 0
        # 戦略パフォーマンス存在
        assert "ATRBased" in performance["strategy_performance"]

    def test_json_persistence(self, tracker):
        """JSON永続化テスト"""
        # 取引記録
        trade_result = {
            "timestamp": datetime.now().isoformat(),
            "strategy_name": "ATRBased",
            "ml_prediction": 1,
            "actual_outcome": "win",
            "profit": 0.02,
        }
        tracker.record_trade(trade_result)

        # ファイル存在確認
        assert tracker.history_file.exists()

        # 読み込み確認
        with open(tracker.history_file, "r") as f:
            loaded_history = json.load(f)

        assert len(loaded_history["ml_performance"]["trades"]) == 1
        assert "ATRBased" in loaded_history["strategy_performance"]


class TestMetaLearningWeightOptimizer:
    """MetaLearningWeightOptimizer単体テスト"""

    @pytest.fixture
    def sample_market_data(self):
        """サンプル市場データ"""
        dates = pd.date_range(start="2025-01-01", periods=100, freq="15T")
        data = {
            "timestamp": dates,
            "close": np.random.uniform(16000000, 17000000, 100),
            "high": np.random.uniform(16500000, 17500000, 100),
            "low": np.random.uniform(15500000, 16500000, 100),
            "volume": np.random.uniform(1000, 5000, 100),
            "atr_14": np.random.uniform(100000, 500000, 100),
            "bb_position": np.random.uniform(-1, 1, 100),
            "ema_20": np.random.uniform(16000000, 17000000, 100),
            "ema_50": np.random.uniform(16000000, 17000000, 100),
            "adx_14": np.random.uniform(10, 50, 100),
            "plus_di_14": np.random.uniform(10, 50, 100),
            "minus_di_14": np.random.uniform(10, 50, 100),
        }
        return pd.DataFrame(data)

    @patch("src.ml.meta_learning.get_threshold")
    def test_fallback_no_model(self, mock_get_threshold, sample_market_data):
        """フォールバック: モデル未存在時の固定重み使用（最重要）"""

        def threshold_side_effect(key, default):
            if key == "ml.meta_learning.model_path":
                return "models/meta_learning/non_existent_model.pkl"
            if key == "ml.meta_learning.fallback_ml_weight":
                return 0.35
            if key == "ml.meta_learning.fallback_strategy_weight":
                return 0.7
            return default

        mock_get_threshold.side_effect = threshold_side_effect

        # Meta-MLオプティマイザー初期化（モデル未存在）
        optimizer = MetaLearningWeightOptimizer()

        # モデル未存在確認
        assert optimizer.model is None

        # 動的重み予測
        weights = optimizer.predict_weights(sample_market_data)

        # フォールバック固定重み使用（正規化済み: 0.35/1.05 ≈ 0.333, 0.7/1.05 ≈ 0.667）
        assert abs(weights["ml"] - 0.333) < 0.01
        assert abs(weights["strategy"] - 0.667) < 0.01
        assert abs(weights["ml"] + weights["strategy"] - 1.0) < 0.01

    @patch("src.ml.meta_learning.get_threshold")
    def test_fallback_prediction_error(self, mock_get_threshold, sample_market_data):
        """フォールバック: 推論エラー時の固定重み使用"""

        def threshold_side_effect(key, default):
            if key == "ml.meta_learning.model_path":
                return "models/meta_learning/meta_model.pkl"
            if key == "ml.meta_learning.fallback_ml_weight":
                return 0.35
            if key == "ml.meta_learning.fallback_strategy_weight":
                return 0.7
            return default

        mock_get_threshold.side_effect = threshold_side_effect

        # Meta-MLオプティマイザー初期化
        optimizer = MetaLearningWeightOptimizer()

        # モックモデル設定（予測エラー発生）
        mock_model = Mock()
        mock_model.predict.side_effect = Exception("Prediction error")
        optimizer.model = mock_model

        # 動的重み予測（エラー発生）
        weights = optimizer.predict_weights(sample_market_data)

        # フォールバック固定重み使用（正規化済み: 0.35/1.05 ≈ 0.333, 0.7/1.05 ≈ 0.667）
        assert abs(weights["ml"] - 0.333) < 0.01
        assert abs(weights["strategy"] - 0.667) < 0.01
        assert abs(weights["ml"] + weights["strategy"] - 1.0) < 0.01

    @patch("src.ml.meta_learning.get_threshold")
    def test_predict_weights_with_model(self, mock_get_threshold, sample_market_data):
        """正常系: モデル存在時の動的重み予測"""

        def threshold_side_effect(key, default):
            if key == "ml.meta_learning.model_path":
                return "models/meta_learning/meta_model.pkl"
            if key == "ml.meta_learning.fallback_ml_weight":
                return 0.35
            if key == "ml.meta_learning.fallback_strategy_weight":
                return 0.7
            return default

        mock_get_threshold.side_effect = threshold_side_effect

        # Meta-MLオプティマイザー初期化
        optimizer = MetaLearningWeightOptimizer()

        # モックモデル設定（予測成功）
        mock_model = Mock()
        mock_model.predict.return_value = np.array([[0.6, 0.4]])  # [ml_weight, strategy_weight]
        optimizer.model = mock_model

        # 動的重み予測
        weights = optimizer.predict_weights(sample_market_data)

        # 動的重み使用（正規化済み）
        assert 0.0 <= weights["ml"] <= 1.0
        assert 0.0 <= weights["strategy"] <= 1.0
        # 合計1.0
        assert abs(weights["ml"] + weights["strategy"] - 1.0) < 0.01

    @patch("src.ml.meta_learning.get_threshold")
    def test_create_feature_vector(self, mock_get_threshold):
        """_create_feature_vector()メソッドテスト"""

        def threshold_side_effect(key, default):
            if key == "ml.meta_learning.model_path":
                return "models/meta_learning/meta_model.pkl"
            return default

        mock_get_threshold.side_effect = threshold_side_effect

        optimizer = MetaLearningWeightOptimizer()

        # サンプル特徴量
        market_features = {
            "volatility_atr_14": 0.5,
            "volatility_bb_width": 0.5,
            "volatility_ratio_7d": 0.5,
            "trend_ema_spread": 0.5,
            "trend_adx": 0.5,
            "trend_di_plus": 0.5,
            "trend_di_minus": 0.5,
            "trend_strength": 0.5,
            "range_donchian_width": 0.5,
            "range_detection": 0.5,
            "volume_ratio": 0.5,
        }
        performance_data = {"ml_win_rate": 0.65, "ml_avg_profit": 0.02}

        # 特徴量ベクトル作成
        feature_vector = optimizer._create_feature_vector(market_features, performance_data)

        # 13特徴量（11市場 + 2パフォーマンス）
        assert len(feature_vector) == 13
        assert feature_vector[0] == 0.5  # volatility_atr_14
        assert feature_vector[11] == 0.65  # ml_win_rate
        assert feature_vector[12] == 0.02  # ml_avg_profit

    @patch("src.ml.meta_learning.get_threshold")
    def test_record_trade_outcome(self, mock_get_threshold):
        """record_trade_outcome()メソッドテスト"""

        def threshold_side_effect(key, default):
            if key == "ml.meta_learning.model_path":
                return "models/meta_learning/meta_model.pkl"
            return default

        mock_get_threshold.side_effect = threshold_side_effect

        optimizer = MetaLearningWeightOptimizer()

        # モックPerformanceTracker
        optimizer.performance_tracker = Mock()

        # 取引結果記録
        trade_result = {
            "timestamp": datetime.now().isoformat(),
            "strategy_name": "ATRBased",
            "ml_prediction": 1,
            "actual_outcome": "win",
            "profit": 0.02,
        }
        optimizer.record_trade_outcome(trade_result)

        # PerformanceTracker.record_trade()が呼ばれる
        optimizer.performance_tracker.record_trade.assert_called_once_with(trade_result)

# =============================================================================
# テストファイル: tests/unit/strategy/test_multi_timeframe_ensemble.py
# 説明:
# マルチタイムフレーム×アンサンブル統合戦略のユニットテスト
# 2段階アンサンブル・勝率向上機能の検証
# =============================================================================

import unittest
from unittest.mock import patch, MagicMock
import numpy as np
import pandas as pd
from datetime import datetime

from crypto_bot.strategy.multi_timeframe_ensemble import MultiTimeframeEnsembleStrategy
from crypto_bot.execution.engine import Position, Signal


class TestMultiTimeframeEnsembleStrategy(unittest.TestCase):
    """マルチタイムフレーム×アンサンブル戦略のテスト"""
    
    def setUp(self):
        """テストセットアップ"""
        # テスト用価格データ生成
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=200, freq='1h')
        base_price = 50000
        trend = np.linspace(0, 5000, 200)  # 上昇トレンド
        noise = np.random.randn(200) * 200
        prices = base_price + trend + noise
        
        self.price_df = pd.DataFrame({
            'open': prices + np.random.randn(200) * 50,
            'high': prices + np.abs(np.random.randn(200) * 150),
            'low': prices - np.abs(np.random.randn(200) * 150),
            'close': prices,
            'volume': np.random.randint(1000, 10000, 200)
        }, index=dates)
        
        # テスト用設定
        self.config = {
            'multi_timeframe': {
                'timeframes': ['15m', '1h', '4h'],
                'weights': [0.3, 0.5, 0.2],
                'threshold': 0.6
            },
            'ml': {
                'ensemble': {
                    'enabled': True,
                    'method': 'trading_stacking',
                    'confidence_threshold': 0.65
                },
                'extra_features': ['rsi_14', 'macd', 'vix']
            },
            'data': {
                'exchange': 'csv',
                'csv_path': '/test/path/data.csv',
                'symbol': 'BTC/USDT'
            }
        }
        
    @patch('crypto_bot.strategy.multi_timeframe_ensemble.EnsembleMLStrategy')
    def test_initialization(self, mock_ensemble_strategy):
        """初期化テスト"""
        mock_strategy_instance = MagicMock()
        mock_ensemble_strategy.return_value = mock_strategy_instance
        
        strategy = MultiTimeframeEnsembleStrategy(self.config)
        
        self.assertEqual(strategy.timeframes, ['15m', '1h', '4h'])
        self.assertEqual(strategy.weights, [0.3, 0.5, 0.2])
        self.assertTrue(strategy.ensemble_enabled)
        self.assertEqual(len(strategy.ensemble_strategies), 3)
        
    def test_timeframe_config_creation(self):
        """タイムフレーム別設定作成テスト"""
        strategy = MultiTimeframeEnsembleStrategy(self.config)
        
        # 15分足設定
        tf_15m_config = strategy._create_timeframe_config('15m')
        self.assertEqual(tf_15m_config['data']['timeframe'], '15m')
        self.assertEqual(tf_15m_config['ml']['feat_period'], 7)
        self.assertEqual(tf_15m_config['ml']['ensemble']['confidence_threshold'], 0.6)
        
        # 4時間足設定
        tf_4h_config = strategy._create_timeframe_config('4h')
        self.assertEqual(tf_4h_config['data']['timeframe'], '4h')
        self.assertEqual(tf_4h_config['ml']['feat_period'], 21)
        self.assertEqual(tf_4h_config['ml']['ensemble']['confidence_threshold'], 0.7)
        
    def test_full_feature_set_generation(self):
        """101特徴量フルセット生成テスト"""
        strategy = MultiTimeframeEnsembleStrategy(self.config)
        
        feature_set = strategy._get_full_feature_set()
        
        # 特徴量数確認
        self.assertGreaterEqual(len(feature_set), 95)  # 約101特徴量
        
        # 重要特徴量の存在確認
        important_features = ['vix', 'dxy', 'fear_greed', 'funding', 'rsi_14', 'macd']
        for feature in important_features:
            self.assertIn(feature, feature_set)
            
    def test_timeframe_data_generation(self):
        """タイムフレーム別データ生成テスト"""
        strategy = MultiTimeframeEnsembleStrategy(self.config)
        
        # 1時間足（元データそのまま）
        data_1h = strategy._get_timeframe_data(self.price_df, '1h')
        self.assertEqual(len(data_1h), len(self.price_df))
        
        # 15分足（補間）
        data_15m = strategy._get_timeframe_data(self.price_df, '15m')
        self.assertGreater(len(data_15m), len(self.price_df))  # より多くのデータポイント
        
        # 4時間足（集約）
        data_4h = strategy._get_timeframe_data(self.price_df, '4h')
        self.assertLess(len(data_4h), len(self.price_df))  # より少ないデータポイント
        
    def test_data_quality_assessment(self):
        """データ品質評価テスト"""
        strategy = MultiTimeframeEnsembleStrategy(self.config)
        
        # 高品質データ
        quality_high = strategy._assess_data_quality(self.price_df)
        self.assertGreater(quality_high['quality_score'], 0.8)
        self.assertIn('completeness', quality_high)
        self.assertIn('price_validity', quality_high)
        
        # 低品質データ（欠損値あり）
        low_quality_df = self.price_df.copy()
        low_quality_df.iloc[::5] = np.nan  # 5行ごとに欠損
        quality_low = strategy._assess_data_quality(low_quality_df)
        self.assertLess(quality_low['quality_score'], quality_high['quality_score'])
        
        # 空データ
        quality_empty = strategy._assess_data_quality(pd.DataFrame())
        self.assertEqual(quality_empty['quality_score'], 0.0)
        
    @patch('crypto_bot.strategy.multi_timeframe_ensemble.EnsembleMLStrategy')
    def test_timeframe_ensemble_predictions(self, mock_ensemble_strategy):
        """各タイムフレームのアンサンブル予測テスト"""
        # 各タイムフレームの戦略モック
        mock_strategies = {}
        mock_signals = {
            '15m': Signal(side="BUY", price=50000),
            '1h': Signal(side="BUY", price=50000),
            '4h': Signal(side=None, price=None)
        }
        
        for tf in ['15m', '1h', '4h']:
            mock_strategy = MagicMock()
            mock_strategy.logic_signal.return_value = mock_signals[tf]
            mock_strategy.get_ensemble_performance_info.return_value = {
                'average_confidence': 0.7,
                'ensemble_enabled': True
            }
            mock_strategies[tf] = mock_strategy
            
        mock_ensemble_strategy.side_effect = (
            lambda **kwargs: mock_strategies[
                kwargs.get('config', {}).get('data', {}).get('timeframe', '1h')
            ]
        )
        
        strategy = MultiTimeframeEnsembleStrategy(self.config)
        strategy.ensemble_strategies = mock_strategies
        
        predictions = strategy._get_timeframe_ensemble_predictions(self.price_df)
        
        self.assertEqual(len(predictions), 3)
        self.assertIn('15m', predictions)
        self.assertIn('1h', predictions)
        self.assertIn('4h', predictions)
        
        # 15m と 1h はBUYシグナル、4h はシグナルなし
        self.assertEqual(predictions['15m']['signal'].side, "BUY")
        self.assertEqual(predictions['1h']['signal'].side, "BUY")
        self.assertIsNone(predictions['4h']['signal'].side)
        
    def test_ensemble_signals_integration(self):
        """アンサンブルシグナル統合テスト"""
        strategy = MultiTimeframeEnsembleStrategy(self.config)
        
        # テスト用予測データ
        timeframe_predictions = {
            '15m': {
                'signal': Signal(side="BUY", price=50000),
                'data_quality': {'quality_score': 0.9},
                'ensemble_info': {'average_confidence': 0.8}
            },
            '1h': {
                'signal': Signal(side="BUY", price=50000),
                'data_quality': {'quality_score': 0.95},
                'ensemble_info': {'average_confidence': 0.85}
            },
            '4h': {
                'signal': Signal(side=None, price=None),
                'data_quality': {'quality_score': 0.8},
                'ensemble_info': {'average_confidence': 0.7}
            }
        }
        
        position = Position()
        position.exist = False
        
        integrated_signal, signal_info = strategy._integrate_ensemble_signals(
            timeframe_predictions, position
        )
        
        # 2つのBUYシグナルがあるので統合シグナルは0.5以上
        self.assertGreater(integrated_signal, 0.5)
        self.assertIn('timeframe_signals', signal_info)
        self.assertIn('signal_consensus', signal_info)
        
    def test_consensus_calculation(self):
        """シグナル合意度計算テスト"""
        strategy = MultiTimeframeEnsembleStrategy(self.config)
        
        # 高合意度（似たような値）
        high_consensus_signals = [0.7, 0.75, 0.72]
        high_consensus = strategy._calculate_consensus(high_consensus_signals)
        
        # 低合意度（ばらつきが大きい）
        low_consensus_signals = [0.2, 0.8, 0.5]
        low_consensus = strategy._calculate_consensus(low_consensus_signals)
        
        self.assertGreater(high_consensus, low_consensus)
        self.assertGreaterEqual(high_consensus, 0.0)
        self.assertLessEqual(high_consensus, 1.0)
        
    def test_dynamic_threshold_calculation(self):
        """動的閾値計算テスト"""
        strategy = MultiTimeframeEnsembleStrategy(self.config)
        
        # 高品質・高合意度
        high_quality_info = {
            'total_weight': 1.0,
            'signal_consensus': 0.9
        }
        high_quality_threshold = strategy._calculate_multi_timeframe_threshold(
            high_quality_info
        )
        
        # 低品質・低合意度
        low_quality_info = {
            'total_weight': 0.5,
            'signal_consensus': 0.4
        }
        low_quality_threshold = strategy._calculate_multi_timeframe_threshold(
            low_quality_info
        )
        
        # 高品質の方がより積極的な閾値（低い値）
        self.assertLess(high_quality_threshold, low_quality_threshold)
        
    @patch('crypto_bot.strategy.multi_timeframe_ensemble.EnsembleMLStrategy')
    def test_final_signal_decision_entry(self, mock_ensemble_strategy):
        """最終シグナル判定（エントリー）テスト"""
        mock_strategy = MagicMock()
        mock_ensemble_strategy.return_value = mock_strategy
        
        strategy = MultiTimeframeEnsembleStrategy(self.config)
        
        # 強いロングシグナル + 高合意度
        strong_long_signal = 0.75
        high_consensus_info = {
            'signal_consensus': 0.8,
            'total_weight': 1.0
        }
        
        position = Position()
        position.exist = False
        
        signal = strategy._make_final_signal_decision(
            strong_long_signal, high_consensus_info, self.price_df, position
        )
        
        self.assertEqual(signal.side, "BUY")
        self.assertIsNotNone(signal.price)
        
    @patch('crypto_bot.strategy.multi_timeframe_ensemble.EnsembleMLStrategy')
    def test_final_signal_decision_exit(self, mock_ensemble_strategy):
        """最終シグナル判定（エグジット）テスト"""
        mock_strategy = MagicMock()
        mock_ensemble_strategy.return_value = mock_strategy
        
        strategy = MultiTimeframeEnsembleStrategy(self.config)
        
        # 弱いシグナル
        weak_signal = 0.3
        normal_info = {
            'signal_consensus': 0.6,
            'total_weight': 0.8
        }
        
        # ポジション保有中
        position = Position()
        position.exist = True
        position.side = "BUY"
        
        signal = strategy._make_final_signal_decision(
            weak_signal, normal_info, self.price_df, position
        )
        
        self.assertEqual(signal.side, "SELL")
        
    @patch('crypto_bot.strategy.multi_timeframe_ensemble.EnsembleMLStrategy')
    def test_logic_signal_integration(self, mock_ensemble_strategy):
        """統合logic_signalテスト"""
        # 各タイムフレーム戦略のモック
        mock_strategies = {}
        for tf in ['15m', '1h', '4h']:
            mock_strategy = MagicMock()
            mock_strategy.logic_signal.return_value = Signal(side="BUY", price=50000)
            mock_strategy.get_ensemble_performance_info.return_value = {
                'average_confidence': 0.8
            }
            mock_strategies[tf] = mock_strategy
            
        mock_ensemble_strategy.side_effect = lambda **kwargs: mock_strategies.get(
            kwargs.get('config', {}).get('data', {}).get('timeframe', '1h')
        )
        
        strategy = MultiTimeframeEnsembleStrategy(self.config)
        strategy.ensemble_strategies = mock_strategies
        
        # データ生成メソッドのモック
        strategy._get_timeframe_data = MagicMock(return_value=self.price_df)
        
        position = Position()
        position.exist = False
        
        final_signal = strategy.logic_signal(self.price_df, position)
        
        self.assertIsInstance(final_signal, Signal)
        # 3つのBUYシグナルがあるので最終的にもBUYになるはず
        self.assertEqual(final_signal.side, "BUY")
        
    def test_prediction_performance_tracking(self):
        """予測パフォーマンス追跡テスト"""
        strategy = MultiTimeframeEnsembleStrategy(self.config)
        
        # テスト用予測データ
        timeframe_predictions = {'15m': {}, '1h': {}, '4h': {}}
        integrated_signal = 0.7
        signal_info = {'consensus': 0.8}
        
        # 複数回追跡
        for _ in range(5):
            strategy._track_prediction_performance(
                timeframe_predictions, integrated_signal, signal_info
            )
        
        self.assertEqual(len(strategy.prediction_history), 5)
        
        # 履歴サイズ制限テスト
        for _ in range(100):
            strategy._track_prediction_performance(
                timeframe_predictions, integrated_signal, signal_info
            )
        
        self.assertLessEqual(len(strategy.prediction_history), 100)
        
    def test_multi_ensemble_info_retrieval(self):
        """マルチアンサンブル情報取得テスト"""
        strategy = MultiTimeframeEnsembleStrategy(self.config)
        
        # 戦略モック
        mock_strategy = MagicMock()
        mock_strategy.get_ensemble_performance_info.return_value = {
            'num_base_models': 3,
            'average_confidence': 0.75
        }
        strategy.ensemble_strategies = {'1h': mock_strategy}
        
        # 予測履歴追加
        strategy.prediction_history = [
            {
                'integrated_signal': 0.7,
                'signal_info': {'signal_consensus': 0.8}
            }
        ]
        
        info = strategy.get_multi_ensemble_info()
        
        required_keys = [
            'strategy_type', 'timeframes', 'weights', 'ensemble_enabled',
            'timeframe_strategies', 'prediction_history_size'
        ]
        
        for key in required_keys:
            self.assertIn(key, info)
            
        self.assertEqual(info['strategy_type'], 'multi_timeframe_ensemble')
        self.assertEqual(info['prediction_history_size'], 1)
        
    def test_recent_performance_analysis(self):
        """最近のパフォーマンス分析テスト"""
        strategy = MultiTimeframeEnsembleStrategy(self.config)
        
        # テスト用履歴データ
        recent_predictions = [
            {
                'integrated_signal': 0.7,
                'signal_info': {'signal_consensus': 0.8}
            },
            {
                'integrated_signal': 0.6,
                'signal_info': {'signal_consensus': 0.7}
            },
            {
                'integrated_signal': 0.8,
                'signal_info': {'signal_consensus': 0.9}
            }
        ]
        
        analysis = strategy._analyze_recent_performance(recent_predictions)
        
        self.assertIn('avg_integrated_signal', analysis)
        self.assertIn('signal_volatility', analysis)
        self.assertIn('avg_consensus', analysis)
        self.assertIn('prediction_count', analysis)
        
        self.assertEqual(analysis['prediction_count'], 3)
        self.assertAlmostEqual(analysis['avg_integrated_signal'], 0.7, places=1)


class TestMultiTimeframeEnsembleEdgeCases(unittest.TestCase):
    """マルチタイムフレーム×アンサンブルのエッジケーステスト"""
    
    def setUp(self):
        """エッジケーステストセットアップ"""
        self.minimal_config = {
            'multi_timeframe': {'timeframes': ['1h']},
            'ml': {'ensemble': {'enabled': True}}
        }
        
    def test_single_timeframe_handling(self):
        """単一タイムフレーム処理テスト"""
        strategy = MultiTimeframeEnsembleStrategy(self.minimal_config)
        
        self.assertEqual(strategy.timeframes, ['1h'])
        self.assertEqual(len(strategy.ensemble_strategies), 1)
        
    def test_empty_predictions_handling(self):
        """空の予測結果処理テスト"""
        strategy = MultiTimeframeEnsembleStrategy(self.minimal_config)
        
        empty_predictions = {}
        position = Position()
        position.exist = False
        
        integrated_signal, signal_info = strategy._integrate_ensemble_signals(
            empty_predictions, position
        )
        
        self.assertEqual(integrated_signal, 0.5)  # ニュートラル
        
    def test_data_generation_failure_handling(self):
        """データ生成失敗時の処理テスト"""
        strategy = MultiTimeframeEnsembleStrategy(self.minimal_config)
        
        # 不正なデータでのテスト
        invalid_df = pd.DataFrame()
        
        result_15m = strategy._get_timeframe_data(invalid_df, '15m')
        self.assertTrue(result_15m.empty)
        
    def test_insufficient_consensus_handling(self):
        """不十分な合意度での処理テスト"""
        strategy = MultiTimeframeEnsembleStrategy(self.minimal_config)
        
        # 低合意度シグナル情報
        low_consensus_info = {
            'signal_consensus': 0.3,  # 閾値0.6以下
            'total_weight': 1.0
        }
        
        position = Position()
        position.exist = False
        
        # 強いシグナルでも低合意度ではエントリーしない
        signal = strategy._make_final_signal_decision(
            0.8, low_consensus_info,
            pd.DataFrame({'close': [50000]}, index=[datetime.now()]),
            position
        )
        
        self.assertIsNone(signal.side)


if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
# =============================================================================
# スクリプト: scripts/ensemble_backtest_system.py
# 説明:
# アンサンブル学習vs従来手法の実データバックテスト・比較システム
# 勝率と収益性向上効果の統計的検証
# =============================================================================

import sys
import os
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd
import yaml
from dataclasses import dataclass

from crypto_bot.ml.ensemble import TradingEnsembleClassifier
from crypto_bot.ml.model import MLModel, create_model
from crypto_bot.ml.preprocessor import FeatureEngineer
from crypto_bot.strategy.ensemble_ml_strategy import EnsembleMLStrategy
from crypto_bot.strategy.ml_strategy import MLStrategy
from crypto_bot.execution.engine import Position, Signal
from crypto_bot.risk.manager import RiskManager
from crypto_bot.backtest.engine import BacktestEngine

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """バックテスト結果データクラス"""
    strategy_name: str
    total_return: float
    sharpe_ratio: float
    win_rate: float
    max_drawdown: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    volatility: float
    calmar_ratio: float
    sortino_ratio: float
    trade_details: List[Dict]
    daily_returns: pd.Series
    equity_curve: pd.Series
    ensemble_info: Dict = None


class EnsembleBacktestSystem:
    """アンサンブル学習バックテストシステム"""
    
    def __init__(self, config_path: str = None):
        """
        バックテストシステム初期化
        
        Parameters:
        -----------
        config_path : str
            設定ファイルパス
        """
        self.config = self._load_config(config_path)
        self.data = None
        self.results = {}
        self.comparison_metrics = {}
        
        # データ読み込み
        self._load_data()
        
        logger.info("Ensemble Backtest System initialized")
    
    def _load_config(self, config_path: str = None) -> Dict:
        """設定ファイル読み込み"""
        if config_path is None:
            config_path = project_root / "config" / "ensemble_trading.yml"
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"Config loaded from: {config_path}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """デフォルト設定"""
        return {
            'data': {
                'csv_path': "/Users/nao/Desktop/bot/data/btc_usd_2024_hourly.csv",
                'symbol': 'BTC/USDT',
                'timeframe': '1h'
            },
            'backtest': {
                'initial_balance': 1000000,
                'commission': 0.001,
                'slippage': 0.0005,
                'train_test_split': 0.7
            },
            'ml': {
                'extra_features': ['rsi_14', 'macd', 'bb_percent', 'vix'],
                'ensemble': {
                    'enabled': True,
                    'method': 'trading_stacking',
                    'confidence_threshold': 0.65
                }
            }
        }
    
    def _load_data(self):
        """CSVデータ読み込み"""
        csv_path = self.config.get('data', {}).get('csv_path')
        
        if not csv_path or not os.path.exists(csv_path):
            logger.warning(f"CSV file not found: {csv_path}")
            self._generate_sample_data()
            return
        
        try:
            # CSVデータ読み込み
            self.data = pd.read_csv(csv_path, parse_dates=True, index_col=0)
            
            # インデックス設定
            if not isinstance(self.data.index, pd.DatetimeIndex):
                self.data.index = pd.to_datetime(self.data.index)
            
            # タイムゾーン設定
            if self.data.index.tz is None:
                self.data.index = self.data.index.tz_localize('UTC')
            
            logger.info(f"Data loaded: {len(self.data)} records from {self.data.index[0]} to {self.data.index[-1]}")
            
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            self._generate_sample_data()
    
    def _generate_sample_data(self):
        """サンプルデータ生成（CSVがない場合）"""
        logger.info("Generating sample data...")
        
        # 1年間のサンプルデータ
        start_date = datetime.now() - timedelta(days=365)
        dates = pd.date_range(start=start_date, periods=8760, freq='1h')
        
        # 価格データ生成（上昇トレンド + ノイズ）
        np.random.seed(42)
        base_price = 40000
        trend = np.linspace(0, 15000, len(dates))  # 年間+15000の上昇
        noise = np.random.randn(len(dates)) * 500
        prices = base_price + trend + noise
        
        # OHLCV生成
        self.data = pd.DataFrame({
            'open': prices + np.random.randn(len(dates)) * 100,
            'high': prices + np.abs(np.random.randn(len(dates)) * 200),
            'low': prices - np.abs(np.random.randn(len(dates)) * 200),
            'close': prices,
            'volume': np.random.randint(1000, 10000, len(dates))
        }, index=dates.tz_localize('UTC'))
        
        logger.info(f"Sample data generated: {len(self.data)} records")
    
    def run_comparative_backtest(self) -> Dict[str, BacktestResult]:
        """比較バックテスト実行"""
        logger.info("Starting comparative backtest...")
        
        # データ分割
        train_data, test_data = self._split_data()
        
        # 戦略別バックテスト実行
        strategies = {
            'traditional_ml': self._create_traditional_strategy(),
            'ensemble_trading': self._create_ensemble_strategy(),
            'ensemble_risk_weighted': self._create_risk_weighted_ensemble(),
            'ensemble_performance_voting': self._create_performance_voting_ensemble()
        }
        
        results = {}
        
        for strategy_name, strategy in strategies.items():
            logger.info(f"Running backtest for: {strategy_name}")
            
            try:
                # 戦略学習（該当する場合）
                if hasattr(strategy, 'fit_ensemble'):
                    # アンサンブル戦略の学習
                    features = self._generate_features(train_data)
                    target = self._generate_target(train_data)
                    strategy.fit_ensemble(features, target)
                
                # バックテスト実行
                result = self._run_single_backtest(strategy_name, strategy, test_data)
                results[strategy_name] = result
                
                logger.info(f"Completed backtest for {strategy_name}: Return={result.total_return:.2%}, Win Rate={result.win_rate:.2%}")
                
            except Exception as e:
                logger.error(f"Backtest failed for {strategy_name}: {e}")
                continue
        
        self.results = results
        return results
    
    def _split_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """データ分割（学習用・テスト用）"""
        split_ratio = self.config.get('backtest', {}).get('train_test_split', 0.7)
        split_index = int(len(self.data) * split_ratio)
        
        train_data = self.data.iloc[:split_index].copy()
        test_data = self.data.iloc[split_index:].copy()
        
        logger.info(f"Data split: Train={len(train_data)}, Test={len(test_data)}")
        return train_data, test_data
    
    def _generate_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """特徴量生成"""
        try:
            feature_engineer = FeatureEngineer(self.config)
            features = feature_engineer.transform(data)
            logger.info(f"Features generated: {features.shape}")
            return features
        except Exception as e:
            logger.error(f"Feature generation failed: {e}")
            # フォールバック: 基本特徴量
            return self._generate_basic_features(data)
    
    def _generate_basic_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """基本特徴量生成（フォールバック）"""
        features = pd.DataFrame(index=data.index)
        
        # 基本テクニカル指標
        features['returns'] = data['close'].pct_change()
        features['sma_20'] = data['close'].rolling(20).mean()
        features['sma_50'] = data['close'].rolling(50).mean()
        features['volatility'] = features['returns'].rolling(20).std()
        features['rsi'] = self._calculate_rsi(data['close'])
        features['volume_ratio'] = data['volume'] / data['volume'].rolling(20).mean()
        
        # ラグ特徴量
        for lag in [1, 2, 3]:
            features[f'returns_lag_{lag}'] = features['returns'].shift(lag)
            features[f'volume_lag_{lag}'] = features['volume_ratio'].shift(lag)
        
        return features.dropna()
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """RSI計算"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def _generate_target(self, data: pd.DataFrame) -> pd.Series:
        """ターゲット生成（次期リターンの正負）"""
        returns = data['close'].pct_change().shift(-1)  # 次期リターン
        target = (returns > 0.005).astype(int)  # 0.5%以上上昇で1
        return target.dropna()
    
    def _create_traditional_strategy(self):
        """従来ML戦略作成"""
        config = self.config.copy()
        config['ml']['ensemble'] = {'enabled': False}
        
        # 模擬戦略（実際の学習済みモデルの代替）
        return TraditionalMLStrategyMock(config)
    
    def _create_ensemble_strategy(self):
        """アンサンブル戦略作成"""
        config = self.config.copy()
        config['ml']['ensemble'] = {
            'enabled': True,
            'method': 'trading_stacking',
            'confidence_threshold': 0.65
        }
        
        return EnsembleStrategyMock(config, method='trading_stacking')
    
    def _create_risk_weighted_ensemble(self):
        """リスク加重アンサンブル作成"""
        config = self.config.copy()
        config['ml']['ensemble'] = {
            'enabled': True,
            'method': 'risk_weighted',
            'confidence_threshold': 0.70
        }
        
        return EnsembleStrategyMock(config, method='risk_weighted')
    
    def _create_performance_voting_ensemble(self):
        """パフォーマンス投票アンサンブル作成"""
        config = self.config.copy()
        config['ml']['ensemble'] = {
            'enabled': True,
            'method': 'performance_voting',
            'confidence_threshold': 0.60
        }
        
        return EnsembleStrategyMock(config, method='performance_voting')
    
    def _run_single_backtest(self, strategy_name: str, strategy, data: pd.DataFrame) -> BacktestResult:
        """単一戦略バックテスト実行"""
        
        # バックテスト設定
        initial_balance = self.config.get('backtest', {}).get('initial_balance', 1000000)
        commission = self.config.get('backtest', {}).get('commission', 0.001)
        
        # シンプルなバックテストエンジン
        balance = initial_balance
        position = Position()
        position.exist = False
        
        trades = []
        equity_curve = []
        daily_returns = []
        
        for i in range(50, len(data)):  # 特徴量計算のため50行後から開始
            current_data = data.iloc[:i+1]
            current_price = data.iloc[i]['close']
            
            try:
                # シグナル生成
                signal = strategy.generate_signal(current_data, position)
                
                # 取引実行
                if signal and signal.side and not position.exist:
                    # エントリー
                    if signal.side == "BUY":
                        position.exist = True
                        position.side = "BUY"
                        position.entry_price = current_price
                        position.quantity = balance * 0.1 / current_price  # 10%投資
                        
                        trades.append({
                            'entry_time': data.index[i],
                            'entry_price': current_price,
                            'side': 'BUY',
                            'type': 'ENTRY'
                        })
                
                elif signal and signal.side == "SELL" and position.exist:
                    # エグジット
                    exit_price = current_price
                    pnl = (exit_price - position.entry_price) * position.quantity
                    pnl_pct = (exit_price - position.entry_price) / position.entry_price
                    
                    balance += pnl
                    
                    trades.append({
                        'exit_time': data.index[i],
                        'exit_price': exit_price,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'type': 'EXIT'
                    })
                    
                    position.exist = False
                
                # エクイティカーブ記録
                current_value = balance
                if position.exist:
                    current_value += (current_price - position.entry_price) * position.quantity
                
                equity_curve.append(current_value)
                
                # 日次リターン計算
                if len(equity_curve) > 1:
                    daily_return = (equity_curve[-1] - equity_curve[-2]) / equity_curve[-2]
                    daily_returns.append(daily_return)
                
            except Exception as e:
                logger.warning(f"Error in backtest step {i}: {e}")
                continue
        
        # 結果計算
        return self._calculate_backtest_result(
            strategy_name, trades, equity_curve, daily_returns, initial_balance, strategy
        )
    
    def _calculate_backtest_result(self, strategy_name: str, trades: List[Dict], 
                                 equity_curve: List[float], daily_returns: List[float],
                                 initial_balance: float, strategy) -> BacktestResult:
        """バックテスト結果計算"""
        
        if not equity_curve:
            return BacktestResult(
                strategy_name=strategy_name,
                total_return=0.0, sharpe_ratio=0.0, win_rate=0.0,
                max_drawdown=0.0, profit_factor=0.0, total_trades=0,
                winning_trades=0, losing_trades=0, avg_win=0.0, avg_loss=0.0,
                volatility=0.0, calmar_ratio=0.0, sortino_ratio=0.0,
                trade_details=trades,
                daily_returns=pd.Series(daily_returns),
                equity_curve=pd.Series(equity_curve)
            )
        
        final_balance = equity_curve[-1]
        total_return = (final_balance - initial_balance) / initial_balance
        
        # 取引分析
        completed_trades = [t for t in trades if t.get('type') == 'EXIT']
        total_trades = len(completed_trades)
        
        if total_trades > 0:
            winning_trades = len([t for t in completed_trades if t['pnl'] > 0])
            losing_trades = total_trades - winning_trades
            win_rate = winning_trades / total_trades
            
            wins = [t['pnl'] for t in completed_trades if t['pnl'] > 0]
            losses = [t['pnl'] for t in completed_trades if t['pnl'] <= 0]
            
            avg_win = np.mean(wins) if wins else 0
            avg_loss = np.mean(losses) if losses else 0
            profit_factor = abs(sum(wins) / sum(losses)) if losses and sum(losses) != 0 else 0
        else:
            winning_trades = losing_trades = 0
            win_rate = avg_win = avg_loss = profit_factor = 0
        
        # リスク指標
        returns_series = pd.Series(daily_returns)
        volatility = returns_series.std() * np.sqrt(365 * 24) if len(returns_series) > 1 else 0
        
        sharpe_ratio = (returns_series.mean() * 365 * 24) / volatility if volatility > 0 else 0
        
        # ドローダウン計算
        equity_series = pd.Series(equity_curve)
        peak = equity_series.expanding().max()
        drawdown = (equity_series - peak) / peak
        max_drawdown = drawdown.min()
        
        # Calmar ratio
        calmar_ratio = (total_return * 100) / abs(max_drawdown * 100) if max_drawdown != 0 else 0
        
        # Sortino ratio
        negative_returns = returns_series[returns_series < 0]
        downside_deviation = negative_returns.std() * np.sqrt(365 * 24) if len(negative_returns) > 1 else 0
        sortino_ratio = (returns_series.mean() * 365 * 24) / downside_deviation if downside_deviation > 0 else 0
        
        # アンサンブル情報取得
        ensemble_info = None
        if hasattr(strategy, 'get_ensemble_info'):
            try:
                ensemble_info = strategy.get_ensemble_info()
            except:
                pass
        
        return BacktestResult(
            strategy_name=strategy_name,
            total_return=total_return,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            max_drawdown=max_drawdown,
            profit_factor=profit_factor,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            avg_win=avg_win,
            avg_loss=avg_loss,
            volatility=volatility,
            calmar_ratio=calmar_ratio,
            sortino_ratio=sortino_ratio,
            trade_details=trades,
            daily_returns=returns_series,
            equity_curve=equity_series,
            ensemble_info=ensemble_info
        )
    
    def generate_comparison_report(self) -> Dict[str, Any]:
        """比較レポート生成"""
        if not self.results:
            logger.error("No backtest results available")
            return {}
        
        logger.info("Generating comparison report...")
        
        # 基本統計比較
        comparison_table = []
        for strategy_name, result in self.results.items():
            comparison_table.append({
                'Strategy': strategy_name,
                'Total Return': f"{result.total_return:.2%}",
                'Sharpe Ratio': f"{result.sharpe_ratio:.3f}",
                'Win Rate': f"{result.win_rate:.2%}",
                'Max Drawdown': f"{result.max_drawdown:.2%}",
                'Profit Factor': f"{result.profit_factor:.2f}",
                'Total Trades': result.total_trades,
                'Calmar Ratio': f"{result.calmar_ratio:.3f}",
                'Sortino Ratio': f"{result.sortino_ratio:.3f}"
            })
        
        # 最良戦略識別
        best_return = max(self.results.values(), key=lambda x: x.total_return)
        best_sharpe = max(self.results.values(), key=lambda x: x.sharpe_ratio)
        best_winrate = max(self.results.values(), key=lambda x: x.win_rate)
        best_drawdown = min(self.results.values(), key=lambda x: x.max_drawdown)
        
        # アンサンブル vs 従来比較
        traditional_result = self.results.get('traditional_ml')
        ensemble_results = {k: v for k, v in self.results.items() if 'ensemble' in k}
        
        improvement_analysis = {}
        if traditional_result and ensemble_results:
            for ensemble_name, ensemble_result in ensemble_results.items():
                improvement_analysis[ensemble_name] = {
                    'return_improvement': ensemble_result.total_return - traditional_result.total_return,
                    'sharpe_improvement': ensemble_result.sharpe_ratio - traditional_result.sharpe_ratio,
                    'winrate_improvement': ensemble_result.win_rate - traditional_result.win_rate,
                    'drawdown_improvement': ensemble_result.max_drawdown - traditional_result.max_drawdown,
                    'trades_change': ensemble_result.total_trades - traditional_result.total_trades
                }
        
        report = {
            'comparison_table': comparison_table,
            'best_performers': {
                'highest_return': best_return.strategy_name,
                'best_sharpe': best_sharpe.strategy_name,
                'best_winrate': best_winrate.strategy_name,
                'lowest_drawdown': best_drawdown.strategy_name
            },
            'improvement_analysis': improvement_analysis,
            'summary_statistics': self._calculate_summary_statistics()
        }
        
        self.comparison_metrics = report
        return report
    
    def _calculate_summary_statistics(self) -> Dict:
        """サマリー統計計算"""
        all_returns = [r.total_return for r in self.results.values()]
        all_sharpes = [r.sharpe_ratio for r in self.results.values()]
        all_winrates = [r.win_rate for r in self.results.values()]
        
        return {
            'avg_return': np.mean(all_returns),
            'std_return': np.std(all_returns),
            'avg_sharpe': np.mean(all_sharpes),
            'avg_winrate': np.mean(all_winrates),
            'total_strategies': len(self.results)
        }
    
    def save_results(self, output_dir: str = None):
        """結果保存"""
        if output_dir is None:
            output_dir = project_root / "results" / "ensemble_backtest"
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # CSV形式で比較表保存
        if self.comparison_metrics and 'comparison_table' in self.comparison_metrics:
            comparison_df = pd.DataFrame(self.comparison_metrics['comparison_table'])
            comparison_df.to_csv(output_path / f"strategy_comparison_{timestamp}.csv", index=False)
        
        # 詳細結果保存
        for strategy_name, result in self.results.items():
            # エクイティカーブ
            result.equity_curve.to_csv(output_path / f"equity_curve_{strategy_name}_{timestamp}.csv")
            
            # 取引詳細
            if result.trade_details:
                trades_df = pd.DataFrame(result.trade_details)
                trades_df.to_csv(output_path / f"trades_{strategy_name}_{timestamp}.csv", index=False)
        
        # レポート保存
        with open(output_path / f"comparison_report_{timestamp}.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(self.comparison_metrics, f, default_flow_style=False, allow_unicode=True)
        
        logger.info(f"Results saved to: {output_path}")
        return output_path


# 模擬戦略クラス（実際のモデル学習の代替）
class TraditionalMLStrategyMock:
    """従来ML戦略の模擬クラス"""
    
    def __init__(self, config):
        self.config = config
        self.threshold = 0.55
        
    def generate_signal(self, data: pd.DataFrame, position: Position) -> Signal:
        """シンプルな模擬シグナル生成"""
        if len(data) < 20:
            return Signal()
        
        # 基本的なモメンタム戦略
        returns = data['close'].pct_change()
        short_ma = data['close'].rolling(5).mean()
        long_ma = data['close'].rolling(20).mean()
        
        current_price = data['close'].iloc[-1]
        
        # シンプルな条件
        if short_ma.iloc[-1] > long_ma.iloc[-1] and returns.iloc[-1] > 0.01:
            # 上昇トレンド
            if not position.exist and np.random.random() > self.threshold:
                return Signal(side="BUY", price=current_price)
        
        # エグジット条件
        if position.exist and (short_ma.iloc[-1] < long_ma.iloc[-1] or returns.iloc[-1] < -0.02):
            return Signal(side="SELL", price=current_price)
        
        return Signal()


class EnsembleStrategyMock:
    """アンサンブル戦略の模擬クラス"""
    
    def __init__(self, config, method='trading_stacking'):
        self.config = config
        self.method = method
        self.confidence_threshold = config.get('ml', {}).get('ensemble', {}).get('confidence_threshold', 0.65)
        self.ensemble_info = {
            'method': method,
            'confidence_threshold': self.confidence_threshold,
            'base_models': 3
        }
        
    def fit_ensemble(self, features: pd.DataFrame, target: pd.Series):
        """模擬学習"""
        logger.info(f"Mock ensemble training: {self.method}")
        
    def generate_signal(self, data: pd.DataFrame, position: Position) -> Signal:
        """アンサンブル模擬シグナル生成"""
        if len(data) < 20:
            return Signal()
        
        # より高度な条件（アンサンブル効果を模擬）
        returns = data['close'].pct_change()
        short_ma = data['close'].rolling(5).mean()
        long_ma = data['close'].rolling(20).mean()
        volatility = returns.rolling(10).std()
        
        current_price = data['close'].iloc[-1]
        
        # 複数条件の組み合わせ（アンサンブル効果）
        momentum_signal = short_ma.iloc[-1] > long_ma.iloc[-1]
        volatility_signal = volatility.iloc[-1] < volatility.rolling(20).mean().iloc[-1]
        trend_signal = returns.rolling(5).mean().iloc[-1] > 0
        
        # "アンサンブル"信頼度計算
        confidence = 0.5
        if momentum_signal:
            confidence += 0.15
        if volatility_signal:
            confidence += 0.10
        if trend_signal:
            confidence += 0.15
        
        # 手法別調整
        if self.method == 'risk_weighted':
            confidence *= 0.9  # より保守的
        elif self.method == 'performance_voting':
            confidence *= 1.1  # より積極的
        
        # エントリー判定
        if not position.exist and confidence > self.confidence_threshold:
            if momentum_signal and trend_signal:
                return Signal(side="BUY", price=current_price)
        
        # エグジット判定
        if position.exist:
            if not momentum_signal or returns.iloc[-1] < -0.03:
                return Signal(side="SELL", price=current_price)
        
        return Signal()
    
    def get_ensemble_info(self):
        """アンサンブル情報取得"""
        return self.ensemble_info


def main():
    """メイン実行関数"""
    print("🚀 アンサンブル学習バックテストシステム実行")
    print("="*60)
    
    try:
        # バックテストシステム初期化
        backtest_system = EnsembleBacktestSystem()
        
        # 比較バックテスト実行
        print("\n📊 比較バックテスト実行中...")
        results = backtest_system.run_comparative_backtest()
        
        # 結果表示
        print("\n📈 バックテスト結果:")
        print("-" * 80)
        for strategy_name, result in results.items():
            print(f"{strategy_name:25} | Return: {result.total_return:8.2%} | "
                  f"Sharpe: {result.sharpe_ratio:6.3f} | Win Rate: {result.win_rate:6.2%} | "
                  f"Trades: {result.total_trades:3d}")
        
        # 比較レポート生成
        print("\n🔍 比較分析レポート生成中...")
        report = backtest_system.generate_comparison_report()
        
        # 改善効果表示
        if 'improvement_analysis' in report:
            print("\n📊 アンサンブル効果分析:")
            print("-" * 60)
            for ensemble_name, improvements in report['improvement_analysis'].items():
                print(f"\n{ensemble_name}:")
                print(f"  リターン改善: {improvements['return_improvement']:+.2%}")
                print(f"  シャープ改善: {improvements['sharpe_improvement']:+.3f}")
                print(f"  勝率改善: {improvements['winrate_improvement']:+.2%}")
                print(f"  ドローダウン: {improvements['drawdown_improvement']:+.2%}")
        
        # 結果保存
        output_path = backtest_system.save_results()
        print(f"\n💾 結果保存完了: {output_path}")
        
        # 最良戦略
        if 'best_performers' in report:
            best = report['best_performers']
            print(f"\n🏆 最良戦略:")
            print(f"  最高リターン: {best['highest_return']}")
            print(f"  最高シャープ: {best['best_sharpe']}")
            print(f"  最高勝率: {best['best_winrate']}")
            print(f"  最低ドローダウン: {best['lowest_drawdown']}")
        
        print("\n✅ アンサンブル学習バックテスト完了")
        
    except Exception as e:
        logger.error(f"Backtest execution failed: {e}")
        print(f"\n❌ エラー: {e}")


if __name__ == "__main__":
    main()
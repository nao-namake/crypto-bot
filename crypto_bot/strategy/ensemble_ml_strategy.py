# =============================================================================
# ファイル名: crypto_bot/strategy/ensemble_ml_strategy.py
# 説明:
# 取引特化型アンサンブル学習と既存MLStrategyの統合アダプター
# 勝率と収益性向上を重視した設計で既存システムとの完全互換性を提供
# =============================================================================

from __future__ import annotations

import logging
from typing import Dict, Any

import numpy as np
import pandas as pd

from crypto_bot.execution.engine import Position, Signal
from crypto_bot.ml.ensemble import create_trading_ensemble
from crypto_bot.strategy.ml_strategy import MLStrategy

logger = logging.getLogger(__name__)


class EnsembleMLStrategy(MLStrategy):
    """
    取引特化型アンサンブル学習統合戦略
    
    既存MLStrategyを継承し、アンサンブル学習機能を追加
    勝率と収益性の向上に焦点を当てた実装
    """
    
    def __init__(
        self, model_path: str = None, threshold: float = None, config: dict = None
    ):
        """
        アンサンブルML戦略の初期化
        
        Parameters:
        -----------
        model_path : str, optional
            既存モデルパス（互換性維持）
        threshold : float, optional
            基本閾値
        config : dict
            設定辞書（アンサンブル設定を含む）
        """
        self.config = config or {}
        
        # アンサンブル設定確認
        ensemble_config = self.config.get('ml', {}).get('ensemble', {})
        self.ensemble_enabled = ensemble_config.get('enabled', False)
        
        if self.ensemble_enabled:
            logger.info("Initializing Trading Ensemble ML Strategy")
            
            # 取引特化型アンサンブルモデル作成
            try:
                self.ensemble_model = create_trading_ensemble(self.config)
                self.is_ensemble = True
                logger.info("Trading ensemble model created successfully")
            except Exception as e:
                logger.error(f"Failed to create trading ensemble: {e}")
                self.ensemble_enabled = False
                self.is_ensemble = False
                
        if not self.ensemble_enabled:
            # フォールバック: 既存MLStrategy使用
            logger.info("Falling back to standard MLStrategy")
            super().__init__(model_path, threshold, config)
            return
        
        # 基本設定（MLStrategyと同様）
        if threshold is not None:
            self.base_threshold = threshold
        else:
            self.base_threshold = self.config.get("threshold", 0.45)  # より保守的
            
        logger.info(
            f"Ensemble ML Strategy initialized with threshold = {self.base_threshold}"
        )
        
        # 既存MLStrategyの初期化処理を継承
        self._initialize_components()
        
        # アンサンブル特有の設定
        self._initialize_ensemble_settings()
        
    def _initialize_components(self):
        """既存MLStrategyコンポーネントの初期化"""
        from crypto_bot.ml.preprocessor import FeatureEngineer
        from crypto_bot.indicator.calculator import IndicatorCalculator
        from sklearn.preprocessing import StandardScaler
        
        try:
            from crypto_bot.data.vix_fetcher import VIXDataFetcher
            self.vix_fetcher = VIXDataFetcher()
            self.vix_available = True
        except ImportError:
            self.vix_fetcher = None
            self.vix_available = False
            
        self.feature_engineer = FeatureEngineer(self.config)
        self.scaler = StandardScaler()
        self.indicator_calc = IndicatorCalculator()
        
        # パフォーマンス追跡
        self.recent_signals = []
        self.max_signal_history = 50
        self.vix_data_cache = None
        self.vix_cache_time = None
        
    def _initialize_ensemble_settings(self):
        """アンサンブル特有の設定初期化"""
        ensemble_config = self.config.get('ml', {}).get('ensemble', {})
        
        # 取引特化型設定
        self.trading_confidence_threshold = ensemble_config.get(
            'confidence_threshold', 0.65
        )
        self.risk_adjustment_enabled = ensemble_config.get('risk_adjustment', True)
        
        # 動的閾値設定
        dynamic_config = self.config.get('ml', {}).get('dynamic_threshold', {})
        self.dynamic_threshold_enabled = dynamic_config.get('enabled', True)
        self.vix_adjustment_enabled = dynamic_config.get(
            'vix_adjustment', True
        )
        
        # 市場レジーム設定
        self.vix_levels = dynamic_config.get('vix_levels', {
            'low_vix': {'threshold': 15, 'adjustment': -0.05},
            'medium_vix': {'threshold': 25, 'adjustment': 0.0},
            'high_vix': {'threshold': 35, 'adjustment': 0.1},
            'extreme_vix': {'threshold': 50, 'adjustment': 0.2}
        })
        
        logger.info(
            f"Ensemble settings: "
            f"confidence_threshold={self.trading_confidence_threshold}, "
            f"risk_adjustment={self.risk_adjustment_enabled}, "
            f"dynamic_threshold={self.dynamic_threshold_enabled}"
        )
    
    def fit_ensemble(self, X: pd.DataFrame, y: pd.Series) -> 'EnsembleMLStrategy':
        """アンサンブルモデルの学習"""
        if not self.ensemble_enabled:
            logger.warning("Ensemble not enabled, cannot fit ensemble model")
            return self
            
        logger.info("Training trading ensemble model")
        
        try:
            # 特徴量エンジニアリング
            feat_df = self.feature_engineer.transform(X)
            
            # スケーリング
            scaled = self.scaler.fit_transform(feat_df.values)
            X_scaled = pd.DataFrame(
                scaled, index=feat_df.index, columns=feat_df.columns
            )
            
            # アンサンブルモデル学習
            self.ensemble_model.fit(X_scaled, y)
            
            logger.info("Trading ensemble model training completed")
            
            # 学習後情報の取得
            ensemble_info = self.ensemble_model.get_trading_ensemble_info()
            logger.info(f"Ensemble Info: {ensemble_info}")
            
        except Exception as e:
            logger.error(f"Ensemble training failed: {e}")
            self.ensemble_enabled = False
            
        return self
    
    def logic_signal(self, price_df: pd.DataFrame, position: Position) -> Signal:
        """
        アンサンブル統合シグナル生成
        
        既存MLStrategy.logic_signalを拡張してアンサンブル機能を統合
        """
        logger.debug("Ensemble ML Strategy: Generating signal")
        
        if not self.ensemble_enabled:
            # フォールバック: 既存MLStrategy使用
            return super().logic_signal(price_df, position)
        
        # 市場コンテキスト生成
        market_context = self._generate_market_context(price_df)
        
        # 特徴量エンジニアリング
        feat_df = self.feature_engineer.transform(price_df)
        if feat_df.empty:
            logger.warning("Empty features DataFrame after transformation")
            return Signal()
        
        # スケーリング
        scaled = self.scaler.fit_transform(feat_df.values)
        X_df = pd.DataFrame(scaled, index=feat_df.index, columns=feat_df.columns)
        last_X = X_df.iloc[[-1]]
        
        current_price = float(price_df["close"].iloc[-1])
        
        try:
            # アンサンブル予測（取引特化型信頼度付き）
            predictions, probabilities, confidence_scores, trading_info = \
                self.ensemble_model.predict_with_trading_confidence(
                    last_X, market_context
                )
                
            # 予測結果の詳細
            prediction = predictions[0]
            probability = probabilities[0, 1]  # 正例クラス確率
            confidence = confidence_scores[0]
            dynamic_threshold = trading_info['dynamic_threshold']
            
            logger.info(
                f"Ensemble Prediction: prob={probability:.4f}, "
                f"confidence={confidence:.4f}, threshold={dynamic_threshold:.4f}, "
                f"market_regime={trading_info['market_regime']}"
            )
            
            # ポジション管理
            position_exists = position is not None and position.exist
            
            if position_exists:
                # エグジット判定（リスク調整型）
                exit_threshold = self._calculate_exit_threshold(
                    trading_info, confidence
                )
                
                if probability < exit_threshold:
                    logger.info(
                        f"Ensemble EXIT signal: prob={probability:.4f} < "
                        f"{exit_threshold:.4f}"
                    )
                    signal = Signal(side="SELL", price=current_price)
                    self._update_signal_history(
                        "EXIT", probability, confidence, trading_info
                    )
                    return signal
                    
                return Signal()  # ホールド
            
            else:
                # エントリー判定（信頼度ベース）
                if prediction == 1 and confidence >= self.trading_confidence_threshold:
                    # 高信頼度ロングシグナル
                    logger.info(
                        f"Ensemble LONG signal: prob={probability:.4f}, "
                        f"confidence={confidence:.4f}"
                    )
                    signal = Signal(side="BUY", price=current_price)
                    self._update_signal_history(
                        "ENTRY_LONG", probability, confidence, trading_info
                    )
                    return signal
                    
                elif (probability < (1.0 - dynamic_threshold) and
                      confidence >= self.trading_confidence_threshold):
                    # 高信頼度ショートシグナル
                    logger.info(
                        f"Ensemble SHORT signal: prob={probability:.4f}, "
                        f"confidence={confidence:.4f}"
                    )
                    signal = Signal(side="SELL", price=current_price)
                    self._update_signal_history(
                        "ENTRY_SHORT", probability, confidence, trading_info
                    )
                    return signal
                
                # 中程度の信頼度でのシグナル（より保守的）
                weak_threshold = dynamic_threshold + 0.1  # より高い閾値
                if probability > (0.5 + weak_threshold) and confidence >= 0.5:
                    logger.info(
                        f"Ensemble Weak LONG: prob={probability:.4f}, "
                        f"confidence={confidence:.4f}"
                    )
                    signal = Signal(side="BUY", price=current_price)
                    self._update_signal_history(
                        "WEAK_LONG", probability, confidence, trading_info
                    )
                    return signal
                
                return Signal()  # ホールド
                
        except Exception as e:
            logger.error(f"Ensemble prediction failed: {e}")
            # フォールバック: 既存MLStrategy使用
            return super().logic_signal(price_df, position)
    
    def _generate_market_context(self, price_df: pd.DataFrame) -> Dict[str, Any]:
        """市場コンテキスト生成"""
        context = {}
        
        try:
            # VIX情報取得
            if self.vix_adjustment_enabled and self.vix_fetcher:
                vix_adj, vix_info = self.get_vix_adjustment()
                if vix_info:
                    context['vix_level'] = vix_info.get('current_vix', 20.0)
                    context['vix_change'] = vix_info.get('vix_change', 0.0)
                    context['market_regime'] = vix_info.get('market_regime', 'normal')
            
            # ボラティリティ計算
            if len(price_df) >= 20:
                returns = price_df["close"].pct_change().dropna()
                if len(returns) >= 20:
                    context['volatility'] = returns.rolling(20).std().iloc[-1]
                else:
                    context['volatility'] = 0.02
            else:
                context['volatility'] = 0.02
                
            # トレンド強度計算
            if len(price_df) >= 50:
                # sma_20 = price_df["close"].rolling(20).mean().iloc[-1]  # Unused
                sma_50 = price_df["close"].rolling(50).mean().iloc[-1]
                current_price = price_df["close"].iloc[-1]
                
                trend_strength = abs(current_price - sma_50) / sma_50
                context['trend_strength'] = min(trend_strength, 1.0)
            else:
                context['trend_strength'] = 0.5
                
        except Exception as e:
            logger.warning(f"Failed to generate market context: {e}")
            
        return context
    
    def _calculate_exit_threshold(self, trading_info: Dict, confidence: float) -> float:
        """動的エグジット閾値計算"""
        base_exit = 0.5
        
        # 市場レジームベース調整
        market_regime = trading_info.get('market_regime', 'normal')
        if market_regime == 'crisis':
            regime_adj = 0.15  # 早めのエグジット
        elif market_regime == 'volatile':
            regime_adj = 0.1
        elif market_regime == 'calm':
            regime_adj = -0.05  # 粘り強くホールド
        else:
            regime_adj = 0.0
        
        # 信頼度ベース調整
        confidence_adj = (1.0 - confidence) * 0.1  # 低信頼度ほど早めにエグジット
        
        return base_exit + regime_adj + confidence_adj
    
    def _update_signal_history(
        self, signal_type: str, probability: float, confidence: float,
        trading_info: Dict
    ):
        """シグナル履歴更新"""
        signal_record = {
            'type': signal_type,
            'probability': probability,
            'confidence': confidence,
            'trading_info': trading_info,
            'timestamp': pd.Timestamp.now()
        }
        
        self.recent_signals.append(signal_record)
        if len(self.recent_signals) > self.max_signal_history:
            self.recent_signals.pop(0)
    
    def get_ensemble_performance_info(self) -> Dict[str, Any]:
        """アンサンブルパフォーマンス情報取得"""
        if not self.ensemble_enabled:
            return {"ensemble_enabled": False}
        
        try:
            base_info = self.ensemble_model.get_trading_ensemble_info()
            
            # 追加の取引関連情報
            trading_performance = {
                "recent_signals_count": len(self.recent_signals),
                "average_confidence": (
                    np.mean([s['confidence'] for s in self.recent_signals[-10:]])
                    if self.recent_signals else 0.0
                ),
                "signal_distribution": self._analyze_signal_distribution(),
                "trading_confidence_threshold": self.trading_confidence_threshold,
                "risk_adjustment_enabled": self.risk_adjustment_enabled,
                "dynamic_threshold_enabled": self.dynamic_threshold_enabled
            }
            
            base_info.update(trading_performance)
            return base_info
            
        except Exception as e:
            logger.error(f"Failed to get ensemble performance info: {e}")
            return {"error": str(e)}
    
    def _analyze_signal_distribution(self) -> Dict[str, int]:
        """最近のシグナル分布分析"""
        if not self.recent_signals:
            return {}
        
        signal_types = [s['type'] for s in self.recent_signals[-20:]]
        distribution = {}
        for signal_type in set(signal_types):
            distribution[signal_type] = signal_types.count(signal_type)
            
        return distribution
    
    def update_ensemble_config(self, new_config: Dict[str, Any]):
        """アンサンブル設定の動的更新"""
        if not self.ensemble_enabled:
            logger.warning("Ensemble not enabled, cannot update config")
            return
        
        # 設定更新
        self.config.update(new_config)
        
        # 閾値更新
        ensemble_config = new_config.get('ml', {}).get('ensemble', {})
        if 'confidence_threshold' in ensemble_config:
            self.trading_confidence_threshold = ensemble_config['confidence_threshold']
            logger.info(
                f"Updated trading confidence threshold: "
                f"{self.trading_confidence_threshold}"
            )
        
        # その他の設定更新
        if 'risk_adjustment' in ensemble_config:
            self.risk_adjustment_enabled = ensemble_config['risk_adjustment']
        
        logger.info("Ensemble configuration updated")

# crypto_bot/strategy/aggressive_ml_strategy.py
# 説明:
# 積極的利益追求のための高度ML戦略クラス
# - マルチタイムフレーム統合判定
# - 信頼度ベースの積極的エントリー
# - 動的利確・損切り戦略
# - 高頻度取引対応

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from crypto_bot.execution.engine import Position, Signal
from crypto_bot.risk.aggressive_manager import AggressiveRiskManager

from .ml_strategy import MLStrategy

logger = logging.getLogger(__name__)


class AggressiveMLStrategy(MLStrategy):
    """
    積極的利益追求のための高度ML戦略
    
    Features:
    - Multi-timeframe analysis (マルチタイムフレーム分析)
    - Confidence-based aggressive entry (信頼度ベース積極エントリー)
    - Dynamic profit taking (動的利確戦略)
    - High-frequency trading support (高頻度取引サポート)
    """
    
    def __init__(self, model_path: str, threshold: float = None, config: dict = None):
        super().__init__(model_path, threshold, config)
        
        # 積極的戦略パラメータ
        strategy_params = self.config.get("strategy", {}).get("params", {})
        self.aggressive_threshold = strategy_params.get("aggressive_threshold", 0.02)
        self.confidence_threshold = strategy_params.get("confidence_threshold", 0.49)
        self.profit_target_multiplier = strategy_params.get("profit_target_multiplier", 1.5)
        self.stop_loss_multiplier = strategy_params.get("stop_loss_multiplier", 0.8)
        
        # マルチタイムフレーム設定
        self.multi_timeframe_enabled = strategy_params.get("multi_timeframe", False)
        self.timeframes = strategy_params.get("timeframes", ["1h", "15m"])
        
        # 積極的リスク管理
        risk_config = self.config.get("risk", {})
        self.aggressive_risk_manager = AggressiveRiskManager(
            risk_per_trade=risk_config.get("risk_per_trade", 0.08),
            kelly_enabled=risk_config.get("kelly_criterion", {}).get("enabled", True),
            kelly_max_fraction=risk_config.get("kelly_criterion", {}).get("max_fraction", 0.4),
            confidence_multiplier=1.5,
            high_winrate_threshold=0.75,
            high_winrate_multiplier=1.3
        )
        
        # パフォーマンス追跡
        self.trade_performance = []
        self.signal_confidence_history = []
        
        # 積極的利確・損切り設定
        self.profit_taking_levels = [0.3, 0.5, 0.7]  # 部分利確レベル
        self.trailing_stop_enabled = True
        self.dynamic_stops = True
        
        logger.info(f"AggressiveMLStrategy initialized:")
        logger.info(f"  aggressive_threshold: {self.aggressive_threshold}")
        logger.info(f"  confidence_threshold: {self.confidence_threshold}")
        logger.info(f"  multi_timeframe: {self.multi_timeframe_enabled}")

    def generate_signal(self, data: pd.DataFrame, position: Position) -> Signal:
        """
        積極的シグナル生成（マルチタイムフレーム統合判定）
        
        Args:
            data: 価格データ
            position: 現在のポジション
            
        Returns:
            Signal: 取引シグナル
        """
        if data.empty or len(data) < 50:
            return Signal()
        
        try:
            # 基本MLシグナル取得
            base_signal = super().generate_signal(data, position)
            
            # 積極的強化判定
            enhanced_signal = self._enhance_signal_aggressively(data, base_signal, position)
            
            return enhanced_signal
            
        except Exception as e:
            logger.error(f"Error in aggressive signal generation: {e}")
            return Signal()

    def _enhance_signal_aggressively(
        self, 
        data: pd.DataFrame, 
        base_signal: Signal, 
        position: Position
    ) -> Signal:
        """
        シグナルの積極的強化
        
        Args:
            data: 価格データ
            base_signal: ベースシグナル
            position: 現在ポジション
            
        Returns:
            強化されたシグナル
        """
        # 特徴量エンジニアリング
        features = self._prepare_features_aggressively(data)
        if features is None:
            return base_signal
        
        # ML予測（信頼度込み）
        prediction, confidence = self._predict_with_confidence(features)
        
        # 信頼度を記録
        self.signal_confidence_history.append({
            "timestamp": data.index[-1],
            "confidence": confidence,
            "prediction": prediction
        })
        
        # 積極的エントリー判定
        if not position.exist:
            signal = self._generate_aggressive_entry_signal(
                data, prediction, confidence, base_signal
            )
        else:
            # エグジット判定（積極的利確・損切り）
            signal = self._generate_aggressive_exit_signal(
                data, position, prediction, confidence
            )
        
        # シグナル強化ログ
        if signal.exist:
            logger.info(f"Aggressive signal generated: {signal.side}, "
                       f"confidence={confidence:.3f}, prediction={prediction:.3f}")
        
        return signal

    def _prepare_features_aggressively(self, data: pd.DataFrame) -> Optional[np.ndarray]:
        """
        積極的特徴量準備（マルチタイムフレーム対応）
        
        Args:
            data: 価格データ
            
        Returns:
            準備された特徴量配列
        """
        try:
            # ベース特徴量
            features = self.feature_engineer.transform(data)
            
            # マルチタイムフレーム特徴量追加
            if self.multi_timeframe_enabled:
                mt_features = self._extract_multi_timeframe_features(data)
                if mt_features is not None:
                    features = np.concatenate([features, mt_features])
            
            return features.reshape(1, -1)
            
        except Exception as e:
            logger.error(f"Error preparing aggressive features: {e}")
            return None

    def _extract_multi_timeframe_features(self, data: pd.DataFrame) -> Optional[np.ndarray]:
        """
        マルチタイムフレーム特徴量抽出
        
        Args:
            data: 価格データ
            
        Returns:
            マルチタイムフレーム特徴量
        """
        try:
            features = []
            
            # 15分足的なモメンタム
            if len(data) >= 4:
                recent_4h = data.tail(4)
                momentum_15m = (recent_4h['close'].iloc[-1] / recent_4h['close'].iloc[0] - 1) * 100
                features.append(momentum_15m)
            
            # 5分足的なボラティリティ（直近12時間の変動）
            if len(data) >= 12:
                recent_12h = data.tail(12)
                volatility_5m = recent_12h['close'].pct_change().std() * 100
                features.append(volatility_5m)
            
            # 短期・中期・長期トレンド一致度
            if len(data) >= 24:
                short_trend = data['close'].tail(4).pct_change().sum()
                medium_trend = data['close'].tail(12).pct_change().sum()
                long_trend = data['close'].tail(24).pct_change().sum()
                
                # トレンド一致スコア
                trend_alignment = np.sign(short_trend) + np.sign(medium_trend) + np.sign(long_trend)
                features.append(trend_alignment / 3.0)  # -1 to 1に正規化
            
            return np.array(features) if features else None
            
        except Exception as e:
            logger.error(f"Error extracting multi-timeframe features: {e}")
            return None

    def _predict_with_confidence(self, features: np.ndarray) -> Tuple[float, float]:
        """
        信頼度付きML予測
        
        Args:
            features: 特徴量配列
            
        Returns:
            (予測値, 信頼度)
        """
        try:
            if self.is_ensemble:
                # アンサンブルモデルの場合
                prediction = self.model.predict_proba(features)[0, 1]  # クラス1の確率
                
                # 信頼度計算（予測確率の0.5からの距離）
                confidence = abs(prediction - 0.5) * 2  # 0-1の範囲
                
            else:
                # 単一モデルの場合
                try:
                    prediction_proba = self.model.predict_proba(features)
                    prediction = prediction_proba[0, 1] if prediction_proba.shape[1] > 1 else prediction_proba[0, 0]
                    confidence = abs(prediction - 0.5) * 2
                except:
                    # predict_probaが使えない場合のフォールバック
                    prediction = self.model.predict(features)[0]
                    prediction = 1 / (1 + np.exp(-prediction))  # シグモイド変換
                    confidence = abs(prediction - 0.5) * 2
            
            return float(prediction), float(confidence)
            
        except Exception as e:
            logger.error(f"Error in prediction with confidence: {e}")
            return 0.5, 0.0

    def _generate_aggressive_entry_signal(
        self, 
        data: pd.DataFrame, 
        prediction: float, 
        confidence: float,
        base_signal: Signal
    ) -> Signal:
        """
        積極的エントリーシグナル生成
        
        Args:
            data: 価格データ
            prediction: ML予測値
            confidence: 信頼度
            base_signal: ベースシグナル
            
        Returns:
            積極的エントリーシグナル
        """
        # 動的閾値計算
        dynamic_threshold = self._calculate_dynamic_threshold(data, confidence)
        
        # 積極的エントリー条件
        aggressive_long = (
            prediction > 0.5 + dynamic_threshold and
            confidence >= self.confidence_threshold
        )
        
        aggressive_short = (
            prediction < 0.5 - dynamic_threshold and
            confidence >= self.confidence_threshold
        )
        
        # より積極的な判定（信頼度が高い場合はさらに緩和）
        if confidence > 0.75:
            high_confidence_threshold = dynamic_threshold * 0.7  # 30%緩和
            aggressive_long = aggressive_long or (prediction > 0.5 + high_confidence_threshold)
            aggressive_short = aggressive_short or (prediction < 0.5 - high_confidence_threshold)
        
        # シグナル生成
        if aggressive_long:
            return Signal(side="BUY", price=data['close'].iloc[-1], exist=True)
        elif aggressive_short:
            return Signal(side="SELL", price=data['close'].iloc[-1], exist=True)
        else:
            return Signal()

    def _generate_aggressive_exit_signal(
        self,
        data: pd.DataFrame,
        position: Position,
        prediction: float,
        confidence: float
    ) -> Signal:
        """
        積極的エグジットシグナル生成
        
        Args:
            data: 価格データ
            position: 現在ポジション
            prediction: ML予測
            confidence: 信頼度
            
        Returns:
            エグジットシグナル
        """
        current_price = data['close'].iloc[-1]
        
        # 基本エグジット条件
        basic_exit = self._check_basic_exit_conditions(position, prediction, confidence)
        if basic_exit:
            return Signal(side="SELL" if position.side == "BUY" else "BUY", 
                         price=current_price, exist=True)
        
        # 積極的利確判定
        profit_exit = self._check_aggressive_profit_taking(position, current_price, data)
        if profit_exit:
            return Signal(side="SELL" if position.side == "BUY" else "BUY",
                         price=current_price, exist=True)
        
        # 動的ストップロス
        if self.dynamic_stops:
            stop_exit = self._check_dynamic_stop_loss(position, current_price, data)
            if stop_exit:
                return Signal(side="SELL" if position.side == "BUY" else "BUY",
                             price=current_price, exist=True)
        
        return Signal()

    def _calculate_dynamic_threshold(self, data: pd.DataFrame, confidence: float) -> float:
        """
        動的閾値計算（積極版）
        
        Args:
            data: 価格データ
            confidence: 信頼度
            
        Returns:
            動的閾値
        """
        # ベース閾値
        base_threshold = self.aggressive_threshold
        
        # 信頼度調整（高信頼度時はより積極的）
        confidence_factor = max(0.5, 1.5 - confidence)  # 高信頼度ほど小さく
        
        # ボラティリティ調整
        if len(data) >= 20:
            recent_volatility = data['close'].tail(20).pct_change().std()
            volatility_factor = min(2.0, max(0.5, recent_volatility * 50))  # 適度な調整
        else:
            volatility_factor = 1.0
        
        # VIX調整
        vix_factor = 1.0
        if hasattr(self, 'last_vix_level'):
            if self.last_vix_level < 15:  # 低VIX時はより積極的
                vix_factor = 0.8
            elif self.last_vix_level > 30:  # 高VIX時は保守的
                vix_factor = 1.3
        
        # 最終閾値
        dynamic_threshold = base_threshold * confidence_factor * volatility_factor * vix_factor
        
        # 範囲制限
        dynamic_threshold = max(0.01, min(dynamic_threshold, 0.08))
        
        logger.debug(f"Dynamic threshold: {dynamic_threshold:.4f} "
                    f"(base={base_threshold:.4f}, conf_factor={confidence_factor:.2f}, "
                    f"vol_factor={volatility_factor:.2f}, vix_factor={vix_factor:.2f})")
        
        return dynamic_threshold

    def _check_basic_exit_conditions(
        self, 
        position: Position, 
        prediction: float, 
        confidence: float
    ) -> bool:
        """
        基本エグジット条件チェック
        
        Args:
            position: 現在ポジション
            prediction: ML予測
            confidence: 信頼度
            
        Returns:
            エグジットすべきかどうか
        """
        # 予測反転 + 高信頼度
        if position.side == "BUY":
            return prediction < 0.45 and confidence > 0.6
        else:  # SHORT
            return prediction > 0.55 and confidence > 0.6

    def _check_aggressive_profit_taking(
        self, 
        position: Position, 
        current_price: float, 
        data: pd.DataFrame
    ) -> bool:
        """
        積極的利確判定
        
        Args:
            position: 現在ポジション
            current_price: 現在価格
            data: 価格データ
            
        Returns:
            利確すべきかどうか
        """
        if not position.exist:
            return False
        
        # 利益率計算
        if position.side == "BUY":
            profit_rate = (current_price - position.entry_price) / position.entry_price
        else:  # SHORT
            profit_rate = (position.entry_price - current_price) / position.entry_price
        
        # 積極的利確条件
        # 1. 短期間で大きな利益
        if position.hold_bars <= 3 and profit_rate > 0.02:  # 3時間以内で2%利益
            logger.info(f"Quick profit taking: {profit_rate:.2%} in {position.hold_bars} bars")
            return True
        
        # 2. 中期間で適度な利益
        if position.hold_bars <= 12 and profit_rate > 0.015:  # 12時間以内で1.5%利益
            logger.info(f"Medium-term profit taking: {profit_rate:.2%} in {position.hold_bars} bars")
            return True
        
        # 3. ATRベースの動的利確
        if len(data) >= 14:
            atr = data['close'].rolling(14).apply(
                lambda x: pd.Series(x).pct_change().abs().mean()
            ).iloc[-1]
            
            if profit_rate > atr * self.profit_target_multiplier:
                logger.info(f"ATR-based profit taking: {profit_rate:.2%} > {atr * self.profit_target_multiplier:.2%}")
                return True
        
        return False

    def _check_dynamic_stop_loss(
        self, 
        position: Position, 
        current_price: float, 
        data: pd.DataFrame
    ) -> bool:
        """
        動的ストップロス判定
        
        Args:
            position: 現在ポジション
            current_price: 現在価格
            data: 価格データ
            
        Returns:
            ストップロスに到達したかどうか
        """
        if not position.exist:
            return False
        
        # 損失率計算
        if position.side == "BUY":
            loss_rate = (position.entry_price - current_price) / position.entry_price
        else:  # SHORT
            loss_rate = (current_price - position.entry_price) / position.entry_price
        
        # 時間ベースの動的ストップ（長時間保有時はより厳格に）
        time_factor = min(2.0, 1.0 + position.hold_bars * 0.1)  # 時間経過で厳格化
        
        # ATRベースの動的ストップ
        if len(data) >= 14:
            atr = data['close'].rolling(14).apply(
                lambda x: pd.Series(x).pct_change().abs().mean()
            ).iloc[-1]
            
            dynamic_stop_threshold = atr * self.stop_loss_multiplier * time_factor
            
            if loss_rate > dynamic_stop_threshold:
                logger.info(f"Dynamic stop loss triggered: {loss_rate:.2%} > {dynamic_stop_threshold:.2%}")
                return True
        
        # 固定ストップロス（最低限の保護）
        if loss_rate > 0.05:  # 5%損失で強制決済
            logger.info(f"Fixed stop loss triggered: {loss_rate:.2%}")
            return True
        
        return False

    def get_position_size_recommendation(
        self, 
        balance: float, 
        entry_price: float, 
        stop_price: float,
        confidence: float,
        market_conditions: Optional[Dict] = None
    ) -> Tuple[float, Dict]:
        """
        ポジションサイズ推奨値取得
        
        Args:
            balance: 口座残高
            entry_price: エントリー価格
            stop_price: ストップ価格
            confidence: 予測信頼度
            market_conditions: 市場環境
            
        Returns:
            (推奨ポジションサイズ, 詳細情報)
        """
        return self.aggressive_risk_manager.dynamic_position_sizing(
            balance=balance,
            entry_price=entry_price,
            stop_price=stop_price,
            confidence=confidence,
            market_conditions=market_conditions
        )

    def update_performance(self, trade_result: Dict):
        """
        パフォーマンス更新
        
        Args:
            trade_result: 取引結果
        """
        self.aggressive_risk_manager.add_trade_result(
            entry_price=trade_result.get("entry_price", 0),
            exit_price=trade_result.get("exit_price", 0),
            balance=trade_result.get("balance", 0),
            confidence=trade_result.get("confidence", 0.6)
        )
        
        self.trade_performance.append(trade_result)
        
        # 履歴制限
        if len(self.trade_performance) > 100:
            self.trade_performance = self.trade_performance[-50:]

    def get_strategy_metrics(self) -> Dict:
        """
        戦略メトリクス取得
        
        Returns:
            戦略パフォーマンス指標
        """
        risk_metrics = self.aggressive_risk_manager.get_risk_metrics()
        
        # 信頼度履歴分析
        if self.signal_confidence_history:
            recent_confidences = [s["confidence"] for s in self.signal_confidence_history[-20:]]
            avg_confidence = np.mean(recent_confidences)
            confidence_trend = np.polyfit(range(len(recent_confidences)), recent_confidences, 1)[0]
        else:
            avg_confidence = 0.6
            confidence_trend = 0.0
        
        return {
            **risk_metrics,
            "avg_confidence": avg_confidence,
            "confidence_trend": confidence_trend,
            "signals_generated": len(self.signal_confidence_history),
            "aggressive_multiplier": self.aggressive_risk_manager.get_aggressive_multiplier(avg_confidence)
        }
# crypto_bot/risk/aggressive_manager.py
# 説明:
# 積極的利益追求のための高度リスク管理クラス
# - 信頼度ベースの動的ポジションサイジング
# - 勝率連動Kelly基準の強化版
# - ボラティリティ・VIX連動のリスク調整
# - 最大収益化のための戦略的リスクテイク

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .manager import RiskManager

logger = logging.getLogger(__name__)


class AggressiveRiskManager(RiskManager):
    """
    積極的利益追求のための高度リスク管理クラス
    
    Features:
    - Confidence-based position sizing (信頼度ベースサイジング)
    - Enhanced Kelly Criterion with win rate bonus (勝率ボーナス付きKelly)
    - Volatility-adaptive risk scaling (ボラティリティ連動リスクスケーリング)
    - Multi-factor risk assessment (多要素リスク評価)
    """
    
    def __init__(
        self,
        risk_per_trade: float = 0.08,  # より積極的なデフォルト
        stop_atr_mult: float = 1.2,
        kelly_enabled: bool = True,
        kelly_lookback_window: int = 20,
        kelly_max_fraction: float = 0.4,  # より積極的
        **kwargs
    ):
        super().__init__(
            risk_per_trade=risk_per_trade,
            stop_atr_mult=stop_atr_mult,
            kelly_enabled=kelly_enabled,
            kelly_lookback_window=kelly_lookback_window,
            kelly_max_fraction=kelly_max_fraction,
        )
        
        # 積極的リスク管理パラメータ
        self.confidence_multiplier = kwargs.get("confidence_multiplier", 1.5)
        self.high_winrate_threshold = kwargs.get("high_winrate_threshold", 0.75)
        self.high_winrate_multiplier = kwargs.get("high_winrate_multiplier", 1.3)
        self.volatility_sensitivity = kwargs.get("volatility_sensitivity", 0.3)
        self.max_aggressive_multiplier = kwargs.get("max_aggressive_multiplier", 2.5)
        
        # パフォーマンス追跡
        self.recent_performance = []
        self.volatility_history = []
        
        logger.info(f"AggressiveRiskManager initialized with:")
        logger.info(f"  risk_per_trade: {self.risk_per_trade}")
        logger.info(f"  kelly_max_fraction: {self.kelly_max_fraction}")
        logger.info(f"  confidence_multiplier: {self.confidence_multiplier}")

    def calculate_confidence_based_size(
        self, 
        base_size: float, 
        confidence: float,
        market_conditions: Optional[Dict] = None
    ) -> float:
        """
        信頼度ベースの動的ポジションサイジング
        
        Args:
            base_size: ベースポジションサイズ
            confidence: モデル予測信頼度 (0.5-1.0)
            market_conditions: 市場環境情報
            
        Returns:
            調整後のポジションサイズ
        """
        if confidence < 0.5:
            logger.warning(f"Low confidence {confidence:.3f}, using minimum size")
            return base_size * 0.3
        
        # 信頼度ボーナス計算
        confidence_bonus = ((confidence - 0.5) * 2) ** 1.2  # 非線形強化
        confidence_multiplier = 1.0 + (confidence_bonus * self.confidence_multiplier)
        
        # 市場環境ボーナス
        market_multiplier = 1.0
        if market_conditions:
            # VIX環境ボーナス
            vix_level = market_conditions.get("vix_level", 20)
            if vix_level < 15:  # 低VIX = 安定市場
                market_multiplier *= 1.2
            elif vix_level > 35:  # 高VIX = 不安定市場
                market_multiplier *= 0.7
            
            # ボラティリティ調整
            volatility = market_conditions.get("volatility", 1.0)
            if volatility > 1.5:  # 高ボラティリティ
                market_multiplier *= (1.0 + self.volatility_sensitivity)
        
        # 最終サイズ計算
        adjusted_size = base_size * confidence_multiplier * market_multiplier
        
        # 上限制御
        max_size = base_size * self.max_aggressive_multiplier
        final_size = min(adjusted_size, max_size)
        
        logger.debug(f"Confidence-based sizing: "
                    f"base={base_size:.4f} → final={final_size:.4f} "
                    f"(conf={confidence:.3f}, conf_mult={confidence_multiplier:.2f}, "
                    f"market_mult={market_multiplier:.2f})")
        
        return final_size

    def enhanced_kelly_position_sizing(
        self, 
        balance: float, 
        entry_price: float, 
        stop_price: float,
        confidence: float = 0.6
    ) -> float:
        """
        強化版Kelly基準ポジションサイジング
        
        Args:
            balance: 口座残高
            entry_price: エントリー価格
            stop_price: ストップロス価格  
            confidence: 予測信頼度
            
        Returns:
            Kelly基準による推奨ポジションサイズ
        """
        if not self.kelly_enabled or len(self.trade_history) < 5:
            # Kelly無効 or データ不足時は基本サイズ
            base_size = self.calc_lot_size(balance, entry_price, stop_price)
            return self.calculate_confidence_based_size(base_size, confidence)
        
        # 最近の取引成績分析
        recent_trades = self.trade_history[-self.kelly_lookback_window:]
        
        if len(recent_trades) < 3:
            base_size = self.calc_lot_size(balance, entry_price, stop_price)
            return self.calculate_confidence_based_size(base_size, confidence)
        
        # 勝率・平均損益計算
        wins = [t for t in recent_trades if t["pnl"] > 0]
        losses = [t for t in recent_trades if t["pnl"] <= 0]
        
        win_rate = len(wins) / len(recent_trades) if recent_trades else 0.5
        avg_win = np.mean([t["pnl_pct"] for t in wins]) if wins else 0.02
        avg_loss = abs(np.mean([t["pnl_pct"] for t in losses])) if losses else 0.02
        
        # Kelly基準計算
        if avg_loss > 0:
            kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        else:
            kelly_fraction = win_rate - 0.5  # フォールバック
        
        # Kelly fraction調整
        kelly_fraction = max(0, min(kelly_fraction, self.kelly_max_fraction))
        
        # 高勝率ボーナス
        if win_rate >= self.high_winrate_threshold:
            high_winrate_bonus = self.high_winrate_multiplier
            kelly_fraction *= high_winrate_bonus
            logger.info(f"High win rate bonus applied: {win_rate:.2f} >= {self.high_winrate_threshold:.2f}, "
                       f"multiplier={high_winrate_bonus:.2f}")
        
        # 信頼度調整
        confidence_adjusted_kelly = kelly_fraction * (0.5 + confidence)
        
        # 最終調整
        final_kelly = min(confidence_adjusted_kelly, self.kelly_max_fraction)
        
        # ポジションサイズ計算
        risk_amount = balance * final_kelly
        price_diff = abs(entry_price - stop_price)
        lot_size = risk_amount / price_diff if price_diff > 0 else 0
        
        logger.info(f"Enhanced Kelly sizing: win_rate={win_rate:.2f}, "
                   f"avg_win={avg_win:.3f}, avg_loss={avg_loss:.3f}, "
                   f"kelly={kelly_fraction:.3f}, final_kelly={final_kelly:.3f}, "
                   f"lot_size={lot_size:.4f}")
        
        return lot_size

    def dynamic_position_sizing(
        self,
        balance: float,
        entry_price: float,
        stop_price: float,
        confidence: float = 0.6,
        market_conditions: Optional[Dict] = None,
        **kwargs
    ) -> Tuple[float, Dict]:
        """
        統合的な動的ポジションサイジング
        
        Args:
            balance: 口座残高
            entry_price: エントリー価格
            stop_price: ストップロス価格
            confidence: 予測信頼度
            market_conditions: 市場環境情報
            
        Returns:
            (ポジションサイズ, 詳細情報)
        """
        # 基本Kelly基準サイズ
        kelly_size = self.enhanced_kelly_position_sizing(
            balance, entry_price, stop_price, confidence
        )
        
        # 信頼度・市場環境調整
        final_size = self.calculate_confidence_based_size(
            kelly_size, confidence, market_conditions
        )
        
        # 安全性チェック
        max_safe_size = balance * self.kelly_max_fraction / abs(entry_price - stop_price) if abs(entry_price - stop_price) > 0 else 0
        final_size = min(final_size, max_safe_size)
        
        # 最小ポジションサイズ制御
        min_size = balance * 0.001 / entry_price  # 0.1%の最小リスク
        final_size = max(final_size, min_size)
        
        # 詳細情報
        info = {
            "kelly_size": kelly_size,
            "confidence": confidence,
            "final_size": final_size,
            "confidence_adjustment": final_size / kelly_size if kelly_size > 0 else 1.0,
            "risk_percentage": (final_size * abs(entry_price - stop_price)) / balance * 100
        }
        
        logger.info(f"Dynamic position sizing: "
                   f"final_size={final_size:.4f}, "
                   f"risk={info['risk_percentage']:.2f}%, "
                   f"confidence={confidence:.3f}")
        
        return final_size, info

    def add_trade_result(
        self, 
        entry_price: float, 
        exit_price: float, 
        balance: float,
        confidence: float = 0.6,
        **kwargs
    ):
        """
        取引結果をトラッキングに追加（Kelly計算用）
        
        Args:
            entry_price: エントリー価格
            exit_price: エグジット価格
            balance: 口座残高
            confidence: その時の予測信頼度
        """
        pnl = exit_price - entry_price
        pnl_pct = pnl / entry_price if entry_price > 0 else 0
        
        trade_record = {
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "balance": balance,
            "confidence": confidence,
            "timestamp": pd.Timestamp.now()
        }
        
        self.trade_history.append(trade_record)
        
        # 履歴制限（メモリ効率化）
        if len(self.trade_history) > self.kelly_lookback_window * 3:
            self.trade_history = self.trade_history[-self.kelly_lookback_window * 2:]
        
        logger.debug(f"Added trade result: PnL={pnl:.2f} ({pnl_pct:.2%}), "
                    f"confidence={confidence:.3f}")

    def get_risk_metrics(self) -> Dict:
        """
        現在のリスク指標を取得
        
        Returns:
            リスク指標辞書
        """
        recent_trades = self.trade_history[-20:] if len(self.trade_history) >= 20 else self.trade_history
        
        if not recent_trades:
            return {
                "win_rate": 0.5,
                "avg_return": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "trades_count": 0
            }
        
        returns = [t["pnl_pct"] for t in recent_trades]
        wins = [r for r in returns if r > 0]
        
        win_rate = len(wins) / len(returns) if returns else 0.5
        avg_return = np.mean(returns) if returns else 0.0
        std_return = np.std(returns) if len(returns) > 1 else 0.01
        sharpe_ratio = avg_return / std_return if std_return > 0 else 0.0
        
        # 最大ドローダウン計算
        cumulative_returns = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = running_max - cumulative_returns
        max_drawdown = np.max(drawdowns) if len(drawdowns) > 0 else 0.0
        
        return {
            "win_rate": win_rate,
            "avg_return": avg_return,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "trades_count": len(recent_trades),
            "recent_returns": returns[-5:] if len(returns) >= 5 else returns
        }

    def should_reduce_risk(self) -> bool:
        """
        リスクを削減すべきかどうかの判定
        
        Returns:
            True if risk should be reduced
        """
        metrics = self.get_risk_metrics()
        
        # リスク削減条件
        conditions = [
            metrics["win_rate"] < 0.4,  # 勝率40%未満
            metrics["max_drawdown"] > 0.2,  # 20%以上のドローダウン
            metrics["sharpe_ratio"] < -1.0,  # 極端に悪いシャープレシオ
            len([r for r in metrics["recent_returns"] if r < -0.05]) >= 3  # 最近5取引で3回以上5%超損失
        ]
        
        if any(conditions):
            logger.warning(f"Risk reduction recommended: metrics={metrics}")
            return True
        
        return False

    def get_aggressive_multiplier(self, confidence: float, market_conditions: Optional[Dict] = None) -> float:
        """
        積極的乗数を計算
        
        Args:
            confidence: 予測信頼度
            market_conditions: 市場環境
            
        Returns:
            積極的乗数 (1.0-2.5)
        """
        base_multiplier = 1.0
        
        # 信頼度ベース
        if confidence > 0.8:
            base_multiplier *= 1.5
        elif confidence > 0.7:
            base_multiplier *= 1.3
        elif confidence > 0.6:
            base_multiplier *= 1.1
        
        # 勝率ベース
        metrics = self.get_risk_metrics()
        if metrics["win_rate"] > 0.75:
            base_multiplier *= 1.2
        elif metrics["win_rate"] < 0.5:
            base_multiplier *= 0.8
        
        # 市場環境ベース
        if market_conditions:
            vix_level = market_conditions.get("vix_level", 20)
            if 12 < vix_level < 25:  # 適度なボラティリティ
                base_multiplier *= 1.1
        
        # 上限制御
        return min(base_multiplier, self.max_aggressive_multiplier)
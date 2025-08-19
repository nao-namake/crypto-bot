"""
ATRベース戦略実装 - シンプル逆張り戦略

ATRとボリンジャーバンドを使用したシンプルな逆張り戦略。
過度な価格変動時の平均回帰を狙う。

戦略ロジック:
1. ATRで市場ボラティリティを測定
2. ボリンジャーバンド位置で過買い・過売り判定
3. RSIで追加確認
4. 市場ストレスで異常状況フィルター

Phase 4改善実装日: 2025年8月18日.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from ...core.exceptions import StrategyError
from ...core.logger import get_logger
from ..base.strategy_base import StrategyBase, StrategySignal
from ..utils import EntryAction, SignalBuilder, StrategyType


class ATRBasedStrategy(StrategyBase):
    """
    ATRベース戦略

    シンプルなボラティリティベース逆張り戦略。
    平均回帰理論に基づく。.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """戦略初期化."""
        # デフォルト設定
        default_config = {
            # シグナル設定
            "bb_overbought": 0.8,  # BB上限（80%位置）
            "bb_oversold": 0.2,  # BB下限（20%位置）
            "rsi_overbought": 70,  # RSI過買い
            "rsi_oversold": 30,  # RSI過売り
            "min_confidence": 0.4,  # 最小信頼度
            # リスク管理
            "stop_loss_atr_multiplier": 1.5,
            "take_profit_ratio": 2.0,
            "position_size_base": 0.015,  # 1.5%（逆張りなので控えめ）
            # フィルター設定
            "market_stress_threshold": 0.7,  # 市場ストレス閾値
            "min_atr_ratio": 0.5,  # 最小ATR比率（低ボラ回避）
        }

        merged_config = {**default_config, **(config or {})}
        super().__init__(name="ATRBased", config=merged_config)

    def analyze(self, df: pd.DataFrame) -> StrategySignal:
        """市場分析とシグナル生成."""
        try:
            self.logger.debug("[ATRBased] 分析開始")

            current_price = float(df["close"].iloc[-1])

            # 各指標分析
            bb_analysis = self._analyze_bb_position(df)
            rsi_analysis = self._analyze_rsi_momentum(df)
            atr_analysis = self._analyze_atr_volatility(df)
            stress_analysis = self._analyze_market_stress(df)

            # 統合判定
            signal_decision = self._make_decision(
                bb_analysis, rsi_analysis, atr_analysis, stress_analysis
            )

            # シグナル生成
            signal = self._create_signal(signal_decision, current_price, df)

            self.logger.debug(
                f"[ATRBased] シグナル: {signal.action} (信頼度: {signal.confidence:.3f})"
            )
            return signal

        except Exception as e:
            self.logger.error(f"[ATRBased] 分析エラー: {e}")
            raise StrategyError(f"ATRベース分析失敗: {e}", strategy_name=self.name)

    def _analyze_bb_position(self, df: pd.DataFrame) -> Dict[str, Any]:
        """ボリンジャーバンド位置分析."""
        try:
            current_bb_pos = float(df["bb_position"].iloc[-1])

            # BB位置によるシグナル判定（逆張り）
            if current_bb_pos >= self.config["bb_overbought"]:
                signal = -1  # 売りシグナル（過買い）
                strength = min((current_bb_pos - self.config["bb_overbought"]) / 0.2, 1.0)
            elif current_bb_pos <= self.config["bb_oversold"]:
                signal = 1  # 買いシグナル（過売り）
                strength = min((self.config["bb_oversold"] - current_bb_pos) / 0.2, 1.0)
            else:
                signal = 0  # ニュートラル
                strength = 0.0

            confidence = 0.3 + strength * 0.4 if abs(signal) > 0 else 0.0

            return {
                "signal": signal,
                "strength": strength,
                "confidence": confidence,
                "bb_position": current_bb_pos,
                "analysis": f"BB位置: {current_bb_pos:.2f} -> {['売り', 'なし', '買い'][signal+1]}",
            }

        except Exception as e:
            self.logger.error(f"BB位置分析エラー: {e}")
            return {
                "signal": 0,
                "strength": 0.0,
                "confidence": 0.0,
                "analysis": "エラー",
            }

    def _analyze_rsi_momentum(self, df: pd.DataFrame) -> Dict[str, Any]:
        """RSIモメンタム分析."""
        try:
            current_rsi = float(df["rsi_14"].iloc[-1])

            # RSI逆張りシグナル
            if current_rsi >= self.config["rsi_overbought"]:
                signal = -1  # 売りシグナル
                strength = min((current_rsi - self.config["rsi_overbought"]) / 30, 1.0)
            elif current_rsi <= self.config["rsi_oversold"]:
                signal = 1  # 買いシグナル
                strength = min((self.config["rsi_oversold"] - current_rsi) / 30, 1.0)
            else:
                signal = 0
                strength = 0.0

            confidence = 0.2 + strength * 0.3 if abs(signal) > 0 else 0.0

            return {
                "signal": signal,
                "strength": strength,
                "confidence": confidence,
                "rsi": current_rsi,
                "analysis": f"RSI: {current_rsi:.1f} -> {['売り', 'なし', '買い'][signal+1]}",
            }

        except Exception as e:
            self.logger.error(f"RSI分析エラー: {e}")
            return {
                "signal": 0,
                "strength": 0.0,
                "confidence": 0.0,
                "analysis": "エラー",
            }

    def _analyze_atr_volatility(self, df: pd.DataFrame) -> Dict[str, Any]:
        """ATRボラティリティ分析."""
        try:
            current_atr = float(df["atr_14"].iloc[-1])
            current_price = float(df["close"].iloc[-1])
            atr_ratio = current_atr / current_price

            # 過去20期間の平均ATR比率と比較
            if len(df) >= 20:
                historical_atr = df["atr_14"].iloc[-20:] / df["close"].iloc[-20:]
                avg_atr_ratio = historical_atr.mean()
                volatility_multiplier = atr_ratio / (avg_atr_ratio + 1e-8)
            else:
                volatility_multiplier = 1.0

            # ボラティリティ状態判定
            if volatility_multiplier < self.config["min_atr_ratio"]:
                regime = "low"  # 低ボラ（取引回避）
                strength = 0.0
            elif volatility_multiplier > 1.5:
                regime = "high"  # 高ボラ（逆張り好機）
                strength = min((volatility_multiplier - 1.5) / 0.5, 1.0)
            else:
                regime = "normal"  # 通常ボラ
                strength = 0.5

            return {
                "regime": regime,
                "strength": strength,
                "atr_ratio": atr_ratio,
                "volatility_multiplier": volatility_multiplier,
                "analysis": f"ボラティリティ: {regime} (倍率: {volatility_multiplier:.2f})",
            }

        except Exception as e:
            self.logger.error(f"ATR分析エラー: {e}")
            return {"regime": "normal", "strength": 0.0, "analysis": "エラー"}

    def _analyze_market_stress(self, df: pd.DataFrame) -> Dict[str, Any]:
        """市場ストレス分析."""
        try:
            current_stress = float(df["market_stress"].iloc[-1])

            # ストレス状態判定
            if current_stress >= self.config["market_stress_threshold"]:
                state = "high"  # 高ストレス（取引回避）
                filter_ok = False
            else:
                state = "normal"  # 通常（取引可能）
                filter_ok = True

            return {
                "state": state,
                "level": current_stress,
                "filter_ok": filter_ok,
                "analysis": f"市場ストレス: {state} ({current_stress:.2f})",
            }

        except Exception as e:
            self.logger.error(f"市場ストレス分析エラー: {e}")
            return {"state": "normal", "filter_ok": True, "analysis": "エラー"}

    def _make_decision(
        self,
        bb_analysis: Dict,
        rsi_analysis: Dict,
        atr_analysis: Dict,
        stress_analysis: Dict,
    ) -> Dict[str, Any]:
        """統合判定."""
        try:
            # フィルター確認
            if not stress_analysis["filter_ok"]:
                return self._create_hold_decision("市場ストレス高")

            if atr_analysis["regime"] == "low":
                return self._create_hold_decision("低ボラティリティ")

            # シグナル統合
            bb_signal = bb_analysis["signal"]
            rsi_signal = rsi_analysis["signal"]

            # 一致度確認
            if bb_signal != 0 and rsi_signal != 0:
                if bb_signal == rsi_signal:
                    # 両方一致
                    action = EntryAction.BUY if bb_signal > 0 else EntryAction.SELL
                    confidence = min(
                        bb_analysis["confidence"] + rsi_analysis["confidence"],
                        1.0,
                    )
                    strength = (bb_analysis["strength"] + rsi_analysis["strength"]) / 2
                else:
                    # 不一致はホールド
                    return self._create_hold_decision("シグナル不一致")
            elif bb_signal != 0:
                # BBシグナルのみ
                action = EntryAction.BUY if bb_signal > 0 else EntryAction.SELL
                confidence = bb_analysis["confidence"] * 0.7  # 単一シグナルなので減額
                strength = bb_analysis["strength"]
            elif rsi_signal != 0:
                # RSIシグナルのみ
                action = EntryAction.BUY if rsi_signal > 0 else EntryAction.SELL
                confidence = rsi_analysis["confidence"] * 0.7
                strength = rsi_analysis["strength"]
            else:
                return self._create_hold_decision("シグナルなし")

            # 高ボラティリティボーナス
            if atr_analysis["regime"] == "high":
                confidence = min(confidence * 1.2, 1.0)

            # 最小信頼度チェック
            if confidence < self.config["min_confidence"]:
                return self._create_hold_decision("信頼度不足")

            return {
                "action": action,
                "confidence": confidence,
                "strength": strength,
                "analysis": f"ATR逆張り: {action} (信頼度: {confidence:.3f})",
            }

        except Exception as e:
            self.logger.error(f"統合判定エラー: {e}")
            return self._create_hold_decision("判定エラー")

    def _create_hold_decision(self, reason: str) -> Dict[str, Any]:
        """ホールド決定作成."""
        return {
            "action": EntryAction.HOLD,
            "confidence": 0.5,
            "strength": 0.0,
            "analysis": f"ATR逆張り: hold ({reason})",
        }

    def _create_signal(
        self, decision: Dict, current_price: float, df: pd.DataFrame
    ) -> StrategySignal:
        """シグナル作成 - 共通モジュール利用."""
        return SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.name,
            decision=decision,
            current_price=current_price,
            df=df,
            config=self.config,
            strategy_type=StrategyType.ATR_BASED,
        )

    def get_required_features(self) -> List[str]:
        """必要特徴量リスト取得."""
        return [
            # 基本データ
            "close",
            # ATR戦略用指標
            "atr_14",  # メイン指標
            "bb_position",  # ボリンジャーバンド位置
            "rsi_14",  # RSI
            "market_stress",  # 市場ストレス
        ]

"""
ATRベース戦略実装 - シンプル逆張り戦略

ATRとボリンジャーバンドを使用したシンプルな逆張り戦略。
過度な価格変動時の平均回帰を狙う。

戦略ロジック:
1. ATRで市場ボラティリティを測定
2. ボリンジャーバンド位置で過買い・過売り判定
3. RSIで追加確認
4. 市場ストレスで異常状況フィルター

Phase 49完了: 市場不確実性計算統合・重複コード削減
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from ...core.exceptions import StrategyError
from ...core.logger import get_logger
from ..base.strategy_base import StrategyBase, StrategySignal
from ..strategy_registry import StrategyRegistry
from ..utils import EntryAction, MarketUncertaintyCalculator, SignalBuilder, StrategyType


@StrategyRegistry.register(name="ATRBased", strategy_type=StrategyType.ATR_BASED)
class ATRBasedStrategy(StrategyBase):
    """
    ATRベース戦略
    シンプルなボラティリティベース逆張り戦略。
    平均回帰理論に基づく。.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """戦略初期化."""
        # 循環インポート回避のため遅延インポート
        from ...core.config.threshold_manager import get_threshold

        # デフォルト設定（thresholds.yaml統合・動的設定対応）
        default_config = {
            # シグナル設定（thresholds.yamlから動的取得）
            "bb_overbought": get_threshold("strategies.atr_based.bb_overbought", 0.7),
            "bb_oversold": get_threshold("strategies.atr_based.bb_oversold", 0.3),
            "rsi_overbought": get_threshold("strategies.atr_based.rsi_overbought", 65),
            "rsi_oversold": get_threshold("strategies.atr_based.rsi_oversold", 35),
            "min_confidence": get_threshold("strategies.atr_based.min_confidence", 0.3),
            # Phase 51.6: リスク管理（ハードコード削除・設定ファイル一元管理）
            "stop_loss_atr_multiplier": get_threshold("sl_atr_normal_vol", 2.0),
            "take_profit_ratio": get_threshold(
                "position_management.take_profit.default_ratio"
            ),  # Phase 51.6: TP 0.9%・RR比1.29:1
            "position_size_base": get_threshold(
                "ml.dynamic_confidence.strategies.atr_based.position_size_base", 0.015
            ),  # Phase 51.9-5: mlプレフィックス追加・設定ファイルから取得
            # フィルター設定
            "market_stress_threshold": get_threshold(
                "ml.dynamic_confidence.strategies.atr_based.market_stress_threshold", 0.7
            ),  # 市場ストレス閾値
            "min_atr_ratio": get_threshold(
                "ml.dynamic_confidence.strategies.atr_based.min_atr_ratio", 0.5
            ),  # 最小ATR比率（低ボラ回避）
            # Phase 28完了・Phase 29最適化対応（thresholds.yaml統合）
            "normal_volatility_strength": get_threshold("strategies.atr_based.normal_volatility_strength", 0.3),
        }
        merged_config = {**default_config, **(config or {})}
        super().__init__(name="ATRBased", config=merged_config)

    def analyze(
        self, df: pd.DataFrame, multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> StrategySignal:
        """市場分析とシグナル生成."""
        try:
            self.logger.info(
                f"[ATRBased] 分析開始 - データシェイプ: {df.shape}, 利用可能列: {list(df.columns)[:10]}..."
            )
            self.logger.debug("[ATRBased] 分析開始")
            current_price = float(df["close"].iloc[-1])
            # 各指標分析
            bb_analysis = self._analyze_bb_position(df)
            rsi_analysis = self._analyze_rsi_momentum(df)
            atr_analysis = self._analyze_atr_volatility(df)
            # Phase 28完了・Phase 29最適化: market_stress削除（15特徴量統一）
            # stress_analysis = self._analyze_market_stress(df)
            # 市場不確実性計算（統一ロジック）
            market_uncertainty = self._calculate_market_uncertainty(df)
            # 統合判定（市場データ基づく動的調整）
            signal_decision = self._make_decision(bb_analysis, rsi_analysis, atr_analysis, None, market_uncertainty)
            # シグナル生成（Phase 31: multi_timeframe_data渡し）
            signal = self._create_signal(signal_decision, current_price, df, multi_timeframe_data)
            self.logger.debug(f"[ATRBased] シグナル: {signal.action} (信頼度: {signal.confidence:.3f})")
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
            # 設定から信頼度パラメータを取得
            from ...core.config import get_threshold

            base_confidence = get_threshold("strategies.atr_based.base_confidence", 0.3)
            confidence_multiplier = get_threshold("strategies.atr_based.confidence_multiplier", 0.4)
            confidence = base_confidence + strength * confidence_multiplier if abs(signal) > 0 else 0.0
            return {
                "signal": signal,
                "strength": strength,
                "confidence": confidence,
                "bb_position": current_bb_pos,
                "analysis": f"BB位置: {current_bb_pos:.2f} -> {['売り', 'なし', '買い'][signal + 1]}",
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
                # 循環インポート回避のため遅延インポート
                from ...core.config.threshold_manager import get_threshold

                strength_normalize = get_threshold(
                    "ml.dynamic_confidence.strategies.atr_based.strength_normalize", 30.0
                )
                strength = min((current_rsi - self.config["rsi_overbought"]) / strength_normalize, 1.0)
            elif current_rsi <= self.config["rsi_oversold"]:
                signal = 1  # 買いシグナル
                # 循環インポート回避のため遅延インポート
                from ...core.config.threshold_manager import get_threshold

                strength_normalize = get_threshold(
                    "ml.dynamic_confidence.strategies.atr_based.strength_normalize", 30.0
                )
                strength = min((self.config["rsi_oversold"] - current_rsi) / strength_normalize, 1.0)
            else:
                signal = 0
                strength = 0.0
            # 循環インポート回避のため遅延インポート
            from ...core.config.threshold_manager import get_threshold

            rsi_base = get_threshold("ml.dynamic_confidence.strategies.atr_based.rsi_base", 0.2)
            rsi_multiplier = get_threshold("ml.dynamic_confidence.strategies.atr_based.rsi_multiplier", 0.3)
            confidence = rsi_base + strength * rsi_multiplier if abs(signal) > 0 else 0.0
            return {
                "signal": signal,
                "strength": strength,
                "confidence": confidence,
                "rsi": current_rsi,
                "analysis": f"RSI: {current_rsi:.1f} -> {['売り', 'なし', '買い'][signal + 1]}",
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
                strength = self.config["normal_volatility_strength"]  # thresholds.yaml設定使用
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

    def _calculate_market_uncertainty(self, df: pd.DataFrame) -> float:
        """
        市場データ基づく不確実性計算（Phase 38.4: 統合ユーティリティ使用）

        Args:
            df: 市場データ

        Returns:
            float: 市場不確実性係数（0-0.1の範囲）
        """
        return MarketUncertaintyCalculator.calculate(df)

    def _make_decision(
        self,
        bb_analysis: Dict[str, Any],
        rsi_analysis: Dict[str, Any],
        atr_analysis: Dict[str, Any],
        stress_analysis: Dict[str, Any] = None,
        market_uncertainty: float = 0.02,
    ) -> Dict[str, Any]:
        """統合判定（動的信頼度計算・早期リターン回避）."""
        try:
            # フィルター確認（Phase 28完了・Phase 29最適化: market_stress無効化）
            if stress_analysis and not stress_analysis["filter_ok"]:
                return self._create_hold_decision("市場ストレス高")
            # 低ボラティリティでも動的信頼度を計算（早期リターン回避）
            volatility_penalty = 0.8 if atr_analysis["regime"] == "low" else 1.0
            # シグナル統合（すべてのケースで動的計算実行）
            bb_signal = bb_analysis["signal"]
            rsi_signal = rsi_analysis["signal"]
            # ケース1: 両方にシグナルがある
            if bb_signal != 0 and rsi_signal != 0:
                if bb_signal == rsi_signal:
                    # 両方一致 - 適度な信頼度（過度な信頼度を回避）
                    action = EntryAction.BUY if bb_signal > 0 else EntryAction.SELL
                    # 循環インポート回避のため遅延インポート
                    from ...core.config.threshold_manager import get_threshold

                    base_confidence = (bb_analysis["confidence"] + rsi_analysis["confidence"]) * 0.7
                    confidence_max = get_threshold("ml.dynamic_confidence.strategies.atr_based.agreement_max", 0.65)
                    confidence = min(base_confidence * (1 + market_uncertainty), confidence_max)
                    strength = (bb_analysis["strength"] + rsi_analysis["strength"]) / 2
                    reason = f"BB+RSI一致シグナル ({bb_analysis['bb_position']:.2f}, RSI:{rsi_analysis['rsi']:.1f})"
                else:
                    # 不一致時はより強いシグナルを採用
                    if bb_analysis["confidence"] >= rsi_analysis["confidence"]:
                        action = EntryAction.BUY if bb_signal > 0 else EntryAction.SELL
                        base_confidence = bb_analysis["confidence"] * 0.8  # 不一致ペナルティ
                        confidence = base_confidence * (1 + market_uncertainty)
                        strength = bb_analysis["strength"]
                        reason = f"BB優勢シグナル ({bb_analysis['bb_position']:.2f})"
                    else:
                        action = EntryAction.BUY if rsi_signal > 0 else EntryAction.SELL
                        base_confidence = rsi_analysis["confidence"] * 0.8
                        confidence = base_confidence * (1 + market_uncertainty)
                        strength = rsi_analysis["strength"]
                        reason = f"RSI優勢シグナル ({rsi_analysis['rsi']:.1f})"
            # ケース2: BBシグナルのみ
            elif bb_signal != 0:
                action = EntryAction.BUY if bb_signal > 0 else EntryAction.SELL
                base_confidence = bb_analysis["confidence"] * 0.7  # 単一シグナル減額
                confidence = base_confidence * (1 + market_uncertainty)
                strength = bb_analysis["strength"]
                reason = f"BB単独シグナル ({bb_analysis['bb_position']:.2f})"
            # ケース3: RSIシグナルのみ
            elif rsi_signal != 0:
                action = EntryAction.BUY if rsi_signal > 0 else EntryAction.SELL
                base_confidence = rsi_analysis["confidence"] * 0.7
                confidence = base_confidence * (1 + market_uncertainty)
                strength = rsi_analysis["strength"]
                reason = f"RSI単独シグナル ({rsi_analysis['rsi']:.1f})"
            # ケース4: 明確なシグナルなし - 微弱な動的信頼度を計算
            else:
                # ニュートラル状態でも市場状況に基づく微弱なシグナルを生成
                bb_pos = bb_analysis["bb_position"]
                rsi_val = rsi_analysis["rsi"]
                # 中央値からの乖離に基づく微弱シグナル
                bb_deviation = abs(bb_pos - 0.5)  # 中央(0.5)からの乖離度
                rsi_deviation = abs(rsi_val - 50) / 50  # RSI中央値からの乖離度
                total_deviation = (bb_deviation + rsi_deviation) / 2
                if total_deviation > 0.25:  # 25%以上の大きな乖離でのみシグナル（抑制強化）
                    # 循環インポート回避のため遅延インポート
                    from ...core.config.threshold_manager import get_threshold

                    weak_base = get_threshold("ml.dynamic_confidence.strategies.atr_based.weak_base", 0.08)
                    weak_multiplier = get_threshold("ml.dynamic_confidence.strategies.atr_based.weak_multiplier", 0.1)

                    # より乖離の大きい指標を採用
                    if bb_deviation > rsi_deviation:
                        action = EntryAction.BUY if bb_pos < 0.5 else EntryAction.SELL
                        base_confidence = weak_base + total_deviation * weak_multiplier  # 設定ベース計算
                    else:
                        action = EntryAction.BUY if rsi_val < 50 else EntryAction.SELL
                        base_confidence = weak_base + total_deviation * weak_multiplier  # 設定ベース計算
                    confidence = base_confidence
                    strength = total_deviation
                    reason = f"極微弱逆張り（BB:{bb_pos:.2f}, RSI:{rsi_val:.1f}, 乖離:{total_deviation:.2f}）"
                else:
                    return self._create_hold_decision(f"中立状態（BB:{bb_pos:.2f}, RSI:{rsi_val:.1f}）")
            # ボラティリティ調整適用
            confidence *= volatility_penalty
            # 高ボラティリティボーナス（抑制）
            if atr_analysis["regime"] == "high":
                # 循環インポート回避のため遅延インポート
                from ...core.config.threshold_manager import get_threshold

                volatility_bonus = get_threshold("ml.dynamic_confidence.strategies.atr_based.volatility_bonus", 1.02)
                volatility_max = get_threshold("ml.dynamic_confidence.strategies.atr_based.volatility_max", 0.65)
                confidence = min(confidence * volatility_bonus, volatility_max)  # 設定ベースボーナス・上限
            # 最小信頼度チェック（緩和済み）
            if confidence < self.config["min_confidence"]:
                # 完全拒否ではなく、動的に調整された信頼度を記録
                adjusted_confidence = max(confidence, self.config["min_confidence"] * 0.8)
                return {
                    "action": EntryAction.HOLD,
                    "confidence": adjusted_confidence,
                    "strength": strength if "strength" in locals() else 0.0,
                    "analysis": f"ATR動的HOLD: {reason} (調整信頼度: {adjusted_confidence:.3f})",
                }
            return {
                "action": action,
                "confidence": confidence,
                "strength": strength,
                "analysis": f"ATR動的判定: {action} (信頼度: {confidence:.3f}, {reason})",
            }
        except Exception as e:
            self.logger.error(f"統合判定エラー: {e}")
            return self._create_hold_decision("判定エラー")

    def _create_hold_decision(self, reason: str) -> Dict[str, Any]:
        """ホールド決定作成."""
        # 循環インポート回避のため遅延インポート
        from ...core.config.threshold_manager import get_threshold

        hold_confidence = get_threshold("strategies.atr_based.hold_confidence", 0.5)
        return {
            "action": EntryAction.HOLD,
            "confidence": hold_confidence,
            "strength": 0.0,
            "analysis": f"ATR逆張り: hold ({reason}) [confidence={hold_confidence}]",
        }

    def _create_signal(
        self,
        decision: Dict[str, Any],
        current_price: float,
        df: pd.DataFrame,
        multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> StrategySignal:
        """シグナル作成 - 共通モジュール利用（Phase 31: マルチタイムフレーム対応）."""
        # Phase 31: multi_timeframe_dataを渡して15m足ATR取得
        return SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.name,
            decision=decision,
            current_price=current_price,
            df=df,
            config=self.config,
            strategy_type=StrategyType.ATR_BASED,
            multi_timeframe_data=multi_timeframe_data,
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
            # Phase 28完了・Phase 29最適化: market_stress削除（15特徴量統一）
        ]

"""
ATRベース戦略実装 - シンプル逆張り戦略

ATRとボリンジャーバンドを使用したシンプルな逆張り戦略。
過度な価格変動時の平均回帰を狙う。

戦略ロジック:
1. ATRで市場ボラティリティを測定
2. ボリンジャーバンド位置で過買い・過売り判定
3. RSIで追加確認
4. 市場ストレスで異常状況フィルター

Phase 52.4-B完了: 市場不確実性計算統合・重複コード削減
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
            # Phase 52.4-B: リスク管理（ハードコード削除・設定ファイル一元管理）
            "stop_loss_atr_multiplier": get_threshold("sl_atr_normal_vol", 2.0),
            "take_profit_ratio": get_threshold(
                "position_management.take_profit.default_ratio"
            ),  # Phase 52.4-B: TP設定
            "position_size_base": get_threshold(
                "ml.dynamic_confidence.strategies.atr_based.position_size_base", 0.015
            ),  # Phase 52.4-B: mlプレフィックス・設定ファイルから取得
            # フィルター設定
            "market_stress_threshold": get_threshold(
                "ml.dynamic_confidence.strategies.atr_based.market_stress_threshold", 0.7
            ),  # 市場ストレス閾値
            "min_atr_ratio": get_threshold(
                "ml.dynamic_confidence.strategies.atr_based.min_atr_ratio", 0.5
            ),  # 最小ATR比率（低ボラ回避）
            # Phase 28完了・Phase 29最適化対応（thresholds.yaml統合）
            "normal_volatility_strength": get_threshold(
                "strategies.atr_based.normal_volatility_strength", 0.3
            ),
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
            signal_decision = self._make_decision(
                bb_analysis, rsi_analysis, atr_analysis, None, market_uncertainty
            )
            # シグナル生成（Phase 31: multi_timeframe_data渡し）
            signal = self._create_signal(signal_decision, current_price, df, multi_timeframe_data)
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
            # 設定から信頼度パラメータを取得（Phase 54.6: デフォルト値更新）
            from ...core.config import get_threshold

            # Phase 54改善適用: base 0.3→0.38, multiplier 0.4→0.55
            base_confidence = get_threshold("strategies.atr_based.base_confidence", 0.38)
            confidence_multiplier = get_threshold(
                "strategies.atr_based.confidence_multiplier", 0.55
            )
            confidence = (
                base_confidence + strength * confidence_multiplier if abs(signal) > 0 else 0.0
            )
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
                strength = min(
                    (current_rsi - self.config["rsi_overbought"]) / strength_normalize, 1.0
                )
            elif current_rsi <= self.config["rsi_oversold"]:
                signal = 1  # 買いシグナル
                # 循環インポート回避のため遅延インポート
                from ...core.config.threshold_manager import get_threshold

                strength_normalize = get_threshold(
                    "ml.dynamic_confidence.strategies.atr_based.strength_normalize", 30.0
                )
                strength = min(
                    (self.config["rsi_oversold"] - current_rsi) / strength_normalize, 1.0
                )
            else:
                signal = 0
                strength = 0.0
            # 循環インポート回避のため遅延インポート
            from ...core.config.threshold_manager import get_threshold

            rsi_base = get_threshold("ml.dynamic_confidence.strategies.atr_based.rsi_base", 0.2)
            rsi_multiplier = get_threshold(
                "ml.dynamic_confidence.strategies.atr_based.rsi_multiplier", 0.3
            )
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

    def _analyze_atr_reversal_signal(
        self,
        bb_analysis: Dict[str, Any],
        rsi_analysis: Dict[str, Any],
        atr_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        ATR反転シグナル分析（Phase 60.14: BBReversalパターン統一）

        全ての状況で統一された動的信頼度計算を実行。
        BBReversalと同じシンプルな設計パターンに統一。

        Args:
            bb_analysis: BB位置分析結果
            rsi_analysis: RSI分析結果
            atr_analysis: ATRボラティリティ分析結果

        Returns:
            Dict[str, Any]: シグナル判断結果
        """
        from ...core.config.threshold_manager import get_threshold

        bb_pos = bb_analysis.get("bb_position", 0.5)
        rsi_val = rsi_analysis.get("rsi", 50.0)
        volatility_regime = atr_analysis.get("regime", "normal")

        # === Phase 60.14: 統一動的信頼度計算（BBReversalと同じパターン） ===

        # 設定から取得
        bb_weight = get_threshold("strategies.atr_based.bb_weight", 0.6)
        rsi_weight = get_threshold("strategies.atr_based.rsi_weight", 0.4)
        min_confidence = get_threshold("strategies.atr_based.min_confidence", 0.15)
        max_confidence = get_threshold("strategies.atr_based.max_confidence", 0.55)
        signal_threshold = get_threshold("strategies.atr_based.signal_threshold", 0.4)

        # BB位置の偏り度合い（0-1スケールに正規化）
        bb_deviation = abs(bb_pos - 0.5) * 2  # 0 ~ 1

        # RSIの偏り度合い（0-1スケールに正規化）
        rsi_deviation = abs(rsi_val - 50) / 50  # 0 ~ 1

        # 総合偏り度合い（重み付け平均）
        total_deviation = bb_deviation * bb_weight + rsi_deviation * rsi_weight

        # 動的信頼度計算（偏りが大きいほど高い）
        confidence_range = max_confidence - min_confidence
        dynamic_confidence = min_confidence + total_deviation * confidence_range

        # ボラティリティ調整（高ボラ時はボーナス、低ボラ時はペナルティ）
        if volatility_regime == "high":
            dynamic_confidence = min(dynamic_confidence * 1.1, max_confidence)
        elif volatility_regime == "low":
            dynamic_confidence = dynamic_confidence * 0.9

        # === 方向判定（BBReversalと同じパターン） ===

        # SELL方向の強さ
        sell_strength = 0.0
        if bb_pos > 0.5:
            sell_strength += (bb_pos - 0.5) * 2  # 0 ~ 1
        if rsi_val > 50:
            sell_strength += (rsi_val - 50) / 50  # 0 ~ 1

        # BUY方向の強さ
        buy_strength = 0.0
        if bb_pos < 0.5:
            buy_strength += (0.5 - bb_pos) * 2  # 0 ~ 1
        if rsi_val < 50:
            buy_strength += (50 - rsi_val) / 50  # 0 ~ 1

        # === シグナル決定 ===

        if sell_strength > buy_strength and sell_strength >= signal_threshold:
            return {
                "action": EntryAction.SELL,
                "confidence": dynamic_confidence,
                "strength": sell_strength,
                "reason": f"ATR反転SELL (BB={bb_pos:.2f}, RSI={rsi_val:.1f}, "
                f"vol={volatility_regime}, 強度={sell_strength:.2f})",
                "analysis": f"過買い圏→反転下落期待 (信頼度={dynamic_confidence:.3f})",
            }
        elif buy_strength > sell_strength and buy_strength >= signal_threshold:
            return {
                "action": EntryAction.BUY,
                "confidence": dynamic_confidence,
                "strength": buy_strength,
                "reason": f"ATR反転BUY (BB={bb_pos:.2f}, RSI={rsi_val:.1f}, "
                f"vol={volatility_regime}, 強度={buy_strength:.2f})",
                "analysis": f"過売り圏→反転上昇期待 (信頼度={dynamic_confidence:.3f})",
            }
        else:
            # HOLDでも動的信頼度を使用（フォールバック値不使用）
            return {
                "action": EntryAction.HOLD,
                "confidence": dynamic_confidence,
                "strength": max(sell_strength, buy_strength),
                "reason": f"ATR中立 (BB={bb_pos:.2f}, RSI={rsi_val:.1f}, "
                f"vol={volatility_regime}, 強度={max(sell_strength, buy_strength):.2f})",
                "analysis": f"方向性不明確 (信頼度={dynamic_confidence:.3f})",
            }

    def _make_decision(
        self,
        bb_analysis: Dict[str, Any],
        rsi_analysis: Dict[str, Any],
        atr_analysis: Dict[str, Any],
        stress_analysis: Dict[str, Any] = None,
        market_uncertainty: float = 0.02,
    ) -> Dict[str, Any]:
        """統合判定（Phase 60.14: シンプル化）."""
        try:
            # Phase 60.14: BBReversalパターンの統一シグナル分析
            return self._analyze_atr_reversal_signal(bb_analysis, rsi_analysis, atr_analysis)
        except Exception as e:
            self.logger.error(f"統合判定エラー: {e}")
            return {
                "action": EntryAction.HOLD,
                "confidence": 0.15,
                "strength": 0.0,
                "analysis": f"判定エラー: {e}",
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

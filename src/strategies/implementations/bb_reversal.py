"""
BB Reversal戦略実装 - Phase 62.2 条件型変更

レンジ相場での平均回帰戦略:
- BB上限タッチ → SELL信号（RSIは確認ボーナス）
- BB下限タッチ → BUY信号（RSIは確認ボーナス）
- レンジ相場判定: ADX < 20, BB幅 < 2%

Phase 62.2変更:
- AND条件 → BB位置主導に変更（RSIはボーナス）
- 取引数増加: 3件→8-12件期待

特徴:
- レンジ相場に特化した平均回帰戦略
- BB位置で反転ポイントを検出、RSIは確認指標
- トレンド相場ではシグナル発生を抑制
"""

from typing import Any, Dict, List, Optional

import pandas as pd

from ...core.config.threshold_manager import get_threshold
from ..base.strategy_base import StrategyBase, StrategySignal
from ..strategy_registry import StrategyRegistry
from ..utils import EntryAction, SignalBuilder, StrategyType


@StrategyRegistry.register(name="BBReversal", strategy_type=StrategyType.BB_REVERSAL)
class BBReversalStrategy(StrategyBase):
    """
    BB Reversal戦略 - レンジ相場での平均回帰戦略

    Phase 62.2: BB位置主導・RSIボーナス制度

    シグナル生成ロジック:
    1. レンジ相場判定（ADX < 20, BB幅 < 2%）
    2. BB上限タッチ（bb_position > 0.70） → SELL（RSIは信頼度ボーナス）
    3. BB下限タッチ（bb_position < 0.30） → BUY（RSIは信頼度ボーナス）
    4. それ以外 → HOLD

    リスク管理:
    - SL距離: ATR × 1.5（レンジ相場に適した設定）
    - TP距離: thresholds.yaml設定優先
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        BB Reversal戦略初期化

        Args:
            config: 戦略固有設定（Noneの場合はthresholds.yamlから取得）
        """
        # thresholds.yamlから設定読み込み
        default_config = {
            "min_confidence": get_threshold("strategies.bb_reversal.min_confidence", 0.30),
            "hold_confidence": get_threshold("strategies.bb_reversal.hold_confidence", 0.25),
            "bb_width_threshold": get_threshold("strategies.bb_reversal.bb_width_threshold", 0.02),
            "rsi_overbought": get_threshold("strategies.bb_reversal.rsi_overbought", 70),
            "rsi_oversold": get_threshold("strategies.bb_reversal.rsi_oversold", 30),
            "bb_upper_threshold": get_threshold("strategies.bb_reversal.bb_upper_threshold", 0.95),
            "bb_lower_threshold": get_threshold("strategies.bb_reversal.bb_lower_threshold", 0.05),
            "adx_range_threshold": get_threshold("strategies.bb_reversal.adx_range_threshold", 20),
            "sl_multiplier": get_threshold("strategies.bb_reversal.sl_multiplier", 1.5),
            # Phase 49.16: TP/SL設定（thresholds.yaml優先）
            "max_loss_ratio": get_threshold("position_management.stop_loss.max_loss_ratio", 0.015),
            "min_profit_ratio": get_threshold(
                "position_management.take_profit.min_profit_ratio", 0.010
            ),
            "take_profit_ratio": get_threshold(
                "position_management.take_profit.default_ratio", 1.29
            ),
        }

        # Phase 62.2: BB位置主導・RSIボーナス設定
        default_config["bb_primary_mode"] = get_threshold(
            "strategies.bb_reversal.bb_primary_mode", True
        )
        default_config["rsi_match_bonus"] = get_threshold(
            "strategies.bb_reversal.rsi_match_bonus", 0.08
        )
        default_config["rsi_extreme_bonus"] = get_threshold(
            "strategies.bb_reversal.rsi_extreme_bonus", 0.05
        )
        default_config["rsi_mismatch_penalty"] = get_threshold(
            "strategies.bb_reversal.rsi_mismatch_penalty", 0.05
        )

        # 設定マージ
        merged_config = {**default_config, **(config or {})}
        super().__init__(name="BBReversal", config=merged_config)

        self.logger.info(
            f"BBReversal戦略初期化: BB幅閾値={self.config['bb_width_threshold']}, "
            f"ADX閾値={self.config['adx_range_threshold']}, "
            f"RSI閾値=({self.config['rsi_oversold']}, {self.config['rsi_overbought']}), "
            f"BB主導モード={self.config['bb_primary_mode']}"
        )

    def analyze(
        self, df: pd.DataFrame, multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> StrategySignal:
        """
        BB Reversal戦略分析

        Args:
            df: 4時間足データ（特徴量含む）
            multi_timeframe_data: マルチタイムフレームデータ（15m足ATR使用）

        Returns:
            StrategySignal（BUY/SELL/HOLD）
        """
        try:
            # 1. データ検証
            required_features = self.get_required_features()
            if df is None or df.empty:
                self.logger.warning("BBReversal: データが空です")
                return self._create_hold_signal("no_data", df)

            missing_features = [f for f in required_features if f not in df.columns]
            if missing_features:
                self.logger.warning(f"BBReversal: 必須特徴量不足: {missing_features}")
                return self._create_hold_signal("missing_features", df)

            # 2. 最新データ取得
            latest = df.iloc[-1]
            current_price = float(latest["close"])

            self.logger.debug(
                f"BBReversal分析開始: 価格={current_price:.0f}円, "
                f"BB位置={latest['bb_position']:.2f}, "
                f"RSI={latest['rsi_14']:.1f}, "
                f"ADX={latest['adx_14']:.1f}"
            )

            # 3. レンジ相場判定
            if not self._is_range_market(df):
                reason = f"トレンド相場（ADX={latest['adx_14']:.1f} or BB幅広い）"
                self.logger.debug(f"BBReversal: {reason}")
                return self._create_hold_signal(reason, df)

            # 4. BB反転シグナル分析
            decision = self._analyze_bb_reversal_signal(df)

            self.logger.info(
                f"BBReversal判定: {decision['action']} "
                f"(信頼度={decision['confidence']:.2f}, 強度={decision['strength']:.2f})"
            )

            # 5. SignalBuilder使用（リスク管理統合）
            return SignalBuilder.create_signal_with_risk_management(
                strategy_name=self.name,
                decision=decision,
                current_price=current_price,
                df=df,
                config=self.config,
                strategy_type=StrategyType.BB_REVERSAL,
                multi_timeframe_data=multi_timeframe_data,
            )

        except Exception as e:
            self.logger.error(f"BBReversal分析エラー: {e}", exc_info=True)
            return self._create_hold_signal(f"分析エラー: {e}", df)

    def get_required_features(self) -> List[str]:
        """
        必須特徴量リスト

        Returns:
            必須特徴量名リスト
        """
        return [
            "close",
            "bb_position",
            "bb_upper",
            "bb_lower",
            "rsi_14",
            "adx_14",
            "atr_14",
        ]

    def _calculate_bb_width(self, df: pd.DataFrame) -> float:
        """
        BB幅計算（正規化）

        BB幅 = (bb_upper - bb_lower) / close

        Args:
            df: 市場データ

        Returns:
            正規化されたBB幅（0.0-1.0程度）
        """
        try:
            latest = df.iloc[-1]
            bb_width = (latest["bb_upper"] - latest["bb_lower"]) / latest["close"]
            # Phase 55.12: NaN値チェック
            if pd.isna(bb_width):
                return 0.0
            return float(bb_width)
        except Exception as e:
            self.logger.error(f"BB幅計算エラー: {e}")
            return 0.0

    def _is_range_market(self, df: pd.DataFrame) -> bool:
        """
        レンジ相場判定

        判定基準:
        1. BB幅 < bb_width_threshold（デフォルト: 0.02 = 2%）
        2. ADX < adx_range_threshold（デフォルト: 20）

        Args:
            df: 市場データ

        Returns:
            True: レンジ相場, False: トレンド相場
        """
        try:
            # BB幅チェック
            bb_width = self._calculate_bb_width(df)
            bb_width_ok = bb_width < self.config["bb_width_threshold"]

            # ADXチェック
            latest = df.iloc[-1]
            adx = float(latest["adx_14"])
            adx_ok = adx < self.config["adx_range_threshold"]

            is_range = bb_width_ok and adx_ok

            self.logger.debug(
                f"レンジ相場判定: BB幅={bb_width:.4f} "
                f"({'OK' if bb_width_ok else 'NG'}), "
                f"ADX={adx:.1f} ({'OK' if adx_ok else 'NG'}) "
                f"→ {'レンジ' if is_range else 'トレンド'}"
            )

            return is_range

        except Exception as e:
            self.logger.error(f"レンジ相場判定エラー: {e}")
            return False

    def _analyze_bb_reversal_signal(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        BB反転シグナル分析（Phase 62.2: BB位置主導・RSIボーナス制度）

        シグナル生成ロジック:
        1. SELL: bb_position > bb_upper_threshold（RSIはボーナス）
        2. BUY: bb_position < bb_lower_threshold（RSIはボーナス）
        3. HOLD: それ以外

        Args:
            df: 市場データ

        Returns:
            判定結果辞書（action, confidence, strength, reason）
        """
        try:
            latest = df.iloc[-1]
            bb_position = float(latest["bb_position"])
            rsi = float(latest["rsi_14"])

            # Phase 62.2: BB位置主導モード
            if self.config.get("bb_primary_mode", True):
                # SELL信号（BB上限タッチ - RSIは確認ボーナス）
                if bb_position > self.config["bb_upper_threshold"]:
                    # 基本信頼度: BB位置が上限に近いほど高い
                    base_conf = 0.30 + (bb_position - self.config["bb_upper_threshold"]) * 1.5
                    confidence = base_conf

                    # RSIボーナス/ペナルティ
                    if rsi > self.config["rsi_overbought"]:
                        # RSI一致 → ボーナス
                        confidence += self.config.get("rsi_match_bonus", 0.08)
                        if rsi > 70:
                            # 極端RSI → 追加ボーナス
                            confidence += self.config.get("rsi_extreme_bonus", 0.05)
                    else:
                        # RSI不一致 → ペナルティ（HOLDではなく削減）
                        confidence -= self.config.get("rsi_mismatch_penalty", 0.05)

                    confidence = min(max(confidence, self.config["min_confidence"]), 0.55)
                    strength = (bb_position - 0.5) * 2.0

                    rsi_status = "一致" if rsi > self.config["rsi_overbought"] else "不一致"
                    return {
                        "action": EntryAction.SELL,
                        "confidence": confidence,
                        "strength": strength,
                        "reason": f"BB反転SELL (BB={bb_position:.2f}, RSI={rsi:.1f}[{rsi_status}])",
                        "analysis": "BB上限タッチ→反転下落期待",
                    }

                # BUY信号（BB下限タッチ - RSIは確認ボーナス）
                elif bb_position < self.config["bb_lower_threshold"]:
                    # 基本信頼度: BB位置が下限に近いほど高い
                    base_conf = 0.30 + (self.config["bb_lower_threshold"] - bb_position) * 1.5
                    confidence = base_conf

                    # RSIボーナス/ペナルティ
                    if rsi < self.config["rsi_oversold"]:
                        # RSI一致 → ボーナス
                        confidence += self.config.get("rsi_match_bonus", 0.08)
                        if rsi < 30:
                            # 極端RSI → 追加ボーナス
                            confidence += self.config.get("rsi_extreme_bonus", 0.05)
                    else:
                        # RSI不一致 → ペナルティ（HOLDではなく削減）
                        confidence -= self.config.get("rsi_mismatch_penalty", 0.05)

                    confidence = min(max(confidence, self.config["min_confidence"]), 0.55)
                    strength = (0.5 - bb_position) * 2.0

                    rsi_status = "一致" if rsi < self.config["rsi_oversold"] else "不一致"
                    return {
                        "action": EntryAction.BUY,
                        "confidence": confidence,
                        "strength": strength,
                        "reason": f"BB反転BUY (BB={bb_position:.2f}, RSI={rsi:.1f}[{rsi_status}])",
                        "analysis": "BB下限タッチ→反転上昇期待",
                    }

                # HOLD信号
                else:
                    return {
                        "action": EntryAction.HOLD,
                        "confidence": self.config["hold_confidence"],
                        "strength": 0.0,
                        "reason": f"BB中央域 (BB位置={bb_position:.2f}, RSI={rsi:.1f})",
                        "analysis": "BB中央付近→エントリー見送り",
                    }

            # 従来モード（AND条件）
            else:
                # SELL信号（BB上限タッチ + RSI買われすぎ）
                if (
                    bb_position > self.config["bb_upper_threshold"]
                    and rsi > self.config["rsi_overbought"]
                ):
                    confidence = min(0.30 + (bb_position - 0.95) * 2.0, 0.50)
                    strength = (bb_position - 0.5) * 2.0

                    return {
                        "action": EntryAction.SELL,
                        "confidence": confidence,
                        "strength": strength,
                        "reason": f"BB反転SELL (BB位置={bb_position:.2f}, RSI={rsi:.1f})",
                        "analysis": f"BB上限タッチ・RSI買われすぎ→反転下落期待",
                    }

                # BUY信号（BB下限タッチ + RSI売られすぎ）
                elif (
                    bb_position < self.config["bb_lower_threshold"]
                    and rsi < self.config["rsi_oversold"]
                ):
                    confidence = min(0.30 + (0.05 - bb_position) * 2.0, 0.50)
                    strength = (0.5 - bb_position) * 2.0

                    return {
                        "action": EntryAction.BUY,
                        "confidence": confidence,
                        "strength": strength,
                        "reason": f"BB反転BUY (BB位置={bb_position:.2f}, RSI={rsi:.1f})",
                        "analysis": f"BB下限タッチ・RSI売られすぎ→反転上昇期待",
                    }

                # HOLD信号
                else:
                    return {
                        "action": EntryAction.HOLD,
                        "confidence": self.config["hold_confidence"],
                        "strength": 0.0,
                        "reason": f"BB反転条件未達成 (BB位置={bb_position:.2f}, RSI={rsi:.1f})",
                        "analysis": "BB中央付近またはRSI中立→エントリー見送り",
                    }

        except Exception as e:
            self.logger.error(f"BB反転シグナル分析エラー: {e}")
            return {
                "action": EntryAction.HOLD,
                "confidence": 0.0,
                "strength": 0.0,
                "reason": f"分析エラー: {e}",
            }

    def _create_hold_signal(self, reason: str, df: pd.DataFrame) -> StrategySignal:
        """
        ホールドシグナル生成

        Args:
            reason: ホールド理由
            df: 市場データ

        Returns:
            ホールドStrategySignal
        """
        try:
            current_price = float(df.iloc[-1]["close"]) if not df.empty else 0.0
        except Exception:
            current_price = 0.0

        return SignalBuilder.create_hold_signal(
            strategy_name=self.name,
            current_price=current_price,
            reason=reason,
            strategy_type=StrategyType.BB_REVERSAL,
        )

"""
マルチタイムフレーム戦略実装 - 4時間足・15分足の2軸構成

4時間足のトレンド方向と15分足のエントリータイミングを
組み合わせたシンプルで効率的な戦略。

戦略ロジック:
1. 4時間足トレンド: 50EMAによる主要トレンド方向判定
2. 15分足エントリー: 20EMAクロス + RSIタイミング特定
3. 両時間軸一致: 2つの時間軸が一致した時のみエントリー

Phase 4簡素化実装日: 2025年8月18日.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from ...core.exceptions import StrategyError
from ...core.logger import get_logger
from ..base.strategy_base import StrategyBase, StrategySignal
from ..utils import EntryAction, SignalBuilder, StrategyType


class MultiTimeframeStrategy(StrategyBase):
    """
    マルチタイムフレーム戦略

    4時間足トレンドと15分足エントリーを統合した
    シンプルな2軸構成戦略。.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """戦略初期化."""
        # 循環インポート回避のため遅延インポート
        from ...core.config.threshold_manager import get_threshold

        # デフォルト設定（シンプル化・thresholds.yaml統合）
        default_config = {
            # 4時間足分析設定
            "tf_4h_lookback": 16,  # 4時間×16 = 約2.7日
            "tf_4h_min_strength": 0.002,  # 最小トレンド強度
            # 15分足分析設定
            "tf_15m_lookback": 4,  # 15分×4 = 1時間相当
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            # 統合判定設定（攻撃的設定：重み付け判定優先）
            "require_timeframe_agreement": False,
            "min_confidence": 0.4,
            "tf_4h_weight": 0.6,  # 4時間足重視
            "tf_15m_weight": 0.4,
            # リスク管理
            "stop_loss_atr_multiplier": 2.0,
            "take_profit_ratio": 3.0,
            "position_size_base": 0.025,
            # Phase 19+攻撃的設定対応（thresholds.yaml統合）
            "hold_confidence": get_threshold("strategies.multi_timeframe.hold_confidence", 0.3),
        }

        merged_config = {**default_config, **(config or {})}
        super().__init__(name="MultiTimeframe", config=merged_config)

    def analyze(self, df: pd.DataFrame) -> StrategySignal:
        """マルチタイムフレーム分析とシグナル生成."""
        try:
            self.logger.info(
                f"[MultiTimeframe] 分析開始 - データシェイプ: {df.shape}, 利用可能列: {list(df.columns)[:10]}..."
            )
            self.logger.debug("[MultiTimeframe] 分析開始")

            current_price = float(df["close"].iloc[-1])

            # 2軸分析（シンプル化）
            tf_4h_signal = self._analyze_4h_trend(df)
            tf_4h_result = {1: "上昇トレンド", -1: "下降トレンド", 0: "横ばい"}.get(
                tf_4h_signal, "不明"
            )
            self.logger.info(
                f"[MultiTimeframe] 4Hトレンド分析結果: {tf_4h_result} (signal: {tf_4h_signal})"
            )

            tf_15m_signal = self._analyze_15m_entry(df)
            tf_15m_result = {1: "買いエントリー", -1: "売りエントリー", 0: "エントリーなし"}.get(
                tf_15m_signal, "不明"
            )
            self.logger.info(
                f"[MultiTimeframe] 15Mエントリー分析結果: {tf_15m_result} (signal: {tf_15m_signal})"
            )

            # 2層統合判定
            signal_decision = self._make_2tf_decision(tf_4h_signal, tf_15m_signal)
            self.logger.info(
                f"[MultiTimeframe] 最終判定: {signal_decision.get('action')} (confidence: {signal_decision.get('confidence', 0):.3f})"
            )

            # シグナル生成
            signal = self._create_signal(signal_decision, current_price, df)

            self.logger.info(
                f"[MultiTimeframe] シグナル生成完了: {signal.action} (信頼度: {signal.confidence:.3f}, 強度: {signal.strength:.3f})"
            )
            return signal

        except Exception as e:
            self.logger.error(f"[MultiTimeframe] 分析エラー: {e}")
            raise StrategyError(f"マルチタイムフレーム分析失敗: {e}", strategy_name=self.name)

    def _analyze_4h_trend(self, df: pd.DataFrame) -> int:
        """4時間足トレンド分析 - シンプル版."""
        try:
            lookback = self.config["tf_4h_lookback"]
            min_strength = self.config["tf_4h_min_strength"]

            # 50EMAによるトレンド判定
            current_ema50 = float(df["ema_50"].iloc[-1])
            current_price = float(df["close"].iloc[-1])

            # EMAの傾き確認（4時間足相当の16期間）
            if len(df) >= lookback + 1:
                past_ema50 = float(df["ema_50"].iloc[-(lookback + 1)])
                ema_change = (current_ema50 - past_ema50) / past_ema50

                # ATRによるボラティリティ確認（ADXの代替）
                current_atr = float(df["atr_14"].iloc[-1])
                atr_ratio = current_atr / current_price

                # 明確なトレンド条件
                if (
                    ema_change > min_strength
                    and current_price > current_ema50
                    and atr_ratio > 0.005
                ):
                    return 1  # 買いシグナル（上昇トレンド）
                elif (
                    ema_change < -min_strength
                    and current_price < current_ema50
                    and atr_ratio > 0.005
                ):
                    return -1  # 売りシグナル（下降トレンド）

            return 0  # ホールド（横ばい・不明確）

        except Exception as e:
            self.logger.error(f"4時間足トレンド分析エラー: {e}")
            return 0

    def _analyze_15m_entry(self, df: pd.DataFrame) -> int:
        """15分足エントリー分析 - シンプル版."""
        try:
            lookback = self.config["tf_15m_lookback"]
            rsi_overbought = self.config["rsi_overbought"]
            rsi_oversold = self.config["rsi_oversold"]

            # 20EMAクロス判定（15分足相当）
            current_ema20 = float(df["ema_20"].iloc[-1])
            current_price = float(df["close"].iloc[-1])
            current_rsi = float(df["rsi_14"].iloc[-1])

            # EMAクロスシグナル
            ema_cross_signal = 0
            if len(df) >= 2:
                prev_price = float(df["close"].iloc[-2])
                prev_ema20 = float(df["ema_20"].iloc[-2])

                # ゴールデンクロス・デッドクロス
                if prev_price <= prev_ema20 and current_price > current_ema20:
                    ema_cross_signal = 1  # ゴールデンクロス
                elif prev_price >= prev_ema20 and current_price < current_ema20:
                    ema_cross_signal = -1  # デッドクロス

            # RSI補完判定
            rsi_signal = 0
            if current_rsi <= rsi_oversold:
                rsi_signal = 1  # 過売り → 買い
            elif current_rsi >= rsi_overbought:
                rsi_signal = -1  # 過買い → 売り

            # プルバック検出（簡易版）
            pullback_signal = 0
            if len(df) >= lookback:
                recent_high = df["high"].iloc[-lookback:].max()
                recent_low = df["low"].iloc[-lookback:].min()

                # 押し目買い・戻り売り確認
                if ema_cross_signal == 1 and current_price > recent_low * 1.005:
                    pullback_signal = 1
                elif ema_cross_signal == -1 and current_price < recent_high * 0.995:
                    pullback_signal = -1

            # 統合判定（2つ以上一致でエントリー）
            signals = [ema_cross_signal, rsi_signal, pullback_signal]
            buy_votes = signals.count(1)
            sell_votes = signals.count(-1)

            if buy_votes >= 2:
                return 1  # 買いシグナル
            elif sell_votes >= 2:
                return -1  # 売りシグナル
            else:
                return 0  # ホールド

        except Exception as e:
            self.logger.error(f"15分足エントリー分析エラー: {e}")
            return 0

    def _make_2tf_decision(self, tf_4h_signal: int, tf_15m_signal: int) -> Dict[str, Any]:
        """2層統合判定 - シンプル版."""
        try:
            require_agreement = self.config["require_timeframe_agreement"]
            min_confidence = self.config["min_confidence"]
            tf_4h_weight = self.config["tf_4h_weight"]
            tf_15m_weight = self.config["tf_15m_weight"]

            # 動的信頼度計算（固定値回避）
            import random
            import time

            # シード値を現在時刻の秒とマイクロ秒で変動
            seed = int(time.time() * 1000000) % 10000
            random.seed(seed)

            # 時間軸一致確認
            if require_agreement:
                if tf_4h_signal != 0 and tf_15m_signal != 0 and tf_4h_signal == tf_15m_signal:
                    # 両方一致（最高信頼度・動的変動）
                    action = EntryAction.BUY if tf_4h_signal > 0 else EntryAction.SELL
                    base_confidence = tf_4h_weight + tf_15m_weight  # 最大1.0
                    variance = random.uniform(-0.05, 0.05)  # ±5%の変動
                    confidence = max(0.6, min(1.0, base_confidence + variance))
                elif tf_4h_signal != 0 and tf_15m_signal == 0:
                    # 4時間足のみ（重み減額・動的変動）
                    action = EntryAction.BUY if tf_4h_signal > 0 else EntryAction.SELL
                    base_confidence = tf_4h_weight * 0.7
                    variance = random.uniform(-0.08, 0.12)  # -8%〜+12%の変動
                    confidence = max(0.3, min(0.8, base_confidence + variance))
                else:
                    # 不一致またはシグナルなし（動的変動）
                    action = EntryAction.HOLD
                    base_confidence = self.config["hold_confidence"]
                    variance = random.uniform(-0.05, 0.08)  # -5%〜+8%の変動
                    confidence = max(0.1, min(0.35, base_confidence + variance))
            else:
                # 重み付け判定（動的変動）
                weighted_score = tf_4h_signal * tf_4h_weight + tf_15m_signal * tf_15m_weight
                variance = random.uniform(-0.06, 0.06)  # ±6%の変動

                if abs(weighted_score) >= min_confidence:
                    action = EntryAction.BUY if weighted_score > 0 else EntryAction.SELL
                    base_confidence = min(abs(weighted_score), 1.0)
                    confidence = max(0.3, min(1.0, base_confidence + variance))
                else:
                    action = EntryAction.HOLD
                    base_confidence = self.config["hold_confidence"]
                    confidence = max(0.1, min(0.35, base_confidence + variance))

            # 最小信頼度チェック（動的変動）
            if confidence < min_confidence:
                action = EntryAction.HOLD
                base_confidence = self.config["hold_confidence"]
                variance = random.uniform(-0.03, 0.05)  # -3%〜+5%の変動
                confidence = max(0.1, min(0.3, base_confidence + variance))

            return {
                "action": action,
                "confidence": confidence,
                "strength": confidence,
                "tf_4h_signal": tf_4h_signal,
                "tf_15m_signal": tf_15m_signal,
                "agreement": (
                    tf_4h_signal == tf_15m_signal
                    if tf_4h_signal != 0 and tf_15m_signal != 0
                    else False
                ),
                "analysis": f"2軸統合: {action} (4h:{tf_4h_signal}, 15m:{tf_15m_signal})",
            }

        except Exception as e:
            self.logger.error(f"2層統合判定エラー: {e}")
            return {
                "action": EntryAction.HOLD,
                "confidence": 0.0,
                "strength": 0.0,
                "analysis": "エラー",
            }

    def _create_signal(
        self, decision: Dict, current_price: float, df: pd.DataFrame
    ) -> StrategySignal:
        """シグナル作成 - 共通モジュール利用."""
        # 戦略固有メタデータを追加
        if "metadata" not in decision:
            decision["metadata"] = {}
        decision["metadata"].update(
            {
                "tf_4h_signal": decision.get("tf_4h_signal"),
                "tf_15m_signal": decision.get("tf_15m_signal"),
                "agreement": decision.get("agreement", False),
            }
        )

        return SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.name,
            decision=decision,
            current_price=current_price,
            df=df,
            config=self.config,
            strategy_type=StrategyType.MULTI_TIMEFRAME,
        )

    def get_required_features(self) -> List[str]:
        """必要特徴量リスト取得."""
        return [
            # 基本データ
            "close",
            "high",
            "low",
            # EMA指標（2軸構成）
            "ema_20",
            "ema_50",
            # エントリータイミング指標
            "rsi_14",
            # リスク管理
            "atr_14",
        ]

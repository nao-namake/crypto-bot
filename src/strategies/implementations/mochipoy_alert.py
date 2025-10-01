"""
もちぽよアラート戦略実装 - シンプルEMA + MACD + RCI

トレンドフォロー戦略の王道指標を組み合わせた
シンプルで効率的な取引戦略。

戦略ロジック:
1. EMAトレンド判定: 20EMA > 50EMA でアップトレンド
2. MACDモメンタム: MACD > 0 でポジティブモメンタム
3. RCI逆張り補完: RCI過買い・過売り水準での確認
4. 多数決判定: 3指標の合意によるエントリー決定

Phase 28完了・Phase 29最適化: 2025年9月27日.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from ...core.exceptions import StrategyError
from ...core.logger import get_logger
from ..base.strategy_base import StrategyBase, StrategySignal
from ..utils import EntryAction, SignalBuilder, StrategyType


class MochipoyAlertStrategy(StrategyBase):
    """
    もちぽよアラート戦略

    EMA、MACD、RCIの3指標を組み合わせた
    シンプルなトレンドフォロー戦略。.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """戦略初期化."""
        # 循環インポート回避のため遅延インポート
        from ...core.config.threshold_manager import get_threshold

        # デフォルト設定（シンプル化・thresholds.yaml統合）
        default_config = {
            # RCI設定
            "rci_period": 14,
            "rci_overbought": 80,
            "rci_oversold": -80,
            # シグナル設定
            "min_confidence": 0.4,
            # リスク管理
            "stop_loss_atr_multiplier": 2.0,
            "take_profit_ratio": 2.0,
            "position_size_base": 0.02,  # 2%
            # Phase 19+攻撃的設定対応（thresholds.yaml統合）
            "hold_confidence": get_threshold("strategies.mochipoy_alert.hold_confidence", 0.3),
        }

        merged_config = {**default_config, **(config or {})}
        super().__init__(name="MochipoyAlert", config=merged_config)

    def analyze(
        self, df: pd.DataFrame, multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> StrategySignal:
        """市場分析とシグナル生成."""
        try:
            self.logger.info(
                f"[MochipoyAlert] 分析開始 - データシェイプ: {df.shape}, 利用可能列: {list(df.columns)[:10]}..."
            )
            self.logger.debug("[MochipoyAlert] 分析開始")

            current_price = float(df["close"].iloc[-1])

            # 3指標のシンプル分析
            ema_signal = self._analyze_ema_trend(df)
            ema_result = {1: "上昇", -1: "下降", 0: "横ばい"}.get(ema_signal, "不明")
            self.logger.info(f"[MochipoyAlert] EMA分析結果: {ema_result} (signal: {ema_signal})")

            macd_signal = self._analyze_macd_momentum(df)
            macd_result = {1: "買い", -1: "売り", 0: "ホールド"}.get(macd_signal, "不明")
            self.logger.info(f"[MochipoyAlert] MACD分析結果: {macd_result} (signal: {macd_signal})")

            rci_signal = self._analyze_rci_reversal(df)
            rci_result = {1: "買い", -1: "売り", 0: "ホールド"}.get(rci_signal, "不明")
            self.logger.info(f"[MochipoyAlert] RCI分析結果: {rci_result} (signal: {rci_signal})")

            # 多数決によるシンプル統合判定
            signal_decision = self._make_simple_decision(ema_signal, macd_signal, rci_signal, df)
            self.logger.info(
                f"[MochipoyAlert] 最終判定: {signal_decision.get('action')} (confidence: {signal_decision.get('confidence', 0):.3f})"
            )

            # シグナル生成（Phase 31: multi_timeframe_data渡し）
            signal = self._create_signal(signal_decision, current_price, df, multi_timeframe_data)

            self.logger.info(
                f"[MochipoyAlert] シグナル生成完了: {signal.action} (信頼度: {signal.confidence:.3f}, 強度: {signal.strength:.3f})"
            )
            return signal

        except Exception as e:
            self.logger.error(f"[MochipoyAlert] 分析エラー: {e}")
            raise StrategyError(f"もちぽよアラート分析失敗: {e}", strategy_name=self.name)

    def _analyze_ema_trend(self, df: pd.DataFrame) -> int:
        """EMAトレンド分析 - シンプルバージョン."""
        try:
            current_ema20 = float(df["ema_20"].iloc[-1])
            current_ema50 = float(df["ema_50"].iloc[-1])

            # シンプルなトレンド判定
            if current_ema20 > current_ema50:
                return 1  # 買いシグナル（アップトレンド）
            elif current_ema20 < current_ema50:
                return -1  # 売りシグナル（ダウントレンド）
            else:
                return 0  # ホールド（横ばい）

        except Exception as e:
            self.logger.error(f"EMAトレンド分析エラー: {e}")
            return 0

    def _analyze_macd_momentum(self, df: pd.DataFrame) -> int:
        """MACDモメンタム分析 - シンプルバージョン."""
        try:
            current_macd = float(df["macd"].iloc[-1])

            # シンプルなモメンタム判定（ゼロライン基準）
            if current_macd > 0:
                return 1  # 買いシグナル（ポジティブモメンタム）
            elif current_macd < 0:
                return -1  # 売りシグナル（ネガティブモメンタム）
            else:
                return 0  # ホールド（ニュートラル）

        except Exception as e:
            self.logger.error(f"MACDモメンタム分析エラー: {e}")
            return 0

    def _analyze_rci_reversal(self, df: pd.DataFrame) -> int:
        """RCI反転分析 - シンプルバージョン."""
        try:
            # RCI計算
            rci_period = self.config["rci_period"]
            overbought = self.config["rci_overbought"]
            oversold = self.config["rci_oversold"]

            rci_values = self._calculate_rci(df["close"], period=rci_period)
            current_rci = rci_values.iloc[-1]

            # シンプルな逆張りシグナル判定
            if current_rci >= overbought:
                return -1  # 売りシグナル（過買い反転）
            elif current_rci <= oversold:
                return 1  # 買いシグナル（過売り反転）
            else:
                return 0  # ホールド（中間水準）

        except Exception as e:
            self.logger.error(f"RCI反転分析エラー: {e}")
            return 0

    def _calculate_rci(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """RCI（順位相関係数）計算 - シンプル版."""
        try:

            def rci_for_window(window):
                if len(window) < period:
                    return 0

                # 価格順位と時間順位
                price_ranks = window.rank(method="min", ascending=False)
                time_ranks = pd.Series(range(len(window), 0, -1), index=window.index)

                # 順位相関係数計算
                n = len(window)
                d_squared_sum = ((price_ranks - time_ranks) ** 2).sum()
                rci = (1 - (6 * d_squared_sum) / (n * (n**2 - 1))) * 100

                return rci

            return prices.rolling(window=period, min_periods=period).apply(
                rci_for_window, raw=False
            )

        except Exception as e:
            self.logger.error(f"RCI計算エラー: {e}")
            return pd.Series([0] * len(prices), index=prices.index)

    def _calculate_market_uncertainty(self, df: pd.DataFrame) -> float:
        """
        市場データ基づく不確実性計算（設定ベース統一ロジック）

        Args:
            df: 市場データ

        Returns:
            float: 市場不確実性係数（設定値の範囲）
        """
        try:
            # 循環インポート回避のため遅延インポート
            from ...core.config.threshold_manager import get_threshold

            # 設定値取得
            volatility_max = get_threshold(
                "dynamic_confidence.market_uncertainty.volatility_factor_max", 0.05
            )
            volume_max = get_threshold(
                "dynamic_confidence.market_uncertainty.volume_factor_max", 0.03
            )
            volume_multiplier = get_threshold(
                "dynamic_confidence.market_uncertainty.volume_multiplier", 0.1
            )
            price_max = get_threshold(
                "dynamic_confidence.market_uncertainty.price_factor_max", 0.02
            )
            uncertainty_max = get_threshold(
                "dynamic_confidence.market_uncertainty.uncertainty_max", 0.10
            )

            # ATRベースのボラティリティ要因
            current_price = float(df["close"].iloc[-1])
            atr_value = float(df["atr_14"].iloc[-1])
            volatility_factor = min(volatility_max, atr_value / current_price)

            # ボリューム異常度（平均からの乖離）
            current_volume = float(df["volume"].iloc[-1])
            avg_volume = float(df["volume"].rolling(20).mean().iloc[-1])
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            volume_factor = min(volume_max, abs(volume_ratio - 1.0) * volume_multiplier)

            # 価格変動率（短期動向）
            price_change = abs(float(df["close"].pct_change().iloc[-1]))
            price_factor = min(price_max, price_change)

            # 統合不確実性（設定値の範囲で市場状況を反映）
            market_uncertainty = volatility_factor + volume_factor + price_factor

            # 設定値で調整範囲を制限
            return min(uncertainty_max, market_uncertainty)

        except Exception as e:
            self.logger.warning(f"市場不確実性計算エラー: {e}")
            return 0.02  # デフォルト値（2%の軽微な調整）

    def _make_simple_decision(
        self, ema_signal: int, macd_signal: int, rci_signal: int, df: pd.DataFrame
    ) -> Dict[str, Any]:
        """シンプル多数決判定 - 設定ベース動的信頼度計算."""
        try:
            # 循環インポート回避のため遅延インポート
            from ...core.config.threshold_manager import get_threshold

            # 3指標の投票結果
            signals = [ema_signal, macd_signal, rci_signal]
            buy_votes = signals.count(1)
            sell_votes = signals.count(-1)
            hold_votes = signals.count(0)

            # 設定値取得（勝率向上最適化版）
            buy_strong_base = get_threshold(
                "dynamic_confidence.strategies.mochipoy_alert.buy_strong_base", 0.70
            )
            buy_strong_max = get_threshold(
                "dynamic_confidence.strategies.mochipoy_alert.buy_strong_max", 0.95
            )
            buy_weak_base = get_threshold(
                "dynamic_confidence.strategies.mochipoy_alert.buy_weak_base", 0.45
            )
            buy_weak_max = get_threshold(
                "dynamic_confidence.strategies.mochipoy_alert.buy_weak_max", 0.60
            )
            sell_strong_base = get_threshold(
                "dynamic_confidence.strategies.mochipoy_alert.sell_strong_base", 0.70
            )
            sell_strong_max = get_threshold(
                "dynamic_confidence.strategies.mochipoy_alert.sell_strong_max", 0.95
            )
            sell_weak_base = get_threshold(
                "dynamic_confidence.strategies.mochipoy_alert.sell_weak_base", 0.45
            )
            sell_weak_max = get_threshold(
                "dynamic_confidence.strategies.mochipoy_alert.sell_weak_max", 0.60
            )
            hold_base = get_threshold(
                "dynamic_confidence.strategies.mochipoy_alert.hold_base", 0.20
            )
            hold_min = get_threshold("dynamic_confidence.strategies.mochipoy_alert.hold_min", 0.1)
            hold_max = get_threshold("dynamic_confidence.strategies.mochipoy_alert.hold_max", 0.35)
            uncertainty_boost = get_threshold(
                "dynamic_confidence.market_uncertainty.uncertainty_boost", 1.5
            )

            # 市場データ基づく動的信頼度調整システム
            market_uncertainty = self._calculate_market_uncertainty(df)

            # 最適化された投票判定（勝率向上版）
            if buy_votes >= 2:
                # 2票以上の強い賛成 - 高信頼度（設定ベース動的変動）
                action = EntryAction.BUY
                base_confidence = buy_strong_base + (buy_votes - 2) * 0.15  # 3票時ボーナス
                confidence = min(
                    buy_strong_max, base_confidence * (1 + market_uncertainty / uncertainty_boost)
                )
            elif sell_votes >= 2:
                # 2票以上の強い反対 - 高信頼度（設定ベース動的変動）
                action = EntryAction.SELL
                base_confidence = sell_strong_base + (sell_votes - 2) * 0.15
                confidence = min(
                    sell_strong_max, base_confidence * (1 + market_uncertainty / uncertainty_boost)
                )
            elif buy_votes == 1 and sell_votes == 0:
                # 1票のBUY（他はHOLD） - 積極的取引（設定ベース動的変動）
                action = EntryAction.BUY
                base_confidence = buy_weak_base
                confidence = min(
                    buy_weak_max, base_confidence * (1 + market_uncertainty / uncertainty_boost)
                )
            elif sell_votes == 1 and buy_votes == 0:
                # 1票のSELL（他はHOLD） - 積極的取引（設定ベース動的変動）
                action = EntryAction.SELL
                base_confidence = sell_weak_base
                confidence = min(
                    sell_weak_max, base_confidence * (1 + market_uncertainty / uncertainty_boost)
                )
            else:
                # 意見が割れるか全てHOLD（設定ベース動的変動）
                action = EntryAction.HOLD
                base_confidence = hold_base
                confidence = max(
                    hold_min,
                    min(hold_max, base_confidence * (1 + market_uncertainty / uncertainty_boost)),
                )

            # 最低信頼度チェック
            if confidence < self.config["min_confidence"]:
                action = EntryAction.HOLD
                confidence = self.config["hold_confidence"]  # thresholds.yaml設定使用

            return {
                "action": action,
                "confidence": confidence,
                "strength": confidence,
                "votes": {
                    "buy": buy_votes,
                    "sell": sell_votes,
                    "hold": hold_votes,
                },
                "analysis": f"多数決: {action} (買い:{buy_votes}, 売り:{sell_votes}, 様子見:{hold_votes})",
            }

        except Exception as e:
            self.logger.error(f"多数決判定エラー: {e}")
            return {
                "action": EntryAction.HOLD,
                "confidence": 0.0,
                "strength": 0.0,
                "analysis": "エラー",
            }

    def _create_signal(
        self,
        decision: Dict[str, Any],
        current_price: float,
        df: pd.DataFrame,
        multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> StrategySignal:
        """シグナル作成 - 共通モジュール利用（Phase 31: マルチタイムフレーム対応）."""
        # 戦略固有メタデータを追加
        if "metadata" not in decision:
            decision["metadata"] = {}
        decision["metadata"]["votes"] = decision.get("votes", {})

        # Phase 31: multi_timeframe_dataを渡して15m足ATR取得
        return SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.name,
            decision=decision,
            current_price=current_price,
            df=df,
            config=self.config,
            strategy_type=StrategyType.MOCHIPOY_ALERT,
            multi_timeframe_data=multi_timeframe_data,
        )

    def get_required_features(self) -> List[str]:
        """必要特徴量リスト取得."""
        return [
            # 基本データ
            "close",
            # EMA指標
            "ema_20",
            "ema_50",
            # MACD指標（シグナル線は使用せず）
            "macd",
            # ATR（ストップロス計算用）
            "atr_14",
        ]

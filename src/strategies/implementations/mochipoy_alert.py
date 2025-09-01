"""
もちぽよアラート戦略実装 - シンプルEMA + MACD + RCI

トレンドフォロー戦略の王道指標を組み合わせた
シンプルで効率的な取引戦略。

戦略ロジック:
1. EMAトレンド判定: 20EMA > 50EMA でアップトレンド
2. MACDモメンタム: MACD > 0 でポジティブモメンタム
3. RCI逆張り補完: RCI過買い・過売り水準での確認
4. 多数決判定: 3指標の合意によるエントリー決定

Phase 4簡素化実装日: 2025年8月18日.
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
        # デフォルト設定（シンプル化）
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
        }

        merged_config = {**default_config, **(config or {})}
        super().__init__(name="MochipoyAlert", config=merged_config)

    def analyze(self, df: pd.DataFrame) -> StrategySignal:
        """市場分析とシグナル生成."""
        try:
            self.logger.debug("[MochipoyAlert] 分析開始")

            current_price = float(df["close"].iloc[-1])

            # 3指標のシンプル分析
            ema_signal = self._analyze_ema_trend(df)
            macd_signal = self._analyze_macd_momentum(df)
            rci_signal = self._analyze_rci_reversal(df)

            # 多数決によるシンプル統合判定
            signal_decision = self._make_simple_decision(ema_signal, macd_signal, rci_signal)

            # シグナル生成
            signal = self._create_signal(signal_decision, current_price, df)

            self.logger.debug(
                f"[MochipoyAlert] シグナル: {signal.action} (信頼度: {signal.confidence:.3f})"
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

    def _make_simple_decision(
        self, ema_signal: int, macd_signal: int, rci_signal: int
    ) -> Dict[str, Any]:
        """シンプル多数決判定."""
        try:
            # 3指標の投票結果
            signals = [ema_signal, macd_signal, rci_signal]
            buy_votes = signals.count(1)
            sell_votes = signals.count(-1)
            hold_votes = signals.count(0)

            # 多数決によるアクション決定
            if buy_votes >= 2:
                action = EntryAction.BUY
                confidence = 0.6 + (buy_votes - 2) * 0.2  # 2票:0.6, 3票:0.8
            elif sell_votes >= 2:
                action = EntryAction.SELL
                confidence = 0.6 + (sell_votes - 2) * 0.2
            else:
                action = EntryAction.HOLD
                confidence = 0.5

            # 最低信頼度チェック
            if confidence < self.config["min_confidence"]:
                action = EntryAction.HOLD
                confidence = 0.5

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
        self, decision: Dict[str, Any], current_price: float, df: pd.DataFrame
    ) -> StrategySignal:
        """シグナル作成 - 共通モジュール利用."""
        # 戦略固有メタデータを追加
        if "metadata" not in decision:
            decision["metadata"] = {}
        decision["metadata"]["votes"] = decision.get("votes", {})

        return SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.name,
            decision=decision,
            current_price=current_price,
            df=df,
            config=self.config,
            strategy_type=StrategyType.MOCHIPOY_ALERT,
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

"""
フィボナッチリトレースメント戦略実装 - シンプル基本レベル版

基本的なフィボナッチレベルでの反転を狙う
シンプルで効率的な戦略。

戦略ロジック:
1. 直近高値・安値: 簡易なスイング検出
2. 基本フィボレベル: 23.6%, 38.2%, 50%, 61.8%
3. レベル接近確認: 価格がレベル近傍にあるか判定
4. 反転確認: RSI + 基本ローソク足での確認

Phase 4簡素化実装日: 2025年8月18日.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from ...core.exceptions import StrategyError
from ...core.logger import get_logger
from ..base.strategy_base import StrategyBase, StrategySignal
from ..utils import EntryAction, SignalBuilder, StrategyType


class FibonacciRetracementStrategy(StrategyBase):
    """
    フィボナッチリトレースメント戦略

    基本フィボレベルでの反転を狙う
    シンプルな戦略。.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """戦略初期化."""
        # 循環インポート回避のため遅延インポート
        from ...core.config.threshold_manager import get_threshold

        # デフォルト設定（シンプル化・thresholds.yaml統合）
        default_config = {
            # スイング検出設定
            "lookback_periods": 20,  # 高値・安値検索期間
            # フィボナッチレベル（基本4レベル）
            "fib_levels": [0.236, 0.382, 0.500, 0.618],
            "level_tolerance": 0.01,  # レベル許容範囲（1%）
            # 反転確認設定
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "min_confidence": 0.4,
            # リスク管理
            "stop_loss_atr_multiplier": 2.0,
            "take_profit_ratio": 2.5,
            "position_size_base": 0.02,  # 2%
            # Phase 19+攻撃的設定対応（thresholds.yaml統合）
            "no_signal_confidence": get_threshold(
                "strategies.fibonacci_retracement.no_signal_confidence", 0.3
            ),
        }

        merged_config = {**default_config, **(config or {})}
        super().__init__(name="FibonacciRetracement", config=merged_config)

    def analyze(self, df: pd.DataFrame) -> StrategySignal:
        """フィボナッチ分析とシグナル生成."""
        try:
            self.logger.info(
                f"[FibonacciRetracement] 分析開始 - データシェイプ: {df.shape}, 利用可能列: {list(df.columns)[:10]}..."
            )
            self.logger.debug("[FibonacciRetracement] 分析開始")

            current_price = float(df["close"].iloc[-1])

            # シンプル分析
            swing_analysis = self._find_recent_swing(df)
            self.logger.info(
                f"[FibonacciRetracement] スイング分析結果: {swing_analysis.get('analysis', 'N/A')}"
            )

            fib_analysis = self._calculate_fib_levels(df, swing_analysis)
            self.logger.info(
                f"[FibonacciRetracement] フィボ分析結果: {fib_analysis.get('analysis', 'N/A')}"
            )

            reversal_analysis = self._check_reversal_signals(df, fib_analysis)
            self.logger.info(
                f"[FibonacciRetracement] 反転分析結果: {reversal_analysis.get('analysis', 'N/A')}"
            )

            # 統合判定
            signal_decision = self._make_simple_decision(fib_analysis, reversal_analysis)
            self.logger.info(
                f"[FibonacciRetracement] 最終判定: {signal_decision.get('action')} (confidence: {signal_decision.get('confidence', 0):.3f})"
            )

            # シグナル生成
            signal = self._create_signal(signal_decision, current_price, df)

            self.logger.info(
                f"[FibonacciRetracement] シグナル生成完了: {signal.action} (信頼度: {signal.confidence:.3f}, 強度: {signal.strength:.3f})"
            )
            return signal

        except Exception as e:
            self.logger.error(f"[FibonacciRetracement] 分析エラー: {e}")
            raise StrategyError(f"フィボナッチ分析失敗: {e}", strategy_name=self.name)

    def _find_recent_swing(self, df: pd.DataFrame) -> Dict[str, Any]:
        """直近スイング検出 - 成績重視版."""
        try:
            lookback = self.config["lookback_periods"]
            recent_data = df.iloc[-lookback:] if len(df) > lookback else df

            if len(recent_data) < 10:
                return {
                    "swing_high": 0,
                    "swing_low": 0,
                    "price_range": 0,
                    "valid": False,
                    "trend": 0,
                    "analysis": "データ不足",
                }

            # 意味のあるスイング検出
            swing_high_idx = recent_data["high"].idxmax()
            swing_low_idx = recent_data["low"].idxmin()

            swing_high = float(recent_data["high"].max())
            swing_low = float(recent_data["low"].min())
            price_range = swing_high - swing_low

            # スイング強度評価
            current_price = float(df["close"].iloc[-1])
            strength = price_range / current_price if current_price > 0 else 0

            # トレンド判定（高値・安値の時系列位置）
            high_position = recent_data.index.get_loc(swing_high_idx)
            low_position = recent_data.index.get_loc(swing_low_idx)

            if high_position > low_position:
                trend = -1  # 高値後→安値（下降気味）
            elif low_position > high_position:
                trend = 1  # 安値後→高値（上昇気味）
            else:
                trend = 0  # 判定困難

            # 現在価格のスイング内位置
            swing_position = (current_price - swing_low) / (price_range + 1e-8)

            return {
                "swing_high": swing_high,
                "swing_low": swing_low,
                "price_range": price_range,
                "strength": strength,
                "trend": trend,
                "swing_position": swing_position,
                "valid": price_range > current_price * 0.01,  # 最低1%の価格幅要求
                "analysis": f"スイング: 高値{swing_high:.0f} 安値{swing_low:.0f} (強度{strength:.1%} トレンド{'上昇' if trend == 1 else '下降' if trend == -1 else '横ばい'})",
            }

        except Exception as e:
            self.logger.error(f"スイング検出エラー: {e}")
            return {
                "swing_high": 0,
                "swing_low": 0,
                "price_range": 0,
                "valid": False,
                "trend": 0,
                "analysis": "エラー",
            }

    def _calculate_fib_levels(self, df: pd.DataFrame, swing_analysis: Dict) -> Dict[str, Any]:
        """フィボナッチレベル計算 - 成績重視版."""
        try:
            if not swing_analysis["valid"]:
                return {
                    "levels": [],
                    "nearest_level": None,
                    "approaching_levels": [],
                    "is_near_level": False,
                    "level_distance": float("inf"),
                    "analysis": "スイング無効",
                }

            fib_ratios = self.config["fib_levels"]
            level_tolerance = self.config["level_tolerance"]
            current_price = float(df["close"].iloc[-1])

            swing_high = swing_analysis["swing_high"]
            swing_low = swing_analysis["swing_low"]
            price_range = swing_analysis["price_range"]
            trend = swing_analysis["trend"]

            # トレンド方向別フィボ計算
            fib_levels = []
            for ratio in fib_ratios:
                if trend >= 0:  # 上昇・横ばい → リトレースメント
                    level_price = swing_high - (price_range * ratio)
                    level_type = "retracement"
                else:  # 下降 → エクステンション的使用
                    level_price = swing_low + (price_range * ratio)
                    level_type = "extension"

                distance = abs(current_price - level_price) / current_price

                # 重要レベル判定（38.2%, 50%, 61.8%）
                is_strong = ratio in [0.382, 0.500, 0.618]

                fib_levels.append(
                    {
                        "ratio": ratio,
                        "price": level_price,
                        "distance": distance,
                        "is_strong": is_strong,
                        "level_type": level_type,
                        "is_near": distance <= level_tolerance,
                    }
                )

            # 距離順でソート
            fib_levels.sort(key=lambda x: x["distance"])

            # 最近接レベル
            nearest_level = fib_levels[0] if fib_levels else None

            # 接近中レベル（複数監視）
            approaching_levels = [level for level in fib_levels if level["is_near"]]

            # 接近判定
            is_near_level = len(approaching_levels) > 0

            # 分析テキスト
            if nearest_level:
                near_info = f"{nearest_level['ratio']:.1%}({nearest_level['level_type']})"
                if nearest_level["is_strong"]:
                    near_info += "★"
                if approaching_levels:
                    near_info += (
                        f" +{len(approaching_levels) - 1}接近"
                        if len(approaching_levels) > 1
                        else ""
                    )
                distance_str = (
                    f'距離{nearest_level["distance"]:.1%}' if not is_near_level else "接近中"
                )
                analysis = f"フィボ: {near_info} {distance_str}"
            else:
                analysis = "フィボ: レベル無し"

            return {
                "levels": fib_levels,
                "nearest_level": nearest_level,
                "approaching_levels": approaching_levels,
                "is_near_level": is_near_level,
                "level_distance": (nearest_level["distance"] if nearest_level else float("inf")),
                "trend_direction": trend,
                "analysis": analysis,
            }

        except Exception as e:
            self.logger.error(f"フィボレベル計算エラー: {e}")
            return {
                "levels": [],
                "nearest_level": None,
                "approaching_levels": [],
                "is_near_level": False,
                "level_distance": float("inf"),
                "analysis": "エラー",
            }

    def _check_reversal_signals(self, df: pd.DataFrame, fib_analysis: Dict) -> Dict[str, Any]:
        """反転シグナル確認 - 成績重視版."""
        try:
            if not fib_analysis["is_near_level"]:
                return {
                    "reversal_signal": 0,
                    "rsi_signal": 0,
                    "candle_signal": 0,
                    "volume_signal": 0,
                    "confidence": 0.0,
                    "analysis": "レベル接近なし",
                }

            rsi_oversold = self.config["rsi_oversold"]
            rsi_overbought = self.config["rsi_overbought"]
            approaching_levels = fib_analysis["approaching_levels"]

            # RSI反転確認（強化版）
            rsi_signal = 0
            rsi_strength = 0.0
            if "rsi_14" in df.columns:
                current_rsi = float(df["rsi_14"].iloc[-1])
                if current_rsi <= rsi_oversold:
                    rsi_signal = 1  # 過売りから反転
                    rsi_strength = (rsi_oversold - current_rsi) / rsi_oversold
                elif current_rsi >= rsi_overbought:
                    rsi_signal = -1  # 過買いから反転
                    rsi_strength = (current_rsi - rsi_overbought) / (100 - rsi_overbought)

            # ローソク足パターン確認（強化版）
            candle_signal = self._check_enhanced_candle_pattern(df)

            # 出来高確認
            volume_signal = self._check_volume_confirmation(df)

            # レベル強度ボーナス
            level_bonus = 0.0
            strong_levels_nearby = [
                level for level in approaching_levels if level.get("is_strong", False)
            ]
            if strong_levels_nearby:
                level_bonus = 0.2 * len(strong_levels_nearby)  # 強力レベル1つにつき20%ボーナス

            # 統合シグナル（重み付け評価）
            signals = [rsi_signal, candle_signal, volume_signal]
            signal_strengths = [
                rsi_strength if rsi_signal != 0 else 0,
                0.5 if candle_signal != 0 else 0,
                0.3 if volume_signal != 0 else 0,
            ]

            buy_votes = signals.count(1)
            sell_votes = signals.count(-1)

            if buy_votes >= 1 and sell_votes == 0:
                reversal_signal = 1
                confidence = 0.3 + sum(
                    s for s in signal_strengths if s > 0
                )  # level_bonus除去（二重加算防止）
            elif sell_votes >= 1 and buy_votes == 0:
                reversal_signal = -1
                confidence = 0.3 + sum(
                    s for s in signal_strengths if s > 0
                )  # level_bonus除去（二重加算防止）
            else:
                reversal_signal = 0
                confidence = self.config["no_signal_confidence"]  # thresholds.yaml設定使用

            confidence = min(confidence, 1.0)  # 上限1.0

            return {
                "reversal_signal": reversal_signal,
                "rsi_signal": rsi_signal,
                "candle_signal": candle_signal,
                "volume_signal": volume_signal,
                "level_bonus": level_bonus,
                "confidence": confidence,
                "strong_levels_count": len(strong_levels_nearby),
                "analysis": f"反転: {['売り', 'なし', '買い'][reversal_signal + 1]} (RSI:{rsi_signal}, ローソク:{candle_signal}, 出来高:{volume_signal}) レベル強度+{level_bonus:.1f}",
            }

        except Exception as e:
            self.logger.error(f"反転シグナル確認エラー: {e}")
            return {
                "reversal_signal": 0,
                "confidence": 0.0,
                "analysis": "エラー",
            }

    def _check_enhanced_candle_pattern(self, df: pd.DataFrame) -> int:
        """ローソク足パターン確認 - 強化版."""
        try:
            if len(df) < 3:
                return 0

            current = df[["open", "high", "low", "close"]].iloc[-1].astype(float)
            prev = df[["open", "high", "low", "close"]].iloc[-2].astype(float)
            prev2 = df[["open", "high", "low", "close"]].iloc[-3].astype(float)

            # 基本ハンマー・シューティングスター
            basic_signal = self._check_basic_candle_pattern(df)
            if basic_signal != 0:
                return basic_signal

            # ピンバー（長いヒゲ）確認
            body_size = abs(current["close"] - current["open"])
            total_range = current["high"] - current["low"]

            if total_range > 0:
                upper_wick = current["high"] - max(current["open"], current["close"])
                lower_wick = min(current["open"], current["close"]) - current["low"]

                # 強いピンバー（ヒゲが実体の2倍以上）
                if lower_wick > body_size * 2 and lower_wick > upper_wick:
                    return 1  # 買いシグナル
                elif upper_wick > body_size * 2 and upper_wick > lower_wick:
                    return -1  # 売りシグナル

            # エンガルフィングパターン
            curr_body = abs(current["close"] - current["open"])
            prev_body = abs(prev["close"] - prev["open"])

            # ブリッシュエンガルフィング
            if (
                prev["close"] < prev["open"]  # 前日陰線
                and current["close"] > current["open"]  # 当日陽線
                and current["open"] < prev["close"]
                and current["close"] > prev["open"]
                and curr_body > prev_body * 1.1
            ):  # 実体が大きい
                return 1

            # ベアリッシュエンガルフィング
            elif (
                prev["close"] > prev["open"]  # 前日陽線
                and current["close"] < current["open"]  # 当日陰線
                and current["open"] > prev["close"]
                and current["close"] < prev["open"]
                and curr_body > prev_body * 1.1
            ):  # 実体が大きい
                return -1

            return 0

        except Exception as e:
            self.logger.error(f"ローソク足パターン確認エラー: {e}")
            return 0

    def _check_basic_candle_pattern(self, df: pd.DataFrame) -> int:
        """基本ローソク足パターン確認."""
        try:
            if len(df) < 1:
                return 0

            current = df[["open", "high", "low", "close"]].iloc[-1].astype(float)

            # ハンマー・シューティングスター検出
            body_size = abs(current["close"] - current["open"])
            total_range = current["high"] - current["low"]

            if total_range > 0:
                upper_wick = current["high"] - max(current["open"], current["close"])
                lower_wick = min(current["open"], current["close"]) - current["low"]

                # ハンマー（長い下ヒゲ）
                if lower_wick >= total_range * 0.6 and body_size < total_range * 0.3:
                    return 1  # 買いシグナル

                # シューティングスター（長い上ヒゲ）
                elif upper_wick >= total_range * 0.6 and body_size < total_range * 0.3:
                    return -1  # 売りシグナル

            return 0

        except Exception as e:
            self.logger.error(f"ローソク足パターン確認エラー: {e}")
            return 0

    def _check_volume_confirmation(self, df: pd.DataFrame) -> int:
        """出来高確認."""
        try:
            if len(df) < 10:
                return 0

            current_volume = float(df["volume"].iloc[-1])
            avg_volume = df["volume"].iloc[-10:].mean()

            # 出来高スパイク（平均の1.5倍以上）
            if current_volume >= avg_volume * 1.5:
                return 1  # 出来高確認

            return 0

        except Exception as e:
            self.logger.error(f"出来高確認エラー: {e}")
            return 0

    def _make_simple_decision(self, fib_analysis: Dict, reversal_analysis: Dict) -> Dict[str, Any]:
        """統合判定 - 成績重視版."""
        try:
            min_confidence = self.config["min_confidence"]

            # 基本条件チェック
            if not fib_analysis["is_near_level"]:
                # 循環インポート回避のため遅延インポート
                from ...core.config.threshold_manager import get_threshold

                no_level_confidence = get_threshold(
                    "strategies.fibonacci_retracement.no_level_confidence", 0.3
                )
                return {
                    "action": EntryAction.HOLD,
                    "confidence": no_level_confidence,
                    "strength": 0.0,
                    "analysis": f"フィボレベル接近なし [confidence={no_level_confidence}]",
                }

            reversal_signal = reversal_analysis["reversal_signal"]
            reversal_confidence = reversal_analysis["confidence"]
            nearest_level = fib_analysis["nearest_level"]

            # 信頼度計算（多要素統合）
            base_confidence = reversal_confidence

            # フィボレベル強度ボーナス
            level_bonus = 0.0
            if nearest_level:
                if nearest_level.get("is_strong", False):
                    level_bonus += 0.15  # 重要レベル（38.2%, 50%, 61.8%）

                # 距離ボーナス（近いほど高い）
                distance = nearest_level.get("distance", 1.0)
                proximity_bonus = max(0, 0.1 * (1 - distance / 0.01))  # 1%以内で最大10%
                level_bonus += proximity_bonus

            # 複数レベル接近ボーナス
            approaching_count = len(fib_analysis.get("approaching_levels", []))
            if approaching_count > 1:
                level_bonus += 0.05 * (approaching_count - 1)  # 追加レベルごとに5%

            # トレンド整合性ボーナス
            trend_direction = fib_analysis.get("trend_direction", 0)
            trend_bonus = 0.0
            if trend_direction != 0 and reversal_signal != 0:
                # トレンドと逆方向の反転（リトレースメント）
                if trend_direction * reversal_signal < 0:
                    trend_bonus = 0.1  # 10%ボーナス

            # 最終信頼度計算
            final_confidence = base_confidence + level_bonus + trend_bonus
            final_confidence = min(final_confidence, 1.0)  # 上限1.0

            # アクション決定
            if reversal_signal != 0 and final_confidence >= min_confidence:
                action = EntryAction.BUY if reversal_signal > 0 else EntryAction.SELL
                confidence = final_confidence
                strength = base_confidence + (level_bonus + trend_bonus) * 0.5
            else:
                action = EntryAction.HOLD
                confidence = self.config["no_signal_confidence"]  # thresholds.yaml設定使用
                strength = 0.0

            # 分析テキスト作成
            bonus_text = []
            if level_bonus > 0:
                bonus_text.append(f"レベル+{level_bonus:.2f}")
            if trend_bonus > 0:
                bonus_text.append(f"トレンド+{trend_bonus:.2f}")

            bonus_str = f" ({', '.join(bonus_text)})" if bonus_text else ""
            analysis = f"フィボナッチ: {action} (基本{base_confidence:.2f}{bonus_str} = {final_confidence:.2f})"

            return {
                "action": action,
                "confidence": confidence,
                "strength": strength,
                "base_confidence": base_confidence,
                "level_bonus": level_bonus,
                "trend_bonus": trend_bonus,
                "final_confidence": final_confidence,
                "analysis": analysis,
            }

        except Exception as e:
            self.logger.error(f"統合判定エラー: {e}")
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
        return SignalBuilder.create_signal_with_risk_management(
            strategy_name=self.name,
            decision=decision,
            current_price=current_price,
            df=df,
            config=self.config,
            strategy_type=StrategyType.FIBONACCI_RETRACEMENT,
        )

    def get_required_features(self) -> List[str]:
        """必要特徴量リスト取得."""
        return [
            # 基本OHLCV（スイング・フィボナッチ計算用）
            "open",
            "high",
            "low",
            "close",
            "volume",
            # 反転確認用指標
            "rsi_14",
            # リスク管理
            "atr_14",
        ]

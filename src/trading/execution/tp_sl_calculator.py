"""
TP/SL再計算サービス - TPSLCalculator
Phase 52.4-B完了 - executor.pyからTP/SL再計算ロジック分離

ライブトレードにおける実約定価格ベースのTP/SL再計算を担当。
3段階ATRフォールバック実装（evaluation → DataService → fallback_atr）
"""

from typing import Any, Optional, Tuple

from ...core.config import get_threshold
from ...core.exceptions import CryptoBotError
from ...core.logger import CryptoBotLogger
from ..core import ExecutionResult, TradeEvaluation


class TPSLCalculator:
    """TP/SL再計算サービス

    Phase 52.4-B: executor.pyから分離
    責任: 実約定価格ベースでTP/SL再計算・3段階ATRフォールバック実装
    """

    def __init__(
        self,
        logger: CryptoBotLogger,
        data_service: Optional[Any] = None,
    ):
        """
        TPSLCalculator初期化

        Args:
            logger: ロガーインスタンス
            data_service: データサービス（ATRフォールバック用・任意）
        """
        self.logger = logger
        self.data_service = data_service

    async def calculate(
        self,
        evaluation: TradeEvaluation,
        result: ExecutionResult,
        side: str,
        amount: float,
    ) -> Tuple[float, float]:
        """
        Phase 52.4-B: ライブトレードTP/SL再計算（3段階ATRフォールバック）

        Args:
            evaluation: 取引評価
            result: 注文実行結果
            side: 取引方向（buy/sell）
            amount: 取引数量

        Returns:
            Tuple[float, float]: (final_tp, final_sl)

        Raises:
            CryptoBotError: ATR取得失敗・TP/SL再計算失敗時
        """
        # Phase 52.4-B: 実約定価格ベースでTP/SL再計算（SL距離5x誤差修正）
        # Phase 52.4-B: TP/SL再計算強化（3段階ATRフォールバック + 再計算必須化）
        actual_filled_price = result.filled_price or result.price

        # 実約定価格でTP/SL価格を再計算
        recalculated_tp = None
        recalculated_sl = None

        if actual_filled_price > 0 and evaluation.take_profit and evaluation.stop_loss:
            from ...strategies.utils.strategy_utils import RiskManager

            # ATR値とATR履歴を取得（3段階フォールバック）
            market_conditions = getattr(evaluation, "market_conditions", {})
            market_data = market_conditions.get("market_data", {})

            current_atr = None
            atr_history = None
            atr_source = None  # デバッグ用：ATR取得元

            # Phase 52.4-B: 3段階ATRフォールバック
            # Level 1: evaluation.market_conditions から取得（既存）
            if "15m" in market_data:
                df_15m = market_data["15m"]
                if "atr_14" in df_15m.columns and len(df_15m) > 0:
                    current_atr = float(df_15m["atr_14"].iloc[-1])
                    atr_history = df_15m["atr_14"].dropna().tail(20).tolist()
                    atr_source = "evaluation.market_conditions[15m]"

            if not current_atr and "4h" in market_data:
                df_4h = market_data["4h"]
                if "atr_14" in df_4h.columns and len(df_4h) > 0:
                    current_atr = float(df_4h["atr_14"].iloc[-1])
                    atr_source = "evaluation.market_conditions[4h]"

            # Level 2: DataService経由で直接取得（Phase 52.4-B新規）
            if not current_atr and hasattr(self, "data_service") and self.data_service:
                try:
                    # 15m足ATRを優先取得
                    df_15m = self.data_service.fetch_ohlcv("BTC/JPY", "15m", limit=50)
                    if "atr_14" in df_15m.columns and len(df_15m) > 0:
                        current_atr = float(df_15m["atr_14"].iloc[-1])
                        atr_history = df_15m["atr_14"].dropna().tail(20).tolist()
                        atr_source = "DataService[15m]"
                        self.logger.info(
                            "✅ Phase 52.4-B: DataService経由ATR取得成功 - "
                            f"15m足ATR={current_atr:.0f}円"
                        )
                except Exception as e:
                    self.logger.warning(f"⚠️ Phase 52.4-B: DataService経由ATR取得失敗 - {e}")

            # Level 3: thresholds.yaml fallback_atr使用（Phase 52.4-B新規）
            if not current_atr:
                try:
                    fallback_atr = float(get_threshold("risk.fallback_atr", 500000))
                except (ValueError, TypeError):
                    # 型変換失敗時はデフォルト値使用
                    fallback_atr = 500000.0
                    self.logger.warning(
                        "⚠️ Phase 52.4-B: fallback_atr型変換失敗 - デフォルト値500,000円使用"
                    )
                current_atr = fallback_atr
                atr_source = "thresholds.yaml[fallback_atr]"
                self.logger.warning(
                    f"⚠️ Phase 52.4-B: フォールバックATR使用 - fallback_atr={fallback_atr:.0f}円"
                )

            # ATR取得完了（3段階いずれかで取得）
            if current_atr and current_atr > 0:
                # Phase 52.4-B: TP/SL設定完全渡し（ハードコード削除・設定ファイル一元管理）
                # Phase 52.4-B: レジーム情報取得追加
                config = {
                    # TP設定（Phase 52.4-B: TP 0.9%・RR比1.29:1）
                    "take_profit_ratio": get_threshold(
                        "position_management.take_profit.default_ratio"
                    ),
                    "min_profit_ratio": get_threshold(
                        "position_management.take_profit.min_profit_ratio"
                    ),
                    # SL設定（Phase 52.4-B: SL 0.7%）
                    "max_loss_ratio": get_threshold("position_management.stop_loss.max_loss_ratio"),
                    "min_distance_ratio": get_threshold(
                        "position_management.stop_loss.min_distance.ratio"
                    ),
                    "default_atr_multiplier": get_threshold(
                        "position_management.stop_loss.default_atr_multiplier"
                    ),
                }

                # Phase 52.4-B: レジーム情報取得
                regime = market_conditions.get("regime", None)
                regime_str = None
                if regime:
                    # RegimeType enumの場合は文字列に変換
                    regime_str = regime.value if hasattr(regime, "value") else str(regime)
                    self.logger.info(f"🎯 Phase 52.4-B: レジーム情報取得 - {regime_str}")

                # Phase 52.4-B: レジーム情報を含めてTP/SL計算
                recalculated_sl, recalculated_tp = RiskManager.calculate_stop_loss_take_profit(
                    side, actual_filled_price, current_atr, config, atr_history, regime=regime_str
                )

                # 再計算成功時、ログ出力
                if recalculated_sl and recalculated_tp:
                    original_sl = evaluation.stop_loss
                    original_tp = evaluation.take_profit
                    sl_diff = abs(recalculated_sl - original_sl)
                    tp_diff = abs(recalculated_tp - original_tp)

                    # 価格差異計算（entry_priceがある場合）
                    if evaluation.entry_price is not None:
                        entry_price_val = float(evaluation.entry_price)
                        actual_price_val = float(actual_filled_price)
                        price_diff = abs(actual_price_val - entry_price_val)
                        price_info = (
                            f"価格: シグナル時={entry_price_val:.0f}円"
                            f"→実約定={actual_price_val:.0f}円 (差{price_diff:.0f}円) | "
                        )
                    else:
                        actual_price_val = float(actual_filled_price)
                        price_info = f"実約定価格={actual_price_val:.0f}円 | "

                    self.logger.info(
                        "🔄 Phase 52.4-B: 実約定価格ベースTP/SL再計算完了 - "
                        f"ATR取得元={atr_source}, ATR={current_atr:.0f}円 | "
                        f"{price_info}"
                        f"SL: {original_sl:.0f}円→{recalculated_sl:.0f}円 (差{sl_diff:.0f}円) | "
                        f"TP: {original_tp:.0f}円→{recalculated_tp:.0f}円 (差{tp_diff:.0f}円)"
                    )
                else:
                    # Phase 52.4-B: 再計算失敗時のハンドリング
                    require_recalc = get_threshold("risk.require_tpsl_recalculation", True)
                    if require_recalc:
                        # 再計算必須モード：エントリー中止
                        self.logger.error(
                            "❌ Phase 52.4-B: TP/SL再計算失敗（require_tpsl_recalculation=True） - "
                            f"ATR={current_atr:.0f}円・エントリー中止"
                        )
                        raise CryptoBotError("TP/SL再計算失敗によりエントリー中止")
                    else:
                        # 再計算任意モード：元のTP/SL使用
                        self.logger.warning(
                            "⚠️ Phase 52.4-B: TP/SL再計算失敗（RiskManager戻り値None） - "
                            f"ATR={current_atr:.0f}円・元のTP/SL使用継続"
                        )
            else:
                # Phase 52.4-B: ATR取得失敗時のハンドリング
                require_recalc = get_threshold("risk.require_tpsl_recalculation", True)
                if require_recalc:
                    # 再計算必須モード：エントリー中止
                    self.logger.error(
                        "❌ Phase 52.4-B: ATR取得失敗（require_tpsl_recalculation=True） - "
                        f"current_atr={current_atr}・エントリー中止"
                    )
                    raise CryptoBotError("ATR取得失敗によりエントリー中止")
                else:
                    # 再計算任意モード：元のTP/SL使用
                    self.logger.warning(
                        f"⚠️ Phase 52.4-B: ATR取得失敗（current_atr={current_atr}） - "
                        "実約定価格ベースTP/SL再計算スキップ・元のTP/SL使用継続"
                    )

        # 再計算された値を使用（失敗時は元の値）
        final_tp = recalculated_tp if recalculated_tp else evaluation.take_profit
        final_sl = recalculated_sl if recalculated_sl else evaluation.stop_loss

        return final_tp, final_sl

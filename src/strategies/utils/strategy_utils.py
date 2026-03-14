"""
戦略共通ユーティリティ統合モジュール - Phase 61.10

戦略関連のユーティリティ機能を統合管理：
- 戦略定数：EntryAction、StrategyType統一
- リスク管理：戦略レベルリスク評価
- シグナル生成：統一的なシグナル構築
- Phase 61.7: 固定金額TP計算
- Phase 61.8: 固定金額TPのバックテスト対応
- Phase 61.10: バックテスト・ライブモード ポジションサイズ統一

統合により関連機能を一元化し、管理しやすい構造を提供。

Phase 61.10更新: Dynamic Position Sizingをバックテストでも使用（ライブ互換）
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import pandas as pd

from ...core.logger import get_logger
from ..base.strategy_base import StrategySignal

if TYPE_CHECKING:
    from ...trading.core.types import PositionFeeData

# === 戦略共通定数定義 ===


class EntryAction:
    """エントリーアクション定数."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    CLOSE = "close"


class StrategyType:
    """戦略タイプ定数 - Phase 51.5-A: 3戦略構成 + Phase 51.7: 3戦略追加."""

    ATR_BASED = "atr_based"
    DONCHIAN_CHANNEL = "donchian_channel"
    ADX_TREND = "adx_trend"
    BB_REVERSAL = "bb_reversal"  # Phase 51.7 Day 3: BB Reversal strategy
    STOCHASTIC_REVERSAL = "stochastic_reversal"  # Phase 51.7 Day 4: Stochastic Reversal strategy
    MACD_EMA_CROSSOVER = "macd_ema_crossover"  # Phase 51.7 Day 5: MACD+EMA Crossover strategy


# 基本リスク管理パラメータ（戦略で上書き可能）
# Phase 51.6: フォールバック値のみ・実際の値は設定ファイル（thresholds.yaml）優先
DEFAULT_RISK_PARAMS: Dict[str, Any] = {
    # ストップロス・テイクプロフィット（Phase 51.6: 設定ファイル優先）
    "stop_loss_atr_multiplier": 2.0,  # フォールバック値
    "take_profit_ratio": 1.29,  # Phase 51.6: RR比1.29:1（フォールバック値）
    # ポジションサイズ（Phase 55.12: 加重平均に合わせて調整）
    "position_size_base": 0.0003,  # 0.0003 BTC（約5,000円 = 証拠金10万円の約5%）
    # 計算設定
    "min_atr_threshold": 0.001,  # ATRの最小値（ゼロ除算回避）
    "max_position_size": 0.05,  # 最大ポジションサイズ（5%）
}


# === リスク管理計算クラス ===


class RiskManager:
    """
    リスク管理計算統合クラス

    全戦略で共通するリスク管理計算を一元化。
    戦略固有のパラメータは各戦略の設定で上書き可能。
    """

    @staticmethod
    def _extract_15m_atr(
        df: pd.DataFrame, multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> Optional[float]:
        """
        Phase 31: 15m足ATR優先取得・4h足ATRフォールバック

        Args:
            df: メインタイムフレームデータ（4h足）
            multi_timeframe_data: マルチタイムフレームデータ

        Returns:
            ATR値（15m優先、なければ4h、取得失敗ならNone）
        """
        logger = get_logger()

        # Phase 31: 15m足ATR優先取得
        if multi_timeframe_data and "15m" in multi_timeframe_data:
            try:
                df_15m = multi_timeframe_data["15m"]
                if "atr_14" in df_15m.columns and len(df_15m) > 0:
                    atr_15m = float(df_15m["atr_14"].iloc[-1])
                    if atr_15m > 0:
                        logger.info(f"✅ Phase 31: 15m足ATR使用 = {atr_15m:.0f}円")
                        return atr_15m
            except Exception as e:
                logger.warning(f"15m足ATR取得失敗: {e}")

        # フォールバック: 4h足ATR取得
        try:
            if "atr_14" in df.columns and len(df) > 0:
                atr_4h = float(df["atr_14"].iloc[-1])
                if atr_4h > 0:
                    logger.info(f"⚠️ Phase 31フォールバック: 4h足ATR使用 = {atr_4h:.0f}円")
                    return atr_4h
        except Exception as e:
            logger.error(f"4h足ATR取得失敗: {e}")

        return None

    @staticmethod
    def _calculate_adaptive_atr_multiplier(
        current_atr: float, atr_history: Optional[List[float]] = None
    ) -> float:
        """
        Phase 30: 適応型ATR倍率計算

        Args:
            current_atr: 現在のATR値
            atr_history: ATR履歴（ボラティリティ判定用、Noneの場合はデフォルト倍率）

        Returns:
            適応型ATR倍率
        """
        from ...core.config import get_threshold

        # 適応型ATR機能が無効な場合
        if not get_threshold("position_management.stop_loss.adaptive_atr.enabled", True):
            return get_threshold("position_management.stop_loss.default_atr_multiplier", 2.0)

        # ATR履歴がない場合はデフォルト
        if not atr_history or len(atr_history) < 10:
            return get_threshold(
                "position_management.stop_loss.adaptive_atr.normal_volatility.multiplier", 2.0
            )

        # ATR平均計算
        import numpy as np

        avg_atr = np.mean(atr_history)

        # ボラティリティ状態判定
        low_threshold = get_threshold(
            "position_management.stop_loss.adaptive_atr.low_volatility.threshold_ratio", 0.7
        )
        high_threshold = get_threshold(
            "position_management.stop_loss.adaptive_atr.high_volatility.threshold_ratio", 1.3
        )

        volatility_ratio = current_atr / avg_atr if avg_atr > 0 else 1.0

        # ボラティリティに応じた倍率選択
        if volatility_ratio < low_threshold:
            # 低ボラティリティ → 広めのSL
            return get_threshold(
                "position_management.stop_loss.adaptive_atr.low_volatility.multiplier", 2.5
            )
        elif volatility_ratio > high_threshold:
            # 高ボラティリティ → 狭めのSL（急変時対策）
            return get_threshold(
                "position_management.stop_loss.adaptive_atr.high_volatility.multiplier", 1.5
            )
        else:
            # 通常ボラティリティ → 標準SL
            return get_threshold(
                "position_management.stop_loss.adaptive_atr.normal_volatility.multiplier", 2.0
            )

    @staticmethod
    def calculate_fixed_amount_tp(
        action: str,
        entry_price: float,
        amount: float,
        fee_data: Optional["PositionFeeData"],
        config: Dict[str, Any],
    ) -> Optional[float]:
        """
        Phase 61.7: 固定金額TP価格計算

        手数料を考慮して、目標純利益を確保するTP価格を計算する。

        計算式:
            必要含み益 = 目標純利益 + エントリー手数料 + 利息 - 決済リベート
            TP価格 = エントリー価格 ± (必要含み益 / 数量)

        Args:
            action: "buy" or "sell"
            entry_price: エントリー価格（円）
            amount: ポジション数量（BTC）
            fee_data: API手数料データ（Noneの場合フォールバック使用）
            config: 固定金額設定（thresholds.yamlから取得）

        Returns:
            TP価格（円）、計算失敗時はNone
        """
        logger = get_logger()

        try:
            target_net_profit = config.get("target_net_profit", 1000)

            # エントリー手数料
            include_entry_fee = config.get("include_entry_fee", True)
            if include_entry_fee:
                # Phase 63.2: fee_data.unrealized_fee_amountは集約ポジション全体の
                # 累積手数料を返すため使用しない。fallbackレートで個別計算。
                fallback_rate = config.get("fallback_entry_fee_rate", 0.0)
                entry_fee = entry_price * amount * fallback_rate
            else:
                entry_fee = 0

            # 利息
            include_interest = config.get("include_interest", True)
            if include_interest:
                # Phase 63.2: fee_data.unrealized_interest_amountも集約ポジション
                # 全体の累積値。新規エントリー時点では利息≈0円。
                interest = 0
            else:
                interest = 0

            # Phase 62.19: 決済手数料推定（Maker 0%）
            # 2026年2月2日手数料改定: Maker 0%（リベート終了）、Taker 0.1%
            if config.get("include_exit_fee_rebate", True):
                exit_fee_rate = config.get("fallback_exit_fee_rate", 0.0)
                # exit_fee_rateが正（手数料）の場合は加算
                exit_fee = entry_price * amount * exit_fee_rate
            else:
                exit_fee = 0

            # 必要含み益計算（Phase 62.11: 決済手数料を加算に修正）
            required_gross_profit = target_net_profit + entry_fee + interest + exit_fee

            if amount <= 0:
                logger.warning("⚠️ Phase 61.7: 数量が0以下のためTP計算不可")
                return None

            price_distance = required_gross_profit / amount

            # Phase 61.8: 妥当性チェック - price_distanceがエントリー価格の10%を超える場合は異常値
            # （ポジションサイズが小さすぎる場合に発生）
            max_distance_ratio = 0.10  # 10%
            if price_distance > entry_price * max_distance_ratio:
                logger.warning(
                    f"⚠️ Phase 61.8: 固定金額TP計算異常 - "
                    f"price_distance={price_distance:.0f}円 > エントリー価格の{max_distance_ratio * 100:.0f}% "
                    f"(数量={amount:.6f}が小さすぎる可能性) - %ベースにフォールバック"
                )
                return None

            if action.lower() == "buy":
                tp_price = entry_price + price_distance
            else:
                tp_price = entry_price - price_distance

            # Phase 61.8: TP価格の妥当性チェック
            if tp_price <= 0:
                logger.warning(
                    f"⚠️ Phase 61.8: 固定金額TP計算結果が負 - "
                    f"TP={tp_price:.0f}円 - %ベースにフォールバック"
                )
                return None

            # デバッグログ（Phase 62.19→68.8: 手数料改定対応 + 信頼度別）
            logger.info(
                f"🎯 Phase 62.19: 固定金額TP計算 - "
                f"目標純利益={target_net_profit:.0f}円, "
                f"エントリー手数料={entry_fee:.0f}円, "
                f"利息={interest:.0f}円, "
                f"決済手数料={exit_fee:.0f}円, "
                f"必要含み益={required_gross_profit:.0f}円, "
                f"TP価格={tp_price:.0f}円 ({action})"
            )

            return tp_price

        except Exception as e:
            logger.error(f"❌ Phase 61.7: 固定金額TP計算エラー: {e}")
            return None

    @staticmethod
    def calculate_stop_loss_take_profit(
        action: str,
        current_price: float,
        current_atr: float,
        config: Dict[str, Any],
        atr_history: Optional[List[float]] = None,
        regime: Optional[str] = None,
        current_time: Optional[datetime] = None,
        fee_data: Optional["PositionFeeData"] = None,
        position_amount: Optional[float] = None,
        confidence: Optional[float] = None,
    ) -> Tuple[Optional[float], Optional[float]]:
        """
        Phase 49.16: TP/SL計算完全見直し - thresholds.yaml完全準拠
        Phase 52.0: レジーム別動的TP/SL調整実装
        Phase 58.6: 土日TP/SL縮小対応
        Phase 61.7: 固定金額TPモード対応

        Args:
            action: エントリーアクション（buy/sell）
            current_price: 現在価格
            current_atr: 現在のATR値
            config: 完全なTP/SL設定（executor.pyから渡される）
            atr_history: ATR履歴（適応型ATR用）
            regime: 市場レジーム（tight_range/normal_range/trending/high_volatility）
            current_time: 現在時刻（バックテスト対応、土日判定用）
            fee_data: Phase 61.7: ポジション手数料データ（固定金額TP用）
            position_amount: Phase 61.7: ポジション数量（固定金額TP用）

        Returns:
            (stop_loss, take_profit)のタプル
        """
        logger = get_logger()
        from ...core.config import get_threshold

        try:
            if action not in [EntryAction.BUY, EntryAction.SELL]:
                return None, None

            # ========================================
            # Phase 52.0: レジーム別TP/SL設定の適用
            # ========================================
            # Phase 52.0: レジーム別設定の有効化確認
            regime_enabled = get_threshold(
                "position_management.take_profit.regime_based.enabled", False
            )
            logger.debug(f"🔍 レジーム別TP/SL確認 - regime={regime}, enabled={regime_enabled}")

            if regime and regime_enabled:
                # レジーム別TP設定取得
                regime_tp = get_threshold(
                    f"position_management.take_profit.regime_based.{regime}.min_profit_ratio", None
                )
                regime_tp_ratio = get_threshold(
                    f"position_management.take_profit.regime_based.{regime}.default_ratio", None
                )
                # レジーム別SL設定取得
                regime_sl = get_threshold(
                    f"position_management.stop_loss.regime_based.{regime}.max_loss_ratio", None
                )

                # レジーム別設定取得をログ出力（DEBUG）
                logger.debug(
                    f"🔍 レジーム別設定取得 - {regime}: "
                    f"TP={regime_tp}, TP_ratio={regime_tp_ratio}, SL={regime_sl}"
                )

                if regime_tp and regime_sl:
                    # レジーム別設定をconfigに反映
                    config["min_profit_ratio"] = regime_tp
                    if regime_tp_ratio:
                        config["take_profit_ratio"] = regime_tp_ratio
                    config["max_loss_ratio"] = regime_sl

                    logger.info(
                        f"🎯 Phase 52.0: レジーム別TP/SL適用 - {regime}: "
                        f"TP={regime_tp * 100:.1f}%, SL={regime_sl * 100:.1f}%, "
                        f"RR比={regime_tp_ratio:.2f}:1"
                    )
                else:
                    logger.warning(
                        f"⚠️ Phase 52.0: レジーム別TP/SL設定が不完全 - {regime}: "
                        f"TP={regime_tp}, SL={regime_sl} → デフォルト設定使用"
                    )

            # ========================================
            # Phase 58.6: 土日TP/SL縮小対応
            # ========================================
            weekend_enabled = get_threshold("position_management.weekend_adjustment.enabled", False)
            if weekend_enabled and regime:
                # 土日判定（バックテスト対応）
                check_time = current_time if current_time else datetime.now()
                is_weekend = check_time.weekday() >= 5  # 5=土, 6=日

                if is_weekend:
                    # 土日用TP設定取得
                    weekend_tp = get_threshold(
                        f"position_management.take_profit.regime_based.{regime}.weekend_ratio",
                        None,
                    )
                    # 土日用SL設定取得
                    weekend_sl = get_threshold(
                        f"position_management.stop_loss.regime_based.{regime}.weekend_ratio",
                        None,
                    )

                    if weekend_tp:
                        config["min_profit_ratio"] = weekend_tp
                    if weekend_sl:
                        config["max_loss_ratio"] = weekend_sl

                    logger.info(
                        f"📅 Phase 58.6: 土日TP/SL縮小適用 - {regime}: "
                        f"TP={weekend_tp * 100:.2f}% ({check_time.strftime('%a')}), "
                        f"SL={weekend_sl * 100:.2f}%"
                        if weekend_tp and weekend_sl
                        else f"📅 Phase 58.6: 土日判定 ({check_time.strftime('%a')}) - 設定なし"
                    )

            # === SL距離計算（max_loss_ratio優先） ===
            # Phase 51.6: ハードコード削除・設定ファイル一元管理（SL 0.7%）
            # Phase 52.0: レジーム別設定が適用済み（上記で反映）
            max_loss_ratio = config.get(
                "max_loss_ratio",
                get_threshold("position_management.stop_loss.max_loss_ratio"),
            )

            # max_loss_ratioベースのSL距離（固定採用）
            sl_distance_from_ratio = current_price * max_loss_ratio

            # ATRベースのSL距離（参考値のみ・採用しない）
            stop_loss_multiplier = RiskManager._calculate_adaptive_atr_multiplier(
                current_atr, atr_history
            )
            sl_distance_from_atr = current_atr * stop_loss_multiplier

            # max_loss_ratio固定採用（安定性優先）
            stop_loss_distance = sl_distance_from_ratio

            logger.info(
                f"🎯 Phase 49.16 SL距離計算: "
                f"max_loss={max_loss_ratio * 100:.1f}% → {sl_distance_from_ratio:.0f}円（固定採用）, "
                f"ATR×{stop_loss_multiplier:.2f} → {sl_distance_from_atr:.0f}円（参考値） "
                f"→ 採用={stop_loss_distance:.0f}円({stop_loss_distance / current_price * 100:.2f}%)"
            )

            # Phase 66.6: 固定金額SLモードチェック
            fixed_sl_config = get_threshold("position_management.stop_loss.fixed_amount", {})
            fixed_sl_enabled = fixed_sl_config.get("enabled", False)

            if fixed_sl_enabled and position_amount and position_amount > 0:
                # レジーム別SL金額取得
                if regime:
                    sl_target = get_threshold(
                        f"position_management.stop_loss.regime_based.{regime}.fixed_amount_target",
                        fixed_sl_config.get("target_max_loss", 500),
                    )
                else:
                    sl_target = fixed_sl_config.get("target_max_loss", 500)

                # Phase 68.8: 信頼度別SL金額
                confidence_config = fixed_sl_config.get("confidence_based", {})
                confidence_label = ""
                if confidence is not None and confidence_config.get("enabled", False):
                    threshold = confidence_config.get("threshold", 0.40)
                    if confidence >= threshold:
                        sl_target = confidence_config.get("high", 500)
                        confidence_label = f"(高信頼度≥{threshold})"
                    else:
                        sl_target = confidence_config.get("low", 400)
                        confidence_label = f"(低信頼度<{threshold})"

                # SL決済手数料考慮（Taker 0.1%）
                exit_fee_rate = fixed_sl_config.get("fallback_exit_fee_rate", 0.001)
                exit_fee = current_price * position_amount * exit_fee_rate

                # Phase 69: entry_feeはサンクコスト（エントリー時に支払済み）
                # SL予算から差し引くとSL距離が極端に狭くなるバグを修正
                gross_loss = sl_target - exit_fee
                if gross_loss > 0:
                    fixed_sl_distance = gross_loss / position_amount

                    # 妥当性チェック（10%超は異常値）
                    if fixed_sl_distance <= current_price * 0.10:
                        stop_loss_distance = fixed_sl_distance
                        logger.info(
                            f"🛡️ Phase 69: 固定金額SL適用 - "
                            f"目標最大損失={sl_target:.0f}円{confidence_label}, "
                            f"決済手数料={exit_fee:.0f}円, "
                            f"SL距離={fixed_sl_distance:.0f}円"
                            f"({fixed_sl_distance / current_price * 100:.2f}%)"
                        )
                    else:
                        logger.warning(
                            f"⚠️ Phase 66.6: 固定金額SL計算異常 - "
                            f"距離={fixed_sl_distance:.0f}円 > 10% "
                            f"→ %ベースを維持"
                        )

            # === TP距離計算 ===
            # Phase 61.7: 固定金額TPモードチェック
            fixed_amount_config = get_threshold("position_management.take_profit.fixed_amount", {})
            fixed_amount_enabled = fixed_amount_config.get("enabled", False)

            take_profit = None  # 後で計算

            if fixed_amount_enabled and position_amount and position_amount > 0:
                # Phase 61.7: 固定金額TPモード
                # レジーム別目標取得
                if regime:
                    regime_target = get_threshold(
                        f"position_management.take_profit.regime_based.{regime}.fixed_amount_target",
                        fixed_amount_config.get("target_net_profit", 1000),
                    )
                    # レジーム別目標をconfigにコピー
                    fixed_amount_config = dict(fixed_amount_config)  # コピーして変更
                    fixed_amount_config["target_net_profit"] = regime_target

                # Phase 68.8: 信頼度別TP金額
                tp_confidence_config = fixed_amount_config.get("confidence_based", {})
                tp_confidence_label = ""
                if confidence is not None and tp_confidence_config.get("enabled", False):
                    tp_threshold = tp_confidence_config.get("threshold", 0.40)
                    if confidence >= tp_threshold:
                        fixed_amount_config = dict(fixed_amount_config)
                        fixed_amount_config["target_net_profit"] = tp_confidence_config.get(
                            "high", 500
                        )
                        tp_confidence_label = f"(高信頼度≥{tp_threshold})"
                    else:
                        fixed_amount_config = dict(fixed_amount_config)
                        fixed_amount_config["target_net_profit"] = tp_confidence_config.get(
                            "low", 400
                        )
                        tp_confidence_label = f"(低信頼度<{tp_threshold})"

                fixed_tp = RiskManager.calculate_fixed_amount_tp(
                    action=action,
                    entry_price=current_price,
                    amount=position_amount,
                    fee_data=fee_data,
                    config=fixed_amount_config,
                )

                if fixed_tp:
                    take_profit = fixed_tp
                    logger.info(
                        f"🎯 Phase 61.7: 固定金額TP適用 - "
                        f"目標純利益={fixed_amount_config.get('target_net_profit', 1000):.0f}円"
                        f"{tp_confidence_label}, "
                        f"TP={fixed_tp:.0f}円"
                    )
                else:
                    logger.warning("⚠️ Phase 61.7: 固定金額TP計算失敗 - %ベースにフォールバック")
                    # フォールバック: 従来の%ベース計算へ

            # 固定金額TPが設定されなかった場合、従来の%ベース計算
            if take_profit is None:
                # Phase 51.6: ハードコード削除・設定ファイル一元管理（TP 0.9%・RR比1.29:1）
                min_profit_ratio = config.get(
                    "min_profit_ratio",
                    get_threshold("position_management.take_profit.min_profit_ratio"),
                )
                default_tp_ratio = config.get(
                    "take_profit_ratio",
                    get_threshold("position_management.take_profit.default_ratio"),
                )

                # min_profit_ratioベースのTP距離
                tp_distance_from_ratio = current_price * min_profit_ratio

                # SL距離×TP比率ベースのTP距離
                tp_distance_from_sl = stop_loss_distance * default_tp_ratio

                # 大きい方を採用（利益確保優先）
                take_profit_distance = max(tp_distance_from_ratio, tp_distance_from_sl)

                logger.info(
                    f"🎯 Phase 49.16 TP距離計算: "
                    f"min_profit={min_profit_ratio * 100:.1f}% → {tp_distance_from_ratio:.0f}円, "
                    f"SL×{default_tp_ratio:.2f} → {tp_distance_from_sl:.0f}円 "
                    f"→ 採用={take_profit_distance:.0f}円({take_profit_distance / current_price * 100:.2f}%)"
                )

                # TP価格計算（%ベース）
                if action == EntryAction.BUY:
                    take_profit = current_price + take_profit_distance
                else:  # SELL
                    take_profit = current_price - take_profit_distance

            # === SL価格計算 ===
            if action == EntryAction.BUY:
                stop_loss = current_price - stop_loss_distance
            else:  # SELL
                stop_loss = current_price + stop_loss_distance

            # 妥当性確認
            if stop_loss <= 0 or take_profit <= 0:
                logger.error(f"無効なTP/SL価格: SL={stop_loss:.0f}円, TP={take_profit:.0f}円")
                return None, None

            # 最終ログ
            rr_ratio = (
                abs((take_profit - current_price) / (current_price - stop_loss))
                if action == EntryAction.BUY
                else abs((current_price - take_profit) / (stop_loss - current_price))
            )
            logger.info(
                f"✅ Phase 49.16 TP/SL確定: "
                f"エントリー={current_price:.0f}円, "
                f"SL={stop_loss:.0f}円({abs(stop_loss - current_price) / current_price * 100:.2f}%), "
                f"TP={take_profit:.0f}円({abs(take_profit - current_price) / current_price * 100:.2f}%), "
                f"RR比={rr_ratio:.2f}:1"
            )

            return stop_loss, take_profit

        except Exception as e:
            logger.error(f"TP/SL計算エラー: {e}")
            return None, None

    @staticmethod
    def calculate_position_size(confidence: float, config: Dict[str, Any]) -> float:
        """
        ポジションサイズ計算

        Args:
            confidence: シグナル信頼度（0.0-1.0）
            config: 戦略設定（position_size_base含む）

        Returns:
            計算されたポジションサイズ
        """
        logger = get_logger()

        try:
            # パラメータ取得
            base_size = config.get("position_size_base", DEFAULT_RISK_PARAMS["position_size_base"])
            max_size = config.get("max_position_size", DEFAULT_RISK_PARAMS["max_position_size"])

            # 信頼度による調整
            position_size = base_size * max(0.0, min(1.0, confidence))

            # 最大サイズ制限
            position_size = min(position_size, max_size)

            return position_size

        except Exception as e:
            logger.error(f"ポジションサイズ計算エラー: {e}")
            return 0.0

    @staticmethod
    def calculate_risk_ratio(current_price: float, stop_loss: Optional[float]) -> Optional[float]:
        """
        リスク比率計算

        Args:
            current_price: 現在価格
            stop_loss: ストップロス価格

        Returns:
            リスク比率（None if 計算不可）
        """
        try:
            if stop_loss is None or current_price <= 0:
                return None

            risk_ratio = abs(stop_loss - current_price) / current_price
            return risk_ratio

        except Exception:
            return None


# === シグナル生成クラス ===


class SignalBuilder:
    """
    StrategySignal生成統合クラス

    全戦略で共通するシグナル生成処理を一元化。
    リスク管理計算も統合して処理。
    """

    @staticmethod
    def create_signal_with_risk_management(
        strategy_name: str,
        decision: Dict[str, Any],
        current_price: float,
        df: pd.DataFrame,
        config: Dict[str, Any],
        strategy_type: Optional[str] = None,
        multi_timeframe_data: Optional[Dict[str, pd.DataFrame]] = None,
    ) -> StrategySignal:
        """
        リスク管理付きシグナル生成

        Args:
            strategy_name: 戦略名
            decision: 戦略の判定結果（action, confidence, strength等）
            current_price: 現在価格
            df: 市場データ（ATR計算用）
            config: 戦略設定
            strategy_type: 戦略タイプ（メタデータ用）
            multi_timeframe_data: マルチタイムフレームデータ（Phase 31対応）

        Returns:
            完全なStrategySignal
        """
        logger = get_logger()

        try:
            action = decision.get("action", EntryAction.HOLD)
            confidence = decision.get("confidence", 0.0)
            strength = decision.get("strength", 0.0)
            reason = decision.get("analysis", decision.get("reason", ""))

            # リスク管理計算（エントリーシグナルのみ）
            stop_loss = None
            take_profit = None
            position_size = None
            risk_ratio = None

            if action in [EntryAction.BUY, EntryAction.SELL]:
                # Phase 31: 15m足ATR優先取得
                current_atr = RiskManager._extract_15m_atr(df, multi_timeframe_data)
                if current_atr is None:
                    logger.warning(f"ATR取得失敗: {strategy_name}")
                    return SignalBuilder._create_error_signal(
                        strategy_name, current_price, "ATR取得失敗"
                    )

                # Phase 30: ATR履歴取得（適応型ATR用）
                atr_history = None
                if multi_timeframe_data and "15m" in multi_timeframe_data:
                    try:
                        df_15m = multi_timeframe_data["15m"]
                        if "atr_14" in df_15m.columns:
                            atr_history = df_15m["atr_14"].dropna().tail(20).tolist()
                    except Exception:
                        pass

                # Phase 53.9: SignalBuilder内でレジーム自動判定（一元化）
                regime = None
                try:
                    from src.core.services.market_regime_classifier import (
                        MarketRegimeClassifier,
                    )

                    regime_classifier = MarketRegimeClassifier()
                    regime_type = regime_classifier.classify(df)
                    regime = (
                        regime_type.value if hasattr(regime_type, "value") else str(regime_type)
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Phase 53.9: レジーム判定失敗（デフォルト使用）: {e}")

                # Phase 61.10: Dynamic Position Sizing（ライブ互換）
                # dfから価格取得、設定から残高取得してライブモードと同等のサイズ計算
                btc_price = None
                current_balance = None
                try:
                    from ...core.config import get_threshold

                    if df is not None and "close" in df.columns and len(df) > 0:
                        btc_price = float(df["close"].iloc[-1])
                    current_balance = get_threshold(
                        "mode_balances.backtest.initial_balance", 500000.0
                    )
                except Exception:
                    pass

                if btc_price and current_balance and btc_price > 0 and current_balance > 0:
                    position_size = SignalBuilder._calculate_dynamic_position_size(
                        confidence=confidence,
                        current_balance=current_balance,
                        btc_price=btc_price,
                        config=config,
                    )
                else:
                    # フォールバック（既存計算）
                    position_size = RiskManager.calculate_position_size(confidence, config)

                # ストップロス・テイクプロフィット計算（レジーム別設定適用）
                # Phase 58.6: 土日判定用にcurrent_time追加（dfのindexから取得）
                signal_time = None
                if df is not None and len(df) > 0 and df.index is not None:
                    try:
                        signal_time = pd.to_datetime(df.index[-1])
                    except Exception:
                        signal_time = None
                # Phase 61.8: position_amountを渡して固定金額TP計算を有効化（バックテスト対応）
                # Phase 68.8: confidence伝播（信頼度別TP/SL用）
                stop_loss, take_profit = RiskManager.calculate_stop_loss_take_profit(
                    action,
                    current_price,
                    current_atr,
                    config,
                    atr_history,
                    regime=regime,
                    current_time=signal_time,
                    fee_data=None,  # バックテスト時はNone（フォールバックレート使用）
                    position_amount=position_size,  # Phase 61.8: 固定金額TP用
                    confidence=confidence,  # Phase 68.8: 信頼度別TP/SL
                )

                # リスク比率計算
                risk_ratio = RiskManager.calculate_risk_ratio(current_price, stop_loss)

            # メタデータ作成
            metadata = {
                "strategy_type": strategy_type,
                "risk_calculated": action in [EntryAction.BUY, EntryAction.SELL],
                "decision_metadata": decision.get("metadata", {}),
            }

            # StrategySignal生成
            return StrategySignal(
                strategy_name=strategy_name,
                timestamp=datetime.now(),
                action=action,
                confidence=confidence,
                strength=strength,
                current_price=current_price,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                position_size=position_size,
                risk_ratio=risk_ratio,
                reason=reason,
                metadata=metadata,
            )

        except Exception as e:
            logger.error(f"シグナル生成エラー ({strategy_name}): {e}")
            return SignalBuilder._create_error_signal(
                strategy_name, current_price, f"シグナル生成エラー: {e}"
            )

    @staticmethod
    def create_hold_signal(
        strategy_name: str,
        current_price: float,
        reason: str = "条件不適合",
        strategy_type: Optional[str] = None,
        confidence: Optional[float] = None,
    ) -> StrategySignal:
        """
        ホールドシグナル生成

        Args:
            strategy_name: 戦略名
            current_price: 現在価格
            reason: ホールド理由
            strategy_type: 戦略タイプ
            confidence: 信頼度（Noneの場合0.5）

        Returns:
            ホールドStrategySignal
        """
        return StrategySignal(
            strategy_name=strategy_name,
            timestamp=datetime.now(),
            action=EntryAction.HOLD,
            confidence=confidence if confidence is not None else 0.5,
            strength=0.0,
            current_price=current_price,
            reason=reason,
            metadata={"strategy_type": strategy_type},
        )

    @staticmethod
    def _calculate_dynamic_position_size(
        confidence: float,
        current_balance: float,
        btc_price: float,
        config: Dict[str, Any],
    ) -> float:
        """
        Phase 67.4: 固定テーブル優先・フォールバックでDynamic計算

        Args:
            confidence: シグナル信頼度（0.0-1.0）
            current_balance: 現在残高（円）
            btc_price: 現在のBTC価格（円）
            config: 戦略設定（互換性維持用、未使用）

        Returns:
            計算されたポジションサイズ（BTC）
        """
        from ...core.config import get_threshold
        from ...trading.risk.sizer import PositionSizeIntegrator

        # Phase 67.4: 固定テーブルモード
        mode = get_threshold("position_sizing.mode", "dynamic")
        if mode == "fixed":
            medium_min = get_threshold("position_sizing.confidence_thresholds.medium_min", 0.50)
            high_min = get_threshold("position_sizing.confidence_thresholds.high_min", 0.65)
            if confidence >= high_min:
                return get_threshold("position_sizing.fixed_table.high", 0.02)
            elif confidence >= medium_min:
                return get_threshold("position_sizing.fixed_table.medium", 0.015)
            else:
                return get_threshold("position_sizing.fixed_table.low", 0.01)

        # フォールバック: 従来のDynamic計算
        max_size = get_threshold("production.max_order_size", 0.15)
        return PositionSizeIntegrator._calculate_dynamic_position_size(
            ml_confidence=confidence,
            current_balance=current_balance,
            btc_price=btc_price,
            max_order_size=max_size,
        )

    @staticmethod
    def _create_error_signal(
        strategy_name: str, current_price: float, error_message: str
    ) -> StrategySignal:
        """
        エラー時のフォールバックシグナル生成

        Args:
            strategy_name: 戦略名
            current_price: 現在価格
            error_message: エラーメッセージ

        Returns:
            エラー用ホールドシグナル
        """
        return StrategySignal(
            strategy_name=strategy_name,
            timestamp=datetime.now(),
            action=EntryAction.HOLD,
            confidence=0.0,
            strength=0.0,
            current_price=current_price,
            reason=error_message,
            metadata={"error": True},
        )

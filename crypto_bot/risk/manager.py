# crypto_bot/risk/manager.py
# 説明:
# このファイルは「リスク管理」クラスです。
# ・1トレードでどれだけリスクを取るか計算（例：1%まで）
# ・ATR（平均的な価格変動）を使ってストップロス（損切り幅）とロット数を自動計算
# ・ボラティリティ連動でロット数を調整し、大きく動く相場でもリスク一定にする
# ・バックテストや自動売買の実運用で、破産リスクや過度な損失を防ぐために重要！

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class RiskManager:
    """
    ポジションサイジング & ストップロス水準の計算。
    risk_per_trade : 口座残高に対するリスク割合 (例: 0.01=1%)
    stop_atr_mult  : ATR の何倍をストップ幅に使うか

    This class also supports *dynamic position sizing* that scales the
    lot size by recent volatility so that each trade risks roughly the
    same fraction of the account regardless of market regime.
    """

    def __init__(
        self,
        risk_per_trade: float = 0.01,
        stop_atr_mult: float = 1.5,
        kelly_enabled: bool = False,
        kelly_lookback_window: int = 50,
        kelly_max_fraction: float = 0.25,
    ):
        if not 0 < risk_per_trade <= 1.0:
            raise ValueError(
                f"risk_per_trade must be between 0 and 1.0, got {risk_per_trade}"
            )
        if stop_atr_mult <= 0:
            raise ValueError(f"stop_atr_mult must be positive, got {stop_atr_mult}")

        self.risk_per_trade = risk_per_trade
        self.stop_atr_mult = stop_atr_mult

        # Kelly Criterion パラメータ
        self.kelly_enabled = kelly_enabled
        self.kelly_lookback_window = kelly_lookback_window
        self.kelly_max_fraction = kelly_max_fraction

        # トレード履歴（Kelly基準計算用）
        self.trade_history: List[Dict] = []

    def calc_stop_price(
        self, entry_price: float, atr: pd.Series, side: str = "BUY"
    ) -> float:
        """
        ATR の最新値を取り、stop_atr_mult 倍した幅でストップ価格を計算する。
        ロングの場合は下にずらし、ショートの場合は上にずらす。

        Parameters
        ----------
        entry_price : float
            エントリー価格（正の値でなければならない）
        atr : pd.Series
            ATR時系列データ（空でない）
        side : str
            ポジション方向（"BUY"=ロング、"SELL"=ショート）

        Returns
        -------
        float
            計算されたストップ価格

        Raises
        ------
        ValueError
            入力パラメータが無効な場合
        """
        if entry_price <= 0:
            raise ValueError(f"entry_price must be positive, got {entry_price}")
        if atr.empty:
            raise ValueError("ATR series cannot be empty")

        try:
            latest_atr = atr.iloc[-1]
            if pd.isna(latest_atr):
                # Phase H.23.6: NaN対策強化（エントリー価格の2%）
                logger.warning("⚠️ ATR value is NaN, using fallback 2% of entry price")
                latest_atr = entry_price * 0.02
            elif latest_atr < 0:
                raise ValueError(f"Invalid ATR value: {latest_atr}")

            # ポジション方向に応じてストップ価格を計算
            if side.upper() == "BUY":
                # ロングポジション：エントリー価格より下にストップ
                stop_price = entry_price - latest_atr * self.stop_atr_mult
                # ストップ価格が負になることを防ぐ
                if stop_price <= 0:
                    logger.warning(
                        f"Calculated LONG stop price {stop_price} is negative, "
                        f"setting to entry_price * 0.01"
                    )
                    stop_price = entry_price * 0.01
            elif side.upper() == "SELL":
                # ショートポジション：エントリー価格より上にストップ
                stop_price = entry_price + latest_atr * self.stop_atr_mult
                logger.debug(
                    f"SHORT stop price calculated: entry={entry_price}, "
                    f"atr={latest_atr}, mult={self.stop_atr_mult}, stop={stop_price}"
                )
            else:
                raise ValueError(f"Invalid side: {side}. Must be 'BUY' or 'SELL'")

            return stop_price

        except (IndexError, KeyError) as e:
            raise ValueError(f"Unable to access ATR data: {e}") from e

    def calc_lot(
        self, balance: float, entry_price: float, stop_price: float, side: str = "BUY"
    ) -> float:
        """
        許容損失 = balance * risk_per_trade
        損失幅 = |entry_price - stop_price|
        ロット数 = 許容損失 ÷ 損失幅

        Parameters
        ----------
        balance : float
            口座残高（正の値でなければならない）
        entry_price : float
            エントリー価格（正の値でなければならない）
        stop_price : float
            ストップ価格（正の値でなければならない）
        side : str
            ポジション方向（"BUY"=ロング、"SELL"=ショート）

        Returns
        -------
        float
            計算されたロット数

        Raises
        ------
        ValueError
            入力パラメータが無効な場合
        """
        if balance <= 0:
            raise ValueError(f"balance must be positive, got {balance}")
        if entry_price <= 0:
            raise ValueError(f"entry_price must be positive, got {entry_price}")
        if stop_price <= 0:
            raise ValueError(f"stop_price must be positive, got {stop_price}")

        # ポジション方向に応じた損失幅計算
        if side.upper() == "BUY":
            # ロング：ストップ価格はエントリー価格より下
            if stop_price >= entry_price:
                raise ValueError(
                    f"For LONG position, stop_price ({stop_price}) must be less than "
                    f"entry_price ({entry_price})"
                )
            loss_per_unit = entry_price - stop_price
        elif side.upper() == "SELL":
            # ショート：ストップ価格はエントリー価格より上
            if stop_price <= entry_price:
                raise ValueError(
                    f"For SHORT position, stop_price ({stop_price}) must be "
                    f"greater than entry_price ({entry_price})"
                )
            loss_per_unit = stop_price - entry_price
        else:
            raise ValueError(f"Invalid side: {side}. Must be 'BUY' or 'SELL'")

        risk_amount = balance * self.risk_per_trade
        lot = risk_amount / loss_per_unit

        # 異常に大きなロット数を防ぐ（口座の50%以上のポジションは危険）
        max_lot = balance * 0.5 / entry_price
        if lot > max_lot:
            logger.warning(
                f"Calculated lot {lot} exceeds maximum safe lot {max_lot}, capping it"
            )
            lot = max_lot

        logger.debug(
            f"Position sizing: {side} entry={entry_price}, stop={stop_price}, "
            f"loss_per_unit={loss_per_unit}, lot={lot}"
        )

        return lot

    # ------------------------------------------------------------------
    # Dynamic position sizing
    # ------------------------------------------------------------------
    def dynamic_position_sizing(
        self,
        balance: float,
        entry_price: float,
        atr: pd.Series,
        target_vol: float = 0.01,
        max_scale: float = 3.0,
    ) -> Tuple[float, float]:
        """
        ボラティリティに応じてロット数をスケーリングする。

        Parameters
        ----------
        balance : float
            現在の口座残高 (USDT 等)
        entry_price : float
            エントリー予定価格
        atr : pd.Series
            ATR 時系列（最新値を使用）
        target_vol : float, default 0.01
            1トレードで狙う「価格変動率」(%表記ではなく比率)。
            例) 0.01 = 1% の価格変動を想定。
        max_scale : float, default 3.0
            スケーリング倍率の上限。過度なレバレッジを防ぐ。

        Returns
        -------
        lot : float
            計算されたロット数
        stop_price : float
            設定されたストップ価格

        Raises
        ------
        ValueError
            入力パラメータが無効な場合
        """
        # 入力検証
        if balance <= 0:
            raise ValueError(f"balance must be positive, got {balance}")
        if entry_price <= 0:
            raise ValueError(f"entry_price must be positive, got {entry_price}")
        if not 0 < target_vol <= 1.0:
            raise ValueError(f"target_vol must be between 0 and 1.0, got {target_vol}")
        if max_scale <= 0:
            raise ValueError(f"max_scale must be positive, got {max_scale}")
        if atr.empty:
            raise ValueError("ATR series cannot be empty")

        try:
            # 1) 通常のストップ価格とベースロットを計算
            stop_price = self.calc_stop_price(entry_price, atr)
            base_lot = self.calc_lot(balance, entry_price, stop_price)

            # 2) ボラティリティ(=ATR/価格) からスケール係数を算出
            latest_atr = atr.iloc[-1]
            if pd.isna(latest_atr):
                # Phase H.23.6: NaN対策強化（エントリー価格の2%）
                logger.warning("⚠️ ATR value is NaN, using fallback 2% of entry price")
                latest_atr = entry_price * 0.02
            elif latest_atr < 0:
                raise ValueError(f"Invalid ATR value: {latest_atr}")

            vol_pct = latest_atr / entry_price

            # vol_pct が 0 のときはスケール 1 とする
            if vol_pct <= 0:
                scale = 1.0
                logger.warning(
                    "Volatility percentage is zero or negative, using scale = 1.0"
                )
            else:
                scale = target_vol / vol_pct

            # 3) スケールを安全域にクランプ
            scale = max(0.1, min(scale, max_scale))

            # 4) 最終ロット
            lot = base_lot * scale

            # 最終的な安全チェック
            max_safe_lot = balance * 0.3 / entry_price  # 口座の30%以内
            if lot > max_safe_lot:
                logger.warning(
                    f"Dynamic lot {lot} exceeds safe limit {max_safe_lot}, capping it"
                )
                lot = max_safe_lot

            logger.info("RiskManager: 動的ポジションサイジング完了")
            return lot, stop_price

        except Exception as e:
            logger.error(f"Error in dynamic position sizing: {e}")
            # フォールバック：安全な値を返す
            try:
                stop_price = self.calc_stop_price(entry_price, atr)
                base_lot = self.calc_lot(balance, entry_price, stop_price)
                return base_lot, stop_price
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                # 最終フォールバック：最小安全値
                safe_stop = entry_price * 0.95  # 5%下
                safe_lot = (balance * self.risk_per_trade) / (entry_price * 0.05)
                max_safe = balance * 0.1 / entry_price  # 最大10%
                return min(safe_lot, max_safe), safe_stop

    # ------------------------------------------------------------------
    # Kelly Criterion Position Sizing
    # ------------------------------------------------------------------
    def add_trade_result(
        self,
        entry_price: float,
        exit_price: float,
        position_size: float,
        trade_type: str = "long",
        timestamp: Optional[pd.Timestamp] = None,
    ) -> None:
        """
        トレード結果をKelly基準計算用の履歴に追加します。

        Parameters
        ----------
        entry_price : float
            エントリー価格
        exit_price : float
            エグジット価格
        position_size : float
            ポジションサイズ
        trade_type : str
            トレードタイプ ("long" or "short")
        timestamp : pd.Timestamp, optional
            トレード時刻
        """
        if timestamp is None:
            timestamp = pd.Timestamp.now()

        # リターン計算
        if trade_type.lower() == "long":
            return_pct = (exit_price - entry_price) / entry_price
        else:  # short
            return_pct = (entry_price - exit_price) / entry_price

        trade_record = {
            "timestamp": timestamp,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "position_size": position_size,
            "trade_type": trade_type,
            "return_pct": return_pct,
            "profit_loss": return_pct * position_size,
            "is_win": return_pct > 0,
        }

        self.trade_history.append(trade_record)

        # 履歴サイズを制限（メモリ効率のため）
        max_history = self.kelly_lookback_window * 2
        if len(self.trade_history) > max_history:
            self.trade_history = self.trade_history[-max_history:]

        logger.debug(
            f"Added trade result: return={return_pct:.4f}, win={return_pct > 0}"
        )

    def calculate_kelly_fraction(self) -> float:
        """
        Kelly基準に基づく最適なポジションサイズの割合を計算します。

        Kelly公式: f* = (bp - q) / b
        where:
        - b = 平均勝ちトレードの倍率 (average win / average loss)
        - p = 勝率 (win probability)
        - q = 負け率 (1 - p)

        Returns
        -------
        float
            最適ポジション割合（0～kelly_max_fraction の範囲）
        """
        if not self.kelly_enabled:
            return self.risk_per_trade

        # 十分なデータがない場合はデフォルト値を返す
        if len(self.trade_history) < 10:
            logger.debug(
                "Insufficient trade history for Kelly calculation, using default risk"
            )
            return self.risk_per_trade

        # 直近のトレード履歴を取得
        recent_trades = self.trade_history[-self.kelly_lookback_window :]

        if len(recent_trades) < 5:
            return self.risk_per_trade

        # 勝ちトレードと負けトレードを分離
        wins = [t for t in recent_trades if t["is_win"]]
        losses = [t for t in recent_trades if not t["is_win"]]

        if len(wins) == 0 or len(losses) == 0:
            logger.debug("No wins or losses in recent history, using default risk")
            return self.risk_per_trade

        # 勝率計算
        win_rate = len(wins) / len(recent_trades)

        # 平均勝ち・負け比率計算
        avg_win = np.mean([abs(t["return_pct"]) for t in wins])
        avg_loss = np.mean([abs(t["return_pct"]) for t in losses])

        if avg_loss == 0:
            logger.warning("Average loss is zero, using default risk")
            return self.risk_per_trade

        # Kelly公式の計算
        b = avg_win / avg_loss  # オッズ比
        p = win_rate
        q = 1 - p

        kelly_fraction = (b * p - q) / b

        logger.debug(
            f"Kelly calculation: win_rate={p:.3f}, avg_win={avg_win:.4f}, "
            f"avg_loss={avg_loss:.4f}, b={b:.3f}, kelly_f={kelly_fraction:.4f}"
        )

        # 負の値の場合は0に制限（ベットしない）
        kelly_fraction = max(0, kelly_fraction)

        # 最大割合に制限（過度なレバレッジを防ぐ）
        kelly_fraction = min(kelly_fraction, self.kelly_max_fraction)

        return kelly_fraction

    def calc_kelly_position_size(
        self, balance: float, entry_price: float, stop_price: float
    ) -> float:
        """
        Kelly基準に基づくポジションサイズを計算します。

        Parameters
        ----------
        balance : float
            現在の口座残高
        entry_price : float
            エントリー予定価格
        stop_price : float
            ストップロス価格

        Returns
        -------
        float
            Kelly基準によるロットサイズ
        """
        if not self.kelly_enabled:
            return self.calc_lot(balance, entry_price, stop_price)

        kelly_fraction = self.calculate_kelly_fraction()

        # Kelly基準によるリスク額
        kelly_risk_amount = balance * kelly_fraction

        # 損失幅
        loss_per_unit = entry_price - stop_price

        if loss_per_unit <= 0:
            logger.warning("Invalid stop price for Kelly calculation, using default")
            return self.calc_lot(balance, entry_price, stop_price)

        # Kelly基準ロットサイズ
        kelly_lot = kelly_risk_amount / loss_per_unit

        # 安全制限の適用
        max_safe_lot = balance * 0.5 / entry_price
        kelly_lot = min(kelly_lot, max_safe_lot)

        logger.info(
            f"Kelly position sizing: fraction={kelly_fraction:.4f}, "
            f"lot={kelly_lot:.4f} (vs default="
            f"{self.calc_lot(balance, entry_price, stop_price):.4f})"
        )

        return kelly_lot

    def get_kelly_statistics(self) -> Dict:
        """
        Kelly基準の統計情報を取得します。

        Returns
        -------
        Dict
            Kelly基準関連の統計情報
        """
        if len(self.trade_history) < 5:
            return {
                "enabled": self.kelly_enabled,
                "trade_count": len(self.trade_history),
                "status": "insufficient_data",
            }

        recent_trades = self.trade_history[-self.kelly_lookback_window :]
        wins = [t for t in recent_trades if t["is_win"]]
        losses = [t for t in recent_trades if not t["is_win"]]

        win_rate = len(wins) / len(recent_trades) if recent_trades else 0
        avg_win = np.mean([abs(t["return_pct"]) for t in wins]) if wins else 0
        avg_loss = np.mean([abs(t["return_pct"]) for t in losses]) if losses else 0

        return {
            "enabled": self.kelly_enabled,
            "trade_count": len(recent_trades),
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "kelly_fraction": self.calculate_kelly_fraction(),
            "max_kelly_fraction": self.kelly_max_fraction,
            "lookback_window": self.kelly_lookback_window,
        }

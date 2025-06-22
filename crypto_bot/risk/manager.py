# crypto_bot/risk/manager.py
# 説明:
# このファイルは「リスク管理」クラスです。
# ・1トレードでどれだけリスクを取るか計算（例：1%まで）
# ・ATR（平均的な価格変動）を使ってストップロス（損切り幅）とロット数を自動計算
# ・ボラティリティ連動でロット数を調整し、大きく動く相場でもリスク一定にする
# ・バックテストや自動売買の実運用で、破産リスクや過度な損失を防ぐために重要！

import logging
from typing import Tuple

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

    def __init__(self, risk_per_trade: float = 0.01, stop_atr_mult: float = 1.5):
        if not 0 < risk_per_trade <= 1.0:
            raise ValueError(
                f"risk_per_trade must be between 0 and 1.0, got {risk_per_trade}"
            )
        if stop_atr_mult <= 0:
            raise ValueError(f"stop_atr_mult must be positive, got {stop_atr_mult}")

        self.risk_per_trade = risk_per_trade
        self.stop_atr_mult = stop_atr_mult

    def calc_stop_price(self, entry_price: float, atr: pd.Series) -> float:
        """
        ATR の最新値を取り、stop_atr_mult 倍した幅を下にずらした価格を返す。

        Parameters
        ----------
        entry_price : float
            エントリー価格（正の値でなければならない）
        atr : pd.Series
            ATR時系列データ（空でない）

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
                # NaNの場合はデフォルトのATR値を使用（エントリー価格の2%）
                logger.warning(f"ATR value is NaN, using default 2% of entry price")
                latest_atr = entry_price * 0.02
            elif latest_atr < 0:
                raise ValueError(f"Invalid ATR value: {latest_atr}")

            stop_price = entry_price - latest_atr * self.stop_atr_mult

            # ストップ価格が負になることを防ぐ
            if stop_price <= 0:
                logger.warning(
                    f"Calculated stop price {stop_price} is negative, "
                    f"setting to entry_price * 0.01"
                )
                stop_price = entry_price * 0.01

            return stop_price

        except (IndexError, KeyError) as e:
            raise ValueError(f"Unable to access ATR data: {e}") from e

    def calc_lot(self, balance: float, entry_price: float, stop_price: float) -> float:
        """
        許容損失 = balance * risk_per_trade
        損失幅 = entry_price - stop_price
        ロット数 = 許容損失 ÷ 損失幅

        Parameters
        ----------
        balance : float
            口座残高（正の値でなければならない）
        entry_price : float
            エントリー価格（正の値でなければならない）
        stop_price : float
            ストップ価格（entry_priceより小さくなければならない）

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
        if stop_price >= entry_price:
            raise ValueError(
                f"stop_price ({stop_price}) must be less than "
                f"entry_price ({entry_price})"
            )

        risk_amount = balance * self.risk_per_trade
        loss_per_unit = entry_price - stop_price

        lot = risk_amount / loss_per_unit

        # 異常に大きなロット数を防ぐ（口座の50%以上のポジションは危険）
        max_lot = balance * 0.5 / entry_price
        if lot > max_lot:
            logger.warning(
                f"Calculated lot {lot} exceeds maximum safe lot {max_lot}, capping it"
            )
            lot = max_lot

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
                logger.warning("ATR value is NaN in dynamic sizing, using default 2%")
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

# crypto_bot/risk/manager.py
# 説明:
# このファイルは「リスク管理」クラスです。
# ・1トレードでどれだけリスクを取るか計算（例：1%まで）
# ・ATR（平均的な価格変動）を使ってストップロス（損切り幅）とロット数を自動計算
# ・ボラティリティ連動でロット数を調整し、大きく動く相場でもリスク一定にする
# ・バックテストや自動売買の実運用で、破産リスクや過度な損失を防ぐために重要！

import pandas as pd


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
        self.risk_per_trade = risk_per_trade
        self.stop_atr_mult = stop_atr_mult

    def calc_stop_price(self, entry_price: float, atr: pd.Series) -> float:
        """
        ATR の最新値を取り、stop_atr_mult 倍した幅を下にずらした価格を返す。
        """
        latest_atr = atr.iloc[-1]
        return entry_price - latest_atr * self.stop_atr_mult

    def calc_lot(self, balance: float, entry_price: float, stop_price: float) -> float:
        """
        許容損失 = balance * risk_per_trade
        損失幅 = entry_price - stop_price
        ロット数 = 許容損失 ÷ 損失幅
        """
        risk_amount = balance * self.risk_per_trade
        loss_per_unit = entry_price - stop_price
        if loss_per_unit <= 0:
            return 0.0
        return risk_amount / loss_per_unit

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
    ) -> tuple[float, float]:
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
        """
        # 1) 通常のストップ価格とベースロットを計算
        stop_price = self.calc_stop_price(entry_price, atr)
        base_lot = self.calc_lot(balance, entry_price, stop_price)

        # 2) ボラティリティ(=ATR/価格) からスケール係数を算出
        latest_atr = atr.iloc[-1]
        vol_pct = latest_atr / entry_price if entry_price else 0.0

        # vol_pct が 0 のときはスケール 1 とする
        if vol_pct <= 0:
            scale = 1.0
        else:
            scale = target_vol / vol_pct

        # 3) スケールを安全域にクランプ
        scale = max(0.1, min(scale, max_scale))

        # 4) 最終ロット
        lot = base_lot * scale
        return lot, stop_price

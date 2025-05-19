import pandas as pd


class RiskManager:
    """
    ポジションサイジング & ストップロス水準の計算。
    risk_per_trade : 口座残高に対するリスク割合 (例: 0.01=1%)
    stop_atr_mult  : ATR の何倍をストップ幅に使うか
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

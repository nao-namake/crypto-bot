# tests/unit/risk/test_manager.py
# テスト対象: crypto_bot/risk/manager.py
# 説明:
#   - RiskManagerの各種計算メソッド（ストップ価格、ロット数、動的サイジング）の検証

import numpy as np
import pandas as pd

from crypto_bot.risk.manager import RiskManager


def test_calc_stop_price():
    rm = RiskManager(risk_per_trade=0.01, stop_atr_mult=2.0)
    entry = 100.0
    atr = pd.Series([1, 2, 3])  # 最新=3
    stop = rm.calc_stop_price(entry, atr)
    # entry - latest_atr * stop_atr_mult = 100 - 3*2 = 94
    assert stop == 94.0


def test_calc_lot_normal():
    rm = RiskManager(risk_per_trade=0.02)
    balance = 100000
    entry = 100.0
    stop = 95.0  # 損失幅5
    lot = rm.calc_lot(balance, entry, stop)
    # 許容損失 = 100000*0.02=2000, ロット=2000/5=400
    assert lot == 400.0


def test_calc_lot_zero_division():
    rm = RiskManager()
    balance = 1000
    entry = 100.0
    stop = 100.0  # 損失幅0
    lot = rm.calc_lot(balance, entry, stop)
    assert lot == 0.0  # 負や0なら0返す


def test_dynamic_position_sizing_basic():
    rm = RiskManager(risk_per_trade=0.01, stop_atr_mult=1.5)
    balance = 10000
    entry = 200
    atr = pd.Series([2, 4, 6])  # 最新=6
    # stop = entry - 6*1.5 = 200 - 9 = 191
    # base_lot = (10000*0.01)/(200-191) = 100/9 ≈ 11.11
    # vol_pct = 6/200=0.03, target_vol=0.01
    # scale = 0.01/0.03 ≈ 0.333..., clamp(0.1, 0.333..., 3.0) = 0.333...
    # lot = 11.11 * 0.333... ≈ 3.70
    lot, stop = rm.dynamic_position_sizing(
        balance, entry, atr, target_vol=0.01, max_scale=3.0
    )
    np.testing.assert_almost_equal(stop, 191.0)
    np.testing.assert_almost_equal(lot, 11.11111111 * 0.33333333, decimal=4)


def test_dynamic_position_sizing_clamp_scale():
    rm = RiskManager()
    balance = 1000
    entry = 50
    atr = pd.Series([0])  # vol_pct=0
    # scale=1, base_lot=...0
    lot, stop = rm.dynamic_position_sizing(
        balance, entry, atr, target_vol=0.01, max_scale=1.0
    )
    assert lot == 0.0
    # scale最大制限
    atr = pd.Series([0.001])  # vol_pct極小
    lot2, _ = rm.dynamic_position_sizing(
        balance, entry, atr, target_vol=10.0, max_scale=1.0
    )
    assert lot2 >= 0.0

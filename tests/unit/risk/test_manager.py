# tests/unit/risk/test_manager.py
# テスト対象: crypto_bot/risk/manager.py
# 説明:
#   - RiskManagerの各種計算メソッド（ストップ価格、ロット数、動的サイジング）の検証

import numpy as np
import pandas as pd
import pytest

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
    stop = 100.0  # 損失幅0 - これは now raises ValueError
    with pytest.raises(ValueError, match="stop_price.*must be less than entry_price"):
        rm.calc_lot(balance, entry, stop)


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
    atr = pd.Series([0.001])  # vol_pct極小だが0ではない
    # scale最大制限 - target_volは1.0以下でなければならない
    lot, _ = rm.dynamic_position_sizing(
        balance, entry, atr, target_vol=0.9, max_scale=1.0
    )
    assert lot >= 0.0


# ========== New Error Handling Tests ==========


def test_risk_manager_init_invalid_params():
    """リスクマネージャー初期化時の無効パラメータテスト"""
    # 負のリスク率
    with pytest.raises(ValueError, match="risk_per_trade must be between 0 and 1.0"):
        RiskManager(risk_per_trade=-0.01)

    # リスク率が1より大きい
    with pytest.raises(ValueError, match="risk_per_trade must be between 0 and 1.0"):
        RiskManager(risk_per_trade=1.5)

    # 負のATR倍率
    with pytest.raises(ValueError, match="stop_atr_mult must be positive"):
        RiskManager(stop_atr_mult=-1.0)


def test_calc_stop_price_invalid_inputs(caplog):
    """ストップ価格計算時の無効入力テスト"""
    rm = RiskManager()

    # 負のエントリー価格
    with pytest.raises(ValueError, match="entry_price must be positive"):
        rm.calc_stop_price(-100.0, pd.Series([1, 2, 3]))

    # 空のATR系列
    with pytest.raises(ValueError, match="ATR series cannot be empty"):
        rm.calc_stop_price(100.0, pd.Series([]))

    # NaNを含むATR - 現在は警告をログに出してデフォルト値を使用する
    import logging

    with caplog.at_level(logging.WARNING):
        stop_price = rm.calc_stop_price(100.0, pd.Series([1, 2, np.nan]))
        assert stop_price > 0  # デフォルト値が使用されることを確認
        assert "ATR value is NaN" in caplog.text

    # 負のATR値
    with pytest.raises(ValueError, match="Invalid ATR value"):
        rm.calc_stop_price(100.0, pd.Series([1, 2, -1]))


def test_calc_lot_invalid_inputs():
    """ロット計算時の無効入力テスト"""
    rm = RiskManager()

    # 負の残高
    with pytest.raises(ValueError, match="balance must be positive"):
        rm.calc_lot(-1000, 100.0, 95.0)

    # 負のエントリー価格
    with pytest.raises(ValueError, match="entry_price must be positive"):
        rm.calc_lot(1000, -100.0, 95.0)

    # 負のストップ価格
    with pytest.raises(ValueError, match="stop_price must be positive"):
        rm.calc_lot(1000, 100.0, -95.0)

    # ストップ価格がエントリー価格以上
    with pytest.raises(ValueError, match="stop_price.*must be less than entry_price"):
        rm.calc_lot(1000, 100.0, 105.0)


def test_dynamic_position_sizing_invalid_inputs():
    """動的ポジションサイジング時の無効入力テスト"""
    rm = RiskManager()

    # 負の残高
    with pytest.raises(ValueError, match="balance must be positive"):
        rm.dynamic_position_sizing(-1000, 100.0, pd.Series([1, 2, 3]))

    # 負のエントリー価格
    with pytest.raises(ValueError, match="entry_price must be positive"):
        rm.dynamic_position_sizing(1000, -100.0, pd.Series([1, 2, 3]))

    # 無効なターゲットボラティリティ
    with pytest.raises(ValueError, match="target_vol must be between 0 and 1.0"):
        rm.dynamic_position_sizing(1000, 100.0, pd.Series([1, 2, 3]), target_vol=-0.01)

    with pytest.raises(ValueError, match="target_vol must be between 0 and 1.0"):
        rm.dynamic_position_sizing(1000, 100.0, pd.Series([1, 2, 3]), target_vol=1.5)

    # 負の最大スケール
    with pytest.raises(ValueError, match="max_scale must be positive"):
        rm.dynamic_position_sizing(1000, 100.0, pd.Series([1, 2, 3]), max_scale=-1.0)

    # 空のATR系列
    with pytest.raises(ValueError, match="ATR series cannot be empty"):
        rm.dynamic_position_sizing(1000, 100.0, pd.Series([]))


def test_calc_stop_price_negative_protection():
    """ストップ価格が負になる場合の保護テスト"""
    rm = RiskManager(stop_atr_mult=10.0)  # 大きなATR倍率
    entry = 5.0
    atr = pd.Series([1.0])  # stop = 5 - 1*10 = -5 -> 保護により 5*0.01 = 0.05

    stop = rm.calc_stop_price(entry, atr)
    assert stop == entry * 0.01  # 保護により最小値設定


def test_calc_lot_max_protection():
    """ロット数の最大値保護テスト"""
    rm = RiskManager(risk_per_trade=0.9)  # 高いリスク率
    balance = 1000
    entry = 100.0
    stop = 99.9  # 非常に小さな損失幅

    lot = rm.calc_lot(balance, entry, stop)
    max_expected = balance * 0.5 / entry  # 最大保護値
    assert lot == max_expected


def test_dynamic_position_sizing_safety_cap():
    """動的ポジションサイジングの安全上限テスト"""
    rm = RiskManager(risk_per_trade=0.5)  # 高いリスク率
    balance = 1000
    entry = 10.0
    atr = pd.Series([0.001])  # 非常に小さなATR → 大きなロット

    lot, _ = rm.dynamic_position_sizing(
        balance, entry, atr, target_vol=1.0, max_scale=100.0
    )
    max_expected = balance * 0.3 / entry  # 安全上限
    assert lot <= max_expected


def test_dynamic_position_sizing_zero_volatility_warning(caplog):
    """ボラティリティが0の場合の警告とフォールバックテスト"""
    rm = RiskManager()
    balance = 1000
    entry = 100.0
    atr = pd.Series(
        [0.0]
    )  # ゼロボラティリティ → stop_price = entry_price → calc_lotでエラー → フォールバック

    with caplog.at_level("WARNING"):
        lot, stop = rm.dynamic_position_sizing(balance, entry, atr)

    # フォールバックが動作することを確認
    assert "Error in dynamic position sizing" in caplog.text
    assert lot >= 0.0
    assert stop > 0.0

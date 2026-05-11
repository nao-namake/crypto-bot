"""
Phase 86: TPSLCalculator のユニットテスト

TP/SL計算の単一実装が正しく動作することを確認。
特に「TP entry_fee加算欠落」「SL floor非対称」のバグ修正検証。
"""

import pytest

from src.trading.execution.tpsl_calculator import TPSLCalculator


class TestCalculateTP:
    """TP計算テスト（手数料加算の対称性検証）"""

    def test_tp_buy_with_fees(self):
        """BUYのTP: entry_price + (target + entry_fee + exit_fee) / amount"""
        # tight_range標準: TP1500、entry 12,840,001、amount 0.015
        # entry_fee = 12.84M * 0.015 * 0.001 = 192.6
        # exit_fee (Maker 0%) = 0
        # gross_needed = 1500 + 192.6 + 0 = 1692.6
        # distance = 1692.6 / 0.015 = 112,840
        # TP = 12,840,001 + 112,840 = 12,952,841
        tp = TPSLCalculator.calculate_tp(
            action="buy",
            entry_price=12_840_001,
            amount=0.015,
            target_net_profit=1500,
            entry_fee_rate=0.001,
            exit_fee_rate=0.0,
        )
        assert abs(tp - 12_952_841) < 1, f"TP={tp}, expected ~12,952,841"

    def test_tp_sell_with_fees(self):
        """SELLのTP: entry_price - distance"""
        tp = TPSLCalculator.calculate_tp(
            action="sell",
            entry_price=12_840_001,
            amount=0.015,
            target_net_profit=1500,
            entry_fee_rate=0.001,
            exit_fee_rate=0.0,
        )
        assert abs(tp - 12_727_161) < 1, f"TP={tp}, expected ~12,727,161"

    def test_tp_entry_fee_not_zero_critical(self):
        """Phase 86 バグ修正: entry_fee が加算されていることを確認"""
        # entry_fee なしの場合と比較してTP距離が広いはず
        tp_with_fee = TPSLCalculator.calculate_tp(
            action="buy",
            entry_price=12_840_001,
            amount=0.015,
            target_net_profit=1500,
            entry_fee_rate=0.001,
            exit_fee_rate=0.0,
        )
        tp_without_fee = TPSLCalculator.calculate_tp(
            action="buy",
            entry_price=12_840_001,
            amount=0.015,
            target_net_profit=1500,
            entry_fee_rate=0.0,
            exit_fee_rate=0.0,
        )
        # entry_fee あり TP > entry_fee なし TP
        assert tp_with_fee > tp_without_fee, "entry_fee 加算で TP距離が拡大するはず"
        # 差は entry_fee/amount ≒ 192.6/0.015 = 12,840
        diff = tp_with_fee - tp_without_fee
        assert 12_000 < diff < 13_000, f"TP距離差={diff}, 期待 12000-13000"


class TestCalculateSL:
    """SL計算テスト（手数料控除と floor強制の検証）"""

    def test_sl_buy_with_fees(self):
        """BUYのSL: entry_price - (target - entry_fee - exit_fee) / amount"""
        # tight_range標準: SL2000、entry 12,840,001、amount 0.015
        # entry_fee = 192.6, exit_fee = 192.6（SLはTaker想定）
        # gross_loss = 2000 - 192.6 - 192.6 = 1614.8
        # distance = 1614.8 / 0.015 = 107,653
        # ただし floor 0.7% = 12.84M * 0.007 = 89,880
        # 107,653 > 89,880 なので floor 不要、distance=107,653
        # SL = 12,840,001 - 107,653 = 12,732,348
        sl = TPSLCalculator.calculate_sl(
            action="buy",
            entry_price=12_840_001,
            amount=0.015,
            target_max_loss=2000,
            entry_fee_rate=0.001,
            exit_fee_rate=0.001,
            min_distance_ratio=0.007,
            enable_floor=True,
        )
        assert abs(sl - 12_732_348) < 2, f"SL={sl}, expected ~12,732,348"

    def test_sl_floor_enforcement(self):
        """SL floor強制: 計算distance < floor のとき floor が適用される"""
        # SL目標500（小さい）の場合
        # gross_loss = 500 - 192.6 - 192.6 = 114.8
        # distance = 114.8 / 0.015 = 7,653（極小）
        # floor 0.7% = 89,880 → こちらが採用される
        sl = TPSLCalculator.calculate_sl(
            action="buy",
            entry_price=12_840_001,
            amount=0.015,
            target_max_loss=500,
            entry_fee_rate=0.001,
            exit_fee_rate=0.001,
            min_distance_ratio=0.007,
            enable_floor=True,
        )
        expected_floor_sl = 12_840_001 - (12_840_001 * 0.007)
        assert abs(sl - expected_floor_sl) < 2, f"SL={sl}, expected floor {expected_floor_sl}"

    def test_sl_floor_disabled(self):
        """SL floor無効時は手数料控除値がそのまま使われる"""
        sl = TPSLCalculator.calculate_sl(
            action="buy",
            entry_price=12_840_001,
            amount=0.015,
            target_max_loss=500,
            entry_fee_rate=0.001,
            exit_fee_rate=0.001,
            min_distance_ratio=0.007,
            enable_floor=False,
        )
        # floor無効 → 7,653 円距離
        expected = 12_840_001 - (500 - 192.6 - 192.6) / 0.015
        assert abs(sl - expected) < 2, f"SL={sl}, expected {expected}"

    def test_sl_fee_overflow_fallback(self):
        """手数料合計 >= target_max_loss のときフォールバック発動"""
        # target=200（極小）、entry_fee+exit_fee=385.2 > 200
        # gross_loss = 200 - 385.2 = -185.2 ≤ 0 → fallback: distance = 200/0.015 = 13,333
        # ただし floor 0.7% = 89,880 が大きいので floor が採用
        sl = TPSLCalculator.calculate_sl(
            action="buy",
            entry_price=12_840_001,
            amount=0.015,
            target_max_loss=200,
            entry_fee_rate=0.001,
            exit_fee_rate=0.001,
            min_distance_ratio=0.007,
            enable_floor=True,
        )
        expected_floor_sl = 12_840_001 - (12_840_001 * 0.007)
        assert abs(sl - expected_floor_sl) < 2, f"SL={sl}, expected floor {expected_floor_sl}"


class TestCalculateBoth:
    """TP/SL一括計算の検証"""

    def test_calculate_both_consistency(self):
        """calculate_both と個別呼び出しが同じ結果を返す"""
        tp_alone = TPSLCalculator.calculate_tp(
            action="buy",
            entry_price=12_840_001,
            amount=0.015,
            target_net_profit=1500,
        )
        sl_alone = TPSLCalculator.calculate_sl(
            action="buy",
            entry_price=12_840_001,
            amount=0.015,
            target_max_loss=2000,
        )
        tp_both, sl_both = TPSLCalculator.calculate_both(
            action="buy",
            entry_price=12_840_001,
            amount=0.015,
            target_net_profit=1500,
            target_max_loss=2000,
        )
        assert tp_alone == tp_both
        assert sl_alone == sl_both


class TestPhase86Regression:
    """Phase 86 バグ修正のリグレッションテスト"""

    def test_tp_distance_with_entry_fee(self):
        """Phase 86: TP距離 = (1500+192.6)/0.015 = 112,840（旧バグでは 100,000）"""
        tp = TPSLCalculator.calculate_tp(
            action="buy",
            entry_price=12_840_001,
            amount=0.015,
            target_net_profit=1500,
            entry_fee_rate=0.001,
            exit_fee_rate=0.0,
        )
        distance = tp - 12_840_001
        # Phase 86修正後の正しい距離
        assert 112_000 < distance < 113_000, (
            f"distance={distance}, expected ~112,840 (Phase 86 fix). "
            f"旧バグでは ~100,000 になっていた。"
        )

    def test_sl_distance_with_floor(self):
        """Phase 86: SL距離は floor 0.7% を強制（noise越え保証）"""
        sl = TPSLCalculator.calculate_sl(
            action="buy",
            entry_price=12_500_000,
            amount=0.015,
            target_max_loss=500,  # 旧Phase 83Bのバグ設定
            min_distance_ratio=0.007,
            enable_floor=True,
        )
        distance = 12_500_000 - sl
        # 旧バグ: SL distance = 0.06% で即SL確定
        # Phase 86: floor 0.7% で 87,500円距離が強制される
        assert distance >= 87_000, f"distance={distance}, floor 0.7% (≥87,500) 強制必須"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

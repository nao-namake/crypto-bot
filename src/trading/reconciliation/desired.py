"""
Desired State 計算 — 実建玉に対する「あるべき」TP/SL 価格

既存の復旧経路 `tp_sl_manager._calculate_fixed_amount_tp_for_position` /
`_calculate_fixed_amount_sl_for_position`（Phase 65.2/66.6）と *同じ計算* を、
純粋関数として再実装する。これにより R0 shadow で既存挙動と一致を確認できる。

計算は TPSLCalculator（Phase 86 の単一実装）に委譲:
- TP: target_net_profit + entry_fee(0.1%) + exit_fee(Maker 0%)
- SL: target_max_loss - entry_fee - exit_fee、floor 0.7% 強制

注: 既存復旧経路は confidence 別 / 土日縮小を *使っていない*（エントリー時のみ適用）。
本実装も同じくデフォルトの固定 target を使い、挙動を変えない。confidence/土日は
将来 DesiredConfig 拡張で導入可能（R1 以降）。
"""

from __future__ import annotations

from dataclasses import dataclass

from ..execution.tp_sl_config import TPSLConfig
from ..execution.tpsl_calculator import TPSLCalculator
from .actions import POSITION_SIDES, ActualState, DesiredSide, DesiredState, entry_side_of


@dataclass(frozen=True)
class DesiredConfig:
    """desired 計算の設定値（reconciler が get_threshold から集約して渡す）。

    純粋関数 compute_desired_state がこれを受け取ることで、設定アクセスと計算を分離し
    テスト容易性を保つ。
    """

    tp_target: float = 1200.0
    tp_entry_fee_rate: float = 0.001
    tp_exit_fee_rate: float = 0.0
    sl_target: float = 2000.0
    sl_entry_fee_rate: float = 0.001
    sl_exit_fee_rate: float = 0.001
    sl_floor_ratio: float = 0.007
    sl_floor_enabled: bool = True
    min_valid_btc: float = 0.001
    # 固定金額SL距離が floor のこの倍数を超えたら「微小端数」= clean-up 対象
    micro_sl_multiple: float = 5.0


def load_desired_config() -> DesiredConfig:
    """thresholds.yaml から DesiredConfig を構築（get_threshold 依存・非純粋）。

    既存 `_calculate_fixed_amount_tp/sl_for_position` と同じ設定パスを参照する。
    """
    from ...core.config import get_threshold

    return DesiredConfig(
        tp_target=get_threshold(TPSLConfig.TP_FIXED_AMOUNT_TARGET, 1500),
        tp_entry_fee_rate=get_threshold(TPSLConfig.TP_FIXED_AMOUNT_FALLBACK_ENTRY_RATE, 0.001),
        tp_exit_fee_rate=get_threshold(TPSLConfig.TP_FIXED_AMOUNT_FALLBACK_EXIT_RATE, 0.0),
        sl_target=get_threshold(TPSLConfig.SL_FIXED_AMOUNT_TARGET, 2000),
        sl_entry_fee_rate=get_threshold(TPSLConfig.SL_FIXED_AMOUNT_ENTRY_FEE, 0.001),
        sl_exit_fee_rate=get_threshold(TPSLConfig.SL_FIXED_AMOUNT_EXIT_FEE, 0.001),
        sl_floor_ratio=get_threshold("position_management.stop_loss.min_distance.ratio", 0.007),
        sl_floor_enabled=get_threshold("position_management.stop_loss.min_distance.enabled", False),
        min_valid_btc=get_threshold("position_management.min_valid_position_btc", 0.001),
        micro_sl_multiple=get_threshold(
            "position_management.reconciliation.micro_sl_multiple", 5.0
        ),
    )


def compute_desired_state(actual: ActualState, config: DesiredConfig) -> DesiredState:
    """実建玉に対し、あるべき TP/SL 価格を計算する純粋関数。

    建玉が無い / ダスト / 平均建値不正 のサイドは None（desired なし）。

    Args:
        actual: 実状態
        config: 計算設定（load_desired_config で構築）

    Returns:
        DesiredState（両サイド・建玉ありのサイドのみ DesiredSide）
    """
    sides = {"long": None, "short": None}
    for ps in POSITION_SIDES:
        st = actual.side(ps)
        if not st.has_position or st.amount < config.min_valid_btc or st.avg_price <= 0:
            continue
        action = entry_side_of(ps)  # long→buy / short→sell（TPSLCalculator の向き）
        tp = TPSLCalculator.calculate_tp(
            action=action,
            entry_price=st.avg_price,
            amount=st.amount,
            target_net_profit=config.tp_target,
            entry_fee_rate=config.tp_entry_fee_rate,
            exit_fee_rate=config.tp_exit_fee_rate,
        )
        sl = TPSLCalculator.calculate_sl(
            action=action,
            entry_price=st.avg_price,
            amount=st.amount,
            target_max_loss=config.sl_target,
            entry_fee_rate=config.sl_entry_fee_rate,
            exit_fee_rate=config.sl_exit_fee_rate,
            min_distance_ratio=config.sl_floor_ratio,
            enable_floor=config.sl_floor_enabled,
        )
        # 微小端数判定: 固定金額SL距離が floor の micro_sl_multiple 倍を超える
        # = amount が小さすぎて固定金額SLが機能しない（例: 0.0018 BTC で距離10%）→ clean-up 対象
        sl_distance = abs(sl - st.avg_price)
        floor_distance = st.avg_price * config.sl_floor_ratio
        is_micro = floor_distance > 0 and sl_distance > floor_distance * config.micro_sl_multiple
        sides[ps] = DesiredSide(
            position_side=ps, amount=st.amount, tp_price=tp, sl_price=sl, is_micro=is_micro
        )

    return DesiredState(long=sides["long"], short=sides["short"])

"""
不変条件（invariant）の検証と自己修復 — 裸ポジを構造的に不可能にする層

Phase 90ο の `_check_position_invariants`（検知のみで警告止まり）を、
「是正アクションが欠けていれば MARKET_CLOSE を強制追加する」自己修復付きに昇格させる。

不変条件:
1. 裸ポジ禁止（最重要）: 実建玉>0 なら、実効 SL が建玉をカバー、または MARKET_CLOSE/
   PLACE_SL が計画済み のいずれか必須。どれも無ければ MARKET_CLOSE を強制追加。
2. 価格 SL 割れの未是正: SL を割っているのに成行決済が計画されていない → MARKET_CLOSE 強制。
3. 両建て禁止: long と short を同時保有（R0/R1 は違反記録のみ・自動是正は後段）。
4. サイズ上限: 建玉合計 > max_total_btc（違反記録・超過是正は後段）。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from .actions import POSITION_SIDES, ActualState, DesiredState, ReconcileAction
from .diff import is_sl_breached


@dataclass(frozen=True)
class InvariantReport:
    """invariant 検証の結果。extra_actions は reconcile に強制追加すべき是正操作。"""

    extra_actions: Tuple[ReconcileAction, ...] = ()
    violations: Tuple[str, ...] = ()

    @property
    def has_violations(self) -> bool:
        return len(self.violations) > 0


def check_invariants(
    actual: ActualState,
    desired: DesiredState,
    planned_actions: List[ReconcileAction],
    *,
    coverage_ratio: float = 0.95,
    min_valid_btc: float = 0.001,
    max_total_btc: float = 0.02,
) -> InvariantReport:
    """不変条件を検証し、是正不足なら強制追加すべき action を返す純粋関数。

    Args:
        actual: 実状態
        desired: あるべき状態
        planned_actions: diff_to_actions が既に計画した action（重複是正を避けるため参照）
        coverage_ratio: SL カバー判定比率
        min_valid_btc: ダスト除外閾値
        max_total_btc: 建玉合計サイズ上限

    Returns:
        InvariantReport（強制追加 action と違反ラベル）
    """
    extra: List[ReconcileAction] = []
    violations: List[str] = []

    if not actual.ok:
        # actual 不明時は是正しない（安全側）。診断のみ。
        return InvariantReport((), ("actual_not_ok",))

    for ps in POSITION_SIDES:
        st = actual.side(ps)
        if not st.has_position or st.amount <= min_valid_btc:
            continue

        d = desired.side(ps)
        sl_covered = st.sl_covered(coverage_ratio)
        sl_breached = d is not None and is_sl_breached(ps, actual.current_price, d.sl_price)
        close_planned = any(a.is_market_close and a.position_side == ps for a in planned_actions)
        place_planned = any(a.places_sl and a.position_side == ps for a in planned_actions)

        # 不変条件1: 裸ポジ禁止（是正 action が一つも無ければ成行決済を強制）
        if not sl_covered and not close_planned and not place_planned:
            violations.append(f"naked_position_uncovered:{ps}")
            extra.append(
                ReconcileAction.market_close(ps, st.amount, "invariant_naked_position_uncovered")
            )
        # 不変条件2: 価格 SL 割れなのに成行決済が計画されていない → 強制
        elif sl_breached and not close_planned:
            violations.append(f"sl_breached_uncorrected:{ps}")
            extra.append(ReconcileAction.market_close(ps, st.amount, "invariant_sl_breached"))

    # 不変条件3: 両建て禁止（R0/R1 は記録のみ）
    if actual.is_hedged:
        violations.append("hedge_detected")

    # 不変条件4: サイズ上限（記録のみ・超過是正は後段フェーズ）
    if actual.total_amount > max_total_btc:
        violations.append(f"size_exceeded:{actual.total_amount:.4f}>{max_total_btc}")

    return InvariantReport(tuple(extra), tuple(violations))

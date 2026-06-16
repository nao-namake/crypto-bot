"""
Reconciler core: actual × desired → ReconcileAction[]（純粋関数・副作用ゼロ）

reconcile の心臓部。取引所の実状態（actual）とあるべき状態（desired）を比較し、
冪等な操作リストを返す。同じ入力なら必ず同じ出力（テスト容易・冪等の核）。

判定の優先順位（各建玉サイドごと）:
1. 建玉なし → 残っている SL/TP は孤児 → CANCEL_ORDER
2. 価格が SL を割っている → stop 再配置は bitbank で即 CANCELED_UNFILLED になる罠 →
   MARKET_CLOSE（成行決済）。SL/TP の他操作はしない
3. SL カバー不足（欠損 or 部分） → 既存 SL を消して全量 PLACE_SL
4. TP カバー不足 → 既存 TP を消して全量 PLACE_TP
5. いずれも満たされている → NOOP（冪等の核・大半はこれ）
"""

from __future__ import annotations

from typing import List

from .actions import POSITION_SIDES, ActualState, DesiredState, ReconcileAction


def is_sl_breached(position_side: str, current_price: float, sl_price: float) -> bool:
    """現在価格が SL トリガーを既に割っているか。

    True の場合、その価格で stop 注文を新規配置すると bitbank が「トリガー条件成立済み」
    と判定して即 CANCELED_UNFILLED で失効させうる（実データで確認済み）。よって
    PLACE_SL ではなく MARKET_CLOSE を選ぶべき局面を表す。
    """
    if current_price <= 0 or sl_price <= 0:
        return False
    if position_side == "long":
        return current_price <= sl_price
    return current_price >= sl_price  # short


def diff_to_actions(
    actual: ActualState,
    desired: DesiredState,
    coverage_ratio: float = 0.95,
) -> List[ReconcileAction]:
    """actual と desired の差分を ReconcileAction のリストに変換する純粋関数。

    Args:
        actual: 取引所スナップショット由来の実状態
        desired: 実建玉に対するあるべき TP/SL
        coverage_ratio: SL/TP が建玉のこの割合以上をカバーしていれば「足りている」

    Returns:
        ReconcileAction のリスト（executor が CANCEL→PLACE→MARKET_CLOSE 順に適用）
    """
    actions: List[ReconcileAction] = []

    # actual 取得失敗時は何もしない（誤是正を避ける・安全側）
    if not actual.ok:
        return [ReconcileAction.noop("actual_not_ok")]

    for ps in POSITION_SIDES:
        st = actual.side(ps)

        # 1. 建玉なし → 残存 SL/TP は孤児
        if not st.has_position:
            for oid in (*st.sl_order_ids, *st.tp_order_ids):
                actions.append(ReconcileAction.cancel_order(oid, "orphan_order_no_position", ps))
            continue

        d = desired.side(ps)
        if d is None:
            # 建玉ありなのに desired 不能 → 安全側で何もしない（invariant 層が拾う）
            actions.append(ReconcileAction.noop("desired_missing_for_position", ps))
            continue

        # 2. 価格 SL 割れ → 成行決済（stop 再配置の罠を回避）。このサイドは以降触らない
        if is_sl_breached(ps, actual.current_price, d.sl_price):
            actions.append(ReconcileAction.market_close(ps, st.amount, "sl_breached_market_close"))
            continue

        side_acted = False

        # 3. SL カバー不足 → 既存 SL を消して全量で張り直し
        if not st.sl_covered(coverage_ratio):
            for oid in st.sl_order_ids:
                actions.append(ReconcileAction.cancel_order(oid, "sl_recover_replace", ps))
            actions.append(
                ReconcileAction.place_sl(ps, st.amount, d.sl_price, "sl_missing_or_partial")
            )
            side_acted = True

        # 4. TP カバー不足 → 既存 TP を消して全量で張り直し
        if not st.tp_covered(coverage_ratio):
            for oid in st.tp_order_ids:
                actions.append(ReconcileAction.cancel_order(oid, "tp_recover_replace", ps))
            actions.append(
                ReconcileAction.place_tp(ps, st.amount, d.tp_price, "tp_missing_or_partial")
            )
            side_acted = True

        # 5. すべて満たされている → NOOP
        if not side_acted:
            actions.append(ReconcileAction.noop("covered", ps))

    return actions

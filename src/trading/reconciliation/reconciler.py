"""
Reconciler — reconcile 1 サイクルのオーケストレーション

trigger の全経路（monitor_only / full cycle）から無条件に呼ばれる単一の入口。
snapshot → desire → diff → invariant → apply → (summary log) を冪等に実行する。

actual 取得に失敗したら ABORT（何もしない・安全側）。
shadow_mode（R0）では executor が発注せずログのみ。
"""

from __future__ import annotations

from typing import Any, Optional

from ...core.config import get_threshold
from ...core.logger import get_logger
from .desired import DesiredConfig, compute_desired_state, load_desired_config
from .diff import diff_to_actions
from .executor import ReconcileExecutor, ReconcileReport
from .invariants import check_invariants
from .state import build_actual_state


class Reconciler:
    """実建玉を唯一の真実源として TP/SL を毎サイクル冪等に reconcile する。"""

    def __init__(
        self,
        bitbank_client: Any,
        logger: Optional[Any] = None,
        shadow_mode: bool = True,
        sl_persistence: Any = None,
        symbol: str = "BTC/JPY",
        coverage_ratio: float = 0.95,
        min_valid_btc: float = 0.001,
        max_total_btc: float = 0.02,
        desired_config: Optional[DesiredConfig] = None,
    ):
        self.client = bitbank_client
        self.logger = logger or get_logger()
        self.shadow_mode = shadow_mode
        self.symbol = symbol
        self.coverage_ratio = coverage_ratio
        self.min_valid_btc = min_valid_btc
        self.max_total_btc = max_total_btc
        # テスト/将来拡張用に desired 設定を注入可能（未指定なら thresholds から）
        self.desired_config = desired_config
        self.executor = ReconcileExecutor(
            bitbank_client, self.logger, shadow_mode, sl_persistence, symbol
        )

    async def reconcile_once(self) -> ReconcileReport:
        # A. Actual 取得（唯一の真実源）
        actual = await build_actual_state(self.client, self.symbol, self.logger)
        if not actual.ok:
            self.logger.warning(
                "⚠️ Phase 90π reconcile: actual 取得失敗 → ABORT（安全側で何もしない）"
            )
            return ReconcileReport(shadow_mode=self.shadow_mode)

        # B. Desired 計算（実建玉基準）
        config = self.desired_config if self.desired_config is not None else load_desired_config()
        desired = compute_desired_state(actual, config)

        # C. 差分 → action（純粋）
        actions = diff_to_actions(actual, desired, self.coverage_ratio)

        # D. 不変条件（純粋・是正不足なら MARKET_CLOSE を強制追加）
        inv = check_invariants(
            actual,
            desired,
            actions,
            coverage_ratio=self.coverage_ratio,
            min_valid_btc=self.min_valid_btc,
            max_total_btc=self.max_total_btc,
        )
        if inv.has_violations:
            self.logger.critical(
                f"🚨 Phase 90π invariant違反: {', '.join(inv.violations)} "
                f"(long={actual.long.amount:.4f}/sl={actual.long.sl_amount:.4f}, "
                f"short={actual.short.amount:.4f}/sl={actual.short.sl_amount:.4f}, "
                f"price={actual.current_price:.0f})"
            )
        all_actions = list(actions) + list(inv.extra_actions)

        # E. 実行（shadow_mode なら発注せずログのみ）
        report = await self.executor.apply(all_actions)

        # F. サマリ（NOOP 以外があれば可視化）
        non_noop = [r for r in report.results if r.status != "noop"]
        if non_noop:
            mode = "SHADOW" if self.shadow_mode else "LIVE"
            self.logger.warning(
                f"🔧 Phase 90π reconcile[{mode}]: {report.summary()} "
                f"(actions={len(all_actions)}, "
                f"long={actual.long.amount:.4f}, short={actual.short.amount:.4f})"
            )
        return report


def create_reconciler(
    bitbank_client: Any, sl_persistence: Any = None, logger: Optional[Any] = None
) -> Reconciler:
    """thresholds.yaml から設定を集約して Reconciler を構築する。"""
    return Reconciler(
        bitbank_client=bitbank_client,
        logger=logger,
        shadow_mode=get_threshold("position_management.reconciliation.shadow_mode", True),
        sl_persistence=sl_persistence,
        symbol=get_threshold("trading_constraints.currency_pair", "BTC/JPY"),
        coverage_ratio=get_threshold("position_management.reconciliation.coverage_ratio", 0.95),
        min_valid_btc=get_threshold("position_management.min_valid_position_btc", 0.001),
        max_total_btc=get_threshold("position_management.max_total_position_btc", 0.02),
    )

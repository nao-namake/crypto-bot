"""
TP/SL Reconciliation Loop パッケージ

取引所の実建玉（fetch_margin_positions）を *唯一の真実源* とし、毎サイクルで
「あるべき状態（desired）」と「実際の状態（actual）」の差分を冪等（idempotent）に
埋める Reconciliation Loop を提供する。

設計思想（Kubernetes Operator / Freqtrade と同型）:
- 真実源は実建玉ひとつ。VP（揮発メモリ）/ 永続化はキャッシュに降格。
- 各サイクルで「実建玉>0 なら必ず実効SLが存在する。さもなくば即成行決済」を
  invariant として構造的に保証し、裸ポジを起こさない。
- bitbank の挙動を予測して条件分岐を足すのではなく、結果（actual）を見て差分を埋める。

レイヤー:
- actions.py     : 型定義（ReconcileAction / ActualState / DesiredState）
- state.py       : Actual State 取得・正規化
- desired.py     : Desired State 計算（TPSLCalculator 再利用）
- diff.py        : actual × desired → ReconcileAction[]（純粋関数・中核）
- invariants.py  : 裸ポジ禁止等の不変条件検証（自己修復）
- executor.py    : ReconcileAction の bitbank への適用（唯一の副作用層）
- reconciler.py  : 1サイクルのオーケストレーション

導入: Phase 90π（TP/SL Reconciliation Loop 全面再設計）
"""

from .actions import (
    ActionType,
    ActualState,
    DesiredSide,
    DesiredState,
    ReconcileAction,
    SideState,
)
from .reconciler import Reconciler, create_reconciler

__all__ = [
    "ActionType",
    "ReconcileAction",
    "SideState",
    "ActualState",
    "DesiredSide",
    "DesiredState",
    "Reconciler",
    "create_reconciler",
]

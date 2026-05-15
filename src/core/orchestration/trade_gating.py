"""Phase 89-α Stage 1: 取引判断 gating

5 分間隔 trigger でも、以下のいずれかに該当しない場合は **取引判断（特徴量計算 + ML 予測 +
戦略評価）をスキップ** して TP/SL 監視のみで終了することで、CPU 課金時間を大幅削減する。

判定基準（早期 reject 順）:
1. **15 分足の完成境界**: 現在分が 00, 15, 30, 45 の ±2 分以内でない → reject
   （bot は 15 分足ベースなので、足が更新されていなければ戦略シグナルも同じ）
2. **同方向ポジ + ポジション数上限**: 既存ポジが新規エントリーをブロックする状態 → reject
   （cooldown / drawdown 判定は既存 trading_cycle_manager に任せる）

設計原則:
- Gating の判定自体を 500ms 以内で済ませる（軽量）
- 取引機会を逃さない（戦略は 15 分足ベース、中間の 5 分 trigger でシグナルは変わらない）
- 既存の取引判断ロジックは一切変更しない（既に同等の判定が trading_cycle_manager で
  行われているのを、入口で先取り評価するだけ）

実測根拠（2026-05-15・24h ログ）:
- 5 分 trigger 実行: 189 回
- 実取引執行: 4 回（6 時間に 1 回）
- 残り 98%（185 回）が「データ取得 → 特徴量 → ML → 取引拒否」で CPU 浪費
- 本 gating で 15分足境界外の 192 回を早期 reject → 重いサイクル発火が 1/3 に
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional

from src.core.logger import get_logger

# 15 分足完成境界（00, 15, 30, 45 分）からの許容ジッター（分）
# Cloud Scheduler の発火ジッターを吸収するため ±2 分
DEFAULT_BOUNDARY_TOLERANCE_MIN = 2


@dataclass
class GatingResult:
    """Gating 判定結果"""

    allowed: bool
    reason: str  # e.g. "ok" / "not_candle_boundary" / "blocked_by_position"
    detail: str = ""  # 追加コンテキスト（ログ出力用）


def check_candle_boundary(
    now: datetime, tolerance_min: int = DEFAULT_BOUNDARY_TOLERANCE_MIN
) -> bool:
    """
    現在時刻が 15 分足の完成境界（00, 15, 30, 45 分の ±tolerance_min 以内）か判定。

    Args:
        now: 判定対象時刻（UTC でも JST でも OK・分の数値のみ参照）
        tolerance_min: 境界からの許容ジッター（default 2 分）

    Returns:
        True: 境界内（取引判断 OK）
        False: 境界外（スキップ）

    例:
        - 07:00 → True (00 分 = 境界 0)
        - 07:01 → True (1 分 = 境界 0 から 1 分以内)
        - 07:13 → True (13 分 = 境界 15 から -2 分以内)
        - 07:14 → True (14 分 = 境界 15 から -1 分以内)
        - 07:17 → True (17 分 = 境界 15 から +2 分以内)
        - 07:18 → False (18 分 = 境界 15 から +3 分・境界 30 から -12 分)
    """
    minute = now.minute
    # 4 つの境界 (0, 15, 30, 45) からの最短距離（巡回考慮: 60 分 = 0 分）
    boundaries = [0, 15, 30, 45, 60]
    min_distance = min(abs(minute - b) for b in boundaries)
    return min_distance <= tolerance_min


def check_position_blocking(margin_positions: List[Any]) -> GatingResult:
    """
    既存ポジションが新規エントリーをブロックする状態か判定。

    判定:
    - 同方向の建玉合計が既に >0 → ブロック（max_same_direction_positions=1 のため）
    - long + short の合計件数が max_open_positions 上限到達 → ブロック

    ただし「ポジションあり = 必ずブロック」ではなく、反対側へのエントリーは可能。
    そのため「同方向制限のみ」では blocking と断定できない（反対方向には開ける）。

    Phase 89-α の方針:
    - long と short の **両方** が既に存在 → 完全にブロック（reject）
    - どちらか片方のみ → 反対方向の取引機会あり（allow）
    - ポジション無し → 全方向に取引可能（allow）

    Args:
        margin_positions: bitbank fetch_margin_positions の戻り値リスト

    Returns:
        GatingResult: allowed=False で reason="blocked_by_position"
    """
    has_long = any(
        (p.get("side") == "long") and (float(p.get("amount") or 0) > 0) for p in margin_positions
    )
    has_short = any(
        (p.get("side") == "short") and (float(p.get("amount") or 0) > 0) for p in margin_positions
    )

    if has_long and has_short:
        return GatingResult(
            allowed=False,
            reason="blocked_by_position",
            detail="long+short 両方の建玉あり（同方向制限 1 で新規不可）",
        )
    # どちらか or ゼロ → 反対方向のエントリー余地あり
    return GatingResult(allowed=True, reason="ok")


async def check_trade_gating(
    now: Optional[datetime] = None,
    margin_positions: Optional[List[Any]] = None,
    tolerance_min: int = DEFAULT_BOUNDARY_TOLERANCE_MIN,
) -> GatingResult:
    """
    Phase 89-α Stage 1: 取引判断の早期 gating。

    `/trigger` ハンドラの最初で呼ばれ、フル取引サイクルを走らせるべきかを判定する。
    判定 NG なら TP/SL 監視のみで終了し、CPU 課金時間を大幅削減する。

    Args:
        now: 判定対象時刻（None で現在時刻）
        margin_positions: 取得済の建玉リスト（None で空扱い）
        tolerance_min: 15 分足境界の許容ジッター（分）

    Returns:
        GatingResult:
            - allowed=True / reason="ok" : フル取引サイクル実行
            - allowed=False / reason="not_candle_boundary" : 15 分足完成タイミング外
            - allowed=False / reason="blocked_by_position" : 既存ポジで新規不可
    """
    logger = get_logger()
    current = now or datetime.now()

    # 1. 15 分足完成境界判定
    if not check_candle_boundary(current, tolerance_min):
        return GatingResult(
            allowed=False,
            reason="not_candle_boundary",
            detail=f"分={current.minute}（境界 00/15/30/45 ±{tolerance_min}分から外れ）",
        )

    # 2. 既存ポジションによるブロック判定
    if margin_positions:
        pos_result = check_position_blocking(margin_positions)
        if not pos_result.allowed:
            return pos_result

    logger.debug(
        f"✅ Phase 89-α Stage 1: gating 通過 (minute={current.minute}, positions={len(margin_positions or [])})"
    )
    return GatingResult(allowed=True, reason="ok")

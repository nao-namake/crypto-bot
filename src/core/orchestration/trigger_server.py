"""
Phase 88 I3: Cloud Scheduler 駆動用 FastAPI アプリ。

設計:
- /trigger (POST): TradingOrchestrator.run_trading_cycle() を 1 回実行 → JSON 返却
- /health (GET):  readiness probe（Firestore 接続確認込み）
- 認証は Cloud Run 側 OIDC で処理（--no-allow-unauthenticated）

bitbank の 5 分間隔取引サイクルを Cloud Run + Cloud Scheduler に移植する。
リクエスト処理中のみ CPU 課金 → idle 時間はメモリのみ課金で GCP 月額を削減。

⚠️ 重要: min_instances=0 を前提とするため、状態は必ず Firestore に永続化されている
こと（Phase 87 H4-H5）。Firestore 接続失敗時は /health が 503 を返し Cloud Run 側
で readiness fail → トラフィック流入停止 → ユーザーが Cloud Logging で即検知する。

Phase R-Hd: FastAPI lifespan で Orchestrator を 1 度だけ初期化して保持。
旧実装は毎リクエストで create_trading_orchestrator + initialize を呼び、cold start 直後
の最初の trigger に 5-8 秒の追加遅延・BitbankClient HTTP session の重複生成・
ML モデルロードの重複が発生していた。

Phase R-Mb: Firestore は「初期化成功」だけでなく実 read/write を試して接続確認。
project ID mismatch・IAM 不足・ネットワーク遮断時に /trigger 初回呼び出しで初めて
503 になるのを防ぎ、起動時に確定させる。
"""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, AsyncIterator, Dict, Optional

from fastapi import FastAPI, HTTPException

from src.core.config import load_config
from src.core.logger import setup_logging
from src.core.orchestration import create_trading_orchestrator
from src.core.orchestration.trade_gating import check_trade_gating
from src.core.persistence.firestore_state import FirestoreStateClient

# モジュールスコープで状態を保持（lifespan 経由で初期化）
_state: Dict[str, Any] = {
    "logger": None,
    "config": None,
    "orchestrator": None,
    "firestore_ok": False,
    "firestore_reason": None,
    "config_reason": None,
}


def _verify_firestore_io(fs_client: FirestoreStateClient, logger) -> tuple:
    """
    Phase R-Mb: Firestore に実 I/O を試して接続を確認する。

    Returns:
        (ok: bool, reason: Optional[str])  reason は失敗時のみ文字列
    """
    if not fs_client.enabled:
        return False, "firestore_client_disabled"
    try:
        # 軽量な save/load/delete で実際の RPC を確認
        ping_payload = {"ts": time.time(), "src": "trigger_server.create_app"}
        if not fs_client.save("health_check", "ping", ping_payload):
            return False, "firestore_save_failed"
        loaded = fs_client.load("health_check", "ping")
        if not isinstance(loaded, dict) or "ts" not in loaded:
            return False, "firestore_load_mismatch"
        # 後始末（失敗してもよい・無視）
        try:
            fs_client.delete("health_check", "ping")
        except Exception:  # pragma: no cover
            pass
        return True, None
    except Exception as e:
        logger.warning(f"⚠️ Phase R-Mb: Firestore I/O 検証で例外: {e}")
        return False, f"firestore_io_exception:{type(e).__name__}"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Phase R-Hd: アプリ起動時に 1 度だけ Orchestrator と Firestore 接続を確立。

    リクエスト処理中のみ CPU 課金される Cloud Run の特性を活かしつつ、
    initialize の重複コスト（BitbankClient session, ML モデルロード等）を削減。
    """
    logger = setup_logging("crypto_bot_trigger")
    _state["logger"] = logger
    logger.info("⚡ Phase 88 I3: lifespan 起動 - Orchestrator/Firestore を初期化")

    # 1. Firestore 接続実体テスト
    fs_client = FirestoreStateClient()
    firestore_ok, firestore_reason = _verify_firestore_io(fs_client, logger)
    _state["firestore_ok"] = firestore_ok
    _state["firestore_reason"] = firestore_reason
    if not firestore_ok:
        logger.critical(
            f"🚨 Phase 88 I3: Firestore I/O 検証失敗 - EMERGENCY_STOP "
            f"(reason={firestore_reason})。/health が 503 を返し、トラフィック流入停止"
        )
    else:
        logger.info("✅ Phase 88 I3: Firestore I/O 検証 OK")

    # 2. 設定ロード
    # Phase 90γ-② fix: cmdline_mode="trigger" は valid_modes (paper/live/backtest) 不一致で
    # ValueError → EMERGENCY_STOP の原因だった。"live" に戻し、WebSocket スキップは
    # orchestrator.py 側で env MODE 環境変数を見て判定する設計に変更。
    config = None
    try:
        config = load_config("config/core/thresholds.yaml", cmdline_mode="live")
        _state["config"] = config
    except Exception as e:
        _state["config_reason"] = f"{type(e).__name__}:{e}"
        logger.critical(f"🚨 Phase 88 I3: 設定読み込み失敗 - EMERGENCY_STOP: {e}")

    # 3. Orchestrator 初期化（Firestore + config がともに OK の場合のみ）
    orchestrator = None
    if firestore_ok and config is not None:
        try:
            orchestrator = await create_trading_orchestrator(config, logger)
            if not await orchestrator.initialize():
                logger.critical("🚨 Phase 88 I3: Orchestrator.initialize() 失敗 - EMERGENCY_STOP")
                orchestrator = None
                _state["config_reason"] = "orchestrator_initialize_failed"
            else:
                logger.info("✅ Phase 88 I3: Orchestrator 初期化 OK（lifespan で保持）")
        except Exception as e:
            logger.critical(f"🚨 Phase 88 I3: Orchestrator 生成失敗: {e}", exc_info=True)
            orchestrator = None
            _state["config_reason"] = f"orchestrator_create_exception:{type(e).__name__}"
    _state["orchestrator"] = orchestrator

    yield  # アプリ稼働中

    logger.info("🛑 Phase 88 I3: lifespan 終了")


def create_app() -> FastAPI:
    """FastAPI アプリ生成。uvicorn でモジュールロード時に1度だけ呼ばれる。"""
    app = FastAPI(title="Crypto Bot Trigger API (Phase 88 I3)", lifespan=lifespan)

    @app.get("/health")
    async def health() -> Dict[str, Any]:
        """Cloud Run readiness probe。Firestore 不通や設定読み込み失敗は 503。"""
        if not _state["firestore_ok"]:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "EMERGENCY_STOP",
                    "reason": _state["firestore_reason"] or "firestore_unavailable",
                },
            )
        if _state["config"] is None or _state["orchestrator"] is None:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "EMERGENCY_STOP",
                    "reason": _state["config_reason"] or "config_or_orchestrator_unavailable",
                },
            )
        return {
            "status": "ok",
            "firestore": True,
            "orchestrator_ready": True,
            "phase": "Phase 88 I3",
        }

    @app.post("/trigger")
    async def trigger() -> Dict[str, Any]:
        """
        Cloud Scheduler から 5 分間隔で呼ばれる。

        Phase 89-α Stage 1: gating で **取引判断スキップが妥当な trigger は monitor_only**
        として軽量実行する。CPU 課金時間を 60-70% 削減する目的。

        判定フロー:
        1. gating（15 分足境界 + 既存ポジ判定）→ NG なら monitor_only
        2. NG: TP/SL 監視のみ（1-3 秒・Phase 87 C5 + Phase 88 H11）
        3. OK: フル取引サイクル（特徴量 → ML → 戦略 → 注文・7-15 秒）

        - 既存 daemon ループ（orchestrator.run()）の代替
        - Orchestrator は lifespan で 1 度だけ初期化済（_state["orchestrator"]）
        """
        logger = _state["logger"]
        orchestrator = _state["orchestrator"]
        if not _state["firestore_ok"]:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "EMERGENCY_STOP",
                    "reason": _state["firestore_reason"] or "firestore_unavailable",
                },
            )
        if orchestrator is None:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "EMERGENCY_STOP",
                    "reason": _state["config_reason"] or "orchestrator_unavailable",
                },
            )

        # Phase 89-α Stage 1: gating 判定（軽量・<1s）
        margin_positions = []
        try:
            bitbank_client = getattr(orchestrator.execution_service, "bitbank_client", None)
            if bitbank_client is not None:
                margin_positions = await bitbank_client.fetch_margin_positions("BTC/JPY")
        except Exception as e:
            # 取得失敗時はポジ無し扱いで gating 続行（取引機会逸失防止）
            if logger:
                logger.warning(f"⚠️ Phase 89-α: margin_positions 取得失敗（gating 続行）: {e}")
            margin_positions = []

        try:
            gating = await check_trade_gating(
                now=datetime.now(),
                margin_positions=margin_positions,
            )
        except Exception as e:
            if logger:
                logger.warning(f"⚠️ Phase 89-α: gating 判定失敗 → フルサイクル fallback: {e}")
            gating = None

        # gating NG → monitor_only で早期 return
        if gating is not None and not gating.allowed:
            if logger:
                logger.warning(
                    f"⏭️ Phase 89-α Stage 1: フル取引判断スキップ "
                    f"(reason={gating.reason}, detail={gating.detail}) → monitor_only"
                )
            try:
                await orchestrator.run_monitor_only()
                return {
                    "status": "monitor_only",
                    "reason": gating.reason,
                    "detail": gating.detail,
                }
            except Exception as e:
                if logger:
                    logger.error(
                        f"❌ Phase 89-α: monitor_only 実行失敗: {e}",
                        exc_info=True,
                    )
                raise HTTPException(
                    status_code=500,
                    detail={"status": "error", "phase": "monitor_only", "error": str(e)},
                )

        # gating OK → フル取引サイクル
        try:
            if logger:
                logger.warning("🎯 Phase 89-α Stage 1: gating 通過 → フル取引サイクル開始")
            await orchestrator.run_trading_cycle()
            return {"status": "success", "cycle_completed": True}
        except Exception as e:
            if logger is not None:
                logger.error(
                    f"❌ Phase 88 I3: trigger 実行失敗: {e}",
                    exc_info=True,
                )
            raise HTTPException(
                status_code=500,
                detail={"status": "error", "error": str(e)},
            )

    return app


# uvicorn 起動時のモジュール参照用（`uvicorn src.core.orchestration.trigger_server:app`）
app = create_app()

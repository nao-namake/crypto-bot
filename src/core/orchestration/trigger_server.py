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

import time
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, Optional

from fastapi import FastAPI, HTTPException

from src.core.config import load_config
from src.core.logger import setup_logging
from src.core.orchestration import create_trading_orchestrator
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

        - 1 リクエスト = 1 取引サイクル（特徴量計算 → ML予測 → 戦略判定 → 注文配置）
        - 既存 daemon ループ（orchestrator.run()）の代替
        - Phase R-Hd: Orchestrator は lifespan で 1 度だけ初期化済（_state["orchestrator"]）
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

        try:
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

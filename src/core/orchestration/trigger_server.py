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
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from src.core.config import load_config
from src.core.logger import setup_logging
from src.core.orchestration import create_trading_orchestrator
from src.core.persistence.firestore_state import FirestoreStateClient


def create_app() -> FastAPI:
    """FastAPI アプリ生成。uvicorn でモジュールロード時に1度だけ呼ばれる。"""
    logger = setup_logging("crypto_bot_trigger")
    app = FastAPI(title="Crypto Bot Trigger API (Phase 88 I3)")

    # 起動時に Firestore 接続を1度だけ検証する（毎リクエストの遅延を回避）
    fs_client = FirestoreStateClient()
    firestore_ok = bool(fs_client.enabled)
    if not firestore_ok:
        logger.critical(
            "🚨 Phase 88 I3: Firestore 不通 - EMERGENCY_STOP "
            "（min_instances=0 ではローカル fallback の state が消失するため運用不可）"
        )
    else:
        logger.info("✅ Phase 88 I3: Firestore 接続確認 OK")

    # 設定は1度だけロードし、リクエスト毎に Orchestrator を都度生成する
    try:
        config = load_config("config/core/thresholds.yaml", cmdline_mode="live")
    except Exception as e:
        # 起動時 fail-fast（health で 503 を返すために state を持つ）
        logger.critical(f"🚨 Phase 88 I3: 設定読み込み失敗 - EMERGENCY_STOP: {e}")
        config = None

    @app.get("/health")
    async def health() -> Dict[str, Any]:
        """Cloud Run readiness probe。Firestore 不通や設定読み込み失敗は 503。"""
        if not firestore_ok:
            raise HTTPException(
                status_code=503,
                detail={"status": "EMERGENCY_STOP", "reason": "firestore_unavailable"},
            )
        if config is None:
            raise HTTPException(
                status_code=503,
                detail={"status": "EMERGENCY_STOP", "reason": "config_load_failed"},
            )
        return {"status": "ok", "firestore": True, "phase": "Phase 88 I3"}

    @app.post("/trigger")
    async def trigger() -> Dict[str, Any]:
        """
        Cloud Scheduler から 5 分間隔で呼ばれる。

        - 1 リクエスト = 1 取引サイクル（特徴量計算 → ML予測 → 戦略判定 → 注文配置）
        - 既存 daemon ループ（orchestrator.run()）の代替
        - 同期処理（リクエスト処理中のみ CPU フル割当 → idle CPU 課金ゼロ）
        """
        if not firestore_ok:
            raise HTTPException(
                status_code=503,
                detail={"status": "EMERGENCY_STOP", "reason": "firestore_unavailable"},
            )
        if config is None:
            raise HTTPException(
                status_code=503,
                detail={"status": "EMERGENCY_STOP", "reason": "config_load_failed"},
            )

        try:
            orchestrator = await create_trading_orchestrator(config, logger)
            if not await orchestrator.initialize():
                raise RuntimeError("orchestrator initialize failed")
            await orchestrator.run_trading_cycle()
            return {"status": "success", "cycle_completed": True}
        except Exception as e:
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

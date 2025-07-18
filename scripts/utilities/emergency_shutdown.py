#!/usr/bin/env python3
"""
緊急時GCPサービス停止スクリプト
予算アラート時に実行してサービスを安全に停止
"""

import logging
import subprocess
import sys

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def emergency_shutdown():
    """緊急時にGCPサービスを停止"""
    try:
        # Cloud Runサービス停止
        logger.info("🚨 Emergency shutdown initiated...")

        # crypto-bot-service-prodを停止
        subprocess.run(
            [
                "gcloud",
                "run",
                "services",
                "update",
                "crypto-bot-service-prod",
                "--region=asia-northeast1",
                "--min-instances=0",
                "--max-instances=0",
                "--cpu=1",
                "--memory=512Mi",
                "--concurrency=1",
                "--no-cpu-throttling",
                "--execution-environment=gen1",
                "--port=8080",
                "--quiet",
            ],
            check=True,
        )

        logger.info("✅ Cloud Run service scaled to 0 instances")

        # アラート通知
        logger.info("📧 Budget exceeded - Services scaled down for cost protection")

        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Emergency shutdown failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error during shutdown: {e}")
        return False


def check_budget_status():
    """予算状況確認"""
    try:
        # 予算状況取得
        result = subprocess.run(
            [
                "gcloud",
                "billing",
                "budgets",
                "list",
                "--billing-account=011DF6-AD4A38-5735FD",
                "--format=value(amount.specifiedAmount.units,displayName)",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        logger.info(f"📊 Budget status: {result.stdout.strip()}")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Budget check failed: {e}")
        return False


if __name__ == "__main__":
    logger.info("🔍 Checking budget status...")
    check_budget_status()

    if len(sys.argv) > 1 and sys.argv[1] == "--shutdown":
        emergency_shutdown()
    else:
        logger.info(
            "💡 To execute emergency shutdown, run: "
            "python emergency_shutdown.py --shutdown"
        )

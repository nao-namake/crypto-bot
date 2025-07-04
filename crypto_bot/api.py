# crypto_bot/api.py
import json
import os
from datetime import datetime

try:
    from fastapi import FastAPI

    FASTAPI_AVAILABLE = True
    app = FastAPI()

    @app.get("/health")
    def health():
        """Enhanced health check with trading bot status"""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": 0,  # Will be updated by actual monitoring
            "region": "unknown",
            "instance_id": "unknown",
            "mode": "testnet-live",  # Updated for live trading
            "version": "1.0.0",
            "is_leader": True,
            "ha_enabled": True,
        }

    @app.get("/healthz")
    def healthz():
        """Provide simple health check for compatibility"""
        return {"status": "ok"}

    @app.get("/trading/status")
    def trading_status():
        """Trading bot status endpoint"""
        try:
            # Try to read trade status from file if exists
            status_file = "/tmp/trading_status.json"
            if os.path.exists(status_file):
                with open(status_file, "r") as f:
                    return json.load(f)
        except Exception:
            pass
        return {
            "status": "running",
            "mode": "testnet-live",
            "exchange": "bybit-testnet",
            "last_update": datetime.now().isoformat(),
            "trades_today": 0,
            "current_position": None,
        }

except ImportError:
    FASTAPI_AVAILABLE = False

    # Create dummy ASGI app for testing compatibility
    class DummyApp:
        def get(self, path):
            def decorator(func):
                return func

            return decorator

        def post(self, path):
            def decorator(func):
                return func

            return decorator

        async def __call__(self, scope, receive, send):
            """Minimal ASGI app implementation for testing"""
            if scope["type"] == "http":
                await send(
                    {
                        "type": "http.response.start",
                        "status": 404,
                        "headers": [[b"content-type", b"application/json"]],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": b'{"detail": "FastAPI not available"}',
                    }
                )

    app = DummyApp()

# crypto_bot/api.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

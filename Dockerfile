# Dockerfile
# Crypto-Bot アプリケーションのDockerイメージを作成
# マルチステージビルドを使い、ランタイム環境を軽量化しています。
# builderステージで依存ライブラリをビルドし、runtimeステージで軽量に実行。

###############################################################################
# builder (wheel-house を作る)
###############################################################################
FROM python:3.11-slim-bullseye AS builder
WORKDIR /build

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# プロジェクト全体をコピー（.dockerignore で不要ファイルは除外）
COPY . .

RUN pip install --upgrade pip \
 # Bot + API 用 extras（fastapi, uvicorn[standard]）を wheel 化
 && pip wheel --no-cache-dir --prefer-binary -w /wheels ".[api]"  \
 && rm -rf ~/.cache/pip

###############################################################################
# runtime
###############################################################################
FROM python:3.11-slim-bullseye
WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends libstdc++6 libgomp1 \
 && rm -rf /var/lib/apt/lists/*

# wheel-house → オフライン install
COPY --from=builder /wheels /tmp/wheels
RUN python -m pip install --no-index --find-links=/tmp/wheels crypto-bot[api] \
 && rm -rf /tmp/wheels

COPY . .

ENV PORT=8080
ENV PYTHONUNBUFFERED=1
EXPOSE 8080

# ──────────────────────────────────────────────
# ① FastAPI で /healthz を提供
# ② Bot 本体を起動
#    → 並列実行用に `&` でバックグラウンド化
# ──────────────────────────────────────────────
CMD uvicorn crypto_bot.api:app --host 0.0.0.0 --port "$PORT" & \
    python -m crypto_bot.main
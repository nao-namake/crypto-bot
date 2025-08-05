# Dockerfile - Ultra-Lightweight Production Build
# Phase 12.2: Container Import Failed根本解決・超軽量化版

FROM python:3.11-slim-bullseye

WORKDIR /app

# 最小限のシステムパッケージのみ
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gcc libc6-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 超軽量requirements（本番最小依存関係のみ）
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    numpy==1.26.4 \
    pandas==1.5.3 \
    scikit-learn==1.3.2 \
    joblib==1.3.2 \
    requests==2.31.0 \
    ccxt==4.4.94 \
    python-dotenv==1.0.0 \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    && rm -rf ~/.cache/pip

# Phase 12.2修正済みアプリケーションコード（最小限）
COPY crypto_bot/ /app/crypto_bot/
COPY config/production/ /app/config/production/
COPY config/core/feature_order.json /app/feature_order.json
COPY models/production/model.pkl /app/models/production/model.pkl
COPY docker/docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# 環境変数設定
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV FEATURE_MODE=lite

EXPOSE 8080

# 軽量ヘルスチェック
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

CMD ["/app/docker-entrypoint.sh"]
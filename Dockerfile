# Phase 53.8 Production Dockerfile
# Python 3.11ダウングレード・99%稼働率達成・GCP環境安定化

FROM python:3.11-slim-bullseye

# メタデータ（Phase 53.8）
LABEL maintainer="crypto-bot-phase53.8-stable-system"
LABEL version="53.8.0"
LABEL description="Phase 53.8: Python 3.11安定化・99%稼働率目標・pandas/gVisor互換性確保"

WORKDIR /app

# システムパッケージ（cmake・libsecp256k1-dev: coincurveビルド対応）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gcc libc6-dev cmake libsecp256k1-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Python依存関係（キャッシュ最適化）
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt && \
    rm -rf ~/.cache/pip

# アプリケーションコード
COPY src/ /app/src/
COPY config/ /app/config/
COPY models/ /app/models/
COPY tax/ /app/tax/
COPY main.py /app/
COPY tests/manual/ /app/tests/manual/

# ログ・キャッシュディレクトリ
RUN mkdir -p /app/.cache/pycache /app/.cache/coverage /app/.cache/pytest /app/cache /app/logs/trading \
    && chmod -R 755 /app/.cache /app/cache /app/logs

# docker-entrypoint.sh（起動スクリプト）
COPY scripts/deployment/docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# 非rootユーザー（セキュリティ強化）
RUN useradd --create-home --shell /bin/bash cryptobot \
    && chown -R cryptobot:cryptobot /app
USER cryptobot

# 環境変数（Phase 52.4-B完了）
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO
ENV FEATURE_MODE=full
ENV PYTHONPYCACHEPREFIX=/app/.cache/pycache

EXPOSE 8080

# ヘルスチェック（30秒間隔）
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# エントリーポイント
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "main.py", "--mode", "paper"]
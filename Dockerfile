# Phase 61 Production Dockerfile
# 戦略分析・コードベース整理・レジーム判定最適化

FROM python:3.13-slim-bullseye

# メタデータ（Phase 61）
LABEL maintainer="crypto-bot-phase61-system"
LABEL version="61.0.0"
LABEL description="Phase 61: 戦略分析・コードベース整理"

WORKDIR /app

# 最小限のシステムパッケージ（統一設定管理体系最適化）
# Phase 51.7 Day 7: cmake・libsecp256k1-dev追加（coincurveビルド対応）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gcc libc6-dev cmake libsecp256k1-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Python依存関係（単一真実源・キャッシュ最適化）
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt && \
    rm -rf ~/.cache/pip

# アプリケーションコード（段階的COPY・最小限）
COPY src/ /app/src/
COPY config/ /app/config/
COPY models/ /app/models/
COPY tax/ /app/tax/
COPY main.py /app/

# ログ・統合キャッシュディレクトリ（統一設定管理体系パターン）
RUN mkdir -p /app/.cache/pycache /app/.cache/coverage /app/.cache/pytest /app/cache /app/logs/trading \
    && chmod -R 755 /app/.cache /app/cache /app/logs

# docker-entrypoint.sh（統一設定管理体系統合機能）
COPY scripts/deployment/docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# 非rootユーザー（セキュリティ強化）
RUN useradd --create-home --shell /bin/bash cryptobot \
    && chown -R cryptobot:cryptobot /app
USER cryptobot

# 環境変数（統一設定管理体系統合・キャッシュ統合対応）
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO
ENV FEATURE_MODE=full
ENV PYTHONPYCACHEPREFIX=/app/.cache/pycache

EXPOSE 8080

# 軽量ヘルスチェック（統一設定管理体系最適化・curl利用）
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# エントリーポイント（統一設定管理体系高度制御）
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "main.py", "--mode", "paper"]
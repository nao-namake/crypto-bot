# Phase 29完了・統一設定管理体系確立完了 Production Dockerfile
# 639テスト100%成功・59.63%カバレッジ・15特徴量統一システム・設定不整合完全解消対応

FROM python:3.13-slim-bullseye

# メタデータ（Phase 29完了・統一設定管理体系確立完了）
LABEL maintainer="crypto-bot-phase29-system"
LABEL version="29.0.0"
LABEL description="Phase 29完了・デプロイ前最終最適化: 統一設定管理体系確立完了・CI/CD・GCP・15特徴量統一システム・設定不整合完全解消"

WORKDIR /app

# 最小限のシステムパッケージ（統一設定管理体系最適化）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gcc libc6-dev \
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
COPY main.py /app/
COPY tests/manual/ /app/tests/manual/

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
# Phase 22: 設定最適化完了・統一システム最適化 Production Dockerfile
# 625テスト・58.64%カバレッジ・15特徴量統一システム・設定最適化完了対応

FROM python:3.13-slim-bullseye

# メタデータ（Phase 22完了）
LABEL maintainer="crypto-bot-phase22"
LABEL version="22.0.0"
LABEL description="Phase 22完了: 設定最適化完了・26キー重複問題解決・15特徴量統一システム・真のシステム性能発揮"

WORKDIR /app

# 最小限のシステムパッケージ（レガシー最適化継承）
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

# ログ・統合キャッシュディレクトリ（Phase 13統合パターン）
RUN mkdir -p /app/.cache/pycache /app/.cache/coverage /app/.cache/pytest /app/cache /app/logs/trading \
    && chmod -R 755 /app/.cache /app/cache /app/logs

# docker-entrypoint.sh（レガシー統合機能継承）
COPY scripts/deployment/docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# 非rootユーザー（セキュリティ強化）
RUN useradd --create-home --shell /bin/bash cryptobot \
    && chown -R cryptobot:cryptobot /app
USER cryptobot

# 環境変数（レガシー＋新システム統合・キャッシュ統合対応）
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO
ENV FEATURE_MODE=full
ENV PYTHONPYCACHEPREFIX=/app/.cache/pycache

EXPOSE 8080

# 軽量ヘルスチェック（レガシー最適化継承・curl利用）
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# エントリーポイント（レガシー高度制御継承）
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "main.py", "--mode", "paper"]
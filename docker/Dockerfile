# Dockerfile - Ultra-Lightweight Production Build
# Phase 12.5: Environment Parity & Dependency Management System
# 単一真実源dependencies・手動管理排除・環境統一実現

FROM python:3.11-slim-bullseye

WORKDIR /app

# 最小限のシステムパッケージのみ
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gcc libc6-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Phase 12.5: 本番最小依存関係（単一真実源・手動管理排除）
COPY requirements/base.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt && \
    rm -rf ~/.cache/pip

# Phase 12.2修正済みアプリケーションコード（最小限）
COPY crypto_bot/ /app/crypto_bot/
COPY config/production/ /app/config/production/
COPY config/core/feature_order.json /app/feature_order.json
COPY models/production/ /app/models/production/

# 初期データキャッシュをコピー（Phase 18: CI環境対応）
# キャッシュディレクトリを作成
RUN mkdir -p /app/cache

# 168時間事前取得データキャッシュをコピー
COPY cache/initial_data_168h.pkl /app/cache/initial_data_168h.pkl
COPY cache/initial_features_168h.pkl /app/cache/initial_features_168h.pkl

# cache/ディレクトリが存在する場合はコピー、なければスキップ
# CI環境ではワークフローで事前作成されたダミーファイルをコピー
COPY cache/ /app/cache/

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
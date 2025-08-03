# Dockerfile - Simplified Single Stage Build
FROM python:3.11-slim-bullseye

WORKDIR /app

# システムパッケージのインストール
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential git ca-certificates libstdc++6 libgomp1 \
 && rm -rf /var/lib/apt/lists/*

# Pythonパッケージのアップグレード
RUN pip install --upgrade pip

# 依存関係ファイルをコピー
COPY requirements-dev.txt ./

# 依存関係をインストール
RUN pip install --no-cache-dir -r requirements-dev.txt \
 && rm -rf ~/.cache/pip

# アプリケーションコードをコピー
COPY crypto_bot/ /app/crypto_bot/
COPY scripts/ /app/scripts/
COPY config/ /app/config/
COPY models/ /app/models/
COPY config/core/feature_order.json /app/feature_order.json
COPY .env.example /app/

# 環境変数設定
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
# デフォルトは軽量モードで起動（高速初期化）
ENV FEATURE_MODE=lite

EXPOSE 8080

# ヘルスチェック（初期化状況確認）
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=5 \
  CMD curl -f http://localhost:8080/health || exit 1

# Live Trading + API Server Mode (Phase H.28 Compatible)
# 本番環境・CI環境ともにAPIサーバー統合実行
# MODE環境変数でライブトレード統合制御
COPY docker/docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh
CMD ["/app/docker-entrypoint.sh"]
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
COPY .env.example /app/

# モデルディレクトリを作成（実行時にモデルファイルが配置される）
RUN mkdir -p /app/model

# 環境変数設定
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 8080

# Live Trading + API Server Mode (Bybit Testnet)
CMD ["python", "scripts/start_live_with_api.py"]
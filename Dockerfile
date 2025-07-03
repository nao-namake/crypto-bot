# Dockerfile
# Crypto-Bot アプリケーションのDockerイメージを作成
# マルチステージビルドを使い、ランタイム環境を軽量化しています。
# builderステージで依存ライブラリをビルドし、runtimeステージで軽量に実行。

###############################################################################
# builder (wheel-house を作る)
###############################################################################
FROM python:3.11-slim-bullseye AS builder
WORKDIR /build

# キャッシュ効率向上：システムパッケージを最初にインストール
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# キャッシュ効率向上：依存関係ファイルを先にコピー
COPY pyproject.toml setup.py requirements*.txt ./

# 依存関係の事前インストール（キャッシュ最適化）
RUN pip install --upgrade pip \
 && pip install --no-cache-dir build wheel

# プロジェクト全体をコピー（.dockerignore で不要ファイルは除外）
COPY . .

# wheelビルド（一度だけ実行）
RUN pip wheel --no-cache-dir --prefer-binary -w /wheels ".[api]" \
 && rm -rf ~/.cache/pip

###############################################################################
# runtime
###############################################################################
FROM python:3.11-slim-bullseye
WORKDIR /app

# キャッシュ効率向上：ランタイム依存関係を最初にインストール
RUN apt-get update \
 && apt-get install -y --no-install-recommends libstdc++6 libgomp1 \
 && rm -rf /var/lib/apt/lists/*

# wheel-house → オフライン install（キャッシュ最適化）
COPY --from=builder /wheels /tmp/wheels
RUN python -m pip install --no-index --find-links=/tmp/wheels crypto-bot[api] \
 && rm -rf /tmp/wheels

# 設定ファイルを先にコピー（頻繁な変更を避けるため）
COPY config/ /app/config/
COPY .env.example /app/

# アプリケーションコードをコピー（最後に配置してキャッシュ効率向上）
COPY crypto_bot/ /app/crypto_bot/
COPY scripts/ /app/scripts/

# MLモデルディレクトリ（存在しない場合は空ディレクトリを作成）
RUN mkdir -p /app/model

ENV PORT=8080
ENV PYTHONUNBUFFERED=1
EXPOSE 8080

# ──────────────────────────────────────────────
# Live Trading + API Server Mode (Bybit Testnet)
# ──────────────────────────────────────────────
CMD ["python", "scripts/start_live_with_api.py"]
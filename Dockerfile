# Dockerfile
# Crypto-Bot アプリケーションのDockerイメージを作成
# マルチステージビルドを使い、ランタイム環境を軽量化しています。
# builderステージで依存ライブラリをビルドし、runtimeステージで軽量に実行。

###############################################################################
# builder stage – wheel-house を作る
###############################################################################
FROM python:3.11-slim-bullseye AS builder
WORKDIR /build

# ネイティブ拡張ビルド用ツール（numpy/scipy など）
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# プロジェクト全体をコピー（.dockerignore で不要ファイルは除外）
COPY . .

RUN pip install --upgrade pip \
 && pip wheel --no-cache-dir --prefer-binary -w /wheels /build

###############################################################################
# runtime stage – wheel-house からオフライン install
###############################################################################
FROM python:3.11-slim-bullseye
WORKDIR /app

# ランタイムに必要な共有ライブラリのみをインストール
RUN apt-get update \
 && apt-get install -y --no-install-recommends libstdc++6 libgomp1 \
 && rm -rf /var/lib/apt/lists/*

# wheel-house をコピーしてオフラインでインストール
COPY --from=builder /wheels /tmp/wheels
RUN python -m pip install --no-index --find-links=/tmp/wheels crypto-bot \
 && rm -rf /tmp/wheels

# アプリケーションソースコードをコピー
COPY . .

ENV PORT=8080
ENV PYTHONUNBUFFERED=1
EXPOSE 8080

# Bot 本体を起動
CMD ["python", "-m", "crypto_bot.main"]
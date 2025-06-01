###############################################################################
# builder stage – wheel-house を作る
###############################################################################
FROM python:3.11-slim-bullseye AS builder
WORKDIR /build

# ネイティブ拡張ビルド用ツール（numpy/scipy など）
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# pyproject.toml だけで wheel を作る
COPY pyproject.toml ./

RUN pip install --upgrade pip \
 # プロジェクト & 依存すべてを wheel 化して /wheels へ
 && pip wheel --no-cache-dir --prefer-binary -w /wheels .

###############################################################################
# runtime stage – wheel-house からオフライン install
###############################################################################
FROM python:3.11-slim-bullseye
WORKDIR /app

# ランタイムに必要な共有ライブラリだけ
RUN apt-get update \
 && apt-get install -y --no-install-recommends libstdc++6 libgomp1 \
 && rm -rf /var/lib/apt/lists/*

# wheel-house をコピーしてオフラインインストール
COPY --from=builder /wheels /tmp/wheels
RUN python -m pip install --no-index --find-links=/tmp/wheels crypto-bot \
 && rm -rf /tmp/wheels

# アプリケーションソース
COPY . .

ENTRYPOINT ["python", "-m", "crypto_bot.main"]

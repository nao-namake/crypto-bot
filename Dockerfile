# ベースイメージ
FROM python:3.11-slim-bullseye

# 作業ディレクトリ
WORKDIR /app

# システムビルドツールをインストール
RUN apt-get update \
    && apt-get install -y build-essential wget ca-certificates autoconf automake libtool pkg-config git \
    && rm -rf /var/lib/apt/lists/*

# --- build latest TA‑Lib from GitHub ---
RUN git clone --depth 1 https://github.com/ta-lib/ta-lib.git \
    && cd ta-lib \
    && chmod +x autogen.sh \
    && ./autogen.sh \
    && ./configure --prefix=/usr \
    && make -j$(nproc) \
    && make install \
    && ldconfig \
    # TA‑Lib installs libta_lib.so, while the Python wheel looks for libta-lib.so.
    && LIBFILE="$(ldconfig -p | awk '/libta_lib\.so/{print $NF; exit}')" \
    && LIBDIR="$(dirname "${LIBFILE}")" \
    && [ -e "${LIBDIR}/libta-lib.so" ] || ln -s "${LIBFILE}" "${LIBDIR}/libta-lib.so" \
    && cd .. \
    && rm -rf ta-lib

# ソースコードをコピー
COPY . .

# TA-Lib の Python ラッパーをインストール
RUN pip install --no-cache-dir TA-Lib

# プロジェクト本体と開発用依存をインストール
RUN pip install --no-cache-dir -U pip \
    && pip install --no-cache-dir -e . \
    && pip install --no-cache-dir -r requirements-dev.txt

# コンテナ起動時に実行するコマンド
ENTRYPOINT ["python", "-m", "crypto_bot.main"]
#!/usr/bin/env bash
# =============================================================================
# ファイル名: docker/run_docker.sh
# 説明:
#   - Dockerコンテナ上でcrypto-botコマンドを実行
#   - 任意の引数を渡して汎用的に使えるラッパー
#   - .envファイルからAPIキー等の環境変数を読み込み
#   - バックテスト、最適化、学習など用途を選ばず利用可能
#   - 例: bash docker/run_docker.sh backtest --config config/default.yml
# =============================================================================
set -euo pipefail

# docker/フォルダ統合後のパス調整（プロジェクトルートに移動）
cd "$(dirname "$0")/.." || exit 1

if [ ! -f .env ]; then
  echo "[ERROR] .envファイルがありません。APIキー等を記入してください。"
  exit 1
fi

echo "=== Dockerコンテナ起動: $* ==="
docker run --rm --env-file .env crypto-bot:latest "$@"
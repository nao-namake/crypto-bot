#!/usr/bin/env bash
# =============================================================================
# ファイル名: scripts/build_docker.sh
# 説明:
#   - Dockerイメージ（crypto-bot:latest）をビルド
#   - builderステージでwheel-houseを構築し、runtimeへコピー
#   - イメージはPython 3.11ベース、依存パッケージもwheel化で高速化
#   - ビルドログやエラーは標準出力に表示
# =============================================================================
set -euo pipefail

echo "=== Dockerイメージのビルド開始 ==="
# docker/フォルダ統合後のパス調整（プロジェクトルートから実行）
cd "$(dirname "$0")/.." || exit 1
docker build -f docker/Dockerfile -t crypto-bot:latest .
echo "=== ビルド完了: イメージ名 = crypto-bot:latest ==="
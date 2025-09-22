#!/bin/bash

# Python実行ヘルパースクリプト
# run_safe.shから呼び出される簡易Python実行スクリプト

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# プロジェクトディレクトリに移動
cd "$PROJECT_ROOT"

# 環境変数設定
export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/src:${PYTHONPATH:-}"
export PYTHONUNBUFFERED=1

# main.py実行
exec python3 main.py "$@"
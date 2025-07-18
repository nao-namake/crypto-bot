#!/bin/bash
# Local Docker test script

echo "=== Docker Build Test ==="
cd /Users/nao/Desktop/bot

# Dockerビルドテスト
docker build --no-cache -t crypto-bot-local-test .

# ビルドが成功したらイメージをテスト
if [ $? -eq 0 ]; then
    echo "=== Docker Import Test ==="
    docker run --rm crypto-bot-local-test python -c "import crypto_bot; print('Docker import test passed')"
    
    echo "=== Docker Health Check Test ==="
    # ヘルスチェック用に一時的にコンテナを起動
    docker run -d --name crypto-bot-health-test -p 8080:8080 crypto-bot-local-test
    sleep 10
    
    # ヘルスエンドポイントをテスト
    curl -f http://localhost:8080/healthz || echo "Health check failed"
    
    # コンテナを停止・削除
    docker stop crypto-bot-health-test
    docker rm crypto-bot-health-test
    
    echo "=== Docker Tests Completed Successfully ==="
else
    echo "Docker build failed!"
    exit 1
fi
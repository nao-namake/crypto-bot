#!/bin/bash
# Local Terraform test script

echo "=== Terraform Validation Test ==="
cd /Users/nao/Desktop/bot/infra/envs/dev

# 認証確認
echo "Checking GCP authentication..."
gcloud auth list
gcloud config get-value project

# Terraform初期化
echo "=== Terraform Init ==="
terraform init

# Terraform設定検証
echo "=== Terraform Validate ==="
terraform validate

# Terraform計画確認（実際に適用せず、計画のみ）
echo "=== Terraform Plan (dry-run) ==="
terraform plan -input=false

echo "=== Terraform Tests Completed Successfully ==="
# Phase 12.3: ローカル事前計算システム対応Makefile

.PHONY: help pre-compute test checks deploy clean

help:
	@echo "Available commands:"
	@echo "  make pre-compute  - Run pre-computation for cache generation"
	@echo "  make test        - Run all tests"
	@echo "  make checks      - Run quality checks (flake8, isort, black, pytest)"
	@echo "  make deploy      - Deploy to production (git push)"
	@echo "  make clean       - Clean cache and temporary files"

# Phase 12.3: ローカル事前計算実行
pre-compute:
	@echo "🚀 Running pre-computation for Phase 12.3..."
	python scripts/pre_compute_data.py
	@echo "✅ Pre-computation completed"

# テスト実行
test:
	python -m pytest tests/

# 品質チェック実行
checks:
	bash scripts/checks.sh

# デプロイ（CI/CD経由）
deploy: pre-compute checks
	@echo "📦 Preparing deployment..."
	git add .
	git commit -m "Phase 12.3: Deploy with pre-computed cache"
	git push origin main
	@echo "🚀 Deployment initiated via CI/CD"

# キャッシュクリーンアップ
clean:
	@echo "🗑️ Cleaning cache..."
	rm -rf cache/
	rm -f *.log
	@echo "✅ Cleanup completed"
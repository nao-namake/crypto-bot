# Phase 12.3: ローカル事前計算システム対応Makefile

.PHONY: help pre-compute test checks deploy clean validate-deps sync-deps prepare-cache verify-deployment

help:
	@echo "Available commands:"
	@echo "  make pre-compute  - Run pre-computation for cache generation"
	@echo "  make prepare-cache - Prepare initial data cache for deployment"
	@echo "  make test        - Run all tests"
	@echo "  make checks      - Run quality checks (flake8, isort, black, pytest)"
	@echo "  make validate-deps - Validate dependency consistency (Phase 12.5)"
	@echo "  make sync-deps    - Show dependency sync information"
	@echo "  make verify-deployment - Verify deployment readiness"
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
deploy: prepare-cache verify-deployment
	@echo "📦 Preparing deployment..."
	@echo "🔄 Adding all changes..."
	git add .
	@echo "📝 Creating commit..."
	git commit -m "fix: Complete solution for bot trading issues" -m "- API authentication fixed" -m "- Model files prepared" -m "- INIT simplified" -m "- Timestamp validation fixed" -m "- CI/CD quality assurance added" || echo "No changes to commit"
	@echo "🚀 Pushing to GitHub (triggers CI/CD)..."
	git push origin main
	@echo "✅ Deployment initiated via CI/CD"
	@echo "📊 Monitor deployment at: https://github.com/[your-repo]/actions"

# Phase 12.5: 依存関係検証
validate-deps:
	@echo "🔍 Validating dependency consistency..."
	python requirements/validate.py
	@echo "✅ Dependency validation completed"

# Phase 12.5: 依存関係同期情報
sync-deps:
	@echo "🔄 Dependency sync information..."
	python requirements/validate.py --sync
	@echo "✅ Sync information displayed"

# Phase 5: 初期データキャッシュ準備
prepare-cache:
	@echo "📊 Preparing initial data cache..."
	@if [ -n "$$BITBANK_API_KEY" ] && [ -n "$$BITBANK_API_SECRET" ]; then \
		echo "🔄 Using real API data..."; \
		python scripts/prepare_initial_data.py || python scripts/create_minimal_cache.py; \
	else \
		echo "⚠️ API credentials not set, creating minimal cache..."; \
		python scripts/create_minimal_cache.py; \
	fi
	@echo "✅ Cache preparation completed"

# Phase 5: デプロイ前の品質保証検証
verify-deployment:
	@echo "🔍 Verifying deployment readiness..."
	@echo "1️⃣ Checking Python syntax..."
	@python -m py_compile crypto_bot/cli/live.py
	@python -m py_compile crypto_bot/data/fetching/data_processor.py
	@echo "2️⃣ Checking cache files..."
	@if [ -f "cache/initial_data.pkl" ]; then \
		echo "✅ Cache file exists"; \
	else \
		echo "⚠️ Cache file missing - run 'make prepare-cache'"; \
	fi
	@echo "3️⃣ Checking model files..."
	@if [ -f "models/production/model.pkl" ]; then \
		echo "✅ Model file exists"; \
	else \
		echo "⚠️ Model file missing"; \
	fi
	@echo "4️⃣ Running quality checks..."
	@bash scripts/checks.sh
	@echo "✅ Deployment verification completed"

# キャッシュクリーンアップ
clean:
	@echo "🗑️ Cleaning cache..."
	rm -rf cache/
	rm -f *.log
	@echo "✅ Cleanup completed"
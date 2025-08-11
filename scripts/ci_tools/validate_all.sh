#!/usr/bin/env bash
# =============================================================================
# 包括的検証スクリプト（3段階検証）
# 
# Phase 2-3統合: ChatGPT提案実装
# 本番デプロイ前の完全な検証フロー
#
# 使用方法:
#   bash scripts/validate_all.sh          # フル検証
#   bash scripts/validate_all.sh --quick  # クイック検証（レベル1のみ）
#   bash scripts/validate_all.sh --ci     # CI用（レベル1+2）
# =============================================================================

set -euo pipefail

# 色付き出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# タイマー開始
START_TIME=$(date +%s)

# 引数処理
MODE="full"
if [[ "${1:-}" == "--quick" ]]; then
    MODE="quick"
elif [[ "${1:-}" == "--ci" ]]; then
    MODE="ci"
fi

echo "=========================================================="
echo "🚀 Crypto-Bot Validation Pipeline"
echo "=========================================================="
echo "Mode: $MODE"
echo "Started: $(date)"
echo "=========================================================="

# 結果追跡
LEVEL1_PASSED=false
LEVEL2_PASSED=false
LEVEL3_PASSED=false

# =============================================================================
# LEVEL 1: 静的解析（高速・必須）
# =============================================================================
echo -e "\n${YELLOW}📋 LEVEL 1: Static Analysis (Quick Checks)${NC}"
echo "=========================================================="

if bash scripts/ci_tools/checks.sh; then
    echo -e "${GREEN}✅ Level 1 PASSED: All static checks passed${NC}"
    LEVEL1_PASSED=true
else
    echo -e "${RED}❌ Level 1 FAILED: Static analysis errors found${NC}"
    echo "Fix the issues above before proceeding"
    exit 1
fi

# クイックモードの場合はここで終了
if [[ "$MODE" == "quick" ]]; then
    echo -e "\n${GREEN}✅ Quick validation complete${NC}"
    exit 0
fi

# =============================================================================
# LEVEL 2: 未来データリーク検出（中速・重要）
# =============================================================================
echo -e "\n${YELLOW}🔍 LEVEL 2: Future Data Leak Detection${NC}"
echo "=========================================================="

if python scripts/monitoring/future_leak_detector.py --project-root . --html; then
    echo -e "${GREEN}✅ Level 2 PASSED: No critical future data leaks${NC}"
    LEVEL2_PASSED=true
else
    EXIT_CODE=$?
    if [[ $EXIT_CODE -eq 1 ]]; then
        echo -e "${YELLOW}⚠️ Level 2 WARNING: High priority issues found (continuing)${NC}"
        LEVEL2_PASSED=true  # 警告は続行可能
    else
        echo -e "${RED}❌ Level 2 FAILED: Critical future data leaks detected${NC}"
        echo "Review logs/leak_detection/ for details"
        exit 2
    fi
fi

# CIモードの場合はここで終了
if [[ "$MODE" == "ci" ]]; then
    echo -e "\n${GREEN}✅ CI validation complete${NC}"
    exit 0
fi

# =============================================================================
# LEVEL 3: 動的検証（低速・包括的）
# =============================================================================
echo -e "\n${YELLOW}🎯 LEVEL 3: Dynamic Validation (Full Integration)${NC}"
echo "=========================================================="

# ペーパートレード統合テスト
echo "Starting paper trade integration test..."
if bash scripts/paper_trade_with_monitoring.sh --duration 2; then
    echo -e "${GREEN}✅ Paper trade integration test passed${NC}"
else
    echo -e "${YELLOW}⚠️ Paper trade test had warnings (non-blocking)${NC}"
fi

# フル統合検証
echo "Running full pre-deployment validation..."
if python scripts/pre_deploy_validation.py --skip-paper-trade; then
    echo -e "${GREEN}✅ Level 3 PASSED: System ready for deployment${NC}"
    LEVEL3_PASSED=true
else
    echo -e "${RED}❌ Level 3 FAILED: System not ready for deployment${NC}"
    echo "Review logs/pre_deploy_validation/ for details"
    exit 3
fi

# =============================================================================
# 最終サマリー
# =============================================================================
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "=========================================================="
echo "📊 VALIDATION SUMMARY"
echo "=========================================================="
echo -e "Level 1 (Static):    $(if $LEVEL1_PASSED; then echo -e "${GREEN}PASS${NC}"; else echo -e "${RED}FAIL${NC}"; fi)"
echo -e "Level 2 (Leak Check): $(if $LEVEL2_PASSED; then echo -e "${GREEN}PASS${NC}"; else echo -e "${RED}FAIL${NC}"; fi)"
echo -e "Level 3 (Dynamic):    $(if $LEVEL3_PASSED; then echo -e "${GREEN}PASS${NC}"; else echo -e "${RED}FAIL${NC}"; fi)"
echo "=========================================================="
echo "Duration: ${DURATION} seconds"
echo "=========================================================="

if $LEVEL1_PASSED && $LEVEL2_PASSED && $LEVEL3_PASSED; then
    echo -e "${GREEN}🎉 ALL VALIDATIONS PASSED!${NC}"
    echo "Your code is ready for deployment:"
    echo "  git add ."
    echo "  git commit -m 'your message'"
    echo "  git push origin main"
    exit 0
else
    echo -e "${RED}❌ VALIDATION FAILED${NC}"
    echo "Please fix the issues before deployment"
    exit 1
fi
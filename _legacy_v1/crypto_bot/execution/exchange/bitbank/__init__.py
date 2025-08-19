"""
Bitbank Execution Exchange Module - Phase 16.2-A Integration

Bitbank取引所専用の統合実行モジュール。
6つの分散実行ファイルを2つの統合ファイルに集約。

統合前 (6ファイル - 3,323行):
├── bitbank_client.py (196行)
├── bitbank_api_rate_limiter.py (473行)
├── bitbank_order_manager.py (605行)
├── bitbank_fee_optimizer.py (514行)
├── bitbank_fee_guard.py (560行)
└── bitbank_execution_efficiency_optimizer.py (975行)

統合後 (2ファイル):
├── core_execution.py - 基本実行機能統合 (1,274行統合)
└── optimization.py - 最適化機能統合 (2,049行統合)

Usage:
    from crypto_bot.execution.exchange.bitbank import core_execution
    from crypto_bot.execution.exchange.bitbank import optimization

    # または個別インポート
    from crypto_bot.execution.exchange.bitbank.core_execution import RateLimitType
    from crypto_bot.execution.exchange.bitbank.optimization import FeeStrategy

Phase 16.2-A実装: 2025年8月8日
統合効果: ファイル数67%削減（6→2）、保守性向上
"""

# Phase 16.15: 統合作業中のため一時的にimport無効化
# 統合完了後にすべてのクラスをexport予定
# from .core_execution import (
#     OrderStatus,
#     OrderType,
#     RateLimitStatus,
#     RateLimitType,
# )
# from .optimization import (
#     EfficiencyMetric,
#     FeeAlertType,
#     FeeOptimizationMode,
#     FeeStrategy,
#     GuardLevel,
#     OptimizationTarget,
# )

__version__ = "16.2.0"
__author__ = "Phase 16.2-A Integration"
__description__ = "Bitbank Integrated Execution Module"

# 統合状況
INTEGRATION_STATUS = {
    "phase": "16.2-A",
    "core_execution_progress": "基本構造完了・段階統合中",
    "optimization_progress": "基本構造完了・段階統合中",
    "files_integrated": "6 → 2",
    "lines_total": "3,323行",
    "completion_target": "Phase 16.3で完全統合完了予定",
}

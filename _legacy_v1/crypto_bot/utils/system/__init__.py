"""
Utils System Module - Phase 16.2-B Integration

utils/system/ 統合システムモジュール。
重複ファイルを統合し、システム機能を一元化。

統合前 (4ファイル - 1,088行):
├── logger.py (423行) - JSON構造化ログフォーマッタ
├── logging.py (51行) - 基本ログ設定
├── status.py (38行) - 基本ステータス管理
└── enhanced_status_manager.py (576行) - 拡張ステータス管理

統合後 (2ファイル):
├── logging_system.py - ログシステム統合 (474行統合)
└── status_manager.py - ステータス管理統合 (614行統合)

Usage:
    # ログシステム
    from crypto_bot.utils.system.logging_system import setup_logging, get_structured_logger

    # ステータス管理
    from crypto_bot.utils.system.status_manager import update_bot_status, get_enhanced_status_manager

    # 個別インポート
    from crypto_bot.utils.system import logging_system, status_manager

Phase 16.2-B実装: 2025年8月8日
統合効果: ファイル数50%削減（4→2）、機能統一
"""

# Phase 16.15: 統合作業中のため一時的にimport無効化
# 統合完了後にすべての機能をexport予定

# メインのエントリポイントのみ提供
from .logging_system import get_structured_logger, setup_logging
from .status_manager import get_enhanced_status_manager

__version__ = "16.2.0"
__author__ = "Phase 16.2-B Integration"
__description__ = "Utils System Integration Module"

# 統合状況
INTEGRATION_STATUS = {
    "phase": "16.2-B",
    "logging_progress": "完全統合完了",
    "status_progress": "完全統合完了",
    "files_integrated": "4 → 2",
    "lines_total": "1,088行",
    "reduction_achieved": "50%削減",
}


# 便利関数
def initialize_system(
    log_level: str = "INFO",
    log_format: str = "standard",
    enable_enhanced_status: bool = True,
) -> tuple:
    """システム初期化 - ログ・ステータス統合セットアップ

    Returns:
        tuple: (logger, status_manager)
    """
    # ログシステム初期化
    setup_logging(level=log_level, format_type=log_format)
    logger = get_structured_logger(__name__)

    # ステータスマネージャー初期化
    status_manager = None
    if enable_enhanced_status:
        status_manager = get_enhanced_status_manager()

    logger.info("System integration modules initialized successfully")

    return logger, status_manager

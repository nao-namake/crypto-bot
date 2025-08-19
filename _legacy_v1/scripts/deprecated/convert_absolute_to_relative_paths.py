#!/usr/bin/env python3
"""
パス統一スクリプト - 絶対パス→相対パス変換

Phase 14.6: データパス管理統一・保守性向上実施
- 絶対パス参照を相対パスに統一変換
- /Users/nao/Desktop/bot/data/ → data/ 変換
- 設定ファイル化対応・環境依存除去
"""

import re
from pathlib import Path
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def convert_paths_in_files():
    """絶対パス→相対パス変換実行"""
    
    logger.info("🔄 絶対パス→相対パス変換開始")
    
    # 対象ファイルリスト (検索結果から特定)
    target_files = [
        "crypto_bot/strategy/multi_timeframe_ensemble.py",
        "scripts/retrain_125_features_model.py",
        "scripts/optimize_confidence_threshold.py", 
        "scripts/retrain_124_features_model.py",
        "scripts/simple_97_feature_flow.py",
        "scripts/quick_feature_comparison.py",
        "scripts/hybrid_backtest_approach.py",
        "scripts/lightweight_feature_backtest.py",
        "scripts/monthly_walkforward_backtest.py",
        "scripts/retrain_125_features_system_model.py",
        "scripts/deployment_issue_validator.py",
        "scripts/create_127_features_model.py",
        "scripts/create_realistic_features_model.py",
        "scripts/diagnose_real_data_features.py",
        "scripts/simple_backtest_validation.py",
        "scripts/performance_comparison_test.py",
        "scripts/ml_integration_system_test.py",
        "scripts/feature_integrity_quality_test.py",
        "scripts/ensemble_ab_testing_system.py"
    ]
    
    # 変換パターン定義
    patterns = [
        # 絶対パス → 相対パス
        (
            r'/Users/nao/Desktop/bot/data/btc_usd_2024_hourly\.csv',
            'data/btc_usd_2024_hourly.csv'
        ),
        (
            r'"/Users/nao/Desktop/bot/data/btc_usd_2024_hourly\.csv"',
            '"data/btc_usd_2024_hourly.csv"'
        ),
        # Path オブジェクト対応
        (
            r'Path\("/Users/nao/Desktop/bot/data/btc_usd_2024_hourly\.csv"\)',
            'Path("data/btc_usd_2024_hourly.csv")'
        ),
        (
            r'Path\(\'data/btc_usd_2024_hourly\.csv\'\)',
            'Path("data/btc_usd_2024_hourly.csv")'
        )
    ]
    
    converted_files = []
    total_replacements = 0
    
    for file_path_str in target_files:
        file_path = Path(file_path_str)
        
        if not file_path.exists():
            logger.warning(f"⚠️ ファイル未発見: {file_path}")
            continue
            
        logger.info(f"🔧 処理中: {file_path}")
        
        try:
            # ファイル読み込み
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            file_replacements = 0
            
            # パターン変換実行
            for pattern, replacement in patterns:
                matches = re.findall(pattern, content)
                if matches:
                    content = re.sub(pattern, replacement, content)
                    file_replacements += len(matches)
                    logger.info(f"  🔄 変換: {pattern} → {replacement} ({len(matches)}回)")
            
            # 変更があった場合のみファイル更新
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                converted_files.append(str(file_path))
                total_replacements += file_replacements
                logger.info(f"  ✅ 更新完了: {file_replacements}箇所")
            else:
                logger.info(f"  ➡️ 変更なし")
                
        except Exception as e:
            logger.error(f"❌ ファイル処理エラー: {file_path} - {e}")
    
    logger.info("✅ 絶対パス→相対パス変換完了")
    logger.info(f"📊 変換ファイル数: {len(converted_files)}")
    logger.info(f"📊 総変換箇所: {total_replacements}")
    
    if converted_files:
        logger.info("📝 変換済みファイル:")
        for file_path in converted_files:
            logger.info(f"  - {file_path}")
    
    return {
        "converted_files": converted_files,
        "total_replacements": total_replacements,
        "success": True
    }


def create_data_path_config():
    """データパス設定ファイル作成"""
    
    logger.info("⚙️ データパス設定ファイル作成")
    
    config_content = '''# data_paths.yml - データパス設定統一管理
# Phase 14.6: パス管理統一・環境依存除去

# メインデータファイルパス
main_data:
  btc_usd_hourly: "data/btc_usd_2024_hourly.csv"
  backup_pattern: "data/btc_usd_2024_hourly_backup_*.csv"

# 将来拡張データパス
historical_data:
  btc_usd_2023: "data/historical/btc_usd_2023_hourly.csv"
  btc_usd_2022: "data/historical/btc_usd_2022_hourly.csv"

# 処理済みデータパス  
processed_data:
  features_97: "data/processed/features_97_processed.pkl"
  ml_ready: "data/processed/ml_ready_dataset.pkl"

# 環境変数対応
environment:
  data_root: "${DATA_ROOT:-data}"
  backup_root: "${BACKUP_ROOT:-data}"

# 品質設定
data_quality:
  max_price: 150000
  min_price: 10000
  max_volume: 100000
  backup_retention_days: 30
'''
    
    config_path = Path("config/core/data_paths.yml")
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        logger.info(f"✅ 設定ファイル作成: {config_path}")
        return str(config_path)
        
    except Exception as e:
        logger.error(f"❌ 設定ファイル作成エラー: {e}")
        return None


if __name__ == "__main__":
    try:
        # 1. 絶対パス→相対パス変換
        path_result = convert_paths_in_files()
        
        # 2. データパス設定ファイル作成
        config_path = create_data_path_config()
        
        print(f"\n🎊 パス統一処理完了!")
        print(f"📊 変換ファイル数: {path_result['total_replacements']}")
        print(f"⚙️ 設定ファイル: {config_path}")
        
    except Exception as e:
        logger.error(f"❌ パス統一処理失敗: {e}")
        raise
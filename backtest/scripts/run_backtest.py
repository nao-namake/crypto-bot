#!/usr/bin/env python3
"""
バックテスト実行ヘルパー
固定ファイル名・絶対パスでバックテストを簡単実行
"""

import argparse
import logging
import sys
from pathlib import Path

# プロジェクトルートに移動
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crypto_bot.main import main as crypto_main

logger = logging.getLogger(__name__)


def setup_logging():
    """ログ設定"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('/Users/nao/Desktop/bot/backtest/results/backtest_runner.log')
        ]
    )


def run_backtest(config_name: str, stats_output: str = None):
    """
    バックテスト実行
    
    Args:
        config_name: 設定ファイル名（.yml拡張子なし）
        stats_output: 結果CSV出力パス（オプション）
    """
    # 絶対パスで設定ファイルを指定
    config_path = f"/Users/nao/Desktop/bot/backtest/configs/{config_name}.yml"
    
    if not Path(config_path).exists():
        logger.error(f"設定ファイルが見つかりません: {config_path}")
        return False
    
    # 結果出力パス（デフォルト）
    if not stats_output:
        stats_output = f"/Users/nao/Desktop/bot/backtest/results/{config_name}_results.csv"
    
    logger.info(f"🚀 バックテスト開始")
    logger.info(f"   設定ファイル: {config_path}")
    logger.info(f"   結果出力: {stats_output}")
    
    try:
        # CLIコマンドを構築
        sys.argv = [
            'crypto_bot',
            'backtest',
            '--config', config_path,
            '--stats-output', stats_output,
            '--show-trades'
        ]
        
        # バックテスト実行
        crypto_main()
        
        logger.info("✅ バックテスト完了")
        return True
        
    except Exception as e:
        logger.error(f"❌ バックテストエラー: {e}")
        return False


def main():
    """メイン関数"""
    setup_logging()
    
    parser = argparse.ArgumentParser(
        description='バックテスト実行ヘルパー',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # RSI + MACD + EMAテスト
  python scripts/run_backtest.py test_rsi_macd_ema
  
  # ベース設定でフル97特徴量テスト
  python scripts/run_backtest.py base_backtest_config
  
  # カスタム結果出力パス指定
  python scripts/run_backtest.py test_rsi_macd_ema --output my_results.csv

利用可能な設定:
  - base_backtest_config (97特徴量フル)
  - test_rsi_macd_ema (RSI + MACD + EMA組み合わせ)
  - その他 config/backtest/ フォルダ内の .yml ファイル（拡張子なし）
        """
    )
    
    parser.add_argument(
        'config_name',
        help='設定ファイル名（.yml拡張子なし）'
    )
    
    parser.add_argument(
        '--output', '-o',
        dest='stats_output',
        help='結果CSV出力パス（オプション）'
    )
    
    parser.add_argument(
        '--list-configs', '-l',
        action='store_true',
        help='利用可能な設定ファイル一覧を表示'
    )
    
    args = parser.parse_args()
    
    # 設定ファイル一覧表示
    if args.list_configs:
        config_dir = Path('/Users/nao/Desktop/bot/backtest/configs')
        yml_files = list(config_dir.glob('*.yml'))
        
        logger.info("利用可能なバックテスト設定:")
        for yml_file in yml_files:
            if yml_file.name != 'README.md':
                config_name = yml_file.stem
                logger.info(f"  - {config_name}")
        return
    
    # バックテスト実行
    success = run_backtest(args.config_name, args.stats_output)
    
    if success:
        logger.info("🎯 バックテスト結果確認:")
        logger.info(f"   結果フォルダ: /Users/nao/Desktop/bot/backtest/results/")
        logger.info(f"   ログファイル: /Users/nao/Desktop/bot/backtest/results/backtest_runner.log")
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
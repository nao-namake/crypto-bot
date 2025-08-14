# CLI commands module
import os

from .live import live_bitbank_command
from .model import retrain_command, validate_model_command
from .stats import stats_command
from .validate import validate_config_command

# 開発環境でのみバックテストコマンドをインポート
backtest_command = None
try:
    # backtest/ディレクトリ存在チェック（開発環境判定）
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    if os.path.exists(os.path.join(project_root, "backtest")):
        from .backtest import backtest_command
except ImportError:
    backtest_command = None

__all__ = [
    "live_bitbank_command",
    "validate_config_command",
    "validate_model_command",
    "retrain_command",
    "stats_command",
]

# 開発環境でのみ backtest_command を __all__ に追加
if backtest_command:
    __all__.append("backtest_command")

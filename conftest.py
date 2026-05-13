"""Phase 87 Stage 3: プロジェクトルートに置く pytest conftest.py

scripts.* パッケージのテストを pyproject.toml の pythonpath 設定なしでも
動作させるため、プロジェクトルートを sys.path に明示的に追加する。
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

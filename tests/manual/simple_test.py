#!/usr/bin/env python3
"""
シンプルなimportテスト.
"""
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path("/Users/nao/Desktop/bot")
sys.path.insert(0, str(project_root / "src"))


def test_imports():
    """インポートテスト."""
    try:
        print("🧪 基本インポートテスト開始")

        # 基本モジュールのインポート
        from src.core.logger import setup_logging

        print("✅ core.logger インポート成功")

        from src.core.config import get_config

        print("✅ core.config インポート成功")

        from src.core.exceptions import ExchangeAPIError

        print("✅ core.exceptions インポート成功")

        # データ層のインポート
        from src.data.bitbank_client import BitbankClient

        print("✅ data.bitbank_client インポート成功")

        print("🎉 全インポートテスト成功！")
        return True

    except Exception as e:
        print(f"❌ インポートエラー: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)

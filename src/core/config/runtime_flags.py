"""
グローバルランタイムフラグシステム - Phase 49完了

バックテストモードなどのランタイム状態を全コンポーネントで共有。
スレッドセーフな実装でマルチスレッド環境でも安全に動作。

Phase 49完了:
- バックテストモード検出（全コンポーネント共有・API呼び出しモック化制御）
- ペーパーモード検出（ライブ/ペーパー切り替え）
- ログレベル動的制御（バックテスト時WARNING・通常時DEBUG）

Phase 35実装:
- スレッドセーフ設計（threading.Lock使用）
- グローバル状態最小化（3フラグのみ: backtest_mode・backtest_log_level・paper_mode）
- シンプルなAPI（get/set関数のみ）
"""

import threading
from typing import Any, Dict

# グローバルランタイムフラグストレージ
_runtime_flags: Dict[str, Any] = {
    "backtest_mode": False,  # バックテストモード有効フラグ
    "backtest_log_level": "WARNING",  # バックテスト時のログレベル
    "paper_mode": False,  # ペーパートレードモード有効フラグ
}

# スレッドセーフロック
_lock = threading.Lock()


def set_backtest_mode(enabled: bool) -> None:
    """
    バックテストモードを設定（Phase 35）

    全コンポーネントがこのフラグを参照し、バックテスト時の動作を制御。
    - BitbankClient: API呼び出しモック化
    - Logger: ログレベル抑制
    - MarginMonitor: API呼び出しスキップ
    - 戦略: エラーログ抑制

    Args:
        enabled: バックテストモード有効化フラグ
    """
    with _lock:
        _runtime_flags["backtest_mode"] = enabled


def is_backtest_mode() -> bool:
    """
    バックテストモード状態取得（Phase 35）

    Returns:
        bool: バックテストモード有効フラグ
    """
    with _lock:
        return _runtime_flags.get("backtest_mode", False)


def set_paper_mode(enabled: bool) -> None:
    """
    ペーパートレードモードを設定

    Args:
        enabled: ペーパーモード有効化フラグ
    """
    with _lock:
        _runtime_flags["paper_mode"] = enabled


def is_paper_mode() -> bool:
    """
    ペーパートレードモード状態取得

    Returns:
        bool: ペーパーモード有効フラグ
    """
    with _lock:
        return _runtime_flags.get("paper_mode", False)


def set_backtest_log_level(level: str) -> None:
    """
    バックテスト時のログレベルを設定

    Args:
        level: ログレベル文字列（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    """
    with _lock:
        _runtime_flags["backtest_log_level"] = level.upper()


def get_backtest_log_level() -> str:
    """
    バックテスト時のログレベル取得

    Returns:
        str: ログレベル文字列
    """
    with _lock:
        return _runtime_flags.get("backtest_log_level", "WARNING")


def reset_all_flags() -> None:
    """
    全フラグをデフォルト値にリセット

    テストやシステムリセット時に使用。
    """
    with _lock:
        _runtime_flags["backtest_mode"] = False
        _runtime_flags["backtest_log_level"] = "WARNING"
        _runtime_flags["paper_mode"] = False


def get_all_flags() -> Dict[str, Any]:
    """
    全フラグの現在値を取得（デバッグ用）

    Returns:
        Dict[str, Any]: 全フラグのコピー
    """
    with _lock:
        return _runtime_flags.copy()

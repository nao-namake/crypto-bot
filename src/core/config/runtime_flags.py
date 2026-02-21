"""
グローバルランタイムフラグシステム - Phase 64.13

バックテストモードなどのランタイム状態を全コンポーネントで共有。
スレッドセーフな実装でマルチスレッド環境でも安全に動作。

Phase 64.13: paper_mode・reset_all_flags・get_all_flags削除（未使用）
Phase 49完了:
- バックテストモード検出（全コンポーネント共有・API呼び出しモック化制御）
- ログレベル動的制御（バックテスト時WARNING・通常時DEBUG）

Phase 35実装:
- スレッドセーフ設計（threading.Lock使用）
- グローバル状態最小化（2フラグ: backtest_mode・backtest_log_level）
- シンプルなAPI（get/set関数のみ）
"""

import threading

# グローバルランタイムフラグストレージ
_runtime_flags = {
    "backtest_mode": False,  # バックテストモード有効フラグ
    "backtest_log_level": "WARNING",  # バックテスト時のログレベル
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

"""
状態永続化システム - Phase 52.4完了

ドローダウン状態の永続化・管理システム。
ローカルファイルとCloud Storage両対応の統一インターフェース。
モード別（paper/live/backtest）状態分離によるデータ安全性確保。

Phase 52.4: 設定ファイル統合・ハードコード削除
- unified.yamlからパステンプレート取得（local_path_template/gcs_path_template）
- get_config()パターン適用によるハードコード値削除完了

Phase 49: 統一永続化インターフェース確立
- DrawdownPersistence: 基底抽象クラス（save_state・load_state・delete_stateインターフェース）
- LocalFilePersistence: ローカルファイル実装（src/core/state/{mode}/drawdown_state.json）
- CloudStoragePersistence: GCP Cloud Storage実装（gs://bucket/{mode}/drawdown_state.json）
- create_persistence(): 環境自動判定ファクトリ関数（GCP/ローカル環境自動選択）
"""

from .drawdown_persistence import (
    CloudStoragePersistence,
    DrawdownPersistence,
    LocalFilePersistence,
    create_persistence,
)

__all__ = [
    "DrawdownPersistence",
    "LocalFilePersistence",
    "CloudStoragePersistence",
    "create_persistence",
]

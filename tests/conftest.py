"""
Phase 90α: pytest セッション全体の環境設定

このファイルは pytest 起動時に最早期に評価される（PyTorch / sklearn / numpy
の C 拡張が import される前）。OpenMP / BLAS スレッド数を 1 に固定して、
macOS Apple Silicon 上での PyTorch + sklearn / LightGBM のスレッドプール
競合（CLAUDE.md 既知問題「macOS 上のテスト連続実行時 SEGFAULT」と同根）を
予防する。

Linux (CI Ubuntu) でも害はない（むしろ test 再現性が向上する）。
"""

import os

# macOS / Linux 共通: OpenMP / BLAS スレッドを 1 に固定
# - MKL: Intel Math Kernel Library（numpy / scipy / scikit-learn が使用）
# - OMP: OpenMP（LightGBM / PyTorch / sklearn 内部スレッド）
# - OPENBLAS: OpenBLAS（numpy が使用するケースあり）
# - PYTORCH_ENABLE_MPS_FALLBACK: macOS MPS バックエンド自動切替を抑止
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "0")

# bitbank API 認証情報が未設定でも test が動くよう mock 値を設定
# （個別 test ファイル冒頭でも同じ処理をしているが、ここで一元化）
os.environ.setdefault("BITBANK_API_KEY", "test_key_for_unit_tests")
os.environ.setdefault("BITBANK_API_SECRET", "test_secret_for_unit_tests")

# Phase 90α: テスト実行中は Firestore real call を抑止
# - FirestoreStateClient で BOT_FORCE_LOCAL_PERSISTENCE=1 を検知し local JSON のみ使用
# - ローカル macOS で認証情報あり (gcloud auth) でも net 接続を試みない
# - CI でも有効化 → Firestore real call 回避で test 高速化 + 確実性向上
os.environ.setdefault("BOT_FORCE_LOCAL_PERSISTENCE", "1")

# 注意: ここで torch を import すると torch の C 拡張が OpenMP プールを先取りし、
# その後 LightGBM の初期化と競合して macOS で SEGFAULT が発生する。
# torch のスレッド設定は (a) 環境変数 OMP_NUM_THREADS=1 で間接制御
#                         (b) nbeats_predictor.py:fit() 内の torch.set_num_threads(1)
# で対処済みのため、conftest.py では torch を import しない。


def pytest_configure(config):
    """pytest 起動時に追加で何か必要なら fixture でなく conftest 設定で行う."""
    pass

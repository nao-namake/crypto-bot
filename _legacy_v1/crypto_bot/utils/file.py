"""
File utility functions
"""

import os


def ensure_dir_for_file(path: str):
    """親ディレクトリが無ければ作成する"""
    dir_path = os.path.dirname(path)
    if dir_path and not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)

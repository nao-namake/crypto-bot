"""
Configuration loading and management
"""

import logging
import os
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def deep_merge(default: dict, override: dict) -> dict:
    """ネストされた辞書を再帰的にマージ"""
    for k, v in override.items():
        if k in default and isinstance(default[k], dict) and isinstance(v, dict):
            default[k] = deep_merge(default[k], v)
        else:
            default[k] = v
    return default


def expand_env_vars_recursive(obj):
    """再帰的に環境変数を展開"""
    if isinstance(obj, dict):
        return {key: expand_env_vars_recursive(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [expand_env_vars_recursive(item) for item in obj]
    elif isinstance(obj, str):
        # ${ENV_VAR} パターンを展開
        return os.path.expandvars(obj)
    else:
        return obj


def load_config(path: str) -> dict:
    """設定ファイルを読み込む"""
    base = Path(__file__).parent.parent

    # 本番環境では production.yml のみを使用（default.yml 読み込み回避）
    if "production" in path:
        with open(path, "r") as f:
            config = yaml.safe_load(f) or {}
        logger.info(f"🔒 [CONFIG] Production mode: Using {path} only")
    else:
        # 開発環境: default.yml があればマージ、なければ設定ファイルのみ使用
        default_path = base / "config" / "development" / "default.yml"
        if default_path.exists():
            # default.yml が存在する場合はマージ
            with open(default_path, "r") as f:
                default_cfg = yaml.safe_load(f) or {}
            with open(path, "r") as f:
                user_cfg = yaml.safe_load(f) or {}
            config = deep_merge(default_cfg, user_cfg)
            logger.info("🔧 [CONFIG] Development mode: Merged with default.yml")
        else:
            # default.yml が存在しない場合は設定ファイルのみ使用
            with open(path, "r") as f:
                config = yaml.safe_load(f) or {}
            logger.info(
                f"🔧 [CONFIG] Development mode: Using {path} only (no default.yml)"
            )

    # 環境変数の展開
    config = expand_env_vars_recursive(config)

    return config

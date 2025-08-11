#!/usr/bin/env python
"""
統合モデル管理ツール

すべてのモデル作成・再学習機能を統合
個別スクリプトの機能を1つにまとめて管理しやすくする

Usage:
    python scripts/model_tools/manage_models.py create --type production
    python scripts/model_tools/manage_models.py create --type ci
    python scripts/model_tools/manage_models.py create --type ensemble
    python scripts/model_tools/manage_models.py retrain --features 97
"""

import argparse
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def create_production_model():
    """本番用モデル作成（create_production_model.py の機能）"""
    from scripts.create_production_model import main as create_prod

    print("📦 Creating production model...")
    return create_prod()


def create_ci_model():
    """CI用モデル作成（create_ci_model.py の機能）"""
    from scripts.create_ci_model import main as create_ci

    print("🧪 Creating CI model...")
    return create_ci()


def create_ensemble_model():
    """アンサンブルモデル作成（create_proper_ensemble_model.py の機能）"""
    from scripts.create_proper_ensemble_model import main as create_ensemble

    print("🎯 Creating ensemble model...")
    return create_ensemble()


def retrain_97_features():
    """97特徴量モデル再学習（retrain_97_features_model.py の機能）"""
    from scripts.retrain_97_features_model import main as retrain

    print("♻️ Retraining 97 features model...")
    return retrain()


def main():
    """メインエントリーポイント"""
    parser = argparse.ArgumentParser(
        description="統合モデル管理ツール - モデルの作成と再学習を統合管理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 本番用モデル作成
  python scripts/model_tools/manage_models.py create --type production
  
  # CI用モデル作成
  python scripts/model_tools/manage_models.py create --type ci
  
  # アンサンブルモデル作成
  python scripts/model_tools/manage_models.py create --type ensemble
  
  # 97特徴量モデル再学習
  python scripts/model_tools/manage_models.py retrain --features 97
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="実行するコマンド")

    # create コマンド
    create_parser = subparsers.add_parser("create", help="モデル作成")
    create_parser.add_argument(
        "--type",
        choices=["production", "ci", "ensemble"],
        required=True,
        help="作成するモデルのタイプ",
    )

    # retrain コマンド
    retrain_parser = subparsers.add_parser("retrain", help="モデル再学習")
    retrain_parser.add_argument(
        "--features", type=int, default=97, help="特徴量数（デフォルト: 97）"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # コマンド実行
    try:
        if args.command == "create":
            if args.type == "production":
                return create_production_model()
            elif args.type == "ci":
                return create_ci_model()
            elif args.type == "ensemble":
                return create_ensemble_model()
        elif args.command == "retrain":
            if args.features == 97:
                return retrain_97_features()
            else:
                print(f"❌ Feature count {args.features} not supported yet")
                return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

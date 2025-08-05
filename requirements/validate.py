#!/usr/bin/env python3
"""
requirements/validate.py
Phase 12.5: Environment Parity & Dependency Management System
依存関係一貫性チェック・同期機能・ドリフト検出
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


class DependencyValidator:
    """依存関係一貫性チェック・同期システム"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.requirements_dir = self.project_root / "requirements"
        self.base_file = self.requirements_dir / "base.txt"
        self.dev_file = self.requirements_dir / "dev.txt"
        self.dockerfile = self.project_root / "Dockerfile"
    
    def parse_requirements(self, file_path: Path) -> Dict[str, str]:
        """requirements.txtファイルを解析してパッケージ辞書を返す"""
        packages = {}
        if not file_path.exists():
            return packages
            
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # コメント・空行・-r継承をスキップ
                if not line or line.startswith('#') or line.startswith('-r'):
                    continue
                    
                # パッケージ名とバージョンを抽出
                match = re.match(r'^([a-zA-Z0-9_-]+)([>=<!~]+.+)?', line)
                if match:
                    package = match.group(1).lower()
                    version = match.group(2) or ""
                    packages[package] = version
                    
        return packages
    
    def extract_dockerfile_deps(self) -> Dict[str, str]:
        """Dockerfileから依存関係を抽出（requirements.txt使用検出）"""
        packages = {}
        if not self.dockerfile.exists():
            return packages
            
        with open(self.dockerfile, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Phase 12.5: requirements.txt使用パターンを検出
        if "requirements/base.txt" in content and "pip install" in content and "-r" in content:
            # 新形式: requirements.txtファイル使用
            # base.txtから依存関係を読み込み
            return self.parse_requirements(self.base_file)
        
        # 旧形式: 直接pip installハードコード（後方互換性）
        pip_pattern = r'pip install[^\\]*?\\([^&]+)'
        matches = re.findall(pip_pattern, content, re.DOTALL)
        
        for match in matches:
            lines = match.split('\\')
            for line in lines:
                line = line.strip()
                if '==' in line:
                    # パッケージ==バージョン形式を抽出
                    match = re.match(r'^([a-zA-Z0-9_-]+)==([0-9.]+)', line)
                    if match:
                        package = match.group(1).lower()
                        version = f"=={match.group(2)}"
                        packages[package] = version
                        
        return packages
    
    def validate_consistency(self) -> Tuple[bool, List[str]]:
        """依存関係一貫性チェック"""
        errors = []
        
        # 各ファイルから依存関係を抽出
        base_deps = self.parse_requirements(self.base_file)
        dockerfile_deps = self.extract_dockerfile_deps()
        
        if not base_deps:
            errors.append("❌ requirements/base.txt が見つからないか空です")
            return False, errors
            
        if not dockerfile_deps:
            errors.append("❌ Dockerfile に pip install 依存関係が見つかりません")
            return False, errors
        
        # base.txt vs Dockerfile 比較
        base_packages = set(base_deps.keys())
        dockerfile_packages = set(dockerfile_deps.keys())
        
        # 不足パッケージチェック
        missing_in_dockerfile = base_packages - dockerfile_packages
        missing_in_base = dockerfile_packages - base_packages
        
        if missing_in_dockerfile:
            errors.append(f"❌ Dockerfile に不足: {sorted(missing_in_dockerfile)}")
            
        if missing_in_base:
            errors.append(f"❌ base.txt に不足: {sorted(missing_in_base)}")
        
        # バージョン不一致チェック
        common_packages = base_packages & dockerfile_packages
        for package in common_packages:
            base_version = base_deps[package]
            dockerfile_version = dockerfile_deps[package]
            if base_version != dockerfile_version:
                errors.append(f"❌ バージョン不一致 {package}: base.txt{base_version} vs Dockerfile{dockerfile_version}")
        
        return len(errors) == 0, errors
    
    def generate_dockerfile_requirements(self) -> str:
        """base.txtからDockerfile用requirements行を生成"""
        base_deps = self.parse_requirements(self.base_file)
        if not base_deps:
            return ""
            
        return "COPY requirements/base.txt /app/requirements.txt\nRUN pip install --no-cache-dir -r /app/requirements.txt"
    
    def sync_dependencies(self) -> bool:
        """依存関係同期（現在は情報表示のみ）"""
        print("🔄 依存関係同期情報:")
        
        base_deps = self.parse_requirements(self.base_file)
        print(f"📋 base.txt: {len(base_deps)} packages")
        for package, version in sorted(base_deps.items()):
            print(f"   - {package}{version}")
            
        dockerfile_suggestion = self.generate_dockerfile_requirements()
        print(f"\n📦 Dockerfile推奨設定:")
        print(dockerfile_suggestion)
        
        return True
    
    def run_validation(self, sync: bool = False) -> bool:
        """バリデーション実行"""
        print("🔍 Phase 12.5: Dependency Validation")
        print("=" * 50)
        
        # ファイル存在チェック
        if not self.base_file.exists():
            print("❌ requirements/base.txt が存在しません")
            return False
            
        if not self.dockerfile.exists():
            print("❌ Dockerfile が存在しません")
            return False
        
        # 同期モード
        if sync:
            return self.sync_dependencies()
        
        # 検証モード
        is_consistent, errors = self.validate_consistency()
        
        if is_consistent:
            print("✅ 依存関係一貫性チェック: 成功")
            print("🎯 Environment Parity: Local ≈ CI ≈ Production")
            return True
        else:
            print("❌ 依存関係一貫性チェック: 失敗")
            for error in errors:
                print(f"   {error}")
            print("\n💡 修正方法:")
            print("   1. requirements/base.txt を更新")
            print("   2. python requirements/validate.py --sync で確認")
            print("   3. 手動でDockerfile調整（必要に応じて）")
            return False


def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(
        description="Phase 12.5: Dependency Validation & Sync System"
    )
    parser.add_argument(
        "--sync", 
        action="store_true",
        help="依存関係同期情報表示"
    )
    
    args = parser.parse_args()
    
    validator = DependencyValidator()
    success = validator.run_validation(sync=args.sync)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
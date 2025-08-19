#!/usr/bin/env python3
"""
Cloud Run環境での外部API接続診断スクリプト
Phase H.19: 本番環境での問題特定用

使用方法:
    python scripts/diagnose_cloud_run_apis.py
"""

import json
import logging
import sys
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crypto_bot.utils.cloud_run_api_diagnostics import run_diagnostics


def main():
    """診断を実行して結果を表示"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    print("🔍 Cloud Run API診断を開始します...")
    print("-" * 80)

    try:
        results = run_diagnostics()

        # 結果の表示
        print(f"\n📊 診断結果サマリー:")
        print(f"  - Cloud Run環境: {results['is_cloud_run']}")
        print(f"  - 総テスト数: {results['summary']['total_tests']}")
        print(f"  - 成功: {results['summary']['successful_tests']}")
        print(f"  - 失敗: {results['summary']['failed_tests']}")
        print(f"  - 診断時間: {results['summary']['total_time_seconds']:.2f}秒")

        # API別の結果
        print(f"\n🌐 API接続結果:")
        for api_name, api_result in results["summary"]["api_results"].items():
            status = "✅" if api_result["success"] else "❌"
            print(f"  {status} {api_name}: ", end="")
            if api_result["success"]:
                print(f"成功 (応答時間: {api_result.get('time_ms', 'N/A'):.1f}ms)")
            else:
                print(f"失敗 - {api_result.get('error', 'Unknown error')}")

        # 推奨事項
        if results["summary"]["recommendations"]:
            print(f"\n💡 推奨事項:")
            for recommendation in results["summary"]["recommendations"]:
                print(f"  - {recommendation}")

        # 詳細な結果をJSONファイルに保存
        output_file = "cloud_run_api_diagnostics_result.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n📄 詳細な診断結果を {output_file} に保存しました。")

        # Cloud Run環境の場合は、環境変数も表示
        if results["is_cloud_run"]:
            print(f"\n🌍 Cloud Run環境変数:")
            env_result = next(
                (r for r in results["results"] if r.get("test") == "environment"), None
            )
            if env_result:
                for key, value in env_result["cloud_run_env"].items():
                    print(f"  - {key}: {value}")

        # 失敗があった場合は終了コード1
        if results["summary"]["failed_tests"] > 0:
            sys.exit(1)

    except Exception as e:
        print(f"\n❌ 診断中にエラーが発生しました: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

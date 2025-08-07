"""
Validation commands
"""

import json
import logging
import sys

import click

from crypto_bot.config import load_config
from crypto_bot.strategy.factory import StrategyFactory

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--config", "-c", "config_path", required=True, type=click.Path(exists=True)
)
def validate_config_command(config_path: str):
    """戦略設定の検証"""
    cfg = load_config(config_path)
    strategy_config = cfg.get("strategy", {})

    if strategy_config.get("type") == "multi":
        strategies_config = strategy_config.get("strategies", [])
        errors = []
        for i, strategy_config in enumerate(strategies_config):
            strategy_errors = StrategyFactory.validate_config(strategy_config)
            for error in strategy_errors:
                errors.append(f"Strategy {i+1}: {error}")

        if errors:
            click.echo("Configuration errors found:")
            for error in errors:
                click.echo(f"  - {error}")
        else:
            click.echo("Multi-strategy configuration is valid!")
    else:
        errors = StrategyFactory.validate_config(strategy_config)
        if errors:
            click.echo("Configuration errors found:")
            for error in errors:
                click.echo(f"  - {error}")
        else:
            click.echo("Strategy configuration is valid!")


@click.command()
def diagnose_apis_command():
    """外部API接続の診断（Phase H.19）"""
    from crypto_bot.utils.cloud_run_api_diagnostics import run_diagnostics

    click.echo("🔍 外部API接続診断を開始します...")
    click.echo("-" * 80)

    try:
        results = run_diagnostics()

        # 結果の表示
        click.echo("\n📊 診断結果サマリー:")
        click.echo(f"  - Cloud Run環境: {results['is_cloud_run']}")
        click.echo(f"  - 総テスト数: {results['summary']['total_tests']}")
        click.echo(f"  - 成功: {results['summary']['successful_tests']}")
        click.echo(f"  - 失敗: {results['summary']['failed_tests']}")
        click.echo(f"  - 診断時間: {results['summary']['total_time_seconds']:.2f}秒")

        # API別の結果
        click.echo("\n🌐 API接続結果:")
        for api_name, api_result in results["summary"]["api_results"].items():
            status = "✅" if api_result["success"] else "❌"
            click.echo(f"  {status} {api_name}: ", nl=False)
            if api_result["success"]:
                click.echo(f"成功 (応答時間: {api_result.get('time_ms', 'N/A'):.1f}ms)")
            else:
                click.echo(f"失敗 - {api_result.get('error', 'Unknown error')}")

        # 推奨事項
        if results["summary"]["recommendations"]:
            click.echo("\n💡 推奨事項:")
            for recommendation in results["summary"]["recommendations"]:
                click.echo(f"  - {recommendation}")

        # 詳細な結果をJSONファイルに保存
        output_file = "cloud_run_api_diagnostics_result.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        click.echo(f"\n📄 詳細な診断結果を {output_file} に保存しました。")

        # Cloud Run環境の場合は、環境変数も表示
        if results["is_cloud_run"]:
            click.echo("\n🌍 Cloud Run環境変数:")
            env_result = next(
                (r for r in results["results"] if r.get("test") == "environment"), None
            )
            if env_result:
                for key, value in env_result["cloud_run_env"].items():
                    click.echo(f"  - {key}: {value}")

        # 失敗があった場合は終了コード1
        if results["summary"]["failed_tests"] > 0:
            sys.exit(1)

    except Exception as e:
        click.echo(f"\n❌ 診断中にエラーが発生しました: {e}", err=True)
        import traceback

        traceback.print_exc()
        sys.exit(1)

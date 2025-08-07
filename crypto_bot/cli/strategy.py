"""
Strategy information CLI commands
"""

import inspect
import logging

import click

from crypto_bot.strategy.factory import StrategyFactory

logger = logging.getLogger(__name__)


@click.command()
def list_strategies_command():
    """利用可能な戦略一覧を表示"""
    strategies = StrategyFactory.list_strategies()

    click.echo("=== Available Strategies ===\n")

    for name, info in strategies.items():
        click.echo(f"📌 {name}")
        click.echo(f"   Class: {info['class'].__name__}")
        click.echo(f"   Module: {info['class'].__module__}")

        # ドキュメント文字列
        if info["class"].__doc__:
            doc_lines = info["class"].__doc__.strip().split("\n")
            click.echo(f"   Description: {doc_lines[0]}")

        # パラメータ
        if info.get("params"):
            click.echo("   Parameters:")
            for param in info["params"]:
                click.echo(f"     - {param}")

        click.echo()  # 空行

    click.echo(f"Total strategies available: {len(strategies)}")


@click.command()
@click.argument("strategy_name")
def strategy_info_command(strategy_name: str):
    """戦略の詳細情報を表示"""
    strategies = StrategyFactory.list_strategies()

    if strategy_name not in strategies:
        click.echo(f"Error: Strategy '{strategy_name}' not found", err=True)
        click.echo("\nAvailable strategies:")
        for name in strategies.keys():
            click.echo(f"  - {name}")
        return

    info = strategies[strategy_name]
    strategy_class = info["class"]

    click.echo(f"\n=== Strategy: {strategy_name} ===\n")
    click.echo(f"Class: {strategy_class.__name__}")
    click.echo(f"Module: {strategy_class.__module__}")

    # ドキュメント文字列
    if strategy_class.__doc__:
        click.echo("\nDescription:")
        click.echo(strategy_class.__doc__.strip())

    # メソッド一覧
    click.echo("\nMethods:")
    for name, method in inspect.getmembers(
        strategy_class, predicate=inspect.isfunction
    ):
        if not name.startswith("_"):  # プライベートメソッドを除外
            sig = inspect.signature(method)
            click.echo(f"  - {name}{sig}")

    # __init__パラメータ
    if hasattr(strategy_class, "__init__"):
        init_sig = inspect.signature(strategy_class.__init__)
        params = []
        for param_name, param in init_sig.parameters.items():
            if param_name not in ["self", "config"]:
                default_str = (
                    f"={param.default}"
                    if param.default != inspect.Parameter.empty
                    else ""
                )
                annotation = (
                    f": {param.annotation}"
                    if param.annotation != inspect.Parameter.empty
                    else ""
                )
                params.append(f"{param_name}{annotation}{default_str}")

        if params:
            click.echo("\nInitialization Parameters:")
            for param in params:
                click.echo(f"  - {param}")

    # 設定例
    click.echo("\nConfiguration Example:")
    click.echo("```yaml")
    click.echo("strategy:")
    click.echo(f'  name: "{strategy_name}"')

    if strategy_name == "ml":
        click.echo("  params:")
        click.echo('    model_path: "models/model.pkl"')
        click.echo("    threshold: 0.5")
        click.echo("    use_ensemble: true")
    elif strategy_name == "multi_timeframe_ensemble":
        click.echo("  params:")
        click.echo('    primary_timeframe: "1h"')
        click.echo('    secondary_timeframes: ["15m", "4h"]')
        click.echo('    ensemble_method: "voting"')
        click.echo("    confidence_threshold: 0.6")
    elif strategy_name in ["bollinger", "rsi", "macd"]:
        click.echo("  params:")
        click.echo("    period: 20")
        click.echo("    threshold: 0.8")

    click.echo("```")

    # 追加情報
    if strategy_name == "ml":
        click.echo("\n📊 ML Strategy Notes:")
        click.echo("- Requires pre-trained model file")
        click.echo("- Supports ensemble models")
        click.echo("- Features are generated automatically")
    elif strategy_name == "multi_timeframe_ensemble":
        click.echo("\n🕐 Multi-Timeframe Notes:")
        click.echo("- Combines signals from multiple timeframes")
        click.echo("- Supports 15m, 1h, 4h timeframes")
        click.echo("- Uses ensemble voting or averaging")

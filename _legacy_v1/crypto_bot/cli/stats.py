"""
Statistics command
"""

import logging

import click

logger = logging.getLogger(__name__)


@click.command()
@click.option(
    "--period", "-p", default="7d", help="Statistics period (e.g., 1d, 7d, 30d)"
)
@click.option(
    "--format",
    "-f",
    "output_format",
    default="table",
    type=click.Choice(["table", "json", "csv"]),
    help="Output format",
)
def stats_command(period: str, output_format: str):
    """取引統計の表示"""
    # TODO: Implement statistics display
    click.echo(
        f"Statistics for period {period} in {output_format} format is not yet implemented"
    )
    logger.warning("stats_command is not yet implemented")

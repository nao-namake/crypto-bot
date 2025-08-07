"""
Chart creation utilities
"""

import logging
from typing import Any, Dict

import pandas as pd

logger = logging.getLogger(__name__)

# matplotlib条件付きimport
MATPLOTLIB_AVAILABLE = False
try:
    import matplotlib.pyplot as plt

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    pass


def create_performance_chart(portfolio_df: pd.DataFrame, cfg: Dict[str, Any]):
    """収益推移のチャートを作成"""
    from crypto_bot.utils.file import ensure_dir_for_file

    # Phase 12.3: matplotlib不在時はスキップ
    if not MATPLOTLIB_AVAILABLE:
        logger.warning("⚠️ [CHART] Matplotlib not available, skipping chart generation")
        return

    try:
        plt.style.use("default")
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

        # 上段: ポートフォリオ価値の推移
        ax1.plot(
            portfolio_df.index,
            portfolio_df["portfolio_value"],
            label="Portfolio Value",
            linewidth=2,
            color="blue",
        )

        # 初期資金ライン
        starting_balance = cfg["backtest"]["starting_balance"]
        ax1.axhline(
            y=starting_balance,
            color="gray",
            linestyle="--",
            label=f"Initial Balance ({starting_balance:,.0f})",
        )

        # 収益エリアの塗りつぶし
        ax1.fill_between(
            portfolio_df.index,
            starting_balance,
            portfolio_df["portfolio_value"],
            where=(portfolio_df["portfolio_value"] >= starting_balance),
            color="green",
            alpha=0.1,
            label="Profit",
        )
        ax1.fill_between(
            portfolio_df.index,
            starting_balance,
            portfolio_df["portfolio_value"],
            where=(portfolio_df["portfolio_value"] < starting_balance),
            color="red",
            alpha=0.1,
            label="Loss",
        )

        ax1.grid(True, alpha=0.3)
        ax1.set_ylabel("Portfolio Value (JPY)")
        ax1.set_title("Portfolio Performance Over Time", fontsize=14, fontweight="bold")
        ax1.legend(loc="upper left")

        # Y軸フォーマット（カンマ区切り）
        ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{x:,.0f}"))

        # 下段: リターン率の推移
        ax2.plot(
            portfolio_df.index,
            portfolio_df["return_pct"],
            label="Return %",
            linewidth=2,
            color=(
                "darkgreen" if portfolio_df["return_pct"].iloc[-1] >= 0 else "darkred"
            ),
        )

        # ゼロライン
        ax2.axhline(y=0, color="black", linestyle="-", linewidth=0.5)

        # 正負エリアの塗りつぶし
        ax2.fill_between(
            portfolio_df.index,
            0,
            portfolio_df["return_pct"],
            where=(portfolio_df["return_pct"] >= 0),
            color="green",
            alpha=0.1,
        )
        ax2.fill_between(
            portfolio_df.index,
            0,
            portfolio_df["return_pct"],
            where=(portfolio_df["return_pct"] < 0),
            color="red",
            alpha=0.1,
        )

        ax2.grid(True, alpha=0.3)
        ax2.set_xlabel("Period")
        ax2.set_ylabel("Return (%)")
        ax2.set_title("Return Rate Evolution", fontsize=12)

        # Y軸フォーマット（パーセント表示）
        ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f"{x:.1f}%"))

        # タイトルに最終成績を追加
        final_value = portfolio_df["portfolio_value"].iloc[-1]
        final_return = portfolio_df["return_pct"].iloc[-1]
        fig.suptitle(
            f"Final Value: ¥{final_value:,.0f} ({final_return:+.2f}%)",
            fontsize=16,
            fontweight="bold",
            y=0.995,
        )

        plt.tight_layout()

        # チャート保存
        chart_path = cfg["backtest"].get(
            "performance_chart", "results/performance_chart.png"
        )
        ensure_dir_for_file(chart_path)
        plt.savefig(chart_path, dpi=150, bbox_inches="tight")
        plt.close()

        logger.info(f"📊 Performance chart saved to {chart_path}")

    except Exception as e:
        logger.error(f"Failed to create performance chart: {e}")

# =============================================================================
# File: crypto_bot/advanced_monitor.py
# Description:
#   Professional-grade real-time monitoring dashboard with advanced analytics,
#   market data integration, trading signals, and comprehensive performance tracking.
# =============================================================================
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ---------------------- Advanced Streamlit Configuration ---------------------
st.set_page_config(
    page_title="Crypto‑Bot Advanced Monitor",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------- Custom CSS for Professional Look --------------------
st.markdown(
    """
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    .status-indicator {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 8px;
    }
    .status-running { background-color: #28a745; }
    .status-stopped { background-color: #dc3545; }
    .status-warning { background-color: #ffc107; }
    .alert-box {
        padding: 0.75rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    .alert-success { background-color: #d4edda; border: 1px solid #c3e6cb; }
    .alert-warning { background-color: #fff3cd; border: 1px solid #ffeaa7; }
    .alert-danger { background-color: #f8d7da; border: 1px solid #f5c6cb; }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------- Header with Status Indicator -----------------------
col1, col2, col3 = st.columns([3, 1, 1])
with col1:
    st.title("🚀 Crypto‑Bot Advanced Monitor")
    st.markdown("**プロフェッショナル リアルタイム監視システム**")

with col2:
    current_time = datetime.now().strftime("%H:%M:%S")
    st.metric("現在時刻", current_time)

with col3:
    # System status indicator
    status_file = Path("status.json")
    if status_file.exists():
        status_indicator = "🟢 ACTIVE"
        status_class = "status-running"
    else:
        status_indicator = "🔴 INACTIVE"
        status_class = "status-stopped"

    st.markdown(
        f"""
    <div class="status-indicator {status_class}"></div>
    <span style="font-weight: bold;">{status_indicator}</span>
    """,
        unsafe_allow_html=True,
    )

# ---------------------- Auto-refresh Configuration --------------------------
refresh_interval = st.sidebar.selectbox(
    "🔄 更新間隔", options=[30, 60, 120, 300], index=1, format_func=lambda x: f"{x}秒"
)


@st.cache_data(ttl=refresh_interval)
def _refresh_dummy():
    return datetime.now()


_ = _refresh_dummy()


# ---------------------- Advanced Data Loading Functions ------------------
@st.cache_data(ttl=300)
def load_comprehensive_data() -> Dict[str, Any]:
    """Load all available data for comprehensive analysis"""
    data = {}

    # Load status data
    status_file = Path("status.json")
    if status_file.exists():
        with status_file.open(encoding="utf-8") as f:
            data["status"] = json.load(f)
    else:
        data["status"] = {}

    # Load daily P&L data
    daily_file = Path("results/aggregate_daily.csv")
    if daily_file.exists():
        data["daily_pnl"] = pd.read_csv(daily_file)
        data["daily_pnl"]["date"] = pd.to_datetime(
            data["daily_pnl"]["exit_time"]
        ).dt.date
    else:
        data["daily_pnl"] = pd.DataFrame()

    # Load trade log
    trade_file = Path("results/trade_log.csv")
    if trade_file.exists():
        data["trades"] = pd.read_csv(trade_file)
        data["trades"]["exit_time"] = pd.to_datetime(data["trades"]["exit_time"])
    else:
        data["trades"] = pd.DataFrame()

    # Load backtest results if available
    backtest_file = Path("results/backtest_results.csv")
    if backtest_file.exists():
        data["backtest"] = pd.read_csv(backtest_file)
    else:
        data["backtest"] = pd.DataFrame()

    return data


def create_real_time_metrics_chart(trades_df: pd.DataFrame) -> go.Figure:
    """Create real-time trading metrics chart"""
    if trades_df.empty:
        return go.Figure()

    # Calculate hourly metrics
    trades_df["hour"] = trades_df["exit_time"].dt.floor("H")
    hourly_stats = (
        trades_df.groupby("hour")
        .agg({"profit": ["sum", "count", "mean"], "return_rate": "mean"})
        .round(2)
    )

    hourly_stats.columns = ["total_profit", "trade_count", "avg_profit", "avg_return"]
    hourly_stats = hourly_stats.reset_index()

    # Create subplot with secondary y-axis
    fig = go.Figure()

    # Profit bars
    fig.add_trace(
        go.Bar(
            x=hourly_stats["hour"],
            y=hourly_stats["total_profit"],
            name="時間別利益",
            marker_color=[
                "green" if x >= 0 else "red" for x in hourly_stats["total_profit"]
            ],
            yaxis="y",
            opacity=0.7,
        )
    )

    # Trade count line
    fig.add_trace(
        go.Scatter(
            x=hourly_stats["hour"],
            y=hourly_stats["trade_count"],
            mode="lines+markers",
            name="取引回数",
            yaxis="y2",
            line=dict(color="blue", width=2),
        )
    )

    fig.update_layout(
        title="⏰ 時間別取引パフォーマンス",
        xaxis_title="時間",
        yaxis=dict(title="利益 (円)", side="left"),
        yaxis2=dict(title="取引回数", side="right", overlaying="y"),
        hovermode="x unified",
        height=400,
    )

    return fig


def create_trading_signals_chart(trades_df: pd.DataFrame) -> go.Figure:
    """Create trading signals analysis chart"""
    if trades_df.empty:
        return go.Figure()

    # Analyze entry patterns
    recent_trades = trades_df.tail(50)  # Last 50 trades

    fig = go.Figure()

    # Price action simulation (since we don't have real price data)
    # This would normally come from market data API
    price_simulation = []
    base_price = 4500000  # Starting around 4.5M yen/BTC

    for _ in range(len(recent_trades)):
        price_change = np.random.normal(0, 0.02)  # 2% volatility
        price_simulation.append(base_price * (1 + price_change))
        base_price = price_simulation[-1]

    # Price line
    fig.add_trace(
        go.Scatter(
            x=recent_trades["exit_time"],
            y=price_simulation,
            mode="lines",
            name="BTC価格 (シミュレーション)",
            line=dict(color="orange", width=2),
        )
    )

    # Entry points
    winning_trades = recent_trades[recent_trades["profit"] > 0]
    losing_trades = recent_trades[recent_trades["profit"] <= 0]

    if not winning_trades.empty:
        fig.add_trace(
            go.Scatter(
                x=winning_trades["exit_time"],
                y=[
                    price_simulation[i]
                    for i in winning_trades.index - recent_trades.index[0]
                ],
                mode="markers",
                name="勝ちトレード",
                marker=dict(color="green", size=10, symbol="triangle-up"),
            )
        )

    if not losing_trades.empty:
        fig.add_trace(
            go.Scatter(
                x=losing_trades["exit_time"],
                y=[
                    price_simulation[i]
                    for i in losing_trades.index - recent_trades.index[0]
                ],
                mode="markers",
                name="負けトレード",
                marker=dict(color="red", size=10, symbol="triangle-down"),
            )
        )

    fig.update_layout(
        title="📊 トレーディングシグナル分析",
        xaxis_title="時間",
        yaxis_title="価格 (円)",
        hovermode="x unified",
        height=400,
    )

    return fig


def calculate_advanced_metrics(
    trades_df: pd.DataFrame, daily_df: pd.DataFrame
) -> Dict[str, Any]:
    """Calculate advanced trading metrics"""
    if trades_df.empty and daily_df.empty:
        return {}

    metrics = {}

    if not trades_df.empty:
        # Basic metrics
        metrics["total_trades"] = len(trades_df)
        metrics["winning_trades"] = len(trades_df[trades_df["profit"] > 0])
        metrics["losing_trades"] = len(trades_df[trades_df["profit"] <= 0])
        metrics["win_rate"] = (
            metrics["winning_trades"] / metrics["total_trades"]
            if metrics["total_trades"] > 0
            else 0
        )

        # Profit metrics
        metrics["total_profit"] = trades_df["profit"].sum()
        metrics["avg_win"] = (
            trades_df[trades_df["profit"] > 0]["profit"].mean()
            if metrics["winning_trades"] > 0
            else 0
        )
        metrics["avg_loss"] = (
            trades_df[trades_df["profit"] <= 0]["profit"].mean()
            if metrics["losing_trades"] > 0
            else 0
        )

        # Risk metrics
        metrics["profit_factor"] = (
            abs(
                metrics["avg_win"]
                * metrics["winning_trades"]
                / (metrics["avg_loss"] * metrics["losing_trades"])
            )
            if metrics["losing_trades"] > 0 and metrics["avg_loss"] != 0
            else float("inf")
        )

        # Recent performance (last 24 hours)
        recent_cutoff = datetime.now() - timedelta(hours=24)
        recent_trades = trades_df[trades_df["exit_time"] >= recent_cutoff]
        metrics["recent_trades"] = len(recent_trades)
        metrics["recent_profit"] = (
            recent_trades["profit"].sum() if not recent_trades.empty else 0
        )

        # Trading frequency
        if not trades_df.empty:
            time_span = (
                trades_df["exit_time"].max() - trades_df["exit_time"].min()
            ).total_seconds() / 3600  # hours
            metrics["trades_per_hour"] = (
                metrics["total_trades"] / time_span if time_span > 0 else 0
            )

    if not daily_df.empty:
        # Daily metrics
        metrics["trading_days"] = len(daily_df)
        metrics["profitable_days"] = (
            len(daily_df[daily_df["total_pl"] > 0])
            if "total_pl" in daily_df.columns
            else 0
        )
        metrics["daily_win_rate"] = (
            metrics["profitable_days"] / metrics["trading_days"]
            if metrics["trading_days"] > 0
            else 0
        )

        # Drawdown calculation
        if "total_pl" in daily_df.columns:
            cumulative = daily_df["total_pl"].cumsum()
            running_max = cumulative.expanding().max()
            drawdown = cumulative - running_max
            metrics["max_drawdown"] = drawdown.min()
            metrics["current_drawdown"] = drawdown.iloc[-1] if len(drawdown) > 0 else 0

    return metrics


def create_performance_comparison_chart(
    daily_df: pd.DataFrame, backtest_df: pd.DataFrame
) -> go.Figure:
    """Create performance comparison between live and backtest"""
    fig = go.Figure()

    if not daily_df.empty:
        cumulative_live = (
            daily_df["total_pl"].cumsum()
            if "total_pl" in daily_df.columns
            else pd.Series()
        )

        fig.add_trace(
            go.Scatter(
                x=(
                    daily_df["date"]
                    if "date" in daily_df.columns
                    else range(len(daily_df))
                ),
                y=cumulative_live,
                mode="lines",
                name="ライブ運用",
                line=dict(color="blue", width=3),
            )
        )

    if not backtest_df.empty and "cumulative_pnl" in backtest_df.columns:
        fig.add_trace(
            go.Scatter(
                x=range(len(backtest_df)),
                y=backtest_df["cumulative_pnl"],
                mode="lines",
                name="バックテスト",
                line=dict(color="green", width=2, dash="dash"),
            )
        )

    fig.update_layout(
        title="📈 ライブ vs バックテスト パフォーマンス比較",
        xaxis_title="期間",
        yaxis_title="累積損益 (円)",
        hovermode="x unified",
        height=400,
    )

    return fig


# ---------------------- Main Dashboard Layout --------------------------------
# Sidebar configuration
st.sidebar.title("⚙️ 監視設定")

# Alert thresholds
st.sidebar.subheader("🚨 アラート設定")
profit_threshold = st.sidebar.number_input("利益アラート (円)", value=1000, step=100)
loss_threshold = st.sidebar.number_input("損失アラート (円)", value=-500, step=100)
drawdown_threshold = st.sidebar.number_input(
    "ドローダウンアラート (%)", value=5.0, step=0.5
)

# Display options
st.sidebar.subheader("📊 表示オプション")
show_advanced_charts = st.sidebar.checkbox("高度なチャート表示", value=True)
show_trading_signals = st.sidebar.checkbox("トレーディングシグナル", value=True)
show_performance_comparison = st.sidebar.checkbox("パフォーマンス比較", value=False)

# Load all data
data = load_comprehensive_data()
status = data.get("status", {})
daily_df = data.get("daily_pnl", pd.DataFrame())
trades_df = data.get("trades", pd.DataFrame())
backtest_df = data.get("backtest", pd.DataFrame())

# Calculate advanced metrics
metrics = calculate_advanced_metrics(trades_df, daily_df)

# ---------------------- Alert System ----------------------------------------
alert_messages = []

if metrics:
    # Check profit/loss alerts
    recent_profit = metrics.get("recent_profit", 0)
    if recent_profit >= profit_threshold:
        alert_messages.append(
            ("success", f"🎉 24時間利益が目標を達成: {recent_profit:,.0f}円")
        )
    elif recent_profit <= loss_threshold:
        alert_messages.append(
            ("danger", f"⚠️ 24時間損失がアラート閾値を超過: {recent_profit:,.0f}円")
        )

    # Check drawdown
    current_drawdown = metrics.get("current_drawdown", 0)
    if abs(current_drawdown) >= (
        drawdown_threshold / 100 * 100000
    ):  # Assuming 100k starting balance
        alert_messages.append(
            ("warning", f"📉 現在のドローダウン: {current_drawdown:,.0f}円")
        )

# Display alerts
if alert_messages:
    st.subheader("🚨 アラート")
    for alert_type, message in alert_messages:
        st.markdown(
            f"""
        <div class="alert-box alert-{alert_type}">
            {message}
        </div>
        """,
            unsafe_allow_html=True,
        )

# ---------------------- Key Metrics Dashboard --------------------------------
st.header("📊 リアルタイム主要指標")

if metrics:
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "総取引数",
            f"{metrics.get('total_trades', 0):,}",
            delta=f"24h: {metrics.get('recent_trades', 0)}",
        )

    with col2:
        win_rate = metrics.get("win_rate", 0)
        st.metric(
            "勝率",
            f"{win_rate:.1%}",
            delta=f"日次: {metrics.get('daily_win_rate', 0):.1%}",
        )

    with col3:
        total_profit = metrics.get("total_profit", 0)
        recent_profit = metrics.get("recent_profit", 0)
        st.metric(
            "総利益", f"{total_profit:,.0f}円", delta=f"24h: {recent_profit:,.0f}円"
        )

    with col4:
        profit_factor = metrics.get("profit_factor", 0)
        if profit_factor == float("inf"):
            pf_display = "∞"
        else:
            pf_display = f"{profit_factor:.2f}"
        st.metric("プロフィットファクター", pf_display)

    with col5:
        max_dd = metrics.get("max_drawdown", 0)
        current_dd = metrics.get("current_drawdown", 0)
        st.metric("最大DD", f"{max_dd:,.0f}円", delta=f"現在: {current_dd:,.0f}円")

st.divider()

# ---------------------- Advanced Charts Section ------------------------------
if show_advanced_charts:
    st.header("📈 高度な分析チャート")

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        if not trades_df.empty:
            rt_metrics_chart = create_real_time_metrics_chart(trades_df)
            st.plotly_chart(rt_metrics_chart, use_container_width=True)
        else:
            st.info("取引データがありません")

    with chart_col2:
        if show_trading_signals and not trades_df.empty:
            signals_chart = create_trading_signals_chart(trades_df)
            st.plotly_chart(signals_chart, use_container_width=True)
        else:
            st.info("シグナルデータがありません")

# ---------------------- Performance Comparison ------------------------------
if show_performance_comparison:
    st.header("⚖️ パフォーマンス比較分析")
    comparison_chart = create_performance_comparison_chart(daily_df, backtest_df)
    st.plotly_chart(comparison_chart, use_container_width=True)

# ---------------------- System Status & Health ------------------------------
st.header("🔧 システム状態")

health_col1, health_col2, health_col3 = st.columns(3)

with health_col1:
    st.subheader("📁 ファイル状況")
    files_to_check = [
        ("status.json", "ライブ状況"),
        ("results/trade_log.csv", "取引ログ"),
        ("results/aggregate_daily.csv", "日次集計"),
        ("config/bitbank_margin_optimized.yml", "設定ファイル"),
        ("model/calibrated_model.pkl", "MLモデル"),
    ]

    for file_path, description in files_to_check:
        if Path(file_path).exists():
            st.success(f"✅ {description}")
        else:
            st.error(f"❌ {description}")

with health_col2:
    st.subheader("⚡ パフォーマンス")
    if metrics:
        trades_per_hour = metrics.get("trades_per_hour", 0)
        st.metric("取引頻度", f"{trades_per_hour:.2f}/時間")

        avg_win = metrics.get("avg_win", 0)
        avg_loss = metrics.get("avg_loss", 0)
        st.metric("平均勝ち", f"{avg_win:,.0f}円")
        st.metric("平均負け", f"{avg_loss:,.0f}円")

with health_col3:
    st.subheader("🕒 システム情報")
    st.metric("現在時刻", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    st.metric("更新間隔", f"{refresh_interval}秒")

    if status:
        last_updated = status.get("last_updated", "不明")
        st.metric("最終更新", last_updated)

# ---------------------- Raw Data Tables (Expandable) ------------------------
with st.expander("📋 詳細データテーブル"):
    tab1, tab2, tab3 = st.tabs(["最新取引", "日次サマリー", "システム状況"])

    with tab1:
        if not trades_df.empty:
            st.dataframe(trades_df.tail(10), use_container_width=True)
        else:
            st.info("取引データがありません")

    with tab2:
        if not daily_df.empty:
            st.dataframe(daily_df.tail(10), use_container_width=True)
        else:
            st.info("日次データがありません")

    with tab3:
        if status:
            st.json(status)
        else:
            st.info("ステータスデータがありません")

# ---------------------- Footer -----------------------------------------------
st.markdown("---")
st.markdown(
    """
<div style="text-align: center; color: #666;">
    <strong>Crypto-Bot Advanced Monitor</strong> |
    Professional Real-time Trading Dashboard |
    Auto-refresh: {refresh_interval}s |
    Last updated: {timestamp}
</div>
""".format(
        refresh_interval=refresh_interval, timestamp=datetime.now().strftime("%H:%M:%S")
    ),
    unsafe_allow_html=True,
)

# Auto-refresh countdown
if st.sidebar.checkbox("リフレッシュカウンター表示", value=False):
    countdown_placeholder = st.sidebar.empty()
    for i in range(refresh_interval, 0, -1):
        countdown_placeholder.metric("次回更新まで", f"{i}秒")
        time.sleep(1)
    countdown_placeholder.metric("次回更新まで", "更新中...")

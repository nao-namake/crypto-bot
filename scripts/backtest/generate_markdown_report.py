#!/usr/bin/env python3
"""
バックテストMarkdownレポート生成スクリプト

目的: JSON形式のバックテストレポートをMarkdownに変換

使用方法:
    python scripts/backtest/generate_markdown_report.py <json_report_path>

出力先: docs/検証記録/backtest_<YYYYMMDD>.md
"""

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.config.threshold_manager import get_threshold


def load_json_report(json_path: Path) -> Dict[str, Any]:
    """JSONレポート読み込み"""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def format_metric(value: float, decimals: int = 2) -> str:
    """
    Phase 57.7: 指標値のフォーマット（∞対応）

    Args:
        value: 指標値（float or inf）
        decimals: 小数点以下桁数

    Returns:
        フォーマット済み文字列（∞はそのまま表示）
    """
    if value is None:
        return "N/A"
    if math.isinf(value):
        return "∞" if value > 0 else "-∞"
    return f"{value:.{decimals}f}"


def extract_all_trades(regime_perf: Dict[str, Any]) -> list:
    """
    Phase 57.12: 全レジームから取引リストを抽出

    Args:
        regime_perf: レジーム別パフォーマンスデータ

    Returns:
        全取引のリスト
    """
    all_trades = []
    for regime, stats in regime_perf.items():
        trades = stats.get("trades", [])
        all_trades.extend(trades)
    return all_trades


def generate_confidence_stats(trades: list) -> Dict[str, Any]:
    """
    Phase 57.12: 信頼度帯別統計を生成

    Args:
        trades: 取引リスト

    Returns:
        信頼度帯別統計（低/中/高）
    """
    # 信頼度帯に分類
    low_conf = [
        t for t in trades if t.get("ml_confidence") is not None and t["ml_confidence"] < 0.50
    ]
    medium_conf = [
        t
        for t in trades
        if t.get("ml_confidence") is not None and 0.50 <= t["ml_confidence"] < 0.65
    ]
    high_conf = [
        t for t in trades if t.get("ml_confidence") is not None and t["ml_confidence"] >= 0.65
    ]
    no_conf = [t for t in trades if t.get("ml_confidence") is None]

    def calc_stats(trade_list: list) -> Dict[str, Any]:
        if not trade_list:
            return {"count": 0, "win_rate": 0.0, "avg_pnl": 0.0, "total_pnl": 0.0}
        wins = len([t for t in trade_list if t.get("pnl", 0) > 0])
        total_pnl = sum(t.get("pnl", 0) for t in trade_list)
        return {
            "count": len(trade_list),
            "win_rate": (wins / len(trade_list)) * 100 if trade_list else 0.0,
            "avg_pnl": total_pnl / len(trade_list) if trade_list else 0.0,
            "total_pnl": total_pnl,
        }

    return {
        "low": calc_stats(low_conf),
        "medium": calc_stats(medium_conf),
        "high": calc_stats(high_conf),
        "no_data": calc_stats(no_conf),
        "has_confidence_data": len(low_conf) + len(medium_conf) + len(high_conf) > 0,
    }


def generate_position_stats(trades: list) -> Dict[str, Any]:
    """
    Phase 57.12: ポジションサイズ統計を生成

    Args:
        trades: 取引リスト

    Returns:
        ポジションサイズ統計
    """
    amounts = [
        t.get("amount", 0) for t in trades if t.get("amount") is not None and t.get("amount") > 0
    ]
    if not amounts:
        return {"has_data": False}

    return {
        "has_data": True,
        "avg_amount": sum(amounts) / len(amounts),
        "max_amount": max(amounts),
        "min_amount": min(amounts),
        "total_trades": len(amounts),
    }


def generate_strategy_stats(trades: list) -> Dict[str, Any]:
    """
    Phase 57.12: 戦略別統計を生成（レジーム問わず）

    Args:
        trades: 取引リスト

    Returns:
        戦略別のパフォーマンス統計
    """
    stats = {}
    for t in trades:
        strategy = t.get("strategy", "unknown")
        pnl = t.get("pnl", 0)

        if strategy not in stats:
            stats[strategy] = {"count": 0, "wins": 0, "total_pnl": 0.0}

        stats[strategy]["count"] += 1
        if pnl > 0:
            stats[strategy]["wins"] += 1
        stats[strategy]["total_pnl"] += pnl

    # 勝率・平均損益計算
    for strategy, data in stats.items():
        data["win_rate"] = (data["wins"] / data["count"] * 100) if data["count"] > 0 else 0.0
        data["avg_pnl"] = data["total_pnl"] / data["count"] if data["count"] > 0 else 0.0

    return stats


def generate_ml_prediction_stats(trades: list) -> Dict[str, Any]:
    """
    Phase 57.12: ML予測別統計を生成

    Args:
        trades: 取引リスト

    Returns:
        ML予測別のパフォーマンス統計（BUY/HOLD/SELL）
    """
    # ml_prediction: 0=SELL, 1=HOLD, 2=BUY
    prediction_labels = {0: "SELL", 1: "HOLD", 2: "BUY"}
    stats = {
        label: {"count": 0, "wins": 0, "total_pnl": 0.0} for label in prediction_labels.values()
    }
    stats["不明"] = {"count": 0, "wins": 0, "total_pnl": 0.0}

    for t in trades:
        ml_pred = t.get("ml_prediction")
        pnl = t.get("pnl", 0)

        if ml_pred is not None and ml_pred in prediction_labels:
            label = prediction_labels[ml_pred]
        else:
            label = "不明"

        stats[label]["count"] += 1
        if pnl > 0:
            stats[label]["wins"] += 1
        stats[label]["total_pnl"] += pnl

    # 勝率・平均損益計算
    for label, data in stats.items():
        data["win_rate"] = (data["wins"] / data["count"] * 100) if data["count"] > 0 else 0.0
        data["avg_pnl"] = data["total_pnl"] / data["count"] if data["count"] > 0 else 0.0

    return stats


def generate_ml_strategy_agreement(trades: list) -> Dict[str, Any]:
    """
    Phase 57.12: ML×戦略一致率分析を生成

    戦略のBUY/SELL決定とML予測が一致しているかを分析。
    - 一致: 戦略BUY + ML BUY、または 戦略SELL + ML SELL
    - 不一致: 上記以外（ML HOLDを含む）

    Args:
        trades: 取引リスト

    Returns:
        一致/不一致時のパフォーマンス統計
    """
    # ml_prediction: 0=SELL, 1=HOLD, 2=BUY
    match_trades = []
    mismatch_trades = []
    ml_hold_trades = []

    for t in trades:
        side = t.get("side", "").lower()
        ml_pred = t.get("ml_prediction")

        if ml_pred is None:
            continue

        # ML HOLDの場合は別カウント
        if ml_pred == 1:
            ml_hold_trades.append(t)
            mismatch_trades.append(t)
            continue

        # 一致判定: 戦略BUY + ML BUY(2)、または 戦略SELL + ML SELL(0)
        is_match = (side == "buy" and ml_pred == 2) or (side == "sell" and ml_pred == 0)

        if is_match:
            match_trades.append(t)
        else:
            mismatch_trades.append(t)

    def calc_stats(trade_list: list) -> Dict[str, Any]:
        if not trade_list:
            return {"count": 0, "wins": 0, "win_rate": 0.0, "total_pnl": 0.0, "avg_pnl": 0.0}
        wins = len([t for t in trade_list if t.get("pnl", 0) > 0])
        total_pnl = sum(t.get("pnl", 0) for t in trade_list)
        return {
            "count": len(trade_list),
            "wins": wins,
            "win_rate": (wins / len(trade_list) * 100) if trade_list else 0.0,
            "total_pnl": total_pnl,
            "avg_pnl": total_pnl / len(trade_list) if trade_list else 0.0,
        }

    return {
        "match": calc_stats(match_trades),
        "mismatch": calc_stats(mismatch_trades),
        "ml_hold": calc_stats(ml_hold_trades),
        "has_data": len(match_trades) + len(mismatch_trades) > 0,
    }


def generate_strategy_regime_matrix(trades: list) -> Dict[str, Dict[str, Any]]:
    """
    Phase 57.12: 戦略×レジーム クロス集計を生成

    Args:
        trades: 取引リスト

    Returns:
        戦略×レジーム別のパフォーマンス統計
    """
    matrix = {}
    for t in trades:
        strategy = t.get("strategy", "unknown")
        regime = t.get("regime", "unknown")
        pnl = t.get("pnl", 0)

        if strategy not in matrix:
            matrix[strategy] = {}
        if regime not in matrix[strategy]:
            matrix[strategy][regime] = {"count": 0, "wins": 0, "total_pnl": 0.0}

        matrix[strategy][regime]["count"] += 1
        if pnl > 0:
            matrix[strategy][regime]["wins"] += 1
        matrix[strategy][regime]["total_pnl"] += pnl

    # 勝率・PF計算
    for strategy, regimes in matrix.items():
        for regime, stats in regimes.items():
            stats["win_rate"] = (
                (stats["wins"] / stats["count"] * 100) if stats["count"] > 0 else 0.0
            )
            stats["avg_pnl"] = stats["total_pnl"] / stats["count"] if stats["count"] > 0 else 0.0

    return matrix


def generate_daily_pnl(trades: list) -> Dict[str, Any]:
    """
    Phase 57.11: 日毎損益分析

    Args:
        trades: 取引リスト（exit_timestamp含む）

    Returns:
        日毎損益データ
    """
    if not trades:
        return {"has_data": False}

    # 取引を日付でグループ化（exit_timestampを使用）
    daily_pnl = defaultdict(lambda: {"pnl": 0.0, "trades": 0, "wins": 0})

    for trade in trades:
        # exit_timestampから日付を抽出
        exit_ts = trade.get("exit_timestamp")
        if not exit_ts:
            continue

        try:
            # ISO形式文字列からdatetimeに変換
            if isinstance(exit_ts, str):
                exit_dt = datetime.fromisoformat(exit_ts.replace("Z", "+00:00"))
            else:
                exit_dt = exit_ts

            date_str = exit_dt.strftime("%Y-%m-%d")
            pnl = trade.get("pnl", 0)

            daily_pnl[date_str]["pnl"] += pnl
            daily_pnl[date_str]["trades"] += 1
            if pnl > 0:
                daily_pnl[date_str]["wins"] += 1
        except Exception:
            continue

    if not daily_pnl:
        return {"has_data": False}

    # 日付順にソート
    sorted_dates = sorted(daily_pnl.keys())

    # 累積損益計算
    cumulative = 0.0
    daily_data = []
    for date_str in sorted_dates:
        data = daily_pnl[date_str]
        cumulative += data["pnl"]
        daily_data.append(
            {
                "date": date_str,
                "pnl": data["pnl"],
                "cumulative": cumulative,
                "trades": data["trades"],
                "wins": data["wins"],
                "win_rate": (data["wins"] / data["trades"] * 100) if data["trades"] > 0 else 0.0,
            }
        )

    # 最良日・最悪日
    best_day = max(daily_data, key=lambda x: x["pnl"])
    worst_day = min(daily_data, key=lambda x: x["pnl"])

    # 利益日数・損失日数
    profitable_days = len([d for d in daily_data if d["pnl"] > 0])
    losing_days = len([d for d in daily_data if d["pnl"] < 0])
    breakeven_days = len([d for d in daily_data if d["pnl"] == 0])

    # 平均日次損益
    avg_daily_pnl = sum(d["pnl"] for d in daily_data) / len(daily_data) if daily_data else 0.0

    return {
        "has_data": True,
        "daily_data": daily_data,
        "best_day": best_day,
        "worst_day": worst_day,
        "profitable_days": profitable_days,
        "losing_days": losing_days,
        "breakeven_days": breakeven_days,
        "avg_daily_pnl": avg_daily_pnl,
        "total_days": len(daily_data),
    }


def generate_monthly_pnl(daily_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Phase 57.11: 月別パフォーマンス集計

    Args:
        daily_data: 日毎データリスト

    Returns:
        月別パフォーマンスリスト
    """
    if not daily_data:
        return []

    monthly = defaultdict(lambda: {"pnl": 0.0, "trades": 0, "wins": 0})

    for day in daily_data:
        # YYYY-MM形式で月を取得
        month_str = day["date"][:7]
        monthly[month_str]["pnl"] += day["pnl"]
        monthly[month_str]["trades"] += day["trades"]
        monthly[month_str]["wins"] += day["wins"]

    # 月順にソート
    sorted_months = sorted(monthly.keys())

    monthly_data = []
    for month_str in sorted_months:
        data = monthly[month_str]
        monthly_data.append(
            {
                "month": month_str,
                "pnl": data["pnl"],
                "trades": data["trades"],
                "wins": data["wins"],
                "win_rate": (data["wins"] / data["trades"] * 100) if data["trades"] > 0 else 0.0,
            }
        )

    return monthly_data


def generate_equity_curve_ascii(
    daily_data: List[Dict[str, Any]], width: int = 60, height: int = 12
) -> str:
    """
    Phase 57.11: ASCII損益曲線生成

    Args:
        daily_data: 日毎データリスト（cumulative含む）
        width: グラフ幅（文字数）
        height: グラフ高さ（行数）

    Returns:
        ASCII損益曲線文字列
    """
    if not daily_data or len(daily_data) < 2:
        return "（データ不足のため損益曲線を生成できません）"

    # 累積損益を取得
    cumulative_values = [d["cumulative"] for d in daily_data]
    min_val = min(cumulative_values)
    max_val = max(cumulative_values)

    # 値域が0の場合（全て同じ値）
    if max_val == min_val:
        max_val = min_val + 1

    # Y軸のスケーリング
    def scale_y(value: float) -> int:
        return int((value - min_val) / (max_val - min_val) * (height - 1))

    # X軸のサンプリング（データポイントをwidth個に圧縮）
    step = max(1, len(cumulative_values) // width)
    sampled_indices = list(range(0, len(cumulative_values), step))[:width]

    # グラフ生成
    canvas = [[" " for _ in range(width)] for _ in range(height)]

    # 0ラインの位置
    zero_y = scale_y(0) if min_val <= 0 <= max_val else -1

    # 0ラインを描画
    if 0 <= zero_y < height:
        for x in range(width):
            if canvas[height - 1 - zero_y][x] == " ":
                canvas[height - 1 - zero_y][x] = "-"

    # 曲線を描画
    prev_y = None
    for x, idx in enumerate(sampled_indices):
        y = scale_y(cumulative_values[idx])

        # 垂直線で前のポイントと接続
        if prev_y is not None and abs(y - prev_y) > 1:
            for fill_y in range(min(prev_y, y) + 1, max(prev_y, y)):
                if 0 <= fill_y < height:
                    canvas[height - 1 - fill_y][x - 1] = "|"

        if 0 <= y < height:
            canvas[height - 1 - y][x] = "*"

        prev_y = y

    # Y軸ラベル生成
    y_labels = []
    for i in range(height):
        value = min_val + (max_val - min_val) * (height - 1 - i) / (height - 1)
        y_labels.append(f"¥{value:>+8,.0f}")

    # 出力文字列生成
    lines = []
    for i, row in enumerate(canvas):
        line = y_labels[i] + " |" + "".join(row)
        lines.append(line)

    # X軸
    x_axis = " " * 10 + "+" + "-" * width
    lines.append(x_axis)

    # X軸ラベル（月を表示）
    if daily_data:
        first_month = daily_data[0]["date"][:7]
        last_month = daily_data[-1]["date"][:7]
        x_label = (
            " " * 11 + first_month + " " * (width - len(first_month) - len(last_month)) + last_month
        )
        lines.append(x_label)

    return "\n".join(lines)


def generate_markdown_report(report_data: Dict[str, Any]) -> str:
    """
    Markdownレポート生成

    Args:
        report_data: JSONレポートデータ

    Returns:
        Markdown形式の文字列
    """
    # データ抽出
    backtest_info = report_data.get("backtest_info", {})
    perf = report_data.get("performance_metrics", {})
    regime_perf = report_data.get("regime_performance", {})
    exec_stats = report_data.get("execution_stats", {})

    # Phase 57.12: 全取引データ抽出
    all_trades = extract_all_trades(regime_perf)

    # 実行日時
    start_date = backtest_info.get("start_date", "N/A")
    end_date = backtest_info.get("end_date", "N/A")
    duration_days = backtest_info.get("duration_days", 0)

    # 日付を整形（ISO形式 → YYYY/MM/DD）
    try:
        start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        start_date_str = start_dt.strftime("%Y/%m/%d")
        end_date_str = end_dt.strftime("%Y/%m/%d")
    except Exception:
        start_date_str = start_date
        end_date_str = end_date

    # パフォーマンス指標
    total_trades = perf.get("total_trades", 0)
    winning_trades = perf.get("winning_trades", 0)
    losing_trades = perf.get("losing_trades", 0)
    win_rate = perf.get("win_rate", 0.0)
    total_pnl = perf.get("total_pnl", 0.0)
    total_profit = perf.get("total_profit", 0.0)
    total_loss = perf.get("total_loss", 0.0)
    profit_factor = perf.get("profit_factor", 0.0)
    max_dd = perf.get("max_drawdown", 0.0)
    max_dd_pct = perf.get("max_drawdown_pct", 0.0)
    avg_win = perf.get("average_win", 0.0)
    avg_loss = perf.get("average_loss", 0.0)

    # Phase 53: 追加指標（重要度別）
    sharpe_ratio = perf.get("sharpe_ratio", 0.0)
    expectancy = perf.get("expectancy", 0.0)
    recovery_factor = perf.get("recovery_factor", 0.0)
    sortino_ratio = perf.get("sortino_ratio", 0.0)
    calmar_ratio = perf.get("calmar_ratio", 0.0)
    payoff_ratio = perf.get("payoff_ratio", 0.0)
    max_consecutive_wins = perf.get("max_consecutive_wins", 0)
    max_consecutive_losses = perf.get("max_consecutive_losses", 0)
    trades_per_month = perf.get("trades_per_month", 0.0)

    # 1取引あたり損益
    avg_pnl_per_trade = total_pnl / total_trades if total_trades > 0 else 0.0

    # Markdown生成
    report_date = datetime.now().strftime("%Y/%m/%d")
    lines = [
        f"# バックテスト記録 - {report_date}",
        "",
        f"**実施日**: {report_date}",
        "",
        "---",
        "",
        "## 実施目的",
        "",
        "定期バックテスト実行による戦略パフォーマンス検証。",
        f"{duration_days}日間のBTC/JPY 15分足データを使用し、本番環境と同一ロジックで検証。",
        "",
        "---",
        "",
        "## 実行概要",
        "",
        f"- **バックテスト期間**: {start_date_str} ~ {end_date_str} ({duration_days}日間)",
        "- **データソース**: CSV (15分足 + 4時間足)",
        f"- **初期残高**: ¥{get_threshold('mode_balances.backtest.initial_balance', 100000):,.0f}",
        "- **取引ペア**: BTC/JPY",
        "- **レバレッジ**: 1.0倍",
        "",
        "---",
        "",
        "## 設定値",
        "",
        "### TP/SL設定",
        "",
        "レジーム別動的TP/SL設定（Phase 52.0実装）:",
        "",
        "| レジーム | TP | SL | 適用ケース |",
        "|----------|----|----|-----------|",
        "| tight_range | 0.8% | 0.6% | レンジ相場（狭い値動き） |",
        "| normal_range | 1.0% | 0.7% | 通常相場 |",
        "| trending | 1.5% | 1.0% | トレンド相場 |",
        "",
        "### レジーム別エントリー制限",
        "",
        f"- tight_range: 最大{get_threshold('position_limits.tight_range', 6)}ポジション",
        f"- normal_range: 最大{get_threshold('position_limits.normal_range', 4)}ポジション",
        f"- trending: 最大{get_threshold('position_limits.trending', 2)}ポジション",
        "",
        "### ML統合設定",
        "",
        "- アンサンブルモデル: LightGBM (50%) + XGBoost (30%) + RandomForest (20%)",
        "- 最小信頼度閾値: 0.45",
        "- 高信頼度閾値: 0.60",
        "",
        "---",
        "",
        "## エントリー統計",
        "",
        f"- **総エントリー数**: {total_trades}件",
        f"- **勝ちトレード**: {winning_trades}件",
        f"- **負けトレード**: {losing_trades}件",
        f"- **勝率**: {win_rate:.1f}%",
        "",
    ]

    # レジーム別パフォーマンス
    if regime_perf:
        lines.extend(
            [
                "---",
                "",
                "## レジーム別パフォーマンス（Phase 51.8-J4-G）",
                "",
                "| レジーム | エントリー数 | 勝率 | 平均損益/取引 | 総損益 |",
                "|---------|------------|------|-------------|--------|",
            ]
        )

        for regime, stats in regime_perf.items():
            regime_total = stats.get("total_trades", 0)
            regime_win_rate = stats.get("win_rate", 0.0)
            regime_avg_pnl = stats.get("average_pnl", 0.0)
            regime_total_pnl = stats.get("total_pnl", 0.0)

            regime_display = {
                "tight_range": "レンジ（狭）",
                "normal_range": "レンジ（通常）",
                "trending": "トレンド",
                "unknown": "不明",
            }.get(regime, regime)

            lines.append(
                f"| {regime_display} | {regime_total}件 | "
                f"{regime_win_rate:.1f}% | ¥{regime_avg_pnl:+,.0f} | ¥{regime_total_pnl:+,.0f} |"
            )

        lines.extend(["", ""])

    # Phase 57.12: 信頼度帯別パフォーマンス
    conf_stats = generate_confidence_stats(all_trades)
    if conf_stats["has_confidence_data"]:
        lines.extend(
            [
                "---",
                "",
                "## 信頼度帯別パフォーマンス（Phase 57.12追加）",
                "",
                "| 信頼度帯 | 取引数 | 勝率 | 平均損益/取引 | 総損益 |",
                "|---------|--------|------|-------------|--------|",
            ]
        )
        for level, label in [
            ("low", "低（<50%）"),
            ("medium", "中（50-65%）"),
            ("high", "高（≥65%）"),
        ]:
            stats = conf_stats[level]
            if stats["count"] > 0:
                lines.append(
                    f"| {label} | {stats['count']}件 | "
                    f"{stats['win_rate']:.1f}% | ¥{stats['avg_pnl']:+,.0f} | ¥{stats['total_pnl']:+,.0f} |"
                )
        if conf_stats["no_data"]["count"] > 0:
            nd = conf_stats["no_data"]
            lines.append(
                f"| データなし | {nd['count']}件 | "
                f"{nd['win_rate']:.1f}% | ¥{nd['avg_pnl']:+,.0f} | ¥{nd['total_pnl']:+,.0f} |"
            )
        lines.extend(["", ""])

    # Phase 57.12: ポジションサイズ統計
    pos_stats = generate_position_stats(all_trades)
    if pos_stats["has_data"]:
        lines.extend(
            [
                "---",
                "",
                "## ポジションサイズ統計（Phase 57.12追加）",
                "",
                f"- **平均ポジションサイズ**: {pos_stats['avg_amount']:.6f} BTC",
                f"- **最大ポジションサイズ**: {pos_stats['max_amount']:.6f} BTC",
                f"- **最小ポジションサイズ**: {pos_stats['min_amount']:.6f} BTC",
                "",
            ]
        )

    # Phase 57.12: 戦略別パフォーマンス
    strategy_stats = generate_strategy_stats(all_trades)
    non_unknown_strategies = [s for s in strategy_stats.keys() if s != "unknown"]
    if non_unknown_strategies:
        lines.extend(
            [
                "---",
                "",
                "## 戦略別パフォーマンス（Phase 57.12追加）",
                "",
                "| 戦略 | 取引数 | 勝率 | 平均損益/取引 | 総損益 |",
                "|------|--------|------|-------------|--------|",
            ]
        )
        # 総損益の降順でソート
        sorted_strategies = sorted(
            [(s, d) for s, d in strategy_stats.items() if s != "unknown"],
            key=lambda x: x[1]["total_pnl"],
            reverse=True,
        )
        for strategy, data in sorted_strategies:
            lines.append(
                f"| {strategy} | {data['count']}件 | "
                f"{data['win_rate']:.1f}% | ¥{data['avg_pnl']:+,.0f} | ¥{data['total_pnl']:+,.0f} |"
            )
        lines.extend(["", ""])

    # Phase 57.12: ML予測別パフォーマンス
    ml_stats = generate_ml_prediction_stats(all_trades)
    has_ml_data = any(ml_stats[label]["count"] > 0 for label in ["BUY", "SELL", "HOLD"])
    if has_ml_data:
        lines.extend(
            [
                "---",
                "",
                "## ML予測別パフォーマンス（Phase 57.12追加）",
                "",
                "| ML予測 | 取引数 | 勝率 | 平均損益/取引 | 総損益 |",
                "|--------|--------|------|-------------|--------|",
            ]
        )
        for label in ["BUY", "SELL", "HOLD"]:
            data = ml_stats[label]
            if data["count"] > 0:
                lines.append(
                    f"| {label} | {data['count']}件 | "
                    f"{data['win_rate']:.1f}% | ¥{data['avg_pnl']:+,.0f} | ¥{data['total_pnl']:+,.0f} |"
                )
        if ml_stats["不明"]["count"] > 0:
            data = ml_stats["不明"]
            lines.append(
                f"| 不明 | {data['count']}件 | "
                f"{data['win_rate']:.1f}% | ¥{data['avg_pnl']:+,.0f} | ¥{data['total_pnl']:+,.0f} |"
            )
        lines.extend(["", ""])

    # Phase 57.12: ML×戦略一致率分析
    agreement_stats = generate_ml_strategy_agreement(all_trades)
    if agreement_stats["has_data"]:
        match = agreement_stats["match"]
        mismatch = agreement_stats["mismatch"]
        ml_hold = agreement_stats["ml_hold"]

        lines.extend(
            [
                "---",
                "",
                "## ML×戦略一致率分析（Phase 57.12追加）",
                "",
                "戦略シグナルとML予測の一致/不一致による勝率・損益の違いを分析。",
                "",
                "| 区分 | 取引数 | 勝率 | 平均損益/取引 | 総損益 |",
                "|------|--------|------|-------------|--------|",
            ]
        )
        if match["count"] > 0:
            lines.append(
                f"| **一致**（戦略=ML） | {match['count']}件 | "
                f"{match['win_rate']:.1f}% | ¥{match['avg_pnl']:+,.0f} | ¥{match['total_pnl']:+,.0f} |"
            )
        if mismatch["count"] > 0:
            lines.append(
                f"| 不一致（戦略≠ML） | {mismatch['count']}件 | "
                f"{mismatch['win_rate']:.1f}% | ¥{mismatch['avg_pnl']:+,.0f} | ¥{mismatch['total_pnl']:+,.0f} |"
            )
        if ml_hold["count"] > 0:
            lines.append(
                f"| └ ML HOLD時 | {ml_hold['count']}件 | "
                f"{ml_hold['win_rate']:.1f}% | ¥{ml_hold['avg_pnl']:+,.0f} | ¥{ml_hold['total_pnl']:+,.0f} |"
            )

        # 一致率計算
        total_with_ml = match["count"] + mismatch["count"]
        if total_with_ml > 0:
            match_rate = match["count"] / total_with_ml * 100
            lines.extend(
                [
                    "",
                    f"**一致率**: {match_rate:.1f}% ({match['count']}/{total_with_ml}件)",
                ]
            )

            # 勝率差の評価
            if match["count"] > 0 and mismatch["count"] > 0:
                win_rate_diff = match["win_rate"] - mismatch["win_rate"]
                if win_rate_diff > 5:
                    lines.append(
                        f"**評価**: 一致時の勝率が{win_rate_diff:.1f}pt高い → ML予測を重視すべき"
                    )
                elif win_rate_diff < -5:
                    lines.append(
                        f"**評価**: 不一致時の勝率が{-win_rate_diff:.1f}pt高い → 戦略シグナルを重視すべき"
                    )
                else:
                    lines.append("**評価**: 勝率差は小さい → 両者の相関は弱い")

        lines.extend(["", ""])

    # Phase 57.12: 戦略×レジーム クロス集計
    strategy_matrix = generate_strategy_regime_matrix(all_trades)
    # unknownのみの場合はスキップ
    non_unknown_strategies_matrix = [s for s in strategy_matrix.keys() if s != "unknown"]
    if non_unknown_strategies_matrix:
        lines.extend(
            [
                "---",
                "",
                "## 戦略×レジーム クロス集計（Phase 57.12追加）",
                "",
                "| 戦略 | レジーム | 取引数 | 勝率 | 平均損益/取引 | 総損益 |",
                "|------|---------|--------|------|-------------|--------|",
            ]
        )
        regime_display = {
            "tight_range": "レンジ（狭）",
            "normal_range": "レンジ（通常）",
            "trending": "トレンド",
            "unknown": "不明",
        }
        for strategy in sorted(strategy_matrix.keys()):
            if strategy == "unknown":
                continue
            for regime, stats in strategy_matrix[strategy].items():
                reg_name = regime_display.get(regime, regime)
                lines.append(
                    f"| {strategy} | {reg_name} | {stats['count']}件 | "
                    f"{stats['win_rate']:.1f}% | ¥{stats['avg_pnl']:+,.0f} | ¥{stats['total_pnl']:+,.0f} |"
                )
        lines.extend(["", ""])

    # Phase 57.11: 日毎損益分析
    daily_pnl_stats = generate_daily_pnl(all_trades)
    if daily_pnl_stats["has_data"]:
        lines.extend(
            [
                "---",
                "",
                "## 日毎損益分析（Phase 57.11追加）",
                "",
                "### 損益曲線",
                "",
                "```",
                generate_equity_curve_ascii(daily_pnl_stats["daily_data"]),
                "```",
                "",
                "### 日別サマリー",
                "",
                "| 指標 | 値 |",
                "|------|-----|",
                f"| 取引日数 | {daily_pnl_stats['total_days']}日 |",
                f"| 利益日数 | {daily_pnl_stats['profitable_days']}日 |",
                f"| 損失日数 | {daily_pnl_stats['losing_days']}日 |",
                f"| 最良日 | {daily_pnl_stats['best_day']['date']} (¥{daily_pnl_stats['best_day']['pnl']:+,.0f}) |",
                f"| 最悪日 | {daily_pnl_stats['worst_day']['date']} (¥{daily_pnl_stats['worst_day']['pnl']:+,.0f}) |",
                f"| 平均日次損益 | ¥{daily_pnl_stats['avg_daily_pnl']:+,.0f} |",
                "",
            ]
        )

        # 月別パフォーマンス
        monthly_data = generate_monthly_pnl(daily_pnl_stats["daily_data"])
        if monthly_data:
            lines.extend(
                [
                    "### 月別パフォーマンス",
                    "",
                    "| 月 | 取引数 | 勝率 | 総損益 |",
                    "|----|--------|------|--------|",
                ]
            )
            for m in monthly_data:
                lines.append(
                    f"| {m['month']} | {m['trades']}件 | {m['win_rate']:.1f}% | ¥{m['pnl']:+,.0f} |"
                )
            lines.extend(["", ""])

    # パフォーマンス指標
    lines.extend(
        [
            "---",
            "",
            "## パフォーマンス指標",
            "",
            "### 損益サマリー",
            "",
            f"- **総損益**: ¥{total_pnl:+,.0f}",
            f"- **総利益**: ¥{total_profit:+,.0f}",
            f"- **総損失**: ¥{total_loss:+,.0f}",
            f"- **平均損益/取引**: ¥{avg_pnl_per_trade:+,.0f}",
            "",
            "### リスク指標",
            "",
            f"- **最大ドローダウン**: ¥{max_dd:,.0f} ({max_dd_pct:.2f}%)",
            f"- **プロフィットファクター**: {format_metric(profit_factor)}",
            f"- **平均勝ちトレード**: ¥{avg_win:+,.0f}",
            f"- **平均負けトレード**: ¥{avg_loss:+,.0f}",
            "",
            "### 取引品質",
            "",
            f"- **勝率**: {win_rate:.1f}%",
            (
                f"- **リスクリワード比**: {abs(avg_win / avg_loss):.2f}:1 (平均)"
                if avg_loss != 0
                else "- **リスクリワード比**: N/A"
            ),
            "",
        ]
    )

    # Phase 53: 詳細評価指標（重要度別）
    lines.extend(
        [
            "---",
            "",
            "## 詳細評価指標（Phase 53追加）",
            "",
            "### 重要指標（必須確認）",
            "",
            "| 指標 | 値 | 判定基準 |",
            "|------|-----|---------|",
        ]
    )

    # シャープレシオ評価（Phase 57.7: ∞対応）
    if math.isinf(sharpe_ratio):
        sharpe_eval = "優秀（∞）"
    else:
        sharpe_eval = (
            "優秀"
            if sharpe_ratio >= 2.0
            else "良好" if sharpe_ratio >= 1.0 else "普通" if sharpe_ratio >= 0 else "要注意"
        )
    lines.append(
        f"| シャープレシオ | {format_metric(sharpe_ratio)} | {sharpe_eval}（≥1.0で良好） |"
    )

    # 期待値評価
    exp_eval = "良好" if expectancy > 0 else "要改善"
    lines.append(f"| 期待値 | ¥{expectancy:+,.0f} | {exp_eval}（>0で収益期待） |")

    # リカバリーファクター評価（Phase 57.7: ∞対応）
    if math.isinf(recovery_factor):
        rf_eval = "優秀（DD=0）"
    else:
        rf_eval = (
            "優秀" if recovery_factor >= 3.0 else "良好" if recovery_factor >= 1.0 else "要注意"
        )
    lines.append(
        f"| リカバリーファクター | {format_metric(recovery_factor)} | {rf_eval}（≥1.0でDD回復） |"
    )

    lines.extend(
        [
            "",
            "### 参考指標",
            "",
            "| 指標 | 値 | 説明 |",
            "|------|-----|------|",
        ]
    )

    # ソルティノレシオ（Phase 57.7: ∞対応）
    lines.append(f"| ソルティノレシオ | {format_metric(sortino_ratio)} | 下方リスク調整リターン |")

    # カルマーレシオ（Phase 57.7: ∞対応）
    lines.append(f"| カルマーレシオ | {format_metric(calmar_ratio)} | 年率リターン/最大DD |")

    # ペイオフレシオ（Phase 57.7: ∞対応）
    lines.append(f"| ペイオフレシオ | {format_metric(payoff_ratio)} | 平均勝ち/平均負け比 |")

    lines.extend(
        [
            "",
            "### 補助指標",
            "",
            "| 指標 | 値 |",
            "|------|-----|",
            f"| 最大連勝数 | {max_consecutive_wins}回 |",
            f"| 最大連敗数 | {max_consecutive_losses}回 |",
            f"| 月間取引頻度 | {trades_per_month:.1f}回/月 |",
            "",
            "---",
            "",
            "## 結論",
            "",
        ]
    )

    # 自動結論生成（Phase 52.0の効果評価）
    if total_trades > 0:
        # 収益性評価（Phase 57.7: ∞対応）
        profitability = "収益性あり" if total_pnl > 0 else "損失発生"
        if math.isinf(profit_factor):
            pf_eval = "優秀（損失なし）"
        else:
            pf_eval = (
                "優秀" if profit_factor >= 1.5 else "良好" if profit_factor >= 1.0 else "要改善"
            )
        win_rate_eval = "高い" if win_rate >= 50 else "中程度" if win_rate >= 40 else "低い"

        lines.extend(
            [
                f"### 総合評価: {profitability}",
                "",
                f"- **プロフィットファクター {format_metric(profit_factor)}**: {pf_eval}",
                f"- **勝率 {win_rate:.1f}%**: {win_rate_eval}",
                f"- **最大DD {max_dd_pct:.2f}%**: {'許容範囲内' if max_dd_pct < 30 else '要注意'}",
                "",
            ]
        )

        # レジーム別評価
        if regime_perf:
            lines.append("### レジーム別評価")
            lines.append("")

            best_regime = None
            best_avg_pnl = float("-inf")

            for regime, stats in regime_perf.items():
                regime_avg = stats.get("average_pnl", 0.0)
                if regime_avg > best_avg_pnl:
                    best_avg_pnl = regime_avg
                    best_regime = regime

            if best_regime:
                regime_display = {
                    "tight_range": "レンジ（狭）",
                    "normal_range": "レンジ（通常）",
                    "trending": "トレンド",
                }.get(best_regime, best_regime)

                lines.append(
                    f"最も収益性が高いレジーム: **{regime_display}** (平均¥{best_avg_pnl:+,.0f}/取引)"
                )
                lines.append("")

        # Phase 52.0効果評価
        lines.extend(
            [
                "### Phase 52.0実装効果",
                "",
                "レジーム別動的TP/SL調整の効果を検証。",
                "",
                "- tight_rangeでのTP 0.8%/SL 0.6%設定による早期利確・損切り",
                "- trendingでのTP 1.5%/SL 1.0%設定によるトレンドフォロー",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "### エントリーなし",
                "",
                "バックテスト期間中、エントリー条件を満たす取引機会が検出されませんでした。",
                "",
            ]
        )

    lines.extend(
        [
            "---",
            "",
            f"**レポート生成日時**: {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}",
        ]
    )

    return "\n".join(lines)


def save_markdown_report(markdown_content: str, output_dir: Path):
    """
    Markdownレポート保存

    Args:
        markdown_content: Markdown内容
        output_dir: 出力ディレクトリ
    """
    # ファイル名生成: backtest_20251221.md
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"backtest_{date_str}.md"
    filepath = output_dir / filename

    # ディレクトリ作成
    output_dir.mkdir(parents=True, exist_ok=True)

    # ファイル保存
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    print(f"✅ Markdownレポート生成完了: {filepath}")
    return filepath


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description="バックテストJSONレポートをMarkdownに変換")
    parser.add_argument(
        "json_path",
        type=str,
        help="JSONレポートファイルパス（例: src/backtest/logs/backtest_20251112_120000.json）",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="docs/検証記録",
        help="出力ディレクトリ（デフォルト: docs/検証記録）",
    )

    args = parser.parse_args()

    # パス準備
    json_path = Path(args.json_path)
    output_dir = Path(args.output_dir)

    # JSONレポート読み込み
    if not json_path.exists():
        print(f"❌ エラー: JSONファイルが見つかりません: {json_path}")
        return 1

    print(f"📄 JSONレポート読み込み: {json_path}")
    report_data = load_json_report(json_path)

    # Markdown生成
    print("🔧 Markdownレポート生成中...")
    markdown_content = generate_markdown_report(report_data)

    # Markdown保存
    save_markdown_report(markdown_content, output_dir)

    return 0


if __name__ == "__main__":
    exit(main())

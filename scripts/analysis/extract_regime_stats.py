#!/usr/bin/env python3
"""
Phase 51.8-9: レジーム別統計抽出スクリプト

バックテストログファイルからレジーム分類情報とエントリー/エグジット情報を抽出し、
レジーム別のパフォーマンス統計を生成する。

使用方法:
    python3 scripts/analysis/extract_regime_stats.py backtest_phase51.8_j4h_test.log
"""

import re
import sys
from collections import defaultdict
from typing import Dict, List


def extract_regime_from_log(log_path: str) -> Dict[str, any]:
    """
    ログファイルからレジーム別統計を抽出

    Args:
        log_path: ログファイルパス

    Returns:
        レジーム別統計辞書
    """
    # レジーム別カウンター
    regime_counts = defaultdict(int)
    regime_entries = defaultdict(list)
    regime_exits = defaultdict(list)

    # エントリー/エグジット情報格納
    entries = {}  # order_id -> {regime, price, timestamp, strategy}
    exits = []  # [{entry_order_id, exit_price, pnl, ...}]

    current_regime = None
    current_timestamp = None

    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            # レジーム分類検出（Phase 51.8-J4-Gで追加したWARNINGログ）
            regime_match = re.search(
                r"(⚠️ 高ボラティリティ検出|📊 狭いレンジ検出|📈 トレンド検出|📊 通常レンジ検出|📊 デフォルト分類)",
                line,
            )
            if regime_match:
                regime_type = regime_match.group(1)
                if "高ボラティリティ" in regime_type:
                    current_regime = "high_volatility"
                elif "狭いレンジ" in regime_type:
                    current_regime = "tight_range"
                elif "トレンド" in regime_type:
                    current_regime = "trending"
                else:  # 通常レンジ or デフォルト
                    current_regime = "normal_range"

                regime_counts[current_regime] += 1

                # タイムスタンプ抽出
                ts_match = re.search(r"\[([^\]]+)\]", line)
                if ts_match:
                    current_timestamp = ts_match.group(1)

            # エントリー検出
            entry_match = re.search(
                r"💰 \[BACKTEST\] (BUY|SELL)エントリー成功.*price=([\d.]+).*order_id=(\d+).*strategy=(\w+)",
                line,
            )
            if entry_match and current_regime:
                side = entry_match.group(1)
                price = float(entry_match.group(2))
                order_id = entry_match.group(3)
                strategy = entry_match.group(4)

                entries[order_id] = {
                    "regime": current_regime,
                    "price": price,
                    "timestamp": current_timestamp,
                    "strategy": strategy,
                    "side": side,
                }
                regime_entries[current_regime].append(order_id)

            # エグジット検出
            exit_match = re.search(
                r"💰 \[BACKTEST\] (TP|SL)決済成功.*entry_order_id=(\d+).*exit_price=([\d.]+).*pnl=([-\d.]+)",
                line,
            )
            if exit_match:
                exit_reason = exit_match.group(1)
                entry_order_id = exit_match.group(2)
                exit_price = float(exit_match.group(3))
                pnl = float(exit_match.group(4))

                if entry_order_id in entries:
                    entry_info = entries[entry_order_id]
                    regime = entry_info["regime"]

                    exits.append(
                        {
                            "regime": regime,
                            "entry_price": entry_info["price"],
                            "exit_price": exit_price,
                            "pnl": pnl,
                            "exit_reason": exit_reason,
                            "strategy": entry_info["strategy"],
                            "side": entry_info["side"],
                        }
                    )
                    regime_exits[regime].append(pnl)

    # 統計計算
    stats = {}
    for regime in ["tight_range", "normal_range", "trending", "high_volatility"]:
        trade_count = len(regime_exits[regime])
        if trade_count == 0:
            stats[regime] = {
                "detection_count": regime_counts[regime],
                "entry_count": len(regime_entries[regime]),
                "trade_count": 0,
                "total_pnl": 0.0,
                "avg_pnl": 0.0,
                "win_count": 0,
                "loss_count": 0,
                "win_rate": 0.0,
            }
            continue

        pnls = regime_exits[regime]
        total_pnl = sum(pnls)
        avg_pnl = total_pnl / trade_count
        win_count = sum(1 for p in pnls if p > 0)
        loss_count = sum(1 for p in pnls if p < 0)
        win_rate = (win_count / trade_count * 100) if trade_count > 0 else 0.0

        stats[regime] = {
            "detection_count": regime_counts[regime],
            "entry_count": len(regime_entries[regime]),
            "trade_count": trade_count,
            "total_pnl": total_pnl,
            "avg_pnl": avg_pnl,
            "win_count": win_count,
            "loss_count": loss_count,
            "win_rate": win_rate,
        }

    return {
        "regime_stats": stats,
        "total_entries": len(entries),
        "total_exits": len(exits),
        "all_trades": exits,
    }


def print_regime_stats(data: Dict[str, any]) -> None:
    """
    レジーム別統計を表示

    Args:
        data: extract_regime_from_log()の戻り値
    """
    print("=" * 80)
    print("📊 Phase 51.8-9: レジーム別パフォーマンス統計")
    print("=" * 80)
    print()

    stats = data["regime_stats"]

    regime_names = {
        "tight_range": "狭いレンジ",
        "normal_range": "通常レンジ",
        "trending": "トレンド",
        "high_volatility": "高ボラティリティ",
    }

    total_trades = sum(s["trade_count"] for s in stats.values())
    total_pnl = sum(s["total_pnl"] for s in stats.values())

    print(f"📌 全体サマリー:")
    print(f"  - 総エントリー数: {data['total_entries']}件")
    print(f"  - 総エグジット数: {data['total_exits']}件")
    print(f"  - 総取引数: {total_trades}件")
    print(f"  - 総損益: ¥{total_pnl:+.0f}")
    print()

    print("📊 レジーム別詳細:")
    print("-" * 80)
    print(
        f"{'レジーム':<15} {'検出':<6} {'エントリー':<8} {'取引':<6} "
        f"{'勝率':<8} {'平均損益':<10} {'総損益':<10}"
    )
    print("-" * 80)

    for regime, name in regime_names.items():
        s = stats[regime]
        if s["trade_count"] == 0:
            print(
                f"{name:<15} {s['detection_count']:>6} {s['entry_count']:>8} "
                f"{s['trade_count']:>6} {'N/A':<8} {'N/A':<10} {'¥0':<10}"
            )
        else:
            print(
                f"{name:<15} {s['detection_count']:>6} {s['entry_count']:>8} "
                f"{s['trade_count']:>6} {s['win_rate']:>6.1f}% "
                f"¥{s['avg_pnl']:>+8.0f} ¥{s['total_pnl']:>+8.0f}"
            )

    print("-" * 80)
    print()

    # レジーム別寄与度分析
    print("📈 レジーム別寄与度分析:")
    print("-" * 80)

    for regime, name in regime_names.items():
        s = stats[regime]
        if total_trades == 0 or s["trade_count"] == 0:
            continue

        trade_ratio = s["trade_count"] / total_trades * 100
        pnl_ratio = s["total_pnl"] / total_pnl * 100 if total_pnl != 0 else 0.0

        print(f"{name}:")
        print(f"  - 取引シェア: {trade_ratio:.1f}% ({s['trade_count']}/{total_trades}件)")
        print(f"  - 損益シェア: {pnl_ratio:+.1f}% (¥{s['total_pnl']:+.0f}/¥{total_pnl:+.0f})")
        print(f"  - 勝率: {s['win_rate']:.1f}% ({s['win_count']}/{s['trade_count']}勝)")
        print()

    print("=" * 80)


def suggest_optimization(data: Dict[str, any]) -> None:
    """
    最適化提案を生成

    Args:
        data: extract_regime_from_log()の戻り値
    """
    print()
    print("=" * 80)
    print("💡 Phase 51.8-9: データドリブンな最適化提案")
    print("=" * 80)
    print()

    stats = data["regime_stats"]

    # 各レジームのパフォーマンス評価
    regime_scores = {}
    for regime, s in stats.items():
        if s["trade_count"] == 0:
            regime_scores[regime] = 0.0
            continue

        # スコア計算: 勝率 × 平均損益（正規化）
        win_rate = s["win_rate"] / 100.0  # 0-1スケール
        avg_pnl_normalized = max(0, min(1, (s["avg_pnl"] + 100) / 200))  # -100~100 → 0~1
        score = win_rate * 0.6 + avg_pnl_normalized * 0.4

        regime_scores[regime] = score

    print("📊 レジーム別パフォーマンススコア（0-1スケール）:")
    regime_names = {
        "tight_range": "狭いレンジ",
        "normal_range": "通常レンジ",
        "trending": "トレンド",
        "high_volatility": "高ボラティリティ",
    }

    for regime, name in regime_names.items():
        score = regime_scores[regime]
        s = stats[regime]
        print(
            f"  - {name}: {score:.3f} "
            f"(勝率{s['win_rate']:.1f}%, 平均¥{s['avg_pnl']:+.0f}, {s['trade_count']}取引)"
        )

    print()
    print("💡 推奨戦略重み設定:")
    print()

    # 最適重み計算（スコアベース）
    total_score = sum(regime_scores.values())
    if total_score == 0:
        print("⚠️  警告: スコア合計がゼロのため、重み計算不可")
        return

    print("```yaml")
    print("# config/core/regime_weights.yaml（新規作成推奨）")
    print()
    print("regime_weights:")
    for regime in ["tight_range", "normal_range", "trending", "high_volatility"]:
        score = regime_scores[regime]
        weight = score / total_score
        print(f"  {regime}: {weight:.3f}  # スコア: {score:.3f}")

    print("```")
    print()
    print("📝 実装手順:")
    print("1. dynamic_strategy_selector.pyに重み設定を反映")
    print("2. レジーム別で戦略信頼度を調整（高スコアレジーム → 高重み）")
    print("3. バックテストで検証（期待収益改善: +10-30%）")
    print()
    print("=" * 80)


def main():
    if len(sys.argv) < 2:
        print("使用方法: python3 extract_regime_stats.py <log_file>")
        print(
            "例: python3 scripts/analysis/extract_regime_stats.py backtest_phase51.8_j4h_test.log"
        )
        sys.exit(1)

    log_path = sys.argv[1]

    print(f"📂 ログファイル読み込み中: {log_path}")
    print()

    data = extract_regime_from_log(log_path)
    print_regime_stats(data)
    suggest_optimization(data)


if __name__ == "__main__":
    main()

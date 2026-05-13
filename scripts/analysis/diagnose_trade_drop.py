#!/usr/bin/env python3
"""
Phase 66: 取引数激減の根本原因診断スクリプト

旧モデル(535取引) → 新モデル(46取引) の原因を特定する。
仮説: ML Signal Recoveryが旧モデルでは大量発動し、新モデルでは発動しない。

使用方法:
    python scripts/analysis/diagnose_trade_drop.py
"""

import asyncio
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

# プロジェクトルートをパスに追加
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# 設定読み込み
from src.core.config import load_config

try:
    load_config("config/core/thresholds.yaml")
except Exception:
    pass

from src.core.config.feature_manager import get_feature_names
from src.core.config.threshold_manager import get_threshold
from src.core.services.market_regime_classifier import MarketRegimeClassifier
from src.features.feature_generator import FeatureGenerator


def load_data():
    """バックテスト用CSVデータを読み込み"""
    from src.backtest.data.csv_data_loader import get_csv_loader

    csv_loader = get_csv_loader()

    # バックテスト期間設定
    from datetime import datetime

    use_fixed = get_threshold("execution.backtest_use_fixed_dates", False)
    if use_fixed:
        start_str = get_threshold("execution.backtest_start_date", "2025-07-01")
        end_str = get_threshold("execution.backtest_end_date", "2025-12-31")
        start_date = datetime.strptime(start_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    else:
        from datetime import timedelta

        backtest_days = get_threshold("execution.backtest_period_days", 30)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=backtest_days)

    csv_data = csv_loader.load_multi_timeframe(
        symbol="BTC/JPY",
        timeframes=["15m"],
        start_date=start_date,
        end_date=end_date,
        limit=get_threshold("backtest.data_limit", 10000),
    )

    main_df = csv_data.get("15m", pd.DataFrame())
    print(f"📊 データ読み込み: {len(main_df)}件 ({start_date} ~ {end_date})")
    return main_df


def load_ml_model():
    """現在のMLモデルを読み込み"""
    from src.core.logger import CryptoBotLogger
    from src.core.orchestration.ml_adapter import MLServiceAdapter

    logger = CryptoBotLogger()
    ml_service = MLServiceAdapter(logger)
    print(f"🤖 MLモデル読み込み: {ml_service.model_type}")
    return ml_service


def build_strategy_manager():
    """StrategyManagerを正しく初期化"""
    from src.strategies.base.strategy_manager import StrategyManager
    from src.strategies.strategy_loader import StrategyLoader

    loader = StrategyLoader()
    strategies_data = loader.load_strategies()
    strategy_names = [s["metadata"]["name"] for s in strategies_data]

    strategy_manager = StrategyManager()
    for s_data in strategies_data:
        instance = s_data["instance"]
        weight = s_data.get("weight", 1.0)
        strategy_manager.register_strategy(instance, weight)

    print(f"  登録戦略: {strategy_names} ({len(strategy_names)}戦略)")
    return strategy_manager, strategy_names


def compute_strategy_signals(main_df):
    """全キャンドルで戦略シグナルを計算"""
    feature_gen = FeatureGenerator()
    strategy_manager, strategy_names = build_strategy_manager()

    total_rows = len(main_df)
    print(f"🎯 戦略シグナル計算開始: {total_rows}件")

    results = []
    progress_interval = max(1, total_rows // 10)

    for i in range(total_rows):
        historical_data = main_df.iloc[: i + 1]

        if i % progress_interval == 0 and i > 0:
            progress = (i / total_rows) * 100
            print(f"  進捗: {progress:.0f}% ({i}/{total_rows})")

        if len(historical_data) < 20:
            results.append(
                {
                    "index": i,
                    "combined_action": "hold",
                    "individual_signals": {},
                }
            )
            continue

        try:
            features_df = feature_gen.generate_features_sync(historical_data)
            if features_df.empty:
                results.append(
                    {
                        "index": i,
                        "combined_action": "hold",
                        "individual_signals": {},
                    }
                )
                continue

            all_features = {"15m": features_df}

            # 個別戦略シグナル取得
            individual_signals = strategy_manager.get_individual_strategy_signals(
                features_df, multi_timeframe_data=all_features
            )

            # 統合シグナル取得
            combined_signal = strategy_manager.analyze_market(
                features_df, multi_timeframe_data=all_features
            )

            results.append(
                {
                    "index": i,
                    "combined_action": combined_signal.action,
                    "combined_confidence": combined_signal.confidence,
                    "individual_signals": individual_signals,
                }
            )

        except Exception as e:
            results.append(
                {
                    "index": i,
                    "combined_action": "hold",
                    "individual_signals": {},
                    "error": str(e),
                }
            )

    print(f"✅ 戦略シグナル計算完了: {len(results)}件")
    return results


def compute_ml_predictions(main_df, ml_service):
    """全キャンドルでML予測を実行"""
    feature_gen = FeatureGenerator()
    features_to_use = get_feature_names()

    # 全データの特徴量を一括生成
    print("🤖 ML予測用特徴量生成中...")
    features_df = feature_gen.generate_features_sync(main_df)

    available_features = [col for col in features_to_use if col in features_df.columns]
    if len(available_features) != len(features_to_use):
        print(f"⚠️ 特徴量不足: {len(available_features)}/{len(features_to_use)}")
        # 不足分を0埋め
        for col in features_to_use:
            if col not in features_df.columns:
                features_df[col] = 0.0

    # 戦略シグナル特徴量を計算して追加
    strategy_manager, strategy_names = build_strategy_manager()
    total_rows = len(main_df)
    strategy_signal_columns = {f"strategy_signal_{name}": [] for name in strategy_names}

    print(f"🎯 戦略シグナル特徴量計算中: {total_rows}件")
    progress_interval = max(1, total_rows // 10)

    for i in range(total_rows):
        historical_data = main_df.iloc[: i + 1]

        if i % progress_interval == 0 and i > 0:
            print(f"  進捗: {(i / total_rows) * 100:.0f}%")

        if len(historical_data) < 20:
            for col in strategy_signal_columns:
                strategy_signal_columns[col].append(0.0)
            continue

        try:
            hist_features = feature_gen.generate_features_sync(historical_data)
            if hist_features.empty:
                for col in strategy_signal_columns:
                    strategy_signal_columns[col].append(0.0)
                continue

            all_features = {"15m": hist_features}
            strategy_signals = strategy_manager.get_individual_strategy_signals(
                hist_features, multi_timeframe_data=all_features
            )

            for name in strategy_names:
                col = f"strategy_signal_{name}"
                if name in strategy_signals:
                    strategy_signal_columns[col].append(strategy_signals[name].get("encoded", 0.0))
                else:
                    strategy_signal_columns[col].append(0.0)

        except Exception:
            for col in strategy_signal_columns:
                strategy_signal_columns[col].append(0.0)

    # 特徴量DataFrameに戦略シグナルカラムを追加
    for col_name, values in strategy_signal_columns.items():
        if len(values) == len(features_df):
            features_df[col_name] = values

    # ML予測実行
    print("🤖 ML一括予測実行中...")
    ml_features = features_df[features_to_use]
    predictions = ml_service.predict(ml_features)
    probabilities = ml_service.predict_proba(ml_features)

    ml_action_map = {0: "sell", 1: "hold", 2: "buy"}
    ml_results = []
    for i in range(len(predictions)):
        pred = int(predictions[i])
        conf = float(np.max(probabilities[i]))
        action = ml_action_map.get(pred, "hold")
        ml_results.append(
            {
                "index": i,
                "prediction": pred,
                "action": action,
                "confidence": conf,
                "probabilities": probabilities[i].tolist(),
            }
        )

    print(f"✅ ML予測完了: {len(ml_results)}件")
    return ml_results


def analyze_recovery(strategy_results, ml_results):
    """ML Signal Recoveryの発動分析"""
    recovery_config = get_threshold("ml.strategy_integration.ml_signal_recovery", {})
    current_min_ml = recovery_config.get("min_ml_confidence", 0.45)
    min_individual = recovery_config.get("min_individual_confidence", 0.30)

    print("\n" + "=" * 70)
    print("📊 ML Signal Recovery 診断結果")
    print("=" * 70)

    # 現在の設定値
    print("\n🔧 現在のRecovery設定:")
    print(f"  min_ml_confidence: {current_min_ml}")
    print(f"  min_individual_confidence: {min_individual}")
    print(f"  recovery_confidence_cap: {recovery_config.get('recovery_confidence_cap', 0.30)}")
    print(f"  enabled: {recovery_config.get('enabled', False)}")

    # ML予測の統計
    ml_actions = Counter(r["action"] for r in ml_results)
    ml_confidences = [r["confidence"] for r in ml_results]
    buy_confidences = [r["confidence"] for r in ml_results if r["action"] == "buy"]
    sell_confidences = [r["confidence"] for r in ml_results if r["action"] == "sell"]
    hold_confidences = [r["confidence"] for r in ml_results if r["action"] == "hold"]

    print("\n📈 ML予測統計:")
    print(f"  総予測数: {len(ml_results)}")
    total = len(ml_results)
    print(f"  BUY: {ml_actions['buy']} ({ml_actions['buy'] / total * 100:.1f}%)")
    print(f"  HOLD: {ml_actions['hold']} ({ml_actions['hold'] / total * 100:.1f}%)")
    print(f"  SELL: {ml_actions['sell']} ({ml_actions['sell'] / total * 100:.1f}%)")
    print(
        f"\n  全体 信頼度: 平均={np.mean(ml_confidences):.3f}, "
        f"中央値={np.median(ml_confidences):.3f}, "
        f"最大={np.max(ml_confidences):.3f}"
    )
    if buy_confidences:
        print(
            f"  BUY  信頼度: 平均={np.mean(buy_confidences):.3f}, "
            f"中央値={np.median(buy_confidences):.3f}"
        )
    if sell_confidences:
        print(
            f"  SELL 信頼度: 平均={np.mean(sell_confidences):.3f}, "
            f"中央値={np.median(sell_confidences):.3f}"
        )
    if hold_confidences:
        print(
            f"  HOLD 信頼度: 平均={np.mean(hold_confidences):.3f}, "
            f"中央値={np.median(hold_confidences):.3f}"
        )

    # 戦略集約の統計
    combined_actions = Counter(r["combined_action"] for r in strategy_results)
    print("\n📊 戦略集約統計:")
    print(f"  BUY: {combined_actions['buy']}")
    print(f"  SELL: {combined_actions['sell']}")
    print(f"  HOLD: {combined_actions['hold']}")
    natural_trades = combined_actions.get("buy", 0) + combined_actions.get("sell", 0)
    print(f"  自然な取引数 (BUY+SELL): {natural_trades}")

    # Recovery発動分析（複数閾値で比較）
    thresholds_to_test = [0.30, 0.33, 0.35, 0.38, 0.40, 0.45, 0.50]

    print("\n🔄 ML Signal Recovery 発動シミュレーション:")
    print(f"  {'閾値':>6} | {'Recovery発動':>12} | {'合計取引':>10} | {'説明'}")
    sep = "-"
    print(f"  {sep * 6}-+-{sep * 12}-+-{sep * 10}-+-{sep * 30}")

    for threshold in thresholds_to_test:
        recovery_count = 0
        recovery_buys = 0
        recovery_sells = 0

        for sr, mr in zip(strategy_results, ml_results):
            if sr["combined_action"] != "hold":
                continue
            if mr["action"] == "hold":
                continue
            if mr["confidence"] < threshold:
                continue

            # 個別戦略でML方向に同意するものがあるかチェック
            has_agreeing = False
            for name, sig in sr.get("individual_signals", {}).items():
                if sig.get("action") == mr["action"] and sig.get("confidence", 0) >= min_individual:
                    has_agreeing = True
                    break

            if has_agreeing:
                recovery_count += 1
                if mr["action"] == "buy":
                    recovery_buys += 1
                else:
                    recovery_sells += 1

        total = natural_trades + recovery_count
        marker = " ← 現在" if threshold == current_min_ml else ""
        print(
            f"  {threshold:>6.2f} | {recovery_count:>12} | {total:>10} | "
            f"BUY={recovery_buys}, SELL={recovery_sells}{marker}"
        )

    # ML信頼度分布のヒストグラム（テキスト版）
    print("\n📊 ML BUY/SELL信頼度分布:")
    non_hold_confidences = [r["confidence"] for r in ml_results if r["action"] != "hold"]
    if non_hold_confidences:
        bins = [0.30, 0.33, 0.35, 0.38, 0.40, 0.45, 0.50, 0.55, 0.60, 1.0]
        for j in range(len(bins) - 1):
            count = sum(1 for c in non_hold_confidences if bins[j] <= c < bins[j + 1])
            bar_len = count // max(1, len(non_hold_confidences) // 50)
            bar = "█" * bar_len
            lo = bins[j]
            hi = bins[j + 1]
            print(f"  {lo:.2f}-{hi:.2f}: {count:>5} {bar}")

    # Recovery発動の詳細（上位10件）
    print("\n📋 Recovery発動例（閾値=0.35、上位10件）:")
    examples = []
    for idx, (sr, mr) in enumerate(zip(strategy_results, ml_results)):
        if sr["combined_action"] != "hold":
            continue
        if mr["action"] == "hold":
            continue
        if mr["confidence"] < 0.35:
            continue

        agreeing = []
        for name, sig in sr.get("individual_signals", {}).items():
            if sig.get("action") == mr["action"] and sig.get("confidence", 0) >= min_individual:
                agreeing.append(f"{name}({sig['confidence']:.3f})")

        if agreeing:
            examples.append(
                {
                    "index": idx,
                    "ml_action": mr["action"],
                    "ml_confidence": mr["confidence"],
                    "agreeing": ", ".join(agreeing),
                }
            )

    for ex in examples[:10]:
        print(
            f"  [{ex['index']:>5}] ML={ex['ml_action'].upper()}({ex['ml_confidence']:.3f}) "
            f"支持: {ex['agreeing']}"
        )

    return natural_trades


def main():
    """メイン実行"""
    import os
    import time

    os.environ["BACKTEST_MODE"] = "true"

    print("=" * 70)
    print("Phase 66: 取引数激減 根本原因診断")
    print("=" * 70)

    start_time = time.time()

    # 1. データ読み込み
    main_df = load_data()
    if main_df.empty:
        print("❌ データが空です")
        return

    # 2. MLモデル読み込み
    ml_service = load_ml_model()

    # 3. 戦略シグナル計算
    strategy_results = compute_strategy_signals(main_df)

    # 4. ML予測計算
    ml_results = compute_ml_predictions(main_df, ml_service)

    # 5. Recovery分析
    natural_trades = analyze_recovery(strategy_results, ml_results)

    elapsed = time.time() - start_time
    print(f"\n⏱ 診断完了: {elapsed:.1f}秒")

    # 結論
    print("\n" + "=" * 70)
    print("📋 結論")
    print("=" * 70)
    print(f"  自然な取引数（戦略集約BUY/SELL）: {natural_trades}")
    print("  → 仮説検証: 自然取引≈46ならRecovery依存が原因")
    print("  → 推奨: min_ml_confidence を 0.35 に調整")


if __name__ == "__main__":
    main()

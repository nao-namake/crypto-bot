#!/usr/bin/env python3
"""
Phase 4 戦略システム テスト

4つの戦略システムの動作確認と統合テスト
- MochipoyAlertStrategy: EMA + MACD + RCI組み合わせ戦略
- ATRBasedStrategy: ボラティリティベース逆張り戦略
- MultiTimeframeStrategy: 複数時間軸統合戦略
- FibonacciRetracementStrategy: フィボナッチレベル反転戦略
- StrategyManager: 4戦略統合管理システム

実行方法:
    python3 tests/manual/test_phase4_strategies.py

Phase 4テスト実装日: 2025年8月18日.
"""

import os
import sys
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# プロジェクトルートのパス追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# テスト対象のインポート
try:
    from src.strategies.base.strategy_manager import StrategyManager
    from src.strategies.implementations.atr_based import ATRBasedStrategy
    from src.strategies.implementations.fibonacci_retracement import FibonacciRetracementStrategy
    from src.strategies.implementations.mochipoy_alert import MochipoyAlertStrategy
    from src.strategies.implementations.multi_timeframe import MultiTimeframeStrategy

    # 定数を直接定義（インポートエラー回避）
    class StrategyType:
        MOCHIPOY_ALERT = "mochipoy_alert"
        ATR_BASED = "atr_based"
        MULTI_TIMEFRAME = "multi_timeframe"
        FIBONACCI_RETRACEMENT = "fibonacci"

    class SignalStrength:
        WEAK = 0.3
        MEDIUM = 0.5
        STRONG = 0.7
        VERY_STRONG = 0.9

    class EntryAction:
        BUY = "buy"
        SELL = "sell"
        HOLD = "hold"
        CLOSE = "close"

    from src.core.logger import get_logger
    from src.features.anomaly import AnomalyDetector
    from src.features.technical import TechnicalIndicators
except ImportError as e:
    print(f"❌ インポートエラー: {e}")
    print("プロジェクトルートから実行してください: python3 tests/manual/test_phase4_strategies.py")
    sys.exit(1)


def create_comprehensive_sample_data(rows: int = 200) -> pd.DataFrame:
    """
    包括的なテスト用サンプルデータ生成（特徴量付き）

    Args:
        rows: データ行数

    Returns:
        全特徴量付きデータフレーム.
    """
    np.random.seed(42)  # 再現性のために固定

    # より複雑な価格パターン生成
    base_price = 1000.0
    trend_component = np.linspace(0, 0.1, rows)  # 10%の上昇トレンド
    cycle_component = 0.05 * np.sin(np.linspace(0, 4 * np.pi, rows))  # サイクル成分
    noise_component = np.random.normal(0, 0.01, rows)  # ノイズ

    price_changes = trend_component + cycle_component + noise_component
    prices = [base_price]

    for change in price_changes[1:]:
        new_price = prices[-1] * (1 + change)
        prices.append(max(new_price, 1.0))

    prices = np.array(prices)

    # OHLCV生成
    data = []
    for i in range(rows):
        close = prices[i]
        volatility = np.random.uniform(0.005, 0.025)

        high = close * (1 + volatility * np.random.uniform(0.2, 1.0))
        low = close * (1 - volatility * np.random.uniform(0.2, 1.0))
        open_price = np.random.uniform(low, high)
        volume = np.random.uniform(1000, 10000) * (
            1 + abs(price_changes[i]) * 5
        )  # ボラティリティ連動

        data.append(
            {
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "timestamp": datetime.now() - timedelta(hours=rows - i),
            }
        )

    df = pd.DataFrame(data)

    # 特徴量エンジニアリング実行
    try:
        # テクニカル指標生成
        tech_indicators = TechnicalIndicators()
        df = tech_indicators.generate_all_features(df)

        # 異常検知指標生成
        anomaly_detector = AnomalyDetector()
        df = anomaly_detector.generate_all_features(df)

        print(f"📊 特徴量付きサンプルデータ生成完了: {len(df)}行, {len(df.columns)}列")

    except Exception as e:
        print(f"⚠️  特徴量生成エラー: {e}")
        print("基本OHLCVデータのみで継続")

    return df


def test_individual_strategies():
    """個別戦略テスト."""
    print("\n🔧 === 個別戦略テスト ===")

    # サンプルデータ生成
    df = create_comprehensive_sample_data(150)
    print(f"📊 テストデータ: {len(df)}行")

    strategies_to_test = [
        ("MochipoyAlert", MochipoyAlertStrategy),
        ("ATRBased", ATRBasedStrategy),
        ("MultiTimeframe", MultiTimeframeStrategy),
        ("FibonacciRetracement", FibonacciRetracementStrategy),
    ]

    test_results = []

    for strategy_name, strategy_class in strategies_to_test:
        print(f"\n📈 {strategy_name}戦略テスト中...")

        try:
            # 戦略初期化
            strategy = strategy_class()

            # 必要特徴量確認
            required_features = strategy.get_required_features()
            missing_features = [f for f in required_features if f not in df.columns]

            if missing_features:
                print(f"  ⚠️  必要特徴量不足: {missing_features}")
                test_results.append(
                    (strategy_name, False, f"必要特徴量不足: {len(missing_features)}個")
                )
                continue

            # シグナル生成実行
            start_time = time.time()
            signal = strategy.generate_signal(df)
            generation_time = time.time() - start_time

            # 結果検証
            is_valid_signal = signal is not None
            has_valid_action = signal.action in ["buy", "sell", "hold", "close"]
            has_valid_confidence = 0.0 <= signal.confidence <= 1.0
            has_valid_strength = 0.0 <= signal.strength <= 1.0

            # 戦略情報取得
            strategy_info = strategy.get_info()

            success = all(
                [is_valid_signal, has_valid_action, has_valid_confidence, has_valid_strength]
            )

            # 結果表示
            print(f"  ⏱️  生成時間: {generation_time:.3f}秒")
            print(f"  📊 アクション: {signal.action}")
            print(f"  📊 信頼度: {signal.confidence:.3f}")
            print(f"  📊 強度: {signal.strength:.3f}")
            print(f"  📊 現在価格: {signal.current_price:.2f}")

            if signal.stop_loss:
                print(f"  📊 ストップロス: {signal.stop_loss:.2f}")
            if signal.take_profit:
                print(f"  📊 利確価格: {signal.take_profit:.2f}")
            if signal.position_size:
                print(f"  📊 ポジションサイズ: {signal.position_size:.4f}")

            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {status}")

            test_results.append((strategy_name, success, "正常" if success else "検証失敗"))

        except Exception as e:
            print(f"  ❌ エラー: {e}")
            test_results.append((strategy_name, False, f"エラー: {str(e)[:50]}"))

    return test_results


def test_strategy_manager():
    """戦略マネージャーテスト."""
    print("\n🚀 === 戦略マネージャーテスト ===")

    try:
        # サンプルデータ生成
        df = create_comprehensive_sample_data(150)
        print(f"📊 テストデータ: {len(df)}行")

        # 戦略マネージャー初期化
        manager = StrategyManager()

        # 4つの戦略を登録
        strategies = [
            (MochipoyAlertStrategy(), 1.0),
            (ATRBasedStrategy(), 0.8),
            (MultiTimeframeStrategy(), 0.9),
            (FibonacciRetracementStrategy(), 0.7),
        ]

        for strategy, weight in strategies:
            manager.register_strategy(strategy, weight)

        print(f"📋 登録戦略数: {len(manager.strategies)}")

        # 統合市場分析実行
        start_time = time.time()
        combined_signal = manager.analyze_market(df)
        analysis_time = time.time() - start_time

        # 結果検証
        is_valid_combined = combined_signal is not None
        has_manager_name = combined_signal.strategy_name == "StrategyManager"
        has_valid_metadata = combined_signal.metadata is not None

        # パフォーマンス統計取得
        strategy_performance = manager.get_strategy_performance()
        manager_stats = manager.get_manager_stats()

        # 結果表示
        print(f"⏱️  統合分析時間: {analysis_time:.3f}秒")
        print(f"📊 統合アクション: {combined_signal.action}")
        print(f"📊 統合信頼度: {combined_signal.confidence:.3f}")
        print(f"📊 統合強度: {combined_signal.strength:.3f}")
        print(
            f"📊 メタデータ要素数: {len(combined_signal.metadata) if combined_signal.metadata else 0}"
        )

        # 個別戦略パフォーマンス
        print("\n📈 個別戦略状況:")
        for strategy_name, perf in strategy_performance.items():
            print(f"  {strategy_name}: 重み={perf['weight']}, 有効={perf['is_enabled']}")

        # マネージャー統計
        print(f"\n📊 マネージャー統計:")
        print(f"  総戦略数: {manager_stats['total_strategies']}")
        print(f"  有効戦略数: {manager_stats['enabled_strategies']}")
        print(f"  総決定数: {manager_stats['total_decisions']}")
        print(f"  コンフリクト数: {manager_stats['signal_conflicts']}")
        print(f"  コンフリクト率: {manager_stats['conflict_rate']:.1f}%")

        # 成功判定
        success = all(
            [
                is_valid_combined,
                has_manager_name,
                has_valid_metadata,
                analysis_time < 5.0,  # 5秒以内
                manager_stats["enabled_strategies"] == 4,  # 全戦略有効
            ]
        )

        status = "✅ PASS" if success else "❌ FAIL"
        print(f"\n{status} 戦略マネージャーテスト")

        return success, combined_signal

    except Exception as e:
        print(f"❌ 戦略マネージャーテストエラー: {e}")
        import traceback

        traceback.print_exc()
        return False, None


def test_strategy_conflict_resolution():
    """戦略コンフリクト解決テスト."""
    print("\n⚔️ === コンフリクト解決テスト ===")

    try:
        # コンフリクトが発生しやすいデータ作成
        conflict_data = create_comprehensive_sample_data(100)

        # 価格急変動を追加（コンフリクト誘発）
        conflict_data.loc[conflict_data.index[-10:], "close"] *= 1.05  # 最後10期間で5%上昇
        conflict_data.loc[conflict_data.index[-5:], "close"] *= 0.98  # 最後5期間で2%下落

        # 戦略マネージャー設定（コンフリクト検出用）
        manager = StrategyManager({"min_conflict_threshold": 0.05})  # 低い閾値でコンフリクト検出

        # 戦略登録（意図的に重みを変える）
        manager.register_strategy(MochipoyAlertStrategy(), 1.0)
        manager.register_strategy(ATRBasedStrategy(), 1.5)  # 高重み
        manager.register_strategy(MultiTimeframeStrategy(), 0.8)
        manager.register_strategy(FibonacciRetracementStrategy(), 1.2)

        # 複数回実行してコンフリクト発生を観察
        conflict_tests = []
        for i in range(5):
            print(f"\n  テスト {i+1}/5:")

            # データ微調整（ランダム性追加）
            test_data = conflict_data.copy()
            noise = np.random.normal(0, 0.005, len(test_data))
            test_data["close"] *= 1 + noise

            # 特徴量再計算
            tech_indicators = TechnicalIndicators()
            test_data = tech_indicators.generate_all_features(test_data)

            anomaly_detector = AnomalyDetector()
            test_data = anomaly_detector.generate_all_features(test_data)

            # 統合分析
            signal = manager.analyze_market(test_data)

            # 結果記録
            conflict_tests.append(
                {
                    "test_id": i + 1,
                    "action": signal.action,
                    "confidence": signal.confidence,
                    "has_conflict_metadata": "conflict_resolved" in (signal.metadata or {}),
                    "resolution_method": (
                        signal.metadata.get("resolution_method") if signal.metadata else None
                    ),
                }
            )

            print(f"    アクション: {signal.action}, 信頼度: {signal.confidence:.3f}")
            if signal.metadata and "conflict_resolved" in signal.metadata:
                print(
                    f"    🔥 コンフリクト解決: {signal.metadata.get('resolution_method', 'unknown')}"
                )

        # コンフリクト統計
        manager_stats = manager.get_manager_stats()
        conflict_rate = manager_stats["conflict_rate"]
        total_conflicts = manager_stats["signal_conflicts"]

        print(f"\n📊 コンフリクト統計:")
        print(f"  総コンフリクト数: {total_conflicts}")
        print(f"  コンフリクト率: {conflict_rate:.1f}%")
        print(
            f"  解決されたテスト: {sum(1 for t in conflict_tests if t['has_conflict_metadata'])}/5"
        )

        # 成功判定（少なくとも1回のコンフリクト解決を期待）
        success = total_conflicts > 0 or any(t["has_conflict_metadata"] for t in conflict_tests)

        status = "✅ PASS" if success else "⚠️  コンフリクト未発生"
        print(f"\n{status} コンフリクト解決テスト")

        return success

    except Exception as e:
        print(f"❌ コンフリクト解決テストエラー: {e}")
        return False


def test_strategy_performance_tracking():
    """戦略パフォーマンス追跡テスト."""
    print("\n📈 === パフォーマンス追跡テスト ===")

    try:
        df = create_comprehensive_sample_data(80)

        # 戦略初期化
        strategy = MochipoyAlertStrategy()

        # 複数回実行してパフォーマンス追跡
        signals = []
        for i in range(10):
            # データ部分取得（時系列シミュレーション）
            end_idx = min(50 + i * 5, len(df))
            partial_df = df.iloc[:end_idx].copy()

            # 特徴量再生成
            tech_indicators = TechnicalIndicators()
            partial_df = tech_indicators.generate_all_features(partial_df)

            signal = strategy.generate_signal(partial_df)
            signals.append(signal)

            # 成功/失敗をランダムシミュレーション
            success = np.random.random() > 0.4  # 60%成功率
            strategy.update_performance(success)

        # パフォーマンス統計取得
        signal_stats = strategy.get_signal_stats()
        strategy_info = strategy.get_info()

        print(f"📊 生成シグナル数: {signal_stats['total']}")
        print(f"📊 成功率: {signal_stats['success_rate']:.1f}%")
        print(f"📊 平均信頼度: {signal_stats['avg_confidence']:.3f}")

        # アクション別統計
        print("📊 アクション別統計:")
        for action, count in signal_stats["by_action"].items():
            print(f"  {action}: {count}回")

        # 成功判定
        success = (
            signal_stats["total"] == 10
            and signal_stats["success_rate"] >= 0
            and signal_stats["avg_confidence"] >= 0
        )

        status = "✅ PASS" if success else "❌ FAIL"
        print(f"\n{status} パフォーマンス追跡テスト")

        return success

    except Exception as e:
        print(f"❌ パフォーマンス追跡テストエラー: {e}")
        return False


def main():
    """メインテスト実行."""
    print("🎯 Phase 4 戦略システム テスト開始")
    print("=" * 60)

    # ログ設定
    logger = get_logger()
    logger.info("Phase 4戦略テスト開始")

    # テスト実行
    test_results = []

    # 1. 個別戦略テスト
    individual_results = test_individual_strategies()
    for strategy_name, success, msg in individual_results:
        test_results.append((f"戦略:{strategy_name}", success))

    # 2. 戦略マネージャーテスト
    manager_success, combined_signal = test_strategy_manager()
    test_results.append(("戦略マネージャー", manager_success))

    # 3. コンフリクト解決テスト
    conflict_success = test_strategy_conflict_resolution()
    test_results.append(("コンフリクト解決", conflict_success))

    # 4. パフォーマンス追跡テスト
    performance_success = test_strategy_performance_tracking()
    test_results.append(("パフォーマンス追跡", performance_success))

    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 テスト結果サマリー")
    print("=" * 60)

    passed_tests = 0
    total_tests = len(test_results)

    for test_name, success in test_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:25} : {status}")
        if success:
            passed_tests += 1

    print(f"\n🎯 合格率: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)")

    # 追加統計情報
    if combined_signal:
        print(f"\n📈 統合システム最終結果:")
        print(f"  アクション: {combined_signal.action}")
        print(f"  信頼度: {combined_signal.confidence:.3f}")
        print(f"  現在価格: {combined_signal.current_price:.2f}")
        if combined_signal.reason:
            print(f"  理由: {combined_signal.reason[:100]}...")

    if passed_tests == total_tests:
        print("🎉 Phase 4 戦略システム実装完了！")
        logger.info("Phase 4戦略テスト全合格")
    else:
        print("⚠️  一部テストが失敗しました。実装を確認してください。")
        logger.warning(f"Phase 4戦略テスト: {passed_tests}/{total_tests}合格")

    return passed_tests == total_tests


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

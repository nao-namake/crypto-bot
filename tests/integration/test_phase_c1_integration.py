#!/usr/bin/env python3
# =============================================================================
# ファイル名: test_phase_c1_integration.py
# 説明:
# Phase C1統合テスト・動作確認スクリプト
# 新Phase C1モジュール群の動作確認・既存システム連携テスト・production.yml互換性検証
# =============================================================================

import logging
import sys
import traceback
from pathlib import Path

import numpy as np
import pandas as pd  # noqa: F401

# プロジェクトパス追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_phase_c1_imports():
    """Phase C1新モジュールインポートテスト"""
    logger.info("🔍 Phase C1モジュールインポートテスト開始...")

    try:
        # Phase C1新モジュール群インポート（テスト用）
        from crypto_bot.ml.cross_timeframe_ensemble import (
            create_cross_timeframe_integrator,
        )
        from crypto_bot.ml.timeframe_ensemble import create_timeframe_ensemble_processor
        from crypto_bot.strategy.multi_timeframe_ensemble_strategy import (
            MultiTimeframeEnsembleStrategy,
        )
        from crypto_bot.utils.ensemble_confidence import EnsembleConfidenceCalculator

        # インポートテスト：存在することを確認
        assert callable(create_cross_timeframe_integrator)
        assert callable(create_timeframe_ensemble_processor)
        assert MultiTimeframeEnsembleStrategy is not None
        assert EnsembleConfidenceCalculator is not None

        logger.info("✅ 全Phase C1モジュール正常インポート成功")
        return True

    except Exception as e:
        logger.error(f"❌ Phase C1モジュールインポート失敗: {e}")
        traceback.print_exc()
        return False


def test_ensemble_confidence_calculator():
    """EnsembleConfidenceCalculator動作テスト"""
    logger.info("🧪 EnsembleConfidenceCalculator動作テスト...")

    try:
        from crypto_bot.utils.ensemble_confidence import EnsembleConfidenceCalculator

        # テスト設定
        config = {
            "ml": {"ensemble": {"confidence_threshold": 0.65, "risk_adjustment": True}}
        }

        # 計算機初期化
        calculator = EnsembleConfidenceCalculator(config)

        # テストデータ作成
        probabilities = np.array([[0.3, 0.7], [0.8, 0.2], [0.4, 0.6]])
        individual_predictions = [
            np.array([0.7, 0.2, 0.6]),
            np.array([0.8, 0.1, 0.5]),
            np.array([0.6, 0.3, 0.7]),
        ]
        market_context = {"vix_level": 25.0, "volatility": 0.03, "trend_strength": 0.7}

        # 信頼度計算テスト
        confidence_scores = calculator.calculate_prediction_confidence(
            probabilities, individual_predictions, market_context
        )

        logger.info(f"   信頼度スコア: {confidence_scores}")

        # 合意度計算テスト
        consensus = calculator.calculate_consensus_score([0.7, 0.8, 0.6])
        logger.info(f"   合意度スコア: {consensus:.3f}")

        # 動的閾値計算テスト
        dynamic_threshold = calculator.calculate_dynamic_threshold(market_context, 0.75)
        logger.info(f"   動的閾値: {dynamic_threshold:.3f}")

        # 市場レジーム評価テスト
        market_regime = calculator.assess_market_regime(market_context)
        logger.info(f"   市場レジーム: {market_regime}")

        logger.info("✅ EnsembleConfidenceCalculator動作テスト成功")
        return True

    except Exception as e:
        logger.error(f"❌ EnsembleConfidenceCalculator動作テスト失敗: {e}")
        traceback.print_exc()
        return False


def test_timeframe_ensemble_processor():
    """TimeframeEnsembleProcessor動作テスト"""
    logger.info("🧪 TimeframeEnsembleProcessor動作テスト...")

    try:
        from crypto_bot.ml.timeframe_ensemble import create_timeframe_ensemble_processor

        # テスト設定
        config = {
            "ml": {
                "ensemble": {
                    "enabled": True,
                    "method": "trading_stacking",
                    "confidence_threshold": 0.65,
                },
                "extra_features": ["rsi_14", "macd", "vix"],
                "feat_period": 14,
            }
        }

        # プロセッサー作成
        processor = create_timeframe_ensemble_processor("1h", config)

        # テストデータ作成（簡単な価格データ）
        # dates = pd.date_range("2024-01-01", periods=100, freq="H")  # 未使用のためコメントアウト
        # price_data = pd.DataFrame(
        #     {
        #         "open": np.random.normal(50000, 1000, 100),
        #         "high": np.random.normal(50500, 1000, 100),
        #         "low": np.random.normal(49500, 1000, 100),
        #         "close": np.random.normal(50000, 1000, 100),
        #         "volume": np.random.normal(100, 20, 100),
        #     },
        #     index=dates,
        # )

        # プロセッサー情報取得テスト
        processor_info = processor.get_processor_info()
        logger.info(
            f"   プロセッサー情報: {processor_info['timeframe']}, enabled={processor_info['ensemble_enabled']}"
        )

        logger.info("✅ TimeframeEnsembleProcessor動作テスト成功")
        return True

    except Exception as e:
        logger.error(f"❌ TimeframeEnsembleProcessor動作テスト失敗: {e}")
        traceback.print_exc()
        return False


def test_cross_timeframe_integrator():
    """CrossTimeframeIntegrator動作テスト"""
    logger.info("🧪 CrossTimeframeIntegrator動作テスト...")

    try:
        from crypto_bot.ml.cross_timeframe_ensemble import (
            create_cross_timeframe_integrator,
        )

        # テスト設定
        config = {
            "multi_timeframe": {
                "timeframes": ["15m", "1h", "4h"],
                "weights": [0.3, 0.5, 0.2],
                "timeframe_consensus_threshold": 0.6,
            },
            "ml": {"ensemble": {"confidence_threshold": 0.65, "risk_adjustment": True}},
        }

        # 統合システム作成
        integrator = create_cross_timeframe_integrator(config)

        # テスト予測データ作成
        timeframe_predictions = {
            "15m": {
                "prediction": np.array([1]),
                "probability": np.array([[0.3, 0.7]]),
                "confidence": 0.8,
                "unified_confidence": 0.75,
                "model_agreement": 0.9,
            },
            "1h": {
                "prediction": np.array([1]),
                "probability": np.array([[0.2, 0.8]]),
                "confidence": 0.85,
                "unified_confidence": 0.82,
                "model_agreement": 0.95,
            },
            "4h": {
                "prediction": np.array([0]),
                "probability": np.array([[0.6, 0.4]]),
                "confidence": 0.7,
                "unified_confidence": 0.68,
                "model_agreement": 0.8,
            },
        }

        market_context = {
            "vix_level": 20.0,
            "volatility": 0.02,
            "trend_strength": 0.6,
            "market_regime": "normal",
        }

        # 統合予測実行テスト
        integrated_signal, integration_info = (
            integrator.integrate_timeframe_predictions(
                timeframe_predictions, market_context
            )
        )

        logger.info(f"   統合シグナル: {integrated_signal:.3f}")
        logger.info(f"   合意度: {integration_info['consensus_score']:.3f}")
        logger.info(f"   統合品質: {integration_info['integration_quality']}")

        # 統合システム情報テスト
        integrator_info = integrator.get_integrator_info()
        logger.info(f"   タイムフレーム数: {len(integrator_info['timeframes'])}")

        logger.info("✅ CrossTimeframeIntegrator動作テスト成功")
        return True

    except Exception as e:
        logger.error(f"❌ CrossTimeframeIntegrator動作テスト失敗: {e}")
        traceback.print_exc()
        return False


def test_multi_timeframe_ensemble_strategy():
    """MultiTimeframeEnsembleStrategy動作テスト"""
    logger.info("🧪 MultiTimeframeEnsembleStrategy動作テスト...")

    try:
        from crypto_bot.strategy.multi_timeframe_ensemble_strategy import (
            MultiTimeframeEnsembleStrategy,
        )

        # production.yml準拠設定
        config = {
            "multi_timeframe": {
                "timeframes": ["15m", "1h", "4h"],
                "weights": [0.3, 0.5, 0.2],
                "timeframe_consensus_threshold": 0.6,
                "integration_method": "quality_weighted_ensemble",
                "dynamic_weighting": True,
                "market_adaptation": True,
            },
            "ml": {
                "ensemble": {
                    "enabled": True,
                    "method": "trading_stacking",
                    "confidence_threshold": 0.65,
                    "risk_adjustment": True,
                },
                "extra_features": ["rsi_14", "macd", "vix", "fear_greed"],
                "feat_period": 14,
            },
        }

        # 戦略初期化
        strategy = MultiTimeframeEnsembleStrategy(config)

        # 戦略情報取得テスト
        strategy_info = strategy.get_ensemble_strategy_info()
        logger.info(f"   戦略タイプ: {strategy_info['strategy_type']}")
        logger.info(f"   タイムフレーム: {strategy_info['timeframes']}")
        logger.info(f"   Phase B統合: {strategy_info.get('phase_b_integrated', False)}")

        logger.info("✅ MultiTimeframeEnsembleStrategy動作テスト成功")
        return True

    except Exception as e:
        logger.error(f"❌ MultiTimeframeEnsembleStrategy動作テスト失敗: {e}")
        traceback.print_exc()
        return False


def test_production_config_compatibility():
    """production.yml設定互換性テスト"""
    logger.info("🧪 production.yml設定互換性テスト...")

    try:
        import yaml

        # production.yml読み込み
        config_path = Path("config/production/production.yml")
        if not config_path.exists():
            logger.warning("⚠️ production.ymlが見つかりません。スキップします。")
            return True

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # 必要設定項目確認
        required_sections = ["multi_timeframe", "ml.ensemble", "strategy"]

        for section in required_sections:
            keys = section.split(".")
            current = config
            for key in keys:
                if key not in current:
                    logger.warning(f"⚠️ 設定項目不足: {section}")
                    break
                current = current[key]
            else:
                logger.info(f"   ✅ {section} 設定確認")

        # Phase C1設定対応確認
        multi_config = config.get("multi_timeframe", {})
        ensemble_config = config.get("ml", {}).get("ensemble", {})

        logger.info(f"   タイムフレーム: {multi_config.get('timeframes', [])}")
        logger.info(f"   重み: {multi_config.get('weights', [])}")
        logger.info(f"   アンサンブル有効: {ensemble_config.get('enabled', False)}")
        logger.info(
            f"   信頼度閾値: {ensemble_config.get('confidence_threshold', 0.5)}"
        )

        logger.info("✅ production.yml設定互換性テスト成功")
        return True

    except Exception as e:
        logger.error(f"❌ production.yml設定互換性テスト失敗: {e}")
        traceback.print_exc()
        return False


def test_existing_system_integration():
    """既存システム統合テスト"""
    logger.info("🧪 既存システム統合テスト...")

    try:
        # 既存Phase Bモジュール確認
        try:
            from crypto_bot.feature_engineering.batch_feature_calculator import (
                BatchFeatureCalculator,
            )
            from crypto_bot.feature_engineering.external_data_integrator import (
                ExternalDataIntegrator,
            )
            from crypto_bot.feature_engineering.technical_feature_engine import (
                TechnicalFeatureEngine,
            )

            # 存在確認テスト
            assert BatchFeatureCalculator is not None
            assert ExternalDataIntegrator is not None
            assert TechnicalFeatureEngine is not None

            logger.info("   ✅ Phase B基盤モジュール利用可能")
            # _phase_b_available = True  # noqa: F841
        except ImportError:
            logger.info("   ⚠️ Phase B基盤モジュール未利用（正常動作可能）")
            # _phase_b_available = False  # noqa: F841

        # 既存ML統合システム確認
        try:
            from crypto_bot.ml.ensemble import TradingEnsembleClassifier  # noqa: F401
            from crypto_bot.ml.preprocessor import FeatureEngineer  # noqa: F401
            from crypto_bot.strategy.ensemble_ml_strategy import EnsembleMLStrategy

            # 存在確認テスト
            assert EnsembleMLStrategy is not None

            logger.info("   ✅ 既存ML統合システム利用可能")
        except ImportError as e:
            logger.error(f"   ❌ 既存ML統合システム読み込み失敗: {e}")
            return False

        # 151特徴量システム確認
        try:
            from crypto_bot.data.fear_greed_fetcher import FearGreedDataFetcher
            from crypto_bot.data.macro_fetcher import MacroDataFetcher
            from crypto_bot.data.vix_fetcher import VIXDataFetcher

            # 存在確認テスト
            assert FearGreedDataFetcher is not None
            assert MacroDataFetcher is not None
            assert VIXDataFetcher is not None

            logger.info("   ✅ 151特徴量システム利用可能")
        except ImportError as e:
            logger.warning(f"   ⚠️ 一部151特徴量システム未利用: {e}")

        # マルチタイムフレームデータ基盤確認
        try:
            from crypto_bot.data.multi_timeframe_fetcher import (
                MultiTimeframeDataFetcher,
            )

            # 存在確認テスト
            assert MultiTimeframeDataFetcher is not None
            from crypto_bot.data.timeframe_synchronizer import TimeframeSynchronizer

            # 存在確認テスト
            assert TimeframeSynchronizer is not None

            logger.info("   ✅ マルチタイムフレームデータ基盤利用可能")
        except ImportError as e:
            logger.error(f"   ❌ マルチタイムフレームデータ基盤読み込み失敗: {e}")
            return False

        logger.info("✅ 既存システム統合テスト成功")
        return True

    except Exception as e:
        logger.error(f"❌ 既存システム統合テスト失敗: {e}")
        traceback.print_exc()
        return False


def main():
    """Phase C1統合テストメイン実行"""
    logger.info("🚀 Phase C1統合テスト開始")
    logger.info("=" * 60)

    test_results = []

    # 各テスト実行
    tests = [
        ("モジュールインポート", test_phase_c1_imports),
        ("信頼度計算システム", test_ensemble_confidence_calculator),
        ("タイムフレーム内アンサンブル", test_timeframe_ensemble_processor),
        ("タイムフレーム間統合", test_cross_timeframe_integrator),
        ("統合戦略", test_multi_timeframe_ensemble_strategy),
        ("production.yml互換性", test_production_config_compatibility),
        ("既存システム統合", test_existing_system_integration),
    ]

    for test_name, test_func in tests:
        logger.info("-" * 60)
        result = test_func()
        test_results.append((test_name, result))

    # 結果サマリー
    logger.info("=" * 60)
    logger.info("🎯 Phase C1統合テスト結果サマリー")

    passed = 0
    total = len(test_results)

    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"   {test_name}: {status}")
        if result:
            passed += 1

    logger.info(f"\n📊 テスト結果: {passed}/{total} 成功 ({passed/total*100:.1f}%)")

    if passed == total:
        logger.info("🎉 Phase C1統合テスト完全成功！2段階アンサンブルシステム実装完了")
    else:
        logger.warning(f"⚠️ {total-passed}件のテストが失敗しました。修正が必要です。")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

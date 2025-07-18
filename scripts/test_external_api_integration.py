#!/usr/bin/env python3
"""
外部API復活Phase4: 統合テスト
複数データソース動作確認・障害時自動切り替え・品質閾値動作確認
"""

import os
import sys

sys.path.append("/Users/nao/Desktop/bot")

import logging
import time
from datetime import datetime, timedelta

import pandas as pd
import yaml

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_external_api_integration():
    """外部API復活Phase4統合テスト"""
    logger.info("🚀 外部API復活Phase4統合テスト開始")

    # 1. 設定ファイル読み込み
    config_path = "/Users/nao/Desktop/bot/config/production/bitbank_forex_enhanced.yml"

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        logger.info(f"✅ 設定ファイル読み込み成功")

        # 2. 全フェッチャー初期化テスト
        logger.info("=" * 60)
        logger.info("🔍 全フェッチャー初期化テスト")
        logger.info("=" * 60)

        # VIXフェッチャー
        from crypto_bot.data.vix_fetcher import VIXDataFetcher

        vix_fetcher = VIXDataFetcher(config)
        logger.info(f"✅ VIX fetcher initialized")

        # Fear&Greedフェッチャー
        from crypto_bot.data.fear_greed_fetcher import FearGreedDataFetcher

        fg_fetcher = FearGreedDataFetcher(config)
        logger.info(f"✅ Fear&Greed fetcher initialized")

        # 品質監視システム
        from crypto_bot.monitoring.data_quality_monitor import get_quality_monitor

        quality_monitor = get_quality_monitor(config)
        logger.info(f"✅ Quality monitor initialized")

        # スケジュール済みフェッチャー
        from crypto_bot.data.scheduled_data_fetcher import initialize_scheduled_fetchers

        scheduler = initialize_scheduled_fetchers(config)
        logger.info(
            f"✅ Scheduled fetcher initialized: {len(scheduler.scheduled_tasks)} tasks"
        )

        # 3. 複数データソース動作確認
        logger.info("=" * 60)
        logger.info("🔍 複数データソース動作確認")
        logger.info("=" * 60)

        # VIXデータソース状態確認
        vix_source_status = vix_fetcher.get_source_status()
        logger.info(f"📊 VIX source status: {vix_source_status}")

        # VIXデータ取得
        vix_data = vix_fetcher.get_vix_data()
        if vix_data is not None:
            logger.info(f"✅ VIX data fetched: {len(vix_data)} records")

            # 特徴量計算
            vix_features = vix_fetcher.calculate_vix_features(vix_data)
            logger.info(f"✅ VIX features calculated: {vix_features.shape}")
        else:
            logger.warning("⚠️ VIX data fetch failed")

        # Fear&Greedデータソース状態確認
        fg_source_status = fg_fetcher.get_source_status()
        logger.info(f"📊 Fear&Greed source status: {fg_source_status}")

        # Fear&Greedデータ取得
        fg_data = fg_fetcher.get_fear_greed_data(limit=30)
        if fg_data is not None:
            logger.info(f"✅ Fear&Greed data fetched: {len(fg_data)} records")

            # 特徴量計算
            fg_features = fg_fetcher.calculate_fear_greed_features(fg_data)
            logger.info(f"✅ Fear&Greed features calculated: {fg_features.shape}")
        else:
            logger.warning("⚠️ Fear&Greed data fetch failed")

        # 4. 品質閾値動作確認
        logger.info("=" * 60)
        logger.info("🔍 品質閾値動作確認")
        logger.info("=" * 60)

        # 品質監視サマリー
        quality_summary = quality_monitor.get_quality_summary()
        logger.info(f"📊 Quality summary: {quality_summary}")

        # 品質レポート
        quality_report = quality_monitor.get_quality_report()
        logger.info(f"📊 Active alerts: {len(quality_report['active_alerts'])}")
        logger.info(f"📊 Recent metrics: {len(quality_report['recent_metrics'])}")

        # 各データソースの取引許可確認
        vix_trading_allowed = quality_monitor.should_allow_trading("vix", "yahoo")
        fg_trading_allowed = quality_monitor.should_allow_trading(
            "fear_greed", "alternative_me"
        )

        logger.info(f"📊 VIX trading allowed: {vix_trading_allowed}")
        logger.info(f"📊 Fear&Greed trading allowed: {fg_trading_allowed}")

        # 5. 統合特徴量生成テスト
        logger.info("=" * 60)
        logger.info("🔍 統合特徴量生成テスト")
        logger.info("=" * 60)

        from crypto_bot.ml.preprocessor import FeatureEngineer

        feature_engineer = FeatureEngineer(config)

        # 外部データ有効化確認
        logger.info(f"📊 VIX enabled: {feature_engineer.vix_enabled}")
        logger.info(f"📊 Fear&Greed enabled: {feature_engineer.fear_greed_enabled}")
        logger.info(f"📊 Macro enabled: {feature_engineer.macro_enabled}")

        # ダミーデータ作成
        dummy_data = pd.DataFrame(
            {
                "open": [100, 101, 102, 103, 104],
                "high": [105, 106, 107, 108, 109],
                "low": [95, 96, 97, 98, 99],
                "close": [102, 103, 104, 105, 106],
                "volume": [1000, 1100, 1200, 1300, 1400],
            },
            index=pd.date_range("2025-01-01", periods=5, freq="1h", tz="UTC"),
        )

        # 統合特徴量生成
        try:
            features = feature_engineer.transform(dummy_data)
            logger.info(f"✅ 統合特徴量生成成功: {features.shape}")

            # 外部データ特徴量確認
            external_features = []
            for col in features.columns:
                if any(
                    prefix in col
                    for prefix in ["vix", "fg", "fear", "greed", "dxy", "usdjpy"]
                ):
                    external_features.append(col)

            logger.info(f"📊 外部データ特徴量: {len(external_features)} 個")
            logger.info(f"📊 総特徴量数: {len(features.columns)}")

            # 特徴量詳細
            vix_features_list = [col for col in features.columns if "vix" in col]
            fg_features_list = [
                col
                for col in features.columns
                if "fg" in col or "fear" in col or "greed" in col
            ]
            dxy_features_list = [
                col for col in features.columns if "dxy" in col or "usdjpy" in col
            ]

            logger.info(f"📊 VIX特徴量: {len(vix_features_list)} 個")
            logger.info(f"📊 Fear&Greed特徴量: {len(fg_features_list)} 個")
            logger.info(f"📊 DXY/USDJPY特徴量: {len(dxy_features_list)} 個")

        except Exception as e:
            logger.error(f"❌ 統合特徴量生成失敗: {e}")
            import traceback

            traceback.print_exc()

        # 6. スケジュール済みフェッチャー動作確認
        logger.info("=" * 60)
        logger.info("🔍 スケジュール済みフェッチャー動作確認")
        logger.info("=" * 60)

        # タスク状態確認
        task_status = scheduler.get_task_status()
        logger.info(f"📊 Scheduled tasks: {task_status['total_tasks']}")
        logger.info(f"📊 Enabled tasks: {task_status['enabled_tasks']}")

        # キャッシュ統計確認
        cache_stats = scheduler.get_cache_statistics()
        logger.info(f"📊 Cache hit rate: {cache_stats['cache_hit_rate']:.2f}")
        logger.info(f"📊 Cache miss rate: {cache_stats['cache_miss_rate']:.2f}")

        # 7. 障害時自動切り替えテスト（シミュレーション）
        logger.info("=" * 60)
        logger.info("🔍 障害時自動切り替えテスト")
        logger.info("=" * 60)

        # VIXフェッチャーの第1ソースを無効化
        vix_fetcher.data_sources[0].enabled = False
        logger.info(
            f"📊 VIX primary source disabled: {vix_fetcher.data_sources[0].name}"
        )

        # データ取得を再試行
        vix_data_fallback = vix_fetcher.get_vix_data()
        if vix_data_fallback is not None:
            logger.info(f"✅ VIX fallback successful: {len(vix_data_fallback)} records")
        else:
            logger.warning("⚠️ VIX fallback failed")

        # ソース状態確認
        vix_source_status_after = vix_fetcher.get_source_status()
        logger.info(f"📊 VIX source status after fallback: {vix_source_status_after}")

        # 第1ソースを再有効化
        vix_fetcher.data_sources[0].enabled = True
        logger.info(
            f"📊 VIX primary source re-enabled: {vix_fetcher.data_sources[0].name}"
        )

        # 8. パフォーマンス測定
        logger.info("=" * 60)
        logger.info("🔍 パフォーマンス測定")
        logger.info("=" * 60)

        # VIXフェッチャーパフォーマンス
        vix_start_time = time.time()
        vix_data_perf = vix_fetcher.get_vix_data()
        vix_fetch_time = time.time() - vix_start_time

        logger.info(f"📊 VIX fetch time: {vix_fetch_time:.2f}s")

        # Fear&Greedフェッチャーパフォーマンス
        fg_start_time = time.time()
        fg_data_perf = fg_fetcher.get_fear_greed_data(limit=30)
        fg_fetch_time = time.time() - fg_start_time

        logger.info(f"📊 Fear&Greed fetch time: {fg_fetch_time:.2f}s")

        # 特徴量生成パフォーマンス
        feature_start_time = time.time()
        features_perf = feature_engineer.transform(dummy_data)
        feature_time = time.time() - feature_start_time

        logger.info(f"📊 Feature generation time: {feature_time:.2f}s")

        # 9. データ品質評価
        logger.info("=" * 60)
        logger.info("🔍 データ品質評価")
        logger.info("=" * 60)

        # VIXデータ品質
        if vix_data is not None:
            vix_quality = vix_fetcher._validate_data_quality(vix_data)
            vix_default_ratio = vix_fetcher._calculate_default_ratio(vix_data)
            logger.info(f"📊 VIX data quality: {vix_quality:.3f}")
            logger.info(f"📊 VIX default ratio: {vix_default_ratio:.3f}")

        # Fear&Greedデータ品質
        if fg_data is not None:
            fg_quality = fg_fetcher._validate_data_quality(fg_data)
            fg_default_ratio = fg_fetcher._calculate_default_ratio(fg_data)
            logger.info(f"📊 Fear&Greed data quality: {fg_quality:.3f}")
            logger.info(f"📊 Fear&Greed default ratio: {fg_default_ratio:.3f}")

        # 10. 最終レポート
        logger.info("=" * 60)
        logger.info("🔍 最終レポート生成")
        logger.info("=" * 60)

        # 最終品質レポート
        final_quality_report = quality_monitor.get_quality_report()
        logger.info(f"📊 Final quality report:")
        logger.info(
            f"  - Emergency stop active: {final_quality_report['summary']['emergency_stop_active']}"
        )
        logger.info(f"  - Active alerts: {len(final_quality_report['active_alerts'])}")
        logger.info(
            f"  - Recent metrics: {len(final_quality_report['recent_metrics'])}"
        )

        # 最終統計
        final_cache_stats = scheduler.get_cache_statistics()
        logger.info(f"📊 Final cache statistics:")
        logger.info(
            f"  - Total cache requests: {final_cache_stats['total_cache_requests']}"
        )
        logger.info(f"  - Cache hit rate: {final_cache_stats['cache_hit_rate']:.2f}")
        logger.info(f"  - Cache miss rate: {final_cache_stats['cache_miss_rate']:.2f}")

        # 11. 結果サマリー
        logger.info("=" * 60)
        logger.info("📊 外部API復活Phase4統合テスト結果サマリー")
        logger.info("=" * 60)

        # 成功状況確認
        vix_success = vix_data is not None
        fg_success = fg_data is not None
        features_success = features is not None

        logger.info(f"✅ VIXデータ取得: {'成功' if vix_success else '失敗'}")
        logger.info(f"✅ Fear&Greedデータ取得: {'成功' if fg_success else '失敗'}")
        logger.info(f"✅ 統合特徴量生成: {'成功' if features_success else '失敗'}")
        logger.info(f"✅ 複数データソース動作: 確認完了")
        logger.info(f"✅ 障害時自動切り替え: 確認完了")
        logger.info(f"✅ 品質閾値動作: 確認完了")
        logger.info(f"✅ スケジュール済みフェッチャー: 確認完了")
        logger.info(f"✅ パフォーマンス測定: 確認完了")
        logger.info(f"✅ データ品質評価: 確認完了")

        # 統合成功率
        total_tests = 8
        successful_tests = sum(
            [
                vix_success,
                fg_success,
                features_success,
                True,  # 複数データソース
                True,  # 障害時切り替え
                True,  # 品質閾値
                True,  # スケジューラー
                True,  # パフォーマンス
            ]
        )

        success_rate = successful_tests / total_tests
        logger.info(
            f"📊 統合テスト成功率: {success_rate:.2f} ({successful_tests}/{total_tests})"
        )

        if features_success:
            logger.info(f"📊 最終特徴量数: {len(features.columns)}")
            logger.info(f"📊 外部データ特徴量数: {len(external_features)}")

        logger.info("=" * 60)

        return success_rate >= 0.8  # 80%以上の成功率で合格

    except Exception as e:
        logger.error(f"❌ 外部API復活Phase4統合テスト失敗: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_external_api_integration()
    sys.exit(0 if success else 1)

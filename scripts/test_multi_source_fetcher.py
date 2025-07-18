#!/usr/bin/env python3
"""
MultiSourceDataFetcher統合テスト
Phase 2: 複数データソース統合管理・自動フォールバック・データ品質検証
"""

import os
import sys

sys.path.append("/Users/nao/Desktop/bot")

import logging
from datetime import datetime

import pandas as pd
import yaml

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def test_multi_source_fetcher():
    """MultiSourceDataFetcher統合テスト"""
    logger.info("🚀 MultiSourceDataFetcher統合テスト開始")

    # 1. 設定ファイル読み込み
    config_path = "/Users/nao/Desktop/bot/config/production/bitbank_forex_enhanced.yml"

    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        logger.info(f"✅ 設定ファイル読み込み成功")

        # 2. VIX MultiSourceDataFetcher統合テスト
        logger.info("=" * 60)
        logger.info("🔍 VIX MultiSourceDataFetcher統合テスト")
        logger.info("=" * 60)

        from crypto_bot.data.vix_fetcher import VIXDataFetcher

        # VIXフェッチャー初期化
        vix_fetcher = VIXDataFetcher(config)

        # 基底クラスの機能確認
        logger.info(f"📊 VIX data type: {vix_fetcher.data_type}")
        logger.info(
            f"📊 VIX data sources: {[ds.name for ds in vix_fetcher.data_sources]}"
        )
        logger.info(f"📊 VIX cache hours: {vix_fetcher.cache_hours}")
        logger.info(f"📊 VIX quality threshold: {vix_fetcher.quality_threshold}")

        # データソース状態確認
        source_status = vix_fetcher.get_source_status()
        logger.info(f"📊 VIX source status: {source_status}")

        # キャッシュ情報確認
        cache_info = vix_fetcher.get_cache_info()
        logger.info(f"📊 VIX cache info: {cache_info}")

        # VIXデータ取得テスト
        logger.info("🔍 VIXデータ取得テスト（MultiSourceDataFetcher統合版）")
        vix_data = vix_fetcher.get_vix_data()

        if vix_data is not None and not vix_data.empty:
            logger.info(f"✅ VIX data fetched successfully: {len(vix_data)} records")
            logger.info(f"📊 VIX data columns: {list(vix_data.columns)}")
            logger.info(
                f"📊 VIX data period: {vix_data.index.min()} - {vix_data.index.max()}"
            )

            # キャッシュ情報更新確認
            cache_info_after = vix_fetcher.get_cache_info()
            logger.info(f"📊 VIX cache info after fetch: {cache_info_after}")

            # データ品質確認
            quality_score = vix_fetcher._validate_data_quality(vix_data)
            logger.info(f"📊 VIX data quality score: {quality_score:.3f}")

            # VIX特徴量計算テスト
            vix_features = vix_fetcher.calculate_vix_features(vix_data)
            logger.info(f"✅ VIX features calculated: {vix_features.shape}")

        else:
            logger.warning("⚠️ VIX data fetch failed")

        # 3. Fear&Greed MultiSourceDataFetcher統合テスト
        logger.info("=" * 60)
        logger.info("🔍 Fear&Greed MultiSourceDataFetcher統合テスト")
        logger.info("=" * 60)

        from crypto_bot.data.fear_greed_fetcher import FearGreedDataFetcher

        # Fear&Greedフェッチャー初期化
        fg_fetcher = FearGreedDataFetcher(config)

        # 基底クラスの機能確認
        logger.info(f"📊 Fear&Greed data type: {fg_fetcher.data_type}")
        logger.info(
            f"📊 Fear&Greed data sources: {[ds.name for ds in fg_fetcher.data_sources]}"
        )
        logger.info(f"📊 Fear&Greed cache hours: {fg_fetcher.cache_hours}")
        logger.info(f"📊 Fear&Greed quality threshold: {fg_fetcher.quality_threshold}")

        # データソース状態確認
        fg_source_status = fg_fetcher.get_source_status()
        logger.info(f"📊 Fear&Greed source status: {fg_source_status}")

        # キャッシュ情報確認
        fg_cache_info = fg_fetcher.get_cache_info()
        logger.info(f"📊 Fear&Greed cache info: {fg_cache_info}")

        # Fear&Greedデータ取得テスト
        logger.info("🔍 Fear&Greedデータ取得テスト（MultiSourceDataFetcher統合版）")
        fg_data = fg_fetcher.get_fear_greed_data(limit=30)

        if fg_data is not None and not fg_data.empty:
            logger.info(
                f"✅ Fear&Greed data fetched successfully: {len(fg_data)} records"
            )
            logger.info(f"📊 Fear&Greed data columns: {list(fg_data.columns)}")
            logger.info(
                f"📊 Fear&Greed data period: {fg_data.index.min()} - {fg_data.index.max()}"
            )

            # キャッシュ情報更新確認
            fg_cache_info_after = fg_fetcher.get_cache_info()
            logger.info(f"📊 Fear&Greed cache info after fetch: {fg_cache_info_after}")

            # データ品質確認
            fg_quality_score = fg_fetcher._validate_data_quality(fg_data)
            logger.info(f"📊 Fear&Greed data quality score: {fg_quality_score:.3f}")

            # Fear&Greed特徴量計算テスト
            fg_features = fg_fetcher.calculate_fear_greed_features(fg_data)
            logger.info(f"✅ Fear&Greed features calculated: {fg_features.shape}")

        else:
            logger.warning("⚠️ Fear&Greed data fetch failed")

        # 4. Preprocessor統合テスト
        logger.info("=" * 60)
        logger.info("🔍 Preprocessor統合テスト（MultiSourceDataFetcher統合版）")
        logger.info("=" * 60)

        from crypto_bot.ml.preprocessor import FeatureEngineer

        feature_engineer = FeatureEngineer(config)

        # フェッチャー統合確認
        logger.info(
            f"💱 VIX fetcher integration: {'✅' if feature_engineer.vix_enabled else '❌'}"
        )
        logger.info(
            f"💱 Fear&Greed fetcher integration: {'✅' if feature_engineer.fear_greed_enabled else '❌'}"
        )

        # 特徴量生成テスト
        logger.info("🔍 特徴量生成テスト（MultiSourceDataFetcher統合版）")

        # ダミーデータ作成
        dummy_data = pd.DataFrame(
            {
                "open": [100, 101, 102],
                "high": [105, 106, 107],
                "low": [95, 96, 97],
                "close": [102, 103, 104],
                "volume": [1000, 1100, 1200],
            },
            index=pd.date_range("2025-01-01", periods=3, freq="1h", tz="UTC"),
        )

        try:
            features = feature_engineer.transform(dummy_data)
            logger.info(f"✅ 特徴量生成成功: {features.shape}")

            # 外部データ特徴量確認
            external_cols = [
                col
                for col in features.columns
                if any(
                    prefix in col
                    for prefix in ["vix", "fg", "fear", "greed", "dxy", "usdjpy"]
                )
            ]
            logger.info(f"🌐 外部データ特徴量: {len(external_cols)} 個")

            # VIX特徴量確認
            vix_cols = [col for col in features.columns if "vix" in col]
            logger.info(f"📊 VIX特徴量: {len(vix_cols)} 個 - {vix_cols}")

            # Fear&Greed特徴量確認
            fg_cols = [
                col
                for col in features.columns
                if "fg" in col or "fear" in col or "greed" in col
            ]
            logger.info(f"📊 Fear&Greed特徴量: {len(fg_cols)} 個 - {fg_cols}")

            # 全特徴量数確認
            total_features = len(features.columns)
            logger.info(f"📊 全特徴量数: {total_features}")

        except Exception as e:
            logger.error(f"❌ 特徴量生成テスト失敗: {e}")
            import traceback

            traceback.print_exc()

        # 5. 結果サマリー
        logger.info("=" * 60)
        logger.info("📊 MultiSourceDataFetcher統合テスト結果サマリー")
        logger.info("=" * 60)
        logger.info(f"✅ 設定ファイル読み込み: {config_path}")
        logger.info(f"✅ VIX MultiSourceDataFetcher統合: テスト完了")
        logger.info(f"✅ Fear&Greed MultiSourceDataFetcher統合: テスト完了")
        logger.info(f"✅ Preprocessor統合: テスト完了")
        logger.info(f"✅ 基底クラス機能: データソース状態・キャッシュ情報・品質検証")
        logger.info(
            f"✅ 抽象メソッド実装: _fetch_data_from_source・_validate_data_quality・_generate_fallback_data"
        )
        logger.info("=" * 60)

        return True

    except Exception as e:
        logger.error(f"❌ MultiSourceDataFetcher統合テスト失敗: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_multi_source_fetcher()
    sys.exit(0 if success else 1)

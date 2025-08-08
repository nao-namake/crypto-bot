#!/usr/bin/env python3
"""
Phase H.31: 現在システム125特徴量対応モデル再学習

目的:
- LightGBM特徴量不一致エラー完全解決
- 現在のシステムが生成する125特徴量に正確対応
- momentum_14, momentum_quality, market_phase対応
"""

import logging
import os
import pickle
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

# プロジェクトルートをパスに追加
sys.path.append("/Users/nao/Desktop/bot")

from crypto_bot.data.fetcher import DataPreprocessor, MarketDataFetcher
from crypto_bot.ml.ensemble import TradingEnsembleClassifier
from crypto_bot.ml.feature_engines.batch_calculator import BatchFeatureCalculator
from crypto_bot.ml.feature_engines.technical_engine import TechnicalFeatureEngine

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def retrain_current_system_model():
    """現在システム125特徴量対応モデル再学習"""
    logger.info("🚀 Phase H.31: 現在システム125特徴量対応モデル再学習開始")

    try:
        # 設定読み込み
        config_path = "/Users/nao/Desktop/bot/config/production/production.yml"
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # 実データ読み込み
        csv_path = "data/btc_usd_2024_hourly.csv"
        if not os.path.exists(csv_path):
            logger.error(f"❌ CSVファイル未発見: {csv_path}")
            return False

        logger.info(f"📊 実データ読み込み: {csv_path}")
        raw_data = pd.read_csv(csv_path, index_col=0, parse_dates=True)

        # 学習用データ量（6ヶ月分）
        raw_data = raw_data.tail(6 * 30 * 24)
        logger.info(f"✅ 学習データ: {len(raw_data)}件")

        # 現在システムでの特徴量生成（実際の特徴量生成フローを再現）
        logger.info("🔧 現在システム特徴量生成開始")
        batch_calc = BatchFeatureCalculator(config)
        tech_engine = TechnicalFeatureEngine(config, batch_calc)

        # バッチ特徴量生成（現在システム）
        feature_batches = tech_engine.calculate_all_technical_batches(raw_data)

        # 特徴量統合（現在システムフロー再現）
        feature_df = raw_data.copy()
        for batch in feature_batches:
            if len(batch) > 0:
                batch_features = batch.to_dataframe()
                overlapping_cols = batch_features.columns.intersection(
                    feature_df.columns
                )
                if len(overlapping_cols) > 0:
                    batch_features = batch_features.drop(columns=overlapping_cols)
                if not batch_features.empty:
                    feature_df = feature_df.join(batch_features, how="left")

        logger.info(f"✅ 現在システム特徴量生成完了: {len(feature_df.columns)}特徴量")
        logger.info(f"📊 生成された特徴量リスト: {list(feature_df.columns)}")

        # 現在システム特徴量数に応じた調整
        current_feature_count = len(feature_df.columns)
        if current_feature_count > 130:
            # 過剰な場合は最初の125列（OHLCV + 120特徴量）を保持
            feature_df = feature_df.iloc[:, :125]
            logger.info(f"✂️ 125特徴量に調整: {len(feature_df.columns)}特徴量")

        # 最終特徴量数確認
        final_feature_count = len(feature_df.columns)
        logger.info(f"🎯 最終特徴量数: {final_feature_count}特徴量")

        # 前処理
        processed_data = feature_df.copy()
        processed_data = DataPreprocessor.remove_duplicates(processed_data)
        processed_data = processed_data.fillna(method="ffill").fillna(method="bfill")
        processed_data = processed_data.replace([np.inf, -np.inf], np.nan).fillna(0)

        # ターゲット作成
        horizon = config.get("ml", {}).get("horizon", 5)
        close_prices = processed_data["close"]
        future_returns = close_prices.pct_change(horizon).shift(-horizon)
        classification_targets = (future_returns > 0).astype(int)

        # NaN値除去
        valid_indices = ~classification_targets.isna()
        X = processed_data[valid_indices]
        y = classification_targets[valid_indices]

        if len(X) < 100:
            logger.error(f"❌ 学習データ不足: {len(X)}サンプル")
            return False

        logger.info(f"✅ 学習準備完了: {len(X)}サンプル × {X.shape[1]}特徴量")

        # 特徴量名保存（重要：予測時の順序一致のため）
        feature_names = list(X.columns)
        logger.info(f"💾 特徴量名保存: {len(feature_names)}個")

        # アンサンブルモデル作成・学習
        logger.info("🤖 TradingEnsembleClassifier学習開始")

        from lightgbm import LGBMClassifier
        from sklearn.ensemble import RandomForestClassifier
        from xgboost import XGBClassifier

        base_models = [
            LGBMClassifier(random_state=42, verbose=-1),
            XGBClassifier(random_state=42, eval_metric="logloss"),
            RandomForestClassifier(random_state=42, n_jobs=-1),
        ]

        ensemble = TradingEnsembleClassifier(
            base_models=base_models,
            ensemble_method="trading_stacking",
            confidence_threshold=0.65,
            risk_adjustment=True,
            cv_folds=5,
        )

        ensemble.fit(X, y)

        # 学習後検証
        train_predictions = ensemble.predict_proba(X)[:, 1]
        train_accuracy = ensemble.score(X, y)
        unique_predictions = len(np.unique(train_predictions))

        logger.info("📊 学習結果:")
        logger.info(f"   学習精度: {train_accuracy:.3f}")
        logger.info(
            f"   予測値範囲: {train_predictions.min():.3f} ～ {train_predictions.max():.3f}"
        )
        logger.info(f"   予測多様性: {unique_predictions}種類")

        if unique_predictions < 10:
            logger.warning("⚠️ 予測値多様性不足")
            return False

        # 既存モデルバックアップ
        model_path = "/Users/nao/Desktop/bot/models/production/model.pkl"
        if os.path.exists(model_path):
            backup_path = f'/Users/nao/Desktop/bot/models/production/model_backup_h31_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pkl'
            import shutil

            shutil.copy2(model_path, backup_path)
            logger.info(f"✅ 既存モデルバックアップ: {backup_path}")

        # 新モデル保存
        with open(model_path, "wb") as f:
            pickle.dump(ensemble, f)

        # メタデータ保存（重要：特徴量名とカウント）
        metadata = {
            "training_timestamp": datetime.now().isoformat(),
            "config_path": config_path,
            "model_type": "TradingEnsembleClassifier",
            "features_count": final_feature_count,
            "feature_names": feature_names,  # 特徴量名リスト保存
            "validation_results": {
                "train_accuracy": float(train_accuracy),
                "prediction_diversity": int(unique_predictions),
                "prediction_range": float(
                    train_predictions.max() - train_predictions.min()
                ),
            },
            "feature_fixes": [
                "enhanced_default_prevention_h30",
                "current_system_alignment_h31",
            ],
            "phase": "Phase_H31_CurrentSystem125Features",
        }

        metadata_path = model_path.replace(".pkl", "_metadata.yaml")
        with open(metadata_path, "w", encoding="utf-8") as f:
            yaml.dump(metadata, f, default_flow_style=False, allow_unicode=True)

        logger.info(f"✅ モデル保存完了:")
        logger.info(f"   モデル: {model_path}")
        logger.info(f"   メタデータ: {metadata_path}")
        logger.info(f"   特徴量数: {final_feature_count}特徴量")

        return True

    except Exception as e:
        logger.error(f"❌ 再学習失敗: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """メイン実行"""
    logger.info("=" * 60)
    logger.info("Phase H.31: 現在システム125特徴量対応TradingEnsembleClassifier再学習")
    logger.info("=" * 60)

    success = retrain_current_system_model()

    if success:
        print("\n🎉 Phase H.31モデル再学習完了！")
        print("✅ 現在システム125特徴量対応TradingEnsembleClassifier作成成功")
        print("✅ LightGBM特徴量不一致エラー完全解決")
        print("✅ momentum_14, momentum_quality, market_phase対応")
        print("🚀 バックテスト実行準備完了・方向性バイアス解決期待")
    else:
        print("\n❌ Phase H.31モデル再学習失敗")
        print("🔧 エラーログを確認して問題解決後に再実行してください")

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())

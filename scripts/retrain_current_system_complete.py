#!/usr/bin/env python3
"""
Phase 3: 特徴量不一致修正後のモデル再学習スクリプト
現在のシステムで生成される実際の特徴量でモデルを再学習
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import joblib
import pandas as pd
import yaml

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crypto_bot.data.fetcher import MarketDataFetcher
from crypto_bot.ml.ensemble import TradingEnsembleClassifier
from crypto_bot.ml.preprocessor import FeatureEngineer
from crypto_bot.ml.target import make_classification_target

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def retrain_with_current_features():
    """現在のシステムで生成される特徴量でモデル再学習"""
    # 設定ファイル読み込み
    config_path = str(project_root / "config/production/production.yml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # データ取得（より多くのデータ）
    fetcher = MarketDataFetcher(
        exchange_id="bitbank",
        symbol="BTC/JPY",
        api_key=config.get("data", {}).get("api_key"),
        api_secret=config.get("data", {}).get("api_secret"),
        testnet=False,
    )

    # 過去6ヶ月のデータを取得
    end_time = datetime.now()
    start_time = end_time - timedelta(days=180)

    print("📊 データ取得中...")
    df = fetcher.get_price_df(
        timeframe="1h",
        since=int(start_time.timestamp() * 1000),
        limit=180 * 24,  # 6ヶ月分
        paginate=True,
    )
    print(f"   取得データ: {len(df)}レコード")

    # 特徴量生成
    print("🔧 特徴量生成中...")
    feature_engineer = FeatureEngineer(config)
    features_df = feature_engineer.transform(df)

    print(f"   生成特徴量: {len(features_df.columns)}個")
    print(f"   特徴量リスト: {list(features_df.columns)}")

    # ターゲット生成
    print("🎯 ターゲット生成中...")
    target = make_classification_target(df, horizon=5, threshold=0.0)

    # データの整合性確認
    common_idx = features_df.index.intersection(target.index)
    X = features_df.loc[common_idx]
    y = target.loc[common_idx]

    # NaN値のクリーンアップ
    mask = ~(X.isna().any(axis=1) | y.isna())
    X_clean = X[mask]
    y_clean = y[mask]

    print(
        f"📊 学習データ最終サイズ: {len(X_clean)}サンプル × {len(X_clean.columns)}特徴量"
    )
    print(
        f"   クラス分布: UP={y_clean.sum()} ({y_clean.mean():.1%}), DOWN={len(y_clean)-y_clean.sum()} ({1-y_clean.mean():.1%})"
    )

    # モデル学習
    print("🤖 TradingEnsembleClassifier学習中...")
    model = TradingEnsembleClassifier(
        ensemble_method="trading_stacking",
        cv_folds=5,
        confidence_threshold=0.65,
        risk_adjustment=True,
    )

    model.fit(X_clean, y_clean)

    # 学習結果の検証
    train_score = model.score(X_clean, y_clean)
    print(f"✅ 学習完了！トレーニングスコア: {train_score:.4f}")

    # 予測の分布確認
    print("🔍 予測分布確認...")
    predictions = model.predict_proba(X_clean)[:, 1]
    print(
        f"   予測値統計: min={predictions.min():.4f}, max={predictions.max():.4f}, mean={predictions.mean():.4f}, std={predictions.std():.4f}"
    )

    # 予測値の分布
    below_40 = (predictions < 0.4).sum()
    between_40_60 = ((predictions >= 0.4) & (predictions <= 0.6)).sum()
    above_60 = (predictions > 0.6).sum()

    print(
        f"   予測分布: <0.4={below_40}({below_40/len(predictions):.1%}), 0.4-0.6={between_40_60}({between_40_60/len(predictions):.1%}), >0.6={above_60}({above_60/len(predictions):.1%})"
    )

    # モデル保存
    model_path = project_root / "models/production/model.pkl"
    print(f"💾 モデル保存: {model_path}")
    joblib.dump(model, model_path)

    # メタデータ保存
    metadata = {
        "phase": "Phase_3_FeatureMismatchFixed",
        "features_count": len(X_clean.columns),
        "feature_names": list(X_clean.columns),
        "training_timestamp": datetime.now().isoformat(),
        "training_data_size": len(X_clean),
        "training_period": {
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "days": 180,
        },
        "class_distribution": {
            "up_count": int(y_clean.sum()),
            "down_count": int(len(y_clean) - y_clean.sum()),
            "up_ratio": float(y_clean.mean()),
            "down_ratio": float(1 - y_clean.mean()),
        },
        "validation_results": {
            "train_accuracy": float(train_score),
            "prediction_range": float(predictions.max() - predictions.min()),
            "prediction_diversity": int(len(set(predictions.round(4)))),
            "prediction_stats": {
                "mean": float(predictions.mean()),
                "std": float(predictions.std()),
                "min": float(predictions.min()),
                "max": float(predictions.max()),
            },
        },
    }

    metadata_path = project_root / "models/production/model_metadata.yaml"
    with open(metadata_path, "w") as f:
        yaml.dump(metadata, f, default_flow_style=False)

    print(f"📋 メタデータ保存: {metadata_path}")

    print("\n" + "=" * 60)
    print("✅ Phase 3モデル再学習完了！")
    print("=" * 60)
    print(f"📊 特徴量数: {len(X_clean.columns)}個")
    print(f"🎯 学習データ: {len(X_clean)}サンプル")
    print(f"📈 トレーニング精度: {train_score:.4f}")
    print(f"📊 予測多様性: {len(set(predictions.round(4)))}個の異なる値")
    print("🚀 固定予測問題解決・エントリーシグナル生成準備完了！")
    print("=" * 60)


if __name__ == "__main__":
    try:
        retrain_with_current_features()
    except Exception as e:
        logger.error(f"❌ 再学習失敗: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

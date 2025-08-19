#!/usr/bin/env python3
"""
97特徴量最適化・特徴量選択による勝率・損益改善スクリプト
Phase 2: 127→97特徴量最適化後のさらなる改善検証

アプローチ:
1. 段階的特徴量削減（97→80→60→40→30→20）
2. 各段階でバックテスト実行・勝率確認
3. 最適な特徴量数を特定
4. 重要度・相関分析による最終選択
"""

import json
import logging
import os
import sys
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.feature_selection import RFE, SelectKBest, f_classif
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.model_selection import train_test_split

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from crypto_bot.ml.feature_order_manager import FeatureOrderManager
from crypto_bot.ml.preprocessor import FeatureEngineer

# ログ設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_training_data():
    """97特徴量訓練データ生成"""
    np.random.seed(42)
    n_rows = 10000

    logger.info(f"97特徴量最適化用データ生成: {n_rows} samples")

    # より現実的な市場データシミュレーション
    t = np.arange(n_rows)

    # 複数の市場サイクル
    trend = 0.0001 * t  # 長期トレンド
    cycle1 = 0.1 * np.sin(2 * np.pi * t / 1000)  # 長期サイクル
    cycle2 = 0.05 * np.sin(2 * np.pi * t / 100)  # 中期サイクル
    noise = np.random.normal(0, 0.02, n_rows)  # ノイズ

    base_price = 100 * np.exp(trend + cycle1 + cycle2 + noise)

    # OHLCV生成
    high = base_price * (1 + np.abs(np.random.normal(0, 0.01, n_rows)))
    low = base_price * (1 - np.abs(np.random.normal(0, 0.01, n_rows)))
    volume = np.random.lognormal(mean=10, sigma=1, size=n_rows)

    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2023-01-01", periods=n_rows, freq="H"),
            "open": base_price,
            "high": high,
            "low": low,
            "close": base_price,
            "volume": volume,
        }
    )

    df.set_index("timestamp", inplace=True)
    return df


def generate_97_features(df, config):
    """97特徴量生成"""
    feature_engineer = FeatureEngineer(config)
    features_df = feature_engineer.transform(df)

    # 97特徴量システムに整合
    fom = FeatureOrderManager()
    features_df = fom.ensure_97_features_completeness(features_df)

    logger.info(f"97特徴量生成完了: {len(features_df.columns)} 特徴量")
    return features_df


def create_target(df):
    """改善されたターゲット生成"""
    # 価格変動率計算
    returns = df["close"].pct_change(periods=5).shift(-5)  # 5期間先の変動

    # より厳格な閾値（ノイズ除去）
    buy_threshold = 0.003  # 0.3%以上
    sell_threshold = -0.003  # -0.3%以下

    target = pd.Series(1, index=returns.index)  # デフォルトHOLD
    target[returns > buy_threshold] = 2  # BUY
    target[returns < sell_threshold] = 0  # SELL

    logger.info(f"ターゲット分布: {target.value_counts().to_dict()}")
    return target


def test_feature_count(features_df, target, n_features, test_name=""):
    """指定特徴量数でのモデル性能テスト"""
    logger.info(f"🧪 {test_name}: {n_features}特徴量でテスト開始")

    # 特徴量選択
    if n_features >= len(features_df.columns):
        selected_features = features_df
    else:
        # F統計量による重要特徴量選択
        selector = SelectKBest(score_func=f_classif, k=n_features)
        selected_features = pd.DataFrame(
            selector.fit_transform(features_df, target),
            columns=features_df.columns[selector.get_support()],
            index=features_df.index,
        )

    # 有効データフィルタ
    valid_mask = ~(selected_features.isna().any(axis=1) | target.isna())
    X = selected_features[valid_mask]
    y = target[valid_mask]

    if len(X) < 100:
        logger.warning(f"データ不足: {len(X)} samples")
        return None

    # 学習・テストデータ分割
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )

    # LightGBMモデル
    model = lgb.LGBMClassifier(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=6,
        num_leaves=31,
        random_state=42,
        verbose=-1,
    )

    # 学習
    model.fit(X_train, y_train)

    # 予測・評価
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average="weighted"
    )

    # 予測分布確認
    pred_distribution = pd.Series(y_pred).value_counts().to_dict()

    result = {
        "n_features": n_features,
        "feature_names": list(selected_features.columns),
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "prediction_distribution": pred_distribution,
        "data_points": len(X_test),
    }

    logger.info(f"✅ {n_features}特徴量結果: Accuracy={accuracy:.4f}, F1={f1:.4f}")
    return result


def run_97_feature_optimization():
    """97特徴量最適化実行"""
    logger.info("🚀 97特徴量最適化開始")

    # 設定読み込み
    config_path = Path("config/production/production.yml")
    if not config_path.exists():
        logger.error(f"設定ファイルが見つかりません: {config_path}")
        return False

    import yaml

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    # データ生成
    df = create_training_data()
    features_df = generate_97_features(df, config)
    target = create_target(df)

    # 段階的特徴量数テスト
    feature_counts = [97, 80, 60, 40, 30, 20, 15, 10]
    results = []

    for n_features in feature_counts:
        try:
            result = test_feature_count(
                features_df, target, n_features, test_name=f"Stage-{len(results)+1}"
            )
            if result:
                results.append(result)
        except Exception as e:
            logger.error(f"特徴量数{n_features}でエラー: {e}")
            continue

    # 結果保存
    output_dir = Path("results/97_feature_optimization")
    output_dir.mkdir(parents=True, exist_ok=True)

    results_summary = {
        "optimization_date": pd.Timestamp.now().isoformat(),
        "base_features": 97,
        "tested_counts": feature_counts,
        "results": results,
        "best_performance": (
            max(results, key=lambda x: x["f1_score"]) if results else None
        ),
    }

    output_file = output_dir / "optimization_results.json"
    with open(output_file, "w") as f:
        json.dump(results_summary, f, indent=2)

    # サマリー表示
    logger.info("📊 97特徴量最適化結果サマリー:")
    for result in results:
        logger.info(
            f"  {result['n_features']:2d}特徴量: "
            f"Accuracy={result['accuracy']:.4f}, "
            f"F1={result['f1_score']:.4f}"
        )

    if results:
        best = results_summary["best_performance"]
        logger.info(
            f"🎯 最適特徴量数: {best['n_features']} " f"(F1={best['f1_score']:.4f})"
        )

    logger.info(f"結果保存: {output_file}")
    return True


def main():
    """メイン実行"""
    try:
        success = run_97_feature_optimization()
        if success:
            logger.info("🎊 97特徴量最適化完了")
            sys.exit(0)
        else:
            logger.error("❌ 最適化失敗")
            sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 予期しないエラー: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

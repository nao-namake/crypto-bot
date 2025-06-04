#!/usr/bin/env python3
# =============================================================================
# ファイル名: tools/plot_pr_curve.py
# 説明:
#   機械学習モデル（分類器）のROC曲線・PR（Precision-Recall）曲線を
#   自動で描画・PNG出力するためのツールです。
#   - データは data/ohlcv.csv から読み込み
#   - モデルは model/calibrated_model.pkl からロード
#   - 結果は results/roc_curve.png / pr_curve.png に保存
#
# 【主な機能】
#   - モデルの識別性能（AUC、精度-再現率）の可視化
#   - 自動でグラフ生成・保存
#
# 【使い方例】
#   python tools/plot_pr_curve.py
#
# 【前提】
#   - ohlcv.csv: "data/ohlcv.csv" にインデックス付きで保存済み
#   - モデル: "model/calibrated_model.pkl" に保存済み
#   - config: "config/default.yml" に設定済み
# =============================================================================

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import yaml
from sklearn.metrics import auc, precision_recall_curve, roc_curve

from crypto_bot.ml.model import MLModel
from crypto_bot.ml.preprocessor import prepare_ml_dataset

matplotlib.rcParams["font.family"] = [
    "AppleGothic",
    "Arial Unicode MS",
    "Helvetica",
    "sans-serif",
]


def main():
    # 1) 設定ファイル読み込み
    cfg = yaml.safe_load(open("config/default.yml"))
    model_path = "model/calibrated_model.pkl"

    # 2) モデル読み込み
    model = MLModel.load(model_path)

    # 3) 生データ読み込み
    raw_df = pd.read_csv(
        Path("data").joinpath("ohlcv.csv"),
        parse_dates=["datetime"],
        index_col="datetime",
    )

    # 4) 特徴量・ラベル作成
    X_all, y_reg, y_clf = prepare_ml_dataset(raw_df, cfg)

    # 5) 検証用データ分割
    X_val = X_all
    y_true = y_clf

    # 6) 予測確率取得
    y_prob = model.predict_proba(X_val)[:, 1]

    # 7) ROC 曲線
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    roc_auc = auc(fpr, tpr)
    plt.figure()
    plt.plot(fpr, tpr)
    plt.title(f"ROC Curve (AUC = {roc_auc:.3f})")
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.tight_layout()
    plt.savefig("results/roc_curve.png")
    plt.close()

    # 8) PR 曲線
    precision, recall, _ = precision_recall_curve(y_true, y_prob)
    pr_auc = auc(recall, precision)
    plt.figure()
    plt.plot(recall, precision)
    plt.title(f"PR Curve (AUC = {pr_auc:.3f})")
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.tight_layout()
    plt.savefig("results/pr_curve.png")
    plt.close()

    print("[INFO] Saved ROC to results/roc_curve.png")
    print("[INFO] Saved PR to results/pr_curve.png")


if __name__ == "__main__":
    main()

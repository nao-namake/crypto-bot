#!/usr/bin/env python3
# =============================================================================
# ファイル名: tools/calibrate_model.py
# 説明:
#   既存のMLモデル（LightGBMやXGBoostなど）の出力確率を「キャリブレーション」するツールです。
#   （Platt's Scalingなどの手法で出力確率を正規化し、予測の信頼性を高めます）
#
# 【用途】
#   - 学習済みモデルの予測確率が過学習や偏りで“ズレている”場合、
#     最新データの一部でキャリブレーションして、より信頼性の高い予測値に変換します。
#
# 【使い方例】
#   python tools/calibrate_model.py \
#       --config config/default.yml \
#       --model model/best_model.pkl \
#       --output model/calibrated_model.pkl
#
#   # 引数を省略した場合、config/default.yml の設定が利用されます。
#
# 【前提条件】
#   - 最新OHLCVデータが data/ohlcv.csv に保存されている必要があります
#     （index=日時, カラム=open,high,low,close,volumeなど）
#   - モデルは MLModel.save() 形式（joblibファイル）で保存されている必要があります
# =============================================================================

import argparse
from pathlib import Path

import pandas as pd
import yaml
from sklearn.calibration import CalibratedClassifierCV

from crypto_bot.ml.model import MLModel
from crypto_bot.ml.preprocessor import prepare_ml_dataset


def _parse_args():
    parser = argparse.ArgumentParser(
        description="Calibrate a pre‑trained classifier with the latest data window."
    )
    parser.add_argument(
        "-c",
        "--config",
        default="config/default.yml",
        help="Path to config YAML (default: %(default)s)",
    )
    parser.add_argument(
        "-m",
        "--model",
        default=None,
        help="Path to the *input* trained model (overrides config).",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="model/calibrated_model.pkl",
        help="Path to save the *output* calibrated model (default: %(default)s)",
    )
    return parser.parse_args()


def main():
    args = _parse_args()
    # 1) 設定＆生データ読み込み
    cfg = yaml.safe_load(open(args.config))
    # 生データCSVを1列目を日時インデックスとして読み込む
    raw_csv = Path("data") / "ohlcv.csv"
    raw_df = pd.read_csv(raw_csv, index_col=0, parse_dates=True)

    # 2) 特徴量・ラベル作成
    X_all, y_reg, y_clf = prepare_ml_dataset(raw_df, cfg)
    test_w = cfg["walk_forward"]["test_window"]
    X_calib = X_all.iloc[-test_w:]
    y_calib = y_clf.iloc[-test_w:]

    # 3) モデル読み込み
    model_path = args.model or cfg["strategy"]["params"]["model_path"]
    model = MLModel.load(model_path)

    # 4) キャリブレーション
    #    method: 'sigmoid' (Platt’s Scaling) or 'isotonic'
    calibrator = CalibratedClassifierCV(
        estimator=model.estimator, method="sigmoid", cv="prefit"
    )
    calibrator.fit(X_calib, y_calib)

    # 5) 保存
    calibrated_model = MLModel(calibrator)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    calibrated_model.save(out_path)
    print(f"[INFO] Calibrated model saved to {out_path}")


if __name__ == "__main__":
    main()

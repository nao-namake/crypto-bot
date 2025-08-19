#!/usr/bin/env python3
"""
RSI特徴量解析デバッグスクリプト
"""

import sys
from pathlib import Path

import yaml

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from crypto_bot.ml.feature_engines.batch_calculator import BatchFeatureCalculator
from crypto_bot.ml.feature_engines.technical_engine import TechnicalFeatureEngine

# 設定ファイル読み込み
config_path = str(project_root / "config/production/production.yml")
with open(config_path, "r") as f:
    config = yaml.safe_load(f)

# BatchCalculatorとTechnicalFeatureEngine作成
batch_calc = BatchFeatureCalculator(config)
tech_engine = TechnicalFeatureEngine(config, batch_calc)

# 解析結果表示
print("=" * 60)
print("🔍 RSI設定解析結果")
print("=" * 60)

# extra_features内のRSI関連特徴量
extra_features = config["ml"].get("extra_features", [])
rsi_features = [f for f in extra_features if "rsi" in f.lower()]
print(f"\n📊 extra_features内のRSI特徴量: {len(rsi_features)}個")
for feat in rsi_features:
    print(f"  - {feat}")

# 解析されたRSI設定
rsi_config = tech_engine.technical_configs["rsi"]
print(f"\n📊 解析されたRSI設定:")
print(f"  - periods: {rsi_config['periods']}")
print(f"  - single_calls: {rsi_config['single_calls']}")

# _parse_technical_featuresメソッドのデバッグ
print("\n🔍 特徴量解析ロジックのテスト:")
for feat in ["rsi_7", "rsi_14", "rsi_21", "rsi"]:
    feat_lc = feat.lower()
    if "_" in feat_lc:
        base, _, param = feat_lc.partition("_")
        print(f"\n  '{feat}' → base='{base}', param='{param}'")
        if param.isdigit():
            period = int(param)
            print(f"    → 期間として認識: {period}")
        else:
            print(f"    → 期間として認識されない")
    else:
        print(f"\n  '{feat}' → アンダースコアなし")
        if feat_lc == "rsi":
            print(f"    → デフォルト期間 [7, 14, 21] を使用")

print("\n" + "=" * 60)

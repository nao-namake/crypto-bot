#!/usr/bin/env python3
"""
RSI生成エラーの修正スクリプト
technical_engine.pyのcalculate_rsi_batchメソッドを修正
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 修正内容
fix_content = '''    def calculate_rsi_batch(self, df: pd.DataFrame) -> FeatureBatch:
        """RSI指標バッチ計算"""
        periods = self.technical_configs["rsi"]["periods"]
        if not periods:
            return FeatureBatch("rsi_batch", {})

        try:
            rsi_features = {}
            close_series = df["close"]

            # 各期間のRSI計算
            for period in periods:
                try:
                    if self.indicator_available and self.ind_calc:
                        # IndicatorCalculator使用
                        rsi_values = self.ind_calc.rsi(close_series, window=period)
                    else:
                        # 内蔵RSI計算
                        rsi_values = self._calculate_rsi_builtin(close_series, period)

                    rsi_features[f"rsi_{period}"] = rsi_values
                except Exception as e:
                    logger.error(f"❌ RSI_{period} calculation failed: {e}")
                    # 個別のRSI計算が失敗してもバッチ全体は継続

            # RSI oversold/overbought特徴量を追加
            if "rsi_14" in rsi_features:
                rsi_14 = rsi_features["rsi_14"]
                rsi_features["rsi_oversold"] = (rsi_14 < 30).astype(int)
                rsi_features["rsi_overbought"] = (rsi_14 > 70).astype(int)

            logger.info(f"✅ RSI batch: {len(rsi_features)} indicators ({periods})")
            return self.batch_calc.create_feature_batch(
                "rsi_batch", rsi_features, df.index
            )

        except Exception as e:
            logger.error(f"❌ RSI batch calculation failed: {e}")
            import traceback
            traceback.print_exc()
            return FeatureBatch("rsi_batch", {})'''

# ファイルパス
technical_engine_path = (
    project_root / "crypto_bot/ml/feature_engines/technical_engine.py"
)

# 実際の修正は行わず、問題点と解決策を出力
print("=" * 60)
print("🔧 RSI生成問題の分析と解決策")
print("=" * 60)

print("\n📊 問題の特定:")
print("1. RSIバッチが空で返されている（サイズ0）")
print("2. エラーがサイレントに処理されている可能性")
print("3. IndicatorCalculatorのRSI計算が失敗している可能性")

print("\n🔧 推奨される修正:")
print("1. エラーログを追加して失敗原因を特定")
print("2. 個別のRSI計算失敗でもバッチ全体は継続")
print("3. トレースバック出力を追加")

print("\n📝 修正方法:")
print(f"ファイル: {technical_engine_path}")
print("メソッド: calculate_rsi_batch()")
print("変更点: try-except内にログ追加、個別期間のエラー処理")

# テスト用RSI計算
print("\n🧪 RSI計算テスト:")
try:
    import numpy as np
    import pandas as pd

    # テストデータ作成
    test_data = pd.DataFrame(
        {
            "close": [100, 102, 101, 103, 105, 104, 106, 108, 107, 109]
            * 5  # 50データポイント
        }
    )

    # 内蔵RSI計算テスト
    def calculate_rsi_builtin(series: pd.Series, period: int) -> pd.Series:
        """内蔵RSI計算"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50)

    # 各期間のRSI計算
    for period in [7, 14, 21]:
        rsi = calculate_rsi_builtin(test_data["close"], period)
        print(f"  - RSI_{period}: 最初の値={rsi.iloc[period:period+3].tolist()}")

except Exception as e:
    print(f"  ❌ テスト失敗: {e}")
    import traceback

    traceback.print_exc()

print("\n" + "=" * 60)

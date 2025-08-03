#!/usr/bin/env python3
"""
IndicatorCalculatorのRSI計算をテスト
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from crypto_bot.indicator.calculator import IndicatorCalculator

    indicator_available = True
except ImportError:
    indicator_available = False
    print("⚠️ IndicatorCalculator not available")

if indicator_available:
    # テストデータ作成
    test_data = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109] * 5)
    print(f"📊 テストデータ: {len(test_data)}データポイント")
    print(f"   最初の10値: {test_data.head(10).tolist()}")

    # IndicatorCalculator作成
    ind_calc = IndicatorCalculator()

    print("\n🔍 RSI計算テスト:")
    for period in [7, 14, 21]:
        try:
            # RSI計算
            rsi_result = ind_calc.rsi(test_data, window=period)

            print(f"\nRSI_{period}:")
            print(f"  - 結果の型: {type(rsi_result)}")
            print(f"  - Noneチェック: {rsi_result is None}")

            if rsi_result is not None:
                if isinstance(rsi_result, pd.Series):
                    print(f"  - サイズ: {len(rsi_result)}")
                    print(f"  - NaN数: {rsi_result.isna().sum()}")
                    print(
                        f"  - 有効値の最初の5個: {rsi_result.dropna().head(5).tolist()}"
                    )
                elif isinstance(rsi_result, pd.DataFrame):
                    print(f"  - DataFrame形状: {rsi_result.shape}")
                    print(f"  - カラム: {list(rsi_result.columns)}")
                    # 最初のカラムを取得
                    first_col = rsi_result.iloc[:, 0]
                    print(f"  - 最初のカラムの型: {type(first_col)}")
                    print(
                        f"  - 最初のカラムの有効値: {first_col.dropna().head(5).tolist()}"
                    )
                else:
                    print(f"  - 予期しない型: {rsi_result}")

        except Exception as e:
            print(f"  ❌ エラー: {e}")
            import traceback

            traceback.print_exc()

    # メソッドの存在確認
    print("\n🔍 IndicatorCalculatorメソッド確認:")
    methods = [method for method in dir(ind_calc) if not method.startswith("_")]
    print(f"  利用可能なメソッド: {methods[:10]}... (最初の10個)")
    if "rsi" in methods:
        print(f"  ✅ rsiメソッドが存在します")
    else:
        print(f"  ❌ rsiメソッドが見つかりません")

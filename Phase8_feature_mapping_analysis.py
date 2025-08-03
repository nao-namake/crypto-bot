#!/usr/bin/env python3
"""
Phase 8.1: production.yml 92特徴量完全マッピング・実装分析

92特徴量の完全分類・実装複雑度・優先度評価を行う
"""

import yaml
from typing import Dict, List, Tuple

def analyze_92_features():
    """production.yml 92特徴量の完全分析"""
    
    with open('config/production/production.yml', 'r') as f:
        config = yaml.safe_load(f)
    
    extra_features = config['ml']['extra_features']
    print(f"=== Phase 8.1: 92特徴量完全マッピング分析 ===")
    print(f"総特徴量数: {len(extra_features)}個\n")
    
    # 重複なし正確分類（最主要カテゴリのみに分類）
    feature_categories = {
        # 優先度：高（基本テクニカル指標）
        "基本ラグ特徴量": ["close_lag_1", "close_lag_3"],  # volume_lagは出来高系に移動
        "リターン系": ["returns_1", "returns_2", "returns_3", "returns_5", "returns_10"],
        "EMA系": ["ema_5", "ema_10", "ema_20", "ema_50", "ema_100", "ema_200"],
        "RSI系": ["rsi_14", "rsi_oversold", "rsi_overbought"],
        "MACD系": ["macd", "macd_signal", "macd_hist", "macd_cross_up", "macd_cross_down"],
        "ATR・ボラティリティ系": ["atr_14", "volatility_20"],
        
        # 優先度：高（価格ポジション・バンド系）
        "価格ポジション系": ["price_position_20", "price_position_50", "price_vs_sma20", "intraday_position"],
        "ボリンジャーバンド系": ["bb_position", "bb_upper", "bb_middle", "bb_lower", "bb_width", "bb_squeeze"],
        
        # 優先度：中（出来高・モメンタム系）
        "出来高系": ["volume_lag_1", "volume_lag_4", "volume_lag_5", "volume_sma_20", "volume_ratio", "volume_trend", "vwap", "vwap_distance", "obv", "obv_sma", "cmf", "mfi", "ad_line", "volume_breakout"],
        "ストキャスティクス系": ["stoch_k", "stoch_d", "stoch_oversold", "stoch_overbought"],
        "オシレーター系": ["cci_20", "williams_r", "ultimate_oscillator", "momentum_14"],
        
        # 優先度：中（トレンド・パターン系）
        "ADX・トレンド系": ["adx_14", "plus_di", "minus_di", "trend_strength", "trend_direction"],
        "サポート・レジスタンス系": ["support_distance", "resistance_distance", "support_strength", "price_breakout_up", "price_breakout_down"],
        "チャートパターン系": ["doji", "hammer", "engulfing", "pinbar"],
        
        # 優先度：低（統計・時間・高度系）
        "統計系": ["zscore", "close_std_10"],
        "時間特徴量系": ["hour", "day_of_week", "is_weekend", "is_asian_session", "is_us_session"],
        "高度テクニカル系": ["roc_10", "roc_20", "trix", "mass_index", "keltner_upper", "keltner_lower", "donchian_upper", "donchian_lower", "ichimoku_conv", "ichimoku_base"],
        "市場状態系": ["price_efficiency", "trend_consistency", "volume_price_correlation", "volatility_regime", "momentum_quality", "market_phase"]
    }
    
    # 実装複雑度評価（1=簡単、5=複雑）
    implementation_complexity = {
        # 複雑度 1-2: 基本計算
        "基本ラグ特徴量": 1,
        "リターン系": 1,
        "EMA系": 2,
        "RSI系": 2,
        "統計系": 2,
        "時間特徴量系": 1,
        
        # 複雑度 3: 中程度
        "価格ポジション系": 3,
        "ボリンジャーバンド系": 3,
        "MACD系": 3,
        "ストキャスティクス系": 3,
        "ATR・ボラティリティ系": 3,
        
        # 複雑度 4: 高度
        "出来高系": 4,
        "オシレーター系": 4,
        "ADX・トレンド系": 4,
        "高度テクニカル系": 4,
        
        # 複雑度 5: 最高度
        "サポート・レジスタンス系": 5,
        "チャートパターン系": 5,
        "市場状態系": 5,
    }
    
    # 実装優先度評価（1=最高、5=最低）
    implementation_priority = {
        # 最高優先度（ML予測に直接影響）
        "EMA系": 1,
        "RSI系": 1,
        "MACD系": 1,
        "基本ラグ特徴量": 1,
        "リターン系": 1,
        
        # 高優先度
        "価格ポジション系": 2,
        "ボリンジャーバンド系": 2,
        "ATR・ボラティリティ系": 2,
        "統計系": 2,
        
        # 中優先度
        "出来高系": 3,
        "ストキャスティクス系": 3,
        "オシレーター系": 3,
        "時間特徴量系": 3,
        
        # 低優先度
        "ADX・トレンド系": 4,
        "高度テクニカル系": 4,
        
        # 最低優先度（実装コストが高い）
        "サポート・レジスタンス系": 5,
        "チャートパターン系": 5,
        "市場状態系": 5,
    }
    
    total_features = 0
    print("📊 カテゴリ別詳細分析:\n")
    
    for category, features in feature_categories.items():
        complexity = implementation_complexity[category]
        priority = implementation_priority[category]
        
        print(f"【{category}】（{len(features)}個）")
        print(f"  実装複雑度: {complexity}/5")
        print(f"  実装優先度: {priority}/5")
        print(f"  特徴量:")
        for feature in features:
            print(f"    - {feature}")
        print()
        
        total_features += len(features)
    
    print(f"✅ 総確認: {total_features}個（期待値: {len(extra_features)}個）")
    
    # 不足・余剰特徴量の確認
    all_categorized = []
    for features in feature_categories.values():
        all_categorized.extend(features)
    
    missing = set(extra_features) - set(all_categorized)
    extra = set(all_categorized) - set(extra_features)
    
    if missing:
        print(f"\n❌ 分類漏れ: {len(missing)}個")
        for f in missing:
            print(f"  - {f}")
    
    if extra:
        print(f"\n❌ 余剰分類: {len(extra)}個")
        for f in extra:
            print(f"  - {f}")
    
    # 実装推奨順序
    print(f"\n🎯 Phase 8.2 実装推奨順序:")
    categories_by_priority = sorted(feature_categories.items(), 
                                  key=lambda x: (implementation_priority[x[0]], implementation_complexity[x[0]]))
    
    for i, (category, features) in enumerate(categories_by_priority, 1):
        priority = implementation_priority[category]
        complexity = implementation_complexity[category]
        print(f"  {i:2d}. {category}: {len(features)}個 (優先度:{priority}, 複雑度:{complexity})")
    
    return feature_categories, implementation_complexity, implementation_priority

if __name__ == "__main__":
    analyze_92_features()
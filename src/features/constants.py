"""
特徴量・戦略の共有定数 - Phase 87 H7 / Phase 89-β / Phase 89-γ / Phase 89-δ

silent failure（特徴量数不一致・戦略不足）を構造的に防止するため、
EXPECTED_FEATURE_COUNT と STRATEGY_COUNT を単一定義する。

Phase 89-β: 37 → 47（funding 1 + sentiment 1 + microstructure 3 + macro_lite 5 = +10）
Phase 89-γ: 47 → 52（microstructure_advanced: VPIN 3 + HMM 状態確率 2 = +5）
Phase 89-δ: 52 → 55（cross_asset: eth_btc_price_ratio + eth_btc_corr_24h + eth_returns_15m = +3）
"""

EXPECTED_FEATURE_COUNT: int = 55
STRATEGY_COUNT: int = 6

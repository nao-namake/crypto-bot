# strategy/ - 取引戦略実装・シグナル生成

## 📋 概要

**Trading Strategy Implementation & Signal Generation System**  
本フォルダは crypto-bot の取引戦略実装を管理し、各種取引アルゴリズム、シグナル生成、エントリー/エグジット判定を担当します。

**🎊 Phase 16.10最適化完了**: 2025年8月8日  
**整理効果**: 22個→18個（18%削減）・1,472行削除・重複解消・保守性向上

## 🎯 主要機能

### **戦略基盤**
- 統一戦略インターフェース（抽象基底クラス）
- シグナル生成（BUY/SELL/EXIT）
- ポジション管理統合
- 戦略ファクトリー・レジストリ

### **機械学習戦略**
- MLモデル予測ベース戦略
- アンサンブル戦略
- マルチタイムフレーム統合
- 信頼度ベース判定

### **テクニカル戦略**
- 移動平均戦略
- RCI×MACD逆張り（もちぽよシグナル）
- ボリンジャーバンド戦略
- 複合テクニカル指標

### **取引所特化戦略**
- Bitbank専用戦略群
- 手数料最適化（メイカー優先）
- 信用取引対応
- JPY建て特化実装

## 📁 ファイル構成

```
strategy/                                   # Phase 16.10最適化後（18個）
├── __init__.py                              # パッケージ初期化
├── README.md                                # 本ドキュメント
│
├── ✅ 基盤・管理ファイル（4個）
├── base.py                                  # 抽象基底クラス（29行）
├── factory.py                               # 戦略ファクトリー（223行）
├── registry.py                              # 戦略レジストリ（174行）
└── composite.py                             # 複合戦略（195行）
│
├── ✅ ML・テクニカル戦略ファイル（5個）
├── ml_strategy.py                           # 基本ML戦略（540行）
├── aggressive_ml_strategy.py                # 積極的ML戦略（635行）
├── ensemble_ml_strategy.py                  # アンサンブルML戦略（440行）
├── multi_timeframe_ensemble.py              # マルチタイムフレーム統合（768行）
└── simple_ma.py                             # 移動平均・ボリンジャー戦略（181行）
│
└── ✅ Bitbank特化戦略ファイル（8個・要統合検討）
├── bitbank_btc_jpy_strategy.py              # BTC/JPY戦略（1,159行）
├── bitbank_xrp_jpy_strategy.py              # XRP/JPY戦略（1,024行）
├── bitbank_integrated_day_trading_system.py # 統合日中システム（1,054行）
├── bitbank_enhanced_position_manager.py     # ポジション管理（994行）
├── bitbank_taker_avoidance_strategy.py      # テイカー回避戦略（899行）
├── bitbank_execution_orchestrator.py        # 実行オーケストレータ（712行）
├── bitbank_day_trading_strategy.py          # 日中取引戦略（634行）
└── bitbank_integrated_strategy.py           # 統合戦略（527行）

📦 archive/legacy_systems/移動済み（Phase 16.10）
├── strategy_deprecated_files/               # 非推奨戦略ファイル（1,179行）
│   └── multi_timeframe_ensemble_strategy.py # 古い重複実装
└── exchange/bitbank/ 削除済み              # 未使用統合ファイル（293行）
```

## 🔍 各ファイルの役割

### **base.py**
- `StrategyBase`抽象クラス - 全戦略の基底
- `logic_signal()`抽象メソッド - 実装必須
- 統一インターフェース提供
- 型安全性保証

### **ml_strategy.py**
- `MLStrategy`クラス - 基本ML戦略
- 特徴量生成・標準化
- モデル予測・信頼度計算
- テクニカルシグナル統合

### **multi_timeframe_ensemble_strategy.py**
- `MultiTimeframeEnsembleStrategy`クラス
- 15分/1時間/4時間統合
- タイムフレーム間投票
- データ品質管理

### **bitbank_integrated_strategy.py**
- `BitbankIntegratedStrategy`クラス
- Bitbank専用最適化
- 手数料戦略統合
- 信用取引対応

### **factory.py**
- `StrategyFactory`クラス - 戦略生成
- 設定ベース動的生成
- パラメータ注入
- エラーハンドリング

### **registry.py**
- `StrategyRegistry`クラス - 戦略管理
- 利用可能戦略一覧
- 動的登録・削除
- メタデータ管理

## 🚀 使用方法

### **基本的な戦略使用**
```python
from crypto_bot.strategy.factory import StrategyFactory

# 戦略生成
strategy = StrategyFactory.create_strategy(
    strategy_type="ml",
    config={
        "model_path": "models/production/model.pkl",
        "threshold": 0.05
    }
)

# シグナル生成
signal = strategy.logic_signal(price_df, current_position)
if signal.side == "BUY":
    execute_buy_order()
```

### **マルチタイムフレーム戦略**
```python
from crypto_bot.strategy.multi_timeframe_ensemble_strategy import MultiTimeframeEnsembleStrategy

mtf_strategy = MultiTimeframeEnsembleStrategy(
    config={
        "timeframes": ["15m", "1h", "4h"],
        "weights": [0.3, 0.5, 0.2],
        "consensus_threshold": 0.6
    }
)

# 複数タイムフレームからのシグナル
signal = mtf_strategy.logic_signal(multi_tf_data, position)
```

### **Bitbank特化戦略**
```python
from crypto_bot.strategy.bitbank_integrated_strategy import BitbankIntegratedStrategy

bitbank_strategy = BitbankIntegratedStrategy(
    config={
        "prefer_maker": True,
        "margin_trading": True,
        "risk_level": "moderate"
    }
)

# 手数料最適化込みシグナル
optimized_signal = bitbank_strategy.generate_optimized_signal(data)
```

## ✅ Phase 16.10最適化完了効果

### **構造最適化達成**
- **ファイル削減**: 22個→18個（18%削減）・1,472行削除完了
- **重複解消**: MultiTimeframeEnsembleStrategyクラス名重複解決・混乱除去
- **未使用削除**: exchange/bitbank/統合ファイル（293行）完全削除
- **保守性向上**: 非推奨ファイルのarchive管理・トレーサビリティ維持

### **分類体系確立**
- **基盤・管理ファイル** (4個): base.py, factory.py, registry.py, composite.py
- **ML・テクニカル戦略ファイル** (5個): 効率的な戦略実装群
- **Bitbank特化戦略ファイル** (8個): 統合検討対象として明確化

## ⚠️ 継続課題・改善点

### **Bitbank戦略群統合（優先度: 高）**
- 8ファイル8,003行の重複設計パターン継続
- 同じimport依存関係・類似クラス構造
- テスト依存により段階的統合が必要

### **抽象化強化（優先度: 中）**
- 取引所別基底クラス未実装
- 共通ロジックの抽出不足
- インターフェース統一性

### **テスト・ドキュメント充実（優先度: 中）**
- 戦略単体テストの充実
- バックテスト統合テスト強化
- パラメータ最適値ガイド策定

## 📝 今後の展開

### **Phase 16.10完了後の発展方向**

1. **Bitbank戦略群統合（次期Phase優先）**
   - 8ファイル8,003行の段階的統合
   - テスト依存関係の段階的修正
   - 共通基底クラス抽出・重複除去

2. **戦略階層再編（理想構成）**
   ```
   strategy/
   ├── base/          # 基底クラス群・共通ロジック
   ├── technical/     # テクニカル戦略（Phase 16.10分類済み）
   ├── ml/           # ML戦略（Phase 16.10分類済み）
   ├── exchange/     # 取引所別戦略（統合版）
   │   ├── bitbank/  # 8ファイル→2-3ファイル統合
   │   └── bybit/    # 将来対応
   └── composite/    # 複合戦略
   ```

3. **次世代機能統合**
   - 自動パラメータ調整・A/Bテスト
   - 戦略パフォーマンス追跡・適応型切替
   - 裁定取引・ペアトレーディング・DeFi統合
   - バックテスト専用・ウォークフォワード分析

4. **archive管理システム**
   - legacy_systems/からの機能復元プロセス
   - 非推奨ファイルの定期評価・現代化
   - Phase整理の継続的改善

---

**Phase 16.10完全達成**: crypto_bot/strategy/フォルダが最適構成に整理され、明確な分類体系と継続改善方向が確立されました。🎊
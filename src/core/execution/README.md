# core/execution/ - 実行モード管理システム

**Phase 14-B リファクタリング**: orchestrator.pyから分離した実行モード機能の統合管理モジュールです。バックテスト・ペーパートレード・ライブトレードの実行を担当し、統一されたインターフェースを提供します。

## 🎯 目的・責任

### **単一責任**: 実行モード別処理・フロー制御
- バックテストモード実行・結果生成
- ペーパートレードモード実行・統計管理
- ライブトレードモード実行・実取引処理
- モード切り替え・設定適用

### **分離された機能**: orchestrator.pyから約200行削減
- `run_backtest()` → `BacktestRunner`
- `run_paper_trading()` → `PaperTradingRunner`
- `run_live_trading()` → `LiveTradingRunner`

## 📁 ファイル構成

```
execution/
├── __init__.py              # モジュール初期化・エクスポート
├── README.md               # このファイル（使用方法・設計思想）
├── base_runner.py          # 基底ランナークラス・共通機能（191行）
├── paper_trading_runner.py # ペーパートレードモード実行（216行）
└── live_trading_runner.py  # ライブトレードモード実行（293行）
```

## 🔧 主要クラス・設計

### **BaseRunner - 基底クラス**
```python
class BaseRunner:
    """実行モードの基底クラス"""
    
    def __init__(self, orchestrator_ref, logger: CryptoBotLogger):
        self.orchestrator = orchestrator_ref
        self.logger = logger
        self.config = orchestrator_ref.config
    
    async def run(self) -> bool:
        """実行モード共通インターフェース"""
        raise NotImplementedError
    
    async def initialize_mode(self) -> bool:
        """モード初期化（共通処理）"""
        pass
    
    async def cleanup_mode(self):
        """モード終了処理（共通処理）"""
        pass
```

### **BacktestRunner - バックテスト専用**
```python  
class BacktestRunner(BaseRunner):
    """バックテストモード実行クラス"""
    
    async def run(self) -> bool:
        """バックテスト実行"""
        pass
    
    async def setup_backtest_engine(self) -> BacktestEngine:
        """バックテストエンジン初期化"""
        pass
    
    async def process_backtest_results(self, results: Dict):
        """バックテスト結果処理・レポート生成"""
        pass
```

### **PaperTradingRunner - ペーパートレード専用**
```python
class PaperTradingRunner(BaseRunner):
    """ペーパートレードモード実行クラス"""
    
    async def run(self) -> bool:
        """ペーパートレード実行"""
        pass
    
    async def execute_paper_trading_cycle(self) -> Dict:
        """ペーパートレードサイクル実行"""
        pass
    
    async def track_session_statistics(self, stats: Dict):
        """セッション統計追跡・レポート生成"""
        pass
```

### **LiveTradingRunner - ライブトレード専用**
```python
class LiveTradingRunner(BaseRunner):
    """ライブトレードモード実行クラス"""
    
    async def run(self) -> bool:
        """ライブトレード実行"""
        pass
    
    async def execute_live_trading_cycle(self) -> Dict:
        """ライブトレードサイクル実行"""
        pass
    
    async def validate_live_trading_conditions(self) -> bool:
        """ライブトレード実行条件確認"""
        pass
```

## 📊 使用例・インテグレーション

### **基本使用法**
```python
from src.core.execution import PaperTradingRunner, LiveTradingRunner

# ペーパートレード実行
paper_runner = PaperTradingRunner(orchestrator_ref, logger)  
paper_success = await paper_runner.run()

# ライブトレード実行
live_runner = LiveTradingRunner(orchestrator_ref, logger)
live_success = await live_runner.run()
```

### **orchestrator.pyとの統合**
```python
# orchestrator.py内での使用（簡素化後）
class TradingOrchestrator:
    def __init__(self, ...):
        self.backtest_runner = BacktestRunner(self, self.logger)
        self.paper_runner = PaperTradingRunner(self, self.logger)
        self.live_runner = LiveTradingRunner(self, self.logger)
    
    async def run(self):
        """統一実行インターフェース"""
        mode = self.config.mode
        
        if mode == "paper":
            return await self.paper_runner.run()
        elif mode == "live":
            return await self.live_runner.run()
        else:
            raise ValueError(f"無効なモード: {mode}")
```

## 🎯 設計原則・利点

### **戦略パターン（Strategy Pattern）**
- 実行モードアルゴリズムの交換可能性
- 実行時モード切り替え・動的選択
- 共通インターフェースによる一貫性

### **テンプレートメソッドパターン**
- BaseRunnerによる共通処理定義
- 各モードの専門処理実装
- 初期化・終了処理の統一

### **ファクトリーパターン適用可能**
```python
class ModeRunnerFactory:
    @staticmethod
    def create_runner(mode: str, orchestrator_ref, logger) -> BaseRunner:
        if mode == "backtest":
            return BacktestRunner(orchestrator_ref, logger)
        elif mode == "paper":
            return PaperTradingRunner(orchestrator_ref, logger)
        elif mode == "live":  
            return LiveTradingRunner(orchestrator_ref, logger)
        else:
            raise ValueError(f"未対応モード: {mode}")
```

## 🔄 モード切り替え・設定管理

### **Phase 14-A設定統合**
```python
class BaseRunner:
    def get_mode_interval(self) -> int:
        """モード別実行間隔取得（Phase 14-A外部化設定）"""
        from ..config import get_threshold
        
        if self.config.mode == "paper":
            return get_threshold("execution.paper_mode_interval_seconds", 60)
        elif self.config.mode == "live":
            return get_threshold("execution.live_mode_interval_seconds", 180)
        else:
            return 1  # バックテスト用
```

### **環境別設定適用**
- **paper**: 高頻度実行（1分間隔）・リスクなし検証
- **live**: 低頻度実行（3分間隔）・実取引慎重実行
- **backtest**: 一回実行・過去データ分析

## 🧪 テスト戦略

### **単体テスト**
```python
# tests/unit/core/modes/test_backtest_runner.py
class TestBacktestRunner:
    def test_backtest_execution(self):
        """バックテスト実行テスト"""
        pass
    
    def test_results_processing(self):
        """結果処理テスト"""  
        pass
```

### **統合テスト**
```python  
# tests/integration/test_modes_integration.py
class TestModesIntegration:
    def test_orchestrator_mode_switching(self):
        """orchestrator.pyとのモード切り替え統合テスト"""
        pass
```

## 🚀 拡張性・将来対応

### **新モード追加容易性**
```python
class ValidationRunner(BaseRunner):
    """設定検証モード（将来追加例）"""
    async def run(self) -> bool:
        # 設定検証・テスト実行のみ
        pass
```

### **カスタムモード対応**
- BaseRunner継承による独自モード実装
- orchestrator.py変更不要での機能追加
- 設定ファイルによるモード定義

## 🔄 Phase 14-B リファクタリング効果

### **コード品質向上**  
- **orchestrator.py削減**: 1249行→約650行（200行削減）
- **責任分離**: 実行モードの完全分離
- **保守性向上**: 各ランナー150行以内・理解容易

### **機能拡張性**
- **新モード追加**: BaseRunner継承で容易実装
- **設定統合**: Phase 14-A外部化設定との連携
- **テスト改善**: モード別独立テスト可能

### **運用効率化**
- **モード切り替え**: 統一インターフェースによる簡潔実行
- **設定適用**: モード別最適化設定の自動適用
- **エラー分離**: モード固有エラーの独立処理

---

**Phase 14-B成果**: 実行モード機能の完全分離により、orchestrator.pyの実行制御責任を明確化し、保守性・拡張性・テスト容易性を大幅向上。戦略パターンによる柔軟なモード管理システムを確立。
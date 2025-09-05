# Phase 19 core/execution/ - MLOps統合実行モード管理システム

**Phase 19 MLOps統合**: feature_manager 12特徴量統合・ProductionEnsemble 3モデル統合・週次学習統合・Cloud Run 24時間稼働統合により、MLOps完全統合した実行モード管理システムです。654テスト品質保証・Discord 3階層監視・GitHub Actions週次学習統合で企業級品質を実現。

## 🎯 目的・責任

### **Phase 19 MLOps統合責任**: MLOps完全統合実行モード制御
- **feature_manager統合**: 12特徴量統一管理・バックテスト・MTF実取引統合
- **ProductionEnsemble統合**: 3モデルアンサンブル・重み付け投票・信頼度闾値統合
- **週次学習統合**: GitHub Actions自動モデル更新・ライブ取引統合
- **Cloud Run統合**: 24時間稼働・Discord 3階層監視・段階的デプロイ統合

### **Phase 19 MLOps統合機能**: orchestrator.py MLOps統合強化
- `run_backtest()` → `BacktestRunner` + feature_manager + ProductionEnsemble統合
- `run_paper_trading()` → `PaperTradingRunner` + 週次学習モデル統合
- `run_live_trading()` → `LiveTradingRunner` + Cloud Run 24時間稼働 + Discord 3階層監視

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

# Phase 19 MLOps統合ペーパートレード実行
paper_runner = PaperTradingRunner(orchestrator_ref, logger, enable_weekly_training=True)  
paper_success = await paper_runner.run()

# Phase 19 MLOps統合ライブトレード実行（Cloud Run統合）
live_runner = LiveTradingRunner(orchestrator_ref, logger, enable_cloud_run=True)
live_success = await live_runner.run()
```

### **orchestrator.pyとの統合**
```python
# orchestrator.py内での使用（簡素化後）
class TradingOrchestrator:
    def __init__(self, ...):
        # Phase 19 MLOps統合ランナー初期化
        self.backtest_runner = BacktestRunner(self, self.logger, enable_production_ensemble=True)
        self.paper_runner = PaperTradingRunner(self, self.logger, enable_weekly_training=True)
        self.live_runner = LiveTradingRunner(self, self.logger, enable_cloud_run=True)
    
    async def run(self):
        """統一実行インターフェース"""
        mode = self.config.mode
        
        if mode == "paper":
            # Phase 19 MLOps統合ペーパートレード（週次学習統合）
            return await self.paper_runner.run_with_weekly_training()
        elif mode == "live":
            # Phase 19 MLOps統合ライブトレード（Cloud Run 24時間稼働）
            return await self.live_runner.run_with_cloud_monitoring()
        else:
            raise ValueError(f"Phase 19無効なモード: {mode}")
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

### **Phase 19 MLOps環境別設定適用**
- **paper**: 週次学習モデル統合（1分間隔）・ProductionEnsembleテスト環境
- **live**: Cloud Run 24時間稼働（3分間隔）・feature_manager 12特徴量統合実取引
- **backtest**: ProductionEnsemble + feature_manager統合・過去データ分析

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

## 🔄 Phase 19 MLOps統合効果

### **MLOps品質保証向上**  
- **654テスト統合**: 59.24%カバレッジ・MLOps統合テスト・品質管理完備
- **feature_manager統合**: 12特徴量統一管理・実行モードシームレス連携
- **ProductionEnsemble統合**: 3モデルアンサンブル・実行モード統合実現

### **週次学習自動化**
- **GitHub Actions統合**: 週次自動モデル更新・ライブトレード統合
- **CI/CD品質ゲート**: 段階的デプロイ・実行モード品質管理
- **自動テスト**: モード別MLOps統合テスト可能

### **Cloud Run 24時間稼働**
- **ライブモード統合**: Discord 3階層監視・Cloud Runスケール管理
- **監視統合**: MLOpsメトリクス監視・モード別アラート管理
- **エラー管理**: MLOpsエラーの独立処理・モード固有アラート

---

**Phase 19 MLOps成果**: feature_manager 12特徴量統合・ProductionEnsemble 3モデル統合・週次自動学習・Cloud Run 24時間稼働・Discord 3階層監視・654テスト品質保証で、MLOps完全統合した企業級品質の実行モード管理システムを実現。
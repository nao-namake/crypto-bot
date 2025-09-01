# core/services/ - サービス層システム

**Phase 14-B リファクタリング**: orchestrator.pyから分離したサービス機能の統合管理モジュールです。ヘルスチェック・エラー記録・取引サイクル管理を担当し、システムの安定稼働を支援します。

## 🎯 目的・責任

### **単一責任**: システム運用・監視・制御サービス
- システムヘルスチェック・依存性検証
- エラー記録・統計・復旧処理
- 取引サイクル管理・フロー制御
- システム状態監視・アラート

### **分離された機能**: orchestrator.pyから約150行削減
- `_health_check()` → `HealthChecker`
- `_record_cycle_error()` → `ErrorRecorder`
- ログ関連メソッド → 各サービスに分散

## 📁 ファイル構成

```
services/
├── __init__.py              # モジュール初期化・エクスポート
├── README.md               # このファイル（使用方法・設計思想）
├── health_checker.py       # システムヘルスチェック（171行）
├── system_recovery.py      # システム復旧（215行）
├── trading_cycle_manager.py # 取引サイクル実行管理（358行）
└── trading_logger.py       # 取引ログサービス（253行）
```

## 🔧 主要クラス・設計

### **HealthChecker - ヘルスチェック**
```python
class HealthChecker:
    """システムヘルスチェッククラス"""
    
    def __init__(self, config: Config, logger: CryptoBotLogger):
        self.config = config
        self.logger = logger
    
    async def check_system_health(self) -> bool:
        """包括的システムヘルスチェック"""
        pass
    
    async def check_data_service(self) -> bool:
        """データサービス稼働確認"""
        pass
    
    async def check_ml_service(self) -> bool:
        """MLサービス稼働確認"""
        pass
    
    async def check_external_apis(self) -> bool:
        """外部API接続確認"""
        pass
```

### **ErrorRecorder - エラー記録管理**
```python  
class ErrorRecorder:
    """エラー記録・統計管理クラス"""
    
    def __init__(self, logger: CryptoBotLogger):
        self.logger = logger
        self.error_history = []
        self.cycle_errors = {}
    
    def record_cycle_error(self, cycle_id: str, error: Exception):
        """取引サイクルエラー記録"""
        pass
    
    async def schedule_system_restart(self):
        """システム再起動スケジューリング"""
        pass
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """エラー統計取得"""
        pass
    
    def should_trigger_recovery(self) -> bool:
        """復旧処理トリガー判定"""
        pass
```

### **CycleManager - 取引サイクル管理**
```python
class CycleManager:
    """取引サイクル実行管理クラス"""
    
    def __init__(self, orchestrator_ref, logger: CryptoBotLogger):
        self.orchestrator = orchestrator_ref
        self.logger = logger
    
    async def execute_trading_cycle(self) -> Dict[str, Any]:
        """取引サイクル実行"""
        pass
    
    async def log_trade_decision(self, evaluation, cycle_id: str):
        """取引判定ログ出力"""
        pass
    
    async def log_execution_result(self, result, cycle_id: str):
        """実行結果ログ出力"""
        pass
    
    async def log_trading_statistics(self, stats: Dict):
        """取引統計ログ出力"""
        pass
```

## 📊 使用例・インテグレーション

### **基本使用法**
```python
from src.core.services import HealthChecker, ErrorRecorder, CycleManager

# ヘルスチェック
health_checker = HealthChecker(config, logger)
health_status = await health_checker.check_system_health()

# エラー記録
error_recorder = ErrorRecorder(logger)
error_recorder.record_cycle_error("cycle_001", exception)

# 取引サイクル管理
cycle_manager = CycleManager(orchestrator_ref, logger)
cycle_result = await cycle_manager.execute_trading_cycle()
```

### **orchestrator.pyとの統合**
```python
# orchestrator.py内での使用（簡素化後）
class TradingOrchestrator:
    def __init__(self, ...):
        self.health_checker = HealthChecker(self.config, self.logger)
        self.error_recorder = ErrorRecorder(self.logger)
        self.cycle_manager = CycleManager(self, self.logger)
    
    async def initialize(self) -> bool:
        # ヘルスチェック（分離された機能）
        return await self.health_checker.check_system_health()
    
    async def run_trading_cycle(self):
        # 取引サイクル実行（分離された機能）
        try:
            result = await self.cycle_manager.execute_trading_cycle()
        except Exception as e:
            self.error_recorder.record_cycle_error("cycle_id", e)
```

## 🎯 設計原則・利点

### **単一責任原則（SRP）**
- ヘルスチェック・エラー管理・サイクル制御の分離
- 各サービスが特定の責任のみを担当
- orchestrator.pyの複雑性削減

### **依存性注入（DI）**
- orchestrator参照によるサービス連携
- テスト時のモック化容易
- サービス間の疎結合実現

### **コマンドパターン適用**
- 取引サイクル実行の抽象化
- 実行ログ・統計の統一インターフェース
- 復旧処理・再試行機能の組み込み

## 🔄 システム復旧機能

### **自動復旧システム**
```python
class ErrorRecorder:
    async def trigger_recovery_if_needed(self):
        """エラー閾値による自動復旧"""
        if self.should_trigger_recovery():
            await self.schedule_system_restart()
            self.logger.warning("🔄 システム自動復旧を実行")
```

### **段階的復旧処理**
1. **エラー記録**: 問題の分類・統計化
2. **閾値判定**: 復旧の必要性評価
3. **復旧実行**: ML再読み込み・接続再確立
4. **状態監視**: 復旧後のヘルスチェック

## 🧪 テスト戦略

### **単体テスト**
```python
# tests/unit/core/services/test_health_checker.py
class TestHealthChecker:
    def test_check_system_health(self):
        """システムヘルスチェックテスト"""
        pass
    
    def test_external_api_check(self):
        """外部API確認テスト"""
        pass
```

### **統合テスト**
```python  
# tests/integration/test_services_integration.py
class TestServicesIntegration:
    def test_orchestrator_services_integration(self):
        """orchestrator.pyとの統合テスト"""
        pass
```

## 🔄 Phase 14-B リファクタリング効果

### **コード品質向上**
- **orchestrator.py削減**: 1249行→約800行（150行削減）
- **責任分離**: サービス機能の完全分離
- **保守性向上**: 各サービス150行以内・明確な責任

### **システム信頼性向上**
- **独立監視**: ヘルスチェック・エラー管理の専門化
- **自動復旧**: エラー閾値による自動対応
- **統計管理**: システム状態の可視化

### **運用効率化**
- **問題特定**: エラー分類・統計による迅速な問題特定
- **予防保守**: ヘルスチェックによる問題の早期発見
- **自動化**: 復旧処理の自動実行

---

**Phase 14-B成果**: サービス機能の完全分離により、orchestrator.pyの運用・監視責任を明確化し、システムの信頼性・保守性・運用効率を大幅向上。専門化されたサービス層による堅牢なシステム監視を確立。
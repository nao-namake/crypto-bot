# core/reporting/ - レポート生成システム

**Phase 18統合システム更新**: バックテストレポート機能を`src/backtest/reporter.py`に統合完了。このフォルダはペーパートレード専用レポート機能を提供し、レポートシステムの責任分離を実現します。

## 🎯 Phase 18統合後の目的・責任

### **専門化された責任**: ペーパートレード専用レポート機能
- ペーパートレード統計のマークダウン生成  
- セッション管理・取引履歴レポート
- リアルタイム取引結果の構造化出力
- Discord通知用フォーマット変換

### **Phase 18統合完了事項**: バックテスト機能統合
- ~~`backtest_report_writer.py`~~ → **削除完了**（`src/backtest/reporter.py`に統合）
- バックテストレポート機能 → **統合レポーター**に移行
- 重複排除により保守性・効率性大幅向上

## 📁 ファイル構成（Phase 18統合後）

```
reporting/
├── __init__.py              # モジュール初期化・エクスポート  
├── README.md               # このファイル（Phase 18統合状況・使用方法）
├── base_reporter.py        # 基底レポートクラス・共通機能（192行）
└── paper_trading_reporter.py # ペーパートレード専用レポート（322行）
```

**🌟 統合完了**: `backtest_report_writer.py`は`src/backtest/reporter.py`に統合され、バックテスト機能の重複が完全に解消されました。

## 🔧 主要クラス・設計

### **BaseReporter - 基底クラス**
```python
class BaseReporter:
    """レポート生成の基底クラス"""
    
    def __init__(self, logger: CryptoBotLogger):
        self.logger = logger
    
    async def save_report(self, data: Dict, report_type: str) -> Path:
        """統一レポート保存インターフェース"""
        pass
    
    def format_markdown(self, data: Dict) -> str:
        """マークダウンフォーマット変換"""
        pass
    
    def format_discord_embed(self, data: Dict) -> Dict:
        """Discord通知用embed生成"""
        pass
```

### **~~BacktestReporter~~ - Phase 18統合完了**  
```python  
# Phase 18統合: src/backtest/reporter.py に移行済み
# 統合レポーターとしてCSV/HTML/JSON/マークダウン/Discord対応
class BacktestReporter:  # <- src/backtest/reporter.py
    """統合バックテストレポート生成クラス（Phase 18統合版）"""
    
    async def generate_backtest_report(...) -> Path:
        """統合レポート生成（マークダウン・JSON同時生成）"""
        
    async def generate_full_report(...) -> Dict[str, str]:
        """CSV・HTML・JSON・Discord対応の包括レポート"""
        
    async def save_error_report(...) -> Path:
        """エラーレポート生成（統合版）"""
```

### **PaperTradingReporter - ペーパートレード専用**
```python
class PaperTradingReporter(BaseReporter):
    """ペーパートレードレポート生成クラス"""
    
    async def generate_session_report(self, stats: Dict) -> Path:
        """セッション統計レポート生成"""
        pass
    
    def format_trading_statistics(self, stats: Dict) -> str:
        """取引統計のフォーマット"""
        pass
```

## 📊 使用例・インテグレーション

### **基本使用法（Phase 18統合後）**
```python
# ペーパートレード専用レポート
from src.core.reporting import PaperTradingReporter

# バックテストレポート → src/backtest/reporter.py（統合版）
from src.backtest.reporter import BacktestReporter

# ペーパートレードレポート生成  
paper_reporter = PaperTradingReporter(logger)
session_path = await paper_reporter.generate_session_report(session_stats)

# バックテストレポート生成（統合版）
backtest_reporter = BacktestReporter()  # 統合版は引数不要
report_path = await backtest_reporter.generate_backtest_report(
    results=backtest_results,
    start_date=start_date,
    end_date=end_date
)
```

### **orchestrator.pyとの統合（Phase 18統合版）**
```python
# orchestrator.py内での使用（Phase 18統合後）
class TradingOrchestrator:
    def __init__(self, ...):
        # Phase 18統合: バックテストレポーターはsrc/backtest/から
        self.backtest_reporter = BacktestReporter()  # <- 統合版  
        self.paper_reporter = PaperTradingReporter(self.logger)
    
    async def _run_backtest_mode(self):
        # BacktestEngine直接使用（Phase 18統合）
        results = await self.backtest_engine.run_backtest(...)
        
        # 統合レポート生成
        await self.backtest_reporter.generate_backtest_report(
            results, start_date, end_date
        )
```

## 🎯 設計原則・利点

### **単一責任原則（SRP）**
- レポート生成のみに特化・他の責任を排除
- バックテスト実行とレポート生成の分離
- フォーマット変換・ファイル保存の統一

### **開放閉鎖原則（OCP）**
- 新しいレポート形式の追加が容易
- 既存コードを変更せずに拡張可能
- BaseReporter継承による一貫性確保

### **依存性逆転原則（DIP）**
- 具体的な実装ではなくインターフェースに依存
- テスト時のモック化が容易
- orchestrator.pyとの疎結合実現

## 🧪 テスト戦略

### **単体テスト**
```python
# tests/unit/core/reporting/test_backtest_reporter.py
class TestBacktestReporter:
    def test_generate_backtest_report(self):
        """バックテストレポート生成テスト"""
        pass
    
    def test_markdown_format(self):
        """マークダウンフォーマットテスト"""
        pass
```

### **統合テスト**
```python  
# tests/integration/test_reporting_integration.py
class TestReportingIntegration:
    def test_orchestrator_reporter_integration(self):
        """orchestrator.pyとの統合テスト"""
        pass
```

## 🔄 Phase 18統合システム効果

### **バックテスト機能統合完了**
- **重複排除**: バックテストレポーター3つ→1つに統合
- **コード削減**: 865行削減（25%削減）・保守性大幅向上  
- **統一インターフェース**: CSV・HTML・JSON・マークダウン・Discord統合対応

### **責任分離の完成**
- **core/reporting**: ペーパートレード専用に特化
- **backtest/reporter**: バックテスト統合レポーター  
- **重複完全排除**: 管理ポイント削減・品質向上

### **保守性・拡張性向上**
- **統合テスト**: 統一されたテスト戦略
- **モック化**: 各レポーター独立テスト容易
- **新フォーマット追加**: 統合アーキテクチャで拡張容易

---

**Phase 18統合成果**: バックテストレポート重複を完全解消し、ペーパートレード専用レポートとして責任を明確化。統合システムにより25%のコード削減と大幅な保守性・品質向上を実現。
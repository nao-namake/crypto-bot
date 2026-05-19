# src/trading/analysis/ - 取引判断事後分析

取引判断の事後検証ロジック。Phase 69.7 で導入。

## ファイル構成

| ファイル | 行数 | 役割 |
|---|---|---|
| `__init__.py` | 0 | エクスポート（空）|
| `trade_analysis_recorder.py` | 274 | 取引判断の事後分析記録（Phase 69.7）|

## TradeAnalysisRecorder

ライブ取引で実施した取引判断（戦略シグナル + ML 品質フィルタの結果）と、その判断から N 時間後の市場状況を比較して「判断正解率」を算出。

主な利用箇所:
- `scripts/live/standard_analysis.py` の Phase 69.7 取引判断事後分析セクション
- ライブ運用 24h 統合診断レポートの「判断正解率」表示

## 関連リンク

- 親 README: [../README.md](../README.md)
- ライブ分析: [../../../scripts/live/standard_analysis.py](../../../scripts/live/standard_analysis.py)

---

**最終更新**: 2026年5月20日（Phase 90α: 新規作成）

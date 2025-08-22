# scripts/analytics/ - 統合分析基盤ディレクトリ

**Phase 13完了**: sklearn警告解消・306テスト100%成功・品質保証完成。統合分析基盤として、データ収集・パフォーマンス分析・ダッシュボード機能を一元管理する統合ディレクトリです。

## 📁 ファイル構成

```
analytics/
├── base_analyzer.py         # 基盤クラス（共通Cloud Runログ取得・gcloudコマンド統合）
├── performance_analyzer.py  # システムパフォーマンス分析
├── data_collector.py        # 実データ収集・統計分析（旧trading_data_collector.py）
├── dashboard.py             # HTML可視化ダッシュボード（旧trading_dashboard.py）
└── README.md                # このファイル
```

## 🎯 ディレクトリの目的・役割

### **統合分析基盤**
Phase 12-2で実装された**base_analyzer.py基盤**を活用し、以下の分析機能を統合：
- 📊 **データ収集**: Cloud Runログからの実取引データ抽出
- 📈 **パフォーマンス分析**: システム・取引成績の包括的評価
- 🎨 **可視化ダッシュボード**: HTML・Chart.js統合レポート
- 🔧 **共通基盤**: gcloudコマンド・エラーログ取得・統計計算

### **重複コード削除効果**
- **500行のCloud Run重複コード削除**: 4スクリプトの共通処理をbase_analyzer.pyに統合
- **統一インターフェース**: 全ツールが同じBaseAnalyzerクラスを継承
- **保守性向上**: 共通機能の一元管理・一貫性確保

## 🔧 各スクリプトの使用方法

### **📊 data_collector.py - 実データ収集**

**目的**: Cloud Runログから取引データを収集・統計分析

```bash
# 基本的な実行
python scripts/analytics/data_collector.py

# 時間指定での収集
python scripts/analytics/data_collector.py --hours 24    # 24時間
python scripts/analytics/data_collector.py --hours 6     # 6時間
python scripts/analytics/data_collector.py --hours 168   # 1週間

# 出力形式指定
python scripts/analytics/data_collector.py --hours 24 --format json
python scripts/analytics/data_collector.py --hours 24 --format csv
```

**主要機能**:
- ✅ **取引統計収集**: 勝率・収益・シグナル頻度・エラー率
- ✅ **CSV/JSON出力**: logs/reports/data_collection/保存
- ✅ **Discord通知**: 重要統計の自動通知
- ✅ **異常検知**: パフォーマンス低下・エラー急増の検出

### **📈 performance_analyzer.py - システム分析**

**目的**: システム全体のパフォーマンス・ヘルス状況を包括的に分析

```bash
# 基本的なパフォーマンス分析
python scripts/analytics/performance_analyzer.py

# 詳細期間指定
python scripts/analytics/performance_analyzer.py --period 24h
python scripts/analytics/performance_analyzer.py --period 7d
python scripts/analytics/performance_analyzer.py --period 30d

# 出力形式指定
python scripts/analytics/performance_analyzer.py --period 7d --format markdown
python scripts/analytics/performance_analyzer.py --period 7d --format json
```

**主要機能**:
- ✅ **システムヘルス**: CPU・メモリ・ネットワーク状況
- ✅ **エラー分析**: エラーカテゴリ・頻度・重要度評価
- ✅ **レスポンス分析**: API応答時間・スループット測定
- ✅ **改善提案**: 自動的な最適化提案生成

### **🎨 dashboard.py - 可視化ダッシュボード**

**目的**: 取引成績・システム状況をHTMLダッシュボードで可視化

```bash
# 基本的なダッシュボード生成
python scripts/analytics/dashboard.py

# Discord通知付きで生成
python scripts/analytics/dashboard.py --discord

# 期間指定でのダッシュボード
python scripts/analytics/dashboard.py --hours 24 --discord
python scripts/analytics/dashboard.py --hours 168  # 1週間
```

**主要機能**:
- ✅ **HTML可視化**: Chart.js・インタラクティブグラフ
- ✅ **取引統計表示**: 勝率・収益・ドローダウン・シャープレシオ
- ✅ **システム監視**: リアルタイム状況・エラー状況
- ✅ **Discord連携**: 自動レポート配信・アラート通知

### **🏗️ base_analyzer.py - 共通基盤クラス**

**目的**: 全分析スクリプトが継承する抽象基盤クラス

**直接実行は不要** - 他のスクリプトから自動的に使用されます

**提供機能**:
- ✅ **Cloud Runログ取得**: 統一されたgcloudコマンド実行
- ✅ **エラーログ分析**: パターン分析・重要度判定
- ✅ **サービスヘルス**: 死活監視・URL応答確認
- ✅ **ファイル出力**: logs/reports/配下への統一保存

## 📋 利用ルール・制約事項

### **✅ 推奨される使用パターン**
1. **日次監視**: data_collector.py（24時間） + dashboard.py
2. **週次分析**: performance_analyzer.py（7日間） + 詳細ダッシュボード
3. **問題調査**: performance_analyzer.py（短期間・詳細モード）
4. **月次レポート**: 全スクリプト実行 + 長期統計

### **⚠️ 注意事項**
1. **GCP認証必須**: gcloud authが設定されている必要があります
2. **ネットワーク接続**: Cloud Run・Discord APIへのアクセス必要
3. **実行時間**: 大量データ処理時は数分かかる場合があります
4. **並列実行制限**: 同時実行は推奨されません（ログ取得競合防止）

### **🚫 禁止・非推奨事項**
1. **base_analyzer.py直接実行**: 抽象クラスのため実行不可
2. **ログファイル直接編集**: scripts実行結果の手動変更
3. **認証情報ハードコード**: 環境変数・gcloud authを使用
4. **高頻度実行**: API制限・コスト増加を避けるため最小限に

## 🔄 他システムとの連携

### **management/との連携**
```bash
# dev_check.pyから自動実行
python scripts/management/dev_check.py monitor  # パフォーマンス分析自動実行
python scripts/management/dev_check.py health-check  # システム監視
```

### **testing/との連携**
- 品質チェック後の性能測定
- テスト結果の可視化・レポート生成

### **deployment/との連携**
- デプロイ後の性能検証
- 本番環境監視・問題検出

## 🚀 今後の拡張計画

### **Phase 13+での改善予定**
- **機械学習統計分析**: A/Bテスト・予測精度分析
- **コスト分析**: GCP使用料・効率性分析
- **自動アラート**: 異常検知→Discord自動通知
- **長期トレンド**: 月次・年次統計分析

### **統合分析基盤の進化**
- **リアルタイム分析**: ストリーミングデータ処理
- **予測分析**: 性能予測・容量計画
- **自動最適化**: パフォーマンス自動調整提案

---

**Phase 13完了**: sklearn警告解消・306テスト100%成功・品質保証完成。統合分析基盤による効率的な監視・分析・可視化環境を実現 🚀

*base_analyzer.py基盤活用により、保守性・拡張性・一貫性を確保した統合分析システム*
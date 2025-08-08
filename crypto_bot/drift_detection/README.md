# drift_detection/ - ドリフト検出・監視システム

## 📋 概要

**Data Drift Detection & Monitoring System**  
本フォルダは crypto-bot のドリフト検出機能を提供し、市場データやモデル予測の分布変化を検出・監視し、モデルの再訓練タイミングを判断します。

## 🎯 主要機能

### **ドリフト検出アルゴリズム**
- 統計的ドリフト検出（KS検定、Chi-squared検定等）
- 概念ドリフト検出（予測精度の劣化）
- 共変量シフト検出（入力データ分布の変化）
- アンサンブルベース検出

### **監視・アラート**
- リアルタイムドリフト監視
- 複数メトリクスの追跡
- 閾値ベースアラート
- 自動対応アクション

### **分析・レポート**
- ドリフト履歴記録
- 統計的有意性テスト
- 可視化・レポート生成
- ドリフトパターン分析

## 📁 ファイル構成

```
drift_detection/
├── __init__.py      # パッケージ初期化
├── detectors.py     # ドリフト検出アルゴリズム実装
├── ensemble.py      # アンサンブルドリフト検出
└── monitor.py       # ドリフト監視・アラートシステム
```

## 🔍 各ファイルの役割

### **detectors.py**
- `DriftDetectorBase`クラス - 基底クラス
- `KSTestDetector` - Kolmogorov-Smirnov検定ベース
- `ChiSquaredDetector` - カイ二乗検定ベース
- `PageHinkleyDetector` - Page-Hinkley検定
- `DDMDetector` - Drift Detection Method
- `EDDMDetector` - Early Drift Detection Method

### **ensemble.py**
- `DriftDetectionEnsemble`クラス - 複数検出器の統合
- 投票ベースの最終判定
- 重み付きアンサンブル
- 検出器の動的追加・削除
- 各検出器の貢献度分析

### **monitor.py**
- `DriftMonitor`クラス - 統合監視システム
- リアルタイムデータストリーム処理
- アラート通知機能
- 自動対応アクション（モデル再訓練等）
- ドリフト履歴管理・分析

## 🚀 使用方法

### **基本的なドリフト検出**
```python
from crypto_bot.drift_detection.detectors import KSTestDetector

# 検出器初期化
detector = KSTestDetector(
    window_size=100,
    significance_level=0.05
)

# データ更新・ドリフト検出
for data_point in data_stream:
    detector.update(data_point)
    if detector.drift_detected:
        print(f"Drift detected at {detector.last_drift_time}")
```

### **アンサンブルドリフト検出**
```python
from crypto_bot.drift_detection.ensemble import DriftDetectionEnsemble

ensemble = DriftDetectionEnsemble()
ensemble.add_detector("ks_test", KSTestDetector())
ensemble.add_detector("ddm", DDMDetector())

# 複数検出器による判定
drift_status = ensemble.detect(data_stream)
```

### **統合監視システム**
```python
from crypto_bot.drift_detection.monitor import DriftMonitor

monitor = DriftMonitor(
    detection_config={
        "window_size": 200,
        "alert_threshold": 0.8
    }
)

# コールバック登録
monitor.register_callback(
    "drift_alert",
    lambda info: print(f"Alert: {info}")
)

# 監視開始
monitor.start_monitoring(data_source)
```

## ⚠️ 課題・改善点

### **検出精度向上**
- False Positive率の削減
- より高度な統計手法の導入
- ドメイン特化型検出器の開発

### **パフォーマンス最適化**
- ストリーミングデータ処理の効率化
- メモリ使用量の削減
- 並列処理対応

### **統合強化**
- MLパイプラインとの密結合
- 自動再訓練トリガー
- A/Bテストとの連携

### **可視化・分析**
- リアルタイムダッシュボード
- ドリフトパターンの可視化
- 根本原因分析ツール

## 📝 今後の展開

1. **高度な検出手法**
   - 深層学習ベース検出
   - 多変量ドリフト検出
   - 因果関係考慮型検出

2. **自動対応強化**
   - 段階的モデル更新
   - オンライン学習統合
   - 自己修復型システム

3. **説明可能性**
   - ドリフト原因の特定
   - 影響範囲の可視化
   - 対策提案機能

4. **予測的検出**
   - ドリフト予兆検出
   - 予防的対策
   - リスク評価機能
# config/environments/live/ - 実取引環境設定

**目的**: 段階的な実資金取引による安全な本番運用への移行

## 📁 ファイル構成

```
live/
├── README.md               # このファイル
├── testing.yaml           # 最小単位実取引テスト
├── validation.yaml         # 1万円実資金検証
├── stage_10.yaml          # 10%資金投入段階
├── stage_50.yaml          # 50%資金投入段階
└── production.yaml        # 100%本番運用
```

## 🎯 段階的取引の流れ

```
Paper → Testing → Validation → Stage 10% → Stage 50% → Production
  ↓        ↓         ↓           ↓          ↓           ↓
仮想取引   最小テスト  1万円検証   保守的運用   バランス運用   フル運用
```

## 💰 各段階の詳細

### testing.yaml - 最小単位実取引テスト
- **目的**: 実取引システムの動作確認
- **リスク**: 0.2%/取引・最小0.0001 BTC
- **制限**: 1日5回・緊急停止2%

### validation.yaml - 1万円実資金検証
- **目的**: 1万円での現実的運用検証
- **リスク**: 0.5%/取引・最大800円損失
- **目標**: 7日間で500円以上利益（5%以上）

### stage_10.yaml - 10%資金投入段階
- **目的**: 保守的な本番運用開始
- **リスク**: 0.5%/取引・10%最大ドローダウン
- **目標**: 14日間・勝率60%・利益5,000円

### stage_50.yaml - 50%資金投入段階
- **目的**: バランス型運用
- **リスク**: 0.8%/取引・15%最大ドローダウン
- **目標**: 21日間・勝率58%・利益12,000円

### production.yaml - 100%本番運用
- **目的**: フル本番運用
- **リスク**: 1.0%/取引・20%最大ドローダウン
- **目標**: 月間17,000円収益

## 🚀 段階的移行手順

### 1. テスト段階
```bash
# 最小単位テスト
python main.py --config config/environments/live/testing.yaml
```

### 2. 検証段階
```bash
# 1万円実資金検証
python main.py --config config/environments/live/validation.yaml
```

### 3. 段階的本番移行
```bash
# 10%段階
bash scripts/deployment/deploy_production.sh --config config/environments/live/stage_10.yaml

# 50%段階（10%成功後）
bash scripts/deployment/deploy_production.sh --config config/environments/live/stage_50.yaml

# 100%本番（50%成功後）
bash scripts/deployment/deploy_production.sh --config config/environments/live/production.yaml
```

## 📊 リスク管理比較

| 段階 | リスク/取引 | 最大ドローダウン | 日次取引制限 | 緊急停止 |
|------|------------|---------------|--------------|----------|
| Testing | 0.2% | 5% | 5回 | 2% |
| Validation | 0.5% | 8% | 20回 | 5% |
| Stage 10% | 0.5% | 10% | 10回 | 5% |
| Stage 50% | 0.8% | 15% | 15回 | 8% |
| Production | 1.0% | 20% | 25回 | 15% |

## 🔒 安全機能

### 全段階共通
- **自動停止**: 連続損失・日次損失制限
- **API制限**: 30秒間隔遵守
- **監視統合**: Discord通知・ログ記録

### 段階別移行条件
- 各段階で成功条件を満たしてから次へ移行
- 失敗時は前段階または停止
- 手動監視による安全性確認

---

**重要**: 実取引は資金損失リスクを伴います。各段階の成功条件を満たしてから慎重に次段階へ進んでください。
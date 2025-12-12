# Phase 52.1ロールバック後の必須対応

**作成日**: 2025年12月13日
**目的**: Phase 52.1（PF 1.34、勝率51.4%、716件エントリー）へロールバック後に必ず適用すべき修正

---

## 過去のロールバック履歴

| 日付 | ロールバック先 | 理由 |
|------|--------------|------|
| 2025/12/07 | Phase 52 | Phase 53-60でPF 1.34→1.00に悪化 |
| 2025/12/10 | Phase 52 | Phase 53でPF 1.27→1.03に悪化 |
| 2025/12/13 | Phase 52.1 | Phase 53.8でエントリー716件→15件に激減 |

---

## 必須対応（GCP稼働に必須）

### 1. RandomForest n_jobs修正（稼働率33%→99%）

**問題**: GCP gVisorでfork()制限
**症状**: n_jobs=-1でクラッシュ、稼働率33%

**修正ファイル**: scripts/ml/create_ml_models.py（Line 201, 717付近）

```python
# 修正前
"n_jobs": -1,

# 修正後
"n_jobs": 1,  # GCP gVisor互換性
```

**注意**: モデル再訓練が必要

---

### 2. 自動タイムアウト無効化

**問題**: signal.alarm(900)がCloud Runと競合
**症状**: 15分毎にコンテナ再起動

**修正ファイル**: main.py

```python
# 修正前
signal.alarm(timeout_seconds)

# 修正後
# signal.alarm(timeout_seconds)  # 無効化
```

---

### 3. bitbank API署名修正（エラー20001解消）

**問題**: GET署名に/v1欠落
**症状**: APIエラー20001

**修正ファイル**: src/data/bitbank_client.py（Line 1592付近）

```python
# 修正前
message = f"{nonce}{endpoint}"

# 修正後
message = f"{nonce}/v1{endpoint}"
```

---

### 4. await漏れ修正（0エントリー問題）

**修正ファイル1**: src/core/orchestration/orchestrator.py（Line 546付近）

```python
# 修正前
balance_data = bitbank_client.fetch_balance()

# 修正後
balance_data = await bitbank_client.fetch_balance()
```

**修正ファイル2**: src/core/execution/live_trading_runner.py（Line 136付近）

```python
# 修正前
balance_data = self.bitbank_client.fetch_balance()

# 修正後
balance_data = await self.bitbank_client.fetch_balance()
```

---

### 5. 証拠金キー名修正（0エントリー問題）

**修正ファイル**: src/data/bitbank_client.py（Line 1483-1527付近）

```python
margin_data = {
    "margin_ratio": data.get("total_margin_balance_percentage"),
    "available_balances": data.get("available_balances", {}),
    "total_margin_balance": data.get("total_margin_balance"),
    "unrealized_pnl": data.get("margin_position_profit_loss"),
    "status": data.get("status"),
    "maintenance_margin": data.get("total_position_maintenance_margin"),
}
```

---

### 6. margin_ratio型変換修正（信用取引口座状況取得エラー解消）

**問題**: bitbank APIがmargin_ratioを文字列で返すが、floatフォーマットを使用
**症状**: `Unknown format code 'f' for object of type 'str'`エラー、維持率チェック失敗

**修正ファイル**: src/data/bitbank_client.py（Line 1519-1527付近）

```python
# 修正前
margin_ratio = margin_data.get("margin_ratio")
if margin_ratio is not None:
    self.logger.info(
        f"📊 信用取引口座状況取得成功 - 維持率: {margin_ratio:.1f}%",

# 修正後
margin_ratio = margin_data.get("margin_ratio")
if margin_ratio is not None:
    try:
        margin_ratio_float = float(margin_ratio)
        self.logger.info(
            f"📊 信用取引口座状況取得成功 - 維持率: {margin_ratio_float:.1f}%",
            extra_data={
                "margin_ratio": margin_ratio_float,
                "status": margin_data.get("status"),
            },
        )
    except (ValueError, TypeError):
        self.logger.info(
            f"📊 信用取引口座状況取得成功 - 維持率: {margin_ratio}",
            extra_data={"status": margin_data.get("status")},
        )
```

**影響**: この修正なしでは全取引サイクルで信用取引口座状況取得が失敗し続ける

---

## 推奨対応

### 7. SMOTEオプション追加（ML 100% hold問題対策）（推奨）

**問題**: クラス不均衡（HOLD 61.7%、BUY 20%、SELL 18.3%）

**修正ファイル**: .github/workflows/model-training.yml

```yaml
# --smote追加
python3 scripts/ml/create_ml_models.py \
  --n-classes 3 \
  --threshold 0.005 \
  --optimize \
  --n-trials "$N_TRIALS" \
  --smote \
  --verbose
```

---

## 不要な対応（適用しない）

| 変更内容 | 不採用理由 |
|---------|-----------|
| Python 3.11統一 | 稼働率向上はn_jobs修正で達成可能（3.13のままでOK） |
| トレンドフィルター | バックテストで効果なし |
| 戦略条件緩和（AND→OR） | 精度低下 |
| MeanReversion追加 | Phase 52に存在しない |

**重要**: GCPのPythonは3.13のままで問題なし。n_jobs=1修正が本質的な解決策。

---

### 8. docsフォルダ名リネーム（現在の構造に合わせる）

Phase 52.1のdocs構造を現在の構造にリネーム:

```bash
# Phase 52.1 (旧) → 現在 (新)
mv docs/development_history docs/開発履歴_en  # 一時退避（後で統合）
mv docs/バックテスト記録 docs/検証記録
mv docs/稼働チェック docs/運用監視
mv docs/運用手順 docs/運用ガイド

# 英語版開発履歴は削除（日本語版に統合済み）
rm -rf docs/開発履歴_en
```

| Phase 52.1 (旧) | 現在 (新) |
|-----------------|----------|
| docs/development_history/ | 削除（日本語版に統合済み） |
| docs/バックテスト記録/ | docs/検証記録/ |
| docs/稼働チェック/ | docs/運用監視/ |
| docs/運用手順/ | docs/運用ガイド/ |
| docs/開発履歴/ | docs/開発履歴/（そのまま） |
| docs/開発計画/ | docs/開発計画/（そのまま） |

---

## 修正適用順序

1. Phase 52.1にロールバック
2. **docsフォルダ名リネーム**（上記8.を実行）
3. 必須修正1-6を適用（1つずつcommit）
4. モデル再訓練（n_jobs=1で）
5. バックテスト実行（目標: PF 1.25以上、700件以上）
6. GCPデプロイ
7. （任意）SMOTEでモデル再訓練

---

## 検証チェックリスト

- [ ] バックテストPF 1.25以上
- [ ] エントリー数700件以上
- [ ] GCP稼働率99%以上
- [ ] APIエラー20001なし
- [ ] 信用取引口座状況取得成功（format codeエラーなし）
- [ ] MLモデル予測分布（hold < 80%）

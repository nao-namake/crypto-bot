# scripts/management/ - ローカル実行スクリプト（Phase 61）

**最終更新**: 2026年1月24日

## ファイル構成

```
scripts/management/
├── README.md        # このファイル
└── run_paper.sh     # ペーパートレード実行スクリプト
```

## run_paper.sh

ローカル環境でペーパートレードを実行するシンプルなスクリプト。

### 使用方法

```bash
# ペーパートレード開始
bash scripts/management/run_paper.sh

# 状況確認
bash scripts/management/run_paper.sh status

# 停止
bash scripts/management/run_paper.sh stop
```

### 機能

| コマンド | 説明 |
|---------|------|
| (引数なし) | ペーパートレード開始 |
| `status` | 実行中プロセス確認 |
| `stop` | プロセス停止 |

### 直接実行との比較

```bash
# スクリプト使用（推奨）
bash scripts/management/run_paper.sh

# 直接実行（上級者向け）
source config/secrets/.env
export PYTHONPATH=$PWD:$PWD/src
python3 main.py --mode paper
```

**スクリプトの利点**:
- 環境変数の自動読み込み
- 重複起動防止
- 簡単な停止コマンド

## 注意事項

- **GCP本番環境**は `docker-entrypoint.sh` を使用（このスクリプトは不使用）
- **ライブトレード**は `python3 main.py --mode live` を直接実行

## 変更履歴

| Phase | 変更内容 |
|-------|---------|
| 49.14 | run_safe.sh + bot_manager.sh 作成 |
| 55.9 | run_paper.sh に統合・簡素化（2スクリプト→1スクリプト） |

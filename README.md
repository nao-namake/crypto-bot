# Crypto-Bot

[![CI](https://github.com/nao-namake/crypto-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/nao-namake/crypto-bot/actions/workflows/ci.yml)

汎用性・拡張性を備えた暗号資産自動売買ボットです。  
バックテスト、最適化、ウォークフォワード、自動発注（Testnet／Live）をサポートします。

🔧 要件
- Python 3.8 以上
- Bybit Testnet API キー & シークレット
- （将来）各取引所 API キー

🚀 セットアップ
```bash
git clone https://github.com/nao-namake/crypto-bot.git
cd crypto-bot

# 仮想環境作成・アクティベート
python3 -m venv .venv
source .venv/bin/activate

# 本体と開発用依存のインストール
pip install -e .
pip install -r requirements-dev.txt

# 環境変数テンプレートをコピー
cp .env.example .env
# エディタで .env を開き、BYBIT_TESTNET_API_KEY/SECRET を設定

⚙️ 設定
すべて config/default.yml で管理します。
・データ取得: 取引所／シンボル／期間
・戦略設定: Bollinger Band／機械学習
・リスク管理: 損切り・ポジションサイズ
・バックテスト／最適化／ウォークフォワードパラメータ

💡 使い方
バックテスト
bash crypto-bot backtest --config config/default.yml

最適化バックテスト
bash crypto-bot optimize-backtest --config config/default.yml

機械学習モデルの学習
bash crypto-bot train --config config/default.yml

学習＋最適化
bash crypto-bot optimize-and-train --config config/default.yml

リアル（Testnet）取引 E2E テスト
bash scripts/run_e2e.sh

コードチェック／テスト
# フォーマット＆リンター＆テスト一発
bash scripts/checks.sh

# 必要なら自動修正モード
bash scripts/checks.sh --fix

📁 フォルダ構成（抜粋）
.
├── config
│   └── default.yml
├── crypto_bot
│   ├── data/           # データ取得・ストリーミング
│   ├── backtest/       # バックテスト・最適化
│   ├── execution/      # 取引所クライアント／注文エンジン
│   ├── strategy/       # 各種戦略
│   ├── ml/             # 機械学習パイプライン
│   └── main.py         # CLI 実装
├── scripts/
│   ├── run_e2e.sh
│   └── checks.sh
├── tests/              # ユニット＆統合テスト
└── README.md           # ← ここ

🤝 貢献・開発フロー
main ブランチを最新化
新しい機能は feature/xxx ブランチを切る
コード整形: bash scripts/checks.sh --fix
PR を作成 → CI が全通したらマージ

📄 ライセンス
MIT License
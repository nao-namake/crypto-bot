Crypto‑Bot 説明書（2025‑06‑17 更新版）

概要

暗号資産の 自動売買ボット です。
バックテスト、パラメータ最適化、ウォークフォワード、機械学習モデル、Testnet／Live 発注までをワンストップで実行できます。

A 主な機能
	•	データ取得 CCXT 経由（既定は Bybit Testnet）
	•	バックテスト スリッページ・手数料・ATR ストップ・損益集計
	•	最適化 テクニカル掃き／Optuna ハイパーパラ探索、ML モデル再学習
	•	ウォークフォワード CAGR・Sharpe を可視化
	•	リスク管理 動的ポジションサイジング（dynamic_position_sizing）
	•	機械学習 LightGBM / RandomForest / XGBoost、追加特徴量（volume_zscore など）
	•	パイプライン run_pipeline.sh で一連処理を自動化
	•	CI GitHub Actions（lint / unit / integration、カバレッジ 75% 以上）
	•	マルチ取引所対応（Bybit, Bitbank, Bitflyer, OKCoinJP：各クライアント雛形実装済／本格対応はSTEP16以降で順次）
	•	監視 / 可観測性 GCP Cloud Monitoring ダッシュボード＋カスタム指標（PnL, trade_count, position_flag）＋アラートポリシー（メール / SMS / LINE など）
	•	ライト級監視 UI Streamlit ダッシュボード（crypto_bot/monitor.py）― 自動メトリクス Push 付き

B 動作要件
	•	Python 3.11 〜 3.12
	•	Bybit Testnet API Key と Secret
	•	動作確認環境 Linux / macOS / WSL2
	•	GCP プロジェクト（Cloud Monitoring 有効化）と Metric Writer 権限付きサービスアカウント

C セットアップ手順
	1.	リポジトリを取得
		git clone https://github.com/nao-namake/crypto-bot.git
		cd crypto-bot

	2.	仮想環境を作成
		python -m venv .venv
		source .venv/bin/activate

	3.	パッケージをインストール
		pip install -e .
		pip install -r requirements-dev.txt

	4.	GCP 認証キーを設定  
		GOOGLE_APPLICATION_CREDENTIALS 環境変数に Metric Writer SA の JSON キーを指定  
		```bash
		export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
		```

	5.	API キーを設定
		cp .env.example .env
		# .env を開いて BYBIT_TESTNET_API_KEY と SECRET を記入
		# 他取引所を使う場合は .env.example 参照

D 設定ファイル（config/default.yml）の主な項目
	•	data 取得取引所・シンボル・期間など
	•	strategy モデルパス、閾値リスト
	•	risk ベースリスク、dynamic_position_sizing 設定
	•	walk_forward 訓練窓・テスト窓・スライド幅
	•	ml 追加特徴量、Optuna 設定、モデルパラメータ

E 基本コマンド例
	•	バックテスト
		python -m crypto_bot.main backtest --config config/default.yml
	•	最適化付きバックテスト
		python -m crypto_bot.main optimize-backtest --config config/default.yml
	•	機械学習モデル学習
		python -m crypto_bot.main train --config config/default.yml
	•   学習＋Optuna 最適化
		python -m crypto_bot.main optimize-and-train --config config/default.yml
	•	Testnet 統合テスト
		bash scripts/run_e2e.sh
	•	コード整形とテスト
		bash scripts/checks.sh
	•	ローカル監視 UI  
		streamlit run crypto_bot/monitor.py

F. GitHub Actions & Docker セットアップ
	1. GitHub Actions (CI/CD)
		①`Secrets` に以下を登録
		- `BYBIT_TESTNET_API_KEY`
		- `BYBIT_TESTNET_API_SECRET`
		- `CODECOV_TOKEN` (Codecov 用)
		- `CR_PAT` (GitHub Container Registry 用)

		②`.github/workflows/ci.yml` が以下のジョブを自動実行
		- **test**            : lint + unit‑tests + coverage  
		- **integration‑tests**: Bybit E2E (Testnet)  
		- **docker-build**     : GHCR へイメージ push  
		- **terraform-deploy-dev**   : Cloud Run(dev) へ自動デプロイ  
		- **terraform-deploy-paper** : Cloud Run(paper) へ自動デプロイ  
		- **terraform-deploy-prod**  : Cloud Run(prod) へ自動デプロイ  

		加えて `workflow_dispatch` トリガも有効化したので、`gh workflow run CI` コマンドで手動実行できます。
		- Cloud Run リビジョンは **Docker イメージの SHA タグが変わったときのみ**更新されます（Terraform でサービス定義に差分が無い場合はリビジョンは作成されません）。

**🔐 GCP 認証は Workload Identity Federation を使用**  
GitHub OIDC トークン → Workload‑Identity Pool / Provider → デプロイ用 SA (github‑deployer@${PROJECT_ID}).  
IAM ロールは Terraform で一元管理され、CI ジョブ実行者のシークレットキーは不要です。

	2. Docker イメージビルド
		①ビルドスクリプトを実行
		bash scripts/build_docker.sh

		②自動プッシュ
		タグ付け → Actions がトリガーされます
		```bash
		git tag vX.Y.Z
		git push origin vX.Y.Z
		```

	3. ローカルで動作確認
		```bash
		docker pull ghcr.io/<ユーザー名>/crypto-bot:vX.Y.Z
		docker run --rm ghcr.io/<ユーザー名>/crypto-bot:vX.Y.Z --help
		```
	4. Infrastructure Deployment (Terraform)
		1. Terraform を使ったインフラ構築
			• Terraform をインストールしてください（https://www.terraform.io/downloads.html）
		2. プロジェクトルートに移動
			cd crypto-bot
		3. Terraform 初期化
			terraform init
		4. インフラプランの確認
			terraform plan
		5. インフラの適用
			terraform apply
		6. インフラの破棄（不要になった場合）
			terraform destroy
		7. Terraform 設定ファイルは infra/ ディレクトリにあります
			• AWS, GCP, Azure などのクラウドリソースを管理可能です

	5. テスト環境へのデプロイ
		1. staging ブランチにマージ
		2. Terraform Workspace を切り替え（例: terraform workspace select staging）
		3. Terraform Apply でリソースを作成/更新（terraform apply）
		4. テスト環境の URL で動作確認

	6. 本番環境へのデプロイ
		1. main ブランチにマージ
		2. Terraform Workspace を切り替え（例: terraform workspace select production）
		3. Terraform Apply でリソースを作成/更新（terraform apply）
		4. 本番環境の URL で最終動作確認

G. パイプライン自動実行（学習 → 閾値スイープ → キャリブ → BT/WF → 可視化）
	1.	最適モデルを作成
		python -m crypto_bot.main optimize-and-train --config config/default.yml

	2.	パイプライン実行（ログを保存）
		caffeinate ./scripts/run_pipeline.sh 2>&1 | tee results/pipeline_log/pipeline_$(date +%Y%m%d_%H%M%S).log
		# 生成物は results/ と model/ フォルダに出力されます。

H. 可視化ツール
	•	tools/plot_performance.py エクイティカーブ・ドローダウン
	•	tools/plot_walk_forward.py CAGR と Sharpe の推移グラフ

I. 主要フォルダ構成（抜粋）
	config/           設定ファイル (YAML)
	crypto_bot/
	├ data/          データ取得・ストリーム
	├ backtest/      バックテストエンジン
	├ execution/     取引所クライアント
	├ strategy/      戦略 (MLStrategy 等)
	├ ml/            前処理・モデル・最適化
	└ scripts/       walk_forward.py ほか
	scripts/          run_pipeline.sh, checks.sh など
	tests/            unit / integration テスト
	README.md         ← 本書

R. 最近の変更点（2025‑06‑17）

	•	**インフラ再編** `infra/` を  
	  ├─ **modules/**（再利用モジュール）  
	  └─ **envs/**（dev / paper / prod の 3 環境）  
	  に分割。各環境は GCS バケット上の個別 backend でステートを完全分離。  
	•	**Workload Identity Federation** GitHub OIDC → GCP への権限委譲を Terraform で管理。  
	•	**CI/CD 拡張** `terraform-deploy‑paper`, `terraform-deploy‑prod` ジョブを追加し、main ブランチ push → dev、タグ push → prod まで全自動化。  
	•	**ペーパートレード環境** Cloud Run サービス名 `crypto-bot-paper`、`MODE=paper` 変数で本番と完全分離。  
	•	**大型ファイル削除** `infra/.terraform/**` に含まれるバイナリを履歴から除去。手順：  
	  ```bash
	  pip install git-filter-repo
	  git filter-repo --path infra/.terraform --invert-paths --force
	  git remote add origin https://github.com/<user>/crypto-bot.git
	  git push --force origin main
	  ```  
	•	**README 整理** このセクションを含め最新フローを反映。
	• **CI/CD 安定化** WIF 周りの IAM ロールを整理し、Terraform Apply が GitHub Actions から通ることを確認。  
	• **Cloud Run dev リビジョン** image_tag 更新時に自動で新リビジョンが作成されることを検証済み。  

J. コントリビューション規約
	1.	main ブランチを pull して最新化
	2.	feature/トピック名 で開発
	3.	bash scripts/checks.sh --fix で整形
	4.	Pull Request 作成 → CI が通ればマージ

K. Botの運用・拡張手順まとめ
	① 機械学習の特徴量（テクニカル指標など）の追加・削除手順
		1.テクニカル指標の追加／削除（例: RSI, MACD, RCI等）
			•crypto_bot/indicator/calculator.py に指標関数を追加または修正
			例）def rsi(...), def macd(...) など
			•必要であれば pandas-ta のドキュメントも参考に（pandas-ta Docs）
		2.特徴量として使う場合は
			•crypto_bot/ml/preprocessor.py の FeatureEngineer クラスのextra_features 処理に該当指標名（例: "rsi_14" など）が記載されているか確認
			•configファイル（config/default.yml）のml:→extra_features:リストに追加/削除
				ml:
				...
				extra_features:
					- rsi_14
					- macd
					- rci_9
					- volume_zscore
					# 追加・削除したい指標名をここに書く
		3.feature/strategy/指標追加したら必ずコード整形＆テスト
			bash scripts/checks.sh
		4.機械学習モデルの再学習・最適化パイプラインを再実行
			# パイプライン自動実行で一通り学習・最適化・キャリブ・可視化まで全部やる
			./scripts/run_pipeline.sh
			•（パイプラインの途中経過や結果ファイルは results/ フォルダを参照）
		5.結果の確認
			•生成されたモデル・グラフ（results/・model/）やログで指標反映・成績変化をチェック
	② 機械学習（ML）以外の戦略に切り替える場合
		1.新しい戦略クラスを作成
			•crypto_bot/strategy/ に、sample_strategy.py のような新ファイルを追加
			•共通インターフェイスとしてStrategyBaseを継承すること
				class MyRuleStrategy(StrategyBase):
					def logic_signal(self, price_df, position):
					# ルール記述
					...
		2.main.py等で「strategy=MyRuleStrategy」に切り替え
			•config/default.yml の strategy:→name:や該当部分を書き換え
			•必要に応じてバックテストや最適化のエントリーポイントで該当クラスを指定
		3.新戦略に合わせた特徴量やパラメータの修正
			•必要なら ml/preprocessor.py なども編集
		4.checks.sh→run_pipeline.shで動作確認
	③ 取引所（Bybit/Bitbank/Bitflyer等）を切り替える場合
		1.configファイル編集
			•config/default.yml の data:→exchange を変更（例：bybit→bitbank）
		2.APIキー/シークレット設定
			•.env ファイルの該当項目を新取引所のAPIキー/シークレットに書き換える
		3.クライアントクラスの対応状況確認
			•crypto_bot/execution/factory.py に該当取引所のクラスが実装済みか確認
			•（なければ新規クラスを追加）
		4.必要であれば個別仕様（APIパラメータ等）の調整
		5.データ取得・バックテスト等で正常動作するか確認
			python -m crypto_bot.main backtest --config config/default.yml
	④ 依存ライブラリやCI/テスト・分析系ファイルのアップデート時
		1.新規パッケージ追加時は
			•requirements.txt/requirements-dev.txt へ記載＆pip install
		2.CI/CD環境やLintルールを変える場合は
			•.github/workflows/以下やscripts/checks.shを編集
	⑤ プロジェクト整理時にやること
		•使わない戦略・取引所client等は削除 or サブディレクトリで退避
		•tools/配下が肥大化したらサブディレクトリ or README/tools.mdで説明追記
		•「この機能は現状不要」というものもREADMEに明記し、「必要なら復活できる」ようにブランチやタグで保管
	参考：機能追加・戦略切替・取引所切替フロー図（概略）
		1.指標追加・削除
		　→ indicator/calculator.py・ml/preprocessor.py・config/default.yml編集
		　→ checks.sh
		　→ run_pipeline.sh
		　→ results/ で確認
		2.戦略追加
		　→ strategy/にクラス追加・mainで指定・config修正
		　→ checks.sh
		　→ run_pipeline.sh
		3.取引所切替
		　→ config修正
		　→ .env修正
		　→ execution/factory.py確認

L. よくある質問（FAQ）
	- Q: マルチ取引所の実運用はどうすれば？**  
		→ 雛形テスト・.env.exampleでAPI管理、実運用は本当に使うときのみ（STEP16で本格対応）
	- Q: テストは全取引所で必須？**  
		→ テストネットのない取引所は雛形まででOK。API仕様変更時のみ実装すればよいです
	- Q: 複数取引所の併用・拡張方法は？**  
		→ configや.envの編集＋factory.pyのクラス追加／修正

N. Dockerでの実行・セットアップ・コマンド例
	1. Docker環境の前提
		•Docker Desktop（またはDocker CLI）がインストールされていること（Mac, Windows, Linux対応）
	2. Dockerイメージのビルド
		まずプロジェクトルートに移動して、下記コマンドを実行してください。
		bash scripts/build_docker.sh
		（または直接 docker build -t crypto-bot:latest . でもOK）
	3. .envファイルの準備
		.env.exampleをコピーし、APIキーやシークレットなどを記入してください。
		cp .env.example .env
		# .env を開いて必要な項目（BYBIT_TESTNET_API_KEY等）を記入
	4. Dockerコンテナでコマンドを実行（run_docker.sh で一元管理）
		スクリプト scripts/run_docker.sh を使うことで、
		どんなコマンドも同じ方法で実行できます。
		•	バックテスト
			bash scripts/run_docker.sh backtest --config config/default.yml
		•	モデル最適化（Optuna）
			bash scripts/run_docker.sh optimize-and-train --config config/default.yml
		•	モデル学習
			bash scripts/run_docker.sh train --config config/default.yml
		•	ウォークフォワード検証
			bash scripts/run_docker.sh walk-forward --config config/default.yml
		•	統合テスト（Bybit Testnet など）
			bash scripts/run_docker.sh e2e-test
		ポイント
		•	run_docker.shはどんなコマンドも引数で指定できる汎用ラッパーです。
		•	.envファイルが自動で読み込まれます（APIキーを含め環境変数が必要な時も安心）。
	5. 注意・補足
		•	用途ごとの専用スクリプト（run_docker_backtest.sh等）は不要です。
			すべて run_docker.sh で完結できます。
		•	必要なDockerコマンド・手順はREADMEにまとめているので、
			今後はここを見れば運用や拡張もスムーズに行えます。

P. 監視 & アラート運用メモ
	1.	カスタム指標 Push  
		•	monitor.py が status.json を読み取り、PnL 等を Cloud Monitoring へ送信  
		•	サービスアカウントに roles/monitoring.metricWriter を付与
	2.	Cloud Monitoring ダッシュボード  
		•	custom.googleapis.com/crypto_bot/* シリーズをウィジェットへ追加  
		•	PnL＝折れ線、取引回数＝スコアカード、position_flag＝ゲージが推奨
	3.	アラート ポリシー  
		•	PnL が –5,000 円 未満で 1 時間持続 → Bot 停止検討  
		•	取引レイテンシ > 3 s が 15 分継続 → 高レイテンシ通知  
		•	通知先：現在はメール、LINE Webhook はチャネルシークレット取得済み・後日追加予定

O. ライセンス
本プロジェクトは MIT License で公開されています。
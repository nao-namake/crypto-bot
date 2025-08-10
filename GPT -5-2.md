現行構成の概要と改善提案

本システムはモジュラー設計で、crypto_bot/ 以下に各機能が分割されています ￼。例えば、cli/にはコマンドライン処理（バックテスト・ライブ取引など）、data/にはデータ取得API、ml/には機械学習パイプライン、strategy/は戦略・リスク管理、execution/はBitbank取引実行、utils/は共通ユーティリティが配置されています ￼。設定はconfig/production/production.yml、学習モデルはmodels/production/model.pkl、インフラはinfra/envs/prod/にTerraform構成があります。まずこの既存構造を尊重しつつ、最小限の改修で問題解決を目指します。
	•	パッケージ構成の明確化：既に各モジュールが分割されているため、ファイル構成は維持し、各機能の責務を明確化します。必要に応じてコメントやREADMEで各モジュール役割を補足します。
	•	設定管理の統一化：設定ファイル(production.yml)から値を確実に読み込む仕組みを強化します。複数箇所で同じ設定を参照する場合は共通の読み込み関数を使うように統一し、誤読を防ぎます。
	•	依存関係の整理：問題発生箇所を見ると、局所的なimportやデータ型不整合が原因となっているため、インポートの集中化や型の明示化でミスを減らします。例えば、必要なライブラリのimportはモジュール冒頭にまとめる、クラス間で引き渡すデータは明確なオブジェクトに変換する等です。
	•	アンサンブルモデルの利用強化：TradingEnsembleClassifierによる複数モデルの統合が正しく機能していないため、実行時に常に正規のアンサンブルモデルがロード・利用されるよう修正します。

これらの改善により、根本的なアーキテクチャ変更を避けつつ、可読性や信頼性を向上させます。

稼働不可の原因と修正策

GPT-5_REQUEST.mdに記載のように、本番運用でエントリーシグナルが出ない原因として、主に以下の4つの問題が報告されています ￼ ￼ ￼ ￼。それぞれ原因を整理し、最小限の修正で対処します。

問題1: UnboundLocalError（局所インポートによるpd未定義） ￼

症状：crypto_bot/cli/live.pyでログ出力時にpd.Timestampを使おうとした際、pdが未定義のためUnboundLocalErrorが発生しています ￼。原因は、ファイル内で条件分岐ごとにimport pandas as pdを行っており、特定のブロック外ではpdが定義されていないためです ￼。

改善策：pandasのインポートはモジュールの先頭で一度だけ行い、局所的な重複を排除します。これにより、ファイル内のどこからでもpdを参照可能になります。

# crypto_bot/cli/live.py（修正例）
import pandas as pd           # ← ファイルの最上部にまとめてインポート

def start_live_trade(...):
    # 中略
    # ログ出力時にpd.Timestampが常に使用可能
    logger.info(f"⏰ {init_prefix} Timestamp: {pd.Timestamp.now()}")
    # 中略

問題2: Strategyオブジェクトではなくdictが渡されている（logic_signal属性エラー） ￼

症状：EntryExitクラスにパラメータとしてdict型が渡されており、logic_signal属性が見つからないAttributeErrorが発生しています ￼。期待されるのは、辞書ではなくStrategyクラスのインスタンスであるべき箇所です ￼。

改善策：設定パラメータ(dict)を受け取る箇所では、必ず対応するクラスのオブジェクトに変換してから処理を行います。以下はEntryExit初期化時に、辞書からStrategyインスタンスを生成する例です。

# 例: StrategyパラメータをStrategyオブジェクトに変換してからEntryExitに渡す
from crypto_bot.strategy import Strategy, EntryExit

def initialize_entry_exit(strategy_params):
    # strategy_params: 設定ファイルから読み込んだ辞書型パラメータ
    # Strategyオブジェクトを生成
    strategy_obj = Strategy(**strategy_params)
    # EntryExitにはStrategyオブジェクトを渡す
    entry_exit = EntryExit(strategy_obj)
    return entry_exit

# 使用例
strategy_config = {...}  # YAML等から読み込んだdict
entry_exit = initialize_entry_exit(strategy_config)

もし既存コード内でEntryExitへの引数が不明確なまま辞書を渡している箇所があれば、上記のようにオブジェクト化して修正します。

問題3: 設定値の不整合（confidence_thresholdの誤使用） ￼

症状：設定ファイルproduction.ymlではconfidence_threshold: 0.35と定義しているにもかかわらず、実行ログでは0.7が使用されています ￼。これは設定読み込み漏れやデフォルト値のハードコーディングが原因と考えられます。

改善策：confidence_thresholdをはじめ全ての設定値は、必ずYAML等の設定ファイルから一貫して読み込むように修正します。例えば、設定管理用のヘルパー関数を使って以下のように読み込む方法が考えられます。

import yaml

def load_config(path):
    with open(path) as f:
        return yaml.safe_load(f)

# 設定ファイルを読み込む例
config = load_config("config/production/production.yml")
threshold = float(config.get("confidence_threshold", 0.35))

これにより、実行時に設定ファイルの値（この例では0.35）が必ず反映され、矛盾を防げます。また、他の箇所で別の値を参照していないか全体をチェックし、重複定義を削除します。

問題4: アンサンブルモデル未使用（TradingEnsembleClassifierが機能していない） ￼

症状：実行時ログに「Strategy does not use ensemble models」とあり、3つのモデルを統合するはずのTradingEnsembleClassifierが利用されておらず、フォールバック戦略が使われている状態です ￼。

改善策：アンサンブルモデルが必ずロード・使用されるように修正します。例えば、学習済みモデルを読み込む箇所で、TradingEnsembleClassifierを明示的に呼び出します。

from crypto_bot.ml.ensemble import TradingEnsembleClassifier

def load_trading_ensemble(model_path, confidence_threshold):
    # 学習済みモデルファイルからアンサンブルモデルを読み込み
    ensemble = TradingEnsembleClassifier.load(model_path)
    # 閾値設定など必要に応じ設定
    ensemble.confidence_threshold = confidence_threshold
    return ensemble

# 使用例
model = load_trading_ensemble("models/production/model.pkl", threshold=0.35)
signal = model.predict(current_feature_vector)

上記のように正規のアンサンブルモデルを使うロジックを確実に通すことで、3モデル統合が機能し、信頼性の高いシグナルが生成されます。

ローカル動作検証の方法

修正後に本番稼働前に動作確認できるよう、以下の方法でローカルテスト環境を整備します。
	•	バックテスト実行：既存のコマンドpython -m crypto_bot.main backtest --config ...を使い、過去データでのシグナル生成や仮想トレードを行います。バックテストモードではBitbankへの実通信を行わないため、修正後のロジック検証に有効です。
	•	ダミー注文機能：executionモジュールにテスト用のモード（例：simulateフラグ）を追加し、実際の注文呼び出しの代わりにログ出力のみ行うようにします。例えば、購入・売却メソッドを以下のように書き換えます。

def place_order_simulation(signal, price, amount):
    # 取引シグナルと価格、数量をログに出力（実際のAPI呼び出しは行わない）
    logger.info(f"[SIMULATION] {signal.upper()} {amount} at {price}")
    # 実環境ではここでBitbank APIを呼ぶ


	•	詳細なログ記録：重要な処理（シグナル生成、注文呼び出し）で構造化ログを出力し、CSV等に保存します。これにより、後から取引シミュレーション結果を分析しやすくします。例えば、logger.info(f"Signal: {signal}, Price: {current_price}")のように明示的に記録します。
	•	設定差分の排除：本番環境と可能な限り同一の設定・環境でテストするため、Dockerコンテナや仮想環境に同じ設定ファイルを用意し、テスト用Bitbankキー・ネットワーク設定を切り替え可能にします。こうすることで本番差異による問題を減らします ￼。

以上の手順で、本番投入前に修正内容を検証し、不具合を未然に防ぎます。
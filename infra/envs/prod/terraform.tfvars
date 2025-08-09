project_id             = "my-crypto-bot-project"
region                 = "asia-northeast1"
artifact_registry_repo = "crypto-bot-repo"
service_name           = "crypto-bot-service-prod"
image_name             = "crypto-bot"
alert_email            = "s00198532@gmail.com"
project_number         = "11445303925"                     # gcloud projects describe で確認済み
github_repo            = "nao-namake/crypto-bot"
deployer_sa            = "github-deployer@my-crypto-bot-project.iam.gserviceaccount.com"
mode                   = "live"                            # Bitbank実資金運用モード
# 重要: このファイルの設定はCI/CDのTF_VAR_modeより優先度が高い
# 本番運用では必ず"live"にする

# ローカル検証用ダミー値（CI/CDでは GitHub Secrets から上書きされる）
bitbank_api_key        = "dummy_key_for_local_validation"
bitbank_api_secret     = "dummy_secret_for_local_validation"
"""
Discord Webhook通知用Cloud Functions
GCPアラートをDiscordに送信する
"""
import json
import base64
import os
from datetime import datetime, timezone, timedelta
import pytz
import requests
from google.cloud import secretmanager


def webhook_notifier(event, context):
    """
    Cloud MonitoringのPub/Subメッセージを受信してDiscordに送信
    Args:
        event (dict): Pub/Subメッセージイベント
        context (google.cloud.functions.Context): メタデータ
    """
    try:
        # Pub/Subメッセージをデコード
        if 'data' in event:
            message_data = base64.b64decode(event['data']).decode('utf-8')
            alert_data = json.loads(message_data)
            print(f"Received alert data: {alert_data}")
        else:
            print("No data in event")
            return

        # Discord Webhook URLを取得
        webhook_url = get_discord_webhook_url()
        if not webhook_url:
            print("Discord Webhook URL not found")
            return

        # Discord形式のメッセージを作成
        discord_message = create_discord_message(alert_data)
        
        # Discordに送信
        send_to_discord(webhook_url, discord_message)
        
        print(f"Alert sent to Discord successfully: {alert_data.get('condition', {}).get('displayName', 'Unknown')}")
        
    except Exception as e:
        print(f"Error in webhook_notifier: {str(e)}")
        return f"Error: {str(e)}", 500


def get_discord_webhook_url():
    """
    Secret ManagerからDiscord Webhook URLを取得
    """
    try:
        # 環境変数から直接取得を試行
        webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
        if webhook_url:
            return webhook_url
            
        # Secret Managerから取得
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.environ.get('GCP_PROJECT', 'my-crypto-bot-project')
        secret_name = f"projects/{project_id}/secrets/discord-webhook-url/versions/latest"
        
        response = client.access_secret_version(request={"name": secret_name})
        return response.payload.data.decode('UTF-8')
        
    except Exception as e:
        print(f"Failed to get Discord webhook URL: {str(e)}")
        return None


def create_discord_message(alert_data):
    """
    GCPアラートデータからDiscord埋め込みメッセージを作成
    """
    try:
        # 基本情報の抽出
        incident = alert_data.get('incident', {})
        condition = alert_data.get('condition', {})
        
        policy_name = incident.get('policy_name', 'Unknown Policy')
        condition_name = condition.get('displayName', 'Unknown Condition')
        state = incident.get('state', 'UNKNOWN')
        
        # 日本時間のタイムスタンプ
        jst = pytz.timezone('Asia/Tokyo')
        now_jst = datetime.now(jst)
        timestamp_str = now_jst.strftime('%Y年%m月%d日 %H:%M:%S JST')
        
        # アラートの種類に応じた色を設定
        color = get_alert_color(policy_name, state)
        
        # アラートタイトルの生成
        title = f"🤖 Crypto-Bot Alert: {condition_name}"
        
        # 詳細説明の生成
        description = create_alert_description(policy_name, condition, incident)
        
        # Discord埋め込みメッセージ
        embed = {
            "title": title,
            "description": description,
            "color": color,
            "timestamp": now_jst.isoformat(),
            "fields": [
                {
                    "name": "📊 ポリシー",
                    "value": policy_name,
                    "inline": True
                },
                {
                    "name": "🚨 状態",
                    "value": get_state_emoji(state) + " " + state,
                    "inline": True
                },
                {
                    "name": "⏰ 検出時刻",
                    "value": timestamp_str,
                    "inline": False
                }
            ],
            "footer": {
                "text": "Crypto-Bot Monitoring System",
                "icon_url": "https://cdn.discordapp.com/emojis/🤖.png"
            }
        }
        
        # URL情報があれば追加
        url = incident.get('url')
        if url:
            embed['url'] = url
        
        return {
            "embeds": [embed]
        }
        
    except Exception as e:
        print(f"Error creating Discord message: {str(e)}")
        return {
            "content": f"⚠️ アラート通知でエラーが発生しました: {str(e)}"
        }


def create_alert_description(policy_name, condition, incident):
    """
    アラートの詳細説明を生成
    """
    try:
        descriptions = {
            "Crypto Bot Loss Alert": "💰 **損失アラート**: 取引で大きな損失が発生しています",
            "High error rate": "❌ **エラー率アラート**: システムエラーが多発しています", 
            "High request latency": "🐌 **レイテンシアラート**: システム応答が遅延しています",
            "Trade Execution Alert": "⚡ **取引実行アラート**: 取引実行に問題が発生しています"
        }
        
        base_description = descriptions.get(policy_name, f"📢 **システムアラート**: {policy_name}")
        
        # 追加の詳細情報
        summary = incident.get('summary', '')
        if summary:
            base_description += f"\n\n**詳細**: {summary}"
            
        return base_description
        
    except Exception as e:
        return f"アラート詳細の取得に失敗しました: {str(e)}"


def get_alert_color(policy_name, state):
    """
    アラートの種類と状態に応じた色を返す
    """
    if state == "CLOSED":
        return 0x00FF00  # 緑（回復）
    
    # アラートの重要度に応じた色分け
    critical_alerts = ["Crypto Bot Loss Alert", "Trade Execution Alert"]
    warning_alerts = ["High error rate"]
    info_alerts = ["High request latency"]
    
    if policy_name in critical_alerts:
        return 0xFF0000  # 赤（重要）
    elif policy_name in warning_alerts:
        return 0xFF8C00  # オレンジ（警告）
    elif policy_name in info_alerts:
        return 0xFFFF00  # 黄（情報）
    else:
        return 0x808080  # グレー（その他）


def get_state_emoji(state):
    """
    アラート状態に応じた絵文字を返す
    """
    emoji_map = {
        "OPEN": "🔴",
        "CLOSED": "✅", 
        "ACKNOWLEDGED": "👀",
        "UNKNOWN": "❓"
    }
    return emoji_map.get(state, "⚪")


def send_to_discord(webhook_url, message):
    """
    DiscordにWebhookメッセージを送信
    """
    try:
        headers = {
            'Content-Type': 'application/json'
        }
        
        response = requests.post(
            webhook_url, 
            json=message, 
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 204:
            print("Discord message sent successfully")
        else:
            print(f"Discord API error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Failed to send Discord message: {str(e)}")
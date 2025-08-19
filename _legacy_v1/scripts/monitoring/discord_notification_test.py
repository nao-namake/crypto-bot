#!/usr/bin/env python3
"""
Discord通知システムのテストスクリプト
GCPアラートのシミュレーションメッセージを送信してDiscord通知をテスト
"""

import json
import base64
import os
from google.cloud import pubsub_v1
from datetime import datetime
import argparse


def create_test_alert_data(alert_type="loss"):
    """テスト用のアラートデータを生成"""
    
    test_alerts = {
        "loss": {
            "incident": {
                "policy_name": "Crypto Bot Loss Alert",
                "state": "OPEN",
                "summary": "テスト: 損失アラート - 実際の取引ではありません",
                "url": "https://console.cloud.google.com/monitoring"
            },
            "condition": {
                "displayName": "PnL < -10000 JPY"
            }
        },
        "error": {
            "incident": {
                "policy_name": "High error rate", 
                "state": "OPEN",
                "summary": "テスト: エラー率アラート - システム正常です",
                "url": "https://console.cloud.google.com/monitoring"
            },
            "condition": {
                "displayName": "5xx error rate > 10%"
            }
        },
        "trade_failure": {
            "incident": {
                "policy_name": "Trade Execution Failure Alert",
                "state": "OPEN", 
                "summary": "テスト: 取引実行失敗アラート - テスト送信です",
                "url": "https://console.cloud.google.com/monitoring"
            },
            "condition": {
                "displayName": "連続取引失敗 > 5回"
            }
        },
        "system_down": {
            "incident": {
                "policy_name": "System Health Check Failure",
                "state": "OPEN",
                "summary": "テスト: システム停止アラート - 正常稼働中です", 
                "url": "https://console.cloud.google.com/monitoring"
            },
            "condition": {
                "displayName": "ヘルスチェック失敗"
            }
        },
        "memory": {
            "incident": {
                "policy_name": "High Memory Usage Alert",
                "state": "OPEN",
                "summary": "テスト: メモリ使用率アラート - テスト送信です",
                "url": "https://console.cloud.google.com/monitoring"
            },
            "condition": {
                "displayName": "メモリ使用率 > 85%"
            }
        },
        "data_fetch": {
            "incident": {
                "policy_name": "Market Data Fetch Failure", 
                "state": "OPEN",
                "summary": "テスト: データ取得停止アラート - データ取得正常です",
                "url": "https://console.cloud.google.com/monitoring"
            },
            "condition": {
                "displayName": "データ取得停止 > 10分"
            }
        }
    }
    
    if alert_type not in test_alerts:
        alert_type = "loss"
        
    return test_alerts[alert_type]


def send_test_alert(project_id="my-crypto-bot-project", alert_type="loss"):
    """テストアラートをPub/Subに送信"""
    
    try:
        # Pub/Sub Publisher クライアント初期化
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(project_id, "crypto-bot-alert-notifications")
        
        # テストアラートデータ作成
        alert_data = create_test_alert_data(alert_type)
        
        # JSON文字列に変換
        message_json = json.dumps(alert_data)
        message_data = message_json.encode('utf-8')
        
        print(f"🧪 テストアラート送信中...")
        print(f"📋 アラートタイプ: {alert_type}")
        print(f"📨 メッセージ: {message_json}")
        
        # Pub/Subにメッセージ送信
        future = publisher.publish(topic_path, message_data)
        message_id = future.result()
        
        print(f"✅ テストアラート送信完了")
        print(f"📝 Message ID: {message_id}")
        print(f"🎯 Discordチャンネルでの通知を確認してください")
        
        return True
        
    except Exception as e:
        print(f"❌ テストアラート送信エラー: {str(e)}")
        return False


def test_discord_webhook_direct():
    """Discord Webhook URLに直接テストメッセージを送信"""
    
    try:
        import requests
        
        # .env.example から Webhook URL を取得
        env_file = "/Users/nao/Desktop/bot/.env.example"
        webhook_url = None
        
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if line.startswith('Discord_Webhook='):
                        webhook_url = line.split('=', 1)[1].strip()
                        break
        
        if not webhook_url:
            print("❌ Discord Webhook URL が見つかりません")
            return False
        
        # テストメッセージ作成
        test_message = {
            "embeds": [{
                "title": "🧪 Discord通知テスト",
                "description": "**crypto-bot Discord通知システムのテストメッセージです**",
                "color": 0x00FF00,  # 緑色
                "timestamp": datetime.now().isoformat(),
                "fields": [
                    {
                        "name": "📊 システム状態", 
                        "value": "正常稼働",
                        "inline": True
                    },
                    {
                        "name": "🧪 テスト種別",
                        "value": "Direct Webhook Test",
                        "inline": True
                    }
                ],
                "footer": {
                    "text": "Crypto-Bot Test System"
                }
            }]
        }
        
        # Discord Webhook に送信
        response = requests.post(webhook_url, json=test_message, timeout=10)
        
        if response.status_code == 204:
            print("✅ Discord直接テスト送信成功")
            print("🎯 Discordチャンネルでテストメッセージを確認してください")
            return True
        else:
            print(f"❌ Discord送信エラー: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Discord直接テストエラー: {str(e)}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Discord通知システムテスト")
    parser.add_argument("--type", choices=[
        "loss", "error", "trade_failure", "system_down", "memory", "data_fetch", "direct"
    ], default="loss", help="テストするアラートタイプ")
    parser.add_argument("--project", default="my-crypto-bot-project", help="GCPプロジェクトID")
    
    args = parser.parse_args()
    
    print("🚀 Discord通知システムテスト開始")
    print("=" * 50)
    
    if args.type == "direct":
        # Discord直接テスト
        success = test_discord_webhook_direct()
    else:
        # Pub/Sub経由テスト  
        success = send_test_alert(args.project, args.type)
    
    if success:
        print("\n🎉 テスト完了: Discordチャンネルで通知を確認してください")
    else:
        print("\n❌ テスト失敗: エラーログを確認してください")


if __name__ == "__main__":
    main()
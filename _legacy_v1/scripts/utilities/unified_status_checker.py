#!/usr/bin/env python3
"""
統合ステータスチェッカー - UTC/JST混在問題を解決

全ての時刻を日本時間（JST）で統一表示し、最新リビジョンのみを監視対象とする
"""

import subprocess
import json
from datetime import datetime, timezone, timedelta
import argparse

JST = timezone(timedelta(hours=9))

def utc_to_jst(utc_string):
    """UTC時刻文字列を日本時間に変換"""
    try:
        # Z suffix or +00:00 形式に対応
        if utc_string.endswith('Z'):
            utc_string = utc_string[:-1] + '+00:00'
        
        utc_time = datetime.fromisoformat(utc_string)
        if utc_time.tzinfo is None:
            utc_time = utc_time.replace(tzinfo=timezone.utc)
        
        jst_time = utc_time.astimezone(JST)
        return jst_time.strftime('%Y-%m-%d %H:%M:%S JST')
    except Exception as e:
        return f"時刻変換エラー: {utc_string} ({e})"

def get_current_jst():
    """現在の日本時間を取得"""
    return datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S JST')

def get_cloud_run_status():
    """GCP Cloud Runサービスステータス（JST表示）"""
    print("🔍 GCP Cloud Run サービスステータス")
    print("=" * 60)
    
    try:
        # 最新リビジョン情報を取得
        result = subprocess.run([
            'gcloud', 'run', 'revisions', 'list',
            '--service=crypto-bot-service-prod',
            '--region=asia-northeast1', 
            '--limit=3',
            '--format=json'
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ GCP コマンドエラー: {result.stderr}")
            return
            
        revisions = json.loads(result.stdout)
        if not revisions:
            print("❌ リビジョン情報が見つかりません")
            return
            
        print(f"📋 最新リビジョン情報 (現在時刻: {get_current_jst()})")
        
        for i, revision in enumerate(revisions):
            name = revision['metadata']['name']
            created = revision['metadata']['creationTimestamp']
            
            # トラフィック割り当て確認
            traffic_status = "🔴 INACTIVE"
            if 'status' in revision and 'conditions' in revision['status']:
                for condition in revision['status']['conditions']:
                    if condition.get('type') == 'Ready' and condition.get('status') == 'True':
                        traffic_status = "✅ ACTIVE" if i == 0 else "⚪ READY"
                        break
            
            print(f"   {name}")
            print(f"     作成時刻: {utc_to_jst(created)}")
            print(f"     ステータス: {traffic_status}")
            
            if i == 0:
                print(f"     → 📌 この最新リビジョンのログを監視対象とします")
            print()
            
    except Exception as e:
        print(f"❌ Cloud Run ステータス取得エラー: {e}")

def get_latest_logs(hours=1, limit=20, severity=None):
    """最新リビジョンのログ取得（JST表示）"""
    print(f"📊 最新ログ (直近{hours}時間、最大{limit}件)")
    if severity:
        print(f"🔍 フィルタ: {severity} レベル以上")
    print("=" * 60)
    
    # ログ取得コマンド構築
    freshness = f"{hours}h"
    cmd = [
        'gcloud', 'logging', 'read',
        'resource.type="cloud_run_revision" AND '
        'resource.labels.service_name="crypto-bot-service-prod" AND '
        'resource.labels.location="asia-northeast1"',
        f'--freshness={freshness}',
        f'--limit={limit}',
        '--format=table(timestamp.date(tz=Asia/Tokyo):label="日本時間",severity:label="レベル",textPayload:label="ログ内容")'
    ]
    
    if severity:
        cmd[1] += f' AND severity>={severity}'
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ ログ取得エラー: {result.stderr}")
            return
            
        if result.stdout.strip():
            print(result.stdout)
        else:
            print("ℹ️  該当するログが見つかりませんでした")
            
    except Exception as e:
        print(f"❌ ログ取得エラー: {e}")

def get_service_health():
    """サービスヘルスチェック"""
    print("🏥 サービスヘルスチェック")
    print("=" * 60)
    
    try:
        result = subprocess.run([
            'curl', '-s', '-w', 'HTTP Status: %{http_code}\\nResponse Time: %{time_total}s\\n',
            'https://crypto-bot-service-prod-11445303925.asia-northeast1.run.app/health'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if lines:
                try:
                    # JSON レスポンスをパース
                    health_data = json.loads(lines[0])
                    timestamp = health_data.get('timestamp', 'unknown')
                    
                    print(f"ステータス: {health_data.get('status', 'unknown')}")
                    print(f"最終応答: {utc_to_jst(timestamp) if timestamp != 'unknown' else 'unknown'}")
                    print(f"モード: {health_data.get('mode', 'unknown')}")
                    print(f"リーダー: {health_data.get('is_leader', 'unknown')}")
                    
                    # HTTP ステータスと応答時間
                    for line in lines[1:]:
                        if 'HTTP Status:' in line or 'Response Time:' in line:
                            print(line)
                            
                except json.JSONDecodeError:
                    print("⚠️ ヘルスチェックの応答形式が異常です")
                    print(result.stdout)
        else:
            print(f"❌ ヘルスチェック失敗: {result.stderr}")
            
    except Exception as e:
        print(f"❌ ヘルスチェックエラー: {e}")

def main():
    parser = argparse.ArgumentParser(
        description='crypto-bot 統合ステータスチェッカー（全て日本時間表示）'
    )
    parser.add_argument('--hours', type=float, default=1.0, help='ログ取得時間範囲（時間）')
    parser.add_argument('--limit', type=int, default=20, help='ログ最大取得件数')
    parser.add_argument('--severity', choices=['ERROR', 'WARNING', 'INFO'], help='ログレベルフィルタ')
    parser.add_argument('--no-health', action='store_true', help='ヘルスチェックをスキップ')
    parser.add_argument('--no-logs', action='store_true', help='ログ取得をスキップ')
    
    args = parser.parse_args()
    
    print(f"🎯 crypto-bot 統合ステータス確認")
    print(f"⏰ 実行時刻: {get_current_jst()}")
    print("=" * 80)
    print()
    
    # 1. Cloud Runステータス（必須）
    get_cloud_run_status()
    print()
    
    # 2. ヘルスチェック
    if not args.no_health:
        get_service_health()
        print()
    
    # 3. 最新ログ
    if not args.no_logs:
        get_latest_logs(args.hours, args.limit, args.severity)
        print()
    
    print("=" * 80)
    print(f"✅ ステータス確認完了: {get_current_jst()}")

if __name__ == '__main__':
    main()
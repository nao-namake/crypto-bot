#!/usr/bin/env python3
"""
監視システムの動作状況を確認するスクリプト
- Cloud Logging Sink の動作確認
- Cloud Monitoring ダッシュボード確認
- アラートポリシーの確認
- カスタムメトリクスの送信テスト
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from google.cloud import bigquery, logging_v2, monitoring_v3


def check_logging_sink():
    """Cloud Logging Sink の動作確認"""
    print("=== Cloud Logging Sink チェック ===")
    
    # Logging クライアント初期化
    logging_client = logging_v2.Client()
    
    try:
        # プロジェクトのシンク一覧を取得
        sinks = list(logging_client.list_sinks())
        
        crypto_bot_sinks = [s for s in sinks if 'crypto_bot' in s.name.lower()]
        
        if crypto_bot_sinks:
            for sink in crypto_bot_sinks:
                print(f"✅ Sink見つかりました: {sink.name}")
                print(f"   宛先: {sink.destination}")
                print(f"   フィルタ: {sink.filter_}")
                
                # BigQuery データセットの確認
                if 'bigquery' in sink.destination:
                    check_bigquery_logs(sink.destination)
        else:
            print("❌ crypto-bot用のLogging Sinkが見つかりません")
            
    except Exception as e:
        print(f"❌ Logging Sink確認エラー: {e}")


def check_bigquery_logs(destination):
    """BigQuery ログの確認"""
    print("\n--- BigQuery ログデータ確認 ---")
    
    try:
        # BigQuery クライアント初期化
        bq_client = bigquery.Client()
        
        # 宛先からプロジェクトIDとデータセットIDを抽出
        # 例: bigquery.googleapis.com/projects/PROJECT_ID/datasets/DATASET_ID
        parts = destination.split('/')
        if len(parts) >= 7:
            project_id = parts[4]
            dataset_id = parts[6]
        else:
            print(f"❌ BigQuery宛先の形式が想定外: {destination}")
            return
        
        print(f"データセット: {project_id}.{dataset_id}")
        
        # データセット内のテーブル一覧
        dataset_ref = bq_client.dataset(dataset_id, project=project_id)
        tables = list(bq_client.list_tables(dataset_ref))
        
        if tables:
            print(f"✅ {len(tables)}個のテーブルが見つかりました")
            
            # 最新のテーブルからサンプルログを取得
            latest_table = max(tables, key=lambda t: t.table_id)
            print(f"最新テーブル: {latest_table.table_id}")
            
            # サンプルクエリ実行
            query = f"""
            SELECT timestamp, severity, textPayload
            FROM `{project_id}.{dataset_id}.{latest_table.table_id}`
            WHERE severity >= 'WARNING'
            ORDER BY timestamp DESC
            LIMIT 5
            """
            
            query_job = bq_client.query(query)
            results = list(query_job.result())
            
            if results:
                print(f"✅ 最新ログ {len(results)}件:")
                for row in results:
                    print(f"   {row.timestamp} [{row.severity}] {row.textPayload}")
            else:
                print("⚠️  WARNING以上のログが見つかりません")
                
        else:
            print("❌ ログテーブルが見つかりません")
            
    except Exception as e:
        print(f"❌ BigQuery確認エラー: {e}")


def check_monitoring_metrics():
    """Cloud Monitoring カスタムメトリクスの確認"""
    print("\n=== Cloud Monitoring メトリクス確認 ===")
    
    try:
        monitoring_client = monitoring_v3.MetricServiceClient()
        
        # プロジェクト名取得
        from google.auth import default
        _, project_id = default()
        project_name = f"projects/{project_id}"
        
        # カスタムメトリクス一覧取得
        descriptors = monitoring_client.list_metric_descriptors(name=project_name)
        
        crypto_bot_metrics = []
        for descriptor in descriptors:
            if 'crypto_bot' in descriptor.type:
                crypto_bot_metrics.append(descriptor)
        
        if crypto_bot_metrics:
            print(f"✅ crypto-bot カスタムメトリクス {len(crypto_bot_metrics)}個:")
            for metric in crypto_bot_metrics:
                print(f"   - {metric.type}")
        else:
            print("⚠️  crypto-bot カスタムメトリクスが見つかりません")
            
        # テストメトリクス送信
        test_custom_metrics_push(monitoring_client, project_name)
        
    except Exception as e:
        print(f"❌ Monitoring確認エラー: {e}")


def test_custom_metrics_push(monitoring_client, project_name):
    """カスタムメトリクスのテスト送信"""
    print("\n--- カスタムメトリクステスト送信 ---")
    
    try:
        # テスト用メトリクス送信
        series = monitoring_v3.TimeSeries()
        series.metric.type = "custom.googleapis.com/crypto_bot/test_metric"
        series.resource.type = "global"
        series.resource.labels["project_id"] = project_name.split('/')[1]
        
        from google.protobuf.timestamp_pb2 import Timestamp
        now_ts = Timestamp()
        now_ts.GetCurrentTime()
        
        point = monitoring_v3.Point({
            "interval": {"end_time": now_ts},
            "value": {"double_value": 123.456},
        })
        series.points.append(point)
        
        monitoring_client.create_time_series(name=project_name, time_series=[series])
        print("✅ テストメトリクス送信成功")
        
    except Exception as e:
        print(f"❌ メトリクス送信テストエラー: {e}")


def check_alert_policies():
    """アラートポリシーの確認"""
    print("\n=== アラートポリシー確認 ===")
    
    try:
        monitoring_client = monitoring_v3.AlertPolicyServiceClient()
        
        # プロジェクト名取得
        from google.auth import default
        _, project_id = default()
        project_name = f"projects/{project_id}"
        
        # アラートポリシー一覧取得
        policies = list(monitoring_client.list_alert_policies(name=project_name))
        
        if policies:
            print(f"✅ アラートポリシー {len(policies)}個:")
            for policy in policies:
                print(f"   - {policy.display_name} ({'有効' if policy.enabled else '無効'})")
                for condition in policy.conditions:
                    print(f"     条件: {condition.display_name}")
        else:
            print("⚠️  アラートポリシーが見つかりません")
            
    except Exception as e:
        print(f"❌ アラートポリシー確認エラー: {e}")


def check_status_json():
    """status.json の存在と内容確認"""
    print("\n=== status.json 確認 ===")
    
    status_file = Path("status.json")
    if status_file.exists():
        try:
            with status_file.open() as f:
                status = json.load(f)
            
            print("✅ status.json 見つかりました")
            print(f"   最終更新: {status.get('last_updated', 'N/A')}")
            print(f"   総利益: {status.get('total_profit', 0)} 円")
            print(f"   取引回数: {status.get('trade_count', 0)}")
            print(f"   ポジション: {status.get('position', 'なし')}")
            print(f"   状態: {status.get('state', 'unknown')}")
            
        except Exception as e:
            print(f"❌ status.json 読み取りエラー: {e}")
    else:
        print("⚠️  status.json が見つかりません")


def generate_monitoring_report():
    """監視状況の総合レポート生成"""
    print("\n" + "="*50)
    print("監視システム総合レポート")
    print("="*50)
    
    report = {
        "check_time": datetime.now(timezone.utc).isoformat(),
        "components": {}
    }
    
    # 各チェック実行
    check_logging_sink()
    check_monitoring_metrics()
    check_alert_policies()
    check_status_json()
    
    print("\n" + "="*50)
    print("チェック完了")
    print("="*50)
    
    # 推奨改善事項
    print("\n🔧 推奨改善事項:")
    print("1. カスタムメトリクスが無い場合: monitor.py の実行確認")
    print("2. エラーログが大量にある場合: アプリケーションの修正")
    print("3. アラートポリシーが無い場合: Terraformでの追加設定")
    print("4. ダッシュボードの微調整: P99レイテンシ、CPU使用率の追加")


if __name__ == "__main__":
    generate_monitoring_report()
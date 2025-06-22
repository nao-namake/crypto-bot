#!/usr/bin/env python3
"""
アラートポリシーのE2Eテストスクリプト
- PnL損失アラートのテスト
- レイテンシアラートのテスト
- カスタムメトリクス送信による通知テスト
"""

import time
from datetime import datetime, timezone

from google.cloud import monitoring_v3


def send_test_pnl_loss():
    """PnL損失アラートのテスト用メトリクス送信"""
    print("=== PnL損失アラートテスト ===")
    
    try:
        monitoring_client = monitoring_v3.MetricServiceClient()
        
        # プロジェクト名取得
        from google.auth import default
        _, project_id = default()
        project_name = f"projects/{project_id}"
        
        # -6000円の損失をシミュレート（閾値-5000円を下回る）
        test_loss = -6000.0
        
        series = monitoring_v3.TimeSeries()
        series.metric.type = "custom.googleapis.com/crypto_bot/pnl"
        series.resource.type = "global"
        series.resource.labels["project_id"] = project_id
        
        from google.protobuf.timestamp_pb2 import Timestamp
        now_ts = Timestamp()
        now_ts.GetCurrentTime()
        
        point = monitoring_v3.Point({
            "interval": {"end_time": now_ts},
            "value": {"double_value": test_loss},
        })
        series.points.append(point)
        
        monitoring_client.create_time_series(name=project_name, time_series=[series])
        
        print(f"✅ テスト損失メトリクス送信: {test_loss} JPY")
        print("⏰ アラート発火まで約5分お待ちください（duration=300s）")
        
        return True
        
    except Exception as e:
        print(f"❌ PnL損失テスト失敗: {e}")
        return False


def send_test_high_trade_count():
    """過剰取引アラートのテスト用メトリクス送信"""
    print("\n=== 過剰取引アラートテスト ===")
    
    try:
        monitoring_client = monitoring_v3.MetricServiceClient()
        
        # プロジェクト名取得
        from google.auth import default
        _, project_id = default()
        project_name = f"projects/{project_id}"
        
        # 異常に高い取引回数をシミュレート
        test_trade_count = 1000
        
        series = monitoring_v3.TimeSeries()
        series.metric.type = "custom.googleapis.com/crypto_bot/trade_count"
        series.resource.type = "global"
        series.resource.labels["project_id"] = project_id
        
        from google.protobuf.timestamp_pb2 import Timestamp
        now_ts = Timestamp()
        now_ts.GetCurrentTime()
        
        point = monitoring_v3.Point({
            "interval": {"end_time": now_ts},
            "value": {"double_value": float(test_trade_count)},
        })
        series.points.append(point)
        
        monitoring_client.create_time_series(name=project_name, time_series=[series])
        
        print(f"✅ テスト取引回数メトリクス送信: {test_trade_count}")
        print("⏰ アラート発火確認のため監視してください")
        
        return True
        
    except Exception as e:
        print(f"❌ 過剰取引テスト失敗: {e}")
        return False


def reset_test_metrics():
    """テスト用メトリクスを正常値にリセット"""
    print("\n=== テストメトリクスリセット ===")
    
    try:
        monitoring_client = monitoring_v3.MetricServiceClient()
        
        # プロジェクト名取得
        from google.auth import default
        _, project_id = default()
        project_name = f"projects/{project_id}"
        
        from google.protobuf.timestamp_pb2 import Timestamp
        now_ts = Timestamp()
        now_ts.GetCurrentTime()
        
        # PnLを正常値にリセット (0円)
        pnl_series = monitoring_v3.TimeSeries()
        pnl_series.metric.type = "custom.googleapis.com/crypto_bot/pnl"
        pnl_series.resource.type = "global"
        pnl_series.resource.labels["project_id"] = project_id
        
        pnl_point = monitoring_v3.Point({
            "interval": {"end_time": now_ts},
            "value": {"double_value": 0.0},
        })
        pnl_series.points.append(pnl_point)
        
        # 取引回数を正常値にリセット (10回)
        trade_series = monitoring_v3.TimeSeries()
        trade_series.metric.type = "custom.googleapis.com/crypto_bot/trade_count"
        trade_series.resource.type = "global"
        trade_series.resource.labels["project_id"] = project_id
        
        trade_point = monitoring_v3.Point({
            "interval": {"end_time": now_ts},
            "value": {"double_value": 10.0},
        })
        trade_series.points.append(trade_point)
        
        monitoring_client.create_time_series(
            name=project_name, 
            time_series=[pnl_series, trade_series]
        )
        
        print("✅ メトリクスを正常値にリセットしました")
        print("   PnL: 0 JPY")
        print("   取引回数: 10")
        
        return True
        
    except Exception as e:
        print(f"❌ メトリクスリセット失敗: {e}")
        return False


def check_alert_policies():
    """現在のアラートポリシー一覧表示"""
    print("\n=== 現在のアラートポリシー ===")
    
    try:
        alert_client = monitoring_v3.AlertPolicyServiceClient()
        
        # プロジェクト名取得
        from google.auth import default
        _, project_id = default()
        project_name = f"projects/{project_id}"
        
        policies = list(alert_client.list_alert_policies(name=project_name))
        
        if policies:
            for i, policy in enumerate(policies, 1):
                status = "🟢 有効" if policy.enabled else "🔴 無効"
                print(f"{i}. {policy.display_name} ({status})")
                
                for j, condition in enumerate(policy.conditions, 1):
                    print(f"   条件{j}: {condition.display_name}")
                
                if policy.notification_channels:
                    print(f"   通知先: {len(policy.notification_channels)}個設定済み")
                else:
                    print("   ⚠️  通知先が設定されていません")
                
                print()
        else:
            print("❌ アラートポリシーが見つかりません")
            
    except Exception as e:
        print(f"❌ アラートポリシー確認エラー: {e}")


def run_interactive_test():
    """インタラクティブなアラートテスト"""
    print("🧪 アラートポリシー E2E テスト")
    print("=" * 50)
    
    check_alert_policies()
    
    print("\n実行するテストを選択してください:")
    print("1. PnL損失アラートテスト (-6000 JPY)")
    print("2. 過剰取引アラートテスト (1000回)")
    print("3. テストメトリクスリセット")
    print("4. 全てのテスト実行")
    print("0. 終了")
    
    while True:
        try:
            choice = input("\n選択 (0-4): ").strip()
            
            if choice == "0":
                print("テスト終了")
                break
            elif choice == "1":
                send_test_pnl_loss()
            elif choice == "2":
                send_test_high_trade_count()
            elif choice == "3":
                reset_test_metrics()
            elif choice == "4":
                print("📧 全テスト実行開始...")
                send_test_pnl_loss()
                time.sleep(2)
                send_test_high_trade_count()
                
                print("\n⏰ 5分後にリセットしますか？ [y/N]: ", end="")
                reset_choice = input().strip().lower()
                if reset_choice == 'y':
                    print("⏰ 5分待機中...")
                    time.sleep(300)  # 5分待機
                    reset_test_metrics()
            else:
                print("無効な選択です")
                
        except KeyboardInterrupt:
            print("\n\n中断されました")
            break
        except Exception as e:
            print(f"エラー: {e}")


if __name__ == "__main__":
    run_interactive_test()
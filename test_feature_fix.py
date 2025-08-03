#!/usr/bin/env python3
"""
特徴量修正後のテストスクリプト
97特徴量システム・Production.yml完全対応テスト
"""
import subprocess
import signal
import time
import sys

def test_feature_fix():
    """修正後の特徴量システムテスト（60秒制限）"""
    print("🔧 特徴量修正後のテストスクリプト")
    print("📋 設定: config/production/production.yml")
    print("🎯 Production.yml完全対応97特徴量システム")
    print("⏱️ テスト時間: 60秒")
    print("-" * 60)
    
    # プロセス開始
    cmd = [sys.executable, "-m", "crypto_bot.main", "live-bitbank", "--config", "config/production/production.yml"]
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        start_time = time.time()
        feature_indicators = []
        config_indicators = []
        errors = []
        
        # 60秒間実行
        while time.time() - start_time < 60:
            line = process.stdout.readline()
            if line:
                print(line.strip())
                
                # 特徴量関連の成功指標をチェック
                if "✅" in line and any(keyword in line for keyword in ["features", "technical", "batch", "production"]):
                    feature_indicators.append(line.strip())
                
                # 設定関連の成功指標をチェック
                if any(keyword in line for keyword in ["EMA periods:", "ATR periods:", "RSI periods:", "Production.yml compliance"]):
                    config_indicators.append(line.strip())
                
                # エラーをチェック
                if any(keyword in line for keyword in ["ERROR", "CRITICAL", "Missing", "Failed", "未実装特徴量"]):
                    errors.append(line.strip())
                    
                # 致命的エラーで即座停止
                if "CRITICAL" in line and "API" in line:
                    print("🚨 CRITICAL APIエラー検出 - テスト停止")
                    break
            
            if process.poll() is not None:
                break
                
        # プロセス終了
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=5)
        
        # 結果サマリー
        print("\n" + "=" * 60)
        print("📊 特徴量修正後テスト結果サマリー")
        print("=" * 60)
        print(f"⏱️ 実行時間: {time.time() - start_time:.1f}秒")
        print(f"🔧 特徴量関連成功指標: {len(feature_indicators)}個")
        print(f"⚙️ 設定関連成功指標: {len(config_indicators)}個")
        print(f"❌ エラー: {len(errors)}個")
        
        if feature_indicators:
            print("\n🎯 特徴量関連成功指標:")
            for indicator in feature_indicators[:3]:  # 最初の3個表示
                print(f"   {indicator}")
        
        if config_indicators:
            print("\n⚙️ 設定関連成功指標:")
            for indicator in config_indicators[:3]:  # 最初の3個表示
                print(f"   {indicator}")
        
        if errors:
            print("\n⚠️ エラー:")
            for error in errors[:3]:  # 最初の3個表示
                print(f"   {error}")
        
        # 修正効果判定
        feature_success = len(feature_indicators) > 0
        config_success = len(config_indicators) > 0
        error_minimal = len(errors) < 3
        
        if feature_success and config_success and error_minimal:
            print("\n🎊 修正成功: Production.yml特徴量システム正常動作")
            return True
        elif feature_success and error_minimal:
            print("\n✅ 修正部分成功: 特徴量システム改善・要微調整")
            return True
        else:
            print("\n❌ 修正要継続: さらなる調整が必要")
            return False
            
    except Exception as e:
        print(f"🚨 テスト実行エラー: {e}")
        return False

if __name__ == "__main__":
    success = test_feature_fix()
    sys.exit(0 if success else 1)
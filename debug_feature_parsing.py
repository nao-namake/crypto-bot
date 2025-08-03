#!/usr/bin/env python3
"""
EMA/ATR期間抽出デバッグスクリプト
"""
import subprocess
import signal
import time
import sys

def debug_feature_parsing():
    """EMA/ATR期間抽出のデバッグ（30秒制限）"""
    print("🔍 EMA/ATR期間抽出デバッグスクリプト")
    print("📋 設定: config/production/production.yml")
    print("⏱️ テスト時間: 30秒")
    print("-" * 50)
    
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
        ema_parsing = []
        atr_parsing = []
        feature_processing = []
        
        # 30秒間実行
        while time.time() - start_time < 30:
            line = process.stdout.readline()
            if line:
                print(line.strip())
                
                # EMAパース関連ログ
                if "EMA" in line and any(keyword in line for keyword in ["feature detected", "period added", "parsing failed"]):
                    ema_parsing.append(line.strip())
                
                # ATRパース関連ログ  
                if "ATR" in line and any(keyword in line for keyword in ["feature detected", "period added", "parsing failed"]):
                    atr_parsing.append(line.strip())
                
                # 特徴量処理全般
                if "Processing feature:" in line:
                    feature_processing.append(line.strip())
                
                # TechnicalEngineの初期化完了で停止
                if "Technical features parsing completed" in line:
                    print("🎯 パース処理完了 - 早期停止")
                    break
                    
            if process.poll() is not None:
                break
                
        # プロセス終了
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=5)
        
        # デバッグ結果サマリー
        print("\n" + "=" * 50)
        print("🔍 EMA/ATR期間抽出デバッグ結果")
        print("=" * 50)
        print(f"⏱️ 実行時間: {time.time() - start_time:.1f}秒")
        print(f"🔍 特徴量処理数: {len(feature_processing)}個")
        print(f"📊 EMAパース: {len(ema_parsing)}個")
        print(f"📊 ATRパース: {len(atr_parsing)}個")
        
        if feature_processing:
            print(f"\n🔍 特徴量処理サンプル（最初の5個）:")
            for fp in feature_processing[:5]:
                print(f"   {fp}")
        
        if ema_parsing:
            print(f"\n📊 EMAパース詳細:")
            for ep in ema_parsing:
                print(f"   {ep}")
        else:
            print(f"\n❌ EMAパース: 検出されませんでした")
            
        if atr_parsing:
            print(f"\n📊 ATRパース詳細:")
            for ap in atr_parsing:
                print(f"   {ap}")
        else:
            print(f"\n❌ ATRパース: 検出されませんでした")
            
    except Exception as e:
        print(f"🚨 デバッグ実行エラー: {e}")
        return False

if __name__ == "__main__":
    debug_feature_parsing()
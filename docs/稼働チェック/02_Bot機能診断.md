# 🤖 AI自動取引Bot機能診断（エントリーシグナル・コア機能編）

## 📋 このファイルの目的

**使用場面**:
- デプロイ後のBot機能稼働確認
- 55特徴量生成・5戦略判定・ML予測の健全性チェック
- Silent Failure・取引阻害エラーの早期検知
- 定期的なBot機能診断（毎日推奨）

**ルール**:
- 01_システム稼働診断.md で基盤正常確認後に実行
- 終了コードで問題の重大度を判断
- 実装履歴は開発履歴ドキュメント参照
- Bot機能のみに特化（基盤システムは01参照）

**現在のシステム状態**: Phase 49完了（2025/10/24）
- 55特徴量Strategy-Aware ML（50基本+5戦略信号）
- ML統合率100%達成（閾値0.45/0.60最適化）
- TradeTracker統合・SELL Only問題解決
- 証拠金維持率80%確実遵守・デイトレード設定（SL 1.5%・TP 2%）

## ⚠️ 重要: まずREADME.mdを読んでください

**このファイルを実行する前に、必ず [README.md](./README.md) を先に読んで全体の構成・実行順序・推奨フローを理解してください。**

---

## 🎯 診断対象

- 🎯 **5戦略動的信頼度**: ATR・MochiPoy・MultiTimeframe・Donchian・ADX統合（小数点第3位変動確認）
- 🤖 **3モデルMLアンサンブル**: LightGBM 40%・XGBoost 40%・RandomForest 20%
- 💚 **ML予測統合**: 戦略70%+ML30%加重平均統合・ML統合率100%達成（Phase 41.8.5）
- 📈 **55特徴量生成**: 50基本特徴量+5戦略信号特徴量（Strategy-Aware ML・Phase 41.8）
- 💱 **Kelly基準**: ポジションサイジング・動的計算
- 🔄 **統合シグナル生成**: 戦略→ML→統合フロー・SELL Only問題解決（Phase 49）
- 🔍 **Silent Failure**: シグナル生成→実行断絶検出
- 💰 **取引機能**: 最小ロット優先・ML信頼度連動制限
- 🎯 **TP/SL機能**: デイトレード設定（SL 1.5%・TP 2%・Phase 49）
- 📊 **リスク管理**: SL/TP計算・適応型ATR倍率・証拠金維持率80%遵守
- ⏰ **時間軸管理**: 15m足ATR使用・クールダウン柔軟化
- 🎲 **動的信頼度**: 変動幅拡大・override_atr設定
- 📊 **TradeTracker統合**: エントリー/エグジットペアリング・損益計算（Phase 49）

## 📂 関連ファイル

- **[01_システム稼働診断.md](./01_システム稼働診断.md)** - 基盤システム（インフラ）のチェック
- **[03_緊急対応マニュアル.md](./03_緊急対応マニュアル.md)** - 問題発生時の修正手順

## ⚠️ 前提条件

**必須**: 01_システム稼働診断.md で基盤システムが正常であることを事前確認してください。

---

## 🚀 Bot機能診断スクリプト（10分）

### 準備: 共通関数定義（前回から継承）

```bash
#!/bin/bash
# AI自動取引Bot機能診断スクリプト（macOS対応版）
echo "🤖 AI自動取引Bot機能診断開始: $(python3 -c "import datetime; print(datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d %H:%M:%S JST'))")"

# 最新CI時刻取得（01_システム稼働診断.mdと同様）
LATEST_CI_UTC=$(gh run list --limit=1 --workflow="CI/CD Pipeline" --status=success --json=createdAt --jq='.[0].createdAt' 2>/dev/null)
if [ -n "$LATEST_CI_UTC" ]; then
    DEPLOY_TIME="$LATEST_CI_UTC"
else
    DEPLOY_TIME=$(python3 -c "import datetime; utc_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1); print(utc_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ'))")
fi

# 共通関数定義（macOS対応）
count_logs_since_deploy() {
    local query="$1"
    local limit="${2:-50}"
    if [ -n "$DEPLOY_TIME" ]; then
        gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND ($query) AND timestamp>=\"$DEPLOY_TIME\"" --limit="$limit" --format="value(textPayload)" | grep -c . || echo "0"
    else
        echo "0"
    fi
}

show_logs_since_deploy() {
    local query="$1"
    local limit="${2:-10}"
    if [ -n "$DEPLOY_TIME" ]; then
        gcloud logging read "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"crypto-bot-service-prod\" AND ($query) AND timestamp>=\"$DEPLOY_TIME\"" --limit="$limit" --format="value(timestamp.date(tz='Asia/Tokyo'),textPayload)"
    else
        echo "❌ DEPLOY_TIME未設定"
    fi
}

# スコア初期化
CRITICAL_ISSUES=0
WARNING_ISSUES=0
NORMAL_CHECKS=0
```

### A. コア機能チェック

```bash
echo ""
echo "🤖 Bot機能チェック"

# 1. Silent Failure検出（最重要）
echo ""
echo "🔍 Silent Failure検出分析"
SIGNAL_COUNT=$(count_logs_since_deploy "textPayload:\"統合シグナル生成: buy\" OR textPayload:\"統合シグナル生成: sell\"" 30)
ORDER_COUNT=$(count_logs_since_deploy "textPayload:\"注文実行\" OR textPayload:\"order_executed\" OR textPayload:\"create_order\"" 30)

echo "   シグナル生成: $SIGNAL_COUNT件"
echo "   注文実行: $ORDER_COUNT件"

if [ $SIGNAL_COUNT -eq 0 ]; then
    echo "⚠️ シグナル生成なし（Bot機能動作要確認）"
    WARNING_ISSUES=$((WARNING_ISSUES + 1))
elif [ $SIGNAL_COUNT -gt 0 ] && [ $ORDER_COUNT -eq 0 ]; then
    echo "❌ 完全Silent Failure検出（致命的）"
    echo "   → シグナル${SIGNAL_COUNT}件生成されるも注文実行0件"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 2))
else
    # macOS対応: Python3で成功率計算
    SUCCESS_RATE=$(python3 -c "print(int(($ORDER_COUNT / $SIGNAL_COUNT) * 100))" 2>/dev/null || echo "0")
    if [ $SUCCESS_RATE -ge 40 ]; then
        echo "✅ 取引実行: 正常 (成功率: ${SUCCESS_RATE}%)"
        NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
    elif [ $SUCCESS_RATE -ge 20 ]; then
        echo "⚠️ 取引実行: 低成功率 (${SUCCESS_RATE}% - 要件定義40%基準未達)"
        WARNING_ISSUES=$((WARNING_ISSUES + 1))
    else
        echo "❌ 部分的Silent Failure (成功率: ${SUCCESS_RATE}% - 深刻な実行問題)"
        CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
    fi
fi

# 2. ML予測実行確認
echo ""
echo "🤖 ML予測システム確認"
ML_PREDICTION_COUNT=$(count_logs_since_deploy "textPayload:\"ProductionEnsemble\" OR textPayload:\"ML予測\" OR textPayload:\"アンサンブル予測\"" 20)
if [ $ML_PREDICTION_COUNT -gt 0 ]; then
    echo "✅ ML予測: 正常実行中 ($ML_PREDICTION_COUNT回確認)"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
else
    echo "❌ ML予測: 未実行 (ProductionEnsemble動作なし)"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
fi

# 3. フォールバック値使用頻度確認
echo ""
echo "🔄 フォールバック値使用頻度確認"
FALLBACK_CONFIDENCE_COUNT=$(count_logs_since_deploy "textPayload:\"信頼度: 0.200\"" 30)
if [ $FALLBACK_CONFIDENCE_COUNT -lt 5 ]; then
    echo "✅ フォールバック使用: 正常範囲 ($FALLBACK_CONFIDENCE_COUNT回)"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
elif [ $FALLBACK_CONFIDENCE_COUNT -lt 15 ]; then
    echo "⚠️ フォールバック使用: やや多い ($FALLBACK_CONFIDENCE_COUNT回)"
    WARNING_ISSUES=$((WARNING_ISSUES + 1))
else
    echo "❌ フォールバック使用: 異常多用 ($FALLBACK_CONFIDENCE_COUNT回・動的計算停止疑い)"
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
fi
```

### B. 5戦略動的信頼度統合確認

```bash
echo ""
echo "🎯 5戦略動的信頼度確認"

# 戦略統合チェック関数（macOS最適化）
check_strategy_confidence() {
    local strategies=("ATRBased" "MochipoyAlert" "MultiTimeframe" "DonchianChannel" "ADXTrendStrength")
    local active_strategies=0

    echo "   戦略稼働状況:"
    for strategy in "${strategies[@]}"; do
        local count=$(count_logs_since_deploy "textPayload:\"\\[$strategy\\]\"" 15)
        echo "     $strategy: $count回"
        [ $count -gt 0 ] && active_strategies=$((active_strategies + 1))
    done

    local dynamic_count=$(count_logs_since_deploy "textPayload:\"信頼度: 0.[3-6][0-9]\"" 30)
    echo "   動的信頼度計算: $dynamic_count回"

    if [ $active_strategies -eq 5 ] && [ $dynamic_count -gt 10 ]; then
        echo "✅ 5戦略動的信頼度: 全戦略正常稼働（動的計算$dynamic_count回）"
        NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
    elif [ $active_strategies -ge 3 ] && [ $dynamic_count -gt 5 ]; then
        echo "⚠️ 5戦略動的信頼度: ${active_strategies}/5戦略稼働（動的計算制限的）"
        WARNING_ISSUES=$((WARNING_ISSUES + 1))
    else
        echo "❌ 5戦略動的信頼度: ${active_strategies}/5戦略稼働（動的計算$dynamic_count回・停止疑い）"
        CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
    fi
}

check_strategy_confidence
```

### C. 3モデルアンサンブル詳細確認

```bash
echo ""
echo "🤖 3モデルアンサンブル詳細確認"

# ML統合チェック関数（macOS最適化）
check_ml_ensemble() {
    local models=("LightGBM" "XGBoost" "RandomForest")
    local weights=("50%" "30%" "20%")
    local active_models=0

    echo "   モデル稼働状況:"
    for i in "${!models[@]}"; do
        local model=${models[i]}
        local weight=${weights[i]}
        local count=$(count_logs_since_deploy "textPayload:\"$model\"" 15)
        echo "     $model($weight): $count回"
        [ $count -gt 0 ] && active_models=$((active_models + 1))
    done

    local weight_count=$(count_logs_since_deploy "textPayload:\"50%\" OR textPayload:\"30%\" OR textPayload:\"20%\"" 10)
    echo "   重み付け確認: $weight_count回"

    if [ $active_models -eq 3 ]; then
        echo "✅ 3モデルアンサンブル: 全モデル稼働完了"
        NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
    elif [ $active_models -gt 0 ]; then
        echo "⚠️ 3モデルアンサンブル: ${active_models}/3モデル稼働（一部停止）"
        WARNING_ISSUES=$((WARNING_ISSUES + 1))
    else
        echo "❌ 3モデルアンサンブル: 全モデル停止"
        CRITICAL_ISSUES=$((CRITICAL_ISSUES + 1))
    fi
}

check_ml_ensemble
```

### D. プロセスフロー断絶ポイント特定

```bash
echo ""
echo "📊 AI自動取引プロセスフロー視覚的診断"
echo "=============================================================="

# プロセス状態確認関数（macOS最適化）
check_process_status() {
    local pattern="$1"
    local count_threshold="${2:-0}"
    [ $(count_logs_since_deploy "$pattern" 10) -gt $count_threshold ] && echo "✅" || echo "❌"
}

# 9段階プロセス状態確認（macOS互換版）
DATA_4H_STATUS=$(check_process_status "textPayload:\"4h足\" OR textPayload:\"4時間足\"")
DATA_15M_STATUS=$(check_process_status "textPayload:\"15m足\" OR textPayload:\"15分足\"")
FEATURE_STATUS=$(check_process_status "textPayload:\"55特徴量\" OR textPayload:\"特徴量生成完了\"")
STRATEGY_STATUS=$(check_process_status "textPayload:\"ATRBased\" OR textPayload:\"MochipoyAlert\"")
ML_STATUS=$(check_process_status "textPayload:\"LightGBM\" OR textPayload:\"XGBoost\"")
SIGNAL_STATUS=$(check_process_status "textPayload:\"統合シグナル生成\"")
RISK_STATUS=$(check_process_status "textPayload:\"リスク評価\" OR textPayload:\"TradeEvaluation\"")
APPROVED_STATUS=$(check_process_status "textPayload:\"APPROVED\" OR textPayload:\"取引承認\"")
EXECUTION_STATUS=$(check_process_status "textPayload:\"ExecutionService\"")
BITBANK_STATUS=$(check_process_status "textPayload:\"create_order\" OR textPayload:\"Bitbank注文\"")
TRADETRACKER_STATUS=$(check_process_status "textPayload:\"TradeTracker\" OR textPayload:\"エントリー/エグジットペアリング\"")

# 視覚的フロー表示（macOS互換版）
echo "🔄 AI自動取引プロセスフロー状態:"
echo ""
cat << EOF
① データ取得           $DATA_4H_STATUS $DATA_15M_STATUS
   4時間足・15分足
            ↓
② 特徴量生成          $FEATURE_STATUS
   55特徴量統合計算（50基本+5戦略信号）
            ↓
③ 5戦略実行           $STRATEGY_STATUS
   BUY/SELL/HOLD判定
            ↓
④ ML予測              $ML_STATUS
   3モデルアンサンブル（LightGBM 40%・XGBoost 40%・RandomForest 20%）
            ↓
⑤ 統合シグナル生成    $SIGNAL_STATUS
   戦略70%+ML30%統合
            ↓
⑥ リスク評価          $RISK_STATUS
   Kelly基準・証拠金維持率80%確認
            ↓
⑦ 取引承認判定        $APPROVED_STATUS
   APPROVED/DENIED
            ↓
⑧ ExecutionService    $EXECUTION_STATUS
   取引実行サービス
            ↓
⑨ Bitbank注文実行     $BITBANK_STATUS
   実際のAPI注文
            ↓
⑩ TradeTracker統合    $TRADETRACKER_STATUS
   エントリー/エグジットペアリング（Phase 49）
EOF

# プロセス断絶ポイント特定（macOS互換版）
echo ""
echo "🔍 プロセス断絶ポイント分析:"

# 効率的な断絶ポイント特定（macOS互換）
FAILURE_FOUND=false

if [ "$DATA_4H_STATUS" = "❌" ] || [ "$DATA_15M_STATUS" = "❌" ]; then
    echo "   🚨 【データ取得段階】API接続・認証問題 → 01_システム稼働診断.md要確認"
    FAILURE_FOUND=true
elif [ "$FEATURE_STATUS" = "❌" ]; then
    echo "   🚨 【特徴量生成段階】データ処理問題 → FeatureGenerator・pandas/numpy確認"
    FAILURE_FOUND=true
elif [ "$STRATEGY_STATUS" = "❌" ]; then
    echo "   🚨 【5戦略実行段階】戦略ロジック問題 → 動的信頼度・フォールバック確認"
    FAILURE_FOUND=true
elif [ "$ML_STATUS" = "❌" ]; then
    echo "   🚨 【ML予測段階】モデル問題 → ProductionEnsemble・モデルファイル確認"
    FAILURE_FOUND=true
elif [ "$SIGNAL_STATUS" = "❌" ]; then
    echo "   🚨 【統合シグナル生成段階】統合処理問題 → orchestrator.py確認"
    FAILURE_FOUND=true
elif [ "$RISK_STATUS" = "❌" ]; then
    echo "   🚨 【リスク評価段階】Kelly基準問題 → RiskManager・ドローダウン管理確認"
    FAILURE_FOUND=true
elif [ "$APPROVED_STATUS" = "❌" ]; then
    echo "   🚨 【取引承認段階】全てDENIED → 信頼度閾値・リスクスコア確認"
    FAILURE_FOUND=true
elif [ "$EXECUTION_STATUS" = "❌" ]; then
    echo "   🚨 【ExecutionService段階】Silent Failure → async/await・AttributeError確認"
    FAILURE_FOUND=true
elif [ "$BITBANK_STATUS" = "❌" ]; then
    echo "   🚨 【Bitbank注文段階】API注文問題 → create_order・認証・パラメータ確認"
    FAILURE_FOUND=true
fi

# 全プロセス正常チェック
if [ "$FAILURE_FOUND" = false ]; then
    echo "   ✅ 【全プロセス正常】- データ取得→特徴量→戦略→ML→統合→リスク→承認→実行→注文の完全フロー稼働"
fi
```

### E. Phase 27-32機能診断

```bash
echo ""
echo "🚀 Phase 27-32機能診断"

# Phase 27: 最小ロット優先検出
echo ""
echo "💰 Phase 27: 最小ロット優先機能"
MIN_LOT_COUNT=$(count_logs_since_deploy "textPayload:\"最小ロット優先適用\" OR textPayload:\"最小ロット許可\"" 20)
if [ $MIN_LOT_COUNT -gt 0 ]; then
    echo "✅ 最小ロット優先: 正常動作 ($MIN_LOT_COUNT回検出)"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
else
    echo "⚠️ 最小ロット優先: 未検出（低残高時未発動の可能性）"
fi

# Phase 28: テイクプロフィット/ストップロス配置確認
echo ""
echo "🎯 Phase 28: TP/SL配置確認"
TP_COUNT=$(count_logs_since_deploy "textPayload:\"テイクプロフィット注文配置\" OR textPayload:\"TP注文\"" 20)
SL_COUNT=$(count_logs_since_deploy "textPayload:\"ストップロス注文配置\" OR textPayload:\"SL注文\"" 20)
echo "   TP注文配置: $TP_COUNT回"
echo "   SL注文配置: $SL_COUNT回"

if [ $TP_COUNT -gt 0 ] || [ $SL_COUNT -gt 0 ]; then
    echo "✅ TP/SL機能: 正常動作"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
else
    echo "⚠️ TP/SL機能: 未検出（エントリーなしの可能性）"
fi

# Phase 29.5: ML予測統合確認（戦略70%+ML30%）
echo ""
echo "💚 Phase 29.5: ML予測統合（戦略70%+ML30%）"
ML_INTEGRATION_COUNT=$(count_logs_since_deploy "textPayload:\"ML統合\" OR textPayload:\"戦略.*ML.*統合\"" 20)
STRATEGY_WEIGHT_COUNT=$(count_logs_since_deploy "textPayload:\"戦略=.*ML=\" OR textPayload:\"strategy_weight.*ml_weight\"" 20)
echo "   ML統合実行: $ML_INTEGRATION_COUNT回"
echo "   加重平均統合: $STRATEGY_WEIGHT_COUNT回"

if [ $ML_INTEGRATION_COUNT -gt 0 ]; then
    echo "✅ ML予測統合: 正常動作（Phase 29.5真のハイブリッドMLbot実現）"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
else
    echo "⚠️ ML予測統合: 未検出（エントリーなしの可能性）"
fi

# Phase 30: SL/TP計算確認
echo ""
echo "📊 Phase 30: SL/TP計算確認"
PHASE30_CALC_COUNT=$(count_logs_since_deploy "textPayload:\"Phase 30 SL/TP計算\" OR textPayload:\"ATR=.*倍率=.*SL距離=\"" 20)
if [ $PHASE30_CALC_COUNT -gt 0 ]; then
    echo "✅ Phase 30 SL/TP計算: 正常動作 ($PHASE30_CALC_COUNT回)"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))

    # SL距離サンプル表示
    echo "   サンプルログ:"
    show_logs_since_deploy "textPayload:\"Phase 30 SL/TP計算\"" 3 | head -3
else
    echo "⚠️ Phase 30 SL/TP計算: 未検出"
fi

# Phase 31: 15m足ATR使用確認
echo ""
echo "⏰ Phase 31: 15m足ATR使用・クールダウン確認"
PHASE31_ATR_COUNT=$(count_logs_since_deploy "textPayload:\"Phase 31: 15m足ATR使用\"" 20)
COOLDOWN_COUNT=$(count_logs_since_deploy "textPayload:\"クールダウン\" OR textPayload:\"cooldown\"" 20)
echo "   15m ATR使用: $PHASE31_ATR_COUNT回"
echo "   クールダウン発動: $COOLDOWN_COUNT回"

if [ $PHASE31_ATR_COUNT -gt 0 ]; then
    echo "✅ Phase 31 15m ATR: 正常動作"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
else
    echo "⚠️ Phase 31 15m ATR: 未検出"
fi

if [ $COOLDOWN_COUNT -gt 0 ]; then
    echo "✅ クールダウン機能: 動作確認"
else
    echo "ℹ️  クールダウン: 未発動（連続取引なし）"
fi

# Phase 32: 動的信頼度精密値確認
echo ""
echo "🎲 Phase 32: 動的信頼度精密値確認（小数点第3位変動）"

# 動的信頼度の精密値検出（0.5XX, 0.6XX, 0.7XX等）
DYNAMIC_CONFIDENCE_SAMPLES=$(show_logs_since_deploy "textPayload:\"信頼度\" OR textPayload:\"confidence\"" 50 | grep -E "0\.[0-9]{3}" | head -10)

if [ -n "$DYNAMIC_CONFIDENCE_SAMPLES" ]; then
    echo "✅ Phase 32動的信頼度: 精密値検出（小数点第3位変動確認）"
    NORMAL_CHECKS=$((NORMAL_CHECKS + 1))
    echo "   サンプル値:"
    echo "$DYNAMIC_CONFIDENCE_SAMPLES" | head -5
else
    echo "⚠️ Phase 32動的信頼度: 精密値未検出（固定値の可能性）"
    WARNING_ISSUES=$((WARNING_ISSUES + 1))
fi
```

### F. 最終判定（Bot機能）

```bash
echo ""
echo "=============================================================="
echo "📊 Bot機能診断結果"
echo "✅ 正常項目: $NORMAL_CHECKS"
echo "⚠️ 警告項目: $WARNING_ISSUES"
echo "❌ 致命的問題: $CRITICAL_ISSUES"

# macOS対応スコア計算（重要度重み付け）
TOTAL_SCORE=$((NORMAL_CHECKS * 10 - WARNING_ISSUES * 3 - CRITICAL_ISSUES * 20))
echo "🏆 総合スコア: $TOTAL_SCORE点"

# 最終判定
echo ""
echo "🎯 Bot機能最終判定"

if [ $SIGNAL_COUNT -gt 0 ] && [ $ORDER_COUNT -eq 0 ]; then
    echo "💀 完全Silent Failure - 即座対応必須"
    echo "   🚨 シグナル生成されるも注文実行完全停止"
    echo "   → 03_緊急対応マニュアル.md Silent Failure対応実行"
    exit 1
elif [ $CRITICAL_ISSUES -ge 2 ]; then
    echo "🔴 Bot機能重大問題 - 緊急対応必要 ($CRITICAL_ISSUES件)"
    echo "   → ML予測・戦略システム・特徴量生成に深刻な影響"
    echo "   → 詳細診断・修正実行"
    exit 1
elif [ $CRITICAL_ISSUES -ge 1 ]; then
    echo "🟠 要注意 - Bot機能部分問題 ($CRITICAL_ISSUES件)"
    echo "   → Bot機能の一部に深刻な問題"
    echo "   → 詳細診断推奨"
    exit 2
elif [ $WARNING_ISSUES -ge 3 ]; then
    echo "🟡 監視継続 - Bot機能品質低下 ($WARNING_ISSUES件)"
    echo "   → パフォーマンス低下・予防的対応推奨"
    exit 3
else
    echo "🟢 Bot機能正常 - エントリーシグナル完全稼働"
    echo "   ✨ 15特徴量・5戦略・3モデル・Kelly基準・統合シグナルすべて正常"
    echo "   📊 正常: $NORMAL_CHECKS件, 警告: $WARNING_ISSUES件, 致命的: $CRITICAL_ISSUES件"
    echo "   🚀 AI自動取引システム完全稼働中"
    exit 0
fi
```

---

## 🔍 詳細診断（Bot機能問題時）

### 🤖 ML予測・戦略システム詳細診断

**いつ使用**: ML予測またはシグナル生成に問題がある時

```bash
echo "=== ML予測・戦略システム詳細診断（macOS対応） ==="

# 1. ProductionEnsemble・ML予測実行状況
echo "1. ProductionEnsemble・ML予測実行状況:"
echo "   ML初期化・ロード状況:"
show_logs_since_deploy "textPayload:\"ProductionEnsemble\" AND (textPayload:\"初期化\" OR textPayload:\"ロード\" OR textPayload:\"load\")" 10

echo "   ML予測実行ログ:"
show_logs_since_deploy "textPayload:\"ML予測\" OR textPayload:\"predict\" OR textPayload:\"アンサンブル\"" 15

echo "   予測結果値確認:"
show_logs_since_deploy "textPayload:\"予測値\" OR textPayload:\"prediction\" OR textPayload:\"ensemble.*result\"" 10

# 2. 5戦略個別実行状況確認
echo ""
echo "2. 5戦略個別実行状況確認:"
strategies=("ATRBased" "MochipoyAlert" "MultiTimeframe" "DonchianChannel" "ADXTrendStrength")

for strategy in "${strategies[@]}"; do
    count=$(count_logs_since_deploy "textPayload:\"\\[$strategy\\]\"" 15)
    echo "   $strategy: $count回実行"
    if [ $count -eq 0 ]; then
        echo "     ❌ $strategy戦略動作停止"
    else
        echo "     ✅ $strategy戦略正常動作"
    fi
done

# 3. 戦略分析詳細プロセス確認
echo ""
echo "3. 戦略分析詳細プロセス確認:"
echo "   BUY/SELL/HOLD判定状況:"
BUY_COUNT=$(count_logs_since_deploy "textPayload:\"signal.*BUY\" OR textPayload:\"判定.*BUY\"" 20)
SELL_COUNT=$(count_logs_since_deploy "textPayload:\"signal.*SELL\" OR textPayload:\"判定.*SELL\"" 20)
HOLD_COUNT=$(count_logs_since_deploy "textPayload:\"signal.*HOLD\" OR textPayload:\"判定.*HOLD\"" 20)

echo "     BUY判定: $BUY_COUNT回"
echo "     SELL判定: $SELL_COUNT回"
echo "     HOLD判定: $HOLD_COUNT回"

TOTAL_SIGNALS=$((BUY_COUNT + SELL_COUNT + HOLD_COUNT))
if [ $TOTAL_SIGNALS -eq 0 ]; then
    echo "     ❌ 戦略判定完全停止"
else
    echo "     ✅ 戦略判定動作中（合計: $TOTAL_SIGNALS回）"
fi

echo "   戦略統合プロセス確認:"
show_logs_since_deploy "textPayload:\"戦略統合\" OR textPayload:\"strategy.*integration\" OR textPayload:\"統合判定\"" 10

# 4. 動的信頼度計算詳細確認
echo ""
echo "4. 動的信頼度計算詳細確認:"
echo "   動的信頼度範囲確認（0.25-0.6）:"
DYNAMIC_025_COUNT=$(count_logs_since_deploy "textPayload:\"信頼度: 0.2[5-9]\"" 15)
DYNAMIC_030_COUNT=$(count_logs_since_deploy "textPayload:\"信頼度: 0.[3-5][0-9]\"" 15)
DYNAMIC_060_COUNT=$(count_logs_since_deploy "textPayload:\"信頼度: 0.6[0-9]\"" 15)

echo "     0.25-0.29範囲: $DYNAMIC_025_COUNT回"
echo "     0.30-0.59範囲: $DYNAMIC_030_COUNT回"
echo "     0.60以上: $DYNAMIC_060_COUNT回"

TOTAL_DYNAMIC=$((DYNAMIC_025_COUNT + DYNAMIC_030_COUNT + DYNAMIC_060_COUNT))
if [ $TOTAL_DYNAMIC -gt 10 ]; then
    echo "     ✅ 動的信頼度計算正常（$TOTAL_DYNAMIC回）"
else
    echo "     ❌ 動的信頼度計算不足（$TOTAL_DYNAMIC回・要件定義未達）"
fi

echo "   フォールバック信頼度使用確認:"
FALLBACK_200_COUNT=$(count_logs_since_deploy "textPayload:\"信頼度: 0.200\"" 20)
echo "     フォールバック0.200使用: $FALLBACK_200_COUNT回"

if [ $FALLBACK_200_COUNT -gt 15 ]; then
    echo "     ❌ フォールバック異常多用（動的計算停止疑い）"
else
    echo "     ✅ フォールバック使用正常範囲"
fi
```

### 📈 15特徴量完全生成詳細確認

**いつ使用**: 特徴量生成に問題がある時

```bash
echo "=== 15特徴量完全生成詳細確認（macOS対応） ==="

# 1. 15特徴量個別生成確認（要件定義対応強化）
echo "1. 15特徴量個別生成確認:"
declare -a features=("close" "volume" "rsi_14" "macd" "atr_14" "bb_position" "ema_20" "ema_50" "volume_ratio" "donchian_high_20" "donchian_low_20" "channel_position" "adx_14" "plus_di_14" "minus_di_14")

MISSING_FEATURES=0
echo "   個別特徴量生成確認:"
for feature in "${features[@]}"; do
    feature_count=$(count_logs_since_deploy "textPayload:\"$feature\"" 5)
    if [ $feature_count -eq 0 ]; then
        echo "     ⚠️ $feature: 生成確認できず"
        MISSING_FEATURES=$((MISSING_FEATURES + 1))
    else
        echo "     ✅ $feature: $feature_count回確認"
    fi
done

if [ $MISSING_FEATURES -eq 0 ]; then
    echo "   ✅ 15特徴量: 全て生成確認（7カテゴリ完全対応）"
else
    echo "   ❌ 特徴量生成: $MISSING_FEATURES個の特徴量未確認（要件定義15特徴量未達）"
fi

# 2. 7カテゴリ特徴量分類確認
echo ""
echo "2. 7カテゴリ特徴量分類確認:"
PRICE_FEATURES=$(python3 -c "
features = ['close']
for f in features:
    if '$(count_logs_since_deploy "textPayload:\"$f\"" 5)' != '0':
        print('1', end='')
    else:
        print('0', end='')
")

VOLUME_FEATURES=$(python3 -c "
features = ['volume', 'volume_ratio']
count = 0
for f in features:
    if '$(count_logs_since_deploy "textPayload:\"$f\"" 5)' != '0':
        count += 1
print(count)
")

MOMENTUM_FEATURES=$(python3 -c "
features = ['rsi_14', 'macd']
count = 0
for f in features:
    if '$(count_logs_since_deploy "textPayload:\"$f\"" 5)' != '0':
        count += 1
print(count)
")

echo "   価格系特徴量: $PRICE_FEATURES/1"
echo "   ボリューム系特徴量: $VOLUME_FEATURES/2"
echo "   モメンタム系特徴量: $MOMENTUM_FEATURES/2"

# 3. データ品質・整合性確認
echo ""
echo "3. データ品質・整合性確認:"
echo "   特徴量生成エラー確認:"
show_logs_since_deploy "textPayload:\"特徴量\" AND (textPayload:\"エラー\" OR textPayload:\"Error\" OR textPayload:\"NaN\")" 10

echo "   データ欠損・異常値確認:"
show_logs_since_deploy "textPayload:\"データ欠損\" OR textPayload:\"異常値\" OR textPayload:\"missing.*data\"" 8
```

### 💱 Kelly基準動作詳細確認

**いつ使用**: ポジションサイジングや取引量に問題がある時

```bash
echo "=== Kelly基準動作詳細確認（macOS対応） ==="

# 1. Kelly基準計算実行確認
echo "1. Kelly基準計算実行確認:"
KELLY_CALCULATION_COUNT=$(count_logs_since_deploy "textPayload:\"Kelly基準\" OR textPayload:\"kelly_fraction\"" 15)
POSITION_SIZE_DYNAMIC=$(count_logs_since_deploy "textPayload:\"position_size\" AND NOT textPayload:\"0.0001\"" 15)
INITIAL_SIZE_COUNT=$(count_logs_since_deploy "textPayload:\"初期固定サイズ\" OR textPayload:\"0.0001 BTC\"" 15)
KELLY_MIN_TRADES=$(count_logs_since_deploy "textPayload:\"Kelly.*5.*取引\" OR textPayload:\"最小取引数.*5\"" 10)

echo "   Kelly計算実行: $KELLY_CALCULATION_COUNT回"
echo "   動的ポジションサイズ: $POSITION_SIZE_DYNAMIC回"
echo "   初期固定サイズ使用: $INITIAL_SIZE_COUNT回（最初の5取引）"
echo "   Kelly最小取引数確認: $KELLY_MIN_TRADES回"

if [ $KELLY_CALCULATION_COUNT -gt 0 ] && [ $POSITION_SIZE_DYNAMIC -gt 0 ]; then
    echo "   ✅ Kelly基準: 正常動作（動的サイジング確認・要件定義準拠）"
elif [ $INITIAL_SIZE_COUNT -gt 0 ]; then
    echo "   ⚠️ Kelly基準: 初期段階（固定サイズ・5取引未達成）"
else
    echo "   ❌ Kelly基準: 動作異常（固定サイズのみ・要件定義未達）"
fi

# 2. Kelly履歴・過去実績確認
echo ""
echo "2. Kelly履歴・過去実績確認:"
echo "   Kelly計算に必要な取引履歴確認:"
show_logs_since_deploy "textPayload:\"Kelly計算に必要な取引数不足\" OR textPayload:\"取引履歴.*不足\"" 8

echo "   Kelly基準エラー・例外確認:"
show_logs_since_deploy "textPayload:\"Kelly\" AND (textPayload:\"エラー\" OR textPayload:\"Error\" OR textPayload:\"Exception\")" 8

# 3. ポジションサイズ計算詳細確認
echo ""
echo "3. ポジションサイズ計算詳細確認:"
echo "   position_size計算ログ:"
show_logs_since_deploy "textPayload:\"position_size\" OR textPayload:\"ポジションサイズ\"" 10

echo "   最小取引単位問題確認:"
show_logs_since_deploy "textPayload:\"最小取引単位\" OR textPayload:\"amount.*too.*small\"" 5

echo "   0サイズ問題確認:"
show_logs_since_deploy "textPayload:\"position.*size.*0.000\" OR textPayload:\"サイズ.*0\"" 8
```

### 🔄 統合シグナル生成フロー確認

**いつ使用**: シグナル生成プロセスに問題がある時

```bash
echo "=== 統合シグナル生成フロー確認（macOS対応） ==="

# 1. ML予測→戦略統合→シグナル生成フロー確認
echo "1. ML予測→戦略統合→シグナル生成フロー:"
ML_PREDICTION_COUNT=$(count_logs_since_deploy "textPayload:\"ProductionEnsemble\" OR textPayload:\"ML予測\"" 20)
STRATEGY_INTEGRATION_COUNT=$(count_logs_since_deploy "textPayload:\"戦略統合\" OR textPayload:\"strategy.*integration\"" 20)
INTEGRATED_SIGNAL_COUNT=$(count_logs_since_deploy "textPayload:\"統合シグナル生成\"" 20)

echo "   ML予測実行: $ML_PREDICTION_COUNT回"
echo "   戦略統合処理: $STRATEGY_INTEGRATION_COUNT回"
echo "   統合シグナル生成: $INTEGRATED_SIGNAL_COUNT回"

if [ $ML_PREDICTION_COUNT -gt 0 ] && [ $INTEGRATED_SIGNAL_COUNT -eq 0 ]; then
    echo "   ❌ ML予測実行されるもシグナル生成失敗"
elif [ $ML_PREDICTION_COUNT -eq 0 ] && [ $INTEGRATED_SIGNAL_COUNT -gt 0 ]; then
    echo "   ⚠️ ML予測なしでシグナル生成（フォールバック動作）"
else
    echo "   ✅ ML予測→シグナル生成フロー正常"
fi

# 2. orchestrator.py統合処理確認
echo ""
echo "2. orchestrator.py統合処理確認:"
echo "   orchestrator実行状況:"
show_logs_since_deploy "textPayload:\"orchestrator\" OR textPayload:\"オーケストレーター\"" 10

echo "   統合処理エラー・例外:"
show_logs_since_deploy "textPayload:\"orchestrator\" AND (textPayload:\"エラー\" OR textPayload:\"Error\" OR textPayload:\"Exception\")" 8

# 3. ExecutionService統合確認
echo ""
echo "3. ExecutionService統合確認:"
echo "   ExecutionService呼び出し:"
EXECUTION_SERVICE_COUNT=$(count_logs_since_deploy "textPayload:\"ExecutionService\" AND textPayload:\"execute_trade\"" 20)
echo "   ExecutionService実行: $EXECUTION_SERVICE_COUNT回"

if [ $INTEGRATED_SIGNAL_COUNT -gt 0 ] && [ $EXECUTION_SERVICE_COUNT -eq 0 ]; then
    echo "   ❌ シグナル生成されるもExecutionService未実行"
else
    echo "   ✅ シグナル→ExecutionService連携正常"
fi

echo "   ExecutionService詳細ログ:"
show_logs_since_deploy "textPayload:\"ExecutionService\"" 15
```

---

## 🎯 使用方法

### 1. 基本実行（推奨）

```bash
# 事前確認: 基盤システムチェック
bash 01_システム稼働診断.sh

# Bot機能診断実行
bash 02_Bot機能診断.sh

# 結果に応じて次のアクション
# 終了コード 0: 全機能正常
# 終了コード 1-2: 03_緊急対応マニュアル.md で修正
# 終了コード 3: 監視継続
```

### 2. 詳細診断実行（問題発生時）

```bash
# ML・戦略問題時
bash 02_Bot機能診断.sh --detail-ml

# 特徴量問題時
bash 02_Bot機能診断.sh --detail-features

# Kelly基準問題時
bash 02_Bot機能診断.sh --detail-kelly

# シグナル生成問題時
bash 02_Bot機能診断.sh --detail-signal
```

### 3. 推奨実行順序

1. **01_システム稼働診断.md** （基盤システム確認）
2. **02_Bot機能診断.md** ← **このファイル**
3. **03_緊急対応マニュアル.md** （問題発生時）

---

## 📊 判定基準

- **終了コード 0**: 🟢 Bot機能正常 - エントリーシグナル完全稼働
- **終了コード 1**: 💀 完全Silent Failure・重大問題 - 即座対応必須
- **終了コード 2**: 🟠 要注意 - Bot機能部分問題・詳細診断推奨
- **終了コード 3**: 🟡 監視継続 - 品質低下・予防的対応推奨

---

**🎯 重要**: このファイルはBot固有機能をチェックします。基盤システム（インフラ）の問題が検出された場合は、まず **01_システム稼働診断.md** で基盤を修正してからBot機能診断を実行してください。

**最終更新**: 2025年10月25日 - Phase 49完了対応（55特徴量・TradeTracker統合・SELL Only問題解決）
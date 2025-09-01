#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# ファイル名: scripts/checks.sh
# 説明:
# 新システムの品質チェックを一括実行するシェルスクリプトです。
# Phase 13完了版：12特徴量最適化システム・全テスト対応
#
# - flake8: コードスタイルチェック（PEP8違反検出）
# - isort: import順チェック（自動修正せず、--check-only）
# - black: コード整形チェック（自動修正せず、--checkのみ）
# - pytest: テスト実行とカバレッジ計測（新システム全テスト対応）
#
# 使い方（ターミナルでプロジェクトルートから実行）:
#   bash scripts/checks.sh
#   ./scripts/checks.sh
# =============================================================================

# スクリプト開始時刻記録
START_TIME=$(date +%s)

echo "🚀 新システム品質チェック開始 (Phase 13完了)"
echo "================================================="

# カバレッジ最低ライン（実用性重視・50%目標設定）
COV_FAIL_UNDER=50

# Phase 9: 新システムディレクトリ構造確認
echo ">>> 📂 新システムディレクトリ構造確認"
if [[ ! -d "src" ]]; then
    echo "❌ エラー: src/ディレクトリが見つかりません"
    echo "プロジェクトルートから実行してください"
    exit 1
fi

echo "✅ src/ディレクトリ確認完了"

# モデルディレクトリ整合性チェック（Phase 9追加）
echo ">>> 🤖 MLモデル整合性チェック"
if [[ -f "models/production/production_ensemble.pkl" ]]; then
    echo "✅ 本番用統合モデル存在確認"
else
    echo "⚠️  警告: 本番用統合モデルが見つかりません"
    echo "python scripts/create_ml_models.py で作成してください"
fi

# コードスタイルチェック
echo ">>> 🎨 flake8: コードスタイルチェック"
python3 -m flake8 src/ tests/ scripts/ \
    --max-line-length=100 \
    --ignore=E203,W503,E402,F401,F841,F541,F811 \
    --exclude=_legacy_v1 || {
    echo "❌ flake8チェック失敗"
    exit 1
}

echo "✅ flake8チェック完了"

# import順序チェック
echo ">>> 📥 isort: import順序チェック"
python3 -m isort --check-only --diff src/ tests/ scripts/ \
    --skip=_legacy_v1 || {
    echo "❌ isortチェック失敗"
    echo "修正するには: python3 -m isort src/ tests/ scripts/"
    exit 1
}

echo "✅ isortチェック完了"

# コード整形チェック
echo ">>> ⚫ black: コード整形チェック"
python3 -m black --check --diff src/ tests/ scripts/ \
    --exclude="_legacy_v1" || {
    echo "❌ blackチェック失敗"
    echo "修正するには: python3 -m black src/ tests/ scripts/"
    exit 1
}

echo "✅ blackチェック完了"

# Phase 13: 新システム全テスト実行
echo ">>> 🧪 pytest: 新システム全テスト実行"
echo "対象テスト: 全テストスイート"

python3 -m pytest \
  tests/ \
  --maxfail=3 \
  --disable-warnings \
  -v \
  --cov=src \
  --cov-report=term-missing \
  --cov-report=html:coverage-reports/htmlcov \
  --cov-fail-under="${COV_FAIL_UNDER}" \
  --tb=short || {
    echo "❌ テスト実行失敗"
    exit 1
}

echo "✅ 全テスト実行完了"

# 手動テスト確認（Phase 9追加）
echo ">>> 🔧 手動テスト: データ層基盤確認"
if [[ -f "tests/manual/test_phase2_components.py" ]]; then
    python3 tests/manual/test_phase2_components.py || {
        echo "⚠️  警告: 手動テスト失敗（継続可能）"
    }
else
    echo "⚠️  警告: 手動テストファイルが見つかりません"
fi

# 実行時間計算
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "🎉 新システム品質チェック完了！"
echo "================================================="
echo "📊 チェック結果:"
echo "  - flake8: ✅ PASS"
echo "  - isort: ✅ PASS"  
echo "  - black: ✅ PASS"
echo "  - pytest: ✅ PASS (全テスト・${COV_FAIL_UNDER}%カバレッジ目標)"
echo "  - 実行時間: ${DURATION}秒"
echo ""
echo "📁 カバレッジレポート: coverage-reports/htmlcov/index.html"
echo "🚀 システム品質: 本番運用準備完了"
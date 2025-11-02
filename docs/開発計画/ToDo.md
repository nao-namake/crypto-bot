# 暗号資産取引Bot - 未達成タスク一覧

## 📋 このファイルの目的

**使用場面**:
- 未達成開発タスク確認
- 実装優先度の把握
- 進捗管理とタスク追跡

**ルール**:
- **未完了タスクのみ記載**（完了済み: `docs/開発履歴/Phase_47-49.md`参照）
- **実装順序**に沿って記載（Phase 50.9 → 51 → 52...）
- 定期的にタスク状況を更新

**🎯 2025/11/03更新**: Phase 51.1-51.4完了 ✅・Phase 51.5-A完了 ✅（戦略削除実行・27ファイル修正・60特徴量固定）→ **Phase 51.5-B実装推奨**（動的戦略管理基盤・93%削減）または **Phase 51.5-C実装推奨**（レガシーコード完全調査）⭐次回優先

---

## ✅ Phase 50.9完了サマリー

### Phase 50.9: 外部API完全削除・シンプル設計回帰（2025/11/01完了） ✅

**実施内容**:
- **62特徴量固定システム確立**（70→62特徴量・外部API 8特徴量削除）
- **2段階Graceful Degradation**（Level 1: 62 → Level 2: 57 → Dummy）
- **コード削減**: 約1,438行削除（external_api.py完全削除・テスト削除・設定簡略化）
- **モデルファイルリネーム**: ensemble_level2/3 → ensemble_full/basic（セマンティック命名）
- **システム安定性向上**: 外部API依存完全解消・ゼロダウンタイム実現

**品質基準**:
- 1,056テスト100%成功（-46テスト・外部APIテスト削除）
- 64.99%カバレッジ達成（要求65%まであと0.01%）
- 外部API参照0件（完全削除確認）
- ensemble_full.pkl (4.7MB)・ensemble_basic.pkl (4.1MB) 存在確認

**効果**:
- システム安定性: ゼロダウンタイム保証（外部API障害リスク完全解消）
- 保守性向上: 約20%向上（コード削減・設計シンプル化）
- 予測精度維持: 62特徴量でも高精度維持（外部API効果統計的有意差なし±0.83%）

**GCPクリーンアップ完了（2025/11/02実施）** ✅:
- Cloud Runサービス: crypto-bot-service-prod 完全削除
- Cloud Runリビジョン: 2個全削除（11/1作成分含む）
- Artifact Registryイメージ: 31個全削除（10/19-11/1作成分）
- **効果**: 過去イメージ参照エラーリスク完全排除・Phase 50.9デプロイ準備完了

**詳細**: `docs/開発履歴/Phase_50.md` Phase 50.9セクション参照

---

## ✅ Phase 50.8完了サマリー

### Phase 50.8: Graceful Degradation完全実装・外部API障害対応（2025/11/01完了）
- **Level 1→2自動フォールバック実装**（外部API障害時も継続動作）
- **動的モデル選択実装**（特徴量数に応じた最適モデル自動選択）
- **ExternalAPIError伝播修正**（正しい例外ハンドリング）
- **本番環境0エントリー問題解決**（根本原因：外部API不安定性）

**品質基準**: 1,117テスト100%成功・68.32%カバレッジ達成

**システム停止完了（2025/11/02実施）** ✅:
- Phase 50.8システム完全停止（GCPクリーンアップ時）
- 診断レポート作成完了（`/tmp/診断レポート.md`）
- 問題分析完了: 外部API依存・特徴量数不一致・Graceful Degradation不全
- **Phase 50.9への移行準備完了**

**詳細**: `docs/開発履歴/Phase_50.md`参照

---

## 🎯 開発方針・品質基準（全Phase共通）

### KISS原則の徹底
- **少ない機能×高精度**を目指す
- 必要最小限の要素に絞る
- Phase 46のシンプル設計方針を継続

### 品質保証プロセス
1. **バックテスト必須**: 全機能追加時に効果検証
2. **段階的導入**: paper → 少額live → 本番の3段階
3. **テスト100%維持**: 新機能は必ず単体・統合テスト追加
4. **カバレッジ維持**: 66%以上を維持

### 複雑化リスク管理
- 各Phase実装後に複雑性評価
- 設定ファイル化の徹底（ハードコード禁止）
- コードレビュー強化

---

## 🔥 未達成タスク一覧（実装優先度順）

---

# ✅ Phase 50.9: 外部API完全削除（1-2日）【完了 ✅ 2025/11/01】

## 目的

**問題**: 外部API特徴量（8個）がGCP環境で不安定・時間軸ミスマッチ（日次更新 vs 5分足取引）・統計的有意性不足（+0.83%）
**解決**: 外部API特徴量を完全削除し、62基本特徴量に最適化されたシステムに移行
**期待効果**: システム安定性向上・ゼロダウンタイム実現・保守性向上・シンプル設計回帰

**✅ 完了ステータス**: Phase 50.9完全完了（2025/11/01）・上記「Phase 50.9完了サマリー」参照

## 背景分析

### 外部API削除の根拠

**時間軸ミスマッチ**:
- 外部APIデータ: 日次更新（24時間単位）
- トレード判断: 5分間隔（288回/日）
- 結果: 288回中287回は同じ値を参照（情報価値ほぼゼロ）

**統計的有意性不足**:
- ML精度向上: +0.83%（CV標準偏差0.042-0.092内で統計的誤差範囲）
- RandomForest: 0.549→0.555（+0.006）
- XGBoost: 0.540→0.545（+0.005）

**GCP環境不安定性**:
- Phase H: 外部API失敗で複数回頓挫
- Phase 50.8: 外部API部分失敗で0エントリー問題発生
- 成功率: 2/8（25%）→ 8/8（100%）修正後も不安定性残存

**BTC市場独立性**:
- BTC価格: 独自変動が80-90%を占める
- USD/JPY・日経平均: 弱相関（相関係数0.2-0.3）
- Fear & Greed Index: BTC価格から派生（因果関係逆転）

### レガシーシステムからの教訓

**過去の失敗パターン**:
- 外部API依存により複数回システム停止
- GCP環境での外部API取得が根本的に不安定
- 複雑性増加による保守性低下

## 実装タスク

### 削除対象ファイル

**完全削除（3ファイル・~838行 + 4.2MB）**:
- `src/features/external_api.py`（436行）
- `tests/unit/features/test_external_api.py`（402行）
- `models/production/ensemble_level1.pkl`（4.2MB・70特徴量モデル）

**モデルファイルリネーム（重要：旧レベルシステム廃止）**:
- `ensemble_level2.pkl`（62特徴量） → **`ensemble_full.pkl`**（完全特徴量セット・デフォルトモデル）
- `ensemble_level3.pkl`（57特徴量） → **`ensemble_basic.pkl`**（基本特徴量セット・フォールバック用）

**リネームの根拠**:
- レベル番号システム廃止 → 旧コードとの混同防止
- 特徴量内容を名前で明示 → 保守性向上
- セマンティックな命名 → 将来の拡張性確保

**部分修正（18ファイル・~600行削除）**:
- `config/core/feature_order.json`: external_apiカテゴリ削除、total_features: 70→62、model_file名更新
- `src/features/feature_generator.py`: 外部API呼び出し削除、**二重カウントバグ修正**
- `src/core/orchestration/ml_loader.py`: Level 1削除、Level 2→full化、モデルパス更新
- `src/core/orchestration/ml_adapter.py`: 外部API関連ロジック削除
- その他14ファイル（設定・テスト・ドキュメント）

### 実行順序（7フェーズ）

#### Phase 1: 影響範囲確認（30分）
- [ ] grep検証（external_api、ExternalAPIError、fetch_external等）
- [ ] 依存関係マッピング
- [ ] 削除ファイルリスト最終確認

#### Phase 2: テスト削除（10分）
- [ ] `tests/unit/features/test_external_api.py`削除
- [ ] `tests/integration/test_phase_50_3_graceful_degradation.py`外部API部分削除

#### Phase 3: 設定ファイル更新（30分）
- [ ] `config/core/feature_order.json`: total_features: 70→62、external_apiカテゴリ削除
- [ ] `config/core/thresholds.yaml`: external_api設定削除
- [ ] `config/core/features.yaml`: external_api設定削除（存在する場合）

#### Phase 4: ML層修正 + モデルファイルリネーム（1-2時間）⭐重要

**4-1. モデルファイル物理リネーム**:
- [ ] `models/production/ensemble_level1.pkl` → **削除**（70特徴量モデル不要）
- [ ] `models/production/ensemble_level2.pkl` → **`ensemble_full.pkl`**（62特徴量・デフォルト）
- [ ] `models/production/ensemble_level3.pkl` → **`ensemble_basic.pkl`**（57特徴量・フォールバック）

```bash
# 実行コマンド
rm models/production/ensemble_level1.pkl
mv models/production/ensemble_level2.pkl models/production/ensemble_full.pkl
mv models/production/ensemble_level3.pkl models/production/ensemble_basic.pkl
```

**4-2. config/core/feature_order.json修正**:
- [ ] `feature_levels`セクション更新:
  - `full_with_external`レベル削除（70特徴量）
  - `full`レベル: `model_file: "ensemble_full.pkl"`
  - `basic`レベル: `model_file: "ensemble_basic.pkl"`

```json
{
  "total_features": 62,
  "feature_levels": {
    "full": {
      "count": 62,
      "description": "完全特徴量（外部APIなし）",
      "model_file": "ensemble_full.pkl"
    },
    "basic": {
      "count": 57,
      "description": "基本特徴量（戦略信号なし）",
      "model_file": "ensemble_basic.pkl"
    }
  }
}
```

**4-3. src/core/orchestration/ml_loader.py修正**:
- [ ] `_determine_feature_level()`簡略化:
  - Level 1（full_with_external・70特徴量）ロジック削除
  - Level 2（full・62特徴量）をデフォルト化
  - `full_with_external`参照を完全削除
- [ ] `_load_production_ensemble()`修正:
  - `level="full_with_external"`処理削除
  - モデルパス: `ensemble_level2.pkl` → `ensemble_full.pkl`
  - モデルパス: `ensemble_level3.pkl` → `ensemble_basic.pkl`
- [ ] ログメッセージ更新（Level 1/2/3 → full/basic表記）

**4-4. src/core/orchestration/ml_adapter.py修正**:
- [ ] 外部API関連ロジック削除
- [ ] `ensure_correct_model()`修正（70特徴量判定削除）

**4-5. src/core/exceptions.py修正**:
- [ ] `ExternalAPIError`クラス削除

**4-6. 完全検証（Phase 4完了後）**:
```bash
# 旧レベルシステム参照が残っていないか確認（全て0件であること）
grep -r "level1\|level2\|level3" src/core/orchestration/ --exclude="*.md"
grep -r "ensemble_level" src/ config/ tests/ --exclude-dir=__pycache__
grep -r "full_with_external" src/ config/
```

#### Phase 5: 特徴量生成修正（1-2時間）⭐重要
- [ ] `src/features/feature_generator.py`:
  - 外部API呼び出し削除（lines 907-929）
  - **二重カウントバグ修正**（`total_generated = len(generated_features) + len(external_api_generated)` → `len(generated_features)`のみ）
  - ExternalAPIError import削除
  - 外部API統合ロジック削除

#### Phase 6: ドキュメント更新（1時間）
- [ ] `README.md`: 70→62特徴量、外部API削除記載
- [ ] `CLAUDE.md`: Phase 50.9追加、70→62特徴量修正
- [ ] `docs/開発履歴/Phase_50.md`: Phase 50.9セクション追加
- [ ] その他ドキュメント（src/README.md、strategies/README.md等）

#### Phase 7: 完全検証（2-3時間）

**7-1. 外部API完全削除確認**:
```bash
# 残存コード確認（全て0件であること）
grep -r "external_api" src/ config/ tests/ --exclude-dir=__pycache__
grep -r "ExternalAPIError" src/ config/ tests/
grep -r "fetch_external" src/
grep -r "from src.features.external_api" src/ tests/
```

**7-2. 旧レベルシステム完全削除確認**:
```bash
# 旧命名が残っていないか確認（全て0件であること）
grep -r "level1\|level2\|level3" src/ config/ --exclude="*.md"
grep -r "ensemble_level" src/ config/ tests/ --exclude-dir=__pycache__
grep -r "full_with_external" src/ config/

# 新モデルファイル存在確認
ls -lh models/production/ensemble_full.pkl    # 存在すること
ls -lh models/production/ensemble_basic.pkl   # 存在すること
ls -lh models/production/ensemble_level*.pkl  # 0件であること（削除済み）
```

**7-3. テスト実行**:
- [ ] `bash scripts/testing/checks.sh`実行
- [ ] テスト数確認: 326 → **280想定**（-46テスト）
- [ ] カバレッジ維持: 68%以上
- [ ] 全テスト100%成功確認

**7-4. ローカル動作確認**:
- [ ] ローカル実行確認（paper mode・24時間）
- [ ] 62特徴量生成成功確認
- [ ] `ensemble_full.pkl`モデル使用確認（ログ確認）
- [ ] ML予測正常動作確認
- [ ] エントリー判断正常動作確認

**7-5. 本番デプロイ**:
- [ ] gitタグ作成（Phase-50.9-external-api-deletion）
- [ ] 本番デプロイ（GCP Cloud Run）
- [ ] 本番環境ログ確認（62特徴量・ensemble_full.pkl使用確認）
- [ ] 24時間監視

### 検証基準

**完全削除確認**:
```bash
# 残存コード確認（全て0件であること）
grep -r "external_api" src/ config/ tests/ --exclude-dir=__pycache__
grep -r "ExternalAPIError" src/ config/ tests/
grep -r "fetch_external" src/
grep -r "level1" src/ config/ --exclude="*.md"
grep -r "full_with_external" src/ config/
```

**テスト成功基準**:
- テスト数: 326 → 280（-46テスト）
- 成功率: 100%
- カバレッジ: 68%以上維持

**動作確認**:
- 62特徴量生成成功
- Level 2（ensemble_level2.pkl）モデル使用
- ML予測正常動作
- エントリー判断正常動作

## Phase 50.9期待効果

- **システム安定性**: ゼロダウンタイム実現（外部API障害リスク完全解消）
- **保守性向上**: ~1,438行削除・シンプル設計回帰
- **テスト削減**: 326 → 280テスト（-46テスト・14%削減）
- **コード品質**: 複雑性削減・KISS原則徹底
- **ML精度**: 統計的有意差なし（0.83%誤差範囲内）
- **特徴量システム**: 62基本特徴量に最適化

## リスクと対策

**リスク**:
- 外部API特徴量削除によるML精度への影響（想定: ±0.83%誤差範囲内）
- Level 1モデル削除による後方互換性問題

**対策**:
- バックテスト比較（削除前後）
- Phase 51.1でレンジ型戦略リバランスによる精度向上（+10-20%）
- 段階的デプロイ（ローカル24時間 → 本番）
- ロールバック準備（gitタグ作成）

---

# 🎯 Phase 51: ML統合アーキテクチャ刷新・レンジ型戦略最適化（2.5-3.5週間）【Phase 50.9完了後・最優先】

## ⚠️ 重要: Phase 51.1（旧）スキップ決定

**旧Phase 51.1**: 戦略重みリバランス（unified.yaml設定変更のみ）

**スキップ理由**:
1. ❌ **Strategy-Aware ML（Phase 41.8）では設定変更だけでは効果薄い**
   - 戦略重み変更 = 戦略信号特徴量の分布変更
   - ML特徴量として戦略信号を使用しているため、ML再学習が必須
2. ❌ **旧Phase 51.1にML再学習が含まれていない**
   - 設定だけ変更してもMLモデルが古い分布で学習済み
   - モデルドリフトが発生し、性能悪化の可能性
3. ✅ **Phase 51.2-51.8実施後に最適化する方が効率的**
   - 戦略削減（5→3-4）確定後にML再学習
   - 新アーキテクチャ導入後に全体最適化

**結論**: Phase 51.1（旧）をスキップし、**新アーキテクチャ（市場状況分類+動的戦略選択）**から開始

---

## 🏗️ 新アーキテクチャ: 市場状況分類+動的戦略選択

### アーキテクチャ概要

**問題認識**:
- 現在の**Strategy-Aware ML**（Phase 41.8）の課題:
  - 戦略とMLの独立性喪失（戦略信号がML特徴量化）
  - 戦略変更時にML再学習必須（柔軟性低下）
  - 過学習リスク（F1スコア0.338-0.409は中程度）
  - 循環依存の複雑性
- 市場の70-80%がレンジ相場だが、戦略配分がミスマッチ
  - レンジ型: 25%のみ（ATRBased）
  - トレンド型: 60%（MochipoyAlert + MultiTimeframe + ADXTrendStrength）

**新設計方針**:
```
市場データ（OHLCV）
    ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[市場状況分類器]（Market Regime Classifier）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ├ レンジ相場（70-80%） → レンジ特化戦略選択
    │   ├ 狭いレンジ（< 2%変動）
    │   ├ 通常レンジ（2-5%変動）
    │   └ 広いレンジ（5-10%変動）
    ├ トレンド相場（15-20%） → トレンド特化戦略選択
    │   ├ 上昇トレンド（ADX > 25）
    │   └ 下降トレンド（ADX > 25）
    └ 高ボラティリティ（5-10%） → 全戦略ディスエーブル（待機）
    ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[動的戦略選択]（Dynamic Strategy Selection）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ├ レンジ相場 → ATRBased(70%) + DonchianReversal(30%)
    ├ トレンド相場 → MultiTimeframe(60%) + Mochipoy(40%)
    └ 高ボラティリティ → 待機（エントリーしない）
    ↓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[選択された戦略実行]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ↓ 戦略シグナル
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[ML予測]（市場状況特徴量も学習）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ↓ ML信頼度
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[最終統合]（Phase 29.5ロジック継続）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    └ 戦略 + ML → エントリー判断
```

**レンジ型bot最適化の特徴**:
1. ✅ **レンジ相場明示的検知**: BB幅・Donchian幅・ADX < 20で判定
2. ✅ **レンジ特化戦略自動選択**: ATRBased・DonchianReversal重視
3. ✅ **フォールスブレイクアウト回避**: 高ボラ時は待機
4. ✅ **解釈性最高**: なぜこの判断か明確（市場状況 → 戦略選択 → 判断）
5. ✅ **保守性向上**: 市場状況別に管理・デバッグ容易

**RR比0.67:1との適合性**:
- レンジ型戦略の最適RR比: 0.5:1 〜 1:1
- 現在設定（TP 1.0% / SL 1.5%）: 完璧に適合 ✅
- レンジ相場で60-70%勝率を目指す

**期待効果**: +20-30%（レンジ相場での大幅改善）

---

## 実装タスク

## Phase 51: レンジ型最適化・市場レジーム分類システム（進行中）

**実装期間**: 2025年11月2日〜
**ステータス**: Phase 51.1-51.5-A完了 ✅ / Phase 51.5-B以降 ⏸未実装
**詳細履歴**: [Phase_51.md](../開発履歴/Phase_51.md), [Phase_51.5-51.X.md](../開発履歴/Phase_51.5-51.X.md)

### ✅ 完了済みサブフェーズ（Phase 51.1-51.5-A）

| サブフェーズ | 完了日 | 主要成果 |
|------------|--------|---------|
| Phase 51.1-New | 11/02 | RegimeType Enum実装・15テスト |
| Phase 51.2-New | 11/02 | MarketRegimeClassifier実装・29テスト |
| Phase 51.2-Fix | 11/02 | high_volatility閾値修正（3.0% → 1.8%） |
| Phase 51.3-New | 11/02 | 動的戦略選択システム・22テスト |
| Phase 51.3-Fix | 11/02 | 戦略重み合計バグ修正 |
| Phase 51.4-Day1-3 | 11/02 | 戦略分析・削除候補特定（MochipoyAlert/MultiTimeframe）・36テスト |
| Phase 51.5-A | 11/03 | 戦略削除実行・27ファイル修正・60特徴量固定・1095テスト100%成功 |

**成果**:
- 市場レジーム分類システム実装完了
- 戦略削減実行完了（5→3戦略）
- 特徴量数固定（62→60特徴量）
- 合計1095テスト・カバレッジ66.31%

---

### ⏸ 未実装サブフェーズ（Phase 51.5-B〜51.11）

#### ✅ Phase 51.5-A: 戦略削除実行完了（2025/11/03完了）

**目的**: MochipoyAlert・MultiTimeframe削除により5戦略から3戦略へ削減

**実施内容**:
- 物理削除: MochipoyAlertStrategy・MultiTimeframeStrategy
- 戦略数削減: 5 → 3 (ATRBased, DonchianChannel, ADXTrendStrength)
- 特徴量数削減: 62 → 60 (戦略シグナル 5→3)
- 修正ファイル数: 27ファイル

**品質保証結果**:
- ✅ 全1095テスト成功
- ✅ カバレッジ66.31% (65%を上回る)
- ✅ システム整合性check: 7項目・誤差0件
- ✅ 特徴量数整合性: 60特徴量
- ✅ 戦略数整合性: 3戦略

**詳細**: `docs/開発履歴/Phase_51.5-51.X.md` 参照

---

#### Phase 51.5-B: 動的戦略管理基盤実装（4.5日）⭐⭐⭐⭐⭐ 次回実装推奨

**目的**: 設定ファイル主導の動的戦略管理システム構築

**背景**:
- Phase 51.5-Aで戦略削除に27ファイル修正が必要だった
- ハードコードされた戦略登録・設定が原因
- 戦略追加・削除の影響範囲を93%削減する設計が必要

**実装内容**:
1. **StrategyRegistry実装** (Registry pattern + decorator)
   - 戦略自動登録機構
   - @decoratorによる宣言的登録
2. **strategies.yaml作成** (新規設定ファイル)
   - 戦略定義・enabled切り替え
   - type・class・module・indicators設定
3. **StrategyLoader実装** (Facade pattern)
   - strategies.yaml読み込み
   - 動的インスタンス化
4. **既存戦略へdecorator適用**
   - ATRBased, DonchianChannel, ADXTrendStrength
5. **orchestrator.py統合**
   - ハードコード削除・動的読み込みへ移行
6. **テスト実装・検証**
   - 後方互換性確認
   - 品質保証 (checks.sh実行)

**期待効果**:
- 修正ファイル数: 27 → 4 (93%削減)
- 設定ファイル変更のみで戦略追加・削除可能
- コード変更最小化・保守性大幅向上

**実装期間**: 4.5日

**詳細**: `docs/開発履歴/Phase_51.5-51.X.md` Phase 51.5-B参照

---

#### Phase 51.5-C: レガシーコード完全調査（1-2日）⭐⭐⭐⭐ 次回実装

**目的**: Phase 51.5-A完了後も残存している可能性のある5戦略・62特徴量・70特徴量の参照を完全調査

**背景**:
- Phase 51.5-Aで2回に分けて詳細調査・置き換え・削除を実施
- まだどこかのコードに残存している可能性があるため完全調査が必要

**調査項目**:
1. **5戦略参照調査**
   - MochipoyAlert文字列検索
   - MultiTimeframe文字列検索
   - 戦略リスト長さ5のハードコード検索
   - ドキュメント内の5戦略言及箇所

2. **62特徴量参照調査**
   - "62" 数値リテラル検索 (特徴量コンテキスト)
   - feature_count: 62 検索
   - assert文での62検索
   - コメント内の62特徴量言及

3. **70特徴量参照調査** (Phase 50.9外部API削除後の残存)
   - "70" 数値リテラル検索 (特徴量コンテキスト)
   - external_api文字列検索
   - Level 1 / full_with_external検索
   - ドキュメント内の70特徴量言及

4. **ドキュメント完全更新**
   - README.md
   - CLAUDE.md
   - docs/開発履歴/*.md
   - docs/開発計画/*.md

**実行コマンド**:
```bash
# 5戦略調査
grep -r "MochipoyAlert" src/ tests/ config/ docs/ scripts/
grep -r "MultiTimeframe" src/ tests/ config/ docs/ scripts/
grep -rn "== 5\|len.*5" tests/ --include="*.py" | grep -i "strateg"

# 62特徴量調査
grep -rn "62" src/ tests/ config/ --include="*.py" --include="*.json" --include="*.yaml" | grep -i "feature"

# 70特徴量調査
grep -rn "70" src/ tests/ config/ docs/ --include="*.py" --include="*.json" --include="*.yaml" --include="*.md" | grep -i "feature"
grep -r "external_api" src/ tests/ config/ docs/
grep -r "full_with_external\|level1\|Level 1" src/ tests/ config/ docs/
```

**期待成果**:
- 完全なレガシーコード削除確認
- ドキュメント整合性100%達成
- システムクリーン性確保

**詳細**: `docs/開発履歴/Phase_51.5-51.X.md` Phase 51.5-C参照

---

#### Phase 51.6: 新戦略実装 + 初期テスト（3-4日）⭐⭐⭐⭐

**実装内容**:
1. 新戦略2つ実装（SignalBuilderパターン準拠）
2. ユニットテスト実装（各15テスト・合計30テスト）
3. バックテスト初期検証（単独勝率55%以上確認）
4. レジーム別適性確認

**品質基準**: 新戦略基本動作確認完了・30テスト追加

---

#### Phase 51.7: レジーム別戦略重み最適化（2-3日）⭐⭐⭐⭐⭐

**実装内容**:
1. thresholds.yaml更新（5戦略対応）
   - tight_range: range型3戦略
   - normal_range: range型3 + trend型1
   - trending: trend型2戦略
   - high_volatility: 全無効化
2. DynamicStrategySelector統合
3. レジームカバレッジ分析（5戦略版）

**品質基準**: レジーム別重み設定完了・統合テスト全成功

---

#### Phase 51.8: ML統合最適化（レジーム別）（3-4日）⭐⭐⭐⭐⭐

**実装内容**:
1. レジーム別ML信頼度閾値調整
   - tight_range: 戦略重視（ML補完控えめ）
   - trending: ML補完重視
2. 70特徴量対応確認（62基本 + 5戦略 + 3時間的）
3. Strategy-Aware ML維持

**品質基準**: レジーム別ML最適化完了・ML統合率100%維持

---

#### Phase 51.9: バックテスト検証（2-3日）⭐⭐⭐⭐

**実装内容**:
1. 180日間バックテスト実行（Phase 51版 vs Phase 50版）
2. 性能メトリクス測定（シャープレシオ・勝率・最大DD・総損益）
3. matplotlib可視化（エクイティカーブ・レジーム別損益・相関ヒートマップ）
4. 性能基準確認（レンジ相場収益率+20-30%向上・最大DD悪化10%以内）

---

#### Phase 51.10: ペーパートレード検証（1週間）⭐⭐⭐⭐

**実装内容**:
1. features.yaml設定（dynamic_strategy_selection.enabled: true）
2. ペーパーモード実行（7日間・レジーム遷移動作確認）
3. 実取引シミュレーション結果分析

---

#### Phase 51.11: 本番展開（1日）⭐⭐⭐⭐⭐

**実装内容**:
1. GCP Cloud Run展開
2. 本番動作確認（24時間ログ監視）
3. Phase 51完了宣言（CLAUDE.md・Phase_51.md更新）

---

### 📊 Phase 51全体設計

**目的**: レンジ型bot最適化・市場レジーム分類システム導入

**期待効果**:
- レンジ相場での収益率+20-30%向上
- 市場レジーム連動の最適戦略選択実現
- バランスの取れた戦略構成（range型3・trend型2）
- システムシンプル化・保守性向上

**実装済み** (Phase 51.1-51.4):
- 市場レジーム分類システム（MarketRegimeClassifier）
- 動的戦略選択システム（DynamicStrategySelector）
- 戦略個別パフォーマンス分析システム
- 削除候補2戦略特定（MochipoyAlert・MultiTimeframe）

**未実装** (Phase 51.5-B〜51.11):
- Phase 51.5-B: 動的戦略管理基盤実装（Registry pattern + strategies.yaml）
- Phase 51.5-C: レガシーコード完全調査（5戦略・62特徴量・70特徴量参照）
- Phase 51.6: 新戦略2つ追加（レンジ型1・トレンド型1）
- Phase 51.7: レジーム別戦略重み最適化（5戦略対応）
- Phase 51.8: ML統合最適化（レジーム別）
- Phase 51.9-51.11: バックテスト検証・ペーパートレード検証・本番展開

**次回セッション開始方法**:
```bash
cd /Users/nao/Desktop/bot

# Phase 51.5-B開始（動的戦略管理基盤実装）
# StrategyRegistry・strategies.yaml・StrategyLoader実装

# Phase 51.5-C開始（レガシーコード完全調査）
grep -r "MochipoyAlert" src/ tests/ config/ docs/ scripts/
grep -r "MultiTimeframe" src/ tests/ config/ docs/ scripts/
grep -rn "62" src/ tests/ config/ --include="*.py" --include="*.json" | grep -i "feature"
grep -rn "70" src/ tests/ config/ docs/ --include="*.py" --include="*.json" | grep -i "feature"
```

---

## Phase 52期待効果

- **エントリー頻度**: +200%（4回/時間 → 12回/時間）
- **RR比改善**: +124-155%（0.67:1 → 1.50-1.71:1）
- **必要勝率低下**: 60% → 37-40%（-20-23pp）
- **TP到達時間短縮**: 2.1時間 → 1.5-2.2時間（-29-50%）
- **収益率向上**: +15-25%（バックテスト目標）
- **Phase 51+52複合効果**: +35-50%総合収益改善

## リスクと対策

**リスク**:
- 5分足ノイズ増加（誤検知率上昇）
- API呼び出し頻度3倍増加（コスト懸念）
- SL設定が攻撃的（tight_range: 0.7%）

**対策**:
- ノイズフィルタリング強化（Phase 52.1・52.3）
- キャッシュ戦略でAPI呼び出し削減（Phase 52.1）
- バックテストで十分な検証（Phase 52.5）
- ペーパートレード1週間検証（Phase 52.6）
- features.yamlでオン・オフ切り替え可能
- 段階的ライブ適用（Phase 52.7）
- 安全マージン確保（6.6-11.4x）でリスク管理

---

# 🔧 Phase 53: 特徴量拡張・継続的改善（Phase 52完了後）【継続的】

## 目的

**問題**: 62特徴量で固定・市場変化への適応不足
**解決**: 継続的に特徴量を追加・評価・モデル性能監視
**期待効果**: ML精度継続向上・市場変化への適応・長期安定運用

## 実装タスク

### Phase 53.1: オンチェーン指標追加（3-4日）

**実装内容**:
- [ ] ファンディングレート: 先物プレミアム
- [ ] 建玉比率（ロング/ショート比率）: 市場センチメント
- [ ] アクティブアドレス数: ネットワーク活性度
- [ ] 流動性指標: 取引所残高推移
- [ ] 5-10特徴量追加

**データソース**:
- CryptoQuant API
- Glassnode API
- 無料枠で取得可能なデータ優先

**品質基準**:
- データ品質確認
- 欠損値処理実装
- バックテストで効果検証
- **GCP環境での安定性確認**（Phase 50.9教訓反映）

### Phase 53.2: 特徴量選択・最適化（2-3日）【Phase 51完了後実施】

**実装内容**:
- [ ] **ミューチュアルインフォメーション分析**
- [ ] **逐次特徴量削減**（Recursive Feature Elimination）
- [ ] 相関分析・冗長性排除
- [ ] L1正則化による特徴量選択
- [ ] 最適特徴量セット決定（過学習防止）

**実装例**:
```python
from sklearn.feature_selection import mutual_info_classif, RFE
from sklearn.linear_model import LassoCV

# ミューチュアルインフォメーション
mi_scores = mutual_info_classif(X, y)
top_features = select_top_k_features(mi_scores, k=60)

# 逐次特徴量削減
rfe = RFE(estimator=model, n_features_to_select=60)
selected_features = rfe.fit_transform(X, y)
```

**品質基準**:
- 特徴量数最適化（62 + N戦略 → 最適数）
- モデル精度維持または向上
- 過学習指標改善

**注**: Phase 51（戦略最適化）完了後に実施・戦略数削減（5→3-4）を反映した特徴量選択

### Phase 53.3: モデルドリフト検知システム（4-5日）

**実装内容**:
- [ ] **データ分布変化検出**
- [ ] **モデル性能劣化検知**
- [ ] 自動再学習トリガー実装
- [ ] 統計的モニタリング（Kolmogorov-Smirnov検定等）
- [ ] Discord通知統合

**実装例**:
```python
from scipy.stats import ks_2samp

# データ分布変化検出
train_distribution = X_train.mean(axis=0)
current_distribution = X_current.mean(axis=0)
statistic, p_value = ks_2samp(train_distribution, current_distribution)

if p_value < 0.05:
    trigger_retraining()
    send_discord_alert("Model drift detected")
```

**品質基準**:
- モデル劣化を1週間以内に検知
- 再学習の自動トリガー実装
- 誤検知率を低く保つ

### Phase 53.4: ABテスト・継続的評価フレームワーク（1週間）

**実装内容**:
- [ ] ABテスト実装（新旧戦略・特徴量比較）
- [ ] バックテスト自動評価
- [ ] 週次パフォーマンスレポート拡張
- [ ] シャープレシオ・ドローダウン監視強化
- [ ] 勝率・平均利益率トラッキング

**品質基準**:
- 自動化された評価プロセス
- 統計的有意性検定
- 可視化ダッシュボード

### Phase 53.5: 先進的手法研究（研究課題）

**研究対象**:
- [ ] RNN/LSTM: 時系列パターン学習
- [ ] CNN: 価格チャートパターン認識
- [ ] Transformer/Attention機構
- [ ] 強化学習（Reinforcement Learning）

**注意事項**:
- **小規模実験のみ**
- 複雑性・過学習リスク高い
- 効果検証後に本番導入判断
- 現在のGBDT系で十分な性能

**品質基準**:
- 実験環境での検証のみ
- 本番導入は慎重に判断
- KISS原則との両立確認

## Phase 53期待効果

- **継続的ML精度向上**: 市場変化への適応
- **モデル安定性向上**: ドリフト検知・自動再学習
- **長期安定運用**: 市場変化への自動対応

## リスクと対策

**リスク**:
- 複雑化による保守性低下
- 過学習リスク増加
- **外部依存リスク**（Phase 50.9教訓反映）

**対策**:
- 各追加機能をfeatures.yamlでトグル管理
- KISS原則チェックを徹底
- 効果不十分なら削除も検討
- **GCP環境での安定性を必須要件化**

---

# 🌐 Phase 53.6: マルチアセット対応（2-3週間）【Phase 53完了後・優先度低】

## 目的

**問題**: BTC/JPY専用
**解決**: ETH/JPY・XRP/JPY・海外アルトコイン対応
**期待効果**: 収益機会+30-50%拡大

**注**: BTC/JPY専用を先に極める・Phase 53完了後に実施判断

## 実装タスク

### Phase 53.6.1: アセット抽象化（3-4日）
- [ ] AssetConfigクラス実装
- [ ] unified.yaml拡張
- [ ] 資産別パラメータ管理

### Phase 53.6.2: bitbank ETH/JPY対応（3-4日）
- [ ] ETH/JPY API対応
- [ ] ETH-BTC相関係数特徴量追加
- [ ] 流動性確認

### Phase 53.6.3: bitbank XRP/JPY対応（3-4日）
- [ ] XRP/JPY API対応
- [ ] XRP-BTC相関係数特徴量追加
- [ ] 流動性確認

### Phase 53.6.4: 海外CEX/DEXマイナーアルトコイン対応（4-5日）
- [ ] 候補資産選定（SOL・AVAX・MATIC・LINK）
- [ ] BTC相関分析（相関係数0.3未満推奨）
- [ ] Binance/Uniswap API統合
- [ ] 法規制確認

### Phase 53.6.5: ポートフォリオ最適化（4-5日）
- [ ] PortfolioOptimizer実装
- [ ] Kelly基準ベース資金配分
- [ ] 相関係数考慮リスク分散

### Phase 53.6.6: 段階的ライブ適用（2-3週間）
- [ ] ペーパートレード検証（各資産1週間）
- [ ] 少額ライブ検証（各1万円・1週間）

## Phase 53.6期待効果

- **収益機会**: +30-50%拡大
- **リスク分散**: 相関係数考慮

## 実装判断基準

以下の条件を満たす場合のみ実装:
1. Phase 50.9-51-52-53でBTC/JPY精度が十分向上
2. システムが安定稼働（3ヶ月以上）
3. 資金規模が10万円以上
4. 流動性・法規制問題をクリア

---

# 📱 Phase 54: モバイル管理アプリ（PWA）（1-2週間）【運用改善】

## 目的

**問題**: 外出先でbotの停止・確認ができない
**解決**: スマホからbot制御可能なPWA実装
**期待効果**: 運用効率向上・緊急対応可能化

## 実装タスク

### Phase 54.1: 認証システム実装（2-3日）
- [ ] JWT認証実装
- [ ] 環境変数でパスワード管理
- [ ] Secret Manager統合

### Phase 54.2: REST API実装（2-3日）
- [ ] FastAPI実装
- [ ] エンドポイント: status/start/stop/balance/positions
- [ ] API認証・レート制限

### Phase 54.3: PWAフロントエンド実装（3-4日）
- [ ] HTML/CSS/JavaScript実装
- [ ] Material Design Lite使用
- [ ] レスポンシブデザイン
- [ ] オフライン対応

### Phase 54.4: Cloud Runデプロイ（1日）
- [ ] Dockerfile拡張
- [ ] HTTPSアクセス確認
- [ ] Cloud Run設定更新

### Phase 54.5: セキュリティ強化（1日）
- [ ] レート制限実装
- [ ] 監査ログ実装
- [ ] CORS設定

## Phase 54期待効果

- **運用効率**: 大幅向上
- **緊急対応**: 外出先から即座に停止可能
- **稼働率**: 99.9%達成

---

## 🎯 開発優先度まとめ

| 優先度 | Phase | 期間 | 効果 | リスク | 推奨 |
|--------|-------|------|------|--------|------|
| ⭐ 最優先 | **Phase 50.9** | 1-2日 | **システム安定化・シンプル設計回帰** | 低 | **即実施** |
| 🎯 最優先 | **Phase 51.1** | 1日 | **レンジ型戦略リバランス・勝率+5-10%** | 低 | **Phase 50.9直後** |
| 🎯 高優先 | Phase 51.2-51.6 | 1-2週間 | 戦略精度+10-20%・KISS原則達成 | 中 | Phase 51.1後実施 |
| 📈 性能向上 | Phase 52 | 1-2週間 | エントリー精度+8-15%（3軸マルチタイムフレーム） | 中 | Phase 51完了後実施 |
| 🔧 継続改善 | Phase 53 | 継続的 | ML精度継続向上・ドリフト検知 | 低 | Phase 52後継続実施 |
| 🌐 拡張 | Phase 53.6 | 2-3週間 | 収益機会+30-50% | 高 | **Phase 53後・条件付き実施** |
| 📱 運用改善 | Phase 54 | 1-2週間 | 運用効率向上 | 低 | 性能向上後実施 |

## 期待される効果

**Phase別効果**:
- **Phase 50.9単独**: システム安定化・シンプル設計回帰・保守性+20%
- **Phase 51.1単独**: レンジ型戦略リバランス・勝率+5-10%・エントリー機会+30-50%
- **Phase 51.2-51.6単独**: 戦略精度+10-20%・KISS原則達成（5→3-4戦略）
- **Phase 52単独**: エントリー精度+8-15%（3軸マルチタイムフレーム）

**複合効果**:
- **Phase 50.9+51.1**: システム安定化 + レンジ型最適化 → **即効性高い**
- **Phase 50.9+51全体**: +15-25%精度向上・シンプル設計達成
- **Phase 50.9+51+52**: +30-45%精度向上
- **Phase 50.9+51+52+53継続改善**: 長期的な精度向上維持・市場変化への適応

## 重要な設計原則

### KISS原則の徹底
- Phase 46の「デイトレード特化・シンプル設計回帰」方針を継続
- **Phase 50.9で外部API削除 → シンプル性回復**
- 複雑化する機能は慎重に検討
- 効果不十分なら削除も躊躇しない

### レンジ型戦略重視
- **Phase 51.1でレンジ型60%に重点配置**
- RR比0.67:1に最適化
- 「安定的な収益」目標に整合

### トレーリングストップについて
- **Phase 46で削除済み・再導入しない**
- デイトレード特化設計と相性が悪い
- シンプル性を優先

### マルチアセットについて
- **Phase 53完了後に実施**
- BTC/JPY専用を極めることを優先
- 実装判断は慎重に

---

**最終更新**: 2025年11月03日 - **Phase 51.5-A完了** ✅（戦略削除実行・27ファイル修正・60特徴量固定・1095テスト100%成功） → **Phase 51.5-B・Phase 51.5-C実装推奨** ⭐次回優先（動的戦略管理基盤93%削減 or レガシーコード完全調査）

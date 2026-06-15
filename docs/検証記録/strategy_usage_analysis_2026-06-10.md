# 戦略稼働分析: なぜ6戦略中3戦略がエントリーに使われないのか

**作成日**: 2026-06-10
**対象期間**: 2026-06-05 デプロイ（リビジョン `0605-2226`）後の約4日間（6/5〜6/9）
**種別**: 調査・分析のみ（**コード/設定変更なし**・取引挙動不変）

---

## 背景・目的

6/5 デプロイ後のライブ実績分析で、**6戦略のうち実エントリーに使われたのは3戦略のみ**だった:

- **稼働**: CMFReversal・ADXTrendStrength・BBReversal
- **不発（エントリー0件）**: ATRBased・StochasticReversal・MACDEMACrossover

「なぜ使われていないのか」を、ソースコード・GCPログ・Web業界知見の3手法で多角的に調査した。
現方針「2026年6月は様子見・7月初に実データで再判断」を尊重し、本調査では**設定変更を行わない**。

> **調査中のノイズについて（重要・無害確認済み）**: `gcloud logging read` の出力に bot ロガー由来の
> ANSI エスケープ（色コード）が大量混入（d9.txt で1638個）し、ターミナル表示が重複・乱れた。
> GCPログ本体・一時ファイル・ソースを全件検索した結果、不審な文字列やデータ汚染・プロンプトインジェクションは
> **一切存在しない**ことを確認（全件 count=0）。表示レイヤーのアーティファクトであり、取引システムへの影響はない。
> 教訓: 今後 `gcloud logging read` の結果は ANSI 除去（`re.sub(r'\x1b\[[0-9;]*m','',...)`）してから集計する。

---

## 実績データ（6/5デプロイ後の全6決済）

bitbank API の実約定を建玉単位でペアリングした結果:

| # | エントリー(JST) | 決済(JST) | 方向 | サイズ | ネット損益 | 結果 | 戦略 |
|---|----------------|-----------|------|--------|-----------|------|------|
| 1 | 06-05 04:30 | 06-05 05:10 | ロング | 0.015 | -1,997 | SL | 不明(ログ期限切れ) |
| 2 | 06-05 05:30+06:45 | 06-05 11:19 | ショート×2 | 0.03 | +1,504 | TP | 不明(ログ期限切れ) |
| 3 | 06-06 11:15 | 06-06 13:16 | ロング | 0.015 | -1,708 | SL | BBReversal |
| 4 | 06-06 19:00 | 06-07 10:18 | ロング | 0.015 | +1,347 | TP | ADXTrendStrength |
| 5 | 06-09 00:30 | 06-09 01:52 | ショート | 0.02 | +1,000 | TP | CMFReversal |
| 6 | 06-09 08:31 | 06-09 18:45 | ロング | 0.02 | -2,056 | SL | CMFReversal |

- **決済6件 / 勝率50%（TP3・SL3） / ネット約 -1,910円 / 実効RR 約0.78:1**
- RR比は以前の0.25:1から大幅改善（Phase 90γ-⑥/δ のTP/SL修正効果）。ただし勝率50%×RR0.78では薄赤字。
- 損益の約4割（手数料760円）はTaker約定由来。Maker化できていれば約-1,150円に縮小。

---

## 分析結論（2層構造）

### 層1: trending相場が64% → 全6戦略が停止（3戦略特有の理由ではない）

6/5-6/9の全445サイクル（trigger gating後の実評価）のレジーム分布:

| レジーム | サイクル数 | 比率 | 戦略の状態 |
|---------|-----------|------|-----------|
| **trending** | 287 | **64%** | 全6戦略 重み0.0（完全停止） |
| normal_range | 128 | 29% | レンジ型主体＋トレンド型に配分 |
| tight_range | 30 | 7% | レンジ型に集中 |

- trending時は CMF/BB/ADX も含め6戦略すべて停止するため、これは「3戦略だけ不発」の説明にはならない。
- trending判定（`src/core/services/market_regime_classifier.py:141-163`）:
  **ADX > 22 AND |EMA傾き| > 0.1%**。Phase 71 で tight判定より優先評価される。

### 層2（本質）: 残り36%のnormal/tight窓で、3戦略は発動条件が構造的に厳しくシグナル自体が出にくい

| 戦略 | 最も厳しい条件（ソース） | 低ボラ/レンジでの不発理由 |
|------|----------------------|------------------------|
| **ATRBased** | ATR消尽率≥70% + ADX<25 + BB帯端 の3条件同時（`src/strategies/implementations/atr_based.py`、`thresholds.yaml` exhaustion_threshold:0.70） | 低ボラ日は当日値幅がATR14の70%に届かず未達 |
| **StochasticReversal** | 乖離検出 + 価格変動≥0.5% + ADX<50 の4条件（`stochastic_reversal.py`、min_price_change_ratio:0.005） | 低ボラだと価格変動0.5%未満で「弱い乖離」として除外 |
| **MACDEMACrossover** | MACDクロス + EMA方向一致 + 出来高≥1.1（`macd_ema_crossover.py`、weight:0.05） | **トレンド型なのにtrending時は重み0、レンジ時は3条件が揃わない=構造的ジレンマ** |

対して稼働した3戦略は発動条件が緩い:
- **CMFReversal**: CMF<±0.10 + ADX≤28（単一主条件）
- **BBReversal**: BB位置帯端(<0.25/>0.75) + ADX<30（最も緩い）
- **ADXTrendStrength**: DIクロス / 強トレンド継続 / RSI逆張り の複数パターンで発動機会が多い

### 二次要因: 維持率拒否（Phase 50.4）はシグナル生成の「後」

- `src/trading/risk/manager.py:743-824` — シグナル生成後に維持率チェック。予測維持率<80%で拒否。
- ポジション保有中（同方向上限1件＋長時間保有あり。例: 6/6 19:00→6/7 10:18 で約15時間）は、
  normal窓でシグナルが出ても新規エントリーが拒否され、機会がさらに細る。
- 6/9 は60サイクル全てが取引拒否（うち維持率拒否が主因）でエントリー成功0件だった。

---

## Web業界知見による裏付け（出典つき）

| 観点 | 業界知見 | 主な出典 |
|------|---------|---------|
| ATR反転/平均回帰 | トレンド相場で機能せず停止が正解（レンジ60-70%の利益をトレンド30-40%が破壊し得る） | SetupAlpha |
| Stochastic乖離 | 強トレンド中は信頼性が低く、低ボラでは乖離が出にくい | LuxAlgo / StockCharts ChartSchool |
| MACD+EMAクロス | レンジ/低ボラで「だまし」60-70%、トレンドが必要 | LuxAlgo / Above The Green Line |
| マルチストラテジー | 一部だけ発動・他が長期不発は**レジーム適応設計では正常**（成功指標） | QuantConnect / Medium「Market Regimes」 |
| レンジ専用設計 | trending全停止は保守的だが妥当。業界標準は「全停止」より「重み調整」で、機会損失はある | QuantConnect / StatOasis |

主要URL:
- https://setupalpha.com/blogs/articles/mean-reversion-strategy-failures-complete-fix-guide
- https://www.luxalgo.com/blog/how-to-use-stochastic-in-trending-vs-ranging-markets/
- https://www.luxalgo.com/blog/macd-crossovers-in-trending-vs-ranging-markets/
- https://www.quantconnect.com/forum/discussion/14818/rage-against-the-regimes-the-illusion-of-market-specific-strategies-/
- https://medium.com/@ashimnandi07/market-regimes-adaptation-is-the-edge-b6c90504ca0f

---

## 総合評価

**「6戦略中3戦略が不発」は、概ね設計どおりの正常な挙動**である:
- trending64%で全停止＝レンジ専用設計（Phase 85）の意図どおり。
- 残り36%で ATR/Stochastic/MACD が不発なのは、各指標の性質（トレンド/高ボラを要求 or 低ボラで条件未達）と、
  発動条件の厳しさによる構造的なもの。Web知見もこれを「正常」と評価。
- ただし**機会損失は存在**し、エントリー数の細さ（4日で6決済）は薄赤字の一因。

---

## 未確定点（今回スコープ外）

- 「3戦略がnormal/tight窓でシグナルを出したが統合/MLで潰されたのか、そもそも出していないのか」は、
  本番が LOG_LEVEL=WARNING で DEBUG 抑制のため直接確認できない。
  **確証には `BACKTEST_MODE=true` のバックテスト（DEBUGログ）解析が必要**。
- 今回はユーザー選択により分析まとめのみ。確証バックテストは将来オプション。

## 参考: 将来の改善オプション（今回は実装しない・7月再判断時の検討材料）

- A. 現状維持（不発は設計どおり・正常と評価）
- B. trending判定閾値（ADX22）の見直しで normal窓 の量を調整
- C. 戦略別ADX閾値の整合（例: StochasticReversal の adx_max_threshold 50→30）
- D. trending時にレンジ反転戦略へ小重み付与（機会増だが「ナイフをつかむ」リスク）
- E. 発動条件の緩和（ATR消尽率70%引き下げ等。サンプル増だが質低下リスク）

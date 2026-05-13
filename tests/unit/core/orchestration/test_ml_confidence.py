"""Phase 87 C2/H10: ML信頼度ヘルパーのテスト"""

import numpy as np
import pytest

from src.core.orchestration.ml_confidence import get_predicted_class_proba


class TestGetPredictedClassProba:
    def test_2d_array_last_row(self):
        """2D配列なら最終行から predicted_class とその確率を返す"""
        probs = np.array([[0.1, 0.9], [0.7, 0.3]])
        cls, conf = get_predicted_class_proba(probs)
        assert cls == 0
        assert conf == pytest.approx(0.7)

    def test_1d_array(self):
        """1D配列はそのまま使用される"""
        probs = np.array([0.2, 0.8])
        cls, conf = get_predicted_class_proba(probs)
        assert cls == 1
        assert conf == pytest.approx(0.8)

    def test_3_class(self):
        probs = np.array([[0.1, 0.7, 0.2]])
        cls, conf = get_predicted_class_proba(probs)
        assert cls == 1
        assert conf == pytest.approx(0.7)

    def test_confidence_equals_max_in_well_formed_input(self):
        """確率分布が正常な場合 confidence == np.max とも一致する（数学的等価）"""
        probs = np.array([[0.25, 0.65, 0.10]])
        cls, conf = get_predicted_class_proba(probs)
        assert conf == pytest.approx(float(np.max(probs[-1])))
        assert cls == int(np.argmax(probs[-1]))

    def test_list_input_supported(self):
        """list を np.asarray でラップ可能"""
        probs = [[0.4, 0.6]]
        cls, conf = get_predicted_class_proba(probs)
        assert cls == 1
        assert conf == pytest.approx(0.6)

    def test_return_types(self):
        """戻り値は (int, float)"""
        probs = np.array([[0.3, 0.7]])
        cls, conf = get_predicted_class_proba(probs)
        assert isinstance(cls, int)
        assert isinstance(conf, float)


class TestEdgeCases:
    """Phase 87 R2: エッジケース（空配列・NaN・単一クラス）"""

    def test_empty_array_raises(self):
        """空配列を渡すと IndexError or ValueError が出る（未定義動作の明示化）。

        本来 ML パイプライン上は空配列は来ないが、保護として「サイレントに
        誤値を返すのではなく、確実に例外で異常を伝える」ことを保証する。
        """
        # ndim=1 で空 → 内部 last=空配列 → np.argmax で ValueError
        with pytest.raises((IndexError, ValueError)):
            get_predicted_class_proba(np.array([]))

    def test_nan_handling_returns_valid_types(self):
        """NaN を含む probabilities でも戻り値の型は (int, float) を保つ。

        np.argmax は NaN を比較不能と扱うが、確率値が NaN の場合 confidence
        も NaN になる。型としては float なので isinstance チェックは通る。
        ML 側で NaN を生成しない設計を維持する前提だが、保険的な検証。
        """
        probs = np.array([[0.3, np.nan]])
        cls, conf = get_predicted_class_proba(probs)
        # 型は維持される（NaN でもクラッシュしない）
        assert isinstance(cls, int)
        assert isinstance(conf, float)

    def test_single_class_probability(self):
        """1クラスのみ（n_classes=1）でも predicted_class=0, confidence=1.0 を返す"""
        probs = np.array([[1.0]])
        cls, conf = get_predicted_class_proba(probs)
        assert cls == 0
        assert conf == pytest.approx(1.0)

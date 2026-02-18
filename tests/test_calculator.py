"""
손해율 계산 모듈 단위 테스트

실행:
    pytest tests/
"""

import pytest
import pandas as pd

from src.calculator import (
    calculate_loss_ratio,
    calculate_combined_ratio,
    classify_loss_ratio,
    add_loss_ratio_columns,
    get_summary_stats,
)


class TestCalculateLossRatio:
    def test_normal_case(self):
        # 손해율 = 8000 / 10000 = 0.8 (80%)
        assert calculate_loss_ratio(8000, 10000) == pytest.approx(0.8)

    def test_below_threshold(self):
        # 60% — 양호 구간
        assert calculate_loss_ratio(6000, 10000) == pytest.approx(0.6)

    def test_above_100_percent(self):
        # 110% — 위험 구간 (보험사 손실)
        assert calculate_loss_ratio(11000, 10000) == pytest.approx(1.1)

    def test_zero_premium_raises(self):
        with pytest.raises(ValueError, match="수입보험료는 0보다 커야 합니다"):
            calculate_loss_ratio(5000, 0)

    def test_negative_premium_raises(self):
        with pytest.raises(ValueError):
            calculate_loss_ratio(5000, -1000)


class TestCalculateCombinedRatio:
    def test_combined_ratio(self):
        # 손해율 0.85 + 사업비율 0.20 = 합산비율 1.05
        assert calculate_combined_ratio(0.85, 0.20) == pytest.approx(1.05)

    def test_zero_expense(self):
        assert calculate_combined_ratio(0.75, 0.0) == pytest.approx(0.75)


class TestClassifyLossRatio:
    def test_good(self):
        assert classify_loss_ratio(0.79) == "양호"

    def test_boundary_good_to_caution(self):
        # 정확히 80%는 '주의'
        assert classify_loss_ratio(0.80) == "주의"

    def test_caution(self):
        assert classify_loss_ratio(0.95) == "주의"

    def test_boundary_caution_to_danger(self):
        # 정확히 100%는 '위험'
        assert classify_loss_ratio(1.00) == "위험"

    def test_danger(self):
        assert classify_loss_ratio(1.10) == "위험"


class TestAddLossRatioColumns:
    def _sample_df(self):
        return pd.DataFrame({
            "연도": [2022, 2023],
            "보험종류": ["실손의료보험", "암보험"],
            "수입보험료": [10000, 5000],
            "발생손해액": [8500, 4000],
        })

    def test_columns_added(self):
        result = add_loss_ratio_columns(self._sample_df())
        assert "손해율" in result.columns
        assert "손해율(%)" in result.columns
        assert "등급" in result.columns

    def test_values_correct(self):
        result = add_loss_ratio_columns(self._sample_df())
        assert result.loc[0, "손해율"] == pytest.approx(0.85)
        assert result.loc[0, "손해율(%)"] == pytest.approx(85.0)
        assert result.loc[0, "등급"] == "주의"

    def test_missing_column_raises(self):
        bad_df = pd.DataFrame({"연도": [2022], "수입보험료": [10000]})
        with pytest.raises(ValueError, match="필수 컬럼이 없습니다"):
            add_loss_ratio_columns(bad_df)

    def test_zero_premium_handled(self):
        df = pd.DataFrame({
            "수입보험료": [10000, 0],
            "발생손해액": [8000, 5000],
        })
        result = add_loss_ratio_columns(df)
        assert pd.isna(result.loc[1, "손해율"])


class TestGetSummaryStats:
    def test_summary_keys(self):
        df = pd.DataFrame({
            "수입보험료": [10000, 5000],
            "발생손해액": [8500, 4000],
            "손해율": [0.85, 0.80],
            "손해율(%)": [85.0, 80.0],
        })
        stats = get_summary_stats(df)
        assert "평균 손해율(%)" in stats
        assert "총 수입보험료" in stats
        assert "총 발생손해액" in stats

    def test_missing_column_raises(self):
        df = pd.DataFrame({"손해율": [0.8]})
        with pytest.raises(ValueError, match="컬럼이 없습니다"):
            get_summary_stats(df)

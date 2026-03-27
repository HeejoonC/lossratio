"""
손해율(Loss Ratio) 계산 모듈

손해율 = 발생손해액 / 수입보험료
- 발생손해액: 지급보험금 + 준비금 증감
- 수입보험료: 원수보험료 + 재보험료 수입 - 재보험료 지출

건강보험 손해율 해석 기준:
- 80% 미만: 양호
- 80~100%: 주의
- 100% 초과: 위험 (보험사 손실 발생)
"""

import pandas as pd


LOSS_RATIO_THRESHOLDS = {
    "양호": 0.80,    # 80% 미만: 양호
    "주의": 1.00,    # 80~100%: 주의
    # 100% 초과: 위험
}


def calculate_loss_ratio(incurred_losses: float, earned_premiums: float) -> float:
    """
    손해율을 계산합니다.

    손해율(Loss Ratio) = 발생손해액 / 수입보험료

    Args:
        incurred_losses: 발생손해액 (지급보험금 + 준비금 증감)
        earned_premiums: 수입보험료 (원수보험료 기준)

    Returns:
        손해율 (소수 형태, e.g. 0.85 = 85%)

    Raises:
        ValueError: 수입보험료가 0 이하인 경우
    """
    if earned_premiums <= 0:
        raise ValueError(f"수입보험료는 0보다 커야 합니다. 입력값: {earned_premiums}")
    return incurred_losses / earned_premiums


def calculate_combined_ratio(loss_ratio: float, expense_ratio: float) -> float:
    """
    합산비율(Combined Ratio)을 계산합니다.

    합산비율 = 손해율 + 사업비율

    Args:
        loss_ratio: 손해율 (소수 형태)
        expense_ratio: 사업비율 (소수 형태)

    Returns:
        합산비율 (소수 형태)
    """
    return loss_ratio + expense_ratio


def classify_loss_ratio(loss_ratio: float) -> str:
    """
    손해율 수준을 분류합니다.

    Args:
        loss_ratio: 손해율 (소수 형태, e.g. 0.85)

    Returns:
        "양호" / "주의" / "위험"
    """
    if loss_ratio < LOSS_RATIO_THRESHOLDS["양호"]:
        return "양호"
    elif loss_ratio < LOSS_RATIO_THRESHOLDS["주의"]:
        return "주의"
    else:
        return "위험"


def add_loss_ratio_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    DataFrame에 손해율 및 분류 컬럼을 추가합니다.

    필수 컬럼:
        - 발생손해액: 지급보험금 합계
        - 수입보험료: 수입 보험료 합계

    Args:
        df: 원본 데이터프레임

    Returns:
        손해율, 손해율(%), 등급 컬럼이 추가된 데이터프레임
    """
    required_cols = {"발생손해액", "수입보험료"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"필수 컬럼이 없습니다: {missing}")

    result = df.copy()
    result["손해율"] = result.apply(
        lambda row: calculate_loss_ratio(row["발생손해액"], row["수입보험료"])
        if row["수입보험료"] > 0 else None,
        axis=1,
    )
    result["손해율(%)"] = result["손해율"] * 100
    result["등급"] = result["손해율"].apply(
        lambda x: classify_loss_ratio(x) if pd.notna(x) else None
    )
    return result


def get_summary_stats(df: pd.DataFrame) -> dict:
    """
    손해율 요약 통계를 반환합니다.

    Args:
        df: 손해율 컬럼이 포함된 데이터프레임

    Returns:
        평균, 최대, 최소, 중앙값 등 요약 딕셔너리
    """
    if "손해율(%)" not in df.columns:
        raise ValueError("손해율(%) 컬럼이 없습니다. add_loss_ratio_columns()를 먼저 호출하세요.")

    series = df["손해율(%)"].dropna()
    return {
        "평균 손해율(%)": round(series.mean(), 2),
        "최대 손해율(%)": round(series.max(), 2),
        "최소 손해율(%)": round(series.min(), 2),
        "중앙값(%)": round(series.median(), 2),
        "총 수입보험료": int(df["수입보험료"].sum()),
        "총 발생손해액": int(df["발생손해액"].sum()),
    }

"""
건강보험 데이터 로딩 모듈

지원하는 데이터 소스:
1. 샘플 데이터 (기본 제공)
2. CSV / Excel 파일 업로드
3. 공공데이터포털 API (data.go.kr) — API 키 필요

공공데이터포털 주요 건강보험 데이터셋:
- 건강보험심사평가원_진료비 통계 지표
- 국민건강보험공단_건강보험 주요통계
"""

import io
import os
from pathlib import Path

import pandas as pd
import requests


SAMPLE_DATA_PATH = Path(__file__).parent.parent / "data" / "sample_data.csv"

# 공공데이터포털 API 기본 URL (건강보험심사평가원 진료비 통계)
PUBLIC_DATA_BASE_URL = "https://apis.data.go.kr/B551182/msInsuHospInfoService"


def load_sample_data() -> pd.DataFrame:
    """
    내장 샘플 데이터를 불러옵니다.

    Returns:
        건강보험 손해율 샘플 데이터프레임
    """
    if not SAMPLE_DATA_PATH.exists():
        raise FileNotFoundError(f"샘플 데이터 파일을 찾을 수 없습니다: {SAMPLE_DATA_PATH}")
    return pd.read_csv(SAMPLE_DATA_PATH, encoding="utf-8-sig")


def load_from_upload(uploaded_file) -> pd.DataFrame:
    """
    Streamlit UploadedFile 객체에서 데이터를 불러옵니다.

    지원 형식: CSV, Excel (.xlsx, .xls)

    Args:
        uploaded_file: st.file_uploader()가 반환하는 파일 객체

    Returns:
        파싱된 데이터프레임
    """
    filename = uploaded_file.name.lower()
    if filename.endswith(".csv"):
        # 한국어 파일의 인코딩을 순서대로 시도
        for encoding in ("utf-8-sig", "euc-kr", "cp949"):
            try:
                content = uploaded_file.read()
                return pd.read_csv(io.BytesIO(content), encoding=encoding)
            except UnicodeDecodeError:
                uploaded_file.seek(0)
        raise ValueError("CSV 파일 인코딩을 인식할 수 없습니다. (UTF-8 또는 EUC-KR 권장)")
    elif filename.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file)
    else:
        raise ValueError(f"지원하지 않는 파일 형식입니다: {uploaded_file.name}")


def load_from_public_api(api_key: str, year: int | None = None) -> pd.DataFrame:
    """
    공공데이터포털 API에서 건강보험 통계를 불러옵니다.

    data.go.kr에서 발급받은 API 키가 필요합니다.
    환경변수 PUBLIC_DATA_API_KEY 또는 .env 파일에서 읽어옵니다.

    Args:
        api_key: 공공데이터포털 인증키
        year: 조회 연도 (None이면 전체)

    Returns:
        API 응답을 파싱한 데이터프레임
    """
    params = {
        "serviceKey": api_key,
        "pageNo": 1,
        "numOfRows": 1000,
        "type": "json",
    }
    if year:
        params["year"] = year

    try:
        response = requests.get(PUBLIC_DATA_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
        if not items:
            raise ValueError("API 응답에 데이터가 없습니다.")
        return pd.DataFrame(items)
    except requests.RequestException as e:
        raise ConnectionError(f"공공데이터포털 API 호출 실패: {e}") from e


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    다양한 소스에서 온 데이터프레임의 컬럼명을 표준 형식으로 변환합니다.

    표준 컬럼:
        - 연도: 기준 연도
        - 보험종류: 건강보험 세부 분류
        - 수입보험료: 수입 보험료 합계 (단위: 백만원)
        - 발생손해액: 발생손해액 합계 (단위: 백만원)

    Args:
        df: 원본 데이터프레임

    Returns:
        컬럼명이 표준화된 데이터프레임
    """
    rename_map = {
        # 영문 컬럼명 매핑
        "year": "연도",
        "insurance_type": "보험종류",
        "earned_premium": "수입보험료",
        "incurred_loss": "발생손해액",
        # 공공데이터포털 컬럼명 매핑 (데이터셋에 따라 조정 필요)
        "prmamnt": "수입보험료",
        "lossamnt": "발생손해액",
        "insuKindNm": "보험종류",
        "stadYyyy": "연도",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # 숫자형 컬럼 변환
    for col in ["수입보험료", "발생손해액"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")

    return df

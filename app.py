"""
건강보험 손해율 분석 대시보드

실행 방법:
    streamlit run app.py

데이터 소스:
    - 샘플 데이터: data/sample_data.csv (기본)
    - 파일 업로드: CSV / Excel (사이드바에서 업로드)
    - 공공데이터포털 API: .env 파일에 PUBLIC_DATA_API_KEY 설정 필요
"""

import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from src.calculator import add_loss_ratio_columns, get_summary_stats
from src.data_loader import load_from_upload, load_sample_data, normalize_columns

load_dotenv()

st.set_page_config(
    page_title="건강보험 손해율 분석",
    page_icon="📊",
    layout="wide",
)

# ── 색상 팔레트 (등급별) ──────────────────────────────────────────────────────
GRADE_COLORS = {"양호": "#2ecc71", "주의": "#f39c12", "위험": "#e74c3c"}


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def badge(grade: str) -> str:
    """등급에 맞는 색상 배지 HTML을 반환합니다."""
    color = GRADE_COLORS.get(grade, "#95a5a6")
    return f'<span style="background:{color};color:#fff;padding:2px 10px;border-radius:12px;font-weight:bold;">{grade}</span>'


@st.cache_data
def load_and_process(source: str, uploaded_file=None) -> pd.DataFrame:
    """데이터를 로드하고 손해율 컬럼을 추가합니다."""
    if source == "sample":
        df = load_sample_data()
    elif source == "upload" and uploaded_file is not None:
        df = load_from_upload(uploaded_file)
    else:
        return pd.DataFrame()

    df = normalize_columns(df)
    df = add_loss_ratio_columns(df)
    return df


# ── 사이드바 ──────────────────────────────────────────────────────────────────

st.sidebar.title("⚙️ 설정")
st.sidebar.markdown("---")

data_source = st.sidebar.radio(
    "데이터 소스",
    options=["샘플 데이터", "파일 업로드"],
    index=0,
)

uploaded_file = None
if data_source == "파일 업로드":
    uploaded_file = st.sidebar.file_uploader(
        "CSV 또는 Excel 파일 업로드",
        type=["csv", "xlsx", "xls"],
        help="필수 컬럼: 연도, 보험종류, 수입보험료, 발생손해액",
    )

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
**컬럼 형식 안내**
| 컬럼 | 설명 |
|------|------|
| 연도 | 기준 연도 |
| 보험종류 | 상품 분류 |
| 지역 | 시도 (선택) |
| 수입보험료 | 단위: 백만원 |
| 발생손해액 | 단위: 백만원 |

**손해율 등급 기준**
- 🟢 양호: 80% 미만
- 🟡 주의: 80~100%
- 🔴 위험: 100% 초과
"""
)

# ── 데이터 로드 ───────────────────────────────────────────────────────────────

source_key = "sample" if data_source == "샘플 데이터" else "upload"

try:
    df = load_and_process(source_key, uploaded_file)
except Exception as e:
    st.error(f"데이터 로드 실패: {e}")
    st.stop()

if df.empty:
    st.info("사이드바에서 파일을 업로드하거나 샘플 데이터를 선택하세요.")
    st.stop()

# ── 필터 ─────────────────────────────────────────────────────────────────────

col_f1, col_f2, col_f3 = st.columns(3)

years = sorted(df["연도"].dropna().unique().tolist())
insurance_types = sorted(df["보험종류"].dropna().unique().tolist())

with col_f1:
    selected_years = st.multiselect("연도 필터", options=years, default=years)
with col_f2:
    selected_types = st.multiselect("보험종류 필터", options=insurance_types, default=insurance_types)
with col_f3:
    if "지역" in df.columns:
        regions = sorted(df["지역"].dropna().unique().tolist())
        selected_regions = st.multiselect("지역 필터", options=regions, default=regions)
    else:
        selected_regions = None

filtered = df[df["연도"].isin(selected_years) & df["보험종류"].isin(selected_types)]
if selected_regions and "지역" in filtered.columns:
    filtered = filtered[filtered["지역"].isin(selected_regions)]

if filtered.empty:
    st.warning("선택한 필터에 해당하는 데이터가 없습니다.")
    st.stop()

# ── 헤더 ─────────────────────────────────────────────────────────────────────

st.title("📊 건강보험 손해율 분석 대시보드")
st.caption(f"데이터 기준: {min(selected_years)}~{max(selected_years)}년 | {len(filtered):,}개 레코드")

# ── KPI 카드 ─────────────────────────────────────────────────────────────────

stats = get_summary_stats(filtered)
overall_loss_ratio = stats["총 발생손해액"] / stats["총 수입보험료"] * 100

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("전체 손해율", f"{overall_loss_ratio:.1f}%")
kpi2.metric("평균 손해율", f"{stats['평균 손해율(%)']:.1f}%")
kpi3.metric("총 수입보험료", f"{stats['총 수입보험료']:,.0f}백만원")
kpi4.metric("총 발생손해액", f"{stats['총 발생손해액']:,.0f}백만원")

st.markdown("---")

# ── 차트 행 1: 연도별 추이 + 보험종류별 비교 ─────────────────────────────────

chart1, chart2 = st.columns(2)

with chart1:
    st.subheader("연도별 손해율 추이")
    trend = (
        filtered.groupby(["연도", "보험종류"])
        .apply(lambda g: g["발생손해액"].sum() / g["수입보험료"].sum() * 100, include_groups=False)
        .reset_index(name="손해율(%)")
    )
    fig_trend = px.line(
        trend,
        x="연도",
        y="손해율(%)",
        color="보험종류",
        markers=True,
        title="보험종류별 손해율 연도 추이",
    )
    fig_trend.add_hline(y=80, line_dash="dot", line_color="#f39c12", annotation_text="주의(80%)")
    fig_trend.add_hline(y=100, line_dash="dot", line_color="#e74c3c", annotation_text="위험(100%)")
    fig_trend.update_layout(yaxis_ticksuffix="%", legend_title="보험종류")
    st.plotly_chart(fig_trend, use_container_width=True)

with chart2:
    st.subheader("보험종류별 손해율 분포")
    box_data = filtered.copy()
    fig_box = px.box(
        box_data,
        x="보험종류",
        y="손해율(%)",
        color="보험종류",
        title="보험종류별 손해율 분포 (박스플롯)",
        points="all",
    )
    fig_box.add_hline(y=80, line_dash="dot", line_color="#f39c12")
    fig_box.add_hline(y=100, line_dash="dot", line_color="#e74c3c")
    fig_box.update_layout(yaxis_ticksuffix="%", showlegend=False)
    st.plotly_chart(fig_box, use_container_width=True)

# ── 차트 행 2: 지역별 히트맵 + 등급 분포 ───────────────────────────────────

chart3, chart4 = st.columns(2)

with chart3:
    if "지역" in filtered.columns:
        st.subheader("지역별 평균 손해율")
        region_data = (
            filtered.groupby("지역")
            .apply(lambda g: g["발생손해액"].sum() / g["수입보험료"].sum() * 100, include_groups=False)
            .reset_index(name="손해율(%)")
            .sort_values("손해율(%)", ascending=True)
        )
        fig_region = px.bar(
            region_data,
            x="손해율(%)",
            y="지역",
            orientation="h",
            title="지역별 평균 손해율",
            color="손해율(%)",
            color_continuous_scale=["#2ecc71", "#f39c12", "#e74c3c"],
            range_color=[60, 110],
        )
        fig_region.add_vline(x=80, line_dash="dot", line_color="#f39c12")
        fig_region.add_vline(x=100, line_dash="dot", line_color="#e74c3c")
        fig_region.update_layout(xaxis_ticksuffix="%", coloraxis_showscale=False)
        st.plotly_chart(fig_region, use_container_width=True)
    else:
        st.subheader("연도별 보험료 vs 손해액")
        bar_data = filtered.groupby("연도")[["수입보험료", "발생손해액"]].sum().reset_index()
        fig_bar = px.bar(
            bar_data.melt(id_vars="연도", var_name="항목", value_name="금액"),
            x="연도",
            y="금액",
            color="항목",
            barmode="group",
            title="연도별 수입보험료 vs 발생손해액",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

with chart4:
    st.subheader("등급별 데이터 분포")
    grade_counts = filtered["등급"].value_counts().reset_index()
    grade_counts.columns = ["등급", "건수"]
    grade_counts["색상"] = grade_counts["등급"].map(GRADE_COLORS)
    fig_pie = px.pie(
        grade_counts,
        names="등급",
        values="건수",
        title="손해율 등급 분포",
        color="등급",
        color_discrete_map=GRADE_COLORS,
    )
    st.plotly_chart(fig_pie, use_container_width=True)

# ── 상세 데이터 테이블 ────────────────────────────────────────────────────────

st.markdown("---")
st.subheader("상세 데이터")

display_cols = ["연도", "보험종류"]
if "지역" in filtered.columns:
    display_cols.append("지역")
display_cols += ["수입보험료", "발생손해액", "손해율(%)", "등급"]

table = filtered[display_cols].copy()
table["손해율(%)"] = table["손해율(%)"].round(1)
table["수입보험료"] = table["수입보험료"].map("{:,.0f}".format)
table["발생손해액"] = table["발생손해액"].map("{:,.0f}".format)

st.dataframe(
    table.sort_values(["연도", "보험종류"]).reset_index(drop=True),
    use_container_width=True,
    height=400,
)

# ── 데이터 다운로드 ───────────────────────────────────────────────────────────

csv_data = filtered[display_cols].to_csv(index=False, encoding="utf-8-sig")
st.download_button(
    label="CSV 다운로드",
    data=csv_data,
    file_name="손해율_분석결과.csv",
    mime="text/csv",
)

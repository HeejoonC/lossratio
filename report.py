"""
건강보험 손해율 분석 보고서 생성기

샘플 데이터 또는 지정한 CSV 파일을 읽어
단일 HTML 파일로 인터랙티브 보고서를 출력합니다.

실행 방법:
    # 샘플 데이터로 생성
    python report.py

    # 실제 데이터 파일 지정
    python report.py --input 실제데이터.csv --output 손해율보고서.html
"""

import argparse
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.calculator import add_loss_ratio_columns, get_summary_stats
from src.data_loader import load_sample_data, normalize_columns

GRADE_COLORS = {"양호": "#2ecc71", "주의": "#f39c12", "위험": "#e74c3c"}


def build_report(df: pd.DataFrame, title: str = "건강보험 손해율 분석 보고서") -> str:
    """데이터프레임을 받아 독립 실행형 HTML 보고서 문자열을 반환합니다."""

    # ── 지표 계산 ──────────────────────────────────────────────────────────────
    stats = get_summary_stats(df)
    overall_lr = stats["총 발생손해액"] / stats["총 수입보험료"] * 100
    report_date = date.today().strftime("%Y년 %m월 %d일")

    # ── 차트 1: 연도별 손해율 추이 ─────────────────────────────────────────────
    trend = (
        df.groupby(["연도", "보험종류"])
        .apply(
            lambda g: g["발생손해액"].sum() / g["수입보험료"].sum() * 100,
            include_groups=False,
        )
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
    fig_trend.update_layout(yaxis_ticksuffix="%")

    # ── 차트 2: 보험종류별 손해율 박스플롯 ────────────────────────────────────
    fig_box = px.box(
        df,
        x="보험종류",
        y="손해율(%)",
        color="보험종류",
        title="보험종류별 손해율 분포",
        points="all",
    )
    fig_box.add_hline(y=80, line_dash="dot", line_color="#f39c12")
    fig_box.add_hline(y=100, line_dash="dot", line_color="#e74c3c")
    fig_box.update_layout(yaxis_ticksuffix="%", showlegend=False)

    # ── 차트 3: 지역별 평균 손해율 ────────────────────────────────────────────
    if "지역" in df.columns:
        region_data = (
            df.groupby("지역")
            .apply(
                lambda g: g["발생손해액"].sum() / g["수입보험료"].sum() * 100,
                include_groups=False,
            )
            .reset_index(name="손해율(%)")
            .sort_values("손해율(%)")
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
    else:
        bar_data = df.groupby("연도")[["수입보험료", "발생손해액"]].sum().reset_index()
        fig_region = px.bar(
            bar_data.melt(id_vars="연도", var_name="항목", value_name="금액"),
            x="연도",
            y="금액",
            color="항목",
            barmode="group",
            title="연도별 수입보험료 vs 발생손해액",
        )

    # ── 차트 4: 등급 파이 ──────────────────────────────────────────────────────
    grade_counts = df["등급"].value_counts().reset_index()
    grade_counts.columns = ["등급", "건수"]
    fig_pie = px.pie(
        grade_counts,
        names="등급",
        values="건수",
        title="손해율 등급 분포",
        color="등급",
        color_discrete_map=GRADE_COLORS,
    )

    # ── HTML 조립 ──────────────────────────────────────────────────────────────
    # include_plotlyjs="cdn" 대신 "require" 없이 완전 내장 (망분리 대응)
    chart_kwargs = dict(full_html=False, include_plotlyjs=False)

    html_trend = fig_trend.to_html(**chart_kwargs)
    html_box = fig_box.to_html(**chart_kwargs)
    html_region = fig_region.to_html(**chart_kwargs)
    html_pie = fig_pie.to_html(**chart_kwargs)

    # 상세 테이블 HTML
    display_cols = ["연도", "보험종류"]
    if "지역" in df.columns:
        display_cols.append("지역")
    display_cols += ["수입보험료", "발생손해액", "손해율(%)", "등급"]

    table_df = df[display_cols].copy()
    table_df["손해율(%)"] = table_df["손해율(%)"].round(1)
    table_df["수입보험료"] = table_df["수입보험료"].map("{:,.0f}".format)
    table_df["발생손해액"] = table_df["발생손해액"].map("{:,.0f}".format)
    table_html = table_df.sort_values(["연도", "보험종류"]).to_html(
        index=False,
        classes="data-table",
        border=0,
    )

    overall_grade = "양호" if overall_lr < 80 else ("주의" if overall_lr < 100 else "위험")
    grade_color = GRADE_COLORS[overall_grade]

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Noto Sans KR', 'Apple SD Gothic Neo', sans-serif;
           background: #f4f6f9; color: #2c3e50; }}
    header {{ background: #1a252f; color: #fff; padding: 32px 40px; }}
    header h1 {{ font-size: 1.8rem; font-weight: 700; }}
    header p  {{ margin-top: 6px; color: #95a5a6; font-size: 0.9rem; }}
    .container {{ max-width: 1200px; margin: 0 auto; padding: 32px 20px; }}
    .kpi-grid {{ display: grid; grid-template-columns: repeat(4, 1fr);
                 gap: 16px; margin-bottom: 32px; }}
    .kpi-card {{ background: #fff; border-radius: 10px; padding: 20px 24px;
                 box-shadow: 0 2px 8px rgba(0,0,0,.06); }}
    .kpi-card .label {{ font-size: 0.8rem; color: #7f8c8d; margin-bottom: 6px; }}
    .kpi-card .value {{ font-size: 1.6rem; font-weight: 700; }}
    .kpi-card .badge {{ display:inline-block; padding: 2px 12px; border-radius: 12px;
                        color:#fff; font-weight:bold; font-size:1rem; }}
    .chart-grid {{ display: grid; grid-template-columns: 1fr 1fr;
                   gap: 20px; margin-bottom: 32px; }}
    .chart-card {{ background: #fff; border-radius: 10px; padding: 16px;
                   box-shadow: 0 2px 8px rgba(0,0,0,.06); }}
    .section-title {{ font-size: 1.1rem; font-weight: 700; margin-bottom: 16px; }}
    .data-table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
    .data-table th {{ background: #2c3e50; color: #fff; padding: 10px 12px;
                      text-align: left; }}
    .data-table td {{ padding: 8px 12px; border-bottom: 1px solid #ecf0f1; }}
    .data-table tr:hover td {{ background: #f8f9fa; }}
    .table-wrap {{ background:#fff; border-radius:10px; padding:20px;
                   box-shadow:0 2px 8px rgba(0,0,0,.06); overflow-x:auto; }}
    .legend {{ display:flex; gap:20px; margin-bottom:8px; font-size:0.8rem; }}
    .legend span {{ display:inline-block; width:12px; height:12px;
                    border-radius:50%; margin-right:4px; vertical-align:middle; }}
    footer {{ text-align:center; padding:24px; color:#95a5a6; font-size:0.8rem; }}
    @media(max-width:768px) {{
      .kpi-grid {{ grid-template-columns: repeat(2,1fr); }}
      .chart-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
<header>
  <h1>📊 {title}</h1>
  <p>기준일: {report_date} &nbsp;|&nbsp; 데이터: {len(df):,}개 레코드</p>
</header>
<div class="container">

  <!-- KPI -->
  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="label">전체 손해율</div>
      <div class="value">
        <span class="badge" style="background:{grade_color}">{overall_lr:.1f}%</span>
      </div>
    </div>
    <div class="kpi-card">
      <div class="label">평균 손해율</div>
      <div class="value">{stats['평균 손해율(%)']:.1f}%</div>
    </div>
    <div class="kpi-card">
      <div class="label">총 수입보험료</div>
      <div class="value" style="font-size:1.2rem">{stats['총 수입보험료']:,}<small style="font-size:0.7rem;margin-left:4px">백만원</small></div>
    </div>
    <div class="kpi-card">
      <div class="label">총 발생손해액</div>
      <div class="value" style="font-size:1.2rem">{stats['총 발생손해액']:,}<small style="font-size:0.7rem;margin-left:4px">백만원</small></div>
    </div>
  </div>

  <!-- 범례 -->
  <div class="legend">
    <div><span style="background:#2ecc71"></span>양호 (손해율 &lt; 80%)</div>
    <div><span style="background:#f39c12"></span>주의 (80% ≤ 손해율 &lt; 100%)</div>
    <div><span style="background:#e74c3c"></span>위험 (손해율 ≥ 100%)</div>
  </div>

  <!-- 차트 -->
  <div class="chart-grid">
    <div class="chart-card">{html_trend}</div>
    <div class="chart-card">{html_box}</div>
    <div class="chart-card">{html_region}</div>
    <div class="chart-card">{html_pie}</div>
  </div>

  <!-- 상세 테이블 -->
  <div class="table-wrap">
    <div class="section-title">상세 데이터</div>
    {table_html}
  </div>
</div>
<footer>본 보고서는 자동 생성되었습니다. &nbsp;|&nbsp; {report_date}</footer>
</body>
</html>"""
    return html


def main():
    parser = argparse.ArgumentParser(description="건강보험 손해율 HTML 보고서 생성")
    parser.add_argument("--input", "-i", default=None, help="입력 CSV/Excel 파일 경로 (미지정 시 샘플 데이터 사용)")
    parser.add_argument("--output", "-o", default="손해율보고서.html", help="출력 HTML 파일명 (기본: 손해율보고서.html)")
    parser.add_argument("--title", "-t", default="건강보험 손해율 분석 보고서", help="보고서 제목")
    args = parser.parse_args()

    # 데이터 로드
    if args.input:
        path = Path(args.input)
        if path.suffix.lower() == ".csv":
            df = pd.read_csv(path, encoding="utf-8-sig")
        else:
            df = pd.read_excel(path)
        print(f"데이터 로드: {path} ({len(df)}행)")
    else:
        df = load_sample_data()
        print(f"샘플 데이터 로드 ({len(df)}행)")

    df = normalize_columns(df)
    df = add_loss_ratio_columns(df)

    # HTML 생성
    html = build_report(df, title=args.title)
    output_path = Path(args.output)
    output_path.write_text(html, encoding="utf-8")
    print(f"보고서 생성 완료: {output_path.resolve()}")


if __name__ == "__main__":
    main()

"""
건강보험 손해율 분석 보고서 생성기

Streamlit 앱과 동일한 3가지 필터(연도·보험종류·지역)를 갖춘
인터랙티브 HTML 파일을 생성합니다.

망분리 환경 대응:
- Plotly.js가 파일 안에 완전히 내장됩니다 (약 3~4 MB).
- 인터넷 연결 없이도 브라우저에서 바로 열 수 있습니다.

실행 방법:
    # 샘플 데이터로 생성
    python report.py

    # 실제 데이터 파일 지정
    python report.py --input 실제데이터.csv --output 손해율보고서.html
"""

import argparse
import json
from datetime import date
from pathlib import Path

import pandas as pd
import plotly.offline

from src.calculator import add_loss_ratio_columns
from src.data_loader import load_sample_data, normalize_columns


GRADE_COLORS = {"양호": "#2ecc71", "주의": "#f39c12", "위험": "#e74c3c"}


def _checkboxes(items: list, group_id: str) -> str:
    """체크박스 HTML을 생성합니다 (기본값: 전체 선택)."""
    return "\n".join(
        f'<label class="cb-label">'
        f'<input type="checkbox" value="{v}" checked '
        f'onchange="updateAll()"> {v}'
        f'</label>'
        for v in items
    )


def build_report(df: pd.DataFrame, title: str = "건강보험 손해율 분석 보고서") -> str:
    """데이터프레임을 받아 독립 실행형 HTML 보고서 문자열을 반환합니다."""

    report_date = date.today().strftime("%Y년 %m월 %d일")
    has_region = "지역" in df.columns

    # ── 필터 옵션 ────────────────────────────────────────────────────────────
    years = sorted(df["연도"].dropna().unique().tolist())
    ins_types = sorted(df["보험종류"].dropna().unique().tolist())
    regions = sorted(df["지역"].dropna().unique().tolist()) if has_region else []

    year_cbs = _checkboxes([str(y) for y in years], "filter-years")
    type_cbs = _checkboxes(ins_types, "filter-types")
    region_cbs = _checkboxes(regions, "filter-regions") if has_region else ""

    region_filter_html = ""
    if has_region:
        region_filter_html = f"""
        <div class="filter-group">
          <div class="filter-label">지역</div>
          <div class="filter-btns">
            <button onclick="selectAll('filter-regions')">전체</button>
            <button onclick="clearAll('filter-regions')">해제</button>
          </div>
          <div class="checkboxes" id="filter-regions">
            {region_cbs}
          </div>
        </div>"""

    # ── JSON 데이터 임베딩 ───────────────────────────────────────────────────
    records = df.to_dict(orient="records")
    data_json = json.dumps(records, ensure_ascii=False, default=str)

    grade_colors_json = json.dumps(GRADE_COLORS, ensure_ascii=False)

    # ── Plotly.js 인라인 임베딩 (망분리 대응) ────────────────────────────────
    plotlyjs = plotly.offline.get_plotlyjs()

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:'Noto Sans KR','Apple SD Gothic Neo',sans-serif;
         background:#f4f6f9;color:#2c3e50;font-size:14px}}

    /* ── 헤더 ── */
    header{{background:#1a252f;color:#fff;padding:28px 40px}}
    header h1{{font-size:1.6rem;font-weight:700}}
    header p{{margin-top:6px;color:#95a5a6;font-size:0.85rem}}

    /* ── 레이아웃 ── */
    .layout{{display:flex;gap:0;min-height:calc(100vh - 90px)}}

    /* ── 사이드바(필터 패널) ── */
    .sidebar{{width:220px;flex-shrink:0;background:#fff;
             border-right:1px solid #e0e0e0;padding:20px 14px;
             overflow-y:auto}}
    .sidebar h2{{font-size:0.95rem;font-weight:700;margin-bottom:16px;color:#34495e}}
    .filter-group{{margin-bottom:18px}}
    .filter-label{{font-size:0.78rem;font-weight:700;color:#7f8c8d;
                  text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}}
    .filter-btns{{display:flex;gap:4px;margin-bottom:6px}}
    .filter-btns button{{flex:1;font-size:0.72rem;padding:3px 0;border:1px solid #bdc3c7;
                         background:#ecf0f1;border-radius:4px;cursor:pointer}}
    .filter-btns button:hover{{background:#dde1e3}}
    .checkboxes{{display:flex;flex-direction:column;gap:4px;
                max-height:180px;overflow-y:auto;padding-right:2px}}
    .cb-label{{display:flex;align-items:center;gap:6px;font-size:0.82rem;
              cursor:pointer;padding:2px 0}}
    .cb-label:hover{{color:#2980b9}}
    .cb-label input{{cursor:pointer}}

    /* ── 메인 영역 ── */
    .main{{flex:1;padding:24px 20px;min-width:0}}

    /* ── KPI ── */
    .kpi-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:20px}}
    .kpi-card{{background:#fff;border-radius:10px;padding:16px 20px;
              box-shadow:0 2px 8px rgba(0,0,0,.06)}}
    .kpi-card .klabel{{font-size:0.75rem;color:#7f8c8d;margin-bottom:6px}}
    .kpi-card .kval{{font-size:1.45rem;font-weight:700}}
    .badge{{display:inline-block;padding:2px 12px;border-radius:12px;
           color:#fff;font-weight:bold;font-size:1rem}}

    /* ── 범례 ── */
    .legend{{display:flex;gap:18px;margin-bottom:14px;font-size:0.78rem;color:#555}}
    .legend-dot{{width:11px;height:11px;border-radius:50%;
                display:inline-block;margin-right:4px;vertical-align:middle}}

    /* ── 차트 그리드 ── */
    .chart-grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px}}
    .chart-card{{background:#fff;border-radius:10px;padding:14px;
                box-shadow:0 2px 8px rgba(0,0,0,.06);min-width:0}}

    /* ── 테이블 ── */
    .table-wrap{{background:#fff;border-radius:10px;padding:18px;
                box-shadow:0 2px 8px rgba(0,0,0,.06);overflow-x:auto}}
    .table-title{{font-size:1rem;font-weight:700;margin-bottom:12px}}
    #data-table{{width:100%;border-collapse:collapse;font-size:0.82rem}}
    #data-table th{{background:#2c3e50;color:#fff;padding:9px 11px;text-align:left}}
    #data-table td{{padding:7px 11px;border-bottom:1px solid #ecf0f1}}
    #data-table tr:hover td{{background:#f8f9fa}}
    .no-data{{text-align:center;padding:30px;color:#95a5a6;font-size:0.9rem}}

    /* ── 빈 상태 경고 ── */
    #empty-warn{{display:none;background:#fdf3cd;border:1px solid #f0c040;
                border-radius:8px;padding:14px 18px;margin-bottom:16px;
                color:#7d6608;font-size:0.88rem}}

    footer{{text-align:center;padding:20px;color:#95a5a6;font-size:0.75rem;
           border-top:1px solid #e0e0e0;background:#fff;margin-top:10px}}

    @media(max-width:900px){{
      .kpi-grid{{grid-template-columns:repeat(2,1fr)}}
      .chart-grid{{grid-template-columns:1fr}}
      .sidebar{{width:100%;border-right:none;border-bottom:1px solid #e0e0e0}}
      .layout{{flex-direction:column}}
    }}
  </style>
</head>
<body>
<header>
  <h1>📊 {title}</h1>
  <p>기준일: {report_date} &nbsp;|&nbsp; 전체 레코드: {len(df):,}개</p>
</header>

<div class="layout">
  <!-- ── 사이드바 필터 ── -->
  <aside class="sidebar">
    <h2>⚙️ 필터</h2>

    <div class="filter-group">
      <div class="filter-label">연도</div>
      <div class="filter-btns">
        <button onclick="selectAll('filter-years')">전체</button>
        <button onclick="clearAll('filter-years')">해제</button>
      </div>
      <div class="checkboxes" id="filter-years">
        {year_cbs}
      </div>
    </div>

    <div class="filter-group">
      <div class="filter-label">보험종류</div>
      <div class="filter-btns">
        <button onclick="selectAll('filter-types')">전체</button>
        <button onclick="clearAll('filter-types')">해제</button>
      </div>
      <div class="checkboxes" id="filter-types">
        {type_cbs}
      </div>
    </div>

    {region_filter_html}

    <hr style="margin:14px 0;border:none;border-top:1px solid #ecf0f1">
    <div style="font-size:0.75rem;color:#7f8c8d;line-height:1.7">
      <strong>손해율 등급 기준</strong><br>
      🟢 양호: 80% 미만<br>
      🟡 주의: 80~100%<br>
      🔴 위험: 100% 초과
    </div>
  </aside>

  <!-- ── 메인 콘텐츠 ── -->
  <main class="main">
    <div id="empty-warn">⚠️ 선택한 필터에 해당하는 데이터가 없습니다.</div>

    <!-- KPI -->
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="klabel">전체 손해율</div>
        <div class="kval" id="kpi-overall">—</div>
      </div>
      <div class="kpi-card">
        <div class="klabel">평균 손해율</div>
        <div class="kval" id="kpi-avg">—</div>
      </div>
      <div class="kpi-card">
        <div class="klabel">총 수입보험료</div>
        <div class="kval" id="kpi-premium" style="font-size:1.1rem">—</div>
      </div>
      <div class="kpi-card">
        <div class="klabel">총 발생손해액</div>
        <div class="kval" id="kpi-loss" style="font-size:1.1rem">—</div>
      </div>
    </div>

    <!-- 범례 -->
    <div class="legend">
      <span><span class="legend-dot" style="background:#2ecc71"></span>양호 (손해율 &lt; 80%)</span>
      <span><span class="legend-dot" style="background:#f39c12"></span>주의 (80% ≤ 손해율 &lt; 100%)</span>
      <span><span class="legend-dot" style="background:#e74c3c"></span>위험 (손해율 ≥ 100%)</span>
    </div>

    <!-- 차트 -->
    <div class="chart-grid">
      <div class="chart-card"><div id="chart-trend" style="height:320px"></div></div>
      <div class="chart-card"><div id="chart-box"   style="height:320px"></div></div>
      <div class="chart-card"><div id="chart-region" style="height:320px"></div></div>
      <div class="chart-card"><div id="chart-pie"   style="height:320px"></div></div>
    </div>

    <!-- 상세 테이블 -->
    <div class="table-wrap">
      <div class="table-title">상세 데이터 (<span id="row-count">0</span>건)</div>
      <table id="data-table">
        <thead id="table-head"></thead>
        <tbody id="table-body"></tbody>
      </table>
    </div>
  </main>
</div>

<footer>본 보고서는 자동 생성되었습니다. &nbsp;|&nbsp; {report_date}</footer>

<!-- ── 내장 Plotly.js (망분리 대응) ── -->
<script>{plotlyjs}</script>

<script>
// ══════════════════════════════════════════════════════
//  데이터 및 설정
// ══════════════════════════════════════════════════════
const RAW_DATA = {data_json};
const GRADE_COLORS = {grade_colors_json};
const HAS_REGION = {'true' if has_region else 'false'};

const WARN_80  = {{type:'line', x0:0, x1:1, xref:'paper', y0:80, y1:80,
                   line:{{dash:'dot', color:'#f39c12', width:1.5}}}};
const WARN_100 = {{type:'line', x0:0, x1:1, xref:'paper', y0:100, y1:100,
                   line:{{dash:'dot', color:'#e74c3c', width:1.5}}}};
const WARN_V80  = {{type:'line', y0:0, y1:1, yref:'paper', x0:80, x1:80,
                    line:{{dash:'dot', color:'#f39c12', width:1.5}}}};
const WARN_V100 = {{type:'line', y0:0, y1:1, yref:'paper', x0:100, x1:100,
                    line:{{dash:'dot', color:'#e74c3c', width:1.5}}}};

const LAYOUT_BASE = {{
  margin:{{t:36,b:40,l:50,r:20}},
  font:{{family:"'Noto Sans KR',sans-serif", size:12}},
  paper_bgcolor:'#fff', plot_bgcolor:'#fff',
  legend:{{orientation:'h', y:-0.18}},
}};

// ══════════════════════════════════════════════════════
//  필터 유틸
// ══════════════════════════════════════════════════════
function getChecked(id) {{
  return [...document.querySelectorAll(`#${{id}} input:checked`)].map(cb => cb.value);
}}
function selectAll(id) {{
  document.querySelectorAll(`#${{id}} input`).forEach(cb => cb.checked = true);
  updateAll();
}}
function clearAll(id) {{
  document.querySelectorAll(`#${{id}} input`).forEach(cb => cb.checked = false);
  updateAll();
}}

function applyFilters() {{
  const years  = getChecked('filter-years');
  const types  = getChecked('filter-types');
  const regions = HAS_REGION ? getChecked('filter-regions') : null;
  return RAW_DATA.filter(d =>
    years.includes(String(d['연도'])) &&
    types.includes(d['보험종류']) &&
    (!HAS_REGION || regions.includes(d['지역']))
  );
}}

// ══════════════════════════════════════════════════════
//  집계 유틸
// ══════════════════════════════════════════════════════
function groupBy(data, keys) {{
  const map = {{}};
  data.forEach(d => {{
    const key = keys.map(k => d[k]).join('||');
    if (!map[key]) map[key] = {{_rows: [], ...Object.fromEntries(keys.map(k => [k, d[k]]))}};
    map[key]._rows.push(d);
  }});
  return Object.values(map);
}}

function lossRatio(rows) {{
  const sp = rows.reduce((s,r) => s + Number(r['수입보험료']),0);
  const sl = rows.reduce((s,r) => s + Number(r['발생손해액']),0);
  return sp > 0 ? sl / sp * 100 : 0;
}}

function gradeColor(lr) {{
  return lr < 80 ? GRADE_COLORS['양호'] : lr < 100 ? GRADE_COLORS['주의'] : GRADE_COLORS['위험'];
}}

// ══════════════════════════════════════════════════════
//  KPI 업데이트
// ══════════════════════════════════════════════════════
function updateKPIs(data) {{
  if (!data.length) {{
    ['kpi-overall','kpi-avg','kpi-premium','kpi-loss'].forEach(id =>
      document.getElementById(id).innerHTML = '—');
    return;
  }}
  const totalPremium = data.reduce((s,r) => s + Number(r['수입보험료']), 0);
  const totalLoss    = data.reduce((s,r) => s + Number(r['발생손해액']), 0);
  const overall      = totalPremium > 0 ? totalLoss / totalPremium * 100 : 0;
  const avg          = data.reduce((s,r) => s + Number(r['손해율(%)']), 0) / data.length;
  const grade        = overall < 80 ? '양호' : overall < 100 ? '주의' : '위험';
  const color        = GRADE_COLORS[grade];

  document.getElementById('kpi-overall').innerHTML =
    `<span class="badge" style="background:${{color}}">${{overall.toFixed(1)}}%</span>`;
  document.getElementById('kpi-avg').textContent = avg.toFixed(1) + '%';
  document.getElementById('kpi-premium').innerHTML =
    `${{Math.round(totalPremium).toLocaleString()}}<small style="font-size:0.7rem;margin-left:4px">백만원</small>`;
  document.getElementById('kpi-loss').innerHTML =
    `${{Math.round(totalLoss).toLocaleString()}}<small style="font-size:0.7rem;margin-left:4px">백만원</small>`;
}}

// ══════════════════════════════════════════════════════
//  차트 렌더링
// ══════════════════════════════════════════════════════
function drawTrend(data) {{
  const grouped = groupBy(data, ['연도','보험종류']);
  const typeSet = [...new Set(data.map(d => d['보험종류']))].sort();
  const traces  = typeSet.map(t => {{
    const rows = grouped.filter(g => g['보험종류'] === t).sort((a,b) => a['연도']-b['연도']);
    return {{
      type:'scatter', mode:'lines+markers', name:t,
      x: rows.map(g => g['연도']),
      y: rows.map(g => lossRatio(g._rows)),
    }};
  }});
  Plotly.react('chart-trend', traces, {{
    ...LAYOUT_BASE,
    title:{{text:'연도별 손해율 추이', font:{{size:13}}}},
    yaxis:{{ticksuffix:'%'}},
    shapes:[WARN_80, WARN_100],
    annotations:[
      {{xref:'paper',x:1,y:80,text:'주의(80%)',showarrow:false,font:{{color:'#f39c12',size:10}}}},
      {{xref:'paper',x:1,y:100,text:'위험(100%)',showarrow:false,font:{{color:'#e74c3c',size:10}}}},
    ],
  }}, {{responsive:true}});
}}

function drawBox(data) {{
  const typeSet = [...new Set(data.map(d => d['보험종류']))].sort();
  const traces  = typeSet.map(t => {{
    const rows = data.filter(d => d['보험종류'] === t);
    return {{
      type:'box', boxpoints:'all', jitter:0.4, name:t,
      y: rows.map(d => Number(d['손해율(%)'])),
    }};
  }});
  Plotly.react('chart-box', traces, {{
    ...LAYOUT_BASE,
    title:{{text:'보험종류별 손해율 분포', font:{{size:13}}}},
    yaxis:{{ticksuffix:'%'}},
    shapes:[WARN_80, WARN_100],
    showlegend:false,
  }}, {{responsive:true}});
}}

function drawRegion(data) {{
  if (HAS_REGION) {{
    const grouped = groupBy(data, ['지역']).map(g => ({{
      지역: g['지역'], lr: lossRatio(g._rows)
    }})).sort((a,b) => a.lr - b.lr);
    Plotly.react('chart-region', [{{
      type:'bar', orientation:'h',
      x: grouped.map(g => g.lr),
      y: grouped.map(g => g.지역),
      marker:{{color: grouped.map(g => gradeColor(g.lr))}},
    }}], {{
      ...LAYOUT_BASE,
      title:{{text:'지역별 평균 손해율', font:{{size:13}}}},
      xaxis:{{ticksuffix:'%'}},
      shapes:[WARN_V80, WARN_V100],
    }}, {{responsive:true}});
  }} else {{
    const grouped = groupBy(data, ['연도']).sort((a,b) => a['연도']-b['연도']);
    Plotly.react('chart-region', [
      {{
        type:'bar', name:'수입보험료',
        x: grouped.map(g => g['연도']),
        y: grouped.map(g => g._rows.reduce((s,r) => s+Number(r['수입보험료']),0)),
      }},
      {{
        type:'bar', name:'발생손해액',
        x: grouped.map(g => g['연도']),
        y: grouped.map(g => g._rows.reduce((s,r) => s+Number(r['발생손해액']),0)),
      }},
    ], {{
      ...LAYOUT_BASE,
      title:{{text:'연도별 보험료 vs 손해액', font:{{size:13}}}},
      barmode:'group',
    }}, {{responsive:true}});
  }}
}}

function drawPie(data) {{
  const grades  = Object.keys(GRADE_COLORS);
  const counts  = grades.map(g => data.filter(d => d['등급'] === g).length);
  Plotly.react('chart-pie', [{{
    type:'pie',
    labels: grades,
    values: counts,
    marker:{{colors: grades.map(g => GRADE_COLORS[g])}},
    textinfo:'label+percent',
  }}], {{
    ...LAYOUT_BASE,
    title:{{text:'손해율 등급 분포', font:{{size:13}}}},
  }}, {{responsive:true}});
}}

// ══════════════════════════════════════════════════════
//  상세 테이블
// ══════════════════════════════════════════════════════
function updateTable(data) {{
  const cols = ['연도','보험종류', ...(HAS_REGION ? ['지역'] : []),
                '수입보험료','발생손해액','손해율(%)','등급'];

  // 헤더 (처음 한 번만 그려도 되지만 필터 변경 시에도 안전하게 재생성)
  document.getElementById('table-head').innerHTML =
    '<tr>' + cols.map(c => `<th>${{c}}</th>`).join('') + '</tr>';

  const sorted = [...data].sort((a,b) =>
    String(a['연도']).localeCompare(String(b['연도'])) ||
    a['보험종류'].localeCompare(b['보험종류']));

  document.getElementById('row-count').textContent = sorted.length.toLocaleString();

  if (!sorted.length) {{
    document.getElementById('table-body').innerHTML =
      `<tr><td colspan="${{cols.length}}" class="no-data">데이터가 없습니다.</td></tr>`;
    return;
  }}

  const rows = sorted.map(d => {{
    const gradeColor = GRADE_COLORS[d['등급']] || '#95a5a6';
    return '<tr>' + cols.map(c => {{
      if (c === '수입보험료' || c === '발생손해액')
        return `<td>${{Number(d[c]).toLocaleString()}}</td>`;
      if (c === '손해율(%)')
        return `<td>${{Number(d[c]).toFixed(1)}}%</td>`;
      if (c === '등급')
        return `<td><span style="background:${{gradeColor}};color:#fff;
          padding:1px 8px;border-radius:10px;font-size:0.75rem">${{d[c]}}</span></td>`;
      return `<td>${{d[c] ?? ''}}</td>`;
    }}).join('') + '</tr>';
  }});
  document.getElementById('table-body').innerHTML = rows.join('');
}}

// ══════════════════════════════════════════════════════
//  메인 업데이트 함수
// ══════════════════════════════════════════════════════
function updateAll() {{
  const data = applyFilters();
  const warn = document.getElementById('empty-warn');
  warn.style.display = data.length ? 'none' : 'block';

  updateKPIs(data);
  drawTrend(data);
  drawBox(data);
  drawRegion(data);
  drawPie(data);
  updateTable(data);
}}

// 페이지 로드 시 초기 렌더링
updateAll();
</script>
</body>
</html>"""
    return html


def main():
    parser = argparse.ArgumentParser(description="건강보험 손해율 인터랙티브 HTML 보고서 생성")
    parser.add_argument("--input",  "-i", default=None,           help="입력 CSV/Excel 파일 경로 (미지정 시 샘플 데이터)")
    parser.add_argument("--output", "-o", default="손해율보고서.html", help="출력 HTML 파일명 (기본: 손해율보고서.html)")
    parser.add_argument("--title",  "-t", default="건강보험 손해율 분석 보고서", help="보고서 제목")
    args = parser.parse_args()

    if args.input:
        path = Path(args.input)
        df = pd.read_csv(path, encoding="utf-8-sig") if path.suffix.lower() == ".csv" else pd.read_excel(path)
        print(f"데이터 로드: {path} ({len(df)}행)")
    else:
        df = load_sample_data()
        print(f"샘플 데이터 로드 ({len(df)}행)")

    df = normalize_columns(df)
    df = add_loss_ratio_columns(df)

    html = build_report(df, title=args.title)
    output_path = Path(args.output)
    output_path.write_text(html, encoding="utf-8")
    print(f"보고서 생성 완료: {output_path.resolve()}")
    print(f"파일 크기: {output_path.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()

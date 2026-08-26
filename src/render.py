"""단일 HTML 출력. 계산은 하지 않는다.

색상 토큰은 dataviz 검증기를 통과한 값이다(라이트/다크 전 항목 PASS,
CVD ΔE 21.6/19.2). 임의로 바꾸지 말 것.
등수분포는 탑4/하위4 두 계열이라 색만으로 구분하지 않고 값 라벨을 같이 붙인다.
"""

import html as _html

CSS = """
:root {
  color-scheme: light;
  --surface: #fcfcfb; --text: #0b0b0b; --text2: #52514e;
  --top4: #2a78d6; --bot4: #e34948; --mid: #f0efec;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --surface: #1a1a19; --text: #ffffff; --text2: #c3c2b7;
    --top4: #3987e5; --bot4: #e66767; --mid: #383835;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --surface: #1a1a19; --text: #ffffff; --text2: #c3c2b7;
  --top4: #3987e5; --bot4: #e66767; --mid: #383835;
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 16px; background: var(--surface); color: var(--text);
  font: 15px/1.6 -apple-system, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
  max-width: 760px; margin-inline: auto;
}
h1 { font-size: 20px; margin: 0 0 4px; }
h2 { font-size: 16px; margin: 28px 0 10px; }
.meta, .muted { color: var(--text2); font-size: 13px; }
.stale { background: var(--bot4); color: #fff; padding: 2px 8px; border-radius: 4px;
         font-size: 12px; display: inline-block; }
.card { border: 1px solid var(--mid); border-radius: 8px; padding: 14px; margin: 12px 0; }
.card h3 { margin: 0 0 2px; font-size: 17px; }
.nums { display: flex; gap: 18px; flex-wrap: wrap; margin: 10px 0 6px; }
.nums b { font-variant-numeric: tabular-nums; font-weight: 600; }
.badge { font-size: 12px; padding: 2px 8px; border-radius: 4px; color: #fff; }
.badge.low { background: var(--top4); }
.badge.high { background: var(--bot4); }
.dist { display: flex; align-items: flex-end; gap: 2px; height: 46px; margin: 10px 0 4px; }
.dist-bar { flex: 1; border-radius: 4px 4px 0 0; min-height: 2px; }
.dist-bar.top4 { background: var(--top4); }
.dist-bar.bot4 { background: var(--bot4); }
.dist-axis { display: flex; gap: 2px; }
.dist-axis span { flex: 1; text-align: center; font-size: 11px; color: var(--text2); }
.legend { font-size: 12px; color: var(--text2); }
.legend i { display: inline-block; width: 9px; height: 9px; border-radius: 2px;
            margin-right: 4px; vertical-align: baseline; }
.route { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; font-size: 13px; }
.route div { border: 1px solid var(--mid); border-radius: 6px; padding: 6px 8px; }
.route b { display: block; color: var(--text2); font-size: 11px; font-weight: 600; }
table { border-collapse: collapse; width: 100%; font-size: 14px; }
td, th { border-bottom: 1px solid var(--mid); padding: 6px 4px; text-align: left; }
td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
.scroll { overflow-x: auto; }
blockquote { margin: 8px 0; padding-left: 10px; border-left: 3px solid var(--mid);
             color: var(--text2); font-size: 13px; }
a { color: inherit; }
""".strip()

_STAGE_LABEL = {"stage-2": "2스테이지", "stage-3": "3스테이지",
                "stage-4": "4스테이지", "stage-5": "5스테이지"}


def _e(value):
    return _html.escape(str(value), quote=True)


def dist_bars(dist):
    """등수분포 막대 여덟 개. 탑4는 파랑, 하위4는 빨강.

    색만으로 뜻을 전달하지 않는다 — 각 막대에 aria-label과 title로 값을 붙인다.
    """
    top = max(dist) if dist and max(dist) > 0 else 1.0
    bars = []
    for index, ratio in enumerate(dist[:8]):
        rank = index + 1
        klass = "top4" if rank <= 4 else "bot4"
        label = f"{rank}등 {round(ratio * 100)}%"
        height = max(2, round(ratio / top * 46))
        bars.append(
            f'<div class="dist-bar {klass}" style="height:{height}px" '
            f'aria-label="{_e(label)}" title="{_e(label)}"></div>'
        )
    axis = "".join(f"<span>{rank}</span>" for rank in range(1, 9))
    return (f'<div class="dist" role="img" aria-label="등수 분포">{"".join(bars)}</div>'
            f'<div class="dist-axis">{axis}</div>')


def _delta_badge(delta):
    if delta is None:
        return '<span class="muted">고티어 표본 없음</span>'
    if delta < 0:
        return f'<span class="badge low">Δ {delta:+.2f} 저티어 전용</span>'
    return f'<span class="badge high">Δ {delta:+.2f} 고티어 전용</span>'


def _route(steps):
    if not steps:
        return ('<p class="muted">단계 경로 없음 — 이 덱은 다이아+ 경로와 '
                '유닛이 충분히 겹치지 않아 억지로 잇지 않았다.</p>')
    cells = []
    for step in steps:
        label = _STAGE_LABEL.get(step["stage"], step["stage"])
        units = ", ".join(_e(u) for u in step["units"])
        avp = "" if step.get("avp") is None else f' · 평균 {step["avp"]:.2f}'
        cells.append(f"<div><b>{_e(label)}{avp}</b>{units}</div>")
    return ('<p class="muted">단계 경로 — 다이아+ 데이터다. 브실골 표본으로는 '
            '단계별 보드를 구할 수 없다.</p>'
            f'<div class="route">{"".join(cells)}</div>')


def _deck_card(deck):
    high = "표본 없음" if deck["avp_high"] is None else f'{deck["avp_high"]:.2f}'
    return f"""<div class="card">
<h3>{_e(deck["name"])}</h3>
<div class="meta">표본 {deck["count"]:,}판</div>
<div class="nums">
  <span>브실골 <b>{deck["avp_low"]:.2f}</b></span>
  <span>다이아+ <b>{_e(high)}</b></span>
  <span>{_delta_badge(deck["delta"])}</span>
</div>
<div class="nums">
  <span>픽률 <b>{deck["pick_rate"]:.1%}</b></span>
  <span>8인 로비 기대 경합 <b>{deck["expected_contest"]:.1f}명</b></span>
</div>
{dist_bars(deck["dist"])}
<div class="legend">
  <i style="background:var(--top4)"></i>1~4등
  <i style="background:var(--bot4);margin-left:10px"></i>5~8등
  · 탑4 {sum(deck["dist"][:4]):.0%}
</div>
{_route(deck.get("route") or [])}
</div>"""


def _index_row(deck):
    """색인 표의 한 줄. Δ가 없는 덱은 칸을 비운다."""
    delta = "" if deck["delta"] is None else f'{deck["delta"]:+.2f}'
    return (f'<tr><td>{_e(deck["name"])}</td>'
            f'<td class="n">{deck["avp_low"]:.2f}</td>'
            f'<td class="n">{_e(delta)}</td></tr>')


def index_section(title, indexes, name_of):
    """유닛 색인. 코스트 순으로 묶고, 각 유닛마다 그 유닛을 쓰는 덱을 접어둔다."""
    if not indexes.get("units"):
        return ""
    blocks = []
    for cost in sorted(indexes["cost_groups"]):
        label = f"{cost}코스트" if cost else "코스트 미상"
        items = []
        for unit in indexes["cost_groups"][cost]:
            decks = indexes["units"][unit]
            rows = "".join(_index_row(deck) for deck in decks)
            items.append(
                f'<details><summary>{_e(name_of(unit))} '
                f'<span class="muted">({len(decks)}덱)</span></summary>'
                f'<div class="scroll"><table><tr><th>덱</th><th class="n">브실골</th>'
                f'<th class="n">Δ</th></tr>{rows}</table></div></details>'
            )
        blocks.append(f'<h3>{_e(label)}</h3>{"".join(items)}')
    return f'<h2>{_e(title)}</h2><p class="muted">손에 들어온 유닛으로 덱을 찾는다.</p>' + "".join(blocks)


def _fundamentals(data):
    blocks = []
    for section in data.get("sections", []):
        rows = "".join(
            "<tr>" + "".join(f'<td{" class=n" if i else ""}>{_e(cell)}</td>'
                             for i, cell in enumerate(row)) + "</tr>"
            for row in section.get("rows", [])
        )
        quote = (f"<blockquote>{_e(section['quote'])}</blockquote>"
                 if section.get("quote") else "")
        note = f'<p class="muted">{_e(section["note"])}</p>' if section.get("note") else ""
        blocks.append(
            f'<h2>{_e(section["title"])}</h2>{note}{quote}'
            f'<div class="scroll"><table>{rows}</table></div>'
            f'<p class="muted"><a href="{_e(section["source"])}">출처 원문</a></p>'
        )
    return "".join(blocks)


def _diff_banner(diff, summary):
    if not diff.get("patch_changed"):
        return ""
    lines = []
    for row in diff.get("moved", []):
        arrow = "나빠짐" if row["after"] > row["before"] else "좋아짐"
        lines.append(f'<li>{_e(row["name"])} {row["before"]:.2f} → {row["after"]:.2f} ({arrow})</li>')
    for row in diff.get("entered", []):
        lines.append(f'<li>{_e(row.get("name"))} 새로 진입</li>')
    for row in diff.get("left", []):
        lines.append(f'<li>{_e(row.get("name"))} 이탈</li>')
    body = f"<ul>{''.join(lines)}</ul>" if lines else "<p>상위 덱 순위는 그대로다.</p>"
    official = ""
    if summary and summary.get("bullets"):
        items = "".join(f"<li>{_e(bullet)}</li>" for bullet in summary["bullets"])
        official = (f'<p class="muted">공식 노트에서 네 덱에 걸리는 항목</p><ul>{items}</ul>'
                    f'<p class="muted"><a href="{_e(summary["url"])}">패치노트 원문</a></p>')
    return (f'<div class="card"><h3>패치 {_e(diff["to_patch"])} 적용됨</h3>'
            f'<div class="meta">직전 {_e(diff["from_patch"])} 대비</div>{body}{official}'
            '<p class="muted">패치 직후 3~5일은 데이터가 안 굳는다. '
            '이 숫자만 보고 덱을 버리지 마라.</p></div>')


def page(context):
    """완성된 HTML 한 장."""
    stale = ""
    if context["stale_hours"] >= 24:
        stale = f'<p><span class="stale">{context["stale_hours"]}시간 전 데이터 — 갱신 실패 중</span></p>'

    if context["decks"]:
        decks_html = "".join(_deck_card(deck) for deck in context["decks"])
    else:
        decks_html = ('<div class="card"><h3>아직 데이터가 없다</h3>'
                      '<p class="muted">셋이 막 바뀌었거나 표본이 하한에 못 미친다. '
                      '집계가 쌓이면 자동으로 채워진다. 그동안은 아래 기본기를 본다.</p></div>')

    return f"""<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>브실골 롤체 치트시트</title>
<style>{CSS}</style>
</head><body>
<h1>브실골 롤체 치트시트</h1>
<p class="meta">{_e(context["set"])} · 패치 {_e(context["patch"])} ·
KR 브론즈~골드 {context["sample_days"]}일 {context["total_games"]:,}판 ·
{_e(context["generated_at"])} 기준</p>
{stale}
{_diff_banner(context["diff"], context.get("notes"))}
<h2>이번 패치 너의 {len(context["decks"])}덱</h2>
<p class="muted">Δ = 브실골 평균등수 − 다이아+ 평균등수. 음수면 네 티어에서 더 잘 나오는 덱이다.
평균등수만으로 줄 세우지 않는다 — 등수 분포와 픽률을 같이 본다.</p>
{decks_html}
{index_section("유닛으로 찾기", context.get("indexes") or {}, context.get("name_of", str))}
{_fundamentals(context["fundamentals"])}
<h2>출처</h2>
<p class="muted">덱 통계·단계 경로: MetaTFT · 한글 이름표: Riot Data Dragon<br>
Riot Games가 승인하거나 후원한 프로젝트가 아니다.</p>
</body></html>"""

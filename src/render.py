"""단일 HTML 출력. 계산은 하지 않는다.

색상 토큰은 dataviz 검증기를 통과한 값이다(라이트/다크 전 항목 PASS,
CVD ΔE 21.6/19.2). 임의로 바꾸지 말 것. 아래 --surface-2/--line/--rail 은
그 여섯 색을 건드리지 않고 같은 웜뉴트럴 계열로 덧붙인 표면 토큰이다.
등수분포는 탑4/하위4 두 계열이라 색만으로 구분하지 않고 값 라벨을 같이 붙인다.
"""

import html as _html

from .notes import is_patch_number

# 폰트는 CDN이 막혀도 폴백 스택으로 멀쩡히 읽혀야 한다 — 본문은 프리텐다드,
# 숫자만 JetBrains Mono. 숫자에만 모노를 씌우는 게 이 페이지 타이포 대비의 전부다.
FONT_LINKS = """<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.css">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400..700&amp;display=swap">"""

# Δ 삼각형 하나. 파일을 따로 두면 Pages 배포에서 빠질 수 있어 data URI로 박는다.
FAVICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
           "%3Crect width='32' height='32' rx='7' fill='%231a1a19'/%3E"
           "%3Cpath d='M16 7 L26 25 H6 Z' fill='%233987e5'/%3E%3C/svg%3E")

# 종이결 한 겹. 네트워크 요청 없이 feTurbulence를 data URI로 굽는다.
_GRAIN = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E"
          "%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' "
          "numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E"
          "%3Crect width='140' height='140' filter='url(%23n)'/%3E%3C/svg%3E")

CSS = """
:root {
  color-scheme: light;
  --surface: #fcfcfb; --text: #0b0b0b; --text2: #52514e;
  --top4: #2a78d6; --bot4: #e34948; --mid: #f0efec;
  --surface-2: #f6f5f1; --line: #e5e3da; --rail: #d6d4c9;
  --shadow: 0 1px 1px rgba(66,62,48,.05), 0 6px 16px -10px rgba(66,62,48,.20);
  --grain: .035;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --surface: #1a1a19; --text: #ffffff; --text2: #c3c2b7;
    --top4: #3987e5; --bot4: #e66767; --mid: #383835;
    --surface-2: #232322; --line: #34342f; --rail: #43423b;
    --shadow: 0 1px 1px rgba(6,6,4,.45), 0 8px 20px -12px rgba(6,6,4,.80);
    --grain: .05;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --surface: #1a1a19; --text: #ffffff; --text2: #c3c2b7;
  --top4: #3987e5; --bot4: #e66767; --mid: #383835;
  --surface-2: #232322; --line: #34342f; --rail: #43423b;
  --shadow: 0 1px 1px rgba(6,6,4,.45), 0 8px 20px -12px rgba(6,6,4,.80);
  --grain: .05;
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0 auto; padding: 20px 16px 44px; max-width: 780px;
  background: var(--surface); color: var(--text);
  font-family: "Pretendard Variable", Pretendard, -apple-system, BlinkMacSystemFont,
    "Apple SD Gothic Neo", "Segoe UI", "Noto Sans KR", "Malgun Gothic", sans-serif;
  font-size: 15px; line-height: 1.62; font-weight: 400;
  word-break: keep-all; overflow-wrap: break-word;
  -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale;
}
.num, td.n, th.n {
  font-family: "JetBrains Mono", ui-monospace, SFMono-Regular, "Cascadia Mono",
    Consolas, monospace;
  font-variant-numeric: tabular-nums; font-feature-settings: "tnum" 1;
}

/* 종이결. 요청 0회, 클릭 통과. */
.grain {
  position: fixed; inset: 0; z-index: 9999; pointer-events: none;
  opacity: var(--grain); background-image: url("GRAIN_URI");
  background-size: 140px 140px;
}
.skip {
  position: absolute; left: -9999px; top: 0;
  background: var(--surface-2); color: var(--text); border: 1px solid var(--line);
  padding: 9px 14px; border-radius: 10px; font-size: 14px; font-weight: 600;
}
.skip:focus { left: 12px; top: 12px; z-index: 10000; }
:focus-visible { outline: 2px solid var(--top4); outline-offset: 3px; border-radius: 5px; }

header { border-bottom: 1px solid var(--line); padding-bottom: 14px; }
h1 { font-size: 22px; font-weight: 700; letter-spacing: -.022em; margin: 0 0 5px; }
h2 {
  font-size: 15px; font-weight: 700; letter-spacing: .005em; margin: 34px 0 8px;
  display: flex; align-items: center; gap: 8px;
}
h2::before {
  content: ""; flex: none; width: 3px; height: 15px; border-radius: 2px;
  background: var(--rail);
}
.meta, .muted { color: var(--text2); font-size: 13px; }
.meta { margin: 0; }
p.muted { margin: 6px 0 10px; }
.stale {
  background: var(--bot4); color: #fff; padding: 3px 9px; border-radius: 6px;
  font-size: 12px; font-weight: 600; letter-spacing: .01em; display: inline-block;
}

/* 안내 상자(게이트 정지·패치 배너·덱 없음). 테두리 대신 살짝 떠 있는 표면. */
.card {
  background: var(--surface-2); border-radius: 12px; padding: 13px 15px;
  margin: 12px 0; box-shadow: var(--shadow);
}
.card h3 { margin: 0 0 4px; font-size: 15px; font-weight: 700; letter-spacing: -.01em; }
.card ul { margin: 6px 0; padding-left: 18px; }
.card li { font-size: 13px; margin: 2px 0; }

/* 덱 카드. 테두리 대신 왼쪽 레일 하나 — 색이 Δ의 부호를 그대로 말한다. */
.deck {
  position: relative; background: var(--surface-2); box-shadow: var(--shadow);
  padding: 14px 15px 15px; margin: 10px 0;
  border-radius: 6px 14px 14px 6px;
  border-left: 4px solid var(--rail);
}
.deck.low { border-left-color: var(--top4); }
.deck.high { border-left-color: var(--bot4); }
.deck-name { margin: 0 0 3px; font-size: 17px; font-weight: 700; letter-spacing: -.015em; }

.figures {
  display: flex; flex-wrap: wrap; align-items: flex-end; gap: 12px 18px;
  margin: 13px 0 2px;
}
.fig { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.fig-label {
  font-size: 10px; font-weight: 600; letter-spacing: .085em; color: var(--text2);
  text-transform: uppercase; white-space: nowrap;
}
.fig-value { font-size: 15px; font-weight: 500; line-height: 1.15; }
.fig.hero { padding-right: 18px; border-right: 1px solid var(--line); }
.fig.hero .fig-value { font-size: 34px; font-weight: 700; letter-spacing: -.045em; }
.fig.hero.low .fig-value { color: var(--top4); }
.fig.hero.high .fig-value { color: var(--bot4); }
.fig.sec .fig-value { font-size: 22px; font-weight: 600; letter-spacing: -.025em; }
/* 값이 숫자가 아닐 때(표본 없음 등). 히어로 자리라도 크게 키우지 않는다. */
.fig-value.none { font-size: 14px; font-weight: 500; color: var(--text2); }
.fig.hero .fig-value.none { font-size: 19px; }
.fig-note { font-size: 11px; font-weight: 600; color: var(--text2); margin-top: 2px; }

/* 막대 높이는 dist_bars가 px로 박는다(최대 46). 넓은 화면에서 폭까지 늘어나면
   분포가 아니라 덩어리로 보여서 컨테이너 폭을 묶어 비율을 모바일과 같게 유지한다. */
.dist, .dist-axis { max-width: 340px; }
.dist { display: flex; align-items: flex-end; gap: 3px; height: 46px; margin: 13px 0 3px; }
.dist-bar { flex: 1; border-radius: 3px 3px 0 0; min-height: 2px; }
.dist-bar.top4 { background: var(--top4); }
.dist-bar.bot4 { background: var(--bot4); }
.dist-axis { display: flex; gap: 3px; }
.dist-axis span {
  flex: 1; text-align: center; font-size: 10px; color: var(--text2);
  font-family: "JetBrains Mono", ui-monospace, Consolas, monospace;
}
.legend { font-size: 12px; color: var(--text2); margin: 7px 0 0; }
.legend i {
  display: inline-block; width: 9px; height: 9px; border-radius: 2px;
  margin-right: 4px; vertical-align: baseline;
}

/* 빌드업 경로는 상자 네 개가 아니라 순서 하나다 — 세로 레일로 잇는다. */
.route { list-style: none; margin: 12px 0 0; padding: 2px 0 2px 20px; position: relative; }
.route::before {
  content: ""; position: absolute; left: 4px; top: 10px; bottom: 10px;
  width: 2px; border-radius: 1px; background: var(--rail);
}
.route li { position: relative; padding: 4px 0; font-size: 13px; }
.route li::before {
  content: ""; position: absolute; left: -20px; top: 12px;
  width: 10px; height: 10px; border-radius: 50%; box-sizing: border-box;
  background: var(--surface-2); border: 2px solid var(--rail);
}
.route li:last-child::before { background: var(--text2); border-color: var(--text2); }
.route b {
  display: block; font-size: 10px; font-weight: 600; letter-spacing: .085em;
  color: var(--text2); text-transform: uppercase;
}

table { border-collapse: collapse; width: 100%; font-size: 13.5px; }
th {
  font-size: 10px; font-weight: 600; letter-spacing: .085em; color: var(--text2);
  text-transform: uppercase;
}
td, th { border-bottom: 1px solid var(--line); padding: 7px 6px; text-align: left; }
td.n, th.n { text-align: right; }
table tr:last-child td { border-bottom: 0; }
.scroll { overflow-x: auto; -webkit-overflow-scrolling: touch; }

details { margin: 3px 0; border-radius: 10px; }
details[open] { background: var(--surface-2); padding-bottom: 6px; }
summary {
  cursor: pointer; padding: 7px 9px; border-radius: 10px; font-size: 14px;
  transition: background-color 180ms ease, color 180ms ease;
}
summary:hover { background: var(--surface-2); color: var(--top4); }
summary:active { background: var(--mid); }
details[open] summary { font-weight: 600; }
details .scroll { padding: 0 9px 2px; }

.sub {
  font-size: 10px; font-weight: 700; letter-spacing: .095em; color: var(--text2);
  text-transform: uppercase; margin: 18px 0 4px;
}
blockquote {
  margin: 8px 0; padding: 3px 0 3px 12px; border-left: 3px solid var(--rail);
  border-radius: 0 5px 5px 0; color: var(--text2); font-size: 13px;
}
a {
  color: inherit; text-decoration-color: var(--rail); text-underline-offset: 3px;
  transition: color 180ms ease, text-decoration-color 180ms ease;
}
a:hover { color: var(--top4); text-decoration-color: currentColor; }
a:active { opacity: .7; }
footer {
  margin-top: 34px; padding-top: 14px; border-top: 1px solid var(--line);
  color: var(--text2); font-size: 12px;
}
footer p { margin: 0; }
@media (max-width: 420px) {
  body { padding: 16px 13px 36px; }
  .fig.hero { padding-right: 14px; }
  .fig.hero .fig-value { font-size: 31px; }
}
@media (prefers-reduced-motion: reduce) {
  * { transition-duration: 1ms !important; animation-duration: 1ms !important; }
}
""".strip().replace("GRAIN_URI", _GRAIN)

_STAGE_LABEL = {"stage-2": "2스테이지", "stage-3": "3스테이지",
                "stage-4": "4스테이지", "stage-5": "5스테이지"}

# 갱신이 끊기면 Pages는 마지막 페이지를 계속 내준다. 돌지 않은 빌드는 자기가 늙었다는 걸
# 알 수 없으니, 페이지가 body[data-generated]를 읽어 스스로 나이를 재고 배지를 켠다.
# 스크립트가 죽어 있으면 배지는 hidden인 채로 남고 나머지는 지금과 똑같이 보인다.
STALE_SCRIPT = """<script>
(function () {
  var box = document.getElementById("stale-box");
  var iso = document.body.getAttribute("data-generated");
  if (!box || !iso || !box.hidden) return;   // 서버가 이미 띄웠으면 그대로 둔다
  var hours = Math.floor((Date.now() - Date.parse(iso)) / 3600000);
  if (!(hours >= 24)) return;                // 파싱 실패(NaN)면 아무것도 하지 않는다
  box.firstElementChild.textContent = hours + "시간 전 데이터 — 갱신 실패 중";
  box.hidden = false;
})();
</script>"""

DESCRIPTION = ("브론즈·실버·골드 구간 전용 롤토체스 치트시트. 브실골과 다이아+ "
               "평균등수 격차로 내 티어에서 실제로 잘 나오는 덱만 추린다.")


def _e(value):
    return _html.escape(str(value), quote=True)


def dist_bars(dist):
    """등수분포 막대 여덟 개. 탑4는 파랑, 하위4는 빨강.

    색만으로 뜻을 전달하지 않는다 — 각 막대에 aria-label과 title로 값을 붙인다.
    분모는 카드마다 제각각이면 안 된다 — 한 화면에 세 장이 쌓이는데 각자 최대값으로
    맞추면 납작한 덱과 뾰족한 덱의 막대 높이가 같아진다. 0.25로 고정하고,
    그보다 높은 막대가 있으면 그 값까지 늘려 잘리지 않게 한다.
    """
    top = max(0.25, max(dist) if dist else 0.0)
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


def _patch_text(patch):
    """패치 번호면 "패치 18.2", 아니면 정직하게 "집계 회차 409".

    patch는 변화 감지용 내부 키를 겸해서 진짜 패치 번호가 아닐 수 있다.
    출처 없는 주장은 안 올린다 — 클러스터 id를 패치 번호라고 부르지 않는다.
    """
    if not patch:
        return "패치 정보 없음"
    return f"패치 {_e(patch)}" if is_patch_number(patch) else f"집계 회차 {_e(patch)}"


def _delta_hero(delta):
    """카드의 초점. (레일 클래스, 히어로 블록)을 돌려준다.

    이 도구가 존재하는 이유가 Δ다. 나머지 숫자보다 두 배 크게, 부호대로 색을 입힌다.
    """
    if delta is None:
        return "", ('<div class="fig hero">'
                    '<span class="fig-label">Δ 티어 격차</span>'
                    '<b class="fig-value none">잴 수 없음</b>'
                    '<span class="fig-note">고티어 표본 없음</span></div>')
    kind = "low" if delta < 0 else "high"
    note = "저티어 전용" if delta < 0 else "고티어 전용"
    return kind, (f'<div class="fig hero {kind}">'
                  f'<span class="fig-label">Δ 티어 격차</span>'
                  f'<b class="fig-value num">{delta:+.2f}</b>'
                  f'<span class="fig-note">{note}</span></div>')


def _route(steps):
    if not steps:
        return ('<p class="muted">단계 경로 없음 — 이 덱은 다이아+ 경로와 '
                '유닛이 충분히 겹치지 않아 억지로 잇지 않았다.</p>')
    cells = []
    for step in steps:
        label = _STAGE_LABEL.get(step["stage"], step["stage"])
        units = ", ".join(_e(u) for u in step["units"])
        avp = "" if step.get("avp") is None else f' · 평균 {step["avp"]:.2f}'
        cells.append(f"<li><b>{_e(label)}{avp}</b>{units}</li>")
    return ('<p class="muted">단계 경로 — 다이아+ 데이터다. 브실골 표본으로는 '
            '단계별 보드를 구할 수 없다.</p>'
            f'<ol class="route">{"".join(cells)}</ol>')


def _deck_card(deck):
    # 한글이 모노 스택으로 새면 자간이 벌어져 숫자처럼 안 읽힌다 — num은 숫자에만 붙인다.
    if deck["avp_high"] is None:
        high = '<b class="fig-value none">표본 없음</b>'
    else:
        high = f'<b class="fig-value num">{deck["avp_high"]:.2f}</b>'
    kind, hero = _delta_hero(deck["delta"])
    return f"""<article class="deck {kind}">
<h3 class="deck-name">{_e(deck["name"])}</h3>
<p class="meta">표본 <span class="num">{deck["count"]:,}</span>판</p>
<div class="figures">
{hero}
<div class="fig sec"><span class="fig-label">브실골 평균등수</span>
<b class="fig-value num">{deck["avp_low"]:.2f}</b></div>
<div class="fig"><span class="fig-label">다이아+ 평균등수</span>
{high}</div>
<div class="fig"><span class="fig-label">픽률</span>
<b class="fig-value num">{deck["pick_rate"]:.1%}</b></div>
<div class="fig"><span class="fig-label">기대 경합</span>
<b class="fig-value"><span class="num">{deck["expected_contest"]:.1f}</span>명</b></div>
</div>
{dist_bars(deck["dist"])}
<p class="legend">
<i style="background:var(--top4)"></i>1~4등
<i style="background:var(--bot4);margin-left:10px"></i>5~8등
· 탑4 {sum(deck["dist"][:4]):.0%}
</p>
{_route(deck.get("route") or [])}
</article>"""


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
        blocks.append(f'<h3 class="sub">{_e(label)}</h3>{"".join(items)}')
    return (f'<section><h2>{_e(title)}</h2>'
            f'<p class="muted">손에 들어온 유닛으로 덱을 찾는다.</p>'
            f'{"".join(blocks)}</section>')


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
            f'<section><h2>{_e(section["title"])}</h2>{note}{quote}'
            f'<div class="scroll"><table>{rows}</table></div>'
            f'<p class="muted"><a href="{_e(section["source"])}">출처 원문</a></p></section>'
        )
    return "".join(blocks)


def _gate_stop_card(message):
    """게이트 정지 안내 — 존재하면 페이지에서 가장 먼저 보인다.

    아래 기본기 화면은 이 문제와 무관하게 그대로 유효하다는 것을 분명히 한다.
    """
    if not message:
        return ""
    return (f'<div class="card"><h3>덱 통계 없음</h3>'
            f'<p class="muted">{_e(message)} 아래 기본기 정보는 이 문제와 무관하니 '
            '그대로 봐도 된다. 집계가 이번 셋으로 넘어오면 다음 갱신 때 자동으로 채워진다.'
            '</p></div>')


def _diff_banner(diff, summary):
    if not diff.get("patch_changed"):
        return ""
    lines = []
    for row in diff.get("moved", []):
        arrow = "나빠짐" if row["after"] > row["before"] else "좋아짐"
        lines.append(f'<li>{_e(row["name"])} <span class="num">{row["before"]:.2f} → '
                     f'{row["after"]:.2f}</span> ({arrow})</li>')
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
    to_patch = diff.get("to_patch")
    headline = f'패치 {_e(to_patch)} 적용됨' if is_patch_number(to_patch) else "집계 회차가 바뀜"
    return (f'<div class="card"><h3>{headline}</h3>'
            f'<div class="meta">직전 {_patch_text(diff.get("from_patch"))} 대비</div>'
            f'{body}{official}'
            '<p class="muted">패치 직후 3~5일은 데이터가 안 굳는다. '
            '이 숫자만 보고 덱을 버리지 마라.</p></div>')


def page(context):
    """완성된 HTML 한 장."""
    # 배지는 항상 자리를 잡아두고 숨겨둔다 — 스크립트가 나중에 채울 수 있게.
    # 빌드가 아예 안 돌면 서버는 자기 나이를 모른다. 그때는 페이지가 스스로 잰다.
    stale_text = (f'{context["stale_hours"]}시간 전 데이터 — 갱신 실패 중'
                  if context["stale_hours"] >= 24 else "")
    stale = (f'<p id="stale-box"{"" if stale_text else " hidden"}>'
             f'<span class="stale">{stale_text}</span></p>')

    if context["decks"]:
        decks_html = "".join(_deck_card(deck) for deck in context["decks"])
        heading = f'이번 패치 너의 {len(context["decks"])}덱'
    else:
        decks_html = ('<div class="card"><h3>아직 데이터가 없다</h3>'
                      '<p class="muted">셋이 막 바뀌었거나 표본이 하한에 못 미친다. '
                      '집계가 쌓이면 자동으로 채워진다. 그동안은 아래 기본기를 본다.</p></div>')
        heading = "추천할 덱이 아직 없다"

    return f"""<!doctype html>
<html lang="ko"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>브실골 롤체 치트시트</title>
<meta name="description" content="{_e(DESCRIPTION)}">
<meta name="theme-color" content="#fcfcfb" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#1a1a19" media="(prefers-color-scheme: dark)">
<meta property="og:type" content="website">
<meta property="og:locale" content="ko_KR">
<meta property="og:title" content="브실골 롤체 치트시트">
<meta property="og:description" content="{_e(DESCRIPTION)}">
<link rel="icon" href="{FAVICON}">
{FONT_LINKS}
<style>{CSS}</style>
</head><body data-generated="{_e(context.get("generated_iso", ""))}">
<a class="skip" href="#main">본문으로 건너뛰기</a>
<div class="grain" aria-hidden="true"></div>
<header>
<h1>브실골 롤체 치트시트</h1>
<p class="meta">{_e(context["set"])} · {_patch_text(context["patch"])} ·
KR 브론즈~골드 <span class="num">{context["sample_days"]}</span>일
<span class="num">{context["total_games"]:,}</span>판 ·
{_e(context["generated_at"])} 기준</p>
</header>
<main id="main">
{_gate_stop_card(context.get("gate_stop"))}
{stale}
{_diff_banner(context["diff"], context.get("notes"))}
<section>
<h2>{_e(heading)}</h2>
<p class="muted">Δ = 브실골 평균등수 − 다이아+ 평균등수. 음수면 네 티어에서 더 잘 나오는 덱이다.
평균등수만으로 줄 세우지 않는다 — 등수 분포와 픽률을 같이 본다.
기대 경합은 8인 로비에서 나를 뺀 일곱 명 중 같은 덱을 잡는 사람 수다.</p>
{decks_html}
</section>
{index_section("유닛으로 찾기", context.get("indexes") or {}, context.get("name_of", str))}
{_fundamentals(context["fundamentals"])}
</main>
<footer>
<p>덱 통계·단계 경로: MetaTFT · 한글 이름표: Riot Data Dragon<br>
Riot Games가 승인하거나 후원한 프로젝트가 아니다.</p>
</footer>
{STALE_SCRIPT}
</body></html>"""

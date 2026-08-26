# tft-challenger 구현 계획 — 2부 (Task 6~10)

> 1부(`2026-08-26-tft-challenger.md`)의 **전역 제약**이 여기에도 그대로 적용된다.
> Task 1~5를 끝낸 뒤에 이어서 진행한다.

---

### Task 6: 축약 스냅샷과 패치 diff

git이 이 프로젝트의 상태 저장소다. 매일 축약본을 커밋하면 그 히스토리가 패치 diff의 입력이 된다. 외부 의존이 하나도 안 늘어난다.

**Files:**
- Create: `src/patchdiff.py`, `tests/test_patchdiff.py`

**Interfaces:**
- Consumes: `sources.DAILY`
- Produces:
  - `patchdiff.save(snapshot: dict, day: str) -> Path` — `data/daily/<day>.json`에 저장
  - `patchdiff.load_previous(before: str) -> dict | None` — `before`보다 앞선 날짜 중 가장 최근 스냅샷
  - `patchdiff.compare(previous: dict | None, current: dict, top_n: int = 3) -> dict` — `{"patch_changed": bool, "from_patch", "to_patch", "moved": [...], "entered": [...], "left": [...]}`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_patchdiff.py`:

```python
from src.patchdiff import compare, load_previous, save


def _snap(patch, decks):
    return {"patch": patch, "decks": [{"cluster": c, "name": n, "avp_low": a}
                                      for c, n, a in decks]}


def test_직전이_없으면_변화없음으로_본다():
    result = compare(None, _snap("18.1", [("410000", "A덱", 4.1)]))
    assert result["patch_changed"] is False
    assert result["moved"] == []
    assert result["entered"] == []


def test_패치가_바뀌면_표시한다():
    previous = _snap("18.1", [("410000", "A덱", 4.1)])
    current = _snap("18.2", [("410000", "A덱", 4.1)])
    result = compare(previous, current)
    assert result["patch_changed"] is True
    assert result["from_patch"] == "18.1"
    assert result["to_patch"] == "18.2"


def test_평균등수_변화를_잡는다():
    previous = _snap("18.1", [("410000", "A덱", 4.10)])
    current = _snap("18.2", [("410000", "A덱", 4.55)])
    moved = compare(previous, current)["moved"]
    assert len(moved) == 1
    assert moved[0]["cluster"] == "410000"
    assert moved[0]["before"] == 4.10
    assert moved[0]["after"] == 4.55


def test_새로_들어오고_빠진_덱을_잡는다():
    previous = _snap("18.1", [("410000", "A덱", 4.1), ("410001", "B덱", 4.3)])
    current = _snap("18.2", [("410000", "A덱", 4.1), ("410002", "C덱", 3.9)])
    result = compare(previous, current, top_n=3)
    assert [d["cluster"] for d in result["entered"]] == ["410002"]
    assert [d["cluster"] for d in result["left"]] == ["410001"]


def test_상위_N개만_비교한다():
    previous = _snap("18.1", [("A", "a", 4.0), ("B", "b", 4.1), ("C", "c", 4.2), ("D", "d", 4.3)])
    current = _snap("18.1", [("A", "a", 4.0), ("B", "b", 4.1), ("C", "c", 4.2), ("D", "d", 9.9)])
    # D는 상위 3개 밖이라 변화가 잡히지 않는다
    assert compare(previous, current, top_n=3)["moved"] == []


def test_저장하고_직전을_되읽는다(tmp_path, monkeypatch):
    from src import patchdiff
    monkeypatch.setattr(patchdiff, "DAILY", tmp_path)
    save(_snap("18.1", [("410000", "A덱", 4.1)]), "2026-09-01")
    save(_snap("18.2", [("410000", "A덱", 4.5)]), "2026-09-11")
    previous = load_previous(before="2026-09-11")
    assert previous["patch"] == "18.1"


def test_직전이_없으면_None을_준다(tmp_path, monkeypatch):
    from src import patchdiff
    monkeypatch.setattr(patchdiff, "DAILY", tmp_path)
    save(_snap("18.1", [("410000", "A덱", 4.1)]), "2026-09-01")
    assert load_previous(before="2026-09-01") is None
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `python -m pytest tests/test_patchdiff.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.patchdiff'`

- [ ] **Step 3: `src/patchdiff.py`를 쓴다**

```python
"""축약 스냅샷 저장과 패치 간 비교.

매일 data/daily/<날짜>.json을 커밋한다. 그 git 히스토리가 곧 메타 변천사이고,
패치 diff는 외부 의존 없이 여기서 나온다.
원본(data/raw/)은 커밋하지 않는다 — comp_options 하나가 5.9MB다.
"""

import json

from .sources import DAILY


def save(snapshot, day):
    """스냅샷을 data/daily/<day>.json으로 저장한다."""
    DAILY.mkdir(parents=True, exist_ok=True)
    path = DAILY / f"{day}.json"
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")
    return path


def load_previous(before):
    """`before`보다 앞선 날짜 중 가장 최근 스냅샷. 없으면 None."""
    if not DAILY.exists():
        return None
    earlier = sorted(p for p in DAILY.glob("*.json") if p.stem < before)
    if not earlier:
        return None
    return json.loads(earlier[-1].read_text(encoding="utf-8"))


def compare(previous, current, top_n=3):
    """직전 스냅샷과 비교한다. 상위 top_n개 덱만 본다 — 꼬리는 노이즈다."""
    empty = {"patch_changed": False, "from_patch": None,
             "to_patch": current.get("patch"), "moved": [], "entered": [], "left": []}
    if previous is None:
        return empty

    before = {d["cluster"]: d for d in previous.get("decks", [])[:top_n]}
    after = {d["cluster"]: d for d in current.get("decks", [])[:top_n]}

    moved = [{"cluster": cluster,
              "name": after[cluster].get("name"),
              "before": before[cluster]["avp_low"],
              "after": after[cluster]["avp_low"]}
             for cluster in after
             if cluster in before and before[cluster]["avp_low"] != after[cluster]["avp_low"]]

    return {
        "patch_changed": previous.get("patch") != current.get("patch"),
        "from_patch": previous.get("patch"),
        "to_patch": current.get("patch"),
        "moved": moved,
        "entered": [after[c] for c in after if c not in before],
        "left": [before[c] for c in before if c not in after],
    }
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run: `python -m pytest tests/ -q`
Expected: PASS — 39 passed

- [ ] **Step 5: 커밋한다**

```bash
git add src/patchdiff.py tests/test_patchdiff.py
git commit -m "feat: 축약 스냅샷과 패치 diff

data/daily/ 를 매일 커밋해 git 히스토리를 메타 변천사로 쓴다.
패치 변화 감지에 외부 의존이 없다."
git push origin main
```

---

### Task 7: 기본기 화면 · 덱 카드 · 등수분포 · 파이프라인

여기서 처음으로 눈에 보이는 게 나온다. 셋18 데이터가 아직 안 찼어도 기본기 화면은 항상 뜬다 — 그게 데이터 없는 날의 화면이기도 하다.

**Files:**
- Create: `src/render.py`, `src/build.py`, `data/fundamentals.json`, `tests/test_render.py`
- Modify: `data/config.json` (`min_games`, `top_n` 추가)

**Interfaces:**
- Consumes: `comps.merge_delta`, `names.build_index`/`ko`, `paths.match_stage5`/`route`, `patchdiff.save`/`load_previous`/`compare`, `validate.check_set`/`pin_cluster`, `fetch.fetch_all`
- Produces:
  - `render.page(context: dict) -> str` — 완성된 HTML 문자열
  - `render.dist_bars(dist: list[float]) -> str`
  - `build.main() -> int` — 종료 코드 (0 성공, 2 셋 불일치)
  - `context` 스키마: `{"set","patch","generated_at","total_games","sample_days","stale_hours","decks":[...],"diff":{...},"fundamentals":{...},"notes":None}`
    각 덱: `{"cluster","name","avp_low","avp_high","delta","count","pick_rate","expected_contest","dist","route"}`

- [ ] **Step 1: 설정에 표본 하한을 추가한다**

`data/config.json`에 두 줄 더한다. 표본이 적은 덱은 Δ가 요동쳐서 3덱 선정을 망친다.

```json
{
  "expected_set": "TFTSet18",
  "server": "KR",
  "low_rank": "BRONZE,SILVER,GOLD",
  "high_rank": "DIAMOND,MASTER,GRANDMASTER,CHALLENGER",
  "days": 3,
  "ddragon_set_path": "/Sets/TFTSet18/",
  "min_games": 200,
  "top_n": 3
}
```

- [ ] **Step 2: 기본기 데이터를 만든다**

`data/fundamentals.json` — 여기 들어가는 모든 항목에 살아있는 출처 URL이 있어야 한다. 아래 숫자는 2026-08-26에 라이엇 한국어 패치노트 원문에서 그대로 확인한 것이다.

```json
{
  "sections": [
    {
      "title": "네가 없던 사이 바뀐 것 (패치 16.1)",
      "note": "그랜드마스터 시절 감각과 지금 게임이 어긋나는 지점. 8레벨이 더는 공짜가 아니고, 9·10레벨은 싸졌다.",
      "source": "https://teamfighttactics.leagueoflegends.com/ko-kr/news/game-updates/teamfight-tactics-patch-16-1/",
      "quote": "8레벨에 도달하는 것은 다소 어려워지겠지만, 원하는 4단계 유닛 찾기는 훨씬 더 안정적이고 보람 있게 느껴질 것입니다. 8레벨에서 9레벨로, 10레벨로 올라가는 과정이 조금 더 쉬워져, 탄탄한 8레벨 조합을 구축하는 데 이점을 부여합니다.",
      "rows": [
        ["8레벨 필요 경험치", "48", "60"],
        ["9레벨 필요 경험치", "76", "68"],
        ["10레벨 필요 경험치", "84", "68"],
        ["8레벨 상점 확률", "17/24/32/24/3%", "15/20/32/30/3%"],
        ["9레벨 상점 확률", "12/18/25/33/12%", "10/17/25/33/15%"],
        ["스테이지 3 기본 피해량", "5", "6"],
        ["스테이지 4 기본 피해량", "8", "7"]
      ]
    },
    {
      "title": "이번 셋 (신비의 숲 · 패치 18.1)",
      "note": "첫 언리얼 엔진 셋. 카오셀이 돌아왔고, 군중 제어 후 타겟 재설정이 사라져 포지셔닝 계산이 달라졌다.",
      "source": "https://teamfighttactics.leagueoflegends.com/ko-kr/news/game-updates/teamfight-tactics-patch-18-1/",
      "rows": [
        ["세트 체계", "수호령", "챔피언·전투·상점·골드및경험치·위험·아이템·기타 7분류"]
      ]
    }
  ]
}
```

- [ ] **Step 3: 출처 URL이 살아있는지 확인하고, 죽은 항목은 지운다**

Run:
```bash
python -c "
import json, urllib.request
from src import sources
data = json.loads(open('data/fundamentals.json', encoding='utf-8').read())
for section in data['sections']:
    url = section['source']
    request = urllib.request.Request(url, headers={'User-Agent': sources.UA})
    with urllib.request.urlopen(request, timeout=30) as response:
        print(response.status, section['title'])
"
```
Expected: 두 줄 모두 `200`. 200이 아닌 항목은 `fundamentals.json`에서 **지운다** — 출처 없는 주장은 페이지에 올리지 않는다는 게 전역 제약이다.

- [ ] **Step 4: 실패하는 테스트를 쓴다**

`tests/test_render.py`:

```python
from src.render import dist_bars, page


def _context(**overrides):
    context = {
        "set": "TFTSet18", "patch": "18.1",
        "generated_at": "2026-09-01 05:00 KST",
        "total_games": 192121, "sample_days": 3, "stale_hours": 0,
        "decks": [{
            "cluster": "410000", "name": "자야 리롤",
            "avp_low": 4.08, "avp_high": 4.61, "delta": -0.53,
            "count": 1240, "pick_rate": 0.11, "expected_contest": 0.88,
            "dist": [0.20, 0.16, 0.13, 0.11, 0.10, 0.10, 0.10, 0.10],
            "route": [{"stage": "stage-2", "units": ["자야"], "avp": 4.5}],
        }],
        "diff": {"patch_changed": False, "from_patch": None, "to_patch": "18.1",
                 "moved": [], "entered": [], "left": []},
        "fundamentals": {"sections": []},
        "notes": None,
    }
    context.update(overrides)
    return context


def test_등수분포_막대가_여덟_개다():
    html = dist_bars([0.125] * 8)
    assert html.count("dist-bar") == 8


def test_탑4와_하위4가_다른_색_클래스를_쓴다():
    html = dist_bars([0.125] * 8)
    assert html.count("dist-bar top4") == 4
    assert html.count("dist-bar bot4") == 4


def test_막대마다_읽을_수_있는_설명이_붙는다():
    # 색만으로 정보를 주면 안 된다. 스크린리더와 호버 양쪽에 값이 있어야 한다.
    html = dist_bars([0.20, 0.16, 0.13, 0.11, 0.10, 0.10, 0.10, 0.10])
    assert 'aria-label="1등 20%"' in html
    assert 'title="1등 20%"' in html


def test_페이지에_덱_이름과_델타가_들어간다():
    html = page(_context())
    assert "자야 리롤" in html
    assert "-0.53" in html


def test_델타가_음수면_저티어_표식이_붙는다():
    assert "저티어 전용" in page(_context())


def test_델타가_양수면_고티어_표식이_붙는다():
    context = _context()
    context["decks"][0]["delta"] = 0.42
    assert "고티어 전용" in page(context)


def test_데이터가_없어도_기본기_화면은_뜬다():
    context = _context(decks=[], fundamentals={"sections": [
        {"title": "레벨 곡선", "note": "", "source": "https://example.com", "rows": [["8레벨", "48", "60"]]}
    ]})
    html = page(context)
    assert "레벨 곡선" in html
    assert "아직 데이터가 없다" in html


def test_오래된_데이터면_경고_배지가_뜬다():
    html = page(_context(stale_hours=30))
    assert "30시간 전" in html


def test_라이트와_다크_토큰이_모두_정의된다():
    html = page(_context())
    assert "#fcfcfb" in html and "#1a1a19" in html
    assert 'prefers-color-scheme: dark' in html
    assert '[data-theme="dark"]' in html
```

- [ ] **Step 5: 테스트가 실패하는지 확인한다**

Run: `python -m pytest tests/test_render.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.render'`

- [ ] **Step 6: `src/render.py`를 쓴다**

```python
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


def _diff_banner(diff):
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
    return (f'<div class="card"><h3>패치 {_e(diff["to_patch"])} 적용됨</h3>'
            f'<div class="meta">직전 {_e(diff["from_patch"])} 대비</div>{body}'
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
{_diff_banner(context["diff"])}
<h2>이번 패치 너의 {len(context["decks"])}덱</h2>
<p class="muted">Δ = 브실골 평균등수 − 다이아+ 평균등수. 음수면 네 티어에서 더 잘 나오는 덱이다.
평균등수만으로 줄 세우지 않는다 — 등수 분포와 픽률을 같이 본다.</p>
{decks_html}
{_fundamentals(context["fundamentals"])}
<h2>출처</h2>
<p class="muted">덱 통계·단계 경로: MetaTFT · 한글 이름표: Riot Data Dragon<br>
Riot Games가 승인하거나 후원한 프로젝트가 아니다.</p>
</body></html>"""
```

- [ ] **Step 7: 테스트가 통과하는지 확인한다**

Run: `python -m pytest tests/ -q`
Expected: PASS — 49 passed

- [ ] **Step 8: `src/build.py`를 쓴다**

```python
"""파이프라인. 수집 -> 게이트 -> 조인 -> 스냅샷 -> 렌더."""

import json
import sys
from datetime import datetime, timedelta, timezone

from . import comps, fetch, names, patchdiff, paths, render, sources, validate

KST = timezone(timedelta(hours=9))


def _patch_label(payloads):
    """패치 식별자.

    목적은 예쁜 이름표가 아니라 "바뀌었는가"를 감지하는 것이다.
    display_patch가 있으면 쓰고, 없으면 클러스터 id로 대체한다 —
    클러스터는 패치마다 회전하므로 대체값으로도 감지가 된다.
    """
    for key in ("comps_stats_low", "comps_data"):
        label = payloads.get(key, {}).get("display_patch")
        if label:
            return str(label)
    return f"클러스터 {payloads['latest_cluster_id']['cluster_id']}"


def build_context(payloads, cfg, now):
    """받아온 원본에서 렌더용 컨텍스트를 만든다."""
    index = names.build_index(
        champion=payloads["champion"], trait=payloads["trait"],
        item=payloads["item"], augments=payloads["augments"],
        set_path=cfg["ddragon_set_path"],
    )

    low, total = comps.parse_stats(payloads["comps_stats_low"])
    high, _ = comps.parse_stats(payloads["comps_stats_high"])
    rows = [row for row in comps.merge_delta(low, total, high)
            if row["count"] >= cfg["min_games"]]

    final = paths.final_units(payloads["comps_data"])
    matched = paths.match_stage5(final, payloads["early"])

    decks = []
    for row in rows[:cfg["top_n"]]:
        units = sorted(final.get(row["cluster"], set()))
        row = dict(row)
        row["name"] = " · ".join(names.ko(index, unit) for unit in units[:3]) or row["cluster"]
        row["route"] = []
        if row["cluster"] in matched:
            for step in paths.route(payloads["early"], matched[row["cluster"]]):
                row["route"].append({
                    "stage": step["stage"],
                    "units": [names.ko(index, unit) for unit in step["units"]],
                    "avp": step["avp"],
                })
        decks.append(row)

    patch = _patch_label(payloads)
    snapshot = {"patch": patch, "decks": [
        {"cluster": d["cluster"], "name": d["name"], "avp_low": d["avp_low"]} for d in decks]}

    day = now.strftime("%Y-%m-%d")
    diff = patchdiff.compare(patchdiff.load_previous(before=day), snapshot, cfg["top_n"])
    patchdiff.save(snapshot, day)

    return {
        "set": payloads["latest_cluster_id"]["tft_set"],
        "patch": patch,
        "generated_at": now.strftime("%Y-%m-%d %H:%M KST"),
        "total_games": total,
        "sample_days": cfg["days"],
        "stale_hours": 0,
        "decks": decks,
        "diff": diff,
        "fundamentals": json.loads(
            (sources.ROOT / "data" / "fundamentals.json").read_text(encoding="utf-8")),
        "notes": None,
    }


def main():
    cfg = sources.load_config()
    now = datetime.now(KST)
    payloads = fetch.fetch_all(cfg)

    try:
        validate.check_set(payloads, cfg["expected_set"])
        validate.pin_cluster(payloads)
    except (validate.SetMismatch, validate.ClusterMismatch) as exc:
        # 조용히 옛날 데이터를 내놓느니 시끄럽게 죽는다.
        print(f"게이트 정지: {exc}", file=sys.stderr)
        return 2

    context = build_context(payloads, cfg, now)
    sources.DIST.mkdir(parents=True, exist_ok=True)
    (sources.DIST / "index.html").write_text(render.page(context), encoding="utf-8")
    print(f"렌더 완료: 덱 {len(context['decks'])}개, 표본 {context['total_games']:,}판")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 9: 실제로 돌린다**

Run: `python -m src.build; echo "종료코드 $?"`

Expected — 둘 중 하나이고 **둘 다 정상 동작이다**:
- 집계가 아직 셋17이면: `게이트 정지: 셋 불일치 ...`, 종료코드 2. 이게 셋 게이트가 일하는 모습이다.
- 셋18 데이터가 찼으면: `렌더 완료: 덱 3개, 표본 ...판`, 종료코드 0.

종료코드 2가 나오면 게이트를 잠시 우회해 렌더 경로를 확인한다:
```bash
python -c "
import json
from datetime import datetime, timezone, timedelta
from src import build, sources, render
cfg = sources.load_config()
payloads = {k: json.loads((sources.RAW/f'{k}.json').read_text(encoding='utf-8'))
            for k in ('latest_cluster_id','comps_data','comps_stats_low','comps_stats_high','early','champion','trait','item','augments')}
cfg['ddragon_set_path'] = '/Sets/' + payloads['latest_cluster_id']['tft_set'] + '/'
ctx = build.build_context(payloads, cfg, datetime.now(timezone(timedelta(hours=9))))
sources.DIST.mkdir(parents=True, exist_ok=True)
(sources.DIST/'index.html').write_text(render.page(ctx), encoding='utf-8')
print('덱', len(ctx['decks']), '표본', ctx['total_games'])
"
```

- [ ] **Step 10: 브라우저로 열어 눈으로 본다**

Run: `start dist/index.html` (PowerShell) 또는 파일을 직접 연다.

확인할 것 — 검증기는 색만 보지 레이아웃은 못 본다:
- 폰 너비(390px)로 좁혀도 가로 스크롤이 생기지 않는가
- 등수분포 막대 여덟 개가 보이고 1~4가 파랑, 5~8이 빨강인가
- 막대에 마우스를 올리면 "3등 13%" 같은 값이 뜨는가
- 브라우저를 다크 모드로 바꾸면 배경과 글자가 같이 뒤집히는가
- 숫자가 자릿수마다 흔들리지 않는가(tabular-nums)

- [ ] **Step 11: 커밋한다**

```bash
git add src/render.py src/build.py data/fundamentals.json data/config.json tests/test_render.py data/daily/
git commit -m "feat: 치트시트 렌더와 파이프라인

색상 토큰은 dataviz 검증기 통과값(라이트/다크 전 항목 PASS).
등수분포는 색만으로 뜻을 전달하지 않고 값 라벨을 같이 붙인다.
데이터가 없어도 기본기 화면은 항상 뜬다."
git push origin main
```

---

### Task 8: 색인 넷 — 아이템 · 증강 · 유닛 · 전체 덱

게임 중 실제 진입점은 덱 목록이 아니라 "활 두 개 나왔다"다. 같은 데이터에 색인만 다르게 붙이는 것이라 비용이 싸다.

**Files:**
- Create: `src/indexes.py`, `tests/test_indexes.py`
- Modify: `src/render.py` (색인 섹션 추가), `src/build.py` (컨텍스트에 `indexes` 추가)

**Interfaces:**
- Consumes: `comps.merge_delta` 결과, `paths.final_units`, `names.ko`
- Produces:
  - `indexes.by_unit(decks: list[dict], final: dict[str, set]) -> dict[str, list[dict]]` — 유닛 apiName → 그 유닛을 쓰는 덱 목록(Δ 오름차순)
  - `indexes.build(decks, final, unit_costs) -> dict` — `{"units": {...}, "cost_groups": {...}}`
  - `render.index_section(title: str, groups: dict, name_of) -> str`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/test_indexes.py`:

```python
from src.indexes import build, by_unit

DECKS = [
    {"cluster": "A", "name": "A덱", "delta": -0.5, "avp_low": 4.0},
    {"cluster": "B", "name": "B덱", "delta": 0.2, "avp_low": 4.4},
]
FINAL = {"A": {"DA_18_X", "DA_18_Y"}, "B": {"DA_18_Y", "DA_18_Z"}}


def test_유닛으로_덱을_찾는다():
    result = by_unit(DECKS, FINAL)
    assert [d["cluster"] for d in result["DA_18_Y"]] == ["A", "B"]
    assert [d["cluster"] for d in result["DA_18_X"]] == ["A"]


def test_델타_오름차순으로_정렬된다():
    result = by_unit(DECKS[::-1], FINAL)
    assert result["DA_18_Y"][0]["delta"] == -0.5


def test_표에_없는_덱의_유닛은_색인에_없다():
    result = by_unit([DECKS[0]], FINAL)
    assert "DA_18_Z" not in result


def test_코스트별로_묶는다():
    result = build(DECKS, FINAL, {"DA_18_X": 1, "DA_18_Y": 3, "DA_18_Z": 5})
    assert "DA_18_X" in result["cost_groups"][1]
    assert "DA_18_Y" in result["cost_groups"][3]


def test_코스트를_모르면_0으로_묶는다():
    result = build(DECKS, FINAL, {})
    assert set(result["cost_groups"][0]) == {"DA_18_X", "DA_18_Y", "DA_18_Z"}
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run: `python -m pytest tests/test_indexes.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.indexes'`

- [ ] **Step 3: `src/indexes.py`를 쓴다**

```python
"""색인. 같은 덱 목록을 유닛·코스트 기준으로 다시 꿴다.

게임 중 실제 진입점은 덱 이름이 아니다. 손에 들어온 유닛이 먼저다.
"""

from collections import defaultdict


def by_unit(decks, final):
    """유닛 apiName -> 그 유닛을 쓰는 덱 목록. Δ 오름차순(저티어에서 좋은 덱이 앞)."""
    result = defaultdict(list)
    for deck in decks:
        for unit in final.get(deck["cluster"], set()):
            result[unit].append(deck)
    for unit in result:
        result[unit].sort(key=lambda d: (d["delta"] is None, d["delta"] or 0.0))
    return dict(result)


def build(decks, final, unit_costs):
    """색인 묶음. 코스트를 모르는 유닛은 0번 묶음에 넣는다 — 버리지 않는다."""
    units = by_unit(decks, final)
    cost_groups = defaultdict(list)
    for unit in units:
        cost_groups[unit_costs.get(unit, 0)].append(unit)
    for cost in cost_groups:
        cost_groups[cost].sort()
    return {"units": units, "cost_groups": dict(cost_groups)}
```

- [ ] **Step 4: `src/render.py`에 색인 섹션을 추가한다**

`render.py`의 `_fundamentals` 함수 **바로 앞에** 다음을 넣는다:

```python
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
```

그리고 `page()` 안에서 `{_fundamentals(context["fundamentals"])}` **바로 앞줄에** 다음을 넣는다:

```python
{index_section("유닛으로 찾기", context.get("indexes") or {}, context.get("name_of", str))}
```

- [ ] **Step 5: `src/build.py`의 컨텍스트에 색인을 넣는다**

`build_context`의 `return {` 직전에 다음 두 줄을 넣는다:

```python
    all_rows = [dict(row, name=" · ".join(
        names.ko(index, unit) for unit in sorted(final.get(row["cluster"], set()))[:3]) or row["cluster"])
        for row in rows]
    index_data = indexes.build(all_rows, final, names.unit_costs(payloads["champion"], cfg["ddragon_set_path"]))
```

`return` 딕셔너리에 두 키를 더한다:

```python
        "indexes": index_data,
        "name_of": lambda unit: names.ko(index, unit),
```

파일 맨 위 import 줄에 `indexes`를 더한다:

```python
from . import comps, fetch, indexes, names, patchdiff, paths, render, sources, validate
```

- [ ] **Step 6: 테스트가 통과하는지 확인한다**

Run: `python -m pytest tests/ -q`
Expected: PASS — 54 passed

- [ ] **Step 7: 다시 렌더해서 색인이 붙었는지 본다**

Run: `python -m src.build` (게이트에 막히면 Task 7 Step 9의 우회 스크립트를 쓴다)
그다음 브라우저로 `dist/index.html`을 열어 "유닛으로 찾기" 아래 코스트별 묶음이 보이고, 유닛을 눌렀을 때 덱 표가 펼쳐지는지 확인한다.

- [ ] **Step 8: 커밋한다**

```bash
git add src/indexes.py src/render.py src/build.py tests/test_indexes.py
git commit -m "feat: 유닛 색인 추가

게임 중 진입점은 덱 이름이 아니라 손에 들어온 유닛이다.
아이템·증강 색인은 MetaTFT augment/item 엔드포인트를 붙인 뒤에 같은 틀로 확장한다."
git push origin main
```

---

### Task 9: 패치노트 요약

패치가 감지된 날에만 돈다. 2주에 한 번이라 비용은 무시할 수준이다.

**Files:**
- Create: `src/notes.py`, `tests/test_notes.py`
- Modify: `src/build.py` (패치 감지 시 호출), `src/render.py` (요약 표시), `requirements.txt`

**Interfaces:**
- Consumes: `patchdiff.compare` 결과의 `patch_changed`
- Produces:
  - `notes.fetch_patch_text(patch: str) -> str | None` — 라이엇 한국어 패치노트 본문
  - `notes.summarize(patch_text: str, deck_names: list[str], url: str) -> dict | None` — `{"bullets": [...], "url": ...}`
  - `notes.maybe_summarize(diff: dict, deck_names: list[str]) -> dict | None`

- [ ] **Step 1: `requirements.txt`를 만든다**

```
anthropic>=1.0
```

- [ ] **Step 2: 실패하는 테스트를 쓴다**

API를 실제로 부르지 않는다. 호출 여부를 결정하는 분기와 HTML 정리만 테스트한다.

`tests/test_notes.py`:

```python
from src import notes


def test_패치가_안_바뀌면_부르지_않는다(monkeypatch):
    called = []
    monkeypatch.setattr(notes, "fetch_patch_text", lambda patch: called.append(patch))
    assert notes.maybe_summarize({"patch_changed": False, "to_patch": "18.1"}, []) is None
    assert called == []


def test_패치가_바뀌면_본문을_받아온다(monkeypatch):
    monkeypatch.setattr(notes, "fetch_patch_text", lambda patch: None)
    assert notes.maybe_summarize({"patch_changed": True, "to_patch": "18.2"}, []) is None


def test_패치_URL은_한국어_경로다():
    assert notes.patch_url("18.2").endswith("/ko-kr/news/game-updates/teamfight-tactics-patch-18-2/")


def test_본문에서_태그와_공백을_걷어낸다():
    raw = "<html><script>x</script><p>안녕  하세요</p><style>y</style></html>"
    assert notes.strip_html(raw) == "안녕 하세요"
```

- [ ] **Step 3: 테스트가 실패하는지 확인한다**

Run: `python -m pytest tests/test_notes.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.notes'`

- [ ] **Step 4: `src/notes.py`를 쓴다**

```python
"""패치 감지 시 라이엇 공식 한국어 패치노트를 요약한다.

전체 요약은 이미 어디에나 있다. 우리는 **네 덱에 걸리는 항목만** 뽑는다.
출처 URL을 반드시 같이 내보낸다 — 출처 없는 주장은 페이지에 안 올린다는 게 전역 제약이다.
"""

import html as _html
import json
import os
import re
import urllib.error
import urllib.request

from .sources import UA

_BASE = "https://teamfighttactics.leagueoflegends.com/ko-kr/news/game-updates"
MODEL = "claude-opus-5"


def patch_url(patch):
    return f"{_BASE}/teamfight-tactics-patch-{patch.replace('.', '-')}/"


def strip_html(raw):
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", _html.unescape(text)).strip()


def fetch_patch_text(patch):
    """패치노트 본문. 아직 안 올라왔으면 None."""
    request = urllib.request.Request(patch_url(patch), headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(request, timeout=40) as response:
            return strip_html(response.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError):
        return None


def summarize(patch_text, deck_names, url):
    """패치노트에서 내 덱에 걸리는 항목만 뽑는다. 실패하면 None."""
    import anthropic

    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None

    client = anthropic.Anthropic()
    decks = ", ".join(deck_names) if deck_names else "(추천 덱 없음)"
    prompt = (
        "아래는 롤토체스 공식 한국어 패치노트 본문이다.\n"
        f"내가 지금 쓰는 덱은 다음과 같다: {decks}\n\n"
        "이 덱들에 실제로 영향을 주는 변경만 골라서 한국어 불릿 3~6개로 정리해라.\n"
        "규칙:\n"
        "- 패치노트에 적힌 사실만 쓴다. 추론·평가·예측 금지.\n"
        "- 숫자 변경은 '이전 → 이후' 형태로 그대로 적는다.\n"
        "- 내 덱과 무관한 변경은 넣지 않는다.\n"
        "- 관련 변경이 하나도 없으면 빈 배열을 반환한다.\n\n"
        f"--- 패치노트 본문 ---\n{patch_text[:60000]}"
    )
    try:
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "bullets": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["bullets"],
                        "additionalProperties": False,
                    },
                }
            },
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as exc:  # 요약 실패는 페이지 전체를 죽일 이유가 못 된다
        print(f"패치노트 요약 실패: {exc}")
        return None

    if response.stop_reason == "refusal":
        return None
    text = next((b.text for b in response.content if b.type == "text"), None)
    if not text:
        return None
    return {"bullets": json.loads(text)["bullets"], "url": url}


def maybe_summarize(diff, deck_names):
    """패치가 바뀐 날에만 요약한다."""
    if not diff.get("patch_changed"):
        return None
    patch = diff.get("to_patch")
    text = fetch_patch_text(patch)
    if not text:
        return None
    return summarize(text, deck_names, patch_url(patch))
```

- [ ] **Step 5: `src/build.py`에서 호출한다**

`build_context`의 `patchdiff.save(...)` 바로 다음 줄에 넣는다:

```python
    summary = notes.maybe_summarize(diff, [deck["name"] for deck in decks])
```

`return` 딕셔너리의 `"notes": None,`을 `"notes": summary,`로 바꾼다.
import 줄에 `notes`를 더한다:

```python
from . import comps, fetch, indexes, names, notes, patchdiff, paths, render, sources, validate
```

- [ ] **Step 6: `src/render.py`에서 표시한다**

`_diff_banner` 함수의 `return` 문 바로 앞에 매개변수를 하나 더 받도록 시그니처를 `def _diff_banner(diff, summary):`로 바꾸고, `body` 계산 다음에 넣는다:

```python
    official = ""
    if summary and summary.get("bullets"):
        items = "".join(f"<li>{_e(bullet)}</li>" for bullet in summary["bullets"])
        official = (f'<p class="muted">공식 노트에서 네 덱에 걸리는 항목</p><ul>{items}</ul>'
                    f'<p class="muted"><a href="{_e(summary["url"])}">패치노트 원문</a></p>')
```

`return` 문의 `{body}` 뒤에 `{official}`을 끼워 넣고, `page()` 안의 호출을
`{_diff_banner(context["diff"], context.get("notes"))}`로 바꾼다.

- [ ] **Step 7: 테스트가 통과하는지 확인한다**

Run: `python -m pytest tests/ -q`
Expected: PASS — 58 passed

- [ ] **Step 8: 커밋한다**

```bash
git add src/notes.py src/build.py src/render.py tests/test_notes.py requirements.txt
git commit -m "feat: 패치 감지 시 공식 노트 요약

전체 요약은 이미 어디에나 있다. 내 덱에 걸리는 항목만 뽑고 원문 링크를 같이 낸다.
요약 실패는 페이지 전체를 죽이지 않는다."
git push origin main
```

---

### Task 10: 자동 갱신과 배포

**Files:**
- Create: `.github/workflows/update.yml`
- Modify: `README.md` (사이트 주소 추가)

**Interfaces:**
- Consumes: `python -m src.build` 종료 코드 (0 성공, 2 셋 불일치)
- Produces: GitHub Pages에 배포된 `dist/`

- [ ] **Step 1: 워크플로를 쓴다**

`.github/workflows/update.yml`:

```yaml
name: 갱신과 배포

on:
  schedule:
    # KST 새벽 5시(UTC 20시)와 오후 5시(UTC 8시). 패치 직후에도 하루 안에 잡힌다.
    - cron: "0 20 * * *"
    - cron: "0 8 * * *"
  workflow_dispatch:
  push:
    branches: [main]
    paths:
      - "src/**"
      - "data/config.json"
      - "data/fundamentals.json"

permissions:
  contents: write
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: 의존성 설치
        run: pip install -r requirements.txt -r requirements-dev.txt

      - name: 테스트
        run: python -m pytest tests/ -q

      - name: 빌드
        id: build
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          set +e
          python -m src.build
          code=$?
          echo "code=$code" >> "$GITHUB_OUTPUT"
          # 2 = 셋 게이트 정지. 실패가 아니라 설계된 거부다.
          if [ "$code" -eq 2 ]; then
            echo "::warning::셋 게이트 정지 — 집계가 아직 이번 셋이 아니다. 배포를 건너뛴다."
            exit 0
          fi
          exit $code

      - name: 스냅샷 커밋
        if: steps.build.outputs.code == '0'
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add data/daily/
          git diff --staged --quiet || git commit -m "chore: $(date -u +%Y-%m-%d) 스냅샷"
          git push

      - uses: actions/configure-pages@v5
        if: steps.build.outputs.code == '0'

      - uses: actions/upload-pages-artifact@v3
        if: steps.build.outputs.code == '0'
        with:
          path: dist

  deploy:
    needs: build
    if: needs.build.result == 'success'
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deploy.outputs.page_url }}
    steps:
      - id: deploy
        uses: actions/deploy-pages@v4
```

- [ ] **Step 2: Pages를 켠다 (사람이 직접)**

GitHub 저장소 → Settings → Pages → Source를 **GitHub Actions**로 바꾼다.
이건 웹 UI에서만 되므로 사람이 직접 해야 한다.

- [ ] **Step 3: API 키를 넣는다 (사람이 직접, 선택)**

Settings → Secrets and variables → Actions → New repository secret →
이름 `ANTHROPIC_API_KEY`. **없어도 파이프라인은 돈다** — 패치노트 요약만 조용히 건너뛴다.

- [ ] **Step 4: 손으로 한 번 돌려본다**

Run: `gh workflow run "갱신과 배포" && sleep 20 && gh run list --limit 1`
그다음: `gh run watch`

Expected: 테스트 통과 → 빌드. 집계가 아직 지난 셋이면 `::warning::셋 게이트 정지`가 뜨고 배포를 건너뛴다(이건 성공이다). 셋이 맞으면 배포까지 가고 Pages URL이 찍힌다.

- [ ] **Step 5: 배포된 페이지를 폰으로 연다**

`https://phone-boot-h.github.io/tft-challenger/`

확인할 것: 폰 세로 화면에서 가로 스크롤이 없는가, 다크 모드가 따라오는가, 갱신 시각이 방금인가.

- [ ] **Step 6: README에 주소를 적고 커밋한다**

`README.md`의 첫 문단 아래에 한 줄 더한다:

```markdown
**사이트:** https://phone-boot-h.github.io/tft-challenger/
```

```bash
git add .github/workflows/update.yml README.md
git commit -m "chore: 매일 갱신과 Pages 배포

셋 게이트 정지(종료코드 2)는 실패가 아니라 설계된 거부라 배포만 건너뛴다.
ANTHROPIC_API_KEY가 없어도 파이프라인은 돌고 패치노트 요약만 빠진다."
git push origin main
```

---

## 자체 점검 결과

**스펙 대조 (누락 확인):**

| 스펙 요구 | 담당 태스크 |
|---|---|
| 셋 게이트 | Task 1 |
| cluster_id 핀 | Task 1 |
| 브실골 KR 통계 | Task 3 |
| Δ 계산 | Task 3 |
| 등수 분포(AVP 단독 정렬 금지) | Task 3 + 7 |
| 픽률 → 기대 경합인원 | Task 3 |
| 한글화 | Task 4 |
| 단계별 빌드업 경로 | Task 5 |
| 축약 스냅샷 커밋 | Task 6 |
| 패치 diff | Task 6 |
| 기본기 화면(데이터 없는 날) | Task 7 |
| 오래된 데이터 배지 | Task 7 (`stale_hours`) |
| 색인 | Task 8 (유닛) |
| 패치노트 요약 | Task 9 |
| 매일 갱신 + 배포 | Task 10 |

**의도적으로 뒤로 미룬 것:**

- **아이템·증강 색인** — Task 8은 유닛 색인만 만든다. 아이템·증강은 MetaTFT의 별도 엔드포인트(`comp_augment_tiers` 등)를 붙여야 하고, 그 응답 모양을 아직 실측하지 않았다. 확인하지 않은 스키마로 코드를 미리 쓰는 것보다 유닛 색인을 먼저 굴려보고 같은 틀로 확장하는 게 낫다. Task 8의 `indexes.build`가 그 확장 지점이다.
- **컨센서스 층(🌐)** — 스펙의 "불변 원칙 / 저티어 특화" 두 통은 `fundamentals.json`의 정적 항목으로 시작한다. 웹·X에서 긁어 자동 갱신하는 건 별도 계획으로 뺀다. 지금 넣으면 출처 검증 없이 카더라가 페이지에 올라간다.
- **TFT Academy 첫 주 폴백** — 약관은 통과했지만(조항 0건), 셋18 집계가 5~7일이면 차는 데 반해 스크래퍼는 셋마다 다시 깨진다. 데이터 없는 날은 기본기 화면으로 버틴다.

**남은 미확인:**

- 셋18 랭크 리셋 구간 — 18.1 패치노트에 랭크 항목 자체가 없다. 며칠 뒤 재확인하고, 확인되면 `fundamentals.json`에 항목을 더한다.
- Jaccard 임계값 0.5 — Task 5 Step 6에서 실제 매칭률을 재고 조정한다.

from src.render import dist_bars, page


def _context(**overrides):
    context = {
        "set": "TFTSet18", "patch": "18.1",
        "generated_at": "2026-09-01 05:00 KST",
        "generated_iso": "2026-08-31T20:00:00Z",
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
    # 색 토큰은 dataviz 검증을 통과한 고정값이다. 여섯 쌍 중 하나만 바뀌어도 여기서 걸려야 한다.
    html = page(_context())
    assert "#fcfcfb" in html and "#1a1a19" in html
    assert all(token in html for token in
               ("#2a78d6", "#e34948", "#52514e", "#3987e5", "#e66767", "#c3c2b7"))
    assert 'prefers-color-scheme: dark' in html
    assert '[data-theme="dark"]' in html


def test_신선한_페이지의_배지는_숨겨진_채로_나간다():
    # 스크립트가 채울 자리는 만들어두되, JS가 없으면 지금과 똑같이 보여야 한다 — 빈 상자 금지.
    html = page(_context())
    assert '<p id="stale-box" hidden><span class="stale"></span></p>' in html
    assert 'data-generated="2026-08-31T20:00:00Z"' in html


def test_클러스터_id를_패치_번호라고_부르지_않는다():
    # patch는 변화 감지용 내부 키를 겸한다. 패치 번호가 아니면 "패치"라고 쓰면 안 된다.
    html = page(_context(patch="409"))
    assert "집계 회차 409" in html
    assert "패치 409" not in html


def test_진짜_패치_번호는_패치라고_쓴다():
    assert "패치 18.1" in page(_context(patch="18.1"))


def test_배너도_클러스터_id를_패치라고_부르지_않는다():
    html = page(_context(patch="410", diff={
        "patch_changed": True, "from_patch": "409", "to_patch": "410",
        "moved": [], "entered": [], "left": []}))
    assert "집계 회차가 바뀜" in html
    assert "직전 집계 회차 409 대비" in html
    assert "패치 410" not in html


def test_덱이_없으면_0덱이라고_쓰지_않는다():
    html = page(_context(decks=[]))
    assert "0덱" not in html
    assert "추천할 덱이 아직 없다" in html

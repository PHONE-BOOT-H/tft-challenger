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

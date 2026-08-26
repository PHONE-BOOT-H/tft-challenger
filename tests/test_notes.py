import sys
import types

from src import notes


def _stub_anthropic(monkeypatch, text, stop_reason="end_turn"):
    """anthropic 클라이언트를 스텁으로 바꿔치기하고 API 키를 설정한다."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    def mock_anthropic_init():
        client = types.SimpleNamespace()
        response = types.SimpleNamespace(
            stop_reason=stop_reason,
            content=[types.SimpleNamespace(type="text", text=text)]
        )
        client.beta = types.SimpleNamespace(
            messages=types.SimpleNamespace(create=lambda **kwargs: response)
        )
        return client

    anthropic_module = types.ModuleType("anthropic")
    anthropic_module.Anthropic = mock_anthropic_init
    monkeypatch.setitem(sys.modules, "anthropic", anthropic_module)


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


def test_유효하지_않은_JSON은_None을_반환한다(monkeypatch):
    """응답이 유효하지 않은 JSON인 경우 None을 반환한다."""
    _stub_anthropic(monkeypatch, "not valid json")
    result = notes.summarize("patch text", ["deck1"], "http://example.com")
    assert result is None


def test_bullets_키가_없으면_None을_반환한다(monkeypatch):
    """JSON에 'bullets' 키가 없으면 None을 반환한다."""
    _stub_anthropic(monkeypatch, '{"other": ["value"]}')
    result = notes.summarize("patch text", ["deck1"], "http://example.com")
    assert result is None


def test_bullets가_문자열_배열이_아니면_None을_반환한다(monkeypatch):
    """'bullets'가 문자열 배열이 아니면 None을 반환한다."""
    _stub_anthropic(monkeypatch, '{"bullets": [1, 2, 3]}')
    result = notes.summarize("patch text", ["deck1"], "http://example.com")
    assert result is None


def test_최상위가_배열이면_None을_반환한다(monkeypatch):
    """JSON은 유효하지만 최상위가 객체가 아니라 배열이면 None을 반환한다."""
    _stub_anthropic(monkeypatch, "[1, 2, 3]")
    result = notes.summarize("patch text", ["deck1"], "http://example.com")
    assert result is None


def test_최상위가_문자열이면_None을_반환한다(monkeypatch):
    """JSON은 유효하지만 최상위가 객체가 아니라 문자열이면 None을 반환한다."""
    _stub_anthropic(monkeypatch, '"hello"')
    result = notes.summarize("patch text", ["deck1"], "http://example.com")
    assert result is None


def test_최상위가_null이면_None을_반환한다(monkeypatch):
    """JSON은 유효하지만 최상위가 객체가 아니라 null이면 None을 반환한다."""
    _stub_anthropic(monkeypatch, "null")
    result = notes.summarize("patch text", ["deck1"], "http://example.com")
    assert result is None


def test_유효한_응답은_bullets와_url을_반환한다(monkeypatch):
    """유효한 JSON 응답은 bullets와 url을 포함한 딕셔너리를 반환한다."""
    _stub_anthropic(monkeypatch, '{"bullets": ["change1", "change2"]}')
    result = notes.summarize("patch text", ["deck1"], "http://example.com")
    assert result == {"bullets": ["change1", "change2"], "url": "http://example.com"}

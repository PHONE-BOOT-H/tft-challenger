import types
import os

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


def test_유효하지_않은_JSON은_None을_반환한다(monkeypatch):
    """응답이 유효하지 않은 JSON인 경우 None을 반환한다."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    def mock_anthropic_init():
        client = types.SimpleNamespace()
        response = types.SimpleNamespace(
            stop_reason="end_turn",
            content=[types.SimpleNamespace(type="text", text="not valid json")]
        )
        client.beta = types.SimpleNamespace(
            messages=types.SimpleNamespace(create=lambda **kwargs: response)
        )
        return client

    import sys
    import types as stdlib_types
    anthropic_module = stdlib_types.ModuleType("anthropic")
    anthropic_module.Anthropic = mock_anthropic_init
    monkeypatch.setitem(sys.modules, "anthropic", anthropic_module)

    result = notes.summarize("patch text", ["deck1"], "http://example.com")
    assert result is None


def test_bullets_키가_없으면_None을_반환한다(monkeypatch):
    """JSON에 'bullets' 키가 없으면 None을 반환한다."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    def mock_anthropic_init():
        client = types.SimpleNamespace()
        response = types.SimpleNamespace(
            stop_reason="end_turn",
            content=[types.SimpleNamespace(type="text", text='{"other": ["value"]}')]
        )
        client.beta = types.SimpleNamespace(
            messages=types.SimpleNamespace(create=lambda **kwargs: response)
        )
        return client

    import sys
    import types as stdlib_types
    anthropic_module = stdlib_types.ModuleType("anthropic")
    anthropic_module.Anthropic = mock_anthropic_init
    monkeypatch.setitem(sys.modules, "anthropic", anthropic_module)

    result = notes.summarize("patch text", ["deck1"], "http://example.com")
    assert result is None


def test_bullets가_문자열_배열이_아니면_None을_반환한다(monkeypatch):
    """'bullets'가 문자열 배열이 아니면 None을 반환한다."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    def mock_anthropic_init():
        client = types.SimpleNamespace()
        response = types.SimpleNamespace(
            stop_reason="end_turn",
            content=[types.SimpleNamespace(type="text", text='{"bullets": [1, 2, 3]}')]
        )
        client.beta = types.SimpleNamespace(
            messages=types.SimpleNamespace(create=lambda **kwargs: response)
        )
        return client

    import sys
    import types as stdlib_types
    anthropic_module = stdlib_types.ModuleType("anthropic")
    anthropic_module.Anthropic = mock_anthropic_init
    monkeypatch.setitem(sys.modules, "anthropic", anthropic_module)

    result = notes.summarize("patch text", ["deck1"], "http://example.com")
    assert result is None


def test_유효한_응답은_bullets와_url을_반환한다(monkeypatch):
    """유효한 JSON 응답은 bullets와 url을 포함한 딕셔너리를 반환한다."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    def mock_anthropic_init():
        client = types.SimpleNamespace()
        response = types.SimpleNamespace(
            stop_reason="end_turn",
            content=[types.SimpleNamespace(type="text", text='{"bullets": ["change1", "change2"]}')]
        )
        client.beta = types.SimpleNamespace(
            messages=types.SimpleNamespace(create=lambda **kwargs: response)
        )
        return client

    import sys
    import types as stdlib_types
    anthropic_module = stdlib_types.ModuleType("anthropic")
    anthropic_module.Anthropic = mock_anthropic_init
    monkeypatch.setitem(sys.modules, "anthropic", anthropic_module)

    result = notes.summarize("patch text", ["deck1"], "http://example.com")
    assert result == {"bullets": ["change1", "change2"], "url": "http://example.com"}

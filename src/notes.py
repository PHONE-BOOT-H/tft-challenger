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

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"패치노트 요약 실패: {exc}")
        return None

    if not isinstance(parsed, dict):
        print("패치노트 요약 실패: 응답이 JSON 객체가 아님")
        return None

    bullets = parsed.get("bullets")
    if not isinstance(bullets, list) or not all(isinstance(b, str) for b in bullets):
        print("패치노트 요약 실패: bullets가 문자열 배열이 아님")
        return None
    return {"bullets": bullets, "url": url}


def maybe_summarize(diff, deck_names):
    """패치가 바뀐 날에만 요약한다."""
    if not diff.get("patch_changed"):
        return None
    patch = diff.get("to_patch")
    text = fetch_patch_text(patch)
    if not text:
        return None
    return summarize(text, deck_names, patch_url(patch))

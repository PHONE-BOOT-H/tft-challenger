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

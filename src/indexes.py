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

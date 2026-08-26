import json
from pathlib import Path

import pytest

from src.paths import final_units, jaccard, match_stage5, route, stage_units

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def test_같은_집합은_1이다():
    assert jaccard({"a", "b"}, {"a", "b"}) == pytest.approx(1.0)


def test_겹치지_않으면_0이다():
    assert jaccard({"a"}, {"b"}) == pytest.approx(0.0)


def test_빈_집합끼리는_0이다():
    assert jaccard(set(), set()) == pytest.approx(0.0)


def test_최종덱_유닛을_units_string에서_뽑는다():
    units = final_units(_load("comps_data"))
    assert units["410000"] == {"DA_18_A", "DA_18_B", "DA_18_E", "DA_18_G", "DA_18_H"}


def test_스테이지_유닛은_딕셔너리_키에서_뽑는다():
    stages = stage_units(_load("early"), "stage-2")
    assert stages[0] == {"DA_18_A", "DA_18_B"}


def test_유닛이_같은_최종덱과_stage5를_잇는다():
    matched = match_stage5(final_units(_load("comps_data")), _load("early"))
    assert matched["410000"] == 0


def test_안_닮은_덱은_아예_넣지_않는다():
    # 410001은 stage-5와 유닛이 하나도 안 겹친다. 억지로 붙이면 틀린 경로가 나간다.
    matched = match_stage5(final_units(_load("comps_data")), _load("early"))
    assert "410001" not in matched


def test_동점이면_평균등수가_더_좋은_stage5를_고른다():
    # 두 stage-5 후보 모두 Jaccard 0.6으로 동점(교집합 3, 합집합 5)이지만
    # 평균 등수(final_place_avg)는 인덱스 1쪽(2.0)이 인덱스 0쪽(5.0)보다 좋다.
    # 인덱스가 큰 쪽을 무조건 고르던 예전 방식이면 우연히 맞지만,
    # 평균 등수를 무시하는 구현이면 이 값을 바꿔서 걸러낼 수 있다.
    early = {"comps_overview": {"stage-5": {"comps": [
        {"units": {"K": {}, "L": {}, "M": {}, "O": {}}, "stats": {"final_place_avg": 5.0}},
        {"units": {"K": {}, "L": {}, "N": {}, "P": {}}, "stats": {"final_place_avg": 2.0}},
    ]}}}
    final = {"c": {"K", "L", "M", "N"}}
    matched = match_stage5(final, early)
    assert matched["c"] == 1


def test_경로는_스테이지2부터_5까지_네_칸이다():
    steps = route(_load("early"), 0)
    assert [step["stage"] for step in steps] == ["stage-2", "stage-3", "stage-4", "stage-5"]


def test_경로는_backwards_links의_최대값을_따라간다():
    # stage-4[0].backwards_links = [80, 20] -> stage-3[0]
    # stage-3[0].backwards_links = [90, 10] -> stage-2[0]
    steps = route(_load("early"), 0)
    assert steps[0]["units"] == ["DA_18_A", "DA_18_B"]
    assert steps[0]["avp"] == pytest.approx(4.5)


def test_경로는_0이_아닌_인덱스로도_거슬러_올라간다():
    # stage-5[1].backwards_links = [30, 70] -> stage-4[1] (인덱스 1이 최대)
    # stage-4[1].backwards_links = [20, 80] -> stage-3[1] (인덱스 1이 최대)
    # stage-3[1].backwards_links = [5, 95]  -> stage-2[1] (인덱스 1이 최대)
    # 매 단계 argmax를 0으로 고정한 구현이면 이 테스트는 실패한다.
    steps = route(_load("early"), 1)
    assert steps[0]["units"] == ["DA_18_C", "DA_18_D"]
    assert steps[0]["avp"] == pytest.approx(4.8)

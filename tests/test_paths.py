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


def test_경로는_스테이지2부터_5까지_네_칸이다():
    steps = route(_load("early"), 0)
    assert [step["stage"] for step in steps] == ["stage-2", "stage-3", "stage-4", "stage-5"]


def test_경로는_backwards_links의_최대값을_따라간다():
    # stage-4[0].backwards_links = [80, 20] -> stage-3[0]
    # stage-3[0].backwards_links = [90, 10] -> stage-2[0]
    steps = route(_load("early"), 0)
    assert steps[0]["units"] == ["DA_18_A", "DA_18_B"]
    assert steps[0]["avp"] == pytest.approx(4.5)

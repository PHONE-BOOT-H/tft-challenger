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

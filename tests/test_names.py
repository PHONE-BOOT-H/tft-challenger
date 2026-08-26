import json
from pathlib import Path

from src.names import build_index, ko, unit_costs

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def _index():
    return build_index(
        champion=_load("ddragon_champion"),
        trait=_load("ddragon_trait"),
        item={"data": {}},
        augments={"data": {}},
        set_path="/Sets/TFTSet18/",
    )


def test_유닛_한글이름을_찾는다():
    assert _index()["DA_18_Xayah"] == "자야"


def test_id_접두사가_불균일해도_경로로_잡는다():
    # DA_Lux18_Light는 DA_18_ 접두사가 아니다. 접두사로 거르면 놓친다.
    assert _index()["DA_Lux18_Light"] == "럭스"


def test_지난_셋_유닛은_색인에_없다():
    assert "TFT17_Aatrox" not in _index()


def test_특성도_같은_색인에_들어간다():
    assert _index()["DA_18_Adaptor"] == "적응가"


def test_코스트를_뽑고_로스터_크기는_읽어서_안다():
    costs = unit_costs(_load("ddragon_champion"), "/Sets/TFTSet18/")
    assert costs["DA_18_Xayah"] == 1
    assert costs["DA_Lux18_Light"] == 5
    assert "TFT17_Aatrox" not in costs


def test_모르는_이름은_접두사를_벗겨_되돌린다():
    assert ko(_index(), "DA_18_Ornn") == "Ornn"


def test_접두사가_없는_모르는_이름은_그대로_돌려준다():
    assert ko(_index(), "Nonsense") == "Nonsense"

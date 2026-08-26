from src.patchdiff import compare, load_previous, save, MOVE_THRESHOLD


def _snap(patch, decks):
    return {"patch": patch, "decks": [{"cluster": c, "name": n, "avp_low": a}
                                      for c, n, a in decks]}


def test_직전이_없으면_변화없음으로_본다():
    result = compare(None, _snap("18.1", [("410000", "A덱", 4.1)]))
    assert result["patch_changed"] is False
    assert result["moved"] == []
    assert result["entered"] == []


def test_패치가_바뀌면_표시한다():
    previous = _snap("18.1", [("410000", "A덱", 4.1)])
    current = _snap("18.2", [("410000", "A덱", 4.1)])
    result = compare(previous, current)
    assert result["patch_changed"] is True
    assert result["from_patch"] == "18.1"
    assert result["to_patch"] == "18.2"


def test_평균등수_변화를_잡는다():
    previous = _snap("18.1", [("410000", "A덱", 4.10)])
    current = _snap("18.2", [("410000", "A덱", 4.55)])
    moved = compare(previous, current)["moved"]
    assert len(moved) == 1
    assert moved[0]["cluster"] == "410000"
    assert moved[0]["before"] == 4.10
    assert moved[0]["after"] == 4.55


def test_임계값_미만_변화는_무시한다():
    previous = _snap("18.1", [("410000", "A덱", 4.10)])
    current = _snap("18.2", [("410000", "A덱", 4.11)])
    assert compare(previous, current)["moved"] == []


def test_임계값과_같으면_변화로_잡는다():
    # 부동소수점에서 정확히 임계값과 같은 차이를 위해 0.0부터 시작
    # 0.0 + MOVE_THRESHOLD로 계산하면 >= 비교는 통과하고 > 비교는 실패함
    before = 0.0
    after = before + MOVE_THRESHOLD
    previous = _snap("18.1", [("410000", "A덱", before)])
    current = _snap("18.2", [("410000", "A덱", after)])
    moved = compare(previous, current)["moved"]
    assert len(moved) == 1
    assert moved[0]["cluster"] == "410000"


def test_새로_들어오고_빠진_덱을_잡는다():
    previous = _snap("18.1", [("410000", "A덱", 4.1), ("410001", "B덱", 4.3)])
    current = _snap("18.2", [("410000", "A덱", 4.1), ("410002", "C덱", 3.9)])
    result = compare(previous, current, top_n=3)
    assert [d["cluster"] for d in result["entered"]] == ["410002"]
    assert [d["cluster"] for d in result["left"]] == ["410001"]


def test_상위_N개만_비교한다():
    previous = _snap("18.1", [("A", "a", 4.0), ("B", "b", 4.1), ("C", "c", 4.2), ("D", "d", 4.3)])
    current = _snap("18.1", [("A", "a", 4.0), ("B", "b", 4.1), ("C", "c", 4.2), ("D", "d", 9.9)])
    # D는 상위 3개 밖이라 변화가 잡히지 않는다
    assert compare(previous, current, top_n=3)["moved"] == []


def test_저장하고_직전을_되읽는다(tmp_path, monkeypatch):
    from src import patchdiff
    monkeypatch.setattr(patchdiff, "DAILY", tmp_path)
    save(_snap("18.1", [("410000", "A덱", 4.1)]), "2026-09-01")
    save(_snap("18.2", [("410000", "A덱", 4.5)]), "2026-09-11")
    previous = load_previous(before="2026-09-11")
    assert previous["patch"] == "18.1"


def test_직전이_없으면_None을_준다(tmp_path, monkeypatch):
    from src import patchdiff
    monkeypatch.setattr(patchdiff, "DAILY", tmp_path)
    save(_snap("18.1", [("410000", "A덱", 4.1)]), "2026-09-01")
    assert load_previous(before="2026-09-01") is None

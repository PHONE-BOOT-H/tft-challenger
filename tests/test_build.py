"""build_context 통합 테스트.

아홉 개 모듈이 한 줄로 꿰이는 유일한 지점이고, 조각마다 옳아도 이음매에서 깨진다.
네트워크는 건드리지 않는다 — 페이로드는 전부 fixtures에서 온다.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src import build, patchdiff, paths, render

FIXTURES = Path(__file__).parent / "fixtures"
KST = timezone(timedelta(hours=9))
NOW = datetime(2026, 9, 1, 5, 0, tzinfo=KST)

CFG = {"ddragon_set_path": "/Sets/TFTSet18/", "min_games": 50, "top_n": 3, "days": 3}


def _load(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def _payloads(**overrides):
    payloads = {
        "latest_cluster_id": {"tft_set": "TFTSet18", "cluster_id": 410},
        "comps_data": _load("comps_data"),
        "comps_stats_low": _load("comps_stats_low"),
        "comps_stats_high": _load("comps_stats_high"),
        "early": _load("early"),
        "champion": _load("ddragon_champion"),
        "trait": _load("ddragon_trait"),
        "item": {"data": {}},
        "augments": {"data": {}},
    }
    payloads.update(overrides)
    return payloads


def _build(monkeypatch, tmp_path, payloads=None, **cfg):
    monkeypatch.setattr(patchdiff, "DAILY", tmp_path)
    return build.build_context(payloads or _payloads(), dict(CFG, **cfg), NOW)


def test_패치가_바뀌어도_빌드가_죽지_않는다(tmp_path, monkeypatch):
    """patch 라벨은 클러스터 id를 겸한다 — 그대로 패치노트 URL에 넣으면 빌드가 죽는다.

    가드가 요약 시도 자체를 막으므로 네트워크 스텁이 필요 없다.
    """
    (tmp_path / "2026-08-31.json").write_text(
        json.dumps({"patch": "409", "set": "TFTSet18", "decks": []}, ensure_ascii=False),
        encoding="utf-8")
    context = _build(monkeypatch, tmp_path)
    assert context["diff"]["patch_changed"] is True
    assert context["notes"] is None


def test_델타로_정렬한_뒤에_판수_하한을_건다(tmp_path, monkeypatch):
    """자르고 거르면 Δ 상위 한 자리가 통째로 빈다. 거르고 잘라야 세 칸이 다 찬다."""
    payloads = _payloads()
    for row in payloads["comps_stats_low"]["results"]:
        if row["cluster"] == "410000":  # Δ가 가장 좋은 덱을 하한 아래로 내린다
            row["count"] = 50
    context = _build(monkeypatch, tmp_path, payloads, min_games=100, top_n=2)
    assert [deck["cluster"] for deck in context["decks"]] == ["410002", "410001"]
    deltas = [deck["delta"] for deck in context["decks"]]
    assert deltas == sorted(deltas)


def test_경로는_매칭된_덱에만_붙는다(tmp_path, monkeypatch):
    """틀린 경로가 경로 없음보다 나쁘다 — 임계값을 못 넘으면 빈 리스트로 둔다."""
    decks = {deck["cluster"]: deck for deck in _build(monkeypatch, tmp_path)["decks"]}
    assert [step["stage"] for step in decks["410000"]["route"]] == list(paths.STAGES)
    assert decks["410001"]["route"] == []


def test_표본이_0이면_덱도_0이고_페이지는_그려진다(tmp_path, monkeypatch):
    empty = {"results": [{"cluster": "", "places": [0]}]}
    context = _build(monkeypatch, tmp_path,
                     _payloads(comps_stats_low=empty, comps_stats_high=empty))
    assert context["decks"] == []
    assert context["total_games"] == 0
    assert "아직 데이터가 없다" in render.page(context)


def test_이름_변환기가_컨텍스트에_실려_렌더까지_간다(tmp_path, monkeypatch):
    context = _build(monkeypatch, tmp_path)
    assert callable(context["name_of"]) and "유닛으로 찾기" in render.page(context)

import json
from pathlib import Path

import pytest

from src.comps import avp, distribution, merge_delta, parse_stats

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def test_avp는_등수별_빈도의_가중평균이다():
    # 1등 1판, 8등 1판 -> (1 + 8) / 2 = 4.5
    assert avp([1, 0, 0, 0, 0, 0, 0, 1, 2]) == pytest.approx(4.5)


def test_avp는_마지막_원소를_등수로_세지_않는다():
    # places[8]은 총합이지 9등 빈도가 아니다. 섞이면 평균등수가 통째로 틀어진다.
    assert avp([4, 0, 0, 0, 0, 0, 0, 0, 4]) == pytest.approx(1.0)


def test_분포는_길이가_8이고_합이_1이다():
    dist = distribution([30, 25, 20, 15, 4, 3, 2, 1, 100])
    assert len(dist) == 8
    assert sum(dist) == pytest.approx(1.0)
    assert dist[0] == pytest.approx(0.30)


def test_전체_판수를_같이_돌려주고_마커는_덱에서_뺀다():
    stats, total = parse_stats(_load("comps_stats_low"))
    assert total == 1000
    assert "" not in stats
    assert set(stats) == {"410000", "410001", "410002"}


def test_저티어에서_좋은_덱이_델타_맨앞에_온다():
    low, low_total = parse_stats(_load("comps_stats_low"))
    high, _ = parse_stats(_load("comps_stats_high"))
    merged = merge_delta(low, low_total, high)
    assert merged[0]["cluster"] == "410000"
    assert merged[0]["delta"] < 0
    assert merged[-1]["cluster"] == "410001"
    assert merged[-1]["delta"] > 0


def test_픽률과_기대_경합인원을_계산한다():
    low, low_total = parse_stats(_load("comps_stats_low"))
    high, _ = parse_stats(_load("comps_stats_high"))
    merged = {row["cluster"]: row for row in merge_delta(low, low_total, high)}
    # 100판 / 전체 1000판 = 10%, 8인 로비 기대 0.8명
    assert merged["410000"]["pick_rate"] == pytest.approx(0.10)
    assert merged["410000"]["expected_contest"] == pytest.approx(0.8)


def test_고티어에_없는_덱은_델타가_None이고_맨뒤로_간다():
    low, low_total = parse_stats(_load("comps_stats_low"))
    merged = merge_delta(low, low_total, {})
    assert all(row["delta"] is None for row in merged)
    assert merged[0]["avp_high"] is None

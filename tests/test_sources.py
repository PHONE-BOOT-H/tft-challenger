import json

import pytest

from src import sources
from src.sources import build_urls

CFG = {"server": "KR", "low_rank": "BRONZE,SILVER,GOLD",
       "high_rank": "DIAMOND,MASTER,GRANDMASTER,CHALLENGER", "days": 3}


def test_저티어_URL에_랭크와_서버가_들어간다():
    urls = build_urls(CFG)
    assert "rank=BRONZE,SILVER,GOLD" in urls["comps_stats_low"]
    assert "server=KR" in urls["comps_stats_low"]
    assert "days=3" in urls["comps_stats_low"]


def test_고티어_URL은_랭크만_다르다():
    urls = build_urls(CFG)
    swapped = urls["comps_stats_low"].replace(
        "BRONZE,SILVER,GOLD", "DIAMOND,MASTER,GRANDMASTER,CHALLENGER")
    assert swapped == urls["comps_stats_high"]


def test_다섯_엔드포인트가_모두_있다():
    assert set(build_urls(CFG)) == {"latest_cluster_id", "comps_stats_low",
                                    "comps_stats_high", "comps_data", "early"}


def test_설정의_셋_번호가_두_군데에서_어긋나면_거부한다(tmp_path, monkeypatch):
    # 어긋나도 게이트는 통과한다. 대신 유닛 이름이 전부 영어 id로 조용히 떨어진다.
    monkeypatch.setattr(sources, "ROOT", tmp_path)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "config.json").write_text(json.dumps(
        {"expected_set": "TFTSet19", "ddragon_set_path": "/Sets/TFTSet18/"}), encoding="utf-8")
    with pytest.raises(ValueError) as err:
        sources.load_config()
    assert "TFTSet19" in str(err.value)

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

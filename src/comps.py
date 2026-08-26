"""comps_stats 파싱과 티어 간 Δ 계산.

응답의 `places`는 원소 아홉 개다. 앞의 여덟 개가 1~8등 빈도, 마지막이 총합이다.
마지막을 9등으로 세면 평균등수가 통째로 틀어지므로 반드시 잘라내고 쓴다.
결과 목록의 첫 원소(`cluster` == "")는 덱이 아니라 전체 판수 마커다.
"""

LOBBY_SIZE = 8


def avp(places):
    """평균등수. places[:8]만 쓴다."""
    counts = places[:LOBBY_SIZE]
    total = sum(counts)
    if total == 0:
        return 0.0
    return sum((rank + 1) * count for rank, count in enumerate(counts)) / total


def distribution(places):
    """1~8등 비율. 길이 8, 합 1.0."""
    counts = places[:LOBBY_SIZE]
    total = sum(counts)
    if total == 0:
        return [0.0] * LOBBY_SIZE
    return [count / total for count in counts]


def parse_stats(payload):
    """(덱별 통계, 전체 판수)를 돌려준다."""
    stats = {}
    total_games = 0
    for row in payload.get("results", []):
        cluster = row.get("cluster", "")
        places = row.get("places", [])
        if cluster == "":
            # 덱이 아니라 전체 판수 마커. places는 원소 하나짜리다.
            total_games = places[0] if places else 0
            continue
        stats[cluster] = {
            "places": places,
            "count": row.get("count", sum(places[:LOBBY_SIZE])),
            "avp": avp(places),
            "dist": distribution(places),
        }
    return stats, total_games


def merge_delta(low, low_total, high):
    """브실골 통계에 다이아+ 평균등수를 붙이고 Δ를 계산한다.

    Δ = 브실골 AVP - 다이아+ AVP. 음수면 저티어에서 더 좋은 덱이다.
    고티어 표본에 없는 덱은 Δ를 None으로 두고 정렬 맨 뒤로 보낸다.
    """
    rows = []
    for cluster, entry in low.items():
        high_avp = high[cluster]["avp"] if cluster in high else None
        delta = None if high_avp is None else entry["avp"] - high_avp
        pick_rate = entry["count"] / low_total if low_total else 0.0
        rows.append({
            "cluster": cluster,
            "avp_low": entry["avp"],
            "avp_high": high_avp,
            "delta": delta,
            "count": entry["count"],
            "pick_rate": pick_rate,
            # 경합은 "나 말고 같은 덱을 하는 사람" 수다. 나를 빼고 7명으로 센다.
            "expected_contest": pick_rate * (LOBBY_SIZE - 1),
            "dist": entry["dist"],
        })
    rows.sort(key=lambda row: (row["delta"] is None, row["delta"] or 0.0))
    return rows

"""단계별 빌드업 경로.

early-comps와 comps는 클러스터 공간이 다르다(실측: comps=409, early=2630).
early 쪽 `cluster`는 스테이지 안에서의 인덱스일 뿐이라 id로 이을 수 없다.
양쪽 다 유닛 목록을 주므로 유닛 집합의 Jaccard 유사도로 잇는다.

임계값에 못 미치면 아예 잇지 않는다. 틀린 경로가 경로 없음보다 나쁘다.
"""

STAGES = ("stage-2", "stage-3", "stage-4", "stage-5")


def jaccard(a, b):
    """교집합 / 합집합. 둘 다 비면 0."""
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def final_units(comps_data):
    """최종 덱 cluster -> 유닛 집합."""
    details = comps_data["results"]["data"]["cluster_details"]
    result = {}
    for cluster, entry in details.items():
        raw = entry.get("units_string", "")
        result[cluster] = {token.strip() for token in raw.split(",") if token.strip()}
    return result


def stage_units(early, stage):
    """스테이지 덱 인덱스별 유닛 집합. units는 리스트가 아니라 딕셔너리다."""
    comps = early["comps_overview"][stage]["comps"]
    return [set(comp.get("units", {}).keys()) for comp in comps]


def match_stage5(final, early, threshold=0.5):
    """최종 덱 cluster -> stage-5 인덱스. 임계값 미달은 넣지 않는다."""
    stage5 = stage_units(early, "stage-5")
    stage5_comps = early["comps_overview"]["stage-5"]["comps"]
    matched = {}
    for cluster, units in final.items():
        # 동점 처리(우연이 아니라 결정): Jaccard가 같으면 평균 등수
        # (final_place_avg, 낮을수록 좋음)가 나은 쪽을 고르고, 그마저 같거나
        # 없으면(없으면 최하 취급) 인덱스가 낮은 쪽을 골라 재실행해도
        # 항상 같은 결과가 나오게 한다.
        scored = []
        for index, board in enumerate(stage5):
            avp = stage5_comps[index].get("stats", {}).get("final_place_avg")
            better_avp = -(avp if avp is not None else float("inf"))
            scored.append((jaccard(units, board), better_avp, -index, index))
        if not scored:
            continue
        best_score, _, _, best_index = max(scored)
        if best_score >= threshold:
            matched[cluster] = best_index
    return matched


def route(early, stage5_index):
    """stage-5 인덱스에서 backwards_links를 거슬러 올라가 2->5 경로를 만든다."""
    overview = early["comps_overview"]
    indices = {"stage-5": stage5_index}
    for stage, previous in (("stage-5", "stage-4"),
                            ("stage-4", "stage-3"),
                            ("stage-3", "stage-2")):
        comp = overview[stage]["comps"][indices[stage]]
        links = comp.get("backwards_links") or []
        if not links:
            break
        indices[previous] = max(range(len(links)), key=lambda i: links[i])

    steps = []
    for stage in STAGES:
        if stage not in indices:
            continue
        comp = overview[stage]["comps"][indices[stage]]
        steps.append({
            "stage": stage,
            "units": sorted(comp.get("units", {}).keys()),
            "avp": comp.get("stats", {}).get("final_place_avg"),
        })
    return steps

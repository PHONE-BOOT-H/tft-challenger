"""셋 게이트. 이 관문을 통과하지 못하면 아무것도 렌더하지 않는다.

집계 사이트는 셋이 바뀐 뒤에도 며칠 동안 지난 셋 데이터를 태연히 내준다.
게이트가 없으면 지난 셋 덱을 이번 셋 덱이라고 내놓게 된다.
"""

_SET_SOURCES = ("latest_cluster_id", "comps_data", "early")


class SetMismatch(RuntimeError):
    """받아온 데이터가 기대한 셋이 아니다."""


class ClusterMismatch(RuntimeError):
    """comps_data가 latest_cluster_id와 다른 클러스터를 말한다."""


def check_set(payloads, expected):
    """받아온 페이로드 전부가 기대한 셋인지 확인한다. 모든 소스가 있어야 하고, 하나라도 어긋나면 예외."""
    missing = [key for key in _SET_SOURCES if key not in payloads]
    if missing:
        raise SetMismatch(f"페이로드 누락: {missing}")

    bad = []
    for key in _SET_SOURCES:
        payload = payloads[key]
        if not isinstance(payload, dict):
            # 배열이 오면 .get에서 AttributeError로 터진다 — 게이트 메시지가 아니라 트레이스백이 나간다.
            raise SetMismatch(f"{key} 응답이 객체가 아니다: {type(payload).__name__}")
        got = payload.get("tft_set")
        if got != expected:
            bad.append(f"{key}={got!r}")
    if bad:
        raise SetMismatch(f"셋 불일치 (기대 {expected!r}): " + ", ".join(bad))


def pin_cluster(payloads):
    """클러스터 id를 핀으로 고정한다. 안 맞추면 두 엔드포인트가 서로 다른 덱을 말한다."""
    pinned = payloads["latest_cluster_id"]["cluster_id"]
    got = payloads["comps_data"]["cluster_id"]
    if got != pinned:
        raise ClusterMismatch(f"cluster_id 불일치: latest={pinned} comps_data={got}")
    return pinned

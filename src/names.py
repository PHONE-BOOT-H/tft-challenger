"""ddragon ko_KR 한글 이름 색인.

챔피언·특성 파일의 `data` 키는 apiName이 아니라 경로다.
예: "Maps/Shipping/Map22/Sets/TFTSet18/Shop/DA_18_Xayah"
apiName은 값의 `id` 필드에 있다.

셋 필터는 반드시 이 경로로 한다. id 접두사(`DA_18_`)로 거르면
`DA_Lux18_*` `DA_Nidalee18_*` `DA_Vi18_*` `DA_Amumu18_*` 같은 변형 유닛을 놓친다.
아이템과 증강은 셋 공용 id가 섞여 있어 경로 필터를 걸지 않고 전부 담는다.
"""


def _by_path(payload, set_path):
    """키 경로에 set_path가 들어간 항목만 (apiName, 값)으로 돌려준다."""
    for key, value in payload.get("data", {}).items():
        if set_path in key and "id" in value:
            yield value["id"], value


def _all(payload):
    """모든 항목에서 (apiName, 값)을 돌려준다."""
    for value in payload.get("data", {}).values():
        if "id" in value:
            yield value["id"], value


def build_index(champion, trait, item, augments, set_path):
    """apiName -> 한글 이름."""
    index = {}
    for payload in (champion, trait):
        for api_name, value in _by_path(payload, set_path):
            index[api_name] = value.get("name", api_name)
    for payload in (item, augments):
        for api_name, value in _all(payload):
            index[api_name] = value.get("name", api_name)
    return index


def unit_costs(champion, set_path):
    """apiName -> 코스트. 로스터 크기는 하드코딩하지 않고 여기서 읽는다."""
    return {api_name: value.get("cost", 0)
            for api_name, value in _by_path(champion, set_path)}


def ko(index, api_name):
    """한글 이름. 없으면 접두사를 벗겨 되돌린다 — 빈칸보다는 영어 이름이 낫다."""
    if api_name in index:
        return index[api_name]
    _, sep, tail = api_name.rpartition("_")
    return tail if sep else api_name

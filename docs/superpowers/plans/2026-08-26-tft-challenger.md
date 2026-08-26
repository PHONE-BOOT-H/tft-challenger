# tft-challenger 구현 계획

> **에이전트 작업자에게:** 필수 하위 스킬 — `superpowers:subagent-driven-development`(권장) 또는
> `superpowers:executing-plans`로 태스크 단위로 구현할 것. 각 단계는 체크박스(`- [ ]`)로 추적한다.

**목표:** 브실골 KR 데이터로 계산한 덱 성적과 단계별 빌드업 경로를 한 페이지에 합쳐, 매일 자동 갱신되는 한국어 치트시트를 GitHub Pages로 띄운다.

**구조:** GitHub Actions가 MetaTFT와 ddragon에서 JSON을 받아 → 셋 게이트를 통과시키고 → 브실골/다이아+ 두 통계를 조인해 Δ를 계산하고 → early-comps 경로를 유닛 집합 매칭으로 덱에 붙이고 → 단일 HTML로 렌더해 Pages에 배포한다. 상태 저장소는 git 자체다: 축약 스냅샷을 매일 커밋하고, 그 히스토리가 패치 diff의 입력이 된다.

**기술 스택:** Python 3.11+ (코어는 표준 라이브러리만) · `anthropic`(notes.py 전용) · `pytest` · GitHub Actions · GitHub Pages

## 전역 제약

이 절의 내용은 모든 태스크의 요구사항에 암묵적으로 포함된다.

- **Python 3.11 이상.** 코어(`sources`/`validate`/`comps`/`names`/`paths`/`patchdiff`/`render`/`build`)는 **표준 라이브러리만** 쓴다. `requests`·`pyyaml`·`pandas` 금지.
- **의존성은 둘뿐:** `anthropic`(패치노트 요약, `src/notes.py`에서만 import) · `pytest`(테스트).
- **User-Agent는 `tft-challenger/1.0 (+https://github.com/PHONE-BOOT-H/tft-challenger)`.** 브라우저 위장 금지. 이 UA로 MetaTFT·ddragon 모두 200을 받는 것을 실측 확인했다.
- **셋 게이트를 통과하기 전에는 어떤 렌더도 하지 않는다.** 2026-08-26 실측 기준 MetaTFT는 셋18 라이브 게임에 셋17 데이터를 내주고 있었다.
- **유닛·특성·아이템·증강의 이름과 목록을 하드코딩하지 않는다.** 전부 ddragon에서 런타임에 읽는다.
- **ddragon 셋18 유닛 필터는 키 경로 `/Sets/TFTSet18/`로 한다.** id 접두사(`DA_18_`)로 거르면 `DA_Lux18_*` 등 11개를 놓친다.
- **`data/raw/`는 커밋하지 않는다(.gitignore에 있음). `data/daily/`만 커밋한다.**
- **UI 문구와 코드 주석은 한국어.**
- **출처 URL이 없는 컨센서스 주장은 렌더하지 않는다.**
- **실시간·게임 중 조언 기능을 만들지 않는다.** Riot 서드파티 정책이 "현재 게임 상태 기반 제안"을 명시적으로 금지한다.
- **색상 토큰은 아래 검증 통과 값에서 바꾸지 않는다.** dataviz 검증기 `--pairs all` 기준 라이트/다크 전 항목 PASS (CVD ΔE 21.6/19.2, 대비 3:1 이상).

```
라이트  surface #fcfcfb · text #0b0b0b · text2 #52514e · 탑4 #2a78d6 · 하위4 #e34948 · 중립 #f0efec
다크    surface #1a1a19 · text #ffffff · text2 #c3c2b7 · 탑4 #3987e5 · 하위4 #e66767 · 중립 #383835
```

## 파일 구조

| 경로 | 책임 |
|---|---|
| `data/config.json` | 셋 이름·서버·랭크 구간·기간. 셋이 바뀌면 여기만 고친다 |
| `src/sources.py` | HTTP 한 곳 + 엔드포인트 URL 조립. 여기 말고는 네트워크를 만지지 않는다 |
| `src/validate.py` | 셋 게이트, cluster_id 핀 |
| `src/fetch.py` | 수집해서 `data/raw/`에 그대로 저장. 가공 안 함 |
| `src/comps.py` | `comps_stats` 파싱, AVP·분포·픽률, 브실골↔다이아+ Δ |
| `src/names.py` | ddragon ko_KR 이름 색인 |
| `src/paths.py` | 유닛 집합 Jaccard 매칭 + `backwards_links` 경로 역추적 |
| `src/patchdiff.py` | 축약 스냅샷 저장/적재, 직전 스냅샷과 비교 |
| `src/notes.py` | 패치 감지 시 공식 패치노트 요약 (Anthropic API) |
| `src/render.py` | 단일 HTML 출력 |
| `src/build.py` | 파이프라인 오케스트레이션 (`python -m src.build`) |
| `data/fundamentals.json` | 기본기 화면 내용(레벨 곡선·확률표·저티어 원칙). 출처 URL 필수 |
| `tests/` | `pytest`. 픽스처는 `tests/fixtures/` |
| `.github/workflows/update.yml` | 매일 cron + 패치 시 상향 + Pages 배포 |

---

### Task 1: 뼈대 · HTTP · 셋 게이트

이 프로젝트에서 제일 값진 코드다. 셋 게이트가 없으면 지난 셋 덱을 이번 셋 덱이라고 내놓는다.

**Files:**
- Create: `src/__init__.py`, `src/sources.py`, `src/validate.py`, `data/config.json`, `tests/__init__.py`, `tests/test_validate.py`, `tests/test_sources.py`, `requirements-dev.txt`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces:
  - `sources.ROOT: Path` · `sources.RAW: Path` · `sources.DAILY: Path` · `sources.DIST: Path`
  - `sources.load_config() -> dict`
  - `sources.get_json(url: str, timeout: float = 40, retries: int = 2) -> dict | list`
  - `sources.build_urls(cfg: dict) -> dict[str, str]` — 키: `latest_cluster_id`, `comps_stats_low`, `comps_stats_high`, `comps_data`, `early`
  - `sources.ddragon_urls() -> tuple[str, dict[str, str]]`
  - `sources.FetchError(RuntimeError)`
  - `validate.check_set(payloads: dict[str, dict], expected: str) -> None` — 불일치 시 `SetMismatch`
  - `validate.pin_cluster(payloads: dict[str, dict]) -> int` — 불일치 시 `ClusterMismatch`
  - `validate.SetMismatch(RuntimeError)` · `validate.ClusterMismatch(RuntimeError)`

- [ ] **Step 1: 설정 파일과 개발 의존성을 만든다**

`data/config.json`:

```json
{
  "expected_set": "TFTSet18",
  "server": "KR",
  "low_rank": "BRONZE,SILVER,GOLD",
  "high_rank": "DIAMOND,MASTER,GRANDMASTER,CHALLENGER",
  "days": 3,
  "ddragon_set_path": "/Sets/TFTSet18/"
}
```

`requirements-dev.txt`:

```
pytest>=8.0
```

`src/__init__.py`와 `tests/__init__.py`는 빈 파일로 만든다.

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`tests/test_validate.py`:

```python
import pytest

from src.validate import ClusterMismatch, SetMismatch, check_set, pin_cluster


def _payloads(cluster_set="TFTSet18", early_set="TFTSet18", cluster_id=410, data_id=410):
    return {
        "latest_cluster_id": {"tft_set": cluster_set, "cluster_id": cluster_id},
        "comps_data": {"tft_set": cluster_set, "cluster_id": data_id},
        "early": {"tft_set": early_set},
    }


def test_셋이_맞으면_통과한다():
    check_set(_payloads(), expected="TFTSet18")


def test_집계가_지난_셋이면_거부한다():
    with pytest.raises(SetMismatch) as err:
        check_set(_payloads(cluster_set="TFTSet17"), expected="TFTSet18")
    assert "TFTSet17" in str(err.value)


def test_early만_지난_셋이어도_거부한다():
    with pytest.raises(SetMismatch) as err:
        check_set(_payloads(early_set="TFTSet17"), expected="TFTSet18")
    assert "early" in str(err.value)


def test_셋_필드가_없으면_거부한다():
    payloads = _payloads()
    del payloads["early"]["tft_set"]
    with pytest.raises(SetMismatch):
        check_set(payloads, expected="TFTSet18")


def test_페이로드가_통째로_없으면_거부한다():
    # 값이 틀린 것만 잡고 키가 빠진 건 통과시키면 게이트에 우회로가 생긴다.
    payloads = _payloads()
    del payloads["early"]
    with pytest.raises(SetMismatch):
        check_set(payloads, expected="TFTSet18")


def test_cluster_id가_맞으면_그_값을_돌려준다():
    assert pin_cluster(_payloads(cluster_id=410, data_id=410)) == 410


def test_cluster_id가_어긋나면_거부한다():
    with pytest.raises(ClusterMismatch):
        pin_cluster(_payloads(cluster_id=410, data_id=409))
```

`tests/test_sources.py`:

```python
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
```

- [ ] **Step 3: 테스트가 실패하는지 확인한다**

Run: `python -m pytest tests/ -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.validate'`

- [ ] **Step 4: `src/sources.py`를 쓴다**

```python
"""HTTP와 엔드포인트 정의. 네트워크를 만지는 곳은 여기뿐이다."""

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DAILY = ROOT / "data" / "daily"
DIST = ROOT / "dist"

UA = "tft-challenger/1.0 (+https://github.com/PHONE-BOOT-H/tft-challenger)"

_COMPS = "https://api-hc.metatft.com/tft-comps-api"
_EARLY = "https://api.metatft.com/tft-early-comps/comps_overview"
_DDRAGON = "https://ddragon.leagueoflegends.com"


class FetchError(RuntimeError):
    """받아오기 실패. 호출자는 마지막 성공분으로 버틴다."""


def load_config():
    return json.loads((ROOT / "data" / "config.json").read_text(encoding="utf-8"))


def get_json(url, timeout=40, retries=2):
    """JSON을 받는다. 실패하면 지수 백오프로 재시도하고, 끝내 실패하면 FetchError."""
    headers = {"User-Agent": UA, "Accept": "application/json"}
    last = None
    for attempt in range(retries + 1):
        try:
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            last = exc
            if attempt < retries:
                time.sleep(2**attempt)
    raise FetchError(f"{url} 실패: {last}")


def build_urls(cfg):
    """설정에서 다섯 엔드포인트 URL을 만든다."""
    window = f"queue=1100&patch=current&days={cfg['days']}"
    server = cfg["server"]
    return {
        "latest_cluster_id": f"{_COMPS}/latest_cluster_id",
        "comps_stats_low": f"{_COMPS}/comps_stats?{window}&rank={cfg['low_rank']}&server={server}",
        "comps_stats_high": f"{_COMPS}/comps_stats?{window}&rank={cfg['high_rank']}&server={server}",
        "comps_data": f"{_COMPS}/comps_data",
        "early": _EARLY,
    }


def ddragon_urls():
    """ddragon 최신 버전과 ko_KR 파일 URL.

    hero/queue/trap은 403이라 요청하지 않는다 (실측).
    """
    version = get_json(f"{_DDRAGON}/api/versions.json")[0]
    base = f"{_DDRAGON}/cdn/{version}/data/ko_KR"
    files = {name: f"{base}/tft-{name}.json"
             for name in ("champion", "trait", "item", "augments")}
    return version, files
```

- [ ] **Step 5: `src/validate.py`를 쓴다**

```python
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
    """받아온 페이로드 전부가 기대한 셋인지 확인한다. 하나라도 어긋나면 예외.

    키가 아예 없는 것도 불일치로 친다. 게이트에 우회로를 남기면 안 된다.
    """
    missing = [key for key in _SET_SOURCES if key not in payloads]
    if missing:
        raise SetMismatch(f"페이로드 누락: {missing}")

    bad = []
    for key in _SET_SOURCES:
        got = payloads[key].get("tft_set")
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
```

- [ ] **Step 6: 테스트가 통과하는지 확인한다**

Run: `python -m pytest tests/ -q`
Expected: PASS — 10 passed

- [ ] **Step 7: 커밋한다**

```bash
git add src/ tests/ data/config.json requirements-dev.txt
git commit -m "feat: 셋 게이트와 HTTP 계층 추가

집계 사이트가 셋 전환 후에도 지난 셋 데이터를 내주는 것을 실측 확인했다.
셋/cluster_id가 어긋나면 렌더 자체를 거부한다."
git push origin main
```

---

### Task 2: 수집

**Files:**
- Create: `src/fetch.py`
- Test: 순수 I/O라 단위 테스트가 값을 못 만든다. 수동 실행으로 확인하고, 파싱 로직은 Task 3에서 픽스처로 검증한다.

**Interfaces:**
- Consumes: `sources.get_json`, `sources.build_urls`, `sources.ddragon_urls`, `sources.load_config`, `sources.RAW`
- Produces:
  - `fetch.fetch_all(cfg: dict) -> dict[str, dict]` — 키: `latest_cluster_id`, `comps_stats_low`, `comps_stats_high`, `comps_data`, `early`, `ddragon_version`, `champion`, `trait`, `item`, `augments`
  - 부수효과: 각 페이로드를 `data/raw/<key>.json`으로 저장

- [ ] **Step 1: `src/fetch.py`를 쓴다**

```python
"""수집만 한다. 파싱도 판단도 하지 않는다."""

import json

from . import sources


def fetch_all(cfg):
    """MetaTFT 다섯 개와 ddragon 네 개를 받아 data/raw/에 그대로 저장한다."""
    sources.RAW.mkdir(parents=True, exist_ok=True)
    payloads = {}

    urls = sources.build_urls(cfg)
    for key in ("latest_cluster_id", "comps_data", "comps_stats_low",
                "comps_stats_high", "early"):
        payloads[key] = sources.get_json(urls[key])

    version, files = sources.ddragon_urls()
    payloads["ddragon_version"] = version
    for name, url in files.items():
        payloads[name] = sources.get_json(url)

    for key, value in payloads.items():
        path = sources.RAW / f"{key}.json"
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    return payloads


if __name__ == "__main__":
    result = fetch_all(sources.load_config())
    for key, value in result.items():
        size = len(json.dumps(value, ensure_ascii=False))
        print(f"{key:20} {size:>10,}자")
```

- [ ] **Step 2: 실제로 돌려서 열 개가 다 떨어지는지 본다**

Run: `python -m src.fetch`
Expected: 열 줄이 찍히고 `data/raw/`에 파일 열 개. 크기 기준: `latest_cluster_id`는 63자 안팎, `early`는 80만자 이상, `comps_data`는 30만자 이상.

- [ ] **Step 3: raw가 커밋되지 않는지 확인한다**

Run: `git status --short`
Expected: `data/raw/`가 목록에 없다. 있으면 `.gitignore`의 `data/raw/` 줄을 확인한다.

- [ ] **Step 4: 커밋한다**

```bash
git add src/fetch.py
git commit -m "feat: MetaTFT·ddragon 수집기 추가"
git push origin main
```

---

### Task 3: 통계 파싱과 Δ 계산

이 프로젝트가 존재하는 이유다. Δ는 브실골 AVP에서 다이아+ AVP를 뺀 값이고, 음수면 저티어에서 더 좋은 덱이다.

**Files:**
- Create: `src/comps.py`, `tests/test_comps.py`, `tests/fixtures/comps_stats_low.json`, `tests/fixtures/comps_stats_high.json`

**Interfaces:**
- Consumes: 없음 (순수 함수)
- Produces:
  - `comps.avp(places: list[int]) -> float`
  - `comps.distribution(places: list[int]) -> list[float]` — 길이 8, 합 1.0
  - `comps.parse_stats(payload: dict) -> tuple[dict[str, dict], int]` — `({cluster: {"places","count","avp","dist"}}, 전체_판수)`
  - `comps.merge_delta(low: dict, low_total: int, high: dict) -> list[dict]` — 각 원소는 `{"cluster","avp_low","avp_high","delta","count","pick_rate","expected_contest","dist"}`, `delta` 오름차순 정렬

- [ ] **Step 1: 픽스처를 만든다**

`tests/fixtures/comps_stats_low.json` — 실제 응답 모양 그대로, 첫 원소가 전체 판수 마커다:

```json
{"results": [
  {"cluster": "", "places": [1000]},
  {"cluster": "410000", "places": [30, 25, 20, 15, 4, 3, 2, 1, 100], "count": 100},
  {"cluster": "410001", "places": [5, 6, 7, 7, 15, 20, 20, 20, 100], "count": 100},
  {"cluster": "410002", "places": [10, 10, 10, 10, 15, 15, 15, 15, 100], "count": 100}
]}
```

`tests/fixtures/comps_stats_high.json`:

```json
{"results": [
  {"cluster": "", "places": [2000]},
  {"cluster": "410000", "places": [5, 6, 7, 7, 15, 20, 20, 20, 100], "count": 100},
  {"cluster": "410001", "places": [30, 25, 20, 15, 4, 3, 2, 1, 100], "count": 100},
  {"cluster": "410002", "places": [10, 10, 10, 10, 15, 15, 15, 15, 100], "count": 100}
]}
```

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`tests/test_comps.py`:

```python
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
```

- [ ] **Step 3: 테스트가 실패하는지 확인한다**

Run: `python -m pytest tests/test_comps.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.comps'`

- [ ] **Step 4: `src/comps.py`를 쓴다**

```python
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
            "expected_contest": pick_rate * LOBBY_SIZE,
            "dist": entry["dist"],
        })
    rows.sort(key=lambda row: (row["delta"] is None, row["delta"] or 0.0))
    return rows
```

- [ ] **Step 5: 테스트가 통과하는지 확인한다**

Run: `python -m pytest tests/ -q`
Expected: PASS — 17 passed

- [ ] **Step 6: 실제 데이터로 눈으로 확인한다**

Run:
```bash
python -c "
import json
from src import comps, sources
low, total = comps.parse_stats(json.loads((sources.RAW/'comps_stats_low.json').read_text(encoding='utf-8')))
high, _ = comps.parse_stats(json.loads((sources.RAW/'comps_stats_high.json').read_text(encoding='utf-8')))
rows = comps.merge_delta(low, total, high)
print(f'전체 {total:,}판, 덱 {len(rows)}개')
for r in rows[:5]:
    d = '없음' if r['delta'] is None else f\"{r['delta']:+.2f}\"
    print(f\"  {r['cluster']}  브실골 {r['avp_low']:.2f}  델타 {d}  픽률 {r['pick_rate']:.1%}\")
"
```
Expected: 전체 판수 19만 안팎, 덱 수십 개, Δ 음수인 덱이 맨 앞. **평균등수가 전부 3.0~5.5 사이여야 한다** — 이 범위를 벗어나면 `places` 마지막 원소를 잘못 세고 있는 것이다.

- [ ] **Step 7: 커밋한다**

```bash
git add src/comps.py tests/test_comps.py tests/fixtures/
git commit -m "feat: 평균등수·등수분포·티어간 델타 계산

Delta = 브실골 AVP - 다이아+ AVP. 음수면 저티어 전용 덱.
places의 마지막 원소는 총합이라 등수 계산에서 제외한다."
git push origin main
```

---

### Task 4: 한글 이름 색인

**Files:**
- Create: `src/names.py`, `tests/test_names.py`, `tests/fixtures/ddragon_champion.json`, `tests/fixtures/ddragon_trait.json`

**Interfaces:**
- Consumes: 없음 (순수 함수)
- Produces:
  - `names.build_index(champion: dict, trait: dict, item: dict, augments: dict, set_path: str) -> dict[str, str]` — apiName → 한글 이름
  - `names.unit_costs(champion: dict, set_path: str) -> dict[str, int]` — apiName → 코스트
  - `names.ko(index: dict, api_name: str) -> str` — 없으면 접두사를 벗겨 되돌린다

- [ ] **Step 1: 픽스처를 만든다**

`tests/fixtures/ddragon_champion.json` — 키가 apiName이 아니라 경로라는 점이 핵심이다:

```json
{"type": "champion", "version": "16.17.1", "data": {
  "Maps/Shipping/Map22/Sets/TFTSet18/Shop/DA_18_Xayah": {"id": "DA_18_Xayah", "name": "자야", "tier": 1, "cost": 1},
  "Maps/Shipping/Map22/Sets/TFTSet18/Shop/DA_Lux18_Light": {"id": "DA_Lux18_Light", "name": "럭스", "tier": 5, "cost": 5},
  "Maps/Shipping/Map22/Sets/TFTSet17/Shop/TFT17_Aatrox": {"id": "TFT17_Aatrox", "name": "아트록스", "tier": 1, "cost": 1}
}}
```

`tests/fixtures/ddragon_trait.json`:

```json
{"type": "trait", "version": "16.17.1", "data": {
  "Maps/Shipping/Map22/Sets/TFTSet18/Trait/DA_18_Adaptor": {"id": "DA_18_Adaptor", "name": "적응가"},
  "Maps/Shipping/Map22/Sets/TFTSet17/Trait/TFT17_Duelist": {"id": "TFT17_Duelist", "name": "결투가"}
}}
```

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`tests/test_names.py`:

```python
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
```

- [ ] **Step 3: 테스트가 실패하는지 확인한다**

Run: `python -m pytest tests/test_names.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.names'`

- [ ] **Step 4: `src/names.py`를 쓴다**

```python
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
```

- [ ] **Step 5: 테스트가 통과하는지 확인한다**

Run: `python -m pytest tests/ -q`
Expected: PASS — 24 passed

- [ ] **Step 6: 실제 ddragon으로 셋18 로스터를 세어본다**

Run:
```bash
python -c "
import json, collections
from src import names, sources
champ = json.loads((sources.RAW/'champion.json').read_text(encoding='utf-8'))
costs = names.unit_costs(champ, '/Sets/TFTSet18/')
print('셋18 유닛', len(costs), '개')
print('코스트 분포', dict(sorted(collections.Counter(costs.values()).items())))
"
```
Expected: 64개 안팎, 코스트 분포가 `{1: 12, 2: 10, 3: 12, 4: 12, 5: 18}` 근처. **0개가 나오면** `config.json`의 `ddragon_set_path`가 셋 이름과 안 맞는 것이다.

- [ ] **Step 7: 커밋한다**

```bash
git add src/names.py tests/test_names.py tests/fixtures/
git commit -m "feat: ddragon ko_KR 한글 이름 색인

셋 필터는 키 경로(/Sets/TFTSet18/)로 한다. id 접두사로 거르면
DA_Lux18_* 등 변형 유닛 11개를 놓친다."
git push origin main
```

---

### Task 5: 단계별 빌드업 경로

`early-comps`는 `comps`와 클러스터 공간이 다르다(실측: 409 대 2630). id로 못 잇는다. 양쪽 다 유닛 목록을 주므로 유닛 집합 유사도로 잇는다.

**Files:**
- Create: `src/paths.py`, `tests/test_paths.py`, `tests/fixtures/early.json`, `tests/fixtures/comps_data.json`

**Interfaces:**
- Consumes: 없음 (순수 함수)
- Produces:
  - `paths.jaccard(a: set, b: set) -> float`
  - `paths.final_units(comps_data: dict) -> dict[str, set[str]]`
  - `paths.stage_units(early: dict, stage: str) -> list[set[str]]`
  - `paths.match_stage5(final: dict[str, set], early: dict, threshold: float = 0.5) -> dict[str, int]`
  - `paths.route(early: dict, stage5_index: int) -> list[dict]` — `[{"stage","units","avp"}, ...]` 2→5 순
  - `paths.STAGES: tuple[str, ...]`

- [ ] **Step 1: 픽스처를 만든다**

`tests/fixtures/early.json` — `units`가 리스트가 아니라 딕셔너리이고, `backwards_links` 길이가 이전 스테이지 덱 수와 같다:

```json
{"tft_set": "TFTSet18", "clustering_id": 2630, "sampleSize": 76838, "comps_overview": {
  "stage-2": {"comps": [
    {"cluster": "0", "units": {"DA_18_A": {}, "DA_18_B": {}}, "stats": {"final_place_avg": 4.5}},
    {"cluster": "1", "units": {"DA_18_C": {}, "DA_18_D": {}}, "stats": {"final_place_avg": 4.8}}
  ]},
  "stage-3": {"comps": [
    {"cluster": "0", "units": {"DA_18_A": {}, "DA_18_B": {}, "DA_18_E": {}}, "stats": {"final_place_avg": 4.2}, "backwards_links": [90.0, 10.0]},
    {"cluster": "1", "units": {"DA_18_C": {}, "DA_18_D": {}, "DA_18_F": {}}, "stats": {"final_place_avg": 4.6}, "backwards_links": [5.0, 95.0]}
  ]},
  "stage-4": {"comps": [
    {"cluster": "0", "units": {"DA_18_A": {}, "DA_18_B": {}, "DA_18_E": {}, "DA_18_G": {}}, "stats": {"final_place_avg": 3.9}, "backwards_links": [80.0, 20.0]}
  ]},
  "stage-5": {"comps": [
    {"cluster": "0", "units": {"DA_18_A": {}, "DA_18_B": {}, "DA_18_E": {}, "DA_18_G": {}, "DA_18_H": {}}, "stats": {"final_place_avg": 3.7}, "backwards_links": [100.0]}
  ]}
}}
```

`tests/fixtures/comps_data.json`:

```json
{"tft_set": "TFTSet18", "cluster_id": 410, "results": {"data": {"cluster_details": {
  "410000": {"Cluster": 410000, "units_string": "DA_18_A, DA_18_B, DA_18_E, DA_18_G, DA_18_H"},
  "410001": {"Cluster": 410001, "units_string": "DA_18_X, DA_18_Y, DA_18_Z"}
}}}}
```

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`tests/test_paths.py`:

```python
import json
from pathlib import Path

import pytest

from src.paths import final_units, jaccard, match_stage5, route, stage_units

FIXTURES = Path(__file__).parent / "fixtures"


def _load(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def test_같은_집합은_1이다():
    assert jaccard({"a", "b"}, {"a", "b"}) == pytest.approx(1.0)


def test_겹치지_않으면_0이다():
    assert jaccard({"a"}, {"b"}) == pytest.approx(0.0)


def test_빈_집합끼리는_0이다():
    assert jaccard(set(), set()) == pytest.approx(0.0)


def test_최종덱_유닛을_units_string에서_뽑는다():
    units = final_units(_load("comps_data"))
    assert units["410000"] == {"DA_18_A", "DA_18_B", "DA_18_E", "DA_18_G", "DA_18_H"}


def test_스테이지_유닛은_딕셔너리_키에서_뽑는다():
    stages = stage_units(_load("early"), "stage-2")
    assert stages[0] == {"DA_18_A", "DA_18_B"}


def test_유닛이_같은_최종덱과_stage5를_잇는다():
    matched = match_stage5(final_units(_load("comps_data")), _load("early"))
    assert matched["410000"] == 0


def test_안_닮은_덱은_아예_넣지_않는다():
    # 410001은 stage-5와 유닛이 하나도 안 겹친다. 억지로 붙이면 틀린 경로가 나간다.
    matched = match_stage5(final_units(_load("comps_data")), _load("early"))
    assert "410001" not in matched


def test_경로는_스테이지2부터_5까지_네_칸이다():
    steps = route(_load("early"), 0)
    assert [step["stage"] for step in steps] == ["stage-2", "stage-3", "stage-4", "stage-5"]


def test_경로는_backwards_links의_최대값을_따라간다():
    # stage-4[0].backwards_links = [80, 20] -> stage-3[0]
    # stage-3[0].backwards_links = [90, 10] -> stage-2[0]
    steps = route(_load("early"), 0)
    assert steps[0]["units"] == ["DA_18_A", "DA_18_B"]
    assert steps[0]["avp"] == pytest.approx(4.5)
```

- [ ] **Step 3: 테스트가 실패하는지 확인한다**

Run: `python -m pytest tests/test_paths.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.paths'`

- [ ] **Step 4: `src/paths.py`를 쓴다**

```python
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
    matched = {}
    for cluster, units in final.items():
        scores = [(jaccard(units, board), index) for index, board in enumerate(stage5)]
        if not scores:
            continue
        best_score, best_index = max(scores)
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
```

- [ ] **Step 5: 테스트가 통과하는지 확인한다**

Run: `python -m pytest tests/ -q`
Expected: PASS — 33 passed

- [ ] **Step 6: 실제 데이터로 매칭률을 잰다**

Run:
```bash
python -c "
import json
from src import paths, sources
early = json.loads((sources.RAW/'early.json').read_text(encoding='utf-8'))
data = json.loads((sources.RAW/'comps_data.json').read_text(encoding='utf-8'))
final = paths.final_units(data)
matched = paths.match_stage5(final, early)
print(f'최종덱 {len(final)}개 중 {len(matched)}개에 경로가 붙었다 ({len(matched)/len(final):.0%})')
"
```
Expected: 매칭률이 찍힌다. **50% 미만이면 임계값 0.5가 너무 빡빡한 것이니 0.4로 낮추고 다시 잰다.** 95%를 넘으면 오히려 느슨한지 의심하고 표본 세 개를 눈으로 확인한다. 최종 수치를 커밋 메시지에 적는다.

- [ ] **Step 7: 커밋한다**

```bash
git add src/paths.py tests/test_paths.py tests/fixtures/
git commit -m "feat: 유닛 집합 매칭으로 단계별 빌드업 경로 연결

early-comps와 comps는 클러스터 공간이 달라 id로 못 잇는다.
Jaccard 임계값 미달이면 경로를 붙이지 않는다 - 틀린 경로가 없느니만 못하다."
git push origin main
```

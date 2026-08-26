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

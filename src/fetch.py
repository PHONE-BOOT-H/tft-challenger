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

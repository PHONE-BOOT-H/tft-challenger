"""파이프라인. 수집 -> 게이트 -> 조인 -> 스냅샷 -> 렌더."""

import json
import sys
from datetime import datetime, timedelta, timezone

from . import comps, fetch, indexes, names, notes, patchdiff, paths, render, sources, validate

KST = timezone(timedelta(hours=9))


def _patch_label(payloads):
    """패치 식별자.

    목적은 예쁜 이름표가 아니라 "바뀌었는가"를 감지하는 것이다.
    display_patch가 있으면 진짜 패치 번호("18.2")지만 실측 응답에는 없었다.
    없으면 클러스터 id를 그대로 쓴다 — 클러스터는 패치마다 회전하므로 감지가 된다.
    즉 이 값은 패치 번호가 아닐 수 있다. 화면에 "패치"라고 붙이거나 패치노트
    URL을 만들기 전에 notes.is_patch_number()로 걸러야 한다.
    """
    for key in ("comps_stats_low", "comps_data"):
        label = payloads.get(key, {}).get("display_patch")
        if label:
            return str(label)
    return str(payloads["latest_cluster_id"]["cluster_id"])


def build_context(payloads, cfg, now):
    """받아온 원본에서 렌더용 컨텍스트를 만든다."""
    index = names.build_index(
        champion=payloads["champion"], trait=payloads["trait"],
        item=payloads["item"], augments=payloads["augments"],
        set_path=cfg["ddragon_set_path"],
    )

    low, total = comps.parse_stats(payloads["comps_stats_low"])
    high, _ = comps.parse_stats(payloads["comps_stats_high"])
    rows = [row for row in comps.merge_delta(low, total, high)
            if row["count"] >= cfg["min_games"]]

    final = paths.final_units(payloads["comps_data"])
    matched = paths.match_stage5(final, payloads["early"])

    decks = []
    for row in rows[:cfg["top_n"]]:
        units = sorted(final.get(row["cluster"], set()))
        row = dict(row)
        row["name"] = " · ".join(names.ko(index, unit) for unit in units[:3]) or row["cluster"]
        row["route"] = []
        if row["cluster"] in matched:
            for step in paths.route(payloads["early"], matched[row["cluster"]]):
                row["route"].append({
                    "stage": step["stage"],
                    "units": [names.ko(index, unit) for unit in step["units"]],
                    "avp": step["avp"],
                })
        decks.append(row)

    patch = _patch_label(payloads)
    snapshot = {"patch": patch, "decks": [
        {"cluster": d["cluster"], "name": d["name"], "avp_low": d["avp_low"]} for d in decks]}

    day = now.strftime("%Y-%m-%d")
    diff = patchdiff.compare(patchdiff.load_previous(before=day), snapshot, cfg["top_n"])
    patchdiff.save(snapshot, day)
    summary = notes.maybe_summarize(diff, [deck["name"] for deck in decks])

    all_rows = [dict(row, name=" · ".join(
        names.ko(index, unit) for unit in sorted(final.get(row["cluster"], set()))[:3]) or row["cluster"])
        for row in rows]
    index_data = indexes.build(all_rows, final, names.unit_costs(payloads["champion"], cfg["ddragon_set_path"]))

    return {
        "set": payloads["latest_cluster_id"]["tft_set"],
        "patch": patch,
        "generated_at": now.strftime("%Y-%m-%d %H:%M KST"),
        # 페이지가 스스로 나이를 계산할 수 있게 기계가 읽는 형태로도 같이 내보낸다.
        "generated_iso": now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_games": total,
        "sample_days": cfg["days"],
        "stale_hours": 0,
        "decks": decks,
        "diff": diff,
        "fundamentals": json.loads(
            (sources.ROOT / "data" / "fundamentals.json").read_text(encoding="utf-8")),
        "notes": summary,
        "indexes": index_data,
        "name_of": lambda unit: names.ko(index, unit),
    }


def main():
    cfg = sources.load_config()
    now = datetime.now(KST)
    payloads = fetch.fetch_all(cfg)

    try:
        validate.check_set(payloads, cfg["expected_set"])
        validate.pin_cluster(payloads)
    except (validate.SetMismatch, validate.ClusterMismatch) as exc:
        # 조용히 옛날 데이터를 내놓느니 시끄럽게 죽는다.
        print(f"게이트 정지: {exc}", file=sys.stderr)
        return 2

    context = build_context(payloads, cfg, now)
    sources.DIST.mkdir(parents=True, exist_ok=True)
    (sources.DIST / "index.html").write_text(render.page(context), encoding="utf-8")
    print(f"렌더 완료: 덱 {len(context['decks'])}개, 표본 {context['total_games']:,}판")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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


def _base_context(cfg, now):
    """정상 경로와 게이트정지 경로가 공유하는 뼈대 — 시각 표기와 기본기.

    기본기(data/fundamentals.json)는 집계 사이트와 무관하게 항상 존재해야 한다.
    """
    return {
        "generated_at": now.strftime("%Y-%m-%d %H:%M KST"),
        "generated_iso": now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sample_days": cfg["days"],
        "stale_hours": 0,
        "fundamentals": json.loads(
            (sources.ROOT / "data" / "fundamentals.json").read_text(encoding="utf-8")),
    }


def gate_stop_context(cfg, now, exc):
    """게이트가 막았을 때 렌더할 최소 컨텍스트 — 덱 통계 없이 기본기만.

    payloads를 신뢰할 수 없는 상태이므로 어떤 계산도 하지 않는다.
    diff는 빈 딕셔너리로 둔다 — _diff_banner는 patch_changed가 없으면 바로 빈 문자열을 낸다.
    """
    return {
        **_base_context(cfg, now),
        "set": cfg["expected_set"],
        "patch": None,
        "total_games": 0,
        "decks": [],
        "diff": {},
        "gate_stop": (f"집계 사이트가 아직 이번 셋 데이터를 내주지 않는다 — {exc}."),
    }


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
    # 매칭이 무너지면(상류 스키마 변경 등) 경로가 조용히 사라진다. 비율을 남겨 눈에 띄게 한다.
    print(f"경로 매칭 {len(matched)}/{len(final)}")

    def deck_name(cluster):
        """상위 세 유닛의 한글 이름. 이름을 못 만들면 내부 id 대신 이름 미상."""
        units = sorted(final.get(cluster, set()))[:3]
        return " · ".join(names.ko(index, unit) for unit in units) or "이름 미상"

    decks = []
    for row in rows[:cfg["top_n"]]:
        row = dict(row)
        row["name"] = deck_name(row["cluster"])
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
    tft_set = payloads["latest_cluster_id"]["tft_set"]
    # 셋을 같이 넣는다. 셋 경계를 넘어 diff하면 새 셋 첫 빌드가 전 덱을 "새로 진입"이라 외친다.
    snapshot = {"patch": patch, "set": tft_set, "decks": [
        {"cluster": d["cluster"], "name": d["name"], "avp_low": d["avp_low"]} for d in decks]}

    day = now.strftime("%Y-%m-%d")
    diff = patchdiff.compare(patchdiff.load_previous(before=day), snapshot, cfg["top_n"])
    patchdiff.save(snapshot, day)
    summary = notes.maybe_summarize(diff, [deck["name"] for deck in decks])

    all_rows = [dict(row, name=deck_name(row["cluster"])) for row in rows]
    index_data = indexes.build(all_rows, final, names.unit_costs(payloads["champion"], cfg["ddragon_set_path"]))

    return {
        **_base_context(cfg, now),
        "set": tft_set,
        "patch": patch,
        "total_games": total,
        "decks": decks,
        "diff": diff,
        "notes": summary,
        "indexes": index_data,
        "name_of": lambda unit: names.ko(index, unit),
        "gate_stop": None,
    }


def _render_to_dist(context):
    sources.DIST.mkdir(parents=True, exist_ok=True)
    (sources.DIST / "index.html").write_text(render.page(context), encoding="utf-8")


def main():
    cfg = sources.load_config()
    now = datetime.now(KST)
    payloads = fetch.fetch_all(cfg)

    try:
        validate.check_set(payloads, cfg["expected_set"])
        validate.pin_cluster(payloads)
    except (validate.SetMismatch, validate.ClusterMismatch) as exc:
        # 조용히 옛날 데이터를 내놓느니 시끄럽게 죽는다 — 그래도 기본기 화면은 띄운다.
        print(f"게이트 정지: {exc}", file=sys.stderr)
        _render_to_dist(gate_stop_context(cfg, now, exc))
        print("게이트 정지 — 기본기만 렌더, 스냅샷은 남기지 않는다", file=sys.stderr)
        return 2

    context = build_context(payloads, cfg, now)
    _render_to_dist(context)
    print(f"렌더 완료: 덱 {len(context['decks'])}개, 표본 {context['total_games']:,}판")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

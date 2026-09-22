#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from common import (
    CATALOG, COMETS, DATA, JPL_QUERY, CATALOG_FIELDS,
    get_json, normalize_catalog_record, write_if_changed,
    utc_now_iso, bucket_for, load_json
)

def fetch_all(page_size: int = 500):
    offset = 0
    all_rows = []
    expected_total = None

    while True:
        data = get_json(JPL_QUERY, {
            "sb-kind": "c",
            "fields": ",".join(CATALOG_FIELDS),
            "sort": "spkid",
            "limit": page_size,
            "limit-from": offset,
            "full-prec": "true",
        })

        fields = data.get("fields") or []
        rows = data.get("data") or []
        expected_total = int(data.get("count") or data.get("total") or 0)

        if not rows:
            break

        for row in rows:
            raw = dict(zip(fields, row))
            all_rows.append(normalize_catalog_record(raw))

        offset += len(rows)
        print(f"JPL catalog: {offset}/{expected_total or '?'}")

        if expected_total and offset >= expected_total:
            break

    return all_rows, expected_total or len(all_rows)

def make_index(records):
    index = []
    for r in records:
        index.append({
            "spkid": r["spkid"],
            "bucket": r["bucket"],
            "designation": r.get("pdes"),
            "full_name": r.get("full_name"),
            "name": r.get("name"),
            "prefix": r.get("prefix"),
            "kind": r.get("kind"),
            "class": r.get("class"),
            "orbit_id": r.get("orbit_id"),
            "epoch": r.get("epoch"),
            "detail": (COMETS / r["bucket"] / f'{r["spkid"]}.json').exists(),
        })
    return index

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page-size", type=int, default=500)
    args = ap.parse_args()

    CATALOG.mkdir(parents=True, exist_ok=True)
    COMETS.mkdir(parents=True, exist_ok=True)

    old_index_doc = load_json(CATALOG / "index.json", {}) or {}
    if isinstance(old_index_doc, dict):
        old_index = old_index_doc.get("records") or []
    elif isinstance(old_index_doc, list):
        # v1 compatibility / defensive fallback
        old_index = old_index_doc
    else:
        old_index = []

    old_map = {
        str(x.get("spkid")): x
        for x in old_index
        if isinstance(x, dict) and x.get("spkid") is not None
    }

    records, total = fetch_all(args.page_size)
    records.sort(key=lambda x: int(x["spkid"]) if x["spkid"].isdigit() else x["spkid"])

    shards = defaultdict(list)
    for r in records:
        shards[r["bucket"]].append(r)

    changed_files = []
    for i in range(64):
        b = f"{i:02x}"
        if write_if_changed(CATALOG / f"{b}.json", {
            "schema_version": 2,
            "bucket": b,
            "count": len(shards[b]),
            "records": shards[b],
        }):
            changed_files.append(f"data/catalog/{b}.json")

    index = make_index(records)
    if write_if_changed(CATALOG / "index.json", {
        "schema_version": 2,
        "source": "JPL SBDB Query API",
        "count": len(index),
        "records": index,
    }):
        changed_files.append("data/catalog/index.json")

    new_map = {str(x["spkid"]): x for x in index}
    added = sorted(set(new_map) - set(old_map))
    removed = sorted(set(old_map) - set(new_map))
    changed_orbits = sorted(
        spkid for spkid in (set(new_map) & set(old_map))
        if (
            new_map[spkid].get("orbit_id") != old_map[spkid].get("orbit_id")
            or new_map[spkid].get("epoch") != old_map[spkid].get("epoch")
        )
    )

    detail_count = sum(1 for _ in COMETS.glob("*/*.json"))
    meta = {
        "schema_version": 2,
        "name": "星の鳥",
        "subtitle": "Comet Orbit Database for Nicole",
        "storage": "GitHub static JSON",
        "updated_at": utc_now_iso(),
        "source": "JPL Small-Body Database",
        "comet_count": len(records),
        "jpl_reported_count": total,
        "detail_file_count": detail_count,
        "catalog_shards": 64,
        "last_update": {
            "added": len(added),
            "removed": len(removed),
            "orbit_changed": len(changed_orbits),
            "changed_files": len(changed_files),
        },
        "paths": {
            "search_index": "data/catalog/index.json",
            "catalog_shard_template": "data/catalog/{bucket}.json",
            "detail_template": "data/comets/{bucket}/{spkid}.json",
        },
    }
    # meta contains updated_at, so it will intentionally change once per completed run.
    write_if_changed(DATA / "meta.json", meta, pretty=True)

    # Used by refresh_existing_details.py in the same workflow.
    state = {
        "added_spkids": added,
        "removed_spkids": removed,
        "orbit_changed_spkids": changed_orbits,
    }
    (DATA / ".last_catalog_diff.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

    print(json.dumps(meta, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

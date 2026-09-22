#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from common import DATA, CATALOG, COMETS, load_json
from fetch_detail import fetch_one

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=20)
    args = ap.parse_args()

    index_doc = load_json(CATALOG / "index.json", {}) or {}
    index = {str(x["spkid"]): x for x in (index_doc.get("records") or [])}

    existing = {}
    for path in COMETS.glob("*/*.json"):
        doc = load_json(path, {}) or {}
        spkid = str(doc.get("spkid") or path.stem)
        existing[spkid] = doc

    needs = []
    for spkid, doc in existing.items():
        current = index.get(spkid)
        if not current:
            continue
        old_orbit = (doc.get("orbit") or {}).get("orbit_id")
        old_epoch = (doc.get("orbit") or {}).get("epoch")
        if old_orbit != current.get("orbit_id") or old_epoch != current.get("epoch"):
            needs.append(spkid)

    needs = needs[:max(0, args.limit)]
    print(f"Existing detail files needing refresh: {len(needs)}")

    failures = []
    for spkid in needs:
        try:
            fetch_one(spkid)
        except Exception as exc:
            failures.append({"spkid": spkid, "error": str(exc)})

    if failures:
        print(json.dumps({"failures": failures}, ensure_ascii=False, indent=2))
        raise SystemExit(1)

if __name__ == "__main__":
    main()

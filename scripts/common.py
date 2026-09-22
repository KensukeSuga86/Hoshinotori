#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CATALOG = DATA / "catalog"
COMETS = DATA / "comets"

JPL_QUERY = "https://ssd-api.jpl.nasa.gov/sbdb_query.api"
JPL_DETAIL = "https://ssd-api.jpl.nasa.gov/sbdb.api"

USER_AGENT = "Hoshinotori/2.0 (Comet Orbit Database for Nicole)"

CATALOG_FIELDS = [
    "spkid","pdes","full_name","name","prefix","kind","class",
    "orbit_id","epoch","equinox",
    "e","a","q","i","om","w","ma","tp","per","n","ad",
    "sigma_e","sigma_a","sigma_q","sigma_i","sigma_om","sigma_w",
    "sigma_ma","sigma_tp","sigma_per","sigma_n","sigma_ad",
    "source","soln_date","producer","data_arc","first_obs","last_obs",
    "n_obs_used","n_del_obs_used","n_dop_obs_used","two_body",
    "pe_used","sb_used","condition_code","rms",
    "t_jup","moid","moid_jup"
]

NUMBER_FIELDS = {
    "epoch","e","a","q","i","om","w","ma","tp","per","n","ad",
    "sigma_e","sigma_a","sigma_q","sigma_i","sigma_om","sigma_w",
    "sigma_ma","sigma_tp","sigma_per","sigma_n","sigma_ad",
    "data_arc","n_obs_used","n_del_obs_used","n_dop_obs_used",
    "condition_code","rms","t_jup","moid","moid_jup"
}

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def bucket_for(spkid: str) -> str:
    try:
        return f"{int(str(spkid)) % 64:02x}"
    except Exception:
        # Rare defensive fallback for unexpected identifiers.
        return f"{sum(str(spkid).encode('utf-8')) % 64:02x}"

def compact_json_bytes(obj: Any) -> bytes:
    return (json.dumps(
        obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ) + "\n").encode("utf-8")

def pretty_json_bytes(obj: Any) -> bytes:
    return (json.dumps(
        obj, ensure_ascii=False, sort_keys=True, indent=2
    ) + "\n").encode("utf-8")

def write_if_changed(path: Path, obj: Any, pretty: bool = False) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    new = pretty_json_bytes(obj) if pretty else compact_json_bytes(obj)
    try:
        old = path.read_bytes()
    except FileNotFoundError:
        old = None
    if old == new:
        return False
    path.write_bytes(new)
    return True

def load_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default

def get_json(url: str, params: dict[str, Any] | None = None, retries: int = 4) -> Any:
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)

    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={"Accept": "application/json", "User-Agent": USER_AGENT},
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:
            last = exc
            if attempt + 1 >= retries:
                raise
            time.sleep(2 ** attempt)
    raise last

def n(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return value

def normalize_catalog_record(raw: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for key, value in raw.items():
        if key in NUMBER_FIELDS:
            out[key] = n(value)
        else:
            out[key] = value if value not in ("", None) else None
    out["spkid"] = str(raw.get("spkid") or "")
    out["bucket"] = bucket_for(out["spkid"])
    return out

def detail_path(spkid: str) -> Path:
    return COMETS / bucket_for(spkid) / f"{spkid}.json"

def catalog_shard_path(bucket: str) -> Path:
    return CATALOG / f"{bucket}.json"

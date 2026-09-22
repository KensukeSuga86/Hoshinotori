#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from common import (
    JPL_DETAIL, detail_path, get_json, write_if_changed,
    utc_now_iso, bucket_for
)

def normalize_detail(spkid: str, data):
    obj = data.get("object") or {}
    orbit = data.get("orbit") or {}
    elements = {
        x.get("name"): {
            "value": x.get("value"),
            "sigma": x.get("sigma"),
            "units": x.get("units"),
            "title": x.get("title"),
            "label": x.get("label"),
        }
        for x in (orbit.get("elements") or [])
        if x.get("name")
    }

    return {
        "schema_version": 2,
        "source": "JPL SBDB API",
        "fetched_at": utc_now_iso(),
        "spkid": str(spkid),
        "bucket": bucket_for(str(spkid)),
        "identity": {
            "designation": obj.get("des"),
            "fullname": obj.get("fullname"),
            "shortname": obj.get("shortname"),
            "prefix": obj.get("prefix"),
            "kind": obj.get("kind"),
            "orbit_class": obj.get("orbit_class"),
            "alternate_designations": obj.get("des_alt") or [],
            "alternate_spkids": obj.get("spkid_alt") or [],
        },
        "orbit": {
            "orbit_id": orbit.get("orbit_id") or obj.get("orbit_id"),
            "epoch": orbit.get("epoch"),
            "equinox": orbit.get("equinox"),
            "source": orbit.get("source"),
            "producer": orbit.get("producer"),
            "solution_date": orbit.get("soln_date"),
            "covariance_epoch": orbit.get("cov_epoch"),
            "condition_code": orbit.get("condition_code"),
            "rms": orbit.get("rms"),
            "first_observation": orbit.get("first_obs"),
            "last_observation": orbit.get("last_obs"),
            "data_arc_days": orbit.get("data_arc"),
            "n_obs_used": orbit.get("n_obs_used"),
            "n_delay_obs_used": orbit.get("n_del_obs_used"),
            "n_doppler_obs_used": orbit.get("n_dop_obs_used"),
            "planetary_ephemeris": orbit.get("pe_used"),
            "perturber_ephemeris": orbit.get("sb_used"),
            "two_body": orbit.get("two_body"),
            "not_valid_before": orbit.get("not_valid_before"),
            "not_valid_after": orbit.get("not_valid_after"),
            "moid_earth_au": orbit.get("moid"),
            "moid_jupiter_au": orbit.get("moid_jup"),
            "tisserand_jupiter": orbit.get("t_jup"),
            "comment": orbit.get("comment"),
            "elements": elements,
            "model_parameters": orbit.get("model_pars") or [],
            "covariance": orbit.get("covariance"),
        },
        "physical_parameters": data.get("phys_par") or [],
    }

def fetch_one(spkid: str):
    data = get_json(JPL_DETAIL, {
        "spk": str(spkid),
        "full-prec": "1",
        "alt-des": "1",
        "alt-spk": "1",
        "cov": "mat",
        "phys-par": "1",
        "nv-fmt": "cd",
    })
    if data.get("code") or (data.get("message") and not data.get("object")):
        raise RuntimeError(data.get("message") or "JPL detail error")

    normalized = normalize_detail(str(spkid), data)
    path = detail_path(str(spkid))
    changed = write_if_changed(path, normalized, pretty=True)
    print(json.dumps({
        "ok": True,
        "spkid": str(spkid),
        "path": str(path),
        "changed": changed,
        "orbit_id": normalized["orbit"]["orbit_id"],
        "epoch": normalized["orbit"]["epoch"],
    }, ensure_ascii=False, indent=2))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spkid")
    args = ap.parse_args()
    fetch_one(args.spkid)

if __name__ == "__main__":
    main()

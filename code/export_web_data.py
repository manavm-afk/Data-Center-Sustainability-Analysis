"""
export_web_data.py — Front-end data layer
==========================================
Exports the derived analysis outputs as a front-end-agnostic JSON layer in
web-data/, consumed by the project's web dashboard (Vercel/Replit — built
separately). The front-end must never hard-code what the pipeline owns:
labels, colors, dataset versions, and headline numbers all ship in meta.json.

Outputs:
  web-data/facilities.geojson       one point per facility, full column contract
  web-data/state_summary.json       state records (weighted + unweighted rates)
  web-data/county_summary.json      county records
  web-data/subregion_summary.json   eGRID subregion records
  web-data/future_projections.json  NA catchment counts by scenario/year/category
  web-data/meta.json                dataset versions, vocab, colors, QA headlines

Usage:
  python code/export_web_data.py
"""

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DERIVED = ROOT / "data" / "derived-data"
WEB = ROOT / "web-data"
WEB.mkdir(exist_ok=True)

# Canonical vocabulary + color tokens (source of truth: preprocessing.py
# CATEGORY_TO_LABEL; sync list in METHODS.md)
CATEGORY_ORDER = ["Low", "Low-Medium", "Medium-High", "High", "Extremely High", "Arid", "No Data"]
CATEGORY_TO_LABEL = {
    "Low": "Low (<10%)",
    "Low-Medium": "Low-Medium (10-20%)",
    "Medium-High": "Medium-High (20-40%)",
    "High": "High (40-80%)",
    "Extremely High": "Extremely High (>80%)",
    "Arid": "Arid and Low Water Use",
    "No Data": "No Data",
}
# Validated against the light chart surface (dataviz six-checks): lightness
# band, chroma floor, CVD separation all pass; the two sub-3:1 steps rely on
# the permanent legend + tooltips (relief rule). Dark variants swap only the
# red for a brighter step; brighter-than-band steps are acceptable on dark.
CATEGORY_COLORS = {
    "Low": "#2ca02c",
    "Low-Medium": "#7dab4a",
    "Medium-High": "#dfa813",
    "High": "#e36c09",
    "Extremely High": "#c00000",
    "Arid": "#9e9e9e",
    "No Data": "#d9d9d9",
}
CATEGORY_COLORS_DARK = {**CATEGORY_COLORS, "Extremely High": "#d03b3b", "No Data": "#4a4a47"}


def _clean(records):
    """Replace NaN/NA with None for strict-JSON output."""
    out = []
    for rec in records:
        out.append({k: (None if (isinstance(v, float) and np.isnan(v)) or v is pd.NA else v)
                    for k, v in rec.items()})
    return out


def export_facilities(master):
    features = []
    props_cols = [c for c in master.columns if c not in ("lon", "lat")]
    for rec in master.to_dict(orient="records"):
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(rec["lon"], 5), round(rec["lat"], 5)]},
            "properties": {k: rec[k] for k in props_cols},
        })
    geojson = {"type": "FeatureCollection", "features": _clean_features(features)}
    (WEB / "facilities.geojson").write_text(json.dumps(geojson, default=_json_default))
    print(f"  facilities.geojson: {len(features)} features")


def _clean_features(features):
    for f in features:
        props = f["properties"]
        for k, v in list(props.items()):
            if (isinstance(v, float) and np.isnan(v)) or v is pd.NA:
                props[k] = None
    return features


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if pd.isna(o):
        return None
    return str(o)


def export_summaries(master, state, county):
    (WEB / "state_summary.json").write_text(
        json.dumps(_clean(state.to_dict(orient="records")), default=_json_default))
    (WEB / "county_summary.json").write_text(
        json.dumps(_clean(county.to_dict(orient="records")), default=_json_default))

    sub = master.groupby(["egrid_subregion", "egrid_subregion_name"], dropna=False).agg(
        dc_count=("id", "count"),
        total_sqft=("sqft", "sum"),
        co2_rate_lb_mwh=("SRCO2RTA", "first"),
        co2eq_rate_lb_mwh=("SRC2ERTA", "first"),
        renewable_pct=("SRTRPR", "first"),
        mw_capacity_known=("mw_capacity", "sum"),
        n_high_stress=("bws_category", lambda s: int(s.isin(["High", "Extremely High"]).sum())),
    ).reset_index().sort_values("dc_count", ascending=False)
    (WEB / "subregion_summary.json").write_text(
        json.dumps(_clean(sub.to_dict(orient="records")), default=_json_default))
    print(f"  summaries: {len(state)} states, {len(county)} counties, {len(sub)} subregions")


def export_future(future):
    scenarios = {"bau": "Business as Usual", "opt": "Optimistic", "pes": "Pessimistic"}
    records = []
    for scen_key, scen_name in scenarios.items():
        for year in ["30", "50", "80"]:
            col = f"{scen_key}{year}_ws_x_l"
            if col not in future.columns:
                continue
            counts = future[col].value_counts()
            for label, n in counts.items():
                records.append({
                    "scenario": scen_key,
                    "scenario_name": scen_name,
                    "year": 2000 + int(year),
                    "category_label": label,
                    "catchment_count": int(n),
                })
    payload = {
        "description": "North American HydroBASINS level-6 catchment counts by projected "
                       "water-stress category (WRI Aqueduct 4.0 future projections)",
        "total_catchments": int(len(future)),
        "records": records,
    }
    (WEB / "future_projections.json").write_text(json.dumps(payload, default=_json_default))
    print(f"  future_projections.json: {len(records)} scenario/year/category records")


def export_meta(master):
    manifest = json.loads((ROOT / "data" / "manifest.json").read_text())
    datasets = {
        key: {
            "name": e["name"],
            "version_used": e["version_used"],
            "access_date": e["access_date"],
            "source_url": e["source_url"],
            "license": e.get("license"),
            "citation": e.get("citation"),
        }
        for key, e in manifest["datasets"].items()
    }

    with_data = master["bws_category"].isin(
        ["Low", "Low-Medium", "Medium-High", "High", "Extremely High", "Arid"])
    high = master["bws_category"].isin(["High", "Extremely High"])
    sqft_w = master.dropna(subset=["SRCO2RTA", "sqft"])
    headline = {
        "n_facilities": int(len(master)),
        "n_states": int(master["state_abb"].nunique()),
        "mean_co2_rate_unweighted_lb_mwh": round(float(master["SRCO2RTA"].mean()), 1),
        "mean_co2_rate_sqft_weighted_lb_mwh": round(
            float(np.average(sqft_w["SRCO2RTA"], weights=sqft_w["sqft"])), 1),
        "n_high_water_stress": int(high.sum()),
        "pct_high_water_stress_of_with_data": round(100 * float(high.sum()) / max(int(with_data.sum()), 1), 1),
        "n_arid": int((master["bws_category"] == "Arid").sum()),
        "n_no_data": int((master["bws_category"] == "No Data").sum()),
        "n_dual_risk": int((high & (master["SRCO2RTA"] > 700)).sum()),
        "dual_risk_definition": "grid CO2 rate > 700 lb/MWh AND basin water stress High or Extremely High",
        "n_with_mw_capacity": int(master["mw_capacity"].notna().sum()),
    }

    meta = {
        "generated": date.today().isoformat(),
        "pipeline": "code/preprocessing.py (see METHODS.md)",
        "datasets": datasets,
        "water_stress_vocabulary": {
            "category_order": CATEGORY_ORDER,
            "category_to_label": CATEGORY_TO_LABEL,
            "category_colors": CATEGORY_COLORS,
            "category_colors_dark": CATEGORY_COLORS_DARK,
        },
        "headline_numbers": headline,
        "attribution": [
            "Data center locations: IM3/PNNL Open Source Data Center Atlas (ODbL)",
            "Grid emissions: US EPA eGRID2023",
            "Water stress: WRI Aqueduct 4.0",
            "Basin polygons: HydroSHEDS HydroBASINS v1c (Lehner & Grill 2013)",
            "Capacity data: FracTracker Alliance US Data Centers Tracker (non-commercial, with credit)",
        ],
    }
    (WEB / "meta.json").write_text(json.dumps(meta, indent=2, default=_json_default))
    print(f"  meta.json: {len(datasets)} datasets, headline numbers embedded")
    return headline


def main():
    print("Exporting web data layer...")
    master = pd.read_csv(DERIVED / "datacenters_master.csv", dtype={"id": str})
    state = pd.read_csv(DERIVED / "state_summary.csv")
    county = pd.read_csv(DERIVED / "county_summary.csv")
    future = pd.read_csv(DERIVED / "aqueduct_future_water_stress_na.csv")

    export_facilities(master)
    export_summaries(master, state, county)
    export_future(future)
    headline = export_meta(master)

    # Validation: every file parses; facility count matches; coordinates in range
    errors = []
    gj = json.loads((WEB / "facilities.geojson").read_text())
    if len(gj["features"]) != len(master):
        errors.append("facilities.geojson feature count != master rows")
    lons = [f["geometry"]["coordinates"][0] for f in gj["features"]]
    lats = [f["geometry"]["coordinates"][1] for f in gj["features"]]
    if not all(-180 <= x <= -60 for x in lons) or not all(15 <= y <= 72 for y in lats):
        errors.append("coordinates outside CONUS+PR+AK bounds")
    for name in ["state_summary.json", "county_summary.json", "subregion_summary.json",
                 "future_projections.json", "meta.json"]:
        json.loads((WEB / name).read_text())

    if errors:
        print("VALIDATION FAILED: " + "; ".join(errors))
        sys.exit(1)
    print(f"Validation passed. Headline: {headline['n_facilities']} facilities, "
          f"{headline['n_high_water_stress']} high-stress, {headline['n_dual_risk']} dual-risk.")


if __name__ == "__main__":
    main()

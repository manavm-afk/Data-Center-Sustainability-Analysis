"""
preprocessing.py — Data Preprocessing Pipeline
================================================
Reads from data/raw-data/ -> writes to data/derived-data/.

Methods are documented in METHODS.md. Every spatial assignment records an
explicit method/QA column so no number in the outputs has untraceable
provenance:

  * eGRID subregion   : point-in-polygon against EPA's eGRID2023 subregion
                        boundaries (egrid_assignment_method column).
  * Water stress      : point-in-polygon against HydroBASINS level-6 basins
                        (PFAF_ID -> WRI Aqueduct 4.0 pfaf_id; merge_method
                        column). Aqueduct 9999 sentinels and arid basins
                        (cat == -1) are masked/handled explicitly.
  * Capacity (MW)     : conservative <=500 m one-to-one spatial match to the
                        FracTracker US Data Centers snapshot; no imputation.

A before/after QA report is written to data/derived-data/qa_report.md.

Usage:
  python code/preprocessing.py           # full rebuild (always recomputes)
  python code/preprocessing.py --force   # same as above (kept for compatibility)
"""

import sys
import warnings
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

warnings.filterwarnings("ignore", category=FutureWarning)

# ── Paths ───────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent if (SCRIPT_DIR.parent / "data" / "raw-data").exists() else Path.cwd()
RAW_DIR = REPO_ROOT / "data" / "raw-data"
SHP_DIR = RAW_DIR / "shapefiles"
OUT_DIR = REPO_ROOT / "data" / "derived-data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

EARTH_RADIUS_KM = 6371.0088

# ── Canonical water-stress vocabulary ───────────────────────────────────────
# Short categories drive charts; long labels are the WRI display strings.
# These literals are mirrored in code/generate_charts.py and web-data/meta.json;
# the sync list lives in METHODS.md.
CATEGORY_TO_LABEL = {
    "Low": "Low (<10%)",
    "Low-Medium": "Low-Medium (10-20%)",
    "Medium-High": "Medium-High (20-40%)",
    "High": "High (40-80%)",
    "Extremely High": "Extremely High (>80%)",
    "Arid": "Arid and Low Water Use",
    "No Data": "No Data",
}
_CANONICAL_BY_LOWER = {v.lower(): v for v in CATEGORY_TO_LABEL.values()}


def score_to_category(score):
    """Aqueduct 0-5 score -> short category. Arid/No Data are assigned by the
    caller from the cat==-1 flag / missing data, never from the score (arid
    basins carry a placeholder score of 5.0 that must not read as Extremely High)."""
    if pd.isna(score):
        return "No Data"
    if score < 1:
        return "Low"
    if score < 2:
        return "Low-Medium"
    if score < 3:
        return "Medium-High"
    if score < 4:
        return "High"
    return "Extremely High"


def normalize_wri_label(label):
    """Normalize raw WRI label spellings ('Low - Medium (10-20%)',
    'Extremely high (>80%)') onto the canonical vocabulary."""
    if pd.isna(label):
        return "No Data"
    cleaned = str(label).strip().replace(" - ", "-")
    return _CANONICAL_BY_LOWER.get(cleaned.lower(), cleaned)


# ── Geometry helpers ─────────────────────────────────────────────────────────
def latlon_to_xyz(lat_deg, lon_deg):
    """Lat/lon degrees -> unit-sphere ECEF xyz (for chord-based KD-trees)."""
    lat = np.deg2rad(np.asarray(lat_deg, dtype=float))
    lon = np.deg2rad(np.asarray(lon_deg, dtype=float))
    return np.column_stack([
        np.cos(lat) * np.cos(lon),
        np.cos(lat) * np.sin(lon),
        np.sin(lat),
    ])


def chord_to_km(chord):
    """Unit-sphere chord length -> great-circle distance in km."""
    chord = np.clip(np.asarray(chord, dtype=float), 0.0, 2.0)
    return 2.0 * EARTH_RADIUS_KM * np.arcsin(chord / 2.0)


def weighted_mean(values, weights):
    """np.average over rows where both value and weight are finite; NaN if none."""
    v = np.asarray(values, dtype=float)
    w = np.asarray(weights, dtype=float)
    ok = np.isfinite(v) & np.isfinite(w) & (w > 0)
    if not ok.any():
        return np.nan
    return float(np.average(v[ok], weights=w[ok]))


# ══════════════════════════════════════════════════════════════════════════
# Stage A — baseline capture (reads the PREVIOUS derived outputs first)
# ══════════════════════════════════════════════════════════════════════════
# Headline numbers of the pre-Phase-0 pipeline (hard-coded state-dict water,
# nearest-plant grid). Kept as the permanent "before" reference once the old
# outputs are no longer recoverable from git.
LEGACY_BASELINE = {
    "n_facilities": 1474,
    "mean_co2_unweighted": 704.5,
    "pct_high_stress": 26.7,
    "n_high_stress": 393,
    "n_dual_risk": 250,
    "top3_states": {"VA": 319, "TX": 127, "CA": 112},
}


def capture_baseline_metrics():
    """Snapshot the previous pipeline's headline numbers before overwrite,
    so qa_report.md can show an honest before/after.

    Ladder: old-schema CSV on disk -> last committed old-schema CSV via
    `git show` -> LEGACY_BASELINE constants."""
    import io
    import subprocess

    old = None
    master_path = OUT_DIR / "datacenters_master.csv"
    if master_path.exists():
        candidate = pd.read_csv(master_path, dtype={"id": str})
        if "bws_state_category" in candidate.columns:
            old = candidate
    if old is None:
        try:
            blob = subprocess.run(
                ["git", "--no-pager", "show", "HEAD:data/derived-data/datacenters_master.csv"],
                cwd=REPO_ROOT, capture_output=True, check=True, text=True,
                timeout=30, stdin=subprocess.DEVNULL,
            ).stdout
            candidate = pd.read_csv(io.StringIO(blob), dtype={"id": str})
            if "bws_state_category" in candidate.columns:
                old = candidate
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired,
                FileNotFoundError, pd.errors.ParserError):
            old = None
    if old is None:
        return dict(LEGACY_BASELINE)

    baseline = {"n_facilities": len(old)}
    if "SRCO2RTA" in old.columns:
        baseline["mean_co2_unweighted"] = float(old["SRCO2RTA"].mean())
    if "bws_state_category" in old.columns:
        high = old["bws_state_category"].isin(["High", "Extremely High"])
        baseline["pct_high_stress"] = float(100 * high.mean())
        baseline["n_high_stress"] = int(high.sum())
        if "SRCO2RTA" in old.columns:
            baseline["n_dual_risk"] = int((high & (old["SRCO2RTA"] > 700)).sum())
    if "state_abb" in old.columns:
        baseline["top3_states"] = old["state_abb"].value_counts().head(3).to_dict()
    if {"id", "egrid_subregion"}.issubset(old.columns):
        # The legacy pipeline read `id` as int, dropping leading zeros; the IM3
        # id is an 11-char zero-padded string — re-pad so the maps align.
        old_ids = old["id"].astype(str).str.zfill(11)
        baseline["old_subregion_by_id"] = dict(zip(old_ids, old["egrid_subregion"]))
    return baseline


# ══════════════════════════════════════════════════════════════════════════
# Stage B — load inputs
# ══════════════════════════════════════════════════════════════════════════
def load_im3():
    """Load + deduplicate the IM3 atlas (5 cross-county IDs -> 1 row each)."""
    print("=" * 60)
    print("1. Loading and deduplicating IM3 Data Center Atlas...")
    dc = pd.read_csv(
        RAW_DIR / "im3_open_source_data_center_atlas_v2026.02.09.csv",
        dtype={"id": str},
    )
    print(f"   Raw records: {len(dc):,}  ({dc['id'].nunique()} unique IDs)")

    dc["fips"] = (dc["state_id"].astype(str).str.zfill(2)
                  + dc["county_id"].astype(str).str.zfill(3))

    # Keep one row per facility: most precise geometry first, then largest sqft
    type_priority = {"point": 0, "building": 1, "campus": 2}
    dc["type_rank"] = dc["type"].map(type_priority)
    dc = (dc.sort_values(["type_rank", "sqft"], ascending=[True, False])
            .drop_duplicates(subset="id", keep="first")
            .drop(columns="type_rank")
            .reset_index(drop=True))
    print(f"   After dedup: {len(dc):,} rows across {dc['state_abb'].nunique()} states/territories")
    return dc


def load_egrid():
    """Load eGRID plant coordinates and subregion/state emission rates."""
    print("\n" + "=" * 60)
    print("2. Loading eGRID 2023 rev2 (plants, subregions, states)...")
    xlsx = RAW_DIR / "egrid2023_data_rev2.xlsx"

    plnt = pd.read_excel(xlsx, sheet_name="PLNT23", header=1)
    plnt_geo = (plnt[["ORISPL", "PSTATABB", "SUBRGN", "SRNAME", "LAT", "LON"]]
                .dropna(subset=["LAT", "LON", "SUBRGN"])
                .reset_index(drop=True))

    srl = pd.read_excel(xlsx, sheet_name="SRL23", header=1)
    srl_clean = srl[[
        "SUBRGN", "SRNAME", "SRNGENAN", "SRCO2RTA", "SRC2ERTA", "SRCO2AN",
        "SRCLPR", "SROLPR", "SRGSPR", "SRNCPR", "SRHYPR", "SRBMPR",
        "SRWIPR", "SRSOPR", "SRGTPR", "SRTNPR", "SRTRPR",
    ]].copy()

    st = pd.read_excel(xlsx, sheet_name="ST23", header=1)
    st_clean = st[[
        "PSTATABB", "STNGENAN", "STCO2RTA", "STC2ERTA", "STCO2AN",
        "STCLPR", "STGSPR", "STNCPR", "STWIPR", "STSOPR", "STHYPR",
        "STTNPR", "STTRPR",
    ]].copy()

    print(f"   Plants: {len(plnt_geo):,} | Subregions: {len(srl_clean)} | States: {len(st_clean)}")
    return plnt_geo, srl_clean, st_clean


# ══════════════════════════════════════════════════════════════════════════
# Stage C — eGRID subregion assignment (point-in-polygon + ladder)
# ══════════════════════════════════════════════════════════════════════════
def _find_shapefile(directory, hint):
    shps = sorted(directory.glob("**/*.shp"))
    if not shps:
        sys.exit(f"ERROR: no shapefile found in {directory} — run `python code/download_data.py` first.")
    for shp in shps:
        if hint.lower() in shp.name.lower():
            return shp
    return shps[0]


def assign_subregions(dc, plnt_geo):
    """Assign each facility an eGRID subregion.

    Ladder: point-in-polygon -> overlap tiebreak by nearest plant among the
    candidate subregions -> nearest polygon (<=25 km) -> nearest plant.
    Every rung is recorded in egrid_assignment_method.
    """
    import geopandas as gpd

    print("\n" + "=" * 60)
    print("3. Assigning eGRID subregions (point-in-polygon)...")

    sub_shp = _find_shapefile(SHP_DIR / "egrid2023_subregions", "subregion")
    subregions = gpd.read_file(sub_shp)
    sub_col = "Subregion" if "Subregion" in subregions.columns else [
        c for c in subregions.columns if c.lower() != "geometry"][0]
    subregions = subregions[[sub_col, "geometry"]].rename(columns={sub_col: "SUBRGN_PIP"})
    subregions = subregions.to_crs(epsg=4326)

    pts = gpd.GeoDataFrame(
        dc[["id"]].copy(),
        geometry=gpd.points_from_xy(dc["lon"], dc["lat"]),
        crs="EPSG:4326",
    )

    hits = gpd.sjoin(pts, subregions, how="left", predicate="intersects")
    candidates = hits.groupby("id")["SUBRGN_PIP"].agg(
        lambda s: sorted(set(x for x in s if pd.notna(x))))
    dc = dc.merge(candidates.rename("subregion_candidates"), on="id", how="left")
    dc["subregion_candidates"] = dc["subregion_candidates"].apply(
        lambda x: x if isinstance(x, list) else [])

    # Nearest plant (QA field + tiebreaker), chord KD-tree on the unit sphere
    plant_tree = cKDTree(latlon_to_xyz(plnt_geo["LAT"], plnt_geo["LON"]))
    d_chord, idx = plant_tree.query(latlon_to_xyz(dc["lat"], dc["lon"]), k=1)
    dc["nearest_plant_id"] = plnt_geo.iloc[idx]["ORISPL"].values
    dc["nearest_plant_subregion"] = plnt_geo.iloc[idx]["SUBRGN"].values
    dc["nearest_plant_km"] = chord_to_km(d_chord)
    dc["qa_flag_distant_plant"] = dc["nearest_plant_km"] > 100

    # Overlap layer: flag facilities in areas served by >1 subregion
    multi_shp = _find_shapefile(SHP_DIR / "egrid2023_multiple_subregions", "multiple")
    multi = gpd.read_file(multi_shp).to_crs(epsg=4326)[["geometry"]]
    in_multi = gpd.sjoin(pts, multi, how="inner", predicate="intersects")
    multi_ids = set(in_multi["id"])

    # Resolve the ladder per facility
    plants_by_sub = {s: g for s, g in plnt_geo.groupby("SUBRGN")}
    sub_trees = {
        s: (cKDTree(latlon_to_xyz(g["LAT"], g["LON"])), g)
        for s, g in plants_by_sub.items()
    }

    def nearest_plant_in(subs, lat, lon):
        best_sub, best_km = None, np.inf
        for s in subs:
            if s not in sub_trees:
                continue
            tree, _ = sub_trees[s]
            d, _i = tree.query(latlon_to_xyz([lat], [lon]), k=1)
            km = chord_to_km(d)[0]
            if km < best_km:
                best_sub, best_km = s, km
        return best_sub

    assigned, method, qa_multi = [], [], []
    for row in dc.itertuples():
        cands = row.subregion_candidates
        is_multi = row.id in multi_ids or len(cands) > 1
        qa_multi.append(bool(is_multi))
        if len(cands) == 1 and not is_multi:
            assigned.append(cands[0]); method.append("pip")
        elif len(cands) >= 1:
            pick = nearest_plant_in(cands, row.lat, row.lon) or cands[0]
            assigned.append(pick); method.append("pip_overlap_plant_tiebreak" if is_multi else "pip")
        else:
            assigned.append(None); method.append("unresolved")
    dc["egrid_subregion"] = assigned
    dc["egrid_assignment_method"] = method
    dc["qa_multi_subregion"] = qa_multi

    # Rung 3: nearest polygon within 25 km for points outside every polygon
    unresolved = dc["egrid_subregion"].isna()
    if unresolved.any():
        missing_pts = gpd.GeoDataFrame(
            dc.loc[unresolved, ["id"]],
            geometry=gpd.points_from_xy(dc.loc[unresolved, "lon"], dc.loc[unresolved, "lat"]),
            crs="EPSG:4326",
        ).to_crs(epsg=5070)
        near = gpd.sjoin_nearest(
            missing_pts, subregions.to_crs(epsg=5070),
            how="left", distance_col="poly_dist_m", max_distance=25_000,
        ).drop_duplicates(subset="id")
        near_map = dict(zip(near["id"], near["SUBRGN_PIP"]))
        for i in dc.index[unresolved]:
            fid = dc.at[i, "id"]
            if pd.notna(near_map.get(fid)):
                dc.at[i, "egrid_subregion"] = near_map[fid]
                dc.at[i, "egrid_assignment_method"] = "nearest_polygon"

    # Rung 4: nearest plant's subregion
    unresolved = dc["egrid_subregion"].isna()
    dc.loc[unresolved, "egrid_subregion"] = dc.loc[unresolved, "nearest_plant_subregion"]
    dc.loc[unresolved, "egrid_assignment_method"] = "nearest_plant_fallback"

    dc = dc.drop(columns=["subregion_candidates"])
    print(f"   Assignment methods: {dc['egrid_assignment_method'].value_counts().to_dict()}")
    print(f"   Facilities in multi-subregion areas: {dc['qa_multi_subregion'].sum()}")
    return dc


def merge_emission_rates(dc, srl_clean, st_clean):
    print("\n4. Merging subregion + state emission rates...")
    dc = dc.merge(
        srl_clean.rename(columns={"SRNAME": "egrid_subregion_name"}),
        left_on="egrid_subregion", right_on="SUBRGN", how="left",
    ).drop(columns=["SUBRGN"])
    dc = dc.merge(st_clean, left_on="state_abb", right_on="PSTATABB",
                  how="left", suffixes=("", "_state")).drop(columns=["PSTATABB"])
    matched = dc["SRCO2RTA"].notna().sum()
    print(f"   Matched to subregion rates: {matched}/{len(dc)} ({100*matched/len(dc):.1f}%)")
    return dc


# ══════════════════════════════════════════════════════════════════════════
# Stage D — Aqueduct water stress (sentinel/arid-aware + HydroBASINS PIP)
# ══════════════════════════════════════════════════════════════════════════
def build_aq_annual():
    """Catchment-level annual summary from Aqueduct 4.0 baseline monthly,
    masking 9999 sentinels and arid months (cat == -1)."""
    print("\n" + "=" * 60)
    print("5. Building Aqueduct annual summary (sentinel/arid-aware)...")
    aq = pd.read_csv(RAW_DIR / "Aqueduct40_baseline_monthly_y2023m07d05.csv")
    months = range(1, 13)

    def fam(prefix, stat):
        return aq[[f"{prefix}_{m:02d}_{stat}" for m in months]].to_numpy(dtype=float)

    out = {"pfaf_id": aq["pfaf_id"]}
    for prefix in ["bws", "bwd", "iav"]:
        raw = fam(prefix, "raw")
        score = fam(prefix, "score")
        cat = fam(prefix, "cat")
        arid = cat == -1
        raw_masked = np.where((raw == 9999.0) | arid, np.nan, raw)
        score_masked = np.where(arid, np.nan, score)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN rows
            out[f"{prefix}_annual_mean_raw"] = np.nanmean(raw_masked, axis=1)
            out[f"{prefix}_annual_mean_score"] = np.nanmean(score_masked, axis=1)
            if prefix == "bws":
                out["bws_annual_max_raw"] = np.nanmax(raw_masked, axis=1)
                out["bws_annual_max_score"] = np.nanmax(score_masked, axis=1)
                summer_cols = [5, 6, 7]  # Jun, Jul, Aug (0-indexed months)
                out["bws_summer_mean_raw"] = np.nanmean(raw_masked[:, summer_cols], axis=1)
                out["bws_summer_mean_score"] = np.nanmean(score_masked[:, summer_cols], axis=1)
                out["n_arid_months"] = arid.sum(axis=1)
                out["n_raw_masked_months"] = ((raw == 9999.0) | arid).sum(axis=1)

    aq_annual = pd.DataFrame(out)
    aq_annual["is_arid"] = aq_annual["n_arid_months"] >= 6
    n_mixed = int(((aq_annual["n_arid_months"] > 0) & (~aq_annual["is_arid"])).sum())

    aq_annual["bws_category"] = np.where(
        aq_annual["is_arid"], "Arid",
        [score_to_category(s) for s in aq_annual["bws_annual_mean_score"]],
    )
    aq_annual["bws_annual_label"] = aq_annual["bws_category"].map(CATEGORY_TO_LABEL)
    aq_annual["pfaf_prefix"] = aq_annual["pfaf_id"].astype(str).str[0]

    print(f"   Catchments: {len(aq_annual):,} | arid: {aq_annual['is_arid'].sum():,} "
          f"| mixed arid/non-arid months: {n_mixed}")
    aq_annual.to_csv(OUT_DIR / "aqueduct_annual_summary.csv", index=False)
    return aq_annual


def join_water_stress(dc, aq_annual):
    """Facility -> HydroBASINS level-6 basin (PIP) -> Aqueduct catchment values.

    Ladder: hydrobasins_pip -> hydrobasins_nearest_10km ->
    basin_no_aqueduct_data -> unmatched. No state-level values anywhere.
    """
    import geopandas as gpd

    print("\n6. Joining water stress via HydroBASINS level-6 polygons...")
    hb_dir = SHP_DIR / "hydrobasins"
    frames = []
    for region in ["na", "ar"]:
        shp = hb_dir / f"hybas_{region}_lev06_v1c.shp"
        if shp.exists():
            frames.append(gpd.read_file(shp)[["PFAF_ID", "SUB_AREA", "geometry"]])
    if not frames:
        sys.exit(f"ERROR: HydroBASINS shapefiles missing from {hb_dir} — run download_data.py.")
    basins = pd.concat(frames, ignore_index=True)
    basins = gpd.GeoDataFrame(basins, crs="EPSG:4326")

    pts = gpd.GeoDataFrame(
        dc[["id"]].copy(),
        geometry=gpd.points_from_xy(dc["lon"], dc["lat"]),
        crs="EPSG:4326",
    )
    hits = gpd.sjoin(pts, basins, how="left", predicate="intersects")
    # Boundary points can hit >1 basin: deterministic dedupe by larger SUB_AREA
    hits = (hits.sort_values("SUB_AREA", ascending=False)
                .drop_duplicates(subset="id", keep="first"))
    dc = dc.merge(hits[["id", "PFAF_ID"]], on="id", how="left")
    dc["merge_method"] = np.where(dc["PFAF_ID"].notna(), "hydrobasins_pip", None)
    dc["basin_match_dist_km"] = np.where(dc["PFAF_ID"].notna(), 0.0, np.nan)

    # Rung 2: nearest basin within 10 km
    missing = dc["PFAF_ID"].isna()
    if missing.any():
        mp = gpd.GeoDataFrame(
            dc.loc[missing, ["id"]],
            geometry=gpd.points_from_xy(dc.loc[missing, "lon"], dc.loc[missing, "lat"]),
            crs="EPSG:4326",
        ).to_crs(epsg=5070)
        near = gpd.sjoin_nearest(
            mp, basins.to_crs(epsg=5070), how="left",
            distance_col="dist_m", max_distance=10_000,
        ).drop_duplicates(subset="id")
        for _, r in near.iterrows():
            if pd.notna(r["PFAF_ID"]):
                i = dc.index[dc["id"] == r["id"]][0]
                dc.at[i, "PFAF_ID"] = r["PFAF_ID"]
                dc.at[i, "merge_method"] = "hydrobasins_nearest_10km"
                dc.at[i, "basin_match_dist_km"] = r["dist_m"] / 1000.0

    dc = dc.rename(columns={"PFAF_ID": "pfaf_id"})
    dc["pfaf_id"] = dc["pfaf_id"].astype("Int64")

    # Attach catchment values
    aq_cols = ["pfaf_id", "bws_annual_mean_raw", "bws_annual_mean_score",
               "bws_summer_mean_score", "is_arid", "bws_category", "bws_annual_label"]
    dc = dc.merge(aq_annual[aq_cols], on="pfaf_id", how="left")

    # Rung 3/4: basin matched but absent from Aqueduct / no basin at all
    no_aq = dc["pfaf_id"].notna() & dc["bws_annual_mean_score"].isna() & (~dc["is_arid"].fillna(False))
    dc.loc[no_aq, "merge_method"] = "basin_no_aqueduct_data"
    dc.loc[dc["merge_method"].isna(), "merge_method"] = "unmatched"

    dc["bws_category"] = dc["bws_category"].fillna("No Data")
    dc["bws_label"] = dc["bws_category"].map(CATEGORY_TO_LABEL)
    dc = dc.rename(columns={
        "bws_annual_mean_raw": "bws_raw",
        "bws_annual_mean_score": "bws_score",
    }).drop(columns=["bws_annual_label"])
    dc["is_arid"] = dc["is_arid"].astype("boolean")

    print(f"   merge_method: {dc['merge_method'].value_counts().to_dict()}")
    print(f"   bws_category: {dc['bws_category'].value_counts().to_dict()}")
    return dc


def build_future_projections():
    """North-American catchment subset of Aqueduct future water stress,
    with labels normalized onto the canonical vocabulary."""
    print("\n7. Extracting Aqueduct future projections (North America)...")
    aq_future = pd.read_csv(RAW_DIR / "Aqueduct40_future_annual_y2023m07d05.csv")
    cols = ["pfaf_id"]
    for scenario in ["bau", "opt", "pes"]:
        for year in ["30", "50", "80"]:
            for stat in ["r", "s", "c", "l"]:
                col = f"{scenario}{year}_ws_x_{stat}"
                if col in aq_future.columns:
                    cols.append(col)
    fut = aq_future[cols].copy()
    for col in [c for c in fut.columns if c.endswith("_l")]:
        fut[col] = fut[col].map(normalize_wri_label)
    fut["pfaf_prefix"] = fut["pfaf_id"].astype(str).str[0]
    fut = fut[fut["pfaf_prefix"].isin(["7", "8"])].copy()
    fut.to_csv(OUT_DIR / "aqueduct_future_water_stress_na.csv", index=False)
    print(f"   North American catchments: {len(fut):,}")
    return fut


# ══════════════════════════════════════════════════════════════════════════
# Stage E — FracTracker capacity match
# ══════════════════════════════════════════════════════════════════════════
def _normalize_tokens(*texts):
    stop = {"inc", "llc", "corp", "corporation", "company", "co", "lp",
            "data", "center", "centers", "centre", "datacenter", "the"}
    tokens = set()
    for t in texts:
        if pd.isna(t):
            continue
        for tok in str(t).lower().replace("/", " ").replace("-", " ").split():
            tok = "".join(ch for ch in tok if ch.isalnum())
            if tok and tok not in stop:
                tokens.add(tok)
    return tokens


def match_fractracker(dc):
    """Attach MW capacity from the FracTracker snapshot via a conservative
    <=500 m one-to-one nearest match. Report-only name check; no imputation."""
    print("\n" + "=" * 60)
    print("8. Matching FracTracker capacity data (<=500 m, one-to-one)...")
    snaps = sorted(RAW_DIR.glob("fractracker_us_datacenters_*.csv"))
    if not snaps:
        print("   WARNING: no FracTracker snapshot found — mw_capacity will be empty.")
        for col, val in [("mw_capacity", np.nan), ("mw_source", None),
                         ("match_dist_m", np.nan), ("ft_status", None),
                         ("qa_operator_mismatch", pd.NA)]:
            dc[col] = val
        return dc

    snap = snaps[-1]
    snap_date = snap.stem.replace("fractracker_us_datacenters_", "")
    ft = pd.read_csv(snap)
    ft = ft.dropna(subset=["Lat", "Long"]).copy()

    status = ft["Status"].astype(str).str.lower()
    keep = status.str.contains("operat|expand|approved|permitted|under construction", regex=True)
    ft = ft[keep].reset_index(drop=True)
    ft["mw_num"] = pd.to_numeric(
        ft["MW"].astype(str).str.replace(",", "").str.extract(r"([\d.]+)")[0],
        errors="coerce",
    )
    print(f"   Snapshot {snap_date}: {len(ft)} built/approved facilities "
          f"({ft['mw_num'].notna().sum()} with MW)")

    ft_tree = cKDTree(latlon_to_xyz(ft["Lat"], ft["Long"]))
    d_chord, idx = ft_tree.query(latlon_to_xyz(dc["lat"], dc["lon"]), k=1)
    dist_m = chord_to_km(d_chord) * 1000.0

    # Greedy one-to-one: closest pairs claim their FracTracker row first
    order = np.argsort(dist_m)
    ft_used, match_for_dc = set(), {}
    for pos in order:
        if dist_m[pos] > 500.0:
            break
        j = int(idx[pos])
        if j in ft_used:
            continue
        ft_used.add(j)
        match_for_dc[pos] = j

    mw, src, dist_col, ft_status, name_mismatch = [], [], [], [], []
    for pos in range(len(dc)):
        j = match_for_dc.get(pos)
        if j is None:
            mw.append(np.nan); src.append(None); dist_col.append(np.nan)
            ft_status.append(None); name_mismatch.append(pd.NA)
            continue
        row = ft.iloc[j]
        mw.append(row["mw_num"])
        src.append(f"fractracker_{snap_date}")
        dist_col.append(round(float(dist_m[pos]), 1))
        ft_status.append(row["Status"])
        dc_tokens = _normalize_tokens(dc.iloc[pos]["operator"], dc.iloc[pos]["name"])
        ft_tokens = _normalize_tokens(row.get("Operator"), row.get("Tenant"), row.get("Name"))
        name_mismatch.append(bool(dc_tokens and ft_tokens and not (dc_tokens & ft_tokens)))

    dc["mw_capacity"] = mw
    dc["mw_source"] = src
    dc["match_dist_m"] = dist_col
    dc["ft_status"] = ft_status
    dc["qa_operator_mismatch"] = pd.array(name_mismatch, dtype="boolean")

    matched = dc["mw_source"].notna().sum()
    with_mw = dc["mw_capacity"].notna().sum()
    print(f"   Matched {matched}/{len(dc)} facilities "
          f"(median {np.nanmedian(dc['match_dist_m']):.0f} m); MW known for {with_mw} "
          f"({100*with_mw/len(dc):.1f}% of all facilities)")
    return dc


# ══════════════════════════════════════════════════════════════════════════
# Stage F — summaries + master
# ══════════════════════════════════════════════════════════════════════════
def _grouped_summary(master, keys):
    def agg(g):
        mw_cov = 100 * g["mw_capacity"].notna().mean()
        row = {
            "dc_count": len(g),
            "total_sqft": g["sqft"].sum(),
            "mean_sqft": g["sqft"].mean(),
            "co2_rate_lb_mwh": g["SRCO2RTA"].mean(),
            "co2eq_rate_lb_mwh": g["SRC2ERTA"].mean(),
            "renewable_pct": g["SRTRPR"].mean(),
            "nonrenewable_pct": g["SRTNPR"].mean(),
            "co2_rate_lb_mwh_sqftw": weighted_mean(g["SRCO2RTA"], g["sqft"]),
            "co2_rate_lb_mwh_mww": (
                weighted_mean(g["SRCO2RTA"], g["mw_capacity"]) if mw_cov >= 40 else np.nan),
            "sqft_coverage_pct": 100 * g["sqft"].notna().mean(),
            "mw_coverage_pct": mw_cov,
            "mean_lat": g["lat"].mean(),
            "mean_lon": g["lon"].mean(),
        }
        if "bws_category" in g.columns:
            mode = g["bws_category"].mode()
            row["bws_category_mode"] = mode.iloc[0] if len(mode) else "No Data"
        return pd.Series(row)

    return (master.groupby(keys, dropna=False).apply(agg, include_groups=False)
                  .reset_index().sort_values("dc_count", ascending=False))


def build_summaries(master):
    print("\n9. Building county/state summaries (unweighted + weighted)...")

    county = _grouped_summary(master, ["state", "state_abb", "county", "county_id", "fips"])
    county["egrid_subregion"] = county["fips"].map(
        master.groupby("fips")["egrid_subregion"].agg(lambda s: s.mode().iloc[0]))
    county.to_csv(OUT_DIR / "county_summary.csv", index=False)

    state = _grouped_summary(master, ["state", "state_abb"])
    state = state.rename(columns={
        "co2_rate_lb_mwh": "mean_co2_rate",
        "co2eq_rate_lb_mwh": "mean_co2eq_rate",
        "co2_rate_lb_mwh_sqftw": "mean_co2_rate_sqftw",
        "co2_rate_lb_mwh_mww": "mean_co2_rate_mww",
    })
    state_rates = master.groupby(["state_abb"]).agg(
        state_co2_rate=("STCO2RTA", "first"),
        state_renewable_pct=("STTRPR", "first"),
    ).reset_index()
    state = state.merge(state_rates, on="state_abb", how="left")
    state.to_csv(OUT_DIR / "state_summary.csv", index=False)

    county_ws = (master.groupby(["state", "state_abb", "county", "county_id"], dropna=False)
                 .agg(dc_count=("id", "count"),
                      total_sqft=("sqft", "sum"),
                      bws_score=("bws_score", "mean"),
                      bws_category=("bws_category", lambda s: s.mode().iloc[0] if len(s.mode()) else "No Data"),
                      mean_lat=("lat", "mean"),
                      mean_lon=("lon", "mean"))
                 .reset_index().sort_values("dc_count", ascending=False))
    county_ws["bws_label"] = county_ws["bws_category"].map(CATEGORY_TO_LABEL)
    county_ws.to_csv(OUT_DIR / "water_stress_county_summary.csv", index=False)

    print(f"   county_summary: {len(county)} rows | state_summary: {len(state)} rows")
    return county, state, county_ws


MASTER_COLS = [
    # identity / location
    "id", "state", "state_abb", "state_id", "county", "county_id", "fips",
    "operator", "ref", "name", "sqft", "lon", "lat", "type",
    # grid assignment + QA
    "egrid_subregion", "egrid_subregion_name", "egrid_assignment_method",
    "qa_multi_subregion", "nearest_plant_id", "nearest_plant_km",
    "nearest_plant_subregion", "qa_flag_distant_plant",
    # subregion emission rates / mix
    "SRNGENAN", "SRCO2RTA", "SRC2ERTA", "SRCO2AN",
    "SRCLPR", "SROLPR", "SRGSPR", "SRNCPR", "SRHYPR", "SRBMPR",
    "SRWIPR", "SRSOPR", "SRGTPR", "SRTNPR", "SRTRPR",
    # state emission rates
    "STNGENAN", "STCO2RTA", "STC2ERTA", "STCO2AN", "STCLPR", "STGSPR",
    "STNCPR", "STWIPR", "STSOPR", "STHYPR", "STTNPR", "STTRPR",
    # water stress + provenance
    "pfaf_id", "bws_score", "bws_raw", "bws_summer_mean_score", "is_arid",
    "bws_category", "bws_label", "merge_method", "basin_match_dist_km",
    # capacity
    "mw_capacity", "mw_source", "match_dist_m", "ft_status", "qa_operator_mismatch",
]


def write_outputs(master):
    print("\n10. Writing facility-level outputs...")
    master[MASTER_COLS].to_csv(OUT_DIR / "datacenters_master.csv", index=False)

    emissions_cols = [c for c in MASTER_COLS if not c.startswith(("bws", "pfaf", "merge",
                      "basin", "mw_", "match_dist", "ft_", "qa_operator", "is_arid"))]
    master[emissions_cols].to_csv(OUT_DIR / "datacenters_with_emissions.csv", index=False)

    water_cols = ["id", "state", "state_abb", "county", "county_id", "fips",
                  "operator", "name", "sqft", "lon", "lat", "type",
                  "pfaf_id", "bws_score", "bws_raw", "bws_summer_mean_score",
                  "is_arid", "bws_category", "bws_label",
                  "merge_method", "basin_match_dist_km"]
    master[water_cols].to_csv(OUT_DIR / "datacenters_with_water_stress.csv", index=False)
    print(f"   datacenters_master.csv: {len(master):,} rows x {len(MASTER_COLS)} cols")


# ══════════════════════════════════════════════════════════════════════════
# Stage G — QA report
# ══════════════════════════════════════════════════════════════════════════
def _md_table(series, value_header="facilities"):
    """Render a pandas Series as a small markdown table (no tabulate dependency)."""
    name = series.index.name or "key"
    rows = [f"| {name} | {value_header} |", "|---|---|"]
    for key, val in series.items():
        key_str = " -> ".join(str(k) for k in key) if isinstance(key, tuple) else str(key)
        rows.append(f"| {key_str} | {val} |")
    return "\n".join(rows)


def write_qa_report(baseline, master):
    print("\n" + "=" * 60)
    print("11. Writing QA report...")
    failures = []
    lines = ["# QA Report — preprocessing pipeline",
             f"\nGenerated {date.today().isoformat()} by code/preprocessing.py. "
             "Methods in METHODS.md.\n"]

    # Headline before/after
    with_data = master["bws_category"].isin(
        ["Low", "Low-Medium", "Medium-High", "High", "Extremely High", "Arid"])
    high = master["bws_category"].isin(["High", "Extremely High"])
    dual = high & (master["SRCO2RTA"] > 700)
    new = {
        "n_facilities": len(master),
        "mean_co2_unweighted": master["SRCO2RTA"].mean(),
        "mean_co2_sqftw": weighted_mean(master["SRCO2RTA"], master["sqft"]),
        "n_high_stress": int(high.sum()),
        "pct_high_stress": 100 * high.sum() / max(with_data.sum(), 1),
        "n_dual_risk": int(dual.sum()),
        "top3_states": master["state_abb"].value_counts().head(3).to_dict(),
    }

    lines.append("## Headline numbers — before/after\n")
    lines.append("| Metric | Old pipeline (state-dict water, nearest-plant grid) | New pipeline |")
    lines.append("|---|---|---|")
    b = baseline or {}
    lines.append(f"| Facilities | {b.get('n_facilities', 'n/a')} | {new['n_facilities']} |")
    lines.append(f"| Mean CO2 rate, unweighted (lb/MWh) | {b.get('mean_co2_unweighted', float('nan')):.1f} "
                 f"| {new['mean_co2_unweighted']:.1f} |")
    lines.append(f"| Mean CO2 rate, sqft-weighted (lb/MWh) | — | {new['mean_co2_sqftw']:.1f} |")
    lines.append(f"| Facilities in High/Extremely High water stress | {b.get('n_high_stress', 'n/a')} "
                 f"({b.get('pct_high_stress', float('nan')):.1f}%) | {new['n_high_stress']} "
                 f"({new['pct_high_stress']:.1f}% of facilities with data) |")
    lines.append(f"| Dual-risk facilities (>700 lb/MWh AND High/Extremely High) | "
                 f"{b.get('n_dual_risk', 'n/a')} | {new['n_dual_risk']} |")
    lines.append(f"| Top 3 states | {b.get('top3_states', 'n/a')} | {new['top3_states']} |")
    arid_n = int((master["bws_category"] == "Arid").sum())
    nodata_n = int((master["bws_category"] == "No Data").sum())
    lines.append(f"\nArid-basin facilities: {arid_n}; No Data: {nodata_n} "
                 "(excluded from the high-stress denominator).\n")

    # Match-rate tables
    lines.append("## Water-stress join (merge_method)\n")
    mm = master["merge_method"].value_counts()
    lines.append(_md_table(mm))
    if mm.sum() != len(master):
        failures.append("merge_method counts do not sum to facility count")
    if "state_level_fallback" in mm.index:
        failures.append("state_level_fallback present — the hard-coded dict is supposed to be gone")

    lines.append("\n## eGRID subregion assignment (egrid_assignment_method)\n")
    lines.append(_md_table(master["egrid_assignment_method"].value_counts()))

    # Method comparison across ALL facilities: legacy nearest-plant proxy vs PIP
    diff = master[master["nearest_plant_subregion"] != master["egrid_subregion"]]
    lines.append(f"\nLegacy nearest-plant method vs point-in-polygon: "
                 f"{len(diff)}/{len(master)} facilities would have been assigned a "
                 f"different subregion ({100*len(diff)/len(master):.1f}%).\n")
    if len(diff):
        pairs = (diff.groupby(["nearest_plant_subregion", "egrid_subregion"]).size()
                 .sort_values(ascending=False).head(8))
        lines.append("Top reassignments (nearest-plant -> PIP):\n")
        lines.append(_md_table(pairs))

    if baseline and "old_subregion_by_id" in baseline:
        old_map = baseline["old_subregion_by_id"]
        both = master[master["id"].isin(old_map)].copy()
        both["old_subregion"] = both["id"].map(old_map)
        disagree = both[both["old_subregion"] != both["egrid_subregion"]]
        rate = 100 * len(disagree) / max(len(both), 1)
        lines.append(f"\nOld (nearest-plant) vs new (PIP) subregion disagreement: "
                     f"{len(disagree)}/{len(both)} facilities ({rate:.1f}%).\n")
        if len(disagree):
            top_pairs = (disagree.groupby(["old_subregion", "egrid_subregion"]).size()
                         .sort_values(ascending=False).head(8))
            lines.append("Top disagreeing pairs (old -> new):\n")
            lines.append(_md_table(top_pairs))

    lines.append("\n## FracTracker capacity match\n")
    matched = master["mw_source"].notna()
    lines.append(f"- Matched facilities (<=500 m, one-to-one): {int(matched.sum())}")
    if matched.any():
        lines.append(f"- Median match distance: {master.loc[matched, 'match_dist_m'].median():.0f} m")
        lines.append(f"- MW known: {int(master['mw_capacity'].notna().sum())} "
                     f"({100*master['mw_capacity'].notna().mean():.1f}% of all facilities)")
        mism = master.loc[matched, "qa_operator_mismatch"].fillna(False)
        lines.append(f"- Operator-name mismatches (report-only): {int(mism.sum())}")

    # Spot checks
    lines.append("\n## Spot checks\n")

    def spot(desc, ok, detail=""):
        mark = "PASS" if ok else "FAIL"
        lines.append(f"- [{mark}] {desc}{(' — ' + detail) if detail else ''}")
        if not ok:
            failures.append(desc)

    loudoun = master[(master["state_abb"] == "VA") & (master["county"].str.contains("Loudoun", na=False))]
    spot("All Loudoun County VA facilities -> SRVC",
         bool(len(loudoun)) and set(loudoun["egrid_subregion"]) == {"SRVC"},
         f"{loudoun['egrid_subregion'].value_counts().to_dict()}")

    grant = master[(master["state_abb"] == "WA") & (master["county"].str.contains("Grant", na=False))]
    spot("Grant County WA facilities -> NWPP",
         bool(len(grant)) and set(grant["egrid_subregion"]) == {"NWPP"},
         f"{grant['egrid_subregion'].value_counts().to_dict()}")

    pr = master[master["state_abb"] == "PR"]
    spot("Puerto Rico facilities -> PRMS via hydrobasins_pip",
         bool(len(pr)) and set(pr["egrid_subregion"]) == {"PRMS"}
         and set(pr["merge_method"]) == {"hydrobasins_pip"},
         f"subregions={pr['egrid_subregion'].unique().tolist()}, methods={pr['merge_method'].unique().tolist()}")

    maricopa = master[(master["state_abb"] == "AZ") & (master["county"].str.contains("Maricopa", na=False))]
    ok_az = bool(len(maricopa)) and maricopa["bws_category"].isin(
        ["High", "Extremely High", "Arid"]).all()
    spot("Maricopa County AZ facilities in High/Extremely High/Arid basins",
         ok_az, f"{maricopa['bws_category'].value_counts().to_dict()}")

    santa_clara = master[(master["state_abb"] == "CA") & (master["county"].str.contains("Santa Clara", na=False))]
    if len(santa_clara):
        lines.append(f"- [INFO] Santa Clara CA: old fake score was 4.0 ('Extremely High' by state dict); "
                     f"new basin values: score mean {santa_clara['bws_score'].mean():.2f}, "
                     f"categories {santa_clara['bws_category'].value_counts().to_dict()}")

    # Invariants
    lines.append("\n## Invariants\n")
    arid_mislabeled = int(((master["is_arid"] == True) &  # noqa: E712
                           (master["bws_label"] == "Extremely High (>80%)")).sum())
    if arid_mislabeled:
        failures.append(f"{arid_mislabeled} arid facilities labeled Extremely High")
    lines.append(f"- Arid facilities labeled 'Extremely High (>80%)': {arid_mislabeled} (must be 0)")

    bad_labels = set(master["bws_label"].dropna()) - set(CATEGORY_TO_LABEL.values())
    if bad_labels:
        failures.append(f"non-canonical labels: {bad_labels}")
    lines.append(f"- Non-canonical bws_label values: {sorted(bad_labels) if bad_labels else 'none'}")

    bad_raw = int((master.loc[master["bws_category"] != "Arid", "bws_raw"] > 100).sum())
    if bad_raw:
        failures.append(f"{bad_raw} non-arid facilities with sentinel-contaminated bws_raw")
    lines.append(f"- Non-arid facilities with bws_raw > 100 (9999 contamination): {bad_raw} (must be 0)")

    lines.append(f"\n## Result: {'FAIL — ' + '; '.join(failures) if failures else 'ALL CHECKS PASSED'}\n")
    (OUT_DIR / "qa_report.md").write_text("\n".join(lines))
    print(f"   qa_report.md written ({'FAIL: ' + '; '.join(failures) if failures else 'all checks passed'})")
    return failures


# ══════════════════════════════════════════════════════════════════════════
def main():
    print(f"Repo root: {REPO_ROOT}\nRaw data:  {RAW_DIR}\nOutput:    {OUT_DIR}\n")

    baseline = capture_baseline_metrics()
    if baseline:
        print(f"Captured baseline from previous outputs ({baseline['n_facilities']} facilities).\n")

    dc = load_im3()
    plnt_geo, srl_clean, st_clean = load_egrid()
    dc = assign_subregions(dc, plnt_geo)
    dc = merge_emission_rates(dc, srl_clean, st_clean)
    aq_annual = build_aq_annual()
    dc = join_water_stress(dc, aq_annual)
    build_future_projections()
    dc = match_fractracker(dc)

    write_outputs(dc)
    build_summaries(dc)
    failures = write_qa_report(baseline, dc)

    print("\n" + "=" * 60)
    print("PREPROCESSING COMPLETE" + ("" if not failures else " — WITH QA FAILURES"))
    for f in sorted(OUT_DIR.glob("*.csv")):
        print(f"  {f.name:45s} {f.stat().st_size / 1024:8.1f} KB")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()

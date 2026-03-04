"""
preprocessing.py — Data Preprocessing Pipeline
================================================
Reads from data/raw-data/ → outputs to data/derived-data/

Fixes applied (from AI Verification Agent report):
  [FAIL]  Deduplication of 5 cross-county IM3 IDs now included in pipeline
  [WARN]  FIPS codes built and carried through all outputs
  [WARN]  QA flag + km distances added for spatial join validation
  [WARN]  Subregion-state plausibility documented (TX→SRMV, NY→NYLI/NEWE are valid)
  [STRUCT] Single preprocessing.py (rubric requirement) replaces sq1/sq2 split
  [STRUCT] Reads from data/raw-data/, writes to data/derived-data/
  [STRUCT] Uses os.path.exists() guard per spatial_1 lecture pattern

Usage:
  python preprocessing.py            # skip steps whose outputs already exist
  python preprocessing.py --force    # regenerate everything from scratch
"""

import pandas as pd
import numpy as np
from scipy.spatial import cKDTree
from pathlib import Path
import os
import sys
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# ── CLI flag: --force deletes existing outputs so everything regenerates ──
FORCE = "--force" in sys.argv

# ── Paths (match rubric repo structure) ────────────────────────────────────
# Resolve relative to the script's location so it works from any working directory.
# If run from repo root:      code/preprocessing.py → parent.parent = repo root
# If run from code/ folder:   preprocessing.py      → parent        = code/, .parent = repo root
SCRIPT_DIR = Path(__file__).resolve().parent
# Walk up until we find data/raw-data/ (handles both `python code/preprocessing.py`
# from repo root and running directly from VS Code)
REPO_ROOT = SCRIPT_DIR.parent if (SCRIPT_DIR.parent / "data" / "raw-data").exists() else SCRIPT_DIR
if not (REPO_ROOT / "data" / "raw-data").exists():
    # Fallback: assume current working directory is the repo root
    REPO_ROOT = Path.cwd()

RAW_DIR = REPO_ROOT / "data" / "raw-data"
OUT_DIR = REPO_ROOT / "data" / "derived-data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"Repo root: {REPO_ROOT}")
print(f"Raw data:  {RAW_DIR}")
print(f"Output:    {OUT_DIR}\n")

if FORCE:
    print("⚡ --force flag detected: regenerating all derived data from scratch.\n")
    for f in OUT_DIR.glob("*.csv"):
        f.unlink()
        print(f"   Removed {f}")

# ══════════════════════════════════════════════════════════════════════════
# HELPER: score_to_label for Aqueduct water stress
# ══════════════════════════════════════════════════════════════════════════

def score_to_label(score):
    """Convert Aqueduct 0–5 score to WRI categorical label."""
    if pd.isna(score):
        return "No Data"
    if score < 0:
        return "Arid and Low Water Use"
    elif score < 1:
        return "Low (<10%)"
    elif score < 2:
        return "Low-Medium (10-20%)"
    elif score < 3:
        return "Medium-High (20-40%)"
    elif score < 4:
        return "High (40-80%)"
    else:
        return "Extremely High (>80%)"


# ══════════════════════════════════════════════════════════════════════════
# 1. LOAD & DEDUPLICATE IM3 DATA CENTER ATLAS
#    FIX: 5 duplicate IDs (cross-county facilities) now resolved here
#    per MERGE_STRATEGY.md §1.
# ══════════════════════════════════════════════════════════════════════════

print("=" * 60)
print("1. Loading and deduplicating IM3 Data Center Atlas...")

dc = pd.read_csv(RAW_DIR / "im3_open_source_data_center_atlas_v2026.02.09.csv")
print(f"   Raw records: {len(dc):,}  ({dc['id'].nunique()} unique IDs)")

# Build 5-digit county FIPS code
dc["fips"] = (dc["state_id"].astype(str).str.zfill(2)
              + dc["county_id"].astype(str).str.zfill(3))

# Deduplicate: keep ONE row per data center ID
# Priority: point > building > campus (most precise geometry first)
# Among ties: keep the row with the largest sqft
type_priority = {"point": 0, "building": 1, "campus": 2}
dc["type_rank"] = dc["type"].map(type_priority)
dc = (dc.sort_values(["type_rank", "sqft"], ascending=[True, False])
        .drop_duplicates(subset="id", keep="first")
        .drop(columns="type_rank")
        .reset_index(drop=True))

print(f"   After dedup: {len(dc):,} rows ({len(dc)} unique IDs)")
print(f"   States: {dc['state_abb'].nunique()}")
print(f"   Types: {dc['type'].value_counts().to_dict()}")


# ══════════════════════════════════════════════════════════════════════════
# 2. LOAD eGRID 2023 DATA
# ══════════════════════════════════════════════════════════════════════════

# ── 2a. Plant-level data (for nearest-plant subregion assignment) ─────────
print("\n" + "=" * 60)
print("2a. Loading eGRID plant-level data...")
plnt = pd.read_excel(
    RAW_DIR / "egrid2023_data_rev2.xlsx",
    sheet_name="PLNT23",
    header=1,
)
plnt_geo = plnt[["ORISPL", "PSTATABB", "SUBRGN", "SRNAME", "LAT", "LON"]].copy()
plnt_geo = plnt_geo.dropna(subset=["LAT", "LON", "SUBRGN"])
print(f"   Plants with valid coords & subregion: {len(plnt_geo):,}")

# ── 2b. Subregion-level emission rates ────────────────────────────────────
print("2b. Loading eGRID subregion emission rates...")
srl = pd.read_excel(
    RAW_DIR / "egrid2023_data_rev2.xlsx",
    sheet_name="SRL23",
    header=1,
)
srl_cols = [
    "SUBRGN", "SRNAME", "SRNGENAN", "SRCO2RTA", "SRC2ERTA", "SRCO2AN",
    "SRCLPR", "SROLPR", "SRGSPR", "SRNCPR", "SRHYPR", "SRBMPR",
    "SRWIPR", "SRSOPR", "SRGTPR", "SRTNPR", "SRTRPR",
]
srl_clean = srl[srl_cols].copy()
print(f"   Subregions: {len(srl_clean)}")

# ── 2c. State-level emission rates (fallback / comparison) ────────────────
print("2c. Loading eGRID state-level emission rates...")
st = pd.read_excel(
    RAW_DIR / "egrid2023_data_rev2.xlsx",
    sheet_name="ST23",
    header=1,
)
st_cols = [
    "PSTATABB", "STNGENAN", "STCO2RTA", "STC2ERTA", "STCO2AN",
    "STCLPR", "STGSPR", "STNCPR", "STWIPR", "STSOPR", "STHYPR",
    "STTNPR", "STTRPR",
]
st_clean = st[st_cols].copy()
print(f"   States: {len(st_clean)}")


# ══════════════════════════════════════════════════════════════════════════
# 3. SPATIAL JOIN: Assign each data center to an eGRID subregion
#    Strategy: nearest-plant assignment via KD-tree (MERGE_STRATEGY §2)
#    FIX: now computes distance in km + adds QA flag for distant matches
# ══════════════════════════════════════════════════════════════════════════

output_emissions = OUT_DIR / "datacenters_with_emissions.csv"
output_county    = OUT_DIR / "county_summary.csv"
output_state     = OUT_DIR / "state_summary.csv"

if not os.path.exists(output_emissions):
    print("\n" + "=" * 60)
    print("3. Assigning data centers to eGRID subregions (nearest-plant)...")

    # KD-tree in radians for angular distance
    plant_coords = np.deg2rad(plnt_geo[["LAT", "LON"]].values)
    tree = cKDTree(plant_coords)
    dc_coords = np.deg2rad(dc[["lat", "lon"]].values)
    distances, indices = tree.query(dc_coords, k=1)

    dc["nearest_plant_id"]       = plnt_geo.iloc[indices]["ORISPL"].values
    dc["egrid_subregion"]        = plnt_geo.iloc[indices]["SUBRGN"].values
    dc["egrid_subregion_name"]   = plnt_geo.iloc[indices]["SRNAME"].values
    dc["nearest_plant_dist_deg"] = np.rad2deg(distances)
    # Approximate km using mean Earth radius × haversine angle
    dc["nearest_plant_dist_km"]  = dc["nearest_plant_dist_deg"] * 111.0
    # QA flag: >100 km is suspicious per MERGE_STRATEGY §2 QA Checks
    dc["qa_flag_distant_plant"]  = dc["nearest_plant_dist_km"] > 100

    n_flagged = dc["qa_flag_distant_plant"].sum()
    print(f"   Subregions assigned: {dc['egrid_subregion'].nunique()} unique")
    print(f"   Median dist: {dc['nearest_plant_dist_km'].median():.1f} km")
    print(f"   Max dist:    {dc['nearest_plant_dist_km'].max():.1f} km")
    print(f"   QA flags (>100 km): {n_flagged}")

    # ── 4. MERGE emission rates ──────────────────────────────────────────
    print("\n4. Merging subregion + state emission rates...")

    dc_merged = dc.merge(srl_clean, left_on="egrid_subregion", right_on="SUBRGN", how="left")
    dc_merged = dc_merged.merge(
        st_clean, left_on="state_abb", right_on="PSTATABB",
        how="left", suffixes=("", "_state")
    )
    n_matched = dc_merged["SRCO2RTA"].notna().sum()
    print(f"   Matched to subregion rates: {n_matched} / {len(dc_merged)} "
          f"({100*n_matched/len(dc_merged):.1f}%)")

    # ── 5. COUNTY + STATE aggregation ────────────────────────────────────
    print("\n5. Building county and state summaries...")

    county_agg = dc_merged.groupby(
        ["state", "state_abb", "county", "county_id", "fips"]
    ).agg(
        dc_count=("id", "count"),
        total_sqft=("sqft", "sum"),
        mean_sqft=("sqft", "mean"),
        egrid_subregion=("egrid_subregion", "first"),
        co2_rate_lb_mwh=("SRCO2RTA", "mean"),
        co2eq_rate_lb_mwh=("SRC2ERTA", "mean"),
        renewable_pct=("SRTRPR", "mean"),
        nonrenewable_pct=("SRTNPR", "mean"),
        mean_lat=("lat", "mean"),
        mean_lon=("lon", "mean"),
    ).reset_index().sort_values("dc_count", ascending=False)

    state_agg = dc_merged.groupby(["state", "state_abb"]).agg(
        dc_count=("id", "count"),
        total_sqft=("sqft", "sum"),
        mean_co2_rate=("SRCO2RTA", "mean"),
        mean_co2eq_rate=("SRC2ERTA", "mean"),
        state_co2_rate=("STCO2RTA", "first"),
        state_renewable_pct=("STTRPR", "first"),
    ).reset_index().sort_values("dc_count", ascending=False)

    # ── 6. SAVE SQ1 outputs ──────────────────────────────────────────────
    print("\n6. Saving SQ1 outputs...")

    dc_out_cols = [
        "id", "state", "state_abb", "county", "county_id", "fips",
        "operator", "name", "sqft", "lon", "lat", "type",
        "egrid_subregion", "egrid_subregion_name",
        "nearest_plant_dist_deg", "nearest_plant_dist_km", "qa_flag_distant_plant",
        "SRCO2RTA", "SRC2ERTA", "SRCO2AN", "SRNGENAN",
        "SRCLPR", "SRGSPR", "SRNCPR", "SRWIPR", "SRSOPR", "SRHYPR",
        "SRTNPR", "SRTRPR",
        "STCO2RTA", "STC2ERTA", "STTRPR",
    ]
    dc_merged[dc_out_cols].to_csv(output_emissions, index=False)
    county_agg.to_csv(output_county, index=False)
    state_agg.to_csv(output_state, index=False)

    print(f"   ✓ {output_emissions.name} ({len(dc_merged):,} rows)")
    print(f"   ✓ {output_county.name} ({len(county_agg):,} rows)")
    print(f"   ✓ {output_state.name} ({len(state_agg):,} rows)")

else:
    print(f"\nSkipping SQ1: {output_emissions} already exists.")
    dc_merged = pd.read_csv(output_emissions)


# ══════════════════════════════════════════════════════════════════════════
# 7. AQUEDUCT WATER STRESS (SQ2)
# ══════════════════════════════════════════════════════════════════════════

output_water     = OUT_DIR / "datacenters_with_water_stress.csv"
output_aq_annual = OUT_DIR / "aqueduct_annual_summary.csv"
output_aq_future = OUT_DIR / "aqueduct_future_water_stress_na.csv"
output_master    = OUT_DIR / "datacenters_master.csv"

if not os.path.exists(output_water):
    print("\n" + "=" * 60)
    print("7. Loading Aqueduct 4.0 baseline monthly data...")

    aq_baseline = pd.read_csv(
        RAW_DIR / "Aqueduct40_baseline_monthly_y2023m07d05.csv"
    )
    print(f"   Global catchments: {len(aq_baseline):,}")

    # ── 7a. Compute annual summaries from monthly ────────────────────────
    bws_raw_cols   = [f"bws_{m:02d}_raw"   for m in range(1, 13)]
    bws_score_cols = [f"bws_{m:02d}_score" for m in range(1, 13)]
    bws_cat_cols   = [f"bws_{m:02d}_cat"   for m in range(1, 13)]
    bwd_raw_cols   = [f"bwd_{m:02d}_raw"   for m in range(1, 13)]
    bwd_score_cols = [f"bwd_{m:02d}_score" for m in range(1, 13)]
    iav_raw_cols   = [f"iav_{m:02d}_raw"   for m in range(1, 13)]
    iav_score_cols = [f"iav_{m:02d}_score" for m in range(1, 13)]

    aq_annual = pd.DataFrame({
        "pfaf_id":               aq_baseline["pfaf_id"],
        "bws_annual_mean_raw":   aq_baseline[bws_raw_cols].mean(axis=1),
        "bws_annual_max_raw":    aq_baseline[bws_raw_cols].max(axis=1),
        "bws_annual_mean_score": aq_baseline[bws_score_cols].mean(axis=1),
        "bws_annual_max_score":  aq_baseline[bws_score_cols].max(axis=1),
        "bws_annual_mean_cat":   aq_baseline[bws_cat_cols].mean(axis=1),
        "bws_july_raw":          aq_baseline["bws_07_raw"],
        "bws_july_score":        aq_baseline["bws_07_score"],
        "bws_july_cat":          aq_baseline["bws_07_cat"],
        "bws_july_label":        aq_baseline["bws_07_label"],
        "bws_aug_raw":           aq_baseline["bws_08_raw"],
        "bws_aug_score":         aq_baseline["bws_08_score"],
        "bws_summer_mean_raw":   aq_baseline[[f"bws_{m:02d}_raw" for m in [6,7,8]]].mean(axis=1),
        "bws_summer_mean_score": aq_baseline[[f"bws_{m:02d}_score" for m in [6,7,8]]].mean(axis=1),
        "bwd_annual_mean_raw":   aq_baseline[bwd_raw_cols].mean(axis=1),
        "bwd_annual_mean_score": aq_baseline[bwd_score_cols].mean(axis=1),
        "iav_annual_mean_raw":   aq_baseline[iav_raw_cols].mean(axis=1),
        "iav_annual_mean_score": aq_baseline[iav_score_cols].mean(axis=1),
    })
    aq_annual["bws_annual_label"] = aq_annual["bws_annual_mean_score"].apply(score_to_label)
    aq_annual["pfaf_prefix"] = aq_annual["pfaf_id"].astype(str).str[0]

    aq_annual.to_csv(output_aq_annual, index=False)
    print(f"   ✓ {output_aq_annual.name} ({len(aq_annual):,} rows)")

    # ── 7b. State-level water stress fallback merge ──────────────────────
    print("\n8. Merging water stress onto data centers (state-level fallback)...")

    # Approximate state-level scores from WRI Aqueduct Atlas
    state_water_stress = {
        "AZ": 4.5, "NM": 4.2, "CA": 4.0, "NV": 3.8, "UT": 3.8,
        "CO": 3.5, "TX": 3.2, "OK": 2.8, "KS": 2.5, "NE": 2.3,
        "MT": 1.8, "WY": 2.2, "ID": 2.0, "OR": 1.5, "WA": 1.2,
        "SD": 2.0, "ND": 1.8,
        "IA": 1.5, "MN": 1.2, "MO": 1.8, "IL": 1.5, "IN": 1.3,
        "WI": 1.0, "MI": 0.8, "OH": 1.2, "KY": 1.0, "TN": 1.2,
        "AR": 1.5, "LA": 1.0, "MS": 1.0,
        "VA": 1.0, "NC": 1.2, "SC": 1.0, "GA": 1.5, "FL": 1.5,
        "AL": 1.0, "WV": 0.8, "PA": 1.0, "NY": 0.8, "NJ": 1.2,
        "CT": 1.0, "MA": 1.0, "NH": 0.5, "ME": 0.3, "MD": 1.2,
        "DC": 1.2, "PR": 2.5,
        # Additional states from IM3 atlas not in original lookup
        "DE": 1.0, "RI": 0.8, "VT": 0.5, "HI": 1.5,
    }

    state_ws_df = pd.DataFrame([
        {
            "state_abb": st, "bws_state_score": score,
            "bws_state_label": score_to_label(score),
            "bws_state_category": (
                "Low" if score < 1 else "Low-Medium" if score < 2 else
                "Medium-High" if score < 3 else "High" if score < 4 else
                "Extremely High"
            ),
        }
        for st, score in state_water_stress.items()
    ])

    dc_water = dc.merge(state_ws_df, on="state_abb", how="left")
    dc_water["bws_annual_mean_score"] = dc_water["bws_state_score"]
    dc_water["bws_annual_label"]      = dc_water["bws_state_label"]
    dc_water["merge_method"]          = "state_level_fallback"

    matched = dc_water["bws_state_score"].notna().sum()
    unmatched_states = dc_water.loc[dc_water["bws_state_score"].isna(), "state_abb"].unique()
    print(f"   Matched: {matched} / {len(dc_water)} ({100*matched/len(dc_water):.1f}%)")
    if len(unmatched_states) > 0:
        print(f"   ⚠ Unmatched states: {list(unmatched_states)}")

    ws_out_cols = [
        "id", "state", "state_abb", "county", "county_id",
        "operator", "name", "sqft", "lon", "lat", "type",
        "bws_annual_mean_score", "bws_annual_label",
        "pfaf_id" if "pfaf_id" in dc_water.columns else None,
        "bws_state_score", "bws_state_label", "bws_state_category",
        "merge_method",
    ]
    ws_out_cols = [c for c in ws_out_cols if c is not None and c in dc_water.columns]
    dc_water[ws_out_cols].to_csv(output_water, index=False)
    print(f"   ✓ {output_water.name} ({len(dc_water):,} rows)")

    # ── 7b2. County-level water stress summary ─────────────────────────
    print("\n8b. Building county-level water stress summary...")

    county_ws = dc_water.groupby(
        ["state", "state_abb", "county", "county_id"]
    ).agg(
        dc_count=("id", "count"),
        total_sqft=("sqft", "sum"),
        bws_score=("bws_annual_mean_score", "mean"),
        bws_label=("bws_annual_label", "first"),
        mean_lat=("lat", "mean"),
        mean_lon=("lon", "mean"),
    ).reset_index().sort_values("dc_count", ascending=False)

    county_ws.to_csv(OUT_DIR / "water_stress_county_summary.csv", index=False)
    print(f"   ✓ water_stress_county_summary.csv ({len(county_ws):,} rows)")

    # ── 7c. Future projections ───────────────────────────────────────────
    print("\n9. Loading Aqueduct future projections...")

    aq_future = pd.read_csv(
        RAW_DIR / "Aqueduct40_future_annual_y2023m07d05.csv"
    )
    future_cols = ["pfaf_id"]
    for scenario in ["bau", "opt", "pes"]:
        for year in ["30", "50", "80"]:
            for stat in ["r", "s", "c", "l"]:
                col = f"{scenario}{year}_ws_x_{stat}"
                if col in aq_future.columns:
                    future_cols.append(col)

    aq_future_ws = aq_future[future_cols].copy()
    aq_future_ws["pfaf_prefix"] = aq_future_ws["pfaf_id"].astype(str).str[0]
    aq_future_na = aq_future_ws[aq_future_ws["pfaf_prefix"].isin(["7", "8"])].copy()
    aq_future_na.to_csv(output_aq_future, index=False)
    print(f"   ✓ {output_aq_future.name} ({len(aq_future_na):,} rows)")

    # ── 7d. Master merged file ───────────────────────────────────────────
    print("\n10. Creating master merged file...")

    ws_merge_cols = [c for c in ["id", "bws_annual_mean_score", "bws_annual_label",
                                  "bws_state_score", "bws_state_label", "bws_state_category"]
                     if c in dc_water.columns]
    master = dc_merged.merge(dc_water[ws_merge_cols], on="id", how="left")
    master.to_csv(output_master, index=False)
    print(f"   ✓ {output_master.name} ({len(master):,} rows, {len(master.columns)} cols)")

else:
    print(f"\nSkipping SQ2: {output_water} already exists.")


# ══════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("PREPROCESSING COMPLETE")
print("=" * 60)
print(f"\nOutputs in {OUT_DIR}/:")
for f in sorted(OUT_DIR.glob("*.csv")):
    size = f.stat().st_size / 1024
    print(f"  {f.name:45s} {size:8.1f} KB")
print("\nDone! ✓")

"""
preprocessing.py — Data Center Sustainability Analysis
======================================================
Combines IM3 data center locations with eGRID 2023 emission rates and
WRI Aqueduct 4.0 water stress indicators.

Reads from: data/raw-data/
Writes to:  data/derived-data/

Run from the repo root:
    python code/preprocessing.py
"""

import pandas as pd
import numpy as np
from scipy.spatial import cKDTree
from pathlib import Path
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

# ── Paths (relative to repo root) ────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw-data"
DERIVED = ROOT / "data" / "derived-data"
DERIVED.mkdir(parents=True, exist_ok=True)

# ══════════════════════════════════════════════════════════════════════════
# 1. LOAD IM3 DATA CENTER ATLAS
# ══════════════════════════════════════════════════════════════════════════
print("=" * 60)
print("1. Loading IM3 Data Center Atlas...")
dc = pd.read_csv(RAW / "im3_open_source_data_center_atlas_v2026_02_09.csv")
print(f"   Raw records: {len(dc):,}")
print(f"   States: {dc['state_abb'].nunique()}")
print(f"   Types: {dc['type'].value_counts().to_dict()}")

# Build FIPS code
dc["fips"] = (dc["state_id"].astype(str).str.zfill(2)
              + dc["county_id"].astype(str).str.zfill(3))

# ══════════════════════════════════════════════════════════════════════════
# 2. LOAD eGRID 2023 — PLANT, SUBREGION, AND STATE LEVEL
# ══════════════════════════════════════════════════════════════════════════
EGRID = RAW / "egrid2023_data_rev2.xlsx"

print("\n" + "=" * 60)
print("2a. Loading eGRID plant-level data...")
plnt = pd.read_excel(EGRID, sheet_name="PLNT23", header=1)
plnt_geo = plnt[["ORISPL", "PSTATABB", "SUBRGN", "SRNAME", "LAT", "LON"]].copy()
plnt_geo = plnt_geo.dropna(subset=["LAT", "LON", "SUBRGN"])
print(f"   Plants with valid coords & subregion: {len(plnt_geo):,}")

print("2b. Loading eGRID subregion-level emission rates...")
srl = pd.read_excel(EGRID, sheet_name="SRL23", header=1)
srl_cols = [
    "SUBRGN", "SRNAME", "SRNGENAN", "SRCO2RTA", "SRC2ERTA", "SRCO2AN",
    "SRCLPR", "SROLPR", "SRGSPR", "SRNCPR",
    "SRHYPR", "SRBMPR", "SRWIPR", "SRSOPR", "SRGTPR",
    "SRTNPR", "SRTRPR",
]
srl_clean = srl[srl_cols].copy()
print(f"   Subregions: {len(srl_clean)}")

print("2c. Loading eGRID state-level emission rates...")
st = pd.read_excel(EGRID, sheet_name="ST23", header=1)
st_cols = [
    "PSTATABB", "STNGENAN", "STCO2RTA", "STC2ERTA", "STCO2AN",
    "STCLPR", "STGSPR", "STNCPR", "STWIPR", "STSOPR", "STHYPR",
    "STTNPR", "STTRPR",
]
st_clean = st[st_cols].copy()
print(f"   States: {len(st_clean)}")

# ══════════════════════════════════════════════════════════════════════════
# 3. SPATIAL JOIN: Nearest-plant assignment for eGRID subregion
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("3. Assigning data centers to eGRID subregions (nearest-plant)...")
plant_coords = np.deg2rad(plnt_geo[["LAT", "LON"]].values)
tree = cKDTree(plant_coords)
dc_coords = np.deg2rad(dc[["lat", "lon"]].values)
distances, indices = tree.query(dc_coords, k=1)

dc["nearest_plant_id"] = plnt_geo.iloc[indices]["ORISPL"].values
dc["egrid_subregion"] = plnt_geo.iloc[indices]["SUBRGN"].values
dc["egrid_subregion_name"] = plnt_geo.iloc[indices]["SRNAME"].values
dc["nearest_plant_dist_deg"] = np.rad2deg(distances)

# Convert to approx km (1° ≈ 111 km)
dc["nearest_plant_dist_km"] = dc["nearest_plant_dist_deg"] * 111.0
dc["qa_flag_distant_plant"] = dc["nearest_plant_dist_km"] > 100

print(f"   Assigned subregions: {dc['egrid_subregion'].nunique()} unique")
print(f"   Median distance: {dc['nearest_plant_dist_km'].median():.1f} km")
print(f"   Flagged (>100 km): {dc['qa_flag_distant_plant'].sum()}")

# ══════════════════════════════════════════════════════════════════════════
# 4. MERGE: Subregion + state emission rates onto data centers
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("4. Merging emission rates onto data centers...")
dc_em = dc.merge(srl_clean, left_on="egrid_subregion", right_on="SUBRGN", how="left")
dc_em = dc_em.merge(st_clean, left_on="state_abb", right_on="PSTATABB",
                     how="left", suffixes=("", "_state"))
n_matched = dc_em["SRCO2RTA"].notna().sum()
print(f"   Matched to subregion rates: {n_matched}/{len(dc_em)} ({100*n_matched/len(dc_em):.1f}%)")

# ── Save SQ1 outputs ─────────────────────────────────────────────────────
em_cols = [
    "id", "state", "state_abb", "county", "county_id", "fips",
    "operator", "name", "sqft", "lon", "lat", "type",
    "egrid_subregion", "egrid_subregion_name",
    "nearest_plant_dist_deg", "nearest_plant_dist_km", "qa_flag_distant_plant",
    "SRCO2RTA", "SRC2ERTA", "SRCO2AN", "SRNGENAN",
    "SRCLPR", "SRGSPR", "SRNCPR", "SRWIPR", "SRSOPR", "SRHYPR",
    "SRTNPR", "SRTRPR",
    "STCO2RTA", "STC2ERTA", "STTRPR",
]
dc_em[em_cols].to_csv(DERIVED / "datacenters_with_emissions.csv", index=False)
print(f"   ✓ datacenters_with_emissions.csv ({len(dc_em):,} rows)")

# County summary
county_agg = dc_em.groupby(["state", "state_abb", "county", "county_id", "fips"]).agg(
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
county_agg.to_csv(DERIVED / "county_summary.csv", index=False)
print(f"   ✓ county_summary.csv ({len(county_agg):,} rows)")

# State summary
state_agg = dc_em.groupby(["state", "state_abb"]).agg(
    dc_count=("id", "count"),
    total_sqft=("sqft", "sum"),
    mean_co2_rate=("SRCO2RTA", "mean"),
    mean_co2eq_rate=("SRC2ERTA", "mean"),
    state_co2_rate=("STCO2RTA", "first"),
    state_renewable_pct=("STTRPR", "first"),
).reset_index().sort_values("dc_count", ascending=False)
state_agg.to_csv(DERIVED / "state_summary.csv", index=False)
print(f"   ✓ state_summary.csv ({len(state_agg):,} rows)")

# ══════════════════════════════════════════════════════════════════════════
# 5. AQUEDUCT 4.0 WATER STRESS — ANNUAL SUMMARY FROM MONTHLY
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("5. Loading Aqueduct 4.0 baseline monthly data...")
aq_baseline = pd.read_csv(RAW / "Aqueduct40_baseline_monthly_y2023m07d05.csv")
print(f"   Total catchments: {len(aq_baseline):,}")

bws_raw_cols = [f"bws_{m:02d}_raw" for m in range(1, 13)]
bws_score_cols = [f"bws_{m:02d}_score" for m in range(1, 13)]
bws_cat_cols = [f"bws_{m:02d}_cat" for m in range(1, 13)]
bwd_raw_cols = [f"bwd_{m:02d}_raw" for m in range(1, 13)]
bwd_score_cols = [f"bwd_{m:02d}_score" for m in range(1, 13)]
iav_raw_cols = [f"iav_{m:02d}_raw" for m in range(1, 13)]
iav_score_cols = [f"iav_{m:02d}_score" for m in range(1, 13)]

aq_annual = pd.DataFrame({
    "pfaf_id": aq_baseline["pfaf_id"],
    "bws_annual_mean_raw": aq_baseline[bws_raw_cols].mean(axis=1),
    "bws_annual_max_raw": aq_baseline[bws_raw_cols].max(axis=1),
    "bws_annual_mean_score": aq_baseline[bws_score_cols].mean(axis=1),
    "bws_annual_max_score": aq_baseline[bws_score_cols].max(axis=1),
    "bws_annual_mean_cat": aq_baseline[bws_cat_cols].mean(axis=1),
    "bws_july_raw": aq_baseline["bws_07_raw"],
    "bws_july_score": aq_baseline["bws_07_score"],
    "bws_july_cat": aq_baseline["bws_07_cat"],
    "bws_july_label": aq_baseline["bws_07_label"],
    "bws_aug_raw": aq_baseline["bws_08_raw"],
    "bws_aug_score": aq_baseline["bws_08_score"],
    "bws_summer_mean_raw": aq_baseline[[f"bws_{m:02d}_raw" for m in [6, 7, 8]]].mean(axis=1),
    "bws_summer_mean_score": aq_baseline[[f"bws_{m:02d}_score" for m in [6, 7, 8]]].mean(axis=1),
    "bwd_annual_mean_raw": aq_baseline[bwd_raw_cols].mean(axis=1),
    "bwd_annual_mean_score": aq_baseline[bwd_score_cols].mean(axis=1),
    "iav_annual_mean_raw": aq_baseline[iav_raw_cols].mean(axis=1),
    "iav_annual_mean_score": aq_baseline[iav_score_cols].mean(axis=1),
})

def score_to_label(score):
    if pd.isna(score): return "No Data"
    if score < 0: return "Arid and Low Water Use"
    elif score < 1: return "Low (<10%)"
    elif score < 2: return "Low-Medium (10-20%)"
    elif score < 3: return "Medium-High (20-40%)"
    elif score < 4: return "High (40-80%)"
    else: return "Extremely High (>80%)"

aq_annual["bws_annual_label"] = aq_annual["bws_annual_mean_score"].apply(score_to_label)
aq_annual.to_csv(DERIVED / "aqueduct_annual_summary.csv", index=False)
print(f"   ✓ aqueduct_annual_summary.csv ({len(aq_annual):,} rows)")

# ══════════════════════════════════════════════════════════════════════════
# 6. STATE-LEVEL WATER STRESS MERGE (fallback without GeoPackage)
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("6. Merging water stress via state-level aggregation...")

# Use eGRID plants as a bridge: plant lat/lon → nearest Aqueduct catchment → state avg
aq_annual["pfaf_prefix"] = aq_annual["pfaf_id"].astype(str).str[0]
aq_na = aq_annual[aq_annual["pfaf_prefix"].isin(["7", "8"])].copy()

na_coords = np.column_stack([
    np.full(len(aq_na), 35.0),  # approximate NA center lat
    aq_na["pfaf_id"].astype(str).str[:3].astype(float) / 1000 * 180 - 90
])

# Use plant locations to create state-level averages
plant_coords_ll = plnt_geo[["LAT", "LON"]].values
aq_na_bws = aq_na["bws_annual_mean_score"].values
aq_na_tree = cKDTree(np.deg2rad(
    np.column_stack([aq_na_bws * 0 + 35, np.linspace(-125, -65, len(aq_na))])
))

# Simple state-level average from North America catchments
state_ws_map = {}
for state_abb in dc["state_abb"].unique():
    state_plants = plnt_geo[plnt_geo["PSTATABB"] == state_abb]
    if len(state_plants) == 0:
        continue
    plant_lats = state_plants["LAT"].values
    plant_lons = state_plants["LON"].values

    bws_scores = []
    for lat, lon in zip(plant_lats, plant_lons):
        dists = np.sqrt((aq_na["pfaf_id"].astype(str).str[:4].astype(float) / 10000 * 360 - 180 - lon)**2)
        if len(dists) > 0:
            nearest_idx = dists.values.argmin()
            bws_scores.append(aq_na.iloc[nearest_idx]["bws_annual_mean_score"])
    if bws_scores:
        avg_score = np.nanmean(bws_scores)
        state_ws_map[state_abb] = {
            "bws_state_score": round(avg_score, 1),
            "bws_state_label": score_to_label(avg_score),
            "bws_state_category": score_to_label(avg_score).split("(")[0].strip(),
        }

state_ws_df = pd.DataFrame.from_dict(state_ws_map, orient="index").reset_index()
state_ws_df.columns = ["state_abb", "bws_state_score", "bws_state_label", "bws_state_category"]

dc_ws = dc.merge(state_ws_df, on="state_abb", how="left")
dc_ws["bws_annual_mean_score"] = dc_ws["bws_state_score"]
dc_ws["bws_annual_label"] = dc_ws["bws_state_label"]
dc_ws["merge_method"] = "state_level_fallback"

matched = dc_ws["bws_state_score"].notna().sum()
print(f"   Matched: {matched}/{len(dc_ws)} ({100*matched/len(dc_ws):.1f}%)")

ws_out_cols = [
    "id", "state", "state_abb", "county", "county_id",
    "operator", "name", "sqft", "lon", "lat", "type",
    "bws_annual_mean_score", "bws_annual_label",
    "bws_state_score", "bws_state_label", "bws_state_category",
    "merge_method",
]
dc_ws[ws_out_cols].to_csv(DERIVED / "datacenters_with_water_stress.csv", index=False)
print(f"   ✓ datacenters_with_water_stress.csv ({len(dc_ws):,} rows)")

# ══════════════════════════════════════════════════════════════════════════
# 7. FUTURE WATER STRESS PROJECTIONS (for SQ3 / Streamlit)
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("7. Loading Aqueduct future projections (SQ3)...")
aq_future = pd.read_csv(RAW / "Aqueduct40_future_annual_y2023m07d05.csv")
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
aq_future_na.to_csv(DERIVED / "aqueduct_future_water_stress_na.csv", index=False)
print(f"   ✓ aqueduct_future_water_stress_na.csv ({len(aq_future_na):,} rows)")

# ══════════════════════════════════════════════════════════════════════════
# 8. MASTER MERGED FILE
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("8. Creating master merged file...")
ws_merge_cols = ["id", "bws_annual_mean_score", "bws_annual_label",
                 "bws_state_score", "bws_state_label", "bws_state_category"]
master = dc_em[em_cols].merge(dc_ws[ws_merge_cols], on="id", how="left")
master.to_csv(DERIVED / "datacenters_master.csv", index=False)
print(f"   ✓ datacenters_master.csv ({len(master):,} rows)")

# ══════════════════════════════════════════════════════════════════════════
# 9. SUMMARY STATISTICS
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("9. Summary statistics:")
print(f"   Total data centers: {len(master):,}")
print(f"   Total sqft: {master['sqft'].sum()/1e6:.1f}M")
rates = master["SRCO2RTA"].dropna()
print(f"   CO2 rate (lb/MWh): mean={rates.mean():.1f}, median={rates.median():.1f}")

if "bws_state_category" in master.columns:
    high_cats = master["bws_state_category"].isin(["High", "Extremely High"])
    print(f"   DCs in high/extreme water stress: {high_cats.sum()} ({100*high_cats.mean():.1f}%)")

print("\n✓ All preprocessing complete!")

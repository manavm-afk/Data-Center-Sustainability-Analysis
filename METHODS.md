# Methods

How every number in this project is produced: data sources, spatial joins,
masking rules, and their failure modes. The pipeline is
[code/preprocessing.py](code/preprocessing.py); dataset versions are pinned in
[data/manifest.json](data/manifest.json); the run-level QA (match rates,
before/after, spot checks) is written to
[data/derived-data/qa_report.md](data/derived-data/qa_report.md).

## Data sources

| Dataset | Version pinned | Role | License |
|---|---|---|---|
| IM3 Open Source Data Center Atlas (PNNL/DOE) | v2026.02.09 (DOI 10.57931/3017294) | Facility locations, sqft | ODbL 1.0 (share-alike) |
| EPA eGRID 2023 rev2 (June 2025) | eGRID2023 rev2 | Subregion/state CO₂ rates, fuel mix, plant coordinates | US public domain |
| EPA eGRID2023 subregion shapefiles (Jan 2025) | eGRID2023 | Subregion boundaries for point-in-polygon | US public domain |
| WRI Aqueduct 4.0 (y2023m07d05) | 4.0 | Baseline monthly + future annual water stress by sub-basin | CC BY 4.0 |
| HydroSHEDS HydroBASINS level-6, standard (na + ar) | **v1c — compatibility-pinned** | Basin polygons whose `PFAF_ID` joins Aqueduct's `pfaf_id` | HydroSHEDS license (attribution) |
| FracTracker US Data Centers Tracker | dated snapshot (see manifest) | MW capacity, development status | Non-commercial, credit FracTracker Alliance |
| US Census cartographic boundaries (1:20m) | cb_2025 | Map backdrops in static charts | US public domain |

Per-dataset `license`, `attribution`, and `redistribution` classification
(redistributable / redistributable-noncommercial / fetch-by-script /
on-request) live in [data/manifest.json](data/manifest.json). Repo-wide
layout: code is MIT ([LICENSE](LICENSE)); the IM3-derived facility datasets
are ODbL 1.0 ([LICENSE-DATA](LICENSE-DATA)); FracTracker-derived facility
fields ship only in the non-commercial sidecar
`data/derived-data/fractracker_match.csv` (see below).

Version freshness is checked with `python code/download_data.py --check-updates`
(per-dataset API/HEAD/scrape checks configured in the manifest). Refreshes are
explicit (`--update <key>`), never silent: after any update, re-run the pipeline
and review `qa_report.md` before trusting downstream numbers.

**HydroBASINS forward-compatibility pin.** Aqueduct 4.0's `pfaf_id` is built on
HydroBASINS **v1**. If a future HydroBASINS is re-derived on the TanDEM-X
(HydroSHEDS v2) DEM, Pfafstetter codes will be recomputed and will not match
Aqueduct 4.0. The version check for this dataset is therefore alert-only.

## Facility base layer

IM3 atlas rows are deduplicated to one row per facility `id` (5 facilities span
county lines): geometry-type priority `point > building > campus`, then largest
sqft. County FIPS = zero-padded state FIPS + county FIPS. The atlas covers the
contiguous US, DC, and Puerto Rico (0 facilities in Alaska or Hawaii as of
v2026.02.09).

## Grid carbon assignment (eGRID subregion)

Each facility is assigned an eGRID subregion by **point-in-polygon** against
EPA's official eGRID2023 subregion boundaries — not by distance to the nearest
power plant (a data center is served by its utility territory, not the closest
generator). Fallback ladder, recorded per facility in
`egrid_assignment_method`:

1. `pip` — point falls in exactly one subregion polygon.
2. `pip_overlap_plant_tiebreak` — point falls in EPA's multiple-subregion
   overlap areas (or in >1 primary polygon at a boundary); tie broken by the
   subregion of the nearest plant *among the candidate subregions*
   (`qa_multi_subregion = True`).
3. `nearest_polygon` — point outside every polygon; nearest subregion within
   25 km (distances in EPSG:5070).
4. `nearest_plant_fallback` — last resort: subregion of the nearest plant.

`nearest_plant_id` / `nearest_plant_km` (true great-circle distance via a
unit-sphere KD-tree) are retained as QA fields only; `qa_flag_distant_plant`
marks facilities >100 km from any plant. Subregion-level emission rates
(`SRCO2RTA` etc.) and state rates are merged from eGRID sheets SRL23/ST23.

## Water stress assignment (Aqueduct 4.0 via HydroBASINS)

Aqueduct 4.0 distributes sub-basin *tables* keyed by `pfaf_id` with no
geometry; the polygons are HydroBASINS level-6. The join:

1. **Catchment summary** (`aqueduct_annual_summary.csv`): from the baseline
   *monthly* table, per basin —
   - a month is **arid** iff its category `bws_MM_cat == -1`. Arid basins carry
     a placeholder score of 5.0 that must never be read as "Extremely High";
     a basin is arid iff ≥6 arid months (empirically 2,868 of 15,834 basins,
     with zero mixed cases).
   - raw values equal to the **9999.0 sentinel** and arid months are masked out
     of raw means/maxima; score means use non-arid months only.
   - annual mean/max, summer (Jun–Aug) mean, and the same for the `bwd`/`iav`
     families.
2. **Facility join ladder**, recorded in `merge_method`:
   - `hydrobasins_pip` — point-in-polygon into a level-6 basin (na + ar
     regions); boundary points hitting >1 basin are resolved deterministically
     to the larger `SUB_AREA`.
   - `hydrobasins_nearest_10km` — nearest basin within 10 km
     (`basin_match_dist_km` records the distance).
   - `basin_no_aqueduct_data` — basin polygon exists but Aqueduct has no row
     for its `pfaf_id` (~42 basins globally) → "No Data".
   - `unmatched` — no basin within 10 km → "No Data".
   There is deliberately **no state-level fallback rung**: an honest "No Data"
   beats a fabricated statewide number.

### Canonical water-stress vocabulary

| `bws_category` | `bws_label` | Score bin | Color |
|---|---|---|---|
| Low | Low (<10%) | [0, 1) | `#2ca02c` |
| Low-Medium | Low-Medium (10-20%) | [1, 2) | `#7dab4a` |
| Medium-High | Medium-High (20-40%) | [2, 3) | `#dfa813` |
| High | High (40-80%) | [3, 4) | `#e36c09` |
| Extremely High | Extremely High (>80%) | [4, 5] | `#c00000` |
| Arid | Arid and Low Water Use | `cat == -1`, not score | `#9e9e9e` |
| No Data | No Data | unmatched/masked | `#d9d9d9` |

Raw WRI label spellings (`"Low - Medium (10-20%)"`, `"Extremely high (>80%)"`)
are normalized onto this vocabulary at the pipeline boundary
(`normalize_wri_label`). **Literal-sync list** — these files repeat the
vocabulary/colors and must change together:
`code/preprocessing.py` (`CATEGORY_TO_LABEL`), `code/generate_charts.py`
(`ws_order`/`ws_colors`), `code/export_web_data.py`
(`CATEGORY_*` constants → `web-data/meta.json`, which the front-end reads
instead of hard-coding).

## Capacity (MW) from FracTracker

The FracTracker snapshot is filtered to built-or-committed facilities
(status contains operating / expanding / approved / permitted / under
construction — proposed, cancelled, and suspended rows are excluded so a paper
project can't match a real building). Facilities match one-to-one to the
nearest FracTracker point within **500 m** (greedy by distance).
`qa_operator_mismatch` flags matches whose normalized operator/tenant name
tokens share nothing with the IM3 operator/name — **report-only**, it never
rejects a match (colo operator vs tenant naming differs legitimately).
**No imputation**: facilities without a match keep `mw_capacity = NaN`, and
coverage is reported honestly in `qa_report.md` and in every summary's
`mw_coverage_pct`.

**Licensing split.** FracTracker's terms are non-commercial with mandatory
credit; ODbL (which covers the master outputs) is share-alike and cannot
absorb non-commercial content. The five FracTracker-derived facility columns
(`mw_capacity`, `mw_source`, `match_dist_m`, `ft_status`,
`qa_operator_mismatch`) are therefore written **only** to
`data/derived-data/fractracker_match.csv` (matched rows, keyed by facility
`id`; citation: *"Data provided by FracTracker Alliance (2026)"*) and are
excluded from `datacenters_master.csv` and `web-data/facilities.geojson` —
the web export fails validation if they leak. Aggregate MW statistics in the
summaries (MW-weighted rates, `mw_coverage_pct`, per-subregion MW totals) are
produced-work statistics computed from the sidecar and published with the
same citation.

## Aggregation and weighting

County/state summaries report, side by side:
- unweighted facility means (comparable to the original pipeline),
- **sqft-weighted CO₂ rates** (primary in the writeup — a 2M sqft hyperscale
  campus should not count the same as a 5,000 sqft colo),
- MW-weighted rates only where the group's MW coverage ≥ 40% (else NaN),
- `sqft_coverage_pct` / `mw_coverage_pct` so readers can judge the weights.

## Dual-risk definition

A facility is dual-risk iff its subregion CO₂ rate exceeds **700 lb/MWh** and
its basin water-stress category is High or Extremely High. The 700 threshold is
inherited from the original analysis and is not yet sensitivity-tested — a
known limitation for Phase 1.

## Known limitations

- **Location, not consumption.** The pipeline characterizes *where* facilities
  sit, not how much energy/water they draw. Consumption modeling
  (MW × load factor × PUE/WUE distributions) is Phase 1 scope.
- **Puerto Rico** falls in one coarse level-6 basin; treat PR water values as
  indicative only.
- **Hawaii** is not covered by HydroBASINS na/ar — moot today (no HI
  facilities in the atlas), documented in case future atlas versions add them.
- **MW coverage is low** (~6% of facilities after conservative matching) —
  FracTracker itself knows MW for only ~37% of tracked facilities. MW-weighted
  metrics are supplementary, never primary.
- **Annual-average carbon intensity** (eGRID `SRCO2RTA`) is attributional; it
  ignores hourly variation, marginal effects, and corporate PPAs. A
  three-signal carbon panel is Phase 1 scope.
- **FracTracker is a rolling, crowdsourced dataset** with uneven completeness;
  one known date typo (year 3036) is clamped in QA. The dated snapshot in
  `data/raw-data/` is the reproducibility anchor.

## Citations

- Lehner, B., Grill, G. (2013). Global river hydrography and network routing:
  baseline data and new approaches to study the world's large river systems.
  *Hydrological Processes*, 27(15), 2171–2186. (HydroBASINS)
- Kuzma, S., et al. (2023). *Aqueduct 4.0: Updated Decision-Relevant Global
  Water Risk Indicators.* World Resources Institute.
- US EPA. *Emissions & Generation Resource Integrated Database (eGRID) 2023*,
  rev2, June 2025.
- IM3/PNNL. *Open Source Data Center Atlas.* MSD-LIVE, v2026.02.09.
  DOI 10.57931/3017294.
- FracTracker Alliance. *U.S. Data Centers Tracker.* fractracker.org/data-centers
  (snapshot date in data/manifest.json).

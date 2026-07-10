# AI Data Center Sustainability Analysis

**Spatial analysis of U.S. AI data center locations, grid carbon intensity, and regional water stress to inform sustainable siting decisions.**

> Individual professional-grade revamp (2026) by **Manav Mutneja** (`manavm-afk`), extending a
> UChicago Harris DAP II (30538) group project with Ankit Dixit. Phase 0 replaced every
> untraceable assignment in the original pipeline with documented spatial joins —
> see [METHODS.md](METHODS.md) and the before/after in
> [data/derived-data/qa_report.md](data/derived-data/qa_report.md).

## Research Question

How do the locations of AI/cloud data centers in the United States relate to local carbon
intensity of the electricity grid and regional water stress — and what are the policy
implications for sustainable data center siting?

### Sub-Questions
1. Which U.S. counties have the highest concentration of data centers, and how carbon-intensive is their local electricity grid?
2. Are data centers disproportionately located in water-stressed regions?
3. Under projected growth scenarios, how might future data center siting exacerbate or alleviate grid carbon and water stress?

## Key Findings (recomputed 2026-07-10 — corrected spatial joins)

- **1,474 unique data centers** across 47 states/territories, led by Virginia (319), Texas (127), and California (112)
- The **sqft-weighted** mean grid CO₂ rate at data center locations is **786 lb/MWh** — 12% *above* the unweighted mean (704 lb/MWh), because larger facilities disproportionately sit on dirtier grids
- **511 facilities (34.7%)** sit in High or Extremely High water-stress catchments (WRI Aqueduct 4.0, HydroBASINS level-6). The state-level shortcut in the original analysis undercounted this (393): it missed genuinely stressed basins in nominally "wet" states — **Virginia is now the #1 high-stress state (97 facilities)** — while overstating others (Santa Clara County's basin is Low-Medium, not "Extremely High")
- **284 facilities face dual environmental risk**: grid CO₂ above 700 lb/MWh *and* a High/Extremely-High-stress basin — led by TX (76), AZ (65), IL (48), CO (20), WY (18)
- Under business-as-usual projections, Extremely-High-stress North American catchments grow **+7.4% by 2080** (257 → 276), reinforcing the case for water-conscious siting
- Grid assignment matters: the original nearest-power-plant proxy would mis-assign **16 facilities (1.1%)** to the wrong eGRID subregion

Full provenance for every number: [data/derived-data/qa_report.md](data/derived-data/qa_report.md).

## Front-end

The former Streamlit dashboard is retired. A custom web dashboard (Vercel/Replit) is the
next workstream; it consumes the front-end-agnostic JSON layer in `web-data/`
(facilities GeoJSON, summaries, scenario projections, and `meta.json` with dataset
versions, canonical labels, and color tokens).

## Setup

```bash
# Option A: Conda
conda env create -f environment.yml
conda activate dc_sustainability

# Option B: pip (use a venv OUTSIDE iCloud-synced folders)
pip install -r requirements.txt
```

## Project Structure

```
├── README.md
├── METHODS.md                     # data sources, joins, masking rules, limitations
├── Final_Project_Summary.qmd      # analysis writeup (Quarto)
├── requirements.txt / environment.yml
├── code/
│   ├── download_data.py           # downloads raw data; --check-updates / --update
│   ├── preprocessing.py           # pipeline: spatial joins, QA report
│   ├── generate_charts.py         # static figures (6 PNGs)
│   └── export_web_data.py         # web-data/ JSON layer for the front-end
├── data/
│   ├── manifest.json              # pinned dataset versions + version checks
│   ├── raw-data/                  # pinned snapshots (+ gitignored shapefiles/)
│   └── derived-data/              # pipeline outputs incl. qa_report.md
├── web-data/                      # front-end data layer (GeoJSON + JSON)
└── output_charts/                 # static figures
```

## Data Sources

| Dataset | Source | Granularity | Version pinned |
|---------|--------|-------------|----------------|
| [IM3 Open Source Data Center Atlas](https://data.msdlive.org/records/65g71-a4731/latest) | PNNL/DOE | Facility (lat/lon, county, sqft) | v2026.02.09 |
| [EPA eGRID 2023](https://www.epa.gov/egrid/detailed-data) | US EPA | Plant, subregion, state | rev2 (June 2025) |
| [eGRID2023 subregion shapefiles](https://www.epa.gov/egrid/egrid-mapping-files) | US EPA | Subregion polygons | Jan 2025 |
| [WRI Aqueduct 4.0](https://www.wri.org/data/aqueduct-global-maps-40-data) | WRI | HydroBASINS level-6 sub-basin | y2023m07d05 |
| [HydroBASINS level-6](https://www.hydrosheds.org/products/hydrobasins) | HydroSHEDS | Basin polygons (PFAF_ID) | v1c (compat-pinned) |
| [FracTracker US Data Centers Tracker](https://www.fractracker.org/data-centers/) | FracTracker Alliance | Facility MW, status | dated snapshot |

Versions, licenses, citations, and programmatic update checks are pinned in
[data/manifest.json](data/manifest.json). Check for newer data any time:

```bash
python code/download_data.py --check-updates   # poll publishers; exit 1 if updates exist
python code/download_data.py --update <key>    # explicit refresh + manifest stamp
```

### Data Processing (see METHODS.md for full detail)

`code/preprocessing.py`:
- Deduplicates the IM3 atlas (1,479 records → 1,474 facilities) and builds county FIPS
- Assigns each facility an eGRID subregion by **point-in-polygon** against EPA's official
  boundaries, with an explicit fallback ladder recorded per facility
  (`egrid_assignment_method`); nearest-plant distance retained as a QA field only
- Assigns water stress by **point-in-polygon into HydroBASINS level-6 basins**, joining
  WRI Aqueduct 4.0 on `pfaf_id` (100% match) — masking Aqueduct's 9999 sentinels and
  handling arid basins (`cat == -1`) explicitly (`merge_method` per facility)
- Attaches MW capacity from the FracTracker snapshot (conservative ≤500 m one-to-one
  match; no imputation; coverage reported honestly)
- Emits county/state summaries with **both unweighted and sqft-weighted** CO₂ rates,
  plus a QA report with before/after numbers, match rates, spot checks, and invariants

## Usage

```bash
python code/download_data.py       # 1. fetch raw data (~90 MB + pinned snapshots)
python code/preprocessing.py       # 2. rebuild derived data + qa_report.md
python code/generate_charts.py     # 3. regenerate the 6 static figures
python code/export_web_data.py     # 4. refresh the web-data/ JSON layer
quarto render Final_Project_Summary.qmd   # 5. re-render the writeup
```

## License

MIT (code). Data licenses per source — see [METHODS.md](METHODS.md); FracTracker data is
non-commercial with credit; IM3 atlas is ODbL; HydroBASINS requires attribution
(Lehner & Grill 2013).

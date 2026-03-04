# AI Data Center Sustainability Analysis

**Spatial analysis of U.S. AI data center locations, grid carbon intensity, and regional water stress to evaluate sustainable siting policy.**

> UChicago Harris School — DAP II (30538) Final Project, Winter 2026

## Research Question

How do the locations of AI/cloud data centers in the United States relate to local carbon intensity of the electricity grid and regional water stress — and what are the policy implications for sustainable data center siting?

### Sub-Questions
1. Which U.S. counties have the highest concentration of data centers, and how carbon-intensive is their local electricity grid?
2. Are data centers disproportionately located in water-stressed regions?
3. Under projected growth scenarios, how might future data center siting exacerbate or alleviate grid carbon and water stress?

## Streamlit Dashboard

🔗 **[Live Dashboard](https://ai-datacenter-sustainability.streamlit.app)**

> **Note:** The Streamlit Community Cloud app may take 30–60 seconds to wake up if it has been idle. Please be patient on the first load.

The interactive dashboard allows users to:
- Explore a map of data center locations colored by grid carbon intensity or water stress
- Compare states by carbon intensity vs. data center concentration
- View future water stress projections under BAU, Optimistic, and Pessimistic scenarios (2030–2080)
- Filter by state, CO₂ rate range, and water stress category

## Setup

```bash
# Option A: Conda (recommended)
conda env create -f environment.yml
conda activate dc_sustainability

# Option B: pip
pip install -r requirements.txt
```

## Project Structure

```
├── README.md
├── requirements.txt
├── environment.yml
├── .gitignore
├── final_project.qmd          # Writeup (Quarto)
├── final_project.html          # Knitted HTML
├── final_project.pdf           # Knitted PDF
├── code/
│   └── preprocessing.py        # Data wrangling & merging
├── data/
│   ├── raw-data/
│   │   ├── im3_open_source_data_center_atlas_v2026_02_09.csv
│   │   ├── egrid2023_data_rev2.xlsx
│   │   ├── Aqueduct40_baseline_monthly_y2023m07d05.csv
│   │   └── Aqueduct40_future_annual_y2023m07d05.csv
│   └── derived-data/
│       ├── datacenters_with_emissions.csv
│       ├── datacenters_with_water_stress.csv
│       ├── datacenters_master.csv
│       ├── county_summary.csv
│       ├── state_summary.csv
│       ├── aqueduct_annual_summary.csv
│       └── aqueduct_future_water_stress_na.csv
└── streamlit-app/
    ├── app.py
    ├── requirements.txt
    └── data/                   # Derived data for deployment
```

## Data Sources

| Dataset | Source | Format | Granularity |
|---------|--------|--------|-------------|
| [IM3 Open Source Data Center Atlas](https://data.msdlive.org/records/65g71-a4731) | Pacific Northwest National Laboratory (PNNL/DOE) | CSV | Individual facility (lat/lon, county, sqft) |
| [EPA eGRID 2023](https://www.epa.gov/egrid/detailed-data) | U.S. Environmental Protection Agency | XLSX | Plant, subregion, and state level |
| [WRI Aqueduct 4.0](https://www.wri.org/applications/aqueduct/water-risk-atlas/) | World Resources Institute | CSV | HydroSHEDS catchment level |

### Data Processing

1. **`code/preprocessing.py`** reads from `data/raw-data/` and writes to `data/derived-data/`:
   - Loads the IM3 data center atlas (1,479 facilities across 47 states)
   - Loads eGRID 2023 plant-level data and assigns each data center to the eGRID subregion of its nearest power plant (spatial KD-tree join)
   - Merges subregion-level CO₂ emission rates onto each data center
   - Computes annual water stress averages from Aqueduct 4.0 monthly baseline data
   - Merges water stress indicators via state-level aggregation
   - Produces future water stress projections for North American catchments

2. To regenerate derived data:
   ```bash
   python code/preprocessing.py
   ```

### Downloading Raw Data

All raw datasets are included in this repository (each file < 100MB). If you need to re-download:

- **IM3 Atlas:** https://data.msdlive.org/records/65g71-a4731
- **eGRID 2023:** https://www.epa.gov/egrid/detailed-data → "eGRID2023 Data File (XLSX)"
- **Aqueduct 4.0:** https://www.wri.org/applications/aqueduct/water-risk-atlas/ → Download baseline monthly and future annual CSVs

Save files to `data/raw-data/` with the exact filenames shown in the project structure above.

## Usage

1. Run preprocessing to generate derived datasets:
   ```bash
   python code/preprocessing.py
   ```

2. Launch the Streamlit dashboard locally:
   ```bash
   streamlit run streamlit-app/app.py
   ```

3. Knit the writeup:
   ```bash
   quarto render final_project.qmd
   ```

## Key Findings

- **1,479 data centers** across 47 states, with Virginia (319), Texas (127), and California (112) leading
- The average grid CO₂ rate at data center locations is **705 lb/MWh** — 19% below the national subregion average, suggesting some preference for cleaner grids
- **~27% of data centers** are located in high or extremely high water stress areas (California, Texas, Arizona, Nevada)
- Under business-as-usual projections, the share of high-stress catchments in North America increases through 2080, intensifying the urgency for water-conscious siting

## License

MIT

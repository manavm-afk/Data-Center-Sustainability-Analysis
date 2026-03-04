# AI Data Center Sustainability Analysis

**Spatial analysis of U.S. AI data center locations, grid carbon intensity, and regional water stress to evaluate sustainable siting policy.**

> UChicago Harris School — DAP II (30538) Final Project, Winter 2026
>
> **Authors:** Manav Mutneja (`manavm-afk`) · Ankit Dixit (`ankitdixit23`)

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
├── final_project.qmd              # Writeup (Quarto, ≤3 pages)
├── final_project_analysis.qmd     # Detailed analysis (Quarto)
├── final_project.html              # Knitted HTML
├── final_project.pdf               # Knitted PDF
├── code/
│   ├── download_data.py            # Downloads raw datasets (~77 MB)
│   ├── preprocessing.py            # Data wrangling & merging
│   └── generate_charts.py          # Static visualizations (6 PNGs)
├── data/
│   ├── raw-data/
│   │   ├── im3_open_source_data_center_atlas_v2026.02.09.csv
│   │   ├── egrid2023_data_rev2.xlsx
│   │   ├── Aqueduct40_baseline_monthly_y2023m07d05.csv
│   │   └── Aqueduct40_future_annual_y2023m07d05.csv
│   └── derived-data/
│       ├── datacenters_master.csv
│       ├── datacenters_with_emissions.csv
│       ├── datacenters_with_water_stress.csv
│       ├── county_summary.csv
│       ├── state_summary.csv
│       ├── aqueduct_annual_summary.csv
│       ├── aqueduct_future_water_stress_na.csv
│       └── water_stress_county_summary.csv
├── output_charts/
│   ├── fig1_top_states.png
│   ├── fig2a_us_map_states.png
│   ├── fig2b_us_map_counties.png
│   ├── fig3_egrid_subregions.png
│   ├── fig4_water_stress.png
│   └── fig5_dual_risk_scatter.png
└── streamlit-app/
    ├── app.py
    ├── requirements.txt
    ├── datacenters_master.csv
    ├── state_summary.csv
    ├── county_summary.csv
    ├── datacenters_with_water_stress.csv
    └── aqueduct_future_water_stress_na.csv
```

## Data Sources

| Dataset | Source | Format | Granularity |
|---------|--------|--------|-------------|
| [IM3 Open Source Data Center Atlas](https://data.msdlive.org/records/65g71-a4731) | Pacific Northwest National Laboratory (PNNL/DOE) | CSV | Individual facility (lat/lon, county, sqft) |
| [EPA eGRID 2023](https://www.epa.gov/egrid/detailed-data) | U.S. Environmental Protection Agency | XLSX | Plant, subregion, and state level |
| [WRI Aqueduct 4.0](https://www.wri.org/applications/aqueduct/water-risk-atlas/) | World Resources Institute | CSV | HydroSHEDS catchment level |

### Data Processing

`code/preprocessing.py` reads from `data/raw-data/` and writes to `data/derived-data/`:
- Loads the IM3 data center atlas (1,479 facilities across 47 states)
- Loads eGRID 2023 plant-level data and assigns each data center to the eGRID subregion of its nearest power plant (spatial KD-tree join)
- Merges subregion-level CO₂ emission rates onto each data center
- Computes annual water stress averages from Aqueduct 4.0 monthly baseline data
- Merges water stress indicators via state-level aggregation
- Produces future water stress projections for North American catchments

### Downloading Raw Data

All raw datasets are included in this repository (each file < 100 MB). To re-download from source:

```bash
python code/download_data.py          # downloads all 4 datasets (~77 MB)
python code/download_data.py --force  # re-download existing files
```

Or manually:
- **IM3 Atlas:** https://data.msdlive.org/records/65g71-a4731
- **eGRID 2023:** https://www.epa.gov/egrid/detailed-data → "eGRID2023 Data File (XLSX)"
- **Aqueduct 4.0:** https://www.wri.org/applications/aqueduct/water-risk-atlas/ → Baseline monthly and future annual CSVs

Save files to `data/raw-data/` with the exact filenames shown in the project structure above.

## Usage

1. Download raw data (if not already present):
   ```bash
   python code/download_data.py
   ```

2. Run preprocessing to generate derived datasets:
   ```bash
   python code/preprocessing.py
   ```

3. Generate static charts:
   ```bash
   python code/generate_charts.py
   ```

4. Launch the Streamlit dashboard locally:
   ```bash
   streamlit run streamlit-app/app.py
   ```

5. Knit the writeup:
   ```bash
   quarto render final_project.qmd
   ```

## Key Findings

- **1,474 unique data centers** across 47 states, with Virginia (319), Texas (127), and California (112) leading
- The average grid CO₂ rate at data center locations is **705 lb/MWh** — 19% below the national subregion average, suggesting some preference for cleaner grids
- **~27% of data centers** are located in high or extremely high water stress areas (California, Texas, Arizona, Nevada)
- **~250 data centers** face dual environmental risk: high grid carbon intensity (>700 lb/MWh) AND high water stress
- Under business-as-usual projections, the share of high-stress catchments in North America increases through 2080, intensifying the urgency for water-conscious siting

## License

MIT

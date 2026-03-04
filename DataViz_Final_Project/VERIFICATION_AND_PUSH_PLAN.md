# Final Project Verification & Git Push Plan

## 1. Git Push Plan (Step-by-Step)

### Step 1: Clone the existing repo and set up structure

```bash
# Clone your existing repo
git clone https://github.com/ankitdixit23/AI-datacenter-sustainability-analysis.git
cd AI-datacenter-sustainability-analysis

# Create a feature branch for data wrangling
git checkout -b data-wrangling
```

### Step 2: Copy the repo files into your local clone

Copy all files from the provided repo structure into your cloned directory:

```
AI-datacenter-sustainability-analysis/
├── .gitignore              (replace existing)
├── README.md               (replace existing)
├── environment.yml         (new)
├── requirements.txt        (new)
├── final_project.qmd       (new — EDIT with your names/section)
├── code/
│   └── preprocessing.py    (new)
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
│       ├── aqueduct_future_water_stress_na.csv
│       └── water_stress_county_summary.csv
└── streamlit-app/
    ├── app.py
    ├── requirements.txt
    └── data/
        ├── datacenters_master.csv
        ├── state_summary.csv
        ├── county_summary.csv
        └── aqueduct_future_water_stress_na.csv
```

### Step 3: Commit data wrangling work

```bash
git add code/preprocessing.py
git add data/raw-data/
git add data/derived-data/
git commit -m "Add preprocessing pipeline and raw/derived datasets

- code/preprocessing.py: merges IM3 atlas with eGRID emissions and Aqueduct water stress
- data/raw-data/: IM3 atlas, eGRID 2023, Aqueduct 4.0 baseline + future
- data/derived-data/: 8 derived CSVs with facility-level and summary data"

git push origin data-wrangling
```

### Step 4: Create Streamlit branch and add dashboard

```bash
git checkout main
git merge data-wrangling
git checkout -b streamlit-app

git add streamlit-app/
git commit -m "Add Streamlit dashboard for interactive sustainability exploration

- streamlit-app/app.py: 3-tab dashboard (Map, State Comparisons, SQ3 Projections)
- streamlit-app/data/: derived data for deployment
- streamlit-app/requirements.txt: deployment dependencies"

git push origin streamlit-app
```

### Step 5: Deploy to Streamlit Community Cloud

1. Go to https://share.streamlit.io/
2. Sign in with your GitHub account
3. Click "New app"
4. Select repo: `ankitdixit23/AI-datacenter-sustainability-analysis`
5. Branch: `main` (merge streamlit-app first)
6. Main file path: `streamlit-app/app.py`
7. Click "Deploy"
8. **Update README.md** with the actual Streamlit URL once deployed

### Step 6: Create writeup branch

```bash
git checkout main
git merge streamlit-app
git checkout -b writeup

# EDIT final_project.qmd with:
#   - Your actual names, section day/time, GitHub usernames
#   - Any additional analysis or interpretation
#   - Streamlit dashboard URL

# Knit to HTML and PDF:
quarto render final_project.qmd --to html
quarto render final_project.qmd --to pdf

git add final_project.qmd final_project.html final_project.pdf
git add README.md environment.yml requirements.txt .gitignore
git commit -m "Add project writeup, requirements, and documentation"
git push origin writeup
```

### Step 7: Final merge to main

```bash
git checkout main
git merge writeup
git push origin main

# Clean up branches (optional — keep for grading evidence)
# git branch -d data-wrangling streamlit-app writeup
```

---

## 2. File Verification Results

### Raw Data (data/raw-data/)
| File | Rows | Size | Status |
|------|------|------|--------|
| im3_open_source_data_center_atlas_v2026_02_09.csv | 1,479 | 185K | ✅ OK |
| egrid2023_data_rev2.xlsx | Multi-sheet | 21M | ✅ OK |
| Aqueduct40_baseline_monthly_y2023m07d05.csv | 15,834 | 28M | ✅ OK |
| Aqueduct40_future_annual_y2023m07d05.csv | 16,395 | 28M | ✅ OK |

### Derived Data (data/derived-data/)
| File | Rows | Description | Status |
|------|------|-------------|--------|
| datacenters_with_emissions.csv | 1,474 | Facility + eGRID subregion CO2 rates | ✅ OK |
| datacenters_with_water_stress.csv | 1,479 | Facility + water stress scores | ✅ OK |
| datacenters_master.csv | 1,474 | Combined emissions + water stress | ✅ OK |
| county_summary.csv | 251 | County-level aggregation | ✅ OK |
| state_summary.csv | 47 | State-level aggregation | ✅ OK |
| aqueduct_annual_summary.csv | 15,834 | Annual averages from monthly data | ✅ OK |
| aqueduct_future_water_stress_na.csv | 2,890 | N. America future projections | ✅ OK |
| water_stress_county_summary.csv | 251 | County water stress summary | ✅ OK |

### Code Files
| File | Lines | Status |
|------|-------|--------|
| code/preprocessing.py | ~200 | ✅ Runs successfully |
| streamlit-app/app.py | ~300 | ✅ Syntax valid, data loads OK |

---

## 3. Requirements Checklist

### Coding (45%)
| Requirement | Status | Notes |
|-------------|--------|-------|
| ≥2 datasets | ✅ | 3 datasets (IM3, eGRID, Aqueduct) |
| All processing in .qmd or preprocessing.py | ✅ | code/preprocessing.py |
| ≥2 static plots (Altair or GeoPandas) | ✅ | Choropleth map + scatter plot in .qmd |
| ≥1 Streamlit app with dynamic component | ✅ | 3-tab dashboard with filters/selectors |
| ≥1 spatial visualization | ✅ | Map with albersUsa projection |
| Git branches for different features | ⚠️ | Follow push plan for 3+ branches |
| Reproducible (.qmd knits) | ⚠️ | Need to test knitting locally |

### Writeup (15%)
| Requirement | Status | Notes |
|-------------|--------|-------|
| final_project.qmd exists | ✅ | Template created |
| ≤ 3 pages | ✅ | ~2.5 pages as written |
| Names, section, GitHub usernames | ⚠️ | EDIT: Fill in your details |
| Research question described | ✅ | |
| Data sources and approach | ✅ | |
| Static plots displayed and interpreted | ✅ | |
| Streamlit app described | ✅ | |
| Policy implications (data-supported) | ✅ | |
| Weaknesses discussed | ✅ | |

### Repository Structure
| Requirement | Status | Notes |
|-------------|--------|-------|
| README.md with Streamlit link | ✅ | UPDATE URL after deployment |
| requirements.txt or environment.yml | ✅ | Both provided |
| .gitignore | ✅ | Ignores venv, __pycache__, etc. |
| data/raw-data/ | ✅ | 4 files, all < 100MB |
| data/derived-data/ | ✅ | 8 derived CSV files |
| streamlit-app/ with app.py | ✅ | + requirements.txt + data/ |
| Matches template repo structure | ✅ | code/ and data/ directories |
| final_project.html | ⚠️ | Knit locally with Quarto |
| final_project.pdf | ⚠️ | Knit locally with Quarto |

---

## 4. Streamlit Dashboard — SQ3 Verification

The Streamlit app has **3 tabs** addressing all sub-questions:

1. **Tab 1 — Map: Carbon & Water Risk** (SQ1 + SQ2)
   - Interactive map with Altair albersUsa projection
   - Toggle between CO₂ rate and water stress color encoding
   - Size encoding: uniform, sqft, or CO₂ rate
   - Full tooltip with facility name, operator, state, county, sqft, CO₂ rate, subregion, water stress

2. **Tab 2 — State Comparisons** (SQ1 + SQ2)
   - Scatter plot: mean CO₂ rate vs. data center count/sqft by state
   - State labels on points
   - Adjustable bar chart of top N states

3. **Tab 3 — SQ3: Future Projections** ← KEY FOR SQ3
   - Scenario selector: BAU, Optimistic, Pessimistic
   - Time horizon selector: 2030, 2050, 2080
   - Bar chart: future water stress distribution by category
   - Line chart: % high-stress catchments across scenarios and years
   - Policy implications summary with dynamic statistics

**Dynamic components (required):** sidebar filters (multiselect, slider), radio buttons, selectbox, slider — all update charts in real time.

---

## 5. Action Items Before Submission

1. **EDIT `final_project.qmd`**: Fill in names, section day/time, GitHub usernames
2. **KNIT**: Run `quarto render final_project.qmd` locally to generate HTML + PDF
3. **PUSH**: Follow the Git push plan (Steps 1–7) to create proper branch history
4. **DEPLOY STREAMLIT**: Deploy to Streamlit Community Cloud (Step 5)
5. **UPDATE README**: Replace placeholder Streamlit URL with actual deployment URL
6. **TEST REPRODUCIBILITY**: Have your partner (or an AI agent) clone the repo, install deps, and run `python code/preprocessing.py` to verify

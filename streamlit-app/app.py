"""
app.py — AI Data Center Sustainability Explorer
=================================================
Interactive Streamlit dashboard for the 30538 Final Project.

Sub-Questions:
  SQ1: Data center concentration & grid carbon intensity
  SQ2: Data centers in water-stressed regions
  SQ3: Future water stress projections under growth scenarios

Data files (in same directory):
  datacenters_master.csv
  state_summary.csv
  county_summary.csv
  datacenters_with_water_stress.csv
  aqueduct_future_water_stress_na.csv
"""

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Data Center Sustainability Explorer",
    page_icon="🌍",
    layout="wide",
)

DATA_DIR = Path(__file__).parent


# ══════════════════════════════════════════════════════════════════════════
# DATA LOADING (cached)
# ══════════════════════════════════════════════════════════════════════════

@st.cache_data
def load_master():
    df = pd.read_csv(DATA_DIR / "datacenters_master.csv")
    # Friendly column names for display
    df["co2_rate"] = df["SRCO2RTA"]
    df["renewable_pct"] = df["SRTRPR"] * 100  # convert 0-1 → 0-100
    df["water_stress_score"] = df["bws_annual_mean_score"]
    df["water_stress_label"] = df["bws_annual_label"]
    return df


@st.cache_data
def load_state_summary():
    return pd.read_csv(DATA_DIR / "state_summary.csv")


@st.cache_data
def load_county_summary():
    return pd.read_csv(DATA_DIR / "county_summary.csv")


@st.cache_data
def load_water_detail():
    return pd.read_csv(DATA_DIR / "datacenters_with_water_stress.csv")


@st.cache_data
def load_future_water():
    return pd.read_csv(DATA_DIR / "aqueduct_future_water_stress_na.csv")


# ══════════════════════════════════════════════════════════════════════════
# SIDEBAR NAVIGATION
# ══════════════════════════════════════════════════════════════════════════

page_names = {
    "🏠 Overview": "overview",
    "⚡ SQ1: Carbon Intensity": "sq1",
    "💧 SQ2: Water Stress": "sq2",
    "🔮 SQ3: Future Projections": "sq3",
}

st.sidebar.title("🌍 Data Center Explorer")
st.sidebar.markdown("---")
selected_page = st.sidebar.selectbox(
    "Navigate to:", list(page_names.keys())
)

# ══════════════════════════════════════════════════════════════════════════
# PAGE: OVERVIEW
# ══════════════════════════════════════════════════════════════════════════

def page_overview():
    st.title("The Environmental Footprint of AI Infrastructure")
    st.markdown(
        """
        **How do U.S. data center locations relate to grid carbon intensity
        and regional water stress — and what are the policy implications
        for sustainable siting?**
        """
    )

    master = load_master()
    state_df = load_state_summary()

    # ── KPI row ──────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Data Centers", f"{len(master):,}")
    c2.metric("States Covered", f"{master['state_abb'].nunique()}")
    c3.metric(
        "Avg CO₂ Rate",
        f"{master['co2_rate'].mean():.0f} lb/MWh",
    )
    ws_high = master["water_stress_label"].isin(
        ["High (40-80%)", "Extremely High (>80%)"]
    ).sum()
    c4.metric("In High Water Stress", f"{ws_high:,} ({100*ws_high/len(master):.0f}%)")

    st.markdown("---")

    # ── National map: all data centers ───────────────────────────────────
    st.subheader("National Map of U.S. Data Centers")

    # Color by carbon intensity
    color_by = st.radio(
        "Color data centers by:",
        ["Carbon Intensity (CO₂ lb/MWh)", "Water Stress Score"],
        horizontal=True,
    )

    color_field = "co2_rate" if "Carbon" in color_by else "water_stress_score"
    color_title = "CO₂ (lb/MWh)" if "Carbon" in color_by else "Water Stress Score"
    color_scheme = "reds" if "Carbon" in color_by else "blues"

    # US states background
    states_url = "https://cdn.jsdelivr.net/npm/vega-datasets@v1.29.0/data/us-10m.json"
    background = (
        alt.Chart(alt.topo_feature(states_url, "states"))
        .mark_geoshape(fill="lightgray", stroke="white", strokeWidth=0.5)
        .project("albersUsa")
        .properties(width=900, height=500)
    )

    points = (
        alt.Chart(master)
        .mark_circle(opacity=0.6)
        .encode(
            longitude="lon:Q",
            latitude="lat:Q",
            size=alt.Size(
                "sqft:Q",
                scale=alt.Scale(range=[10, 300]),
                title="Facility Sq Ft",
            ),
            color=alt.Color(
                f"{color_field}:Q",
                scale=alt.Scale(scheme=color_scheme),
                title=color_title,
            ),
            tooltip=[
                alt.Tooltip("name:N", title="Facility"),
                alt.Tooltip("operator:N", title="Operator"),
                alt.Tooltip("state:N", title="State"),
                alt.Tooltip("county:N", title="County"),
                alt.Tooltip("co2_rate:Q", title="CO₂ (lb/MWh)", format=".0f"),
                alt.Tooltip("water_stress_score:Q", title="Water Stress Score", format=".1f"),
                alt.Tooltip("sqft:Q", title="Sq Ft", format=",.0f"),
            ],
        )
        .project("albersUsa")
    )

    st.altair_chart(background + points, use_container_width=True)

    # ── Top-10 states bar chart ──────────────────────────────────────────
    st.subheader("Top 10 States by Data Center Count")
    top10 = state_df.nlargest(10, "dc_count")
    bar = (
        alt.Chart(top10)
        .mark_bar()
        .encode(
            x=alt.X("dc_count:Q", title="Number of Data Centers"),
            y=alt.Y("state_abb:N", sort="-x", title="State"),
            color=alt.Color(
                "mean_co2_rate:Q",
                scale=alt.Scale(scheme="reds"),
                title="Avg CO₂ Rate",
            ),
            tooltip=[
                alt.Tooltip("state:N"),
                alt.Tooltip("dc_count:Q", title="Data Centers"),
                alt.Tooltip("mean_co2_rate:Q", title="Avg CO₂ Rate", format=".0f"),
                alt.Tooltip("state_renewable_pct:Q", title="Renewable %", format=".1f"),
            ],
        )
        .properties(height=350)
    )
    st.altair_chart(bar, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════
# PAGE: SQ1 — CARBON INTENSITY
# ══════════════════════════════════════════════════════════════════════════

def page_sq1():
    st.title("⚡ SQ1: Data Center Concentration & Grid Carbon Intensity")
    st.markdown(
        """
        *Which U.S. counties have the highest concentration of data centers,
        and how carbon-intensive is their local electricity grid?*
        """
    )

    master = load_master()
    county_df = load_county_summary()

    # ── Sidebar filters ──────────────────────────────────────────────────
    st.sidebar.markdown("### SQ1 Filters")

    all_states = sorted(master["state_abb"].dropna().unique())
    selected_states = st.sidebar.multiselect(
        "Filter by state:", all_states, default=[]
    )

    co2_range = st.sidebar.slider(
        "CO₂ emission rate (lb/MWh):",
        min_value=int(master["co2_rate"].min()),
        max_value=int(master["co2_rate"].max()),
        value=(int(master["co2_rate"].min()), int(master["co2_rate"].max())),
    )

    # Apply filters
    filtered = master.copy()
    if selected_states:
        filtered = filtered[filtered["state_abb"].isin(selected_states)]
    filtered = filtered[
        (filtered["co2_rate"] >= co2_range[0])
        & (filtered["co2_rate"] <= co2_range[1])
    ]

    # ── KPIs ─────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    c1.metric("Facilities Shown", f"{len(filtered):,}")
    c2.metric("Avg CO₂ Rate", f"{filtered['co2_rate'].mean():.0f} lb/MWh")
    c3.metric("Avg Renewable %", f"{filtered['renewable_pct'].mean():.1f}%")

    st.markdown("---")

    # ── Map: carbon intensity ────────────────────────────────────────────
    st.subheader("Data Centers Colored by Grid Carbon Intensity")

    states_url = "https://cdn.jsdelivr.net/npm/vega-datasets@v1.29.0/data/us-10m.json"
    bg = (
        alt.Chart(alt.topo_feature(states_url, "states"))
        .mark_geoshape(fill="#f0f0f0", stroke="white", strokeWidth=0.5)
        .project("albersUsa")
        .properties(width=900, height=500)
    )

    pts = (
        alt.Chart(filtered)
        .mark_circle(opacity=0.7)
        .encode(
            longitude="lon:Q",
            latitude="lat:Q",
            size=alt.value(40),
            color=alt.Color(
                "co2_rate:Q",
                scale=alt.Scale(scheme="redyellowgreen", reverse=True),
                title="CO₂ (lb/MWh)",
            ),
            tooltip=[
                alt.Tooltip("name:N", title="Facility"),
                alt.Tooltip("operator:N"),
                alt.Tooltip("state:N"),
                alt.Tooltip("county:N"),
                alt.Tooltip("egrid_subregion:N", title="eGRID Subregion"),
                alt.Tooltip("co2_rate:Q", title="CO₂ (lb/MWh)", format=".0f"),
                alt.Tooltip("renewable_pct:Q", title="Renewable %", format=".1f"),
            ],
        )
        .project("albersUsa")
    )

    st.altair_chart(bg + pts, use_container_width=True)

    # ── Subregion comparison ─────────────────────────────────────────────
    st.subheader("Emission Rates by eGRID Subregion")

    subregion_agg = (
        filtered.groupby(["egrid_subregion", "egrid_subregion_name"])
        .agg(
            dc_count=("id", "count"),
            mean_co2=("co2_rate", "mean"),
            mean_renewable=("renewable_pct", "mean"),
        )
        .reset_index()
        .sort_values("mean_co2", ascending=False)
    )

    bar = (
        alt.Chart(subregion_agg)
        .mark_bar()
        .encode(
            x=alt.X("mean_co2:Q", title="Avg CO₂ Emission Rate (lb/MWh)"),
            y=alt.Y("egrid_subregion:N", sort="-x", title="eGRID Subregion"),
            color=alt.Color(
                "mean_co2:Q",
                scale=alt.Scale(scheme="redyellowgreen", reverse=True),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("egrid_subregion_name:N", title="Subregion Name"),
                alt.Tooltip("dc_count:Q", title="Data Centers"),
                alt.Tooltip("mean_co2:Q", title="Avg CO₂", format=".0f"),
                alt.Tooltip("mean_renewable:Q", title="Avg Renewable %", format=".1f"),
            ],
        )
        .properties(height=500)
    )
    st.altair_chart(bar, use_container_width=True)

    # ── Scatter: CO₂ vs renewable ────────────────────────────────────────
    st.subheader("Carbon Intensity vs. Renewable Share by County")

    county_filtered = county_df.copy()
    if selected_states:
        county_filtered = county_filtered[county_filtered["state_abb"].isin(selected_states)]

    scatter = (
        alt.Chart(county_filtered)
        .mark_circle(opacity=0.6)
        .encode(
            x=alt.X("co2_rate_lb_mwh:Q", title="CO₂ Rate (lb/MWh)"),
            y=alt.Y("renewable_pct:Q", title="Renewable Generation %", scale=alt.Scale(domain=[0, 1])),
            size=alt.Size("dc_count:Q", title="Data Centers", scale=alt.Scale(range=[20, 500])),
            color=alt.Color("state_abb:N", title="State"),
            tooltip=[
                alt.Tooltip("county:N"),
                alt.Tooltip("state_abb:N"),
                alt.Tooltip("dc_count:Q", title="Data Centers"),
                alt.Tooltip("co2_rate_lb_mwh:Q", title="CO₂ Rate", format=".0f"),
                alt.Tooltip("renewable_pct:Q", title="Renewable %", format=".2f"),
            ],
        )
        .properties(width=800, height=450)
    )
    st.altair_chart(scatter, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════
# PAGE: SQ2 — WATER STRESS
# ══════════════════════════════════════════════════════════════════════════

def page_sq2():
    st.title("💧 SQ2: Data Centers in Water-Stressed Regions")
    st.markdown(
        """
        *Are data centers disproportionately located in water-stressed regions?*
        """
    )

    master = load_master()
    water = load_water_detail()

    # ── Sidebar filters ──────────────────────────────────────────────────
    st.sidebar.markdown("### SQ2 Filters")

    stress_categories = [
        "Low (<10%)",
        "Low-Medium (10-20%)",
        "Medium-High (20-40%)",
        "High (40-80%)",
        "Extremely High (>80%)",
    ]
    selected_stress = st.sidebar.multiselect(
        "Water stress level:", stress_categories, default=stress_categories
    )

    all_states = sorted(master["state_abb"].dropna().unique())
    selected_states = st.sidebar.multiselect(
        "Filter by state (SQ2):", all_states, default=[], key="sq2_states"
    )

    # Apply filters
    filtered = master[master["water_stress_label"].isin(selected_stress)].copy()
    if selected_states:
        filtered = filtered[filtered["state_abb"].isin(selected_states)]

    # ── KPIs ─────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Facilities Shown", f"{len(filtered):,}")
    c2.metric("Avg Water Stress Score", f"{filtered['water_stress_score'].mean():.2f}")
    high = filtered["water_stress_label"].isin(["High (40-80%)", "Extremely High (>80%)"]).sum()
    c3.metric("High/Extreme Stress", f"{high:,}")
    c4.metric(
        "% in High Stress",
        f"{100*high/len(filtered):.1f}%" if len(filtered) > 0 else "N/A",
    )

    st.markdown("---")

    # ── Map: water stress ────────────────────────────────────────────────
    st.subheader("Data Centers Colored by Water Stress")

    # Assign numeric for ordered coloring
    stress_order = {
        "Low (<10%)": 0,
        "Low-Medium (10-20%)": 1,
        "Medium-High (20-40%)": 2,
        "High (40-80%)": 3,
        "Extremely High (>80%)": 4,
        "No Data": -1,
        "Arid and Low Water Use": -1,
    }
    filtered["stress_num"] = filtered["water_stress_label"].map(stress_order).fillna(-1)

    states_url = "https://cdn.jsdelivr.net/npm/vega-datasets@v1.29.0/data/us-10m.json"
    bg = (
        alt.Chart(alt.topo_feature(states_url, "states"))
        .mark_geoshape(fill="#f0f0f0", stroke="white", strokeWidth=0.5)
        .project("albersUsa")
        .properties(width=900, height=500)
    )

    pts = (
        alt.Chart(filtered)
        .mark_circle(opacity=0.7)
        .encode(
            longitude="lon:Q",
            latitude="lat:Q",
            size=alt.value(40),
            color=alt.Color(
                "water_stress_label:N",
                scale=alt.Scale(
                    domain=stress_categories,
                    range=["#1a9641", "#a6d96a", "#ffffbf", "#fdae61", "#d7191c"],
                ),
                title="Water Stress Level",
            ),
            tooltip=[
                alt.Tooltip("name:N", title="Facility"),
                alt.Tooltip("operator:N"),
                alt.Tooltip("state:N"),
                alt.Tooltip("county:N"),
                alt.Tooltip("water_stress_score:Q", title="Stress Score", format=".2f"),
                alt.Tooltip("water_stress_label:N", title="Stress Level"),
            ],
        )
        .project("albersUsa")
    )

    st.altair_chart(bg + pts, use_container_width=True)

    # ── Distribution of water stress ─────────────────────────────────────
    st.subheader("Distribution of Data Centers by Water Stress Level")

    stress_counts = (
        master.groupby("water_stress_label")
        .size()
        .reset_index(name="count")
    )
    # Ensure order
    stress_counts["order"] = stress_counts["water_stress_label"].map(stress_order)
    stress_counts = stress_counts.sort_values("order")

    bar = (
        alt.Chart(stress_counts)
        .mark_bar()
        .encode(
            x=alt.X(
                "water_stress_label:N",
                sort=stress_categories,
                title="Water Stress Level",
            ),
            y=alt.Y("count:Q", title="Number of Data Centers"),
            color=alt.Color(
                "water_stress_label:N",
                scale=alt.Scale(
                    domain=stress_categories,
                    range=["#1a9641", "#a6d96a", "#ffffbf", "#fdae61", "#d7191c"],
                ),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip("water_stress_label:N", title="Level"),
                alt.Tooltip("count:Q", title="Data Centers"),
            ],
        )
        .properties(height=350)
    )
    st.altair_chart(bar, use_container_width=True)

    # ── Scatter: Water Stress vs CO₂ (dual burden) ──────────────────────
    st.subheader("Dual Burden: Water Stress vs. Carbon Intensity")
    st.markdown(
        "Each point is a data center. Facilities in the **upper-right** face "
        "both high carbon intensity and high water stress."
    )

    scatter = (
        alt.Chart(filtered)
        .mark_circle(opacity=0.5)
        .encode(
            x=alt.X("water_stress_score:Q", title="Water Stress Score (0–5)"),
            y=alt.Y("co2_rate:Q", title="CO₂ Rate (lb/MWh)"),
            size=alt.Size("sqft:Q", title="Facility Sq Ft", scale=alt.Scale(range=[10, 300])),
            color=alt.Color("state_abb:N", title="State"),
            tooltip=[
                alt.Tooltip("name:N", title="Facility"),
                alt.Tooltip("state:N"),
                alt.Tooltip("water_stress_score:Q", format=".2f"),
                alt.Tooltip("co2_rate:Q", format=".0f"),
                alt.Tooltip("sqft:Q", format=",.0f"),
            ],
        )
        .properties(width=800, height=500)
    )
    st.altair_chart(scatter, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════
# PAGE: SQ3 — FUTURE PROJECTIONS
# ══════════════════════════════════════════════════════════════════════════

def page_sq3():
    st.title("🔮 SQ3: Future Water Stress Projections")
    st.markdown(
        """
        *Under projected growth scenarios, how might future data center siting
        exacerbate or alleviate grid carbon and water stress?*

        This page uses WRI Aqueduct 4.0 future projections for North American
        catchments under three scenarios (Business-as-Usual, Optimistic,
        Pessimistic) at three time horizons (2030, 2050, 2080).
        """
    )

    future = load_future_water()

    # Normalize label casing (Aqueduct future uses lowercase variants)
    label_cols = [c for c in future.columns if c.endswith("_ws_x_l")]
    for col in label_cols:
        future[col] = future[col].str.strip().str.title()
        # Fix specific known patterns
        future[col] = future[col].replace({
            "Low (<10%)": "Low (<10%)",
            "Low-Medium (10-20%)": "Low-Medium (10-20%)",
            "Medium-High (20-40%)": "Medium-High (20-40%)",
            "High (40-80%)": "High (40-80%)",
            "Extremely High (>80%)": "Extremely High (>80%)",
            "Arid And Low Water Use": "Arid and Low Water Use",
        })

    # ── Sidebar controls ─────────────────────────────────────────────────
    st.sidebar.markdown("### SQ3 Controls")

    scenario = st.sidebar.selectbox(
        "Scenario:",
        ["Business as Usual (BAU)", "Optimistic", "Pessimistic"],
    )
    scenario_prefix = {"Business as Usual (BAU)": "bau", "Optimistic": "opt", "Pessimistic": "pes"}[scenario]

    # ── Build comparison dataframe across years ──────────────────────────
    stress_categories = [
        "Low (<10%)",
        "Low-Medium (10-20%)",
        "Medium-High (20-40%)",
        "High (40-80%)",
        "Extremely High (>80%)",
    ]

    records = []
    for year in ["30", "50", "80"]:
        label_col = f"{scenario_prefix}{year}_ws_x_l"
        if label_col in future.columns:
            counts = future[label_col].value_counts()
            for cat in stress_categories:
                records.append({
                    "Year": f"20{year}",
                    "Category": cat,
                    "Catchments": counts.get(cat, 0),
                })

    proj_df = pd.DataFrame(records)

    # ── KPIs for selected scenario ───────────────────────────────────────
    st.subheader(f"Scenario: {scenario}")

    col_2030 = f"{scenario_prefix}30_ws_x_l"
    col_2080 = f"{scenario_prefix}80_ws_x_l"

    if col_2030 in future.columns and col_2080 in future.columns:
        high_2030 = future[col_2030].isin(["High (40-80%)", "Extremely High (>80%)"]).sum()
        high_2080 = future[col_2080].isin(["High (40-80%)", "Extremely High (>80%)"]).sum()
        total = len(future)

        c1, c2, c3 = st.columns(3)
        c1.metric("NA Catchments Analyzed", f"{total:,}")
        c2.metric(
            "High/Extreme Stress (2030)",
            f"{high_2030:,}",
        )
        c3.metric(
            "High/Extreme Stress (2080)",
            f"{high_2080:,}",
            delta=f"{high_2080 - high_2030:+,}",
            delta_color="inverse",
        )

    st.markdown("---")

    # ── Stacked bar: stress distribution over time ───────────────────────
    st.subheader("Water Stress Distribution Across Time Horizons")

    stress_color_scale = alt.Scale(
        domain=stress_categories,
        range=["#1a9641", "#a6d96a", "#ffffbf", "#fdae61", "#d7191c"],
    )

    stacked = (
        alt.Chart(proj_df)
        .mark_bar()
        .encode(
            x=alt.X("Year:N", title="Projection Year"),
            y=alt.Y("Catchments:Q", title="Number of Catchments", stack="normalize"),
            color=alt.Color(
                "Category:N",
                scale=stress_color_scale,
                sort=stress_categories,
                title="Water Stress Level",
            ),
            tooltip=[
                alt.Tooltip("Year:N"),
                alt.Tooltip("Category:N", title="Stress Level"),
                alt.Tooltip("Catchments:Q"),
            ],
        )
        .properties(width=500, height=400)
    )
    st.altair_chart(stacked, use_container_width=True)

    # ── Absolute counts grouped bar ──────────────────────────────────────
    st.subheader("Absolute Catchment Counts by Stress Level")

    grouped = (
        alt.Chart(proj_df)
        .mark_bar()
        .encode(
            x=alt.X("Year:N", title="Projection Year"),
            y=alt.Y("Catchments:Q", title="Catchments"),
            color=alt.Color(
                "Category:N",
                scale=stress_color_scale,
                sort=stress_categories,
                title="Stress Level",
            ),
            column=alt.Column("Category:N", sort=stress_categories, title="Water Stress Level"),
            tooltip=[
                alt.Tooltip("Year:N"),
                alt.Tooltip("Category:N"),
                alt.Tooltip("Catchments:Q"),
            ],
        )
        .properties(width=120, height=300)
    )
    st.altair_chart(grouped, use_container_width=False)

    # ── Score distribution histogram ─────────────────────────────────────
    st.subheader("Raw Water Stress Score Distribution")

    year_choice = st.selectbox(
        "Select projection year:", ["2030", "2050", "2080"]
    )
    year_code = year_choice[2:]  # "30", "50", "80"
    score_col = f"{scenario_prefix}{year_code}_ws_x_s"

    if score_col in future.columns:
        score_data = future[[score_col]].dropna().rename(columns={score_col: "score"})

        hist = (
            alt.Chart(score_data)
            .mark_bar(opacity=0.7)
            .encode(
                x=alt.X("score:Q", bin=alt.Bin(maxbins=30), title="Water Stress Score"),
                y=alt.Y("count()", title="Number of Catchments"),
            )
            .properties(width=700, height=350)
        )
        st.altair_chart(hist, use_container_width=True)
    else:
        st.warning(f"Score column {score_col} not found in the data.")

    # ── Policy implications callout ──────────────────────────────────────
    st.markdown("---")
    st.subheader("📋 Policy Implications")
    st.markdown(
        """
        The projections reveal a modest but concerning trend toward increased
        water stress across North America. Key takeaways for data center
        siting policy:

        - **Regions projected to worsen** (Southwest, Southern Plains) should
          require water impact assessments for new data center permits
        - **Regions projected to remain stable** (Pacific Northwest, Upper Midwest,
          New England) are lower-risk candidates for future development
        - **Data centers are long-lived assets** (20–30 year lifespans), so
          siting decisions today lock in environmental impacts for decades
        """
    )


# ══════════════════════════════════════════════════════════════════════════
# DISPATCH
# ══════════════════════════════════════════════════════════════════════════

page_fn = {
    "🏠 Overview": page_overview,
    "⚡ SQ1: Carbon Intensity": page_sq1,
    "💧 SQ2: Water Stress": page_sq2,
    "🔮 SQ3: Future Projections": page_sq3,
}

page_fn[selected_page]()

# ── Footer ───────────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    **Data Sources:**
    - [IM3 Data Center Atlas](https://data.msdlive.org/records/65g71-a4731) (PNNL/DOE)
    - [EPA eGRID 2023](https://www.epa.gov/egrid)
    - [WRI Aqueduct 4.0](https://www.wri.org/applications/aqueduct/water-risk-atlas/)

    *30538 Final Project — UChicago Harris*
    """
)

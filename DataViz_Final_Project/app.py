"""
Streamlit App: Data Center Sustainability Explorer
===================================================
Interactive dashboard for exploring the environmental impacts of
U.S. AI/cloud data centers — grid carbon intensity, water stress,
and future projections under different scenarios.

Addresses Sub-Question 3: Under projected growth scenarios, how might
future data center siting exacerbate or alleviate grid carbon and
water stress?

Run locally:  streamlit run streamlit-app/app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from pathlib import Path

# ── Page config ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Data Center Sustainability Explorer",
    page_icon="🏭",
    layout="wide",
)

# ── Data loading ──────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    """Load all derived datasets."""
    # Try multiple possible paths (local dev vs. deployed)
    for base in [Path(__file__).parent / "data",
                 Path(__file__).parent.parent / "data" / "derived-data",
                 Path("data/derived-data"),
                 Path("streamlit-app/data")]:
        master_path = base / "datacenters_master.csv"
        if master_path.exists():
            data_dir = base
            break
    else:
        st.error("Data files not found. Please run preprocessing.py first.")
        st.stop()

    master = pd.read_csv(data_dir / "datacenters_master.csv")
    state_summary = pd.read_csv(data_dir / "state_summary.csv")
    county_summary = pd.read_csv(data_dir / "county_summary.csv")

    future_path = data_dir / "aqueduct_future_water_stress_na.csv"
    future_ws = pd.read_csv(future_path) if future_path.exists() else None

    return master, state_summary, county_summary, future_ws

master, state_summary, county_summary, future_ws = load_data()

# ── Sidebar filters ───────────────────────────────────────────────────────
st.sidebar.title("🔍 Filters")

# State filter
all_states = sorted(master["state_abb"].dropna().unique())
selected_states = st.sidebar.multiselect(
    "Select States",
    options=all_states,
    default=[],
    help="Leave empty to show all states"
)

# CO2 rate filter
co2_min, co2_max = float(master["SRCO2RTA"].min()), float(master["SRCO2RTA"].max())
co2_range = st.sidebar.slider(
    "Grid CO₂ Rate (lb/MWh)",
    min_value=co2_min,
    max_value=co2_max,
    value=(co2_min, co2_max),
    step=10.0,
)

# Water stress filter
ws_categories = ["Low", "Low-Medium", "Medium-High", "High", "Extremely High"]
selected_ws = st.sidebar.multiselect(
    "Water Stress Category",
    options=ws_categories,
    default=ws_categories,
)

# Apply filters
df = master.copy()
if selected_states:
    df = df[df["state_abb"].isin(selected_states)]
df = df[(df["SRCO2RTA"] >= co2_range[0]) & (df["SRCO2RTA"] <= co2_range[1])]
if "bws_state_category" in df.columns:
    df = df[df["bws_state_category"].isin(selected_ws)]

# ── Header ────────────────────────────────────────────────────────────────
st.title("🏭 U.S. Data Center Sustainability Explorer")
st.markdown(
    "**Research Question:** How do the locations of AI/cloud data centers "
    "relate to local carbon intensity and regional water stress — and what "
    "are the policy implications for sustainable data center siting?"
)

# ── KPI cards ─────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Data Centers", f"{len(df):,}")
col2.metric("Total Sqft", f"{df['sqft'].sum()/1e6:.0f}M")
col3.metric("Avg CO₂ Rate", f"{df['SRCO2RTA'].mean():.0f} lb/MWh")
if "bws_state_score" in df.columns:
    col4.metric("Avg Water Stress", f"{df['bws_state_score'].mean():.1f}/5")

st.divider()

# ══════════════════════════════════════════════════════════════════════════
# TAB LAYOUT
# ══════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3 = st.tabs([
    "📍 Map: Carbon & Water Risk",
    "📊 State Comparisons",
    "🔮 SQ3: Future Projections"
])

# ── TAB 1: Interactive Map ────────────────────────────────────────────────
with tab1:
    st.subheader("Data Center Locations by Carbon Intensity and Water Stress")

    map_color = st.radio(
        "Color encoding:",
        ["Grid CO₂ Rate (lb/MWh)", "Water Stress Category"],
        horizontal=True,
    )

    if map_color == "Grid CO₂ Rate (lb/MWh)":
        color_enc = alt.Color(
            "SRCO2RTA:Q",
            scale=alt.Scale(scheme="redyellowgreen", reverse=True),
            title="CO₂ Rate (lb/MWh)",
        )
    else:
        cat_order = ["Low", "Low-Medium", "Medium-High", "High", "Extremely High"]
        color_enc = alt.Color(
            "bws_state_category:N",
            scale=alt.Scale(
                domain=cat_order,
                range=["#2166ac", "#67a9cf", "#fddbc7", "#ef8a62", "#b2182b"]
            ),
            title="Water Stress",
        )

    # Size encoding
    size_field = st.selectbox(
        "Size encoding:",
        ["Uniform", "Facility Sqft", "CO₂ Rate"],
        index=0,
    )

    if size_field == "Facility Sqft":
        size_enc = alt.Size("sqft:Q", title="Sqft", scale=alt.Scale(range=[10, 300]))
    elif size_field == "CO₂ Rate":
        size_enc = alt.Size("SRCO2RTA:Q", title="CO₂ Rate", scale=alt.Scale(range=[10, 300]))
    else:
        size_enc = alt.value(40)

    map_chart = alt.Chart(df).mark_circle(opacity=0.6, stroke="black", strokeWidth=0.3).encode(
        longitude="lon:Q",
        latitude="lat:Q",
        color=color_enc,
        size=size_enc,
        tooltip=[
            alt.Tooltip("name:N", title="Facility"),
            alt.Tooltip("operator:N", title="Operator"),
            alt.Tooltip("state_abb:N", title="State"),
            alt.Tooltip("county:N", title="County"),
            alt.Tooltip("sqft:Q", title="Sqft", format=","),
            alt.Tooltip("SRCO2RTA:Q", title="CO₂ lb/MWh", format=".0f"),
            alt.Tooltip("egrid_subregion:N", title="eGRID Subregion"),
            alt.Tooltip("bws_state_category:N", title="Water Stress"),
        ],
    ).properties(
        width=900,
        height=500,
        title="U.S. Data Center Locations — Carbon & Water Risk"
    ).project("albersUsa")

    st.altair_chart(map_chart, use_container_width=True)

    st.caption(
        "Each dot is a data center facility. Color shows grid carbon intensity or "
        "water stress category. Data: IM3 Atlas (PNNL), eGRID 2023 (EPA), Aqueduct 4.0 (WRI)."
    )

# ── TAB 2: State Comparisons ─────────────────────────────────────────────
with tab2:
    st.subheader("State-Level Comparison: Carbon Intensity vs. Data Center Concentration")

    # State-level scatter with interactive selection
    state_df = df.groupby(["state", "state_abb"]).agg(
        dc_count=("id", "count"),
        total_sqft=("sqft", "sum"),
        mean_co2=("SRCO2RTA", "mean"),
        mean_ws=("bws_state_score", "mean") if "bws_state_score" in df.columns else ("SRCO2RTA", "count"),
    ).reset_index()

    y_axis_choice = st.radio(
        "Y-axis metric:",
        ["Number of Data Centers", "Total Facility Sqft (millions)"],
        horizontal=True,
    )

    y_field = "dc_count" if "Number" in y_axis_choice else "total_sqft"
    if y_field == "total_sqft":
        state_df["total_sqft_m"] = state_df["total_sqft"] / 1e6
        y_field_plot = "total_sqft_m"
        y_title = "Total Sqft (millions)"
    else:
        y_field_plot = "dc_count"
        y_title = "Number of Data Centers"

    scatter = alt.Chart(state_df).mark_circle(size=80, opacity=0.7).encode(
        x=alt.X("mean_co2:Q", title="Mean Grid CO₂ Rate (lb/MWh)"),
        y=alt.Y(f"{y_field_plot}:Q", title=y_title),
        color=alt.Color(
            "mean_ws:Q" if "bws_state_score" in df.columns else "mean_co2:Q",
            scale=alt.Scale(scheme="redyellowblue", reverse=True),
            title="Water Stress Score" if "bws_state_score" in df.columns else "CO₂ Rate",
        ),
        tooltip=[
            alt.Tooltip("state_abb:N", title="State"),
            alt.Tooltip("dc_count:Q", title="Data Centers"),
            alt.Tooltip("mean_co2:Q", title="Avg CO₂ Rate", format=".0f"),
        ],
    ).properties(
        width=700,
        height=400,
        title="States: Grid Carbon vs. Data Center Concentration"
    )

    text = scatter.mark_text(dy=-10, fontSize=10).encode(
        text="state_abb:N"
    )

    st.altair_chart(scatter + text, use_container_width=True)

    # Bar chart: top states
    st.subheader("Top States by Data Center Count")
    top_n = st.slider("Number of states to show:", 5, 25, 15)

    top_states = state_df.nlargest(top_n, "dc_count")
    bar = alt.Chart(top_states).mark_bar().encode(
        x=alt.X("dc_count:Q", title="Number of Data Centers"),
        y=alt.Y("state_abb:N", sort="-x", title="State"),
        color=alt.Color(
            "mean_co2:Q",
            scale=alt.Scale(scheme="redyellowgreen", reverse=True),
            title="CO₂ Rate (lb/MWh)"
        ),
        tooltip=[
            alt.Tooltip("state_abb:N", title="State"),
            alt.Tooltip("dc_count:Q", title="Data Centers"),
            alt.Tooltip("mean_co2:Q", title="Avg CO₂ lb/MWh", format=".0f"),
        ]
    ).properties(width=600, height=max(top_n * 25, 200))

    st.altair_chart(bar, use_container_width=True)

# ── TAB 3: SQ3 — Future Projections ──────────────────────────────────────
with tab3:
    st.subheader("Sub-Question 3: Future Water Stress Projections")
    st.markdown(
        "Under projected growth scenarios, how might future data center siting "
        "exacerbate or alleviate grid carbon and water stress?"
    )

    if future_ws is not None and len(future_ws) > 0:
        # ── Scenario selector ─────────────────────────────────────────────
        col_a, col_b = st.columns(2)
        with col_a:
            scenario = st.selectbox(
                "Climate/Development Scenario",
                ["Business as Usual (BAU)", "Optimistic", "Pessimistic"],
            )
        with col_b:
            time_horizon = st.selectbox(
                "Time Horizon",
                ["2030", "2050", "2080"],
            )

        scenario_map = {
            "Business as Usual (BAU)": "bau",
            "Optimistic": "opt",
            "Pessimistic": "pes",
        }
        year_map = {"2030": "30", "2050": "50", "2080": "80"}
        prefix = scenario_map[scenario] + year_map[time_horizon]

        score_col = f"{prefix}_ws_x_s"
        label_col = f"{prefix}_ws_x_l"

        if score_col in future_ws.columns:
            future_clean = future_ws[[
                "pfaf_id", score_col, label_col
            ]].dropna(subset=[score_col]).copy()
            future_clean.columns = ["pfaf_id", "future_score", "future_label"]

            # Distribution of future water stress
            st.markdown(f"#### Water Stress Distribution — {scenario}, {time_horizon}")

            label_order = [
                "Low (<10%)", "Low-Medium (10-20%)", "Medium-High (20-40%)",
                "High (40-80%)", "Extremely High (>80%)"
            ]
            label_colors = ["#2166ac", "#67a9cf", "#fddbc7", "#ef8a62", "#b2182b"]

            future_dist = future_clean["future_label"].value_counts().reset_index()
            future_dist.columns = ["Category", "Catchments"]

            dist_chart = alt.Chart(future_dist).mark_bar().encode(
                x=alt.X("Category:N", sort=label_order, title="Water Stress Category"),
                y=alt.Y("Catchments:Q", title="Number of Catchments (N. America)"),
                color=alt.Color(
                    "Category:N",
                    scale=alt.Scale(domain=label_order, range=label_colors),
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("Category:N"),
                    alt.Tooltip("Catchments:Q", format=","),
                ],
            ).properties(width=600, height=350)

            st.altair_chart(dist_chart, use_container_width=True)

            # ── Compare scenarios side by side ────────────────────────────
            st.markdown("#### Scenario Comparison: Share of High-Stress Catchments Over Time")

            comparison_data = []
            for sc_name, sc_code in scenario_map.items():
                for yr_name, yr_code in year_map.items():
                    col = f"{sc_code}{yr_code}_ws_x_s"
                    if col in future_ws.columns:
                        scores = future_ws[col].dropna()
                        n_total = len(scores)
                        n_high = (scores >= 3).sum()  # score >=3 = High or Extremely High
                        comparison_data.append({
                            "Scenario": sc_name,
                            "Year": int("20" + yr_code),
                            "Pct_High_Stress": 100 * n_high / n_total if n_total > 0 else 0,
                            "N_High": n_high,
                            "N_Total": n_total,
                        })

            comp_df = pd.DataFrame(comparison_data)

            if len(comp_df) > 0:
                line_chart = alt.Chart(comp_df).mark_line(
                    point=alt.OverlayMarkDef(size=60)
                ).encode(
                    x=alt.X("Year:O", title="Year"),
                    y=alt.Y("Pct_High_Stress:Q",
                             title="% Catchments with High/Extreme Water Stress"),
                    color=alt.Color(
                        "Scenario:N",
                        scale=alt.Scale(
                            domain=list(scenario_map.keys()),
                            range=["#ff7f0e", "#2ca02c", "#d62728"]
                        ),
                    ),
                    tooltip=[
                        alt.Tooltip("Scenario:N"),
                        alt.Tooltip("Year:O"),
                        alt.Tooltip("Pct_High_Stress:Q", title="% High Stress", format=".1f"),
                        alt.Tooltip("N_High:Q", title="# High-Stress Catchments"),
                    ]
                ).properties(
                    width=600,
                    height=350,
                    title="Projected High Water Stress Under Three Scenarios"
                )

                st.altair_chart(line_chart, use_container_width=True)

            # ── Policy implications ───────────────────────────────────────
            st.markdown("#### 💡 Policy Implications")

            # Compute current vs future high-stress stats
            current_high_pct = 0
            if "bws_state_category" in master.columns:
                high_mask = master["bws_state_category"].isin(["High", "Extremely High"])
                current_high_pct = 100 * high_mask.mean()

            future_high_selected = comp_df[
                (comp_df["Scenario"] == scenario) &
                (comp_df["Year"] == int("20" + year_map[time_horizon]))
            ]

            st.markdown(
                f"- **Currently**, approximately **{current_high_pct:.0f}%** of U.S. data centers "
                f"are located in high or extremely high water stress areas.\n"
                f"- Under the **{scenario}** scenario by **{time_horizon}**, "
                f"**{future_high_selected['Pct_High_Stress'].values[0]:.1f}%** of North American "
                f"catchments are projected to face high or extreme water stress.\n"
                f"- Strategic siting of new data centers in lower-stress regions, combined with "
                f"investments in water-efficient cooling and clean grid electricity, can significantly "
                f"reduce the environmental footprint of AI infrastructure growth."
            )

        else:
            st.warning(f"Column {score_col} not found in future projections data.")
    else:
        st.info("Future water stress projections data not available.")

# ── Footer ────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "**Data Sources:** IM3 Open Source Data Center Atlas (PNNL/DOE), "
    "EPA eGRID 2023, WRI Aqueduct 4.0 Water Risk Atlas. "
    "Built for UChicago Harris DAP Final Project, Winter 2026."
)

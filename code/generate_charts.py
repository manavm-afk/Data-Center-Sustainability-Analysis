"""
generate_charts.py — Static Visualizations for Final Report
============================================================
Generates all static plots (PNG) referenced in the final project report.

Figures:
  1. Top 10 States by Data Center Count (horizontal bar, color=CO2)
  2. U.S. Map of Data Centers by Grid Carbon Intensity (spatial scatter)
  3. Top 10 eGRID Subregions: DC Count and Carbon Intensity (bar+line)
  4. Water Stress Distribution (pie + horizontal bar side-by-side)
  5. Dual Risk Scatter: CO2 vs Water Stress
     *** ENHANCED: top-5 dual-risk state annotation table inside risk zone ***

Usage:
  python code/generate_charts.py

Outputs saved to: output_charts/
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DERIVED = ROOT / "data" / "derived-data"
OUT = ROOT / "output_charts"
OUT.mkdir(parents=True, exist_ok=True)

LBS_TO_KG = 0.453592

# ── Load data ─────────────────────────────────────────────────────────────
print("Loading data...")
master = pd.read_csv(DERIVED / "datacenters_master.csv")
state_summary = pd.read_csv(DERIVED / "state_summary.csv")
county_summary = pd.read_csv(DERIVED / "county_summary.csv")
future_ws = pd.read_csv(DERIVED / "aqueduct_future_water_stress_na.csv")

print(f"  Master: {len(master):,} rows, States: {len(state_summary)}, Counties: {len(county_summary)}")
print(f"  Future water stress: {len(future_ws):,} catchments")


# ══════════════════════════════════════════════════════════════════════════
# FIGURE 1: Top 10 States by Data Center Count
# ══════════════════════════════════════════════════════════════════════════
def fig1_top_states():
    print("\n[Figure 1] Top 10 States by Data Center Count...")

    top10 = state_summary.nlargest(10, "dc_count").iloc[::-1]

    fig, ax = plt.subplots(figsize=(10, 6))

    co2_vals = top10["mean_co2_rate"].values
    norm = plt.Normalize(vmin=350, vmax=1100)
    cmap = plt.cm.RdYlGn_r
    colors = [cmap(norm(v)) for v in co2_vals]

    bars = ax.barh(top10["state"], top10["dc_count"], color=colors, edgecolor="gray", linewidth=0.5)

    for bar, (_, row) in zip(bars, top10.iterrows()):
        lbs = row["mean_co2_rate"]
        kg = lbs * LBS_TO_KG
        label = f"{lbs:.0f} lbs/MWh ({kg:.0f} kg/MWh)"
        ax.text(bar.get_width() + 3, bar.get_y() + bar.get_height() / 2,
                label, va="center", fontsize=9)

    ax.set_xlabel("Number of Data Centers", fontsize=12)
    ax.set_title("Top 10 States by Data Center Count\n(Color = Mean Grid CO\u2082 Rate)",
                  fontsize=13, fontweight="bold")
    ax.set_xlim(0, max(top10["dc_count"]) * 1.45)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, pad=0.02, aspect=30)
    cbar.set_label("CO\u2082 Rate (lbs/MWh)", fontsize=10)

    plt.tight_layout()
    plt.savefig(OUT / "fig1_top_states.png", dpi=200, bbox_inches="tight")
    plt.close()
    print("  Done: fig1_top_states.png")


# ══════════════════════════════════════════════════════════════════════════
# FIGURE 2: U.S. Maps — Data Centers by Grid Carbon Intensity
#   2a = Top 10 STATE annotations (matches Picture_1.png)
#   2b = CITY/COUNTY annotations  (matches Picture_3.png)
# Uses Census Bureau cartographic boundary shapefiles for county + state layers
# ══════════════════════════════════════════════════════════════════════════

COUNTY_URL = "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_county_20m.zip"
STATE_URL  = "https://www2.census.gov/geo/tiger/GENZ2023/shp/cb_2023_us_state_20m.zip"
CACHE_DIR  = ROOT / "data" / "shapefiles"


def _load_boundaries():
    """Load and cache US county + state boundaries from Census Bureau."""
    import geopandas as gpd
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    county_cache = CACHE_DIR / "cb_2023_us_county_20m"
    state_cache  = CACHE_DIR / "cb_2023_us_state_20m"

    if county_cache.exists() and any(county_cache.glob("*.shp")):
        counties = gpd.read_file(county_cache)
    else:
        print("    Downloading county boundaries (first run only)...")
        counties = gpd.read_file(COUNTY_URL)
        county_cache.mkdir(exist_ok=True)
        counties.to_file(county_cache / "counties.shp")

    if state_cache.exists() and any(state_cache.glob("*.shp")):
        states = gpd.read_file(state_cache)
    else:
        print("    Downloading state boundaries (first run only)...")
        states = gpd.read_file(STATE_URL)
        state_cache.mkdir(exist_ok=True)
        states.to_file(state_cache / "states.shp")

    # Filter to continental US
    exclude_fips = {"02", "15", "60", "66", "69", "72", "78"}
    counties = counties[~counties["STATEFP"].isin(exclude_fips)]
    states   = states[~states["STATEFP"].isin(exclude_fips)]
    return counties, states


def _base_map(fig, ax, counties, states, dc_df):
    """Draw boundary layers + data center scatter. Returns filtered df and scatter."""
    # Layer 1: County boundaries (light gray, thin)
    counties.boundary.plot(ax=ax, color="#cccccc", linewidth=0.15)
    # Layer 2: State borders (black, thicker)
    states.boundary.plot(ax=ax, color="black", linewidth=0.8)

    df = dc_df[(dc_df["lon"].between(-130, -65)) & (dc_df["lat"].between(24, 50))].copy()
    df["plot_size"] = np.where(df["sqft"].isna(), 5, np.clip(df["sqft"] / 50000, 3, 150))

    norm = plt.Normalize(vmin=200, vmax=1300)
    cmap = plt.cm.RdYlGn_r

    scatter = ax.scatter(df["lon"], df["lat"], c=df["SRCO2RTA"], cmap=cmap, norm=norm,
                         s=df["plot_size"], alpha=0.65, edgecolors="black", linewidth=0.3, zorder=3)

    for sqft_val, label in [(50000, "50K sq ft"), (500000, "500K sq ft"),
                            (5000000, "5M sq ft"), (20000000, "20M sq ft")]:
        s = np.clip(sqft_val / 50000, 3, 150)
        ax.scatter([], [], s=s, c="gray", alpha=0.5, edgecolors="black", linewidth=0.3, label=label)
    ax.legend(loc="lower left", title="Facility Size", fontsize=8, title_fontsize=9, framealpha=0.9)

    cbar = fig.colorbar(scatter, ax=ax, shrink=0.6, pad=0.02, aspect=25)
    cbar.set_label("CO\u2082 Emission Rate (lb/MWh)", fontsize=10)

    ax.set_xlim(-128, -65); ax.set_ylim(24, 50)
    ax.set_axis_off()
    return df, scatter


def fig2a_state_map():
    """Map with top 10 STATE annotations (Virginia 319 DCs, California 112 DCs...)"""
    print("\n[Figure 2a] U.S. Map — top 10 state annotations...")
    try:
        counties, states = _load_boundaries()
    except Exception as e:
        print(f"  ⚠ Skipped (no boundaries): {e}")
        return

    fig, ax = plt.subplots(figsize=(14, 9))
    df, scatter = _base_map(fig, ax, counties, states, master)

    state_counts = df.groupby(["state_abb", "state"]).agg(
        dc_count=("id", "count"), mean_lon=("lon", "mean"), mean_lat=("lat", "mean"),
    ).reset_index().nlargest(10, "dc_count")

    offsets = {
        "VA": (35, -20), "TX": (-20, -25), "CA": (-60, -15), "OR": (-70, 15),
        "OH": (25, 15), "WA": (-70, 10), "AZ": (-25, -30), "IA": (15, 15),
        "NJ": (40, -10), "IL": (15, 20),
    }
    for _, row in state_counts.iterrows():
        abb = row["state_abb"]
        label = f"{row['state']}\n({row['dc_count']:.0f} DCs)"
        dx, dy = offsets.get(abb, (20, 15))
        ax.annotate(label, (row["mean_lon"], row["mean_lat"]),
                    xytext=(dx, dy), textcoords="offset points",
                    fontsize=8, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.85, edgecolor="gray"),
                    arrowprops=dict(arrowstyle="-", color="gray", lw=0.8), zorder=5)

    ax.set_title("U.S. Data Center Locations by Grid Carbon Intensity\n"
                  "Each dot is a data center \u00b7 color = eGRID subregion CO\u2082 rate \u00b7 top 10 states annotated",
                  fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUT / "fig2a_us_map_states.png", dpi=200, bbox_inches="tight")
    plt.close()
    print("  Done: fig2a_us_map_states.png")


def fig2b_county_map():
    """Map with CITY/COUNTY cluster annotations (N. Virginia 303 DCs, Portland 85 DCs...)"""
    print("\n[Figure 2b] U.S. Map — city/county annotations...")
    try:
        counties, states = _load_boundaries()
    except Exception as e:
        print(f"  ⚠ Skipped (no boundaries): {e}")
        return

    fig, ax = plt.subplots(figsize=(14, 9))
    df, scatter = _base_map(fig, ax, counties, states, master)

    annots = [
        (-77.4,  39.05, "N. Virginia\n(303 DCs)",     30, -25),
        (-121.9, 37.4,  "Santa Clara, CA\n(75 DCs)", -50, -30),
        (-112.0, 33.5,  "Phoenix, AZ\n(63 DCs)",     -20, -30),
        (-119.7, 45.6,  "Portland, OR\n(85 DCs)",    -60,  15),
        (-119.5, 47.4,  "Grant Co., WA\n(39 DCs)",   -70,  10),
        (-93.6,  41.6,  "Des Moines, IA\n(26 DCs)",   20,  15),
        (-87.7,  42.0,  "Chicago, IL\n(29 DCs)",      15,  20),
        (-82.8,  40.0,  "Columbus, OH\n(65 DCs)",     20,  15),
        (-96.8,  33.0,  "Dallas, TX\n(25 DCs)",      -20, -25),
        (-98.5,  29.4,  "San Antonio, TX\n(33 DCs)", -50, -20),
    ]
    for lon, lat, label, dx, dy in annots:
        ax.annotate(label, (lon, lat), xytext=(dx, dy), textcoords="offset points",
                    fontsize=7.5, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="white", alpha=0.85, edgecolor="gray"),
                    arrowprops=dict(arrowstyle="-", color="gray", lw=0.8), zorder=5)

    ax.set_title("U.S. Data Center Locations by Grid Carbon Intensity\n"
                  "Each dot is a data center \u00b7 color = eGRID subregion CO\u2082 rate \u00b7 size = facility sq ft",
                  fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(OUT / "fig2b_us_map_counties.png", dpi=200, bbox_inches="tight")
    plt.close()
    print("  Done: fig2b_us_map_counties.png")


# ══════════════════════════════════════════════════════════════════════════
# FIGURE 3: Top 10 eGRID Subregions
# ══════════════════════════════════════════════════════════════════════════
def fig3_egrid_subregions():
    print("\n[Figure 3] Top 10 eGRID Subregions...")

    sub = master.groupby("egrid_subregion").agg(
        dc_count=("id", "count"), co2_rate=("SRCO2RTA", "first"),
    ).reset_index().nlargest(10, "dc_count")

    fig, ax1 = plt.subplots(figsize=(11, 6))
    x = np.arange(len(sub))

    norm = plt.Normalize(vmin=350, vmax=1100)
    cmap = plt.cm.RdYlGn_r
    colors = [cmap(norm(v)) for v in sub["co2_rate"]]

    ax1.bar(x, sub["dc_count"], color=colors, edgecolor="gray", linewidth=0.5, width=0.6)
    ax1.set_xticks(x)
    ax1.set_xticklabels(sub["egrid_subregion"], rotation=35, ha="right", fontsize=10)
    ax1.set_ylabel("Number of Data Centers", fontsize=11)
    ax1.set_xlabel("eGRID Subregion", fontsize=11)

    ax2 = ax1.twinx()
    ax2.plot(x, sub["co2_rate"], "k-o", linewidth=2, markersize=6, label="CO\u2082 Rate (lbs/MWh)", zorder=5)
    ax2.plot(x, sub["co2_rate"] * LBS_TO_KG, "--", color="gray", linewidth=1.5,
             marker="s", markersize=4, label="CO\u2082 Rate (kg/MWh)", zorder=4)
    ax2.set_ylabel("CO\u2082 Emission Rate", fontsize=11)
    ax2.legend(loc="upper right", fontsize=9, framealpha=0.9)

    ax1.set_title("Top 10 eGRID Subregions: Data Center Count and Carbon Intensity",
                   fontsize=13, fontweight="bold")

    plt.tight_layout()
    plt.savefig(OUT / "fig3_egrid_subregions.png", dpi=200, bbox_inches="tight")
    plt.close()
    print("  Done: fig3_egrid_subregions.png")


# ══════════════════════════════════════════════════════════════════════════
# FIGURE 4: Water Stress Distribution
# ══════════════════════════════════════════════════════════════════════════
def fig4_water_stress():
    print("\n[Figure 4] Water Stress Distribution...")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    ws_order = ["Low", "Low-Medium", "Medium-High", "High", "Extremely High"]
    ws_colors = ["#2ca02c", "#a8d08d", "#ffd966", "#e36c09", "#c00000"]

    ws_counts = master["bws_state_category"].value_counts()
    sizes = [ws_counts.get(cat, 0) for cat in ws_order]

    wedges, texts, autotexts = ax1.pie(
        sizes, labels=None, autopct=lambda p: f"{p:.1f}%",
        colors=ws_colors, startangle=90, pctdistance=0.75, textprops={"fontsize": 10})
    ax1.set_title("Data Centers by\nWater Stress Category", fontsize=12, fontweight="bold")
    ax1.legend(wedges, [f"{c} ({ws_counts.get(c,0)})" for c in ws_order],
               title="Water Stress Level", loc="lower left", fontsize=8, title_fontsize=9)

    high_stress = master[master["bws_state_category"].isin(["High", "Extremely High"])]
    state_high = high_stress.groupby("state_abb").size().nlargest(7).iloc[::-1]

    bars = ax2.barh(state_high.index, state_high.values,
                    color=["#c00000" if v > 50 else "#e36c09" for v in state_high.values],
                    edgecolor="gray", linewidth=0.5)
    for bar, v in zip(bars, state_high.values):
        ax2.text(bar.get_width() + 1.5, bar.get_y() + bar.get_height() / 2,
                 str(v), va="center", fontsize=10, fontweight="bold")
    ax2.set_xlabel("Number of Data Centers in High/Extreme Water Stress", fontsize=10)
    ax2.set_title("States with Most Water-Stressed\nData Centers", fontsize=12, fontweight="bold")
    ax2.set_xlim(0, max(state_high.values) * 1.15)

    plt.tight_layout()
    plt.savefig(OUT / "fig4_water_stress.png", dpi=200, bbox_inches="tight")
    plt.close()
    print("  Done: fig4_water_stress.png")


# ══════════════════════════════════════════════════════════════════════════
# FIGURE 5: Dual Risk Scatter  (ENHANCED with Top-5 state context)
# ══════════════════════════════════════════════════════════════════════════
def fig5_dual_risk():
    print("\n[Figure 5] Dual Risk Scatter (ENHANCED with top-5 state annotations)...")

    fig, ax1 = plt.subplots(figsize=(14, 9))

    ws_order = ["Low", "Low-Medium", "Medium-High", "High", "Extremely High"]
    ws_x_map = {cat: i for i, cat in enumerate(ws_order)}

    df = master.copy()
    df["ws_x"] = df["bws_state_category"].map(ws_x_map)
    df = df.dropna(subset=["ws_x", "SRCO2RTA"])

    np.random.seed(42)
    df["ws_x_jitter"] = df["ws_x"] + np.random.uniform(-0.35, 0.35, len(df))
    df["plot_size"] = np.where(df["sqft"].isna(), 8, np.clip(df["sqft"] / 100000, 5, 120))

    dual_risk_mask = (df["SRCO2RTA"] > 700) & (df["ws_x"] >= 3)
    n_dual = dual_risk_mask.sum()

    # Shaded dual risk zone
    rect = mpatches.FancyBboxPatch(
        (2.6, 700), 2.3, 950, boxstyle="round,pad=0.05",
        facecolor="#ffcccc", alpha=0.20, edgecolor="#cc0000",
        linewidth=1.5, linestyle="--", zorder=1)
    ax1.add_patch(rect)

    ax1.annotate(f"DUAL RISK ZONE\n({n_dual} Data Centers)",
                 xy=(4.3, 1580), fontsize=11, fontweight="bold", color="#cc0000", ha="center",
                 bbox=dict(boxstyle="round,pad=0.4", facecolor="white", edgecolor="#cc0000", alpha=0.9),
                 zorder=6)

    # ── TOP 5 DUAL-RISK STATES context layer ──────────────────────────────
    dual_df = df[dual_risk_mask]
    top5 = dual_df.groupby("state_abb").agg(
        count=("id", "count"), mean_co2=("SRCO2RTA", "mean"),
        ws_cat=("bws_state_category", "first"),
    ).nlargest(5, "count").reset_index()

    lines = ["     Top 5 Dual-Risk States", "  " + "\u2500" * 42,
             f"  {'State':<7} {'DCs':>5}  {'CO\u2082 (lb/MWh)':>13}  {'kg/MWh':>8}  {'Water Stress'}",
             "  " + "\u2500" * 42]
    for _, r in top5.iterrows():
        kg = r["mean_co2"] * LBS_TO_KG
        lines.append(f"  {r['state_abb']:<7} {r['count']:>5}  {r['mean_co2']:>10.1f}   {kg:>7.1f}   {r['ws_cat']}")
    lines += ["  " + "\u2500" * 42, f"  Total: {top5['count'].sum()} of {n_dual} dual-risk DCs"]

    ax1.text(3.05, 1430, "\n".join(lines), fontsize=8.5, fontfamily="monospace",
             bbox=dict(boxstyle="round,pad=0.5", facecolor="#fff5f5",
                       edgecolor="#cc0000", alpha=0.93, linewidth=1.2),
             verticalalignment="top", zorder=6)

    # Scatter points
    ax1.scatter(df[~dual_risk_mask]["ws_x_jitter"], df[~dual_risk_mask]["SRCO2RTA"],
                s=df[~dual_risk_mask]["plot_size"], c="steelblue", alpha=0.35,
                edgecolors="gray", linewidth=0.2, zorder=2)
    ax1.scatter(df[dual_risk_mask]["ws_x_jitter"], df[dual_risk_mask]["SRCO2RTA"],
                s=df[dual_risk_mask]["plot_size"], c="#cc3333", alpha=0.55,
                edgecolors="darkred", linewidth=0.3, zorder=3)

    ax2 = ax1.twinx()
    y_min, y_max = 150, 1650
    ax1.set_ylim(y_min, y_max); ax2.set_ylim(y_min * LBS_TO_KG, y_max * LBS_TO_KG)
    ax2.set_ylabel("Grid CO\u2082 Emission Rate (kg/MWh)", fontsize=11)

    ax1.set_xticks(range(5))
    ax1.set_xticklabels(["Low\n(<10%)", "Low-Med\n(10-20%)", "Med-High\n(20-40%)",
                          "High\n(40-80%)", "Ext. High\n(>80%)"], fontsize=10)
    ax1.set_xlabel("Water Stress Category (WRI Aqueduct 4.0)", fontsize=12)
    ax1.set_ylabel("Grid CO\u2082 Emission Rate (lbs/MWh)", fontsize=11)
    ax1.set_title("Data Centers: Grid Carbon Intensity vs. Water Stress\n"
                   "(Bubble size = facility square footage)", fontsize=13, fontweight="bold")
    ax1.axhline(y=700, color="gray", linestyle=":", linewidth=0.8, alpha=0.5)

    legend_el = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="steelblue", markersize=8, alpha=0.5, label="Standard risk"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#cc3333", markersize=8, alpha=0.7, label="Dual risk (high CO\u2082 + water stress)"),
        mpatches.Patch(facecolor="#ffcccc", edgecolor="#cc0000", alpha=0.3, linestyle="--", label=f"Dual risk zone ({n_dual} DCs)"),
    ]
    ax1.legend(handles=legend_el, loc="upper left", fontsize=9, framealpha=0.9)

    plt.tight_layout()
    plt.savefig(OUT / "fig5_dual_risk_scatter.png", dpi=200, bbox_inches="tight")
    plt.close()
    print("  Done: fig5_dual_risk_scatter.png")


# ══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("  Generating Static Visualizations for Final Report")
    print("=" * 60)
    fig1_top_states()
    fig2a_state_map()
    fig2b_county_map()
    fig3_egrid_subregions()
    fig4_water_stress()
    fig5_dual_risk()
    print("\n" + "=" * 60)
    print(f"All charts saved to: {OUT}")
    for f in sorted(OUT.glob("*.png")):
        print(f"  {f.name} ({f.stat().st_size / 1024:.0f} KB)")
    print("=" * 60)

import type { Meta } from "@/lib/types";

export default function KpiTiles({
  headline,
}: {
  headline: Meta["headline_numbers"];
}) {
  const tiles = [
    {
      label: "Data centers",
      value: headline.n_facilities.toLocaleString(),
      note: `${headline.n_states} states & territories`,
    },
    {
      label: "Grid CO₂, sqft-weighted",
      value: `${Math.round(headline.mean_co2_rate_sqft_weighted_lb_mwh)}`,
      unit: "lb/MWh",
      note: `${Math.round(headline.mean_co2_rate_unweighted_lb_mwh)} unweighted`,
    },
    {
      label: "In high water stress",
      value: headline.n_high_water_stress.toLocaleString(),
      note: `${headline.pct_high_water_stress_of_with_data}% of facilities (basin-level)`,
    },
    {
      label: "Dual risk",
      value: headline.n_dual_risk.toLocaleString(),
      note: ">700 lb/MWh + High/Extremely High basin",
    },
  ];

  return (
    <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {tiles.map((t) => (
        <div key={t.label} className="card px-4 py-3 flex flex-col gap-0.5">
          <span
            className="text-xs font-medium"
            style={{ color: "var(--text-secondary)" }}
          >
            {t.label}
          </span>
          <span className="text-2xl font-semibold tracking-tight">
            {t.value}
            {t.unit ? (
              <span
                className="ml-1 text-sm font-normal"
                style={{ color: "var(--text-secondary)" }}
              >
                {t.unit}
              </span>
            ) : null}
          </span>
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            {t.note}
          </span>
        </div>
      ))}
    </section>
  );
}

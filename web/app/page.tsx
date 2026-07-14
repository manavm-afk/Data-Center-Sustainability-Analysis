import { getFacilityPoints, getMeta } from "@/lib/data";
import KpiTiles from "@/components/KpiTiles";
import UsMap from "@/components/UsMap";

export default function Home() {
  const meta = getMeta();
  const facilities = getFacilityPoints();
  const h = meta.headline_numbers;
  const vocab = meta.water_stress_vocabulary;

  return (
    <main className="mx-auto w-full max-w-6xl px-4 py-8 flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">
          US Data Center Sustainability Explorer
        </h1>
        <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
          Grid carbon intensity and basin-level water stress for{" "}
          {h.n_facilities.toLocaleString()} facilities. Every assignment is a
          documented spatial join — methods and provenance in the{" "}
          <a
            className="underline underline-offset-2"
            href="https://github.com/manavm-afk/Data-Center-Sustainability-Analysis"
          >
            project repo
          </a>
          .
        </p>
      </header>

      <KpiTiles headline={h} />

      <section className="card p-4">
        <UsMap
          facilities={facilities}
          nationalMeanCo2={h.mean_co2_rate_sqft_weighted_lb_mwh}
          waterColors={vocab.category_colors}
          waterColorsDark={vocab.category_colors_dark}
          waterOrder={vocab.category_order}
          waterLabels={vocab.category_to_label}
        />
      </section>

      <footer
        className="text-xs leading-relaxed"
        style={{ color: "var(--text-muted)" }}
      >
        <p>
          Data (pipeline run {meta.generated}):{" "}
          {Object.values(meta.datasets)
            .map((d) => `${d.name} (${d.version_used})`)
            .join(" · ")}
        </p>
        <p className="mt-1">{meta.attribution.join(" · ")}</p>
        <p className="mt-1">
          Licensing: code {meta.licensing.code} · facility datasets{" "}
          {meta.licensing.facility_datasets} · FracTracker fields:{" "}
          {meta.licensing.fractracker_fields} · per-dataset terms:{" "}
          {meta.licensing.details}
        </p>
      </footer>
    </main>
  );
}

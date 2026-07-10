"use client";

import { useEffect, useMemo, useState } from "react";
import { geoAlbersUsa, geoPath } from "d3-geo";
import { scaleDiverging } from "d3-scale";
import { feature, mesh } from "topojson-client";
import type { Topology, GeometryCollection } from "topojson-specification";
import statesTopo from "us-atlas/states-10m.json";
import type { FacilityPoint, WaterCategory } from "@/lib/types";

const W = 975;
const H = 610;

type Mode = "carbon" | "water";

interface Props {
  facilities: FacilityPoint[];
  nationalMeanCo2: number;
  waterColors: Record<WaterCategory, string>;
  waterColorsDark: Record<WaterCategory, string>;
  waterOrder: WaterCategory[];
  waterLabels: Record<WaterCategory, string>;
}

/** Diverging tokens — must mirror --div-* in globals.css (light/dark selected). */
const DIVERGING = {
  light: { cool: "#2a78d6", mid: "#f0efec", warm: "#d03b3b" },
  dark: { cool: "#3987e5", mid: "#383835", warm: "#e66767" },
};

function mixHex(a: string, b: string, u: number): string {
  const pa = a.replace("#", "").match(/\w\w/g)!.map((x) => parseInt(x, 16));
  const pb = b.replace("#", "").match(/\w\w/g)!.map((x) => parseInt(x, 16));
  return `rgb(${pa.map((v, i) => Math.round(v + (pb[i] - v) * u)).join(",")})`;
}

/** Diverging carbon scale: cool = cleaner than the national sqft-weighted
 * mean, warm = dirtier. One meaningful midpoint; SSR-safe (no DOM access). */
function useCarbonColor(mid: number, isDark: boolean) {
  return useMemo(() => {
    const { cool, mid: midC, warm } = DIVERGING[isDark ? "dark" : "light"];
    const scale = scaleDiverging<string>()
      .domain([300, mid, 1100])
      .interpolator((t) =>
        t < 0.5 ? mixHex(cool, midC, t * 2) : mixHex(midC, warm, (t - 0.5) * 2),
      );
    return (v: number | null) => (v === null ? "transparent" : scale(Math.max(300, Math.min(1100, v))));
  }, [mid, isDark]);
}

export default function UsMap({
  facilities,
  nationalMeanCo2,
  waterColors: waterColorsLight,
  waterColorsDark,
  waterOrder,
  waterLabels,
}: Props) {
  const [mode, setMode] = useState<Mode>("carbon");
  const [hover, setHover] = useState<{ f: FacilityPoint; x: number; y: number } | null>(null);
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    setIsDark(mq.matches);
    const onChange = (e: MediaQueryListEvent) => setIsDark(e.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const waterColors = isDark ? waterColorsDark : waterColorsLight;

  const { statesPath, borders, project } = useMemo(() => {
    const topo = statesTopo as unknown as Topology<{ states: GeometryCollection }>;
    const states = feature(topo, topo.objects.states);
    // This us-atlas build ships unprojected lon/lat — project geometry and
    // points through the same albersUsa transform.
    const projection = geoAlbersUsa().scale(1300).translate([W / 2, H / 2]);
    const path = geoPath(projection);
    return {
      statesPath: path(states) ?? "",
      borders: path(mesh(topo, topo.objects.states, (a, b) => a !== b)) ?? "",
      // Round to 2dp: server (Node) and browser trig differ in the last ulp,
      // which otherwise triggers React hydration mismatches on cx/cy.
      project: (lon: number, lat: number) => {
        const p = projection([lon, lat]);
        return p ? ([Math.round(p[0] * 100) / 100, Math.round(p[1] * 100) / 100] as [number, number]) : null;
      },
    };
  }, []);

  const carbonColor = useCarbonColor(nationalMeanCo2, isDark);

  const dots = useMemo(
    () =>
      facilities
        .map((f) => {
          const p = project(f.lon, f.lat);
          return p ? { f, x: p[0], y: p[1] } : null;
        })
        .filter((d): d is { f: FacilityPoint; x: number; y: number } => d !== null),
    [facilities, project],
  );

  const r = (f: FacilityPoint) =>
    f.sqft ? Math.max(1.6, Math.min(9, Math.sqrt(f.sqft / 40000))) : 1.6;

  return (
    <figure className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <figcaption className="text-sm font-medium">
          {mode === "carbon"
            ? "Grid CO₂ rate vs the national sqft-weighted mean"
            : "Basin water-stress category (WRI Aqueduct 4.0)"}
        </figcaption>
        <div
          className="flex rounded-lg border text-xs overflow-hidden"
          style={{ borderColor: "var(--border)" }}
          role="tablist"
          aria-label="Color facilities by"
        >
          {(["carbon", "water"] as Mode[]).map((m) => (
            <button
              key={m}
              role="tab"
              aria-selected={mode === m}
              className="px-3 py-1.5 font-medium"
              style={{
                background: mode === m ? "var(--accent)" : "transparent",
                color: mode === m ? "#fff" : "var(--text-secondary)",
              }}
              onClick={() => setMode(m)}
            >
              {m === "carbon" ? "Carbon" : "Water"}
            </button>
          ))}
        </div>
      </div>

      <div className="relative">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img"
          aria-label="Map of US data centers">
          <path
            d={statesPath}
            fill="var(--map-land)"
            stroke="var(--baseline)"
            strokeWidth={0.5}
          />
          <path
            d={borders}
            fill="none"
            stroke="var(--baseline)"
            strokeWidth={0.5}
          />
          {dots.map(({ f, x, y }, i) => (
            <circle
              key={i}
              cx={x}
              cy={y}
              r={r(f)}
              fill={mode === "carbon" ? carbonColor(f.co2) : waterColors[f.bws]}
              stroke="var(--baseline)"
              strokeWidth={0.4}
              opacity={0.85}
              onMouseEnter={() => setHover({ f, x, y })}
              onMouseLeave={() => setHover(null)}
              style={{ cursor: "pointer" }}
            />
          ))}
        </svg>

        {hover && (
          <div
            className="card absolute z-10 px-3 py-2 text-xs shadow-lg pointer-events-none max-w-60"
            style={{
              left: `${(hover.x / W) * 100}%`,
              top: `${(hover.y / H) * 100}%`,
              transform: "translate(-50%, calc(-100% - 10px))",
            }}
          >
            <p className="font-semibold">
              {hover.f.name ?? hover.f.operator ?? "Data center"}
            </p>
            <p style={{ color: "var(--text-secondary)" }}>
              {hover.f.county ? `${hover.f.county}, ` : ""}
              {hover.f.state}
              {hover.f.operator && hover.f.name ? ` · ${hover.f.operator}` : ""}
            </p>
            <p className="tabular mt-1">
              {hover.f.co2 !== null ? `${Math.round(hover.f.co2)} lb/MWh (${hover.f.subregion})` : "no grid data"}
            </p>
            <p>{waterLabels[hover.f.bws]}</p>
            {hover.f.mw !== null && <p className="tabular">{hover.f.mw} MW</p>}
            {hover.f.dualRisk && (
              <p className="font-medium" style={{ color: "var(--div-warm)" }}>
                ⚠ dual risk
              </p>
            )}
          </div>
        )}
      </div>

      {mode === "water" ? (
        <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs" aria-label="Legend">
          {waterOrder.map((c) => (
            <li key={c} className="flex items-center gap-1.5">
              <span
                aria-hidden
                className="inline-block h-3 w-3 rounded-full"
                style={{ background: waterColors[c], border: "1px solid var(--border)" }}
              />
              <span style={{ color: "var(--text-secondary)" }}>{c}</span>
            </li>
          ))}
        </ul>
      ) : (
        <div className="flex items-center gap-2 text-xs" aria-label="Legend">
          <span style={{ color: "var(--text-secondary)" }}>cleaner</span>
          <span
            aria-hidden
            className="h-2 w-40 rounded-full"
            style={{
              background:
                "linear-gradient(to right, var(--div-cool), var(--div-mid), var(--div-warm))",
            }}
          />
          <span style={{ color: "var(--text-secondary)" }}>dirtier</span>
          <span style={{ color: "var(--text-muted)" }}>
            · midpoint = {Math.round(nationalMeanCo2)} lb/MWh (national sqft-weighted mean)
          </span>
        </div>
      )}
    </figure>
  );
}

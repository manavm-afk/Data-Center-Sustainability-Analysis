import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { FacilityPoint, Meta, StateSummary, WaterCategory } from "./types";

const DATA_DIR = join(process.cwd(), "public", "data");

function readJson<T>(name: string): T {
  return JSON.parse(readFileSync(join(DATA_DIR, name), "utf-8")) as T;
}

export function getMeta(): Meta {
  return readJson<Meta>("meta.json");
}

export function getStateSummaries(): StateSummary[] {
  return readJson<StateSummary[]>("state_summary.json");
}

interface GeoFeature {
  geometry: { coordinates: [number, number] };
  properties: Record<string, unknown>;
}

/** Slim the full facilities GeoJSON down to what the map needs. */
export function getFacilityPoints(): FacilityPoint[] {
  const geojson = readJson<{ features: GeoFeature[] }>("facilities.geojson");
  return geojson.features.map((f) => {
    const p = f.properties;
    const co2 = (p.SRCO2RTA as number | null) ?? null;
    const bws = (p.bws_category as WaterCategory | null) ?? "No Data";
    return {
      lon: f.geometry.coordinates[0],
      lat: f.geometry.coordinates[1],
      name: (p.name as string | null) ?? null,
      operator: (p.operator as string | null) ?? null,
      state: p.state_abb as string,
      county: (p.county as string | null) ?? null,
      co2,
      subregion: (p.egrid_subregion as string | null) ?? null,
      bws,
      bwsScore: (p.bws_score as number | null) ?? null,
      sqft: (p.sqft as number | null) ?? null,
      dualRisk:
        co2 !== null && co2 > 700 && (bws === "High" || bws === "Extremely High"),
    };
  });
}

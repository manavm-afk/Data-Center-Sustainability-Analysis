export type WaterCategory =
  | "Low"
  | "Low-Medium"
  | "Medium-High"
  | "High"
  | "Extremely High"
  | "Arid"
  | "No Data";

export interface Meta {
  generated: string;
  pipeline: string;
  datasets: Record<
    string,
    {
      name: string;
      version_used: string;
      access_date: string;
      source_url: string;
      license: string | null;
      citation: string | null;
    }
  >;
  water_stress_vocabulary: {
    category_order: WaterCategory[];
    category_to_label: Record<WaterCategory, string>;
    category_colors: Record<WaterCategory, string>;
    category_colors_dark: Record<WaterCategory, string>;
  };
  headline_numbers: {
    n_facilities: number;
    n_states: number;
    mean_co2_rate_unweighted_lb_mwh: number;
    mean_co2_rate_sqft_weighted_lb_mwh: number;
    n_high_water_stress: number;
    pct_high_water_stress_of_with_data: number;
    n_arid: number;
    n_no_data: number;
    n_dual_risk: number;
    dual_risk_definition: string;
    n_with_mw_capacity: number;
  };
  attribution: string[];
}

/** Slim facility record passed to the client map (subset of GeoJSON props). */
export interface FacilityPoint {
  lon: number;
  lat: number;
  name: string | null;
  operator: string | null;
  state: string;
  county: string | null;
  co2: number | null; // SRCO2RTA lb/MWh
  subregion: string | null;
  bws: WaterCategory;
  bwsScore: number | null;
  mw: number | null;
  sqft: number | null;
  dualRisk: boolean;
}

export interface StateSummary {
  state: string;
  state_abb: string;
  dc_count: number;
  total_sqft: number | null;
  mean_co2_rate: number | null;
  mean_co2_rate_sqftw: number | null;
  mean_co2_rate_mww: number | null;
  sqft_coverage_pct: number | null;
  mw_coverage_pct: number | null;
  bws_category_mode: WaterCategory | null;
  state_co2_rate: number | null;
  state_renewable_pct: number | null;
}

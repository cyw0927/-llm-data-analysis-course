export type Region = {
  region_code: string;
  region_name: string;
  center_lat: number | null;
  center_lng: number | null;
};
export type TrendRow = {
  reference_date: string;
  keyword: string;
  ratio: number;
};
export type DemandRow = {
  reference_date: string;
  region_code: string;
  stay_strength: number | null;
  consumption_strength: number | null;
};
export type PlaceRow = {
  id: number;
  region_code: string | null;
  search_category: string;
  name: string;
  category: string | null;
  latitude: number | null;
  longitude: number | null;
  address?: string | null;
  road_address?: string | null;
  source_link?: string | null;
  collected_at?: string;
};
export type AnalysisRow = {
  analysis_date: string;
  region_code: string;
  summary: string;
  limitations: string | null;
  llm_provider?: string | null;
  model_name?: string | null;
  created_at?: string;
};
export type DashboardData = {
  regions: Region[];
  trends: TrendRow[];
  demands: DemandRow[];
  places: PlaceRow[];
  analyses: AnalysisRow[];
};

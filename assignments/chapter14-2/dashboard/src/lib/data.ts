import { createClient } from "@supabase/supabase-js";
import type { DashboardData } from "./types";

/** Server-rendered route에서 Publishable Key + RLS로 읽기 전용 조회. */
export async function getDashboardData(
  url: string,
  publishableKey: string,
): Promise<DashboardData> {
  const db = createClient(url, publishableKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
  const [regions, trends, demands, places, analyses] = await Promise.all([
    db.from("regions").select("region_code,region_name,center_lat,center_lng")
      .order("region_name", { ascending: true }).limit(300),
    db.from("naver_trend").select("reference_date,keyword,ratio")
      .order("reference_date", { ascending: false }).limit(240),
    db.from("tourism_demand").select("reference_date,region_code,stay_strength,consumption_strength")
      .order("reference_date", { ascending: false }).limit(500),
    db.from("local_places").select("id,region_code,search_category,name,category,latitude,longitude")
      .order("collected_at", { ascending: false }).limit(500),
    db.from("ai_region_analysis").select("analysis_date,region_code,summary,limitations")
      .order("analysis_date", { ascending: false }).limit(100),
  ]);
  for (const [name, response] of [
    ["regions", regions], ["naver_trend", trends],
    ["tourism_demand", demands], ["local_places", places],
    ["ai_region_analysis", analyses],
  ] as const) {
    if (response.error) {
      throw new Error(`Supabase ${name} 조회 실패: ${response.error.message}`);
    }
  }
  return {
    regions: regions.data ?? [],
    trends: trends.data ?? [],
    demands: demands.data ?? [],
    places: places.data ?? [],
    analyses: analyses.data ?? [],
  };
}

import { createClient } from "@supabase/supabase-js";
import type {
  AnalysisRow,
  DashboardData,
  DemandRow,
  PlaceRow,
  Region,
  TrendRow,
} from "./types";

/** Public SELECT only. Paginate so growing history never hides districts or places. */
export async function getDashboardData(
  url: string,
  publishableKey: string,
): Promise<DashboardData> {
  if (publishableKey.startsWith("sb_secret_"))
    throw new Error("Public read key required");
  if (publishableKey.startsWith("eyJ")) {
    try {
      const payload = JSON.parse(
        Buffer.from(publishableKey.split(".")[1], "base64url").toString(),
      );
      if (payload.role !== "anon") throw new Error("Public read key required");
    } catch {
      throw new Error("Public read key required");
    }
  }
  const db = createClient(url, publishableKey, {
    auth: { persistSession: false, autoRefreshToken: false },
    global: {
      fetch: (input, init) => fetch(input, { ...init, cache: "no-store" }),
    },
  });
  async function read<T>(
    table: string,
    fields: string,
    order: string,
  ): Promise<T[]> {
    const result: T[] = [];
    const pageSize = 500;
    for (let offset = 0; ; offset += pageSize) {
      const { data, error } = await db
        .from(table)
        .select(fields)
        .order(order, { ascending: false })
        .order("id", { ascending: false })
        .range(offset, offset + pageSize - 1);
      if (error)
        throw new Error(`${table} read failed (${error.code ?? "unknown"})`);
      result.push(...((data ?? []) as unknown as T[]));
      if (!data || data.length < pageSize) return result;
    }
  }
  // regions has a string primary key, rather than the numeric id on observations.
  const regions = db
    .from("regions")
    .select("region_code,region_name,center_lat,center_lng")
    .order("region_code", { ascending: true })
    .limit(500);
  const [regionResult, trends, demands, places, analyses] = await Promise.all([
    regions,
    read<TrendRow>(
      "naver_trend",
      "reference_date,keyword,ratio",
      "reference_date",
    ),
    read<DemandRow>(
      "tourism_demand",
      "reference_date,region_code,stay_strength,consumption_strength",
      "reference_date",
    ),
    read<PlaceRow>(
      "local_places",
      "id,region_code,search_category,name,category,latitude,longitude,address,road_address,source_link,collected_at",
      "collected_at",
    ),
    read<AnalysisRow>(
      "ai_region_analysis",
      "analysis_date,region_code,summary,limitations,llm_provider,model_name,created_at",
      "analysis_date",
    ),
  ]);
  if (regionResult.error)
    throw new Error(
      `regions read failed (${regionResult.error.code ?? "unknown"})`,
    );
  return {
    regions: (regionResult.data ?? []) as Region[],
    trends,
    demands,
    places,
    analyses,
  };
}

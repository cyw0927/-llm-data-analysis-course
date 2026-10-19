import type {
  AnalysisRow,
  DashboardData,
  DemandRow,
  PlaceRow,
  Region,
  TrendRow,
} from "./types";

export function initialRegion(data: DashboardData): string {
  if (data.regions.some((row) => row.region_code === "11")) return "11";
  return data.regions[0]?.region_code ?? "all";
}

export function latestForRegion<T extends { region_code: string }>(
  rows: T[],
  region: string,
  date: (row: T) => string,
): T | undefined {
  if (region === "all") return undefined;
  return rows
    .filter((row) => row.region_code === region)
    .reduce<
      T | undefined
    >((latest, row) => (!latest || date(row) > date(latest) ? row : latest), undefined);
}

export function matchesRegion(code: string | null, region: string): boolean {
  return (
    region === "all" ||
    (region.length === 2 ? !!code?.startsWith(region) : code === region)
  );
}

export function filterPlaces(
  places: PlaceRow[],
  region: string,
  category: string,
  search = "",
): PlaceRow[] {
  const needle = search.trim().toLocaleLowerCase("ko-KR");
  return places.filter(
    (place) =>
      matchesRegion(place.region_code, region) &&
      (category === "all" || place.search_category === category) &&
      (!needle ||
        `${place.name} ${place.address ?? ""} ${place.road_address ?? ""} ${place.category ?? ""}`
          .toLocaleLowerCase("ko-KR")
          .includes(needle)),
  );
}

export function hasCoordinates(place: PlaceRow): boolean {
  return (
    typeof place.latitude === "number" &&
    Number.isFinite(place.latitude) &&
    typeof place.longitude === "number" &&
    Number.isFinite(place.longitude) &&
    place.latitude >= -90 &&
    place.latitude <= 90 &&
    place.longitude >= -180 &&
    place.longitude <= 180
  );
}

export function monthsBehind(
  reference: string | undefined,
  today: string,
): number | null {
  if (!reference || !/^\d{4}-\d{2}-\d{2}$/.test(reference)) return null;
  const [year, month] = reference.split("-").map(Number);
  const [nowYear, nowMonth] = today.split("-").map(Number);
  return Math.max(0, (nowYear - year) * 12 + nowMonth - month);
}

export function sortedRegions(regions: Region[]): Region[] {
  return [...regions].sort(
    (a, b) =>
      a.region_code.length - b.region_code.length ||
      a.region_name.localeCompare(b.region_name, "ko"),
  );
}

export function latestDemand(rows: DemandRow[], region: string) {
  return latestForRegion(rows, region, (row) => row.reference_date);
}

export function latestAnalysis(rows: AnalysisRow[], region: string) {
  return latestForRegion(
    rows,
    region,
    (row) => `${row.analysis_date}|${row.created_at ?? ""}`,
  );
}

export function safeSourceLink(
  value: string | null | undefined,
): string | undefined {
  if (!value) return undefined;
  try {
    const url = new URL(value);
    return ["https:", "http:"].includes(url.protocol) ? url.href : undefined;
  } catch {
    return undefined;
  }
}

/** Calendar months ending at the latest observed month, not the wall clock. */
export function trendInMonths(rows: TrendRow[], months: number | null): TrendRow[] {
  if (months == null || !rows.length) return rows;
  const latest = rows.reduce((date, row) => row.reference_date > date ? row.reference_date : date, "");
  const [year, month] = latest.split("-").map(Number);
  const start = new Date(Date.UTC(year, month - months, 1)).toISOString().slice(0, 10);
  return rows.filter((row) => row.reference_date >= start);
}

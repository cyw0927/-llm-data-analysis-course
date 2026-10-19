const { test } = require("node:test");
const assert = require("node:assert/strict");
const {
  latestDemand,
  latestAnalysis,
  matchesRegion,
  filterPlaces,
  hasCoordinates,
  monthsBehind,
  safeSourceLink,
  initialRegion,
  trendInMonths,
} = require("../src/lib/selectors.ts");

test("regional KPIs never borrow another district or show an aggregate for all regions", () => {
  const rows = [
    { region_code: "11", reference_date: "2025-09-01", stay_strength: 89.81 },
    { region_code: "11110", reference_date: "2026-01-01", stay_strength: 111 },
  ];
  assert.equal(latestDemand(rows, "11").stay_strength, 89.81);
  assert.equal(latestDemand(rows, "all"), undefined);
  assert.equal(latestDemand(rows, "11680"), undefined);
});
test("latest observation is chosen within the selected region", () => {
  const rows = [
    { region_code: "11", reference_date: "2025-10-01" },
    { region_code: "11", reference_date: "2025-09-01" },
    { region_code: "11110", reference_date: "2026-01-01" },
  ];
  assert.equal(latestDemand(rows, "11").reference_date, "2025-10-01");
});
test("city place filter includes its districts, district filter stays exact", () => {
  assert.equal(matchesRegion("11680", "11"), true);
  assert.equal(matchesRegion("11110", "11680"), false);
  assert.equal(matchesRegion(null, "11"), false);
  assert.equal(matchesRegion(null, "all"), true);
});
test("category and address search combine with region filtering", () => {
  const rows = [
    {
      id: 1,
      region_code: "11680",
      search_category: "카페",
      name: "한강",
      road_address: "서울 강남구",
    },
    { id: 2, region_code: "11110", search_category: "관광명소", name: "한강" },
  ];
  assert.deepEqual(
    filterPlaces(rows, "11", "카페", "강남").map((p) => p.id),
    [1],
  );
  assert.equal(filterPlaces(rows, "11680", "관광명소").length, 0);
});
test("invalid and partially missing coordinates never reach map markers", () => {
  for (const point of [
    { latitude: null, longitude: 127 },
    { latitude: NaN, longitude: 127 },
    { latitude: 37, longitude: Infinity },
    { latitude: 375665000, longitude: 1269780000 },
  ])
    assert.equal(hasCoordinates(point), false);
  assert.equal(hasCoordinates({ latitude: 37.5665, longitude: 126.978 }), true);
});
test("stale data is based on observation month, including year rollover", () => {
  assert.equal(monthsBehind("2025-09-01", "2026-10-16"), 13);
  assert.equal(monthsBehind("2026-10-01", "2026-10-16"), 0);
  assert.equal(monthsBehind(undefined, "2026-10-16"), null);
});
test("AI latest tie is resolved by actual creation time and never crosses regions", () => {
  const rows = [
    {
      region_code: "11",
      analysis_date: "2026-10-16",
      created_at: "2026-10-16T08:00:00Z",
      summary: "old",
    },
    {
      region_code: "11",
      analysis_date: "2026-10-16",
      created_at: "2026-10-16T09:00:00Z",
      summary: "new",
    },
  ];
  assert.equal(latestAnalysis(rows, "11").summary, "new");
  assert.equal(latestAnalysis(rows, "11110"), undefined);
});
test("untrusted place URLs cannot become script links", () => {
  assert.equal(safeSourceLink("javascript:alert(1)"), undefined);
  assert.equal(safeSourceLink("invalid"), undefined);
  assert.equal(
    safeSourceLink("https://map.naver.com/"),
    "https://map.naver.com/",
  );
});
test("initial display uses Seoul when present so available KPIs and AI are visible", () => {
  assert.equal(
    initialRegion({
      regions: [{ region_code: "11110" }, { region_code: "11" }],
    }),
    "11",
  );
  assert.equal(initialRegion({ regions: [] }), "all");
});

test("Supabase reads paginate beyond 500 rows without dropping the final page", async () => {
  const { getDashboardData } = require("../src/lib/data.ts");
  const originalFetch = global.fetch;
  const requests = [];
  global.fetch = async (input) => {
    const url = new URL(
      typeof input === "string" ? input : (input.url ?? String(input)),
    );
    const table = url.pathname.split("/").pop();
    const offset = Number(url.searchParams.get("offset") ?? 0);
    requests.push({ table, offset });
    const rows =
      table === "naver_trend"
        ? Array.from(
            { length: Math.min(500, Math.max(0, 1001 - offset)) },
            (_, index) => ({
              reference_date: "2026-10-01",
              keyword: `term-${offset + index}`,
              ratio: 10,
            }),
          )
        : table === "regions"
          ? [
              {
                region_code: "11",
                region_name: "서울특별시",
                center_lat: null,
                center_lng: null,
              },
            ]
          : [];
    return new Response(JSON.stringify(rows), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  };
  try {
    const result = await getDashboardData(
      "https://dashboard-test.example",
      "sb_publishable_test",
    );
    assert.equal(result.trends.length, 1001);
    assert.equal(result.trends.at(-1).keyword, "term-1000");
    assert.deepEqual(
      requests.filter((r) => r.table === "naver_trend").map((r) => r.offset),
      [0, 500, 1000],
    );
  } finally {
    global.fetch = originalFetch;
  }
});

test("privileged keys are rejected before any dashboard request", async () => {
  const { getDashboardData } = require("../src/lib/data.ts");
  await assert.rejects(
    getDashboardData("https://dashboard-test.example", "sb_secret_test"),
    /Public read key required/,
  );
  const payload = Buffer.from(
    JSON.stringify({ role: "service_role" }),
  ).toString("base64url");
  await assert.rejects(
    getDashboardData(
      "https://dashboard-test.example",
      `eyJhbGciOiJIUzI1NiJ9.${payload}.test`,
    ),
    /Public read key required/,
  );
});

test("trend periods use calendar months across year boundaries and retain all keywords", () => {
  const rows = [
    { reference_date: "2025-08-01", keyword: "여행", ratio: 1 },
    { reference_date: "2025-09-01", keyword: "여행", ratio: 2 },
    { reference_date: "2026-02-01", keyword: "여행", ratio: 3 },
    { reference_date: "2026-02-01", keyword: "맛집", ratio: 4 },
  ];
  assert.deepEqual(trendInMonths(rows, 6), rows.slice(1));
  assert.deepEqual(trendInMonths(rows, null), rows);
  assert.deepEqual(trendInMonths([], 6), []);
});

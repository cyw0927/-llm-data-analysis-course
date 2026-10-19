"use client";

import { useMemo, useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { NaverMap } from "@/components/NaverMap";
import { TrendChart } from "@/components/TrendChart";
import {
  filterPlaces,
  initialRegion,
  latestAnalysis,
  latestDemand,
  matchesRegion,
  monthsBehind,
  safeSourceLink,
  sortedRegions,
  trendInMonths,
} from "@/lib/selectors";
import type { DashboardData } from "@/lib/types";

const formatNumber = (value: number | null | undefined) =>
  value == null
    ? "—"
    : value.toLocaleString("ko-KR", { maximumFractionDigits: 2 });
const monthLabel = (value?: string) =>
  value
    ? `${value.slice(0, 4)}년 ${Number(value.slice(5, 7))}월`
    : "기준월 없음";

function Symbol({ type }: { type: "map" | "trend" | "spark" | "clock" }) {
  const paths = {
    map: (
      <>
        <path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3Z" />
        <path d="M9 3v15M15 6v15" />
      </>
    ),
    trend: (
      <>
        <path d="M4 19V5M4 19h16M7 14l4-5 4 3 5-7" />
      </>
    ),
    spark: (
      <>
        <path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z" />
      </>
    ),
    clock: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
      </>
    ),
  };
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[type]}
    </svg>
  );
}

export function Dashboard({
  data,
  loadedAt,
}: {
  data: DashboardData;
  loadedAt: string;
}) {
  const router = useRouter();
  const [refreshing, startRefresh] = useTransition();
  const [region, setRegion] = useState(() => initialRegion(data));
  const [category, setCategory] = useState("all");
  const [search, setSearch] = useState("");
  const [trendPeriod, setTrendPeriod] = useState("all");
  const displayedTrends = useMemo(
    () => trendInMonths(data.trends, trendPeriod === "all" ? null : Number(trendPeriod)),
    [data.trends, trendPeriod],
  );
  const regions = useMemo(() => sortedRegions(data.regions), [data.regions]);
  const regionName =
    regions.find((row) => row.region_code === region)?.region_name ??
    "전체 지역";
  const categories = useMemo(
    () =>
      [
        ...new Set(
          data.places
            .filter((p) => matchesRegion(p.region_code, region))
            .map((p) => p.search_category),
        ),
      ].sort(),
    [data.places, region],
  );
  const places = useMemo(
    () => filterPlaces(data.places, region, category, search),
    [data.places, region, category, search],
  );
  const demand = latestDemand(data.demands, region);
  const analysis = latestAnalysis(data.analyses, region);
  const lag = monthsBehind(demand?.reference_date, loadedAt.slice(0, 10));
  const latestTrend = data.trends.reduce(
    (latest, row) =>
      row.reference_date > latest ? row.reference_date : latest,
    "",
  );
  const trendMonths = new Set(displayedTrends.map((row) => row.reference_date))
    .size;
  const changeRegion = (value: string) => {
    setRegion(value);
    setCategory("all");
    setSearch("");
  };

  return (
    <div className="app-shell">
      <aside className="side-nav" aria-label="주 메뉴">
        <a className="brand" href="#overview">
          <span className="brand-mark">
            <Symbol type="map" />
          </span>
          <span>
            TRIP<span className="brand-light">SIGNAL</span>
            <small>TOURISM INSIGHTS</small>
          </span>
        </a>
        <p className="nav-caption">WORKSPACE</p>
        <a className="nav-item nav-current" href="#overview">
          <Symbol type="trend" />
          관광 인사이트
        </a>
        <a className="nav-item" href="#explore">
          <Symbol type="map" />
          지역 탐색
        </a>
        <a className="nav-item" href="#analysis">
          <Symbol type="spark" />
          AI 브리핑
        </a>
        <div className="side-note">
          <span className="status-dot" />
          검증된 관측 데이터
          <small>
            기준 기간과 지역 범위를
            <br />
            함께 확인하세요.
          </small>
        </div>
      </aside>
      <main className="dashboard-main" id="overview">
        <div className="topbar">
          <span>
            워크스페이스 <span className="separator">/</span> 관광 인사이트
          </span>
          <span className="topbar-status">
            <span className="status-dot" />
            데이터 연결됨
          </span>
        </div>
        <header className="page-header">
          <div>
            <p className="eyebrow">REGIONAL TOURISM INTELLIGENCE</p>
            <h1>
              지역 관광 인사이트<span className="heading-dot">.</span>
            </h1>
            <p className="page-description">
              검색 관심도와 지역 관광 지표를 한눈에 살펴보세요.
            </p>
          </div>
          <button
            className="refresh-button"
            disabled={refreshing}
            onClick={() => startRefresh(() => router.refresh())}
          >
            <span className={refreshing ? "spin" : ""}>↻</span>
            {refreshing ? "불러오는 중" : "데이터 새로고침"}
          </button>
        </header>
        <section className="region-bar" aria-label="조회 지역 선택">
          <div className="region-label">
            <span className="icon-box">
              <Symbol type="map" />
            </span>
            <div>
              <span className="label-caption">선택 지역</span>
              <strong>{regionName}</strong>
            </div>
          </div>
          <label className="sr-only" htmlFor="region-select">
            지역 선택
          </label>
          <select
            id="region-select"
            className="input region-select"
            value={region}
            onChange={(e) => changeRegion(e.target.value)}
          >
            <option value="all">전체 지역 · 장소 둘러보기</option>
            {regions.map((r) => (
              <option key={r.region_code} value={r.region_code}>
                {r.region_code.length > 2 ? "서울 · " : ""}
                {r.region_name}
              </option>
            ))}
          </select>
          <p className="scope-note">
            관광 지표는 선택한 지역 기준
            <br />
            검색 관심도는 전국 기준
          </p>
        </section>
        {lag != null && lag > 2 && (
          <div className="period-notice">
            <Symbol type="clock" />
            <p>
              관광 지표는 <strong>{monthLabel(demand?.reference_date)}</strong>{" "}
              자료입니다. 최신 검색 관심도({monthLabel(latestTrend)})와 기준
              기간이 다릅니다.
            </p>
            <span>기간 확인</span>
          </div>
        )}
        <section className="metric-grid" aria-label="핵심 관광 지표">
          <article className="metric-card metric-featured">
            <div className="metric-top">
              <span>관광 체류 강도</span>
              <span className="metric-symbol">↗</span>
            </div>
            <p className="metric-value">
              {formatNumber(demand?.stay_strength)}
              <small>지수</small>
            </p>
            <p className="metric-foot">
              {region === "all"
                ? "지역을 선택하면 표시됩니다"
                : `${monthLabel(demand?.reference_date)} · ${regionName}`}
            </p>
          </article>
          <article className="metric-card">
            <div className="metric-top">
              <span>관광 소비 강도</span>
              <span className="metric-symbol">◎</span>
            </div>
            <p className="metric-value">
              {formatNumber(demand?.consumption_strength)}
              <small>지수</small>
            </p>
            <p className="metric-foot">체류 강도와 별개의 관광 지표</p>
          </article>
          <article className="metric-card">
            <div className="metric-top">
              <span>탐색할 수 있는 장소</span>
              <Symbol type="map" />
            </div>
            <p className="metric-value">
              {places.length.toLocaleString("ko-KR")}
              <small>곳</small>
            </p>
            <p className="metric-foot">
              {data.places.length
                ? "선택한 지역·유형·검색 조건 기준"
                : "실제 장소 데이터를 준비하고 있습니다"}
            </p>
          </article>
          <article className="metric-card">
            <div className="metric-top">
              <span>검색 관심도 관측</span>
              <Symbol type="trend" />
            </div>
            <p className="metric-value">
              {trendMonths}
              <small>개월</small>
            </p>
            <p className="metric-foot">
              {new Set(data.trends.map((row) => row.keyword)).size}개 키워드 ·{" "}
              {displayedTrends.length}개 관측값
            </p>
          </article>
        </section>
        <section className="panel trend-panel" id="trends">
          <div className="section-header">
            <div>
              <p className="section-kicker">SEARCH TRENDS</p>
              <h2>전국 검색 관심도</h2>
            </div>
            <span className="subtle-badge">전국 · 월별 상대지수</span>
          </div>
          <p className="section-description">
            여행·축제·캠핑·맛집에 대한 검색 관심도입니다. 검색 건수나 지역별
            관광 수요를 뜻하지 않습니다.
          </p>
          <div className="trend-period-control">
            <label htmlFor="trend-period-select">검색 관심도 기간</label>
            <select id="trend-period-select" className="input" value={trendPeriod} onChange={(e) => setTrendPeriod(e.target.value)}>
              <option value="all">전체 관측 기간</option>
              <option value="12">최근 관측 12개월</option>
              <option value="6">최근 관측 6개월</option>
            </select>
          </div>
          <TrendChart rows={displayedTrends} />
          <div className="panel-footnote">
            <span>출처 NAVER Search Trend</span>
            <span>
              최신 관측 {monthLabel(latestTrend)} · 이번 달 값은 부분 월
            </span>
          </div>
        </section>
        <section className="panel" id="explore">
          <div className="section-header">
            <div>
              <p className="section-kicker">EXPLORE THE REGION</p>
              <h2>{regionName} 장소 탐색</h2>
            </div>
            <span className="subtle-badge">{places.length}개 장소</span>
          </div>
          <div className="place-controls">
            <label className="search-box">
              <span aria-hidden="true">⌕</span>
              <input
                aria-label="장소 검색"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="장소 이름 또는 주소로 검색"
              />
            </label>
            <label className="sr-only" htmlFor="category-select">
              장소 유형
            </label>
            <select
              id="category-select"
              className="input"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            >
              <option value="all">전체 장소 유형</option>
              {categories.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </div>
          <div className="explore-grid">
            <NaverMap
              places={places}
              region={regions.find((row) => row.region_code === region)}
            />
            <div className="place-list" aria-live="polite">
              {places.length ? (
                <ul>
                  {places.map((place) => (
                    <li key={place.id}>
                      <span className="place-category">
                        {place.search_category}
                      </span>
                      <h3>
                        {safeSourceLink(place.source_link) ? (
                          <a
                            href={safeSourceLink(place.source_link)}
                            target="_blank"
                            rel="noreferrer"
                          >
                            {place.name}
                            <span aria-hidden="true"> ↗</span>
                          </a>
                        ) : (
                          place.name
                        )}
                      </h3>
                      <p>
                        {place.road_address ||
                          place.address ||
                          "주소 정보 없음"}
                      </p>
                      <small>{place.category}</small>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="empty-list">
                  <Symbol type="map" />
                  <h3>
                    {data.places.length
                      ? "조건에 맞는 장소가 없습니다"
                      : "장소 정보를 준비하고 있습니다"}
                  </h3>
                  <p>
                    {data.places.length
                      ? "다른 지역이나 장소 유형으로 검색해 보세요."
                      : "검증된 장소가 등록되면 지도와 목록에 함께 표시됩니다."}
                  </p>
                </div>
              )}
            </div>
          </div>
        </section>
        <section className="panel ai-panel" id="analysis">
          <div className="section-header">
            <div className="ai-heading">
              <span className="ai-icon">
                <Symbol type="spark" />
              </span>
              <div>
                <p className="section-kicker">AI REGIONAL BRIEFING</p>
                <h2>{regionName} AI 브리핑</h2>
              </div>
            </div>
            <span className="subtle-badge">
              {analysis ? "저장된 분석" : "분석 대기"}
            </span>
          </div>
          {analysis ? (
            <>
              <div className="analysis-meta">
                <span>분석일 {analysis.analysis_date}</span>
                {analysis.model_name && (
                  <span>
                    {analysis.llm_provider ?? "AI"} · {analysis.model_name}
                  </span>
                )}
              </div>
              <div className="analysis-body">
                {analysis.summary
                  .split(/\n\s*\n/)
                  .filter(Boolean)
                  .map((paragraph, index) => (
                    <p key={index}>{paragraph}</p>
                  ))}
              </div>
              {analysis.limitations && (
                <div className="analysis-limit">
                  <strong>해석할 때 확인하세요</strong>
                  <p>{analysis.limitations}</p>
                </div>
              )}
            </>
          ) : (
            <div className="analysis-empty">
              <p>
                {region === "all"
                  ? "지역을 선택하면 저장된 AI 분석을 확인할 수 있습니다."
                  : "이 지역에 저장된 AI 분석이 아직 없습니다."}
              </p>
              {region !== "11" &&
                data.analyses.some((row) => row.region_code === "11") && (
                  <button
                    className="text-button"
                    onClick={() => changeRegion("11")}
                  >
                    서울특별시 전체 분석 보기 →
                  </button>
                )}
            </div>
          )}
        </section>
        <footer className="dashboard-footer">
          <span>
            TRIPSIGNAL <span>관측 데이터로 이해하는 지역 관광</span>
          </span>
          <span>
            마지막 조회{" "}
            {new Date(loadedAt).toLocaleString("ko-KR", {
              timeZone: "Asia/Seoul",
              hour12: false,
            })}
          </span>
        </footer>
      </main>
    </div>
  );
}

"use client";

import { useMemo, useState } from "react";
import { NaverMap } from "@/components/NaverMap";
import { TrendChart } from "@/components/TrendChart";
import type { DashboardData } from "@/lib/types";

function number(value: number | null | undefined): string {
  return value == null ? "데이터 없음" : value.toLocaleString("ko-KR", { maximumFractionDigits: 2 });
}

export function Dashboard({ data }: { data: DashboardData }) {
  const [region, setRegion] = useState("all");
  const [category, setCategory] = useState("all");
  const categories = useMemo(() => [...new Set(data.places.map((p) => p.search_category))].sort(), [data.places]);

  const filteredPlaces = useMemo(() => data.places.filter(
    (p) => (region === "all" || p.region_code === region)
      && (category === "all" || p.search_category === category)
  ), [data.places, region, category]);
  const demand = useMemo(() => {
    const filtered = data.demands.filter((d) => region === "all" || d.region_code === region);
    return [...filtered].sort((a, b) => b.reference_date.localeCompare(a.reference_date))[0];
  }, [data.demands, region]);
  const analysis = useMemo(() => [...data.analyses]
    .filter((row) => region === "all" || row.region_code === region)
    .sort((a, b) => b.analysis_date.localeCompare(a.analysis_date))[0], [data.analyses, region]);
  const distinctRegions = data.regions.length ? data.regions : [
    ...new Set(data.demands.map((d) => d.region_code))
  ].map((code) => ({ region_code: code, region_name: code, center_lat: null, center_lng: null }));

  return (
    <main className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-8">
      <header className="space-y-2">
        <p className="text-sm font-bold tracking-widest text-blue-700">CHAPTER 14-2 · TOURISM DATA</p>
        <h1 className="text-3xl font-bold tracking-tight">지역 관광 수요 AI 대시보드</h1>
        <p className="muted">검증된 Supabase 데이터만 조회해. NAVER 검색 관심도는 전국 상대지수야.</p>
      </header>

      <section className="card flex flex-wrap gap-4" aria-label="지역 및 장소 유형 선택">
        <label className="flex min-w-52 flex-1 flex-col gap-2 text-sm font-medium">
          지역
          <select value={region} onChange={(e) => setRegion(e.target.value)} className="input">
            <option value="all">전체 (최근 기록)</option>
            {distinctRegions.map((r) => <option key={r.region_code} value={r.region_code}>{r.region_name}</option>)}
          </select>
        </label>
        <label className="flex min-w-52 flex-1 flex-col gap-2 text-sm font-medium">
          장소 유형
          <select value={category} onChange={(e) => setCategory(e.target.value)} className="input">
            <option value="all">전체 장소</option>
            {categories.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
      </section>

      <section className="grid grid-cols-2 gap-3 lg:grid-cols-4" aria-label="핵심 지표">
        <div className="card"><p className="muted">최근 관광 기준일</p><p className="kpi">{demand?.reference_date ?? "—"}</p></div>
        <div className="card"><p className="muted">관광 체류 강도</p><p className="kpi">{number(demand?.stay_strength)}</p></div>
        <div className="card"><p className="muted">관광 소비 강도</p><p className="kpi">{number(demand?.consumption_strength)}</p></div>
        <div className="card"><p className="muted">표시 장소 수</p><p className="kpi">{filteredPlaces.length.toLocaleString("ko-KR")}</p></div>
      </section>

      <div className="grid gap-5 lg:grid-cols-5">
        <section className="card space-y-3 lg:col-span-3">
          <h2 className="section-title">NAVER 지도 · 장소 마커</h2>
          <NaverMap places={filteredPlaces} />
        </section>
        <section className="card space-y-3 lg:col-span-2">
          <h2 className="section-title">장소 목록</h2>
          {!filteredPlaces.length ? <p className="muted">선택한 조건의 장소가 없어.</p> :
            <ul className="max-h-[400px] divide-y divide-slate-100 overflow-y-auto">
              {filteredPlaces.slice(0, 80).map((p) => (
                <li key={p.id} className="py-3">
                  <p className="font-medium">{p.name}</p>
                  <p className="muted">{p.search_category} · {p.category || "상세 분류 없음"}</p>
                </li>
              ))}
            </ul>}
        </section>
      </div>

      <section className="card space-y-3">
        <h2 className="section-title">전국 NAVER 검색 관심도 추이</h2>
        <p className="muted">ratio(0~100)는 검색 건수가 아니며 지역 필터를 적용하지 않아.</p>
        <TrendChart rows={data.trends} />
      </section>

      <section className="card space-y-3">
        <h2 className="section-title">저장된 AI 지역 분석</h2>
        {analysis ? <>
          <p className="muted">분석 기준일: {analysis.analysis_date}</p>
          <p className="whitespace-pre-wrap leading-7">{analysis.summary}</p>
          {analysis.limitations && <div className="border-t pt-3">
            <p className="text-sm font-semibold">이 결과의 한계</p>
            <p className="whitespace-pre-wrap text-slate-600">{analysis.limitations}</p>
          </div>}
        </> : <p className="muted">이 지역에 저장된 AI 분석이 아직 없어. Dashboard는 직접 LLM을 호출하지 않아.</p>}
      </section>
      <footer className="pb-5 text-xs text-slate-500">
        데이터 흐름: Make 수집 → Supabase 적재·검증 → 읽기 전용 Dashboard. 최신 기준일과 수집일은 다를 수 있어.
      </footer>
    </main>
  );
}

"use client";

import Script from "next/script";
import { useEffect, useRef, useState } from "react";
import type { PlaceRow } from "@/lib/types";

type MapInstance = { destroy?: () => void };
type NaverMapsApi = {
  LatLng: new (lat: number, lng: number) => unknown;
  Map: new (element: HTMLElement, options: { center: unknown; zoom: number }) => MapInstance;
  Marker: new (options: { position: unknown; map: MapInstance; title: string }) => unknown;
};

declare global {
  interface Window {
    naver?: { maps: NaverMapsApi };
  }
}

export function NaverMap({ places }: { places: PlaceRow[] }) {
  const key = process.env.NEXT_PUBLIC_NAVER_MAP_NCP_KEY_ID;
  const container = useRef<HTMLDivElement | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!loaded || !container.current || !window.naver?.maps) return;
    const api = window.naver.maps;
    const points = places.filter((place) =>
      place.latitude != null && place.longitude != null
      && Number.isFinite(place.latitude) && Number.isFinite(place.longitude)
      && place.latitude >= -90 && place.latitude <= 90
      && place.longitude >= -180 && place.longitude <= 180
    );
    const center = points[0];
    const map = new api.Map(container.current, {
      center: new api.LatLng(center?.latitude ?? 37.5665, center?.longitude ?? 126.978),
      zoom: center ? 10 : 7,
    });
    for (const point of points) {
      new api.Marker({
        position: new api.LatLng(point.latitude!, point.longitude!),
        map,
        title: point.name,
      });
    }
    return () => map.destroy?.();
  }, [loaded, places]);

  if (!key) {
    return <div className="empty">NAVER Maps API 키가 아직 설정되지 않았어. .env.local의 NAVER Map 키 ID를 확인해.</div>;
  }
  return (
    <div className="relative">
      <Script src={`https://oapi.map.naver.com/openapi/v3/maps.js?ncpKeyId=${encodeURIComponent(key)}`}
        strategy="afterInteractive" onReady={() => setLoaded(true)}
        onError={() => setFailed(true)} />
      {failed && <p className="text-sm text-rose-700">지도 스크립트 로딩 실패. 발급 상태/허용 도메인을 확인해.</p>}
      <div ref={container} className="h-[380px] w-full rounded-xl bg-slate-100"
        aria-label="관광 장소 지도" />
      {!places.some((p) => p.latitude != null && p.longitude != null) &&
        <p className="mt-2 text-sm text-slate-500">표시할 좌표가 없어서 기본 위치로 표시 중이야.</p>}
    </div>
  );
}

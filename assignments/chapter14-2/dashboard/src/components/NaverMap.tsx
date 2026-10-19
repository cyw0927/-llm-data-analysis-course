"use client";

import Script from "next/script";
import { useEffect, useRef, useState } from "react";
import { hasCoordinates } from "@/lib/selectors";
import type { PlaceRow, Region } from "@/lib/types";

type MapInstance = {
  destroy?: () => void;
  fitBounds: (
    coordinates: unknown[],
    options?: {
      top?: number;
      right?: number;
      bottom?: number;
      left?: number;
      maxZoom?: number;
    },
  ) => void;
};
type MarkerInstance = { setMap: (map: MapInstance | null) => void };
type NaverMapsApi = {
  LatLng: new (lat: number, lng: number) => unknown;
  Map: new (
    element: HTMLElement,
    options: { center: unknown; zoom: number; zoomControl: boolean },
  ) => MapInstance;
  Marker: new (options: {
    position: unknown;
    map: MapInstance;
    title: string;
  }) => MarkerInstance;
};
declare global {
  interface Window {
    naver?: { maps: NaverMapsApi };
    navermap_authFailure?: () => void;
  }
}

export function NaverMap({
  places,
  region,
}: {
  places: PlaceRow[];
  region?: Region;
}) {
  const key = process.env.NEXT_PUBLIC_NAVER_MAP_NCP_KEY_ID;
  const container = useRef<HTMLDivElement | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);
  const points = places.filter(hasCoordinates);

  useEffect(() => {
    if (!key) return;
    const previous = window.navermap_authFailure;
    const onFailure = () => setFailed(true);
    window.navermap_authFailure = onFailure;
    const timeout = window.setTimeout(() => {
      if (!window.naver?.maps) setFailed(true);
    }, 15000);
    return () => {
      window.clearTimeout(timeout);
      if (window.navermap_authFailure === onFailure)
        window.navermap_authFailure = previous;
    };
  }, [key]);

  useEffect(() => {
    if (!loaded || failed || !container.current || !window.naver?.maps) return;
    const api = window.naver.maps;
    const valid = places.filter(hasCoordinates);
    const coordinates = valid.map(
      (point) => new api.LatLng(point.latitude!, point.longitude!),
    );
    const center = valid[0];
    const map = new api.Map(container.current, {
      center: new api.LatLng(
        center?.latitude ?? region?.center_lat ?? 37.5665,
        center?.longitude ?? region?.center_lng ?? 126.978,
      ),
      zoom: valid.length === 1 ? 14 : 11,
      zoomControl: true,
    });
    if (coordinates.length > 1)
      map.fitBounds(coordinates, {
        top: 35,
        right: 35,
        bottom: 35,
        left: 35,
        maxZoom: 14,
      });
    const markers = valid.map(
      (point, index) =>
        new api.Marker({
          position: coordinates[index],
          map,
          title: point.name,
        }),
    );
    return () => {
      markers.forEach((marker) => marker.setMap(null));
      map.destroy?.();
    };
  }, [loaded, failed, places, region]);

  if (!key || failed)
    return (
      <div className="map-wrap">
        <div className="map-placeholder" role="status">
          <span className="map-pin" aria-hidden="true">
            ⌖
          </span>
          <h3>
            {failed
              ? "지도를 불러오지 못했습니다"
              : "지도 연결을 준비하고 있습니다"}
          </h3>
          <p>
            {failed
              ? "잠시 후 다시 시도해 주세요. 장소 정보는 오른쪽 목록에서 확인할 수 있습니다."
              : "지도 서비스가 연결되면 검증된 실제 장소를 이곳에서 살펴볼 수 있습니다."}
          </p>
          <small>NAVER MAPS</small>
        </div>
      </div>
    );
  return (
    <div className="map-wrap">
      <Script
        id="naver-map-sdk"
        src={`https://oapi.map.naver.com/openapi/v3/maps.js?ncpKeyId=${encodeURIComponent(key)}`}
        strategy="afterInteractive"
        onReady={() => setLoaded(true)}
        onError={() => setFailed(true)}
      />
      <div
        ref={container}
        className="map-canvas"
        aria-label={`${region?.region_name ?? "전체 지역"} 관광 장소 지도`}
      />
      {!loaded && (
        <div className="map-loading" role="status">
          지도를 불러오는 중입니다…
        </div>
      )}
      {loaded && !points.length && (
        <p className="map-note">
          선택한 조건에 표시할 장소 좌표가 없어 기본 지도를 표시합니다.
        </p>
      )}
    </div>
  );
}

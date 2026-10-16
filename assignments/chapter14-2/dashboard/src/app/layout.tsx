import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "지역 관광 수요 AI Dashboard | Chapter 14-2",
  description: "NAVER Trend와 관광 수요·장소 데이터를 Supabase에서 조회하는 실습용 지도 대시보드",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ko"><body>{children}</body></html>;
}

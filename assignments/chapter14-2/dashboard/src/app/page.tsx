import { Dashboard } from "@/components/Dashboard";
import { getDashboardData } from "@/lib/data";

export const dynamic = "force-dynamic";

function Notice({ title, content }: { title: string; content: string }) {
  return (
    <main className="notice-page">
      <p className="eyebrow">TRIPSIGNAL · TOURISM INSIGHTS</p>
      <h1>{title}</h1>
      <p>{content}</p>
      <a href="/">다시 불러오기 →</a>
    </main>
  );
}

export default async function Home() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if (!url || !key)
    return (
      <Notice
        title="데이터 연결을 준비하고 있습니다"
        content="관광 데이터 저장소에 연결되면 지역 지표와 분석을 확인할 수 있습니다."
      />
    );
  try {
    const data = await getDashboardData(url, key);
    return <Dashboard data={data} loadedAt={new Date().toISOString()} />;
  } catch (error) {
    // Do not expose service URLs, headers, or database details to the browser.
    console.error(
      "Dashboard public data read failed",
      error instanceof Error ? error.message : "unknown",
    );
    return (
      <Notice
        title="데이터를 불러오지 못했습니다"
        content="일시적으로 관광 데이터를 조회할 수 없습니다. 잠시 후 다시 불러와 주세요."
      />
    );
  }
}

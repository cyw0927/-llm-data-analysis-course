import { Dashboard } from "@/components/Dashboard";
import { getDashboardData } from "@/lib/data";

export const dynamic = "force-dynamic";

function Notice({ title, content }: { title: string; content: string }) {
  return (
    <main className="mx-auto mt-20 max-w-2xl rounded-2xl border bg-white p-8 shadow-sm">
      <p className="text-sm font-semibold text-blue-700">Chapter 14-2</p>
      <h1 className="mt-3 text-2xl font-bold">{title}</h1>
      <p className="mt-4 leading-7 text-slate-600">{content}</p>
    </main>
  );
}

export default async function Home() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if (!url || !key) {
    return <Notice title="Supabase 연결 설정이 필요해"
      content="dashboard/.env.local에 URL과 Publishable Key를 입력한 뒤 개발 서버를 재시작해. Secret Key는 넣으면 안 돼." />;
  }
  try {
    const data = await getDashboardData(url, key);
    return <Dashboard data={data} />;
  } catch (error) {
    const detail = error instanceof Error ? error.message : "알 수 없는 조회 오류";
    return <Notice title="Supabase 조회 실패"
      content={`DB 설정·테이블·RLS를 확인해. 오류: ${detail}`} />;
  }
}

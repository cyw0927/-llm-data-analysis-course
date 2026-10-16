"use client";

import { useMemo } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TrendRow } from "@/lib/types";

const COLORS = ["#2563eb", "#0891b2", "#16a34a", "#db2777"];

export function TrendChart({ rows }: { rows: TrendRow[] }) {
  const keywords = useMemo(() => [...new Set(rows.map((row) => row.keyword))].sort(), [rows]);
  const periods = useMemo(() => {
    const indexed = new Map<string, Record<string, string | number>>();
    for (const row of rows) {
      const found = indexed.get(row.reference_date) ?? { date: row.reference_date };
      found[row.keyword] = Number(row.ratio);
      indexed.set(row.reference_date, found);
    }
    return [...indexed.values()].sort((a, b) => String(a.date).localeCompare(String(b.date)));
  }, [rows]);

  if (!rows.length) return <p className="muted">NAVER 검색 관심도 데이터가 아직 없어.</p>;
  return (
    <div className="h-72 w-full" role="img" aria-label="전국 NAVER 키워드별 검색 상대 관심도 추이">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={periods} margin={{ top: 8, right: 14, left: -24, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="date" tickFormatter={(value: string) => value.slice(2, 7)} fontSize={11} />
          <YAxis domain={[0, 100]} fontSize={11} />
          <Tooltip />
          <Legend />
          {keywords.map((keyword, index) => (
            <Line key={keyword} type="monotone" dataKey={keyword}
              stroke={COLORS[index % COLORS.length]} strokeWidth={2}
              dot={false} connectNulls={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
